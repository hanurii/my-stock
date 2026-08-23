# -*- coding: utf-8 -*-
import json,sys,random,collections,math,itertools
sys.stdout.reconfigure(encoding='utf-8')
D=json.load(open('public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[e for e in D['events'] if e['result'] in ('win','loss')]
BUCK=['<2천','2~5천','5~1만','1~2만','2~5만','5만+']; ORD={b:i for i,b in enumerate(BUCK)}
days=collections.defaultdict(list)
for e in ev: days[e['entry_date']].append(e)
usable=[d for d in sorted(days) if len(days[d])>=3]
w=lambda e:1 if e['result']=='win' else 0
def binom_two(k,n):
    if n==0: return 1.0
    pk=[math.comb(n,i)*0.5**n for i in range(n+1)]; obs=pk[k]
    return min(1.0,sum(p for p in pk if p<=obs*1.0000001))

print('== 버킷 서열 방식의 동점 무작위 처리 민감도 (seed 20개) ==')
tops=[];bots=[];signs=[]
for seed in range(20):
    rnd=random.Random(seed); tw=bw=0; pos=neg=0
    for d in usable:
        g=days[d]; k=sorted([(ORD[e['price_bucket']],rnd.random(),e) for e in g],key=lambda x:(x[0],x[1]))
        t=sum(w(x[2]) for x in k[-2:]); b=sum(w(x[2]) for x in k[:2])
        exp=2*sum(w(e) for e in g)/len(g)
        tw+=t; bw+=b
        if t>exp: pos+=1
        elif t<exp: neg+=1
    tops.append(tw/(2*len(usable))); bots.append(bw/(2*len(usable))); signs.append(binom_two(pos,pos+neg))
print(' TOP2 승률 범위 %.3f~%.3f (평균 %.3f)'%(min(tops),max(tops),sum(tops)/len(tops)))
print(' BOT2 승률 범위 %.3f~%.3f (평균 %.3f)'%(min(bots),max(bots),sum(bots)/len(bots)))
print(' 부호검정 p 범위 %.3f~%.3f (평균 %.3f), p<0.05인 seed %d/20'%(min(signs),max(signs),sum(signs)/len(signs),sum(1 for p in signs if p<0.05)))

print('\n== TOP2 vs BOT2 직접 짝비교 (entry_price 연속값, 같은날) ==')
pos=neg=0; dt=0; db=0
for d in usable:
    g=sorted(days[d],key=lambda e:e['entry_price'])
    t=sum(w(e) for e in g[-2:]); b=sum(w(e) for e in g[:2]); dt+=t; db+=b
    if t>b: pos+=1
    elif t<b: neg+=1
print(' TOP2 총승 %d/%d=%.1f%%  BOT2 총승 %d/%d=%.1f%%'%(dt,2*len(usable),100*dt/(2*len(usable)),db,2*len(usable),100*db/(2*len(usable))))
print(' 날짜별 부호: TOP우세 %d / BOT우세 %d / 동률 %d  p=%.4f'%(pos,neg,len(usable)-pos-neg,binom_two(pos,pos+neg)))

print('\n== 같은날 짝비교: 저가주 관점 (싼 쪽이 이김) ==')
tot=agree=0
for d in usable:
    for a,b2 in itertools.combinations(days[d],2):
        if a['result']==b2['result'] or a['entry_price']==b2['entry_price']: continue
        tot+=1
        lo=a if a['entry_price']<b2['entry_price'] else b2
        if lo['result']=='win': agree+=1
print(' 승/패 짝 %d  싼쪽승 %d = %.1f%%  p=%.4f'%(tot,agree,100*agree/tot,binom_two(min(agree,tot-agree),tot)))

print('\n== 버킷 단위 같은날 짝비교 (다른 버킷끼리만) ==')
tot=agree=0
for d in usable:
    for a,b2 in itertools.combinations(days[d],2):
        if a['result']==b2['result']: continue
        if ORD[a['price_bucket']]==ORD[b2['price_bucket']]: continue
        tot+=1
        hi=a if ORD[a['price_bucket']]>ORD[b2['price_bucket']] else b2
        if hi['result']=='win': agree+=1
print(' 승/패 짝 %d  비싼버킷승 %d = %.1f%%  p=%.4f'%(tot,agree,100*agree/tot,binom_two(min(agree,tot-agree),tot)))

print('\n== 같은날 상대순위(백분위)별 승률 — 연속 형태 확인 ==')
bins=collections.defaultdict(lambda:[0,0])
for d in usable:
    g=sorted(days[d],key=lambda e:e['entry_price']); n=len(g)
    for i,e in enumerate(g):
        q=int(( (i+0.5)/n )*4); q=min(q,3)
        bins[q][0]+=w(e); bins[q][1]+=1
for q in range(4):
    ww,nn=bins[q]; print('  Q%d(저가→고가) n=%3d 승률 %.1f%%'%(q+1,nn,100*ww/nn))

print('\n== 최소 표본 검토: 검출력 ==')
n=2*len(usable)
print(' 픽 %d개, 기저승률 %.3f → 승률 차이 표준오차 약 %.3f (한쪽) '%(n,0.3935,(0.3935*0.6065/n)**0.5))
print(' 즉 대략 %.1f%%p 이상 차이나야 유의 감지 가능(80%% 검출력 근사)'%(100*2.8*(0.3935*0.6065/n)**0.5))
