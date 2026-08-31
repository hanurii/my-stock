# -*- coding: utf-8 -*-
r"""141d — **창을 틀린 두 해만 다시 짓는다.**

🚨 사고 기록: 141c 재빌드에서 **2017 · 2021 의 «창»을 틀렸다.**
   각 `uspath_*.json` 의 `params` 에서 인자를 읽어 맞췄다고 적어 놓고
   **1999 · 2026 의 양 끝만 확인하고 나머지는 「연초~연말」로 «가정»했다.**
```
2017  옛 params start = **2017-09-05**   (내가 쓴 것 2017-01-01)  → 짝 2,325 · 새쪽만 4,922
2021  옛 params start = **2021-02-01**   (내가 쓴 것 2021-01-01)  → 새쪽만 602
```
   ★ **겹치는 부분은 필드 어긋남이 «0» 이었다** — 내용은 맞고 «범위»만 넓었다.
   ★ 교훈: 「params 에서 읽었다」고 «적는» 것과 «전 연도를 대조하는» 것은 다르다.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path("D:/stock-data/uspath-warm/full")
SPANS = {2017: ("2017-09-05", "2017-12-31"), 2021: ("2021-02-01", "2021-12-31")}

t0 = time.time()
for y, (s, e) in SPANS.items():
    out = OUT / ("uspath_%d.json" % y)
    print("[%5.1f분] %d (%s ~ %s) …" % ((time.time() - t0) / 60, y, s, e), flush=True)
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "backtest_volatility_pilot_us.py"),
         "--market", "us", "--start", s, "--end", e, "--step", "1",
         "--emit-paths", "--emit-warmup", "--warm-days", "700",
         "--out", str(out).replace("\\", "/")],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    ok = out.exists()
    print("   rc=%s · 크기 %.0f MB" % (p.returncode, out.stat().st_size / 1e6 if ok else -1),
          flush=True)
    if p.returncode:
        print((p.stderr or "")[-600:], flush=True)
print("===== 고침 끝 (%.1f분) =====" % ((time.time() - t0) / 60), flush=True)
