# -*- coding: utf-8 -*-
"""03번 독립 검증 — 1순위(날 단위) 재현 + k>=4판 직접 계산."""
import json, glob, collections, statistics as st, random
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
ev=[]
for f in sorted(glob.glob(BT+r"\bt_*.json")): ev+=json.load(open(f,encoding='utf-8'))['events']
seen,U=set(),[]
for e in sorted(ev,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
R=[e for e in U if e['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for e in R: byday[e['entry_date']].append(e)

def day_stats(kmin, seed=31000):
    rnd=random.Random(seed); out=[]
    for d in sorted(byday):
        v=byday[d]
        if len(v)<kmin: continue
        s=sorted(v,key=lambda e:-e['turnover_eok'])
        top=[net(x['gain_at_resolve_pct']) for x in s[:2]]
        bot=[net(x['gain_at_resolve_pct']) for x in s[-2:]]
        rd=rnd.sample(v,2); rr=[net(x['gain_at_resolve_pct']) for x in rd]
        out.append((d, st.mean(top)-st.mean(rr), st.mean(top)-st.mean(bot)))
    return out

def boot_ci(vals, n=1000, seed=30000, block=(20,40)):
    rnd=random.Random(seed); n_d=len(vals); ms=[]
    for _ in range(n):
        s=[]; 
        while len(s)<n_d:
            L=rnd.randint(*block); a=rnd.randint(0,max(0,n_d-L))
            s+=vals[a:a+L]
        s=s[:n_d]; ms.append(st.mean(s))
    ms.sort()
    return st.mean(ms), ms[int(n*.025)], ms[int(n*.975)], st.pstdev(ms)

def report(kmin):
    ds=day_stats(kmin)
    print("\n=== 후보 %d개 이상인 날: %d일 (거래 %d건) ===" % (kmin,len(ds),sum(len(byday[d]) for d,_,_ in ds)))
    for lab,ix in (('5a 상위2−무작위2',1),('5b 상위2−하위2',2)):
        v=[x[ix] for x in ds]
        m,lo,hi,sd = boot_ci(v)
        pos=sum(1 for x in v if x>0)
        print("  %-16s 평균 %+.4f%%p · 중앙 %+.4f · 양수 %d/%d(%.1f%%) · 95%% %+.4f ~ %+.4f · MDE %.4f%%p"
              % (lab, st.mean(v), st.median(v), pos, len(v), 100*pos/len(v), lo, hi, 2.80*sd))
    # 연도별
    for lab,ix in (('5a',1),('5b',2)):
        yr=collections.defaultdict(list)
        for d,a,b in ds: yr[d[:4]].append(a if ix==1 else b)
        row=" · ".join("%s %+.2f" % (y, st.mean(yr[y])) for y in sorted(yr))
        print("    %s 연도별: %s" % (lab,row))
        for y in sorted(yr):
            sub=[x[ix] for x in ds if x[0][:4]!=y]
            if abs(st.mean(sub))>0 and (st.mean(sub)>0) != (st.mean([x[ix] for x in ds])>0):
                print("      → %s 제거 시 부호 반전: %+.4f" % (y, st.mean(sub)))
report(3); report(4)
print("\n=== 거래대금 구간별 (entry_date 연도) ===")
def tb(t):
    for hi,l in [(10,'5~10억'),(20,'10~20억'),(50,'20~50억'),(100,'50~100억'),(300,'100~300억')]:
        if t<hi: return l
    return '300억+'
g=collections.defaultdict(list)
for e in R: g[tb(e['turnover_eok'])].append(e)
for k in ['5~10억','10~20억','20~50억','50~100억','100~300억','300억+']:
    v=g[k]; n=[net(e['gain_at_resolve_pct']) for e in v]
    print("  %-9s n=%4d 승률 %.1f%% 거래당 %+.3f%%" % (k,len(v),100*sum(1 for e in v if e['result']=='win')/len(v),st.mean(n)))
u20=[e for e in R if e['turnover_eok']<20]
print("  20억 미만 합계: n=%d 승률 %.1f%% 거래당 %+.3f%%  (페이지 26.9%%)"
      % (len(u20),100*sum(1 for e in u20 if e['result']=='win')/len(u20),
         st.mean(net(e['gain_at_resolve_pct']) for e in u20)))
