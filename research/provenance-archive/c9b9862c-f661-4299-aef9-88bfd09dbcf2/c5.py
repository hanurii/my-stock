import json,os,collections
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
LAB={"1":"① 150·200일선","2":"② 150>200","3":"③ 200일선상승","4":"④ 50일선정렬","5":"⑤ 50일선","6":"⑥ 52주저가","7":"⑦ 52주고가","8":"⑧ RS"}
H=[r for r in rows if r.get('h10')]
print('10일 고정창 표본 n=%d, 종목 %d'%(len(H),len({r['code'] for r in H})))
def st(rs):
    n=len(rs); s=sum(1 for r in rs if r['h10']['out']=='stop'); t=sum(1 for r in rs if r['h10']['out']=='target')
    ret=sum(r['h10']['ret'] for r in rs)/n; mfe=sum(r['h10']['mfe'] for r in rs)/n
    return n,s,t,100*s/n,100*t/n,ret,mfe
n,s,t,sr,tr,ret,mfe=st(H)
print('전체: n=%d 손절%d(%.1f%%) +20%%%d(%.1f%%) 10일수익 %.2f%% MFE %.2f%%'%(n,s,sr,t,tr,ret,mfe))
print()
print('=== 1) tightest 별 (10일 고정창) ===')
print(f"{'조건':<14}{'n':>4}{'종목':>5}{'손절':>5}{'손절률':>8}{'+20%':>6}{'도달률':>8}{'10일수익':>9}{'MFE':>7}")
by=collections.defaultdict(list)
for r in H: by[r['tightest']].append(r)
for k in '12345678':
    rs=by.get(k)
    if not rs: continue
    n,s,t,sr,tr,ret,mfe=st(rs)
    print(f"{LAB[k]:<14}{n:>4}{len({r['code'] for r in rs}):>5}{s:>5}{sr:>8.1f}{t:>6}{tr:>8.1f}{ret:>9.2f}{mfe:>7.2f}")
print()
print('=== 1b) 같은 표를 종목단위(코드별 평균 후 코드 가중 1) ===')
print(f"{'조건':<14}{'종목수':>6}{'평균손절확률':>12}{'평균10일수익':>12}")
for k in '12345678':
    rs=by.get(k)
    if not rs: continue
    bc=collections.defaultdict(list)
    for r in rs: bc[r['code']].append(r)
    sr=[sum(1 for x in v if x['h10']['out']=='stop')/len(v) for v in bc.values()]
    rr=[sum(x['h10']['ret'] for x in v)/len(v) for v in bc.values()]
    print(f"{LAB[k]:<14}{len(bc):>6}{100*sum(sr)/len(sr):>12.1f}{sum(rr)/len(rr):>12.2f}")
