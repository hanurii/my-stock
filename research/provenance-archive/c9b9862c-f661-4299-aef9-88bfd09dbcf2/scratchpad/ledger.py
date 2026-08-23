import json, sys, os, math, statistics as st
sys.path.insert(0, r'C:\Users\hanul\playground\my-stock\scripts')
os.chdir(r'C:\Users\hanul\playground\my-stock')
from canslim_lib.trend_template import compute_gate_margin
from collections import Counter
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
A = json.load(open(SP+r'\asof.json', encoding='utf-8')); byasof=A['byasof']; dates=sorted(byasof)
ld = json.load(open('public/data/sepa-buy-rec-ledger.json', encoding='utf-8'))
ents = ld['entries'] if isinstance(ld,dict) else ld
print('entries', len(ents)); print(json.dumps(ents[0], ensure_ascii=False))
def gm(asof, code):
    rec = byasof[asof]['recs'].get(code)
    if rec is None: return None
    return compute_gate_margin(rec, rec.get('current_price'), rec.get('rs'), rs_min=80)
def pick(code, d, strict=True):
    for x in reversed([z for z in dates if (z<d if strict else z<=d)]):
        m=gm(x,code)
        if m is not None: return x,m
    return None,None
out=[]
for e in ents:
    d,m = pick(e['code'], e['date'], True)
    r = e.get('resolved') or {}
    out.append(dict(code=e['code'], name=e.get('name'), date=e['date'], score=e.get('score'),
                    status=e.get('status'), gate_near=e.get('gate_near'),
                    sp=(m or {}).get('score'), tight=(m or {}).get('tightest'), asof=d,
                    outcome=r.get('outcome'), days=r.get('days'), maxg=r.get('max_gain_pct'), cur=r.get('cur_ret_pct')))
json.dump(out, open(SP+r'\myLedger.json','w',encoding='utf-8'), ensure_ascii=False)
print('matched sp', sum(1 for o in out if o['sp'] is not None), '/', len(out))
print('outcomes', Counter(o['outcome'] for o in out))
res=[o for o in out if o['outcome'] in ('target','stop') and o['sp'] is not None]
print('resolved w/ sp', len(res), Counter(o['outcome'] for o in res))
def mw(a,b):
    n1,n2=len(a),len(b); allv=sorted(a+b); ranks={}; i=0; tc=0.0
    while i<len(allv):
        j=i
        while j+1<len(allv) and allv[j+1]==allv[i]: j+=1
        rr=(i+1+j+1)/2.0
        for k in range(i,j+1): ranks.setdefault(allv[k],rr)
        t=j-i+1; tc+=t**3-t; i=j+1
    R1=sum(ranks[x] for x in a); U1=R1-n1*(n1+1)/2; auc=U1/(n1*n2); mu=n1*n2/2; N=n1+n2
    sd=math.sqrt(n1*n2/12*((N+1)-tc/(N*(N-1)))); z=(U1-mu-(0.5 if U1>mu else -0.5))/sd if sd>0 else 0
    p=2*(1-0.5*(1+math.erf(abs(z)/math.sqrt(2)))); return auc,z,p
T=[o['sp'] for o in res if o['outcome']=='target']; S=[o['sp'] for o in res if o['outcome']=='stop']
a,z,p=mw(T,S)
print(f'ledger target med {st.median(T):.1f} n={len(T)} | stop med {st.median(S):.1f} n={len(S)} AUC(target>stop)={a:.3f} z={z:.2f} p={p:.3f}')
for lo,hi in [(0,20),(20,40),(40,60),(60,80),(80,101)]:
    g=[o for o in res if lo<=o['sp']<hi]
    if g: print(f'  [{lo},{hi}) n={len(g):3d} target {sum(1 for o in g if o["outcome"]=="target")/len(g)*100:4.1f}%')
for c in [5,10,20,30,50]:
    lo=[o for o in res if o['sp']<c]; hi=[o for o in res if o['sp']>=c]
    if lo and hi:
        print(f'  cut{c}: <c n={len(lo)} target {sum(1 for o in lo if o["outcome"]=="target")/len(lo)*100:.0f}% | >=c n={len(hi)} target {sum(1 for o in hi if o["outcome"]=="target")/len(hi)*100:.0f}%')
# cur_ret by bin (all entries with sp and cur)
allc=[o for o in out if o['sp'] is not None and o['cur'] is not None]
print('with cur:', len(allc))
for lo,hi in [(0,20),(20,40),(40,60),(60,80),(80,101)]:
    g=[o for o in allc if lo<=o['sp']<hi]
    if g: print(f'  [{lo},{hi}) n={len(g):3d} mean cur {st.mean([o["cur"] for o in g]):+.2f}%  median {st.median([o["cur"] for o in g]):+.2f}%')
# sp==0 group in ledger
z0=[o for o in res if o['sp']==0]
print('ledger sp=0 resolved n=',len(z0),'target%',round(sum(1 for o in z0 if o['outcome']=='target')/len(z0)*100,1) if z0 else None,
      '| overall target%', round(sum(1 for o in res if o['outcome']=='target')/len(res)*100,1))
# July vs Aug split for ledger
for lbl,f in [('JUL', lambda o:o['date']<'2026-08-01'), ('AUG', lambda o:o['date']>='2026-08-01')]:
    sub=[o for o in res if f(o)]
    if len(sub)<10: continue
    T2=[o['sp'] for o in sub if o['outcome']=='target']; S2=[o['sp'] for o in sub if o['outcome']=='stop']
    a2,z2,p2=mw(T2,S2)
    print(f'  {lbl}: n={len(sub)} target={len(T2)} stop={len(S2)} AUC={a2:.3f} p={p2:.3f} | tgt med {st.median(T2):.1f} stop med {st.median(S2):.1f}')
    for lo,hi in [(0,20),(20,50),(50,101)]:
        g=[o for o in sub if lo<=o['sp']<hi]
        if g: print(f'     [{lo},{hi}) n={len(g):3d} target {sum(1 for o in g if o["outcome"]=="target")/len(g)*100:4.1f}%')
