# -*- coding: utf-8 -*-
"""15번 독립 검증 — 블록 부트스트랩 1,000회로 (변형2 − 현행) 차이 분포."""
import json, collections, statistics as st, random, sys, os
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
SAVE = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\6169d0c4-0281-4b63-96b9-ea3ec7e90cf4\scratchpad\v15_partial.json"
net = slot_sim.net
paths=[]; cal=set()
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        paths.append({'code':p['code'],'pat':p['pattern'],'sd':p['scan_date'],'ed':p['entry_date'],
                      'E':p['entry_price'],'o':p['o'],'h':p['h'],'l':p['l'],'c':p['c'],'dt':p['dates']})
        cal.update(p['dates'])
    del d
lo=min(p['ed'] for p in paths); hi=max(p['dt'][-1] for p in paths)
all_dates=sorted(x for x in cal if lo<=x<=hi); pos={d:i for i,d in enumerate(all_dates)}
n_pos=len(all_dates)

def resolve(p, day=None, thr=-5.0):
    E=p['E']; T=E*1.20; S=E*0.90; o,h,l,c=p['o'],p['h'],p['l'],p['c']; n=len(c)
    for i in range(n):
        ht,hs=h[i]>=T,l[i]<=S
        if ht and hs: return i,'loss',(c[i]/E-1)*100,'both'
        if ht: return i,'win',(c[i]/E-1)*100,'target'
        if hs: return i,'loss',(c[i]/E-1)*100,'stop'
        if day is not None and i==day and (c[i]/E-1)*100 <= thr:
            if i+1<n:
                g=(o[i+1]/E-1)*100; return i+1,('win' if g>0 else 'loss'),g,'signal'
            g=(c[i]/E-1)*100; return i,('win' if g>0 else 'loss'),g,'signal'
    g=(c[-1]/E-1)*100
    return n-1,('win' if g>0 else 'loss'),g,'last'

def mk(day):
    out=[]
    for p in paths:
        i,lb,g,rea=resolve(p,day)
        out.append({'code':p['code'],'pattern':p['pat'],'scan_date':p['sd'],'entry_date':p['ed'],
                    'gain':g,'result':lb,'days_held':i,'pos':pos[p['ed']],'reason':rea,
                    'base_gain':None})
    return out
B=mk(None); V2=mk(5)
for i,t in enumerate(V2): t['base_gain']=B[i]['gain']

def boot_sim(by_pos, seed, slots=5):
    eq=1.0; held=[]
    for p in range(n_pos):
        if held:
            for h in held:
                if not h[3] and h[0]<p: eq += h[2]*net(h[1]['gain'])/100; h[3]=True
            held=[h for h in held if h[0]>=p]
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

def idx_of(tr):
    d=collections.defaultdict(list)
    for t in tr: d[t['pos']].append(t)
    return d

def run(trA, trB, n_boot=1000, seed0=20000, n_seed=1, tag=""):
    ia, ib = idx_of(trA), idx_of(trB)
    rnd=random.Random(seed0); diffs=[]
    for b in range(n_boot):
        blocks=[]; tot=0
        while tot<n_pos:
            L=rnd.randint(20,40); a=rnd.randint(0,n_pos-L)
            blocks.append((a,min(L,n_pos-tot))); tot+=L
        def lay(ix):
            by=collections.defaultdict(list); off=0
            for a,L in blocks:
                for j in range(L):
                    for t in ix.get(a+j,()): by[off+j].append(t)
                off+=L
            return by
        ba, bb = lay(ia), lay(ib)
        if n_seed==1:
            diffs.append(boot_sim(ba,seed0)-boot_sim(bb,seed0))
        else:
            diffs.append(st.median(boot_sim(ba,seed0+s) for s in range(n_seed))
                         - st.median(boot_sim(bb,seed0+s) for s in range(n_seed)))
        if (b+1)%200==0:
            json.dump({'tag':tag,'n':b+1,'diffs':diffs}, open(SAVE,'w'))
            print("   %s %d/%d" % (tag,b+1,n_boot), flush=True)
    ds=sorted(diffs)
    return {'median':st.median(ds),'lo':ds[int(len(ds)*.025)],'hi':ds[int(len(ds)*.975)],
            'pos_pct':100*sum(1 for x in diffs if x>0)/len(diffs)}

r=run(V2,B,1000,20000,1,"주 판정")
print("\n[문턱1] 차이 중앙 %+.2f%%p · 95%% 구간 %+.2f ~ %+.2f · 양수 %.1f%%"
      % (r['median'],r['lo'],r['hi'],r['pos_pct']))
print("        결과 파일: +10.02 · -57.94 ~ +102.56 · 66.3%")
# 문턱 4 — 기여 상위 5건 양팔 제거
gain=[(net(V2[i]['gain'])-net(B[i]['gain']), i) for i in range(len(B))]
top5={i for _,i in sorted(gain,reverse=True)[:5]}
V2b=[t for i,t in enumerate(V2) if i not in top5]; Bb=[t for i,t in enumerate(B) if i not in top5]
r4=run(V2b,Bb,300,20000,1,"문턱4")
print("[문턱4] 상위5 제거 차이 중앙 %+.2f%%p · 95%% %+.2f ~ %+.2f  (결과파일 +8.41)"
      % (r4['median'],r4['lo'],r4['hi']))
