import json, statistics as st, collections
E=json.load(open("evfull.json",encoding="utf-8"))
R=json.load(open("rulescan.json",encoding="utf-8"))
RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]
def px(i,k,which="close"):
    s=E[i]["ser"]; b=E[i]["bi_local"]
    j=b+k
    if j>=len(s["closes"]): j=len(s["closes"])-1
    return s[which+"s"][j] if which!="close" else s["closes"][j]
def openpx(i,k):
    s=E[i]["ser"]; b=E[i]["bi_local"]; j=min(b+k,len(s["closes"])-1)
    return s["opens"][j] if s["opens"][j] is not None else s["closes"][j]

base_g=[r["gain"] for r in R]; base_d=[r["days"] for r in R]
print("BASE  n=%d EV=%.3f sum=%.1f days=%d perday=%.4f"%(len(R),st.mean(base_g),sum(base_g),sum(base_d),sum(base_g)/sum(base_d)))
print()
print("규칙별 점등률(결착 전까지 한 번이라도 violation) 및 규칙청산 성적")
hdr="%-24s %5s %5s | %8s %8s %7s | %8s"%("rule","fire","early","EV_close","EV_open","days","perday")
print(hdr)
def sim(rule_fn, mode="close"):
    gs=[];ds=[]
    for r in R:
        i=r["i"]; k=rule_fn(r)
        if k is not None and k < r["days"]:
            P=E[i]["entry_price"]
            if mode=="close": g=(px(i,k)/P-1)*100; d=k
            else: g=(openpx(i,k+1)/P-1)*100; d=k+1
            gs.append(g); ds.append(d)
        else:
            gs.append(r["gain"]); ds.append(r["days"])
    return gs,ds
for rid in RULES:
    f=lambda r,rid=rid: r["fires"][rid]
    nf=sum(1 for r in R if r["fires"][rid] is not None)
    ne=sum(1 for r in R if r["fires"][rid] is not None and r["fires"][rid]<r["days"])
    gc,dc=sim(f,"close"); go,do=sim(f,"open")
    print("%-24s %5d %5d | %8.3f %8.3f %7d | %8.4f"%(rid,nf,ne,st.mean(gc),st.mean(go),sum(dc),sum(gc)/sum(dc)))
# any-rule
def anyf(r):
    ks=[r["fires"][x] for x in RULES if r["fires"][x] is not None]
    return min(ks) if ks else None
gc,dc=sim(anyf,"close"); go,do=sim(anyf,"open")
ne=sum(1 for r in R if anyf(r) is not None and anyf(r)<r["days"])
print("%-24s %5d %5d | %8.3f %8.3f %7d | %8.4f"%("ANY5",sum(1 for r in R if anyf(r) is not None),ne,st.mean(gc),st.mean(go),sum(dc),sum(gc)/sum(dc)))
# 2+ rules
def two(r):
    ks=sorted(r["fires"][x] for x in RULES if r["fires"][x] is not None)
    return ks[1] if len(ks)>=2 else None
gc,dc=sim(two,"close")
print("%-24s %5d %5d | %8.3f %8s %7d | %8.4f"%("2+rules",sum(1 for r in R if two(r) is not None),sum(1 for r in R if two(r) is not None and two(r)<r["days"]),st.mean(gc),"-",sum(dc),sum(gc)/sum(dc)))
def three(r):
    ks=sorted(r["fires"][x] for x in RULES if r["fires"][x] is not None)
    return ks[2] if len(ks)>=3 else None
gc,dc=sim(three,"close")
print("%-24s %5d %5d | %8.3f %8s %7d | %8.4f"%("3+rules",sum(1 for r in R if three(r) is not None),sum(1 for r in R if three(r) is not None and three(r)<r["days"]),st.mean(gc),"-",sum(dc),sum(gc)/sum(dc)))
