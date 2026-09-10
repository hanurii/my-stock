#!/usr/bin/env bash
# 227a — «스스로» 재개하는 루프 (두뇌 얼개 2026-09-07)
#  ⛔ 관문 ① 바퀴 상한 12   ⛔ ② 바퀴마다 로그 한 줄   ⛔ ③ n 이 «안» 늘면 2회 연속 시 중단
#  ⛔ ④ 정본 .cache/bt5y/sub/ 는 «안» 건드림 (각본이 D:/stock-data/uspath-noliq/ 에만 쓴다)
cd /c/Users/hanul/playground/my-stock/research/handoff || exit 1
LOG=results/_227.log
DST=D:/stock-data/uspath-noliq
count() { ls -1 "$DST"/uspath_*.json 2>/dev/null | wc -l | tr -d ' '; }

prev=$(count)
same=0
i=0
while [ "$i" -lt 12 ]; do
  n=$(count)
  if [ "$n" -ge 28 ]; then
    echo "[끝] $(date +%H:%M:%S) — $n / 28 ✅ «전부» 만들었다" >> "$LOG"
    exit 0
  fi
  i=$((i + 1))
  echo "[재개 $i 바퀴] $(date +%H:%M:%S) — 지금 $n / 28" >> "$LOG"
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/227-build-noliq.py >> "$LOG" 2>&1
  now=$(count)
  echo "[바퀴 $i 끝] $(date +%H:%M:%S) — $prev → $now" >> "$LOG"
  if [ "$now" -le "$prev" ]; then
    same=$((same + 1))
    echo "  ⚠️ 한 해도 «안» 늘었다 ($same 회 «연속»)" >> "$LOG"
    if [ "$same" -ge 2 ]; then
      echo "[멈춤] 🚨 2회 «연속» «안» 늘었다 — 「이어 돌기」가 «망가졌다** ⇒ 중단" >> "$LOG"
      exit 2
    fi
  else
    same=0
  fi
  prev=$now
done
echo "[멈춤] 🚨 바퀴 «상한»(12)에 닿았다 — $(count) / 28" >> "$LOG"
exit 3
