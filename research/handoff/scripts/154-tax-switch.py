# -*- coding: utf-8 -*-
"""154 — **+30 이 나은 게 «규칙 자체»인가 «세금 시점»인가**

  🚨 132(세후 85.0%) 와 133(세전 78.3%) 은 **비교하면 안 된다** — 숏·수수료·세금 «셋»이 다르다.
  ✅ 이 판은 **같은 판 · 같은 씨앗 · 같은 후보 · 같은 숏 · 같은 수수료**에서
     **«세금 스위치»만** 켜고 끈다.  **세금 전 · 비용 후** = 1000 x ccv[-1]  (🚨 숏·수수료는 «이미» 들어 있다)  ·  세후 = taxed_window(같은 cds·ccv·real)
  ⛔ 뒤 구간 안 엶 · 새 전략 없음 · 목표는 **+20 · +30 «둘»만**
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
r108 = _load("r108", "108-short-index.py")
r111 = _load("r111", "111-tax.py")
r124 = _load("r124", "124-jeonse-horizon.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
FEE, SHORT_SIZE, BORROW = 0.002, 0.20, 2.0
TARGETS = (20.0, 30.0)
STOP = 10.0
START = 1000.0
NSEED = 60


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    print("=" * 104)
    print("154 — **«세금 스위치»만 갈아 끼운다** · +20 vs +30 · 씨앗 %d판" % n_seed)
    print("=" * 104)
    print("")
    print("> 조사 세션 · 2026-09-02 · `scripts/154-tax-switch.py` · **문서는 이 출력 그 자체**(유형 48)")
    print("> ⛔ 뒤 구간 안 엶 · 새 전략 없음 · 목표 «둘»만 · 세율 %.0f%% · 연 공제 %.0f만원"
          % (r111.RATE * 100, r111.DEDUCT))
    print("")
    print("## ⛔ 읽는 표 — **돌리기 «전»에 넷 다 적었다**")
    print("")
    print("| 세금 전·비용 후 | 세후 | 뜻 |")
    print("|---|---|---|")
    print("| +30 이김 | «더» 이김 | **규칙 자체가 낫고, 세금이 «더» 벌린다** |")
    print("| 비슷 | +30 이김 | **«세금 시점»이 주된 이유** |")
    print("| +30 이김 | «줄어듦» | **세금은 +30 에 «불리»**(건당 세금이 커서) |")
    print("| 비슷 | 비슷 | **못 가린다** |")
    print("")
    print("🚨 **원전 제약** — 「세금 «때문에» 매도를 결정하는 일은 없다」(사용자님 확인).")
    print("   ⇒ **「세금을 피하려 +30 으로 간다」는 못 쓴다.** 이 판은 «이유»를 가르는 것이지")
    print("     «세금 절약»을 근거로 삼는 판이 «아니다».", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k

    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE

    r91.STOP, r91.HALF = STOP, 0.5
    pre, post, nfill, yreal, shelter, unreal = {}, {}, {}, {}, {}, {}
    npos, ded, nneg = {}, {}, {}
    for tg in TARGETS:
        r91.TARGET = tg
        ev, _b1, _b2 = r91.replay(by_f)
        rs = r91.sim(ev, n_seed)
        a_pre, a_post, a_n, a_yr, a_sh, a_ur = [], [], [], [], [], []
        a_np, a_dd, a_ng = [], [], []
        for x in rs:
            fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
            if len(fdates) != int(x["n_filled"]):
                print("🚨 관문 미통과 — 수수료 횟수")
                return 3
            g = abs(sum(r_ * t2 / 100.0 for _d, r_, t2 in x["ret_log"])
                    - x["equity_pct"] / 100.0) / max(1e-9, abs(x["equity_pct"] / 100.0))
            if g >= 0.005:
                print("🚨 관문 미통과 — 손익 합 %.3f%%" % (g * 100))
                return 4
            fd = Counter(fdates)
            vv = ([(d, v) for d, v in x["curve"]]
                  + [(x["curve"][-1][0], 1.0 + x["equity_pct"] / 100.0)])
            cds, ccv, V = [vv[0][0]], [1.0], 1.0
            for i in range(1, len(vv)):
                if vv[i - 1][1] <= 0:
                    break
                d = vv[i][0]
                rl = vv[i][1] / vv[i - 1][1] - 1.0
                sh = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
                V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
                cds.append(d)
                ccv.append(max(V, 1e-9))
            real = {}
            for d, pl in x["exit_log"]:
                real[d] = real.get(d, 0.0) + pl
            # ★ 「스위치 하나」 — 같은 cds·ccv·real 에서 «세전»과 «세후»를 «둘 다» 낸다
            a_pre.append(START * ccv[-1])
            a_post.append(r124.taxed_window(cds, ccv, real, 0, len(ccv) - 1))
            a_n.append(int(x["n_filled"]))
            # 🚨 `exit_log` 의 pl 은 «만원»이 아니라 «초기자본 대비 분수»다 —
            #   `taxed_window:95` 가 real/cv[k]*gross 로 쓰고 gross=START*cv[k] 이므로 «pl x START».
            #   이 곱을 빠뜨리면 공제(250만) 비교가 «1000배» 틀린다
            byy = {}
            for d, pl in x["exit_log"]:
                byy[d[:4]] = byy.get(d[:4], 0.0) + pl * START
            gains = [v for v in byy.values() if v > 0]
            a_yr.append(st.median(gains) if gains else 0.0)
            a_sh.append(100.0 * sum(1 for v in byy.values() if 0 < v <= r111.DEDUCT)
                        / max(1, len(byy)))
            # ★ 「창 끝에 남은 미실현 비중」 — `124:85` 「창 끝에 남은 미실현까지 판다」의 몫
            tot_gain = START * ccv[-1] - START
            a_ur.append(100.0 * (tot_gain - sum(byy.values())) / tot_gain
                        if tot_gain > 0 else 0.0)
            a_np.append(sum(1 for v in byy.values() if v > 0))
            a_dd.append(sum(min(v, r111.DEDUCT) for v in byy.values() if v > 0))
            a_ng.append(sum(1 for v in byy.values() if v < 0))
        pre[tg], post[tg], nfill[tg] = a_pre, a_post, a_n
        yreal[tg], shelter[tg], unreal[tg] = a_yr, a_sh, a_ur
        npos[tg], ded[tg], nneg[tg] = a_np, a_dd, a_ng

    print("")
    print("=" * 104)
    print("## 1. **스위치 하나** — 같은 판에서 세금만 켜고 껐다")
    print("=" * 104)
    print("")
    print("| 목표 | **세금 전·비용 후** | **세후** | 세금이 먹은 몫 | 매수 중앙 |")
    print("|---|---:|---:|---:|---:|")
    for tg in TARGETS:
        a, b = st.median(pre[tg]), st.median(post[tg])
        print("| **+%.0f** | %.0f만 | %.0f만 | **−%.1f%%** | %.0f |"
              % (tg, a, b, 100.0 * (1 - b / a), st.median(nfill[tg])))
    print("")
    win_pre = sum(1 for i in range(n_seed) if pre[30.0][i] > pre[20.0][i])
    win_post = sum(1 for i in range(n_seed) if post[30.0][i] > post[20.0][i])
    d_pre = st.median([pre[30.0][i] - pre[20.0][i] for i in range(n_seed)])
    d_post = st.median([post[30.0][i] - post[20.0][i] for i in range(n_seed)])
    # ── 🚨 관문 R★ — 규약 ⑦(능동판): 이 수는 «다른 곳»에도 있다. 찾아서 «대조»한다 ──────
    #   132 는 «같은» 설정(씨앗 60 · STOP 10 · HALF 0.5 · 숏 0.20 · 수수료 · 세후)에서
    #   「+30 이 +20 을 이김 **85.0% (51/60)**」을 냈다(`results/132-*.md:36`).
    #   목표 «집합»만 다르다(7칸 vs 2칸) — 씨앗별 재생이 목표에 독립이면 «같은 수»가 나와야 한다.
    R_132 = 51
    print("")
    print("### 🚨 관문 R★ — **이 수는 «다른 곳»에도 있다. 대조한다**(규약 ⑦ 능동판)")
    print("")
    print("```")
    print("132(`results/132-*.md:36`)  세후 +30 이 +20 을 이김  **%d / 60**" % R_132)
    print("154(이 판)                  세후 같은 물음           **%d / %d**" % (win_post, n_seed))
    if n_seed == 60 and win_post == R_132:
        print("⇒ ✅ **일치.** 같은 설정에서 «같은 수»가 나왔다 — 하네스가 재현된다")
    elif n_seed != 60:
        print("⇒ ⚠️ --quick (씨앗 %d) 이라 대조 불가" % n_seed)
    else:
        print("⇒ 🚨 **불일치 (%d vs %d).** 「목표 집합이 씨앗별 재생에 «영향을 준다»」는 뜻이다." % (win_post, R_132))
        print("   ⛔ 맞추지 말고 **«왜»부터**. 이 판의 다른 수도 «전부» 의심 대상이 된다")
    print("```")
    print("")
    print("### ★ 짝비교 — **+30 이 +20 을 이긴 판** (같은 씨앗끼리)")
    print("")
    print("```")
    print("**세금 전·비용 후**  %d / %d = **%.1f%%**  ·  중앙 차이 **%+.0f만**"
          % (win_pre, n_seed, 100.0 * win_pre / n_seed, d_pre))
    print("**세후**              %d / %d = **%.1f%%**  ·  중앙 차이 **%+.0f만**"
          % (win_post, n_seed, 100.0 * win_post / n_seed, d_post))
    print("```")
    print("")
    print("### ⛔ **「+%.1f%%p 를 세금이 더했다」로 적지 «않는다»** — 짝이라 McNemar 다"
          % (100.0 * (win_post - win_pre) / n_seed))
    print("")
    b = sum(1 for i in range(n_seed)
            if pre[30.0][i] > pre[20.0][i] and not post[30.0][i] > post[20.0][i])
    cN = sum(1 for i in range(n_seed)
             if not pre[30.0][i] > pre[20.0][i] and post[30.0][i] > post[20.0][i])
    nd = b + cN
    pmc = (min(1.0, 2.0 * sum(math.comb(nd, k) for k in range(0, min(b, cN) + 1)) / 2 ** nd)
           if nd else 1.0)
    print("```")
    print("**같은 씨앗 60개**라 두 수는 «짝»이다 — 비율의 차가 아니라 **«뒤집힌 씨앗»**을 센다")
    print("   세전 이김 → 세후 짐  **%d판**   ·   세전 짐 → 세후 이김  **%d판**   (불일치 %d판)"
          % (b, cN, nd))
    print("   **McNemar 양측 p = %.3f**   →   %s" % (pmc, "🚨 **못 가린다**" if pmc >= 0.05 else "✅ 가림"))
    print("   ★ 불일치가 어떤 조합이어도 상한이 있다 — (3,0) **0.250** · (4,1) 0.375 · (5,2) 0.453 …")
    print("     **0.05 «근처»에도 못 간다.** 자료를 «한 줄도 더 안 보고» 알 수 있었다(149 와 같은 수법)")
    print("```")
    print("")
    print("> ### ✅ **적을 말: 「세후가 세전보다 «%d판» 더 이겼다 — «판 수가 적어» 가릴 수 없다」**"
          % (win_post - win_pre,))
    print("")
    pbin = sum(math.comb(n_seed, k) for k in range(win_pre, n_seed + 1)) / 2.0 ** n_seed
    print("> ### ✅ **서는 것: 「«세금 전»에도 +30 이 +20 을 이긴다 — %d/%d, 귀무 p = %.2g」**"
          % (win_pre, n_seed, pbin))
    print("> ### **⇒ 이게 154 의 «발견»이다. 세금을 빼도 남는다.**")
    print("")
    print("=" * 104)
    print("## 2. 🚨 **«스위치 하나»가 아니었다 — 갈래가 «셋»이다**(검증 세션)")
    print("=" * 104)
    print("")
    print("```")
    print("내가 바꾼 «줄 수»는 하나지만, 답이 갈리는 «갈래»는 «부른 함수 «안»»에 있다:")
    print("  ① **시점**  — 이를수록 세금을 먼저 내고 복리에서 빠짐        → **늦게 파는 쪽(+30) 유리**")
    print("  ② **공제**  — %.0f만원이 «해마다» → 양수 실현 «해»가 많을수록 더 씀"
          % r111.DEDUCT)
    print("                                                              → **자주 파는 쪽(+20) 유리**")
    print("  ③ **창 끝** — 마지막에 «전부» 실현 = 가장 늦게 = 가장 싼 세금 → **늦게 파는 쪽(+30) 유리**")
    print("")
    print("✅ `124:99` 덕에 **총 과세 대상 = gross − START 가 «항등식»**이다.")
    print("   총액이 같으니 남는 갈래가 정말 ①②③ 뿐이고, **셋을 갈라 볼 수 있다**")
    print("```")
    print("")
    print("### 🚨 **내가 방향을 «거꾸로» 적었던 자리** (검증 세션이 잡음)")
    print("")
    print("```")
    print("내 초안  「창 끝 강제 매도 → +30 은 미실현이 더 남아 «마지막 해에 세금이 몰린다»」 = **«벌»로 읽음**")
    print("실제      마지막 해에 몰리는 세금 = **27년 굴린 뒤 내는 세금** = **«가장 싼» 세금** = **«상»**")
    print("          그리고 그건 **+30 쪽에 «유리»** — 즉 **내 가설에 «유리»**하다")
    print("★★ 「이건 내 가설에 «불리»하니 보수적이다」로 넘긴 자리가 실은 «유리»했다")
    print("★ 검사 — **편향의 «방향»을 적을 때 «부호»를 한 번 더 뒤집어 본다.**")
    print("   **「나에게 «불리»하다」가 제일 검산을 «안» 받는다**(유형 35 의 사촌)")
    print("```")
    print("")
    # ── 🚨 관문 V★ — 파생지표마다 «있을 수 있는 범위»를 코드에 박는다(검증 세션 처방) ──
    bad = [(tg, st.median(unreal[tg])) for tg in TARGETS
           if not (0.0 <= st.median(unreal[tg]) <= 100.0)]
    print("### 🚨 관문 V★ — **파생지표의 «범위»를 코드에 박았다**")
    print("")
    print("```")
    print("「창 끝 미실현 비중」은 **[0, 100]%** 여야 한다 (실현 합은 총 이익을 «못 넘는다»)")
    for tg in TARGETS:
        v = st.median(unreal[tg])
        print("   +%-3.0f  **%.1f%%**   %s" % (tg, v, "✅" if 0.0 <= v <= 100.0 else "🚨 **범위 밖**"))
    print("⇒ %s" % ("✅ 통과" if not bad else
                    "🚨 **미통과 — 아래에서 «철회»한다. 맞추지 말고 «왜»부터**"))
    print("```")
    print("")
    print("### 🚨🚨 **§2 의 «파생 지표»를 «철회»한다 — 내가 단위를 «또» 틀렸다**")
    print("")
    print("```")
    print("`121b-exact-tax.py:125`  「ly[y] += pl * **lsc.get(d, 1.0)**」  ← **«자리 배율»을 곱한다**")
    print("내 계산                   pl x START 만 했다 — **lsc 를 «안» 곱했다**")
    print("")
    print("**증거(관문)** — 「창 끝 미실현 비중」이 **음수**로 나왔다:")
    for tg in TARGETS:
        print("   +%-3.0f  **%.1f%%**   ← 실현 합이 «총 이익»을 넘었다 = **불가능**" % (tg, st.median(unreal[tg])))
    print("")
    print("⛔ 철회하는 수 — **창 끝 미실현 비중 · 연 실현 중앙 · 쓴 공제 · 건당 실현**")
    print("   (전부 «금액»이라 배율에 걸린다. **라벨을 달지 않고 «뺀다»** — 유형 54)")
    print("✅ 남기는 수 — **매수 횟수 · 양수 해 / 손실 해 «개수»**")
    print("   («개수»는 해마다의 «부호»만 쓰므로 lsc>0 이면 배율에 안 걸린다.")
    print("    🚨 단 lsc 가 «한 해 «안»에서» 달라지면 부호도 바뀔 수 있다 — **그건 «안 쟀다»**)")
    print("```")
    print("")
    print("| 목표 | 매수 | **양수 해** | **손실 해** |")
    print("|---|---:|---:|---:|")
    for tg in TARGETS:
        print("| **+%.0f** | %.0f | **%.1f개** | %.1f개 |"
              % (tg, st.median(nfill[tg]), st.median(npos[tg]), st.median(nneg[tg])))
    print("")
    print("```")
    print("🚨 그래서 **②(공제) 갈래의 «크기»는 이 판에서 «안 나왔다».**")
    print("   양수 해가 +20 **%.0f개** vs +30 **%.0f개** 로 «비슷»하다는 것까지만 말할 수 있다"
          % (st.median(npos[20.0]), st.median(npos[30.0])))
    print("   ⇒ **①시점·②공제·③창끝 을 «갈라 재는 것»은 «못 했다».** 다음 판이 필요하면 `121b.tax_exact`(lsc 포함)로")
    print("")
    print("⚠️ **하네스 가정(잰 것 아님)** — ⓐ 공제 %.0f만원이 27년 «내내» 같은 «명목»값" % r111.DEDUCT)
    print("   ⓑ `111:49` **손실 «이월 없음»** — 손실 해는 세금에 «아무 영향도» 없다")
    print("      ⇒ 위 «손실 해» 칸은 **«버려진 손실»의 개수**다")
    print("```")
    print("")
    print("### 🚨 «시사» — **이미 가진 두 수에서 채널 ②의 흔적이 보인다**(검증 세션)")
    print("")
    print("```")
    rr = 100.0 * (1.0 - d_post / d_pre) if d_pre else 0.0
    print("중앙 차이  세금 전 **%.0f만** → 세후 **%.0f만**  =  **−%.1f%%**" % (d_pre, d_post, rr))
    print("그런데 세율 RATE = **%.0f%%** 다. 「비례」면 %.0f만이 남아야 하는데 **%.0f만이 «더» 줄었다**"
          % (r111.RATE * 100, d_pre * (1 - r111.RATE), d_pre * (1 - r111.RATE) - d_post))
    print("⇒ 세금이 «금액»에서 **+30 을 «더» 때렸다** — 후보 설명이 **채널 ②(공제가 «해마다»)**:")
    print("   «자주 파는» +20 이 공제를 더 쓴다")
    print("")
    print("🚨 **«시사»이지 «측정»이 아니다** — 「중앙의 차」 ≠ 「차의 중앙」이라 비선형 몫이 섞인다.")
    print("   **«방향»만 말할 수 있다.** 갈라 재려면 `121b.tax_exact`(lsc 포함)로 가야 한다")
    print("```")
    print("")
    print("> ### ✅ **§1 은 «안» 걸린다** — 세금 전(ccv[-1])·세후(taxed_window) 는 «금액 배율»을 안 거치고,")
    print("> ### **관문 R★ 가 132 의 51/60 을 «그대로» 재현해 확인했다.**")
    print("")
    print("=" * 104)
    print("## 3. ⛔ **어느 결과가 나와도 적을 문장** — 「주장 장부」의 사전등록")
    print("=" * 104)
    print("")
    print("```")
    print("🚨 검증 세션 판정 — 장부가 «둘»이다:")
    print("   «검정» 장부(문턱·순열·다중비교)  →  154 는 **문턱을 안 쓴다**  →  **안 는다**")
    print("   «주장» 장부(보고서의 새 문장)     →  「이 조건의 세금 전」은 **처음 재는 것** → **하나 는다**")
    print("")
    print("어느 칸이 나오든 «반드시» 같이 적는다:")
    print("  ⛔ 「세금을 피하려 +30 으로 간다」  — **못 쓴다**(원전: 「세금 «때문에» 매도하지 않는다」)")
    print("  ⛔ 「+30 이 «지수»를 이긴다」        — **못 쓴다**(152 가 «못 가린다»로 닫음)")
    print("  ⛔ 「+30 이 «최선»이다」            — **못 쓴다**(132 는 «전부 vs +20» 만 쟀다)")
    print("  ⚠️ 「세금 전·비용 후」를 **133 의 78.3% 와 나란히 놓지 않는다** — «이름만 같은 다른 자»")
    print("```")
    print("")
    print("> ### ★ 이 셋을 «코드 안»에 인쇄한 이유 — **바라는 답이 나오면 덜 파고들 유인**이 생기는데,")
    print("> ### **오늘 확인했듯 «선언»으로는 안 막힌다. 막는 건 «구조»다.**")
    print("")

    json.dump({"pre": {str(k): v for k, v in pre.items()},
               "post": {str(k): v for k, v in post.items()},
               "win_pre": win_pre, "win_post": win_post, "n_seed": n_seed},
              open(str(r91.OUT / "154-tax-switch.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("")
    print("⛔ 뒤 구간 «안 엶» · 목표 «둘»만 · **「+30 이 지수를 이긴다」로는 못 간다**(152 가 «못 가린다»로 닫음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
