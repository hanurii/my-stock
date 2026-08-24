#!/bin/bash
# 38번 · **방아쇠 전수 경로** 방출 — 연도별 6회. 개발 구간만.
#   🚨 확인 구간(2017-09~2021-01)은 열지 않는다.
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
NEED=2.0
free(){ python -c "
import ctypes
class M(ctypes.Structure):
    _fields_=[('a',ctypes.c_ulong),('b',ctypes.c_ulong),('c',ctypes.c_ulonglong),('d',ctypes.c_ulonglong),('e',ctypes.c_ulonglong),('f',ctypes.c_ulonglong),('g',ctypes.c_ulonglong),('h',ctypes.c_ulonglong),('i',ctypes.c_ulonglong)]
m=M(); m.a=ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); print('%.2f'%(m.d/2**30))"; }
SK=0
while read Y A B; do
  O=".cache/bt5y/sub/uspath_${Y}.json"
  [ -f "$O" ] && { echo "skip $Y"; continue; }
  F=$(free)
  if python -c "import sys;sys.exit(0 if float('$F')>=$NEED else 1)"; then
    echo "=== paths $Y (직전 여유 ${F}GB) ==="
    python research/handoff/scripts/25-run-guarded.py "research/handoff/scripts/_uspath_${Y}.log" -- \
      python -u scripts/backtest_volatility_pilot_us.py --market us --emit-paths \
      --start "$A" --end "$B" --out "$O" 2>&1 | tail -4
  else
    echo "=== paths $Y 건너뜀 — 여유 ${F}GB < ${NEED} ==="; SK=$((SK+1))
  fi
done << 'YEARS'
2021 2021-02-01 2021-12-31
2022 2022-01-01 2022-12-31
2023 2023-01-01 2023-12-31
2024 2024-01-01 2024-12-31
2025 2025-01-01 2025-12-31
2026 2026-01-01 2026-08-21
YEARS
D=$(ls .cache/bt5y/sub/uspath_20*.json 2>/dev/null | wc -l)
echo "[paths] **완료 ${D}/6**"
[ "$SK" -eq 0 ] && echo "건너뛴 해 없음 (0/6)" || echo "건너뛴 해 ${SK}개"
du -sh .cache/bt5y/sub/uspath_20*.json 2>/dev/null | tail -6
echo PATHS_DONE
