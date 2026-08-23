import sys, json
sys.path.insert(0,'C:/Users/hanul/playground/my-stock/scripts')
from canslim_lib import ohlcv_matrix
from canslim_lib.sell_rules import evaluate_holding, avg_volume
H=json.load(open('C:/Users/hanul/playground/my-stock/public/data/sepa-holdings.json',encoding='utf-8'))['holdings']
for h in H:
    if h['code'] not in ('076610','053260','159010','034730','071200'): continue
    s=ohlcv_matrix.get_series(h['code'])
    for pv,tag in ((h['pivot_price'],'현행'),(None,'피벗없음')):
        r=evaluate_holding(s,h['buy_datetime'][:10],h['buy_price'],h['stop_loss_pct'],pivot_price=pv)
        print(f"{h['code']} {h['name'][:9]:10s} [{tag:5s} pv={pv}] signal={r['signal']} viol={r['violation_count']} bo={r['breakout_date']} est={r['breakout_date_estimated']} ext={r['extension_pct']} profit={r['profit_pct']}")
        for x in r['rules']:
            print(f"        {x['id']}: {x['status']} — {x['detail']}")
    # buy-day volume ratio
    byi=max(i for i,x in enumerate(s['dates']) if x<=h['buy_datetime'][:10])
    av=avg_volume(s['volumes'],byi)
    print(f"        [참고] 매수일 {s['dates'][byi]} 거래량 {s['volumes'][byi]:,} / 50일평균 {av and round(av):,} = {av and round(s['volumes'][byi]/av,2)}배")
    print()
