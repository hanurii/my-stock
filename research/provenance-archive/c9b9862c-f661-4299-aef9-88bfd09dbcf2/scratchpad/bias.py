# -*- coding: utf-8 -*-
import json, collections, pickle, os
SP=os.path.dirname(os.path.abspath(__file__)); ROOT=r"C:/Users/hanul/playground/my-stock"
D=pickle.load(open(SP+"/regime_metrics.pkl","rb"))
pos,M,up=D["pos"],D["M"],D["up"]
d=json.load(open(ROOT+"/public/data/backtest-volatility-pilot.json",encoding="utf-8"))
S=M["⑬상승일비율10"]
allev=d["events"]
def band(e):
    i=pos[e["entry_date"]]-1
    if not up[i]: return "조정국면"
    v=S[i]
    return "상승-연일상승(80%+)" if v>=80 else ("상승-보통" if v>=55 else "상승-횡보/눌림(≤50%)")
c=collections.defaultdict(collections.Counter)
for e in allev: c[band(e)][e["result"]]+=1
print("[미결착(ambiguous/unresolved) 제외 편향 점검]")
for b,cc in c.items():
    tot=sum(cc.values()); res=cc["win"]+cc["loss"]
    print(f"  {b:<22} 전체 {tot:>3}건, 결착 {res:>3}, 미결착 {tot-res:>2} ({100*(tot-res)/tot:4.1f}%), "
          f"결착승률 {100*cc['win']/res:4.1f}%, 최악가정(미결착=패) {100*cc['win']/tot:4.1f}%")
# max_gain distribution for hot days (were they close to +20?)
import statistics
for b in c:
    g=[e["max_gain_pct"] for e in allev if band(e)==b and e["result"]=="loss"]
    if g: print(f"  {b:<22} 패배건 최대상승 중앙값 {statistics.median(g):+.1f}%")
