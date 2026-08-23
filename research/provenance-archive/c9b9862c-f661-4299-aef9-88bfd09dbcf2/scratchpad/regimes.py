import json, bisect, collections, sys
sys.path.insert(0,'.')

IDX=json.load(open('idx.json'))
PIT=json.load(open('C:/Users/hanul/AppData/Local/Temp/pit_index.json',encoding='utf-8'))
LIVE=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))

def ma_flags(dates, closes, n):
    """returns dict date -> (close>MA(n)) using only data up to and including that date"""
    out={}
    for i in range(len(dates)):
        if i+1<n: out[dates[i]]=None; continue
        ma=sum(closes[i-n+1:i+1])/n
        out[dates[i]] = closes[i]>ma
    return out

def upday_flags(dates, closes):
    out={}
    for i in range(len(dates)):
        out[dates[i]] = None if i==0 else closes[i]>closes[i-1]
    return out

def build(sym):
    d=IDX[sym]; dates=sorted(d); closes=[d[x] for x in dates]
    return dates, closes

def asof(flagmap, dates_sorted, dt):
    """latest flag at date <= dt"""
    i=bisect.bisect_right(dates_sorted, dt)-1
    if i<0: return None
    return flagmap[dates_sorted[i]]

def asof_strict(flagmap, dates_sorted, dt):
    """latest flag at date STRICTLY < dt (for overseas markets)"""
    i=bisect.bisect_left(dates_sorted, dt)-1
    if i<0: return None
    return flagmap[dates_sorted[i]]

class Regime:
    def __init__(self, name, fn):
        self.name=name; self.fn=fn
    def __call__(self, ev): return self.fn(ev)

def make_all():
    R=[]
    # baseline: point-in-time equal weight 20MA
    pit_up=dict(zip(PIT['dates'],PIT['up']))
    R.append(Regime('EW20_baseline(등가중20일선)', lambda e: pit_up.get(e['scan_date'])))
    # cw
    pdates=PIT['dates']; cw=PIT['cw']
    cw20=ma_flags(pdates,cw,20)
    R.append(Regime('CW20(시총가중20일선)', lambda e: cw20.get(e['scan_date'])))
    ew=PIT['ew']
    for n in (10,20,30,50):
        f=ma_flags(pdates,ew,n)
        R.append(Regime(f'EW{n}(등가중{n}일선)', (lambda f: lambda e: f.get(e['scan_date']))(f)))
    # domestic indices - asof scan_date (inclusive)
    for sym,label in (('KS11','코스피'),('KQ11','코스닥'),('KS200','코스피200')):
        ds,cs=build(sym)
        for n in (10,20,50,100,200):
            f=ma_flags(ds,cs,n)
            R.append(Regime(f'{label}{n}일선',
                (lambda f,ds: lambda e: asof(f,ds,e['scan_date']))(f,ds)))
    # overseas: use last close strictly before ENTRY date (available pre-open in KR)
    for sym,label in (('IXIC','나스닥'),('US500','S&P500'),('DJI','다우')):
        ds,cs=build(sym)
        fu=upday_flags(ds,cs)
        R.append(Regime(f'{label} 전일종가상승',
            (lambda fu,ds: lambda e: asof_strict(fu,ds,e['entry_date']))(fu,ds)))
        for n in (20,50):
            f=ma_flags(ds,cs,n)
            R.append(Regime(f'{label}{n}일선',
                (lambda f,ds: lambda e: asof_strict(f,ds,e['entry_date']))(f,ds)))
    # live regime file
    lv={s['date']:s['up'] for s in LIVE['series']}
    lvd=sorted(lv)
    R.append(Regime('라이브 국면파일(market-regime.json)', lambda e: asof(lv,lvd,e['scan_date'])))
    # own-market 20MA
    ksd,ksc=build('KS11'); kqd,kqc=build('KQ11')
    ks20=ma_flags(ksd,ksc,20); kq20=ma_flags(kqd,kqc,20)
    def own(e):
        if e['market']=='KOSPI': return asof(ks20,ksd,e['scan_date'])
        return asof(kq20,kqd,e['scan_date'])
    R.append(Regime('자기시장 20일선(코스피주=코스피,코스닥주=코스닥)', own))
    # combos
    def both(e):
        a=asof(ks20,ksd,e['scan_date']); b=asof(kq20,kqd,e['scan_date'])
        if a is None or b is None: return None
        return a and b
    R.append(Regime('코스피20 AND 코스닥20', both))
    def either(e):
        a=asof(ks20,ksd,e['scan_date']); b=asof(kq20,kqd,e['scan_date'])
        if a is None or b is None: return None
        return a or b
    R.append(Regime('코스피20 OR 코스닥20', either))
    ixd,ixc=build('IXIC'); ix20=ma_flags(ixd,ixc,20)
    def ewnas(e):
        a=pit_up.get(e['scan_date']); b=asof_strict(ix20,ixd,e['entry_date'])
        if a is None or b is None: return None
        return a and b
    R.append(Regime('등가중20 AND 나스닥20', ewnas))
    return R
