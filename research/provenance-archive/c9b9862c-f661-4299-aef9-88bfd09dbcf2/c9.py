import json,os,collections,random
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
LAB={"1":"① 150·200일선","2":"② 150>200","3":"③ 200일선상승","4":"④ 50일선정렬","5":"⑤ 50일선","6":"⑥ 52주저가","7":"⑦ 52주고가","8":"⑧ RS"}
H=[r for r in rows if r.get('h10')]
for r in H:
    o=r['h10']['out']; r['is_stop']=1 if o=='stop' else 0
    r['rule_ret']=-10.0 if o=='stop' else (20.0 if o=='target' else r['h10']['ret'])
print('=== 날짜별 손절률(시장 국면 확인) ===')
byd=collections.defaultdict(list)
for r in H: byd[r['date']].append(r)
for d in sorted(byd):
    rs=byd[d]; print(f"  {d} n={len(rs):>3} 손절률 {100*sum(r['is_stop'] for r in rs)/len(rs):>5.1f}%")
print()
print('=== 3b) 날짜 내(within-date) 비교: 그날 중앙값 위 vs 아래 손절률 ===')
print(f"{'조건':<14}{'상위n':>6}{'상위손절':>9}{'하위n':>6}{'하위손절':>9}{'차(상-하)':>10}{'날짜중 상위>하위':>16}")
for k in ['pct_'+x for x in '12345678']+['gm_score']:
    hi=[];lo=[];win=0;tot=0
    for d,rs in byd.items():
        if len(rs)<4: continue
        v=sorted(r[k] for r in rs); med=v[len(v)//2]
        a=[r for r in rs if r[k]>med]; b=[r for r in rs if r[k]<=med]
        if not a or not b: continue
        hi+=a; lo+=b; tot+=1
        if sum(r['is_stop'] for r in a)/len(a) > sum(r['is_stop'] for r in b)/len(b): win+=1
    if not hi or not lo: print(k,'skip'); continue
    sa=100*sum(r['is_stop'] for r in hi)/len(hi); sb=100*sum(r['is_stop'] for r in lo)/len(lo)
    name=LAB.get(k[-1],'종합(min)') if k.startswith('pct_') else '종합(min)'
    print(f"{name:<14}{len(hi):>6}{sa:>9.1f}{len(lo):>6}{sb:>9.1f}{sa-sb:>10.1f}{f'{win}/{tot}':>16}")
print()
print('=== 조건 간 상관(피어슨, pct) ===')
import math
def corr(a,b):
    ma=sum(a)/len(a); mb=sum(b)/len(b)
    num=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    da=math.sqrt(sum((x-ma)**2 for x in a)); db=math.sqrt(sum((y-mb)**2 for y in b))
    return num/(da*db) if da and db else 0
ks='12345678'
print('    '+''.join(f'{k:>7}' for k in ks))
for i in ks:
    print(f'  {i} '+''.join(f'{corr([r["pct_"+i] for r in H],[r["pct_"+j] for r in H]):>7.2f}' for j in ks))
