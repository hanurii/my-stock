# -*- coding: utf-8 -*-
r"""177 — **「«더 매력적인» 종목이 나타나면 «갈아탄다»」** · 사전등록 `tasks/177-swap-for-better.md`

  🏷️ **세대 B** · 규칙 **+30/-10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  🚨 **이 판은 «새 기계»가 필요했다** — 앞 판들은 «거래의 청산»만 갈아 끼우면 됐지만
     「갈아탄다」는 **«슬롯 배분» 자체**를 바꾼다. `slot_sim_lots.py` 를 **«복사»**해
     `_sim_swap.py` 를 만들고 거기에만 손댔다. **원본은 «안» 건드렸다.**
     ⇒ **MA★ 이 그 사본을 «검산»한다**(`swap="off"` 가 12,377만을 내야 한다).
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
sw = _load("sw", "_sim_swap.py")
f92a = r102.f92a
pt = r91.pt

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NSEED, NASSIGN, YRS, DELTA, T60 = 60, 10, 27.4, 1.23, 2.001
MA_REF = 12377
NA_TOL = 0.01
CACHE = Path(str(r91.OUT / "177-partial.json"))


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    dry = "--dry" in sys.argv
    P = print
    P("=" * 104)
    P("177 - **「«더 매력적인» 종목이 나타나면 «갈아탄다»」** · 씨앗 %d판%s"
      % (n_seed, "  🚨 **--dry(«구조»만)**" if dry else ""))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-04 · `scripts/177-swap-for-better.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## 🔴 **머리 «정정» — `177` 사전등록 §0 이 «틀린 수»를 인용하고 있다**")
    P("")
    P("```")
    P("사전등록 §0: 「체결률이 «팔마다» 거의 «같다»(① 36.8% · Ⓚ 37.2% · Ⓛ 37.9%)」")
    P("")
    P("🔴 그 수는 **«체결률»이 «아니다»** — `173` 이 `len(ev)`(중복 제거 «후» 후보 수)를")
    P("   `n_filled`(«실제로» 산 수)로 «불렀다». **«자»가 «틀렸다**(`176` 에서 잡았다)")
    P("")
    P("✅ **맞는 수 «셋»** — 이 판이 «다시» 찍는다:")
    P("   ㉠ **후보** · ㉡ **중복 제거 «후»** · ㉢ ★**«실제로» 산 것**(`n_filled`)")
    P("")
    P("## ⇒ 「자리 벽이 «있다」」는 **«더» 강해진다** — 그런데 「팔마다 «같다»」는")
    P("## **«중복 제거» 통과율에서 본 것이라 «체결률»로는 «다시» 재야 한다. 이 판이 «잰다»**")
    P("```")
    P("")
    P("## 🚨 **「축이 다르다」를 «좁힌다» — «자리» 축은 «이미» 대부분 «막혔다**")
    P("")
    P("```")
    P("**회전**   「출구 «셋» 중 **회전이 96.4% «점유»**」(`compounding-and-fees`)  ⇒ **«막힘»**")
    P("**슬롯 수** `138` — 칸 8 · 칸 12 · 자본 기준 **«전부» 나쁨**                  ⇒ **«막힘»**")
    P("")
    P("## ⇒ ★ **«새» 것은 「«같은» 슬롯 «수»에서 «누가» 자리를 «차지»하나」 «하나»뿐이다**")
    P("   ⛔ 「이번엔 «축»이 다르다」를 «넓게» 적으면 **«매번 나오는 말»의 «변종»**이다")
    P("```")
    P("")
    P("## 🔴 **ⓐ 는 「«안» 정의한다」가 «아니다 — 「«최신성»으로 «정의»한」 것이다**")
    P("")
    P("```")
    P("「더 «최근»으로 갈아탄다」 = **「«나중» 돌파가 «더» 좋다」**는 **«주장»**이다")
    P("   ⇒ 묻는 것 = **「«더 최근» 돌파로 갈아타면?」**")
    P("")
    P("## ★★ **«진짜» 장점은 「고르기를 «안» 들인다」가 «아니라» —**")
    P("## **「우리가 «고른» 자가 «아니라» «도착 «순서»»라 «자유도»가 «작다»」**이다")
    P("   («고르기가 아니다」는 «반박»되지만 「자유도가 작다」는 «참»이다)")
    P("")
    P("🚨 그리고 **ⓐ 는 원전의 「«더 매력적»」이 «아니다** — **「«근사»다」를 «같은 줄»에**")
    P("   (`175` 「원전 α 는 «방아쇠»지 «가격» 아님」 · `176` 「ⓐ 는 «반전»의 «근사»」와 «같은 자리»)")
    P("```")
    P("")
    P("## 🚨 **사전 근거 — «어느 짝»에 «붙는지»를 «같은 줄»에**(`176` 에서 배웠다)")
    P("")
    P("```")
    P("🔎 「**회전이 출구 셋 중 96.4% «점유»**」(`compounding-and-fees`)")
    P("   **Ⓡ − ①**  「갈아타기 «전체»」   ⇒ ✅ **«강하게»** — 「«비용»이 «먹는다»」 ⇒ «음수» 예상")
    P("   **Ⓡ − Ⓓ**  「«누구»를 내보내나」 ⇒ 🔴 **«안» 걸린다** — 회전 «횟수»가 «같기» 때문")
    P("")
    P("🔎 `133`·`132` 「늦출수록 이김」(세후 85.0%)")
    P("   **Ⓡ − ①** 에 ✅ «걸린다»(갈아타면 «일찍» 판다)  ·  **Ⓡ − Ⓓ** 엔 🔴 «안» 걸린다")
    P("")
    P("## ⇒ ★ **`Ⓡ−Ⓓ` 가 «정확히» 묻는 것:**")
    P("## **「«최저»를 내보내는 것이 «중앙»을 내보내는 것보다 «나은가」」**")
    P("   («무작위» 보유분의 «기대값»은 «중앙»이다 — 칸 5 중 1)")
    P("   ⛔ 「«무작위»보다 낫다」로 «적지» 않는다")
    P("```")
    P("")
    P("```")
    P("자료   Sharadar SEP/DAILY · %s ~ %s (%.1f년) · 배당 «포함» · 상폐 «포함»" % (D0, D1, YRS))
    P("규칙   손절 **-%.0f%%** · 목표 **+%.0f%%**(절반) · 칸 **%d** · 한 종목 상한 20%%"
      % (STOP, TARGET, SLOTS))
    P("Δ = %.2f%%p                             ← 150 의 우리-QQQ 격차" % DELTA)
    P("MA★ 기준 %s만                      ← 156·161~168·170·173·175·176 의 ①" % format(MA_REF, ","))
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
    n_cand = sum(len(v) for v in keep.values())

    base, pathmap, n_dup, exmap = [], {}, 0, {}
    for y in sorted(keep):
        open_until = {}
        for p in keep[y]:
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                n_dup += 1
                continue
            open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
            t["stop_frac"] = STOP / 100.0
            base.append(t)
            pathmap[id(t)] = p
            exmap[(t["scan_date"], t["code"], t.get("pattern", ""))] = (
                t["entry_px"], t["masks"][()]["exits"])

    P("")
    P("## 1. 관문 — 구조")
    P("")
    P("```")
    P("🚨 **VA★ — 「제일 «낮은» 수익률」이 «진입 시점에 «아는»» 값인가**")
    P("")
    P("   `_sim_swap.py:_unreal()` — **`p[\"c\"][j-1]`**(«전날» 종가)만 읽는다")
    P("   판 값은 **`p[\"o\"][j]`**(«오늘» 시가) — **새 후보를 «사는» 그 값**과 «같은» 날 «같은» 종류")
    P("   ⇒ ★ **«결정»은 «어제» 값으로, «집행»은 «오늘 시가»로** ⇒ **«룩어헤드»가 «아니다»**")
    P("   🚨 그리고 **`j >= 1` 인 것만 후보**다(«오늘» 산 것은 «오늘» 안 판다) — 아래에서 «수»로 «확인»한다")
    P("")
    P("🚨 **VE★ — «비용»이 «들어가는가**(회전이 «느는» 판이라 «빠지면» 부풀려진다)")
    P("   갈아탈 때 파는 것도 `credit()` 을 지나고, 거기서 **`net(g)`** 가 «걸린다»")
    P("   `r91.COST` = **%s** · `r91.r41.Cost(...)` 로 «감싸서» 돌린다" % str(r91.COST))
    P("```", flush=True)

    if dry:
        P("🚨 **--dry — 여기까지가 «구조»다. 시뮬레이션은 «안» 돌렸다**")
        return 0

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    def sim(key, mode, sseed=0):
        if key in cache:
            return [tuple(a) for a in cache[key]], cache[key + "|m"]
        with r91.r41.Cost(*r91.COST):
            rs = [sw.sim_swap(base, seed=sd, slots=SLOTS, risk=0.02, cap=0.20,
                              reserve=False, fill_rule="truncate", cash_rule="per_slot",
                              swap=mode, pathmap=pathmap, swap_seed=sseed)
                  for sd in range(n_seed)]
        v = [acc.account(x) for x in rs]
        sl_ = [q for x in rs for q in x["swap_log"]]
        m = {"n": len(base), "nf": st.median([x["n_filled"] for x in rs]),
             "expo": st.median([x["expo_mean"] for x in rs]),
             "nsw": st.median([x["n_swap"] for x in rs]),
             "ret": sorted(q[3] for q in sl_),
             "minj": (min(q[2] for q in sl_) if sl_ else None),
             "skip": _skip(sl_)}
        cache[key] = [list(a) for a in v]
        cache[key + "|m"] = m
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        return v, m

    def _skip(sl_):
        """🆕 `176` 에서 배운 것 — 「«−10% 손절»을 «건너뛰는가»」.
        내보낸 그 자리가 ① 에서라면 «그 뒤에» 손절로 끝났을 건수."""
        n_sk = n_tot = 0
        for dd, key, _j, _u in sl_:
            got = exmap.get(tuple(key))
            if got is None:
                continue
            epx, ex = got
            n_tot += 1
            if any(e[0] >= dd and e[2] <= epx * (1.0 - STOP / 100.0) * 1.0001 for e in ex):
                n_sk += 1
        return (n_sk, n_tot)

    out, meta = {}, {}
    out["①"], meta["①"] = sim("v1|off|n%d" % n_seed, "off")
    P("  ① %.0f만(후보 %d · 체결중앙 %.0f · 갈아탄 %.0f)"
      % (st.median([a[0] for a in out["①"]]), meta["①"]["n"],
         meta["①"]["nf"], meta["①"]["nsw"]), flush=True)
    m1 = st.median([a[0] for a in out["①"]])
    if abs(m1 - MA_REF) >= 1.0:
        P("")
        P("🚨 **MA★ «미통과» — 사본이 원본과 «다르다». «멈춘다»**")
        P("   ① **%.0f만** vs %s만" % (m1, format(MA_REF, ",")))
        return 3

    out["Ⓡ"], meta["Ⓡ"] = sim("v1|low|n%d" % n_seed, "low")
    P("  Ⓡ %.0f만(갈아탄 중앙 %.0f)"
      % (st.median([a[0] for a in out["Ⓡ"]]), meta["Ⓡ"]["nsw"]), flush=True)

    accs, ex_, nsw_, ret_, skip_ = [], [], [], [], []
    for ai in range(n_as):
        v, m = sim("v1|rand|a%d|n%d" % (ai, n_seed), "rand", sseed=ai + 1)
        accs.append(v)
        ex_.append(m["expo"])
        nsw_.append(m["nsw"])
        ret_ += m["ret"]
        skip_.append(m["skip"])
        P("    Ⓓ%d %.0f만(갈아탄 %.0f)" % (ai, st.median([a[0] for a in v]), m["nsw"]),
          flush=True)
    out["Ⓓ"] = [tuple(st.mean(accs[ai][i][j] for ai in range(n_as)) for j in range(4))
                for i in range(n_seed)]
    meta["Ⓓ"] = {"n": len(base), "nf": meta["①"]["nf"], "expo": None, "expo_d": ex_,
                 "nsw": st.median(nsw_), "ret": sorted(ret_),
                 "skip": (sum(a for a, _b in skip_), sum(b for _a, b in skip_))}

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
            return "**4a** «확실히» «양수»·CI «전체»가 Δ 아래" if hi <= DELTA else "**4b** «양수»·Δ 를 «걸침»"
        if hi < 0:
            return "**4a** «확실히» «음수»·CI «전체»가 −Δ 위" if lo >= -DELTA else "**4b** «음수»·Δ 를 «걸침»"
        return "**5** 🚨 «못 가린다»"

    def q(a, f):
        return a[int(len(a) * f)] if a else float("nan")

    P("")
    P("## 2. 관문 — 수")
    P("")
    P("```")
    P("**MA★ 앵커** — ① **%.0f만** vs %s만  →  ✅ **일치**" % (m1, format(MA_REF, ",")))
    P("   ★ **그 «일치»가 「`_sim_swap.py` 사본이 원본과 «같다»」의 «검산»이다**")
    P("")
    P("🚨 **「수」가 «셋»이다 — «자»를 «같은 줄»에**(유형 67 · 규약 ⑦ · `173` 정정)")
    P("   ㉠ **후보**(사다리 ② + 펀더 통과)                    — **%s**" % format(n_cand, ","))
    P("   ㉡ **중복 제거 «후»**(같은 종목 겹침 %s 건 뺌)       — **%s** (㉠ 의 %.1f%%)"
      % (format(n_dup, ","), format(len(base), ","), 100.0 * len(base) / max(n_cand, 1)))
    P("")
    P("   | 팔 | ㉢ ★**«실제로» 산 것**(`n_filled` 중앙) | ㉡ 대비 | ㉠ 대비 |")
    P("   |---|---:|---:|---:|")
    for nm in ("①", "Ⓡ", "Ⓓ"):
        P("   | **%s** | **%.0f** | **%.1f%%** | %.1f%% |"
          % (nm, meta[nm]["nf"], 100.0 * meta[nm]["nf"] / max(len(base), 1),
             100.0 * meta[nm]["nf"] / max(n_cand, 1)))
    P("")
    P("   ## 🔴 **`173` 의 「체결률 36.8%」는 ㉡/㉠ 이고 — «진짜» 체결률은 ㉢/㉡ 이다**")
    P("")
    P("🚨 **VC★ — 갈아탄 «횟수»가 Ⓡ·Ⓓ «같아야» 한다**")
    P("   Ⓡ **%.0f** vs Ⓓ **%.0f** (배정별 %s)  →  차 **%+.1f%%**  →  %s"
      % (meta["Ⓡ"]["nsw"], meta["Ⓓ"]["nsw"],
         " · ".join("%.0f" % x for x in nsw_),
         100.0 * (meta["Ⓡ"]["nsw"] - meta["Ⓓ"]["nsw"]) / max(meta["Ⓓ"]["nsw"], 1),
         "✅" if abs(meta["Ⓡ"]["nsw"] - meta["Ⓓ"]["nsw"]) <= 0.005 * max(meta["Ⓓ"]["nsw"], 1)
         else "🚨 **«어긋난다» — 판정을 그만큼 «약하게» 읽는다**"))
    P("")
    P("🚨 **㉰(관문) — 회전이 «늘지» «않으면» 구현이 «틀렸다**")
    P("   ① 갈아탄 횟수 **%.0f** → Ⓡ **%.0f**  →  %s"
      % (meta["①"]["nsw"], meta["Ⓡ"]["nsw"],
         "✅ **늘었다**" if meta["Ⓡ"]["nsw"] > meta["①"]["nsw"] else "🚨 **멈춘다**"))
    P("")
    P("🚨 **VA★ — «오늘» 산 것을 «오늘» 판 건수**")
    P("   path 날 번호의 «최솟값» — Ⓡ **%s** · Ⓓ **%s**  →  %s"
      % (meta["Ⓡ"]["minj"], meta["Ⓓ"].get("minj", "—"),
         "✅ **≥ 1**" if (meta["Ⓡ"]["minj"] or 1) >= 1 else "🚨 **멈춘다**"))
    P("")
    P("🚨 **🆕 `176` 에서 배운 검사 — 「«−10% 손절»을 «건너뛰는가»」**")
    for nm in ("Ⓡ", "Ⓓ"):
        a_, b_ = meta[nm]["skip"]
        P("   **%s** — 내보낸 %s 자리 중 **%s** (%.1f%%) 가 ① 이라면 «그 뒤» «손절»로 끝났을 것"
          % (nm, format(b_, ","), format(a_, ","), 100.0 * a_ / max(b_, 1)))
    P("   ⇒ ★ **Ⓡ 와 Ⓓ 가 «비슷»하면 그 성분은 `Ⓡ−Ⓓ` 에서 «상쇄»된다**(`176` 과 «같은 꼴»)")
    P("   🚨 **`Ⓡ−①` 에는 «상쇄»가 «없다** — 그 짝은 «그만큼» «오염»돼 있다")
    P("")
    P("**노출 — «팔마다»** · ⛔ **«보정» «금지»**(유형 73)")
    P("   ① **%.1f%%** · Ⓡ **%.1f%%** · Ⓓ **%.1f ~ %.1f%%**(중앙 %.1f%%)"
      % (meta["①"]["expo"], meta["Ⓡ"]["expo"], min(ex_), max(ex_), st.median(ex_)))
    P("```")

    P("")
    P("## 3. 🆕 **「«내보낸» 것」의 «수익률 분포» — 「하락·횡보」의 «근사»가 «얼마나» 근사인가**")
    P("")
    P("| 팔 | n | P10 | **중앙** | P90 | 음수 비율 |")
    P("|---|---:|---:|---:|---:|---:|")
    for nm in ("Ⓡ", "Ⓓ"):
        a_ = meta[nm]["ret"]
        P("| **%s** | %s | %+.1f%% | **%+.1f%%** | %+.1f%% | **%.1f%%** |"
          % (nm, format(len(a_), ","), q(a_, .10), q(a_, .50), q(a_, .90),
             100.0 * sum(1 for x in a_ if x < 0) / max(len(a_), 1)))
    P("")
    P("```")
    med = q(meta["Ⓡ"]["ret"], .50)
    P("🔴 원전 「«하락»하고 «횡보»」는 **«절대» 상태** · 「제일 «낮은» 수익률」은 **«상대» 순위**")
    P("   ⇒ 보유 다섯이 **«전부» +20%** 여도 「제일 낮은 것」을 «내보낸다» — **원전은 그걸 «말한 적 없다»**")
    P("")
    P("## ⇒ ★ **「근사가 «얼마나» 근사인가」가 «수»가 됐다 — 중앙 %+.1f%%**" % med)
    P("   %s" % ("✅ **중앙이 «음수»다 ⇒ 「하락·횡보」에 «가깝다»**" if med < 0 else
                 "🔴 **중앙이 «양수»다 ⇒ 「하락·횡보」가 «아니다». «근사»가 «멀다»**"))
    P("```")

    P("")
    P("## 4. 팔 — 📏폭 «전부»(VD★ · 🚨 **Ⓓ 가 아니라 ① 과 견준다**)")
    P("")
    P("| 팔 | 뜻 | 세후 총액(중앙) | 연 환산 | **📏폭** | ① 대비 | 낙폭 중앙 | 회복 |")
    P("|---|---|---:|---:|---:|---:|---:|---:|")
    sp1 = spread(out["①"])
    LAB = {"①": "**현행** — 자리가 «차면» 새 후보를 «버린다»",
           "Ⓡ": "**«갈아탄다»** — 「보유 중 «수익률 «제일 낮은»»」을 «팔고» 산다",
           "Ⓓ": "«플라세보» — **«같은 방아쇠»**에 «무작위» 보유분을 «판다»"}
    for nm in ("①", "Ⓡ", "Ⓓ"):
        v = out[nm]
        mm = st.median([a[0] for a in v])
        P("| **%s** | %s | %.0f만 | **%+.2f%%** | **%.2f** | **%+.0f%%** | %+.1f%% | %.1f년 |"
          % (nm, LAB[nm], mm, acc.cagr(mm, YRS), spread(v),
             100.0 * (spread(v) / sp1 - 1.0),
             st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0))

    P("")
    P("## 5. 판정 — **정본 §판정표** · Δ = %.2f%%p" % DELTA)
    P("")
    P("| 짝 | 뜻 | Δ연환산 | 95% CI | 판정 |")
    P("|---|---|---:|---:|:--|")
    rd = dif("Ⓡ", "Ⓓ")
    P("| **Ⓡ − Ⓓ** | ★**판정** — 「**«최저»를 내보내는 것이 «중앙»을 내보내는 것보다 «나은가»**」 | **%+.3f%%p** | [%+.3f, %+.3f] | %s |"
      % (rd[0], rd[1], rd[2], cell(rd[1], rd[2])))
    d1 = dif("Ⓓ", "①")
    P("| **Ⓓ − ①** | 「**«갈아타는» 것 «자체»**」(🚨 손절 건너뛰기가 «섞임») | **%+.3f%%p** | [%+.3f, %+.3f] | %s |"
      % (d1[0], d1[1], d1[2], cell(d1[1], d1[2])))
    r1 = dif("Ⓡ", "①")
    P("| **Ⓡ − ①** | «참고» — 「**«실제로» 얻는 것**」(회전 96.4%% · `133` «강하게» 걸림) | **%+.3f%%p** | [%+.3f, %+.3f] | %s |"
      % (r1[0], r1[1], r1[2], cell(r1[1], r1[2])))
    P("")
    P("```")
    e = rd[0] + d1[0] - r1[0]
    P("🚨 **VB★ 합 검산 «항등식»** — |(Ⓡ−Ⓓ)+(Ⓓ−①)−(Ⓡ−①)| = **%+.4f%%p**  →  %s"
      % (e, "✅" if abs(e) < NA_TOL else "🚨 **멈춘다**"))
    P("")
    P("★ **`175`·`176` 의 «갈라 읽기»를 «그대로»**")
    P("   **`Ⓡ−Ⓓ`** = 「**«고르는» 힘**」  ·  **`Ⓡ−①`** = 「**«실제로» 얻는 것**」")
    P("   ⇒ ⛔ **둘을 «섞으면» 「«없는» 이득」이 된다**(`175` 에서 그게 «제일» 큰 자리였다)")
    P("")
    P("★ **방향 «예측» 대조**")
    P("   ㉮ **Ⓡ−① 은 «음수»일 것**(회전 «비용» · `133`) — 실측 **%+.3f**  ⇒  %s"
      % (r1[0], "✅ **맞았다**" if r1[0] < 0 else "🔴 **«빗나갔다»**"))
    P("   ㉯ **Ⓡ−Ⓓ 는 «모르겠다»**(그게 이 판을 «돌릴» 값어치였다) — 실측 **%+.3f** ⇒ %s"
      % (rd[0], cell(rd[1], rd[2]).split(" ")[0]))
    P("   ㉰ **회전이 «크게» 늘 것** — «관문»으로 «옮겼다»(위 ㉰)")
    P("")
    P("🚨 **㉱ — 내가 «바라던» 것은 「Ⓡ−Ⓓ «양수»」였다**(열세 판 만의 «첫» «자리 배분» 성공)")
    P("   ⇒ ✅ **«안 바라는» 쪽을 «먼저» 적었는가:** 위 표에서 **Ⓡ−Ⓓ %s** · **Ⓡ−① %s**"
      % (cell(rd[1], rd[2]).split(" ")[0], cell(r1[1], r1[2]).split(" ")[0]))
    P("   ⇒ 그리고 **「양수」여도 📏폭을 «먼저» 가른다** — Ⓡ **%.2f** vs ① **%.2f** (**%+.0f%%**)"
      % (spread(out["Ⓡ"]), sp1, 100.0 * (spread(out["Ⓡ"]) / sp1 - 1.0)))
    P("```")
    P("")
    P("```")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ 「원전의 «갈아타기»가 맞다/틀리다」 — **「«더 매력적»」의 «자»가 «우리» 것**(ⓐ 는 «근사»)")
    P("   ⛔ 「자리 배분이 «답»이다」 — **«한 판»**이다")
    P("   ⛔ **Ⓡ 의 폭을 Ⓓ 와 견주기** — **① 과 견준다**(`175` 에서 배웠다)")
    P("   ⛔ 「회전이 늘어 좋아졌다」 — **«비용»을 «뺐는지» «먼저»**(VE★)")
    P("   ⛔ 「또 실패했다」로 «세게» «닫기** — 유형 78")
    P("   ⛔ **`Ⓓ−①` 을 「갈아타는 것 «자체»의 값」으로만** — **「손절 건너뛰기」가 «섞였다»**(`176`)")
    P("   ⛔ **ⓐ 를 「매력을 «안» 정의한다」로** — **「«최신성»으로 «정의»한」 것**이다")
    P("   ⛔ **`173` 의 「체결률 36.8%」 인용** — **«중복 제거» 통과율**이다")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 손절 −10 · 목표 +30",
                     "같은 칸 5", "**같은 검출기 섞임**(VCP 76.9%)",
                     "**같은 거래 목록**(중복 제거를 ① 로 «한 번»만)"]):
        P(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
