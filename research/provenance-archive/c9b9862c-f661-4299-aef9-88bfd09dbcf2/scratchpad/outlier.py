"""등가중 보유 수익의 집중도 / 이상치 점검"""
import json, pickle, statistics as st
from pathlib import Path
SP = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
P = pickle.load(open(SP / "panel.pkl", "rb"))
dates, rows, meta = P["dates"], P["rows"], P["meta"]
HOLD = [d for d in dates if d > "2025-11-26"]
def pr(c):
    cum, n = 1.0, 0
    for d in HOLD:
        r = rows[c].get(d)
        if not r or r[0] is None: continue
        cum *= 1 + r[0]/100; n += 1
    return ((cum-1)*100) if n else None
univ = json.loads((SP/"universe_20251126.json").read_text(encoding="utf-8"))
bt = json.loads((Path(r"C:\Users\hanul\playground\my-stock")/"public/data/backtest-volatility-pilot.json").read_text(encoding="utf-8"))
btc = sorted({e["code"] for e in bt["events"]})
def report(codes, label):
    v = sorted([(pr(c), c) for c in codes if pr(c) is not None], reverse=True)
    m = sum(x for x,_ in v)/len(v)
    print(f"\n[{label}] n={len(v)} 평균 {m:+.2f}% 중앙 {st.median([x for x,_ in v]):+.2f}%")
    print("  상위5:", [(meta[c]['name'], round(x)) for x,c in v[:5]])
    for k in (1,3,5,10):
        rest = [x for x,_ in v[k:]]
        print(f"   상위 {k:>2} 제외 -> 평균 {sum(rest)/len(rest):+.2f}%")
    xs=[x for x,_ in v]; kk=int(len(xs)*0.05)
    print(f"   절사평균(5%) {sum(sorted(xs)[kk:len(xs)-kk])/len(sorted(xs)[kk:len(xs)-kk]):+.2f}%")
    print(f"   >0 비율 {sum(1 for x in xs if x>0)/len(xs)*100:.1f}% · +100%초과 {sum(1 for x in xs if x>100)}종목")
report(list(univ), "① 유니버스 291")
report(btc, "② 백테스트 350")
# ②의 look-ahead 분해: 11/26 유니버스에 이미 있던 188 vs 나중 편입 162
report([c for c in btc if c in univ], "②-a 11/26에 이미 유니버스였던 188")
report([c for c in btc if c not in univ], "②-b 나중에 편입된 162(룩어헤드)")
# 데이터 이상치 확인
print("\n전종목 상위 이상치:")
v = sorted([(pr(c), c) for c in rows if "2025-11-26" in rows[c] and pr(c) is not None], reverse=True)[:6]
for x,c in v: print(f"  {meta[c]['name']} {c} {x:+.0f}% 시총 {rows[c]['2025-11-26'][2]}억")
