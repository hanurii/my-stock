import json, statistics as st, collections
E=json.load(open("evfull.json",encoding="utf-8"))
R=json.load(open("rulescan.json",encoding="utf-8"))
g=[r["gain"] for r in R]
mon=[r["entry_date"][:7] for r in R]
print("Leave-one-month-out (현행 EV)")
for m in sorted(set(mon)):
    rest=[g[i] for i in range(len(g)) if mon[i]!=m]
    print("  %s 제외 → EV %+6.3f (n=%d)"%(m,st.mean(rest),len(rest)))
print()
# ambiguous 내역
amb=[e for e in E if e["result"]=="ambiguous"]
both=0;d0stop=0
for e in amb:
    s=e["ser"];b=e["bi_local"];P=e["entry_price"];T=P*1.2;S=P*0.9
    i=b+e["days_held"]
    ht=s["highs"][i]>=T; hs=s["lows"][i]<=S
    if ht and hs: both+=1
    else: d0stop+=1
print("ambiguous %d건 = 같은날 양쪽터치 %d · 진입일 손절만 %d"%(len(amb),both,d0stop))
base=sum(g)
print("비관(현행 파일) EV %.3f"%(base/614))
print("낙관A: 같은날 양쪽터치만 +20 → EV %.3f"%((base+both*30)/614))
print("낙관B: ambiguous 전부 +20 → EV %.3f"%((base+24*30)/614))
print()
# 진입일 손절(day0)만 따로
d0=[r for r in R if r["days"]==0]
print("진입일 당일 -10% 도달(첫날 즉사) %d건 = %.1f%%"%(len(d0),100*len(d0)/614))
# 승자의 도달 소요일
w=[r["days"] for r in R if r["result"]=="win"]
print("승자 %d건 목표도달 소요일 중앙 %d · 평균 %.1f · 90퍼센타일 %d"%(len(w),st.median(w),st.mean(w),sorted(w)[int(.9*len(w))]))
l=[r["days"] for r in R if r["result"]=="loss"]
print("패자 %d건 손절 소요일 중앙 %d · 평균 %.1f"%(len(l),st.median(l),st.mean(l)))
