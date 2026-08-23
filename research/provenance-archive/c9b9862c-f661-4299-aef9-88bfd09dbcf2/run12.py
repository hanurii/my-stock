import io
exec(io.open('run11.py',encoding='utf-8').read().split('h1=[d')[0])
SPLIT='2026-03-25'
h1=[d for d in DAYS if d<SPLIT]; h2=[d for d in DAYS if d>=SPLIT]
for nm,dd in (('전반',h1),('후반',h2),('전체',DAYS)):
    for slots in (4,6,8):
        rnd=random.Random(55+slots); sims=[sim2(None,slots,dd,rnd) for _ in range(300)]
        b=sorted(x[0] for x in sims); mw=sum(x[2] for x in sims)/300; mn=sum(x[1] for x in sims)/300
        e,n,w=sim2('거래대금큰순',slots,dd)
        pct=sum(1 for x in b if x<e)/len(b)*100
        print(f'{nm} 슬롯{slots}: 무작위중앙 {b[200]:.3f}(승률{mw:.1f}%,거래{mn:.0f}) | 거래대금큰순 {e:.3f} 승률{w:.1f}% 거래{n}  상위{100-pct:.0f}%ile')
    print()
