import json, sys
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
L=json.load(open('public/data/sepa-buy-rec-ledger.json',encoding='utf-8'))['entries']
losses=[('005430','2026-08-05'),('275630','2026-07-31'),('005950','2026-08-18'),('383220','2026-07-31'),('900260','2026-08-03'),('007340','2026-08-11'),('009190','2026-08-13'),('083450','2026-08-13'),('252990','2026-08-13'),('122640','2026-08-18'),('131290','2026-08-18'),('034730','2026-08-18'),('446540','2026-08-18')]
print('LEDGER presence on buy date / any date')
for code,day in losses:
    on=[e for e in L if e['code']==code and e['date']==day]
    anyd=sorted({e['date'] for e in L if e['code']==code})
    print(code, day, 'on-date:', [(e['status'],e['score'],e.get('gate_near')) for e in on], 'dates:', anyd[-6:] if anyd else 'NONE')
print()
print('52wk high variants + close location + next days')
for code,day in losses:
    s=ohlcv_matrix.get_series(code); d=s['dates']; i=d.index(day)
    c=s['closes']; h=s['highs']; lo=s['lows']
    hi250h=max(h[max(0,i-249):i+1]); hi250c=max(c[max(0,i-249):i+1])
    hi_prior=max(h[max(0,i-251):i])  # excluding today
    cl=(c[i]-lo[i])/(h[i]-lo[i]) if h[i]>lo[i] else None
    # MA200 slope: ma200 today vs 20 days ago
    ma200=sum(c[i-199:i+1])/200; ma200_20=sum(c[i-219:i-19])/200
    nxt=[(d[j], round(s['opens'][j]), round(h[j]), round(lo[j]), round(c[j]), s['volumes'][j]) for j in range(i+1,min(i+4,len(d)))]
    print(f"{code} {day} close={c[i]:.0f} off_hi250(high)={(c[i]/hi250h-1)*100:.1f}% off_hi250(close)={(c[i]/hi250c-1)*100:.1f}% off_hi_prior={(c[i]/hi_prior-1)*100:.1f}% closeloc={cl and round(cl,2)} ma200_rising={ma200>ma200_20} 150>200={sum(c[i-149:i+1])/150>ma200} next={nxt}")
