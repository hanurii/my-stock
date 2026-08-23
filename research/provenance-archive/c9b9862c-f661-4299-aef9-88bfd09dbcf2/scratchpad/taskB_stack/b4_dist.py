import sys, random, statistics as s
sys.path.insert(0,"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/taskB_stack")
from blib import *
d, ev = bload()
YEARS=180/250.0; SLOTS=5; POS=10_000_000
alldates=sorted(set(e["entry_date"] for e in ev))

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

STACKS = [
 ("S0 전체(무필터)",        lambda e: True),
 ("S1 상승국면",            lambda e: e["regime_up"]),
 ("S2 상승+VCP",           lambda e: e["regime_up"] and e["pattern"]=="VCP"),
 ("S3 상승+VCP+거래대금상위50%", lambda e: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=0.5)),
 ("S4 상승+VCP+거래대금상위25%", lambda e: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=0.75)),
 ("S4b 상승+거래대금상위25%",   lambda e: e["regime_up"] and (e["to_pct"] is None or e["to_pct"]>=0.75)),
 ("S5 상승+VCP+거래대금상위10%", lambda e: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=0.90)),
]
print("슬롯 배정 순서를 200번 무작위로 바꿔 본 분포 (슬롯 5·1건 1,000만원)")
print("="*140)
print(f"{'스택':30s} {'체결수 중앙':>10s} {'승률 중앙':>9s} {'9개월손익 중앙':>13s} {'하위10%':>10s} {'상위90%':>10s} {'적자확률':>8s} {'연환산 중앙':>12s}")
print("="*140)
for lab, f in STACKS:
    pnls=[]; wrs=[]; ns=[]
    for sd_ in range(200):
        t=simulate(f, sd_)
        pnls.append(sum(POS*e["gain_at_resolve_pct"]/100 for e in t))
        w,n=wr(t); wrs.append(w if w is not None else 0); ns.append(len(t))
    pnls.sort()
    med=s.median(pnls)
    print(f"{lab:30s} {s.median(ns):10.0f} {s.median(wrs):8.1f}% {med/1e4:+12.0f}만 {pnls[19]/1e4:+9.0f}만 {pnls[179]/1e4:+9.0f}만 "
          f"{100*sum(1 for x in pnls if x<0)/len(pnls):7.1f}% {med/YEARS/1e4:+11.0f}만")
print("="*140)

print("\n[전후반 슬롯 시뮬 (무작위 200회 중앙값)]")
for lab, f in STACKS:
    out=[]
    for tag, lo, hi in [("전반","2025-11-01","2026-03-25"),("후반","2026-03-25","2099-01-01")]:
        pnls=[]; wrs=[]
        for sd_ in range(100):
            t=[e for e in simulate(f, sd_) if lo<=e["scan_date"]<hi]
            pnls.append(sum(POS*e["gain_at_resolve_pct"]/100 for e in t))
            w,n=wr(t); wrs.append(w if w is not None else 0)
        out.append(f"{tag} 승률 {s.median(wrs):.1f}% 손익 {s.median(pnls)/1e4:+.0f}만")
    print(f"   {lab:30s} " + " | ".join(out))
