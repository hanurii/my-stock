import io
exec(io.open('rules.py',encoding='utf-8').read())
ALLD=sorted({e['entry_date'] for e in EV}|{e['resolve_date'] for e in EV if e.get('resolve_date')})

def sim(rule=None, slots=6, regime_filter=False, rnd=None, ret_mode='fix'):
    eq=1.0; busy=[]  # list of (resolve_date, code, amount, e)
    held=set(); trades=[]
    for d in ALLD:
        busy2=[]
        for rd,code,amt,e in busy:
            if rd<d:
                eq+= amt*ret(e)/100.0
                held.discard(code); trades.append(e)
            else: busy2.append((rd,code,amt,e))
        busy=busy2
        g=BY.get(d)
        if not g: continue
        if regime_filter and not regime_up(g[0]['scan_date']): continue
        free=slots-len(busy)
        if free<=0: continue
        if rule: order=rank(g,rule)
        else:
            order=g[:]; rnd.shuffle(order)
        for e in order:
            if free<=0: break
            if e['code'] in held: continue
            busy.append((e['resolve_date'],e['code'],eq/slots,e)); held.add(e['code']); free-=1
    for rd,code,amt,e in busy:
        eq+=amt*ret(e)/100.0; trades.append(e)
    w=sum(1 for e in trades if is_win(e))
    return eq, len(trades), w/len(trades)*100

print('6슬롯 포트폴리오 시뮬 (자본 1.0 시작, 슬롯당 1/6, 결착 시 정산)')
base=[]
rnd=random.Random(21)
for _ in range(400):
    e,n,w=sim(None,6,False,rnd); base.append((e,n,w))
be=sorted(x[0] for x in base)
print(f'  무작위 순서   : 최종자본 중앙값 {be[200]:.3f}  [5%~95%: {be[20]:.3f}~{be[379]:.3f}]  거래수~{sum(x[1] for x in base)/400:.0f}  승률{sum(x[2] for x in base)/400:.1f}%')
rows=[]
for r in RULES:
    e,n,w=sim(r,6,False); rows.append((e,r,n,w))
rows.sort(reverse=True)
for e,r,n,w in rows:
    pct=sum(1 for x in be if x< e)/len(be)*100
    print(f'  {r:22s}: {e:.3f} (무작위분포 상위 {100-pct:.0f}%ile)  거래{n} 승률{w:.1f}%')
print()
rnd2=random.Random(22); base2=[]
for _ in range(400):
    e,n,w=sim(None,6,True,rnd2); base2.append(e)
b2=sorted(base2)
print(f'  [조정국면일 진입 안 함] 무작위 순서: 중앙값 {b2[200]:.3f} [5~95%: {b2[20]:.3f}~{b2[379]:.3f}]')
for r in ('거래대금큰순','거래대금작은순','갭업큰순(먼저돌파)','ATR낮은순(저변동)','RS높은순'):
    e,n,w=sim(r,6,True); print(f'  [조정회피] {r:20s}: {e:.3f} 거래{n} 승률{w:.1f}%')
