import json,os,collections,random
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
LAB={"1":"① 150·200일선","2":"② 150>200","3":"③ 200일선상승","4":"④ 50일선정렬","5":"⑤ 50일선","6":"⑥ 52주저가","7":"⑦ 52주고가","8":"⑧ RS"}
H=[r for r in rows if r.get('h10')]
for r in H:
    o=r['h10']['out']; r['is_stop']=1 if o=='stop' else 0
    r['rule_ret']=-10.0 if o=='stop' else (20.0 if o=='target' else r['h10']['ret'])
print('=== pct 분포 (전체 350) ===')
for k in '12345678':
    v=sorted(r['pct_'+k] for r in H)
    q=lambda p: v[int(p*(len(v)-1))]
    cap=100*sum(1 for x in v if x>=100)/len(v)
    print(f"{LAB[k]:<14} min{v[0]:6.1f} p10{q(.1):6.1f} p25{q(.25):6.1f} 중앙{q(.5):6.1f} p75{q(.75):6.1f} p90{q(.9):6.1f} 100상한비율 {cap:5.1f}%")
print()
def auc_cluster(rs,key,B=2000,seed=3):
    # AUC of "lower pct -> stop"  (즉 pct 낮을수록 손절 확률 ↑ 이면 >0.5)
    pos=[r[key] for r in rs if r['is_stop']]; neg=[r[key] for r in rs if not r['is_stop']]
    if not pos or not neg: return None
    def a(p,ng):
        c=0; t=0
        for x in p:
            for y in ng:
                t+=1
                c+= 1 if x<y else (0.5 if x==y else 0)
        return c/t
    base=a(pos,neg)
    rnd=random.Random(seed)
    byc=collections.defaultdict(list)
    for r in rs: byc[r['code']].append(r)
    ks=list(byc); vals=[]
    for _ in range(B):
        samp=[x for kk in (rnd.choice(ks) for _ in ks) for x in byc[kk]]
        p=[r[key] for r in samp if r['is_stop']]; ng=[r[key] for r in samp if not r['is_stop']]
        if p and ng: vals.append(a(p,ng))
    vals.sort()
    return base, vals[int(.025*len(vals))], vals[int(.975*len(vals))]
print('=== 2) 조건별 pct 단독 판별력 (AUC: 0.5=무신호, >0.5 = 빡빡할수록 손절↑) ===')
res={}
for k in '12345678':
    out=auc_cluster(H,'pct_'+k)
    res[k]=out
    print(f"{LAB[k]:<14} AUC {out[0]:.3f}  종목클러스터95%CI[{out[1]:.3f},{out[2]:.3f}]")
out=auc_cluster(H,'gm_score'); print(f"{'종합(min)':<14} AUC {out[0]:.3f}  CI[{out[1]:.3f},{out[2]:.3f}]")
