#!/bin/bash
cd /c/Users/hanul/playground/my-stock
export PYTHONIOENCODING=utf-8
for cfg in "500 1" "500 2" "1000 1" "1000 2" "2000 1"; do
  set -- $cfg; N=$1; SD=$2
  for Y in 2021 2022 2023 2024 2025 2026; do
    if [ "$Y" = "2021" ]; then A=2021-02-01; B=2021-12-31
    elif [ "$Y" = "2026" ]; then A=2026-01-01; B=2026-08-21
    else A=${Y}-01-01; B=${Y}-12-31; fi
    O=".cache/bt5y/sub/n${N}s${SD}_${Y}.json"
    [ -f "$O" ] && { echo "skip $O"; continue; }
    echo "=== N=$N seed=$SD $Y ==="
    python -u scripts/backtest_volatility_pilot_sub.py --start $A --end $B --series pdata \
      --sample $N --sample-seed $SD --out "$O" 2>&1 | tail -2
  done
done
echo "ALL DONE"
