import json, os, glob
from collections import Counter
SP = r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad"
bt = json.load(open(r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json", encoding='utf-8'))
ev = bt['events']
sets = json.load(open(os.path.join(SP,'sets.json')))
cj = json.load(open(os.path.join(SP,'contrib.json'), encoding='utf-8'))
names = cj['names']

bycode = {}
for e in ev: bycode.setdefault(e['code'], []).append(e)
print("distinct codes in events:", len(bycode), "events:", len(ev))

# confirm baseline
res = Counter(e['result'] for e in ev)
print("results:", dict(res))
dec = [e for e in ev if e['result'] in ('win','loss')]
w = [e for e in dec if e['result']=='win']; l=[e for e in dec if e['result']=='loss']
print("decided %d  win %d (avg %+.2f%%)  loss %d (avg %+.2f%%)  avg/trade %+.2f%%" % (
  len(dec), len(w), sum(x['gain_at_resolve_pct'] for x in w)/len(w),
  len(l), sum(x['gain_at_resolve_pct'] for x in l)/len(l),
  sum(x['gain_at_resolve_pct'] for x in dec)/len(dec)))
print("scan_date range:", min(e['scan_date'] for e in ev), max(e['scan_date'] for e in ev))

print()
print("="*100)
print("[2] 지수 상승 주역이 백테스트 events 에 나왔나?")
print("="*100)
TOP10 = sets['top10']; TOP30 = sets['top30']
for label, codes in (("기여 상위 10", TOP10), ("시총 상위 30", TOP30)):
    hit = [c for c in codes if c in bycode]
    print(f"\n-- {label}: {len(codes)}종목 중 events 등장 {len(hit)}종목")
    for c in hit:
        for e in bycode[c]:
            print(f"   {c} {names.get(c)} {e['scan_date']}->{e['entry_date']} pat={e['pattern']} rs={e['rs']} "
                  f"result={e['result']} gain={e['gain_at_resolve_pct']:+.2f}% maxgain={e['max_gain_pct']:+.2f}% days={e['days_held']}")
    miss = [c for c in codes if c not in bycode]
    print(f"   미등장 {len(miss)}: " + ", ".join(f"{c}({names.get(c)})" for c in miss[:40]))

# market cap distribution of events (cap at scan_date)
PD = r"C:/Users/hanul/playground/my-stock/.cache/pdata"
capcache = {}
def cap(code, date):
    d = date.replace('-','')
    if d not in capcache:
        p = os.path.join(PD, f"price_{d}.json")
        capcache[d] = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    v = capcache[d].get(code)
    return (v or {}).get('market_cap_eok')
caps=[]
for e in ev:
    c = cap(e['code'], e['scan_date'])
    if c: caps.append((c,e))
caps.sort(reverse=True)
print()
print("="*100)
print("[2b] 백테스트 진입 종목의 시총 분포 (scan_date 시점)")
print("="*100)
import statistics
vals=[c for c,_ in caps]
print("n=%d  중앙 %.0f억  평균 %.0f억  최대 %.0f억(%s)  최소 %.0f억" % (
  len(vals), statistics.median(vals), sum(vals)/len(vals), vals[0], caps[0][1]['name'], vals[-1]))
for th,lab in ((100000,'10조+'),(50000,'5조+'),(20000,'2조+'),(10000,'1조+'),(5000,'5천억+')):
    n=sum(1 for v in vals if v>=th); print(f"  시총 {lab:>6}: {n:>4}건 ({n/len(vals)*100:.1f}%)")
print("\n 시총 상위 10 진입건:")
for c,e in caps[:10]:
    print(f"   {c/10000:>6.1f}조 {e['code']} {e['name']:<12} {e['scan_date']} rs={e['rs']} {e['result']} {e['gain_at_resolve_pct']:+.2f}%")
