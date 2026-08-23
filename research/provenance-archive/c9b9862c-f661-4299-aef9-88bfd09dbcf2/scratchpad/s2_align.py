# -*- coding: utf-8 -*-
"""나스닥 날짜 키 자체를 검사: 미국 거래일 캘린더인가? 휴장일/DST."""
import json, os, datetime as dt, collections
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
NQ=json.load(open(B+'nasdaq.json',encoding='utf-8'))
dts=sorted(NQ['close'])
print("nasdaq days:", len(dts), dts[0], "~", dts[-1])
print("close keys == up keys:", sorted(NQ['close'])==sorted(NQ['up']))
# 요일 분포
wd=collections.Counter(dt.date.fromisoformat(d).weekday() for d in dts)
print("weekday counts (0=Mon..6=Sun):", dict(sorted(wd.items())))
# 연도별 거래일 수 (정상 미국 거래일 = 251~252)
yr=collections.Counter(d[:4] for d in dts)
print("per-year:", dict(sorted(yr.items())))
# 미국 공휴일 스팟체크 (있으면 안 됨)
hol = ["2021-01-18","2021-07-05","2021-11-25","2021-12-24","2022-01-17","2022-06-20",
       "2023-01-02","2023-07-04","2023-11-23","2024-01-01","2024-06-19","2024-11-28",
       "2025-01-09","2025-07-04","2026-01-01","2026-01-19","2026-07-03"]
print("\n[미국 휴장일이 데이터에 있는가 — 있으면 캘린더 오염]")
for h in hol:
    print(f"  {h} in data: {h in NQ['close']}")
# 한국 공휴일이 미국엔 열려있음 → 있어야 정상
kh=["2021-03-01","2022-05-05","2023-10-03","2024-03-01","2025-05-05","2026-05-05"]
print("\n[한국 휴장·미국 개장일 — 있어야 정상]")
for h in kh: print(f"  {h} in data: {h in NQ['close']}")
# up 값 자체 검증: close 대비 전일비로 재계산해 일치하는가
bad=0; miss=0
for i in range(1,len(dts)):
    u = NQ['close'][dts[i]] > NQ['close'][dts[i-1]]
    if NQ['up'][dts[i]] != u: bad+=1
print(f"\n[up[] 재계산 일치] 불일치 {bad}/{len(dts)-1}")
print("up 비율:", sum(1 for d in dts if NQ['up'][d])/len(dts)*100)
# 연속 결측 gap (거래일 간 캘린더 간격)
gap=collections.Counter()
for i in range(1,len(dts)):
    gap[(dt.date.fromisoformat(dts[i])-dt.date.fromisoformat(dts[i-1])).days]+=1
print("consecutive calendar gap:", dict(sorted(gap.items())))
big=[(dts[i-1],dts[i]) for i in range(1,len(dts)) if (dt.date.fromisoformat(dts[i])-dt.date.fromisoformat(dts[i-1])).days>=5]
print("gap>=5d:", big)
