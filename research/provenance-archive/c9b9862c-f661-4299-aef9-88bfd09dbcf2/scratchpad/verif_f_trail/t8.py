import json, sys
from pathlib import Path
sys.path.insert(0, r"C:/Users/hanul/playground/my-stock/scripts")
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR=Path(r"C:/Users/hanul/playground/my-stock/.cache/ohlcv/series")
exec(open("sim2.py",encoding="utf-8").read().split('if __name__')[0])
print("[인샘플 614건 — 추적폭 스윕 / 대안 규칙]")
base=build(maxhold=60); n=len(base)
b0=sum(r["base_ret"] for r in base)/n
print(f"  현행 +20/-10 익절            {b0:+.2f}%/건")
for tr in (5,7.5,10,12.5,15,20,25,30):
    R=[sim(e,"trail",trail=tr,maxhold=60) for e in EV]
    print(f"  +20 후 -{tr}% 추적            {sum(r['ret'] for r in R)/n:+.2f}%/건  (차이 {sum(r['ret'] for r in R)/n-b0:+.2f})")
print()
for tg in (25,30,40,50):
    R=[sim(e,"base",target=tg,maxhold=60) for e in EV]
    print(f"  고정 +{tg}/-10 익절           {sum(r['ret'] for r in R)/n:+.2f}%/건  (차이 {sum(r['ret'] for r in R)/n-b0:+.2f})")
print()
# 절반 익절 + 절반 추적
half=[]
for e in EV:
    a=sim(e,"base",maxhold=60); t=sim(e,"trail",maxhold=60)
    half.append(0.5*a["ret"]+0.5*t["ret"] if a["kind"]=="target" else a["ret"])
print(f"  +20에서 절반익절+절반추적      {sum(half)/n:+.2f}%/건  (차이 {sum(half)/n-b0:+.2f})")
