# -*- coding: utf-8 -*-
"""같은-entry_date 안에서 atr_pct 낮은 순 상위2 vs 무작위2 vs 상위(높은)2 검정."""
import json, math, random, itertools
from collections import defaultdict

random.seed(20260822)

PATH = r"C:\Users\hanul\playground\my-stock\public\data\backtest-volatility-pilot.json"
d = json.load(open(PATH, encoding="utf-8"))
ev = [e for e in d["events"] if e["result"] in ("win", "loss")]
print("resolved(win/loss) events:", len(ev), "| excluded:", len(d["events"]) - len(ev))

by_date = defaultdict(list)
for e in ev:
    by_date[e["entry_date"]].append(e)

dates_all = sorted(by_date)
dates = [dt for dt in dates_all if len(by_date[dt]) >= 3]
print("all entry_dates:", len(dates_all), "| dates with >=3 candidates:", len(dates))
print("candidates on those dates:", sum(len(by_date[dt]) for dt in dates))

# 동점 확인 (경계에서 atr_pct 같은 값이 얼마나 되나)
tie_boundary = 0
for dt in dates:
    xs = sorted(e["atr_pct"] for e in by_date[dt])
    if xs[1] == xs[2]:
        tie_boundary += 1
    ys = sorted((e["atr_pct"] for e in by_date[dt]), reverse=True)
    if ys[1] == ys[2]:
        tie_boundary += 0
print("상위2 경계 동점 날짜 수:", tie_boundary)


def pick_stat(key, reverse):
    """각 날짜에서 key 기준 2개 선택. 동점은 모든 조합 평균(가중)으로 처리."""
    wins = 0.0
    n = 0
    diffs = []
    per_date = []
    for dt in dates:
        cands = by_date[dt]
        vals = [e[key] for e in cands]
        outs = [1.0 if e["result"] == "win" else 0.0 for e in cands]
        order = sorted(range(len(cands)), key=lambda i: (-vals[i] if reverse else vals[i]))
        # 경계 동점 처리: 2번째 자리 값과 같은 값들 사이에서 평균
        v2 = vals[order[1]]
        strict = [i for i in order if (vals[i] > v2 if reverse else vals[i] < v2)]
        tied = [i for i in order if vals[i] == v2]
        need = 2 - len(strict)
        sel_w = sum(outs[i] for i in strict) + need * (sum(outs[i] for i in tied) / len(tied))
        day_rate = sum(outs) / len(outs)
        wins += sel_w
        n += 2
        diffs.append(sel_w / 2.0 - day_rate)
        per_date.append((dt, len(cands), sel_w, day_rate))
    return wins / n * 100, diffs, per_date, wins, n


top_rate, top_diffs, top_pd, top_w, top_n = pick_stat("atr_pct", reverse=False)   # 저변동 2개
bot_rate, bot_diffs, bot_pd, bot_w, bot_n = pick_stat("atr_pct", reverse=True)    # 고변동 2개

# 무작위 2개의 기대값 = 그날 전체 승률의 (날짜 균등) 평균
rand_rate = sum(sum(1 for e in by_date[dt] if e["result"] == "win") / len(by_date[dt]) for dt in dates) / len(dates) * 100
pool_rate = sum(1 for dt in dates for e in by_date[dt] if e["result"] == "win") / sum(len(by_date[dt]) for dt in dates) * 100

print()
print("=== 승률 (같은날 상위2 설계) ===")
print(f"저변동 상위2 : {top_rate:.1f}%  ({top_w:.1f}/{top_n})")
print(f"무작위2 기대 : {rand_rate:.1f}%  (날짜균등 그날승률 평균)")
print(f"고변동 하위2 : {bot_rate:.1f}%  ({bot_w:.1f}/{bot_n})")
print(f"[참고] 해당 날짜 전체 풀 승률: {pool_rate:.1f}%")

# --- 부호검정 ---
def sign_test(diffs, label):
    pos = sum(1 for x in diffs if x > 1e-12)
    neg = sum(1 for x in diffs if x < -1e-12)
    zer = len(diffs) - pos - neg
    m = pos + neg
    if m == 0:
        return 1.0, pos, neg, zer
    k = min(pos, neg)
    p = 2 * sum(math.comb(m, i) for i in range(0, k + 1)) / (2 ** m)
    p = min(1.0, p)
    print(f"{label}: 유리한 날 {pos} / 불리한 날 {neg} / 무승부 {zer}  → sign test p={p:.4f}")
    return p, pos, neg, zer

print()
print("=== 부호검정 (날짜별: 선택2 승률 - 그날 승률) ===")
p_sign_top, tp, tn, tz = sign_test(top_diffs, "저변동 상위2")
p_sign_bot, bp, bn, bz = sign_test(bot_diffs, "고변동 하위2")
print(f"저변동 평균 날짜별 차이: {sum(top_diffs)/len(top_diffs)*100:+.2f}%p")
print(f"고변동 평균 날짜별 차이: {sum(bot_diffs)/len(bot_diffs)*100:+.2f}%p")

# --- 부트스트랩: 각 날짜에서 무작위 2개 뽑기 2000회 ---
B = 2000
outs_by_date = {dt: [1 if e["result"] == "win" else 0 for e in by_date[dt]] for dt in dates}
boot = []
for _ in range(B):
    w = 0
    for dt in dates:
        o = outs_by_date[dt]
        w += sum(random.sample(o, 2))
    boot.append(w / (2 * len(dates)) * 100)
