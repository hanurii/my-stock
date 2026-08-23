import json, statistics
from collections import defaultdict
rows = json.load(open("rows.json"))
for r in rows: r["d"]=r["tr_ret"]-r["base_ret"]; r["m"]=r["entry"][:7]
n=len(rows); tot=sum(r["d"] for r in rows)
nz=[r["d"] for r in rows if abs(r["d"])>1e-9]
print("전체 %d건  현행 %+.2f%%/건, 추적 %+.2f%%/건, 차이 %+.3f%%p/건 (합 %+.0f%%p)" % (
    n, sum(r["base_ret"] for r in rows)/n, sum(r["tr_ret"] for r in rows)/n, tot/n, tot))
print("영향받은 거래 %d건: 이득 %d / 손해 %d / 중앙값 %+.2f%%p / 평균 %+.2f%%p" % (
    len(nz), sum(1 for x in nz if x>0), sum(1 for x in nz if x<0), statistics.median(nz), sum(nz)/len(nz)))
sd=sorted(nz, reverse=True)
print("\n[꼬리 의존] 상위 k건 제거 후 차이/건")
for k in (0,1,3,5,10,15,20,25,30):
    print(f"  top{k:>2} 제거: 합 {tot-sum(sd[:k]):+8.0f}  차이/건 {(tot-sum(sd[:k]))/n:+.3f}%p   (상위{k}가 개선분의 {sum(sd[:k])/tot*100:.0f}%)")
print("\n[월별]  n   현행    추적    차이/건   차이합")
by=defaultdict(list)
for r in rows: by[r["m"]].append(r)
for m in sorted(by):
    v=by[m]; b=sum(x["base_ret"] for x in v)/len(v); t=sum(x["tr_ret"] for x in v)/len(v)
    print(f"  {m}  {len(v):4d}  {b:+7.2f} {t:+7.2f}  {t-b:+7.2f}  {sum(x['d'] for x in v):+8.0f}")
print("\n[월 제외 민감도]")
for drop in [["2026-04"],["2026-05"],["2026-04","2026-05"],["2026-01"],["2025-12"],["2026-04","2026-05","2026-01"]]:
    keep=[r for r in rows if r["m"] not in drop]
    print(f"  {'+'.join(drop):<26} 제외: n={len(keep):3d}  차이/건 {sum(r['d'] for r in keep)/len(keep):+.3f}%p  (현행 {sum(r['base_ret'] for r in keep)/len(keep):+.2f} → 추적 {sum(r['tr_ret'] for r in keep)/len(keep):+.2f})")
print("\n[전후반 2026-03-25 분할]")
for lab,f in [("전반 ~03-24", lambda r: r["entry"]<="2026-03-24"),("후반 03-25~", lambda r: r["entry"]>="2026-03-25")]:
    v=[r for r in rows if f(r)]
    print(f"  {lab}: n={len(v)} 현행 {sum(x['base_ret'] for x in v)/len(v):+.2f} 추적 {sum(x['tr_ret'] for x in v)/len(v):+.2f} 차이 {sum(x['d'] for x in v)/len(v):+.3f}%p (이득{sum(1 for x in v if x['d']>0)}/손해{sum(1 for x in v if x['d']<0)})")
    sdv=sorted([x['d'] for x in v],reverse=True); tv=sum(sdv)
    print(f"     상위5 제거 후 차이/건 {(tv-sum(sdv[:5]))/len(v):+.3f}%p, 상위10 제거 {(tv-sum(sdv[:10]))/len(v):+.3f}%p")
