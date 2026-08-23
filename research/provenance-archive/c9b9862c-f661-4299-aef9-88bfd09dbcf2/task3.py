# -*- coding: utf-8 -*-
"""과제 C-3: '이 날은 쉰다' 규칙별 슬롯5 실전 시뮬 (1건 1,000만원)"""
import sys, json
from datetime import date
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build

rows=[r for r in build()]
byscan={r['scan_date']:r for r in rows}
SLOT=5; SIZE=10_000_000
START=date(2025,11,26); END=date(2026,8,21)
YEARS=(END-START).days/365.0

# 4분위 컷 (사후 선택임을 명시)
def cut(key, q=0.75, sel=None):
    vs=sorted(r[key] for r in rows if r.get(key) is not None and (sel is None or sel(r)))
    return vs[int(len(vs)*q)]

C_RET10_UP = cut('ret10',0.75, lambda r:r['up'])
C_NH52_UP  = cut('pct_nh52',0.75, lambda r:r['up'])
C_A200_UP  = cut('pct_above200',0.75, lambda r:r['up'])
C_SLOPE_UP = cut('slope_ma20_5',0.75, lambda r:r['up'])

RULES = [
 ('①전부 산다(현행)',            lambda r: True),
 ('②상승국면 날만',              lambda r: r['up']),
 ('③상승국면 + 지수10일↑ 과열 제외', lambda r: r['up'] and r['ret10'] < C_RET10_UP),
 ('④상승국면 + 신고가비율 과열 제외', lambda r: r['up'] and r['pct_nh52'] < C_NH52_UP),
 ('⑤상승국면 + 200일선비율 과열 제외',lambda r: r['up'] and r['pct_above200'] < C_A200_UP),
 ('⑥상승국면 + 20일선기울기 과열 제외',lambda r: r['up'] and r['slope_ma20_5'] < C_SLOPE_UP),
 ('⑦상승국면 + 4잣대 모두 통과',    lambda r: r['up'] and r['ret10']<C_RET10_UP and r['pct_nh52']<C_NH52_UP
                                    and r['pct_above200']<C_A200_UP and r['slope_ma20_5']<C_SLOPE_UP),
 ('⑧국면 무시 + 신고가비율 과열만 제외', lambda r: r['pct_nh52'] < cut('pct_nh52',0.75)),
]

def sim(passfn, order='turnover'):
    """슬롯5 점유 시뮬. 하루에 통과하면 빈 슬롯만큼 매수(거래대금 큰 순)."""
    open_pos=[]   # (resolve_date, gain)
    pnl=0.0; taken=[]; skipped_slot=0; skipped_day=0
    for r in rows:
        D=r['entry_date']
        open_pos=[p for p in open_pos if p[0]>=D]   # resolve_date < 오늘이면 청산됨
        free=SLOT-len(open_pos)
        es=sorted(r['events'], key=lambda e:-(e.get('turnover_eok') or 0))
        if not passfn(r):
            skipped_day+=len(es); continue
        for e in es:
            if free<=0: skipped_slot+=1; continue
            open_pos.append((e['resolve_date'], e['gain_at_resolve_pct']))
            pnl += SIZE*e['gain_at_resolve_pct']/100.0
            taken.append(e); free-=1
    w=sum(1 for e in taken if e['result']=='win'); l=sum(1 for e in taken if e['result']=='loss')
    ev=sum(e['gain_at_resolve_pct'] for e in taken)/len(taken) if taken else 0
    return dict(n=len(taken), w=w, l=l, wr=100*w/(w+l) if w+l else 0, ev=ev, pnl=pnl,
                annual=pnl/YEARS, skipped_day=skipped_day, skipped_slot=skipped_slot,
                days=sum(1 for r in rows if passfn(r)))

print(f"기간 {START}~{END} ({YEARS:.2f}년), 슬롯 {SLOT} × {SIZE:,}원 = 운용자금 {SLOT*SIZE:,}원")
print(f"컷(상승국면 상위25% 경계): 지수10일 {C_RET10_UP:.2f}% · 신고가비율 {C_NH52_UP:.2f}% · 200일선위 {C_A200_UP:.1f}% · 20일선기울기 {C_SLOPE_UP:.2f}%\n")
print(f"{'규칙':32s}{'매매일':>6s}{'매수':>5s}{'승':>4s}{'패':>4s}{'승률':>7s}{'건당':>8s}{'총손익':>13s}{'연환산':>13s}{'수익률/년':>9s}")
base=None
for name,fn in RULES:
    s=sim(fn)
    if base is None: base=s
    print(f"{name:32s}{s['days']:6d}{s['n']:5d}{s['w']:4d}{s['l']:4d}{s['wr']:6.1f}%{s['ev']:+7.2f}%{s['pnl']:13,.0f}{s['annual']:13,.0f}{100*s['annual']/(SLOT*SIZE):8.1f}%")
