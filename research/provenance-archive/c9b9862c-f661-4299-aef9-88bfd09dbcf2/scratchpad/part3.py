import json
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/'
ROOT='C:/Users/hanul/playground/my-stock/'
bt=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=bt['events']
rows=json.load(open(SP+'daytab.json',encoding='utf-8'))
big=sorted([r for r in rows if r['n']>=4],key=lambda r:r['date'])
resolved=sorted([x for x in ev if x['result'] in ('win','loss')],key=lambda x:(x['resolve_date'],x['entry_date']))
def last_k(entry_date,k):
    seq=[x['result'] for x in resolved if x['resolve_date']<entry_date]
    return seq[-k:] if len(seq)>=k else None
def report(name,skipfn,days):
    sk=[r for r in days if skipfn(r)]
    kp=[r for r in days if not skipfn(r)]
    def agg(g):
        n=sum(r['n'] for r in g); w=sum(r['w'] for r in g)
        return len(g),n,w,(100*w/n if n else 0),sum(1 for r in g if r['w']==0),sum(1 for r in g if r['w']/r['n']>=0.5)
    a=agg(sk); b=agg(kp)
    print(f"{name}")
    print(f"   쉰 날 {a[0]:>3}일 (거래{a[1]:>3}건 승률 {a[3]:>5.1f}%) 그중 전멸 {a[4]}일 / 승률50%+ {a[5]}일")
    print(f"   산 날 {b[0]:>3}일 (거래{b[1]:>3}건 승률 {b[3]:>5.1f}%) 그중 전멸 {b[4]}일 / 승률50%+ {b[5]}일")
print(f"기준: 4건+ 진입일 {len(big)}일 중 전멸 14일, 전체 승률 39.2%\n")
for k in (3,4,5,6):
    def f(r,k=k):
        s=last_k(r['date'],k)
        return s is not None and all(v=='loss' for v in s)
    report(f"[미너비니 규칙] 직전 {k}건 전부 손절이면 쉰다", f, big)
for k,mx in ((5,1),(8,2),(10,3)):
    def f(r,k=k,mx=mx):
        s=last_k(r['date'],k)
        return s is not None and sum(1 for v in s if v=='win')<=mx
    report(f"[완화] 직전 {k}건 중 승 {mx}건 이하면 쉰다", f, big)
# 반대 방향: 최근 성적 좋으면 쉰다?
for k,mn in ((5,4),(8,5)):
    def f(r,k=k,mn=mn):
        s=last_k(r['date'],k)
        return s is not None and sum(1 for v in s if v=='win')>=mn
    report(f"[반대] 직전 {k}건 중 승 {mn}건 이상이면 쉰다", f, big)
# 규칙이 발동한 날 목록
print('\n직전 5건 전부 손절 발동일:')
for r in big:
    s=last_k(r['date'],5)
    if s and all(v=='loss' for v in s):
        print(f"   {r['date']} n={r['n']} 승{r['w']}")
