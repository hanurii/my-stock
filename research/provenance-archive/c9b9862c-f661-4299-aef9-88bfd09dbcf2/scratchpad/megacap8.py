import json, os, glob, statistics, random
SP=r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad"
PD=r"C:/Users/hanul/playground/my-stock/.cache/pdata"
bt=json.load(open(r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json",encoding='utf-8'))
ev=bt['events']
pit=json.load(open(r'C:/Users/hanul/AppData/Local/Temp/pit_index.json',encoding='utf-8'))
upmap={d:u for d,u in zip(pit['dates'],pit['up'])}

files=sorted(glob.glob(os.path.join(PD,"price_*.json")))
dall=[os.path.basename(f)[6:14] for f in files]
sel=[(d,f) for d,f in zip(dall,files) if "20251126"<=d<="20260821"]
DATES=[d for d,_ in sel]; days=[json.load(open(f,encoding='utf-8')) for _,f in sel]
idx={d:i for i,d in enumerate(DATES)}
def path(code, ed):
    i=idx.get(ed.replace('-',''))
    if i is None: return []
    out=[];c=1.0
    for t in range(i+1,len(DATES)):
        v=days[t].get(code)
        if not v or v.get('fltRt') is None: continue
        c*=(1+v['fltRt']/100.0); out.append((c-1)*100)
    return out
def sim(p,stop=-10.0,tp=None,trail=None,arm=20.0):
    peak=0.0;armed=False
    for g in p:
        peak=max(peak,g)
        if tp is not None and g>=tp: return tp
        if trail is not None:
            if g>=arm: armed=True
            if armed and g<=peak-trail: return peak-trail
        if g<=stop: return stop
    return p[-1] if p else 0.0
def capof(code,date,_c={}):
    d=date.replace('-','')
    if d not in _c:
        pth=os.path.join(PD,f"price_{d}.json"); _c[d]=json.load(open(pth,encoding='utf-8')) if os.path.exists(pth) else {}
    return (_c[d].get(code) or {}).get('market_cap_eok') or 0

rows=[]
for e in ev:
    p=path(e['code'],e['entry_date'])
    rows.append(dict(e=e, cur=sim(p,stop=-10,tp=20), tr=sim(p,stop=-10,trail=15,arm=20),
                     up=upmap.get(e['entry_date']), cap=capof(e['code'],e['scan_date'])))
def m(xs): return sum(xs)/len(xs) if xs else 0.0

print("="*104); print("[검증 A] 국면별 — let-run 우위가 조정국면에도 남는가"); print("="*104)
print(f"{'국면':<12}{'n':>5}{'현행 +20/-10':>14}{'+20후 15%트레일':>16}{'차이%p':>9}")
for lab,f in (("상승국면",lambda r:r['up'] is True),("조정국면",lambda r:r['up'] is False)):
    s=[r for r in rows if f(r)]
    print(f"{lab:<12}{len(s):>5}{m([r['cur'] for r in s]):>+14.2f}{m([r['tr'] for r in s]):>+16.2f}{m([r['tr'] for r in s])-m([r['cur'] for r in s]):>+9.2f}")

print()
print("="*104); print("[검증 B] 집중도 — 상위 몇 건이 let-run 이득을 만드나 (이득 큰 순 제거)"); print("="*104)
gain=sorted(rows,key=lambda r:-(r['tr']-r['cur']))
base_c=m([r['cur'] for r in rows]); base_t=m([r['tr'] for r in rows])
print(f"{'제거':<16}{'n':>5}{'현행':>10}{'트레일':>10}{'차이%p':>9}")
for k in (0,1,3,5,10,20,40):
    s=gain[k:]
    print(f"{'상위 '+str(k)+'건 제거':<16}{len(s):>5}{m([r['cur'] for r in s]):>+10.2f}{m([r['tr'] for r in s]):>+10.2f}{m([r['tr'] for r in s])-m([r['cur'] for r in s]):>+9.2f}")
tot_diff=sum(r['tr']-r['cur'] for r in rows)
print(f"\n총 이득 {tot_diff:.0f}%p 중 상위 5건이 {sum(r['tr']-r['cur'] for r in gain[:5])/tot_diff*100:.0f}%, 상위 10건이 {sum(r['tr']-r['cur'] for r in gain[:10])/tot_diff*100:.0f}%")
print("  상위 5건:", ", ".join(f"{r['e']['name']}({r['tr']-r['cur']:+.0f}%p)" for r in gain[:5]))

print()
print("="*104); print("[검증 C] 같은날 짝비교 (같은 entry_date 안에서만 비교) + 부호검정"); print("="*104)
byd={}
for r in rows: byd.setdefault(r['e']['entry_date'],[]).append(r)
d_c=[];d_t=[]
for d,s in byd.items():
    d_c.append(m([r['cur'] for r in s])); d_t.append(m([r['tr'] for r in s]))
diffs=[t-c for t,c in zip(d_t,d_c)]
pos=sum(1 for x in diffs if x>0); neg=sum(1 for x in diffs if x<0); zer=sum(1 for x in diffs if x==0)
print(f"진입일 {len(byd)}일: 트레일 우세 {pos}일 / 열세 {neg}일 / 동일 {zer}일, 일평균차 {m(diffs):+.2f}%p, 중앙차 {statistics.median(diffs):+.2f}%p")
# sign test p-value (binomial, two-sided) via normal approx + exact for small
from math import comb
n=pos+neg; k=min(pos,neg)
p=sum(comb(n,i) for i in range(0,k+1))/2**n*2 if n<=1000 else None
print(f"부호검정 n={n}, p={p:.4g}" if p is not None else "")

print()
print("="*104); print("[검증 D] 월별 — 특정 몇 달에 몰렸는가"); print("="*104)
bym={}
for r in rows: bym.setdefault(r['e']['month'],[]).append(r)
print(f"{'월':<10}{'n':>5}{'현행':>10}{'트레일':>10}{'차이%p':>9}")
for mo in sorted(bym):
    s=bym[mo]; print(f"{mo:<10}{len(s):>5}{m([r['cur'] for r in s]):>+10.2f}{m([r['tr'] for r in s]):>+10.2f}{m([r['tr'] for r in s])-m([r['cur'] for r in s]):>+9.2f}")
mo_pos=sum(1 for mo in bym if m([r['tr'] for r in bym[mo]])>m([r['cur'] for r in bym[mo]]))
print(f"\n트레일이 이긴 달: {mo_pos}/{len(bym)}")
