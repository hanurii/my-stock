import json, os, glob, bisect
SP = r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad"
PD = r"C:/Users/hanul/playground/my-stock/.cache/pdata"
files = sorted(glob.glob(os.path.join(PD,"price_*.json")))
dall=[os.path.basename(f)[6:14] for f in files]
# need 260 trading days of history before 2025-11-26
i_start = dall.index("20251126")
lo = max(0, i_start-270)
usef = [(dall[i], files[i]) for i in range(lo, len(dall)) if dall[i] <= "20260821"]
print("loading", len(usef), "days:", usef[0][0], "->", usef[-1][0])
DATES=[d for d,_ in usef]
data=[json.load(open(f,encoding='utf-8')) for _,f in usef]

# build chained adjusted price series per code via fltRt (base 100 at first appearance)
series={}   # code -> dict(dayindex->adjprice)
for t,dd in enumerate(data):
    for c,v in dd.items():
        r=v.get('fltRt')
        s=series.get(c)
        if s is None:
            series[c]={'i':[t],'p':[100.0]}
        else:
            last=s['p'][-1]
            s['i'].append(t); s['p'].append(last*(1+(r or 0)/100.0))
print("codes:", len(series))
json_out={}

W_IDX = DATES.index("20251126")
def adj_at(c, t):
    s=series.get(c)
    if not s: return None
    j=bisect.bisect_right(s['i'], t)-1
    if j<0 or s['i'][j]!=t: return None
    return s['p'][j]

# RS percentile per day (Minervini-ish: 250d return, percentile rank across all with 250d history)
NEED=250
rs_hist={}   # code -> list of (date, rs)
sample_ts=list(range(W_IDX, len(DATES), 5))   # every 5 trading days
for t in sample_ts:
    rets=[]
    for c,s in series.items():
        p_now=adj_at(c,t); p_old=adj_at(c,t-NEED)
        if p_now and p_old and p_old>0:
            rets.append((p_now/p_old-1, c))
    rets.sort()
    n=len(rets)
    for rank,(r,c) in enumerate(rets):
        rs = int(rank/n*98)+1
        rs_hist.setdefault(c,[]).append((DATES[t], rs, r*100))
print("RS sampled on", len(sample_ts), "days; universe w/ 250d hist ~", n)

def ma(c,t,w):
    vals=[adj_at(c,t-k) for k in range(w)]
    vals=[v for v in vals if v]
    return sum(vals)/len(vals) if len(vals)>=w*0.8 else None

sets=json.load(open(os.path.join(SP,'sets.json')))
cj=json.load(open(os.path.join(SP,'contrib.json'),encoding='utf-8'))
names=cj['names']; contrib=cj['contrib']
bt=json.load(open(r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json",encoding='utf-8'))
codes_in_ev={e['code'] for e in bt['events']}

miss = [c for c in sets['top30'] if c not in codes_in_ev]
print()
print("="*110)
print("[3] events 미등장 종목 — 왜 안 나왔나 (RS 프록시: 250일 수익률 백분위, 5거래일 간격 표본)")
print("="*110)
print(f"{'code':<7}{'name':<16}{'기여%p':>8}{'구간수익%':>9}{'RS최대':>7}{'RS중앙':>7}{'RS>=80비율':>11}{'200MA위 비율':>12}")
for c in miss:
    h=rs_hist.get(c,[])
    if not h:
        print(f"{c:<7}{str(names.get(c)):<16}{'':>8}{'':>9}  (250일 이력 없음)"); continue
    rss=[x[1] for x in h]
    rss_sorted=sorted(rss)
    above=0; tot=0
    for t in sample_ts:
        p=adj_at(c,t); m=ma(c,t,200)
        if p and m: tot+=1; above += 1 if p>m else 0
    ret_w=None
    p0=adj_at(c,W_IDX); p1=adj_at(c,len(DATES)-1)
    if p0 and p1: ret_w=(p1/p0-1)*100
    print(f"{c:<7}{str(names.get(c)):<16}{contrib.get(c,0)*100:>+8.2f}{(ret_w if ret_w is not None else 0):>+9.1f}"
          f"{max(rss):>7}{rss_sorted[len(rss_sorted)//2]:>7}"
          f"{sum(1 for x in rss if x>=80)/len(rss)*100:>10.0f}%{(above/tot*100 if tot else 0):>11.0f}%")

# preferred shares in events?
pref=[c for c in codes_in_ev if c.endswith('5') and c[:5].isdigit() and c[:1]=='0']
print("\n우선주(코드 …5) events 등장:", sorted(pref)[:20], "총", len(pref))
allpref_ev=[e for e in bt['events'] if e['code'].endswith(('5','7','9')) and e['code'][:4].isdigit() and int(e['code'][4:])>=5]
print("우선주 추정 진입건수:", len(allpref_ev), [ (e['code'],e['name']) for e in allpref_ev[:10]])
