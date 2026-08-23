import json, os, glob, statistics
SP = r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad"
PD = r"C:/Users/hanul/playground/my-stock/.cache/pdata"
bt = json.load(open(r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json", encoding='utf-8'))
ev = bt['events']
sets = json.load(open(os.path.join(SP,'sets.json')))
cj = json.load(open(os.path.join(SP,'contrib.json'), encoding='utf-8'))
names, contrib = cj['names'], cj['contrib']

files = sorted(glob.glob(os.path.join(PD, "price_*.json")))
dall = [os.path.basename(f)[6:14] for f in files]
sel = [(d,f) for d,f in zip(dall,files) if "20251126" <= d <= "20260821"]
DATES=[d for d,_ in sel]
days=[(d, json.load(open(f,encoding='utf-8'))) for d,f in sel]
idx={d:i for i,(d,_) in enumerate(days)}

def hold_to_end(code, entry_date):
    """chained fltRt from day AFTER entry_date to window end (entry at entry_date close-ish)."""
    i = idx.get(entry_date.replace('-',''))
    if i is None: return None
    c=1.0
    for d,dd in days[i+1:]:
        v=dd.get(code)
        if v and v.get('fltRt') is not None: c*=(1+v['fltRt']/100.0)
    return (c-1)*100

print("="*104)
print("[4] 우리 방법 vs 그냥 들고 있기 — '기여 상위10' 종목에서 실제로 무슨 일이 있었나")
print("="*104)
print(f"{'code':<7}{'name':<14}{'진입일':<12}{'실현%':>8}{'MFE%':>8}{'보유일':>6}{'진입후 끝까지%':>13}{'놓친%p':>9}")
rows=[]
for c in sets['top10']:
    es=[e for e in ev if e['code']==c]
    for e in sorted(es,key=lambda x:x['entry_date']):
        h=hold_to_end(c, e['entry_date'])
        g=e['gain_at_resolve_pct']
        rows.append((c,e,g,h))
        print(f"{c:<7}{e['name']:<14}{e['entry_date']:<12}{g:>+8.2f}{e['max_gain_pct']:>+8.2f}{e['days_held']:>6}{h:>+13.1f}{h-g:>+9.1f}")
tot_real=sum(r[2] for r in rows); tot_hold=sum(r[3] for r in rows)
print(f"\n  합계 {len(rows)}건: 실현 {tot_real:+.1f}%p  vs  끝까지보유 {tot_hold:+.1f}%p  →  포기한 수익 {tot_hold-tot_real:+.1f}%p")
print(f"  건당 평균: 실현 {tot_real/len(rows):+.2f}%  vs  보유 {tot_hold/len(rows):+.2f}%  (배수 {tot_hold/tot_real:.1f}x)")

# 전체 614건으로 확장
print()
print("="*104)
print("[4b] 전체 614건: +20/-10 청산 vs 진입 후 기간 끝까지 보유")
print("="*104)
allr=[]
for e in ev:
    h=hold_to_end(e['code'], e['entry_date'])
    if h is None: continue
    allr.append((e, e['gain_at_resolve_pct'], h))
r_real=[x[1] for x in allr]; r_hold=[x[2] for x in allr]
print("n=%d  실현 평균 %+.2f%% (중앙 %+.2f)   끝까지보유 평균 %+.2f%% (중앙 %+.2f)" % (
   len(allr), sum(r_real)/len(allr), statistics.median(r_real),
   sum(r_hold)/len(allr), statistics.median(r_hold)))
# split by cap
capc={}
def cap(code,date):
    d=date.replace('-','')
    if d not in capc:
        p=os.path.join(PD,f"price_{d}.json"); capc[d]=json.load(open(p,encoding='utf-8')) if os.path.exists(p) else {}
    return (capc[d].get(code) or {}).get('market_cap_eok')
print()
print(f"{'시총대역':<14}{'n':>5}{'실현평균%':>11}{'보유평균%':>11}{'승률%':>8}")
bands=[(200000,10**9,'20조+'),(50000,200000,'5~20조'),(10000,50000,'1~5조'),(3000,10000,'3천억~1조'),(0,3000,'3천억 미만')]
for lo,hi,lab in bands:
    sub=[(e,a,b) for e,a,b in allr if (cap(e['code'],e['scan_date']) or 0)>=lo and (cap(e['code'],e['scan_date']) or 0)<hi]
    if not sub: continue
    dec=[x for x in sub if x[0]['result'] in ('win','loss')]
    wr=sum(1 for x in dec if x[0]['result']=='win')/len(dec)*100 if dec else 0
    print(f"{lab:<14}{len(sub):>5}{sum(x[1] for x in sub)/len(sub):>+11.2f}{sum(x[2] for x in sub)/len(sub):>+11.2f}{wr:>8.1f}")
