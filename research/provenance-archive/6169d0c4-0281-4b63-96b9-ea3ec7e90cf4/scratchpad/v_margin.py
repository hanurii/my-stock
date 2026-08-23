# -*- coding: utf-8 -*-
"""메모리에 '유효'로 남긴 승률 35.6% · 여유 0.4%p 가 M1(당일 손절 포함)에 견디는가."""
import json, statistics as st
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
ev = []
for y in range(2021, 2027):
    ev += json.load(open(BT + r"\bt_%d.json" % y, encoding='utf-8'))['events']
seen, U = set(), []
for e in sorted(ev, key=lambda x: (x['entry_date'], x['code'])):
    k = (e['scan_date'], e['code'], e['pattern'])
    if k not in seen: seen.add(k); U.append(e)

conf = [e for e in U if e['result'] in ('win','loss')]
amb  = [e for e in U if e['result'] == 'ambiguous']
unres= [e for e in U if e['result'] == 'unresolved']

def stats(nets, label):
    w = [x for x in nets if x > 0]; l = [x for x in nets if x <= 0]
    wr = len(w)/len(nets)*100
    be = abs(st.mean(l))/(st.mean(w)+abs(st.mean(l)))*100
    print("%-34s n=%5d  승률 %5.2f%%  손익분기 %5.2f%%  여유 %+5.2f%%p  거래당순 %+5.3f%%"
          % (label, len(nets), wr, be, wr-be, st.mean(nets)))
    return wr - be

base = [net(e['gain_at_resolve_pct']) for e in conf]
m_base = stats(base, "현행 표본 (확정 3,681건)")

# M1: 매수 당일 손절 터치를 손절가 체결 손실로 포함
print("\nambiguous 74건 내역:")
import collections
print("  ", dict(collections.Counter(e.get('exit_reason','?') for e in amb)))
stop_net = net(-10.0)
print("   손절가 체결 시 순수익 = %+.2f%%" % stop_net)
m1 = base + [stop_net]*len(amb)
m_m1 = stats(m1, "M1 적용 (ambiguous 74건 = 손절)")

# 종가 체결로 넣으면 (경로 자료가 있으니 실제 당일 종가로도 가능하나 여기선 손절가 기준)
# unresolved 21건은 미결이라 제외 유지
print("\n같은 계산을 연도 구간별로 (M1 적용):")
def seg(d):
    y = d[:4]; return y if y in ('2021','2022','2023','2024') else '2025~26'
byseg = {}
for e in conf: byseg.setdefault(seg(e['entry_date']), []).append(net(e['gain_at_resolve_pct']))
for e in amb:  byseg.setdefault(seg(e['entry_date']), []).append(stop_net)
for s in sorted(byseg): stats(byseg[s], "   " + s)
