import json, random, statistics, collections

BT='C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json'
PIT='C:/Users/hanul/AppData/Local/Temp/pit_index.json'

def load_events():
    d=json.load(open(BT,encoding='utf-8'))
    return d['events']

BUY_FEE=0.0014
SELL_FEE=0.0034

def net_mult(g_pct):
    return (1.0+g_pct/100.0)*(1.0-SELL_FEE)/(1.0+BUY_FEE)

def sim_slot5(events, allowed, slots=5, n_iter=300, seed=0, fee=True):
    """events: list; allowed: set of event ids (index) permitted to enter."""
    evs=[e for i,e in enumerate(events) if i in allowed]
    by_entry=collections.defaultdict(list)
    for e in evs: by_entry[e['entry_date']].append(e)
    all_dates=sorted(set([e['entry_date'] for e in evs]+[e['resolve_date'] for e in evs]))
    rnd=random.Random(seed)
    finals=[]
    for it in range(n_iter):
        equity=1.0
        cash=1.0
        open_pos=[]  # (resolve_date, amount_invested, gain)
        for dt in all_dates:
            # close positions resolving on dt (before opening new)
            still=[]
            for rd,amt,g in open_pos:
                if rd<=dt:
                    m = net_mult(g) if fee else (1.0+g/100.0)
                    cash += amt*m
                else:
                    still.append((rd,amt,g))
            open_pos=still
            cands=by_entry.get(dt,[])
            if cands:
                cands=list(cands); rnd.shuffle(cands)
                for e in cands:
                    if len(open_pos)>=slots: break
                    # equity = cash + open at cost basis (approx)
                    eq = cash + sum(a for _,a,_ in open_pos)
                    size = eq/slots
                    if size>cash: size=cash
                    if size<=1e-9: break
                    cash-=size
                    open_pos.append((e['resolve_date'],size,e['gain_at_resolve_pct']))
        for rd,amt,g in open_pos:
            m = net_mult(g) if fee else (1.0+g/100.0)
            cash+=amt*m
        finals.append(cash-1.0)
    finals.sort()
    return statistics.median(finals)*100.0, finals

def pit_regime():
    p=json.load(open(PIT,encoding='utf-8'))
    return dict(zip(p['dates'], p['up']))
