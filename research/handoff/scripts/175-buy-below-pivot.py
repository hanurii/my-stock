# -*- coding: utf-8 -*-
r"""175 — **「피벗보다 «싸게» 산다」**(원전 ①) · 사전등록 `tasks/175-buy-below-pivot.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  🚨 **머리에 «라벨 둘»** — `174` 가 낸 것:
     ① **「합의 판정은 «사실상» VCP 의 판정이다」** — 후보의 **VCP 76.9%** · 3C 20.8% · PP 2.3%
     ② **「α 가 «세 검출기»에 «다른 뜻»이다」** —
        **VCP 는 「«종가» 최고 − α」 · 3C·PP 는 「«장중 고가» − α」** ⇒ **«같은 α»가 «다른 자리»**

  🔴 **설계가 «돌리기 «전»»에 «한 번» 바뀌었다** — 원래 Ⓝ′ 는 **«항등식»**이었다:
     「−α 에 닿았고 «나중에» 피벗도 «넘은» 것」 ⇒ 후보는 **«전부»** 피벗을 넘는다(고가<피벗 **0건**)
     ⇒ **Ⓝ = Ⓝ′** ⇒ 분해가 **0**  ⇒  **Ⓝ″(집합을 «맞춘» 대조)로 «바꿨다»**
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
ALPHAS = (0.005, 0.0065, 0.010)
MA_REF = 12377
NA_TOL = 0.01
DET = next((a.split("=", 1)[1].upper() for a in sys.argv if a.startswith("--det=")), None)
if "--vcp" in sys.argv:                 # 옛 이름 — 같은 것
    DET = "VCP"
if DET not in (None, "VCP", "3C", "PP"):
    raise SystemExit("--det= 는 VCP · 3C · PP 중 하나여야 한다: %r" % DET)
CACHE = Path(str(r91.OUT / ("175%s-partial.json" % ("_" + DET.replace("3C", "c").replace("PP", "p").replace("VCP", "v") if DET else ""))))


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    dry = "--dry" in sys.argv
    P = print
    P("=" * 104)
    P("175 — **「피벗보다 «싸게» 산다」**(원전 ①) · 씨앗 %d판%s"
      % (n_seed, "  🚨 **--dry(«구조»만)**" if dry else ""))
    P("=" * 104)
    if DET:
        P("")
        P("## 🆕🚨 **`--det=%s` — 후보를 **%s «만»**으로 «좁혀» 돌린 판이다**(179 ③ · «강건성 검사»)" % (DET, DET))
        P("")
        P("```")
        P("⛔ **판정을 «새로» 내지 «않는다»** — 「«바뀌나 / 안 바뀌나»」 «하나»만 본다")
        P("🚨 **MA★ 이 12,377만과 «다른» 것이 «정상»이다** — «유니버스»가 «다르다**")
        P("🚨 **N 이 «줄어» CI 가 «넓어질» 수 있다** ⇒ 「판정칸이 바뀐 것」 ≠ 「효과가 바뀐 것」")
        P("   ⇒ ✅ **«점추정 이동»과 «CI 폭»을 «같이»** 읽는다")
        P("```")
        P("")
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/175-buy-below-pivot.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## 🚨🚨 **머리에 «라벨 둘» — `174` 가 낸 것**")
    P("")
    P("```")
    P("① ## **「합의 판정은 «사실상» **VCP** 의 판정이다」**")
    P("   후보 — **VCP 76.9%** · 3C 20.8% · PP 2.3%  ⇒  **「합」이라는 낱말이 «뭉개지» 않게 «적는다»**")
    P("")
    P("② ## **「α 가 «세 검출기»에 «다른 뜻»이다」**")
    P("   **VCP** 는 「**«종가»** 최고 − α」  ·  **3C·PP** 는 「**«장중 고가»** − α」")
    P("   ⇒ **«같은 α»가 «다른 자리»**다")
    P("")
    P("🚨 **검출기별로 «갈라» 판정하지 «않는다»** — 3 검출기 × 3 α = **«아홉» 칸**이면")
    P("   **자유도가 «크게» 는다**(`23` 래칫: 효과가 «전혀» 없어도 최선을 고르면 귀무 95% **+87.47%p**)")
    P("   ⇒ ✅ **판정은 «합» «하나». 검출기별은 «묘사»로만**")
    P("```")
    P("")
    P("## ★★★ **원전이 «묻는» 것은 «한 조각»뿐이다**")
    P("")
    P("```")
    P("# **원전 = `Ⓝ − Ⓝ″` «하나»**  (「같은 것을 «더 싸게» 사도 «얻는 것이 없다」)")
    P("")
    P("나머지 «둘»은 **«우리» 이야기**이고 **«원전»과 «무관»**하다:")
    P("   `Ⓝ″ − Ⓓ″` = 「**«갭업»한 것을 «버리는»** 값」")
    P("   `Ⓓ″ − ①`  = 「**«덜 사는 것» «자체»**」  ← **플라세보가 «흡수»**")
    P("⇒ ⛔ **「원전이 맞다/틀리다」를 `Ⓝ−①` 로 «말하지» 않는다**")
    P("```")
    P("")
    P("## 🔴 **«라벨»이 틀렸었다 — 「−α 는 «더» 산다」가 «아니다»**")
    P("")
    P("```")
    P("🔴 한때 이렇게 적을 뻔했다: 「+α 는 «덜» 산다 / **−α 는 «같이/더» 산다**」")
    P("✅ 실제(**«장전 예약 «지정가»»**):")
    P("   **+α** 「«고가» ≥ pivot+α」여야 체결 ⇒ 덜 삼 ⇒ **「«약하게» 오른 것」을 «거름»**")
    P("   **−α** 「«저가» ≤ pivot−α」여야 체결 ⇒ 🚨 **«또» 덜 삼** ⇒ **「«갭업»한 것」을 «거름»**")
    P("")
    P("## ⇒ ✅ **「«둘 다» «덜» 산다. 다만 «다른 것»을 «거른다»」**")
    P("   ⛔ 「거울」도 ⛔ 「구조가 «비대칭»」도 «아니다** — **«물음»이 대칭이지 «구조»가 아니다**")
    P("")
    P("🚨 **«원인»**: 「가격을 «낮추면» 더 산다」는 **«시장가/즉시체결»의 «직관»**이었다")
    P("   그런데 **집행 방식이 «기억»에 «있었다**(`entry-execution-method` — 장전 예약 · `max(pivot,open)`)")
    P("   ⇒ ★ **「«아는» 것을 «안» 대고 «직관»으로 «부호»를 적었다」**")
    P("```")
    P("")
    P("## 🚨 **사전 근거 — `Ⓝ″−Ⓓ″`(«갭업» 버리기)가 «음수»일 «강한» 근거가 «있다**")
    P("")
    P("```")
    P("🔎 `22` — **「≥3배 날 갭업 «35.4%» vs 나머지 «21.9%» — 핵심은 «꼬리»」**")
    P("   (**사용자 «본인 이유»가 검정을 «통과»한 «드문» 자리**다)")
    P("")
    P("⇒ ★ **Ⓝ 은 «갭업»한 것을 «버린다»** ⇒ **`Ⓝ″−Ⓓ″` 가 «음수»일 «사전» 근거가 «있다**")
    P("⇒ 🚨 **«미리» 적는다 — 안 적으면 음수가 나왔을 때 「원전이 맞았다」로 «오귀속»된다**")
    P("   **원전은 «가격»만 말했다. «갭업»은 «우리» 이야기다**")
    P("```")
    P("")
    P("## 🔴 **설계가 «돌리기 «전»»에 «한 번» 바뀌었다 — «기록»으로 남긴다**")
    P("")
    P("```")
    P("🔴 원래 설계: **Ⓝ′ = 「−α 에 닿았고 «나중에» 피벗도 «넘은» 것」**")
    P("   🔎 실측 — 후보 **24,995** 중 「진입일 «고가» < 피벗」 = **«0 건»**")
    P("   ⇒ **우리 후보는 «정의상» «전부» 피벗을 «넘는다»** ⇒ **Ⓝ = Ⓝ′** ⇒ **분해가 «0»**")
    P("   ★ 검출기 「이 «변화»가 «정의상» 저절로인가」가 **«또»** 걸렸다")
    P("")
    P("✅ **바꾼 설계: Ⓝ″ = 「−α 에 «닿는» 것」만 «현행 가격»에 삼**(집합을 «맞춘» 대조)")
    P("   **Ⓝ − Ⓝ″ = «순수 «가격»» 효과**  ← 🚨 **원전이 «묻는» 것**(「같은 것을 «더 싸게»」)")
    P("   **Ⓝ″ − Ⓓ″ = «순수 «집합»» 효과**  ← **「«갭업»을 «버리는»」 값**")
    P("   **Ⓓ″ − ①  = 「«덜 사는 것» «자체»」**  ← 🆕 **«플라세보»가 «흡수»**")
    P("   ⇒ **합 = Ⓝ − ①**  ⇒ ✅ **«항등식»이 «생긴다»**")
    P("")
    P("   🚨 **Ⓓ″ 를 «안» 두면** — `Ⓝ″−①` 안에 「«집합»이 나쁘다」와 「«덜 사는 것» «자체»」가")
    P("     **«섞인다»**. `165`·`166`·`167` 은 **«항상»** 그 자리에 플라세보를 깔았다")
    P("   🚨 **Ⓝ″ 는 «분해 «전용»»**이다 — 「그날 «저가»가 −α 아래인가」는 **«장전»에 «모른다»**")
    P("     ⇒ **«판정»에 «안» 쓴다**(`165` Ⓔ 와 «같은 격»)")
    P("")
    P("🔴 **그리고 방향 ㉰ 의 «부호»가 «반대»였다:**")
    P("   🔴 원래: 「사는 «수»가 «늘» 것」")
    P("   ✅ 실제: 피벗−α 지정가는 **「저가 ≤ 피벗−α」여야 «체결»** ⇒ **«갭업» 건을 «못» 산다**")
    P("     (현행 `max(pivot, open)` 은 **갭업에도 «산다»**)")
    P("   ⇒ ✅ **관문의 «방향»을 «뒤집었다»: 「사는 수가 «줄지» «않으면» 구현이 «틀렸다»」**")
    P("   ★ **「예측을 «관문»으로 옮긴」 것은 맞았고 「«방향»」이 틀렸다 — «둘»은 «다른» 잘못이다**")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("「피벗보다 «싸게» 사도 얻는 것이 없다」 ← 출처: 원전 «글자**")
    P("α 격자 0.5 / 0.65 / 1.0%              ← 0.65% 는 `165` 의 **원전 20센트 «환산값»**")
    P("체결가 `max(pivot−α, open)`            ← 사용자 방식(장전 예약) 모사와 **«일관»**")
    P("Δ = 1.23%p                             ← 150 의 우리−QQQ 격차")
    P("MA★ 기준 %s만                      ← 156·161~168·170·173 의 ①" % format(MA_REF, ","))
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    keep = {}
    for y in sorted(by2):
        keep[y] = []
        for p in by2[y]:
            if DET and p.get("pattern") != DET:   # 🆕 «한 갈래»만(179 ③)
                continue
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                keep[y].append(p)

    def touch(p, al):
        pv = p.get("pivot")
        lo = p["l"][0]
        return pv is not None and lo is not None and lo <= pv * (1.0 - al)

    def build(mode, al=0.0, ksel=None):
        """mode: base(①) | N(−α 가격) | N2(같은 집합 · 현행 가격) | D(무작위 같은 수)"""
        out_, n_open, n_lvl = [], 0, 0
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                if mode in ("N", "N2") and not touch(p, al):
                    continue
                if mode == "D" and ksel is not None and id(p) not in ksel:
                    continue
                q = p
                if mode == "N":
                    pv = p["pivot"]
                    o0 = (p.get("o") or [None])[0]
                    lvl = pv * (1.0 - al)
                    q = dict(p)
                    q["entry_price"] = lvl if o0 is None else max(lvl, o0)
                    if o0 is not None and o0 > lvl:
                        n_open += 1
                    else:
                        n_lvl += 1
                t = pt.resolve_trade(q, ft="limit", fs="market", stop=STOP, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                t["stop_frac"] = STOP / 100.0
                out_.append(t)
        return out_, n_open, n_lvl

    base, _, _ = build("base")
    n_all = sum(len(v) for v in keep.values())
    P("")
    P("## 1. 관문 — 구조")
    P("")
    P("```")
    P("**㉰ «뒤집힌» 관문 — 「사는 수가 «줄지» «않으면» 구현이 «틀렸다»」**")
    P("")
    P("| α | 「−α 에 «닿는»」 후보 | 후보 중 | «못» 사는 것 | 판정 |")
    P("|---|---:|---:|---:|:--|")
    npre = {}
    for al in ALPHAS:
        k = sum(1 for y in keep for p in keep[y] if touch(p, al))
        npre[al] = k
        P("| **%.2f%%** | %s | **%.1f%%** | **%.1f%%** | %s |"
          % (100 * al, format(k, ","), 100.0 * k / n_all, 100.0 * (n_all - k) / n_all,
             "✅ **줄었다**" if k < n_all else "🚨 **안 줄었다 — 멈춘다**"))
    P("")
    P("★ **「«갭업»을 «못» 산다」**가 그 «기전»이다 — 현행 `max(pivot, open)` 은 갭업에도 «산다**")
    P("```", flush=True)
    if any(npre[al] >= n_all for al in ALPHAS):
        return 3
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

    out, meta, fills = {}, {}, {}
    byyear = {y: list(v) for y, v in keep.items()}
    out["①"], meta["①"] = sim(base, "v1|base|n%d" % n_seed)
    P("")
    P("  ① %.0f만(%d)" % (st.median([a[0] for a in out["①"]]), meta["①"]["n"]), flush=True)
    for al in ALPHAS:
        evN, n_open, n_lvl = build("N", al)
        evN2, _, _ = build("N2", al)
        fills[al] = (n_open, n_lvl)
        kN, kN2 = "N%.4f" % al, "M%.4f" % al
        out[kN], meta[kN] = sim(evN, "v1|N|%.4f|n%d" % (al, n_seed))
        out[kN2], meta[kN2] = sim(evN2, "v1|M|%.4f|n%d" % (al, n_seed))
        # 🆕 Ⓓ″ — 「Ⓝ″ 와 «같은 수»를 «무작위»로 «버림»」 (중복제거 «전»)
        accs, exs, ns = [], [], []
        for ai in range(n_as):
            rg = random.Random(ai + 1_000_000 + int(al * 1e6))
            ksel = set()
            for y, ks in byyear.items():
                n_t = sum(1 for p in ks if touch(p, al))
                ksel |= {id(p) for p in rg.sample(ks, min(n_t, len(ks)))}
            evD, _, _ = build("D", al, ksel)
            v, m = sim(evD, "v2|D|%.4f|a%d|n%d" % (al, ai, n_seed))
            accs.append(v)
            exs.append(m["expo"])
            ns.append(m["n"])
        kD = "D%.4f" % al
        out[kD] = [tuple(st.mean(accs[ai][i][j] for ai in range(n_as)) for j in range(4))
                   for i in range(n_seed)]
        meta[kD] = {"expo": None, "expo_d": exs, "n": st.mean(ns)}
        P("  α %.2f%% — Ⓝ %.0f만(%d) · Ⓝ″ %.0f만(%d) · Ⓓ″ %.0f만(%.0f)"
          % (100 * al, st.median([a[0] for a in out[kN]]), meta[kN]["n"],
             st.median([a[0] for a in out[kN2]]), meta[kN2]["n"],
             st.median([a[0] for a in out[kD]]), meta[kD]["n"]), flush=True)

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    def dif(x, y):
        d = [acc.cagr(out[x][i][0], YRS) - acc.cagr(out[y][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("")
    P("## 2. 관문 — 수")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①"]])
    P("**MA★ 앵커** — ① **%.0f만** vs %s만  →  %s"
      % (m1, format(MA_REF, ","), "✅ **일치**" if abs(m1 - MA_REF) < 1.0 else "🚨 **멈춘다**"))
    P("")
    P("**합 검산 «항등식»** — |(Ⓝ−Ⓝ″)+(Ⓝ″−Ⓓ″)+(Ⓓ″−①) − (Ⓝ−①)| < %.2f%%p" % NA_TOL)
    for al in ALPHAS:
        kN, kM, kD = "N%.4f" % al, "M%.4f" % al, "D%.4f" % al
        e = (dif(kN, kM)[0] + dif(kM, kD)[0] + dif(kD, "①")[0] - dif(kN, "①")[0])
        P("   α %.2f%%  오차 **%+.4f%%p**  →  %s"
          % (100 * al, e, "✅" if abs(e) < NA_TOL else "🚨 **멈춘다**"))
    P("")
    P("**체결 «갈래» — 「체결가가 «시가»인가 «−α»인가」**(⛔ 「갭다운」이라는 «이름»은 «안» 쓴다)")
    P("   🚨 «시가»가 «이미» −α 아래인 것이 «절반» 가까이다 ⇒ **그건 「갭다운」이 «아니라» «보통»이다**")
    for al in ALPHAS:
        o_, l_ = fills[al]
        P("   α %.2f%%  **«−α» 체결 %s (%.1f%%)** · «시가» 체결 %s (%.1f%%)"
          % (100 * al, format(l_, ","), 100.0 * l_ / max(o_ + l_, 1),
             format(o_, ","), 100.0 * o_ / max(o_ + l_, 1)))
    P("   (`165` 의 「피벗 체결 77.3% · 시가 체결 22.7%」와 **«같은 꼴»**)")
    P("")
    P("**노출 — «팔마다»** · ⛔ **«보정» «금지»**(유형 73)")
    P("   ① **%.1f%%**" % meta["①"]["expo"])
    for al in ALPHAS:
        e_ = meta["D%.4f" % al]["expo_d"]
        P("   α %.2f%%  Ⓝ **%.1f%%** · Ⓝ″ **%.1f%%** · Ⓓ″ **%.1f ~ %.1f%%**(중앙 %.1f%%)"
          % (100 * al, meta["N%.4f" % al]["expo"], meta["M%.4f" % al]["expo"],
             min(e_), max(e_), st.median(e_)))
    P("```")

    P("")
    P("## 3. 팔 — 🚨 **팔은 «%d»이다**(① + α %d 칸 × 셋[Ⓝ·Ⓝ″·Ⓓ″]) — 📏폭 «전부»"
      % (1 + 3 * len(ALPHAS), len(ALPHAS)))
    P("")
    P("| 팔 | 거래 | 세후 총액(중앙) | 연 환산 | **📏폭** | 낙폭 중앙 | 회복 |")
    P("|---|---:|---:|---:|---:|---:|---:|")
    for nm, lab in [("①", "**①현행**")] + [
            (k, l) for al in ALPHAS
            for k, l in (("N%.4f" % al, "**Ⓝ α=%.2f%%**" % (100 * al)),
                         ("M%.4f" % al, "Ⓝ″ α=%.2f%% 🚨«분해 전용»" % (100 * al)),
                         ("D%.4f" % al, "Ⓓ″ α=%.2f%% «플라세보»" % (100 * al)))]:
        v = out[nm]
        mm = st.median([a[0] for a in v])
        P("| %s | %.0f | %.0f만 | **%+.2f%%** | **%.2f** | %+.1f%% | %.1f년 |"
          % (lab, meta[nm]["n"], mm, acc.cagr(mm, YRS), spread(v),
             st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0))

    P("")
    P("## 4. 🚨 **분해 — 「가격」과 「집합」을 «갈라»**")
    P("")
    P("| α | **Ⓝ−Ⓝ″** «가격» ★**원전** | **Ⓝ″−Ⓓ″** «갭업 버림» | **Ⓓ″−①** «덜 삼» | **Ⓝ−①** 합 | 판정(«가격»만) |")
    P("|---|---:|---:|---:|---:|:--|")
    cells = []
    for al in ALPHAS:
        kN, kM = "N%.4f" % al, "M%.4f" % al
        p1, l1, h1 = dif(kN, kM)
        kD = "D%.4f" % al
        p2 = dif(kM, kD)[0]
        p2b = dif(kD, "①")[0]
        p3 = dif(kN, "①")[0]
        if l1 >= DELTA:
            c = "**1** ✅ CI 하한 ≥ +Δ"
        elif h1 <= -DELTA:
            c = "**2** 🚨 CI 상한 ≤ −Δ"
        elif l1 > 0:
            c = "**4a** «확실히» «양수»·CI «전체»가 Δ 아래" if h1 <= DELTA else "**4b** «양수»·Δ 를 «걸침»"
        elif h1 < 0:
            c = "**4a** ⚠️ «확실히» «음수»·CI «전체»가 −Δ 위" if l1 >= -DELTA else "**4b** «음수»·Δ 를 «걸침»"
        else:
            c = "**5** 🚨 «못 가린다»"
        cells.append((al, p1, l1, h1, p2, p3, c, p2b))
        P("| **%.2f%%** | **%+.3f%%p** [%+.3f, %+.3f] | %+.3f%%p | %+.3f%%p | %+.3f%%p | %s |"
          % (100 * al, p1, l1, h1, p2, p2b, p3, c))
    P("")
    P("```")
    P("# 🚨🚨 **«제일» 큰 것 — `Ⓝ−Ⓝ″` 는 «따로» «얻을 수 «없다»»**")
    P("")
    P("**Ⓝ″ 는 「그날 «저가»가 pivot−α 아래였나」를 «알아야» 만들어진다** ⇒ 🚨 **«시점 불가»**")
    P("   ⇒ **Ⓝ″ 는 «분해 전용»이고 «팔»이 «아니다**(장전 예약으로 «못» 낸다)")
    P("")
    P("## ⇒ ★★★ **「«가격» 조각만 «취하고» «갭업 버림»·«덜 삼»은 «피한다」」는 «불가»다**")
    P("## **Ⓝ 은 «실행 가능»하다 — 그 «안»에서 «조각»을 «골라 가질» 수는 «없다**")
    P("")
    P("**«실제로» 얻는 것 = «합» `Ⓝ−①`:**")
    for al_, p1_, _l_, _h_, _p2_, p3_, _c_, _b_ in cells:
        P("   α %.2f%%   **합 %+.3f%%p**    (「가격」 조각은 %+.3f%%p)" % (100 * al_, p3_, p1_))
    P("")
    P("   🔴 **α 가 커지면 «합»이 «부호»를 «바꾼다» — %s**"
      % " → ".join("%+.3f" % c[5] for c in cells))
    P("")
    P("★ **`165`·`166` 의 Ⓔ 와 «다르다»** — 그건 **«천장»**(«도달 못 할» 상한)이었고")
    P("  여기 Ⓝ″ 는 **«기여분»**(«합» 안의 «한 조각»)이다. **«섞으면» 「«없는» 이득」이 된다**")
    P("```")
    P("")
    P("```")
    P("🚨 **판정 규칙 — α «세 칸» «전부» «같은 칸»이어야 「일한다」**")
    same = len({c[6].split(" ")[0] for c in cells}) == 1
    P("   실측 — %s  ⇒  %s"
      % (" · ".join("%.2f%%:%s" % (100 * c[0], c[6].split(" ")[0]) for c in cells),
         "✅ **같은 칸**" if same else "🔴 **«갈린다» ⇒ 「일한다」로 «못» 쓴다**"))
    P("")
    P("✅ **「«못» 씀」의 «이유»를 «정확»히 — 「효과가 «없다»」가 «아니다**")
    P("   🚨 「셋 «다» 같은 칸」은 **«값을 «보기 전»»에 세운 규칙**이다 ⇒ **«결과를 보고» «푸는» 것은 «금지»**")
    P("   ✅ ⇒ **「«규칙» 미통과」**이지 **「효과가 «없다»」가 «아니다**")
    P("")
    P("★ **그래서 «남길» 기록 «셋» — «수»로:**")
    P("   ㉠ **«부호»가 셋 «다» 같은가** — 양수 **%d/%d** ⇒ %s"
      % (sum(1 for c in cells if c[1] > 0), len(cells),
         "✅" if all(c[1] > 0 for c in cells) else "🚨"))
    P("   ㉡ **CI 가 셋 «다» 0 을 «배제»하는가** — **%d/%d** ⇒ %s"
      % (sum(1 for c in cells if c[2] > 0 or c[3] < 0), len(cells),
         "✅" if all(c[2] > 0 or c[3] < 0 for c in cells) else "🚨"))
    P("   ㉢ **α 가 커질수록 «단조»로 «주는»가** — %s ⇒ %s"
      % (" > ".join("%+.3f" % c[1] for c in cells),
         "✅ **단조**" if all(cells[i][1] > cells[i + 1][1] for i in range(len(cells) - 1))
         else "🚨 **아니다**"))
    P("")
    P("## ⇒ ★ **「갈린다」의 «정도»가 «작다» — 차이는 「Δ 를 «넘느냐»」 «하나»뿐이다**")
    P("   (%s — 셋 «다» 「양수·CI 0 배제」다)"
      % " · ".join("%.2f%%:%s" % (100 * c[0], c[6].split(" ")[0]) for c in cells))
    P("")
    P("🆕 ★ 「셋 다」 규칙의 «근거»(`23` 귀무 95% **+87.47%p**)는 **「«고르기»를 막는」** 것인데 —")
    P("   **«단조»는 «고르기»로는 «안» 나온다** ⇒ 「규칙이 «엄하다»」는 **«주장»할 수 «있으나**")
    P("   ⛔ **«이 판»에서 «풀지» 않는다. «다음 판»에서 «사전»에 적는다**")
    P("")
    P("## 🆕 🚨 **그러면 이 판은 「α 를 «고르는»」 문제가 «된다» — 그게 «막힌» 자리다**")
    P("")
    _bi = max(range(len(cells)), key=lambda i: cells[i][5])
    _ba = cells[_bi][0]
    _bk = "N%.4f" % _ba
    _m1 = st.median([a[0] for a in out["①"]])
    _mb = st.median([a[0] for a in out[_bk]])
    P("   **«합»이 «제일» 큰 칸 — α %.2f%%** 에서는 «넷»이 «다» ① 보다 «낫다»:" % (100 * _ba))
    P("     세후 **%.0f만** vs ① %.0f만 (**%+.0f%%**) · 연 **%+.2f%%** vs %+.2f%%"
      % (_mb, _m1, 100.0 * (_mb / _m1 - 1.0), acc.cagr(_mb, YRS), acc.cagr(_m1, YRS)))
    P("     📏폭 **%.2f** vs %.2f · 낙폭 **%+.1f%%** vs %+.1f%% · 회복 **%.1f년** vs %.1f년"
      % (spread(out[_bk]), spread(out["①"]),
         st.median([a[1] for a in out[_bk]]), st.median([a[1] for a in out["①"]]),
         st.median([a[2] for a in out[_bk]]) / 252.0, st.median([a[2] for a in out["①"]]) / 252.0))
    P("")
    P("## ⇒ 🔴 **그런데 그 칸을 «고르는» 것이 «바로» 「셋 다」 규칙이 «막는» 것이다**")
    P("   **α 를 «셋» 재고 «제일 좋은» 하나를 «고르면»** — 그건 `23` 의 «귀무 95% +87.47%p»")
    P("   (「효과가 «전혀» 없어도 여러 칸 중 «최선»을 고르면 «크게» 나온다」) «그 자리»다")
    P("")
    P("   ✅ **그래서 「서는 문장」 «옆»에 «적는다**:")
    P("     ## **「이 판은 «α 를 «고르는»» 문제로 «바뀐다» — 이 판은 그 «고르기»를 «안» 한다」**")
    P("   ⇒ ★ **«다음 판»의 «모양»이 «보인다» — α 를 «값 보기 «전»»에 «하나»로 «박고**")
    P("     **그 «하나»로 «표본 밖»(또는 «다른» 자)에서 «다시» 재는 판**이다")
    P("   🚨 **그 판을 «이 자료»에서 «또» 돌리면 «고르기»를 «한 번 더» 하는 것이다** — «자»를 «바꿔야» 한다")
    P("")
    P("★ **«네 조합» — «미리» 적은 대로 «부호»를 맞춰 읽는다:**")
    for al, p1, _l, _h, p2, _p3, _c, _p2b in cells:
        if p1 <= 0 and p2 <= 0:
            r = "원전 «맞음» + 집합도 «나쁨»"
        elif p1 <= 0 and p2 > 0:
            r = "🚨 **«집합»이 «살렸다»**(갭업을 «안» 사는 게 «이득»)"
        elif p1 > 0 and p2 <= 0:
            r = "🚨 **원전이 «틀렸는데» «집합»이 «먹었다»**"
        else:
            r = "원전 «틀림** + 집합도 «이득»"
        P("   α %.2f%%  가격 %+.3f · 집합 %+.3f  ⇒  **%s**" % (100 * al, p1, p2, r))
    P("")
    P("📏 **폭 — 「«값»을 치렀나」**(`173`: Ⓚ 는 4a 인데 폭 **1.41 → 2.22 = +57%**)")
    sp1 = spread(out["①"])
    P("   ① 폭 **%.2f**" % sp1)
    for al_ in ALPHAS:
        spN = spread(out["N%.4f" % al_])
        spM = spread(out["M%.4f" % al_])
        spD = spread(out["D%.4f" % al_])
        P("   α %.2f%%  Ⓝ **%.2f** (① 대비 **%+.0f%%**) · Ⓝ″ %.2f · Ⓓ″ %.2f"
          % (100 * al_, spN, 100.0 * (spN / sp1 - 1.0), spM, spD))
    P("   ⇒ Ⓝ 의 폭 증가는 **%+.0f ~ %+.0f%%** — `173` 의 **+57%%** 보다 **%s**"
      % (min(100.0 * (spread(out["N%.4f" % a_]) / sp1 - 1.0) for a_ in ALPHAS),
         max(100.0 * (spread(out["N%.4f" % a_]) / sp1 - 1.0) for a_ in ALPHAS),
         "«작다»" if max(spread(out["N%.4f" % a_]) / sp1 for a_ in ALPHAS) - 1.0 < 0.57
         else "«크다»"))
    P("   🚨 **Ⓓ″(«플라세보») 는 폭이 «크게» «작다»(%.2f ~ %.2f)** — 「«무작위»로 버리면 «흩어짐»이 «준다»」"
      % (min(spread(out["D%.4f" % a_]) for a_ in ALPHAS),
         max(spread(out["D%.4f" % a_]) for a_ in ALPHAS)))
    P("     ⇒ ⛔ **Ⓝ 의 폭을 «Ⓓ″»와 견주지 «않는다». «①»과 견준다**")
    P("")
    P("🚨 **사전 근거는 «빗나갔다» — «먼저» 적는다**")
    P("   «미리» 적은 것: 「`Ⓝ″−Ⓓ″`(갭업 버리기)가 **«음수»**일 «강한» 근거가 있다」(`22`)")
    P("   실측: %s  ⇒  🔴 **«양수»가 %d/%d — «빗나갔다»**"
      % (" · ".join("%+.3f" % c[4] for c in cells),
         sum(1 for c in cells if c[4] > 0), len(cells)))
    P("")
    P("✅ **그런데 «그래도» 일했다 — «나중»에 적는다**")
    P("   «안» 적었으면 **%+.3f%%p** 를 「원전이 «틀렸다»」에 **«보태»** 썼을 것이다"
      % max(c[4] for c in cells))
    P("   ⇒ ★ **「사전등록은 «맞히려고» 적는 게 아니라 «섞이지» 않게 적는다」**")
    P("   🚨 단 **«자»가 «다르다»** — `22` 는 **«꼬리»**(≥3배 날 확률) · 이 판은 **«계좌»**(%p)")
    P("")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ **Ⓝ″ 의 수를 «전략 성적»으로** — «분해 전용»이다(장전 예약으론 «못» 씀)")
    P("   ⛔ 「원전이 맞다/틀리다」를 **Ⓝ−① 로** — 원전이 «묻는» 건 **Ⓝ−Ⓝ″**(«가격») «하나»다")
    P("   ⛔ **「«대칭»인 건 «구조»다」** — ✅ **«물음»이 대칭이지 «구조»가 «아니다»**")
    P("     **+α 도 −α 도 «둘 다» «덜» 산다. 다만 «다른 것»을 «거른다»**")
    P("   ⛔ **「`Ⓝ″−Ⓓ″` 가 음수 ⇒ 원전이 맞았다」** — 그건 **«갭업»** 이야기다(`22`)")
    P("   ⛔ **검출기별로 «갈라» 판정** — 아홉 칸이면 자유도가 «크게» 는다(`23` +87.47%p)")
    P("   🔢 ⛔ 「합」을 «세 검출기»의 «평균»처럼 — **VCP 가 76.9%다**")
    P("   ⛔ 「갭다운」이라는 «이름** — 시가가 −α 아래인 건 «보통»이다(위 표)")
    P("   ⛔ **노출 «보정»**(유형 73)")
    P("   🆕 ⛔ 「**−α 로 바꾸면 %+.3f%%p 를 «얻는다**」 — **«분해 전용» 조각**이다"
      % max(c[1] for c in cells))
    P("   🆕 ⛔ 「**−α 가 «이득»이다**」 — **α 에 따라 «합»의 «부호»가 «바뀐다**(%s)"
      % " · ".join("%.2f%%:%+.3f" % (100 * c[0], c[5]) for c in cells))
    P("```")
    P("")
    P("```")
    P("## 🆕 **«다음 판»의 «정확한 이름» — «등록»한다**")
    P("")
    P("🚨 내가 「못 쟀다」로 적은 것: 「−α 가 «왜» 이득인가」")
    P("   그때 후보로 적은 것: 「진입가가 낮아 **+30% 목표**가 «가까워진다»」")
    P("   🔴 **그 물음은 «틀렸다»** — **손절선 −10% 도 «같이» 내려간다**(둘 «다» «비율»이다)")
    P("")
    P("## ✅ **「목표와 손절이 «같이» 내려갈 때 «비대칭»이 «있는가»」**")
    P("   ⇒ `163`(손절폭) · `161` 과 «얽히는» **«정확한»** 이름이다")
    P("   🚨 **이 판은 «안» 쟀다** — 「기전」은 **«미측정»**이다")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 손절 −10 · 목표 +30",
                     "같은 칸 5", "**같은 검출기 섞임**(VCP 76.9%)"]):
        P(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
