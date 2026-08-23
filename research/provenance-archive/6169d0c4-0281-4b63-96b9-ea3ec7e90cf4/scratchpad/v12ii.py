# -*- coding: utf-8 -*-
"""(iii) 결론의 독립 확인 — '겹침으로 막힌 후보'가 실제로 평균보다 나쁜가."""
import json, collections, statistics as st
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
agg = {False: [], True: []}
byyear = collections.defaultdict(lambda: {False: [], True: []})
tot = collections.Counter()
for y in (2021,2022,2023,2024,2025,2026):
    d = json.load(open(BT + r"\out\cand_paths_%d.json" % y, encoding='utf-8'))
    for p in d['paths']:
        E=p['entry_price']; T=E*1.20; S=E*0.90; h,l,c=p['h'],p['l'],p['c']; r=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: r=(i,'loss',(c[i]/E-1)*100); break
            if ht: r=(i,'win',(c[i]/E-1)*100); break
            if hs: r=(i,'loss',(c[i]/E-1)*100); break
        if r is None:
            g=(c[-1]/E-1)*100; r=(len(c)-1,'win' if g>0 else 'loss',g)
        b = bool(p['blocked_overlap'])
        agg[b].append((net(r[2]), r[1]=='win'))
        byyear[y][b].append(net(r[2]))
        tot[('blocked' if b else 'taken', y)] += 1
    del d
print("후보 전수 %d  (진입 %d · 막힘 %d)" % (len(agg[False])+len(agg[True]), len(agg[False]), len(agg[True])))
print("   목표 9,334 = 3,776 + 5,558 %s" % ("일치" if len(agg[False])==3776 and len(agg[True])==5558 else "★불일치★"))
print()
for b,lab in ((False,'하네스가 실제로 산 것'),(True,'겹침으로 막힌 것')):
    v=[x[0] for x in agg[b]]; w=sum(1 for x in agg[b] if x[1])
    print("%-16s n=%5d  승률 %.2f%%  거래당 순수익 %+.4f%%" % (lab,len(v),100*w/len(v),st.mean(v)))
diff = st.mean(x[0] for x in agg[True]) - st.mean(x[0] for x in agg[False])
print("→ 막힌 후보 − 산 후보 = %+.4f%%p" % diff)
print()
print("연도별 (거래당 순수익)")
for y in (2021,2022,2023,2024,2025,2026):
    a=byyear[y][False]; b=byyear[y][True]
    print("   %d  산 것 %+.3f%% (n=%4d)  ·  막힌 것 %+.3f%% (n=%4d)  ·  차이 %+.3f%%p"
          % (y, st.mean(a), len(a), st.mean(b), len(b), st.mean(b)-st.mean(a)))
