"""같은 진입, 규칙(+20/-10) vs 그냥 끝까지 보유 — 선별능력 vs 청산규칙 분리"""
import json, sys, statistics as st
from pathlib import Path
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(MAIN / "scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"

bt = json.loads((MAIN / "public/data/backtest-volatility-pilot.json").read_text(encoding="utf-8"))
ev = bt["events"]
END = "2026-08-21"
rule, hold, pairs, miss = [], [], [], 0
for e in ev:
    s = ohlcv_matrix.get_series(e["code"])
    if not s: miss += 1; continue
    d, c = s["dates"], s["closes"]
    # 진입일 이후 마지막 종가
    idx = [i for i, x in enumerate(d) if x <= END and c[i]]
    if not idx: miss += 1; continue
    last = c[idx[-1]]
    if d.index(e["entry_date"]) if e["entry_date"] in d else -1:
        pass
    h = (last / e["entry_price"] - 1) * 100
    r = e["gain_at_resolve_pct"]
    if r is None: continue
    rule.append(r); hold.append(h); pairs.append((e, r, h))
print(f"짝지은 거래 {len(pairs)} (누락 {miss})")
print(f"규칙(+20/-10) 평균 {sum(rule)/len(rule):+.2f}% · 중앙 {st.median(rule):+.2f}%")
print(f"같은 진입 끝까지 보유 평균 {sum(hold)/len(hold):+.2f}% · 중앙 {st.median(hold):+.2f}%")
diff = [h - r for r, h in zip(rule, hold)]
print(f"차이(보유-규칙) 평균 {sum(diff)/len(diff):+.2f}%p · 중앙 {st.median(diff):+.2f}%p · 보유가 나은 비율 {sum(1 for x in diff if x>0)/len(diff)*100:.1f}%")
hs = sorted(hold); q = lambda p: hs[int(p*(len(hs)-1))]
print(f"보유 분포 P10 {q(.10):+.1f} P25 {q(.25):+.1f} P75 {q(.75):+.1f} P90 {q(.90):+.1f} max {hs[-1]:+.1f}")
# 절사평균(상하 5%)
def trim(x, p=0.05):
    xs = sorted(x); k = int(len(xs)*p)
    return sum(xs[k:len(xs)-k])/len(xs[k:len(xs)-k])
print(f"절사평균(5%) 규칙 {trim(rule):+.2f}% / 보유 {trim(hold):+.2f}%")
# 진입 시점(월)별
from collections import defaultdict
by = defaultdict(list)
for e, r, h in pairs: by[e["entry_date"][:7]].append((r, h))
print("\n월별  n  규칙평균  보유평균")
for k in sorted(by):
    v = by[k]; print(f"  {k} {len(v):>4}  {sum(a for a,_ in v)/len(v):+7.2f}%  {sum(b for _,b in v)/len(v):+7.2f}%")
