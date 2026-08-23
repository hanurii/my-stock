import sys, random, statistics as s
sys.path.insert(0,"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/taskB_stack")
from blib import *
d, ev = bload()
YEARS = 180/250.0
SLOTS = 5
POS = 10_000_000

alldates = sorted(set(e["entry_date"] for e in ev))

def simulate(filt, rank, slots=SLOTS, seed=None):
    """rank: 후보 정렬 키(작을수록 우선). seed 주면 무작위 순서."""
    rng = random.Random(seed) if seed is not None else None
    cands = defaultdict(list)
    for e in ev:
        if filt(e): cands[e["entry_date"]].append(e)
    open_pos = []   # (resolve_date, code, event)
    taken = []
    for dte in alldates:
        open_pos = [p for p in open_pos if p[0] >= dte]  # resolve_date < 오늘이면 슬롯 해제
        held = set(p[1] for p in open_pos)
        lst = [e for e in cands.get(dte, []) if e["code"] not in held]
        if rng: rng.shuffle(lst)
        else: lst.sort(key=rank)
        for e in lst:
            if len(open_pos) >= slots: break
            if e["code"] in held: continue
            open_pos.append((e["resolve_date"], e["code"], e))
            held.add(e["code"]); taken.append(e)
    return taken

def report(label, filt, rank):
    taken = simulate(filt, rank)
    pool = [e for e in ev if filt(e)]
    w,n = wr(taken); r,_ = realized(taken)
    pnl = sum(POS*e["gain_at_resolve_pct"]/100 for e in taken)
    # 무작위 순서 20회 민감도
    rs_=[]
    for sd_ in range(20):
        t2 = simulate(filt, rank, seed=sd_)
        rs_.append(sum(POS*e["gain_at_resolve_pct"]/100 for e in t2))
    ann_tr = len(taken)/YEARS
    ann_pnl = pnl/YEARS
    print(f"{label:32s} | 후보풀 {len(pool):4d} → 실제체결 {len(taken):3d} ({100.0*len(taken)/max(1,len(pool)):4.0f}%) "
          f"| 승률 {w:5.1f}%(n{n:3d}) 기대값 {r:+5.2f}% | 9개월손익 {pnl/1e4:+8.0f}만원 "
          f"| 연환산 거래 {ann_tr:5.0f}회 손익 {ann_pnl/1e4:+8.0f}만원 (자본5천만 대비 {100*ann_pnl/(SLOTS*POS):+6.1f}%) "
          f"| 무작위순서 중앙 {s.median(rs_)/1e4:+7.0f}만원")
    return dict(label=label, taken=taken, pool=len(pool), pnl=pnl, ann_pnl=ann_pnl, wr=w, n=n)

print("슬롯 5개 · 1건 1,000만원 · 동일종목 중복보유 차단 · 슬롯 부족시 그날 거래대금 큰 순")
print("기간 180 스캔일(=0.72년) 실측 → 연환산")
print("="*175)
res=[]
res.append(report("S0 전체(무필터)",        lambda e: True,                     lambda e: -e["turnover_eok"]))
res.append(report("S1 상승국면",            lambda e: e["regime_up"],            lambda e: -e["turnover_eok"]))
res.append(report("S2 상승+VCP",           lambda e: e["regime_up"] and e["pattern"]=="VCP", lambda e: -e["turnover_eok"]))
res.append(report("S3 상승+VCP+거래대금상위50%", lambda e: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=0.5), lambda e: -e["turnover_eok"]))
res.append(report("S4 상승+VCP+거래대금상위25%", lambda e: e["regime_up"] and e["pattern"]=="VCP" and (e["to_pct"] is None or e["to_pct"]>=0.75), lambda e: -e["turnover_eok"]))
res.append(report("S4b 상승+거래대금상위25%",   lambda e: e["regime_up"] and (e["to_pct"] is None or e["to_pct"]>=0.75), lambda e: -e["turnover_eok"]))
res.append(report("S6 상승+VCP+그날 거래대금1위", lambda e: e["regime_up"] and e["pattern"]=="VCP" and e["to_rank"]==1, lambda e: -e["turnover_eok"]))
print("="*175)

print("\n[비교] 필터는 S1(상승국면)만, 슬롯 채우는 순서만 바꿔보기 — '거르기' vs '고르기'")
for lab, rk in [("거래대금 큰 순", lambda e: -e["turnover_eok"]),
                ("RS 높은 순",     lambda e: -e["rs"]),
                ("ATR 낮은 순",    lambda e: e["atr_pct"]),
                ("갭업 작은 순",    lambda e: e["gap_up_pct"]),
                ("종목코드 순(중립)", lambda e: e["code"])]:
    t=simulate(lambda e: e["regime_up"], rk)
    w,n=wr(t); r,_=realized(t)
    p=sum(POS*e["gain_at_resolve_pct"]/100 for e in t)
    print(f"   {lab:16s} 체결 {len(t):3d} 승률 {w:5.1f}% 기대값 {r:+5.2f}% 9개월손익 {p/1e4:+7.0f}만원 (연 {p/YEARS/1e4:+7.0f}만원)")

print("\n[비교] 무필터 + 순서만")
for lab, rk in [("거래대금 큰 순", lambda e: -e["turnover_eok"]),
                ("RS 높은 순",     lambda e: -e["rs"]),
                ("종목코드 순(중립)", lambda e: e["code"])]:
    t=simulate(lambda e: True, rk)
    w,n=wr(t); r,_=realized(t)
    p=sum(POS*e["gain_at_resolve_pct"]/100 for e in t)
    print(f"   {lab:16s} 체결 {len(t):3d} 승률 {w:5.1f}% 기대값 {r:+5.2f}% 9개월손익 {p/1e4:+7.0f}만원 (연 {p/YEARS/1e4:+7.0f}만원)")

print("\n[슬롯 회전 용량 계산]")
R=resolved(ev)
mh=s.mean(e["days_held"] for e in ev)
print(f"   평균 보유일 {mh:.1f}일 → 슬롯1개 연 회전 {250/mh:.1f}회 → 슬롯5개 연 용량 약 {5*250/mh:.0f}건")
print(f"   무필터 신호 발생량: 연 {len(ev)/YEARS:.0f}건  (용량의 {len(ev)/YEARS/(5*250/mh):.1f}배)")
