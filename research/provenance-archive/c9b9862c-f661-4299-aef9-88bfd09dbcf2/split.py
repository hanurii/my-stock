import json, math, statistics
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/'
rows=json.load(open(SP+'daytab.json',encoding='utf-8'))
big=sorted([r for r in rows if r['n']>=4],key=lambda r:r['date'])
def rank(v):
    idx=sorted(range(len(v)),key=lambda i:v[i]); r=[0.0]*len(v); i=0
    while i<len(idx):
        j=i
        while j+1<len(idx) and v[idx[j+1]]==v[idx[i]]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): r[idx[k]]=avg
        i=j+1
    return r
def spear(x,y):
    rx,ry=rank(x),rank(y); n=len(x); mx=sum(rx)/n; my=sum(ry)/n
    num=sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    dx=math.sqrt(sum((a-mx)**2 for a in rx)); dy=math.sqrt(sum((b-my)**2 for b in ry))
    return num/(dx*dy) if dx and dy else 0.0
TOP=['b_a50','b_a200','b_a20_chg5','r_up_streak','b_adv10','r_ret10']
SPLIT='2026-03-25'
print('=== 전후반 안정성 (진입일 기준 분할 %s) ==='%SPLIT)
print(f"{'요인':<14}{'전반ρ':>8}{'후반ρ':>8}{'전반일':>7}{'후반일':>7}{'전반전멸':>9}{'후반전멸':>9}")
for f in TOP:
    for lab,g in (('',[r for r in big if r['date']<=SPLIT]),('',[r for r in big if r['date']>SPLIT])):
        pass
    a=[r for r in big if r['date']<=SPLIT]; b=[r for r in big if r['date']>SPLIT]
    ra=spear([r[f] for r in a],[r['w']/r['n'] for r in a])
    rb=spear([r[f] for r in b],[r['w']/r['n'] for r in b])
    print(f"{f:<14}{ra:>8.3f}{rb:>8.3f}{len(a):>7}{len(b):>7}{sum(1 for r in a if r['w']==0):>9}{sum(1 for r in b if r['w']==0):>9}")

print('\n=== 규칙: 그날 아침 50일선 위 종목비율(b_a50) 상위 1/3 이면 쉰다 ===')
vals=sorted(r['b_a50'] for r in big)
q23=vals[int(len(vals)*2/3)]
print(f'상위 1/3 컷 = {q23:.1f}%')
skip=[r for r in big if r['b_a50']>=q23]; keep=[r for r in big if r['b_a50']<q23]
for lab,g in (('쉰 날',skip),('산 날',keep)):
    n=sum(r['n'] for r in g); w=sum(r['w'] for r in g); z=sum(1 for r in g if r['w']==0)
    good=sum(1 for r in g if r['w']/r['n']>=0.5)
    print(f'{lab}: {len(g)}일 거래{n}건 승률 {100*w/n:.1f}% 전멸일 {z} 승률50%+인날 {good}')
# tertiles of every top feature: wipeout share
print('\n=== 상위/중간/하위 1/3 별 전멸일 비율 ===')
for f in TOP:
    v=sorted(r[f] for r in big); c1=v[len(v)//3]; c2=v[2*len(v)//3]
    for lab,sel in (('하위1/3',lambda r:r[f]<c1),('중간',lambda r:c1<=r[f]<c2),('상위1/3',lambda r:r[f]>=c2)):
        g=[r for r in big if sel(r)]
        if not g: continue
        n=sum(r['n'] for r in g); w=sum(r['w'] for r in g)
        print(f'  {f:<12}{lab:<8}{len(g):>3}일 전멸 {sum(1 for r in g if r["w"]==0):>2}일 승률 {100*w/n:>5.1f}%')
