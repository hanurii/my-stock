import io
exec(io.open('rules.py',encoding='utf-8').read())

# ---- 전멸률: 6건 이상 나온 날 top6 ----
print('[A] 6건 이상 나온 날(%d일) top6 전멸(0승) 비율'%sum(1 for d in DAYS if len(BY[d])>=6))
d6=[d for d in DAYS if len(BY[d])>=6]
res={}
for r in RULES:
    z=sum(1 for d in d6 if not any(is_win(e) for e in rank(BY[d],r)[:6]))
    a=sum(1 for d in d6 if all(is_win(e) for e in rank(BY[d],r)[:6]))
    res[r]=(z/len(d6)*100,a)
for r,(z,a) in sorted(res.items(),key=lambda x:x[1][0]):
    print(f'   {r:22s} 전멸 {z:5.1f}%  전승{a}')
rnd=random.Random(3); tot=0
for _ in range(5000):
    z=0
    for d in d6:
        g=BY[d][:]; rnd.shuffle(g)
        if not any(is_win(e) for e in g[:6]): z+=1
    tot+=z/len(d6)
print(f'   {"무작위 6개":22s} 전멸 {tot/5000*100:5.1f}%')
# 국면별
for nm,f in (('상승국면일',True),('조정국면일',False)):
    dd=[d for d in d6 if regime_up(BY[d][0]["scan_date"])==f]
    if not dd: print(nm,'없음'); continue
    tot=0
    for _ in range(3000):
        z=0
        for d in dd:
            g=BY[d][:]; rnd.shuffle(g)
            if not any(is_win(e) for e in g[:6]): z+=1
        tot+=z/len(dd)
    print(f'   {nm}({len(dd)}일) 무작위6개 전멸 {tot/3000*100:5.1f}%')

# ---- 풀에서 6개 무작위 추출 전멸(부트스트랩) ----
print('\n[B] 국면별 전체 풀에서 무작위 6건 뽑았을 때 전멸 확률(부트스트랩)')
for nm,f in (('전체',None),('상승국면',True),('조정국면',False)):
    pool=[e for e in EV if (f is None or regime_up(e['scan_date'])==f)]
    z=0
    for _ in range(20000):
        z+= 0 if any(is_win(pool[rnd.randrange(len(pool))]) for _ in range(6)) else 1
    print(f'   {nm} (n={len(pool)}) 6개 전멸 {z/20000*100:5.1f}%')
