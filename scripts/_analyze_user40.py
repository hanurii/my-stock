# -*- coding: utf-8 -*-
"""6/24 데이트레이딩 검증 — 사용자 합의 규칙.
분류: 첫3분봉 body% → 장대양봉(>=+6)/양봉(0~+6)/음봉(-6~0)/장대음봉(<=-6, 스킵)
진입(09:00~10:00 창):
  양봉  : 09:03 종가 즉시매수 (+거래량비율 표기)
  장대양봉: 거래량 마름(<=첫봉*0.5)+변동성 축소(range<첫봉*0.7) 첫 봉 종가 매수
  음봉  : 첫 음봉 몸통보다 큰 양봉 첫 출현 봉 종가 매수
청산 시나리오 A(+6/-5) · B(+10/-6), 동시터치=손절우선, 미달시 종가청산, 비용 0.5%차감
"""
import json, glob, os, statistics, io, sys

data = json.load(open('scripts/_min3_user40_0624.json', encoding='utf-8'))
COST = 0.5
W = 20  # 09:00~10:00

def series(code):
    p = f'.cache/ohlcv/series/{code}.json'
    if not os.path.exists(p): return None
    return json.load(open(p, encoding='utf-8'))

def classify(b0):
    body = (b0['c']/b0['o']-1)*100
    if body >= 6: return '장대양봉', body
    if body > 0: return '양봉', body
    if body > -6: return '음봉', body
    return '장대음봉', body

def exit_sim(bars, ei, entry, target, stop):
    tp = entry*(1+target/100); sl = entry*(1+stop/100)
    mfe = mae = 0.0
    for k in range(ei+1, len(bars)):
        x = bars[k]
        mfe = max(mfe, (x['h']/entry-1)*100); mae = min(mae, (x['l']/entry-1)*100)
        hit_sl = x['l'] <= sl; hit_tp = x['h'] >= tp
        if hit_sl and hit_tp: return stop, '손절(동시)', mfe, mae
        if hit_sl: return stop, '손절', mfe, mae
        if hit_tp: return target, '익절', mfe, mae
    return (bars[-1]['c']/entry-1)*100, '종가', mfe, mae

rows = []  # (nm, code, gap, form, body, vol_ratio, entry_idx, entry_px, skip_reason)
for nm, d in data.items():
    bars = d['bars']; code = str(d['code'])
    if not bars: continue
    b0 = bars[0]
    form, body = classify(b0)
    s = series(code)
    prevc = s['closes'][-1] if s and s.get('closes') else None
    gap = (b0['o']/prevc-1)*100 if prevc else None
    avg50 = statistics.mean(s['volumes'][-50:]) if s and s.get('volumes') else None
    vr = (b0['v']/avg50) if avg50 else None  # 첫3분봉 거래량 / 50일 평균일거래량

    ei = None; reason = None
    if form == '장대음봉':
        reason = '장대음봉(룰상 매수금지)'
    elif form == '양봉':
        ei = 0  # 09:03 종가 즉시매수
    elif form == '장대양봉':
        r0 = b0['h']-b0['l']
        for j in range(1, min(W, len(bars))):
            x = bars[j]
            if x['v'] <= b0['v']*0.5 and (x['h']-x['l']) < r0*0.7:
                ei = j; break
        if ei is None: reason = '장대양봉 눌림(거래량마름+변동성축소) 미발생'
    else:  # 음봉
        body0 = b0['o']-b0['c']  # 음봉 몸통
        for j in range(1, min(W, len(bars))):
            x = bars[j]
            if x['c'] > x['o'] and (x['c']-x['o']) > body0:
                ei = j; break
        if ei is None: reason = '음봉 상쇄양봉 미발생'

    entry_px = bars[ei]['c'] if ei is not None else None
    rows.append(dict(nm=nm, code=code, gap=gap, form=form, body=body, vr=vr,
                     ei=ei, entry=entry_px, reason=reason, bars=bars))

out = io.StringIO()
def p(*a): print(*a, file=out)

# 1) 그날 성격
forms = {}
for r in rows: forms[r['form']] = forms.get(r['form'],0)+1
p("="*86)
p(f"  6/24 데이트레이딩 검증 — 신호일 6/23 → 매매일 6/24  (39종목)")
p("="*86)
p(f"  첫3분봉 분포: " + " / ".join(f"{k} {v}" for k,v in sorted(forms.items())))
gaps=[r['gap'] for r in rows if r['gap'] is not None]
if gaps: p(f"  시가갭(전일종가 대비): 평균 {statistics.mean(gaps):+.1f}%  (최대 {max(gaps):+.1f}, 최소 {min(gaps):+.1f})")
p("-"*86)

