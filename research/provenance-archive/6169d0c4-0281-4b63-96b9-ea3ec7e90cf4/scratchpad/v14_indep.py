# -*- coding: utf-8 -*-
"""14번 독립 재계산 — 조사 세션 스크립트를 쓰지 않고 경로 자료에서 직접."""
import json, collections, statistics as st
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100

rows = []   # (year, key, arm-> (gain_pct, label, kind), dead?)
for y in (2021, 2022, 2023, 2024, 2025, 2026):
    d = json.load(open(BT + r"\out\paths_%d.json" % y, encoding='utf-8'))
    ends = collections.Counter(p['dates'][-1] for p in d['paths'])
    modal = ends.most_common(1)[0][0]
    for p in d['paths']:
        E, h, l, c = p['entry_price'], p['h'], p['l'], p['c']
        T, S = E*1.20, E*0.90
        dead = p['dates'][-1] != modal          # 종목 소멸
        n = len(c)
        # ① 현행 (M1): 당일 포함 선착, 동시접촉=패, 체결=닿은 날 종가
        a1 = None
        for i in range(n):
            ht, hs = h[i] >= T, l[i] <= S
            if ht and hs: a1 = ((c[i]/E-1)*100, 'loss', 'both'); break
            if ht:        a1 = ((c[i]/E-1)*100, 'win',  'target'); break
            if hs:        a1 = ((c[i]/E-1)*100, 'loss', 'stop'); break
        if a1 is None: a1 = ((c[-1]/E-1)*100, None, 'last')
        # ② 목표만
        a2 = None
        for i in range(n):
            if h[i] >= T: a2 = ((c[i]/E-1)*100, 'win', 'target'); break
        if a2 is None: a2 = ((c[-1]/E-1)*100, None, 'last')
        # ③ 끝까지
        a3 = ((c[-1]/E-1)*100, None, 'last')
        rows.append((y, (p['scan_date'], p['code'], p['pattern']), a1, a2, a3, dead))
    del d

def label(v):
    g, lb, kind = v
    if lb: return lb
    return 'win' if g > 0 else 'loss'     # 마지막 종가: 부호, 0.00%면 패
def val(v, mode, dead):
    g, lb, kind = v
    if mode == 'main': return g
    if mode == 'drop': return None if (dead and kind == 'last') else g
    if mode == 'd50':  return -50.0 if (dead and kind == 'last') else g

print("관문 — 진입 수 / 미결착 내역")
for nm, ix in (('①', 2), ('②', 3), ('③', 4)):
    tot = len(rows)
    conf = sum(1 for r in rows if r[ix][2] in ('target','stop','both'))
    d_last = sum(1 for r in rows if r[ix][2] == 'last' and r[5])
    e_last = sum(1 for r in rows if r[ix][2] == 'last' and not r[5])
    print("  %s 진입 %d · 확정 %d · 미결착(소멸 %d / 구간끝 %d)" % (nm, tot, conf, d_last, e_last))

def table(mode, cut=None, quiet=False):
    out = {}
    for y in (2021,2022,2023,2024,2025,2026):
        sel = [r for r in rows if r[0] == y]
        if cut: sel = [r for r in sel if r[1][0] < cut]
        v1 = [net(val(r[2], mode, r[5])) for r in sel if val(r[2], mode, r[5]) is not None]
        v2 = [net(val(r[3], mode, r[5])) for r in sel if val(r[3], mode, r[5]) is not None]
        v3 = [net(val(r[4], mode, r[5])) for r in sel if val(r[4], mode, r[5]) is not None]
        if not v1: continue
        out[y] = (len(v1), st.mean(v1), st.mean(v2), st.mean(v3))
    sel = [r for r in rows if (cut is None or r[1][0] < cut)]
    v1 = [net(val(r[2],mode,r[5])) for r in sel if val(r[2],mode,r[5]) is not None]
    v2 = [net(val(r[3],mode,r[5])) for r in sel if val(r[3],mode,r[5]) is not None]
    v3 = [net(val(r[4],mode,r[5])) for r in sel if val(r[4],mode,r[5]) is not None]
    out['전체'] = (len(v1), st.mean(v1), st.mean(v2), st.mean(v3))
    if not quiet:
        print("\n[%s%s]  %-6s %6s %9s %9s %9s %10s %10s" % (mode, ' cut' if cut else '', '연도','n','①현행','②목표만','③끝까지','①−②','②−③'))
        for k, (n_, m1, m2, m3) in out.items():
            print("        %-8s %6d %+8.2f%% %+8.2f%% %+8.2f%% %+9.2f%%p %+9.2f%%p"
                  % (k, n_, m1, m2, m3, m1-m2, m2-m3))
    return out

for mode in ('main','drop','d50'):
    o = table(mode)
    signs = ''.join('+' if o[y][1]-o[y][2] > 0 else '-' for y in (2021,2022,2023,2024,2025,2026))
    print("        ①vs② 연도 부호: %s  (%d/6)" % (signs, signs.count('+')))
for mode in ('main','drop','d50'):
    o = table(mode, cut='2026-02-21', quiet=True)
    signs = ''.join('+' if o[y][1]-o[y][2] > 0 else '-' for y in (2021,2022,2023,2024,2025,2026))
    print("[%s cut] 전체 ①−② %+.2f%%p · 부호 %s (%d/6)" % (mode, o['전체'][1]-o['전체'][2], signs, signs.count('+')))

# 절대 성적
print("\n세 팔 절대 성적 (전체·주판정)")
for nm, ix in (('①',2), ('②',3), ('③',4)):
    nets = [net(r[ix][0]) for r in rows]
    labs = [label(r[ix]) for r in rows]
    w = [n_ for n_, lb in zip(nets, labs) if lb == 'win']
    lo = [n_ for n_, lb in zip(nets, labs) if lb != 'win']
    wr = len(w)/len(nets)*100
    be = abs(st.mean(lo))/(st.mean(w)+abs(st.mean(lo)))*100
    print("  %s n=%d 승률 %5.2f%% 본전 %5.2f%% 여유 %+5.2f%%p 거래당 %+6.3f%%"
          % (nm, len(nets), wr, be, wr-be, st.mean(nets)))
