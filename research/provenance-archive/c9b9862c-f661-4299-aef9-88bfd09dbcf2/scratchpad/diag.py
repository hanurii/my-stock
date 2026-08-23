# -*- coding: utf-8 -*-
import os, pickle, sys
sys.stdout.reconfigure(encoding='utf-8')
OUT = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
panel = pickle.load(open(os.path.join(OUT, "panel.pkl"), "rb"))
n=0
for p in panel:
    pv=p["pivot"]; T=pv*1.20; S=pv*0.90
    res=None
    if p["entry_h"]>=T and p["entry_l"]<=S: res="ambiguous"
    elif p["entry_h"]>=T: res="win"
    elif p["entry_l"]<=S: res="ambiguous"
    else:
        for d in p["days"]:
            ht=d["h"]>=T; hs=d["l"]<=S
            if ht and hs: res="ambiguous"; break
            if ht: res="win"; break
            if hs: res="loss"; break
    if res is None: res="unresolved"
    if res!=p["result"]:
        n+=1
        print(p["code"],p["name"],p["entry_date"],"shipped",p["result"],"days",p["days_held"],"maxg",p["max_gain_pct"],"maxdd",p["max_dd_pct"],"-> mine",res, "pivot",round(pv,1),"entryC",p["entry_c"])
print("total",n)
