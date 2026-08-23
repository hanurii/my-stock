# -*- coding: utf-8 -*-
"""표본 크기 프로브 v2 — 실제 '매수 신호'에 해당하는 건수만 센다(수익률 계산 없음)."""
import json, sys, time, collections
from bisect import bisect_right, bisect_left
from pathlib import Path
ROOT = Path(r"C:/Users/hanul/playground/my-stock")
sys.path.insert(0, str(ROOT/"scripts"))
SER = ROOT/".cache"/"ohlcv"/"series"
from canslim_lib.trend_template import evaluate_trend_template, compute_gate_margin
from canslim_lib.minervini_filter import classify_non_minervini
from canslim_lib.liveness import load_excluded_codes
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat
from canslim_lib.power_play import evaluate_power_play

store={}
for f in sorted(SER.glob("*.json")):
    try: store[f.stem]=json.loads(f.read_text(encoding="utf-8"))
    except Exception: pass
excl=load_excluded_codes()
ref=store["005930"]["dates"]
KEYS=("dates","closes","opens","highs","lows","volumes","timestamps")
days=ref[252:]
print(f"구간 {days[0]}~{days[-1]} ({len(days)}일)")

state={}   # (code,pat) -> last status ('' if unseen)
entry=collections.Counter()      # 패턴별 신규 돌파진입(entry_ready & breakout & 직전 breakout 아님)
actionable=collections.Counter() # 패턴별 신규 진입임박
gate_bucket=collections.Counter()
per_day=[]
t0=time.time()
for asof in days:
    ks={c:bisect_right(s["dates"],asof) for c,s in store.items()}
    rets=[]
    for c,s in store.items():
        k=ks[c]
        if k<253: continue
        b=s["closes"][k-253]
        if not b: continue
        rets.append((c, s["closes"][k-1]/b-1.0))
    vals=sorted(x[1] for x in rets); n=len(vals)
    rs={c:max(1,min(99,round(bisect_left(vals,r)/n*100))) for c,r in rets}
    passers=[]
    nuni=0
    for c,s in store.items():
        k=ks[c]
        if k<200 or c in excl: continue
        if all((v or 0)==0 for v in s["volumes"][max(0,k-5):k]): continue
        if classify_non_minervini({"code":c}, s, asof=asof): continue
        nuni+=1
        sub=s["closes"][:k]
        r=evaluate_trend_template(sub, rs.get(c), 80)
        if r["pass"]:
            g=compute_gate_margin(r, sub[-1], rs.get(c), 80)
            passers.append((c, g["score"] if g else None, g["tightest"] if g else None))
    dayent=0
    for c,score,tight in passers:
        s=store[c]; k=ks[c]
        sub={kk:(s.get(kk) or [])[:k] for kk in KEYS if s.get(kk) is not None}
        for pname,fn,dk in (("VCP",evaluate_vcp,"vcp_detected"),("3C",evaluate_cheat,"pattern_detected"),("PP",evaluate_power_play,"pattern_detected")):
            r=fn(sub); st=r["status"]; det=bool(r.get(dk))
            key=(c,pname); prev=state.get(key)
            if det and st=="breakout" and prev!="breakout":
                entry[pname]+=1; dayent+=1
                if score is not None:
                    gate_bucket[("<20" if score<20 else "20~40" if score<40 else "40~60" if score<60 else "60+")]+=1
            if det and st=="actionable" and prev!="actionable":
                actionable[pname]+=1
            state[key]=st
    per_day.append((asof,nuni,len(passers),dayent))
el=time.time()-t0
D=len(days)
print(f"소요 {el:.0f}s ({el/D*1000:.0f} ms/일)")
tot_e=sum(entry.values()); tot_a=sum(actionable.values())
print(f"신규 '돌파 진입' 신호: {dict(entry)}  합계 {tot_e}건 ({tot_e/D:.1f}건/일) → 299일 환산 {tot_e/D*299:.0f}건")
print(f"신규 '진입임박' 신호: {dict(actionable)}  합계 {tot_a}건 → 299일 환산 {tot_a/D*299:.0f}건")
print(f"관문여유 점수 분포(돌파진입 기준): {dict(gate_bucket)}")
mm=collections.defaultdict(lambda:[0,0,0])
for asof,nu,np_,de in per_day:
    m=asof[:7]; mm[m][0]+=1; mm[m][1]+=np_; mm[m][2]+=de
print("월별: 일수 · 관문통과 평균 · 돌파진입 건")
for m in sorted(mm):
    d,p,e=mm[m]; print(f"  {m}: {d}일 · {p/d:.0f} · {e}건")
