"""벤치마크 공정성: 등가중 바이앤홀드 / 시총가중 지수 / 집중도"""
import json, pickle, statistics as st
from pathlib import Path
SP = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
P = pickle.load(open(SP / "panel.pkl", "rb"))
dates, rows, meta = P["dates"], P["rows"], P["meta"]
D0 = "2025-11-26"
HOLD = [d for d in dates if d > D0]        # 매수 익일부터의 등락률을 연쇄
print("보유 거래일", len(HOLD), HOLD[0], "~", HOLD[-1])

def path_ret(code):
    """fltRt 연쇄 누적수익 경로. returns (최종수익%, 마지막관측일, 관측일수)"""
    r = rows.get(code)
    if not r: return None, None, 0
    cum, last, n = 1.0, None, 0
    for d in HOLD:
        rec = r.get(d)
        if rec is None: continue          # 상폐/거래정지로 결측 -> 그 날은 건너뜀
        f = rec[0]
        if f is None: continue
        cum *= (1 + f / 100.0); last = d; n += 1
    return (cum - 1) * 100, last, n

def ew_stats(codes, label, delist_mode="last"):
    rets, alive, dead, missing = [], 0, [], 0
    for c in codes:
        v, last, n = path_ret(c)
        if v is None or n == 0:
            missing += 1; continue
        if last != HOLD[-1]:
            dead.append((c, meta.get(c, {}).get("name"), round(v, 1), last))
            if delist_mode == "zero": v = -100.0
        else:
            alive += 1
        rets.append(v)
    m = sum(rets) / len(rets)
    med = st.median(rets)
    print(f"\n[{label}] n={len(rets)} (생존 {alive} / 중도소멸 {len(dead)} / 데이터없음 {missing}) "
          f"상폐처리={delist_mode}")
    print(f"  등가중 평균수익 {m:+.2f}% · 중앙값 {med:+.2f}% · 승률(>0) {sum(1 for x in rets if x>0)/len(rets)*100:.1f}%")
    rs_ = sorted(rets)
    q = lambda p: rs_[int(p*(len(rs_)-1))]
    print(f"  분포 P10 {q(.10):+.1f} / P25 {q(.25):+.1f} / P75 {q(.75):+.1f} / P90 {q(.90):+.1f} / 최대 {rs_[-1]:+.1f} / 최소 {rs_[0]:+.1f}")
    return m, med, rets, dead

# ── 1) 매매 유니버스(RS80+, 거래대금5억+) 291종목 ─────────────────────────
univ = json.loads((SP / "universe_20251126.json").read_text(encoding="utf-8"))
print("=" * 70)
m1, md1, r1, dead1 = ew_stats(list(univ), "①-a 매매 유니버스 291 등가중 보유", "last")
m1z, _, _, _ = ew_stats(list(univ), "①-b 동일(상폐=-100% 가정)", "zero")
print("  중도소멸 종목:", dead1[:10])
# 8관문 통과분만
tt = [c for c, v in univ.items() if v["tt_pass"]]
ew_stats(tt, f"①-c 그중 8관문 통과 {len(tt)}종목", "last")
# 시장별
for mk in ("KOSPI", "KOSDAQ"):
    ew_stats([c for c, v in univ.items() if v["market"] == mk], f"①-d {mk} {sum(1 for v in univ.values() if v['market']==mk)}종목", "last")

# ── 2) 백테스트 등장 종목 350 ─────────────────────────────────────────────
bt = json.loads(Path(r"C:\Users\hanul\playground\my-stock\public\data\backtest-volatility-pilot.json").read_text(encoding="utf-8"))
codes_bt = sorted({e["code"] for e in bt["events"]})
print("=" * 70)
print("백테스트 등장 종목", len(codes_bt))
m2, md2, r2, dead2 = ew_stats(codes_bt, "② 백테스트 등장 350종목 등가중 보유", "last")
ew_stats(codes_bt, "②-b 동일(상폐=-100%)", "zero")
inuniv = [c for c in codes_bt if c in univ]
print(f"  이 중 11/26 유니버스에도 있던 종목 {len(inuniv)} / {len(codes_bt)}")

# ── 전체 평균종목(등가중 시장) 참고 ───────────────────────────────────────
evalable = json.loads((SP / "evaluable_20251126.json").read_text(encoding="utf-8"))
print("=" * 70)
ew_stats(list(evalable), f"참고 평가대상 전체 {len(evalable)}종목(거래대금5억+, RS무관) 등가중", "last")
allc = [c for c in rows if D0 in rows[c]]
ew_stats(allc, f"참고 시장 전종목 {len(allc)} 등가중", "last")

json.dump({"univ_ret": r1, "bt_ret": r2}, open(SP / "ew_rets.json", "w"))
