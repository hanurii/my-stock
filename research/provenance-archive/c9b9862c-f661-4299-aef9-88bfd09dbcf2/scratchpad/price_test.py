# -*- coding: utf-8 -*-
import json, sys, random, collections, math
io = sys.stdout
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

D = json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json', encoding='utf-8'))
ev = [e for e in D['events'] if e['result'] in ('win','loss')]
print('resolved events (win/loss only):', len(ev),
      ' win:', sum(1 for e in ev if e['result']=='win'),
      ' loss:', sum(1 for e in ev if e['result']=='loss'))

# bucket ordinal (low price -> high price)
BUCKETS = ['<2천','2~5천','5~1만','1~2만','2~5만','5만+']
seen = collections.Counter(e['price_bucket'] for e in ev)
print('buckets present:', dict(seen))
ORD = {b:i for i,b in enumerate(BUCKETS)}
missing = [b for b in seen if b not in ORD]
if missing:
    print('!! unknown bucket labels:', missing); sys.exit(1)

# group by entry_date
days = collections.defaultdict(list)
for e in ev:
    days[e['entry_date']].append(e)
alld = sorted(days)
usable = [d for d in alld if len(days[d]) >= 3]
print('all entry_dates:', len(alld), ' dates with >=3 candidates:', len(usable),
      ' events on those dates:', sum(len(days[d]) for d in usable))
print('cand/day dist on usable days:', dict(collections.Counter(len(days[d]) for d in usable)))

def w(e): return 1 if e['result']=='win' else 0

def run(name, keyfn, reps=2000, seed=12345):
    """keyfn(e) -> numeric score; TOP = highest score. Ties broken randomly, averaged over reps."""
    rnd = random.Random(seed)
    ndays = len(usable)
    top_hits=[]; bot_hits=[]; rnd_hits=[]
    per_day_top=[]; per_day_bot=[]; per_day_exp=[]
    for r in range(reps):
        t=b=rr=0
        for d in usable:
            g = days[d]
            keyed = [(keyfn(e), rnd.random(), e) for e in g]
            keyed.sort(key=lambda x:(x[0], x[1]))
            lo = keyed[:2]; hi = keyed[-2:]
            tw = sum(w(x[2]) for x in hi); bw = sum(w(x[2]) for x in lo)
            pick = rnd.sample(g,2); pw = sum(w(e) for e in pick)
            t+=tw; b+=bw; rr+=pw
            if r==0:
                per_day_top.append(tw); per_day_bot.append(bw)
                per_day_exp.append(2*sum(w(e) for e in g)/len(g))
        top_hits.append(t/(2*ndays)); bot_hits.append(b/(2*ndays)); rnd_hits.append(rr/(2*ndays))
    top = sum(top_hits)/reps; bot = sum(bot_hits)/reps
    exp = sum(per_day_exp)/(2*ndays)   # analytic expectation of a random 2-pick
    rndmean = sum(rnd_hits)/reps
    # bootstrap p: how often does a random 2-pick beat (or tie) the observed top2 / bottom2
    p_top_hi = (sum(1 for x in rnd_hits if x>=top)+1)/(reps+1)
    p_top_lo = (sum(1 for x in rnd_hits if x<=top)+1)/(reps+1)
    p_top = min(1.0, 2*min(p_top_hi,p_top_lo))
    p_bot_hi = (sum(1 for x in rnd_hits if x>=bot)+1)/(reps+1)
    p_bot_lo = (sum(1 for x in rnd_hits if x<=bot)+1)/(reps+1)
    p_bot = min(1.0, 2*min(p_bot_hi,p_bot_lo))
    # sign test on per-day diffs (rep 0 realization, ties randomized once)
    pos = sum(1 for a,b2 in zip(per_day_top,per_day_exp) if a> b2)
    neg = sum(1 for a,b2 in zip(per_day_top,per_day_exp) if a< b2)
    n = pos+neg
    def binom_two(k,n):
        if n==0: return 1.0
        c=lambda n,k: math.comb(n,k)
        pk=[c(n,i)*0.5**n for i in range(n+1)]
        obs=pk[k]; return min(1.0, sum(p for p in pk if p<=obs*1.0000001))
    p_sign = binom_two(pos,n)
    posb = sum(1 for a,b2 in zip(per_day_bot,per_day_exp) if a> b2)
    negb = sum(1 for a,b2 in zip(per_day_bot,per_day_exp) if a< b2)
    p_signb = binom_two(posb, posb+negb)
    print('\n=== %s ===' % name)
    print(' days used: %d   picks: %d (2/day)' % (ndays, 2*ndays))
    print(' TOP2 (고가주) winrate : %.4f  (%.1f%%)' % (top, 100*top))
    print(' RANDOM2      winrate : %.4f  (%.1f%%)  [analytic %.4f, bootstrap mean %.4f, sd %.4f]'
          % (rndmean, 100*rndmean, exp, rndmean,
             (sum((x-rndmean)**2 for x in rnd_hits)/reps)**0.5))
    print(' BOT2  (저가주) winrate : %.4f  (%.1f%%)' % (bot, 100*bot))
    print(' bootstrap p (top2 vs random, 2-sided, %d reps): %.4f' % (reps,p_top))
    print(' bootstrap p (bot2 vs random, 2-sided): %.4f' % p_bot)
    print(' sign test TOP2 vs day-expectation: days better %d / worse %d / tie %d  p=%.4f'
          % (pos,neg,ndays-n,p_sign))
    print(' sign test BOT2 vs day-expectation: days better %d / worse %d / tie %d  p=%.4f'
          % (posb,negb,ndays-posb-negb,p_signb))
    print(' monotonic (top>random>bot)?', top>rndmean>bot, ' | reverse (bot>random>top)?', bot>rndmean>top)
    return dict(top=top,rnd=rndmean,bot=bot,p_top=p_top,p_bot=p_bot,p_sign=p_sign,
                p_signb=p_signb,ndays=ndays,npicks=2*ndays)

