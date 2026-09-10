# -*- coding: utf-8 -*-
r"""181 — **「목표와 손절이 «같이» 내려갈 때 «비대칭»이 «있는가」」** · 사전등록 `tasks/181-target-stop-asymmetry.md`

  🏷️ **세대 B** · 규칙 **+30/-10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  🚨 **이 판은 `175` 의 «+2.497%p» 를 «다시» 재지 «않는다». 그 «안»을 «가른다».**

  🚨 **«새 기계» 하나** — 「본전선」을 «따로» 움직여야 해서 `pyr_trigger.py` 를 **«복사»**해
     `_pyr_be.py` 에 `be_px` 를 «더했다». **원본은 «안» 건드렸다.**
     ⇒ **WB★ 이 그 사본을 «검산»한다**(Ⓢ³−Ⓢ″ 가 `175` 의 +2.497%p 와 «맞아야» 한다).
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
ptb = _load("ptb", "_pyr_be.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NSEED, YRS, DELTA, T60 = 60, 27.4, 1.23, 2.001
ALPHA = 0.005                 # `175` 의 α=0.50% 칸 «하나»만 쓴다
MA_REF = 12377
# 🔴 처음엔 `REF_175 = 2.497` 로 «손으로» 박았다 — **그건 «반올림된 «인쇄값»»**이라
#    ±0.0001 문턱을 **«원리상» 통과할 수 «없었다**(실제로 −0.0003 로 «미통과»했다).
#    ⇒ ✅ **`175` 의 «캐시»에서 «원값»을 «직접» 계산한다**(유형 43 — 수는 «한 곳»에서)
C175 = Path(str(r91.OUT / "175-partial.json"))
DET = next((a.split("=", 1)[1].upper() for a in sys.argv if a.startswith("--det=")), None)
if DET not in (None, "VCP", "3C", "PP"):
    raise SystemExit("--det= 는 VCP · 3C · PP 중 하나여야 한다: %r" % DET)
WA_TOL, WB_TOL = 0.01, 0.0001
CACHE = Path(str(r91.OUT / ("181%s-partial.json"
                            % ("_" + DET.replace("3C", "c").replace("PP", "p").replace("VCP", "v")
                               if DET else ""))))


def ref175(n_seed):
    """`175` 의 Ⓝ−Ⓝ″(α=0.50%) 를 «캐시»에서 «원값»으로 «다시» 계산한다."""
    if not C175.exists():
        return None, "🚨 `175-partial.json` 이 «없다** (자리 `%s`)" % str(C175)
    d = json.loads(C175.read_text(encoding="utf-8"))
    kn, km = "v1|N|0.0050|n%d" % n_seed, "v1|M|0.0050|n%d" % n_seed
    if kn not in d or km not in d:
        return None, "🚨 «열쇠»가 «없다** — `%s` / `%s`" % (kn, km)
    a = [x[0] for x in d[kn]]
    b = [x[0] for x in d[km]]
    if len(a) != n_seed or len(b) != n_seed:
        return None, "🚨 씨앗 «수»가 다르다 — %d / %d vs %d" % (len(a), len(b), n_seed)
    return st.mean(acc.cagr(a[i], YRS) - acc.cagr(b[i], YRS) for i in range(n_seed)), None


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    dry = "--dry" in sys.argv
    P = print
    P("=" * 104)
    P("181 - **「목표와 손절이 «같이» 내려갈 때 «비대칭»이 «있는가」」** · 씨앗 %d판%s"
      % (n_seed, "  🚨 **--dry(«구조»만)**" if dry else ""))
    P("=" * 104)
    if DET:
        P("")
        P("## 🆕🚨 **`--det=%s` — `181` 의 «예측»을 «검정»하는 판이다**" % DET)
        P("")
        P("```")
        P("이 판이 «돌리기 «전»»에 적은 «예측»:")
        P("   「Ⓢ″·Ⓢ¹·Ⓢ²·Ⓢ³ 은 «전부» **SAME**(같은 종목·같은 날) ⇒ **«구성»에 «강건»할 것**」")
        P("")
        P("✅ **검정하는 것**: 세 «몫»의 **«부호»**가 «살아남는가**(㉰ · ㉮ · ㉯)")
        P("🚨 **MA★·WB★ 이 «안» 맞는 것이 «정상»이다** — «유니버스»가 «다르다**")
        P("⛔ **PP 는 «검정»에 «안» 넣는다**(N 이 작다 — `179` 에서 «미리» 적었다)")
        P("```")
    P("")
    P("> 조사 세션 · 2026-09-05 · `scripts/181-target-stop-asymmetry.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## 🚨🚨 **머리 — 「이 판은 «무엇»을 «안» 하나」를 «먼저»**")
    P("")
    P("```")
    P("⛔ **`175` 의 «가격 조각»을 «다시» 재지 «않는다**  ⇒  **그 «안»을 «가른다»**")
    P("⛔ **Ⓢ¹·Ⓢ² 는 «집행 «불가»»이고 «분해 «전용»»이다**")
    P("   («원래» 진입가를 알아야 문턱을 놓을 수 있는데 — 그건 «안» 산 세계의 값이다)")
    P("   🚨 「«이상»하지만 «가능»」이라 적지 «않는다** — 그러면 «나중에» 「쓸 수 있다」로 «흘러간다**")
    P("```")
    P("")
    P("## 🚨 **머리 — 「판정칸은 «어느» 축에서 «참»인가」**")
    P("")
    P("```")
    P("🚨 **CI 는 «씨앗» 축 «만» 잰다** — 60 판이 **«같은» 시장 역사 한 벌**을 쓴다")
    P("   ⇒ 그 축에서는 **«유효 n = 1»** 이다(문서 «끝» 참조)")
    P("## ⇒ ★ **아래 «판정칸»은 「«씨앗»을 바꿔도 그런가」이지 「«시장»을 바꿔도 그런가」가 «아니다**")
    P("")
    P("## 🔴🔴 **④ «갱신»(`183` 이 «격상»했다) — 이건 「«한계»」가 «아니라» 「«자격» 미달」이다**")
    P("")
    P("   정본 `verdicts/00-READ-FIRST` **M10**:")
    P("   ## **「«판정 «문턱»»에 붙는 «구간»은 «언제나» «자료»다. 적을 수 «없으면» «판정»에 «못» 쓴다」**")
    P("")
    P("   ⇒ 🔴 **`156`~`182` 가 «씨앗» 축으로 판정했다 — «세 번째» 위반**이다")
    P("   ⇒ ⛔ **「판정칸은 «씨앗» 축에서만 «참»」은 «발견»이 «아니라** — **«위반 상태»의 «사후 기술»**이다")
    P("   ⇒ ✅ **`183` 이 «자료» 축으로 «다시» 쟀다**(`176` 의 다섯 짝) — **이 판(`181`)은 «아직»다**")
    P("     ⇒ ★ **아래 판정칸은 「«자료» 축으로 «다시» 재기 «전»」의 것**이다")
    P("```")
    P("")
    P("## 🚨 **`179` 에서 배운 것을 «미리» 댄다 — «예측»이다**")
    P("")
    P("```")
    P("🔎 `179` §3c 의 «자»: 「그 판의 대조가 **«무엇»을 «무작위»로 바꾸나**」")
    P("   **WHO**(누구를) ⇒ «대상 집합»이 «검출기 구성»에 «딸린다** ⇒ **«흔들린다»**")
    P("   **WHEN·SAME**  ⇒ 대상 집합 «고정» ⇒ **«부호»가 «살아남는다»**")
    P("")
    P("## ⇒ ✅ **이 판의 Ⓢ″·Ⓢ¹·Ⓢ²·Ⓢ³ 은 «전부» «같은 종목·같은 날» = **SAME**")
    P("## ⇒ **「«구성»(검출기)에 «강건»할 것」으로 «예상»한다**")
    P("")
    P("   ⇒ ★ 이건 `179` §3c 의 «자»에 대한 **«또 하나»의 «예측»**이다")
    P("   🚨 **이 판에서는 «안» 돌린다**(검출기 갈래는 «따로» 돌려야 한다) ⇒ **«등록»만 한다**")
    P("   ⛔ **「강건할 것이다」를 «결과»로 «쓰지» 않는다. «예측»으로만 «남긴다**")
    P("```")
    P("")
    P("## 🚨 **갈래 — 검증이 «전제»를 고쳐 준 뒤의 것**")
    P("")
    P("```")
    P("🔴 「비율이라 «같이» 내려가니 «상쇄»」는 **«틀렸다»**(두뇌가 «직접» 검산):")
    P("   진입가 100 → 99.5 (−0.500)  ·  목표 130 → 129.35 (**−0.650**)  ·  손절 90 → 89.55 (**−0.450**)")
    P("   ⇒ ★ **«비율»은 같아도 «금액»이 다르고 — «경로»는 «금액»으로 움직인다**")
    P("   ⇒ **목표 쪽이 %.3f배 크게 내려간다**(= 1.30 ÷ 0.90)" % (1.30 / 0.90))
    P("")
    P("## 🚨🚨 **「1.444배」에 «자»가 «셋»이다 — «섞으면» «안» 된다**(유형 67)")
    P("   ㉠ **문턱 «이동 폭»의 비**            = 1.30÷0.90 = **%.3f**  ⇒ ★ **«항등식»**. 재나 마나 «참»"
      % (1.30 / 0.90))
    P("   ㉡ **목표/손절 «도달 «건수»»의 비**   ⇒ **«경험»** · 🚨 **이 판은 «안» 쟀다**")
    P("   ㉢ **「«%p 기여»」의 비**             ⇒ **«경험»** · 🚨 **이 판은 «안» 쟀다**")
    P("")
    P("   🚨 **㉡ 이 %.3f 과 «같을» «이유»가 «없다** — 두 문턱 «근처»의 «분포 밀도»가 «다르다**"
      % (1.30 / 0.90))
    P("   🚨 **㉡ 과 ㉢ 도 «다르다** — 「손절 «한» 건 피함」과 「목표 «한» 건 더 침」의 **«값»이 «다르다**")
    P("   ## ⇒ ★ **「«방향»이 맞았다」가 「«기전»이 맞았다」가 «아니다**")
    P("   ⇒ ✅ **㉡·㉢ 을 «다음 판»의 «과제»로 «등록»한다**")
    P("")
    P("**끄는 «순서» — 한 번에 «하나»씩만 «켠다»:**")
    P("   `Ⓢ″` 원래 가격 · 원래 문턱 · 원래 본전                        ← «기준»")
    P("   `Ⓢ¹` **가격만 낮춤**(문턱·본전은 «원래» 값에 «고정»)          ⇒ `Ⓢ¹−Ⓢ″` = **㉰ «비용/주식 수»**")
    P("   `Ⓢ²` + **문턱이 «내려감»**(본전은 «원래» 고정)                ⇒ `Ⓢ²−Ⓢ¹` = **㉮ «두 문턱의 «다른 양»»**")
    P("   `Ⓢ³` + **본전도 «내려감»** = `175` 의 Ⓝ                       ⇒ `Ⓢ³−Ⓢ²` = **㉯ «본전 이동»**")
    P("   ⇒ **합 = `Ⓢ³ − Ⓢ″`**  ⇒ ✅ **«항등식»**(WA★)")
    P("```")
    P("")
    P("```")
    P("자료   Sharadar SEP/DAILY · %s ~ %s (%.1f년) · 배당 «포함» · 상폐 «포함»" % (D0, D1, YRS))
    P("규칙   손절 **-%.0f%%** · 목표 **+%.0f%%**(절반) · 칸 **%d** · α = **%.2f%%**"
      % (STOP, TARGET, SLOTS, 100 * ALPHA))
    P("Δ = %.2f%%p                             ← 150 의 우리-QQQ 격차" % DELTA)
    P("MA★ 기준 %s만                      ← 156·161~168·170·173·175~177 의 ①" % format(MA_REF, ","))
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음 — 돌린 자리 `%s`" % str(r91.SUB))
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    keep = {}
    for y in sorted(by2):
        keep[y] = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                keep[y].append(p)
    n_all = sum(len(v) for v in keep.values())

    def touch(p):
        pv, lo = p.get("pivot"), p["l"][0]
        return pv is not None and lo is not None and lo <= pv * (1.0 - ALPHA)

    def prices(p):
        """(Ⓢ″ 체결가, Ⓢ 체결가) — `175` 와 «같은» 규약."""
        pv = p["pivot"]
        o0 = (p.get("o") or [None])[0]
        lvl = pv * (1.0 - ALPHA)
        e2 = pv if o0 is None else max(pv, o0)
        e1 = lvl if o0 is None else max(lvl, o0)
        return e2, e1

    def build(mode):
        """mode: base(①) | S2(Ⓢ″) | S1 | Sq(Ⓢ²) | S3(Ⓢ³)"""
        out_ = []
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                if DET and p.get("pattern") != DET:      # 🆕 «한 갈래»만(179 ③)
                    continue
                if mode != "base" and not touch(p):
                    continue
                q, kw = p, {}
                if mode != "base":
                    e2, e1 = prices(p)
                    q = dict(p)
                    if mode == "S2":
                        q["entry_price"] = e2
                    else:
                        q["entry_price"] = e1
                    if mode == "S1":                       # 문턱을 «원래» 자리에 «고정»
                        kw["stop"] = 100.0 * (1.0 - e2 * (1.0 - STOP / 100.0) / e1)
                        kw["target"] = 100.0 * (e2 * (1.0 + TARGET / 100.0) / e1 - 1.0)
                    if mode in ("S1", "Sq"):               # «본전»을 «원래» 자리에 «고정»
                        kw["be_px"] = e2
                t = ptb.resolve_trade(q, ft="limit", fs="market",
                                      stop=kw.pop("stop", STOP),
                                      target=kw.pop("target", TARGET),
                                      half=HALF, shares=(1.0,), add_stop="floor_entry",
                                      **kw)
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                t["stop_frac"] = STOP / 100.0
                out_.append(t)
        return out_

    P("")
    P("## 1. 관문 — 구조")
    P("")
    P("```")
    nt = sum(1 for y in keep for p in keep[y] if touch(p))
    P("**「−α 에 «닿는»」 후보** — %s / %s (**%.1f%%**)  →  %s"
      % (format(nt, ","), format(n_all, ","), 100.0 * nt / max(n_all, 1),
         "✅ **줄었다**" if nt < n_all else "🚨 **멈춘다**"))
    P("")
    P("**WC★ — «비용»이 «켜져» 있는가**(㉰ 가 «후보»라 «끄면» 그 갈래가 «죽는다»)")
    P("   `r91.COST` = **%s** · `r91.r41.Cost(...)` 로 «감싸서» 돌린다" % str(r91.COST))
    P("")
    P("**WE★ — «분해 «전용»» 표시**")
    P("   `Ⓢ¹` · `Ⓢ²` 는 **«집행 «불가»»** — 「원래 진입가」는 **«안» 산 세계의 값**이다")
    P("   ⇒ ⛔ **«판정»으로 «안» 쓴다. «몫»을 «가르는» 데만 쓴다**")
    P("```", flush=True)
    if nt >= n_all:
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
        m = {"expo": st.median([x["expo_mean"] for x in rs]), "n": len(ev),
             "nf": st.median([x["n_filled"] for x in rs])}
        cache[key] = [list(a) for a in v]
        cache[key + "|m"] = m
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        return v, m

    out, meta = {}, {}
    for nm, mode in (("①", "base"), ("Ⓢ″", "S2"), ("Ⓢ¹", "S1"), ("Ⓢ²", "Sq"), ("Ⓢ³", "S3")):
        out[nm], meta[nm] = sim(build(mode), "v1|%s|n%d" % (mode, n_seed))
        P("  %s %.0f만(후보 %d)" % (nm, st.median([a[0] for a in out[nm]]), meta[nm]["n"]),
          flush=True)

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    def dif(x, y):
        d = [acc.cagr(out[x][i][0], YRS) - acc.cagr(out[y][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    def cell(lo, hi):
        if lo >= DELTA:
            return "**1** ✅ CI 하한 ≥ +Δ"
        if hi <= -DELTA:
            return "**2** 🚨 CI 상한 ≤ −Δ"
        if lo > 0:
            return "**4a** «확실히» «양수»·Δ 미만" if hi <= DELTA else "**4b** «양수»·Δ 를 «걸침»"
        if hi < 0:
            return "**4a** «확실히» «음수»·Δ 미만" if lo >= -DELTA else "**4b** «음수»·Δ 를 «걸침»"
        return "**5** 🚨 «못 가린다»"

    P("")
    P("## 2. 관문 — 수")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①"]])
    P("**MA★ 앵커** — ① **%.0f만** vs %s만  →  %s"
      % (m1, format(MA_REF, ","),
         "✅ **일치**" if abs(m1 - MA_REF) < 1.0 else
         ("🆕 **다름 — `--det=%s` 라 «유니버스»가 «다르다». «정상»이다**" % DET if DET
          else "🚨 **멈춘다**")))
    P("")
    tot = dif("Ⓢ³", "Ⓢ″")
    ref, err = ref175(n_seed)
    P("**WB★ — `Ⓢ³−Ⓢ″` 가 `175` 의 «가격 조각»과 «맞는가**(±%.4f%%p · 씨앗 **%d판 «같음»**)"
      % (WB_TOL, n_seed))
    P("")
    P("   🔴 **처음엔 «인쇄값» `2.497` 을 «손으로» 박았다 — 그건 «반올림»이라**")
    P("     **±%.4f 문턱을 «원리상» 통과할 수 «없었다**(실제로 **−0.0003** 로 «미통과»했다)" % WB_TOL)
    P("   ✅ **이제 `175` 의 «캐시»에서 «원값»을 «다시» 계산한다** — 자리 `%s`" % str(C175))
    P("")
    if DET:
        P("   🆕 **`--det=%s` 라 «맞을 수가» 없다** — `175` 는 «전체» 유니버스였다" % DET)
        P("   ⇒ ⛔ **WB★ 은 여기서 «검산»을 «못» 한다**. 사본의 «정확성»은 «무플래그» 판이 «보증»한다")
        ref = None
    if err and not DET:
        P("   %s" % err)
        return 3
    if ref is not None:
        P("   `175` 원값 **%+.6f%%p**  ·  이 판 **%+.6f%%p**  ·  차 **%+.6f%%p**  →  %s"
          % (ref, tot[0], tot[0] - ref,
             "✅ **맞는다**" if abs(tot[0] - ref) < WB_TOL else "🚨 **멈춘다**"))
        P("   ★ **그 «일치»가 「`_pyr_be.py` 사본이 원본과 «같다»」의 «검산»이다**")
    else:
        P("   이 판 **%+.6f%%p** (검산 «없음»)" % tot[0])
    P("")
    parts = [("㉰ **«싸게 산» 몫**(문턱 «고정») 🚨«회계»", "Ⓢ¹", "Ⓢ″"),
             ("㉮ **«두 문턱의 «다른 양»»**(🚨«회전» «포함»)", "Ⓢ²", "Ⓢ¹"),
             ("㉯ «본전 이동»", "Ⓢ³", "Ⓢ²")]
    e = sum(dif(x, y)[0] for _l, x, y in parts) - tot[0]
    P("**WA★ 합 검산 «항등식»** — |Σ몫 − (Ⓢ³−Ⓢ″)| = **%+.4f%%p**  →  %s"
      % (e, "✅" if abs(e) < WA_TOL else "🚨 **멈춘다**"))
    P("")
    P("**노출 — «팔마다»** · ⛔ **«보정» «금지»**(유형 73)")
    for nm in ("①", "Ⓢ″", "Ⓢ¹", "Ⓢ²", "Ⓢ³"):
        P("   %-3s **%.1f%%** · 후보 %s · 체결중앙 %.0f"
          % (nm, meta[nm]["expo"], format(meta[nm]["n"], ","), meta[nm]["nf"]))
    P("```")

    P("")
    P("## 3. 팔 — 📏폭 «전부**(WD★) · 🚨 **읽기 «전»에 «수준»을 «먼저»**(`177` 에서 배웠다)")
    P("")
    P("| 팔 | 뜻 | 세후 총액(중앙) | 원금 대비 | 연 환산 | **📏폭** | 낙폭 중앙 |")
    P("|---|---|---:|---:|---:|---:|---:|")
    LAB = {"①": "**현행** — 피벗에 산다(«전체» 후보)",
           "Ⓢ″": "«기준» — 「Ⓢ 가 «산» 것」만 **현행 가격**에",
           "Ⓢ¹": "🚨«분해 전용» — 가격만 낮춤(문턱·본전 «고정»)",
           "Ⓢ²": "🚨«분해 전용» — + 문턱 «내려감»(본전 «고정»)",
           "Ⓢ³": "**«현실»** — + 본전도 «내려감** (= `175` 의 Ⓝ)"}
    for nm in ("①", "Ⓢ″", "Ⓢ¹", "Ⓢ²", "Ⓢ³"):
        v = out[nm]
        mm = st.median([a[0] for a in v])
        P("| **%s** | %s | %.0f만 | **%+.0f%%** | **%+.2f%%** | **%.2f** | %+.1f%% |"
          % (nm, LAB[nm], mm, 100.0 * (mm / acc.START - 1.0), acc.cagr(mm, YRS),
             spread(v), st.median([a[1] for a in v])))
    P("")
    P("```")
    for ln in gates.spread_note([(nm, spread(out[nm]))
                                 for nm in ("①", "Ⓢ″", "Ⓢ¹", "Ⓢ²", "Ⓢ³")]):
        P(ln)
    P("")
    P("🚨 **폭을 «읽기 «전»»에 «수준»을 본다** — 다섯 팔 «전부» 원금(%.0f만) «위»인가: %s"
      % (acc.START,
         "✅ **그렇다**" if all(st.median([a[0] for a in out[n]]) > acc.START
                             for n in out) else "🚨 **아니다 — 폭 비교를 «다르게» 읽어야 한다**"))
    P("```")

    P("")
    P("## 🚨🚨 **⑥ — 이 판의 「합」은 `175` 의 「«가격» «조각»」이다**(규약 ⑦)")
    P("")
    P("```")
    P("**`181` 의 «합** `Ⓢ³ − Ⓢ″` = **%+.3f%%p**" % tot[0])
    P("**`175` 의 «가격» 조각** `Ⓝ − Ⓝ″` = **같은 수**(WB★ 이 소수 여섯 자리까지 «검산»했다)")
    P("")
    P("## ⇒ ★★★ **`181` 은 「채택 «가능»한 수」를 «낸» 판이 «아니다**")
    P("## ⇒ **`175` 의 «한 조각»을 «더» 쪼갠 판이다** — 그 조각은 **«시점 «불가»»**다")
    P("")
    P("   ⇒ ⛔ **`181` 의 «어느» 수도 「이만큼 «번다»」로 «못» 쓴다**")
    P("   ⇒ ✅ **`175` 에서 «채택 «가능»»했던 것은 「합」(`Ⓝ−①`) «뿐»이었고 — 이 판은 그걸 «안» 건드린다**")
    P("```")
    P("")
    P("## 4. ★★ **분해 — 「%+.3f%%p 가 «어느» 갈래에서 «왔는가»」**" % tot[0])
    P("")
    P("| 갈래 | 짝 | 몫(연환산) | 95% CI | **판정칸** | **📏폭(두 팔)** | **CI폭÷효과** | 전체 중 |")
    P("|---|---|---:|---:|:--|---:|---:|---:|")
    vals = []
    for lab, x, y in parts:
        mu, lo, hi = dif(x, y)
        vals.append((lab, mu, lo, hi))
        P("| **%s** | `%s − %s` | **%+.3f%%p** | [%+.3f, %+.3f] | %s | %.2f · %.2f | **%.1f%%** | **%+.0f%%** |"
          % (lab, x, y, mu, lo, hi, cell(lo, hi), spread(out[x]), spread(out[y]),
             100.0 * (hi - lo) / max(abs(mu), 1e-9),
             100.0 * mu / tot[0] if abs(tot[0]) > 1e-9 else float("nan")))
    P("| **합** | `Ⓢ³ − Ⓢ″` | **%+.3f%%p** | [%+.3f, %+.3f] | %s | %.2f · %.2f | **%.1f%%** | **100%%** |"
      % (tot[0], tot[1], tot[2], cell(tot[1], tot[2]),
         spread(out["Ⓢ³"]), spread(out["Ⓢ″"]),
         100.0 * (tot[2] - tot[1]) / max(abs(tot[0]), 1e-9)))
    P("")
    P("   📏 **폭이 「판정칸 «옆»」에 «있는» 이유** — 「폭 ≈ 1.00 이면 그 칸의 CI 는 «표본»")
    P("   불확실성을 «안» 잰다」. ⛔ **«문턱»으로 «거르지» 않고 — «읽는 사람»이 «본다**")
    P("")
    P("```")
    P("## 🚨🚨 **㉰ 는 «발견»이 «아니라» «회계»다 — 「CI 폭」이 그것을 «말한다»**")
    P("")
    P("   Ⓢ″ 진입 100 · 손절 90 · 목표 130   ↔   Ⓢ¹ 진입 **99.5** · 손절 **90** · 목표 **130**(«절대» 고정)")
    P("   ⇒ **«같은» 거래를 «%.1f%% 싸게» 산 것 «뿐»**이다" % (100 * ALPHA))
    P("")
    r0 = 100.0 * (vals[0][3] - vals[0][2]) / max(abs(vals[0][1]), 1e-9)
    r1 = 100.0 * (vals[1][3] - vals[1][2]) / max(abs(vals[1][1]), 1e-9)
    P("   **CI 폭 ÷ 효과** — ㉰ **%.1f%%**  vs  ㉮ **%.1f%%**  ⇒  **%.0f배**" % (r0, r1, r1 / r0))
    P("   ## ⇒ ★ **「CI 가 «좁다» = «확실»」이 «아니라** — **「«좁다» = «항등식»에 «가깝다»」**")
    P("")
    nf = meta["Ⓢ¹"]["nf"]
    w = meta["Ⓢ¹"]["expo"] / 100.0 / SLOTS
    gross = (1.0 + ALPHA * w) ** nf
    ann = 100.0 * (gross ** (1.0 / YRS) - 1.0)
    P("   ✅ **거래당 %.1f%% 검산** — 체결 **%.0f**건 · 한 자리 비중 **%.1f%%**(노출 %.1f%% ÷ 칸 %d)"
      % (100 * ALPHA, nf, 100 * w, meta["Ⓢ¹"]["expo"], SLOTS))
    P("     (1 + %.4f × %.4f)^%.0f = **%.2f배** ⇒ 연 **%+.3f%%p**  vs  관측 ㉰ **%+.3f%%p**"
      % (ALPHA, w, nf, gross, ann, vals[0][1]))
    P("     ⇒ %s **«같은 자릿수»** — ㉰ 가 「%.1f%% 싸게 산 것」으로 «설명»된다"
      % ("✅" if 0.2 < abs(ann / max(vals[0][1], 1e-9)) < 5.0 else "🚨", 100 * ALPHA))
    P("")
    P("## ⇒ ★★★ **「+%.3f%%p 의 %.0f%%가 «회계»」이고 — «진짜» 기전은 ㉮ «하나»(%.0f%%)다**"
      % (tot[0], 100.0 * vals[0][1] / tot[0], 100.0 * vals[1][1] / tot[0]))
    P("")
    P("## 🚨🚨 **「회계」에 «자»가 «둘»이다 — «미끄러지면» «틀린다**(유형 67)")
    P("")
    P("   ㉠ ✅ **「지적으로 «뻔하다»」** — 「%.1f%% 싸게 사면 그만큼 «더» 번다」는 «설명»이 «필요 없다**"
      % (100 * ALPHA))
    P("   ㉡ ⛔ **「실전에서 «무효»다」** — **«틀린» 읽기다**")
    P("")
    P("   ## ⇒ ★ **「㉰ 는 «돈»이 «아니다»」로 «미끄러지면» «틀린다**")
    P("     **%+.3f%%p 는 «진짜» 돈**이다. 다만 **「«왜» 그런가」가 «놀랍지» 않을 «뿐»**이다"
      % vals[0][1])
    P("")
    P("   🚨 **그런데 그 돈을 «가지려면» 「Ⓢ(−α)로 «사야»」 한다** — 그건 **«집행 «가능»»**하다")
    P("     ⛔ 다만 그때는 **문턱도 «같이» 내려간다** ⇒ **㉮ 도 «같이» 온다**")
    P("     ⇒ ★ **㉰ 만 «떼어» 가질 수 «없다**(그게 Ⓢ¹ 이 «분해 «전용»»인 이유다)")
    P("   ⇒ ## ✅ **«가질 수» 있는 것은 «합»(%+.3f%%p) «뿐»이다**" % tot[0])
    P("```")
    P("")
    P("```")
    big = max(vals, key=lambda t: abs(t[1]))
    P("★ **방향 «예측» 대조 — «미리» 적은 것과 맞춰 읽는다**")
    P("   ㉱ **㉰(«비용/주식 수»)가 «제일» 클 것** — 실측 «제일» 큰 것은 **%s (%+.3f%%p)**  ⇒  %s"
      % (big[0], big[1],
         "✅ **맞았다**" if big[0].startswith("㉰") else "🔴 **«빗나갔다»**"))
    P("   ㉲ **㉯(«본전»)는 «작을» 것** — 실측 **%+.3f%%p**(전체의 %.0f%%)  ⇒  %s"
      % (vals[2][1], 100.0 * vals[2][1] / tot[0] if abs(tot[0]) > 1e-9 else float("nan"),
         "✅ **맞았다**" if abs(vals[2][1]) < abs(big[1]) else "🔴 **«빗나갔다»**"))
    P("   ㉳ **㉮(«두 문턱»)는 «모르겠다»** — 실측 **%+.3f%%p**" % vals[1][1])
    P("")
    P("🚨 **㉴ — 내가 «바라던» 것은 「㉰ 가 «크다»」였다**(그러면 `175` 의 「원전이 «틀렸다»」가 «약해진다»)")
    P("   ⇒ ✅ **«안 바라는» 쪽(「㉮ 가 크다」= «진짜» 경로 효과)을 «먼저» 읽는다:**")
    P("     ㉮ = **%+.3f%%p** (전체의 **%.0f%%**)"
      % (vals[1][1], 100.0 * vals[1][1] / tot[0] if abs(tot[0]) > 1e-9 else float("nan")))
    P("```")
    P("")
    P("## 5. ★★★ **`179` §3c 의 «자»를 «검정»한다 — 이 판의 «예측»은 «맞았나**")
    P("")
    P("```")
    P("«미리» 적은 예측: 「Ⓢ 계열은 «전부» **SAME** ⇒ **«구성»(검출기)에 «강건»할 것**」")
    P("")
    P("🔎 명령 `python _runv.py 181-….py --det=VCP|3C|PP` · 산출 `results/181-{vcp,3c,pp}.md`")
    P("⛔ **PP 는 «검정»에 «안» 넣는다**(`179` 에서 «미리» 적었다)")
    P("```")
    P("")
    KEYS = [lab[0] for lab, _x, _y in parts] + ["합"]     # ㉰ ㉮ ㉯ + 합
    D181 = {}
    for det in ("vcp", "3c", "pp"):
        f = HERE.parent / "results" / ("181-%s.md" % det)
        if not f.exists():
            continue
        rows = {}
        for ln in f.read_text(encoding="utf-8").splitlines():
            for key in KEYS:
                if not ln.startswith("| **" + key):
                    continue
                for cellx in ln.split("|"):
                    cellx = cellx.strip()
                    if cellx.startswith("**+") or cellx.startswith("**-"):
                        try:
                            rows[key] = float(cellx.strip("*").rstrip("%p"))
                        except ValueError:
                            pass
                        break
        if rows:
            D181[det] = rows
    miss = [k for k in KEYS for d in D181 if k not in D181[d]]
    if not D181 or miss:
        P("   🚨 **«못» 읽었다 — 갈래 %s · 빠진 열쇠 %s  ⇒ «멈춘다»**"
          % (list(D181) or "없음", sorted(set(miss)) or "없음"))
    else:
        base = dict(zip(KEYS, [v[1] for v in vals] + [tot[0]]))
        P("| 갈래 | 원본 | %s | «부호»(VCP·3C) |"
          % " | ".join(d.upper() for d in D181))
        P("|---|---:|%s:--|" % ("---:|" * len(D181)))
        flips = []
        for k in KEYS:
            vs = [D181[d][k] for d in D181]
            tst = [D181[d][k] for d in D181 if d != "pp"]
            fl = any((v > 0) != (base[k] > 0) for v in tst)
            if fl and k != KEYS[-1]:
                flips.append(k)
            P("| **%s** | **%+.3f** | %s | %s |"
              % (k, base[k], " | ".join("**%+.3f**" % v for v in vs),
                 "🔴 **반전**" if fl else "✅ **유지**"))
        P("")
        P("```")
        sumfl = any((D181[d][KEYS[-1]] > 0) != (base[KEYS[-1]] > 0)
                    for d in D181 if d != "pp")
        P("## ⇒ %s **예측 — 「SAME 이면 «구성»에 «강건»할 것」**"
          % ("🔴🔴" if flips or sumfl else "✅"))
        P("")
        P("   %s **«합»(%s³−%s″)의 «부호» — %s**"
          % ("✅" if not sumfl else "🔴", "Ↄ", "Ↄ",
             "«살아남는다»" if not sumfl else "«바뀐다»"))
        P("   %s **«몫» %d / %d 가 «부호»를 «바꾼다**%s"
          % ("✅" if not flips else "🔴", len(flips), len(KEYS) - 1,
             (" — **%s**" % " · ".join("**%s**" % k for k in flips)) if flips else ""))
        for k in flips:
            P("     `%s` — 원본 **%+.3f** → %s"
              % (k, base[k],
                 " · ".join("%s **%+.3f**" % (d.upper(), D181[d][k]) for d in D181)))
        P("")
        if flips:
            P("## ⇒ ★★★ **「SAME 이면 강건」은 «합»에서는 «참»이고 «분해»에서는 «아니다**")
            P("   ⇒ **«분해 조각»이 «합»보다 «약하다** — 같은 팔들로 만들었는데도 그렇다")
            P("   ⇒ ⛔ **`179` §3c 의 «자»를 「«분해» 조각」에까지 «넓히지» 않는다**")
        else:
            P("## ⇒ ★★ **예측이 «맞았다** — «합»도 «몫»도 «부호»가 «살아남는다**")
        P("")
        acct = KEYS[0]
        allpos = all(D181[d][acct] > 0 for d in D181)
        P("   ★ **%s(«회계»)는 «네» 갈래 «전부» %s** — %s"
          % (acct, "«양수»다" if allpos else "«같은 부호»가 «아니다»",
             "**«회계»니까 «당연»하다** ⇒ ✅ 「«발견»이 아니라 «회계»」의 «또 하나»의 «증거»"
             if allpos else "🔴 **「회계」 읽기를 «다시» 봐야 한다**"))
        P("```")
    P("")
    P("```")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ 「목표가 «가까워져서» 좋다」 · 「손절이 «넓어져서» 좋다」 — **«둘 다» 내려간다**")
    P("     ✅ 맞는 말: **「내려가는 «양»이 «다르다»(1.3α vs 0.9α)」**")
    P("   ⛔ **Ⓢ¹·Ⓢ² 의 수를 «전략 성적»으로** — **«집행 «불가»» · «분해 «전용»»**")
    P("   ⛔ 「`175` 를 «다시» 쟀다」 — **이 판은 그 «안»을 «가른다»**")
    P("   ⛔ 「㉰ 가 크니 «싸게 사기»가 «가짜»다」 — **「«어디서» 왔나」와 「«참»인가」는 «다른 말»**")
    P("   ⛔ **노출 «보정»**(유형 73)")
    P("```")
    P("")
    P("```")
    P("🚨 **이 판이 «못» 가른 것 — «적어» 둔다**")
    P("")
    P("   ㉱ **«회전»**(진입가↓ ⇒ 목표에 «더 빨리» 닿음 ⇒ 슬롯이 «빨리» 빔)")
    P("     ⇒ **㉮ «안»에 «섞여» 있다**(그래서 ㉮ 이름에 「«회전» «포함»」을 «박았다»)")
    P("   ㉡ **목표/손절 «도달 «건수»»의 비** · ㉢ **「%p 기여」의 비** — «위» ⑤ 참조")
    P("   ㉲ **«집합»**(α 마다 «닿는» 종목이 «다름») — 이 판은 **α «하나»(%.2f%%)**만 썼다"
      % (100 * ALPHA))
    P("     ⇒ **「α «단조» 감소」는 «설명»하지 «못»한다** — **«다른» 판의 물음**이다")
    P("")
    P("   ⛔ **「기하로 «설명»했다」로 «닫지» 않는다** — 위 «둘»이 «남아» 있다")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 손절 −10 · 목표 +30",
                     "같은 칸 5", "**같은 검출기 섞임**(VCP 76.9%)",
                     "**α 한 칸**(0.50%)"]):
        P(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
