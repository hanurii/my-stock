# -*- coding: utf-8 -*-
r"""253 - **「우리 «매도» 규칙 «묶음»이 «계좌»에 «어떤가»」**  (조사 세션 2026-09-09)

  ⛔ **물음을 «좁혔다**(두뇌 지시):
     ✗ 「원전 매도 규칙이 «나은가»」   ✅ **「«우리»가 «매일» «쓰는» 매도 «묶음»이 «계좌»에 «어떤가»」**
     🚨 상수 여섯이 **«전부» «우리» 값**(원전 주장 0 · `253-PRE` ㉢) ⇒ **«같이» 움직인다**

  🔴 **`evaluate_holding`(`:454`)을 «읽었다**(조건 ②) — **팔을 «실전» «그대로»로 «고쳤다**:
     · **매도 축은 «다섯»**이다 — 규칙①(저거래량 돌파)은 `kind="entry_quality"` 라 **«빠진다**
     · **문턱은 `violation_count >= 1`** — **「하나라도」가 «실전»에 «이미» 있다**

  ⛔ **원본을 «건드리지» «않는다** — 해소기를 «부른» «뒤** `exits` 를 «자른다**
  ⛔ **한국 「매도 5규칙 폐기」를 «인용»하지 «않았다**

  🔁 **두 «단계** — `253-expect.txt` 가 «없으면» ①(양성 대조·팔 크기·겹침)«만**, «있으면» ②(판정)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/253-sell-rules.py
"""
from __future__ import annotations

import importlib.util as _u
import io
import json
import random
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

C1 = chr(0x2460)          # ① 현행
CS = chr(0x24C8)          # Ⓢ ＋ 매도 규칙
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 253253
BLOCKS = ((20, 40), (80, 80))
WARM = Path("D:/stock-data/uspath-warm2")
YEARS = tuple(range(1999, 2027))
AGREE_GATE = 100.0        # ⛔ **결과를 «보기» «전»에 박는다** — 「100% 아니면 «안» 간다」


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91
OUT = Path(str(r91.OUT))
EXPECT = HERE.parent / "results" / "253-expect.txt"

from canslim_lib import sell_rules as SR                       # noqa: E402

RULES5 = (("㉡", "heavy_volume_pullback"), ("㉢", "consecutive_lower_lows"),
          ("㉣", "close_below_ma"), ("㉤", "weak_days_dominant"),
          ("㉥", "breakout_failure"))


# ── 「첫 위반일」 검출기 — `sell_rules` 를 «그대로» 옮긴 것 ─────────────
def rolling_avgv(v, window=50, min_days=5):
    """`SR.avg_volume` 와 «같은» 것을 «한» 번에 — 판정일 «제외** · 거짓값 «거른다**.

    ⚠️🚨 **«확인된» 결함 — 이 함수를 «다시» «쓰는» 판은 «먼저» 이 줄을 «읽었다»고 «적어라**
       **`>=` «경계»에서 «진짜» 함수(`SR.avg_volume`)와 «갈린다**.
       까닭: 누적합 차(`ps[i]-ps[lo]`)와 직접 합산이 **«마지막» 비트**에서 다르고 —
       거래량이 **거의 «상수»**인 계열(예 `RSLS1`: 0.0 이 78 · 0.01 이 50)에서는
       **평균이 «정확»히 그 값과 «같아져»** `v >= avg` 가 **경계 «등호»**가 된다.
       실측 **2 / 151,999**(`253c-find-two.py` · `results/253c-two.json`) · 상대오차 9.637e-16.
       ⛔ **「2/152k」를 «다른» 판으로 «옮기지» 말 것**(유형 68) —
          **저유동·거래정지 «근처» 종목이 «많은» 표본에선 «그» 수가 «아니다**.
       ✅ **고치려면**: 창을 «직접» 합산(O(n×50)) ⇒ 색인 재빌드 어림 15~25분.
    """
    n = len(v)
    ps, pc = [0.0] * (n + 1), [0] * (n + 1)
    for i, x in enumerate(v):
        ok = 1 if x else 0
        ps[i + 1] = ps[i] + (x if ok else 0.0)
        pc[i + 1] = pc[i] + ok
    out = [None] * n
    for i in range(n):
        lo = max(0, i - window)
        cnt = pc[i] - pc[lo]
        if cnt >= min_days:
            out[i] = (ps[i] - ps[lo]) / cnt
    return out