r_price = run('A. entry_price 연속값 기준 (TOP2=최고가 2종목, BOT2=최저가 2종목)', lambda e: e['entry_price'])
r_buck  = run('B. price_bucket 서열 기준 (동점 무작위, TOP2=고가버킷, BOT2=저가버킷)', lambda e: ORD[e['price_bucket']])

# --- descriptive: bucket-level pooled (calendar-illusion prone, for contrast only) ---
print('\n--- 참고: 전체 풀 버킷별 (같은날 비교 아님, 달력 착시 가능) ---')
for b in BUCKETS:
    sub=[e for e in ev if e['price_bucket']==b]
    if sub:
        wr=sum(w(e) for e in sub)/len(sub)
        print('  %-7s n=%3d  win=%3d  winrate=%.1f%%' % (b,len(sub),sum(w(e) for e in sub),100*wr))

# --- within-day rank correlation sanity check ---
print('\n--- 같은날 내 순위 vs 결과 (전체 dates>=3) ---')
tot=0; agree=0
import itertools
for d in usable:
    g=days[d]
    for a,b2 in itertools.combinations(g,2):
        if a['result']==b2['result']: continue
        if a['entry_price']==b2['entry_price']: continue
        tot+=1
        hi = a if a['entry_price']>b2['entry_price'] else b2
        if hi['result']=='win': agree+=1
print('  같은날 승/패 짝 %d개 중 "비싼 쪽이 이김" %d개 = %.1f%% (50%%면 무신호)' % (tot,agree,100*agree/tot))
pv = 0.0
from math import comb
k=min(agree,tot-agree)
pv = 2*sum(comb(tot,i)*0.5**tot for i in range(0,k+1))
print('  짝비교 이항검정 p=%.4f' % min(1.0,pv))

# --- median entry price per day check ---
print('\n--- 표본 규모 참고 ---')
print('  usable days=%d, picks=%d, 전체 resolved=%d' % (len(usable), 2*len(usable), len(ev)))
