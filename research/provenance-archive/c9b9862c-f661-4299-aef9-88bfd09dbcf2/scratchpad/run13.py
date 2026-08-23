import io
exec(io.open('rules.py',encoding='utf-8').read())
W=lambda e: 1.0 if is_win(e) else 0.0
R=lambda e: ret(e)
SPLIT='2026-03-25'
h1=[d for d in DAYS if d<SPLIT]; h2=[d for d in DAYS if d>=SPLIT]
for nm,dd in (('전반',h1),('후반',h2)):
    print(nm)
    for K in (1,2,3,5,6):
        s,n,_=stat_selminusday('거래대금큰순',K,W,dd)
        s2,_,_=stat_selminusday('거래대금큰순',K,R,dd)
        g,_,_=stat_selminusday('갭업큰순(먼저돌파)',K,W,dd)
        print(f'  K={K} 유효일{n:3d}  거래대금큰순 승률차{s*100:+6.2f}%p 수익차{s2:+6.2f}%p | 갭업큰순 승률차{g*100:+6.2f}%p')
