# -*- coding: utf-8 -*-
"""정렬 검증: 한국 entry_date 아침에 실제로 볼 수 있는 나스닥 종가인가 + DST."""
import json, os, bisect, datetime as dt, collections
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
NQ=json.load(open(B+'nasdaq.json',encoding='utf-8'))
nqd=sorted(NQ['up'])
EV=json.load(open(os.path.dirname(__file__)+'/EV.json',encoding='utf-8'))
print("up 비율:", f"{sum(NQ['up'][d] for d in nqd)/len(nqd)*100:.1f}%", f"({len(nqd)}일)")

def nq_before(k):
    i=bisect.bisect_left(nqd,k)
    return nqd[i-1] if i>0 else None

# --- 미국 서머타임 판정 (2007~ 규칙: 3월 2번째 일요일 ~ 11월 1번째 일요일)
def dst_us(d):
    y=d.year
    mar=dt.date(y,3,8);  mar+= dt.timedelta(days=(6-mar.weekday())%7)   # 2nd Sunday of March
    nov=dt.date(y,11,1); nov+= dt.timedelta(days=(6-nov.weekday())%7)   # 1st Sunday of Nov
    return mar<=d<nov

days=sorted({e['entry_date'] for e in EV})
print(f"\n한국 매매일 {len(days)}일에 붙은 미국 날짜 검사")
lag=collections.Counter(); viol=[]; arrive=collections.Counter()
for k in days:
    u=nq_before(k)
    kd=dt.date.fromisoformat(k); ud=dt.date.fromisoformat(u)
    lag[(kd-ud).days]+=1
    if ud>=kd: viol.append((k,u))
    # 미국 종가(16:00 ET)가 한국 시간 언제 도착하나
    et_off = 4 if dst_us(ud) else 5           # ET = UTC-4(EDT) / UTC-5(EST)
    kst_close = dt.datetime.combine(ud, dt.time(16,0)) + dt.timedelta(hours=et_off+9)
    kor_open  = dt.datetime.combine(kd, dt.time(9,0))
    hrs=(kor_open-kst_close).total_seconds()/3600
    arrive[round(hrs)]+=1
    if hrs<=0: print("  !! 개장 후 도착:",k,u,hrs)
print("  캘린더 시차(한국날짜-미국날짜) 분포:", dict(sorted(lag.items())))
print("  미국날짜 >= 한국날짜 (룩어헤드) 건수:", len(viol))
print("  나스닥 종가 확정 → 한국 개장까지 여유(시간) 분포:", dict(sorted(arrive.items())))
print("  최소 여유시간:", min(arrive), "시간")

# DST 전환 주 스팟체크
print("\n[서머타임 전환 전후 스팟체크 — 한국날짜 : 붙은 미국날짜 : 시차 : 여유(h) : EDT?]")
sw=[]
for y in range(2021,2027):
    mar=dt.date(y,3,8);  mar+=dt.timedelta(days=(6-mar.weekday())%7)
    nov=dt.date(y,11,1); nov+=dt.timedelta(days=(6-nov.weekday())%7)
    sw += [mar,nov]
for s in sw:
    for off in (-1,0,1,2):
        k=(s+dt.timedelta(days=off)).isoformat()
        if k not in days: continue
        u=nq_before(k); ud=dt.date.fromisoformat(u); kd=dt.date.fromisoformat(k)
        et=4 if dst_us(ud) else 5
        hrs=((dt.datetime.combine(kd,dt.time(9,0)))-(dt.datetime.combine(ud,dt.time(16,0))+dt.timedelta(hours=et+9))).total_seconds()/3600
        print(f"   {k} : {u} : {(kd-ud).days}d : {hrs:.0f}h : {'EDT' if dst_us(ud) else 'EST'}")

# 시차 3일 이상인 날 = 연휴. 샘플 출력
odd=[(k,nq_before(k)) for k in days if (dt.date.fromisoformat(k)-dt.date.fromisoformat(nq_before(k))).days>=4]
print(f"\n시차>=4일인 한국 매매일 {len(odd)}건 (연휴 겹침):", odd[:12])
