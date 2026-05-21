"""빠른 상승 시그니처 — 목표 +10/15/20/25/30% 동시 비교 × 3단계.

§13-c 5신호(거래량≤50일평균 & 종가≤52주고가88% & 50일선±10% &
외인or기관60일순매수>0 & RS≥50)가 떴을 때, 목표를 +10~+30%로 바꾸면
도달 비율(정밀도)·lift 가 어떻게 변하는지 NON/MID/WIN 3단계로 비교.
'클린' = 도중 −10% 안 빠지고 60거래일내 +T% 도달.

raw_multiple(사이클 peak/trough)로 NON(<+50%)/MID(+50~200%)/WIN(상위200).
RS사전계산 캐시(`_rs_sortmap.json`) 재사용. Yahoo·네이버 frgn.
사이클내 사후·인-샘플·상폐제외. 환각 금지·결손 비임퓨트.

사용:  python analyze_fast20_thresholds.py [--n 40] [--seed 7]
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
TARGETS = [10, 15, 20, 25, 30]      # %
MAXH, DROP = 60, 0.10


def nidx(d, ds):
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
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
    random.seed(args.seed)
    smp = {
        "NON 안오름(<+50%)": random.sample(NON, min(args.n, len(NON))),
        "MID 중간(+50~200%)": random.sample(MID, min(args.n, len(MID))),
        "WIN 위너(상위200)": random.sample(winners, min(args.n, len(winners))),
    }

    cache = CY / "_rs_sortmap.json"
    if cache.exists():
        sortmap = json.loads(cache.read_text(encoding="utf-8"))
    else:
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
        cache.write_text(json.dumps(sortmap), encoding="utf-8")
    gdates = sorted(sortmap)

    def rs_pct(ret, ds):
        i = bisect.bisect_right(gdates, ds) - 1
        if i < 0:
            return None
        a = sortmap[gdates[i]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    def hits_for(c, x, n):
        """도중 −10% 전 60일내 도달한 목표 %들의 집합."""
        got = set()
        for k in range(x + 1, min(n, x + MAXH + 1)):
            if c[k] <= c[x] * (1 - DROP):
                break
            g = (c[k] / c[x] - 1) * 100
            for t in TARGETS:
                if g >= t:
                    got.add(t)
            if len(got) == len(TARGETS):
                break
        return got

    def scan(stocklist):
        # variant -> {fired, hit[T]}
        agg = {kk: {"f": 0, "h": {t: 0 for t in TARGETS}}
               for kk in ("core", "core+RS")}
        npts = 0
        base = {t: 0 for t in TARGETS}
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
                got = hits_for(c, x, n)
                for t in got:
                    base[t] += 1
                v50 = sum(v[x - 50:x]) / 50 if x >= 50 and sum(v[x - 50:x]) else None
                hi52 = max(c[max(0, x - 252):x + 1])
                ma50 = sum(c[x - 49:x + 1]) / 50 if x >= 49 else None
                sel = [r for r in frs if r["date"] <= ts[x]][-60:]
                accum = (sum(r.get("fgn_net") or 0 for r in sel) > 0
                         or sum(r.get("org_net") or 0 for r in sel) > 0
                         ) if len(sel) >= 30 else None
                rp = (rs_pct(c[x] / c[x - 252] - 1, ts[x])
                      if x >= 252 and c[x - 252] > 0 else None)
                core = (v50 is not None and v[x] / v50 <= 1.0
                        and hi52 and c[x] <= 0.88 * hi52
                        and ma50 and abs(c[x] / ma50 - 1) <= 0.10
                        and accum is True)
                if core:
                    agg["core"]["f"] += 1
                    for t in got:
                        agg["core"]["h"][t] += 1
                    if rp is not None and rp >= 50:
                        agg["core+RS"]["f"] += 1
                        for t in got:
                            agg["core+RS"]["h"][t] += 1
                x += 1
        return agg, npts, base

    L = [f"[c2024-12] 빠른 상승 — 목표 +10/15/20/25/30% × 3단계 비교",
         f"(단계별 무작위 {args.n}종목, seed {args.seed}; 클린=−10%전 "
         f"{MAXH}거래일내 도달)",
         f"신호: 거래량≤50평 & 종가≤52주고88% & 50선±10% & 외인or기관매수 "
         f"(+RS≥50). 풀 NON {len(NON)}/MID {len(MID)}/WIN {len(winners)}",
         ""]
    for tag, lst in smp.items():
        agg, npts, base = scan(lst)
        L.append(f"== {tag} (스윙저점 {npts}) ==")
        L.append(f"  목표 | 기저율 | core 정밀(lift) | core+RS 정밀(lift)")
        for t in TARGETS:
            b = 100 * base[t] / npts if npts else 0
            row = f"  +{t}% | {round(b,1)}%"
            for kk in ("core", "core+RS"):
                f_, h_ = agg[kk]["f"], agg[kk]["h"][t]
                p = 100 * h_ / f_ if f_ else 0
                lift = p / b if b else 0
                mark = "★" if t == 20 else " "
                row += f" | {round(p,1)}%({round(lift,2)}x){mark}"
            L.append(row)
        L.append(f"  (발동수: core {agg['core']['f']} / "
                 f"core+RS {agg['core+RS']['f']})")
        L.append("")
    L += ["해석: 목표↓ 정밀도↑(쉬움)·lift는 신호 변별. ★=+20%(기존 기준).",
          "NON<MID<WIN 단조면 진짜. core+RS 견고(§13-c).",
          "한계: 단일 사이클·인-샘플·사후·상폐제외·표본 무작위. I는 "
          "fgn>0 OR org>0 느슨. frgn 동적페이지 도달분만. 결손 비임퓨트."]
    fn = f"_fast20_thresholds_n{args.n}s{args.seed}.txt"
    (CY / fn).write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()
