# -*- coding: utf-8 -*-
"""12a 독립 검증 — 조사 세션의 복사본이 아니라 실제 cmp_exit.py 를 불러 대조한다."""
import json, sys, os, random, statistics as st, importlib.util, collections
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim

BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"

# ── 실제 cmp_exit.py 를 불러온다 (경로 상수만 환경변수로 맞춰 준다) ──
os.environ['LOCALAPPDATA'] = os.path.dirname(os.path.dirname(BT))  # → .../.cache 상위
spec = importlib.util.spec_from_file_location("cmp_exit_real", BT + r"\cmp_exit.py")
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)   # 모듈 최상단에서 표를 출력하므로 stdout 을 잠시 죽인다
except SystemExit:
    pass
print("cmp_exit.py 적재 완료. B =", m.B)

ev = []
for y in range(2021, 2027):
    ev += [e for e in json.load(open(BT + r"\bt_%d.json" % y, encoding='utf-8'))['events']
           if e['result'] in ('win', 'loss')]
seen, U = set(), []
for e in sorted(ev, key=lambda x: (x['entry_date'], x['code'])):
    k = (e['scan_date'], e['code'], e['pattern'])
    if k not in seen:
        seen.add(k); U.append(e)
ev = U
print("확정 거래", len(ev))
trades = [{"code": e["code"], "pattern": e["pattern"], "scan_date": e["scan_date"],
           "entry_date": e["entry_date"], "resolve_date": e["resolve_date"],
           "gain": e["gain_at_resolve_pct"], "result": e["result"]} for e in ev]

# ── [1] 실제 cmp_exit.sim vs slot_sim(stream+sameday+input) ──
d_eq = d_n = d_mdd = 0.0
for s in range(50):
    o = m.sim(ev, seed=s)                       # ← 진짜 옛 정본
    nn = slot_sim.sim(trades, seed=s, rng_mode="stream", reuse="sameday", base_order="input")
    d_eq = max(d_eq, abs(o[0] - nn["equity_pct"]))
    d_n = max(d_n, abs(o[1] - nn["n_filled"]))
    d_mdd = max(d_mdd, abs(o[3] - nn["mdd_pct"]))
print("[1] 진짜 cmp_exit.sim 대조(seed 50): 자산곡선 최대차 %.12f · 체결수 최대차 %d · 낙폭 최대차 %.12f"
      % (d_eq, d_n, d_mdd))
print("    참고 seed0 체결수: 옛 %d" % m.sim(ev, seed=0)[1])

# ── [2] 조합별 seed 배열 (200) ──
CFG = {
 '①stream+sameday': dict(rng_mode='stream', reuse='sameday'),
 '②perdate+sameday': dict(rng_mode='perdate', reuse='sameday'),
 '③stream+nextday': dict(rng_mode='stream', reuse='nextday'),
 '④perdate+nextday': dict(rng_mode='perdate', reuse='nextday'),
 '⑤perdate+슬롯만익일': dict(rng_mode='perdate', reuse='nextday_cash_today'),
}
N = 200
res = {}
for k, kw in CFG.items():
    res[k] = [slot_sim.sim(trades, seed=i, base_order='canonical', **kw) for i in range(N)]
    e = sorted(r['equity_pct'] for r in res[k])
    print("%-22s 중앙 %+7.1f%%  5~95%% %+7.1f ~ %+7.1f  체결중앙 %.0f"
          % (k, st.median(e), e[N//20-1], e[N-N//20], st.median(r['n_filled'] for r in res[k])))

# ①은 base_order='input' 으로도 확인
e_in = sorted(slot_sim.sim(trades, seed=i, rng_mode='stream', reuse='sameday',
                           base_order='input')['equity_pct'] for i in range(N))
print("①(base_order=input) 중앙 %+.4f%%   vs ①(canonical) 중앙 %+.4f%%"
      % (st.median(e_in), st.median(r['equity_pct'] for r in res['①stream+sameday'])))

# ── [3] 짝비교(같은 seed) — 중앙값 차이가 아니라 차이의 분포 ──
def paired(a, b):
    d = [res[a][i]['equity_pct'] - res[b][i]['equity_pct'] for i in range(N)]
    ds = sorted(d)
    return (sum(1 for x in d if x > 0) / N * 100, st.median(d), ds[N//20-1], ds[N-N//20])
print("\n[3] 같은 seed 짝비교 (200회)")
for a, b in [('③stream+nextday','①stream+sameday'), ('④perdate+nextday','②perdate+sameday'),
             ('②perdate+sameday','①stream+sameday'), ('⑤perdate+슬롯만익일','④perdate+nextday')]:
    w, md, lo, hi = paired(a, b)
    print("   %-22s vs %-22s 우세율 %5.1f%%  차이중앙 %+7.1f%p  5~95%% %+7.1f ~ %+7.1f"
          % (a, b, w, md, lo, hi))
