# -*- coding: utf-8 -*-
import json, math
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
SP = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")

def build():
    bt = json.loads((ROOT/"public/data/backtest-volatility-pilot.json").read_text(encoding='utf-8'))
    ev = bt['events']; per_date = {p['scan_date']:p for p in bt['per_date']}
    reg = json.loads((ROOT/"public/data/market-regime.json").read_text(encoding='utf-8'))['series']
    rd = [r['date'] for r in reg]
    ridx = {d:i for i,d in enumerate(rd)}
    br = json.loads((SP/"breadth_series.json").read_text(encoding='utf-8'))
    bidx = {d:i for i,d in enumerate(br['dates'])}
    ad = json.loads((SP/"adv_dec.json").read_text(encoding='utf-8'))
    adates = sorted(ad)
    aidx = {d:i for i,d in enumerate(adates)}

    # 국면 전환 후 경과일
    flip = {}
    last = None; cnt = 0
    for i,r in enumerate(reg):
        if last is None or r['up'] != last:
            cnt = 0; last = r['up']
        else:
            cnt += 1
        flip[r['date']] = cnt

    days = defaultdict(list)
    for e in ev:
        days[e['scan_date']].append(e)

    rows = []
    for S in sorted(days):
        es = days[S]
        i = ridx.get(S)
        if i is None: continue
        m = {'scan_date':S, 'entry_date':es[0]['entry_date'], 'n':len(es)}
        m['up'] = reg[i]['up']
        idx = reg[i]['index']; ma = reg[i]['ma20']
        m['dist_ma20'] = (idx/ma - 1)*100 if ma else None
        m['slope_ma20_5'] = (ma/reg[i-5]['ma20'] - 1)*100 if i>=5 and reg[i-5]['ma20'] else None
        m['slope_ma20_10'] = (ma/reg[i-10]['ma20'] - 1)*100 if i>=10 and reg[i-10]['ma20'] else None
        m['ret5'] = (idx/reg[i-5]['index'] - 1)*100 if i>=5 else None
        m['ret10'] = (idx/reg[i-10]['index'] - 1)*100 if i>=10 else None
        m['ret20'] = (idx/reg[i-20]['index'] - 1)*100 if i>=20 else None
        m['ret1'] = (idx/reg[i-1]['index'] - 1)*100 if i>=1 else None
        m['days_since_flip'] = flip[S]
        # breadth (series 캐시)
        bi = bidx.get(S)
        if bi is not None and br['tot200'][bi]:
            m['pct_above200'] = 100*br['above200'][bi]/br['tot200'][bi]
            m['pct_nh52'] = 100*br['nh52'][bi]/max(1,br['tot52'][bi])
            # 5일 변화
            if bi>=5 and br['tot200'][bi-5]:
                m['d_above200_5'] = m['pct_above200'] - 100*br['above200'][bi-5]/br['tot200'][bi-5]
            if bi>=5 and br['tot52'][bi-5]:
                m['d_nh52_5'] = m['pct_nh52'] - 100*br['nh52'][bi-5]/max(1,br['tot52'][bi-5])
        # adv/dec
        ai = aidx.get(S)
        if ai is not None:
            a = ad[S]
            m['ad'] = 100*a['up']/max(1,a['up']+a['dn'])
            m['ad_liq'] = 100*a['upl']/max(1,a['upl']+a['dnl'])
            if ai>=4:
                tot_u=tot_d=0
                for j in range(ai-4, ai+1):
                    x = ad[adates[j]]; tot_u+=x['up']; tot_d+=x['dn']
                m['ad5'] = 100*tot_u/max(1,tot_u+tot_d)
            if ai>=9:
                tot_u=tot_d=0
                for j in range(ai-9, ai+1):
                    x = ad[adates[j]]; tot_u+=x['up']; tot_d+=x['dn']
                m['ad10'] = 100*tot_u/max(1,tot_u+tot_d)
        p = per_date.get(S)
        m['n_candidates'] = p['n_candidates'] if p else None
        m['n_entered'] = p['n_entered'] if p else None
        # 결과
        w = sum(1 for e in es if e['result']=='win')
        l = sum(1 for e in es if e['result']=='loss')
        m['w']=w; m['l']=l; m['nres']=w+l
        m['wr'] = 100*w/(w+l) if w+l else None
        rets = [e.get('gain_at_resolve_pct') for e in es if e.get('gain_at_resolve_pct') is not None]
        m['mean_ret'] = sum(rets)/len(rets) if rets else None
        m['n_ret'] = len(rets)
        m['events'] = es
        rows.append(m)
    return rows

if __name__ == '__main__':
    rows = build()
    print("scan days", len(rows), "trades", sum(r['n'] for r in rows))
    miss = defaultdict(int)
    for k in ['dist_ma20','slope_ma20_5','ret5','ret10','pct_above200','pct_nh52','ad','ad5','ad10','n_candidates']:
        miss[k] = sum(1 for r in rows if r.get(k) is None)
    print(dict(miss))
    print(rows[0]['scan_date'], rows[-1]['scan_date'])
    r=rows[-1]; print({k:(round(v,2) if isinstance(v,float) else v) for k,v in r.items() if k!='events'})
