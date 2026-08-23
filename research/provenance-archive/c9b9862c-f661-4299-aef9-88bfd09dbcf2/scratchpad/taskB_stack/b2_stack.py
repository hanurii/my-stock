import sys, random, statistics as s
sys.path.insert(0,"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/taskB_stack")
from blib import *
random.seed(7)
d, ev = bload()
TOTAL = len(ev)

# 스캔 기간: 2025-11-26 ~ 2026-08-21, 180 스캔일 = 약 0.72년(연 250거래일 기준)
YEARS = 180/250.0

def stack_stats(sub, label, rank_key=None):
    w,n = wr(sub); r,_ = realized(sub)
    share = 100.0*len(sub)/TOTAL
    return dict(label=label, n_all=len(sub), n_res=n, wr=w, real=r, share=share)

def cum(sub):
    return sum(e["gain_at_resolve_pct"] for e in sub)

# ---- 필터 정의 ----
F = {}
F["S0 전체(무필터)"]              = lambda e: True
F["S1 +상승국면"]                = lambda e: e["regime_up"]
F["S2 +VCP만"]                  = lambda e: e["regime_up"] and e["pattern"]=="VCP"
F["S3 +그날 거래대금 상위절반"]        = lambda e: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=0.5)
F["S4 +그날 거래대금 상위25%"]       = lambda e: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=0.75)
F["S5 +그날 거래대금 1~3위만"]       = lambda e: e["regime_up"] and e["pattern"]=="VCP" and e["to_rank"]<=3
F["S6 +그날 거래대금 1위만"]         = lambda e: e["regime_up"] and e["pattern"]=="VCP" and e["to_rank"]==1
# 참고: VCP 없이 국면+거래대금
F["(참고)상승국면+거래대금 상위절반"]     = lambda e: e["regime_up"] and (e["to_pct"] is None or e["to_pct"]>=0.5)
F["(참고)상승국면+거래대금 상위25%"]    = lambda e: e["regime_up"] and (e["to_pct"] is None or e["to_pct"]>=0.75)
F["(참고)거래대금 상위25%만(국면무관)"]  = lambda e: (e["to_pct"] is None or e["to_pct"]>=0.75)

print("="*118)
print(f"{'스택':30s} {'거래수':>6s} {'남는비율':>7s} {'결착':>5s} {'승률':>7s} {'실현기대값':>9s} {'누적%합':>9s}")
print("="*118)
rows=[]
for lab, f in F.items():
    sub=[e for e in ev if f(e)]
    w,n=wr(sub); r,_=realized(sub)
    rows.append((lab, sub, w, n, r))
    print(f"{lab:30s} {len(sub):6d} {100.0*len(sub)/TOTAL:6.1f}% {n:5d} {w:6.1f}% {r:+8.2f}% {cum(sub):+8.0f}%")
print("="*118)

# ---- 전후반 안정성 ----
print("\n[전후반 분할 안정성 (2026-03-25 기준)]")
print(f"{'스택':30s} {'전반 승률(n)':>18s} {'후반 승률(n)':>18s} {'전반기대값':>10s} {'후반기대값':>10s}")
for lab, sub, w, n, r in rows:
    a=[e for e in sub if e["scan_date"]<"2026-03-25"]; b=[e for e in sub if e["scan_date"]>="2026-03-25"]
    wa=wr(a); wb=wr(b); ra=realized(a); rb=realized(b)
    fa = f"{wa[0]:.1f}%(n{wa[1]})" if wa[0] is not None else "n/a"
    fb = f"{wb[0]:.1f}%(n{wb[1]})" if wb[0] is not None else "n/a"
    sa = f"{ra[0]:+.2f}%" if ra[0] is not None else "n/a"
    sb = f"{rb[0]:+.2f}%" if rb[0] is not None else "n/a"
    print(f"{lab:30s} {fa:>18s} {fb:>18s} {sa:>10s} {sb:>10s}")
