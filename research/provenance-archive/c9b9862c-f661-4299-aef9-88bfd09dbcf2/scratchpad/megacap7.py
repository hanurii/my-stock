import json, os, glob, statistics
SP=r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad"
PD=r"C:/Users/hanul/playground/my-stock/.cache/pdata"
bt=json.load(open(r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json",encoding='utf-8'))
ev=bt['events']; codes_ev={e['code'] for e in ev}
cj=json.load(open(os.path.join(SP,'contrib.json'),encoding='utf-8'))
contrib,names,total=cj['contrib'],cj['names'],cj['total']
sets=json.load(open(os.path.join(SP,'sets.json')))

print("="*104)
print("[2c] 지수 상승분 중 '우리가 실제로 진입한 종목'이 차지하는 비중")
print("="*104)
pos={c:v for c,v in contrib.items() if v>0}
pos_tot=sum(pos.values())
covered=sum(v for c,v in pos.items() if c in codes_ev)
print(f"전체 지수 상승 {total*100:+.2f}%p (양(+)기여 합 {pos_tot*100:.2f}%p)")
print(f"우리가 1번 이상 진입한 종목의 양(+)기여 합: {covered*100:.2f}%p = 양기여의 {covered/pos_tot*100:.1f}%, 순지수상승의 {covered/total*100:.1f}%")
t10=[c for c in sets['top10'] if c in codes_ev]
c10=sum(contrib[c] for c in t10)
print(f"기여 상위10 중 진입한 8종목 기여 합: {c10*100:.2f}%p = 순지수상승의 {c10/total*100:.1f}%")
print("   ->", ", ".join(f"{names[c]}({contrib[c]*100:+.2f})" for c in t10))

# ---------- realizable alternative exits (daily close chain from pdata) ----------
files=sorted(glob.glob(os.path.join(PD,"price_*.json")))
dall=[os.path.basename(f)[6:14] for f in files]
sel=[(d,f) for d,f in zip(dall,files) if "20251126"<=d<="20260821"]
DATES=[d for d,_ in sel]; days=[json.load(open(f,encoding='utf-8')) for _,f in sel]
idx={d:i for i,d in enumerate(DATES)}

def path(code, entry_date):
    i=idx.get(entry_date.replace('-',''))
    if i is None: return []
    out=[]; c=1.0
    for t in range(i+1, len(DATES)):
        v=days[t].get(code)
        if not v or v.get('fltRt') is None: continue
        c*=(1+v['fltRt']/100.0); out.append((c-1)*100)
    return out

def sim(p, stop=-10.0, tp=None, trail=None, arm=20.0):
    """close-based. tp: fixed take-profit. trail: after gain>=arm, trail X% off peak."""
    peak=0.0; armed=False
    for g in p:
        peak=max(peak,g)
        if tp is not None and g>=tp: return tp
        if trail is not None:
            if g>=arm: armed=True
            if armed and g <= peak-trail: return peak-trail
        if g<=stop: return stop
    return p[-1] if p else 0.0

paths={}
for e in ev:
    paths[(e['code'],e['entry_date'])]=path(e['code'],e['entry_date'])

def capof(code,date,_c={}):
    d=date.replace('-','')
    if d not in _c:
        pth=os.path.join(PD,f"price_{d}.json"); _c[d]=json.load(open(pth,encoding='utf-8')) if os.path.exists(pth) else {}
    return (_c[d].get(code) or {}).get('market_cap_eok') or 0

variants=[("현행 +20/-10", dict(stop=-10,tp=20)),
          ("+20/-10 (재현확인)", dict(stop=-10,tp=20)),
          ("-10 손절, 익절없음(끝까지)", dict(stop=-10)),
          ("-10 → +20 도달후 20%트레일", dict(stop=-10,trail=20,arm=20)),
          ("-10 → +20 도달후 15%트레일", dict(stop=-10,trail=15,arm=20)),
          ("-10 → +20 도달후 25%트레일", dict(stop=-10,trail=25,arm=20)),
          ("-10 → +20 도달후 절반익절+20%트레일", None)]
print()
print("="*104)
print("[4c] 실현가능한 청산 대안 (종가기준 재시뮬, 614건 전체 / 시총 5조+ / 20조+)")
print("="*104)
print(f"{'규칙':<34}{'전체 평균%':>11}{'중앙%':>8}{'5조+ 평균%':>12}{'20조+ 평균%':>12}")
subs={'all':list(paths.items()),
      'big':[(k,v) for k,v in paths.items() if capof(k[0], next(e['scan_date'] for e in ev if e['code']==k[0] and e['entry_date']==k[1]))>=50000],
      'mega':[(k,v) for k,v in paths.items() if capof(k[0], next(e['scan_date'] for e in ev if e['code']==k[0] and e['entry_date']==k[1]))>=200000]}
for label,kw in variants:
    if kw is None:
        f=lambda p: (0.5*sim(p,stop=-10,tp=20)+0.5*sim(p,stop=-10,trail=20,arm=20)) if p else 0.0
    else:
        f=lambda p,kw=kw: sim(p,**kw) if p else 0.0
    r={k:[f(v) for _,v in s] for k,s in subs.items()}
    print(f"{label:<34}{sum(r['all'])/len(r['all']):>+11.2f}{statistics.median(r['all']):>+8.2f}"
          f"{sum(r['big'])/len(r['big']):>+12.2f}{sum(r['mega'])/len(r['mega']):>+12.2f}")
print(f"\n(표본 n: 전체 {len(subs['all'])}, 5조+ {len(subs['big'])}, 20조+ {len(subs['mega'])})")
