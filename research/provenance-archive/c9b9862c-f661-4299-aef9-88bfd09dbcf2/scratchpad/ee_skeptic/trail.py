import json, statistics as st, collections, random
exec(open("final.py",encoding="utf-8").read().split("POL={}")[0])
print("트레일 촘촘 격자 (EV / 2026-04 제외 EV / 갭반영 EV)")
for T in [x/2 for x in range(14,45)]:
    g=[gsim(E[r["i"]],trail=T)[1] for r in R]
    g2=[g[i] for i in range(len(R)) if R[i]["entry_date"][:7]!="2026-04"]
    gr=[gsim(E[r["i"]],trail=T,realfill=True)[1] for r in R]
    print(f"   -{T:>4.1f}%   {st.mean(g):+7.3f}   {st.mean(g2):+7.3f}   {st.mean(gr):+7.3f}")
b=[gsim(E[r["i"]])[1] for r in R]
print(f"   현행     {st.mean(b):+7.3f}   {st.mean([b[i] for i in range(len(R)) if R[i]['entry_date'][:7]!='2026-04']):+7.3f}   {st.mean([gsim(E[r['i']],realfill=True)[1] for r in R]):+7.3f}")
# 군집 부트스트랩: 트레일-12% vs 현행
codes=sorted({r["code"] for r in R}); idxby=collections.defaultdict(list)
for i,r in enumerate(R): idxby[r["code"]].append(i)
rnd=random.Random(5)
for T in (10.0,12.0,15.0):
    g=[gsim(E[r["i"]],trail=T)[1] for r in R]
    d=[g[i]-b[i] for i in range(len(R))]
    bs=[]
    for _ in range(3000):
        idx=[]
        for _ in range(len(codes)): idx+=idxby[rnd.choice(codes)]
        bs.append(st.mean([d[i] for i in idx]))
    bs.sort()
    print(f"트레일-{T:.0f}% Δ={st.mean(d):+.3f}  95%CI [{bs[75]:+.3f} ~ {bs[2924]:+.3f}]  P(Δ>0)={sum(1 for x in bs if x>0)/3000:.3f}")