boot.sort()
mean_b = sum(boot) / B
ge = sum(1 for b in boot if b >= top_rate - 1e-9)
le = sum(1 for b in boot if b <= top_rate + 1e-9)
p_boot_top = 2 * min(ge, le) / B
p_boot_top = min(1.0, max(p_boot_top, 1.0 / B))
ge_b = sum(1 for b in boot if b >= bot_rate - 1e-9)
le_b = sum(1 for b in boot if b <= bot_rate + 1e-9)
p_boot_bot = min(1.0, max(2 * min(ge_b, le_b) / B, 1.0 / B))

print()
print(f"=== 부트스트랩 무작위2 x {B}회 ===")
print(f"무작위 승률 분포: 평균 {mean_b:.2f}%, 2.5%={boot[int(.025*B)]:.2f}%, 97.5%={boot[int(.975*B)]:.2f}%, 최소={boot[0]:.2f}%, 최대={boot[-1]:.2f}%")
print(f"저변동 상위2 {top_rate:.2f}% → 양측 p={p_boot_top:.4f} (>= {ge}/{B}, <= {le}/{B})")
print(f"고변동 하위2 {bot_rate:.2f}% → 양측 p={p_boot_bot:.4f}")

print()
print("=== 단조성 ===")
print(f"저변동2 {top_rate:.1f}%  vs  무작위 {rand_rate:.1f}%  vs  고변동2 {bot_rate:.1f}%")
print("monotonic(저변동>무작위>고변동):", top_rate > rand_rate > bot_rate)

# 참고: 전체 풀 (달력 착시 있는 잘못된 설계)
lo = sorted(ev, key=lambda e: e["atr_pct"])
q = len(lo) // 4
lo_wr = sum(1 for e in lo[:q] if e["result"] == "win") / q * 100
hi_wr = sum(1 for e in lo[-q:] if e["result"] == "win") / q * 100
print()
print("[참고 - 무효설계] 전체풀 ATR 하위25pct 승률 {:.1f}pct, 상위25pct 승률 {:.1f}pct (달력 착시 포함)".format(lo_wr, hi_wr))

from collections import Counter
print("후보수 분포(>=3인 날):", sorted(Counter(len(by_date[dt]) for dt in dates).items()))
print("선택된 거래 수: 저변동2 =", top_n)

# --- 직접 짝비교: 같은 날 저변동2 vs 고변동2 ---
pairs = [(t[2], b[2]) for t, b in zip(top_pd, bot_pd)]
pos = sum(1 for a, b in pairs if a > b)
neg = sum(1 for a, b in pairs if a < b)
zer = len(pairs) - pos - neg
m = pos + neg
import math as _m
k = min(pos, neg)
p_pair = min(1.0, 2 * sum(_m.comb(m, i) for i in range(k + 1)) / (2 ** m)) if m else 1.0
print()
print("=== 같은날 저변동2 vs 고변동2 직접 짝비교 ===")
print("저변동 우세 {}일 / 고변동 우세 {}일 / 동일 {}일 -> sign test p={:.4f}".format(pos, neg, zer, p_pair))

# --- 수익률 축 (승률 말고 실현손익) ---
def mean_gain(pd_list, key, reverse):
    tot = 0.0; n = 0
    for dt in dates:
        c = sorted(by_date[dt], key=lambda e: (-e["atr_pct"] if reverse else e["atr_pct"]))[:2]
        for e in c:
            tot += e["gain_at_resolve_pct"]; n += 1
    return tot / n
g_top = mean_gain(top_pd, "atr_pct", False)
g_bot = mean_gain(bot_pd, "atr_pct", True)
g_all = sum(e["gain_at_resolve_pct"] for dt in dates for e in by_date[dt]) / sum(len(by_date[dt]) for dt in dates)
print()
print("=== 거래당 실현수익 (해당 85일) ===")
print("저변동2 {:+.2f}pct / 전체(무작위 기대) {:+.2f}pct / 고변동2 {:+.2f}pct".format(g_top, g_all, g_bot))

# --- 견고성: 후보 4개 이상인 날만 ---
dates4 = [dt for dt in dates if len(by_date[dt]) >= 4]
def rate_sub(ds, reverse):
    w = 0; n = 0
    for dt in ds:
        c = sorted(by_date[dt], key=lambda e: (-e["atr_pct"] if reverse else e["atr_pct"]))[:2]
        w += sum(1 for e in c if e["result"] == "win"); n += 2
    return w / n * 100, n
r4t, n4 = rate_sub(dates4, False)
r4b, _ = rate_sub(dates4, True)
r4rand = sum(sum(1 for e in by_date[dt] if e["result"] == "win") / len(by_date[dt]) for dt in dates4) / len(dates4) * 100
print()
print("=== 견고성: 후보 4개 이상인 {}일만 ===".format(len(dates4)))
print("저변동2 {:.1f}pct / 무작위 {:.1f}pct / 고변동2 {:.1f}pct (거래 {}건)".format(r4t, r4rand, r4b, n4))

# --- ATR 값 자체 분포 ---
import statistics
allatr = [e["atr_pct"] for dt in dates for e in by_date[dt]]
selt = [e["atr_pct"] for dt in dates for e in sorted(by_date[dt], key=lambda x: x["atr_pct"])[:2]]
selb = [e["atr_pct"] for dt in dates for e in sorted(by_date[dt], key=lambda x: -x["atr_pct"])[:2]]
print()
print("ATR pct 중앙값 - 저변동2 {:.2f} / 전체 {:.2f} / 고변동2 {:.2f}".format(
    statistics.median(selt), statistics.median(allatr), statistics.median(selb)))
