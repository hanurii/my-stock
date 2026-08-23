# -*- coding: utf-8 -*-
"""조건부 주문: '먼저 돌파(체결)되는 2개'를 사는 방식 = 무작위 2개와 같은가?
같은 entry_date 안에서만 비교. 체결 순서 대리변수 = 시가가 피벗 위로 열린 종목(gap>0)이 9시에 먼저 체결,
나머지(gap==0, 장중 피벗 터치)는 그 뒤. 동점은 무작위 타이브레이크 2000회 평균.
"""
import json, random, statistics as st
from collections import defaultdict

D = json.load(open('public/data/backtest-volatility-pilot.json', encoding='utf-8'))
EV = [e for e in D['events'] if e['result'] in ('win', 'loss')]
print("확정(win/loss) 표본:", len(EV), " win:", sum(e['result'] == 'win' for e in EV),
      " 전체승률: %.4f" % (sum(e['result'] == 'win' for e in EV) / len(EV)))

byday = defaultdict(list)
for e in EV:
    byday[e['entry_date']].append(e)
days_all = sorted(byday)
days = [d for d in days_all if len(byday[d]) >= 3]
print("entry_date 총 %d일, 후보 3개 이상인 날 %d일, 그 날들의 후보 %d건"
      % (len(days_all), len(days), sum(len(byday[d]) for d in days)))

# 그 날 무작위 2개의 기대승률 = 그날 승률 (날짜 균등가중)
rand_rate = st.mean(sum(x['result'] == 'win' for x in byday[d]) / len(byday[d]) for d in days)
print("무작위 2개(날짜균등) 기대승률: %.4f" % rand_rate)

def key_first(e):   # 먼저 체결되는 순서: gap>0 (시가 돌파) 먼저, gap 클수록 더 확실히 시초 체결
    return (-1 if e['gap_up_pct'] > 0 else 0, -e['gap_up_pct'])

def key_first_binary(e):  # 시초체결 여부만
    return (-1 if e['gap_up_pct'] > 0 else 0,)

def run(keyfn, label, N=2000, seed=7):
    rng = random.Random(seed)
    per_day_top, per_day_bot, per_day_rand = {}, {}, {}
    for d in days:
        c = byday[d]
        top_acc = bot_acc = 0.0
        for _ in range(N):
            sh = c[:]
            rng.shuffle(sh)                      # 동점 무작위 타이브레이크
            sh.sort(key=keyfn)
            top_acc += sum(x['result'] == 'win' for x in sh[:2]) / 2
            bot_acc += sum(x['result'] == 'win' for x in sh[-2:]) / 2
        per_day_top[d] = top_acc / N
        per_day_bot[d] = bot_acc / N
        per_day_rand[d] = sum(x['result'] == 'win' for x in c) / len(c)
    top = st.mean(per_day_top.values()); bot = st.mean(per_day_bot.values())
    # 부호검정
    w = sum(1 for d in days if per_day_top[d] > per_day_rand[d] + 1e-12)
    l = sum(1 for d in days if per_day_top[d] < per_day_rand[d] - 1e-12)
    t = len(days) - w - l
    from math import comb
    n = w + l
    if n:
        p_sign = min(1.0, 2 * sum(comb(n, k) for k in range(min(w, l) + 1)) / 2 ** n)
    else:
        p_sign = 1.0
    # 무작위 2개 뽑기 부트스트랩
    rng2 = random.Random(99)
    boot = []
    for _ in range(2000):
        boot.append(st.mean(sum(x['result'] == 'win' for x in rng2.sample(byday[d], 2)) / 2 for d in days))
    m = st.mean(boot); s = st.pstdev(boot)
    ge = sum(1 for b in boot if b >= top); le = sum(1 for b in boot if b <= top)
    p_boot = min(1.0, 2 * min(ge, le) / len(boot))
    lo, hi = sorted(boot)[50], sorted(boot)[1949]
    print("\n=== %s ===" % label)
    print("  먼저체결 2개 승률 : %.4f  (%d일 * 2건 = %d거래)" % (top, len(days), len(days) * 2))
    print("  무작위 2개        : %.4f" % rand_rate)
    print("  나중체결 2개      : %.4f" % bot)
    print("  차이(먼저-무작위) : %+.4f (%+.2f%%p)" % (top - rand_rate, (top - rand_rate) * 100))
    print("  부호검정: 먼저가 나은 날 %d / 못한 날 %d / 동률 %d  -> p=%.4f" % (w, l, t, p_sign))
    print("  부트스트랩(무작위2 2000회) 평균 %.4f sd %.4f 95%%[%.4f, %.4f] -> 양측 p=%.4f"
          % (m, s, lo, hi, p_boot))
    return top, bot

run(key_first, "체결순서 대리 = 시초돌파 우선 + 갭 큰 순")
run(key_first_binary, "체결순서 대리 = 시초돌파(갭>0)만 우선, 나머지는 완전 무작위")

# 갭 유형 자체 비교 (같은 날, 양쪽 다 존재하는 날만)
both = [d for d in days_all if any(x['gap_up_pct'] > 0 for x in byday[d]) and any(x['gap_up_pct'] == 0 for x in byday[d])]
g1 = st.mean(st.mean(x['result'] == 'win' for x in byday[d] if x['gap_up_pct'] > 0) for d in both)
g0 = st.mean(st.mean(x['result'] == 'win' for x in byday[d] if x['gap_up_pct'] == 0) for d in both)
print("\n같은날 직접비교(양쪽 다 있는 %d일): 시초돌파(갭>0) %.4f vs 장중돌파(갭0) %.4f  차이 %+.2f%%p"
      % (len(both), g1, g0, (g1 - g0) * 100))
ng = sum(1 for e in EV if e['gap_up_pct'] > 0)
print("갭>0 건수 %d / 갭=0 건수 %d" % (ng, len(EV) - ng))
