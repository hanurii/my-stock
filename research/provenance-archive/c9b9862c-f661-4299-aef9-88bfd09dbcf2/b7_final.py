import sys, random, statistics as s
sys.path.insert(0,"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/taskB_stack")
from blib import *
d, ev = bload()
S4b = lambda e: e["regime_up"] and (e["to_pct"] is None or e["to_pct"]>=0.75)
S4  = lambda e: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=0.75)

print("[월별] 상승국면+그날 거래대금 상위25%")
bym=defaultdict(list)
for e in ev:
    if S4b(e): bym[e["month"]].append(e)
for m in sorted(bym):
    w,n=wr(bym[m]); r,_=realized(bym[m])
    print(f"   {m}: n={len(bym[m]):3d} 결착{n:3d} 승률 {w if w else 0:5.1f}% 실현 {r if r else 0:+6.2f}%")

print("\n[하루 몇 건 나오나]")
byday=defaultdict(int); alld=set()
for e in ev:
    alld.add(e["scan_date"])
    if S4b(e): byday[e["scan_date"]]+=1
updays=set(e["scan_date"] for e in ev if e["regime_up"])
cnts=[byday.get(dte,0) for dte in sorted(updays)]
print(f"   상승국면 스캔일 {len(updays)}일 중 신호 있는 날 {sum(1 for c in cnts if c>0)}일, 평균 {s.mean(cnts):.2f}건/일, 중앙 {s.median(cnts):.0f}건")
print(f"   전체 스캔일 {len(alld)}일 · 무필터 평균 {len(ev)/len(alld):.2f}건/일")

print("\n[패턴별 · 상승국면+거래대금 상위25% 안에서]")
for p in ("VCP","3C","PP"):
    sub=[e for e in ev if S4b(e) and e["pattern"]==p]
    if not sub: continue
    w,n=wr(sub); r,_=realized(sub)
    print(f"   {p}: n={len(sub):3d} 승률 {w if w else 0:5.1f}%(결착{n}) 실현 {r if r else 0:+6.2f}%")

print("\n[조정국면에서도 거래대금 상위25%면 살아나나]")
sub=[e for e in ev if not e["regime_up"] and (e["to_pct"] is None or e["to_pct"]>=0.75)]
w,n=wr(sub); r,_=realized(sub)
sub2=[e for e in ev if not e["regime_up"] and not (e["to_pct"] is None or e["to_pct"]>=0.75)]
w2,n2=wr(sub2); r2,_=realized(sub2)
print(f"   조정+상위25% : 승률 {w:5.1f}%(n{n}) 실현 {r:+.2f}%")
print(f"   조정+나머지  : 승률 {w2:5.1f}%(n{n2}) 실현 {r2:+.2f}%")

print("\n[손절폭을 좁혀 승률을 낮추는 대신 손실을 줄이면? — 참고 (max_dd 사용, 근사)]")
R=resolved(ev)
for stop in (5,7,10,15):
    wins=0; losses=0; tot=0.0
    for e in R:
        if e["max_dd_pct"] <= -stop:
            # 손절이 먼저였는지 알 수 없으므로 근사: 손절폭 내에서 눌린 적 있으면 손절 처리(보수적)
            losses+=1; tot+= -stop
        else:
            wins+=1; tot+= e["gain_at_resolve_pct"]
    print(f"   손절 -{stop}% 가정(보수적 근사): 승률 {100*wins/(wins+losses):.1f}% 거래당 {tot/(wins+losses):+.2f}%")
