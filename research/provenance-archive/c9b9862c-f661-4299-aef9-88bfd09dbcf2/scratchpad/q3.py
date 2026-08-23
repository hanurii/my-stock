# -*- coding: utf-8 -*-
from engine import *
from statistics import mean, median

def first_touch(p, lvl):
    for k,b in enumerate(p["path"]):
        if b["h"] >= lvl: return k
    return None
def first_stop(p, lvl=-10.0):
    for k,b in enumerate(p["path"]):
        if b["l"] <= lvl: return k
    return None

winners=[]   # 현행 규칙 승리(=-10 이전에 +20 도달)
for p in PATHS:
    t = first_touch(p,20.0); s = first_stop(p)
    if t is None: continue
    if s is not None and s < t: continue
    if s is not None and s == t: continue   # 같은날 동시 = 모호, 제외
    winners.append((p,t))
print("현행 승리(+20 선착):", len(winners), "종목", len(set(p['code'] for p,_ in winners)))

dts=[t for _,t in winners]
print("\n[+20% 도달까지 걸린 거래일] (진입일=0)")
print(f"  중앙 {median(dts):.0f}  평균 {mean(dts):.1f}  Q1 {q(dts,.25):.0f}  Q3 {q(dts,.75):.0f}  P90 {q(dts,.90):.0f}  최대 {max(dts)}")
import collections
cum=collections.Counter()
for t in dts: cum[t]+=1
acc=0; tot=len(dts)
print("  누적 도달비율:", end=" ")
for cut in (0,1,2,3,5,7,10,15,20,30,40):
    n=sum(1 for t in dts if t<=cut)
    print(f"{cut}일 {n/tot*100:.0f}%", end="  ")
print()

print("\n[+20% 도달 전 최저점 — 진입가 대비] (손절 -10 이 하한)")
mins=[]; retr=[]; belows=[]; belowf=[]; troughday=[]; stall=[]
for p,t in winners:
    seg=p["path"][:t+1]
    mn=min(b["l"] for b in seg); mins.append(mn)
    troughday.append(min(range(len(seg)), key=lambda i: seg[i]["l"]))
    # 고점 대비 최대 되돌림
    pk=-1e9; worst=0.0
    for b in seg:
        pk=max(pk,b["h"])
        worst=min(worst, b["l"]-pk)
    retr.append(worst)
    belows.append(sum(1 for b in seg[:-1] if b["c"] < 0))
    belowf.append(sum(1 for b in seg[:-1] if b["c"] < 5))
    # 최장 무진전(신고가 미경신) 연속일
    pk=-1e9; run=0; mx=0
    for b in seg:
        if b["h"]>pk: pk=b["h"]; run=0
        else: run+=1; mx=max(mx,run)
    stall.append(mx)
for lbl,v in (("최저(진입가대비)%",mins),("고점대비 최대되돌림%p",retr)):
    print(f"  {lbl}: 중앙 {median(v):.1f}  Q1 {q(v,.25):.1f}  Q3 {q(v,.75):.1f}  최악 {min(v):.1f}")
print(f"  진입가 아래에서 보낸 거래일: 중앙 {median(belows):.0f}  Q3 {q(belows,.75):.0f}  최대 {max(belows)}")
print(f"  +5% 미만에서 보낸 거래일   : 중앙 {median(belowf):.0f}  Q3 {q(belowf,.75):.0f}  최대 {max(belowf)}")
print(f"  최저점이 찍힌 일차         : 중앙 {median(troughday):.0f}  Q3 {q(troughday,.75):.0f}")
print(f"  최장 무진전(신고가 미경신) : 중앙 {median(stall):.0f}  Q3 {q(stall,.75):.0f}  최대 {max(stall)}")
th=[1 for v in mins if v<=-5]; th8=[1 for v in mins if v<=-8]
print(f"  -5% 아래까지 내려갔다 온 승자 {len(th)}/{tot} ({len(th)/tot*100:.0f}%),  -8% 아래 {len(th8)}/{tot} ({len(th8)/tot*100:.0f}%)")
r5=[1 for v in retr if v<=-8]; r10=[1 for v in retr if v<=-12]
print(f"  고점 대비 8%p 이상 되돌린 승자 {len(r5)}/{tot} ({len(r5)/tot*100:.0f}%), 12%p 이상 {len(r10)}/{tot} ({len(r10)/tot*100:.0f}%)")

print("\n[참고] 손절 무시하고 끝까지 들었다면 +20% 도달 건수")
allt=[first_touch(p,20.0) for p in PATHS]
n20=sum(1 for t in allt if t is not None)
print(f"  614건 중 {n20}건 ({n20/614*100:.0f}%) 이 경로 안에서 언젠가 +20% 터치 (중앙 {median([t for t in allt if t is not None]):.0f}일)")
