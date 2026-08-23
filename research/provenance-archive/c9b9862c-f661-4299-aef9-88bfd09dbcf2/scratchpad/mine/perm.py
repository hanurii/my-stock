import json, math, random, statistics as st, collections
P=r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\trades_mine.json"
rows=json.load(open(P,encoding="utf-8"))
sp=[r["sp"] for r in rows]; win=[1 if r["net"]>0 else 0 for r in rows]; net=[r["net"] for r in rows]
cuts=[c for c in range(1,101) if 5<=sum(1 for x in sp if x<c)<=len(sp)-5]
print("cuts scanned:",len(cuts), cuts[:5],"...",cuts[-5:])
def maxstat(labels, vals):
    best=0; bestc=None
    for c in cuts:
        A=[labels[i] for i in range(len(sp)) if sp[i]<c]; B=[labels[i] for i in range(len(sp)) if sp[i]>=c]
        d=abs(st.mean(A)-st.mean(B))
        if d>best: best,bestc=d,c
    return best,bestc
obs_w,cw=maxstat(win,None); obs_n,cn=maxstat(net,None)
print(f"observed max |winrate diff| = {obs_w:.3f} at cut {cw}")
print(f"observed max |meanNet diff| = {obs_n:.3f} at cut {cn}")
random.seed(7)
NP=20000
cw_=0; cn_=0
for _ in range(NP):
    perm=win[:]; random.shuffle(perm)
    m,_c=maxstat(perm,None)
    if m>=obs_w: cw_+=1
for _ in range(NP):
    perm=net[:]; random.shuffle(perm)
    m,_c=maxstat(perm,None)
    if m>=obs_n: cn_+=1
print(f"permutation p (max over all cuts, winrate) = {(cw_+1)/(NP+1):.4f}")
print(f"permutation p (max over all cuts, meanNet)  = {(cn_+1)/(NP+1):.4f}")
# also spearman permutation
def rank(v):
    s=sorted(range(len(v)),key=lambda i:v[i]); r=[0]*len(v); i=0
    while i<len(s):
        j=i
        while j+1<len(s) and v[s[j+1]]==v[s[i]]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): r[s[k]]=avg
        i=j+1
    return r
def pear(x,y):
    mx=st.mean(x);my=st.mean(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
rs_=pear(rank(sp),rank(net)); print("spearman", round(rs_,3))
c=0
for _ in range(NP):
    perm=net[:]; random.shuffle(perm)
    if abs(pear(rank(sp),rank(perm)))>=abs(rs_): c+=1
print("spearman perm p =", (c+1)/(NP+1))
