# -*- coding: utf-8 -*-
"""04 독립 검증 — 점수 조립 재구성 + 하위 통계 전부 재계산."""
import json, glob, collections, statistics as st, random, math, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib.superperf import score as sp_score
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100

ev = {}
for f in sorted(glob.glob(BT + r"\bt_*.json")):
    for e in json.load(open(f, encoding='utf-8'))['events']:
        ev[(e['scan_date'], e['code'], e['pattern'])] = e
seen, U = set(), []
for e in sorted(ev.values(), key=lambda x: (x['entry_date'], x['code'])):
    k = (e['scan_date'], e['code'], e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
R = {(e['scan_date'],e['code'],e['pattern']): e for e in U if e['result'] in ('win','loss')}

S = {}
for f in sorted(glob.glob(BT + r"\out\_04_score_cache\scores_*.json")):
    S.update(json.load(open(f, encoding='utf-8'))['scores'])
print("캐시 점수 %d건 / 확정 %d건" % (len(S), len(R)))

# ── [A] 점수 조립을 superperf.score 로 재구성 ──
bad6 = bad4 = 0
for key, s in S.items():
    sd, code, pat = key.split('|')
    e = R.get((sd, code, pat))
    if e is None: continue
    fm = s['factors_mkt']
    p6, _ = sp_score(e['rs'], fm['prior_adv'], fm['rs_nh_days'], fm['rs_leads'])
    p4, _ = sp_score(None, fm['prior_adv'], fm['rs_nh_days'], fm['rs_leads'])  # RS 성분 제거
    if p6 != s['score6_mkt']: bad6 += 1
    if p4 != s['score4_mkt']: bad4 += 1
print("[A] 점수 조립 재구성: 6점판 불일치 %d건 · 4점판 불일치 %d건" % (bad6, bad4))

# ── [B] 하위 통계 ──
rows = []
for key, s in S.items():
    sd, code, pat = key.split('|')
    e = R.get((sd, code, pat))
    if e is None: continue
    rows.append({'k':(sd,code,pat), 'ed':e['entry_date'], 'yr':e['entry_date'][:4],
                 'net':net(e['gain_at_resolve_pct']), 'win':e['result']=='win',
                 's6':s['score6_mkt'], 's4':s['score4_mkt']})
print("대상 %d건" % len(rows))
hi = [r for r in rows if r['s6']>=4]; lo = [r for r in rows if r['s6']<=2]
print("[B] 6점판 고득점 %d · 저득점 %d  (파일 1430 / 1400)" % (len(hi), len(lo)))
Sstat = st.mean(r['net'] for r in hi) - st.mean(r['net'] for r in lo)
print("    S = %+.4f%%p  (파일 -1.2134)" % Sstat)
h4=[r for r in rows if r['s4']>=3]; l4=[r for r in rows if r['s4']<=1]
print("    4점판 고 %d · 저 %d · S = %+.4f  (파일 677 / 1933 / -0.7683)"
      % (len(h4), len(l4), st.mean(r['net'] for r in h4)-st.mean(r['net'] for r in l4)))

byday = collections.defaultdict(list)
for r in rows: byday[r['ed']].append(r)
d6 = {}
for d, v in byday.items():
    a=[x['net'] for x in v if x['s6']>=4]; b=[x['net'] for x in v if x['s6']<=2]
    if a and b: d6[d] = st.mean(a)-st.mean(b)
pos = sum(1 for x in d6.values() if x>0)
def signtest(vals):
    p=sum(1 for x in vals if x>0); n=sum(1 for x in vals if x<0); t=p+n
    if t==0: return 1.0
    k=min(p,n); return min(1.0, 2*sum(math.comb(t,i) for i in range(k+1))/2**t)
print("[B] L1: 성립 날 %d일 (파일 491) · 양수 %d (파일 231) · 중앙 %+.4f (파일 -0.5175) · p %.4f (파일 0.2064)"
      % (len(d6), pos, st.median(d6.values()), signtest(list(d6.values()))))

print("\n[B] 점수별 표 (6점 만점)")
g = collections.defaultdict(list)
for r in rows: g[r['s6']].append(r)
for k in sorted(g):
    v=g[k]
    print("   %d점 n=%4d 승률 %.1f%% 거래당 %+.3f%%" % (k,len(v),100*sum(x['win'] for x in v)/len(v),st.mean(x['net'] for x in v)))
print("[B] 점수별 표 (4점 만점)")
g4=collections.defaultdict(list)
for r in rows: g4[r['s4']].append(r)
for k in sorted(g4):
    v=g4[k]
    print("   %d점 n=%4d 승률 %.1f%% 거래당 %+.3f%%" % (k,len(v),100*sum(x['win'] for x in v)/len(v),st.mean(x['net'] for x in v)))

print("\n[B] leave-one-year (6점판 S)")
for y in ('2021','2022','2023','2024','2025','2026'):
    sub=[r for r in rows if r['yr']!=y]
    a=[r['net'] for r in sub if r['s6']>=4]; b=[r['net'] for r in sub if r['s6']<=2]
    print("   %s 제거 → S %+.4f" % (y, st.mean(a)-st.mean(b)))
print("[B] L3 다섯 구간 (파일 -1.33 / +2.02 / -0.91 / -0.05 / -3.26)")
def seg(y): return y if y in ('2021','2022','2023','2024') else '2025~26'
sg=collections.defaultdict(list)
for r in rows: sg[seg(r['yr'])].append(r)
for k in sorted(sg):
    v=sg[k]; a=[x['net'] for x in v if x['s6']>=4]; b=[x['net'] for x in v if x['s6']<=2]
    print("   %-8s S %+.3f (고 %d · 저 %d)" % (k, st.mean(a)-st.mean(b), len(a), len(b)))

print("\n[B] 9개월(2025-11-26~) 점수별 승률")
nine=[r for r in rows if r['ed']>='2025-11-26']
g9=collections.defaultdict(list)
for r in nine: g9[r['s6']].append(r)
page={1:46.3,2:41.4,3:38.1,4:35.7,5:34.6}
for k in sorted(g9):
    v=g9[k]; wr=100*sum(x['win'] for x in v)/len(v)
    se=100*math.sqrt(wr/100*(1-wr/100)/len(v))
    p=page.get(k)
    extra = "  페이지 %.1f%% → 차이 %+.1f%%p = %.2f SE" % (p, wr-p, abs(wr-p)/se) if p else ""
    print("   %d점 n=%3d 승률 %.1f%% (SE %.1f%%p)%s" % (k,len(v),wr,se,extra))