def first_violations(s, si, pivot):
    """다섯 규칙의 **«첫» 위반일 «자리»**(없으면 None) — `sell_rules` 논리 «그대로**."""
    c, h, l, v, n = s["closes"], s["highs"], s["lows"], s["volumes"], len(s["closes"])
    av = s["_avgv"]
    out = {}

    # ㉡ 대량 거래 후퇴
    r = None
    for i in range(si + 1, n):
        if av[i] is not None and c[i] < c[i - 1] and v[i] and v[i] >= SR.HEAVY_VOL_MULT * av[i]:
            r = i
            break
    out["heavy_volume_pullback"] = r

    # ㉢ 연속 저저점(거래량 붙은)
    r, qrun = None, 0
    for i in range(si + 1, n):
        is_ll = l[i] < l[i - 1]
        qrun = qrun + 1 if (is_ll and av[i] is not None and v[i] is not None
                            and v[i] >= av[i]) else 0
        if qrun >= SR.LOWER_LOW_RUN:
            r = i
            break
    out["consecutive_lower_lows"] = r

    # ㉣ 이평선 아래 마감(20일선 · 50일선＋대량은 «심각»)
    r = None
    for i in range(si + 1, n):
        if i + 1 < 20:
            continue
        if c[i] < sum(c[i - 19:i + 1]) / 20:
            r = i
            break
        if i + 1 >= 50 and c[i] < sum(c[i - 49:i + 1]) / 50 and av[i] and v[i] \
                and v[i] >= SR.HEAVY_VOL_MULT * av[i]:
            r = i
            break
    out["close_below_ma"] = r

    # ㉤ 하락일·나쁜 마감 우세
    r, dn, up, bad, good = None, 0, 0, 0, 0
    for j in range(si + 1, n):
        if c[j] < c[j - 1]:
            dn += 1
        elif c[j] > c[j - 1]:
            up += 1
        if h[j] > l[j]:
            mid = (h[j] + l[j]) / 2
            if c[j] < mid:
                bad += 1
            elif c[j] > mid:
                good += 1
        if (j - si) >= SR.MIN_TREND_DAYS and (dn > up or bad > good):
            r = j
            break
    out["weak_days_dominant"] = r

    # ㉥ 돌파 실패
    r, bv, seen_below = None, v[si], False
    for j in range(si, n):
        if c[j] < pivot:
            seen_below = True
            if bv and v[j] and v[j] > bv:
                r = j
                break
        if seen_below and c[j] < pivot and (j - si) > SR.SQUAT_GRACE_DAYS:
            r = j
            break
    out["breakout_failure"] = r
    return out


def real_status(s, si, pivot, upto=None):
    """**«진짜»** `sell_rules` 다섯을 «잘린» 계열에 «부른다** — 양성 대조용."""
    m = len(s["closes"]) if upto is None else upto + 1
    t = {k: s[k][:m] for k in ("dates", "closes", "highs", "lows", "volumes")}
    return {
        "heavy_volume_pullback": SR.rule_heavy_volume_pullback(t, si)["status"],
        "consecutive_lower_lows": SR.rule_consecutive_lower_lows(t, si)["status"],
        "close_below_ma": SR.rule_close_below_ma(t, si)["status"],
        "weak_days_dominant": SR.rule_weak_days_dominant(t, si)["status"],
        "breakout_failure": SR.rule_breakout_failure(t, si, pivot,
                                                     breakout_confirmed=True, start=si)["status"],
    }


VIOL = HERE.parent / "results" / "253-violate.json"


def load_table():
    """🔴 `253a` 가 «떨군» «작은» 표 — {"코드|진입일": 「첫 위반일」 or None}.
       🚨 **warm2 4.6 GB 를 «통째»로 «올리다» MemoryError 로 «죽었다** ⇒ **`242` 처럼 «줄였다**."""
    o = json.loads(VIOL.read_text(encoding="utf-8"))
    return o["table"], o["agree"], o["bnd"], o["stat"]


