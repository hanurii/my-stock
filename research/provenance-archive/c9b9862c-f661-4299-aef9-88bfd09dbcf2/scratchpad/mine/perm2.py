import json, math, random, statistics as st
P=r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\trades_mine.json"
rows=json.load(open(P,encoding="utf-8"))
rows.sort(key=lambda r:r["sp"])
sp=[r["sp"] for r in rows]
n=len(rows)
MIN=5
splits=[k for k in range(MIN,n-MIN+1) if sp[k-1]!=sp[k]]  # split after k items
print("n=",n,"valid split points:",len(splits))
def maxstat(lab):
    pre=[0.0]*(n+1)
    for i,v in enumerate(lab): pre[i+1]=pre[i]+v
    best=0.0; bk=None
    for k in splits:
        d=abs(pre[k]/k-(pre[n]-pre[k])/(n-k))
        if d>best: best,bk=d,k
    return best,bk
for name,lab in (("winrate",[1.0 if r["net"]>0 else 0.0 for r in rows]),("meanNet",[r["net"] for r in rows])):
    obs,bk=maxstat(lab)
    print(f"{name}: observed max |diff| = {obs:.4f} at split after {bk} items (sp cut ~{sp[bk-1]:.1f}/{sp[bk]:.1f}), groups {bk}/{n-bk}")
    random.seed(11); NP=20000; c=0
    for _ in range(NP):
        perm=lab[:]; random.shuffle(perm)
        m,_=maxstat(perm)
        if m>=obs-1e-12: c+=1
    print(f"   permutation p (max over {len(splits)} cuts) = {(c+1)/(NP+1):.4f}")
