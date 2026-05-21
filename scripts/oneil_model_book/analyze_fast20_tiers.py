"""§13 빠른 +20% 시그니처 정밀도 — 3단계(안오름/중간/위너) 깨끗한 검증.

사용자 지적: 기존 '비위너=상위200 빼고 무작위'는 위너 같은 종목 오염
→ 검증이 보수적(격차 과소). 결과(raw_multiple=사이클 peak/trough)로
3단계 분리:
  안오름 NON  raw_multiple < 1.5  (저점 대비 최대 +50% 미만 = 진짜 안 오름)
  중간   MID  1.5 ≤ rm < 3.0      (+50~+200%)
  위너   WIN  winners_final 상위200 그대로
  (상위200 아니면서 rm≥3.0 = 모호한 준위너 → 어느 단계도 아님, 제외·count만)

신호가 진짜면 NON→MID→WIN 으로 정밀도·발동률이 단계적 상승해야 함.
신호=거래량≤50일평균 & 종가≤52주고가88% & 50일선±10% & 외인or기관
60일순매수>0 (+변형 RS≥50, +직전60일상승). 클린+20%=−10%전 60일내 +20%.

데이터 Yahoo(종가·거래량)·네이버 frgn. 사이클내 사후·인-샘플·상폐제외.
환각 금지·결손 비임퓨트.

사용:  python analyze_fast20_tiers.py [--n 40] [--seed 7]
"""
import argparse
import bisect
import json
import random
import sys
from datetime import datetime, timezone, date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.fetch import yahoo_symbol  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

CY = cyclecfg.DIR
GAIN, MAXH, DROP = 0.20, 60, 0.10


def nidx(d, ds):
    """d 오름차순 날짜에서 <=ds 인 마지막 인덱스 (이분탐색 O(logN))."""
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)   # 단계별 표본
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    winners = wf["winners"]
    win_codes = {x["code"] for x in winners}
    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]

    def ok(r):
        return (not r.get("exclude_reason") and r.get("trough_date")
                and r.get("n_days", 0) >= 60 and r.get("raw_multiple"))
    rest = [r for r in rv if r["code"] not in win_codes and ok(r)]
    NON = [r for r in rest if r["raw_multiple"] < 1.5]
    MID = [r for r in rest if 1.5 <= r["raw_multiple"] < 3.0]
    AMB = [r for r in rest if r["raw_multiple"] >= 3.0]   # 모호 준위너(제외)

    random.seed(args.seed)
    smp = {
        "NON 안오름(<+50%)": random.sample(NON, min(args.n, len(NON))),
        "MID 중간(+50~200%)": random.sample(MID, min(args.n, len(MID))),
        "WIN 위너(상위200)": random.sample(winners, min(args.n, len(winners))),
    }

    # RS 백분위용 주봉 그리드 — 결정적·전 스크립트 공통 → 파일 캐시 재사용
    any_d = U[list(U)[0]]["d"]
    cache = CY / "_rs_sortmap.json"
    if cache.exists():
        sm = json.loads(cache.read_text(encoding="utf-8"))
        sortmap = {k: v for k, v in sm.items()}
    else:
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
        cache.write_text(json.dumps(sortmap), encoding="utf-8")
    gdates = sorted(sortmap)

    def rs_pct(ret, ds):
        i = bisect.bisect_right(gdates, ds) - 1
        if i < 0:
            return None
        a = sortmap[gdates[i]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    def scan(stocklist):
        agg = {"core": [0, 0], "core+RS": [0, 0], "core+RS+up": [0, 0]}
        npts = nhit = 0
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
            # frgn 페이지: 저점~현재 거리만큼만(1p≈20거래일≈28일) +버퍼
            try:
                gap = (_date.fromisoformat(ts[-1])
                       - _date.fromisoformat(tro)).days
            except Exception:
                gap = 500
            pages = min(30, max(10, gap // 28 + 5))
            try:
                fr = fetch_naver_org_flow(code, pages=pages, sleep_ms=130)
            except Exception:
                fr = []
            frs = sorted(fr, key=lambda r: r["date"])
            x = max(ti, 252, 55)
            while x < n - 5:
                if c[x] <= 0 or c[x] != min(c[max(0, x - 5):min(n, x + 6)]):
                    x += 1
                    continue
                npts += 1
                tgt, hit = c[x] * (1 + GAIN), False
                for k in range(x + 1, min(n, x + MAXH + 1)):
                    if c[k] <= c[x] * (1 - DROP):
                        break
                    if c[k] >= tgt:
                        hit = True
                        break
                if hit:
                    nhit += 1
                v50 = sum(v[x - 50:x]) / 50 if x >= 50 and sum(v[x - 50:x]) else None
                hi52 = max(c[max(0, x - 252):x + 1])
                ma50 = sum(c[x - 49:x + 1]) / 50 if x >= 49 else None
                sel = [r for r in frs if r["date"] <= ts[x]][-60:]
                accum = (sum(r.get("fgn_net") or 0 for r in sel) > 0
                         or sum(r.get("org_net") or 0 for r in sel) > 0
                         ) if len(sel) >= 30 else None
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
        return agg, npts, nhit

    L = [f"[c2024-12] 빠른 +20% 시그니처 — 3단계 깨끗한 정밀도 검증",
         f"(단계별 무작위 {args.n}종목, seed {args.seed}; raw_multiple=사이클 "
         f"peak/trough 로 분리)",
         f"풀 크기: NON {len(NON)} / MID {len(MID)} / WIN {len(winners)} "
         f"| 제외(준위너 rm≥3 비톱200) {len(AMB)}",
         "신호=거래량≤50평 & 종가≤52주고88% & 50선±10% & 외인or기관매수. "
         "클린+20%=−10%전 60일내.",
         ""]
    res = {}
    for tag, lst in smp.items():
        agg, npts, nhit = scan(lst)
        res[tag] = (agg, npts, nhit)
        base = 100 * nhit / npts if npts else 0
        L.append(f"-- {tag} (스윙저점 {npts}, 기저 클린+20% {round(base,1)}%) --")
        for k in ("core", "core+RS", "core+RS+up"):
            f, h = agg[k]
            prec = 100 * h / f if f else 0
            lift = prec / base if base else 0
            L.append(f"  {k:11s} 발동 {f}({round(100*f/npts,1) if npts else 0}%) "
                     f"→ +20% {h} | 정밀도 {round(prec,1)}% | "
                     f"lift {round(lift,2)}x | 헛신호 {round(100-prec,1)}%")
        L.append("")
    # 단계 상승성 점검
    L.append("== 단계별 상승성 (신호 진짜면 NON<MID<WIN) ==")
    for k in ("core", "core+RS"):
        row = []
        for tag in smp:
            agg, npts, _ = res[tag]
            f, h = agg[k]
            row.append(f"{tag.split()[0]} 정밀{round(100*h/f,1) if f else 0}%·"
                       f"발동{round(100*f/npts,1) if npts else 0}%")
        L.append(f"[{k}] " + " | ".join(row))
    L += ["",
          "해석: 깨끗한 NON 기저는 낮아야 정상. 정밀도·발동률이 "
          "NON<MID<WIN 단조 상승 = 진짜 신호. WIN은 생존자라 기저 높음.",
          "한계: 사이클내 사후·인-샘플·상폐제외·표본 무작위(시드). I는 "
          "fgn>0 OR org>0 느슨. frgn 30p 도달분만. 결손 비임퓨트."]
    fn = f"_fast20_tiers_n{args.n}s{args.seed}.txt"
    (CY / fn).write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()
