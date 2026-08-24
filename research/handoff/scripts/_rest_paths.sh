#!/bin/bash
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
while read Y A B; do
  O=".cache/bt5y/sub/uspath_${Y}.json"
  [ -f "$O" ] && { echo "skip $Y"; continue; }
  echo "=== paths $Y ==="
  python research/handoff/scripts/25-run-guarded.py "research/handoff/scripts/_uspath_${Y}.log" -- \
    python -u scripts/backtest_volatility_pilot_us.py --market us --emit-paths \
    --start "$A" --end "$B" --out "$O" 2>&1 | tail -4
done << 'YEARS'
2025 2025-01-01 2025-12-31
2026 2026-01-01 2026-08-21
YEARS
D=$(ls .cache/bt5y/sub/uspath_20*.json 2>/dev/null | wc -l)
echo "[rest] 경로 ${D}/6"
if [ "$D" -eq 6 ]; then
  echo "[rest] 연장 재생성"
  python -u research/handoff/scripts/40-extend-cap-paths.py 2>&1 | tail -8
fi
echo REST_DONE
