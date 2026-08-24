import os, sys, json, time, urllib.request as ur, urllib.parse as up
sys.path.insert(0, 'scripts')
# load .env
for line in open('.env', encoding='utf-8'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k,v)
from canslim_lib import kis_api

tok = kis_api.get_access_token()
print('token ok:', bool(tok))

def base():
    env=(os.environ.get('KIS_ENV') or 'real').lower()
    return 'https://openapivts.koreainvestment.com:29443' if env in ('vps','mock','demo') else 'https://openapi.koreainvestment.com:9443'

def one_call(code, end_hhmmss):
    qs=up.urlencode({
        'FID_ETC_CLS_CODE':'',
        'FID_COND_MRKT_DIV_CODE':'J',
        'FID_INPUT_ISCD':code,
        'FID_INPUT_HOUR_1':end_hhmmss,
        'FID_PW_DATA_INCU_YN':'N',
    })
    url=f'{base()}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice?{qs}'
    h={'content-type':'application/json','authorization':f'Bearer {tok}',
       'appkey':os.environ['KIS_APP_KEY'],'appsecret':os.environ['KIS_APP_SECRET'],
       'tr_id':'FHKST03010200','custtype':'P'}
    req=ur.Request(url,headers=h)
    with ur.urlopen(req,timeout=8) as r:
        return json.loads(r.read().decode('utf-8'))

d=one_call('000890','153000')
print('rt_cd',d.get('rt_cd'),'msg',d.get('msg1'))
o2=d.get('output2') or []
print('n bars in 1 call:', len(o2))
if o2:
    print('first row keys:', list(o2[0].keys()))
    for r in o2[:3]:
        print(r.get('stck_bsop_date'), r.get('stck_cntg_hour'), 'O',r.get('stck_oprc'),'H',r.get('stck_hgpr'),'L',r.get('stck_lwpr'),'C',r.get('stck_prpr'),'V',r.get('cntg_vol'))
    print('...')
    print('last row:', o2[-1].get('stck_cntg_hour'), o2[-1].get('stck_prpr'))
