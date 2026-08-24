#!/bin/bash
# 24칸이 다 차면 `30-arm25.py` 를 **기본 경로**로 돌린다(부분 결과 금지 장치가 켜진 채).
# preflight: params → 스캔일 수 → 24/24 → 항등 검산 → Δ 천장 → 계산
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
for i in $(seq 1 300); do          # 최대 2.5시간
  N=$(ls .cache/bt5y/sub/kr_gate_20*.json .cache/bt5y/sub/kr_gatege_20*.json \
        .cache/bt5y/sub/us_gate_20*.json .cache/bt5y/sub/us_gatege_20*.json 2>/dev/null | wc -l)
  if [ "$N" -ge 24 ]; then echo "24/24 — 30번 시작"; break; fi
  sleep 30
done
python research/handoff/scripts/30-arm25.py > research/handoff/scripts/_arm25.log 2>&1
echo "EXIT=$?"
tail -5 research/handoff/scripts/_arm25.log
