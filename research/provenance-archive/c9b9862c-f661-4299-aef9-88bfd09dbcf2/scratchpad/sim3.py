# -*- coding: utf-8 -*-
import os, pickle, sys, random, statistics
from collections import defaultdict
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as S
from sim2 import sim_one, exit_date, VAR, SAMPLE, H
random.seed(21)
def dd(s): return date(int(s[:4]), int(s[5:7]), int(s[8:10]))

print("=" * 100)
print("[9] 이상치 민감도 — 상위 수익 절사 후에도 (d15)(d20)(f) 우위가 남나")
print("=" * 100)
print(f"{'규칙':<22}{'평균':>8}{'중앙값':>9}{'상위5% 절사평균':>16}{'상위10% 절사평균':>17}{'최대수익':>9}{'최대손실':>9}")
for nm, kw in VAR:
    rows = sorted(r[0] for r in (sim_one(e, H, **kw) for e in SAMPLE))
    n = len(rows)
    t5 = rows[:int(n * 0.95)]; t10 = rows[:int(n * 0.90)]
    print(f"{nm:<22}{sum(rows)/n:>8.2f}{statistics.median(rows):>9.2f}"
          f"{sum(t5)/len(t5):>16.2f}{sum(t10)/len(t10):>17.2f}{rows[-1]:>9.1f}{rows[0]:>9.1f}")

print()
print("=" * 100)
print("[10] 슬롯5 시뮬 — 같은날 후보 순서 무작위 300회 (평균 ± 표준편차)")
print("=" * 100)
ORDER0 = sorted(SAMPLE, key=lambda e: e["entry_date"])
d0 = ORDER0[0]["entry_date"]; d1 = max(exit_date(e, H) for e in ORDER0)
span = (dd(d1) - dd(d0)).days
byday = defaultdict(list)
for e in SAMPLE:
    byday[e["entry_date"]].append(e)
days_sorted = sorted(byday)
pre = {}
for nm, kw in VAR:
    pre[nm] = {id(e): sim_one(e, H, **kw) for e in SAMPLE}
REP = 300
print(f"{'규칙':<22}{'체결(평균)':>11}{'총손익 만원':>13}{'±sd':>9}{'연환산 만원':>13}{'승률':>7}{'손익비':>7}{'>0 비율':>9}")
for nm, kw in VAR:
    tot = []; ntk = []; wr = []; pr = []
    for rep in range(REP):
        held = []; pnl = 0.0; taken = 0; w = 0; wins = []; loss = []
        for dday in days_sorted:
            cands = byday[dday][:]
            random.shuffle(cands)
            held = [h for h in held if h[0] > dday]
            for e in cands:
                if len(held) >= 5 or any(h[1] == e["code"] for h in held):
                    continue
                r, k, why = pre[nm][id(e)]
                held.append((exit_date(e, k), e["code"]))
                pnl += r / 100 * 1000; taken += 1
                (wins if r > 0 else loss).append(r)
        tot.append(pnl); ntk.append(taken)
        wr.append(len(wins) / taken * 100)
        pr.append((sum(wins) / len(wins)) / abs(sum(loss) / len(loss)) if wins and loss else float('nan'))
    m = sum(tot) / REP
    print(f"{nm:<22}{sum(ntk)/REP:>11.0f}{m:>13.0f}{statistics.pstdev(tot):>9.0f}"
          f"{m*365/span:>13.0f}{sum(wr)/REP:>7.1f}{sum(pr)/REP:>7.2f}{sum(1 for t in tot if t>0)/REP*100:>8.0f}%")

print()
print("=" * 100)
print("[11] ②+⑥ 조합이 거래 단위로 얼마나 자주 뜨나 / 뜬 거래의 결말")
print("=" * 100)
ROWS = pickle.load(open(os.path.join(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad", "obs.pkl"), "rb"))
bytrade = defaultdict(list)
for r in ROWS:
    bytrade[(r["code"], r["entry_date"])].append(r)
fired = [k for k, v in bytrade.items() if any(x["v_heavy_volume_pullback"] and x["v_breakout_failure"] for x in v)]
print(f"보유 중 ②+⑥ 동시점등 경험 거래: {len(fired)}/{len(bytrade)} = {len(fired)/len(bytrade)*100:.1f}%")
first_k = [min(x["k"] for x in bytrade[k] if x["v_heavy_volume_pullback"] and x["v_breakout_failure"]) for k in fired]
print(f"  첫 점등 보유일차 중앙값 {statistics.median(first_k):.0f}일 (평균 {sum(first_k)/len(first_k):.1f})")
rem_at = [ [x for x in bytrade[k] if x["v_heavy_volume_pullback"] and x["v_breakout_failure"]][0]["rem"] for k in fired]
print(f"  첫 점등 시점의 '계속 보유 시 남은 수익' 평균 {sum(rem_at)/len(rem_at):+.2f}%  (중앙 {statistics.median(rem_at):+.2f}%)")
nofire = [k for k in bytrade if k not in set(fired)]
allrem = [x["rem"] for k in nofire for x in bytrade[k] if x["k"] == 1]
print(f"  (대조) 미점등 거래의 k=1 남은 수익 평균 {sum(allrem)/len(allrem):+.2f}%")
