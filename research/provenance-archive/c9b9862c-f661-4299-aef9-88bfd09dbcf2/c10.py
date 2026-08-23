import json,os,collections,random,math
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
H=[r for r in rows if r.get('h10')]
for r in H:
    o=r['h10']['out']; r['is_stop']=1 if o=='stop' else 0
    r['rule_ret']=-10.0 if o=='stop' else (20.0 if o=='target' else r['h10']['ret'])
    p={k:r['pct_'+k] for k in '12345678'}
    v=sorted(p.values())
    r['S_min']=v[0]
    r['S_low2']=(v[0]+v[1])/2
    r['S_mean']=sum(v)/8
    r['S_7']=p['7']
    r['S_min78']=min(p['7'],p['8'])
    r['S_min7_5']=min(p['7'],p['5'])
    r['S_min_struct']=min(p['1'],p['2'],p['3'],p['4'])
    r['S_min_1234_7']=min(p['1'],p['2'],p['3'],p['4'],p['7'])
    r['S_7minus_ext']=p['7']-(p['6']+p['8'])/2
def auc(rs,key,B=2000,seed=11):
    pos=[r[key] for r in rs if r['is_stop']]; neg=[r[key] for r in rs if not r['is_stop']]
    def a(p,ng):
        c=0;t=0
        for x in p:
            for y in ng:
                t+=1; c+= 1 if x<y else (0.5 if x==y else 0)
        return c/t
    base=a(pos,neg)
    rnd=random.Random(seed); byc=collections.defaultdict(list)
    for r in rs: byc[r['code']].append(r)
    ks=list(byc); vals=[]
    for _ in range(B):
        samp=[x for kk in (rnd.choice(ks) for _ in ks) for x in byc[kk]]
        p=[r[key] for r in samp if r['is_stop']]; ng=[r[key] for r in samp if not r['is_stop']]
        if p and ng: vals.append(a(p,ng))
    vals.sort(); return base, vals[int(.025*len(vals))], vals[int(.975*len(vals))]
byd=collections.defaultdict(list)
for r in H: byd[r['date']].append(r)
def within(key):
    hi=[];lo=[]
    for d,rs in byd.items():
        if len(rs)<4: continue
        v=sorted(r[key] for r in rs); med=v[len(v)//2]
        a=[r for r in rs if r[key]>med]; b=[r for r in rs if r[key]<=med]
        if a and b: hi+=a; lo+=b
    sa=100*sum(r['is_stop'] for r in hi)/len(hi); sb=100*sum(r['is_stop'] for r in lo)/len(lo)
    ra=sum(r['rule_ret'] for r in hi)/len(hi); rb=sum(r['rule_ret'] for r in lo)/len(lo)
    return sa,sb,sa-sb,ra,rb,ra-rb
def terc(key):
    v=sorted(H,key=lambda r:r[key]); n=len(v); a=v[:n//3]; c=v[-(n//3):]
    f=lambda g:(100*sum(r['is_stop'] for r in g)/len(g), sum(r['rule_ret'] for r in g)/len(g))
    return f(a),f(c)
names={'S_min':'현행 min(8조건)','S_low2':'하위2개 평균','S_mean':'8개 평균','S_7':'⑦ 단독',
 'S_min78':'min(⑦,⑧)','S_min7_5':'min(⑦,⑤)','S_min_struct':'min(①②③④)','S_min_1234_7':'min(①②③④⑦)',
 'S_7minus_ext':'⑦ - (⑥⑧평균)'}
print('=== 4) 종합점수 대안 비교 (10일창 n=%d, 종목 %d) ==='%(len(H),len({r['code'] for r in H})))
print(f"{'방식':<18}{'AUC':>7}{'95%CI':>16}{'날짜내 상위-하위 손절차':>22}{'규칙수익차':>11}{'하위1/3손절':>11}{'상위1/3손절':>11}")
for k,nm in names.items():
    a=auc(H,k); w=within(k); (sa,ra),(sc,rc)=terc(k)
    print(f"{nm:<18}{a[0]:>7.3f}  [{a[1]:.3f},{a[2]:.3f}]{w[2]:>20.1f}%p{w[5]:>10.2f}%p{sa:>10.1f}%{sc:>10.1f}%")
