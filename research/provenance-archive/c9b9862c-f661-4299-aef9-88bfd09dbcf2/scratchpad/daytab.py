import json, sys
from collections import defaultdict
ROOT='C:/Users/hanul/playground/my-stock/'
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/'
bt=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=bt['events']
per={r['scan_date']:r for r in bt['per_date']}
reg=json.load(open(ROOT+'public/data/market-regime.json',encoding='utf-8'))['series']
brd={r['date']:r for r in json.load(open(SP+'breadth.json',encoding='utf-8'))}
regd=[r['date'] for r in reg]
regi={r['date']:i for i,r in enumerate(reg)}

byday=defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)

# check scan_date == prev trading day of entry_date
bad=0
for x in ev:
    i=regi.get(x['scan_date'])
    if i is None or i+1>=len(regd) or regd[i+1]!=x['entry_date']: bad+=1
print('scan/entry mismatch:',bad,'of',len(ev))

def regfeat(sd):
    i=regi.get(sd)
    if i is None: return None
    f={}
    r=reg[i]
    f['idx']=r['index']; f['ma20']=r['ma20']; f['up']=1 if r['up'] else 0
    f['dist_ma20']=100*(r['index']/r['ma20']-1)
    for k in (1,3,5,10,20):
        if i-k>=0: f[f'ret{k}']=100*(r['index']/reg[i-k]['index']-1)
        else: f[f'ret{k}']=None
    # streak above ma20
    s=0
    j=i
    while j>=0 and reg[j]['up']: s+=1; j-=1
    f['up_streak']=s
    s=0; j=i
    while j>=0 and not reg[j]['up']: s+=1; j-=1
    f['down_streak']=s
    # ma20 slope 5d
    f['ma20_slope5']=100*(r['ma20']/reg[i-5]['ma20']-1) if i-5>=0 else None
    # distribution-ish: down days >=0.5% in last 25
    dd=0
    for j in range(max(1,i-24),i+1):
        if reg[j]['index']/reg[j-1]['index']-1 <= -0.005: dd+=1
    f['dist_days25']=dd
    # index vs 25d high
    if i>=24:
        hi=max(reg[j]['index'] for j in range(i-24,i+1))
        f['off_hi25']=100*(r['index']/hi-1)
    else: f['off_hi25']=None
    return f

def brdfeat(sd):
    b=brd.get(sd)
    if not b: return {}
    out={('b_'+k):v for k,v in b.items() if k not in ('date','n','adv','dec','nh_den')}
    # 5-day avg adv_pct
    idx=sorted(brd)
    p=idx.index(sd)
    def avg(key,k):
        vs=[brd[idx[j]][key] for j in range(max(0,p-k+1),p+1) if brd[idx[j]][key] is not None]
        return round(sum(vs)/len(vs),2) if vs else None
    out['b_adv5']=avg('adv_pct',5)
    out['b_adv10']=avg('adv_pct',10)
    out['b_a20_chg5']=None
    if p>=5 and brd[idx[p-5]]['a20'] is not None and b['a20'] is not None:
        out['b_a20_chg5']=round(b['a20']-brd[idx[p-5]]['a20'],2)
    if p>=5 and brd[idx[p-5]]['a50'] is not None and b['a50'] is not None:
        out['b_a50_chg5']=round(b['a50']-brd[idx[p-5]]['a50'],2)
    else: out['b_a50_chg5']=None
    return out

# my own recent record: resolved trades with resolve_date < entry_date
resolved=sorted([x for x in ev if x['result'] in ('win','loss') and x.get('resolve_date')],
                key=lambda x:(x['resolve_date'],x['entry_date']))
def recent_record(entry_date,k):
    seq=[x for x in resolved if x['resolve_date']<entry_date]
    seq=seq[-k:]
    if len(seq)<k: return None
    return sum(1 for x in seq if x['result']=='win')

rows=[]
for dt,evs in sorted(byday.items()):
    r=[x for x in evs if x['result'] in ('win','loss')]
    if not r: continue
    i=regi[dt]
    sd=regd[i-1]
    f={'date':dt,'scan_date':sd,'n':len(r),'w':sum(1 for x in r if x['result']=='win')}
    f['wr']=f['w']/f['n']
    rf=regfeat(sd)
    f.update({('r_'+k):v for k,v in rf.items()})
    f.update(brdfeat(sd))
    pr=per.get(sd,{})
    f['n_cand']=pr.get('n_candidates'); f['n_eval']=pr.get('n_eval')
    for k in (3,4,5,8,10):
        f[f'last{k}_wins']=recent_record(dt,k)
    f['codes']=[(x['code'],x['name'],x['pattern'],x['result'],x['rs'],x['turnover_eok'],x['max_gain_pct'],x['gain_at_resolve_pct']) for x in evs]
    rows.append(f)
json.dump(rows,open(SP+'daytab.json','w',encoding='utf-8'),ensure_ascii=False)
print('day rows',len(rows))
print({k:v for k,v in rows[0].items() if k!='codes'})
