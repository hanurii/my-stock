# -*- coding: utf-8 -*-
"""짝비교 재현성 탐침 — 성과는 계산하지 않는다. '같은 seed면 같은 후보를 뽑는가'만 본다."""
import json, glob, random, collections, copy

ev = []
for f in sorted(glob.glob('.cache/bt5y/bt_*.json')):
    ev += json.load(open(f, encoding='utf-8'))['events']
seen = set(); U = []
for e in sorted(ev, key=lambda x: (x['entry_date'], x['code'])):
    k = (e['scan_date'], e['code'], e['pattern'])
    if k not in seen:
        seen.add(k); U.append(e)
R = [e for e in U if e['result'] in ('win', 'loss')]

def picks(events, slots=5, seed=0):
    """cmp_exit.sim()과 같은 순서 로직. 성과 대신 '뽑힌 거래 목록'만 반환."""
    byday = collections.defaultdict(list)
    for e in events:
        byday[e['entry_date']].append(e)
    rnd = random.Random(seed); held = []; taken = []; shuffles = 0
    for d in sorted(set(list(byday) + [e['resolve_date'] for e in events])):
        held = [h for h in held if h[0] > d]
        free = slots - len(held)
        if free > 0 and d in byday:
            c = byday[d][:]; rnd.shuffle(c); shuffles += 1
            for e in c[:free]:
                held.append((e['resolve_date'], e))
                taken.append((e['entry_date'], e['code']))
    return taken, shuffles

base, sh0 = picks(R, seed=0)
same, sh1 = picks(R, seed=0)
print('sanity  base vs base : identical =', base == same, ' shuffles =', sh0)

# 변형 흉내: 단 한 건의 resolve_date만 하루 미룬다(성과는 안 본다)
dates = sorted({e['entry_date'] for e in R} | {e['resolve_date'] for e in R})
idx = {d: i for i, d in enumerate(dates)}
V = copy.deepcopy(R)
tgt = V[0]
tgt['resolve_date'] = dates[min(idx[tgt['resolve_date']] + 1, len(dates) - 1)]
vt, sh2 = picks(V, seed=0)
print('one-trade perturbation: 첫 거래 %s %s  resolve %s -> %s'
      % (R[0]['entry_date'], R[0]['code'], R[0]['resolve_date'], tgt['resolve_date']))
sb, sv = set(base), set(vt)
print('  taken base=%d  variant=%d  공통=%d  base에만=%d  variant에만=%d  shuffles %d vs %d'
      % (len(base), len(vt), len(sb & sv), len(sb - sv), len(sv - sb), sh0, sh2))
# 앞에서 몇 번째 픽부터 갈라지는가
for i, (a, b) in enumerate(zip(base, vt)):
    if a != b:
        print('  첫 불일치 픽 순번:', i, a, b); break
