# -*- coding: utf-8 -*-
import json, collections, statistics as st, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
rows = []
for y in (2021,2022,2023,2024,2025,2026):
    d = json.load(open(BT + r"\out\paths_%d.json" % y, encoding='utf-8'))
    modal = collections.Counter(p['dates'][-1] for p in d['paths']).most_common(1)[0][0]
    for p in d['paths']:
        E,h,l,c,dt = p['entry_price'],p['h'],p['l'],p['c'],p['dates']
        T,S = E*1.20, E*0.90; n=len(c); a1=a2=None
        for i in range(n):
            ht,hs = h[i]>=T, l[i]<=S
            if ht and hs: a1=((c[i]/E-1)*100,'loss','both',dt[i]); break
            if ht: a1=((c[i]/E-1)*100,'win','target',dt[i]); break
            if hs: a1=((c[i]/E-1)*100,'loss','stop',dt[i]); break
        if a1 is None: a1=((c[-1]/E-1)*100,None,'last',dt[-1])
        for i in range(n):
            if h[i]>=T: a2=((c[i]/E-1)*100,'win','target',dt[i]); break
        if a2 is None: a2=((c[-1]/E-1)*100,None,'last',dt[-1])
        a3=((c[-1]/E-1)*100,None,'last',dt[-1])
        rows.append({'y':y,'ed':p['entry_date'],'sd':p['scan_date'],'code':p['code'],
                     'pat':p['pattern'],'a':(a1,a2,a3),'dead':p['dates'][-1]!=modal})
    del d

def lab(v): return v[1] if v[1] else ('win' if v[0] > 0 else 'loss')
def stats(arm, rs=rows):
    nets=[net(r['a'][arm][0]) for r in rs]; labs=[lab(r['a'][arm]) for r in rs]
    w=[x for x,L in zip(nets,labs) if L=='win']; lo=[x for x,L in zip(nets,labs) if L!='win']
    wr=len(w)/len(nets)*100; be=abs(st.mean(lo))/(st.mean(w)+abs(st.mean(lo)))*100
    return len(nets), wr, be, wr-be, st.mean(nets)

print("== [5] 여유가 음수인 이유 분해 (①) ==")
sub = [r for r in rows if r['a'][0][2] in ('target','stop')]          # 옛 표본에 해당
print("  옛 표본 근사(당일접촉·미결착 제외) n=%d 승률 %.2f%% 본전 %.2f%% 여유 %+.2f%%p 거래당 %+.3f%%" % stats(0, sub))
sub2 = [r for r in rows if r['a'][0][2] != 'last']                     # + M1 편입
print("  + M1 당일접촉 편입           n=%d 승률 %.2f%% 본전 %.2f%% 여유 %+.2f%%p 거래당 %+.3f%%" % stats(0, sub2))
print("  + 미결착 21건 편입(=결과값)   n=%d 승률 %.2f%% 본전 %.2f%% 여유 %+.2f%%p 거래당 %+.3f%%" % stats(0))

print("\n== [7] 동시접촉 4건 라벨을 승으로 바꾸면 ==")
both=[r for r in rows if r['a'][0][2]=='both']
print("  동시접촉 %d건, 순수익 %s" % (len(both), [round(net(r['a'][0][0]),2) for r in both]))
nets=[net(r['a'][0][0]) for r in rows]
labs=[('win' if r['a'][0][2]=='both' else lab(r['a'][0])) for r in rows]
w=[x for x,L in zip(nets,labs) if L=='win']; lo=[x for x,L in zip(nets,labs) if L!='win']
wr=len(w)/len(nets)*100; be=abs(st.mean(lo))/(st.mean(w)+abs(st.mean(lo)))*100
print("  승 라벨 시: 승률 %.2f%% 본전 %.2f%% 여유 %+.2f%%p (거래당은 불변 %+.3f%%)" % (wr,be,wr-be,st.mean(nets)))

print("\n== [2] ②의 미결착 1,205건이 결과를 지배하는가 ★사후 탐색 · 판정 불가 ★ ==")
u2=[r for r in rows if r['a'][1][2]=='last']
print("  ② 미결착 %d건(31.9%%)의 마지막 종가 순수익: 중앙 %+.2f%% 평균 %+.2f%% 최악 %+.2f%%"
      % (len(u2), st.median([net(r['a'][1][0]) for r in u2]), st.mean([net(r['a'][1][0]) for r in u2]),
         min(net(r['a'][1][0]) for r in u2)))
d_all = st.mean([net(r['a'][0][0]) for r in rows]) - st.mean([net(r['a'][1][0]) for r in rows])
res2=[r for r in rows if r['a'][1][2]!='last']
d_res = st.mean([net(r['a'][0][0]) for r in res2]) - st.mean([net(r['a'][1][0]) for r in res2])
print("  주 판정(전부 포함)      ①−② %+.2f%%p" % d_all)
print("  ② 미결착을 아예 뺀 판   ①−② %+.2f%%p  (n=%d) ← 사후, 판정에 쓸 수 없음" % (d_res, len(res2)))
for pen in (-20, -30, -50):
    v2=[net(pen if r['a'][1][2]=='last' else r['a'][1][0]) for r in rows]
    print("  ② 미결착을 %d%%로 청산  ①−② %+.2f%%p ← 사후" % (pen, st.mean([net(r['a'][0][0]) for r in rows])-st.mean(v2)))

print("\n== [4] 슬롯5 — 체결 건수와 M4 하한 ==")
def trades(arm):
    return [{'code':r['code'],'pattern':r['pat'],'scan_date':r['sd'],'entry_date':r['ed'],
             'resolve_date':r['a'][arm][3],'gain':r['a'][arm][0],'result':lab(r['a'][arm])} for r in rows]
t1,t2,t3 = trades(0),trades(1),trades(2)
N=200
r1=[slot_sim.sim(t1,seed=i) for i in range(N)]
r2=[slot_sim.sim(t2,seed=i) for i in range(N)]
r3=[slot_sim.sim(t3,seed=i) for i in range(N)]
d=[r1[i]['equity_pct']-r2[i]['equity_pct'] for i in range(N)]
print("  ①vs② 우세율 %.1f%%  차이중앙 %+.1f%%p   체결중앙 ① %.0f · ② %.0f · ③ %.0f"
      % (sum(1 for x in d if x>0)/N*100, st.median(d),
         st.median(r['n_filled'] for r in r1), st.median(r['n_filled'] for r in r2),
         st.median(r['n_filled'] for r in r3)))
# 구간별 체결
for nm,tt in (('①',t1),('②',t2),('③',t3)):
    per=collections.Counter()
    s=slot_sim.sim(tt,seed=0)
    # 구간별 체결은 시뮬 내부라 근사: 진입일 기준으로 뽑힌 거래를 세기 위해 재현
    print("    %s 체결 중앙 %.0f → 다섯 구간 평균 %.1f건/구간  M4 하한(30건) %s"
          % (nm, st.median(r['n_filled'] for r in (r1 if nm=='①' else r2 if nm=='②' else r3)),
             st.median(r['n_filled'] for r in (r1 if nm=='①' else r2 if nm=='②' else r3))/5,
             "통과" if st.median(r['n_filled'] for r in (r1 if nm=='①' else r2 if nm=='②' else r3))/5>=30 else "**미달 → 판정불가**"))
