# -*- coding: utf-8 -*-
import os,sys,json,time,glob,urllib.request as ur,urllib.parse as up
sys.path.insert(0,'scripts')
for line in open('.env',encoding='utf-8'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k,v)
from canslim_lib import kis_api
tok=kis_api.get_access_token()
DATE='20260624'

codes=json.load(open('scripts/_codes_user40.json',encoding='utf-8'))

# 캐시: code -> bars (기존 3개 파일)
cache={}
for fp in ['scripts/_min3_0624_for0623sig.json','scripts/_min3_20260624.json','scripts/_min3_20260624_b2.json']:
    if os.path.exists(fp):
        for nm,d in json.load(open(fp,encoding='utf-8')).items():
            if d.get('code') and d.get('bars'): cache[str(d['code'])]=d['bars']

def call(code,end):
    qs=up.urlencode({'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':code,'FID_INPUT_DATE_1':DATE,
                     'FID_INPUT_HOUR_1':end,'FID_PW_DATA_INCU_YN':'Y','FID_FAKE_TICK_INCU_YN':'N'})
    url=f'https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice?{qs}'
    h={'content-type':'application/json','authorization':f'Bearer {tok}','appkey':os.environ['KIS_APP_KEY'],
       'appsecret':os.environ['KIS_APP_SECRET'],'tr_id':'FHKST03010230','custtype':'P'}
    for _ in range(4):
        try:
            with ur.urlopen(ur.Request(url,headers=h),timeout=10) as r:
                d=json.loads(r.read().decode('utf-8'))
            if d.get('rt_cd')=='0': return d.get('output2') or []
            if d.get('msg_cd')=='EGW00201': time.sleep(0.6); continue
            return []
        except Exception: time.sleep(0.4)
    return []

def dec(h):
    s=int(h[:2])*3600+int(h[2:4])*60+int(h[4:6])-60
    return None if s<0 else f'{s//3600:02d}{(s%3600)//60:02d}{s%60:02d}'

def fetch(code):
    bars={}; end='153000'
    for _ in range(25):
        rows=call(code,end); time.sleep(0.08)
        if not rows: break
        for r in rows:
            t=r.get('stck_cntg_hour')
            if not t or not r.get('stck_prpr'): continue
            bars[t]={'o':float(r['stck_oprc']),'h':float(r['stck_hgpr']),'l':float(r['stck_lwpr']),
                     'c':float(r['stck_prpr']),'v':float(r.get('cntg_vol') or 0)}
        e=min(bars)
        if e<='090000': break
        n=dec(e)
        if not n or n>=end: break
        end=n
    return bars

def to3(bars):
    out=[]
    for hh in range(9,16):
        for mm in range(0,60,3):
            if hh==15 and mm>21: break
            keys=[f'{hh:02d}{mm+x:02d}00' for x in range(3)]
            sub=[bars[k] for k in keys if k in bars]
            if not sub: continue
            out.append({'t':f'{hh:02d}:{mm:02d}','o':sub[0]['o'],'h':max(s['h'] for s in sub),
                        'l':min(s['l'] for s in sub),'c':sub[-1]['c'],'v':sum(s['v'] for s in sub)})
    return out

res={}; reuse=0; new=0
for nm,code in codes.items():
    code=str(code)
    if code in cache:
        res[nm]={'code':code,'bars':cache[code]}; reuse+=1; continue
    b=to3(fetch(code)); res[nm]={'code':code,'bars':b}; new+=1
    print(f'  fetched {code} {nm}: {len(b)} 3min-bars', flush=True)
json.dump(res, open('scripts/_min3_user40_0624.json','w',encoding='utf-8'), ensure_ascii=False)
print(f'DONE {len(res)} stocks (reuse {reuse}, new {new})')
# 커버리지 체크
bad=[nm for nm,d in res.items() if not d['bars'] or d['bars'][0]['t']!='09:00']
print('빈/불완전:', bad if bad else '없음')
