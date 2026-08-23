# -*- coding: utf-8 -*-
import json, collections, pickle, os, random, statistics
random.seed(3)
SP=os.path.dirname(os.path.abspath(__file__)); ROOT=r"C:/Users/hanul/playground/my-stock"
D=pickle.load(open(SP+"/regime_metrics.pkl","rb"))
dates,pos,M,up=D["dates"],D["pos"],D["M"],D["up"]
d=json.load(open(ROOT+"/public/data/backtest-volatility-pilot.json",encoding="utf-8"))
ev=[x for x in d["events"] if x["result"] in ("win","loss")]
def pay(e):
    g=e.get("gain_at_resolve_pct")
    return g if g is not None else (20.0 if e["result"]=="win" else -10.0)
byday=collections.defaultdict(list)
for e in ev: byday[e["entry_date"]].append(e)
S=M["⑬상승일비율10"]

SLOT=6
def sim(skip_fn, order="turnover"):
    tr=[]
    for dt in sorted(byday):
        if skip_fn(dt): continue
        lst=byday[dt][:]
        if order=="turnover": lst.sort(key=lambda e:-e["turnover_eok"])
        elif order=="random": random.shuffle(lst)
        tr += lst[:SLOT]
    n=len(tr); w=sum(1 for e in tr if e["result"]=="win")
    avg=sum(pay(e) for e in tr)/n
    return n, 100*w/n, avg, sum(pay(e) for e in tr)

print("[슬롯 6개 제약 시뮬레이션 — 거래대금 상위순으로 6개, 한 건당 수익률]")
for lab, fn in (("① 전부 매매(기준)", lambda dt: False),
                ("② 연일상승(10일중 8일↑) 날 쉬기", lambda dt: (S[pos[dt]-1] or 0)>=80),
                ("③ 조정국면 날 쉬기(이미 아는 규칙)", lambda dt: not up[pos[dt]-1]),
                ("④ 둘 다 쉬기", lambda dt: (not up[pos[dt]-1]) or (S[pos[dt]-1] or 0)>=80)):
    n,wr,avg,tot=sim(fn)
    print(f"  {lab:<32} 거래 {n:>3}건 승률 {wr:4.1f}%  건당 {avg:+5.2f}%  합계 {tot:+7.0f}%p")

# walk-forward: threshold = 75th percentile of the metric over PRIOR entry days only
days=sorted(byday)
hist=[]
tr_wf=[]; skipped=0
for dt in days:
    v=S[pos[dt]-1]
    thr=None
    if len(hist)>=30:
        h=sorted(hist); thr=h[int(0.75*len(h))]
    take = not (thr is not None and up[pos[dt]-1] and v>=thr)
    if take:
        lst=sorted(byday[dt], key=lambda e:-e["turnover_eok"])[:SLOT]; tr_wf+=lst
    else: skipped+=1
    hist.append(v)
n=len(tr_wf); w=sum(1 for e in tr_wf if e["result"]=="win")
print(f"\n[워크포워드(과거 데이터만으로 기준선) 상승국면 상위25% 날 쉬기] 쉰 날 {skipped}일 "
      f"거래 {n}건 승률 {100*w/n:.1f}% 건당 {sum(pay(e) for e in tr_wf)/n:+.2f}%")

# what if the rule is applied but you must trade something (opportunity cost of sitting out)
n0,wr0,avg0,tot0=sim(lambda dt: False)
n2,wr2,avg2,tot2=sim(lambda dt:(S[pos[dt]-1] or 0)>=80)
print(f"\n쉬어서 포기한 거래 {n0-n2}건, 합계 {tot0-tot2:+.0f}%p (그 거래들 건당 {(tot0-tot2)/(n0-n2):+.2f}%)")

# 전후반 분할 (진입일 2026-03-25)
print("\n[전후반 분할 — ② 규칙]")
for lab,f in (("전반",lambda dt:dt<"2026-03-25"),("후반",lambda dt:dt>="2026-03-25")):
    base=[e for dt in days if f(dt) for e in sorted(byday[dt],key=lambda e:-e["turnover_eok"])[:SLOT]]
    filt=[e for dt in days if f(dt) and not ((S[pos[dt]-1] or 0)>=80) for e in sorted(byday[dt],key=lambda e:-e["turnover_eok"])[:SLOT]]
    def ss(t): return (len(t), 100*sum(1 for e in t if e["result"]=="win")/len(t), sum(pay(e) for e in t)/len(t))
    a=ss(base); b=ss(filt)
    print(f"  {lab}: 기준 {a[0]}건 {a[1]:.1f}% {a[2]:+.2f}%  →  규칙 {b[0]}건 {b[1]:.1f}% {b[2]:+.2f}%  (건당 {b[2]-a[2]:+.2f}%p)")
