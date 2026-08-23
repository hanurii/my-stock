# -*- coding: utf-8 -*-
"""events 614건에 as-of 요인들을 붙인다. scan_date 까지 절단한 시계열만 사용."""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(MAIN / "scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"
from canslim_lib.pivot_backtest import truncate_series
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat, DEFAULT_PARAMS as CHEAT_P
from canslim_lib.power_play import evaluate_power_play

SCR = Path(sys.argv[0]).parent
data = json.loads((MAIN / "public/data/backtest-volatility-pilot.json").read_text(encoding="utf-8"))
events = data["events"]
per_date = {p["scan_date"]: p for p in data["per_date"]}

# ── pdata 시가총액(그날 스냅샷) ────────────────────────────────
scan_dates = sorted({e["scan_date"] for e in events})
cap = {}   # (date, code) -> cap_eok
for d in scan_dates:
    p = MAIN / ".cache" / "pdata" / f"price_{d.replace('-','')}.json"
    if not p.exists():
        continue
    recs = json.loads(p.read_text(encoding="utf-8"))
    for code, r in recs.items():
        c = r.get("market_cap_eok")
        if c is not None:
            cap[(d, code)] = c
print("pdata 시총 적재", len(scan_dates), "일", flush=True)

# ── 섹터 태그(참고용, 룩어헤드 위험 명시) ────────────────────
sect = json.loads((MAIN / "public/data/sepa-leading-sectors.json").read_text(encoding="utf-8"))["tags"]

def ma(xs, n):
    xs = [x for x in xs[-n:] if x is not None]
    return sum(xs)/len(xs) if len(xs) >= n*0.8 else None

out = []
codes = sorted({e["code"] for e in events})
series_cache = {}
for c in codes:
    s = ohlcv_matrix.get_series(c)
    if s and s.get("closes"):
        series_cache[c] = s
print("시계열", len(series_cache), "/", len(codes), flush=True)

for e in events:
    s = series_cache.get(e["code"])
    row = dict(e)
    D = e["scan_date"]
    row["cap_eok"] = cap.get((D, e["code"]))
    row["n_eval_day"] = (per_date.get(D) or {}).get("n_eval")
    row["n_cand_day"] = (per_date.get(D) or {}).get("n_candidates")
    row["n_entered_day"] = (per_date.get(D) or {}).get("n_entered")
    tg = sect.get(e["code"])
    row["sector_short"] = tg["short"] if tg else None
    row["sector_rank"] = tg["rank"] if tg else None
    if s:
        t = truncate_series(s, D)
        cl, hi, lo = t["closes"], t["highs"], t["lows"]
        n = len(cl)
        px = cl[-1]
        row["close_D"] = px
        w = min(252, n)
        seg_h = [x for x in hi[-w:] if x is not None]
        seg_l = [x for x in lo[-w:] if x is not None]
        row["win52_days"] = w
        row["dist_52wh_pct"] = round((px/max(seg_h) - 1)*100, 2) if seg_h else None
        row["gain_52wl_pct"] = round((px/min(seg_l) - 1)*100, 2) if seg_l and min(seg_l) > 0 else None
        row["pct_to_pivot"] = round((e["pivot"]/px - 1)*100, 2) if px else None
        m50, m200, m150 = ma(cl, 50), ma(cl, 200), ma(cl, 150)
        row["ext_50ma_pct"] = round((px/m50 - 1)*100, 2) if m50 else None
        row["ext_200ma_pct"] = round((px/m200 - 1)*100, 2) if m200 else None
        row["ext_150ma_pct"] = round((px/m150 - 1)*100, 2) if m150 else None
        for k in (5, 20, 60, 120):
            row[f"ret_{k}d_pct"] = round((px/cl[-1-k] - 1)*100, 2) if n > k and cl[-1-k] else None
        # 패턴 상세 재산출
        try:
            if e["pattern"] == "VCP":
                r = evaluate_vcp(t)
                row["base_len"] = r.get("base_length_days")
                row["base_depth"] = r.get("base_depth_pct")
                row["n_contractions"] = r.get("num_contractions")
                row["dryup"] = r.get("volume_dryup_ratio")
                row["tightness"] = r.get("tightness_pct")
                row["coil_len"] = r.get("coil_len")
                row["coil_dry_mean"] = r.get("coil_dry_mean")
                row["coil_min_dry"] = r.get("coil_min_dry")
                row["coil_range_pct"] = r.get("coil_range_pct")
            elif e["pattern"] == "3C":
                r = evaluate_cheat(t, CHEAT_P)
                row["base_len"] = r.get("cup_base_days")
                row["base_depth"] = r.get("cup_depth_pct")
                row["shelf_pos"] = r.get("shelf_position_pct")
            else:
                r = evaluate_power_play(t)
                row["base_len"] = r.get("flag_length_days")
                row["base_depth"] = r.get("flag_depth_pct")
                row["pole_gain"] = r.get("flagpole_gain_pct")
        except Exception as ex:
            row["detect_err"] = str(ex)[:80]
    out.append(row)

(SCR/"events_feat.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print("saved", len(out))
# 결측 점검
keys = ["cap_eok","dist_52wh_pct","gain_52wl_pct","pct_to_pivot","ext_50ma_pct","ext_200ma_pct",
        "ret_5d_pct","ret_20d_pct","ret_60d_pct","ret_120d_pct","base_len","base_depth","dryup",
        "n_contractions","tightness","coil_dry_mean","coil_min_dry","sector_short"]
for k in keys:
    miss = sum(1 for r in out if r.get(k) is None)
    print(f"  {k:<18} 결측 {miss}/{len(out)}")
