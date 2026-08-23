# -*- coding: utf-8 -*-
"""비용·현실 검증: 수수료 3시나리오 x 슬리피지 x 슬롯수 x MDD(실현/평가)."""
import json, random, collections, glob, os, sys, statistics as st
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = 'C:/Users/hanul/playground/my-stock/'
J = json.load(open(ROOT+'public/data/backtest-volatility-pilot.json', encoding='utf-8'))
EV = [e for e in J['events'] if e['result'] in ('win', 'loss')]
REG = {p['date']: p['up'] for p in json.load(open(ROOT+'public/data/market-regime.json', encoding='utf-8'))['series']}

COSTS = {
    'a_none':  (0.0,    0.0),
    'b_new':   (0.0,    0.002),          # 신규 증권사: 매수 0, 매도 세금 0.2%
    'c_mirae': (0.0014, 0.0014+0.002),   # 미래에셋
}

# ── 평가액 MDD용 경로: 백테스트와 같은 수정주가 캐시(.cache/ohlcv/series) ──────
SER = ROOT + '.cache/ohlcv/series/'
_cache = {}
def series(code):
    if code not in _cache:
        try:
            _cache[code] = json.load(open(SER+code+'.json', encoding='utf-8'))
        except Exception:
            _cache[code] = None
    return _cache[code]

def build_paths():
    """이벤트별 {날짜: 체결가대비 종가 평가수익률%} — 진입일~결착일."""
    paths, miss = {}, 0
    for i, e in enumerate(EV):
        s = series(e['code']); P = e['entry_price']
        if not s:
            paths[i] = {}; miss += 1; continue
        d, c = s['dates'], s['closes']
        p = {}
        for k, dt in enumerate(d):
            if dt < e['entry_date']:
                continue
            if dt > e['resolve_date']:
                break
            if c[k]:
                p[dt] = (c[k]/P-1)*100
        paths[i] = p
        if not p:
            miss += 1
    return paths, miss

PATHS, PATH_MISS = build_paths()

# ── 시뮬 ───────────────────────────────────────────────────────────────────
def run(slots=5, seed=0, regime=False, cost='c_mirae', slip=0.0, mtm=False):
    fb, fs = COSTS[cost]
    def net(g):
        return ((1+g/100)*(1-fs)/(1+fb)-1)*100
    byday = collections.defaultdict(list)
    for i, e in enumerate(EV):
        if regime and not REG.get(e['scan_date'], True):
            continue
        byday[e['entry_date']].append(i)
    rnd = random.Random(seed)
    eq = 1.0
    held = []          # (resolve_date, idx, weight)
    alld = sorted(set(list(byday) + [EV[i]['resolve_date'] for i in range(len(EV))]))
    peak = 1.0; mdd = 0.0; peak_m = 1.0; mdd_m = 0.0
    taken = []
    for d in alld:
        for rd, i, w in [h for h in held if h[0] <= d]:
            e = EV[i]
            g = e['gain_at_resolve_pct'] - (slip if e['result'] == 'loss' else 0.0)
            eq += w*net(g)/100
            taken.append(i)
        held = [h for h in held if h[0] > d]
        free = slots - len(held)
        if free > 0 and d in byday:
            c = byday[d][:]; rnd.shuffle(c)
            for i in c[:free]:
                held.append((EV[i]['resolve_date'], i, eq/slots))
        peak = max(peak, eq); mdd = min(mdd, eq/peak-1)
        if mtm:
            m = eq + sum(w*net(PATHS[i].get(d, 0.0))/100 for _, i, w in held)
            peak_m = max(peak_m, m); mdd_m = min(mdd_m, m/peak_m-1)
    n = len(taken); wn = sum(1 for i in taken if EV[i]['result'] == 'win')
    return dict(final=(eq-1)*100, n=n, win=wn/n*100 if n else 0,
                mdd=mdd*100, mdd_mtm=mdd_m*100)

