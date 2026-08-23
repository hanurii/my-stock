# -*- coding: utf-8 -*-
"""기전 검증: '신고가 과열' 이 실제로 시장 천장을 짚나 (지수 250일 전체, 매매 데이터 밖 구간 포함)"""
import json
from pathlib import Path
SP=Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
ROOT=Path(r"C:\Users\hanul\playground\my-stock")
br=json.loads((SP/"breadth_series.json").read_text(encoding='utf-8'))
nh={d:100*n/max(1,t) for d,n,t in zip(br['dates'],br['nh52'],br['tot52']) if t}
reg=json.loads((ROOT/"public/data/market-regime.json").read_text(encoding='utf-8'))['series']
CUT=7.92
recs=[]
for i,r in enumerate(reg):
    v=nh.get(r['date'])
    if v is None: continue
    fwd={}
    for h in (5,10,20):
        if i+h < len(reg): fwd[h]=(reg[i+h]['index']/r['index']-1)*100
    recs.append((r['date'], v, r['up'], fwd))
upr=[x for x in recs if x[2]]
print(f"지수 계열 {len(recs)}일 (상승국면 {len(upr)}일), 기간 {recs[0][0]}~{recs[-1][0]}")
for h in (5,10,20):
    hot=[x[3][h] for x in upr if x[1]>=CUT and h in x[3]]
    cool=[x[3][h] for x in upr if x[1]<CUT and h in x[3]]
    if not hot: continue
    print(f"  상승국면 {h}일 뒤 지수 수익률: 과열날 {sum(hot)/len(hot):+5.2f}% (n={len(hot)}) vs 평소날 {sum(cool)/len(cool):+5.2f}% (n={len(cool)})  음수비율 과열 {100*sum(1 for v in hot if v<0)/len(hot):.0f}% vs 평소 {100*sum(1 for v in cool if v<0)/len(cool):.0f}%")
# 과열날이 어느 달에 있었나 (매매 데이터 밖 포함)
hd=[x[0] for x in upr if x[1]>=CUT]
print(f"\n지수 계열 전체 과열날 {len(hd)}일: {', '.join(hd)}")
