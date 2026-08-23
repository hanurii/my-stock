# -*- coding: utf-8 -*-
"""옛 '무손절 근사'가 항등식인지 — 두뇌 세션 철회 판단을 무너뜨려 본다."""
import json, statistics as st, collections
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
FEE = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
ev = []
for y in range(2021, 2027):
    ev += [e for e in json.load(open(BT + r"\bt_%d.json" % y, encoding='utf-8'))['events']
           if e['result'] in ('win','loss')]
seen, U = set(), []
for e in sorted(ev, key=lambda x: (x['entry_date'], x['code'])):
    k = (e['scan_date'], e['code'], e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
EV = U
loss = [e for e in EV if e['result'] == 'loss']
win  = [e for e in EV if e['result'] == 'win']

# [2] 반례 — max_dd 가 결착손익보다 나은 건이 하나라도 있는가
viol = [e for e in EV if e['max_dd_pct'] > e['gain_at_resolve_pct']]
eq   = [e for e in EV if e['max_dd_pct'] == e['gain_at_resolve_pct']]
print("전체 %d건 중 max_dd > 결착손익 인 건: %d건" % (len(EV), len(viol)))
print("   패 %d건 중: %d건 · 승 %d건 중: %d건"
      % (len(loss), sum(1 for e in loss if e['max_dd_pct'] > e['gain_at_resolve_pct']),
         len(win),  sum(1 for e in win  if e['max_dd_pct'] > e['gain_at_resolve_pct'])))
print("   정확히 같은 건: %d건 (소수 둘째 자리 반올림 때문)" % len(eq))
d = [e['gain_at_resolve_pct'] - e['max_dd_pct'] for e in loss]
print("패 1건당 (결착손익 − max_dd): 평균 %+.2f%%p · 중앙 %+.2f%%p · 최소 %+.2f%%p"
      % (st.mean(d), st.median(d), min(d)))
print("패 비율 %.1f%% × 평균차 %.2f%%p = %+.2f%%p" % (len(loss)/len(EV)*100, st.mean(d),
                                                 len(loss)/len(EV)*st.mean(d)))

# [3] 연도별 재현 — 어느 해든 부호가 뒤집힐 수 있는가
print("\n연도별 (analyze2.py ⑤절 그대로 재현)")
print("%-8s %14s %16s %10s" % ("연도", "규칙대로(순)", "'손절없었다면'", "차이"))
for y in ('2021','2022','2023','2024','2025','2026'):
    g = [e for e in EV if e['scan_date'][:4] == y]
    if not g: continue
    real = st.mean([FEE(e['gain_at_resolve_pct']) for e in g])
    nos  = st.mean([FEE(e['gain_at_resolve_pct'] if e['result']=='win' else e['max_dd_pct']) for e in g])
    print("%-8s %13.2f%% %15.2f%% %9.2f%%p  뒤집힘? %s"
          % (y, real, nos, real-nos, "예" if nos > real else "아니오"))

# 승 팔이 정말 동일한지
same = all(FEE(e['gain_at_resolve_pct']) == FEE(e['gain_at_resolve_pct']) for e in win)
print("\n승 %d건: 두 팔의 계산식이 문자 그대로 동일 → 차이는 전부 패 팔에서만 발생 (%s)"
      % (len(win), same))

# 부분집합 어디서든 뒤집힐 수 있는가 — 무작위 하위표본 2000회
import random
rnd = random.Random(0); flips = 0
for _ in range(2000):
    g = rnd.sample(EV, 200)
    real = st.mean([FEE(e['gain_at_resolve_pct']) for e in g])
    nos  = st.mean([FEE(e['gain_at_resolve_pct'] if e['result']=='win' else e['max_dd_pct']) for e in g])
    if nos > real: flips += 1
print("무작위 200건 하위표본 2,000회 중 '무손절이 더 나은' 경우: %d회" % flips)
