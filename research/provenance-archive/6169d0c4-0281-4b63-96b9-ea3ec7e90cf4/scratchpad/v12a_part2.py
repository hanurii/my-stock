# -*- coding: utf-8 -*-
"""12a 검증 2부 — 짝비교 분포 · 집중도 · 셔플 불변성 · 같은날 재진입 거래 목록."""
import json, sys, random, statistics as st, collections
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"

ev = []
for y in range(2021, 2027):
    ev += [e for e in json.load(open(BT + r"\bt_%d.json" % y, encoding='utf-8'))['events']
           if e['result'] in ('win', 'loss')]
seen, U = set(), []
for e in sorted(ev, key=lambda x: (x['entry_date'], x['code'])):
    k = (e['scan_date'], e['code'], e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
trades = [{"code": e["code"], "pattern": e["pattern"], "scan_date": e["scan_date"],
           "entry_date": e["entry_date"], "resolve_date": e["resolve_date"],
           "gain": e["gain_at_resolve_pct"], "result": e["result"]} for e in U]
N = 200
CFG = {'①': dict(rng_mode='stream', reuse='sameday'),
       '②': dict(rng_mode='perdate', reuse='sameday'),
       '③': dict(rng_mode='stream', reuse='nextday'),
       '④': dict(rng_mode='perdate', reuse='nextday'),
       '⑤': dict(rng_mode='perdate', reuse='nextday_cash_today')}

def runs(tr, keys=CFG, n=N):
    return {k: [slot_sim.sim(tr, seed=i, base_order='canonical', **kw)['equity_pct']
                for i in range(n)] for k, kw in keys.items()}
R = runs(trades)

def paired(a, b, R=R):
    d = [R[a][i] - R[b][i] for i in range(N)]; ds = sorted(d)
    return (sum(1 for x in d if x > 0)/N*100, st.median(d), ds[N//20-1], ds[N-N//20])

print("[3] 같은 seed 짝비교 200회 — 차이의 분포 (중앙값 두 개의 뺄셈이 아님)")
for a, b, lab in [('③','①','재진입 고침만'), ('④','②','재진입 고침만(난수고침 위에서)'),
                  ('②','①','난수 고침만'), ('④','①','둘 다 = 정본 vs 옛'),
                  ('⑤','④','손익 반영 시점')]:
    w, md, lo, hi = paired(a, b)
    print("   %s vs %s (%-22s) 우세율 %5.1f%%  차이중앙 %+7.1f  5~95%% %+7.1f ~ %+7.1f"
          % (a, b, lab, w, md, lo, hi))

# ── [4] 집중도: 순수익 상위 k건을 표본에서 빼고 다시 ──
print("\n[4] 집중도 렌즈 — 기여 상위 거래를 빼면 차이가 남는가")
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
order_by_net = sorted(range(len(trades)), key=lambda i: -net(trades[i]['gain']))
for k in (0, 5, 10, 20):
    drop = set(order_by_net[:k])
    tr = [t for i, t in enumerate(trades) if i not in drop]
    Rk = runs(tr, {'①': CFG['①'], '③': CFG['③'], '④': CFG['④']})
    d31 = [Rk['③'][i] - Rk['①'][i] for i in range(N)]
    d41 = [Rk['④'][i] - Rk['①'][i] for i in range(N)]
    print("   상위 %2d건 제거: ①중앙 %+7.1f · ③중앙 %+7.1f · ④중앙 %+7.1f | ③-① 중앙 %+6.1f 우세율 %5.1f%% | ④-① 중앙 %+6.1f 우세율 %5.1f%%"
          % (k, st.median(Rk['①']), st.median(Rk['③']), st.median(Rk['④']),
             st.median(d31), sum(1 for x in d31 if x>0)/N*100,
             st.median(d41), sum(1 for x in d41 if x>0)/N*100))

# ── [5] 같은 날 재진입이 실제로 몇 번, 어떤 거래였나 ──
print("\n[5] '같은 날 결착 → 같은 날 재진입'이 실제로 일어난 횟수 (seed 0~9)")
def sameday_refills(tr, seed):
    byday = slot_sim._byday(tr, 'canonical')
    dates = sorted(set(list(byday) + [t['resolve_date'] for t in tr]))
    rnd = random.Random(seed); eq = 1.0; held = []; hits = []
    for d in dates:
        done = [h for h in held if h[0] <= d]
        held = [h for h in held if h[0] > d]
        for rd, t, wg in done: eq += wg*net(t['gain'])/100
        free = slots = 5 - len(held)
        if free > 0 and d in byday:
            c = byday[d][:]; rnd.shuffle(c)
            taken = c[:free]
            # 오늘 결착으로 생긴 슬롯 수만큼은 '같은 날 재진입'
            k = min(len(done), len(taken))
            for t in taken[:k]:
                hits.append((d, t['code'], t['result'], round(net(t['gain']), 1)))
            for t in taken: held.append((t['resolve_date'], t, eq/5))
    return hits
tot = []
for s in range(10):
    hs = sameday_refills(trades, s); tot.append(len(hs))
    if s == 0:
        wins = [x for x in hs if x[2] == 'win']
        print("   seed0: 같은날 재진입 %d회 (승 %d · 패 %d), 순수익 합 %+.1f%%p, 최대 1건 %+.1f%%"
              % (len(hs), len(wins), len(hs)-len(wins), sum(x[3] for x in hs),
                 max((x[3] for x in hs), default=0)))
        print("   seed0 상위 5건:", sorted(hs, key=lambda x: -x[3])[:5])
print("   seed0~9 같은날 재진입 횟수: %s (중앙 %.0f)" % (tot, st.median(tot)))

# ── [6] perdate 셔플이 규칙이 바뀌어도 같은 순서를 주는가 ──
print("\n[6] 셔플 불변성 탐침")
import copy
V = copy.deepcopy(trades)
ds = sorted({t['entry_date'] for t in trades} | {t['resolve_date'] for t in trades})
idx = {d: i for i, d in enumerate(ds)}
V[0]['resolve_date'] = ds[min(idx[V[0]['resolve_date']]+1, len(ds)-1)]   # 한 건만 하루 미룸
same = diff = 0
for d in sorted({t['entry_date'] for t in trades}):
    a = [t['code'] for t in slot_sim._byday(trades, 'canonical')[d]]
    b = [t['code'] for t in slot_sim._byday(V, 'canonical')[d]]
    ra, rb = a[:], b[:]
    random.Random("%d|%s" % (0, d)).shuffle(ra)
    random.Random("%d|%s" % (0, d)).shuffle(rb)
    if ra == rb: same += 1
    else: diff += 1
print("   같은 유니버스·결착일만 다름 → 날짜별 후보 순서 동일 %d일 / 다름 %d일" % (same, diff))
# 유니버스가 다르면?
W = [t for t in trades if not (t['entry_date'] == trades[5]['entry_date'] and t['code'] == trades[5]['code'])]
dd = trades[5]['entry_date']
a = [t['code'] for t in slot_sim._byday(trades, 'canonical')[dd]]
b = [t['code'] for t in slot_sim._byday(W, 'canonical')[dd]]
ra, rb = a[:], b[:]
random.Random("%d|%s" % (0, dd)).shuffle(ra); random.Random("%d|%s" % (0, dd)).shuffle(rb)
print("   유니버스가 1건 다른 날 %s: 원본순서 %s → %s / 축소순서 %s → %s"
      % (dd, a, ra, b, rb))
print("   공통 종목의 상대 순서 유지? %s"
      % ([x for x in ra if x in rb] == [x for x in rb if x in ra]))
