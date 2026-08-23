# -*- coding: utf-8 -*-
"""14번 독립 재계산 v2 — ㉠는 전 팔에서 소멸키 제외(유니버스 동일), 컷은 entry_date 기준."""
import json, collections, statistics as st, random
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
rows = []
for y in (2021, 2022, 2023, 2024, 2025, 2026):
    d = json.load(open(BT + r"\out\paths_%d.json" % y, encoding='utf-8'))
    modal = collections.Counter(p['dates'][-1] for p in d['paths']).most_common(1)[0][0]
    for p in d['paths']:
        E, h, l, c = p['entry_price'], p['h'], p['l'], p['c']
        T, S = E*1.20, E*0.90
        dead = p['dates'][-1] != modal
        n = len(c); a1 = a2 = None
        for i in range(n):
            ht, hs = h[i] >= T, l[i] <= S
            if ht and hs: a1 = ((c[i]/E-1)*100, 'loss', 'both'); break
            if ht:        a1 = ((c[i]/E-1)*100, 'win', 'target'); break
            if hs:        a1 = ((c[i]/E-1)*100, 'loss', 'stop'); break
        if a1 is None: a1 = ((c[-1]/E-1)*100, None, 'last')
        for i in range(n):
            if h[i] >= T: a2 = ((c[i]/E-1)*100, 'win', 'target'); break
        if a2 is None: a2 = ((c[-1]/E-1)*100, None, 'last')
        a3 = ((c[-1]/E-1)*100, None, 'last')
        rows.append({'y': y, 'ed': p['entry_date'], 'code': p['code'],
                     'a': (a1, a2, a3), 'dead': dead})
    del d

def value(r, arm, mode):
    g, lb, kind = r['a'][arm]
    if mode == 'd50' and r['dead'] and kind == 'last': return -50.0
    return g
def sel_rows(mode, cut):
    s = rows
    if mode == 'drop': s = [r for r in s if not r['dead']]      # 전 팔에서 소멸키 제외
    if cut: s = [r for r in s if r['ed'] < cut]
    return s
def diff12(mode, cut=None, drop_top=0, per_year=False):
    s = sel_rows(mode, cut)
    def mean_arm(rs, arm): return st.mean([net(value(r, arm, mode)) for r in rs])
    if drop_top:
        # 기여 상위 = ①−② 차이가 큰 순 (양쪽 방향 각각 볼 수 있게 부호 그대로)
        s = sorted(s, key=lambda r: -(net(value(r,0,mode)) - net(value(r,1,mode))))[drop_top:]
    if per_year:
        out = {}
        for y in (2021,2022,2023,2024,2025,2026):
            g = [r for r in s if r['y'] == y]
            if g: out[y] = (len(g), mean_arm(g,0) - mean_arm(g,1))
        return out, (len(s), mean_arm(s,0) - mean_arm(s,1))
    return len(s), mean_arm(s,0) - mean_arm(s,1)

print("== 여섯 조합 ①−② (독립 재계산) ==")
for cut in (None, '2026-02-21'):
    for mode in ('main','drop','d50'):
        py, tot = diff12(mode, cut, per_year=True)
        signs = ''.join('+' if py[y][1] > 0 else '-' for y in sorted(py))
        print("  %-12s %-5s n=%4d  전체 %+.2f%%p  부호 %s (%d/6)"
              % ('전체' if not cut else '02-21컷', mode, tot[0], tot[1], signs, signs.count('+')))
print()
print("== 집중도 — ①−② 차이에 크게 기여한 거래를 빼면 ==")
for mode in ('main',):
    for k in (0, 5, 10, 20, 50):
        py, tot = diff12(mode, None, drop_top=k, per_year=True)
        signs = ''.join('+' if py[y][1] > 0 else '-' for y in sorted(py))
        print("  ①에 유리한 상위 %2d건 제거: 전체 %+.2f%%p  부호 %s (%d/6)  | 2024 %+.2f · 2025 %+.2f"
              % (k, tot[1], signs, signs.count('+'), py[2024][1], py[2025][1]))
print()
print("== 2024·2025 뒤집힘이 몇 건에 기대는가 (그 해 안에서 ②에 유리한 상위 제거) ==")
for y in (2024, 2025):
    g = [r for r in rows if r['y'] == y]
    g2 = sorted(g, key=lambda r: (net(value(r,0,'main')) - net(value(r,1,'main'))))  # ②에 유리한 순
    for k in (0, 1, 3, 5, 10, 20):
        gg = g2[k:]
        d = st.mean([net(value(r,0,'main')) for r in gg]) - st.mean([net(value(r,1,'main')) for r in gg])
        print("   %d: ②에 유리한 상위 %2d건 제거 → ①−② %+.2f%%p %s" % (y, k, d, '(뒤집힘 유지)' if d < 0 else '← 부호 복귀'))
