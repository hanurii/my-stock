# -*- coding: utf-8 -*-
"""08 독립 재현 — P(승 | max_gain >= 8) 및 부가 수치."""
import json, glob, collections, statistics as st, random, math
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
ev=[]
for f in sorted(glob.glob(BT+r"\bt_*.json")): ev+=json.load(open(f,encoding='utf-8'))['events']
seen,U=set(),[]
for e in sorted(ev,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
R=[e for e in U if e['result'] in ('win','loss')]
W=[e for e in R if e['result']=='win']; L=[e for e in R if e['result']=='loss']
L8=[e for e in L if e['max_gain_pct']>=8]
print("확정 %d · 승 %d · 패 %d" % (len(R),len(W),len(L)))
print("[주 지표] 분모 %d (승 %d + max_gain>=8 인 패 %d) · P = %.2f%%   (파일 2,080 / 1,309 / 771 / 62.93)"
      % (len(W)+len(L8), len(W), len(L8), 100*len(W)/(len(W)+len(L8))))
# Wilson
n=len(W)+len(L8); p=len(W)/n; z=1.96
den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
print("   Wilson 95%% = %.2f ~ %.2f (폭 %.1f%%p)  (파일 폭 4.2)" % (100*(c-h),100*(c+h),100*2*h))
# 블록 부트스트랩 (날 단위)
pool=W+L8
byday=collections.defaultdict(list)
for e in pool: byday[e['entry_date']].append(e)
days=sorted(byday)
rnd=random.Random(80000); out=[]
for _ in range(1000):
    s=[]
    while len(s)<len(days):
        Lb=rnd.randint(20,40); a=rnd.randint(0,max(0,len(days)-Lb)); s+=days[a:a+Lb]
    s=s[:len(days)]
    v=[x for d in s for x in byday[d]]
    out.append(100*sum(1 for x in v if x['result']=='win')/len(v))
out.sort()
print("   블록 부트스트랩 95%% = %.2f ~ %.2f (폭 %.1f%%p)  (파일 59.62 ~ 66.08 / 6.5)"
      % (out[25],out[975],out[975]-out[25]))
print("\n[구간별] (entry_date 연도 → 다섯 구간)")
def seg(d):
    y=d[:4]; return y if y in ('2021','2022','2023','2024') else '2025~26'
g=collections.defaultdict(list)
for e in pool: g[seg(e['entry_date'])].append(e)
for k in sorted(g):
    v=g[k]; w=sum(1 for x in v if x['result']=='win'); n2=len(v); pp=w/n2
    den2=1+z*z/n2; c2=(pp+z*z/(2*n2))/den2; h2=z*math.sqrt(pp*(1-pp)/n2+z*z/(4*n2*n2))/den2
    print("   %-8s n=%4d  점추정 %.2f%%  Wilson 하한 %.2f%% %s"
          % (k,n2,100*pp,100*(c2-h2),"← 55% 미달" if 100*(c2-h2)<55 else ""))
print("\n[L2'] 한 해씩 제거 (파일 62.06 ~ 63.69)")
vals=[]
for y in ('2021','2022','2023','2024','2025','2026'):
    v=[e for e in pool if e['entry_date'][:4]!=y]
    vals.append(100*sum(1 for x in v if x['result']=='win')/len(v))
    print("   %s 제거 → %.2f%%" % (y, vals[-1]))
print("   범위 %.2f ~ %.2f" % (min(vals),max(vals)))
print("\n[L4] 한 종목·한 달이 분모의 5%% 넘는가")
mo=collections.Counter(e['entry_date'][:7] for e in pool)
cd=collections.Counter(e['code'] for e in pool)
tm=mo.most_common(1)[0]; tc=cd.most_common(1)[0]
print("   최대 월 %s %d건 = %.2f%% %s" % (tm[0],tm[1],100*tm[1]/len(pool),"← 초과" if 100*tm[1]/len(pool)>5 else ""))
print("   최대 종목 %s %d건 = %.2f%%" % (tc[0],tc[1],100*tc[1]/len(pool)))
print("\n[문턱 민감도]")
for t in (5,8,10,12,15):
    lt=[e for e in L if e['max_gain_pct']>=t]
    print("   >=%2d%%: 분모 %4d · P = %.2f%%" % (t,len(W)+len(lt),100*len(W)/(len(W)+len(lt))))
print("\n[뺏긴 771건] max_gain 분포")
mg=sorted(e['max_gain_pct'] for e in L8)
for t in (12,15):
    print("   +%d%%까지 갔다가 손절: %d건 (%.1f%%)" % (t,sum(1 for x in mg if x>=t),100*sum(1 for x in mg if x>=t)/len(mg)))