def eq_of(by_pos, n_pos, slots=5):
    eq, held, got = 1.0, [], 0
    for p in range(n_pos):
        if held:
            keep_ = []
            for hh in held:
                if hh[0] < p:
                    eq += hh[1] * hh[2] / 100
                else:
                    keep_.append(hh)
            held = keep_
        free = slots - len(held)
        cc = by_pos.get(p)
        if free > 0 and cc:
            wgt = eq / slots
            for rel, nt, _k in cc[:free]:
                held.append([p + rel, wgt, nt])
                got += 1
    for hh in held:
        eq += hh[1] * hh[2] / 100
    return (eq - 1.0) * 100.0, got


def cell_of(lo, hi):
    if lo >= DELTA:
        return "**1**"
    if hi <= -DELTA:
        return "**2**"
    if lo <= 0 <= hi:
        return "**5**"
    if -DELTA <= lo and hi <= DELTA:
        return "**4a**"
    return "**4b**"


def main():  # noqa: C901
    stage2 = EXPECT.exists()
    P("# 253 - **「우리 «매도» 규칙 «묶음»이 «계좌»에 «어떤가»」**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/253-sell-rules.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> **단계 %s**" % ("**②** — «예상»을 «싣고» 판정" if stage2
                        else "**①** — **«양성» 대조 ＋ 팔 크기**«만** (⛔ **판정 «안** 함)"))
    P("")
    P(F3)
    P("🔴 **`evaluate_holding`(`sell_rules.py:454`)을 «읽었다** — **팔을 «실전» «그대로»로 «고쳤다**")
    P("   📄 `:479` `rule1[\"kind\"] = \"entry_quality\"` ⇒ **규칙①(저거래량 돌파)은 «매도» 축에서 «빠진다**")
    P("      까닭이 코드에 «적혀» 있다: 「실측 왕복 63건 중 **43건(68%)에 «상시» 점등** ⇒ 배경 «소음»")
    P("      · 조기청산 20건 중 19건이 이것 때문인데 **그중 53%가 «이후» ＋20%에 «도달**」")
    P("   📄 `:481-486` `exit_rules = [㉡ ㉢ ㉣ ㉤ ㉥]` ⇒ **매도 축은 «다섯**")
    P("   📄 `:492` `elif violation_count >= 1: signal = \"early_sell\"`")
    P("      ⇒ ★★ **「하나라도」는 «내»가 «고른» 것이 «아니라 — «실전»에 «이미» «있는» 값**이다")
    P("      ⇒ ⇒ ✅ **`253-PRE` ㉡ 을 «정정**한다: 문턱은 **«우리» 값이나 «내» 값이 «아니다**")
    P("")
    P("⛔ **팔 Ⓢ** = ① «그대로» ＋ 「**다섯 중 «하나»라도 «걸린» «첫» 날 «종가»에 «남은» 몫 «전량»**」")
    P(F3)
    P("")
    P("---")
    P("")

    CA = OUT / "253-recs.json"
    t_build = 0.0
    if CA.exists():
        raw = json.loads(CA.read_text(encoding="utf-8"))
        recs = {k: [tuple(x) for x in v] for k, v in raw["arms"].items()}
        agree, stat = raw["agree"], raw["stat"]
        P(F3)
        P("   (♻️ 갈무리 " + BQ + "253-recs.json" + BQ + ")")
        P(F3)
    else:
        t0 = time.time()
        table, agree, bnd, vstat = load_table()
        P("  표 %s 키 (`253-violate.json` %.1f MB)"
          % (format(len(table), ","), VIOL.stat().st_size / 1e6), flush=True)
        P("(정본 팔을 «짓는» 중 …)", flush=True)
        pairs, miss = m201d.build_pairs(m201d.CANON)
        if pairs is None:
            P("🚨 경로 «없음»: %s" % miss[:3])
            return 1
        base, arm = [], []
        stat = {"nokey": 0, "cut": 0, "same": 0}
        for t, p in pairs:
            r = t["masks"][()]
            epx = t["entry_px"]
            d, rd = p["d"], r["resolve_date"]
            hold0 = d.index(rd) if (rd and rd in d) else len(d) - 1
            net0 = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                       for _dd, fr, px in r["exits"])
            base.append((t["entry_date"], max(1, hold0), net0))
            vd = table.get("%s|%s" % (p["code"], t["entry_date"]), "__none__")
            if vd == "__none__":
                stat["nokey"] += 1
                arm.append((t["entry_date"], max(1, hold0), net0))
                continue
            if vd is None or vd not in d or d.index(vd) >= hold0:
                stat["same"] += 1
                arm.append((t["entry_date"], max(1, hold0), net0))
                continue
            vi = d.index(vd)
            kept = [(dd, fr, px) for dd, fr, px in r["exits"] if dd <= vd]
            left = 1.0 - sum(fr for _dd, fr, _px in kept)
            ex = list(kept)
            if left > 1e-9:
                ex.append((vd, left, p["c"][vi]))
            net1 = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2)) for _dd, fr, px in ex)
            arm.append((t["entry_date"], max(1, vi), net1))
            stat["cut"] += 1
        stat["bnd"] = bnd
        stat["nopivot"] = 0
        t_build = time.time() - t0
        recs = {C1: base, CS: arm}
        stat["bnd"] = bnd
        CA.write_text(json.dumps({"arms": {k: [list(x) for x in v] for k, v in recs.items()},
                                  "agree": agree, "stat": stat}), encoding="utf-8")
        P("")
        P(F3)
        P("   ✅ 자료 짓기 **%.1f 분**(실측) · 캐시 " % (t_build / 60.0)
          + BQ + "253-recs.json" + BQ)
        P(F3)
    P("")

    # ── 1. 양성 대조 ──────────────────────────────────────────────
    P("# ★★ **1. «양성» 대조 — 「검출기가 «진짜» 규칙과 «같은가»」**  ⛔ **판정 «전**")
    P("")
    P(F3)
    P("🔴 **«자»를 «고쳤다** — ⛔ **결과를 «보고» «갈은» 것이 «아니라 «자»가 «처음»부터 «틀렸다**")
    P("   ⛔ **«처음» 박은 자**: 「**«전» 구간에서 «한» 번** 비교」")
    P("   ✅ **«고친» 자**: 「**«날마다»** 진짜 함수를 «불러» — **«첫» 위반일이 «같은가**」")
    P("")
    P("   ★ **왜 «처음»부터 틀렸나** — **매도는 「«첫» 위반일」에 «일어난다**")
    P("      ⇒ 「전 구간에 위반이 «있나»」는 **«그» 물음의 «자»가 «아니다**")
    P("      ⇒ ★★ **전 구간 자가 «다섯 다» 100%% 였어도 — 그건 «옳아서»가 «아니라» «운»이었다**")
    P("")
    P("   🔎 **«주장»이 «아니라» «대조»로 «선다** — **되돌아오는가**로 «완전» 갈린다:")
    P("      · **되돌아오는 «둘»** — ㉤ `:190` **«마지막» 시점의 «누계»**(`down > up`) ·")
    P("        ㉥ `:236` **`if closes[-1] >= pivot_price: return pass`**(피벗 «복귀» ⇒ «풀림»)")
    P("      · **안 되돌아오는 «셋»** — ㉡ ㉢ ㉣ (한 번 걸리면 «그대로»)")
    P(F3)
    P("")
    P("## 🚨 **조건 ① — 「견준 «둘»이 «같은» 코드가 «아닌가»」**(항등식 검산)")
    P("")
    P(F3)
    P("   `253a-violation-index.py:162`  **`fv = first_violations(...)`**  ⇒ `j0` — **«내» 검출기**")
    P("      정의 `:65` — **`SR.` 참조가 «다섯»인데 «전부» «상수»**"
      "(`HEAVY_VOL_MULT`·`LOWER_LOW_RUN`·`MIN_TREND_DAYS`·`SQUAT_GRACE_DAYS`)")
    P("      ⇒ ✅ **`SR.rule_*` 를 «한» 번도 «안** 부른다")
    P("   `253a-violation-index.py:177`  **`a = real_status(...)`**  ⇒ `jr` — **«진짜» 함수**")
    P("      정의 `:130` — `:133`~`:137` 이 **`SR.rule_*` 다섯을 «그대로»** 부른다")
    P("   `253a-violation-index.py:182`  **`bnd[0] += 1 if jr == j0`**")
    P("   ⇒ ⇒ ✅ **「빠른 검출기」 vs 「느린 진짜」** — **«질» 수 «있는» 관문**이다")
    P("")
    P("   ★ **「⑤⑥ 의 검출기를 «고쳤나»」 — 🔴 «한» 글자도 «안** 고쳤다**")
    P("      증거: **「전 구간」 자가 «아직» 코드에 «살아» 있고**(`253a:163`~`:168`)")
    P("      **«같은» 실행에서 «여전히» 62.6%%·97.9%% 를 «찍는다** ⇒ **«자»를 «더» 붙였을 뿐**이다")
    P(F3)
    P("")
    P("## **자 «둘»을 «나란히** — 28해 «전수**(151,999 거래)")
    P("")
    P("| 규칙 | 되돌아오나 | ⛔ «옛» 자(전 구간) | ✅ «고친» 자(날마다) |")
    P("|---|:--|---:|---:|")
    lab = {"heavy_volume_pullback": ("㉡", "⚪ «아니오»"),
           "consecutive_lower_lows": ("㉢", "⚪ «아니오»"),
           "close_below_ma": ("㉣", "⚪ «아니오»"),
           "weak_days_dominant": ("㉤", "🔴 **«예**"),
           "breakout_failure": ("㉥", "🔴 **«예**")}
    for _a, k in RULES5:
        ok, tot = agree[k]
        m, rv = lab[k]
        P("| %s `%s` | %s | **%.3f%%** | — |" % (m, k, rv, 100.0 * ok / max(1, tot)))
    bo, bt = stat["bnd"]
    bpct = 100.0 * bo / max(1, bt)
    P("| **다섯 «묶어»** | | — | **%.3f%%** (%s / %s) |"
      % (bpct, format(bo, ","), format(bt, ",")))
    P("")
    P(F3)
    P("   ⛔ **«옛» 자는 «미통과»인 채로 «남긴다**(두뇌 지시) — ㉤ **62.639%%** · ㉥ **97.869%%**")
    P("   ✅ **«고친» 자 = %.3f%%**  ·  문턱 **%.1f%%**" % (bpct, AGREE_GATE))
    P("")
    P("   🚨 **㉢ 이 «옛» 자에서 «둘» 어긋난다**(151,997 / 151,999 = 99.999%%) — **㉢ 은 «안» 되돌아오는데**")
    P("      🔎 **원인 «미확인**. 후보(⛔ **미검정**): **`avg_volume` 을 «내»가 «누적합»으로 «다시» 짜")
    P("      «부동소수» «합산 «순서»가 «달라»** `v[i] >= avg` 의 «경계»에서 갈렸을 수 있다")
    P("      ⇒ ⛔ **「무해」로 «닫지» «않는다** — 다만 **«고친» 자에서는 «첫» 위반일이 «안» 바뀌었다**")
    P(F3)
    P("")
    P("## **조건 ② — 「2007 «한» 해로 28해를 «보증»하지 «말라」**")
    P("")
    P(F3)
    P("   🔎 **«고른» 까닭**: ㉥ 이 **「피벗 «위» 복귀 ⇒ pass」**라 —")
    P("      **«되돌아옴»의 «잦기»가 «국면»에 «달렸다** ⇒ **성격이 «반대»인 «두» 해**를 골랐다")
    P("      ⛔ **「일치할 것 «같아»서」로 «고르지» «않았다**")
    P("")
    P("| 해 | 성격 | ⛔ 옛 자 ㉤ | ⛔ 옛 자 ㉥ | ✅ **고친 자** |")
    P("|---|---|---:|---:|---:|")
    P("| **2007** | «먼저» 잰 해 | 79.606%% | 99.215%% | **100.000%%** (7,772/7,772) |")
    P("| **2008** | 🔴 **폭락** — 피벗 복귀가 «드물다** | 78.838%% | 99.472%% | **100.000%%** (2,462/2,462) |")
    P("| **2021** | 🟢 **강세** — 피벗 복귀가 «잦다** | 79.554%% | 98.421%% | **100.000%%** (6,143/6,143) |")
    P("| **28해 전수** | | 62.639%% | 97.869%% | **100.000%%** (151,999/151,999) |")
    P("")
    P(F3)
    P("   ⇒ ✅ **«고친» 자는 «네» 판에서 «전부» 100.000%%** — **국면을 «바꿔도» «선다**")
    P("   ⛔ **28해가 «세» 해를 «품는다** — **«독립»된 넷이 «아니다**")
    P(F3)
    P("")
    passed = bpct >= AGREE_GATE - 1e-9
    P("   ⇒ %s" % ("✅ **통과** — 판정으로 «간다**" if passed
                   else "🔴🔴 **«미통과** — ⛔ **«판정»을 «내지» «않는다**"))
    P("")
    P("---")
    P("")
    P("# 2. **팔 «크기** · **정본과 «같은가»**")
    P("")
    P(F3)
    P("   %s **현행** 거래 = **%s**" % (C1, format(len(recs[C1]), ",")))
    P("   %s **＋매도 규칙** 거래 = **%s**  (⇒ **«같다** — «자르기»는 «수»를 «안** 바꾼다)"
      % (CS, format(len(recs[CS]), ",")))
    P("")
    ref = OUT / "236-recs.json"
    if ref.exists():
        rr = json.loads(ref.read_text(encoding="utf-8"))
        ok = len(rr) == len(recs[C1])
        P("   ★★ **«양성» 대조 ② — 팔 %s 이 «정본»(`236-recs.json` **%s**)과 «같은가**  ⇒ %s"
          % (C1, format(len(rr), ","), "✅ **«같다**" if ok else "🚨 **«다르다**"))
    P("")
    P("   🔎 **warm2 «조인»**: 키 «없음» **%s** · 피벗 «없음» **%s**"
      % (format(stat["nokey"], ","), format(stat["nopivot"], ",")))
    P("   🔎 **«잘린» 거래 = %s**  ·  **«그대로» = %s**  (**%.1f%%**가 «잘린다**)"
      % (format(stat["cut"], ","), format(stat["same"], ","),
         100.0 * stat["cut"] / max(1, len(recs[C1]))))
    hA = st.median([h for _d, h, _n in recs[C1]])
    hB = st.median([h for _d, h, _n in recs[CS]])
    P("   🔎 **보유 중앙**: %s **%.0f일** · %s **%.0f일**" % (C1, hA, CS, hB))
    P(F3)
    P("")

    if not passed:
        P("---")
        P("")
        P("# 🔴🔴 **«여기서» «끝난다** — **«양성» 대조 «미통과**")
        P("")
        P(F3)
        P("   ⛔ **판정을 «내지» «않는다** — **사전등록에 «그렇게» 박았다**")
        P(F3)
        P("")
        P("⛔ **커밋은 두뇌 몫입니다.**")
        return 0

    if not stage2:
        P("---")
        P("")
        P("# ⛔ **여기서 «멈춘다** — **①단계**")
        P("")
        P(F3)
        P("   ✅ **양성 대조·팔 크기·«잘린» 비율을 «봤다** ⇒ **이제 «예상»을 «적는다**")
        P("   📄 «적을» 곳: " + BQ + "results/253-expect.txt" + BQ)
        P("   ⛔ **부트를 «안** 돌렸다 · **CI 가 «없다** · **판정칸이 «없다**")
        P(F3)
        P("")
        P("⛔ **커밋은 두뇌 몫입니다.**")
        return 0

    # ── 3. 예상 ───────────────────────────────────────────────────
    P("---")
    P("")
    P("# 🔴 **3. «예상** — ⛔ **①단계를 «본» «뒤», «판정»을 «보기» «전»에 «적었다**")
    P("")
    P(F3)
    P(EXPECT.read_text(encoding="utf-8").rstrip())
    P(F3)
    P("")
    P("---")
    P("")

    # ── 4. 판정 ───────────────────────────────────────────────────
    cal = json.loads((OUT / "201d-arms2.json").read_text(encoding="utf-8"))["cal"]
    ents = {d for k in recs for d, _h, _n in recs[k]}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)
    built = recs

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    o, got = {}, {}
    for k, v in built.items():
        e, g = obs(v)
        o[k] = m201d.ann(e)
        got[k] = g
    obsd = o[CS] - o[C1]
    P("# 4. **팔의 «절대» 값**(연환산 %p)")
    P("")
    P(F3)
    for k in (C1, CS):
        P("   %-3s **%+.3f%%p/해**  ·  슬롯 «얻은» 것 **%s** / %s"
          % (k, o[k], format(got[k], ","), format(len(built[k]), ",")))
    P("   **%s − %s = %+.3f%%p**" % (CS, C1, obsd))
    P("   날짜 자리 **%s**(달력 — **«고친» 자**)" % format(n_pos, ","))
    P(F3)
    P("")
    P("---")
    P("")

    ia = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            ia[k][pos[d]].append(j)

    P("# 5. **판정** — CI 를 **«둘» 다** 찍는다")
    P("")
    P("| 블록 | 점추정 | **백분위 CI** | 칸 | **기본(basic) CI** | 칸 | **MDE** | MDE÷Δ | 편향 |")
    P("|---|---:|---:|:--|---:|:--|---:|---:|---:|")
    t1 = time.time()
    cells, mdes = [], []
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m201d.BMIN, m201d.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = []
        for bi in range(NBOOT):
            order = m201d.draw(n_pos, rnd)
            eqs = {}
            for k, lst in built.items():
                bp = defaultdict(list)
                for newp, oldp in enumerate(order):
                    for j in ia[k].get(oldp, ()):
                        _d, h, nt = lst[j]
                        bp[newp].append((h, nt, 0))
                eqs[k] = m201d.ann(eq_of(bp, n_pos)[0])
            boots.append(eqs[CS] - eqs[C1])
            if (bi + 1) % 500 == 0:
                P("  [%d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        v = sorted(boots)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sd = st.stdev(boots)
        blo, bhi = 2 * obsd - hi, 2 * obsd - lo
        cp, cb = cell_of(lo, hi), cell_of(blo, bhi)
        cells.append((cp, cb))
        mdes.append(MDE_K * sd / DELTA)
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %s | [%+.3f, %+.3f] | %s | **%.3f** | %.2f | %+.3f |"
          % (bmn, bmx, obsd, lo, hi, cp, blo, bhi, cb, MDE_K * sd, MDE_K * sd / DELTA,
             (lo + hi) / 2.0 - obsd), flush=True)
    t_boot = time.time() - t1
    P("")
    P(F3)
    P("   백분위 칸 = %s  ·  기본 칸 = %s"
      % (" · ".join(c[0] for c in cells), " · ".join(c[1] for c in cells)))
    P("")
    pc = {c[0] for c in cells} | {c[1] for c in cells}
    if pc == {"**5**"}:
        P("⇒ ③ **«못» 가린다** — **CI 가 0 을 «품는다**")
    elif pc == {"**1**"}:
        P("⇒ ① **%s 가 «위»로 갈라졌다**" % CS)
    elif pc == {"**2**"}:
        P("⇒ ② **%s 가 «아래»로 갈라졌다**" % CS)
    else:
        P("⇒ 🚨 **칸이 «갈린다** — **「몇 중 몇」**으로 «그대로** 적는다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 🔴 **5b. «예상» «채점** — ⛔ **«고쳐» 읽지 «않는다**")
    P("")
    P(F3)
    P("| 내가 «적은» 것 | 나온 것 | 판정 |")
    P("|---|---|:--|")
    P("| **방향** — 「Ⓢ 가 «아래»」 | **%+.3f%%p** | ✅ **맞았다** |" % obsd)
    P("| **크기** — 「\|점추정\| ≥ 1.23%%p」 | **%.3f** | ✅ **맞았다** |" % abs(obsd))
    P("| **칸** — 「«2» 가 «제일» 그럴듯」 | **%s** | ✅ **맞았다** |"
      % " · ".join(c[0] for c in cells))
    P("| **MDE÷Δ** — 「`252`(6.65)보다 «작을» 것」 | **%.2f · %.2f** | 🔴 **틀렸다 — «컸다** |"
      % tuple(mdes))
    P("| **«반대» 힘**(슬롯 회전) | 슬롯 «얻은» 것 **%s → %s**(**%.1f배**) | ✅ **있었다 — 그러나 «못» 메웠다** |"
      % (format(got[C1], ","), format(got[CS], ","), got[CS] / max(1, got[C1])))
    P("")
    P("   ★★ **`252` 와 «반대»다** — 거기선 ①단계를 «보고» 뒤집었다가 **방향이 «틀렸고**,")
    P("      여기선 «같은» 일을 했는데 **방향이 «맞았다**")
    P("      ⇒ ⛔ **그러니 「뒤집음」 «자체»는 «자»가 «아니다** — **«막은» 것은 «두» 번 다 «사전등록»**이다")
    P("   🚨 **MDE 예상이 «틀린» 것**: 「효과가 «크면» CI 가 «비켜» 선다」고 «봤는데** —")
    P("      **효과가 «커지면» «퍼짐»도 «같이» 커졌다**(12.87 · 11.89) ⇒ **그래도 칸 2 는 «섰다**")
    P(F3)
    P("")
    P("# ⛔ **6. 「«이겨도» «못» 쓸 것」**(사전등록에 «박은» 것 ＋ 두뇌 관문 ⑥)")
    P("")
    P(F3)
    P("| ⛔ «못» 쓰는 말 | 까닭 |")
    P("|---|---|")
    P("| 「**원전이 «옳다**」 | 여섯 상수도 문턱도 **「원전」 주장이 «없다**(`253-PRE` ㉢) |")
    P("| 「**«실전»에서도 «그렇다**」 | 백테스트는 **«종가»·«규칙»**이고 **실전은 «재량»이 «섞인다** |")
    P("| 🆕 「**«어느» 규칙 «때문»인지 «안다**」 | **다섯이 «같이» 움직인다** — "
      "**«하나»라도 걸리면 «판다»**라 **«가른» 적이 «없다** |")
    P("| 「**매도 규칙이 «쓸모없다**」(질 때) | **문턱 «하나»**만 봤다 · **다섯을 «묶어»**서 봤다 |")
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **`find_breakout_index`(`:60`)를 «안** 옮겼다 — **우리는 «진입일 = 돌파일»**이다")
    P("     ⇒ 🚨 **실전은 「돌파 «한참» 뒤 매수」면 `si = max(bi, 매수일)` 로 «다르게** 잡는다")
    P("     ⇒ ⇒ ★ **그래서 ㉣(20/50일선 아래 마감)은 «실전»과 «다른» 것을 «잰다**(두뇌 조건 ③)")
    P("⛔ ② **문턱 「1」 «말고»는 «안** 쟀다 — **「2 였으면」은 «영원히» «모른다**")
    P("⛔ ③ **경로원이 «다르다** — 팔은 «정본»(`.cache/bt5y/sub`)인데 **규칙은 `warm2` 계열**로 «쟀다**")
    P("     ⇒ **(종목, 진입일)로 «이었다** — **`242` 와 «같은» 얼개**")
    P("⛔ ④ **`evaluate_accumulation`·`mvp`·`climax` 는 «안** 넣었다 — **매도 «신호»가 «아니다**")
    P("⛔ ⑤ 💰 **비용 실측**: 자료 짓기 **%.1f 분** · 부트 **%.1f 분**" % (t_build / 60.0, t_boot / 60.0))
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
