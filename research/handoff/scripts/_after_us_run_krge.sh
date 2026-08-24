#!/bin/bash
# 현재 미국 배치가 끝나면 `kr ge` 를 이어 돌린다. **순차 보장** — 병렬로 띄우지 않는다
# (여유 RAM 1.5GB 안팎이라 병렬은 규약 위반).
#   기다리는 조건: us_gate_*(strict) 6개 + us_gatege_*(ge) 6개 = 12개
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
for i in $(seq 1 240); do            # 최대 2시간
  N=$(ls .cache/bt5y/sub/us_gate_20*.json .cache/bt5y/sub/us_gatege_20*.json 2>/dev/null | wc -l)
  P=$(powershell -NoProfile -Command "(Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count" 2>/dev/null | tr -d '\r')
  if [ "$N" -ge 12 ]; then echo "미국 배치 완주(12/12) — kr ge 시작"; break; fi
  if [ "${P:-0}" -eq 0 ] && [ "$i" -gt 2 ]; then
    echo "🚨 파이썬이 없는데 미국 파일이 ${N}/12 — 배치가 죽었다. kr ge 를 먼저 돌린다."
    break
  fi
  sleep 30
done
bash research/handoff/scripts/_gate_run.sh kr ge
echo "ALL_GATE_DONE"
