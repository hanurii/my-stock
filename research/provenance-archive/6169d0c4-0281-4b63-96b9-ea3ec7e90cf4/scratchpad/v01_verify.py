# -*- coding: utf-8 -*-
"""01번 독립 검증 — 조사 세션 스크립트를 쓰지 않고 산출물만으로 다시 판정한다."""
import json, glob, os, collections, statistics as st

BT = '.cache/bt5y'
OUT = BT + '/out'

# 1) 원본 이벤트
ev = {}
for f in sorted(glob.glob(BT + '/bt_*.json')):
    for e in json.load(open(f, encoding='utf-8'))['events']:
        ev[(e['scan_date'], e['code'], e['pattern'])] = e
print('원본 이벤트 키 %d' % len(ev))

def replay(h, l, c, E, tp, sp):
    """pivot_backtest.simulate_pivot_trade 를 사양서만 보고 새로 구현."""
    T = E * (1 + tp / 100.0)
    S = E * (1 - sp / 100.0)
    n = len(c)
    def out(kind, i, reason):
        return (kind, i, round((c[i] / E - 1) * 100, 2),
                round((max(h[:i+1]) / E - 1) * 100, 2),
                round((min(l[:i+1]) / E - 1) * 100, 2), reason)
    ht, hs = h[0] >= T, l[0] <= S
    if ht and hs: return out('ambiguous', 0, 'both_same_day_breakout')
    if ht:        return out('win', 0, 'target')
    if hs:        return out('ambiguous', 0, 'stop_on_breakout_day')
    for i in range(1, n):
        ht, hs = h[i] >= T, l[i] <= S
        if ht and hs: return out('ambiguous', i, 'both_same_day')
        if ht:        return out('win', i, 'target')
        if hs:        return out('loss', i, 'stop')
    return out('unresolved', n - 1, 'open')

def margin(h, l, E, tp, sp):
    """결착까지 훑으며 문턱과의 최소 상대거리. 0.0 = 정확한 등호."""
    T = E * (1 + tp / 100.0); S = E * (1 - sp / 100.0)
    m = float('inf')
    for i in range(len(h)):
        m = min(m, abs(h[i] - T) / T, abs(l[i] - S) / S)
        if h[i] >= T or l[i] <= S:
            break
    return m

GRID = [(t, s) for t in (15, 20, 25, 30, 40, 50) for s in (5, 7, 10, 12)]

gate = collections.Counter(); mism = []
struct = collections.Counter(); structbad = []
lens = []; gapinfo = collections.Counter()
tie = {g: collections.Counter() for g in GRID}
flip = {g: collections.Counter() for g in GRID}
tie_examples = []
n_paths = 0
keys_seen = set()

