import io
exec(io.open('rules.py',encoding='utf-8').read())
rnd=random.Random(5)
def wipe(days,K,rule=None,nsim=3000):
    if rule:
        z=sum(1 for d in days if not any(is_win(e) for e in rank(BY[d],rule)[:K]))
        return z/len(days)*100
    tot=0
    for _ in range(nsim):
        z=0
        for d in days:
            g=BY[d][:]; rnd.shuffle(g)
            if not any(is_win(e) for e in g[:K]): z+=1
        tot+=z/len(days)
    return tot/nsim*100
for minn,label in ((1,'후보1건이상 전체146일'),(2,'2건이상'),(3,'3건이상'),(4,'4건이상'),(6,'6건이상')):
    dd=[d for d in DAYS if len(BY[d])>=minn]
    up=[d for d in dd if regime_up(BY[d][0]['scan_date'])]; dn=[d for d in dd if not regime_up(BY[d][0]['scan_date'])]
    print(f'{label} ({len(dd)}일): 무작위6칸 전멸 {wipe(dd,6):.1f}%  | 상승({len(up)}) {wipe(up,6):.1f}%  조정({len(dn)}) {wipe(dn,6):.1f}%'
          + f'  | 거래대금큰순 {wipe(dd,6,"거래대금큰순"):.1f}%  갭업큰순 {wipe(dd,6,"갭업큰순(먼저돌파)"):.1f}%')
