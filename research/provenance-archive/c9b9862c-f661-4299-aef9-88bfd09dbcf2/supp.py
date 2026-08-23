# -*- coding: utf-8 -*-
"""보정 적용 + 근접 셀 정밀 검증."""
from base import *
import json, statistics as st, random, collections, sys

EV, _ = load_events()
NET = [FEE(e['gain_at_resolve_pct']) for e in EV]
DAYS = sorted({e['entry_date'] for e in EV})
DIDX = {d: i for i, d in enumerate(DAYS)}
F = {d: feat('IXIC', d) for d in DAYS}
REG = [UP.get(e['scan_date']) for e in EV]
REGKS = [UPKS.get(e['scan_date']) for e in EV]

out = json.load(open('variants_out.json', encoding='cp949'))
rows = out['rows']
# 참조행(국면만)은 나스닥 순열이 라벨을 안 바꾸므로 검정 불가 -> 제외 표시
fam = [r for r in rows if r['name'] != '국면상승만(나스닥 무시.참조)']
ps = sorted((r['p'], r['name']) for r in fam)
m = len(fam)
print("=== 다중검정 보정 (검정 가능한 변형 %d개; 참조행 1개는 순열 불가로 제외) ===" % m)
print("Bonferroni 문턱 alpha/m = %.5f" % (0.05/m))
print("BH: rank  p        BH문턱(0.05*k/m)  통과?   변형")
surv = 0
for k, (p, nm) in enumerate(ps, 1):
    thr = 0.05*k/m
    ok = p <= thr
    if ok: surv = k
    print("   %2d  %.4f  %.5f   %s  %s" % (k, p, thr, 'YES' if ok else 'no ', nm))
    if k >= 8: print("   ... (나머지 %d개 전부 p>%.3f)" % (m-8, ps[8][0])); break
print("BH 생존 개수: %d   Bonferroni 생존 개수: %d" % (surv, sum(1 for p, _ in ps if p <= 0.05/m)))
print("보정 전 p<0.05 였던 변형: %s" % [nm for p, nm in ps if p < 0.05])

# ---- 조건부 검정: 국면 안에서 나스닥이 뭔가 더하나 ----
print("\n=== 조건부(국면 고정) 나스닥 효과 ===")
def perm_cond(regval, obs):
    N = len(DAYS); cnt = tot = 0
    for sh in range(1, N):
        shifted = {DAYS[i]: F[DAYS[(i+sh) % N]] for i in range(N)}
        s1 = c1 = s0 = c0 = 0.0
        for e, v, r in zip(EV, NET, REG):
            if r is not regval: continue
            f = shifted[e['entry_date']]
            if f is None: continue
            if f['ret'] > 0: s1 += v; c1 += 1
            else:            s0 += v; c0 += 1
        if c1 < 50 or c0 < 50: continue
        tot += 1
        if abs(s1/c1 - s0/c0) >= abs(obs)-1e-12: cnt += 1
    return (cnt+1)/(tot+1)

for regval, lab in [(True, '국면 상승 안에서'), (False, '국면 조정 안에서')]:
    a = [v for e, v, r in zip(EV, NET, REG) if r is regval and F[e['entry_date']] and F[e['entry_date']]['ret'] > 0]
    b = [v for e, v, r in zip(EV, NET, REG) if r is regval and F[e['entry_date']] and F[e['entry_date']]['ret'] <= 0]
    d = st.mean(a)-st.mean(b)
    p = perm_cond(regval, d)
    print("  %s  나스닥상승 n=%d %+.2f%%  vs  나스닥하락 n=%d %+.2f%%  차 %+.2f%%p  p=%.4f"
          % (lab, len(a), st.mean(a), len(b), st.mean(b), d, p))

# ---- 4칸 연도별 안정성 ----
print("\n=== 4칸 연도별 (거래당 순수익%, 괄호=건수) ===")
cells = [('G 상승+상승', True, True), ('Y 상승+하락', True, False),
         ('Y 조정+상승', False, True), ('R 조정+하락', False, False)]
print("%-6s %-16s %-16s %-16s %-16s" % ('연도', *[c[0] for c in cells]))
for y in ('2021', '2022', '2023', '2024', '2025', '2026'):
    line = "%-6s " % y
    for lab, r, n in cells:
        g = [v for e, v, rr in zip(EV, NET, REG)
             if e['scan_date'][:4] == y and rr is r and F[e['entry_date']] and (F[e['entry_date']]['ret'] > 0) == n]
        line += "%-16s " % (("%+.2f%% (%d)" % (st.mean(g), len(g))) if len(g) >= 5 else "- (%d)" % len(g))
    print(line)

