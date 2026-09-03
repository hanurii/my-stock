# -*- coding: utf-8 -*-
r"""173 — **「«적자»를 «골라» 사면 «계좌»가 어떻게 되나」** · 사전등록 `tasks/173-buy-the-losers.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  🚨 **「고르기」의 «열두 번째»다** — 앞 열한 판이 «다» 실패했다
     ⇒ ⛔ **「이번엔 «다르다」」를 «안» 쓴다.** 다른 점은 «하나»뿐 —
        **«우리가 «찾은»» 축**이지 «원전»이 준 축이 «아니다**

  🚨 **「대박률」과 「계좌」는 «다른 자»다:**
     `92` 꼬리 **+6.65** 인데 **계좌 −61.05%p** · 기억 「«꼬리» 넓히는 칸 ≠ «기대값» 올리는 칸」

  🚨 **이 판은 «합 검산»을 «걸 수 «없다»»** — Ⓚ 와 Ⓛ 이 «겹치지» 않아 **«분해»가 «없다»**
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
CACHE = Path(str(r91.OUT / "173-partial.json"))
TERMS = (("e0", "eps", 0), ("e1", "eps", 1), ("r0", "revenue", 0), ("r1", "revenue", 1))


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    dry = "--dry" in sys.argv
    P = print
    P("=" * 104)
    P("173 — **「«적자»를 «골라» 사면 «계좌»가」** · 씨앗 %d × 배정 %d%s"
      % (n_seed, n_as, "  🚨 **--dry(«구조»만)**" if dry else ""))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/173-buy-the-losers.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## 🚨 **「고르기」의 «열두 번째»다**")
    P("")
    P("```")
    P("앞 «열한» 판이 «다» 실패했다 ⇒ ⛔ **「이번엔 «다르다」」를 «안» 쓴다**")
    P("다른 점은 «하나»뿐 — **«우리가 «찾은»» 축**이지 «원전»이 준 축이 «아니다**")
    P("")
    P("🚨 **「대박률」과 「계좌」는 «다른 자»다:**")
    P("   `92` 꼬리 **+6.65** 인데 **계좌 −61.05%p** · 「«꼬리» 넓히는 칸 ≠ «기대값» 올리는 칸」")
    P("   ⇒ ⛔ **「대박률이 높으니 계좌도 오른다」로 «안» 쓴다 — «그게» 이 판이 «묻는» 것이다**")
    P("")
    P("🚨 **이 판은 «합 검산»을 «걸 수 «없다»»**")
    P("   Ⓚ(N2(ii)만)와 Ⓛ(True만)은 **«겹치지» 않는다** ⇒ **«분해»가 «없다»**")
    P("   ⇒ ★ 지금까지 «전부» 합 검산이 «있었으므로» — **«없다»는 사실을 «적어» 둔다**")
    P("   ⇒ ✅ 대신 **«팔마다» 플라세보**(Ⓓ·Ⓔ)를 «따로» 둔다(유형 62)")
    P("```")
    P("")
    P("## 🚨 **Δ 를 «쓴다» — `171` 과 «반대»다**")
    P("")
    P("```")
    P("이 판의 자 = **«계좌» 연환산 (%p)**  ⇒  **Δ(1.23) 가 «같은 자»**다 ⇒ **쓴다**")
    P("(`171` 은 **«비율» (%p)**이라 **«안» 썼다** — 유형 67)")
    P("")
    P("**판정칸 1 = CI «하한» ≥ +Δ**  ·  **판정칸 2 = CI «상한» ≤ −Δ**  ·  「그 사이」엔 **«부호»를 «항상»**")
    P("")
    P("🚨 **㉯ — 📏폭은 «넓어질» 것이다**(대박률이 «진짜로» 높다: +100% 자 **15.3% vs 8.4%**)")
    P("   ⇒ 그래서 **판정칸 1 안에서 1a/1b 를 «미리» 가른다:**")
    P("     **1a** 📏폭이 «안» 넓어짐        ⇒ ✅ 「**«공짜»로 얻는다**」")
    P("     **1b** 🚨 📏폭이 «크게» 넓어짐   ⇒ 「**«운»을 «키워» 얻었다 — «값»을 «치렀다»**」")
    P("```")
    P("")
    P("## 🔎 **SE★ — 「없다」엔 «명령»과 «돌린 자리»**")
    P("")
    P("```")
    P("자리 `%s`" % os.getcwd().replace("\\\\", "/"))
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    def why_term(arq, j, fld, off):
        def g(k):
            return arq[k][ix[fld]] if 0 <= k < len(arq) else None
        cur, prev = g(j - off), g(j - off - 4)
        if r103._nan(cur):
            return "cur"
        if r103._nan(prev) or prev is None:
            return "prev"
        if prev <= 0:
            return "neg"
        return None

    cur_neg = cur_pos = cur_na = 0
    kept, K, L, byyear = set(), set(), set(), {}
    for y in sorted(by2):
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            ok_ = (a is not None
                   and r102._ord(p["entry_date"]) - r102._ord(a[0]) <= r102.STALE_MAX)
            byyear.setdefault(p["entry_date"][:4], []).append(p)
            if not ok_:
                kept.add(id(p))
                continue
            j = arq.index(a)
            v = r103.judge(arq, j, ix, 1, 2)
            if v is not False:
                kept.add(id(p))
            if v is True:
                L.add(id(p))
                continue
            if v is not None or j < 5:
                continue
            hit = None
            for nm, fld, off in TERMS:
                w = why_term(arq, j, fld, off)
                if w is not None:
                    hit = w
                    break
            if hit == "neg":
                K.add(id(p))
                # 🚨 물음 ① — 「그 «분기»가 적자」인가 「«지금»도 적자」인가
                cur = arq[j][ix["eps"]] if j < len(arq) else None
                if cur is None or r103._nan(cur):
                    cur_na += 1
                elif cur <= 0:
                    cur_neg += 1
                else:
                    cur_pos += 1

    P("")
    P("## 1. 🚨 **물음 ① — 「N2(ii)」가 「«적자»」와 «같은 자»인가**")
    P("")
    P("```")
    P("🚨 `_yoy` 의 `prev<=0` 은 **「«전년동기» 분기가 적자」**다 —")
    P("   **「회사가 «지금» 적자 «상태»」와 «같은 자»가 «아닐» 수 있다**")
    P("")
    P("✅ **«직접» 쟀다 — N2(ii) %s 건에서 «이번» 분기 EPS 의 부호:**"
      % format(len(K), ","))
    tot = max(cur_neg + cur_pos + cur_na, 1)
    P("   **«이번»도 «적자»(≤0)** — **%s** (**%.1f%%**)" % (format(cur_neg, ","), 100.0 * cur_neg / tot))
    P("   **«이번»은 «흑자»(>0)** — **%s** (**%.1f%%**)" % (format(cur_pos, ","), 100.0 * cur_pos / tot))
    P("   «이번»이 «없음/NaN»   — **%s** (**%.1f%%**)" % (format(cur_na, ","), 100.0 * cur_na / tot))
    P("")
    if cur_neg > 0.7 * tot:
        P("## ⇒ ✅ **대체로 «같은 자»다** — %.1f%%가 **«이번»도 «적자»**" % (100.0 * cur_neg / tot))
        P("   🚨 단 **%.1f%%는 «흑자로 «돌아선»»** 것이다 ⇒ **「적자 «상태»」로 «뭉개면» «틀린다»**"
          % (100.0 * cur_pos / tot))
    else:
        P("## ⇒ 🔴 **«같은 자»가 «아니다»** — «이번»도 적자는 **%.1f%%**뿐이다"
          % (100.0 * cur_neg / tot))
        P("   ⇒ ⛔ **팔 이름을 「«적자»」로 «쓰면» «오도»다**")
        P("   ✅ 정확한 이름: **「«전년동기» 분기가 «적자»였던 것」**")
    P("")
    P("★ **어느 쪽이든 팔 «자체»는 «안» 바꾼다** — 재는 것은 **`_yoy` 가 «버리는» 그 집합**이고,")
    P("  그게 **`168` 헤드라인을 «만든» 집합**이다. **바꾸면 «다른 물음»이 된다**")
    P("```", flush=True)

    def build(sel, drop=None):
        out_, npre = [], 0
        for y in sorted(by2):
            open_until = {}
            for p in by2[y]:
                if not sel(p):
                    continue
                if drop is not None and id(p) in drop:
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
        return out_

    ARMS = {"①": lambda p: id(p) in kept,
            "Ⓚ": lambda p: id(p) in K,
            "Ⓛ": lambda p: id(p) in L}
    n_pre = {"①": len(kept), "Ⓚ": len(K), "Ⓛ": len(L)}
    P("")
    P("## 2. 관문 SA★ · SB★ — **「살 수 «있었던» 수」와 「담기는 수」**")
    P("")
    P("```")
    n_all = sum(len(v) for v in byyear.values())
    for nm in ("①", "Ⓚ", "Ⓛ"):
        P("   %s  «담기는» 수 **%s** / 후보 %s (**%.1f%%**)"
          % (nm, format(n_pre[nm], ","), format(n_all, ","), 100.0 * n_pre[nm] / n_all))
    P("")
    P("🚨 **SA★ — 플라세보는 「사려고 «시도»해 «담기는» 수」에 맞춘다**(«실현» 거래 수가 «아니다»)")
    P("   («실현» 수에 맞추면 **«결과»에 조건을 다는** 셈이다)")
    P("   Ⓓ ↔ Ⓚ **%s**  ·  Ⓔ ↔ Ⓛ **%s**" % (format(len(K), ","), format(len(L), ",")))
    P("")
    P("🚨 **SF★ — 「같은 수」를 쓸 때 «어느» 수인지 «적는다»**(오늘 «두 번» 걸렸다)")
    P("   위 「%s」는 **«중복제거 «전»» 후보 수**다 — 아래 표의 「거래」는 **«중복제거 «뒤»»**다"
      % format(len(K), ","))
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
            rs = [r91.sl.sim_lots(ev, seed=sd, slots=SLOTS, risk=0.02, cap=0.20,
                                  reserve=False, fill_rule="truncate",
                                  cash_rule="per_slot") for sd in range(n_seed)]
        v = [acc.account(x) for x in rs]
        m = {"expo": st.median([x["expo_mean"] for x in rs]), "n": len(ev)}
        cache[key] = [list(a) for a in v]
        cache[key + "|m"] = m
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        return v, m

    out, meta = {}, {}
    for nm, sel in ARMS.items():
        out[nm], meta[nm] = sim(build(sel), "v1|%s|n%d" % (nm, n_seed))
        P("  %s %.0f만(%d)" % (nm, st.median([a[0] for a in out[nm]]), meta[nm]["n"]), flush=True)

    for dn, target in (("Ⓓ", K), ("Ⓔ", L)):
        accs, exs, ns = [], [], []
        for ai in range(n_as):
            rg = random.Random(ai + 1_000_000 + len(target))
            keepset = set()
            for y, ks in byyear.items():
                n_t = sum(1 for p in ks if id(p) in target)
                keepset |= {id(p) for p in rg.sample(ks, min(n_t, len(ks)))}
            v, m = sim(build(lambda p, s=keepset: id(p) in s),
                       "v1|%s|a%d|n%d" % (dn, ai, n_seed))
            accs.append(v)
            exs.append(m["expo"])
            ns.append(m["n"])
        out[dn] = [tuple(st.mean(accs[ai][i][j] for ai in range(n_as)) for j in range(4))
                   for i in range(n_seed)]
        meta[dn] = {"expo": None, "expo_d": exs, "n": st.mean(ns)}
        P("  %s %.0f만(%.0f · 배정 %d개 평균)"
          % (dn, st.median([a[0] for a in out[dn]]), meta[dn]["n"], n_as), flush=True)

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    def dif(x, y):
        d = [acc.cagr(out[x][i][0], YRS) - acc.cagr(out[y][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("")
    P("## 3. 관문 — 수")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①"]])
    P("**MA★ 앵커** — ① **%.0f만** vs %s만  →  %s   («열한 번째»)"
      % (m1, format(MA_REF, ","), "✅ **일치**" if abs(m1 - MA_REF) < 1.0 else "🚨 **멈춘다**"))
    P("")
    P("**SD★ 노출 — «팔마다» «반복문»으로** · ⛔ **«보정» «금지»**(유형 73 — 노출은 팔의 «결과»)")
    for nm in ("①", "Ⓚ", "Ⓛ", "Ⓓ", "Ⓔ"):
        if meta[nm]["expo"] is not None:
            P("   %-2s **%.1f%%**" % (nm, meta[nm]["expo"]))
        else:
            e = meta[nm]["expo_d"]
            P("   %-2s **%.1f ~ %.1f%%**(중앙 **%.1f%%**)" % (nm, min(e), max(e), st.median(e)))
    P("```")

    P("")
    P("## 4. 팔 다섯 — 🚨 **SC★ 📏폭을 «전부»**")
    P("")
    P("| 팔 | 거래 | 세후 총액(중앙) | 연 환산 | **📏폭** | 낙폭 중앙 | 회복 |")
    P("|---|---:|---:|---:|---:|---:|---:|")
    for nm in ("①", "Ⓚ", "Ⓛ", "Ⓓ", "Ⓔ"):
        v = out[nm]
        mm = st.median([a[0] for a in v])
        P("| **%s** | %.0f | %.0f만 | **%+.2f%%** | **%.2f** | %+.1f%% | %.1f년 |"
          % (nm, meta[nm]["n"], mm, acc.cagr(mm, YRS), spread(v),
             st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0))

    P("")
    P("## 5. 판정")
    P("")
    P("| 짝 | 차 | **95% CI** | 📏폭 | 판정칸 |")
    P("|---|---:|---|---:|:--|")
    for lab, x, y in (("**Ⓚ−Ⓓ** «적자»를 골라 삼 ★판정", "Ⓚ", "Ⓓ"),
                      ("Ⓛ−Ⓔ «가속»만 삼 (대조)", "Ⓛ", "Ⓔ"),
                      ("Ⓚ−① «참고»", "Ⓚ", "①")):
        mu, lo, hi = dif(x, y)
        sx, sy = spread(out[x]), spread(out[y])
        if lo >= DELTA:
            vd = ("**1a** ✅ CI 하한 ≥ +Δ · 📏폭 «안» 넓어짐 — **«공짜»로 얻는다**"
                  if sx <= sy * 1.1 else
                  "**1b** 🚨 CI 하한 ≥ +Δ «인데» 📏폭이 **%.2f → %.2f** — **«운»을 «키워» 얻었다**"
                  % (sy, sx))
        elif hi <= -DELTA:
            vd = "**2** 🚨 CI «상한» ≤ −Δ"
        elif lo > 0:
            vd = "**4** «확실히» «양수»인데 Δ 미만"
        elif hi < 0:
            vd = "**4** ⚠️ «확실히» «음수»인데 Δ 미만"
        else:
            vd = "🚨 **못 가린다**"
        P("| %s | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f vs %.2f | %s |"
          % (lab, mu, lo, hi, sx, sy, vd))

    P("")
    P("```")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ 「«적자»가 «좋다»/«나쁘다»」 — 잰 건 **«우리 규칙 «위»»에서 «골라» 산 것**   ← «범위». 손글씨")
    P("   ⛔ 「`92` 와 «같은» 것」 — **roe(수준)** vs **전년동기 EPS «부호»** ⇒ «다른 자»")
    P("     🔢 그리고 **«겹치는 종목 수»를 «안» 셌다**")
    P("   ⛔ 「대박률이 높으니 계좌도 오른다」 — **그게 «이 판이 묻는» 것**이다")
    P("   ⛔ 「이번엔 «다르다」」(«열두 번째»)  ·  ⛔ 「또 실패했다」로 «세게 «닫기»»(**유형 78**)")
    P("   ⛔ **노출 «보정»**(유형 73)  ·  ⛔ **팔 이름을 「적자」로**(위 §1 참조)")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 손절 −10 · 목표 +30",
                     "같은 칸 5", "**같은 검출기**"]):
        P(ln)
    P("🚨 **그리고 이 판엔 «합 검산»이 «없다»** — Ⓚ·Ⓛ 이 «겹치지» 않아 «분해»가 «없다**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
