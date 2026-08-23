# -*- coding: utf-8 -*-
import json, glob, os, collections, statistics as st
ROOT='C:/Users/hanul/playground/my-stock/'
files=sorted(glob.glob(ROOT+'.cache/pdata/price_*.json'))
files=[f for f in files if '20251126'<=os.path.basename(f)[6:14]<='20260821']
prev=None; lvl_cw=1.0; lvl_ew=1.0
contrib=collections.defaultdict(float); nm={}
ew_daily=[]
for f in files:
    p=json.load(open(f,encoding='utf-8'))
    if prev is not None:
        # 전일 시총 가중
        tot=0.0; items=[]
        for c,v in p.items():
            pv=prev.get(c)
            if not pv: continue
            try:
                cap=float(pv.get('market_cap_eok') or 0); fl=float(v.get('fltRt') or 0)
            except Exception: continue
            if cap<=0: continue
            if abs(fl)>60: continue     # 리베이스 아티팩트 차단
            items.append((c,cap,fl)); tot+=cap; nm[c]=v.get('itmsNm','')
        if tot>0:
            r=sum(cap*fl/100 for c,cap,fl in items)/tot
            for c,cap,fl in items: contrib[c]+= lvl_cw*(cap/tot)*(fl/100)*100
            lvl_cw*= (1+r)
            rew=st.mean(fl for c,cap,fl in items)/100
            lvl_ew*= (1+rew); ew_daily.append(rew)
    prev=p
print('전종목 시총가중 %+.2f%%   등가중 %+.2f%%   (%d거래일)'%((lvl_cw-1)*100,(lvl_ew-1)*100,len(files)))
rk=sorted(contrib.items(), key=lambda x:-x[1])
tot=(lvl_cw-1)*100
print('지수 총상승 %.2f%%p'%tot)
for c,v in rk[:10]:
    print('  %-12s %+6.2f%%p  (%.1f%%)'%(nm.get(c,c), v, 100*v/tot))
print('상위2 합 %.1f%% / 상위5 %.1f%% / 상위10 %.1f%%'%(
    100*sum(v for _,v in rk[:2])/tot, 100*sum(v for _,v in rk[:5])/tot, 100*sum(v for _,v in rk[:10])/tot))
