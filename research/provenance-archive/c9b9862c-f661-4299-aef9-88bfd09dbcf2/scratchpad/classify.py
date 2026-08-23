# -*- coding: utf-8 -*-
import sys, json, os, collections, statistics
SCR = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
sys.path.insert(0, SCR)
from lib import load, series, simulate

snap = json.load(open(os.path.join(SCR,"cand_hist.json"), encoding="utf-8"))
asofs = sorted(snap.keys())
sc = load("scorecard.json"); trades = sc["trades"]
fills = load("scorecard-fills.json")["fills"]
reg = {r["date"]: r for r in load("market-regime.json")["series"]}

# note lookup: (date, code) -> note
noteby = {}
for f in fills:
    if f["side"]=="buy":
        noteby.setdefault((f["date"], f["code"]), []).append(f.get("note") or "")

def prev_asof(d):
    prev = [a for a in asofs if a < d]
    return prev[-1] if prev else None

def lookup(code, d):
    """returns (asof_used, best_pattern_record) - best = entry_ready > detected > listed"""
    a = prev_asof(d)
    if a is None: return None, None, None
    day = snap[a]
    best = None; bestpat=None; listed=False
    for pat in ("VCP","3C","PP"):
        rec = day.get(pat,{}).get(code)
        if rec is None: continue
        listed = True
        rank = (2 if rec.get("entry_ready") else (1 if rec.get("detected") else 0))
        if best is None or rank > best[0]:
            best = (rank, rec); bestpat = pat
    if not listed: return a, None, None
    return a, best[1], bestpat

rows=[]
for t in trades:
    d = t["open_date"]; code=t["code"]
    a, rec, pat = lookup(code, d)
    # regime on buy date (use last available regime date <= d)
    rd = max([x for x in reg if x <= d], default=None)
    up = reg[rd]["up"] if rd else None
    piv = rec.get("pivot") if rec else None
    er  = bool(rec.get("entry_ready")) if rec else False
    det = bool(rec.get("detected")) if rec else False
    st  = rec.get("status") if rec else None
    buy = t["avg_buy"]
    dev = (buy/piv-1)*100 if piv else None
    rows.append(dict(code=code, name=t["name"], d=d, close=t["close_date"], buy=buy,
        net_won=t["net_won"], net_pct=t["net_pct"], gross_pct=t["gross_pct"], outcome=t["outcome"],
        asof=a, listed=(rec is not None), detected=det, entry_ready=er, status=st, pat=pat,
        pivot=piv, dev=dev, up=up, stop_viol=t.get("stop_violation"), hold=t["hold_days"],
        note=" / ".join(noteby.get((d,code),[]))))

json.dump(rows, open(os.path.join(SCR,"rows.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)

def agg(sel, label):
    n=len(sel); s=sum(r["net_won"] for r in sel)
    w=sum(1 for r in sel if r["outcome"]=="win")
    m=statistics.mean([r["net_pct"] for r in sel]) if sel else 0
    print(f"{label}: {n}건  승={w} 승률={100*w/n if n else 0:.1f}%  손익합={s:>12,.0f}원  평균={m:+.2f}%")

print("=== 전체 ===")
agg(rows,"63건")
print()
print("=== A. 리스트/검출 상태 ===")
agg([r for r in rows if not r["listed"]], "(a) 그날 후보 리스트에 아예 없음")
agg([r for r in rows if r["listed"] and not r["detected"]], "(b1) 리스트엔 있으나 패턴 미검출")
agg([r for r in rows if r["detected"] and not r["entry_ready"]], "(b2) 패턴 검출됐으나 entry_ready 아님")
agg([r for r in rows if r["entry_ready"]], "(정상) entry_ready 종목")
print()
print("=== B. 피벗 대비 매수가 (entry_ready 건만) ===")
er=[r for r in rows if r["entry_ready"] and r["dev"] is not None]
agg([r for r in er if r["dev"] < 0], "(c) 피벗 아래 선진입")
agg([r for r in er if 0 <= r["dev"] <= 3], "(정상) 피벗~+3%")
agg([r for r in er if r["dev"] > 3], "(d) 피벗 +3% 초과 추격")
print()
print("=== B'. 피벗 대비 (검출된 모든 건, entry_ready 아니어도 피벗 있으면) ===")
allp=[r for r in rows if r["pivot"] and r["detected"]]
agg([r for r in allp if r["dev"] < 0], "(c) 피벗 아래 선진입")
agg([r for r in allp if 0 <= r["dev"] <= 3], "피벗~+3%")
agg([r for r in allp if r["dev"] > 3], "(d) 피벗 +3% 초과 추격")
print()
print("=== C. 국면 ===")
agg([r for r in rows if r["up"] is False], "(e) 조정국면 진입")
agg([r for r in rows if r["up"] is True], "상승국면 진입")
print()
print("=== D. 청산 ===")
agg([r for r in rows if r["stop_viol"]], "(f) 손절선 하회 체결")
agg([r for r in rows if r["outcome"]=="win" and r["gross_pct"] < 20], "(g) 이익인데 +20% 전 조기청산")
agg([r for r in rows if r["outcome"]=="win" and r["gross_pct"] >= 20], "  +20% 이상에서 청산")
agg([r for r in rows if r["outcome"]=="loss" and r["gross_pct"] > -10], "(g') 손실인데 -10% 전 조기손절")
agg([r for r in rows if r["outcome"]=="loss" and r["gross_pct"] <= -10], "  -10% 이하에서 손절")
