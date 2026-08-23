# 읽기 전용 재시뮬 — .cache/ohlcv/series 는 open(read) 만 한다. 쓰기/삭제 없음.
import json, os, sys, statistics, random
from pathlib import Path
ROOT = Path(r"C:\Users\hanul\playground\my-stock")
SER  = ROOT/".cache"/"ohlcv"/"series"
D = json.load(open(ROOT/"public/data/backtest-volatility-pilot.json", encoding="utf-8"))
EV = D["events"]

_cache={}
def series(code):
    if code not in _cache:
        p = SER/f"{code}.json"
        _cache[code] = json.load(open(p,encoding="utf-8")) if p.exists() else None
    return _cache[code]

def sim(s, b, base, target, stop):
    """simulate_pivot_trade 동일 재현. base=진입가(원 코드가 pivot 자리에 epx 를 넣음)."""
    highs, lows, closes, dates = s["highs"], s["lows"], s["closes"], s["dates"]
    T, S = base*(1+target/100), base*(1-stop/100)
    hi, lo = highs[b], lows[b]
    ht = hi is not None and hi >= T
    hs = lo is not None and lo <= S
    if ht and hs: return "ambiguous", b
    if ht:        return "win", b
    if hs:        return "ambiguous", b     # stop_on_breakout_day
    for i in range(b+1, len(closes)):
        hi, lo = highs[i], lows[i]
        ht = hi is not None and hi >= T
        hs = lo is not None and lo <= S
        if ht and hs: return "ambiguous", i
        if ht:        return "win", i
        if hs:        return "loss", i
    return "unresolved", len(closes)-1

rows=[]
miss=0
for e in EV:
    s = series(e["code"])
    if s is None or e["entry_date"] not in s["dates"]:
        miss+=1; continue
    b = s["dates"].index(e["entry_date"])
    base = e["entry_price"]
    r10, i10 = sim(s,b,base,20.0,10.0)
    r15, i15 = sim(s,b,base,20.0,15.0)
    rows.append(dict(e, r10=r10, i10=i10, r15=r15, i15=i15, b=b,
                     d10=i10-b, d15=i15-b,
                     last_close=s["closes"][-1],
                     c10=s["closes"][i10], c15=s["closes"][i15]))
print("이벤트", len(EV), "재현 실패(시계열/날짜 없음)", miss)
agree = sum(1 for r in rows if r["r10"]==r["result"])
print("stop -10%% 재시뮬 == 기록된 result :", agree, "/", len(rows), round(agree/len(rows)*100,1),"%")
from collections import Counter
print("불일치 상세:", Counter((r["result"],r["r10"]) for r in rows if r["r10"]!=r["result"]))
json.dump(rows, open(os.path.dirname(os.path.abspath(__file__))+"/rows.json","w",encoding="utf-8"), ensure_ascii=False)
