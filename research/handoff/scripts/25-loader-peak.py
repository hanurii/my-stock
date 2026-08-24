# -*- coding: utf-8 -*-
"""25 · **미국 로더 peak RSS 실측용 자식 프로세스.** 로더만 돌리고 끝난다.

`_peak_rss.py` 로 감싸서 부른다:
  python research/handoff/scripts/_peak_rss.py us500 -- \
    python research/handoff/scripts/25-loader-peak.py 500

★ 하네스는 돌리지 않는다. **로더 한 통과의 봉우리만** 잰다.
"""
from __future__ import annotations
import sys, time, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import us_loader  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
BUILD_UNI = "--no-universe" not in sys.argv
START, END = "2019-12-01", "2026-08-21"
t0 = time.time()
uni, packed, full, meta = us_loader.build_all(START, END, "base", 1300.0, N or None, BUILD_UNI)
print(json.dumps({
    "limit": N, "build_universe": BUILD_UNI, "seconds": round(time.time() - t0, 1),
    "n_codes_window": meta["n_codes_window"], "n_with_series": meta["n_codes_with_series"],
    "n_rows": meta["n_rows"], "n_dates": meta["n_dates"],
    "universe_entries": sum(len(v) for v in uni.values()),
}, ensure_ascii=False))
