# -*- coding: utf-8 -*-
"""05 독립 검증 — 집단 A 짝차이·구간·도달률."""
import json, collections, statistics as st, random
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
rows=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        E=p['E'] if 'E' in p else p['entry_price']
        o,h,l,c=p['o'],p['h'],p['l'],p['c']
        if c[0] >= E: continue                      # 집단 A 아님
        T,S=E*1.20,E*0.90; res=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: res=(i,'loss',(c[i]/E-1)*100); break
            if ht: res=(i,'win',(c[i]/E-1)*100); break
            if hs: res=(i,'loss',(c[i]/E-1)*100); break
        if res is None:
            g=(c[-1]/E-1)*100; res=(len(c)-1,'win' if g>0 else 'loss',g)
        i,lb,g=res
        sell = g if i==0 else (o[1]/E-1)*100         # 익일 시가 매도
        rows.append({'ed':p['entry_date'],'yr':p['entry_date'][:4],'d0':(c[0]/E-1)*100,
                     'hold':g,'sell':sell,'win':lb=='win','same':i==0,
                     'diff':net(g)-net(sell)})
    del d
print("집단 A %d건 (파일 2,076) · 두 팔이 같은 건 %d (파일 67) · 갈리는 짝 %d (파일 2,009)"
      % (len(rows), sum(r['same'] for r in rows), sum(1 for r in rows if not r['same'])))
dv=[r['diff'] for r in rows]
print("\n[1순위] 평균 %+.4f%%p (파일 +0.1838) · 중앙 %+.4f (파일 -5.9645)" % (st.mean(dv), st.median(dv)))
print("[절대성적] 완주 승률 %.1f%% 거래당 %+.3f%% (파일 26.7 / -2.584)"
      % (100*sum(r['win'] for r in rows)/len(rows), st.mean(net(r['hold']) for r in rows)))
sw=sum(1 for r in rows if net(r['sell'])>0)
print("           익일 승률 %.1f%% 거래당 %+.3f%% (파일 15.9 / -2.768)"
      % (100*sw/len(rows), st.mean(net(r['sell']) for r in rows)))
# 블록 부트스트랩 (날 단위)
byday=collections.defaultdict(list)
for r in rows: byday[r['ed']].append(r)
days=sorted(byday)
def boot(stat, n=1000, seed=50000):
    rnd=random.Random(seed); out=[]
    for _ in range(n):
        s=[]
        while len(s)<len(days):
            L=rnd.randint(20,40); a=rnd.randint(0,max(0,len(days)-L))
            s+=days[a:a+L]
        s=s[:len(days)]
        v=[x['diff'] for d in s for x in byday[d]]
        out.append(stat(v))
    out.sort(); return out
bm=boot(st.mean); bmed=boot(st.median)
print("  평균 95%% %+.4f ~ %+.4f (파일 -0.8792 ~ +1.1606) · SD %.4f (파일 0.5268) · MDE %.4f (파일 1.4749)"
      % (bm[25],bm[975],st.pstdev(bm),2.80*st.pstdev(bm)))
print("  중앙 95%% %+.4f ~ %+.4f (파일 -6.4590 ~ -5.4638)" % (bmed[25],bmed[975]))
# L4
top5=sorted(range(len(rows)),key=lambda i:-rows[i]['diff'])[:5]
sub=[r for i,r in enumerate(rows) if i not in set(top5)]
print("\n[L4] 상위 5건 제거 → 평균 %+.4f (파일 +0.0685) · 그 5건 기여 %.0f%%"
      % (st.mean(r['diff'] for r in sub), 100*(1-st.mean(r['diff'] for r in sub)/st.mean(dv))))
# leave-one-year
print("\n[L2'] leave-one-year 평균")
for y in ('2021','2022','2023','2024','2025','2026'):
    s=[r['diff'] for r in rows if r['yr']!=y]
    print("   %s 제거 → %+.4f %s" % (y, st.mean(s), "← 부호 반전" if (st.mean(s)>0)!=(st.mean(dv)>0) else ""))
# 첫날 손실폭 네 구간
print("\n['산수' 검정] 첫날 손실폭 구간별")
def bk(x):
    if x>-2: return '−0~−2%'
    if x>-4: return '−2~−4%'
    if x>-6: return '−4~−6%'
    return '−6%~'
g=collections.defaultdict(list)
for r in rows: g[bk(r['d0'])].append(r)
for k in ('−0~−2%','−2~−4%','−4~−6%','−6%~'):
    v=g[k]
    print("   %-8s n=%4d 평균차이 %+.3f%%p · 중앙 %+.3f · +20%% 도달 %.1f%%"
          % (k,len(v),st.mean(x['diff'] for x in v),st.median(x['diff'] for x in v),
             100*sum(x['win'] for x in v)/len(v)))
print("   (파일 도달률 32.3 / 24.7 / 16.5 / 7.2)")

print("\n[승률 정의 대조] 익일매도 팔")
gw=sum(1 for r in rows if r['sell']>0); nw=sum(1 for r in rows if net(r['sell'])>0)
print("   총수익>0 기준 %.1f%% (파일 15.9) · 순수익>0 기준 %.1f%% (내 계산 10.2)"
      % (100*gw/len(rows), 100*nw/len(rows)))
print("   완주 팔 승률 26.7%는 '목표 도달' 기준이고 익일 팔은 '부호' 기준 — 두 열이 다른 것을 센다")
print("\n[−6%~ 구간 구성]")
v=g['−6%~']
same=sum(1 for x in v if x['same'])
print("   n=%d · 두 팔이 같은 건(당일 결착) %d (%.0f%%) · 차이가 정확히 0인 건 %d"
      % (len(v), same, 100*same/len(v), sum(1 for x in v if abs(x['diff'])<1e-12)))
print("   → 중앙값이 0.000인 것은 '차이가 없어서'가 아니라 **절반 이상이 이미 당일 결착**이라 두 팔이 같기 때문")
