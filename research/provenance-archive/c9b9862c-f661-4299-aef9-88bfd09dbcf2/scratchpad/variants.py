# -*- coding: utf-8 -*-
"""나스닥 신호 변형 전수 탐색 - 사전등록 변형 전부 보고 + BH/Bonferroni 보정."""
from base import *
import random, statistics as st, json, sys, collections

EV, _ = load_events()
DAYS = sorted({e['entry_date'] for e in EV})
DIDX = {d: i for i, d in enumerate(DAYS)}
NET = [FEE(e['gain_at_resolve_pct']) for e in EV]
DSUM = [0.0]*len(DAYS); DCNT = [0]*len(DAYS)
for e, v in zip(EV, NET):
    i = DIDX[e['entry_date']]; DSUM[i] += v; DCNT[i] += 1

F = {d: {s: feat(s, d) for s in ('IXIC', 'US500', 'DJI')} for d in DAYS}
REG_EV = [UP.get(e['scan_date']) for e in EV]   # 국면 = 스캔일 종가(무lookahead)

def mk(sym, fn):
    return lambda d: (None if F[d][sym] is None else bool(fn(F[d][sym])))

V = []
def add(g, name, fn): V.append(dict(g=g, name=name, fn=fn))

# G1 나스닥 크기
add('1크기', '나스닥 +1.0% 이상',        mk('IXIC', lambda x: x['ret'] >= 1.0))
add('1크기', '나스닥 +0.5~+1.0%',        mk('IXIC', lambda x: 0.5 <= x['ret'] < 1.0))
add('1크기', '나스닥 0~+0.5%',           mk('IXIC', lambda x: 0.0 < x['ret'] < 0.5))
add('1크기', '나스닥 -0.5~0%',           mk('IXIC', lambda x: -0.5 <= x['ret'] <= 0.0))
add('1크기', '나스닥 -1.0~-0.5%',        mk('IXIC', lambda x: -1.0 <= x['ret'] < -0.5))
add('1크기', '나스닥 -1.0% 미만',        mk('IXIC', lambda x: x['ret'] < -1.0))
add('1크기', '나스닥 +0.5% 이상(누적)',  mk('IXIC', lambda x: x['ret'] >= 0.5))
add('1크기', '나스닥 상승(방향)',        mk('IXIC', lambda x: x['ret'] > 0))
add('1크기', '나스닥 하락(방향)',        mk('IXIC', lambda x: x['ret'] <= 0))
# G2 연속성
add('2연속', '나스닥 2일 연속 상승',     mk('IXIC', lambda x: x['streak'] >= 2))
add('2연속', '나스닥 3일 연속 상승',     mk('IXIC', lambda x: x['streak'] >= 3))
# G3 20일선
add('3_20MA', '나스닥 20일선 위',        mk('IXIC', lambda x: x['above20']))
add('3_20MA', '나스닥 20일선 아래',      mk('IXIC', lambda x: not x['above20']))
add('3_20MA', '나스닥 20일선위 & 상승',  mk('IXIC', lambda x: x['above20'] and x['ret'] > 0))
# G4 S&P500
add('4SP500', 'S&P500 상승',             mk('US500', lambda x: x['ret'] > 0))
add('4SP500', 'S&P500 +1.0% 이상',       mk('US500', lambda x: x['ret'] >= 1.0))
add('4SP500', 'S&P500 +0.5% 이상',       mk('US500', lambda x: x['ret'] >= 0.5))
add('4SP500', 'S&P500 2일 연속 상승',    mk('US500', lambda x: x['streak'] >= 2))
add('4SP500', 'S&P500 3일 연속 상승',    mk('US500', lambda x: x['streak'] >= 3))
add('4SP500', 'S&P500 20일선 위',        mk('US500', lambda x: x['above20']))
# G5 다우
add('5DJI', '다우 상승',                 mk('DJI', lambda x: x['ret'] > 0))
add('5DJI', '다우 +1.0% 이상',           mk('DJI', lambda x: x['ret'] >= 1.0))
add('5DJI', '다우 +0.5% 이상',           mk('DJI', lambda x: x['ret'] >= 0.5))
add('5DJI', '다우 2일 연속 상승',        mk('DJI', lambda x: x['streak'] >= 2))
add('5DJI', '다우 3일 연속 상승',        mk('DJI', lambda x: x['streak'] >= 3))
add('5DJI', '다우 20일선 위',            mk('DJI', lambda x: x['above20']))

CROSS = [('6교차', 'G 국면상승+나스닥상승', True, 'up'),
         ('6교차', 'Y 국면상승+나스닥하락', True, 'down'),
         ('6교차', 'Y 국면조정+나스닥상승', False, 'up'),
         ('6교차', 'R 국면조정+나스닥하락', False, 'down'),
         ('6교차', '최악칸(국면조정+나스닥상승) 제외', None, 'excl'),
         ('6교차', '국면상승만(나스닥 무시.참조)', True, 'any'),
         ('6교차', '국면상승 & 나스닥20MA위', True, 'above20')]

def cross_ok(r, f, reg, nq):
    if f is None: return False
    if nq == 'excl':    return not (r is False and f['ret'] > 0)
    if nq == 'any':     return r is reg
    if nq == 'above20': return (r is reg) and f['above20']
    return (r is reg) and ((f['ret'] > 0) if nq == 'up' else (f['ret'] <= 0))

