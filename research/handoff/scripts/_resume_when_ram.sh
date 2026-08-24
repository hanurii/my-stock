#!/bin/bash
# 여유 RAM 이 생기면 재방출을 이어서 돌린다. **기다리는 게 강제로 시작하는 것보다 낫다.**
# (21:51 에 감시기가 0.486GB 에서 우리 배치를 끊었다. SEPA 는 그때 이미 끝나 있었고
#  압박은 claude 세션 셋에서 왔다. 문턱은 그대로 두고 «기다린다».)
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
NEED=2.3
free(){ python -c "
import ctypes,ctypes.wintypes as wt
class M(ctypes.Structure):
    _fields_=[('a',wt.DWORD),('b',wt.DWORD)]+[(c,ctypes.c_ulonglong) for c in 'cdefghi']
m=M(); m.a=ctypes.sizeof(m); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); print('%.3f'%(m.d/2**30))"; }
for i in $(seq 1 120); do
  D=$(ls .cache/bt5y/sub/uspath_20*.json 2>/dev/null | wc -l)
  [ "$D" -ge 6 ] && { echo "[resume] 이미 6/6"; break; }
  F=$(free)
  if python -c "import sys;sys.exit(0 if float('$F')>=$NEED else 1)"; then
    echo "[resume] 여유 ${F}GB >= ${NEED} — 재개 (현재 ${D}/6)"
    rm -f research/handoff/scripts/_YIELD_HEARTBEAT.txt research/handoff/scripts/_YIELDED_TO_SEPA.txt
    nohup bash research/handoff/scripts/_yield_sup.sh >> research/handoff/scripts/_yield_sup.log 2>&1 &
    bash research/handoff/scripts/_reemit_chain.sh 2>&1 | tail -20
    D=$(ls .cache/bt5y/sub/uspath_20*.json 2>/dev/null | wc -l)
    [ "$D" -ge 6 ] && break
    echo "[resume] ${D}/6 — 다시 기다린다"
  else
    [ $((i % 10)) -eq 1 ] && echo "[resume] 여유 ${F}GB < ${NEED} — 대기 (${D}/6)"
  fi
  sleep 60
done
echo RESUME_DONE
