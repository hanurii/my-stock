# -*- coding: utf-8 -*-
"""문턱 5 재구현 — (A) 조사 세션 방식(복제당 seed 1개) (B) 복제당 seed 5개 평균.
관측 통계는 400회 중앙값인데 귀무는 seed 1개짜리다. 그 불일치의 크기를 잰다."""
import json, collections, statistics as st, random, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = slot_sim.net
paths=[]; cal=set()
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        paths.append({'code':p['code'],'pat':p['pattern'],'sd':p['scan_date'],'ed':p['entry_date'],
                      'E':p['entry_price'],'h':p['h'],'l':p['l'],'c':p['c'],'dt':p['dates']})
        cal.update(p['dates'])
    del d
lo=min(p['ed'] for p in paths); hi=max(p['dt'][-1] for p in paths)
all_dates=sorted(x for x in cal if lo<=x<=hi)
pos={d:i for i,d in enumerate(all_dates)}
n_pos=len(all_dates); print("달력 %d일 (%s ~ %s)" % (n_pos, all_dates[0], all_dates[-1]))

def cell(tg,sp):
    out=[]
    for p in paths:
        E=p['E']; T=E*(1+tg/100); S=E*(1-sp/100); h,l,c=p['h'],p['l'],p['c']
        r=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs:
                r=(0,'loss') if i==0 else 'amb'; break
            if ht: r=(i,'win'); break
            if hs: r=(i,'loss'); break
        if r=='amb': continue
        if r is None:
            g=(c[-1]/E-1)*100; r=(len(c)-1,'win' if g>0 else 'loss')
        i,lb=r
        out.append({'code':p['code'],'pattern':p['pat'],'scan_date':p['sd'],'entry_date':p['ed'],
                    'resolve_date':p['dt'][i],'gain':(c[i]/E-1)*100,'result':lb,
                    'days_held':i,'pos':pos[p['ed']]})
    return out
TG=[15,20,25,30,40,50]; SP=[5,7,10,12]
cells={(t,s):cell(t,s) for t in TG for s in SP}
print("24칸 생성 완료", flush=True)

def boot_sim(by_pos, seed, slots=5):
    eq=1.0; held=[]
    for p in range(n_pos):
        if held:
            for h in held:
                if not h[3] and h[0] < p:
                    eq += h[2]*net(h[1]['gain'])/100; h[3]=True
            held=[h for h in held if h[0] >= p]
        free=slots-len(held)
        if free>0:
            c=by_pos.get(p)
            if c:
                if len(c)>1: c=sorted(c,key=lambda t: slot_sim.order_key(seed,t))
                w=eq/slots
                for t in c[:free]: held.append([p+t['days_held'],t,w,False])
    for h in held:
        if not h[3]: eq += h[2]*net(h[1]['gain'])/100
    return (eq-1)*100

idx={k: collections.defaultdict(list) for k in cells}
for k,tr in cells.items():
    for t in tr: idx[k][t['pos']].append(t)
BASE=(20,10)
# 관측 우위(400회 중앙) — 원 달력
E400={k:[slot_sim.sim(tr,seed=i)['equity_pct'] for i in range(400)] for k,tr in cells.items()}
obs={k: st.median([E400[k][i]-E400[BASE][i] for i in range(400)]) for k in cells if k!=BASE}
obs_max=max(obs.values()); obs_cell=max(obs,key=obs.get)
print("관측 최고 칸 +%d/-%d · 우위 %+.1f%%p (결과파일 +50/-7 +67.6)" % (obs_cell[0],obs_cell[1],obs_max), flush=True)

def run_boot(n_boot, n_seed, seed0=10000, tag=""):
    rnd=random.Random(seed0); maxes=[]
    for b in range(n_boot):
        blocks=[]; tot=0
        while tot<n_pos:
            L=rnd.randint(20,40); a=rnd.randint(0,n_pos-L)
            blocks.append((a,min(L,n_pos-tot))); tot+=L
        eqs={}
        for k in cells:
            by=collections.defaultdict(list); off=0
            for a,L in blocks:
                for j in range(L):
                    for t in idx[k].get(a+j,()): by[off+j].append(t)
                off+=L
            eqs[k]=st.median([boot_sim(by,seed0+b*17+s) for s in range(n_seed)])
        maxes.append(max(eqs[k]-eqs[BASE]-obs[k] for k in obs))
        if (b+1)%25==0: print("   %s %d/%d" % (tag,b+1,n_boot), flush=True)
    ms=sorted(maxes)
    return st.median(ms), ms[int(len(ms)*.95)], sum(1 for x in maxes if x>=obs_max)/len(maxes)

m,p95,pv = run_boot(200,1,tag="(A) seed 1개")
print("\n(A) 조사 세션 방식 재현 — 복제당 seed 1개, 200회")
print("    귀무 중앙 %+.1f · 95%% 분위 %+.1f · p = %.3f   [결과파일: 95%% +358.2 · p 0.728]" % (m,p95,pv))
m5,p95_5,pv5 = run_boot(80,5,seed0=20000,tag="(B) seed 5개")
print("\n(B) 복제당 seed 5개 중앙 — 80회")
print("    귀무 중앙 %+.1f · 95%% 분위 %+.1f · p = %.3f" % (m5,p95_5,pv5))
