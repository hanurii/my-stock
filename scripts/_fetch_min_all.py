import os, sys, json, time, urllib.request as ur, urllib.parse as up
sys.path.insert(0,'scripts')
for line in open('.env',encoding='utf-8'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k,v)
from canslim_lib import kis_api
tok=kis_api.get_access_token()

def base():
    return 'https://openapi.koreainvestment.com:9443'
def call(code,end):
    qs=up.urlencode({'FID_ETC_CLS_CODE':'','FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':code,
                     'FID_INPUT_HOUR_1':end,'FID_PW_DATA_INCU_YN':'N'})
    url=f'{base()}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice?{qs}'
    h={'content-type':'application/json','authorization':f'Bearer {tok}',
       'appkey':os.environ['KIS_APP_KEY'],'appsecret':os.environ['KIS_APP_SECRET'],
       'tr_id':'FHKST03010200','custtype':'P'}
    for _ in range(4):
        try:
            with ur.urlopen(ur.Request(url,headers=h),timeout=8) as r:
                d=json.loads(r.read().decode('utf-8'))
            if d.get('rt_cd')=='0': return d.get('output2') or []
            if d.get('msg_cd')=='EGW00201': time.sleep(0.6); continue
            return []
        except Exception:
            time.sleep(0.4)
    return []

def hhmm_dec(h):  # subtract 1 minute from HHMMSS
    s=int(h[:2])*3600+int(h[2:4])*60+int(h[4:6]); s-=60
    if s<0: return None
    return f'{s//3600:02d}{(s%3600)//60:02d}{s%60:02d}'

def fetch_day(code):
    bars={}  # hhmm -> row (1-min)
    end='153000'
    for _ in range(20):
        rows=call(code,end)
        time.sleep(0.08)
        if not rows: break
        for r in rows:
            t=r['stck_cntg_hour']
            bars[t]={'o':float(r['stck_oprc']),'h':float(r['stck_hgpr']),
                     'l':float(r['stck_lwpr']),'c':float(r['stck_prpr']),'v':float(r['cntg_vol'])}
        earliest=min(bars)
        if earliest<='090000': break
        nxt=hhmm_dec(earliest)
        if not nxt or nxt>=end: break
        end=nxt
    return bars

def to_3min(bars):
    # regular session 0900-1520 → 3-min buckets; ignore closing auction 1530 single print here
    out=[]
    for hh in range(9,16):
        for mm in range(0,60,3):
            if hh==15 and mm>21: break
            keys=[f'{hh:02d}{mm+k:02d}00' for k in range(3)]
            sub=[bars[k] for k in keys if k in bars and bars[k]['v']>=0 and bars[k]['c']>0]
            sub=[s for s in [bars.get(k) for k in keys] if s]
            if not sub: continue
            o=sub[0]['o']; c=sub[-1]['c']
            hi=max(s['h'] for s in sub); lo=min(s['l'] for s in sub); v=sum(s['v'] for s in sub)
            out.append({'t':f'{hh:02d}:{mm:02d}','o':o,'h':hi,'l':lo,'c':c,'v':v})
    return out

codes=json.load(open('scripts/_tmp_codes.json',encoding='utf-8'))
res={}
for nm,code in codes.items():
    b=fetch_day(code)
    bars3=to_3min(b)
    res[nm]={'code':code,'bars':bars3}
    rng=(bars3[0]['t']+'~'+bars3[-1]['t']) if bars3 else 'NONE'
    print(f'{code} {nm:14s} 1min={len(b):3d} 3min={len(bars3):3d}  {rng}', flush=True)
json.dump(res, open('scripts/_min3_20260624.json','w',encoding='utf-8'), ensure_ascii=False)
print('saved scripts/_min3_20260624.json')