def stats_from_mask(mask):
    a = [v for v, m in zip(NET, mask) if m]
    b = [v for v, m in zip(NET, mask) if not m]
    wa = sum(1 for e, m in zip(EV, mask) if m and e['result'] == 'win')
    return dict(n=len(a), wr=(wa/len(a)*100 if a else float('nan')),
                net=(st.mean(a) if a else float('nan')),
                net_o=(st.mean(b) if b else float('nan')),
                diff=((st.mean(a)-st.mean(b)) if a and b else float('nan')))

def perm_p_day(dl, obs):
    N = len(DAYS); cnt = tot = 0
    for sh in range(1, N):
        s1 = c1 = s0 = c0 = 0.0
        for i in range(N):
            if dl[(i+sh) % N]: s1 += DSUM[i]; c1 += DCNT[i]
            else:              s0 += DSUM[i]; c0 += DCNT[i]
        if c1 < 50 or c0 < 50: continue
        tot += 1
        if abs(s1/c1 - s0/c0) >= abs(obs)-1e-12: cnt += 1
    return (cnt+1)/(tot+1), tot

def perm_p_cross(reg, nq, obs):
    N = len(DAYS); cnt = tot = 0
    for sh in range(1, N):
        shifted = {DAYS[i]: F[DAYS[(i+sh) % N]]['IXIC'] for i in range(N)}
        s1 = c1 = s0 = c0 = 0.0
        for e, val, r in zip(EV, NET, REG_EV):
            if cross_ok(r, shifted[e['entry_date']], reg, nq): s1 += val; c1 += 1
            else:                                             s0 += val; c0 += 1
        if c1 < 50 or c0 < 50: continue
        tot += 1
        if abs(s1/c1 - s0/c0) >= abs(obs)-1e-12: cnt += 1
    return (cnt+1)/(tot+1), tot

SEEDS_OBS = 200; SHIFTS = 150; SEEDS_SH = 5
def eq_med(events, seeds): return st.median([sim(events, seed=s)[0] for s in seeds])

def equity_test(mask, dl=None, cross=None):
    sub = [e for e, m in zip(EV, mask) if m]
    obs = eq_med(sub, range(SEEDS_OBS))
    rnd = random.Random(12345); N = len(DAYS); null = []
    for k in range(SHIFTS):
        sh = rnd.randrange(1, N)
        if cross is None:
            lab = {DAYS[i]: dl[(i+sh) % N] for i in range(N)}
            s2 = [e for e in EV if lab[e['entry_date']]]
        else:
            reg, nq = cross
            shifted = {DAYS[i]: F[DAYS[(i+sh) % N]]['IXIC'] for i in range(N)}
            s2 = [e for e, r in zip(EV, REG_EV) if cross_ok(r, shifted[e['entry_date']], reg, nq)]
        if len(s2) < 50: continue
        null.append(st.median([sim(s2, seed=1000*k+j)[0] for j in range(SEEDS_SH)]))
    null.sort()
    beat = sum(1 for x in null if x < obs)/len(null)*100 if null else float('nan')
    return obs, (st.median(null) if null else float('nan')), beat

BASE_EQ = eq_med(EV, range(SEEDS_OBS))
print("[base] all 3681  net %+.3f%%  wr %.1f%%  slot5 %+.1f%%" % (
    st.mean(NET), sum(1 for e in EV if e['result'] == 'win')/len(EV)*100, BASE_EQ))
sys.stdout.flush()

rows = []
for v in V:
    dl = [bool(v['fn'](d)) if v['fn'](d) is not None else False for d in DAYS]
    mask = [dl[DIDX[e['entry_date']]] for e in EV]
    s = stats_from_mask(mask)
    p, tot = perm_p_day(dl, s['diff'])
    eq, eqn, beat = equity_test(mask, dl=dl)
    rows.append(dict(g=v['g'], name=v['name'], days=sum(dl), p=p, eq=eq, eq_null=eqn, eq_beat=beat, **s))
    print("  %-8s %-28s n=%5d wr=%5.1f%% net=%+6.2f%% d=%+6.2f%%p p=%.4f eq=%+8.1f%% null=%+8.1f%% beat=%.0f%%"
          % (v['g'], v['name'], s['n'], s['wr'], s['net'], s['diff'], p, eq, eqn, beat))
    sys.stdout.flush()

for g, name, reg, nq in CROSS:
    mask = [cross_ok(r, F[e['entry_date']]['IXIC'], reg, nq) for e, r in zip(EV, REG_EV)]
    s = stats_from_mask(mask)
    p, tot = perm_p_cross(reg, nq, s['diff'])
    eq, eqn, beat = equity_test(mask, cross=(reg, nq))
    rows.append(dict(g=g, name=name, days=None, p=p, eq=eq, eq_null=eqn, eq_beat=beat, **s))
    print("  %-8s %-28s n=%5d wr=%5.1f%% net=%+6.2f%% d=%+6.2f%%p p=%.4f eq=%+8.1f%% null=%+8.1f%% beat=%.0f%%"
          % (g, name, s['n'], s['wr'], s['net'], s['diff'], p, eq, eqn, beat))
    sys.stdout.flush()

json.dump(dict(base_eq=BASE_EQ, base_net=st.mean(NET), rows=rows),
          open('variants_out.json', 'w'), ensure_ascii=False, indent=1)
print("\nTOTAL VARIANTS:", len(rows))
