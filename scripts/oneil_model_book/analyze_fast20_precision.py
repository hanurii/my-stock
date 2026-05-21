"""§12 빠른 +20% 시그니처 — 정밀도(헛신호율) 검증 (위너 vs 비위너 대조).

§12 핵심신호를 *전향 트리거*로 정식화해, 위너표본 + 비위너 대조표본의
*모든 스윙저점*에 적용. 측정:
  정밀도 = 신호 발동한 지점 중 *클린 빠른 +20%* 가 따라온 비율
  기저율 = (신호 무관) 아무 스윙저점이 클린 빠른 +20% 가는 비율
  lift   = 정밀도 / 기저율 (>1이면 신호에 변별력)
  + 위너 vs 비위너 정밀도 비교(위너서만 통하고 비위너서 헛터지나)

신호(§12 실측 도출):
  거래량마름 v[b]/50일평균 ≤ 1.0  & 신고가아님 종가 ≤ 52주고가 88%
  & 50일선근처 |종가/50일평균−1| ≤ 10%  & 수급 외인or기관 60일 순매수>0
  (변형: +RS≥50, +직전60일 상승>0)
클린 빠른 +20% = 도중 −10% 안 빠지고 60거래일내 +20% 도달.

데이터: Yahoo(종가·거래량)·네이버 frgn(수급). 표본=위너 무작위 +
비위너(ranked_valid−위너) 무작위, 시드고정. 사이클내 사후·인-샘플·
상폐제외이나 *비위너 대조 포함* → 정밀도/헛신호 측정 가능. 환각 금지.

사용:  python analyze_fast20_precision.py [--nw 30] [--nc 30] [--seed 7]
"""
import argparse
import bisect
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.fetch import yahoo_symbol  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

CY = cyclecfg.DIR
GAIN, MAXH, DROP = 0.20, 60, 0.10


