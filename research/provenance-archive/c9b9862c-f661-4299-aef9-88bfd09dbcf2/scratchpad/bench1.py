# -*- coding: utf-8 -*-
"""읽기전용 벤치마크: 검출기 as-of 리플레이 처리량 측정."""
import json, sys, time, random, os
from pathlib import Path
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import ohlcv_matrix
from canslim_lib import vcp_history, power_play_history, cheat_history
from canslim_lib.trend_template import evaluate_trend_template, compute_gate_margin
from canslim_lib.pivot_backtest import truncate_series, simulate_pivot_trade

SER = ROOT / ".cache" / "ohlcv" / "series"
files = sorted(SER.glob("*.json"))
print("series files:", len(files))

random.seed(7)
sample = random.sample(files, 20)

# --- 1) 파일 로드 속도 ---
t0 = time.time()
loaded = []
for f in sample:
    s = json.loads(f.read_text(encoding="utf-8"))
    loaded.append((f.stem, s))
t_load = time.time() - t0
lens = [len(s["closes"]) for _, s in loaded]
print(f"[load] 20종목 {t_load*1000:.0f}ms  ({t_load/20*1000:.1f}ms/종목)  bars min/med/max={min(lens)}/{sorted(lens)[10]}/{max(lens)}")

# 200봉 이상만
ok = [(c, s) for c, s in loaded if len(s["closes"]) >= 200]
print("200봉 이상:", len(ok))

SCAN = 5
res = {}
for name, fn in [("VCP", vcp_history.replay_vcp),
                 ("PP", power_play_history.replay_power_play),
                 ("3C", cheat_history.replay_cheat)]:
    t0 = time.time()
    cnt = 0
    for c, s in ok:
        r = fn(s, SCAN, None)
        cnt += len(r)
    dt = time.time() - t0
    res[name] = dt / cnt
    print(f"[{name}] {cnt} 종목일 in {dt*1000:.0f}ms → {dt/cnt*1000:.3f} ms/종목일 ({cnt/dt:.0f} 종목일/초)")

# --- 트렌드 템플레이트 (as-of 절단 + 8조건 + 관문여유) ---
t0 = time.time(); cnt = 0
for c, s in ok:
    closes = s["closes"]
    n = len(closes)
    for i in range(n - SCAN, n):
        sub = closes[:i+1]
        r = evaluate_trend_template(sub, 85, 80)
        g = compute_gate_margin(r, sub[-1], 85, 80)
        cnt += 1
dt = time.time() - t0
res["TT"] = dt / cnt
print(f"[TT+gate] {cnt} 종목일 in {dt*1000:.0f}ms → {dt/cnt*1000:.3f} ms/종목일 ({cnt/dt:.0f} 종목일/초)")

# --- 체결 시뮬 ---
t0 = time.time(); cnt = 0
for c, s in ok:
    for i in range(len(s["closes"]) - 60, len(s["closes"]) - 55):
        simulate_pivot_trade(s, i, s["closes"][i], 20.0, 10.0)
        cnt += 1
dt = time.time() - t0
print(f"[simulate] {cnt}건 in {dt*1000:.1f}ms → {dt/cnt*1000:.4f} ms/건")

tot = res["VCP"]+res["PP"]+res["3C"]+res["TT"]
print(f"\n합계 4검출기: {tot*1000:.3f} ms/종목일 → {1/tot:.0f} 종목일/초 (1코어)")
