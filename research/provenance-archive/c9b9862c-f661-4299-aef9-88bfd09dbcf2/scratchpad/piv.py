import sys, json
sys.path.insert(0,'C:/Users/hanul/playground/my-stock/scripts')
from canslim_lib import ohlcv_matrix
from canslim_lib.sell_rules import find_breakout_index, avg_volume
H=json.load(open('C:/Users/hanul/playground/my-stock/public/data/sepa-holdings.json',encoding='utf-8'))['holdings']
fb={h['code']:h for h in json.load(open('C:/Users/hanul/playground/my-stock/public/data/sepa-holdings-feedback.json',encoding='utf-8'))['holdings']}
for h in H:
    s=ohlcv_matrix.get_series(h['code'])
    bd=h['buy_datetime'][:10]; pv=h['pivot_price']
    bi,est=find_breakout_index(s,bd,pv)
    d=s['dates'][bi]
    av=avg_volume(s['volumes'],bi)
    ratio=(s['volumes'][bi]/av) if av else None
    # buy-day index
    byi=max(i for i,x in enumerate(s['dates']) if x<=bd)
    # price context on buy day
    print(f"{h['code']} {h['name'][:10]:11s} buy {bd} @{h['buy_price']:>8} pivot={pv} buy/pivot={h['buy_price']/pv*100-100:+6.2f}%")
    print(f"    돌파일판정={d} estimated={est} (매수일={s['dates'][byi]}) 그날거래량비={ratio and round(ratio,2)}")
    print(f"    매수일 O/H/L/C={s['opens'][byi]},{s['highs'][byi]},{s['lows'][byi]},{s['closes'][byi]}  현재종가={s['closes'][-1]} ({s['dates'][-1]})")
    f=fb[h['code']]
    print(f"    feedback: signal={f['signal']} viol={f['violation_count']} rules={[ (r['id'],r['status']) for r in f.get('rules',[])]}")
