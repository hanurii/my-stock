# -*- coding: utf-8 -*-
import json,statistics,io,sys,os,glob
alld=json.load(open('scripts/_min3_0624_for0623sig.json',encoding='utf-8'))
out=io.StringIO()
def p(*x): print(*x,file=out)

# 1) basket breadth: 6/23 close -> 6/24 close for the 45
moves=[]
for nm,d in alld.items():
    code=d['code']; sp=f'.cache/ohlcv/series/{code}.json'
    if not os.path.exists(sp): continue
    c623=json.load(open(sp))['closes'][-1]; c624=d['bars'][-1]['c']
    moves.append((nm,(c624/c623-1)*100))
up=sum(1 for _,m in moves if m>0)
p(f"[검색식 45종목] 6/24 등락(6/23종가→종가): 평균 {statistics.mean([m for _,m in moves]):+.2f}%  중앙값 {statistics.median([m for _,m in moves]):+.2f}%  상승 {up}/{len(moves)}")

# 2) market index 6/24 via FDR
try:
    import FinanceDataReader as fdr
    for sym,nm in [('KS11','코스피'),('KQ11','코스닥')]:
        df=fdr.DataReader(sym,'2026-06-20','2026-06-24')
        if len(df)>=2:
            ch=(df['Close'].iloc[-1]/df['Close'].iloc[-2]-1)*100
            p(f"[{nm} 지수] 6/24 등락: {ch:+.2f}%  (종가 {df['Close'].iloc[-1]:.1f})")
except Exception as e:
    p(f"[지수] FDR 실패: {e}")

# 3) broad-market breadth proxy: random 120 stocks 6/23->6/24 via KIS current price (today close)
sys.path.insert(0,'scripts')
for line in open('.env',encoding='utf-8'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k,v)
from canslim_lib import kis_api
import urllib.request as ur, urllib.parse as up, time
tok=kis_api.get_access_token()
series_files=sorted(glob.glob('.cache/ohlcv/series/*.json'))
# deterministic sample across the universe
sample=series_files[::25][:140]
def cur_close(code):
    qs=up.urlencode({'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':code})
    url=f'https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price?{qs}'
    h={'content-type':'application/json','authorization':f'Bearer {tok}','appkey':os.environ['KIS_APP_KEY'],'appsecret':os.environ['KIS_APP_SECRET'],'tr_id':'FHKST01010100','custtype':'P'}
    try:
        with ur.urlopen(ur.Request(url,headers=h),timeout=8) as r:
            d=json.loads(r.read().decode('utf-8'))
        o=d.get('output') or {}
        return float(o.get('stck_prpr')), float(o.get('prdy_ctrt'))  # 현재가, 전일대비율(%)
    except Exception: return None,None
bm=[]
for sf in sample:
    code=os.path.basename(sf)[:-5]
    _,ctrt=cur_close(code); time.sleep(0.05)
    if ctrt is not None: bm.append(ctrt)
if bm:
    upb=sum(1 for x in bm if x>0)
    p(f"[전체시장 표본 {len(bm)}종목] 6/24 등락(전일대비): 평균 {statistics.mean(bm):+.2f}%  중앙값 {statistics.median(bm):+.2f}%  상승 {upb}/{len(bm)} ({100*upb/len(bm):.0f}%)")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
