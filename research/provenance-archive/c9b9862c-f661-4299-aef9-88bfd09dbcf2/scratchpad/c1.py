import json,os,collections
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'joined.json'),encoding='utf-8'))
print('n',len(rows))
print('outcome',collections.Counter(r['outcome'] for r in rows))
print('status',collections.Counter(r['status'] for r in rows))
print('all_pass',collections.Counter(r['all_pass'] for r in rows))
print('gate_near',collections.Counter(r.get('gate_near') for r in rows))
print('uniq codes',len({r['code'] for r in rows}))
print('dup (date,code)',len(rows)-len({(r['date'],r['code']) for r in rows}))
print('tightest',collections.Counter(r['tightest'] for r in rows).most_common())
opn=[r for r in rows if r['outcome']=='open']
print('open days', collections.Counter(r['days'] for r in opn).most_common())
