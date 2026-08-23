import json, math, random
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/'
rows=json.load(open(SP+'daytab.json',encoding='utf-8'))
big=[r for r in rows if r['n']>=4]
N=sum(r['n'] for r in big); W=sum(r['w'] for r in big)
p=W/N
print(f"4건+ 진입일 {len(big)}일, 거래 {N}건, 승 {W}건, 승률 {100*p:.1f}%")
# observed wipeouts
obs0=sum(1 for r in big if r['w']==0); obsAll=sum(1 for r in big if r['w']==r['n'])
print('관측 전멸일',obs0,'전승일',obsAll)
# expected under independence with common p
exp0=sum((1-p)**r['n'] for r in big); expAll=sum(p**r['n'] for r in big)
print(f"독립가정 기대 전멸일 {exp0:.2f} ({100*exp0/len(big):.1f}%), 전승 {expAll:.2f}")
# variance test (overdispersion / ICC)
# Pearson chi2 for binomial homogeneity
chi=sum((r['w']-r['n']*p)**2/(r['n']*p*(1-p)) for r in big)
df=len(big)-1
print(f"과분산 chi2={chi:.1f} df={df} ratio={chi/df:.3f}")
# ICC estimate (Fleiss kappa-like) : rho from chi2
nbar=N/len(big)
rho=(chi/df-1)/(nbar-1)
print(f"평균 n={nbar:.2f}, 같은날 상관 rho≈{rho:.4f}")
# variance of daily win rate observed vs independent expectation
import statistics
wr=[r['w']/r['n'] for r in big]
varobs=statistics.pvariance(wr)
varind=sum(p*(1-p)/r['n'] for r in big)/len(big)
print(f"그날 승률 분산: 관측 {varobs:.4f}, 독립가정 {varind:.4f}, 배수 {varobs/varind:.2f}")
# beta-binomial MLE
def bb_ll(a,b):
    s=0
    for r in big:
        n,k=r['n'],r['w']
        s+= math.lgamma(a+k)+math.lgamma(b+n-k)-math.lgamma(a+b+n) - (math.lgamma(a)+math.lgamma(b)-math.lgamma(a+b))
    return s
best=None
for m in [x/200 for x in range(10,120)]:
    for s in [0.5,1,1.5,2,3,4,5,6,8,10,15,20,30,50,100]:
        a=m*s; b=(1-m)*s
        if a<=0 or b<=0: continue
        ll=bb_ll(a,b)
        if best is None or ll>best[0]: best=(ll,m,s,a,b)
ll,m,s,a,b=best
rho_bb=1/(s+1)
print(f"베타이항 MLE: 평균 {100*m:.1f}%, 집중도 s={s}, rho={rho_bb:.3f}, logL={ll:.2f}")
# predicted wipeout under beta-binomial
def bb_p0(n,a,b):
    return math.exp(math.lgamma(a+b)-math.lgamma(b)+math.lgamma(b+n)-math.lgamma(a+b+n))
pred0=sum(bb_p0(r['n'],a,b) for r in big)
def bb_pall(n,a,b):
    return math.exp(math.lgamma(a+b)-math.lgamma(a)+math.lgamma(a+n)-math.lgamma(a+b+n))
predAll=sum(bb_pall(r['n'],a,b) for r in big)
print(f"베타이항 기대 전멸일 {pred0:.2f}, 전승일 {predAll:.2f}")
# LRT vs binomial
ll0=sum(r['w']*math.log(p)+(r['n']-r['w'])*math.log(1-p) for r in big)
print(f"이항 logL={ll0:.2f}  LRT={2*(ll-ll0):.2f} (df=1)")
# simulation p-value for wipeout count under independence
random.seed(7)
cnt=0; B=20000
for _ in range(B):
    z=sum(1 for r in big if sum(1 for _ in range(r['n']) if random.random()<p)==0)
    if z>=obs0: cnt+=1
print(f"독립 시뮬 P(전멸일>={obs0}) = {cnt/B:.5f}")
# decomposition: how much explained by regime(up/down)
for lab,sel in (('상승국면',lambda r:r['r_up']==1),('조정국면',lambda r:r['r_up']==0)):
    g=[r for r in big if sel(r)]
    if not g: continue
    n=sum(r['n'] for r in g); w=sum(r['w'] for r in g)
    z=sum(1 for r in g if r['w']==0)
    e=sum((1-w/n)**r['n'] for r in g)
    print(f"  {lab}: {len(g)}일 승률 {100*w/n:.1f}% 전멸 {z}일 (그 국면 승률로 독립기대 {e:.1f}일)")
