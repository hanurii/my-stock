import json, glob, os, random, collections, statistics as st, bisect as bi
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
EV=[]
for f in sorted(glob.glob(B+'bt_*.json')):
    EV += [e for e in json.load(open(f,encoding='utf-8'))['events'] if e['result'] in ('win','loss')]
seen=set(); U=[]
for e in sorted(EV,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
EV=U
REG=json.load(open(B+'regime_long.json',encoding='utf-8'))
UP={d:u for d,u in zip(REG['dates'],REG['up_ew20'])}
KOS={d:v for d,v in zip(REG['dates'],REG['kospi'])}
NQ=json.load(open(B+'nasdaq.json',encoding='utf-8')); nqd=sorted(NQ['close'])
def nqlab(d):
    i=bi.bisect_left(nqd,d)-1
    return bool(NQ['up'][nqd[i]])
for e in EV: e['nq']=nqlab(e['entry_date'])
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
def sim(events, slots=5, seed=0, filt=None):
    pool=[e for e in events if (filt is None or filt(e))]
    byday=collections.defaultdict(list)
    for e in pool: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]; n=0; w=0
    alld=sorted(set(list(byday)+[e['resolve_date'] for e in pool]))
    for d in alld:
        for rd,e,wg in [h for h in held if h[0]<=d]:
            eq += wg*FEE(e['gain_at_resolve_pct'])/100; n+=1; w+= e['result']=='win'
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
    return (eq-1)*100, n
def band(f,N=200):
    r=[sim(EV,seed=i,filt=f) for i in range(N)]
    v=sorted(x[0] for x in r)
    return v[N//2], v[N//20], v[N-N//20], sorted(x[1] for x in r)[N//2]
rows=[('전부 매수',None),
      ('상승국면에만',lambda e: UP.get(e['scan_date']) is True),
      ('상승국면 + 나스닥상승',lambda e: UP.get(e['scan_date']) is True and e['nq']),
      ('상승국면 + 나스닥하락',lambda e: UP.get(e['scan_date']) is True and not e['nq']),
      ('나스닥 상승일만',lambda e: e['nq']),
      ('나스닥 하락일만',lambda e: not e['nq'])]
d0,d1=EV[0]['entry_date'],EV[-1]['resolve_date']
ks=(KOS[max(d for d in REG['dates'] if d<=d1)]/KOS[min(d for d in REG['dates'] if d>=d0)]-1)*100
print('기간 %s ~ %s  코스피 %+.1f%%'%(d0,d1,ks))
for lab,f in rows:
    m,lo,hi,n=band(f)
    print('%-24s 최종 %+8.1f%%  (5~95%%: %+.0f ~ %+.0f)  체결 %d건'%(lab,m,lo,hi,n))
