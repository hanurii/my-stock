import json, sys, statistics
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix

sc=json.load(open('public/data/scorecard.json',encoding='utf-8'))
fills=json.load(open('public/data/scorecard-fills.json',encoding='utf-8'))['fills']
trades=[t for t in sc['trades'] if t['close_date']>='2026-08-01']

def first_buy_date(code, open_date):
    # first buy fill on/after open_date for the code (open_date itself is the first buy)
    return open_date

def stats(code, day):
    s=ohlcv_matrix.get_series(code)
    d=s['dates']; 
    if day not in d:
        return None
    i=d.index(day)
    v=s['volumes']; c=s['closes']; h=s['highs']
    prior=v[max(0,i-50):i]
    avg50=sum(prior)/len(prior) if prior else None
    ratio=v[i]/avg50 if avg50 else None
    ma200=sum(c[i-199:i+1])/200 if i>=199 else None
    ma150=sum(c[i-149:i+1])/150 if i>=149 else None
    ma50=sum(c[i-49:i+1])/50 if i>=49 else None
    hi52=max(h[max(0,i-251):i+1])
    lo52=min(s['lows'][max(0,i-251):i+1])
    return dict(idx=i, close=c[i], open=s['opens'][i], high=h[i], low=s['lows'][i], vol=v[i], avg50=avg50, ratio=ratio,
                ma200=ma200, ma150=ma150, ma50=ma50, hi52=hi52, lo52=lo52,
                below200=(c[i]<ma200) if ma200 else None,
                below150=(c[i]<ma150) if ma150 else None,
                off_hi52_pct=(c[i]/hi52-1)*100, above_lo52_pct=(c[i]/lo52-1)*100,
                ndays=len(d))

def counterfactual(code, open_date, close_date, avg_buy, stop_pct=-5.0):
    s=ohlcv_matrix.get_series(code)
    d=s['dates']; i0=d.index(open_date); i1=d.index(close_date)
    stop=avg_buy*(1+stop_pct/100)
    for i in range(i0, i1+1):
        lo=s['lows'][i]; op=s['opens'][i]
        if lo<=stop:
            # conservative: if open already below stop -> open; else stop price
            touch_px = min(stop, op)
            nxt_open = s['opens'][i+1] if i+1<len(d) else None
            return dict(touch_date=d[i], touch_px=touch_px, next_open=nxt_open, day_low=lo, day_open=op)
    return None

out=[]
for t in trades:
    st=stats(t['code'], t['open_date'])
    out.append((t,st))
    print(f"{t['name']:10s} {t['outcome']:4s} open={t['open_date']} close={t['close_date']} net%={t['net_pct']:7.2f} won={t['net_won']:>10,} "
          f"volx={st['ratio']:.2f} vol={st['vol']:,} avg50={st['avg50']:,.0f} close={st['close']} ma200={st['ma200'] and round(st['ma200'])} below200={st['below200']} "
          f"ma150={st['ma150'] and round(st['ma150'])} below150={st['below150']} ma50={st['ma50'] and round(st['ma50'])} off52hi={st['off_hi52_pct']:.1f}% up_from_lo52={st['above_lo52_pct']:.0f}% O/H/L/C={st['open']}/{st['high']}/{st['low']}/{st['close']}")

print()
losses=[(t,st) for t,st in out if t['outcome']=='loss']
wins=[(t,st) for t,st in out if t['outcome']=='win']
print('loss ratios', sorted(round(st['ratio'],2) for t,st in losses))
print('win ratios', sorted(round(st['ratio'],2) for t,st in wins))
print('median loss', statistics.median(st['ratio'] for t,st in losses), 'median win', statistics.median(st['ratio'] for t,st in wins))
print('loss total', sum(t['net_won'] for t,st in losses), 'n', len(losses))
print('win total', sum(t['net_won'] for t,st in wins), 'n', len(wins))
c0818=[t for t,st in losses if t['open_date']=='2026-08-18']
print('0818 cluster losses', [(t['name'],t['net_won']) for t in c0818], sum(t['net_won'] for t in c0818))
print('low vol (<1.0) losses', [(t['name'],round(st['ratio'],2)) for t,st in losses if st['ratio']<1.0])
print('below200 losses', [(t['name']) for t,st in losses if st['below200']])

print()
print('COUNTERFACTUAL -5% for trades opened >= 2026-08-13')
tot_actual=0; tot_cf_touch=0; tot_cf_next=0
for t,st in out:
    if t['open_date']<'2026-08-13': continue
    cf=counterfactual(t['code'],t['open_date'],t['close_date'],t['avg_buy'])
    qty=t['buy_qty']
    actual=t['net_won']
    tot_actual+=actual
    if cf:
        # fee/tax: after 8/18 new broker tax 0.2% only; before fees 0.14%+0.2%.
        sell_cost_rate = 0.002 if cf['touch_date']>='2026-08-18' else 0.0034
        buy_cost_rate = 0.0 if t['open_date']>='2026-08-18' else 0.0014
        def net(px):
            return round(qty*(px*(1-sell_cost_rate)-t['avg_buy']*(1+buy_cost_rate)))
        n_touch=net(cf['touch_px']); n_next=net(cf['next_open']) if cf['next_open'] else None
        tot_cf_touch+=n_touch; tot_cf_next+= (n_next if n_next is not None else n_touch)
        print(f"{t['name']:10s} buy {t['open_date']} @{t['avg_buy']} actual {actual:>10,} ({t['net_pct']}%) | -5% touch {cf['touch_date']} open={cf['day_open']} low={cf['day_low']} exit@touch={cf['touch_px']:.0f} -> {n_touch:>10,} | next open={cf['next_open']} -> {n_next}")
    else:
        tot_cf_touch+=actual; tot_cf_next+=actual
        print(f"{t['name']:10s} buy {t['open_date']} @{t['avg_buy']} actual {actual:>10,} ({t['net_pct']}%) | -5% never touched -> keep actual")
print('actual total', tot_actual, ' cf(touch/gap-open conservative)', tot_cf_touch, ' cf(next-day open)', tot_cf_next)

# buys per session 8/13~8/20
from collections import Counter
buys=[f for f in fills if f['side']=='buy' and '2026-08-13'<=f['date']<='2026-08-20']
cnt=Counter(f['date'] for f in buys)
print('buy fills per day', dict(cnt), 'total', len(buys))
s=ohlcv_matrix.get_series('005930')
print('sessions 8/13-8/20', [x for x in s['dates'] if '2026-08-13'<=x<='2026-08-20'])
