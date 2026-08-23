import json, math, random, statistics
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/'
rows=json.load(open(SP+'daytab.json',encoding='utf-8'))
big=[r for r in rows if r['n']>=4]
big.sort(key=lambda r:r['date'])
FEATS=['r_up','r_dist_ma20','r_ret1','r_ret3','r_ret5','r_ret10','r_ret20','r_up_streak','r_down_streak',
 'r_ma20_slope5','r_dist_days25','r_off_hi25','b_adv_pct','b_up3_pct','b_dn3_pct','b_a20','b_a50','b_a200',
 'b_nh_pct','b_nl_pct','b_adv5','b_adv10','b_a20_chg5','b_a50_chg5','n_cand','n_eval',
 'last3_wins','last4_wins','last5_wins','last8_wins','last10_wins']
def rank(v):
    idx=sorted(range(len(v)),key=lambda i:v[i])
    r=[0.0]*len(v); i=0
    while i<len(idx):
        j=i
        while j+1<len(idx) and v[idx[j+1]]==v[idx[i]]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): r[idx[k]]=avg
        i=j+1
    return r
def spearman(x,y):
    rx,ry=rank(x),rank(y)
    n=len(x); mx=sum(rx)/n; my=sum(ry)/n
    num=sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    dx=math.sqrt(sum((a-mx)**2 for a in rx)); dy=math.sqrt(sum((b-my)**2 for b in ry))
    return num/(dx*dy) if dx and dy else 0.0

wr=[r['w']/r['n'] for r in big]
zero=[1 if r['w']==0 else 0 for r in big]
print(f"대상 {len(big)}일 (전멸 {sum(zero)}일)\n")
print(f"{'요인':<16}{'유효일':>5}{'ρ(승률)':>9}{'전멸일평균':>11}{'정상일평균':>11}{'AUC':>7}")
res={}
for f in FEATS:
    idx=[i for i,r in enumerate(big) if r.get(f) is not None]
    if len(idx)<40: 
        print(f"{f:<16}{len(idx):>5}  (유효일 부족, 제외)"); continue
    x=[big[i][f] for i in idx]; y=[wr[i] for i in idx]; z=[zero[i] for i in idx]
    rho=spearman(x,y)
    a=[x[i] for i in range(len(idx)) if z[i]==1]; b=[x[i] for i in range(len(idx)) if z[i]==0]
    # AUC (prob random wipeout-day feature > random normal-day)
    rx=rank(x); ra=sum(rx[i] for i in range(len(idx)) if z[i]==1)
    na,nb=len(a),len(b)
    auc=(ra-na*(na+1)/2)/(na*nb) if na and nb else float('nan')
    res[f]=dict(idx=idx,x=x,rho=rho,auc=auc,na=na,nb=nb)
    print(f"{f:<16}{len(idx):>5}{rho:>9.3f}{statistics.mean(a):>11.2f}{statistics.mean(b):>11.2f}{auc:>7.3f}")
json.dump({k:{'rho':v['rho'],'auc':v['auc']} for k,v in res.items()},open(SP+'p1raw.json','w'))
