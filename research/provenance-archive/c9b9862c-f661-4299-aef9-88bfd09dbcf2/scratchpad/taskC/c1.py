import json,os,collections
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC.json'),encoding='utf-8'))
print('n',len(rows))
print('outcome',collections.Counter(r['outcome'] for r in rows))
print('status',collections.Counter(r['status'] for r in rows))
print('all_pass',collections.Counter(r['all_pass'] for r in rows))
print('gate_near',collections.Counter(r.get('gate_near') for r in rows))
print('uniq codes',len({r['code'] for r in rows}))
print('dup (date,code)',len(rows)-len({(r['date'],r['code']) for r in rows}))
print('tightest',sorted(collections.Counter(r['tightest'] for r in rows).items()))
opn=[r for r in rows if r['outcome']=='open']
print('open days', sorted(collections.Counter(r['days'] for r in opn).items()))
res=[r for r in rows if r['outcome'] in ('stop','target')]
print('resolved n',len(res))
print('score dist', sorted(round(r['gm_score']) for r in rows)[::40])
