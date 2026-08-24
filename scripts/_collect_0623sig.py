# -*- coding: utf-8 -*-
import os,sys,json,time,glob,urllib.request as ur,urllib.parse as up
sys.path.insert(0,'scripts')
for line in open('.env',encoding='utf-8'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k,v)
from canslim_lib import kis_api
tok=kis_api.get_access_token()

codes=json.load(open('scripts/_codes_0623sig.json',encoding='utf-8'))
# add 송원사업 from pdata (no series file)
f=sorted(glob.glob('.cache/pdata/*.json'))[-1]; pd=json.load(open(f,encoding='utf-8'))
for code,r in pd.items():
    if r['itmsNm']=='송원사업': codes['송원사업']=code
# existing collected bars
existing={}
for fp in ['scripts/_min3_20260624.json','scripts/_min3_20260624_b2.json']:
    existing.update(json.load(open(fp,encoding='utf-8')))

def call(code,end):
    qs=up.urlencode({'FID_ETC_CLS_CODE':'','FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':code,'FID_INPUT_HOUR_1':end,'FID_PW_DATA_INCU_YN':'N'})
    url=f'https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice?{qs}'
    h={'content-type':'application/json','authorization':f'Bearer {tok}','appkey':os.environ['KIS_APP_KEY'],'appsecret':os.environ['KIS_APP_SECRET'],'tr_id':'FHKST03010200','custtype':'P'}
    for _ in range(4):
        try:
            with ur.urlopen(ur.Request(url,headers=h),timeout=8) as r:
                d=json.loads(r.read().decode('utf-8'))
            if d.get('rt_cd')=='0': return d.get('output2') or []
            if d.get('msg_cd')=='EGW00201': time.sleep(0.6); continue
            return []
        except Exception: time.sleep(0.4)
    return []
def dec(h):
    s=int(h[:2])*3600+int(h[2:4])*60-60
    return None if s<0 else f'{s//3600:02d}{(s%3600)//60:02d}00'
def fetch(code):
    bars={}; end='153000'
    for _ in range(20):
        rows=call(code,end); time.sleep(0.07)
        if not rows: break
        for r in rows:
            bars[r['stck_cntg_hour']]={'o':float(r['stck_oprc']),'h':float(r['stck_hgpr']),'l':float(r['stck_lwpr']),'c':float(r['stck_prpr']),'v':float(r['cntg_vol'])}
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
            sub=[bars[k] for k in (f'{hh:02d}{mm+x:02d}00' for x in range(3)) if k in bars]
            if not sub: continue
            out.append({'t':f'{hh:02d}:{mm:02d}','o':sub[0]['o'],'h':max(s['h'] for s in sub),'l':min(s['l'] for s in sub),'c':sub[-1]['c'],'v':sum(s['v'] for s in sub)})
    return out

res={}; new=0; reuse=0
for nm,code in codes.items():
    if nm in existing and existing[nm].get('bars'):
        res[nm]=existing[nm]; reuse+=1; continue
    b=to3(fetch(code)); res[nm]={'code':code,'bars':b}; new+=1
    print(f'  fetched {code} {nm} ({len(b)} bars)', flush=True)
json.dump(res, open('scripts/_min3_0624_for0623sig.json','w',encoding='utf-8'), ensure_ascii=False)
print(f'done: {len(res)} stocks (reuse {reuse}, new {new})')
