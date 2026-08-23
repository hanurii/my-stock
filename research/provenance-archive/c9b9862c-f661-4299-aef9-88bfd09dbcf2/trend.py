# -*- coding: utf-8 -*-
"""크기 단조성 검정 + 자산곡선 다중검정 보정."""
from base import *
import json, statistics as st, collections

EV, _ = load_events()
NET = [FEE(e['gain_at_resolve_pct']) for e in EV]
DAYS = sorted({e['entry_date'] for e in EV})
F = {d: feat('IXIC', d) for d in DAYS}
RET = {d: (F[d]['ret'] if F[d] else None) for d in DAYS}

# 1) 크기 단조성: 나스닥 수익률과 거래당 순수익의 상관 (일 단위 원형이동 순열)
xs = [RET[e['entry_date']] for e in EV]
pairs = [(x, v) for x, v in zip(xs, NET) if x is not None]
n = len(pairs)
mx = st.mean([p[0] for p in pairs]); my = st.mean([p[1] for p in pairs])
num = sum((a-mx)*(b-my) for a, b in pairs)
den = (sum((a-mx)**2 for a, b in pairs)*sum((b-my)**2 for a, b in pairs))**0.5
obs_r = num/den
DSUM = collections.defaultdict(float); DCNT = collections.Counter()
for e, v in zip(EV, NET): DSUM[e['entry_date']] += v; DCNT[e['entry_date']] += 1
N = len(DAYS); cnt = tot = 0
for sh in range(1, N):
    px = [RET[DAYS[(i+sh) % N]] for i in range(N)]
    P = [(px[i], DAYS[i]) for i in range(N) if px[i] is not None]
    tx = []; ty = []
    for x, d in P:
        for _ in range(DCNT[d]): tx.append(x)
        ty.append(DSUM[d])
    # 가중 상관 (일 합계 사용)
    wx = [x for x, d in P]; wc = [DCNT[d] for x, d in P]; ws = [DSUM[d] for x, d in P]
    tn = sum(wc); mX = sum(x*c for x, c in zip(wx, wc))/tn; mY = sum(ws)/tn
    nu = sum((x-mX)*(s-c*mY) for x, c, s in zip(wx, wc, ws))
    d1 = sum(c*(x-mX)**2 for x, c in zip(wx, wc))
    tot += 1
    if abs(nu) >= abs(num)-1e-9 and d1 > 0: cnt += 1
print("나스닥 수익률 vs 거래당 순수익 상관 r = %+.4f  (n=%d)  원형이동 순열 p = %.4f"
      % (obs_r, n, (cnt+1)/(tot+1)))

print("\n크기 6구간 평균 (단조성 눈으로 확인):")
bands = [('<= -1.0%', lambda x: x < -1.0), ('-1.0~-0.5', lambda x: -1.0 <= x < -0.5),
         ('-0.5~0', lambda x: -0.5 <= x <= 0.0), ('0~+0.5', lambda x: 0.0 < x < 0.5),
         ('+0.5~+1.0', lambda x: 0.5 <= x < 1.0), ('>= +1.0%', lambda x: x >= 1.0)]
for lab, f in bands:
    g = [v for x, v in pairs if f(x)]
    print("  %-12s n=%4d  거래당 %+6.2f%%" % (lab, len(g), st.mean(g)))

# 2) 자산곡선 백분위에도 BH 적용
out = json.load(open('variants_out.json', encoding='cp949'))
rows = [r for r in out['rows'] if r['name'] != '국면상승만(나스닥 무시.참조)']
eqp = sorted(((100-r['eq_beat'])/100, r['name'], r['eq'], r['eq_null']) for r in rows)
m = len(eqp)
print("\n=== 자산곡선(널 대비 상위백분위 = 단측 p) 다중검정 보정, m=%d ===" % m)
surv = 0
for k, (p, nm, eq, nl) in enumerate(eqp[:6], 1):
    thr = 0.05*k/m
    if p <= thr: surv = k
    print("  %2d  p=%.3f  BH문턱 %.5f  %s %-26s 슬롯5 %+.1f%% (널 %+.1f%%)"
          % (k, p, thr, 'YES' if p <= thr else 'no ', nm, eq, nl))
print("  BH 생존 %d개 / Bonferroni 문턱 %.5f 생존 %d개"
      % (surv, 0.05/m, sum(1 for p, *_ in eqp if p <= 0.05/m)))
print("  (자산곡선 백분위는 150회 원형이동 널이라 분해능 하한 p=0.007)")
