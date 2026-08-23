import json, statistics as st, random, os
from pathlib import Path
D=Path(r"C:\Users\hanul\playground\my-stock\.cache\ohlcv\series")
files=sorted(D.glob("*.json"))
random.Random(3).shuffle(files)
S,Eb="2025-11-26","2026-08-21"
rets=[]
for p in files[:900]:
    try: s=json.loads(p.read_text(encoding="utf-8"))
    except Exception: continue
    ds=s.get("dates") or []; cl=s.get("closes") or []
    a=b=None
    for i,d in enumerate(ds):
        if a is None and d>=S: a=i
        if d<=Eb: b=i
    if a is None or b is None or b<=a or not cl[a] or not cl[b]: continue
    rets.append((cl[b]/cl[a]-1)*100)
rets.sort()
print(f"표본 {len(rets)}종목 · 2025-11-26→2026-08-21 개별주 수익률")
print(f"  중앙 {st.median(rets):+.1f}%  평균 {st.mean(rets):+.1f}%  25%p {rets[len(rets)//4]:+.1f}  75%p {rets[3*len(rets)//4]:+.1f}")
