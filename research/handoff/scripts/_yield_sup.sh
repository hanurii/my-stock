#!/usr/bin/env bash
# 양보 감시기의 «감시자».
#
# 🚨 실패 방향을 뒤집는다.
#    전: 감시기가 죽어도 배치는 계속 돈다 (= 감시 없이 사용자 작업과 경합)
#    후: 감시기를 못 살리면 **배치를 멈춘다** (= 사용자 작업에 길을 내준다)
#
# 하는 일
#   1. 감시기가 없으면 다시 띄운다 (최대 3번)
#   2. 심장박동(_YIELD_HEARTBEAT.txt)이 90초 넘게 멎으면 감시기를 죽이고 다시 띄운다
#   3. 3번 되살리기에 실패하면 **우리 배치를 끊고** 끝낸다
#   4. 감시기가 끝 코드 0(할 일 끝) 또는 1(양보함)로 끝나면 조용히 같이 끝낸다
#
# 실행: nohup bash research/handoff/scripts/_yield_sup.sh > .../_yield_sup.log 2>&1 &

cd "$(dirname "$0")/../../.." || exit 2
D=research/handoff/scripts
BEAT=$D/_YIELD_HEARTBEAT.txt
LOG=$D/_yield.log
STALE=90
TRIES=0

say() { echo "[$(date +%H:%M:%S)] $*"; }

alive() {
  powershell -NoProfile -Command \
    "@(Get-CimInstance Win32_Process | Where-Object { \$_.Name -match 'python' -and \$_.CommandLine -match '_yield_watch' }).Count" \
    2>/dev/null | tr -d '\r' | head -1
}

kill_batch() {
  say "🚨 우리 배치를 끊는다 — 감시 없이 도는 것보다 멈추는 게 낫다"
  powershell -NoProfile -Command \
    "Get-CimInstance Win32_Process | Where-Object { \$_.Name -match 'python|bash' -and \$_.CommandLine -match '_us_paths_run|25-run-guarded|--emit-paths' -and \$_.CommandLine -notmatch 'ohlcv_matrix|_after_paths_gate' } | ForEach-Object { Write-Output \$_.ProcessId; Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }"
  # 잘린 json 지우기 — **파일이 있다 != 온전하다**
  PYTHONIOENCODING=utf-8 python -c "
import json,pathlib
p=pathlib.Path('.cache/bt5y/sub')
for f in sorted(p.glob('uspath_*.json')):
    try: json.loads(f.read_text(encoding='utf-8'))
    except Exception: f.unlink(); print('지움(잘림):',f.name)
print('남은 경로:',[f.stem for f in sorted(p.glob('uspath_*.json'))])"
}

start() {
  TRIES=$((TRIES+1))
  say "감시기 기동 (${TRIES}/3)"
  PYTHONIOENCODING=utf-8 nohup python -u "$D/_yield_watch.py" >> "$LOG" 2>&1 &
  sleep 6
}

say "감시자 시작 — 심장박동 ${STALE}초 · 되살리기 최대 3회"
[ "$(alive)" = "0" ] && start

while true; do
  sleep 20
  N=$(alive)
  if [ "$N" != "0" ]; then
    # 살아 있다 — 심장박동이 멎지 않았는지 본다
    if [ -f "$BEAT" ]; then
      E=$(grep '^epoch=' "$BEAT" | cut -d= -f2)
      AGE=$(( $(date +%s) - ${E:-0} ))
      if [ "$AGE" -gt "$STALE" ]; then
        say "⚠️ 심장박동 ${AGE}초 멎음 — 감시기가 굳었다. 죽이고 다시 띄운다"
        powershell -NoProfile -Command \
          "Get-CimInstance Win32_Process | Where-Object { \$_.Name -match 'python' -and \$_.CommandLine -match '_yield_watch' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }"
        [ "$TRIES" -ge 3 ] && { kill_batch; exit 1; }
        start
      fi
    fi
    continue
  fi

  # 감시기가 없다 — 제 할 일을 끝낸 것인가, 죽은 것인가
  S=$(grep '^state=' "$BEAT" 2>/dev/null | cut -d= -f2)
  case "$S" in
    done|yielded)
      say "감시기가 정상 종료(state=$S) — 감시자도 끝낸다"; exit 0 ;;
  esac
  say "⚠️ 감시기가 죽었다 (state=${S:-없음})"
  if [ "$TRIES" -ge 3 ]; then
    say "🚨 3회 되살리기 실패 — 감시를 보장할 수 없다"
    kill_batch
    exit 1
  fi
  start
done
