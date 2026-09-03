# -*- coding: utf-8 -*-
r"""168 — **원전 「기술적 분석」의 «마지막 둘»** · 사전등록 `tasks/168-fundamentals-two-claims.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  ★★★ **㉠ 은 «조건»이 «뒤집혀» 있다:**
     우리가 «지금까지» 잰 것 :  **P( 대박 | 실적 좋음 )**   ← «고르는» 쪽 (92·94·147)
     원전이 «말한» 것        :  **P( 실적 좋음 | 대박 )**   ← «사후 관찰»
     🚨 **P(A|B) 가 높다고 P(B|A) 가 높은 게 «아니다» — «기저율»에 달렸다**
     ⇒ 「대박의 70%가 실적이 좋았다」는 **«전체»의 70%도 그러면 «아무 말도 안 한다»**

  ★★ **㉡ 은 「«덜» 거르자」다 — 앞 일곱 판이 «전부» 「«더» 거르자」였다**
     현행은 `103 judge` 로 「실적 «가속»이 «아닌» 것(False)」을 «버린다»
     ⇒ 그게 **«정확히» 원전 ②가 «하지 말라»는 것**이다
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
import os
import random
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
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NSEED, NASSIGN, YRS, DELTA, T60 = 60, 10, 27.4, 1.23, 2.001
MA_REF = 12377
PA_TOL = 0.01                 # PA★ 합 검산 허용 오차(%p)
CACHE = Path(str(r91.OUT / "168-partial.json"))


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    dry = "--dry" in sys.argv
    P = print
    P("=" * 104)
    P("168 — **원전 「기술적 분석」의 «마지막 둘»** · 씨앗 %d × 배정 %d%s"
      % (n_seed, n_as, "  🚨 **--dry(«구조»만)**" if dry else ""))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/168-fundamentals-two-claims.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## ★★★ **㉠ 은 «조건»이 «뒤집혀» 있다**")
    P("")
    P("```")
    P("우리가 «지금까지» 잰 것 :  **P( 대박 | 실적 좋음 )**   ← «고르는» 쪽 (92·94·147)")
    P("원전이 «말한» 것        :  **P( 실적 좋음 | 대박 )**   ← «사후 관찰»")
    P("")
    P("🚨 **P(A|B) 가 높다고 P(B|A) 가 높은 게 «아니다» — «기저율»에 달렸다**")
    P("⇒ 「대박의 70%가 실적이 좋았다」는 **«전체»의 70%도 그러면 «아무 말도 «안» 한다**")
    P("```")
    P("")
    P("## 🔎 **「전에 물었나」 — PF★: «명령»과 «돌린 자리»를 «같이» 적는다**")
    P("")
    P("```")
    P("명령   `grep -rl \"기저율\" research/handoff/{tasks,verdicts}`")
    P("자리   `%s`" % os.getcwd().replace("\\\\", "/"))
    P("결과   **0 건** (두뇌 세션 실행) ⇒ **«처음»이다**")
    P("")
    P("🚨 오늘 「없다」가 **«세 얼굴»**이었다 — 그래서 «명령»과 «자리»를 «같이» 적는다:")
    P("   ① `head -N` 의 **«잘림»**을 「N 곳」으로   ② **«안 찾아봄»**을 「없음」으로")
    P("   ③ `cd` 누적으로 **«자리가 틀림»**을 「없음」으로")
    P("```")
    P("")
    P("## ✅ **Ⓘ 의 «설계 근거» — 「전부 삼」이 «곧» 원전 ②다**")
    P("")
    P("```")
    P("원전 ② 「펀더멘털이 나빠도 **«차트가 강하면»** 산다」")
    P("Ⓘ     「**전부** 삼」")
    P("★ **우리 후보는 «이미» 차트 조건을 «통과»한 것들**이다(돌파 + 추세 + 유동성)")
    P("⇒ ✅ **그래서 「전부 삼」이 «곧» 「차트가 강하면 «산다»」**가 된다")
    P("🚨 **이걸 «안» 적으면 Ⓘ 가 「아무거나 삼」으로 «오도»된다** — 그래서 «앞»에 적는다")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("「대박의 70%가 앞서 좋은 실적」 ← 출처: 원전 «글자»")
    P("「실적으로 «거르지» 마라」      ← 출처: 원전 «글자»")
    P("Δ = 1.23%p                     ← 출처: 150 의 우리−QQQ 격차")
    P("MA★ 기준 %s만              ← 출처: 156·161~167 의 ①" % format(MA_REF, ","))
    P("")
    P("🚨 **출처가 «빈» 가정 — «셋»:**")
    P("   ⛔ **「좋은 실적」 = `103 judge`(EPS·매출 «가속»)** — **«우리» 정의**지 «원전의 말»이 «아니다**")
    P("   ⛔ **「크게 상승」의 «자»** — 원전은 「크게」라고만 했다 ⇒ **«넷» «다» 적는다**(PD★)")
    P("   ✅ ~~문턱~~ — **«없앴다»**. 「기저율과 «다른가」」만 묻는다(CI 0 배제)")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    # ── judge 등급 + 「크게 상승」의 «자 넷» ────────────────────────────────
    rows, keep, kept = [], {}, set()
    for y in sorted(by2):
        keep[y] = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            ok_ = (a is not None
                   and r102._ord(p["entry_date"]) - r102._ord(a[0]) <= r102.STALE_MAX)
            v = r103.judge(arq, arq.index(a), ix, 1, 2) if ok_ else None
            ep = p["entry_price"]
            hs = [x for x in p["h"] if x is not None]
            run = (max(hs) / ep - 1.0) if (hs and ep and ep > 0) else None
            rows.append((v, run, len(p["c"])))
            if v is not False:
                keep[y].append(p)
                kept.add(id(p))

    good = [r for r in rows if r[1] is not None]
    good.sort(key=lambda r: -r[1])
    n_all = len(rows)
    base_true = sum(1 for r in rows if r[0] is True)
    base_rate = 100.0 * base_true / n_all

    P("")
    P("## 1. 🚨 **PC★ — 기저율은 «거르기 «전»»(`by2`)에서 잰다**")
    P("")
    P("```")
    P("(`by_f` 로 재면 **«우리 필터»가 이미 올려놓아 «순환»**이다)")
    P("")
    P("후보 **%s** 중 `judge` — **True %s(%.1f%%)** · None %s(%.1f%%) · False %s(%.1f%%)"
      % (format(n_all, ","), format(base_true, ","), base_rate,
         format(sum(1 for r in rows if r[0] is None), ","),
         100.0 * sum(1 for r in rows if r[0] is None) / n_all,
         format(sum(1 for r in rows if r[0] is False), ","),
         100.0 * sum(1 for r in rows if r[0] is False) / n_all))
    P("")
    P("## ⇒ **기저율 P(실적 좋음) = %.1f%%**" % base_rate)
    P("")
    P("🚨🚨 **기저율이 «세 층»이다 — 어느 층인지 «적지» 않으면 유형 67 이다:**")
    P("   **1층** 시장 «전체» 상장사                      🚨 **원전이 말한 건 «이쪽»일 가능성이 크다**")
    P("   **2층** 우리 «후보»(돌파+추세 통과 · 실적 «전») = `by2`   ← **여기서 쟀다** ✅")
    P("   **3층** 우리 «매수»(실적 «후») = `by_f`                  ← «순환». **안 썼다** ✅")
    P("")
    P("   🚨 **`by2` «도» «순환»의 «일부»다** — 돌파+추세가 **«이미» 걸러 놓았다**")
    P("   ⇒ ⛔ **«범위 문장»: 「«1층»(시장 전체)은 «안» 쟀다」**")
    P("     (1층은 156a·159a 부품에 실적을 붙여야 해서 **«비싸다». «안» 재고 «적기»만 한다)")
    P("   ⇒ ★ 그러면 **「원전의 70% 와 «같은 자»인지 «모른다」」**가 **«정확»**해진다")
    P("   ⇒ ✅ 그래도 **「같은 모집단(2층) «안»에서 대박군이 «더» 높은가」**는 «답할 수» 있다 — 그게 이 판이다")
    P("```", flush=True)

    P("")
    P("## 2. 🚨 **PD★ — 「크게 상승」의 «자»가 «넷»이다. «하나»만 적으면 «고른» 것**")
    P("")
    P("```")
    P("자: `run` = **경로 «전체» 최고가 ÷ 체결가 − 1**(우리 청산 규칙에 «안» 걸린 «주가»의 움직임)")
    P("🚨 **경로 길이가 종목마다 다르다** — 중앙 **%d** 거래일. **「같은 기간」이 «아니다»**"
      % st.median([r[2] for r in good]))
    P("")
    P("| 자 | 대박군 n | **P(실적 좋음 | 대박)** | 기저율 | **차** | 판정 |")
    P("|---|---:|---:|---:|---:|:--|")
    n_g = len(good)
    METERS = (("㉠-a 상위 **1%**", good[:max(1, n_g // 100)]),
              ("㉠-b 상위 **5%**", good[:max(1, n_g // 20)]),
              ("㉠-c **+100%** 이상", [r for r in good if r[1] >= 1.0]),
              ("㉠-d **+30%** 도달", [r for r in good if r[1] >= 0.30]))
    for nm, sub in METERS:
        k = len(sub)
        t = sum(1 for r in sub if r[0] is True)
        pr = 100.0 * t / max(k, 1)
        se = math.sqrt(max(pr * (100 - pr) / max(k, 1), 1e-12))
        lo, hi = pr - 1.96 * se - base_rate, pr + 1.96 * se - base_rate
        vd = ("✅ **기저율보다 «높다» — 「70%」에 «정보가 있다»**" if lo > 0 else
              ("🚨 **기저율보다 «낮다» — «거꾸로»다**" if hi < 0 else
               "🚨 **기저율과 «구분 안 됨» — 「70%」는 «아무 말도 안 한다»**"))
        P("| %s | %s | **%.1f%%** | %.1f%% | **%+.1f%%p** [%+.1f, %+.1f] | %s |"
          % (nm, format(k, ","), pr, base_rate, pr - base_rate, lo, hi, vd))
    P("")
    P("✅ **문턱을 «안» 건다 — 두뇌 세션이 «스스로» 없앴다:**")
    P("   물음은 「70%가 «정보»인가」이고, 「정보인가」 = **「기저율과 «다른가»」**이지")
    P("   **「«얼마나» 다른가」가 «아니다»** ⇒ **CI 가 0 을 «배제»하는가**로 «충분»하다")
    P("   ★ 「눈에 띄게 높아야」의 **「눈에 띄게」가 «수»가 «아니었다»** — 오늘의 「«고를 자리»를 «없앤다」」")
    P("🚨 **단 «크기»는 «적는다»** — 「0 과 «다르다»」와 「«실무적»으로 «크다»」는 **«다른 말»**이다")
    P("```", flush=True)

    # ── ㉡ 팔 셋 ───────────────────────────────────────────────────────────
    def build(mode, drop=None):
        """mode: cur(True∪None) | all(전부) | rnd(무작위 m개 버림)"""
        out_, npre = [], 0
        for y in sorted(by2):
            open_until = {}
            for p in by2[y]:
                k = (p["scan_date"], p["code"], p["pattern"])
                if mode == "cur" and id(p) not in kept:
                    npre += 1
                    continue
                if mode == "rnd" and drop is not None and k in drop:
                    npre += 1
                    continue
                t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                t["stop_frac"] = STOP / 100.0
                out_.append(t)
        return out_, npre

    ev_cur, m_cur = build("cur")
    ev_all, _ = build("all")
    P("")
    P("## 3. 관문 — 구조")
    P("")
    P("```")
    P("**PB★ 「실적으로 버린 수 m」이 ① 과 Ⓓ 에서 «같은가»**")
    P("   ① 이 버린 m = **%s** (= `judge` False 수) · Ⓓ 도 «같은 수»를 «무작위»로 버린다(설계)"
      % format(m_cur, ","))
    P("   🚨 **«중복제거 «전»»에서 뺀다** — `165` LB★ 가 «여기서» 터졌다")
    P("")
    P("**최종 거래 수** — ①(True∪None) **%s** · Ⓘ(전부) **%s**"
      % (format(len(ev_cur), ","), format(len(ev_all), ",")))
    P("```", flush=True)
    if dry:
        P("")
        P("🚨 **--dry — 여기까지가 «구조»다. 시뮬레이션은 «안» 돌렸다**")
        return 0

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    def sim(ev, key):
        if key in cache:
            return [tuple(a) for a in cache[key]], cache[key + "|m"]
        with r91.r41.Cost(*r91.COST):
            rs = [r91.sl.sim_lots(ev, seed=s, slots=SLOTS, risk=0.02, cap=0.20,
                                  reserve=False, fill_rule="truncate",
                                  cash_rule="per_slot") for s in range(n_seed)]
        v = [acc.account(x) for x in rs]
        m = {"expo": st.median([x["expo_mean"] for x in rs]), "n": len(ev)}
        cache[key] = [list(a) for a in v]
        cache[key + "|m"] = m
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        return v, m

    out, meta = {}, {}
    out["①"], meta["①"] = sim(ev_cur, "v1|cur|n%d" % n_seed)
    out["Ⓘ"], meta["Ⓘ"] = sim(ev_all, "v1|all|n%d" % n_seed)
    P("  ① %.0f만(%d) · Ⓘ %.0f만(%d)"
      % (st.median([a[0] for a in out["①"]]), meta["①"]["n"],
         st.median([a[0] for a in out["Ⓘ"]]), meta["Ⓘ"]["n"]), flush=True)

    allk = {y: [(p["scan_date"], p["code"], p["pattern"]) for p in by2[y]] for y in by2}
    nex = {y: sum(1 for p in by2[y] if id(p) not in kept) for y in by2}
    accs, exs, ns = [], [], []
    for ai in range(n_as):
        rg = random.Random(ai + 1_000_000)
        drop = set()
        for y, ks in allk.items():
            drop |= set(rg.sample(ks, min(nex[y], len(ks))))
        evD, _ = build("rnd", drop=drop)
        v, m = sim(evD, "v1|D|a%d|n%d" % (ai, n_seed))
        accs.append(v)
        exs.append(m["expo"])
        ns.append(m["n"])
    out["Ⓓ"] = [tuple(st.mean(accs[ai][i][j] for ai in range(n_as)) for j in range(4))
                 for i in range(n_seed)]
    meta["Ⓓ"] = {"expo": None, "expo_d": exs, "n": st.mean(ns)}
    P("  Ⓓ %.0f만(%.0f · 배정 %d개 평균)"
      % (st.median([a[0] for a in out["Ⓓ"]]), meta["Ⓓ"]["n"], n_as), flush=True)

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    def dif(x, y):
        d = [acc.cagr(out[x][i][0], YRS) - acc.cagr(out[y][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("")
    P("## 4. 관문 — 수")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①"]])
    P("**MA★ 앵커** — ① **%.0f만** vs %s만  →  %s   («아홉 번째»)"
      % (m1, format(MA_REF, ","), "✅ **일치**" if abs(m1 - MA_REF) < 1.0 else "🚨 **멈춘다**"))
    e = dif("①", "Ⓓ")[0] - dif("Ⓘ", "Ⓓ")[0] - dif("①", "Ⓘ")[0]
    P("")
    P("**PA★ 합 검산** — |(①−Ⓓ) − (Ⓘ−Ⓓ) − (①−Ⓘ)| < %.2f%%p  →  **%+.4f%%p**  %s"
      % (PA_TOL, e, "✅" if abs(e) < PA_TOL else "🚨 **멈춘다**"))
    P("")
    P("**PE★ 노출 — «팔마다» «반복문»으로**(「물어본 것만 잰다」를 «구조적»으로 «불가능»하게)")
    P("🚨 **PE2★ — Ⓘ 는 m 개를 «더» 산다 ⇒ 자리 경쟁이 세지고 «노출»이 «오를» 것이다. «수»로 찍는다**")
    P("   ★ `167` 에서 Ⓗb 가 노출 **−2.2%p** 로 걸렸던 «그 자리»이고 — **이번엔 «반대 방향»**이다")
    for nm in ("①", "Ⓘ", "Ⓓ"):
        if meta[nm]["expo"] is not None:
            P("   %-3s **%.1f%%**" % (nm, meta[nm]["expo"]))
        else:
            d_ = meta[nm]["expo_d"]
            P("   %-3s **%.1f ~ %.1f%%**(중앙 **%.1f%%**)" % (nm, min(d_), max(d_), st.median(d_)))
    def _ex(nm):
        return meta[nm]["expo"] if meta[nm]["expo"] is not None else st.median(meta[nm]["expo_d"])

    slope = acc.cagr(m1, YRS) / meta["①"]["expo"]
    P("")
    P("🚨🚨 **이 판에서는 «노출 보정»을 «쓸 수 없다» — «기울기 부호»가 «반대»다:**")
    P("   팔 셋의 (노출, 성적): ① (%.1f%%, %+.2f%%) · Ⓓ (%.1f%%, %+.2f%%) · Ⓘ (%.1f%%, %+.2f%%)"
      % (_ex("①"), acc.cagr(m1, YRS), _ex("Ⓓ"),
         acc.cagr(st.median([a[0] for a in out["Ⓓ"]]), YRS), _ex("Ⓘ"),
         acc.cagr(st.median([a[0] for a in out["Ⓘ"]]), YRS)))
    in_slope = ((acc.cagr(st.median([a[0] for a in out["Ⓘ"]]), YRS) - acc.cagr(m1, YRS))
                / max(_ex("Ⓘ") - _ex("①"), 1e-9))
    P("   ⇒ **노출이 «오를수록» 성적이 «내린다»** — 판 «안»의 기울기 **%+.3f%%p/%%p**" % in_slope)
    P("   ⇒ 🚨 **① 에서 뽑은 «+%.3f» 과 «부호»가 «반대»이고 크기도 «%.0f배»**"
      % (slope, abs(in_slope / slope)))
    P("")
    P("   ## ⇒ ⛔ **그래서 「보정」을 «안» 한다 — 그건 «수»가 아니라 «잘못된 «모형»»이다**")
    P("   ★ 팔들이 다른 건 **「«얼마나» 사는가」가 아니라 「«무엇»을 사는가」**여서,")
    P("     **노출을 «설명 변수»로 쓰면 «인과»를 «거꾸로» 붙인다**")
    P("   ✅ 대신 **Ⓓ 가 그것을 «흡수»하는지**를 «수»로 본다(아래 PE2★)")
    P("")
    P("**PE2★ — Ⓘ 는 +%.1f%% 를 «더» 산다 ⇒ 「«안 걸러서»」와 「«더 사서»」가 «섞인다»**"
      % (100.0 * (meta["Ⓘ"]["n"] - meta["①"]["n"]) / meta["①"]["n"]))
    P("   최종 거래 — ① **%s** · Ⓓ **%.0f** · Ⓘ **%s**"
      % (format(meta["①"]["n"], ","), meta["Ⓓ"]["n"], format(meta["Ⓘ"]["n"], ",")))
    P("   🚨 **Ⓓ 가 ① 보다 «%+.1f%%» 더 산다** — 「같은 m 개를 뺐는데」 «중복제거»가 «다르게» 이어져서다"
      % (100.0 * (meta["Ⓓ"]["n"] - meta["①"]["n"]) / meta["①"]["n"]))
    P("     (① 이 빼는 건 **«상관된»**(judge False) 것 · Ⓓ 는 **«무작위»**)")
    P("")
    if meta["Ⓓ"]["n"] > meta["①"]["n"]:
        P("   ⇒ ★ **Ⓓ 가 ① 보다 «더 많이» 사고, 이 판에선 «더 사는 쪽»이 «나쁘다»**(Ⓘ 가 제일 나쁨)")
        P("   ⇒ 🚨 **그러므로 ①−Ⓓ 의 «+%.3f%%p» 에는 「Ⓓ 가 «더 사서» 손해 본 몫」이 «섞여» 있다**"
          % dif("①", "Ⓓ")[0])
        P("   ⇒ ⛔ **「실적 필터의 «순수한» 값」은 «이 수보다 «작다»».** «얼마나»는 **«안» 쟀다**")
        P("   ★ 그래도 **①−Ⓘ(**%+.3f%%p**)는 «거래 수»가 «둘 다 «안» 겹치게» 다르니 «같은 문제»가 있다"
          % dif("①", "Ⓘ")[0])
        P("     ⇒ ✅ **「필터가 «값»을 한다」의 «부호»는 «셋 다» 같은 쪽이다. «크기»만 «미정»이다**")
    else:
        P("   ⇒ ★ Ⓓ 가 ① 보다 «적게» 사니 «반대» 방향이다")
    P("```")

    P("")
    P("## 5. 팔 셋")
    P("")
    P("| 팔 | 거래 | 세후 총액(중앙) | 연 환산 | 📏폭 | 낙폭 중앙 | 회복 |")
    P("|---|---:|---:|---:|---:|---:|---:|")
    for nm in ("①", "Ⓘ", "Ⓓ"):
        v = out[nm]
        mm = st.median([a[0] for a in v])
        P("| **%s** | %.0f | %.0f만 | **%+.2f%%** | %.2f | %+.1f%% | %.1f년 |"
          % (nm, meta[nm]["n"], mm, acc.cagr(mm, YRS), spread(v),
             st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0))

    P("")
    P("## 5b. 🚨 **㉯(「①−Ⓓ 가 «양수»」)에 «반대» 증거가 «미리» 있었다 — «알고» 있었다**")
    P("")
    P("```")
    P("기억 `us-fundamentals-2026-08` — `92` 는 **«두 축»**이었다:")
    P("   «꼬리» 축   `roe` 가 「한때 2배」를 **«양»**으로 가름(관측 +6.65)")
    P("   🚨 **«계좌» 축**  「골라 사면」 **+108.83 → +47.78% = «−61.05%p»**  ← **«음수»**")
    P("")
    P("⇒ ★ **`92` 의 «계좌» 결과가 ㉯(«양수»)와 «반대» 방향이었다**")
    P("⇒ 그리고 이 판 **㉠(꼬리)도 «음»** 이었다")
    P("## ⇒ 🚨 **㉠(꼬리 «음») · `92` 계좌(«음») 이 «둘 다» ㉯(«양») 과 «반대»였다**")
    P("")
    P("✅ **사전등록은 «안» 고쳤다.** 다만 **「«알고» 있었다」를 «적어» 둔다** —")
    P("   그래야 ㉡ 의 결과가 어느 쪽이든 **「예상대로 / 뜻밖」이 «정확»해진다**")
    P("⚠️ 🚨 **단 ㉠ 은 «꼬리», ㉡ 은 «계좌»다** — **㉠ 으로 ㉡ 을 «예단하지» 않는다**")
    P("   (그리고 실제로 **㉡ 은 «양수»로 나왔다** — 세 「반대 증거」와 **«또» 어긋난다**)")
    P("```")
    P("")
    P("## 6. 판정 — 🚨 **«안 바라는» 칸을 «먼저», «더 잘게»**")
    P("")
    P("```")
    P("🚨 내가 «바라는» 답은 「①−Ⓓ 가 «양수»」(= 현행이 최적점)다 ⇒ **«아닌» 칸을 «먼저» 쪼갠다**")
    P("   **1b** 「**«실적»이 아니라 «덜 사는 것»이 일한 것**일 수 있다」  ← Ⓘ−Ⓓ > 0 일 때")
    P("   **2a** 「**«다 사는» 게 «낫다»**(원전 ② «강한 지지»)」")
    P("   **2b** 「필터는 나쁜데 **«다 사는» 것도 «안» 낫다**」")
    P("★ 「그 사이」 칸에는 **«부호»를 «항상»** 적는다(오늘 세운 규칙)")
    P("```")
    P("")
    P("| 짝 | 차 | **95% CI** | 판정 |")
    P("|---|---:|---|:--|")
    for lab, x, y in (("**①−Ⓓ** 「실적 필터가 «무작위»보다 나은가」 ★", "①", "Ⓓ"),
                      ("**Ⓘ−Ⓓ** 「«덜 사는 것» «자체»의 몫」", "Ⓘ", "Ⓓ"),
                      ("**①−Ⓘ** 「거르는 것 vs «다» 사는 것」(원전 ②)", "①", "Ⓘ")):
        mu, lo, hi = dif(x, y)
        if lo > DELTA:
            vd = "✅ **Δ «보다» 강하게 «양수»**"
        elif lo > 0 and hi > DELTA:
            vd = "**4b** 🚨 **«양수»·CI 가 Δ 를 «걸침»**"
        elif lo > 0:
            vd = "**4a** **«확실히» «양수»인데 «크기»가 Δ 미만**"
        elif hi < 0 and mu <= -DELTA:
            vd = "🚨 **Δ «보다» 강하게 «음수»**"
        elif hi < 0:
            vd = "**칸3** ⚠️ **«확실히» «음수»인데 «크기»가 Δ 미만**"
        else:
            vd = "🚨 **못 가린다**"
        P("| %s | **%+.3f%%p** | [%+.3f, %+.3f] | %s |" % (lab, mu, lo, hi, vd))

    P("")
    P("```")
    P("★★ **147(«더» 거르기 실패) + 이 판 ㉡(«덜» 거르기)이 «짝»이다**")
    P("   ⇒ **「현행이 «양쪽»에서 눌려 있나」**를 «닫는다**")
    P("")
    P("⛔ **못 쓸 말** — 「이유」에 «수»가 있으면 **«생성»**한다(오늘 정한 규칙)")
    P("   🚨 **범위 문장 — «둘 다» 막는 «한 문장»:**")
    P("     ## **「이 판은 원전 ①을 «검정»한 것이 «아니라» —**")
    P("     ## **  «우리 «가속» 자»로 «같은 «모양»의 물음»을 «다시» 던진 것이다」**")
    P("     (기저율 **%.1f%%** vs 원전 「70%%」 — **«자릿수»가 다르다** ⇒ 「틀렸다」도 「맞다」도 «못» 쓴다)"
      % base_rate)
    P("")
    P("   🚨 **`92` 와도 «다른 자»다**(유형 67):")
    P("     `92`  `roe`   = 수익성 **«수준»**   ·   `168` `judge` = EPS·매출 **«가속»**")
    P("     ⇒ ✅ **「roe(수준)와 judge(가속)가 «다른 부호»를 냈다 — 그 둘이 «같은 축»인지는 «안» 쟀다」**")
    P("")
    P("   ⛔ 「원전 ①이 맞다/틀리다」 — **«좋은 실적»의 자가 «우리» 것**이고")
    P("     **«1층»(시장 전체) 기저율을 «안» 쟀다** ⇒ **«같은 자»인지 «모른다»**   ← «범위». 손글씨")
    P("   🆕 ⛔ **「펀더멘털은 «무의미»하다」** — 잰 건 **«우리 필터»**(`103 judge`)이지")
    P("     **«펀더멘털 «일반»»이 «아니다»**                                        ← «범위». 손글씨")
    P("   🆕 ⛔ **Ⓘ 를 「원전 ②의 «성적»」으로** — **차트 조건이 «후보»에 «있음»을 «안 적으면» «오도»**")
    P("   ⛔ 「`147` 과 «같은» 판」 — **방향이 «반대»**다(147 은 «더» 거르기, 이 판은 «덜» 거르기)")
    P("   ⛔ 「원전 ②가 맞다/틀리다」 — **«절반»만** 잰다(우리는 False «만» 버린다)  ← «범위». 손글씨")
    P("   🔢 ⛔ 「대박의 70%%가 실적이 좋다」 — 기저율이 **%.1f%%** 라 **«차»로만** 말한다" % base_rate)
    P("   🔢 ⛔ 「「크게 상승」은 «이것»이다」 — 자가 **%d 개**다. **«넷» «다» 적었다**" % len(METERS))
    P("   ⛔ **Ⓘ 를 「원전 ②의 «완전한» 구현」으로** — 우리는 `judge` **False** 만 버린다")
    P("     (**True·None 은 «이미» 산다**) ⇒ **원전이 말한 「거르지 마라」의 «일부»**다   ← «범위». 손글씨")
    P("```")
    P("")
    P("## 7. ★★★ **㉠ 과 ㉡ 을 «같이» 읽으면 — 「승자 찾기」가 «아니라» 「패자 피하기」**")
    P("")
    P("```")
    P("🚨 «따로» 보면 «어긋나» 보인다:")
    P("   ㉠ 대박군에서 실적 좋은 비율이 기저율 «보다 «낮다»»(−4.3 / −4.2%p)")
    P("   ㉡ 그런데 실적 «나쁜» 것을 버리면 **+3.686%p** 나 «좋아진다»")
    P("")
    P("✅ **어긋나지 «않는다» — «다른 것»을 말한다:**")
    P("| 등급 | n | %s |" % " | ".join("**%s**" % nm.split(" ")[0] for nm, _x in METERS))
    P("|---|---:|%s" % ("---:|" * len(METERS)))
    for g, gl in ((True, "True «가속»"), (None, "None «판정 불가»"), (False, "**False** «버린 것»")):
        sub = [r for r in good if r[0] is g]
        P("| %s | %s | %s |"
          % (gl, format(len(sub), ","),
             " | ".join("%.1f%%" % (100.0 * sum(1 for r in sub if r[1] >= th) / max(len(sub), 1))
                        for th in (good[max(1, n_g // 100) - 1][1], good[max(1, n_g // 20) - 1][1],
                                   1.0, 0.30))))
    P("")
    # 🚨 결론을 «표»에서 «생성»한다 — 손으로 적으면 표와 «어긋난다»(오늘 두 번 났다)
    ths = (good[max(1, n_g // 100) - 1][1], good[max(1, n_g // 20) - 1][1], 1.0, 0.30)
    rate = {}
    for g in (True, None, False):
        sub = [r for r in good if r[0] is g]
        rate[g] = [100.0 * sum(1 for r in sub if r[1] >= th) / max(len(sub), 1) for th in ths]
    lowest_F = all(rate[False][i] == min(rate[True][i], rate[None][i], rate[False][i])
                   for i in range(len(ths)))
    highest_N = all(rate[None][i] == max(rate[True][i], rate[None][i], rate[False][i])
                    for i in range(len(ths)))
    P("")
    P("## ⇒ ★★ **표가 «말하는» 것 — «생성»된 문장이다:**")
    P("   **False «버린 것»**이 네 자 %s 에서 대박이 **%s**"
      % ("**전부**" if lowest_F else "**일부**", "**제일 «낮다»**" if lowest_F else "«섞인다»"))
    P("     ⇒ ✅ **버려도 «승자를 «크게» 잃지 «않는다»»** — 그래서 ①−Ⓓ 가 «양수»다")
    P("   🚨 **None «판정 불가»**가 네 자 %s 에서 대박이 **%s** (%.1f / %.1f / %.1f / %.1f%%)"
      % ("**전부**" if highest_N else "**일부**", "**제일 «높다»**" if highest_N else "«섞인다»",
         rate[None][0], rate[None][1], rate[None][2], rate[None][3]))
    P("     ⇒ ★★ **㉠ 이 «음수»로 나온 «이유»가 «여기»다** — 대박군을 «채운» 것은")
    P("       **True 가 아니라 «None»**이고, 그래서 **True 의 «몫»이 기저율 아래로 밀렸다**")
    P("")
    P("## ⇒ 🔴🔴 **«정정**(2026-09-03 · `170`·`172`) — 이 문장이 «두 번» 바뀌었다:**")
    P("")
    P("   🔴 처음: 「실적이 «좋으면» 대박」이 아니라 — **「실적을 «잴 수 «없으면»» 대박」**")
    P("     (그리고 「None = «신생·소형»이 많을 자리」라 «덧붙였다»)")
    P("   🔴 `170`: **「신생」도 「소형」도 «틀렸다»** — N1(이력 부족) **2.7%** · 중·대형 **91.6%**")
    P("   🔴 `172`: **「«잴 수 없으면»」도 «틀렸다»** — 코드를 읽으니 `_yoy` 의 `prev <= 0` 때문에")
    P("     **None 의 «90.2%»가 «전년동기 «적자»»**다(값이 «있는데» 규칙이 «버린» 것)")
    P("")
    P("   ## ✅ **고친 문장: 「«전년동기»가 «적자»면 대박」**")
    P("   ⇒ ★ **«자료» 이야기가 «아니라» «회사» 이야기**이고 —")
    P("     🚨 **진입 시점에 «완전히» 관측 «가능»**하다(`asof` 가 «집은» 값이다)")
    P("   ⇒ 🚨 그리고 그건 **«우리 «규칙»의 성질»**이기도 하다 — `_yoy` 가 «적자»를 «판정 불가»로 «보낸다»")
    P("   ⛔ **「`_yoy` 를 «고치자」」로 «가지» 않는다** — `92`·`94`·`103`·`147` 이 «전부» 바뀐다(«다른 판»)")
    P("   ⇒ ⛔ 그러니 **「실적이 «무의미»하다」로도, 「실적이 «먹힌다»」로도 «못» 쓴다**")
    P("     ✅ 쓸 수 있는 말: **「`judge` **False** 를 버리는 것은 «값»을 한다(+%.3f%%p).**"
      % dif("①", "Ⓓ")[0])
    P("       **그러나 «대박»을 «부르는» 것은 True 가 «아니라» None 이다」**")
    P("")
    P("🚨 **안 잰 것 «둘»:**")
    P("   ① **«꼬리»의 «크기»** — 「대박을 «놓치는» 값」과 「패자를 «피하는» 값」을 «갈라» 재지 «않았다»")
    P("   ② **None 이 «무엇»인지** — 「자료가 «없는» 종목」의 «성격»(신생·소형·상장 직후 …)을 «안» 봤다")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 손절 −10 · 목표 +30",
                     "같은 칸 5", "**같은 검출기**"]):
        P(ln)
    P("🚨 **Ⓓ 의 «%d × %d = %d» 은 «유효 n» 이 «아니다»** — 배정 축은 «평균»으로 «없앴고»,"
      % (n_seed, n_as, n_seed * n_as))
    P("   남은 축은 **씨앗 %d** 이며 그것도 위 목록 때문에 **«유효 n = 1»** 이다" % n_seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
