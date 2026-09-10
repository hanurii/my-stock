# -*- coding: utf-8 -*-
r"""244 - **「매매 «한» 번당」 — «단서»**  (조사 세션 2026-09-09)

  사전등록: results/244-PRE.md  (⛔ **판마다가 «아니라» «한» 번**)
  🔴 «사용자» 결정: **「계좌가 «판정» · 거래당은 «단서»」** — **«둘»이 «어긋나면» «계좌»를 «따른다**

  ⛔ **«쓰지» «않을» 말**: 「가려졌다」·「칸 1/2/4a/4b/5」·「판정」·「낫다/나쁘다」
  ✅ **«쓸» 말**: 「거래의 «질»이 «바뀌었다/«안» 바뀌었다」·「«방향»은 ○○ 쪽」·「«단서»」

  자 = **날짜별 «짝»차이의 «평균»**(`16:50` 꼴) · 문턱 **±0.5%p**(M16-2 · `16:50`·`10:33`)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/244-per-trade.py
"""
from __future__ import annotations

import importlib.util as _u
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

C1 = chr(0x2460)
THR = 0.5          # M16-2 동등성 폭 — «우리»가 「거래당」 자리에서 «이미» 쓴 문턱
MDE_K = 2.8016
NBOOT, SEED = 2000, 244244
BLOCKS = ((20, 40), (80, 80))


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m234 = _load("m234", "234-rejudge.py")
OUT = m234.OUT
J = m234.J


def draw(n, rnd, bmn, bmx):
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(bmn, bmx)
        a = rnd.randint(0, n - 1)
        LL = min(L, n - tot)
        for j in range(LL):
            out.append((a + j) % n)
        tot += LL
    return out


# ── «더» 붙이는 팔 (234 REG 밖) ────────────────────────────────────────
def arms_201d():
    d = J("201d-arms2.json")["arms"]
    return ({k: [tuple(x) for x in v] for k, v in d.items()},
            [(chr(0x211D), chr(0x211D), C1)])


def arms_236():
    r = J("236-recs.json")
    base = [(x[0], x[1], x[2]) for x in r]
    arm = [(x[0], x[1], x[2]) for x in r if x[3] <= 1.5]
    return {C1: base, chr(0x24BC): arm}, [(chr(0x24BC), chr(0x24BC), C1)]


def arms_242():
    r = J("242-recs.json")
    z = J("242-gap.json")["flag"]
    flag = {tuple(k.split("|", 1)): v for k, v in z.items()}
    base = [(x[0], x[1], x[2]) for x in r]
    arm = [(x[0], x[1], x[2]) for x in r if not flag.get((x[0], x[3]), False)]
    return {C1: base, chr(0x24BC): arm}, [(chr(0x24BC), chr(0x24BC), C1)]


def arms_237():
    m237 = _load("m237", "237-ftd.py")
    allow, _ds, _nf, _nc = m237.build_allow()
    r = J("236-recs.json")
    base = [(x[0], x[1], x[2]) for x in r]
    arm = [(x[0], x[1], x[2]) for x in r if allow.get(x[0], True)]
    return {C1: base, chr(0x24BB): arm}, [(chr(0x24BB), chr(0x24BB), C1)]


EXTRA = {"201d": (arms_201d, "201d-rs-threshold"), "236": (arms_236, "236-chase-width"),
         "237": (arms_237, "237-ftd"), "242": (arms_242, "242-gap-history")}


def per_trade(built, ka, kb):
    """날짜별 «짝»차이의 «평균» — «양» 팔이 «둘» 다 거래를 «가진» 날«만»."""
    ma, mb = defaultdict(list), defaultdict(list)
    for d, _h, n in built[ka]:
        ma[d].append(n)
    for d, _h, n in built[kb]:
        mb[d].append(n)
    ds = sorted(set(ma) & set(mb))
    diff = [sum(ma[d]) / len(ma[d]) - sum(mb[d]) / len(mb[d]) for d in ds]
    return ds, diff


