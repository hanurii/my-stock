import json, glob, os, pickle, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT='C:/Users/hanul/playground/my-stock'
SC='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'

files=sorted(glob.glob(ROOT+'/.cache/pdata/price_*.json'))
files=[f for f in files if os.path.basename(f)[6:14]>='20251001']
dates=[os.path.basename(f)[6:14] for f in files]
dates=[d[:4]+'-'+d[4:6]+'-'+d[6:] for d in dates]
n=len(dates)
print('days',n,dates[0],dates[-1])

# per code arrays
data={}   # code -> dict with lists index-aligned (None where missing)
for i,f in enumerate(files):
    p=json.load(open(f,encoding='utf-8'))
    for code,r in p.items():
        d=data.get(code)
        if d is None:
            d={'flt':[None]*n,'cl':[None]*n,'hi':[None]*n,'lo':[None]*n,'op':[None]*n,'vol':[None]*n,'name':r.get('itmsNm'),'mkt':r.get('mrktCtg')}
            data[code]=d
        d['flt'][i]=r.get('fltRt')
        d['cl'][i]=r.get('clpr')
        d['hi'][i]=r.get('hipr')
        d['lo'][i]=r.get('lopr')
        d['op'][i]=r.get('mkp')
        d['vol'][i]=r.get('trqu')
print('codes',len(data))

# build adjusted close index by chaining fltRt (carry-forward when missing)
for code,d in data.items():
    adj=[None]*n
    cur=None
    for i in range(n):
        c=d['cl'][i]
        if c is None:
            adj[i]=cur   # carry forward (no trade / not listed)
            continue
        f=d['flt'][i]
        if cur is None:
            cur=1.0
        else:
            if f is None: f=0.0
            cur=cur*(1.0+f/100.0)
        adj[i]=cur
    d['adj']=adj
    # intraday adjusted high/low/open via same-day ratio to close
    ah=[None]*n; al=[None]*n; ao=[None]*n
    for i in range(n):
        c=d['cl'][i]; a=adj[i]
        if c is None or a is None or c==0: continue
        if d['hi'][i]: ah[i]=a*d['hi'][i]/c
        if d['lo'][i]: al[i]=a*d['lo'][i]/c
        if d['op'][i]: ao[i]=a*d['op'][i]/c
    d['adjhi']=ah; d['adjlo']=al; d['adjop']=ao

pickle.dump({'dates':dates,'data':data}, open(SC+'/px.pkl','wb'), protocol=4)
print('saved')
