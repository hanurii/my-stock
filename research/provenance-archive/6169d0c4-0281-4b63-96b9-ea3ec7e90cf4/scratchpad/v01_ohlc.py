# -*- coding: utf-8 -*-
"""OHLC 모순의 크기를 잰다 — 부동소수 잡음인가, 자료 문제인가."""
import json, collections
worst = []
cnt = collections.Counter()
rels = []
for y in (2021, 2022, 2023, 2024, 2025, 2026):
    d = json.load(open('.cache/bt5y/out/paths_%d.json' % y, encoding='utf-8'))
    for p in d['paths']:
        o, h, l, c = p['o'], p['h'], p['l'], p['c']
        for i in range(len(c)):
            hi_need = max(o[i], c[i]); lo_need = min(o[i], c[i])
            if h[i] < hi_need:
                r = (hi_need - h[i]) / h[i]; cnt['high<max(o,c)'] += 1; rels.append(r)
                worst.append((r, 'high', p['code'], p['dates'][i], o[i], h[i], l[i], c[i]))
            if l[i] > lo_need:
                r = (l[i] - lo_need) / l[i]; cnt['low>min(o,c)'] += 1; rels.append(r)
                worst.append((r, 'low', p['code'], p['dates'][i], o[i], h[i], l[i], c[i]))
    del d
rels.sort()
worst.sort(reverse=True)
print('위반 일수 합계:', dict(cnt), ' 총', len(rels))
if rels:
    print('상대 크기: 최소 %.3e / 중앙 %.3e / P99 %.3e / 최대 %.3e'
          % (rels[0], rels[len(rels)//2], rels[int(len(rels)*.99)], rels[-1]))
    print('1e-12 초과 건수:', sum(1 for r in rels if r > 1e-12),
          ' 1e-9 초과:', sum(1 for r in rels if r > 1e-9),
          ' 1e-6 초과:', sum(1 for r in rels if r > 1e-6))
    print('\n가장 큰 위반 5건:')
    for w in worst[:5]:
        print('  rel=%.3e %s %s %s  o=%r h=%r l=%r c=%r' % w)
