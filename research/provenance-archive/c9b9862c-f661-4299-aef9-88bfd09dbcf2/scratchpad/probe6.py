import sys, os, json, bisect, glob
import numpy as np
ROOT=r"C:\Users\hanul\playground\my-stock"
sys.path.insert(0, os.path.join(ROOT,"scripts"))
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat, DEFAULT_PARAMS as CHEAT_P
from canslim_lib.power_play import evaluate_power_play
from canslim_lib.pivot_backtest import truncate_series

P=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad\passmatrix.npz'
z=np.load(P, allow_pickle=True)
dates=list(z['dates']); codes=list(z['codes'])
idx=z['idx']; hr=z['hi_r']; lr=z['lo_r']; orr=z['open_r']; vol=z['vol']; pres=z['present']; ap=z['all_pass']

D="2026-08-13"; i=dates.index(D)
sel=[j for j in range(len(codes)) if ap[i,j]]
print("passmatrix all_pass at", D, len(sel))

SER=os.path.join(ROOT,".cache","ohlcv","series")
agree={"VCP":[0,0],"3C":[0,0],"PP":[0,0]}
pxdiff=[]; voldiff=[]
n=0
for j in sel:
    code=codes[j]
    p=os.path.join(SER, code+".json")
    if not os.path.exists(p): continue
    d=json.load(open(p,encoding="utf-8"))
    tc=truncate_series(d, D)
    if len(tc["closes"])<200: continue
    # build from passmatrix: last 400 rows where present
    rows=[k for k in range(max(0,i-420), i+1) if pres[k,j] and idx[k,j]>0]
    if len(rows)<200: continue
    tp={"dates":[dates[k] for k in rows],
        "closes":[float(idx[k,j]) for k in rows],
        "opens":[float(idx[k,j]*orr[k,j]) for k in rows],
        "highs":[float(idx[k,j]*hr[k,j]) for k in rows],
        "lows":[float(idx[k,j]*lr[k,j]) for k in rows],
        "volumes":[int(vol[k,j]) for k in rows]}
    # price scale differs (index vs won) -> compare ratios
    m=min(len(tc["closes"]), len(tp["closes"]))
    a=np.array(tc["closes"][-m:]); b=np.array(tp["closes"][-m:])
    r=b/a
    pxdiff.append(float(np.std(r)/np.mean(r)))
    va=np.array(tc["volumes"][-m:],dtype=float); vb=np.array(tp["volumes"][-m:],dtype=float)
    voldiff.append(float(np.mean(np.abs(va-vb))/max(1.0,np.mean(va))))
    for name,fn in (("VCP",lambda x:evaluate_vcp(x)),("3C",lambda x:evaluate_cheat(x,CHEAT_P)),("PP",lambda x:evaluate_power_play(x))):
        try: ra=fn(tc); rb=fn(tp)
        except Exception: continue
        agree[name][1]+=1
        if (ra.get("status")==rb.get("status")) and (bool(ra.get("entry_ready"))==bool(rb.get("entry_ready"))):
            agree[name][0]+=1
    n+=1
print("compared codes:", n)
for k,(ok,tot) in agree.items():
    print(f"{k}: status+entry_ready agree {ok}/{tot} = {ok/tot*100:.1f}%" if tot else k)
print("price-ratio CV (should be ~0 if same shape): median %.2e  max %.2e" % (np.median(pxdiff), np.max(pxdiff)))
print("volume mean abs rel diff: median %.4f  max %.4f" % (np.median(voldiff), np.max(voldiff)))
