import json, statistics
from collections import defaultdict
rows = json.load(open("rows.json"))
for r in rows: r["d"]=r["tr_ret"]-r["base_ret"]; r["m"]=r["entry"][:7]
by=defaultdict(list)
for r in rows: by[r["m"]].append(r)
print("월별 (진입월)  n   현행평균  추적평균   차이/건    차이합")
for m in sorted(by):
    v=by[m]; b=sum(x["base_ret"] for x in v)/len(v); t=sum(x["tr_ret"] for x in v)/len(v)
    print(f"  {m}  {len(v):4d}  {b:+7.2f}  {t:+7.2f}  {t-b:+7.2f}  {sum(x['d'] for x in v):+8.0f}")
print()
tot=sum(r["d"] for r in rows); n=len(rows)
for drop in ["2026-04","2026-05","2026-01","2025-12"]:
    keep=[r for r in rows if r["m"]!=drop]
    print(f"drop {drop}: n={len(keep)} delta/trade={sum(r['d'] for r in keep)/len(keep):+.3f}  base={sum(r['base_ret'] for r in keep)/len(keep):+.2f} trail={sum(r['tr_ret'] for r in keep)/len(keep):+.2f}")
keep=[r for r in rows if r["m"] not in ("2026-04","2026-05")]
print(f"drop 04+05: n={len(keep)} delta/trade={sum(r['d'] for r in keep)/len(keep):+.3f}")
print()
# 전후반
for lab,f in [("전반 ~2026-03-24", lambda r: r["entry"]<="2026-03-24"),("후반 2026-03-25~", lambda r: r["entry"]>="2026-03-25")]:
    v=[r for r in rows if f(r)]
    print(f"{lab}: n={len(v)} base={sum(x['base_ret'] for x in v)/len(v):+.2f} trail={sum(x['tr_ret'] for x in v)/len(v):+.2f} delta={sum(x['d'] for x in v)/len(v):+.3f}  posDelta={sum(1 for x in v if x['d']>0)} negDelta={sum(1 for x in v if x['d']<0)}")