for y in (2021, 2022, 2023, 2024, 2025, 2026):
    fp = OUT + '/paths_%d.json' % y
    d = json.load(open(fp, encoding='utf-8'))
    for p in d['paths']:
        n_paths += 1
        k = (p['scan_date'], p['code'], p['pattern'])
        keys_seen.add(k)
        e = ev.get(k)
        if e is None:
            structbad.append(('이벤트에 없는 경로', k)); continue
        h, l, c, o = p['h'], p['l'], p['c'], p['o']
        E = p['entry_price']
        lens.append(len(c))

        # --- 구조 점검 ---
        if p['dates'][0] != e['entry_date']: struct['첫날≠entry_date'] += 1
        if len(set(map(len, (p['dates'], o, h, l, c, p['ma20'])))) != 1: struct['배열길이불일치'] += 1
        if any(v is None for v in o + h + l + c): struct['가격 None'] += 1
        if any(not (l[i] <= min(o[i], c[i]) and h[i] >= max(o[i], c[i])) for i in range(len(c))):
            struct['OHLC 모순'] += 1
        if list(p['dates']) != sorted(p['dates']): struct['날짜 비단조'] += 1
        epx_calc = max(e['pivot'], o[0])
        if abs(epx_calc - E) > 1e-9: struct['entry_price≠max(pivot,o0)'] += 1
        gapinfo['gap' if E > e['pivot'] + 1e-12 else 'nogap'] += 1
        # ma20: 20일 이상 지난 지점만 자체 검산 가능
        for j in (19, 40, 80):
            if j < len(c) and p['ma20'][j] is not None:
                if abs(p['ma20'][j] - sum(c[j-19:j+1]) / 20) > 1e-6 * abs(p['ma20'][j]):
                    struct['ma20 불일치'] += 1
                    break

        # --- 관문 재현 (현행 +20/-10) ---
        r = replay(h, l, c, E, 20.0, 10.0)
        chk = {'result': (r[0], e['result']), 'days_held': (r[1], e['days_held']),
               'gain': (r[2], e['gain_at_resolve_pct']), 'max_gain': (r[3], e['max_gain_pct']),
               'max_dd': (r[4], e['max_dd_pct']),
               'entry_price': (round(E, 2), e['entry_price'])}
        bad = [(f, a, b) for f, (a, b) in chk.items() if a != b]
        for f, (a, b) in chk.items():
            gate['%s_%s' % (f, 'ok' if a == b else 'NG')] += 1
        if bad: mism.append((k, e.get('name'), bad))

        # --- 24칸 등호·부동소수 취약성 ---
        for (tp, sp) in GRID:
            m = margin(h, l, E, tp, sp)
            if m == 0.0: tie[(tp, sp)]['exact'] += 1
            if m < 1e-12: tie[(tp, sp)]['lt1e-12'] += 1
            if m < 1e-9: tie[(tp, sp)]['lt1e-9'] += 1
            if m < 1e-7: tie[(tp, sp)]['lt1e-7'] += 1
            if m < 1e-5: tie[(tp, sp)]['lt1e-5'] += 1
            if m == 0.0 and len(tie_examples) < 15:
                tie_examples.append((k, e.get('name'), tp, sp, E))
            # 피벗 2자리 반올림 오차(±0.005)로 판정이 뒤집히는가 — 갭업 아닌 건만 해당
            base = replay(h, l, c, E, tp, sp)
            for dE in (0.005, -0.005):
                alt = replay(h, l, c, E + dE, tp, sp)
                if alt[0] != base[0] or alt[1] != base[1]:
                    flip[(tp, sp)]['pivot±0.005'] += 1
                    break
            for rel in (1e-9, -1e-9):
                alt = replay(h, l, c, E * (1 + rel), tp, sp)
                if alt[0] != base[0] or alt[1] != base[1]:
                    flip[(tp, sp)]['rel1e-9'] += 1
                    break
    del d
    print('  %d 완료 (누적 %d)' % (y, n_paths), flush=True)

print()
print('경로 %d건 / 원본키 %d건 / 경로에만 %d / 원본에만 %d'
      % (n_paths, len(ev), len(keys_seen - set(ev)), len(set(ev) - keys_seen)))
print('관문:', {k: v for k, v in sorted(gate.items()) if k.endswith('NG')} or '불일치 0')
print('  일치:', {k: v for k, v in sorted(gate.items()) if k.endswith('ok')})
print('불일치 예:', mism[:5])
print('구조 이상:', dict(struct) or '없음', ' 기타:', structbad[:3])
lens.sort()
print('경로 길이: 최소 %d 중앙 %d 최대 %d / 4일미만 %d'
      % (lens[0], lens[len(lens)//2], lens[-1], sum(1 for x in lens if x < 4)))
print('갭업 진입 %d / 비갭업 %d' % (gapinfo['gap'], gapinfo['nogap']))
print()
print('=== 24칸 등호·취약성 (건수) ===')
print('%-10s %6s %8s %8s %8s %8s | %10s %8s' % ('칸','정확등호','<1e-12','<1e-9','<1e-7','<1e-5','피벗±.005','rel1e-9'))
for g in GRID:
    t = tie[g]; f = flip[g]
    print('+%d/-%-6d %6d %8d %8d %8d %8d | %10d %8d'
          % (g[0], g[1], t['exact'], t['lt1e-12'], t['lt1e-9'], t['lt1e-7'], t['lt1e-5'],
             f['pivot±0.005'], f['rel1e-9']))
print()
print('정확 등호 예시:', tie_examples[:10])
