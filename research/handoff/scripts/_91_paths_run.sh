#!/bin/bash
# 91 — 표본 밖 경로 방출. `_us_paths_run.sh` 와 «같은 규약», 자료만 전체이력판.
#   🚨 이미 있는 uspath_*.json 은 건너뛴다(skip). 옛 2017~2026 을 덮지 않는다.
#   🚨 SEPA-Daily 가 우리보다 우선 — 여유 RAM 2.0GB 미만이면 그 해를 건너뛴다.
cd /c/Users/hanul/playground/my-stock; export PYTHONIOENCODING=utf-8
NEED=${NEED:-2.0}
free(){ python -c "
import ctypes
class M(ctypes.Structure):
    _fields_=[('a',ctypes.c_ulong),('b',ctypes.c_ulong)]+[(c,ctypes.c_ulonglong) for c in 'cdefghi']
m=M(); m.a=ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); print('%.2f'%(m.d/2**30))"; }
SK=0; OK=0
while read Y A B; do
  O=".cache/bt5y/sub/uspath_${Y}.json"
  [ -f "$O" ] && { echo "skip $Y (이미 있음)"; continue; }
  F=$(free)
  if python -c "import sys;sys.exit(0 if float('$F')>=$NEED else 1)"; then
    T0=$(date +%s)
    echo "=== paths $Y  $A~$B  (직전 여유 ${F}GB) ==="
    python research/handoff/scripts/25-run-guarded.py "research/handoff/scripts/_uspath_${Y}.log" -- \
      python -u scripts/backtest_volatility_pilot_us.py --market us --emit-paths \
      --start "$A" --end "$B" --out "$O" 2>&1 | tail -3
    T1=$(date +%s)
    if [ -f "$O" ]; then OK=$((OK+1)); echo "    ✅ $Y 완료 $((T1-T0))초  $(du -h $O | cut -f1)";
    else echo "    🚨 $Y 파일이 안 나왔다"; fi
  else
    echo "=== paths $Y 건너뜀 — 여유 ${F}GB < ${NEED} ==="; SK=$((SK+1))
  fi
done << 'YEARS'
1999 1999-04-01 1999-12-31
2000 2000-01-01 2000-12-31
2001 2001-01-01 2001-12-31
2002 2002-01-01 2002-12-31
2003 2003-01-01 2003-12-31
2004 2004-01-01 2004-12-31
2005 2005-01-01 2005-12-31
2006 2006-01-01 2006-12-31
2007 2007-01-01 2007-12-31
2008 2008-01-01 2008-12-31
2009 2009-01-01 2009-12-31
2010 2010-01-01 2010-12-31
2011 2011-01-01 2011-12-31
2012 2012-01-01 2012-12-31
2013 2013-01-01 2013-12-31
2014 2014-01-01 2014-12-31
2015 2015-01-01 2015-12-31
2016 2016-01-01 2016-12-31
YEARS
echo "[91-paths] 완료 ${OK} · 건너뜀 ${SK}"
ls .cache/bt5y/sub/uspath_*.json | wc -l
echo PATHS91_DONE
