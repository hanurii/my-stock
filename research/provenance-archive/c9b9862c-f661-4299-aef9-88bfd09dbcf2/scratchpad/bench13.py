# -*- coding: utf-8 -*-
"""표본 크기 프로브 v3 — 실제 매수규율(진입임박→익일 피벗돌파)의 '진입 건수'만 집계.
수익률·승률 일절 계산하지 않음(타당성 진단용 표본크기 측정)."""
import json, sys, time, collections, math
from bisect import bisect_right, bisect_left
from pathlib import Path
import numpy as np
ROOT=Path(r"C:/Users/hanul/playground/my-stock"); sys.path.insert(0,str(ROOT/"scripts"))
SER=ROOT/".cache"/"ohlcv"/"series"
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
days=ref[252:-1]   # 익일 확인 필요 → 마지막 날 제외
print(f"구간 {days[0]}~{days[-1]} ({len(days)}일)")

# 등가중 시장 변동성(20일 연율화) — 캐시만으로 산출
codes=list(store)
allmat={}
retmat=[]
for i,d in enumerate(ref):
    pass
# 간단히: 각 종목 일수익률 평균
prev={}; ewret=[]
for di,d in enumerate(ref):
    rs_=[]
    for c,s in store.items():
        k=bisect_right(s["dates"],d)
        if k<2: continue
        if s["dates"][k-1]!=d: continue
        a,b=s["closes"][k-2],s["closes"][k-1]
        if a and b: rs_.append(b/a-1.0)
    ewret.append(sum(rs_)/len(rs_) if rs_ else 0.0)
ewret=np.array(ewret)
vol20=np.array([np.std(ewret[max(0,i-19):i+1])*math.sqrt(252)*100 for i in range(len(ewret))])
di={d:i for i,d in enumerate(ref)}
vq=np.percentile(vol20[di[days[0]]:di[days[-1]]+1],[33,67])
print(f"변동성(등가중 20일 연율) 33/67 분위: {vq[0]:.1f}% / {vq[1]:.1f}%")

entries=[]
t0=time.time()
open_until={}
for asof in days:
    ks={c:bisect_right(s["dates"],asof) for c,s in store.items()}
    rets=[]
    for c,s in store.items():
        k=ks[c]
        if k<253: continue
        b=s["closes"][k-253]
        if not b: continue
        rets.append((c,s["closes"][k-1]/b-1.0))
    vals=sorted(x[1] for x in rets); n=len(vals)
    rsd={c:max(1,min(99,round(bisect_left(vals,r)/n*100))) for c,r in rets}
    v=vol20[di[asof]]
    vb="저" if v<vq[0] else "중" if v<vq[1] else "고"
    for c,s in store.items():
        k=ks[c]
        if k<200 or c in excl: continue
        if all((x or 0)==0 for x in s["volumes"][max(0,k-5):k]): continue
        if classify_non_minervini({"code":c},s,asof=asof): continue
        sub=s["closes"][:k]
        r=evaluate_trend_template(sub,rsd.get(c),80)
        if not r["pass"]: continue
        g=compute_gate_margin(r,sub[-1],rsd.get(c),80)
        gs=g["score"] if g else None
        st={kk:(s.get(kk) or [])[:k] for kk in KEYS if s.get(kk) is not None}
        for pname,fn in (("VCP",evaluate_vcp),("3C",evaluate_cheat),("PP",evaluate_power_play)):
            rr=fn(st)
            if rr.get("status")!="actionable" or not rr.get("pivot_price"): continue
            piv=rr["pivot_price"]
            if k>=len(s["dates"]): continue
            hi=s["highs"][k]
            if hi is None or hi<piv: continue
            ed=s["dates"][k]
            if c in open_until and ed<=open_until[c]: continue
            open_until[c]=ed   # 근사(실제는 청산일까지)
            entries.append({"code":c,"pat":pname,"scan":asof,"entry":ed,
                            "vb":vb,"gs":gs,"rs":rsd.get(c),"month":ed[:7]})
el=time.time()-t0
print(f"소요 {el:.0f}s · 총 진입 {len(entries)}건 ({len(entries)/len(days):.2f}건/일)")
print("패턴별:",dict(collections.Counter(e['pat'] for e in entries)))
print("변동성구간별:",dict(collections.Counter(e['vb'] for e in entries)))
gsv=[e['gs'] for e in entries if e['gs'] is not None]
if gsv:
    q=np.percentile(gsv,[25,50,75]); print(f"관문여유 점수 사분위 {np.round(q,1)}")
    b=collections.Counter("Q1" if x<q[0] else "Q2" if x<q[1] else "Q3" if x<q[2] else "Q4" for x in gsv)
    print("관문여유 사분위별:",dict(b))
print("월별:",dict(sorted(collections.Counter(e['month'] for e in entries).items())))
json.dump(entries, open(r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/entries.json","w"), ensure_ascii=False)
print(f"→ 299일 환산 총 진입 {len(entries)/len(days)*299:.0f}건")
