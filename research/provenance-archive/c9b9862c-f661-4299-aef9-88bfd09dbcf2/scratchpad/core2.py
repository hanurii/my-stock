import sys
sys.path.insert(0,r'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad')
from core import *

def sim2(i, target=20.0, stop=-10.0, from_day=None, level=None, gap_fill=True):
    """from_day 이후 '아무 날이나' 종가<=level 이면 정리(단발 날짜 아님)."""
    p = PATHS[i]; h,l,c,o = p["h"],p["l"],p["c"],p["o"]
    m=len(c)
    for k in range(0,m):
        hi,lo,op=h[k],l[k],o[k]
        ht = hi is not None and hi>=target
        hs = lo is not None and lo<=stop
        if ht and hs:
            return {"ret": (min(op,stop) if (gap_fill and op is not None and op<=stop) else stop),"days":k,"kind":"amb"}
        if ht:
            return {"ret": (max(op,target) if (gap_fill and op is not None and op>=target) else target),"days":k,"kind":"win"}
        if hs:
            return {"ret": (min(op,stop) if (gap_fill and op is not None and op<=stop) else stop),"days":k,"kind":"loss"}
        if from_day is not None and k>=from_day and c[k] is not None and c[k]<=level:
            return {"ret": c[k],"days":k,"kind":"cut"}
    last=next((c[k] for k in range(m-1,-1,-1) if c[k] is not None),0.0)
    return {"ret":last,"days":m-1,"kind":"open"}
