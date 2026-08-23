import json, os, glob
PD = r"C:/Users/hanul/playground/my-stock/.cache/pdata"
SP = r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad"
files = sorted(glob.glob(os.path.join(PD, "price_*.json")))
dates_all = [os.path.basename(f)[6:14] for f in files]
START, END = "20251126", "20260821"
sel = [(d,f) for d,f in zip(dates_all,files) if START <= d <= END]
def load(f):
    with open(f, encoding='utf-8') as fp: return json.load(fp)
days = [(d, load(f)) for d,f in sel]
d0 = days[0][1]

cj = json.load(open(os.path.join(SP,'contrib.json'), encoding='utf-8'))
contrib, names, total = cj['contrib'], cj['names'], cj['total']

# chained fltRt return from 2025-11-27 .. end (returns of days after start)
def chain(code):
    c = 1.0; n = 0
    for d, dd in days[1:]:
        if code in dd and dd[code].get('fltRt') is not None:
            c *= (1 + dd[code]['fltRt']/100.0); n += 1
    return (c-1)*100, n

# ---- 1) top 30 by market cap at start
top30 = sorted([(v.get('market_cap_eok') or 0, c) for c,v in d0.items()], reverse=True)[:30]
print("="*100)
print("[1] 2025-11-26 시총 상위 30 — fltRt 연쇄 수익률 & 지수 기여도")
print("="*100)
print(f"{'#':>2} {'code':<7}{'name':<16}{'mkt':<7}{'시총(조)':>9}{'비중%':>7}{'수익률%':>9}{'기여%p':>8}{'기여순위':>8}")
rank_by_contrib = {c:i+1 for i,(c,_) in enumerate(sorted(contrib.items(), key=lambda x:-x[1]))}
totcap0 = sum((v.get('market_cap_eok') or 0) for v in d0.values())
rows30=[]
for i,(mc,c) in enumerate(top30,1):
    ret,n = chain(c)
    ct = contrib.get(c,0.0)*100
    nm = d0[c].get('itmsNm')
    rows30.append((c,nm,ret,ct,mc))
    print(f"{i:>2} {c:<7}{nm:<16}{d0[c].get('mrktCtg'):<7}{mc/10000:>9.1f}{mc/totcap0*100:>7.2f}{ret:>9.1f}{ct:>8.2f}{rank_by_contrib.get(c,0):>8}")

# ---- top 10 by contribution (whole market)
print()
print("="*100)
print("[1b] 지수 기여도 상위 10 (전 종목 대상, 전일시총 가중 연결기여)")
print("="*100)
top10 = sorted(contrib.items(), key=lambda x:-x[1])[:15]
print(f"{'#':>2} {'code':<7}{'name':<16}{'기여%p':>8}{'전체대비%':>9}{'수익률%':>9}{'시총(조)':>9}")
cum=0
for i,(c,v) in enumerate(top10,1):
    ret,n = chain(c)
    mc = (d0.get(c,{}) or {}).get('market_cap_eok') or 0
    if i<=10: cum+=v
    print(f"{i:>2} {c:<7}{str(names.get(c)):<16}{v*100:>8.2f}{v/total*100:>9.1f}{ret:>9.1f}{mc/10000:>9.1f}")
print(f"\n상위 10 합계 기여: {cum*100:.2f}%p / 전체 {total*100:.2f}%p = {cum/total*100:.1f}%")
json.dump({'top10':[c for c,_ in top10[:10]],'top30':[c for _,c in top30]},
          open(os.path.join(SP,'sets.json'),'w'), ensure_ascii=False)
