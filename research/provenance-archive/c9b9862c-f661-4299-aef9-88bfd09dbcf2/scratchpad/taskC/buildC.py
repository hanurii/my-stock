import json, subprocess, sys, os, collections
sys.path.insert(0,'scripts')
from canslim_lib.trend_template import compute_gate_margin, GATE_MARGIN_REF, GATE_MARGIN_LABEL

ROOT='C:/Users/hanul/playground/my-stock'
os.chdir(ROOT)

out = subprocess.run(['git','log','--format=%H %ad','--date=short','--','public/data/sepa-trend-candidates.json'],
                     capture_output=True, text=True).stdout.strip().split('\n')
# git log is newest-first; first occurrence of a date = last commit of that date
last_by_date={}
for line in out:
    h,d=line.split()
    if d not in last_by_date:
        last_by_date[d]=h
print('dates:',len(last_by_date), min(last_by_date), max(last_by_date))

ledger=json.load(open('public/data/sepa-buy-rec-ledger.json',encoding='utf-8'))
entries=ledger['entries']
need_dates=sorted({e['date'] for e in entries})
print('ledger dates:',len(need_dates), need_dates[0], need_dates[-1])
missing=[d for d in need_dates if d not in last_by_date]
print('missing commit for ledger dates:',missing)

cache={}
for d in need_dates:
    if d not in last_by_date: continue
    h=last_by_date[d]
    raw=subprocess.run(['git','show',f'{h}:public/data/sepa-trend-candidates.json'],capture_output=True)
    j=json.loads(raw.stdout.decode('utf-8'))
    asof=j.get('asof')
    rec={}
    for c in j.get('candidates',[]):
        close = c.get('last_close') or c.get('current_price')
        m = compute_gate_margin(c, close, c.get('rs'), rs_min=80)
        rec[c['code']] = (c, m)
    cache[d]={'asof':asof,'n':len(rec),'rec':rec}
    print(d, 'asof=',asof, 'cands=',len(rec))

rows=[]
nomatch=0
for e in entries:
    d=e['date']; code=e['code']
    cd=cache.get(d)
    if not cd: nomatch+=1; continue
    got=cd['rec'].get(code)
    if not got: nomatch+=1; continue
    c,m=got
    if not m: nomatch+=1; continue
    r=dict(e)
    r.pop('resolved',None)
    res=e.get('resolved') or {}
    r['outcome']=res.get('outcome')
    r['max_gain_pct']=res.get('max_gain_pct')
    r['cur_ret_pct']=res.get('cur_ret_pct')
    r['days']=res.get('days')
    r['asof']=cd['asof']
    r['gm_score']=m['score']; r['tightest']=m['tightest']
    for k in '12345678':
        r['pct_'+k]=m['per_condition'][k]['pct']
        r['mrg_'+k]=m['per_condition'][k]['margin']
    r['all_pass']=c.get('all_pass'); r['rs']=c.get('rs')
    rows.append(r)
print('joined:',len(rows),'nomatch:',nomatch)
json.dump(rows,open(os.path.join(os.environ['SCRATCH'],'taskC/joinedC.json'),'w',encoding='utf-8'),ensure_ascii=False)
