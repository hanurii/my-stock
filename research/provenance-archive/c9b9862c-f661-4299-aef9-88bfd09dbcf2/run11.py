import io
exec(io.open('run8.py',encoding='utf-8').read().split("print('6슬롯")[0])
SPLIT='2026-03-25'
def sim2(rule,slots,days,rnd=None):
    eq=1.0; busy=[]; held=set(); trades=[]
    alld=sorted(set(days)|{e['resolve_date'] for d in days for e in BY[d]})
    for d in alld:
        b2=[]
        for rd,c,a,e in busy:
            if rd<d: eq+=a*ret(e)/100; held.discard(c); trades.append(e)
            else: b2.append((rd,c,a,e))
        busy=b2
        if d not in BY or d not in set(days): continue
        g=BY[d]; free=slots-len(busy)
        if free<=0: continue
        order=rank(g,rule) if rule else (lambda x:(rnd.shuffle(x),x)[1])(g[:])
        for e in order:
            if free<=0: break
            if e['code'] in held: continue
            busy.append((e['resolve_date'],e['code'],eq/slots,e)); held.add(e['code']); free-=1
    for rd,c,a,e in busy: eq+=a*ret(e)/100; trades.append(e)
    w=sum(1 for e in trades if is_win(e))
    return eq,len(trades),(w/len(trades)*100 if trades else 0)
h1=[d for d in DAYS if d<SPLIT]; h2=[d for d in DAYS if d>=SPLIT]
for nm,dd in (('전반',h1),('후반',h2)):
    rnd=random.Random(41); b=sorted(sim2(None,6,dd,rnd)[0] for _ in range(400))
    e,n,w=sim2('거래대금큰순',6,dd)
    e2,_,_=sim2('갭업큰순(먼저돌파)',6,dd)
    pct=sum(1 for x in b if x<e)/len(b)*100
    print(f'{nm}({len(dd)}일) 무작위중앙값 {b[200]:.3f} | 거래대금큰순 {e:.3f} (상위 {100-pct:.0f}%ile, 거래{n} 승률{w:.1f}%) | 갭업큰순 {e2:.3f}')
