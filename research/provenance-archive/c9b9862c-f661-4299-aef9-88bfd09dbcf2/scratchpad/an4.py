import json, os, statistics, random, sys
from collections import defaultdict
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix
SCRATCH=os.environ["SCRATCH"]
P=json.load(open(os.path.join(SCRATCH,"panel.json"),encoding="utf-8"))
RULES=P["rules"]; EV=P["events"]
for e in EV:
    e["ff"]={}; e["retk"]={dd["k"]: dd["ret_close"] for dd in e["days"]}
    for ri,r in enumerate(RULES):
        f=None
        for dd in e["days"]:
            if dd["st"][ri]=="violation": f=dd["k"]; break
        e["ff"][r]=f
    f=None
    for dd in e["days"]:
        if any(st=="violation" for st in dd["st"]): f=dd["k"]; break
    e["ff"]["ANY5"]=f
ALL=RULES+["ANY5"]
def ret_rule(e,r):
    k=e["ff"][r]
    return e["retk"][k] if (k is not None and k<e["K"]) else e["ret_hold"]

print("="*100)
print("[E] 전후반 분할 (진입일 2026-03-25 기준) — 부호 유지 확인")
print("="*100)
H1=[e for e in EV if e["entry_date"]<"2026-03-25"]; H2=[e for e in EV if e["entry_date"]>="2026-03-25"]
print(f"전반 {len(H1)}건(끝까지 평균 {statistics.mean(x['ret_hold'] for x in H1):+.2f}%), 후반 {len(H2)}건({statistics.mean(x['ret_hold'] for x in H2):+.2f}%)")
for r in ALL:
    row=[]
    for lab,S in (("전반",H1),("후반",H2)):
        b=statistics.mean(e["ret_hold"] for e in S); m=statistics.mean(ret_rule(e,r) for e in S)
        fired=[e for e in S if e["ff"][r] is not None and e["ff"][r]<e["K"]]
        wf=sum(1 for e in fired if e["result"]=="win")/len(fired)*100 if fired else float('nan')
        clean=[e for e in S if not(e["ff"][r] is not None and e["ff"][r]<e["K"])]
        wc=sum(1 for e in clean if e["result"]=="win")/len(clean)*100 if clean else float('nan')
        row.append(f"{lab}: 돈차 {m-b:+.2f}%p / 점등후승률 {wf:.0f}% vs 미점등 {wc:.0f}% (n={len(fired)})")
    print(f"■ {r:24s} " + " | ".join(row))

print()
print("="*100)
print("[F] 강건성 — 종가 대신 '다음날 시가'에 파는 현실 집행")
print("="*100)
cache={}
for e in EV:
    s=cache.get(e["code"]) or ohlcv_matrix.get_series(e["code"]); cache[e["code"]]=s
    b=s["dates"].index(e["entry_date"]); e["_b"]=b; e["_s"]=s
def ret_rule_open(e,r):
    k=e["ff"][r]
    if k is None or k>=e["K"]: return e["ret_hold"]
    s=e["_s"]; i=e["_b"]+k+1
    if i>=len(s["opens"]) or not s["opens"][i]: return e["retk"][k]
    px=s["opens"][i]
    # 다음날 시가가 이미 스톱/타깃 밖이면 그 값으로 클램프하지 않고 시가 그대로(현실)
    return (px/e["entry_price"]-1)*100
base=statistics.mean(e["ret_hold"] for e in EV)
for r in ALL:
    m1=statistics.mean(ret_rule(e,r) for e in EV); m2=statistics.mean(ret_rule_open(e,r) for e in EV)
    print(f"■ {r:24s} 당일종가매도 {m1:+.2f}% ({m1-base:+.2f}%p) | 익일시가매도 {m2:+.2f}% ({m2-base:+.2f}%p)")

print()
print("="*100)
print("[G] 조건부 변형 — '규칙 뜬 날 손실 중일 때만 판다' / '이익 중일 때만 판다'")
print("="*100)
for r in ALL:
    def rr(e, cond):
        k=e["ff"][r]
        if k is not None and k<e["K"] and cond(e["retk"][k]): return e["retk"][k]
        return e["ret_hold"]
    a=statistics.mean(rr(e, lambda x: x<0) for e in EV)
    bp=statistics.mean(rr(e, lambda x: x>=0) for e in EV)
    na=sum(1 for e in EV if e["ff"][r] is not None and e["ff"][r]<e["K"] and e["retk"][e["ff"][r]]<0)
    nb=sum(1 for e in EV if e["ff"][r] is not None and e["ff"][r]<e["K"] and e["retk"][e["ff"][r]]>=0)
    print(f"■ {r:24s} 손실중만 매도 {a:+.2f}% ({a-base:+.2f}%p, n={na}) | 이익중만 매도 {bp:+.2f}% ({bp-base:+.2f}%p, n={nb})")

print()
print("="*100)
print("[H] '-10% 손절이 이미 하는 일'인가? — 손절 없이 +20%만 노릴 때 규칙의 가치")
print("="*100)
# 손절 없는 기준선: 진입 후 +20% 먼저 닿으면 익절, 아니면 데이터 끝 종가
def hold_nostop(e):
    s=e["_s"]; b=e["_b"]; T=e["pivot"]*1.2
    for i in range(b, len(s["closes"])):
        if s["highs"][i] is not None and s["highs"][i]>=T:
            return (T/e["entry_price"]-1)*100
    return (s["closes"][-1]/e["entry_price"]-1)*100
base_ns=statistics.mean(hold_nostop(e) for e in EV)
print(f"손절 없는 기준선(+20% 익절만, 아니면 8/21까지 보유): 평균 {base_ns:+.2f}%/건")
for r in ALL:
    def rr(e):
        k=e["ff"][r]
        if k is not None and k<e["K"]: return e["retk"][k]
        return hold_nostop(e)
    m=statistics.mean(rr(e) for e in EV)
    print(f"■ {r:24s} 규칙매도 {m:+.2f}% ({m-base_ns:+.2f}%p)")
