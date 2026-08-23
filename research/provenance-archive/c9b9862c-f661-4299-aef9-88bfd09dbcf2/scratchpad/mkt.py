import sys, os, json, glob
os.chdir(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
files = glob.glob('.cache/ohlcv/series/*.json')
print("files", len(files))
# target dates
from collections import defaultdict
dates_all = None
adv=defaultdict(int); dec=defaultdict(int); flat=defaultdict(int)
above200=defaultdict(int); above50=defaultdict(int); n200=defaultdict(int); n50=defaultdict(int)
low52=defaultdict(int); n52=defaultdict(int)
turnover=defaultdict(float); volup=defaultdict(int); nvol=defaultdict(int)
eqret=defaultdict(list)
start='2026-07-20'
for f in files:
    code=os.path.basename(f).split('.')[0]
    try:
        s=ohlcv_matrix.get_series(code)
    except Exception as e:
        continue
    if not s: continue
    d=s['dates']; c=s['closes']; v=s['volumes']
    if not d or d[-1] < '2026-08-01': continue
    n=len(d)
    for i in range(n):
        if d[i] < start: continue
        if i==0: continue
        if c[i] is None or c[i-1] is None or c[i-1]==0: continue
        if v[i] is None or v[i]==0: continue  # skip halted
        r=c[i]/c[i-1]-1
        eqret[d[i]].append(r)
        if r>0: adv[d[i]]+=1
        elif r<0: dec[d[i]]+=1
        else: flat[d[i]]+=1
        turnover[d[i]]+= c[i]*v[i]
        if v[i-1]: 
            nvol[d[i]]+=1
            if v[i]>v[i-1]: volup[d[i]]+=1
        if i>=199:
            w=c[i-199:i+1]
            if all(x is not None for x in w):
                n200[d[i]]+=1
                if c[i]>sum(w)/200: above200[d[i]]+=1
        if i>=49:
            w=c[i-49:i+1]
            if all(x is not None for x in w):
                n50[d[i]]+=1
                if c[i]>sum(w)/50: above50[d[i]]+=1
        if i>=250:
            lows=s['lows'][i-250:i+1]
            if all(x is not None for x in lows):
                n52[d[i]]+=1
                if s['lows'][i] <= min(lows): low52[d[i]]+=1
print("date adv dec flat eqret% turnover(조) volup% a200% a50% low52")
for dt in sorted(eqret):
    rs=eqret[dt]
    print(dt, adv[dt], dec[dt], flat[dt], f"{100*sum(rs)/len(rs):+.2f}", f"{turnover[dt]/1e12:.1f}", f"{100*volup[dt]/max(nvol[dt],1):.0f}", f"{100*above200[dt]/max(n200[dt],1):.1f}({n200[dt]})", f"{100*above50[dt]/max(n50[dt],1):.1f}", low52[dt], f"({n52[dt]})")
