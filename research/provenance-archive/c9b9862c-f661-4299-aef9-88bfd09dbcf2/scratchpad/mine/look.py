import json, sys, math, statistics as st
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix
rows=json.load(open(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\trades_mine.json",encoding="utf-8"))
out=[]
for r in rows:
    if r["ss"] is None: continue
    s=ohlcv_matrix.get_series(r["code"])
    if not s: continue
    ds=s["dates"]; cl=s["closes"]
    if r["open_date"] not in ds: continue
    i=ds.index(r["open_date"])
    if i==0: continue
    dayret=(cl[i]/cl[i-1]-1)*100
    out.append((r,dayret))
def pear(x,y):
    mx=st.mean(x);my=st.mean(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
d=[x for _,x in out]; delta=[r["ss"]-r["sp"] for r,_ in out]; net=[r["net"] for r,_ in out]
print("n",len(out))
print("corr(buy-day return, ss-sp) =",round(pear(d,delta),3))
print("corr(buy-day return, net)   =",round(pear(d,net),3))
print("corr(sp, net)=",round(pear([r['sp'] for r,_ in out],net),3),"  corr(ss, net)=",round(pear([r['ss'] for r,_ in out],net),3))
print("mean buy-day return: winners",round(st.mean([x for r,x in out if r['net']>0]),2),"losers",round(st.mean([x for r,x in out if r['net']<=0]),2))
