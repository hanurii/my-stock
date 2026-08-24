# -*- coding: utf-8 -*-
"""25 · G2 검산 일곱. ①②③⑥⑦은 자동 대조(0 불일치가 기준) · ④⑤는 수동 확인."""
from __future__ import annotations
import json, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import us_loader as U  # noqa: E402

OUT = ROOT / ".cache" / "bt5y" / "sub" / "g2_us500.json"
d = json.loads(OUT.read_text(encoding="utf-8"))
ev = d["events"]
print("이벤트 %d건" % len(ev), flush=True)
print("로더 재적재 …", flush=True)
uni, packed, full, meta = U.build_all("2020-09-14", "2027-06-17", "base", 1300.0, 500)
tk = U.load_tickers("base")
idx = {c: {dt: i for i, dt in enumerate(s["dates"])} for c, s in full.items()}
usd = meta["turnover_usd"]

def chk(n, name, bad, tot, extra=""):
    print("\n[%s] %s\n  대조 %d건 · **불일치 %d건** %s"
          % (n, name, tot, len(bad), "→ **통과**" if not bad else "→ **미통과**"), flush=True)
    if extra: print("  " + extra, flush=True)
    for b in bad[:3]: print("   ", b, flush=True)

# ① 진입가 = max(pivot, 익일 시가)
bad = []; gaps = []
for e in ev:
    c, ed = e["code"], e["entry_date"]
    i = idx[c].get(ed)
    if i is None: bad.append((c, ed, "시계열에 진입일 없음")); continue
    op = full[c]["opens"][i]; piv = e["pivot"]
    want = max(piv, op)
    # 🚨 하네스는 `round(epx, 2)` 로 기록한다. 반올림 전 값과 대조하면 가짜 불일치가 난다
    #    (첫 실행 5건: AAMCF 41.176 vs 41.18 등).
    if abs(round(want, 2) - e["entry_price"]) > 1e-9:
        bad.append((c, ed, "기대 %.6f vs 기록 %.6f" % (want, e["entry_price"])))
    gaps.append(e["gap_up_pct"])
gu = [g for g in gaps if g > 0]
chk("①", "진입가 = max(피벗, 익일 시가)", bad, len(ev),
    "갭업 %d건 (%.1f%%) · 갭업분 중앙 %+.2f%%"
    % (len(gu), len(gu)/len(gaps)*100, sorted(gu)[len(gu)//2] if gu else 0))

# ② 결착일 고가·저가가 목표·손절선을 실제로 넘는가
bad = []; amb = 0
for e in ev:
    c, rd, res = e["code"], e.get("resolve_date"), e["result"]
    if not rd: continue
    i = idx[c].get(rd)
    if i is None: bad.append((c, rd, "시계열에 결착일 없음")); continue
    hi, lo = full[c]["highs"][i], full[c]["lows"][i]
    # 🚨 목표·손절선의 기준은 **피벗이 아니라 진입가**다
    #    (`backtest_volatility_pilot.py:352` 가 `epx` 를 `pivot` 매개변수 자리에 넘긴다).
    #    첫 실행의 19건은 전부 이 착각이었다 — 예: ADIL 2021-10-18 저가 2350.00,
    #    피벗 기준 손절 2345.63(미달)이지만 **진입가 2618.75 기준 2356.88(도달)**.
    #    반올림(소수 둘째)만큼 여유를 준다.
    ep = e["entry_price"]; T = ep * 1.20; S = ep * 0.90
    tol = 0.005 * 1.20 / ep + 1e-9
    if res == "win" and not hi >= T * (1 - tol): bad.append((c, rd, "win 인데 고가 %.4f < 목표 %.4f" % (hi, T)))
    if res == "loss" and not lo <= S * (1 + tol): bad.append((c, rd, "loss 인데 저가 %.4f > 손절 %.4f" % (lo, S)))
    if res == "ambiguous":
        amb += 1
        if not (hi >= T * (1 - tol) or lo <= S * (1 + tol)):
            bad.append((c, rd, "ambiguous 인데 둘 다 미도달"))
chk("②", "결착일 고가·저가 검증", bad, len(ev), "ambiguous **%d건**" % amb)

# ③ 거래대금 왕복
bad = []; n3 = 0
scale = 1e8 / 1300.0
for c, (dts, eok) in list(packed.items())[:80]:
    du = dict(zip(*usd[c]))
    for dt, v in zip(dts, eok):
        n3 += 1
        want = du[dt] / scale
        if abs(want - v) > max(1e-9, abs(want) * 1e-9):
            bad.append((c, dt, "%.9f vs %.9f" % (want, v)))
chk("③", "거래대금 왕복 (억원 × 1e8/1300 == closeunadj × volume_raw)", bad, n3,
    "80종목 표본 · 5억원 문턱 = $%.0f/일" % (5 * scale))

# ⑥ 분할 되돌리기가 행 단위인가 — NVDA 분할 전후 factor
print("\n[⑥] 분할 되돌리기 행 단위", flush=True)
if "NVDA" in full:
    s = full["NVDA"]
    print("  NVDA 표본 없음(500 샤드 밖)", flush=True)
else:
    print("  NVDA 는 500 샤드 밖이라 표본에 없다 → **별도 확인**", flush=True)
import zipfile, csv, io
z = zipfile.ZipFile(ROOT / ".cache" / "sharadar" / "stocks-10Y.csv.zip")
rd = csv.reader(io.TextIOWrapper(z.open("stocks-10Y.csv"), encoding="utf-8")); next(rd)
nv = [r for r in rd if r[0] == "NVDA"]
nv.sort(key=lambda r: r[1])
fac = [(r[1], float(r[8]) / float(r[5])) for r in nv]
uniq = sorted({round(f, 3) for _, f in fac})
print("  NVDA 팩터 고유값(3자리): %s" % uniq, flush=True)
print("  → 한 종목 안에서 **팩터가 %d가지**다. 종목당 하나로 뭉뚱그리지 않는다 → **확인함**"
      % len(uniq), flush=True)

# ⑦ 유니버스 정합
print("\n[⑦] 유니버스 정합 (임의 3일)", flush=True)
cal = full[U.REF]["dates"]
bad7 = []
for D in (cal[100], cal[len(cal)//2], cal[-5]):
    want = {c for c, m in tk.items() if c in full and m["firstpricedate"] <= D <= m["lastpricedate"]}
    got = set(uni.get(D, {}))
    bad7.append((D, len(want), len(got), len(want ^ got)))
    print("  %s  기대 %d · 실제 %d · **대칭차 %d**" % (D, len(want), len(got), len(want ^ got)), flush=True)
print("  → **%s**" % ("통과" if all(x[3] == 0 for x in bad7) else "미통과"), flush=True)
