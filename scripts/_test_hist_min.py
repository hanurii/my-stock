import os,sys,json,urllib.request as ur,urllib.parse as up
sys.path.insert(0,'scripts')
for line in open('.env',encoding='utf-8'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k,v)
from canslim_lib import kis_api
tok=kis_api.get_access_token()
h={'content-type':'application/json','authorization':f'Bearer {tok}','appkey':os.environ['KIS_APP_KEY'],'appsecret':os.environ['KIS_APP_SECRET'],'custtype':'P'}

def try_daily_min(code,date,end='153000'):
    # TR FHKST03010230 = 주식일별분봉조회 (과거 특정일 분봉)
    qs=up.urlencode({'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':code,'FID_INPUT_DATE_1':date,'FID_INPUT_HOUR_1':end,'FID_PW_DATA_INCU_YN':'Y','FID_FAKE_TICK_INCU_YN':'N'})
    url=f'https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice?{qs}'
    hh=dict(h); hh['tr_id']='FHKST03010230'
    try:
        with ur.urlopen(ur.Request(url,headers=hh),timeout=8) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'_err':str(e)}

for date in ['20260617','20260610','20260602','20260520','20260424']:
    d=try_daily_min('000890',date)
    if '_err' in d: print(date,'HTTP err',d['_err'][:60]); continue
    o2=d.get('output2') or []
    nonempty=[x for x in o2 if x.get('stck_cntg_hour')]
    print(f"{date}: rt={d.get('rt_cd')} msg={d.get('msg1','')[:20]} bars={len(nonempty)} "
          + (f"first={nonempty[0].get('stck_cntg_hour')}({nonempty[0].get('stck_prpr')}) last={nonempty[-1].get('stck_cntg_hour')}" if nonempty else ""))
