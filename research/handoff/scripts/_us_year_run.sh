#!/bin/bash
# 미국 **연도별 재실행** — 한국과 «구조까지» 같게 만든다(두뇌 세션 승인).
#   · warm 430일 (기본값 140은 200일선·52주 고가를 만들 수 없었다)
#   · 실행 단위를 연도별로 = `open_until` 이 해마다 초기화 → 한국 bt_YYYY.json 과 동일
#   · 매 해 시작 전 여유 RAM 측정 · 문턱 미만이면 건너뛰고 «그 줄을 찍는다»
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
NEED=2.0
free(){ python -c "
import ctypes
class M(ctypes.Structure):
    _fields_=[('a',ctypes.c_ulong),('b',ctypes.c_ulong),('c',ctypes.c_ulonglong),('d',ctypes.c_ulonglong),('e',ctypes.c_ulonglong),('f',ctypes.c_ulonglong),('g',ctypes.c_ulonglong),('h',ctypes.c_ulonglong),('i',ctypes.c_ulonglong)]
m=M(); m.a=ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); print('%.2f'%(m.d/2**30))"; }
SKIPPED=0
while read Y A B; do
  O=".cache/bt5y/sub/us_${Y}.json"
  [ -f "$O" ] && { echo "skip $Y (이미 있음)"; continue; }
  F=$(free)
  if python -c "import sys;sys.exit(0 if float('$F')>=$NEED else 1)"; then
    echo "=== US $Y (직전 여유 ${F}GB) ==="
    python research/handoff/scripts/25-run-guarded.py "research/handoff/scripts/_us_${Y}.log" -- \
      python -u scripts/backtest_volatility_pilot_us.py --market us \
      --start "$A" --end "$B" --out "$O" 2>&1 | tail -4
  else
    echo "=== US $Y 건너뜀 — 여유 ${F}GB < ${NEED} (조용한 절단 아님: 이 줄이 기록이다) ==="
    SKIPPED=$((SKIPPED+1))
  fi
done << 'YEARS'
2021 2021-02-01 2021-12-31
2022 2022-01-01 2022-12-31
2023 2023-01-01 2023-12-31
2024 2024-01-01 2024-12-31
2025 2025-01-01 2025-12-31
2026 2026-01-01 2026-08-21
YEARS
DONE=$(ls .cache/bt5y/sub/us_20*.json 2>/dev/null | wc -l)
echo "[US 연도별] **완료 ${DONE}/6**"
if [ "$DONE" -lt 6 ]; then
  echo "🚨 빠진 해:"
  for Y in 2021 2022 2023 2024 2025 2026; do
    [ -f ".cache/bt5y/sub/us_${Y}.json" ] || echo "    - $Y"
  done
fi
[ "$SKIPPED" -eq 0 ] && echo "건너뛴 해 없음 (0/6)" || echo "건너뛴 해 ${SKIPPED}개"
echo US_YEAR_DONE
