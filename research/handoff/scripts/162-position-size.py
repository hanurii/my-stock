# -*- coding: utf-8 -*-
r"""162 — **「한 종목에 얼마나」**(원전 ⑥ · 칸 수) · 사전등록 `tasks/162-position-size.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (2026-09-02~ · `41db459d`)** · 배당 포함 · 숏 없음

  🚨 **우리 「위험 기반 사이징」은 «아무 일도 안 한다»** — 그리고 **원전도 «같은 구조»다**:
     `lim = min(eq × risk / stop_frac, eq × cap)` = min(eq×0.20, eq×0.20) = **eq × 0.20**
     원전 「5% 손절 × 25% 포지션 = 위험 1.25%」 → 0.0125/0.05 = **0.2500** = 최대 **0.2500**
     ⇒ **원전이 「위험 기반」과 「비율 기반」을 «같은 것»으로 놓았다**
     ⇒ 칸↔상한↔위험을 «한 손잡이»로 묶는 것이 «임의»가 아니라 **«원전과 같은 구조»**다

  ★ 원전의 「4~8개」가 **«두 수»에서 «유도»**된다:
     위험 2.50% ÷ 손절 10% = 25%   → **칸 4** (원전 「최대 25%」)
     위험 1.25% ÷ 손절 10% = 12.5% → **칸 8** (원전 「보통 4~8개」)
     우리 2.0% ÷ 10% = 20%         → **칸 5** — 원전 범위 «안», «위쪽»
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
import statistics as st
import sys
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
acc = _load("acc", "account_lib.py")
gates = _load("gates", "_gates.py")
f92a = r102.f92a
pt = r91.pt

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF = 30.0, 10.0, 0.5
SF = STOP / 100.0                        # 🚨 «명시»로 쓴다 — 기본값에 «기대지» 않는다
NSEED, YRS, DELTA, T60 = 60, 27.4, 1.23, 2.001
CACHE = Path(str(r91.OUT / "162-partial.json"))
SLOTS = (3, 4, 5, 6, 8, 12)
NOTE = {3: "범위 «밖»", 4: "**원전 상단**", 5: "**현행**", 6: "", 8: "**원전 하단**", 12: "범위 «밖»"}


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    P = print
    P("=" * 104)
    P("162 — **「한 종목에 얼마나」**(원전 ⑥) · 🏷️ 세대 B · +30/−10 · 씨앗 %d판" % n_seed)
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-02 · `scripts/162-position-size.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## 🚨 **「위험 기반」과 「비율 기반」은 «같은 것»이다 — 원전도, 우리도**")
    P("")
    P("```")
    P("우리  `lim = min(eq × risk / stop_frac, eq × cap)`")
    P("      risk 0.02 / sf 0.10 = **0.20**  ·  cap = **0.20**   ⇒  **두 항이 «같다»**")
    P("원전  「5% 손절 × 25% 포지션 = 위험 1.25%」  →  0.0125/0.05 = **0.2500** = 최대 **0.2500**")
    P("⇒ ★ **원전이 «스스로» 둘을 «같은 것»으로 놓았다.** 그러니 칸↔상한↔위험을 «한 손잡이»로")
    P("  묶는 것은 **«임의»가 아니라 «원전과 «같은 구조»»**다")
    P("")
    P("⚠️ **두뇌 세션 문장 하나를 «정정»한다:**")
    P("   ⛔ 「현행 하네스는 `stop_frac` 을 «안 넣는다» ⇒ 기본값 0.10」")
    P("   ✅ **`pyr_trigger.py:161` 이 `stop_frac = stop/100` 을 «넣는다»** — 값이 «같을» 뿐이다")
    P("      (`slot_sim_lots:243` 의 `or 0.10` 은 «안» 쓰인다)")
    P("   ⇒ **차이가 «중요»하다** — 손절폭을 바꾸면 «위험항이 실제로 움직인다». 「죽은 코드」가 «아니다»")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("칸 N ↔ 상한 1/N ↔ 위험 (1/N)×손절폭   ← 출처: **원전의 «자기 계산»이 항등식**(위 참조)")
    P("원전 「4~8개」 → 칸 4·8              ← 출처: 원전 «글자» + 위 유도")
    P("손절폭 0.10                          ← 출처: 커밋 `41db459d` (STOP_PCT = 10.0)")
    P("Δ = 1.23%p                           ← 출처: 150 의 우리−QQQ 격차")
    P("㉮ 「4칸이 5칸보다 자산이 높을 것」    ← 출처: **`86:37-38` +371.98% vs +298.44%**")
    P("                                        🚨 86 의 «3칸» 수는 **인용 금지**")
    P("점유율은 «재구성» 값                  ← 출처: 159·160·161 에서 라벨 붙임")
    P("⚠️ **출처가 «빈» 가정: 없음**")
    P("```")
    P("")
    P("## ⛔ **이 판이 «안» 하는 것 — 피라미딩**")
    P("")
    P("```")
    P("⛔ 「74 로 «닫혔다」")
    P("✅ **「74 가 «그 구현»을 닫았고(진 이유는 «증액 후 손절선을 원가 아래로 «안» 내린 것»),**")
    P("   **«원전 방식»(5%→25%)은 «안 쟀다». 76 이 「짝으로 바꾸면 부호 반전하나 «146~290년»**")
    P("   **필요」를 냈다 ⇒ «잴 수 없다»」**")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    ev = []
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is False:
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                continue
            open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
            t["stop_frac"] = SF                 # 🚨 «명시» — 기본값에 안 기댄다
            ev.append(t)

    P("")
    P("## 관문 HB★ — **`lim` 에서 «어느 항»이 무는가**")
    P("")
    P("```")
    P("거래 **%s** 개 · `stop_frac` **«명시»로 %.2f** (기본값 «아님»)" % (format(len(ev), ","), SF))
    P("")
    P("| 칸 N | 상한 1/N | 위험 (1/N)×%.0f%% | 위험÷손절폭 | 무는 항 |" % (SF * 100))
    P("|---|---:|---:|---:|---|")
    for n in SLOTS:
        cap = 1.0 / n
        risk = cap * SF
        P("| **%d** | %.4f | %.4f | %.4f | **%s** |"
          % (n, cap, risk, risk / SF,
             "«같다» — 어느 쪽도 «혼자» 안 문다" if abs(risk / SF - cap) < 1e-12 else "🚨 갈린다"))
    P("")
    P("⇒ ★ **설계상 «두 항이 항상 같다».** 그래서 이 판은 **«한 손잡이»**를 움직인다")
    P("  (86 이 «여기서» 사양이 깨졌던 자리 — 그때는 셋이 «따로» 움직였다)")
    P("```", flush=True)

    span = (r102._ord(D1) - r102._ord(D0)) or 1
    rd = {(t["scan_date"], t["code"], t["pattern"]):
          (t["entry_date"], t["masks"][()]["resolve_date"] or t["entry_date"]) for t in ev}

    def occupancy(x, n):
        tot_ = 0
        for f in x["fill_log"]:
            if f[1] != "pilot":
                continue
            v = rd.get(f[0])
            if v:
                tot_ += max(0, r102._ord(v[1]) - r102._ord(v[0]))
        return 100.0 * tot_ / (n * span)

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out, occ, rec = {}, {}, {}
    for n in SLOTS:
        key = "s%d|n%d" % (n, n_seed)
        if key in cache:
            out[n] = [tuple(a) for a in cache[key]]
            occ[n] = cache.get(key + "|occ")
            P("  ♻️ 칸 %d — 갈무리" % n, flush=True)
            continue
        cap = 1.0 / n
        with r91.r41.Cost(*r91.COST):
            rs = [r91.sl.sim_lots(ev, seed=s, slots=n, risk=cap * SF, cap=cap,
                                  reserve=False, fill_rule="truncate", cash_rule="per_slot")
                  for s in range(n_seed)]
        out[n] = [acc.account(x) for x in rs]
        occ[n] = st.median([occupancy(x, n) for x in rs])
        cache[key] = [list(a) for a in out[n]]
        cache[key + "|occ"] = occ[n]
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        P("  칸 %d — 중앙 %.0f만 · 매수 %.0f · 점유 %.1f%%"
          % (n, st.median([a[0] for a in out[n]]),
             st.median([a[3] for a in out[n]]), occ[n]), flush=True)

    P("")
    P("=" * 104)
    P("## 1. 팔 여섯 — 🚨 **HD★: «자산만»으로 판정 «안» 한다**")
    P("=" * 104)
    P("")
    P("| 칸 | 상한 | 위험 | 세후 총액(중앙) | 연 환산 | **운의 폭 5~95%** | «세전» 낙폭 | 회복 | 매수 | 점유 |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for n in SLOTS:
        v = sorted(a[0] for a in out[n])
        m = st.median(v)
        lo5, hi95 = v[int(len(v) * .05)], v[int(len(v) * .95)]
        P("| **%d** %s | %.1f%% | %.2f%% | %.0f만 | **%+.2f%%** | **%.0f ~ %.0f만** | %+.1f%% | %.1f년 | %.0f | %.1f%% |"
          % (n, NOTE[n], 100.0 / n, 100.0 * SF / n, m, acc.cagr(m, YRS), lo5, hi95,
             st.median([a[1] for a in out[n]]),
             st.median([a[2] for a in out[n]]) / 252.0,
             st.median([a[3] for a in out[n]]), occ[n]))
    P("")
    P("```")
    P("**HA★** 평균 노출(자리-일 점유)이 «±5%p 안»인가 — 🚨 안 맞으면 **«보정» 말고 «라벨»**")
    ob = occ[5]
    bad = [n for n in SLOTS if abs(occ[n] - ob) > 5.0]
    for n in SLOTS:
        P("   칸 %-2d  점유 **%.1f%%** (%+.1f%%p vs 칸 5)%s"
          % (n, occ[n], occ[n] - ob, "   🚨 **±5%p 밖**" if abs(occ[n] - ob) > 5.0 else ""))
    if bad:
        P("   ⇒ 🚨 **%s 은 «집중»이 아니라 «현금»도 «같이» 재고 있다** — 그 라벨로 읽는다"
          % ", ".join("칸 %d" % n for n in bad))
        P("     ⛔ **«보정»하지 «않는다»** — 보정하면 **«새 손잡이»**가 생긴다(159 에서 «적었던» 자리)")
    else:
        P("   ⇒ ✅ **여섯 팔이 «같은 노출»**이다")
    P("```")
    P("")
    P("=" * 104)
    P("## 2. ⛔ **HC★(자산) · HD★(위험) — «따로» 낸다**")
    P("=" * 104)
    P("")

    def pair(n):
        d = [acc.cagr(out[n][i][0], YRS) - acc.cagr(out[5][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, sd, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("🚨 **낙폭 열은 «부호»가 «거꾸로 읽힌다»** — 낙폭은 «음수»라 «−가 더 깊다».")
    P("   그래서 **«낱말»로 적는다**(수만 적으면 「−1.2%p = 더 얕다」로 «읽힌다»)")
    P("")
    P("| 칸 | 자산 차(vs 칸 5) | **95% CI** | **낙폭 — 칸 5 보다** | 운의 폭(배) |")
    P("|---|---:|---|:--|---:|")
    res = {}
    w5 = sorted(a[0] for a in out[5])
    sp5 = (w5[int(len(w5) * .95)] - w5[int(len(w5) * .05)]) / max(st.median(w5), 1)
    for n in SLOTS:
        if n == 5:
            continue
        mu, sd, lo, hi = pair(n)
        res[n] = (mu, sd, lo, hi)
        v = sorted(a[0] for a in out[n])
        sp = (v[int(len(v) * .95)] - v[int(len(v) * .05)]) / max(st.median(v), 1)
        dd = st.median([a[1] for a in out[n]]) - st.median([a[1] for a in out[5]])
        P("| **%d** | **%+.3f%%p** | [%+.3f, %+.3f] | **%.1f%%p %s** | **%.2f배**(칸5=%.2f) |"
          % (n, mu, lo, hi, abs(dd),
             "🔴 더 «깊다»" if dd < -0.05 else
             ("🟢 더 «얕다»" if dd > 0.05 else "≈ «같다»"), sp, sp5))
    P("")
    P("```")
    P("★ **판정 규칙 — «값 보기 전»에 박았다**(사전등록 `d509662c`):")
    P("   HC★(자산) «와» HD★(위험) **둘 다** 통과  →  「**맞바꿈이 «아니라» «둘 다» 낫다**」")
    P("   **하나만** 통과  →  🚨 «미통과»가 «아니라» **«다른 답»**: 「**«맞바꿈»이다**」")
    P("                     ⇒ **«사용자 선택»으로 넘긴다**")
    P("   둘 다 미통과  →  「현행(칸 5)을 바꿀 근거가 «없다」")
    P("")
    P("⛔ **「수익 ÷ 낙폭」 같은 «합성 자»를 «헤드라인»으로 «안» 쓴다** —")
    P("   그건 **«손잡이»**다(어떤 비율로 나눌 건가?). **유형 49** 의 자리다")
    P("✅ **두 축을 «따로» 내고 «사용자가 고르게»** 한다")
    P("```")
    P("")
    P("### 🧮 사전등록 규칙을 **«기계적으로»** 적용하면 (⏸️ **검증 2차 전 «미확정»**)")
    P("")
    P("```")
    v5 = sorted(a[0] for a in out[5])
    for n in SLOTS:
        if n == 5:
            continue
        mu, sd, lo, hi = res[n]
        vn = sorted(a[0] for a in out[n])
        spn = (vn[int(len(vn) * .95)] - vn[int(len(vn) * .05)]) / max(st.median(vn), 1)
        ddn = st.median([a[1] for a in out[n]]) - st.median([a[1] for a in out[5]])
        hc = mu >= DELTA and lo > 0
        hd = ddn > 0.05 and spn < sp5          # 낙폭 «얕고» 운의 폭 «좁다»
        lost = mu <= -DELTA and hi < 0        # 🚨 사전등록 표에 «없던» 칸
        note = ("«둘 다» 낫다" if (hc and hd) else
                ("🚨 **«맞바꿈»이나 «값»이 Δ 를 «넘는다»** — 아래 ⚠️ 참조" if (hd and lost) else
                 ("🚨 **«맞바꿈»** ⇒ **사용자 선택으로 넘긴다**" if (hc or hd) else
                  ("자산 축에서 **«졌다»**" if lost else "바꿀 근거 «없다»"))))
        why = []
        if not hc:
            why.append("자산 %+.3f%%p %s Δ(%.2f)" % (mu, "<" if mu < DELTA else ">=", DELTA)
                       + ("" if lo > 0 else " · CI 가 0 을 «문다»"))
        if not hd:
            why.append("낙폭 %s · 운의 폭 %.2f%s%.2f"
                       % ("더 깊다" if ddn < -0.05 else ("같다" if abs(ddn) <= 0.05 else "더 얕다"),
                          spn, ">" if spn > sp5 else "<=", sp5))
        P("칸 %-2d  HC★(자산) %s · HD★(위험) %s  →  **%s**"
          % (n, "✅" if hc else "❌", "✅" if hd else "❌", note))
        for w in why:
            P("        ↳ %s" % w)
    P("")
    P("⚠️ **사전등록 판정표에 «구멍»이 있어 «메웠다» — 161 과 «같은 종류»다:**")
    P("   표는 「둘 다 통과 / 하나만 통과 = 맞바꿈 / 둘 다 미통과」 셋뿐이었다.")
    P("   🚨 그런데 **「자산이 −Δ «아래»로 «졌다»」는 칸이 «없다».**")
    P("   그대로 두면 **칸 8(자산 −2.40%p = Δ 의 «두 배» 손실)**이 「HD★ 통과」 하나로")
    P("   **「맞바꿈 ⇒ 사용자 선택」**으로 «흘러간다». **«고르라고 내놓을 물건»이 아니다**")
    P("   ⇒ 「맞바꿈」과 「«값»이 Δ 를 넘는 맞바꿈」을 **«갈라»** 적었다.")
    P("     ⛔ **어느 쪽인지 «내가» 정하지 «않는다»** — 두뇌 세션이 «판정표를 고칠» 자리다")
    P("```")
    P("")
    for n in (4, 8):
        if n in res:
            P("```")
            P("칸 %d vs 칸 5 — 효과/씨앗SD" % n)
            for ln in gates.p_informative(res[n][0], res[n][1], n=n_seed)[1]:
                P("   " + ln)
            P("```")
    P("")
    P("```")
    P("⛔ **못 쓸 말** — 「원전 ⑥ 이 «틀렸다/맞다»」 · 「수익÷낙폭」 합성 자 · **86 의 «3칸» 수**")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 진입 규칙",
                     "같은 손절 −%.0f" % STOP, "**같은 거래 집합**(아무도 «안» 뺌)"]):
        P(ln)
    P("⇒ ✅ **이 CI 는 «우리 규칙 안에서 안정적인가»이지 «시장에서 나은가»가 아니다**")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
