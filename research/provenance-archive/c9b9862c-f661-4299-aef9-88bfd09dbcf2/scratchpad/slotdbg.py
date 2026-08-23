import json, statistics as st, random, collections
exec(open("slot.py",encoding="utf-8").read().split("print(\"=== 슬롯")[0])
sums=[];eqs=[];cnts=[];wins=[]
for sd in range(300):
    t,g,h=slotsim(policy_base,5,seed=sd)
    eq=1.0
    for x in g: eq*=(1+x/100/5)
    sums.append(sum(g)); eqs.append((eq-1)*100); cnts.append(len(t)); wins.append(sum(1 for x in g if x>0)/len(g))
print("체결수 중앙 %d, 합계수익%%p 중앙 %.1f (평균 %.1f), 건당 %.3f, 승률 %.3f"%(st.median(cnts),st.median(sums),st.mean(sums),st.mean(sums)/st.mean(cnts),st.mean(wins)))
print("복리 중앙 %.2f%%"%st.median(eqs))
# 전체 614건 승률/건당
print("전체 614: 건당 %.3f 승률 %.3f"%(st.mean([r['gain'] for r in R]),sum(1 for r in R if r['gain']>0)/len(R)))
# 슬롯 선택된 거래의 월 분포 vs 전체
c=collections.Counter(); 
for sd in range(50):
    t,g,h=slotsim(policy_base,5,seed=sd)
    for i in t: c[R[i]["entry_date"][:7]]+=1
tot=sum(c.values())
allc=collections.Counter(r["entry_date"][:7] for r in R)
print("월 비중(슬롯선택 vs 전체):")
for m in sorted(allc): print("   %s  %5.1f%% vs %5.1f%%"%(m,100*c[m]/tot,100*allc[m]/614))
