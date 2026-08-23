import json,os,collections,random,statistics as stx
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
LAB={"1":"① 150·200일선","2":"② 150>200","3":"③ 200일선상승","4":"④ 50일선정렬","5":"⑤ 50일선","6":"⑥ 52주저가","7":"⑦ 52주고가","8":"⑧ RS"}
H=[r for r in rows if r.get('h10')]
for r in H:
    o=r['h10']['out']
    r['rule_ret'] = -10.0 if o=='stop' else (20.0 if o=='target' else r['h10']['ret'])
    r['is_stop'] = 1 if o=='stop' else 0
def summ(rs):
    n=len(rs); s=sum(r['is_stop'] for r in rs)
    return n,100*s/n,sum(r['rule_ret'] for r in rs)/n
n,sr,rr=summ(H); print('전체 n=%d 손절률 %.1f%% 규칙적용수익 %.2f%%'%(n,sr,rr))
print()
print('=== 1c) tightest 별 규칙적용 수익 ===')
by=collections.defaultdict(list)
for r in H: by[r['tightest']].append(r)
for k in '12345678':
    rs=by.get(k)
    if not rs: continue
    n_,sr_,rr_=summ(rs)
    print(f"{LAB[k]:<14} n={n_:>3} 종목{len({r['code'] for r in rs}):>3}  손절률 {sr_:>5.1f}%  규칙수익 {rr_:>6.2f}%")

# 클러스터 부트스트랩(종목 단위 재표본) — ⑦ vs 나머지
def boot(groupA,groupB,B=4000,seed=7):
    rnd=random.Random(seed)
    ca=collections.defaultdict(list); cb=collections.defaultdict(list)
    for r in groupA: ca[r['code']].append(r)
    for r in groupB: cb[r['code']].append(r)
    ka=list(ca); kb=list(cb); diffs=[]
    for _ in range(B):
        sa=[x for k in (rnd.choice(ka) for _ in ka) for x in ca[k]]
        sb=[x for k in (rnd.choice(kb) for _ in kb) for x in cb[k]]
        diffs.append(100*sum(r['is_stop'] for r in sa)/len(sa)-100*sum(r['is_stop'] for r in sb)/len(sb))
    diffs.sort()
    return diffs[int(.025*B)],diffs[int(.975*B)],sum(1 for d in diffs if d<=0)/B
print()
for k in '12345678':
    A=by.get(k) or []
    if len(A)<6: continue
    B_=[r for r in H if r['tightest']!=k]
    lo,hi,p=boot(A,B_)
    d=100*sum(r['is_stop'] for r in A)/len(A)-100*sum(r['is_stop'] for r in B_)/len(B_)
    print(f"{LAB[k]:<14} 손절률차 {d:+6.1f}%p  95%CI[{lo:+6.1f},{hi:+6.1f}]  p(차<=0)={p:.3f}")
