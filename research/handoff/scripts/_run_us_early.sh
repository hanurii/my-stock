#!/usr/bin/env bash
# 57번 — 미국 표본을 5.6년 → 9.0년으로 넓힌다 (2017-09 ~ 2020-12 추가 방출)
# 🚨 순차 실행. 병렬 금지 — 한 해당 최대 1.5GB 이고 SEPA-Daily(20:00~)에 자리를 내줘야 한다.
set -u
cd /c/Users/hanul/playground/my-stock || exit 1
LOG=research/handoff/scripts

run() {  # $1=연도 $2=시작 $3=끝
  local y=$1 s=$2 e=$3
  local out=".cache/bt5y/sub/uspath_${y}.json"
  if [ -s "$out" ]; then echo "[$y] 이미 있음 — 건너뜀"; return 0; fi
  echo "[$y] $s ~ $e 시작 $(date +%H:%M:%S)"
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python -u scripts/backtest_volatility_pilot_us.py \
      --market us --emit-paths --start "$s" --end "$e" --out "$out" \
      > "$LOG/_uspath_${y}.log" 2>&1
  local rc=$?
  echo "[$y] 끝 rc=$rc $(date +%H:%M:%S)  $(ls -l "$out" 2>/dev/null | awk '{print $5}') bytes"
  # 관문: 후보가 조용히 0 이 아닌지 본다 (웜업 부족의 전형적 증상)
  local nz
  nz=$(grep -cE '후보 [1-9]' "$LOG/_uspath_${y}.log" 2>/dev/null)
  echo "[$y] 후보>0 인 스캔일 ${nz}개"
  if [ "${nz:-0}" -lt 20 ]; then
    echo "🚨 [$y] 후보가 거의 0 이다 — 웜업 부족 의심. 멈춘다."
    return 3
  fi
}

run 2018 2018-01-01 2018-12-31 || exit 3
run 2019 2019-01-01 2019-12-31 || exit 3
run 2020 2020-01-01 2020-12-31 || exit 3
run 2017 2017-09-05 2017-12-31 || exit 3
echo "=== 전부 끝 $(date +%H:%M:%S)"
