# -*- coding: utf-8 -*-
import json, sys, random, statistics as st
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
ev = []
for y in range(2021, 2027):
    ev += [e for e in json.load(open(BT + r"\bt_%d.json" % y, encoding='utf-8'))['events']
           if e['result'] in ('win','loss')]
seen, U = set(), []
for e in sorted(ev, key=lambda x: (x['entry_date'], x['code'])):
    k = (e['scan_date'], e['code'], e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
trades = [{"code": e["code"], "pattern": e["pattern"], "scan_date": e["scan_date"],
           "entry_date": e["entry_date"], "resolve_date": e["resolve_date"],
           "gain": e["gain_at_resolve_pct"], "result": e["result"]} for e in U]
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100

def picks(tr, seed, reuse, rng_mode='stream'):
    byday = slot_sim._byday(tr, 'canonical')
    dates = sorted(set(list(byday) + [t['resolve_date'] for t in tr]))
    rnd = random.Random(seed); eq = 1.0; held = []; taken = []
    for d in dates:
        if reuse == 'sameday':
            done = [h for h in held if h[0] <= d]; held = [h for h in held if h[0] > d]
        else:
            done = [h for h in held if h[0] < d];  held = [h for h in held if h[0] >= d]
        for rd, t, wg in done: eq += wg*net(t['gain'])/100
        free = 5 - len(held)
        if d in byday:
            c = byday[d][:]
            if rng_mode == 'perdate': random.Random("%d|%s" % (seed, d)).shuffle(c)
            elif free > 0: rnd.shuffle(c)
            if free > 0:
                for t in c[:free]:
                    held.append((t['resolve_date'], t, eq/5)); taken.append((t['entry_date'], t['code']))
    return taken

ov = []
for s in range(20):
    a = set(picks(trades, s, 'sameday')); b = set(picks(trades, s, 'nextday'))
    ov.append((len(a), len(b), len(a & b)))
print("[7] 같은 seed에서 ①과 ③이 실제로 산 거래 (seed 0~19)")
print("    ① 체결 중앙 %d · ③ 체결 중앙 %d · 공통 중앙 %d (공통 비율 중앙 %.0f%%)"
      % (st.median(x[0] for x in ov), st.median(x[1] for x in ov), st.median(x[2] for x in ov),
         st.median(100*x[2]/x[0] for x in ov)))
print("    seed0: ① %d건 · ③ %d건 · 공통 %d건 → 서로 다른 거래 %d건"
      % (ov[0][0], ov[0][1], ov[0][2], ov[0][0]+ov[0][1]-2*ov[0][2]))

print("\n[8] 유니버스가 달라져도 상대 순서를 지키는 대안 (키 정렬)")
d0 = trades[5]['entry_date']
full = slot_sim._byday(trades, 'canonical')[d0]
less = [t for t in full if t['code'] != trades[5]['code']]
def keyorder(lst, seed):
    return [t['code'] for t in sorted(lst, key=lambda t: random.Random(
        "%d|%s|%s|%s" % (seed, t['code'], t['scan_date'], t['pattern'])).random())]
a, b = keyorder(full, 0), keyorder(less, 0)
print("    전체 %s" % a)
print("    1건 뺀 것 %s" % b)
print("    공통 종목의 상대 순서 유지? %s" % ([x for x in a if x in b] == b))
