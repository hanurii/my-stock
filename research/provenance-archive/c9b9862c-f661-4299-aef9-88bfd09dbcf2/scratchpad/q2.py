# -*- coding: utf-8 -*-
from engine import *
base = run_rule()
print("── 조기익절 규칙의 '기준 대비 손실'을 전·후반으로 쪼개기 ──")
print(f"{'X':>4} {'전반차':>8} {'p전':>7} {'후반차':>8} {'p후':>7} {'부호유지':>7}")
for X in (3,5,7,8,10,12,15):
    r = run_rule(tp=float(X))
    pairs=[(a,b) for a,b in zip(r,base)]
    ra1=[a for a,b in pairs if a["entry_date"]<SPLIT]; rb1=[b for a,b in pairs if b["entry_date"]<SPLIT]
    ra2=[a for a,b in pairs if a["entry_date"]>=SPLIT]; rb2=[b for a,b in pairs if b["entry_date"]>=SPLIT]
    d1,p1=paired_perm(ra1,rb1); d2,p2=paired_perm(ra2,rb2)
    print(f"{X:>4} {d1:>8.2f} {p1:>7.4f} {d2:>8.2f} {p2:>7.4f} {'예' if d1*d2>0 else '아니오':>7}")

print()
print("── (다) 최소 보유일 M: M거래일 전에는 익절 금지 (조기익절 +8% 기준, 손절 -10 상시) ──")
b8 = run_rule(tp=8.0)
print(f"{'M':>3} {'평균%':>7} {'승률':>6} {'평균일':>6} {'일당%':>7} {'vs +8즉시':>9} {'p':>7} {'vs현행':>7} {'p':>7}")
s8=stats(b8)
print(f"{0:>3} {s8['avg']:>7.2f} {s8['win_rate']:>6.1f} {s8['avg_days']:>6.1f} {s8['ret_per_day']:>7.4f} {0.0:>9.2f} {'-':>7} {stats(b8)['avg']-stats(base)['avg']:>7.2f}")
for M in (3,5,7,10,15,20):
    r = run_rule(tp=8.0, min_hold=M)
    s=stats(r); d,p=paired_perm(r,b8); d2,p2=paired_perm(r,base)
    print(f"{M:>3} {s['avg']:>7.2f} {s['win_rate']:>6.1f} {s['avg_days']:>6.1f} {s['ret_per_day']:>7.4f} {d:>9.2f} {p:>7.4f} {d2:>7.2f} {p2:>7.4f}")
print()
print("── 같은 것을 조기익절 +10 / +12 / +15 위에서도 ──")
for X in (10.0,12.0,15.0):
    bX=run_rule(tp=X)
    line=[f"tp+{int(X)}: M0 {stats(bX)['avg']:.2f}"]
    for M in (3,5,7,10):
        r=run_rule(tp=X,min_hold=M); d,p=paired_perm(r,bX)
        line.append(f"M{M} {stats(r)['avg']:.2f}(+{d:.2f},p={p:.3f})")
    print("  ".join(line))
