#!/bin/bash
# 2.5단계 「관문만」 팔(β1) — 연도별로 쪼개 돌린다(두뇌 세션 결정 5).
#   · 진입이 패턴 팔의 수십 배라 이벤트 목록이 커서 한 번에 올리면 RAM 규약에 걸린다.
#   · 매 해 시작 전에 여유 RAM 을 재고, 문턱 미만이면 **건너뛴다**(조용히 줄이지 않고 찍는다).
#   · 결정 B: `--arm gate` 는 per_date 에 후보 종목 코드를 남긴다.
#   · 🚨 동점 규칙 **둘 다 무조건** 돌린다(strict / ge). 조건부 발동 없음.
#     규율: **문턱을 하나 더 다는 것보다 둘 다 돌리는 게 싸면, 둘 다 돌린다.**
# 사용: bash research/handoff/scripts/_gate_run.sh kr|us [strict|ge]
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
MKT="${1:-kr}"
TIE="${2:-strict}"
DONE=0
SFX=""; [ "$TIE" = "ge" ] && SFX="ge"
SKIPPED=0
if [ "$MKT" = "kr" ]; then EXTRA="--series pdata"; NEED=1.8; else EXTRA=""; NEED=1.6; fi

free(){ python -c "
import ctypes
class M(ctypes.Structure):
    _fields_=[('a',ctypes.c_ulong),('b',ctypes.c_ulong),('c',ctypes.c_ulonglong),('d',ctypes.c_ulonglong),('e',ctypes.c_ulonglong),('f',ctypes.c_ulonglong),('g',ctypes.c_ulonglong),('h',ctypes.c_ulonglong),('i',ctypes.c_ulonglong)]
m=M(); m.a=ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); print('%.2f'%(m.d/2**30))"; }

while read Y A B; do
  O=".cache/bt5y/sub/${MKT}_gate${SFX}_${Y}.json"
  [ -f "$O" ] && { echo "skip $Y (이미 있음)"; DONE=$((DONE+1)); continue; }
  F=$(free)
  if python -c "import sys;sys.exit(0 if float('$F')>=$NEED else 1)"; then
    echo "=== $MKT/$TIE $Y (직전 여유 ${F}GB) ==="
    python -u scripts/backtest_volatility_pilot_us.py --market "$MKT" --arm gate \
      --gate-tie "$TIE" --start "$A" --end "$B" $EXTRA --out "$O" 2>&1 | tail -2
  else
    echo "=== $MKT/$TIE $Y 건너뜀 — 여유 ${F}GB < ${NEED} (조용한 절단 아님: 이 줄이 기록이다) ==="
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
# 🚨 24 실행이면 한두 개가 조용히 실패해도 안 보인다 → **실제 파일 수를 세어 찍는다.**
DONE=$(ls .cache/bt5y/sub/${MKT}_gate${SFX}_*.json 2>/dev/null | wc -l)
echo "[$MKT/$TIE] **완료 ${DONE}/6**"
if [ "$DONE" -lt 6 ]; then
  echo "[$MKT/$TIE] 🚨 빠진 해:"
  for Y in 2021 2022 2023 2024 2025 2026; do
    [ -f ".cache/bt5y/sub/${MKT}_gate${SFX}_${Y}.json" ] || echo "    - $Y"
  done
fi
# 빈 로그는 「안 돌았음」과 구분이 안 된다 → 건너뛴 해가 없어도 «명시적으로» 찍는다.
if [ "$SKIPPED" -eq 0 ]; then
  echo "[$MKT/$TIE] 건너뛴 해 없음 (0/6) — 여섯 해 전부 실행함"
else
  echo "[$MKT/$TIE] 건너뛴 해 ${SKIPPED}개 — 위 줄들 참조. 결과에 반드시 적을 것."
fi
echo "GATE_${MKT}_${TIE}_DONE"
