import subprocess, json, sys
ROOT='C:/Users/hanul/playground/my-stock'
H=json.load(open(ROOT+'/public/data/sepa-holdings.json',encoding='utf-8'))['holdings']
# commits per date
log=subprocess.run(['git','-C',ROOT,'log','--format=%H %ad','--date=short','--','public/data/sepa-vcp-candidates.json'],capture_output=True,text=True).stdout.strip().split('\n')
by_date={}
for l in log:
    sha,dt=l.split(' ',1)
    by_date.setdefault(dt,sha)  # newest per date (log is newest-first)
def get(sha,f):
    o=subprocess.run(['git','-C',ROOT,'show',f'{sha}:public/data/{f}'],capture_output=True,text=True,encoding='utf-8')
    try: return json.loads(o.stdout)
    except Exception: return None
for h in H:
    bd=h['buy_datetime'][:10]
    # find candidate snapshot on buy date, else previous available
    cands=sorted([d for d in by_date if d<=bd],reverse=True)
    hit=None
    for d in cands[:3]:
        sha=by_date[d]
        row={}
        for f,tag in (('sepa-vcp-candidates.json','VCP'),('sepa-3c-candidates.json','3C'),('sepa-power-play-candidates.json','PP')):
            data=get(sha,f)
            if not data: continue
            for c in data.get('candidates',[]):
                if c['code']==h['code']:
                    row[tag]=(c.get('pivot_price'),c.get('status'),c.get('gate_near'))
        print(f"{h['code']} {h['name'][:10]:11s} 매수 {bd} 목록피벗={h['pivot_price']} setup={h['setup']} | 스냅 {d}: {row if row else '후보파일에 없음(관문 탈락)'}")
    print()