def nidx(d, ds):
    cand = [k for k in range(len(d)) if d[k] <= ds]
    return cand[-1] if cand else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nw", type=int, default=30)   # 위너 표본
    ap.add_argument("--nc", type=int, default=30)   # 비위너 대조 표본
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    winners = wf["winners"]
    win_codes = {x["code"] for x in winners}
    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]
    pool_ctrl = [r for r in rv if r["code"] not in win_codes
                 and not r.get("exclude_reason") and r.get("trough_date")
                 and r.get("n_days", 0) >= 60]
    random.seed(args.seed)
    smp_w = random.sample(winners, min(args.nw, len(winners)))
    smp_c = random.sample(pool_ctrl, min(args.nc, len(pool_ctrl)))

    # RS 백분위용 주봉 그리드
    any_d = U[list(U)[0]]["d"]
    sortmap = {}
    for gi in range(252, len(any_d), 5):
        gd = any_d[gi]
        rr = []
        for s in U.values():
            d, c = s.get("d"), s.get("c")
            if not d or not c:
                continue
            j = gi if (gi < len(d) and d[gi] == gd) else nidx(d, gd)
            if j is None or j < 252 or c[j - 252] <= 0:
                continue
            rr.append(c[j] / c[j - 252] - 1)
        rr.sort()
        sortmap[gd] = rr
    gdates = sorted(sortmap)

    def rs_pct(ret, ds):
        cand = [x for x in gdates if x <= ds]
        if not cand:
            return None
        a = sortmap[cand[-1]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    def scan(stocklist):
        """반환: dict 변형별 [n_fired, n_fired_hit] + 전체 [n_pts, n_pts_hit]."""
        agg = {"core": [0, 0], "core+RS": [0, 0], "core+RS+up": [0, 0]}
        n_pts = n_pts_hit = 0
        per = []
        for w in stocklist:
            code, mkt, tro = w["code"], w["market"], w["trough_date"]
            ch = cyclecfg.yahoo(yahoo_symbol(code, mkt))
            if not ch or not ch.get("closes"):
                continue
            ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
                  for t in ch["timestamps"]]
            c, v = ch["closes"], ch["volumes"]
            n = len(c)
            ti = nidx(ts, tro) or 0
            try:
                fr = fetch_naver_org_flow(code, pages=30, sleep_ms=160)
            except Exception:
                fr = []
            frs = sorted(fr, key=lambda r: r["date"])
            s_pts = s_hit = 0
            x = max(ti, 252, 55)
            while x < n - 5:
                if c[x] <= 0 or c[x] != min(c[max(0, x - 5):min(n, x + 6)]):
                    x += 1
                    continue
                n_pts += 1
                s_pts += 1
                # 클린 빠른 +20% 여부
                tgt, hit = c[x] * (1 + GAIN), False
                for k in range(x + 1, min(n, x + MAXH + 1)):
                    if c[k] <= c[x] * (1 - DROP):
                        break
                    if c[k] >= tgt:
                        hit = True
                        break
                if hit:
                    n_pts_hit += 1
                    s_hit += 1
                # 신호 변수
                v50 = sum(v[x - 50:x]) / 50 if x >= 50 and sum(v[x - 50:x]) else None
                hi52 = max(c[max(0, x - 252):x + 1])
                ma50 = sum(c[x - 49:x + 1]) / 50 if x >= 49 else None
                sel = [r for r in frs if r["date"] <= ts[x]][-60:]
                accum = None
                if len(sel) >= 30:
                    accum = (sum(r.get("fgn_net") or 0 for r in sel) > 0
                             or sum(r.get("org_net") or 0 for r in sel) > 0)
                rp = (rs_pct(c[x] / c[x - 252] - 1, ts[x])
                      if x >= 252 and c[x - 252] > 0 else None)
                up60 = c[x] / min(c[max(0, x - 60):x + 1]) - 1
                core = (v50 is not None and v[x] / v50 <= 1.0
                        and hi52 and c[x] <= 0.88 * hi52
                        and ma50 and abs(c[x] / ma50 - 1) <= 0.10
                        and accum is True)
                if core:
                    agg["core"][0] += 1
                    agg["core"][1] += hit
                    if rp is not None and rp >= 50:
                        agg["core+RS"][0] += 1
                        agg["core+RS"][1] += hit
                        if up60 > 0:
                            agg["core+RS+up"][0] += 1
                            agg["core+RS+up"][1] += hit
                x += 1
            per.append((code, s_pts, s_hit))
        return agg, n_pts, n_pts_hit, per

    aw, pw, hw, _ = scan(smp_w)
    ac, pc, hc, _ = scan(smp_c)

    def line(tag, agg, npts, nhit):
        base = 100 * nhit / npts if npts else 0
        out = [f"-- {tag} (스윙저점 {npts}개, 클린+20% 기저율 {round(base,1)}%) --"]
        for k in ("core", "core+RS", "core+RS+up"):
            f, h = agg[k]
            prec = 100 * h / f if f else 0
            lift = prec / base if base else 0
            out.append(f"  {k:11s} 발동 {f} → +20% {h} | 정밀도 "
                       f"{round(prec,1)}% | lift {round(lift,2)}x | "
                       f"헛신호 {round(100-prec,1)}%")
        return out, base

    L = [f"[c2024-12] 빠른 +20% 시그니처 정밀도 — 위너 {len(smp_w)} vs "
         f"비위너 {len(smp_c)} (seed {args.seed})",
         "신호: 거래량≤50일평균 & 종가≤52주고가88% & 50일선±10% & "
         "외인or기관60일순매수>0. 클린+20%=−10%전 60일내 +20%.",
         ""]
    lw, bw = line("위너 표본", aw, pw, hw)
    lc, bc = line("비위너 대조", ac, pc, hc)
    L += lw + [""] + lc + [""]
    # 통합 + 위너/비위너 변별
    for k in ("core", "core+RS", "core+RS+up"):
        fw_, hw_ = aw[k]
        fc_, hc_ = ac[k]
        prw = 100 * hw_ / fw_ if fw_ else 0
        prc = 100 * hc_ / fc_ if fc_ else 0
        L.append(f"[{k}] 정밀도 위너 {round(prw,1)}% vs 비위너 {round(prc,1)}% "
                 f"| 위너/비위너 배수 {round(prw/prc,2) if prc else 'inf'}x "
                 f"(발동률 위너 {round(100*fw_/pw,1) if pw else 0}% vs "
                 f"비위너 {round(100*fc_/pc,1) if pc else 0}%)")
    L += ["",
          "해석: lift>1 & 위너정밀도≫비위너정밀도 면 진짜 신호. 발동률이",
          "위너≫비위너면 신호 자체가 위너에 더 자주 = 변별. 비슷하면 헛신호.",
          "한계: 사이클내 사후·인-샘플·상폐제외. 표본 무작위(시드). I는",
          "fgn>0 OR org>0 느슨. frgn 30p 도달분만(미달=신호 평가 제외).",
          ]
    block = "\n".join(L)
    fn = f"_fast20_precision_w{len(smp_w)}c{len(smp_c)}s{args.seed}.txt"
    (CY / fn).write_text(block, encoding="utf-8")
    print(f"saved: {fn} (W {len(smp_w)} pts{pw} / C {len(smp_c)} pts{pc})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
