# -*- coding: utf-8 -*-
"""실사용 형태 벤치마크: 20종목 × 299 as-of일 전체 리플레이."""
import json, sys, time, random
from pathlib import Path
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib import vcp_history, power_play_history, cheat_history

SER = ROOT / ".cache" / "ohlcv" / "series"
files = sorted(SER.glob("*.json"))
random.seed(11)
sample = random.sample(files, 20)
loaded = []
for f in sample:
    s = json.loads(f.read_text(encoding="utf-8"))
    if len(s["closes"]) >= 300:
        loaded.append((f.stem, s))
print("대상 종목:", len(loaded), " 봉수:", [len(s['closes']) for _,s in loaded][:5], "...")

SCAN = 299
tot = {}
for name, fn in [("VCP", vcp_history.replay_vcp),
                 ("PP", power_play_history.replay_power_play),
                 ("3C", cheat_history.replay_cheat)]:
    t0 = time.time(); cnt = 0; ev = 0
    for c, s in loaded:
        r = fn(s, SCAN, None)
        cnt += len(r)
    dt = time.time() - t0
    tot[name] = dt/cnt
    print(f"[{name}] {cnt} 종목일 {dt:.2f}s → {dt/cnt*1000:.3f} ms/종목일 ({cnt/dt:.0f}/초)")
t = sum(tot.values())
print(f"3검출기 합: {t*1000:.3f} ms/종목일 → {1/t:.0f} 종목일/초")

# 이벤트 밀도 측정
nev = 0
for c, s in loaded:
    for name, fn, evf in [("VCP", vcp_history.replay_vcp, vcp_history.find_breakout_events),
                          ("PP", power_play_history.replay_power_play, power_play_history.find_breakout_events),
                          ("3C", cheat_history.replay_cheat, cheat_history.find_breakout_events)]:
        r = fn(s, SCAN, None)
        nev += len(evf(r))
print(f"돌파 이벤트: {len(loaded)}종목 × 299일 → {nev}건 ({nev/len(loaded):.2f}건/종목)")
