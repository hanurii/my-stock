# -*- coding: utf-8 -*-
"""범용 1일 데이트레이딩 검증: python _run_day.py <YYYYMMDD> <codes.json>
신호일=전 영업일, 매매일=DATE. 우리 합의 규칙(4분기 + 시나리오 A/B)."""
import os,sys,json,time,glob,statistics,io,urllib.request as ur,urllib.parse as up
sys.path.insert(0,'scripts')
for line in open('.env',encoding='utf-8'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k,v)
from canslim_lib import kis_api
DATE=sys.argv[1]; CODES=sys.argv[2]
DATE_ISO=f'{DATE[:4]}-{DATE[4:6]}-{DATE[6:]}'
tok=kis_api.get_access_token()
codes=json.load(open(CODES,encoding='utf-8'))
COST=0.5; W=20
MIN_FILE=f'scripts/_min3_{DATE}.json'

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
            bars[t]={'o':float(r['stck_oprc']),'h':float(r['stck_hgpr']),'l':float(r['stck_lwpr']),'c':float(r['stck_prpr']),'v':float(r.get('cntg_vol') or 0)}
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

if os.path.exists(MIN_FILE):
    data=json.load(open(MIN_FILE,encoding='utf-8'))
else:
    data={}
    for nm,code in codes.items():
        b=to3(fetch(str(code))); data[nm]={'code':str(code),'bars':b}
        print(f'  {code} {nm}: {len(b)} bars',flush=True)
    json.dump(data,open(MIN_FILE,'w',encoding='utf-8'),ensure_ascii=False)

def series_before(code):
    p=f'.cache/ohlcv/series/{code}.json'
    if not os.path.exists(p): return None,None
    s=json.load(open(p,encoding='utf-8'))
    ds=s.get('dates') or []
    idx=ds.index(DATE_ISO) if DATE_ISO in ds else len(ds)
    prevc=s['closes'][idx-1] if idx>=1 else None
    vols=s['volumes'][max(0,idx-50):idx]
    avg50=statistics.mean(vols) if vols else None
    return prevc,avg50

def classify(b0):
    body=(b0['c']/b0['o']-1)*100
    if body>=6: return '장대양봉',body
    if body>0: return '양봉',body
    if body>-6: return '음봉',body
    return '장대음봉',body
def exit_sim(bars,ei,entry,target,stop):
    tp=entry*(1+target/100); sl=entry*(1+stop/100); mfe=mae=0.0
    for k in range(ei+1,len(bars)):
        x=bars[k]; mfe=max(mfe,(x['h']/entry-1)*100); mae=min(mae,(x['l']/entry-1)*100)
        hs=x['l']<=sl; ht=x['h']>=tp
        if hs and ht: return stop,'손절(동시)',mfe,mae
        if hs: return stop,'손절',mfe,mae
        if ht: return target,'익절',mfe,mae
    return (bars[-1]['c']/entry-1)*100,'종가',mfe,mae

rows=[]
for nm,d in data.items():
    bars=d['bars']
    if not bars: continue
    b0=bars[0]; form,body=classify(b0)
    prevc,avg50=series_before(str(d['code']))
    gap=(b0['o']/prevc-1)*100 if prevc else None
    vr=(b0['v']/avg50) if avg50 else None
    ei=None; reason=None
    if form=='장대음봉': reason='장대음봉(매수금지)'
    elif form=='양봉': ei=0
    elif form=='장대양봉':
        r0=b0['h']-b0['l']
        for j in range(1,min(W,len(bars))):
            x=bars[j]
            if x['v']<=b0['v']*0.5 and (x['h']-x['l'])<r0*0.7: ei=j; break
        if ei is None: reason='장대양봉 눌림 미발생'
    else:
        body0=b0['o']-b0['c']
        for j in range(1,min(W,len(bars))):
            x=bars[j]
            if x['c']>x['o'] and (x['c']-x['o'])>body0: ei=j; break
        if ei is None: reason='음봉 상쇄양봉 미발생'
    rows.append(dict(nm=nm,code=d['code'],gap=gap,form=form,body=body,vr=vr,ei=ei,
                     entry=bars[ei]['c'] if ei is not None else None,reason=reason,bars=bars))

