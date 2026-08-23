import json, random, statistics as st
from collections import defaultdict
root=r'C:\Users\hanul\playground\my-stock'
d=json.load(open(root+r'\public\data\backtest-volatility-pilot.json',encoding='utf-8'))
m=json.load(open(root+r'\public\data\market-regime.json',encoding='utf-8'))['series']
streak={}; s=0
for r in m:
    s=s+1 if r['up'] else 0; streak[r['date']]=s
up={r['date']:r['up'] for r in m}
ev=d['events']; res=[e for e in ev if e['result'] in ('win','loss')]
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
days=sorted([dt for dt,v in byday.items() if len(v)>=4])
wipe=set(dt for dt in days if all(x['result']=='loss' for x in byday[dt]))
# --- (4) 전후반 ---
print('== 전후반 분할 (진입일 2026-03-25) ==')
for lab,sel in [('전반',lambda dt: dt<'2026-03-25'),('후반',lambda dt: dt>='2026-03-25')]:
    dd=[dt for dt in days if sel(dt)]
    w=[dt for dt in dd if dt in wipe]
    A=[e for dt in w for e in byday[dt]]
    Bl=[e for dt in dd if dt not in wipe for e in byday[dt] if e['result']=='loss']
    Ball=[e for dt in dd if dt not in wipe for e in byday[dt]]
    if not A or not Bl: 
        print(lab,'표본부족'); continue
    print(f'{lab}: 날 {len(dd)} 전멸 {len(w)}({100*len(w)/len(dd):.0f}%) | maxgain중앙 전멸 {st.median([e["max_gain_pct"] for e in A]):.2f} vs 그밖패배 {st.median([e["max_gain_pct"] for e in Bl]):.2f} vs 그밖전체 {st.median([e["max_gain_pct"] for e in Ball]):.2f}'
          f' | 3%미만 {100*sum(1 for e in A if e["max_gain_pct"]<3)/len(A):.0f}% vs {100*sum(1 for e in Bl if e["max_gain_pct"]<3)/len(Bl):.0f}%'
          f' | 3일이내 {100*sum(1 for e in A if e["days_held"]<=3)/len(A):.0f}% vs {100*sum(1 for e in Bl if e["days_held"]<=3)/len(Bl):.0f}%')
print()
# --- (5) 특성 차이 날단위 순열 ---
print('== 종목 특성: 날 라벨 순열 3000회 (종목반복·같은날묶음 반영) ==')
allday=[(dt,byday[dt]) for dt in days]
def charstat(wset):
    A=[e for dt,g in allday if dt in wset for e in g]; B=[e for dt,g in allday if dt not in wset for e in g]
    return {f: st.median([e[f] for e in A])-st.median([e[f] for e in B]) for f in ('rs','atr_pct','turnover_eok')}
obs=charstat(wipe)
random.seed(11); N=3000; cnt={k:0 for k in obs}
for _ in range(N):
    ws=set(random.sample(days,14))
    r=charstat(ws)
    for k in obs:
        if abs(r[k])>=abs(obs[k]): cnt[k]+=1
for k in obs: print(f'{k:14s} 관측차(전멸-그밖) {obs[k]:8.2f}  양측 p={cnt[k]/N:.3f}')
print()
# --- (6) streak 규칙의 돈값 ---
print('== streak 규칙 (사후 선택) 승률: 전반/후반 ==')
for thr in (9,12,15):
    row=[]
    for lab,sel in [('전반',lambda dt: dt<'2026-03-25'),('후반',lambda dt: dt>='2026-03-25'),('전체',lambda dt: True)]:
        keep=[e for dt in days if sel(dt) and streak.get(dt,0)<thr for e in byday[dt]]
        skip=[e for dt in days if sel(dt) and streak.get(dt,0)>=thr for e in byday[dt]]
        def wr(x): return (100*sum(1 for e in x if e['result']=='win')/len(x)) if x else float('nan')
        row.append(f'{lab} 지킴 {len(keep):3d}건 {wr(keep):5.1f}% / 버림 {len(skip):3d}건 {wr(skip):5.1f}%')
    print(f'streak>={thr}: ' + ' | '.join(row))
