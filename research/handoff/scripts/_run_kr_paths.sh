#!/usr/bin/env bash
# 70번 — 한국 경로 방출 (미국과 «같은 코드·같은 규약»)
set -u
cd /c/Users/hanul/playground/my-stock || exit 1
LOG=research/handoff/scripts
run(){ local y=$1 s=$2 e=$3
  local out=".cache/bt5y/sub/krpath_${y}.json"
  [ -s "$out" ] && { echo "[$y] 이미 있음"; return 0; }
  echo "[$y] $s ~ $e 시작 $(date +%H:%M:%S)"
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python -u scripts/backtest_volatility_pilot_us.py \
    --market kr --series pdata --emit-paths --start "$s" --end "$e" --out "$out" \
    > "$LOG/_krpath_${y}.log" 2>&1
  local rc=$? nz
  nz=$(grep -cE '후보 [1-9]' "$LOG/_krpath_${y}.log" 2>/dev/null)
  echo "[$y] 끝 rc=$rc $(date +%H:%M:%S) · $(ls -l "$out" 2>/dev/null|awk '{print $5}') bytes · 후보>0 인 날 ${nz}"
  [ "${nz:-0}" -lt 20 ] && { echo "🚨 [$y] 후보 거의 0 — 멈춘다"; return 3; }
  return 0
}
run 2021 2021-02-01 2021-12-31 || exit 3
run 2022 2022-01-01 2022-12-31 || exit 3
run 2023 2023-01-01 2023-12-31 || exit 3
run 2024 2024-01-01 2024-12-31 || exit 3
run 2025 2025-01-01 2025-12-31 || exit 3
run 2026 2026-01-01 2026-08-21 || exit 3
echo "=== 전부 끝 $(date +%H:%M:%S)"