out=io.StringIO()
def p(*a): print(*a,file=out)
forms={}
for r in rows: forms[r['form']]=forms.get(r['form'],0)+1
p("="*86); p(f"  데이트레이딩 검증 — 매매일 {DATE_ISO}  ({len(rows)}종목)"); p("="*86)
p("  첫3분봉: "+" / ".join(f"{k} {v}" for k,v in sorted(forms.items())))
gaps=[r['gap'] for r in rows if r['gap'] is not None]
if gaps: p(f"  시가갭: 평균 {statistics.mean(gaps):+.1f}%  (최대 {max(gaps):+.1f}, 최소 {min(gaps):+.1f})")
def summarize(label,target,stop):
    p(f"\n  ── 시나리오 {label}: 목표 +{target}% / 손절 {stop}% ──")
    by={'양봉':[],'장대양봉':[],'음봉':[]}
    for r in rows:
        if r['ei'] is None: continue
        ret,why,mfe,mae=exit_sim(r['bars'],r['ei'],r['entry'],target,stop)
        by[r['form']].append((r['nm'],ret-COST,why,mfe,mae)); r[f'res_{label}']=(ret-COST,why,mfe,mae)
    allr=[]
    for k in ['양봉','장대양봉','음봉']:
        L=by[k]
        if not L: p(f"    [{k}] 진입 0"); continue
        rets=[x[1] for x in L]; wins=sum(1 for x in rets if x>0)
        tp=sum(1 for x in L if x[2]=='익절'); sl=sum(1 for x in L if '손절' in x[2]); cc=sum(1 for x in L if x[2]=='종가')
        p(f"    [{k}] {len(L)}건  평균 {statistics.mean(rets):+.2f}%/건  승률 {100*wins/len(L):.0f}%  (익절{tp}/손절{sl}/종가{cc})")
        allr+=rets
    if allr:
        w=sum(1 for x in allr if x>0)
        p(f"    ▶ 전체 {len(allr)}건  평균 {statistics.mean(allr):+.2f}%/건  승률 {100*w/len(allr):.0f}%  합계 {sum(allr):+.1f}%p")
summarize('A',6,-5); summarize('B',10,-6)
p("\n  ── 진입가능 종목 그날 최대 상승폭(09:03 종가 기준) ──")
mfes=[]
for r in rows:
    if r['form']=='장대음봉': continue
    b0c=r['bars'][0]['c']; mx=max((x['h']/b0c-1)*100 for x in r['bars'][1:]) if len(r['bars'])>1 else 0; mfes.append(mx)
for thr in [6,10,15,20]: p(f"    +{thr}%↑ 도달: {sum(1 for m in mfes if m>=thr)}/{len(mfes)}")
blind=[]
for r in rows:
    if r['form']=='장대음봉': continue
    b0c=r['bars'][0]['c']; blind.append((r['bars'][-1]['c']/b0c-1)*100-COST)
p(f"\n  ── 블라인드(전 종목 09:03매수→종가): {len(blind)}종목 평균 {statistics.mean(blind):+.2f}%/건 승률 {100*sum(1 for x in blind if x>0)/len(blind):.0f}% ──")
p("\n"+"-"*86); p("  [종목별]  형태|갭|거래량비|진입|A|B")
for r in sorted(rows,key=lambda x:(x['form'],-(x['body']))):
    gp=f"{r['gap']:+5.1f}%" if r['gap'] is not None else "  n/a"; vr=f"{r['vr']*100:4.0f}%" if r['vr'] is not None else " n/a"
    if r['ei'] is None: p(f"   {r['nm']:<12}{r['form']:<5}갭{gp} 량{vr} →스킵:{r['reason']}")
    else:
        a=r.get('res_A'); b=r.get('res_B')
        p(f"   {r['nm']:<12}{r['form']:<5}갭{gp} 량{vr} 진입{r['bars'][r['ei']]['t']}@{r['entry']:.0f} A{a[0]:+6.2f}[{a[1]}] B{b[0]:+6.2f}[{b[1]}] (최대+{a[2]:.1f})")
txt=out.getvalue(); sys.stdout.buffer.write(txt.encode('utf-8')); open(f'scripts/_result_{DATE}.txt','w',encoding='utf-8').write(txt)
