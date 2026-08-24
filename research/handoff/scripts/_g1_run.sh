#!/bin/bash
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
free(){ python -c "
import ctypes
class M(ctypes.Structure):
    _fields_=[('a',ctypes.c_ulong),('b',ctypes.c_ulong),('c',ctypes.c_ulonglong),('d',ctypes.c_ulonglong),('e',ctypes.c_ulonglong),('f',ctypes.c_ulonglong),('g',ctypes.c_ulonglong),('h',ctypes.c_ulonglong),('i',ctypes.c_ulonglong)]
m=M(); m.a=ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); print('%.2f'%(m.d/2**30))"; }
while read Y A B; do
  O=".cache/bt5y/sub/g1_${Y}.json"
  [ -f "$O" ] && { echo "skip $Y"; continue; }
  F=$(free)
  if python -c "import sys;sys.exit(0 if float('$F')>=1.6 else 1)"; then
    echo "=== $Y (직전 여유 ${F}GB) ==="
    python -u scripts/backtest_volatility_pilot_us.py --market kr --start $A --end $B --series pdata --out "$O" 2>&1 | tail -1
  else
    echo "=== $Y 건너뜀 — 여유 ${F}GB < 1.6 ==="
  fi
done << 'YEARS'
2021 2021-02-01 2021-12-31
2022 2022-01-01 2022-12-31
2024 2024-01-01 2024-12-31
2025 2025-01-01 2025-12-31
2026 2026-01-01 2026-08-21
YEARS
echo G1_ALL_DONE
