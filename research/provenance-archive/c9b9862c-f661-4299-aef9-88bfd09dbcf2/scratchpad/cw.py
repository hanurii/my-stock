"""시총가중 지수 재구성 + 상위 기여 종목 제거 (집중도)"""
import json, pickle
from pathlib import Path
SP = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
P = pickle.load(open(SP / "panel.pkl", "rb"))
dates, rows, meta = P["dates"], P["rows"], P["meta"]
HOLD = [d for d in dates if d > "2025-11-26"]

def cw_index(codes, exclude=set()):
    """일별: 전일 시총 가중 x 당일 등락률. 반환 (최종수익%, 종목별 기여도)"""
    lvl = 1.0
    contrib = {}
    for i, d in enumerate(HOLD):
        prev = dates[dates.index(d) - 1]
        num, den = 0.0, 0.0
        parts = []
        for c in codes:
            if c in exclude: continue
            rp = rows[c].get(prev); rc = rows[c].get(d)
            if not rp or not rc: continue
            cap = rp[2]; f = rc[0]
            if cap is None or f is None or cap <= 0: continue
            den += cap; parts.append((c, cap, f))
        if den <= 0: continue
        r = sum(cap * f / 100.0 for _, cap, f in parts) / den
        for c, cap, f in parts:
            contrib[c] = contrib.get(c, 0.0) + lvl * (cap / den) * (f / 100.0)
        lvl *= (1 + r)
    return (lvl - 1) * 100, contrib

ks = [c for c in rows if meta[c]["market"] == "KOSPI" and "2025-11-26" in rows[c]]
kq = [c for c in rows if meta[c]["market"] == "KOSDAQ" and "2025-11-26" in rows[c]]
allc = ks + kq
for label, codes in (("KOSPI 전종목", ks), ("KOSDAQ 전종목", kq), ("KOSPI+KOSDAQ", allc)):
    v, _ = cw_index(codes)
    print(f"{label:<14} n={len(codes):>5}  시총가중 {v:+.2f}%")

print("\n=== 집중도: KOSPI 시총가중 ===")
base, contrib = cw_index(ks)
top = sorted(contrib.items(), key=lambda kv: -kv[1])
print(f"기준 {base:+.2f}%   (기여 합계 {sum(contrib.values())*100:+.2f}%p)")
for c, v in top[:12]:
    print(f"  {meta[c]['name']:<12} {c}  기여 {v*100:+7.2f}%p  시총 {rows[c]['2025-11-26'][2]:,.0f}억")
for k in (1, 2, 3, 5, 10):
    ex = {c for c, _ in top[:k]}
    v, _ = cw_index(ks, ex)
    print(f"  상위 {k:>2}종목 제외 -> {v:+.2f}%  (원래 {base:+.2f}%, 차이 {v-base:+.1f}%p)")

print("\n=== 집중도: KOSPI+KOSDAQ 시총가중 ===")
base2, contrib2 = cw_index(allc)
top2 = sorted(contrib2.items(), key=lambda kv: -kv[1])
print(f"기준 {base2:+.2f}%")
for c, v in top2[:8]:
    print(f"  {meta[c]['name']:<12} {c} ({meta[c]['market']}) 기여 {v*100:+7.2f}%p")
for k in (1, 2, 3, 5, 10):
    ex = {c for c, _ in top2[:k]}
    v, _ = cw_index(allc, ex)
    print(f"  상위 {k:>2}종목 제외 -> {v:+.2f}%  (차이 {v-base2:+.1f}%p)")

# 상위 5 제외 후 나머지 KOSPI 종목 등가중도
print("\n=== 참고: KOSPI 종목 등가중(시총 무시) ===")
import statistics as st
def ew(codes):
    out = []
    for c in codes:
        cum, n = 1.0, 0
        for d in HOLD:
            rec = rows[c].get(d)
            if not rec or rec[0] is None: continue
            cum *= 1 + rec[0] / 100; n += 1
        if n: out.append((cum - 1) * 100)
    return sum(out) / len(out), st.median(out), len(out)
m, md, n = ew(ks); print(f"  KOSPI 등가중 평균 {m:+.2f}% 중앙 {md:+.2f}% (n={n})")
m, md, n = ew(kq); print(f"  KOSDAQ 등가중 평균 {m:+.2f}% 중앙 {md:+.2f}% (n={n})")
