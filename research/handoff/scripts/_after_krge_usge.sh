#!/bin/bash
# `kr ge` 6해가 끝나면 **빠진 `us ge` 6해**를 이어 돌린다. 순차 보장(병렬 금지).
#   ⚠️ 원래 4배치 체인이 `us strict` 까지만 돌고 끊겼다 — `us_gatege_*` 가 0개다.
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
for i in $(seq 1 240); do
  N=$(ls .cache/bt5y/sub/kr_gatege_20*.json 2>/dev/null | wc -l)
  [ "$N" -ge 6 ] && { echo "kr ge 완주(6/6) — us ge 시작"; break; }
  sleep 30
done
bash research/handoff/scripts/_gate_run.sh us ge
echo "ALL_24_ATTEMPTED"
ls .cache/bt5y/sub/ | grep -E "^(kr|us)_gate(ge)?_20" | wc -l
