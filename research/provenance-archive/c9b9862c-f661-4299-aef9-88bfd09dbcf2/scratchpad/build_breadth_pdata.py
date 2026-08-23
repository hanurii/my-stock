# -*- coding: utf-8 -*-
"""pdata 일자 캐시 -> 그날 상승/하락 종목 수 (진짜 시점 유니버스, 상폐 포함)"""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
PD = ROOT/".cache"/"pdata"
OUT = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")

# 2025-10-01 이후만 (진입 2025-11-26 시작, 5·10일 평균 여유)
files = sorted(PD.glob("price_2025*.json")) + sorted(PD.glob("price_2026*.json"))
files = [f for f in files if f.stem[6:] >= "20251001"]
print("files", len(files))
res = {}
for i,f in enumerate(files):
    bd = f.stem[6:]
    d = f"{bd[:4]}-{bd[4:6]}-{bd[6:]}"
    try:
        rows = json.loads(f.read_text(encoding='utf-8'))
    except Exception:
        continue
    up=dn=fl=0; upl=dnl=0
    for k,r in rows.items():
        mc = r.get('mrktCtg')
        if mc not in ('KOSPI','KOSDAQ'): continue
        fr = r.get('fltRt')
        if fr is None: continue
        if fr > 0: up+=1
        elif fr < 0: dn+=1
        else: fl+=1
        # 유동성 있는 종목만(거래대금 5억+) — 파일럿 유니버스와 유사
        if (r.get('trPrc_eok') or 0) >= 5.0:
            if fr>0: upl+=1
            elif fr<0: dnl+=1
    res[d] = {'up':up,'dn':dn,'fl':fl,'upl':upl,'dnl':dnl}
    if (i+1)%50==0: print(i+1, d, flush=True)

(OUT/"adv_dec.json").write_text(json.dumps(res), encoding='utf-8')
print("saved", len(res))
ks = sorted(res)[-3:]
for k in ks: print(k, res[k])