def band(N=300, **kw):
    rs = [run(seed=i, **kw) for i in range(N)]
    f = sorted(r['final'] for r in rs); m = sorted(r['mdd'] for r in rs)
    mm = sorted(r['mdd_mtm'] for r in rs); nn = sorted(r['n'] for r in rs)
    ww = sorted(r['win'] for r in rs)
    return dict(fin=f[N//2], lo=f[N//20], hi=f[N-N//20], mdd=m[N//2], mdd_w=m[0],
                mdd_m=mm[N//2], mdd_mw=mm[0], n=nn[N//2], win=ww[N//2])


def row(lab, r):
    return (f"{lab:<30}{r['fin']:>+8.1f}%{('%+.1f~%+.1f' % (r['lo'], r['hi'])):>18}"
            f"{r['n']:>6}{r['win']:>6.1f}%{r['mdd']:>9.1f}%{r['mdd_m']:>9.1f}%{r['mdd_mw']:>9.1f}%")

HDR = f"{'':<30}{'최종':>9}{'5~95%':>18}{'매수':>6}{'승률':>7}{'실현MDD':>9}{'평가MDD':>9}{'평가MDD최악':>11}"

if __name__ == '__main__':
    import statistics
    print('580 확정거래(승227/패353) · 2025-11-26~2026-08-21 · 무작위 순서 300회 중앙값')
    print('평가MDD = 미결 보유분 종가 평가까지 반영한 진짜 낙폭 / 실현MDD = 청산분만')
    print()
    print('■ 1) 수수료 3시나리오 (슬롯5)')
    print(HDR)
    for ck, cl in (('a_none','(a) 무비용'), ('b_new','(b) 신규 매도0.2%'), ('c_mirae','(c) 미래 0.14+0.34%')):
        for rg, rl in ((False,'전부매수'), (True,'상승국면만')):
            print(row(f'{cl} · {rl}', band(slots=5, regime=rg, cost=ck, mtm=True)))
    print()
    print('■ 2) 손절 슬리피지 (미래에셋 비용 · 슬롯5)  손절 353건에만 추가 손실')
    print(HDR)
    for sl, sl_lab in ((0.0,'-10.0% 체결(기준)'), (0.5,'-10.5% 체결'), (1.0,'-11.0% 체결'), (2.0,'-12.0% 체결')):
        for rg, rl in ((False,'전부매수'), (True,'상승국면만')):
            print(row(f'{sl_lab} · {rl}', band(slots=5, regime=rg, cost='c_mirae', slip=sl, mtm=True)))
    print()
    print('■ 2b) 슬리피지 × 무비용 (비용과 분리해서 보기)')
    print(HDR)
    for sl in (0.0, 1.0, 2.0):
        for rg, rl in ((False,'전부매수'), (True,'상승국면만')):
            print(row(f'무비용 슬립{sl:.1f}pp · {rl}', band(slots=5, regime=rg, cost='a_none', slip=sl, mtm=True)))
    print()
    print('■ 3) 슬롯 수 (미래에셋 비용 · 슬리피지 0)')
    print(HDR)
    for k in (5, 10, 11, 15):
        for rg, rl in ((False,'전부매수'), (True,'상승국면만')):
            print(row(f'슬롯{k} · {rl}', band(slots=k, regime=rg, cost='c_mirae', mtm=True)))
    print()
    print('■ 3b) 슬롯11 + 슬리피지 -12% + 미래에셋 = 최악 조합')
    print(HDR)
    for rg, rl in ((False,'전부매수'), (True,'상승국면만')):
        print(row(f'슬롯11·슬립2pp · {rl}', band(slots=11, regime=rg, cost='c_mirae', slip=2.0, mtm=True)))
    print()
    print('■ 4) 참고: 580건 중 실제 매수된 비율 (슬롯 제약)')
    for k in (5, 10, 11, 15, 999):
        a = band(slots=k, regime=False, cost='c_mirae')['n']
        b = band(slots=k, regime=True, cost='c_mirae')['n']
        print(f'  슬롯{k:<4} 전부매수 {a:>3}건  상승국면만 {b:>3}건')