# ---- 최악칸 집중도 ----
print("\n=== '국면조정+나스닥상승' 781건의 시기 집중도 ===")
bad = [(e, v) for e, v, r in zip(EV, NET, REG) if r is False and F[e['entry_date']] and F[e['entry_date']]['ret'] > 0]
bm = collections.Counter(e['scan_date'][:7] for e, v in bad)
tot_net = sum(v for e, v in bad)
by_m = collections.defaultdict(float)
for e, v in bad: by_m[e['scan_date'][:7]] += v
worst = sorted(by_m.items(), key=lambda x: x[1])[:5]
print("  총 %d건, 순수익 합 %+.0f%%p" % (len(bad), tot_net))
print("  최악 5개월이 합계에서 차지하는 비중: %.0f%%" % (sum(w for _, w in worst)/tot_net*100 if tot_net else float('nan')))
for mth, s in worst: print("    %s  합%+.0f%%p (%d건)" % (mth, s, bm[mth]))
lo = sorted(by_m.items(), key=lambda x: x[1])
print("  최악 5개월 제외 시 나머지 거래당: %+.2f%%" %
      (sum(v for e, v in bad if e['scan_date'][:7] not in dict(worst)) /
       max(1, sum(1 for e, v in bad if e['scan_date'][:7] not in dict(worst)))))

# ---- 코스피 20MA 국면으로 바꾸면? ----
print("\n=== 국면 정의를 코스피 20MA로 바꾸면 (4칸) ===")
for lab, r, n in cells:
    g = [v for e, v, rr in zip(EV, NET, REGKS) if rr is r and F[e['entry_date']] and (F[e['entry_date']]['ret'] > 0) == n]
    w = sum(1 for e, rr in zip(EV, REGKS) if rr is r and F[e['entry_date']] and (F[e['entry_date']]['ret'] > 0) == n and e['result'] == 'win')
    print("  %-14s n=%5d 승률 %5.1f%%  거래당 %+.2f%%" % (lab, len(g), w/len(g)*100, st.mean(g)))

# ---- 전후반 분할 (OOS) ----
print("\n=== 전후반 분할: '최악칸 제외' 필터 ===")
mid = '2024-01-01'
for lab, sel in [('전반(2021-02~2023)', lambda e: e['scan_date'] < mid), ('후반(2024~2026-08)', lambda e: e['scan_date'] >= mid)]:
    keep = [(e, v) for e, v, r in zip(EV, NET, REG) if sel(e) and not (r is False and F[e['entry_date']] and F[e['entry_date']]['ret'] > 0)]
    allx = [(e, v) for e, v in zip(EV, NET) if sel(e)]
    print("  %-20s 전부 n=%4d %+.2f%%   최악칸제외 n=%4d %+.2f%%   차 %+.2f%%p"
          % (lab, len(allx), st.mean([v for _, v in allx]), len(keep), st.mean([v for _, v in keep]),
             st.mean([v for _, v in keep])-st.mean([v for _, v in allx])))

# ---- 슬롯5 자산곡선: 헤드라인 후보들 (200시드 5~95%) ----
print("\n=== 슬롯5 자산곡선 분포 (200시드, 5%/중앙/95%) ===")
def band(sub):
    r = sorted(sim(sub, seed=s)[0] for s in range(200))
    return r[10], r[100], r[190]
cands = [('전부 매수(기준)', lambda e, r: True),
         ('최악칸 제외', lambda e, r: not (r is False and F[e['entry_date']] and F[e['entry_date']]['ret'] > 0)),
         ('나스닥 -0.5~0%만', lambda e, r: F[e['entry_date']] and -0.5 <= F[e['entry_date']]['ret'] <= 0),
         ('나스닥 +0.5~1%만', lambda e, r: F[e['entry_date']] and 0.5 <= F[e['entry_date']]['ret'] < 1.0),
         ('나스닥 하락일만', lambda e, r: F[e['entry_date']] and F[e['entry_date']]['ret'] <= 0),
         ('나스닥 상승일만', lambda e, r: F[e['entry_date']] and F[e['entry_date']]['ret'] > 0),
         ('국면상승만(참조)', lambda e, r: r is True)]
for lab, f in cands:
    sub = [e for e, r in zip(EV, REG) if f(e, r)]
    lo, md, hi = band(sub)
    print("  %-18s n=%5d   %+7.1f%% | %+7.1f%% | %+7.1f%%" % (lab, len(sub), lo, md, hi))
print("  (코스피 같은 기간 +109.0%)")
