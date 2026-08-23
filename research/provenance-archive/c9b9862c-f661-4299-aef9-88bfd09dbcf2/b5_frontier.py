import sys, random, statistics as s
sys.path.insert(0,"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/taskB_stack")
from blib import *
d, ev = bload()
YEARS=180/250.0; SLOTS=5; POS=10_000_000
alldates=sorted(set(e["entry_date"] for e in ev))
TOTAL=len(ev)

def simulate(filt, seed):
    rng=random.Random(seed)
    cands=defaultdict(list)
    for e in ev:
        if filt(e): cands[e["entry_date"]].append(e)
    open_pos=[]; taken=[]
    for dte in alldates:
        open_pos=[p for p in open_pos if p[0]>=dte]
        held=set(p[1] for p in open_pos)
        lst=[e for e in cands.get(dte,[]) if e["code"] not in held]
        rng.shuffle(lst)
        for e in lst:
            if len(open_pos)>=SLOTS: break
            if e["code"] in held: continue
            open_pos.append((e["resolve_date"],e["code"],e)); held.add(e["code"]); taken.append(e)
    return taken

def frontier(lab, f, n=120):
    pool=[e for e in ev if f(e)]
    w,nn=wr(pool); r,_=realized(pool)
    pnls=[];exec_n=[];wrs=[]
    for sd_ in range(n):
        t=simulate(f,sd_)
        pnls.append(sum(POS*e["gain_at_resolve_pct"]/100 for e in t)); exec_n.append(len(t))
        ww,_=wr(t); wrs.append(ww if ww else 0)
    a=[e for e in pool if e["scan_date"]<"2026-03-25"]; b=[e for e in pool if e["scan_date"]>="2026-03-25"]
    wa=wr(a)[0]; wb=wr(b)[0]
    ok = "OK" if (wa is not None and wb is not None and wa>=40 and wb>=40) else ("불안정" if wa is not None and wb is not None else "표본부족")
    print(f"{lab:38s} 풀{len(pool):4d}({100*len(pool)/TOTAL:4.1f}%) 승률 {w if w else 0:5.1f}%(n{nn:3d}) 기대값 {r if r else 0:+5.2f}% | "
          f"체결중앙 {s.median(exec_n):3.0f} 연손익중앙 {s.median(pnls)/YEARS/1e4:+7.0f}만 | 전반 {wa if wa else 0:5.1f}% 후반 {wb if wb else 0:5.1f}% [{ok}]")

print("=== 거래대금 백분위 컷을 조금씩 올려가며 (상승국면 + VCP 고정) ===")
for cut,lab in [(0.0,"컷없음"),(0.25,"하위25% 제외"),(0.5,"상위50%"),(0.75,"상위25%"),(0.85,"상위15%"),(0.90,"상위10%")]:
    frontier(f"상승+VCP+거래대금 {lab}", lambda e,c=cut: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=c))
print()
print("=== 같은 것, VCP 조건 없이 ===")
for cut,lab in [(0.0,"컷없음"),(0.5,"상위50%"),(0.75,"상위25%"),(0.90,"상위10%")]:
    frontier(f"상승국면+거래대금 {lab}", lambda e,c=cut: e["regime_up"] and (e["to_pct"] is None or e["to_pct"]>=c))
print()
print("=== '억지로 50% 만들기' — 검정 통과 못 한 요인들을 덧붙이면? (과적합 시연) ===")
base=lambda e: e["regime_up"] and (e["to_pct"] is None or e["to_pct"]>=0.75)
frontier("기준: 상승+거래대금상위25%", base)
frontier("  +ATR<6%", lambda e: base(e) and e["atr_pct"]<6)
frontier("  +ATR<6% +갭업<1%", lambda e: base(e) and e["atr_pct"]<6 and e["gap_up_pct"]<1)
frontier("  +ATR<6% +갭업<1% +RS>=90", lambda e: base(e) and e["atr_pct"]<6 and e["gap_up_pct"]<1 and e["rs"]>=90)
frontier("  +ATR<6% +갭업<1% +RS>=90 +VCP", lambda e: base(e) and e["atr_pct"]<6 and e["gap_up_pct"]<1 and e["rs"]>=90 and e["pattern"]=="VCP")
print()
print("=== 손익분기 승률 ===")
R=resolved(ev)
w=[e["gain_at_resolve_pct"] for e in R if e["result"]=="win"]; l=[e["gain_at_resolve_pct"] for e in R if e["result"]=="loss"]
mw=s.mean(w); ml=s.mean(l)
print(f"   실측 평균 이익 {mw:+.2f}% / 평균 손실 {ml:+.2f}%  →  손익분기 승률 {100*(-ml)/(mw-ml):.1f}%")
print(f"   명목 +20/-10 기준 손익분기 33.3%")
for p in (39.1,45,48,50,55):
    print(f"   승률 {p:.1f}% → 거래당 기대값 {(p/100*mw+(1-p/100)*ml):+.2f}% (실측 이익/손실 크기 적용)")
