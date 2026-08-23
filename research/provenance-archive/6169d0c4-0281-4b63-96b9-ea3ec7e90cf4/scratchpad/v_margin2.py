# -*- coding: utf-8 -*-
"""ambiguous 74건을 경로의 '그날 실제 종가'로 넣어 다시 — M1 갭업/장중 구분 포함."""
import json, statistics as st, collections
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
paths = {}
for y in range(2021, 2027):
    for p in json.load(open(BT + r"\out\paths_%d.json" % y, encoding='utf-8'))['paths']:
        paths[(p['scan_date'], p['code'], p['pattern'])] = p
ev = []
for y in range(2021, 2027):
    ev += json.load(open(BT + r"\bt_%d.json" % y, encoding='utf-8'))['events']
seen, U = set(), []
for e in sorted(ev, key=lambda x: (x['entry_date'], x['code'])):
    k = (e['scan_date'], e['code'], e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
conf = [e for e in U if e['result'] in ('win','loss')]
amb  = [e for e in U if e['result'] == 'ambiguous']

gap = [e for e in amb if e['gap_up_pct'] > 0]
intr = [e for e in amb if e['gap_up_pct'] <= 0]
print("ambiguous 74건: 갭업 진입 %d · 장중 진입 %d" % (len(gap), len(intr)))
def dayclose(e):
    p = paths[(e['scan_date'], e['code'], e['pattern'])]
    return (p['c'][0] / p['entry_price'] - 1) * 100
cl = [dayclose(e) for e in amb]
print("당일 종가(매수가 대비): 중앙 %+.2f%% · 평균 %+.2f%% · 최악 %+.2f%% · %d건이 -10%% 아래"
      % (st.median(cl), st.mean(cl), min(cl), sum(1 for x in cl if x < -10)))

def stats(nets, label):
    w = [x for x in nets if x > 0]; l = [x for x in nets if x <= 0]
    wr = len(w)/len(nets)*100
    be = abs(st.mean(l))/(st.mean(w)+abs(st.mean(l)))*100
    print("%-40s n=%5d  승률 %5.2f%%  본전 %5.2f%%  여유 %+5.2f%%p  거래당순 %+6.3f%%"
          % (label, len(nets), wr, be, wr-be, st.mean(nets)))
base = [net(e['gain_at_resolve_pct']) for e in conf]
stats(base, "① 현행 표본 (메모리에 '유효'로 남긴 값)")
stats(base + [net(-10.0)]*len(amb), "② M1 — 74건 전부 손절가 체결")
stats(base + [net(dayclose(e)) for e in amb], "③ M1 — 74건 전부 그날 종가 체결")
stats(base + [net(dayclose(e)) for e in gap], "④ M1 — 갭업 %d건만 포함(장중 제외)" % len(gap))
