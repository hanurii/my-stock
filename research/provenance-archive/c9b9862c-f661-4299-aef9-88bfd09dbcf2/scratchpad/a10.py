import json, collections, datetime as DT
import numpy as np
P='C:/Users/hanul/playground/my-stock/'
d=json.load(open(P+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for x in ev: byday[x['entry_date']].append(1 if x['result']=='win' else 0)
alld=sorted(byday)
ordn={k:DT.date.fromisoformat(k).toordinal() for k in alld}
rng=np.random.default_rng(99)
# anchors: days with >=6 trades AND 5 further entry days available after
anchors=[]
for i,k in enumerate(alld):
    if len(byday[k])>=6 and i+5<len(alld): anchors.append(i)
print("matched anchors:",len(anchors))
S=60000
def run(mode,sep=1):
    wipe=0;wins=0;n=0;spans=[]
    for _ in range(S):
        i=anchors[rng.integers(len(anchors))]
        if mode=='same':
            k=alld[i]; idx=rng.choice(len(byday[k]),6,replace=False); o=[byday[k][j] for j in idx]
        else:
            picks=[i]; j=i+1
            while len(picks)<6 and j<len(alld):
                if ordn[alld[j]]-ordn[alld[picks[-1]]]>=sep: picks.append(j)
                j+=1
            if len(picks)<6: continue
            spans.append(ordn[alld[picks[-1]]]-ordn[alld[picks[0]]])
            o=[byday[alld[q]][rng.integers(len(byday[alld[q]]))] for q in picks]
        n+=1; s=sum(o); wins+=s
        if s==0: wipe+=1
    wr=wins/(6*n); ind=(1-wr)**6
    sp=f" mean span={np.mean(spans):.0f}d" if spans else ""
    print(f"{mode} sep={sep}: n={n} winrate={100*wr:.1f}% wipeout={100*wipe/n:.1f}% (independent would be {100*ind:.1f}% -> {(wipe/n)/ind:.2f}x){sp}")
run('same')
run('spread',1)
run('spread',3)
run('spread',7)
run('spread',14)
