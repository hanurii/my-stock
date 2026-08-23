# -*- coding: utf-8 -*-
"""events 에 진입 시점 특성 부착 (읽기 전용)."""
import json, sys, glob, os
from pathlib import Path
from bisect import bisect_right

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(MAIN / "scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"

SCRATCH = Path(os.environ["SCRATCH"])
ev = json.load(open(MAIN / "public/data/backtest-volatility-pilot.json", encoding="utf-8"))["events"]

# --- pdata 시가총액 (해당 날짜, 없으면 직전 영업일) ---
files = sorted(glob.glob(str(MAIN / ".cache/pdata/price_2025*.json"))) + \
        sorted(glob.glob(str(MAIN / ".cache/pdata/price_2026*.json")))
pdates = [os.path.basename(f)[6:14] for f in files]
pdates = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in pdates]
need = sorted({e["scan_date"] for e in ev})
cap_cache = {}
want_files = {}
for d in need:
    k = bisect_right(pdates, d) - 1
    if k >= 0:
        want_files.setdefault(files[k], []).append(d)
for f, ds in want_files.items():
    rec = json.load(open(f, encoding="utf-8"))
    m = {c: r.get("market_cap_eok") for c, r in rec.items()}
    for d in ds:
        cap_cache[d] = m

W52 = 252
out = []
series_cache = {}
for e in ev:
    c, D = e["code"], e["scan_date"]
    s = series_cache.get(c)
    if s is None:
        s = ohlcv_matrix.get_series(c) or {}
        series_cache[c] = s
    dates = s.get("dates") or []
    try:
        i = dates.index(D)
    except ValueError:
        i = None
    r = dict(e)
    if i is not None:
        cl = s["closes"]; hi = s["highs"]; lo = s["lows"]; vol = s.get("volumes") or []
        c0 = cl[i]
        seg = slice(max(0, i - W52 + 1), i + 1)
        his = [x for x in hi[seg] if x]
        los = [x for x in lo[seg] if x]
        r["close_D"] = c0
        r["hi52"] = max(his) if his else None
        r["lo52"] = min(los) if los else None
        r["from_lo52_pct"] = round((c0 / min(los) - 1) * 100, 2) if los and min(los) else None
        r["to_hi52_pct"] = round((c0 / max(his) - 1) * 100, 2) if his else None
        # 선행 상승폭 (6개월=125거래일)
        j = i - 125
        r["run6m_pct"] = round((c0 / cl[j] - 1) * 100, 2) if j >= 0 and cl[j] else None
        # 피벗까지 거리 (진입 필요 상승률)
        r["pivot_dist_pct"] = round((e["pivot"] / c0 - 1) * 100, 2) if c0 else None
        # 50일 평균 거래량 대비 최근 5일 (마름 정도) — 참고
        if len(vol) > i and i >= 50:
            v50 = [v for v in vol[i-49:i+1] if v]
            v5 = [v for v in vol[i-4:i+1] if v]
            r["dryup"] = round((sum(v5)/len(v5)) / (sum(v50)/len(v50)), 3) if v50 and v5 else None
    r["cap_eok"] = (cap_cache.get(D) or {}).get(c)
    out.append(r)

json.dump(out, open(SCRATCH / "events_feat.json", "w", encoding="utf-8"), ensure_ascii=False)
miss = {k: sum(1 for r in out if r.get(k) is None) for k in
        ("close_D", "cap_eok", "from_lo52_pct", "to_hi52_pct", "run6m_pct", "pivot_dist_pct", "dryup")}
print("n=", len(out), "missing:", miss)
