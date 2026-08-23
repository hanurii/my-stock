"""2025-11-26 시점 매매 유니버스 확정 (백테스트 하네스와 동일 절차)
   = pdata 시점 유니버스 -> 시계열 200일+ -> 거래정지 제외 -> 50일 평균 거래대금 5억+ -> RS>=80
"""
import json, re, sys
from bisect import bisect_right
from pathlib import Path
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(MAIN / "scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"
from canslim_lib.pivot_backtest import truncate_series
from canslim_lib import liveness
from canslim_lib.trend_template import evaluate_trend_template
from screen_trend_template import _compute_rs_for_all

PDATA = MAIN / ".cache" / "pdata"
D = "2025-11-26"
MIN_TURNOVER_EOK, TURNOVER_WINDOW, MIN_CLOSES, RS_MIN = 5.0, 50, 200, 80
EXCLUDE_PATTERN = re.compile(
    r"스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$|우$|우\(전환\)|우B\(전환\)")

# --- pdata 적재(워밍 140일) ---
warm = "20250709"   # D-140일 근사
end = D.replace("-", "")
universe_by_date, turnover = {}, {}
for p in sorted(x for x in PDATA.glob("price_*.json") if warm <= x.stem[6:] <= end):
    dd = p.stem[6:]; date = f"{dd[:4]}-{dd[4:6]}-{dd[6:]}"
    recs = json.loads(p.read_text(encoding="utf-8"))
    day = {}
    for code, r in recs.items():
        if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ"):
            continue
        name = r.get("itmsNm") or ""
        t = r.get("trPrc_eok")
        if t is not None:
            turnover.setdefault(code, []).append((date, t))
        if EXCLUDE_PATTERN.search(name):
            continue
        day[code] = {"name": name, "market": r.get("mrktCtg"), "cap_eok": r.get("market_cap_eok")}
    universe_by_date[date] = day
turnover = {c: ([d for d, _ in h], [t for _, t in h]) for c, h in turnover.items()}
day_univ = universe_by_date[D]
print("pdata 시점 유니버스(스팩/우선주 등 제외 후):", len(day_univ))

def avg_turnover_asof(hist, asof, window=TURNOVER_WINDOW):
    if not hist: return None
    dates, vals = hist
    k = bisect_right(dates, asof)
    if k < window // 2: return None
    seg = vals[max(0, k - window):k]
    return sum(seg) / len(seg)

stD, drops = {}, {"no_series": 0, "short": 0, "halted": 0, "low_turnover": 0}
for c in day_univ:
    s = ohlcv_matrix.get_series(c)
    if not s or not s.get("closes"): drops["no_series"] += 1; continue
    t = truncate_series(s, D)
    if len(t["closes"]) < MIN_CLOSES or not t["dates"] or t["dates"][-1] != D:
        drops["short"] += 1; continue
    if liveness.is_halted(t, asof=D): drops["halted"] += 1; continue
    tv = avg_turnover_asof(turnover.get(c), D)
    if tv is None or tv < MIN_TURNOVER_EOK: drops["low_turnover"] += 1; continue
    stD[c] = (t, tv)
print("탈락:", drops, "-> 평가대상", len(stD))

rs = _compute_rs_for_all([{"code": c, "closes": t["closes"], "ok": True} for c, (t, _) in stD.items()])
univ = {}
tt_pass = 0
for c, (t, tv) in stD.items():
    rsv = (rs.get(c) or {}).get("rs")
    if rsv is None or rsv < RS_MIN: continue
    r = evaluate_trend_template(t["closes"], rs=rsv, rs_min=RS_MIN)
    if r["pass"]: tt_pass += 1
    univ[c] = {"name": day_univ[c]["name"], "market": day_univ[c]["market"],
               "cap_eok": day_univ[c]["cap_eok"], "rs": rsv,
               "turnover_eok": round(tv, 2), "tt_pass": bool(r["pass"]),
               "close": t["closes"][-1]}
print(f"RS>=80 유니버스: {len(univ)}종목 (그중 8관문 통과 {tt_pass})")
from collections import Counter
print(Counter(v["market"] for v in univ.values()))
OUT = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\universe_20251126.json")
OUT.write_text(json.dumps(univ, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved", OUT)
# 평가대상 전체(RS 무관)도 저장 -> 비교용
ALL = {c: {"name": day_univ[c]["name"], "market": day_univ[c]["market"],
           "cap_eok": day_univ[c]["cap_eok"], "rs": (rs.get(c) or {}).get("rs"),
           "turnover_eok": round(tv, 2)} for c, (t, tv) in stD.items()}
Path(str(OUT).replace("universe_", "evaluable_")).write_text(json.dumps(ALL, ensure_ascii=False, indent=1), encoding="utf-8")
