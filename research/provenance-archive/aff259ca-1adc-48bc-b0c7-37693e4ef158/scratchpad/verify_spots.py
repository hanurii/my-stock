import json

def load(code):
    p = rf"C:\Users\hanul\playground\my-stock\.cache\ohlcv\series\{code}.json"
    return json.load(open(p, encoding="utf-8"))

def check(code, name, entry_date, fill, n=10):
    s = load(code)
    dts = s["dates"]
    i0 = dts.index(entry_date)
    win = range(i0, min(i0+n, len(dts)))
    lows = [s["lows"][i] for i in win]
    highs = [s["highs"][i] for i in win]
    closes = [s["closes"][i] for i in win]
    mae = (min(lows)/fill - 1) * 100
    mfe = (max(highs)/fill - 1) * 100
    r10 = (closes[-1]/fill - 1) * 100
    # relvol on entry day: vol / mean(prior 50)
    pv = s["volumes"][max(0, i0-50):i0]
    relvol = s["volumes"][i0] / (sum(pv)/len(pv))
    print(f"{name} entry {entry_date} fill {fill}: mae10 {mae:.2f} mfe10 {mfe:.2f} r10(last of {len(list(win))}d) {r10:.2f} relvol {relvol:.2f}")
    return s, i0

check("009150", "삼성전기", "2026-07-01", 2249561.12)
check("219130", "타이거일렉a", "2026-07-01", 62799.45)
s, i0 = check("044820", "코스맥스비티아이", "2026-08-10", 23499.96)
# resolve check: first day high >= fill*1.2
tgt = 23499.96 * 1.2
for i in range(i0, min(i0+5, len(s["dates"]))):
    print("  ", s["dates"][i], "H", s["highs"][i], ">=tgt?" , s["highs"][i] >= tgt)
check("029460", "케이씨", "2026-07-01", 35251.23)
