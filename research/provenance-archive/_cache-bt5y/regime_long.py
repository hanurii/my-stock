# -*- coding: utf-8 -*-
"""2020~2026 시점 국면 지수 — 사전등록 주 정의(등가중>20MA) + 대조군(코스피 20MA)."""
import json, glob, os, statistics as st
PD='C:/Users/hanul/playground/my-stock/.cache/pdata/'
out_p='C:/Users/hanul/AppData/Local/Temp/bt5y/regime_long.json'
dates=[]; ew=[]; cw=[]
prev_cap={}
for f in sorted(glob.glob(PD+'price_*.json')):
    d=os.path.basename(f)[6:14]; date=f"{d[:4]}-{d[4:6]}-{d[6:]}"
    try: recs=json.loads(open(f,encoding='utf-8').read())
    except Exception: continue
    rs=[]; num=den=0.0
    for code,r in recs.items():
        if r.get('mrktCtg') not in ('KOSPI','KOSDAQ'): continue
        fr=r.get('fltRt')
        if fr is None or abs(fr)>31: continue
        rs.append(fr)
        pc=prev_cap.get(code)
        if pc: num+=pc*fr; den+=pc
    for code,r in recs.items():
        if r.get('mrktCtg') in ('KOSPI','KOSDAQ') and r.get('market_cap_eok'):
            prev_cap[code]=r['market_cap_eok']
    if len(rs)<500: continue
    dates.append(date); ew.append(st.mean(rs)); cw.append(num/den if den else 0.0)

def cum(a):
    v=100.0; o=[]
    for r in a: v*=(1+r/100); o.append(v)
    return o
EWI=cum(ew); CWI=cum(cw)
def ma(a,n): return [None if i<n-1 else sum(a[i-n+1:i+1])/n for i in range(len(a))]
ew20=ma(EWI,20)

# 대조군: 코스피 20일선
import FinanceDataReader as fdr
ks=fdr.DataReader('KS11', dates[0], dates[-1])
kmap={d.strftime('%Y-%m-%d'):float(c) for d,c in zip(ks.index, ks['Close'])}
kser=[kmap.get(d) for d in dates]
# 결측은 직전값 유지
last=None
for i,v in enumerate(kser):
    if v is None: kser[i]=last
    else: last=v
ks20=ma([v if v else 0 for v in kser],20)

res={'dates':dates,'ew':EWI,'cw':CWI,'kospi':kser,
     'up_ew20':[None if ew20[i] is None else EWI[i]>ew20[i] for i in range(len(dates))],
     'up_ks20':[None if (ks20[i] is None or not kser[i]) else kser[i]>ks20[i] for i in range(len(dates))]}
json.dump(res, open(out_p,'w'), ensure_ascii=False)
print(f"{dates[0]} ~ {dates[-1]}  {len(dates)}일")
print(f"{'연도':<6}{'등가중':>10}{'시총가중':>11}{'코스피':>11}{'상승국면일(주정의)':>18}")
for y in range(2020,2027):
    ix=[i for i,d in enumerate(dates) if d.startswith(str(y))]
    if not ix: continue
    a,b=ix[0],ix[-1]
    up=[res['up_ew20'][i] for i in ix if res['up_ew20'][i] is not None]
    print(f"{y:<6}{(EWI[b]/EWI[a]-1)*100:>+9.1f}%{(CWI[b]/CWI[a]-1)*100:>+10.1f}%"
          f"{((kser[b]/kser[a]-1)*100 if kser[a] and kser[b] else 0):>+10.1f}%"
          f"{f'{sum(up)}/{len(up)} ({sum(up)/len(up)*100:.0f}%)':>18}")