def main():  # noqa: C901
    P("# 244 - **「매매 «한» 번당」 — «단서»**  ⛔ **«판정»이 «아니다**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/244-per-trade.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ 사전등록 " + BQ + "results/244-PRE.md" + BQ)
    P("")
    P(F3)
    P("🔴 **«사용자» 결정**: **「계좌가 «판정» · 거래당은 «단서»」** — **«둘»이 «어긋나면» «계좌»를 «따른다**")
    P("⛔ **«이» 문서에 「가려졌다」·「칸 N」·「판정」·「낫다/나쁘다」는 «쓰지» «않는다**")
    P("")
    P("🚨 **「거래당」이 «지우는» 것 «셋** — **«머리»에 «붙인다**")
    P("   ① **슬롯 «경쟁»** — `232b`: **`231b` 의 «처치»는 271 이 «아니라» «열» 건**이었다")
    P("      ⇒ **거래당으로 보면 271 이 «다» «산다** — **«실제»로는 «못» 사는데**")
    P("   ② **자본 «제약»**(돈이 «모자라» «못» 삼)  ③ **«복리»**(`64`: 초기 몇 건이 자산을 «지배»)")
    P("   ⇒ ⛔ **「거래당 «낫다」 ≠ 「계좌가 «낫다」」** — `139`(−71%) · `138`(투입률↑ 돈 −40%)")
    P("")
    P("📐 **자** = 날짜별 «짝»차이의 «평균**(`16:50` 꼴) · **문턱 ±%.1f%%p**(M16-2 · `16:50`·`10:33`)" % THR)
    P("⛔ **`23:137` 의 「0.2172」를 «옮기지» «않았다** — **판마다 «자기» MDE 를 «낸다**")
    P(F3)
    P("")
    P("---")
    P("")

    todo = [(k, m234.REG[k][0], m234.REG[k][1]) for k in m234.REG]
    todo += [(k, v[0], v[1]) for k, v in EXTRA.items()]

    P("# 1. **단서 표**")
    P("")
    P("| 판 | 짝 | 날 | 점추정 | **95%% CI**(백분위) | 기본 CI | **MDE** | 문턱 %.1f | 읽기 |" % THR)
    P("|---|---|---:|---:|---:|---:|---:|:--|:--|")
    t0 = time.time()
    rows = []
    for key, fn, title in todo:
        try:
            got = fn()
        except Exception as e:                       # noqa: BLE001
            P("| `%s` | — | — | — | — | — | — | ⚪ | 🚨 **«못» 읽음**: %s |" % (key, e))
            continue
        built, pairs = got[0], got[1]
        for nm, ka, kb in pairs:
            ds, diff = per_trade(built, ka, kb)
            if len(ds) < 50:
                P("| `%s` | %s | %d | — | — | — | — | ⚪ | 🚨 **날이 «모자람**(<50) |"
                  % (key, nm, len(ds)))
                continue
            pt = sum(diff) / len(diff)
            n = len(diff)
            res = []
            for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
                rnd = random.Random(SEED + bi_blk)
                bs = []
                for _ in range(NBOOT):
                    order = draw(n, rnd, bmn, bmx)
                    bs.append(sum(diff[i] for i in order) / len(order))
                v = sorted(bs)
                lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
                res.append((lo, hi, st.stdev(bs)))
            lo = min(r[0] for r in res)
            hi = max(r[1] for r in res)
            sd = max(r[2] for r in res)
            blo, bhi = 2 * pt - hi, 2 * pt - lo
            mde = MDE_K * sd
            degen = (mde == 0.0 and abs(pt) < 1e-12)
            over = (not degen) and abs(pt) >= THR and (lo > 0 or hi < 0)
            near = (not degen) and mde <= THR
            if degen:
                read = ("🚨 **«자»가 «구조»상 «0» 을 낸다** — "
                        "**«날짜»를 «거르는» 팔이라 «같은» 날엔 «두» 팔이 «똑같다**")
            elif over:
                read = "🟢 **«질»이 «바뀌었다**(방향 %s)" % ("＋" if pt > 0 else "−")
            else:
                read = ("⚪ «질»의 «변화»가 **«안» 보인다** %s"
                        % ("· 🔎 자는 «문턱» 아래" if near else ""))
            rows.append((key, nm, n, pt, lo, hi, mde, over, near, degen))
            P("| `%s` | %s | %s | **%+.4f** | [%+.4f, %+.4f] | [%+.4f, %+.4f] | **%.4f** | %s | %s |"
              % (key, nm, format(n, ","), pt, lo, hi, blo, bhi, mde,
                 "🟢 «넘음»" if over else "⚪", read), flush=True)
    el = time.time() - t0
    P("")
    P(F3)
    n_over = sum(1 for r in rows if r[7])
    n_near = sum(1 for r in rows if r[8])
    n_deg = sum(1 for r in rows if r[9])
    P("   **짝 %d «중»** — 🟢 **문턱 ±%.1f 를 «넘고» CI 가 0 을 «배제» = %d**  ·  ⚪ **나머지 %d**"
      % (len(rows), THR, n_over, len(rows) - n_over))
    P("   🔎 **«자»가 문턱 «아래»(MDE ≤ %.1f)인 짝 = %d / %d**" % (THR, n_near, len(rows)))
    P("   🚨 **«자»가 «구조»상 «0» 인 짝 = %d**(«날짜»를 «거르는» 팔) — **「«못» 잰다」다**" % n_deg)
    P("")
    if n_over:
        P("⇒ ✅ **사전등록 「있다」 쪽** — **거래의 «질»이 «바뀐» 자리가 «있다**")
    else:
        P("⇒ 🔴 **사전등록 「없다」 쪽** — **거래당 자로도 «질»의 «변화»가 «안» 보인다**")
        P("   ⇒ ★ 그러면 **「«자»를 «바꿔도» «같다」」**이고 — **§B 는 «더» «세진다**")
    P("")
    P("   ⛔ **«어느» 쪽이든 — «계좌» 판정(§B)은 «그대로»다**(«사용자» 결정)")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 💰 **실측**")
    P("")
    P(F3)
    P("   **%.1f 분** (⚠️ 어림은 「판당 1분 «미만» · 십수 분」이었다)" % (el / 60.0))
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 하는 것**")
    P("")
    P(F3)
    P("⛔ ① 🚨 **「«거래당» «낫다」 ≠ 「«계좌»가 «낫다」」** — **«맺음»에 «다시» 적는다**")
    P("⛔ ② **날짜가 «양» 팔에 «다» 있는 날«만»** 썼다 — **«한» 팔에만 있는 날은 «버렸다**")
    P("     ⇒ 🚨 **「덜 사는」 팔의 «값»어치가 «그» 버림에 «숨는다**")
    P("⛔ ③ **`net` 은 «비용 «뒤»»**(세금 0.2%) — **거래당이 «음수»로 «기우는» 것이 «정상**이다")
    P("⛔ ④ **문턱 ±%.1f 도 «우리»가 «정한» 것**(M16-2) — **원전이 «준» 것이 «아니다**" % THR)
    P("⛔ ⑤ 🚨 **「문턱을 «넘은» 짝」의 «대부분»이 `183`·`185`·`191`·`193b`**다 —")
    P("     **「«같은» 거래를 «다른» 규칙으로 «푼»」 판**이라 **짝차이가 «거의» «결정»적**이다")
    P("     ⇒ ⛔ **그건 「거래의 «질»」이 «아니라 「규칙의 «산술»」에 «가까울** 수 있다")
    P("⛔ ⑥ **§B 를 «고치지» «않았다** — **«단서»는 §B 의 «판정»을 «안** 바꾼다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