# 2) 시나리오별 집계
def summarize(label, target, stop):
    p(f"\n  ── 시나리오 {label}: 목표 +{target}% / 손절 {stop}% ──")
    by = {'양봉':[], '장대양봉':[], '음봉':[]}
    for r in rows:
        if r['ei'] is None: continue
        ret, why, mfe, mae = exit_sim(r['bars'], r['ei'], r['entry'], target, stop)
        by[r['form']].append((r['nm'], ret-COST, why, mfe, mae))
        r[f'res_{label}'] = (ret-COST, why, mfe, mae)
    allr=[]
    for k in ['양봉','장대양봉','음봉']:
        L=by[k]
        if not L: p(f"    [{k}] 진입 0"); continue
        rets=[x[1] for x in L]; wins=sum(1 for x in rets if x>0)
        tp=sum(1 for x in L if x[2]=='익절'); sl=sum(1 for x in L if '손절' in x[2]); cc=sum(1 for x in L if x[2]=='종가')
        p(f"    [{k}] {len(L)}건  평균 {statistics.mean(rets):+.2f}%/건  승률 {100*wins/len(L):.0f}%  (익절{tp}/손절{sl}/종가{cc})")
        allr+=rets
    if allr:
        w=sum(1 for x in allr if x>0)
        p(f"    ▶ 전체 진입 {len(allr)}건  평균 {statistics.mean(allr):+.2f}%/건  승률 {100*w/len(allr):.0f}%  합계 {sum(allr):+.1f}%p")

summarize('A', 6, -5)
summarize('B', 10, -6)

# 3) MFE 분포 (전 종목, 09:03 종가 기준 그날 최대 상승)
p("\n  ── 진입가능 종목들의 '그날 장중 최대 상승폭' 분포 (09:03 종가 기준) ──")
mfes=[]
for r in rows:
    if r['form']=='장대음봉': continue
    b0c=r['bars'][0]['c']
    mx=max((x['h']/b0c-1)*100 for x in r['bars'][1:]) if len(r['bars'])>1 else 0
    mfes.append(mx)
for thr in [6,10,15,20]:
    p(f"    +{thr}% 이상 도달: {sum(1 for m in mfes if m>=thr)}/{len(mfes)}종목")

# 4) 블라인드 벤치마크 (규칙 무시, 전 종목 09:03매수→종가)
p("\n  ── 비교: 규칙 무시하고 '전 종목 09:03 종가 매수 → 당일 종가 청산' ──")
blind=[]
for r in rows:
    if r['form']=='장대음봉': continue
    b0c=r['bars'][0]['c']; cl=r['bars'][-1]['c']
    blind.append((cl/b0c-1)*100 - COST)
p(f"    {len(blind)}종목  평균 {statistics.mean(blind):+.2f}%/건  승률 {100*sum(1 for x in blind if x>0)/len(blind):.0f}%")

# 5) 종목별 상세
p("\n" + "-"*86)
p("  [종목별 상세]  형태 | 갭 | 거래량비(첫3분/50일평균) | 진입 | A결과 | B결과")
p("-"*86)
for r in sorted(rows, key=lambda x:(x['form'], -(x['body']))):
    gap = f"{r['gap']:+5.1f}%" if r['gap'] is not None else "  n/a"
    vr = f"{r['vr']*100:5.0f}%" if r['vr'] is not None else "  n/a"
    if r['ei'] is None:
        p(f"   {r['nm']:<12} {r['form']:<6} 갭{gap} 거래량비{vr}  → 스킵: {r['reason']}")
    else:
        a=r.get('res_A'); b=r.get('res_B')
        et=r['bars'][r['ei']]['t']
        p(f"   {r['nm']:<12} {r['form']:<6} 갭{gap} 거래량비{vr}  진입{et}@{r['entry']:.0f}  "
          f"A {a[0]:+6.2f}%[{a[1]}]  B {b[0]:+6.2f}%[{b[1]}]  (장중최대+{a[2]:.1f}%)")

sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
open('scripts/_result_user40.txt','w',encoding='utf-8').write(out.getvalue())
