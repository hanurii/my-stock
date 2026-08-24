# -*- coding: utf-8 -*-
"""35 · **극단 역분할 언더플로** — 하네스 오염 민감도 + 자릿수 검산(양 시장).

발견
----
Sharadar 의 `volume` 은 **수정 거래량**(실제 × f, `f = closeunadj/close`)이다.
누적 역분할이 극단이면 f 가 1e-12 급이라 **수정 거래량이 1.0 에 바닥친다.**
```
ADTX 2021-02-10  close 2,001,456,000,480.349  volume **1.0**  closeunadj **4.1**
```
→ `거래대금 = close × volume = $2조/일` — 실제(≈$200만)의 **100만 배**.
⚠️ **G2 검산 ③은 못 잡았다** — 그 검산은 「내 두 환산식이 서로 일치하는가」였지
   **「값이 현실에서 가능한가」가 아니었다.** 잡은 건 **자릿수 판단**이었다.

이 스크립트가 하는 것
---------------------
**① 하네스 오염 민감도** — 오염 종목의 진입을 뺀 판을 **슬롯 시뮬 단계에서만** 낸다.
   🚨 **한계: 「그 거래들을 뺀 효과」만 잰다.** 유니버스에서 빼면 `n_eval`·후보·진입 수가
   다 바뀌는데 그건 **하네스 재실행이 있어야** 잰다. **헤드라인이 흔들리면 그때 재실행한다.**
   («재는 데 33분 걸리는 것과 3분이면 되는 것이 있으면 3분짜리를 먼저 한다.»)

**② 자릿수 검산 — 양 시장 짝으로.**
   「단일 종목의 하루 거래대금이 시장 총액의 X%를 넘는 종목-일」을 센다.
   **시장 무관한 이상 탐지기**이고 자릿수 검산의 일반형이다. 0건이면 그 사실을 적는다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/35-extreme-adjust.py
"""
from __future__ import annotations

import csv
import io
import json
import re
import statistics as st
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
START, END = "2021-02-01", "2026-08-21"
F_CUT = 1e-4
SHARE_CUTS = (0.05, 0.10, 0.25, 0.50)
REGIMES = {"무비용": (0.0, 0.0), "한국-미래에셋": (0.0014, 0.0034)}
EXCLUDE_KR = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN_KR = re.compile("^9[0-9]{5}$")


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


def us_factor_stats():
    """종목별 최소 f 와 문턱별 종목 수. 그리고 시장 총액 대비 단일 종목 비중."""
    import us_loader as U
    meta = U.load_tickers("base")
    codes = set(meta)
    minf = {}
    day_tot = defaultdict(float)
    day_max = {}
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for r in rd:
            t, d = r[0], r[1]
            if t not in codes or d < START or d > END:
                continue
            c, cu, v = float(r[5]), float(r[8]), float(r[6])
            if c <= 0:
                continue
            f = cu / c
            if t not in minf or f < minf[t]:
                minf[t] = f
            if v > 0:
                tv = c * v
                day_tot[d] += tv
                if d not in day_max or tv > day_max[d][0]:
                    day_max[d] = (tv, t)
    return minf, day_tot, day_max


def kr_share_stats():
    P = ROOT / ".cache" / "pdata"
    s, e = START.replace("-", ""), END.replace("-", "")
    day_tot = defaultdict(float)
    day_max = {}
    for p in sorted(x for x in P.glob("price_*.json") if s <= x.stem[6:] <= e):
        d = p.stem[6:]
        date = "%s-%s-%s" % (d[:4], d[4:6], d[6:])
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ") or FOREIGN_KR.match(code):
                continue
            if EXCLUDE_KR.search(r.get("itmsNm") or ""):
                continue
            tv = r.get("trPrc_eok") or 0
            if tv:
                tv = float(tv)
                day_tot[date] += tv
                if date not in day_max or tv > day_max[date][0]:
                    day_max[date] = (tv, code)
    return day_tot, day_max


def share_check(name, day_tot, day_max):
    print("", flush=True)
    print("  [%s] 거래일 %d — **단일 종목이 시장 총액에서 차지한 최대 비중**"
          % (name, len(day_tot)), flush=True)
    sh = []
    for d, tot in day_tot.items():
        if tot > 0 and d in day_max:
            sh.append((day_max[d][0] / tot, d, day_max[d][1]))
    sh.sort(reverse=True)
    med = st.median(x[0] for x in sh)
    print("     중앙 %.2f%% · 최대 **%.2f%%** (%s %s)"
          % (med * 100, sh[0][0] * 100, sh[0][2], sh[0][1]), flush=True)
    out = {"median_pct": med * 100, "max_pct": sh[0][0] * 100,
           "max_code": sh[0][2], "max_date": sh[0][1], "counts": {}}
    for c in SHARE_CUTS:
        k = sum(1 for x in sh if x[0] >= c)
        out["counts"]["%.0f%%" % (c * 100)] = k
        print("     %2.0f%% 초과 종목-일: **%d** (%.2f%%)"
              % (c * 100, k, k / len(sh) * 100), flush=True)
    print("     상위 5: %s"
          % " · ".join("%s %s %.1f%%" % (x[2], x[1], x[0] * 100) for x in sh[:5]),
          flush=True)
    return out


def load_us_events():
    ev = []
    for f in sorted((BT / "sub").glob("us_20*.json")):
        ev += json.loads(f.read_text(encoding="utf-8"))["events"]
    seen, out = set(), []
    last = max((e.get("resolve_date") or e["entry_date"]) for e in ev)
    for e in sorted(ev, key=lambda x: (x["entry_date"], x["code"], x.get("pattern", ""))):
        k = (e["scan_date"], e["code"], e.get("pattern", ""))
        if k in seen or e.get("gain_at_resolve_pct") is None:
            continue
        seen.add(k)
        out.append({"code": e["code"], "scan_date": e["scan_date"],
                    "pattern": e.get("pattern", ""), "entry_date": e["entry_date"],
                    "resolve_date": e.get("resolve_date") or last,
                    "gain": e["gain_at_resolve_pct"], "result": e["result"]})
    return out


