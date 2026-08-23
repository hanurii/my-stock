import io
exec(io.open('rules.py',encoding='utf-8').read())
W=lambda e: 1.0 if is_win(e) else 0.0
out=[]
for K in (1,2,3,5,6):
    for r in RULES:
        obs,n,p=perm_p(r,K,W,nperm=3000,seed=100+K)
        out.append((p,r,K,obs*100,n))
out.sort()
print('rule x K  (50 tests) sorted by permutation p (win-rate, within-day random-selection null)')
for p,r,K,o,n in out[:14]:
    print(f'  {r:22s} K={K} 승률차{o:+6.2f}%p  p={p:.4f}  days={n}')
# BH over all 50
m=len(out); print('\nBH q for top rows (m=%d):'%m)
qs=[]
for i,(p,r,K,o,n) in enumerate(out,1):
    qs.append(min(1.0,p*m/i))
# monotone
for i in range(m-2,-1,-1): qs[i]=min(qs[i],qs[i+1])
for i in range(8):
    p,r,K,o,n=out[i]; print(f'  {r:22s} K={K} p={p:.4f} q={qs[i]:.3f}')
