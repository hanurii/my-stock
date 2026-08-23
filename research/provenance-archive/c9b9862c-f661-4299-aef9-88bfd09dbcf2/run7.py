import io
exec(io.open('rules.py',encoding='utf-8').read())
rnd=random.Random(9)
def wipe(days,K,rule=None,nsim=4000,winf=is_win):
    if rule:
        return sum(1 for d in days if not any(winf(e) for e in rank(BY[d],rule)[:K]))/len(days)*100
    tot=0
    for _ in range(nsim):
        z=0
        for d in days:
            g=BY[d][:]; rnd.shuffle(g)
            if not any(winf(e) for e in g[:K]): z+=1
        tot+=z/len(days)
    return tot/nsim*100
# entry_date 기준 국면
upE=[d for d in DAYS if regime_up(d)]; dnE=[d for d in DAYS if not regime_up(d)]
print('진입일 기준 국면: 상승%d일 %.1f%% / 조정%d일 %.1f%%'%(len(upE),wipe(upE,6),len(dnE),wipe(dnE,6)))
# ambiguous를 승으로
winb=lambda e: e['result'] in ('win','ambiguous')
print('ambiguous를 승으로 치면 전체146일 전멸 %.1f%%'%wipe(DAYS,6,winf=winb))

# 선택이 실제로 구속되는 날(후보 7건 이상)만
d7=[d for d in DAYS if len(BY[d])>=7]
print('\n[선택이 구속되는 날: 후보 7건 이상 %d일] top6 전멸률'%len(d7))
rows=sorted(((wipe(d7,6,r),r) for r in RULES))
for z,r in rows: print(f'   {r:22s} {z:5.1f}%')
print(f'   {"무작위":22s} {wipe(d7,6):5.1f}%')
print(f'   {"그날 전부(대조)":22s} {sum(1 for d in d7 if not any(is_win(e) for e in BY[d]))/len(d7)*100:5.1f}%')
# 그리고 승수 기대치
for r in ['거래대금큰순','거래대금작은순','갭업큰순(먼저돌파)']:
    m=sum(sum(1 for e in rank(BY[d],r)[:6] if is_win(e)) for d in d7)/len(d7)
    print(f'   평균 승리개수 {r}: {m:.2f}/6')
tot=0
for _ in range(4000):
    s=0
    for d in d7:
        g=BY[d][:]; rnd.shuffle(g); s+=sum(1 for e in g[:6] if is_win(e))
    tot+=s/len(d7)
print(f'   평균 승리개수 무작위: {tot/4000:.2f}/6')
