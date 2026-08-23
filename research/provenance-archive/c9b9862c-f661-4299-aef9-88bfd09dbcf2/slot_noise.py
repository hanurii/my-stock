import json, statistics as st, random, collections
exec(open("slot.py",encoding="utf-8").read().split("print(\"=== ")[0])
def anyf(r):
    ks=[r["fires"][x] for x in RULES if r["fires"][x] is not None]
    return min(ks) if ks else None
pols={"현행":policy_base,
      "heavy_vol_pullback":make_rule_policy(lambda r:r["fires"]["heavy_volume_pullback"]),
      "ANY5":make_rule_policy(anyf)}
for ns in (3,5,10):
    print("[슬롯 %d] 동일진입일 순서 무작위 300회"%ns)
    res={}
    for name,p in pols.items():
        eqs=[]
        for s in range(300):
            t,g,h=slotsim(p,ns,seed=s)
            eq=1.0
            for x in g: eq*=(1+x/100/ns)
            eqs.append((eq-1)*100)
        res[name]=eqs
        print("  %-20s 중앙 %+7.2f%%  [5%%~95%%: %+7.2f ~ %+7.2f]  평균 %+7.2f"%(name,st.median(eqs),sorted(eqs)[15],sorted(eqs)[284],st.mean(eqs)))
    b=res["현행"]; h=res["heavy_vol_pullback"]
    wins=sum(1 for i in range(300) if h[i]>b[i])
    print("  → heavy_vol_pullback 이 현행을 이긴 추첨: %d/300"%wins)
