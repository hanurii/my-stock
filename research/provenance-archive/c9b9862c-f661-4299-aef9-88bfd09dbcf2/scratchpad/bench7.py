# -*- coding: utf-8 -*-
"""표본 크기 프로브(수익률 계산 없음): 가용 구간에서 하루당 몇 건이 나오는지만 센다."""
import json, sys, time
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

# 가용 구간: 253봉 이상 = 2026-01-13 부터
start=252
days=ref[start:]
print(f"프로브 구간 {days[0]} ~ {days[-1]} ({len(days)}일)")

prev_status={}   # (code,pat) -> status
tot={"universe":0,"pass":0}
det_cnt={p:{"detected":0,"entry_ready":0,"breakout_event":0} for p in ("VCP","3C","PP")}
t0=time.time()
per_day=[]
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
    keep=[]
    for c,s in store.items():
        k=ks[c]
        if k<200 or c in excl: continue
        if all((v or 0)==0 for v in s["volumes"][max(0,k-5):k]): continue
        if classify_non_minervini({"code":c}, s, asof=asof): continue
        keep.append(c)
    passers=[]
    for c in keep:
        s=store[c]; k=ks[c]
        sub=s["closes"][:k]
        r=evaluate_trend_template(sub, rs.get(c), 80)
        if r["pass"]: passers.append(c)
    tot["universe"]+=len(keep); tot["pass"]+=len(passers)
    dd={p:0 for p in det_cnt}
    for c in passers:
        s=store[c]; k=ks[c]
        sub={kk:(s.get(kk) or [])[:k] for kk in KEYS if s.get(kk) is not None}
        for pname,fn,dk in (("VCP",evaluate_vcp,"vcp_detected"),
                            ("3C",evaluate_cheat,"pattern_detected"),
                            ("PP",evaluate_power_play,"pattern_detected")):
            r=fn(sub)
            st=r["status"]; d=r.get(dk)
            if d: det_cnt[pname]["detected"]+=1
            er = bool(d and st in ("breakout","actionable"))
            if er: det_cnt[pname]["entry_ready"]+=1; dd[pname]+=1
            key=(c,pname)
            if st=="breakout" and prev_status.get(key)!="breakout":
                det_cnt[pname]["breakout_event"]+=1
            prev_status[key]=st
    per_day.append((asof,len(keep),len(passers),dd["VCP"],dd["3C"],dd["PP"]))
el=time.time()-t0
D=len(days)
print(f"소요 {el:.0f}초 ({el/D*1000:.0f} ms/일)")
print(f"평균 유니버스 {tot['universe']/D:.0f} · 평균 8조건통과 {tot['pass']/D:.1f}")
for p,v in det_cnt.items():
    print(f"  {p}: 검출 종목일 {v['detected']}  진입가능 종목일 {v['entry_ready']}  신규돌파 이벤트 {v['breakout_event']}")
tot_ev=sum(v['breakout_event'] for v in det_cnt.values())
print(f"  합계 신규돌파 이벤트 {tot_ev}건 / {D}일 = {tot_ev/D:.2f}건/일 → 299일 환산 {tot_ev/D*299:.0f}건")
print("\n월별 통과/이벤트:")
import collections
mm=collections.defaultdict(lambda:[0,0,0])
for asof,nk,np_,a,b,c in per_day:
    m=asof[:7]; mm[m][0]+=1; mm[m][1]+=np_; mm[m][2]+=a+b+c
for m in sorted(mm):
    d,p,e=mm[m]; print(f"  {m}: {d}일 · 통과 평균 {p/d:.0f} · 진입가능 종목일 {e}")
