#!/bin/bash
# 경로 6/6 이 차면 **0회차 재현 관문**을 돌린다. 통과해야 1회차 변형을 계산한다.
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
for i in $(seq 1 300); do
  N=$(ls .cache/bt5y/sub/uspath_20*.json 2>/dev/null | wc -l)
  [ "$N" -ge 6 ] && { echo "경로 6/6 — 관문 시작"; break; }
  sleep 30
done
python research/handoff/scripts/39-exit-variants.py > research/handoff/scripts/_gate39.log 2>&1
echo "EXIT=$?"
tail -22 research/handoff/scripts/_gate39.log