def main():
    print("=" * 88, flush=True)
    print("① 극단 역분할 f 분포 — **문턱을 옮기면 답이 바뀌는지 바로 보인다**", flush=True)
    print("=" * 88, flush=True)
    minf, us_tot, us_max = us_factor_stats()
    print("  종목 %d · 최소 f 의 분포" % len(minf), flush=True)
    for c in (1e-2, 1e-3, F_CUT, 1e-5, 1e-6, 1e-9):
        k = sum(1 for v in minf.values() if v < c)
        print("     f < %-8.0e : **%4d 종목**" % (c, k), flush=True)
    print("", flush=True)
    print("  🚨 **문턱 근거는 «언더플로 산수»다. 결과에 맞춘 값이 아니다.**", flush=True)
    print("     수정 거래량 = 실제 × f. 실제 1e6주라면", flush=True)
    print("       f = 1e-6 → 수정 1.0     **정보 완전 소실**", flush=True)
    print("       f = 1e-4 → 수정 100     아직 여유가 있다 ← **보수적으로 여기서 자른다**", flush=True)
    print("       f = 1e-3 → 수정 1,000   여유 충분", flush=True)
    print("     **보수적으로 잡았다는 것 자체가 문턱이 결과 방향과 무관하다는 증거다.**",
          flush=True)
    bad = {t for t, v in minf.items() if v < F_CUT}
    print("  → 제외 대상 **%d 종목**" % len(bad), flush=True)

    print("", flush=True)
    print("=" * 88, flush=True)
    print("② 하네스 오염 민감도 — **슬롯 시뮬 단계에서만**(재실행 없이)", flush=True)
    print("=" * 88, flush=True)
    tr = load_us_events()
    keep = [t for t in tr if t["code"] not in bad]
    hit = [t for t in tr if t["code"] in bad]
    print("  미국 거래 %d 중 오염 종목 진입 **%d건 (%.2f%%) · %d종목**"
          % (len(tr), len(hit), len(hit) / len(tr) * 100, len({t["code"] for t in hit})),
          flush=True)
    res = {"n_trades": len(tr), "n_contaminated": len(hit),
           "codes": sorted({t["code"] for t in hit})}
    for rg, (b, sl) in REGIMES.items():
        with Cost(b, sl):
            a = slot_sim.band(tr, n_runs=N_SEED)
            c = slot_sim.band(keep, n_runs=N_SEED)
            pa = st.mean(slot_sim.net(t["gain"]) for t in tr)
            pc = st.mean(slot_sim.net(t["gain"]) for t in keep)
        res[rg] = {"equity_all": a["median"], "equity_ex": c["median"],
                   "filled_all": a["n_filled"], "filled_ex": c["n_filled"],
                   "mdd_all": a["mdd"], "mdd_ex": c["mdd"],
                   "per_trade_all": pa, "per_trade_ex": pc}
        print("  %-10s 원판     자산 %+8.2f%% · 체결 %3.0f · MDD %6.2f%% · 거래당 %+.4f%%"
              % (rg, a["median"], a["n_filled"], a["mdd"], pa), flush=True)
        print("  %-10s 제외 후  자산 %+8.2f%% · 체결 %3.0f · MDD %6.2f%% · 거래당 %+.4f%% "
              "· **차이 자산 %+.2f%%p · 거래당 %+.4f%%p**"
              % ("", c["median"], c["n_filled"], c["mdd"], pc,
                 c["median"] - a["median"], pc - pa), flush=True)
    print("", flush=True)
    print("  ⚠️ **한계: 이건 「그 거래들을 뺀 효과」만 잰다.** 유니버스에서 빼면", flush=True)
    print("     `n_eval`·후보·진입 수가 다 바뀌는데 그건 **하네스 재실행이 있어야** 잰다.",
          flush=True)
    print("     **헤드라인이 흔들리면 그때 33분을 쓴다.**", flush=True)

    print("", flush=True)
    print("=" * 88, flush=True)
    print("③ 자릿수 검산 — **양 시장 짝으로**. 「단일 종목이 시장 총액의 몇 %를 먹었나」",
          flush=True)
    print("=" * 88, flush=True)
    print("  시장 무관한 이상 탐지기다. 정합성 검산은 자료 오류를 못 잡는다 —", flush=True)
    print("  **「이 값이 현실에서 가능한가」는 별도 검산이어야 한다.**", flush=True)
    res["share_us"] = share_check("미국(원판)", us_tot, us_max)
    us_tot2 = defaultdict(float)
    us_max2 = {}
    # 제외 후 다시 — 오염 종목을 빼면 이상치가 사라지는지
    import us_loader as U
    meta = U.load_tickers("base")
    codes = set(meta) - bad
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for r in rd:
            t, d = r[0], r[1]
            if t not in codes or d < START or d > END:
                continue
            c, v = float(r[5]), float(r[6])
            if c > 0 and v > 0:
                tv = c * v
                us_tot2[d] += tv
                if d not in us_max2 or tv > us_max2[d][0]:
                    us_max2[d] = (tv, t)
    res["share_us_ex"] = share_check("미국(제외 후)", us_tot2, us_max2)
    kt, km = kr_share_stats()
    res["share_kr"] = share_check("한국", kt, km)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "35-extreme-adjust.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/35-extreme-adjust.json", flush=True)


if __name__ == "__main__":
    main()
