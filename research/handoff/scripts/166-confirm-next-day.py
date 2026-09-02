# -*- coding: utf-8 -*-
r"""166 — **「돌파일 «종가»로 «확인»하고 «다음 날» 산다」** · 사전등록 `tasks/166-confirm-next-day.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  ★★★ **이 판은 `165` 와 «격»이 «다르다»:**
     **주 팔 Ⓕ 가 «완전히» 집행 가능하고, «분해 도구» Ⓕ′ 도 «시점 불가»까지다**
     ⇒ **이 판은 «전부» 「사용자가 «실제로» 할 수 있는 것」 «안»에 있다**

  🚨 **「룩어헤드」와 «시점 불가»를 «가른다»:**
     `165` Ⓔ  「α 에 «도달할지」」 = **«미래»**      → **«룩어헤드»** · 정보가 «없다» ⇒ «영영» 못 씀
     `166` Ⓕ′ 「종가가 피벗 «위»인가」 = **«과거»** → **«시점 불가»** · 정보는 «있는데» «그때»
                                                      (장중) 못 씀 ⇒ 집행을 바꾸면 «일부» 닿음
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
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
CACHE = Path(str(r91.OUT / "166-partial.json"))
MA_REF = 12377


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    P = print
    P("=" * 104)
    P("166 — **「돌파일 «종가»로 «확인»하고 «다음 날» 산다」** · 씨앗 %d × 배정 %d" % (n_seed, n_as))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/166-confirm-next-day.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## ★★★ **이 판은 «전부» 「사용자가 «실제로» 할 수 있는 것」 «안»에 있다**")
    P("")
    P("```")
    P("| | 무엇을 보나 | 이름 | 처방 |")
    P("|---|---|---|---|")
    P("| `165` Ⓔ | 「α 에 «도달할지»」 = **«미래»** | **룩어헤드** | 정보가 «없다» ⇒ **«영영» 못 씀** |")
    P("| **`166` Ⓕ′** | 「종가가 피벗 «위»인가」 = **«과거»** | 🆕 **«시점 불가»** |"
      " 정보는 «있는데» «그때» 못 씀 |")
    P("")
    P("★ 그리고 **주 팔 Ⓕ 는 «시점 불가»조차 «아니다»** — 마감 후에 알고 **다음 날 아침에 산다**")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("「종가가 피벗 «위»면 산다」   ← 출처: 원전 «글자»(「기다린다」의 «다른» 번안)")
    P("「다음 날 «시가»에 산다」     ← 출처: **사용자 방식**(장 시작 «전» 예약) · `entry-execution-method`")
    P("Δ = 1.23%p                   ← 출처: 150 의 우리−QQQ 격차")
    P("MA★ 기준 %s만            ← 출처: 156·161·162·163·164·165 의 ①" % format(MA_REF, ","))
    P("⚠️ **출처가 «빈» 가정 — «하나»:**")
    P("   ⛔ 「«종가»가 확인의 «자»다」 — 원전은 「거래될 때까지」라 했지 「종가」라 «안» 했다")
    P("     (`165` 가 «장중 α» 판이고 이 판이 «종가» 판이다. **둘은 «다른 번안»**이다)")
    P("")
    P("⛔ **🇰🇷 `05`·`sepa-nextday-breakout-findings` 를 «근거»로 «안» 쓴다 — «한국» 판정이다**")
    P("✅ **「조합(종가 확인 «+» α)은 «안 쟀다» — 원전도 «혹은»이라 했다」**")
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
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                keep[y].append(p)

    def has_next(p):
        o = p.get("o") or []
        return len(o) >= 2 and o[1] is not None and len(p["d"]) >= 2

    def confirmed(p):
        pv = p.get("pivot")
        return pv is not None and p["c"][0] is not None and p["c"][0] > pv

    # ── 갭 분포 — «선행 계산». 판정 낱말이 여기서 갈린다 ──────────────────────
    gp = [(p.get("o") or [None, None])[1] / p["c"][0] - 1.0
          for y in keep for p in keep[y]
          if has_next(p) and p["c"][0] and p["c"][0] > 0]
    gp.sort()
    ge = [(p.get("o") or [None, None])[1] / p["c"][0] - 1.0
          for y in keep for p in keep[y]
          if has_next(p) and confirmed(p) and p["c"][0] and p["c"][0] > 0]
    ge.sort()
    P("")
    P("## 🚨 **선행 계산 — 「돌파일 종가 → 다음 날 시가」 갭**")
    P("")
    P("```")
    P("★ 이 값이 **판정 «낱말»을 정한다** — 중앙 갭이 α(0.65%)와 «같은 자릿수»면")
    P("  「하루 기다린 값」이 **«갭»에 «지배»**되고, 그러면 「확인이 좋다/나쁘다」가 «아니라»")
    P("  **「«갭»이 «먹는다»」**로 적어야 한다")
    P("")
    P("| 대상 | n | **중앙** | P10 | P90 | 갭업(>0) |")
    P("|---|---:|---:|---:|---:|---:|")
    for nm, v in (("전체 후보", gp), ("**Ⓕ 대상**(종가>피벗)", ge)):
        P("| %s | %s | **%+.3f%%** | %+.3f%% | %+.3f%% | %.1f%% |"
          % (nm, format(len(v), ","), 100 * v[len(v) // 2], 100 * v[len(v) // 10],
             100 * v[9 * len(v) // 10], 100.0 * sum(1 for x in v if x > 0) / len(v)))
    P("")
    P("⇒ ✅ **① «체계»(중앙 %+.3f%%)는 α(0.65%%)의 «약 1/%d» — 「갭이 «체계적으로» 먹는다」가 «아니다»**"
      % (100 * ge[len(ge) // 2], round(0.0065 / max(abs(ge[len(ge) // 2]), 1e-9))))
    P("  갭업 %.1f%% = **거의 «동전»**. ⇒ 판정 낱말을 «바꾸지 않는다»"
      % (100.0 * sum(1 for x in ge if x > 0) / len(ge)))
    P("⇒ 🚨 **② «산포»(P10 %+.2f%% ~ P90 %+.2f%%)는 폭이 α 의 «약 %.1f배»**"
      % (100 * ge[len(ge) // 10], 100 * ge[9 * len(ge) // 10],
         (ge[9 * len(ge) // 10] - ge[len(ge) // 10]) / 0.0065))
    P("  ⇒ **거래 «하나하나»는 갭이 α 보다 «크게» 흔든다 — 다만 «방향이 없어» 60판에서 «씻긴다»**")
    P("")
    P("## ⇒ **「하루 기다리는 값」의 «체계» 부분은 «갭 탓»이 «아니다». «잡음»이지 «편향»이 아니다**")
    P("```", flush=True)

    def build(mode, drop=None):
        """mode: base | F(다음 날 시가) | F2(같은 조건 · 돌파일 피벗) | D(무작위 배제)"""
        out_, bad, npre = [], 0, 0
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                if mode in ("F", "F2", "D"):
                    # 🚨 ME★ — 「다음 날이 «없는»」 거래는 **네 팔 «전부»**에서 뺀다(유형 62)
                    if not has_next(p):
                        npre += 1
                        continue
                if mode in ("F", "F2") and not confirmed(p):
                    npre += 1
                    continue
                if drop is not None and (p["scan_date"], p["code"], p["pattern"]) in drop:
                    npre += 1
                    continue
                q = p
                if mode == "F":
                    # ★ 경로를 **하루 «밀어»** 다음 날을 «진입일»로 만든다
                    q = dict(p)
                    for k in ("o", "h", "l", "c", "d"):
                        q[k] = p[k][1:]
                    q["entry_date"] = p["d"][1]
                    q["entry_price"] = p["o"][1]
                    if q["d"][0] != p["d"][1]:
                        bad += 1
                t = pt.resolve_trade(q, ft="limit", fs="market", stop=STOP, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                c = p["code"]
                ed = q["entry_date"]
                if c in open_until and ed <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or ed
                t["stop_frac"] = STOP / 100.0
                out_.append(t)
        return out_, bad, npre

    base, _, _ = build("base")
    evF, badF, preF = build("F")
    evF2, _, preF2 = build("F2")
    pool = {y: [(p["scan_date"], p["code"], p["pattern"]) for p in ks if has_next(p)]
            for y, ks in keep.items()}
    nsig = {y: sum(1 for p in ks if has_next(p) and not confirmed(p)) for y, ks in keep.items()}

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
    out["①"], meta["①"] = sim(base, "v1|base|n%d" % n_seed)
    out["Ⓕ"], meta["Ⓕ"] = sim(evF, "v1|F|n%d" % n_seed)
    out["Ⓕ′"], meta["Ⓕ′"] = sim(evF2, "v1|F2|n%d" % n_seed)
    P("  ① %.0f만(%d) · Ⓕ %.0f만(%d) · Ⓕ′ %.0f만(%d)"
      % (st.median([a[0] for a in out["①"]]), meta["①"]["n"],
         st.median([a[0] for a in out["Ⓕ"]]), meta["Ⓕ"]["n"],
         st.median([a[0] for a in out["Ⓕ′"]]), meta["Ⓕ′"]["n"]), flush=True)

    accs, exs, ns = [], [], []
    for ai in range(n_as):
        rg = random.Random(ai + 1_000_000)
        drop = set()
        for y, ks in pool.items():
            drop |= set(rg.sample(ks, min(nsig[y], len(ks))))
        evD, _, _ = build("D", drop=drop)
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

    nmiss = sum(1 for y in keep for p in keep[y] if not has_next(p))
    nall = sum(len(v) for v in keep.values())
    P("")
    P("## 관문")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①"]])
    P("**MA★ 앵커** — ① **%.0f만** vs %s만  →  %s"
      % (m1, format(MA_REF, ","), "✅ **일치**" if abs(m1 - MA_REF) < 1.0 else "🚨 **멈춘다**"))
    P("   ★ 상시 관문 «일곱 번째»")
    P("")
    P("**MC★ 체결일 «전수» 검산** — Ⓕ 가 «전부» 돌파일 «다음» 거래일인가")
    P("   어긋난 거래 **%d** / %s  →  %s"
      % (badF, format(meta["Ⓕ"]["n"], ","), "✅ **항등식이 선다**" if badF == 0 else "🚨 **멈춘다**"))
    P("")
    P("**ME★ 「다음 날이 «없는»」 거래를 «네 팔 전부»에서 뺐는가** — 🚨 「작을 것」이 아니라 **«세었다»**")
    P("   **%d / %s = %.2f%%**  ⇒  ✅ Ⓕ·Ⓕ′·Ⓓ 에 «같은» 제외를 걸어 **비대칭이 «사라졌다»**(유형 62)"
      % (nmiss, format(nall, ","), 100.0 * nmiss / nall))
    P("   🚨 **①(앵커)만 «전체»를 쓴다** — MA★ 가 «옛 판들»과 «같은 수»를 요구하기 때문이다")
    P("   ⇒ 그래서 **주 판정은 Ⓕ−Ⓓ 이고 Ⓕ−① 은 «따로»** 적는다")
    P("")
    P("**MB★ 「중복제거 «전» 뺀 수」가 Ⓕ↔Ⓓ 에서 «정확히» 일치하는가**(`165` 가 «여기서» 터졌다)")
    P("   Ⓕ **%s** ↔ Ⓓ(설계) **%s**  →  %s"
      % (format(preF, ","), format(nmiss + sum(nsig.values()), ","),
         "✅ **같다**" if preF == nmiss + sum(nsig.values()) else "🚨 **멈춘다**"))
    P("   ★ Ⓕ 가 빼는 것 = 「다음 날 없음 **%s**」 + 「종가가 피벗 «아래» **%s**」"
      % (format(nmiss, ","), format(sum(nsig.values()), ",")))
    P("")
    P("🚨 **«최종 거래 수»는 어긋난다 — «라벨»로 두지 않고 «방향»을 본다**(유형 69):")
    P("   Ⓕ **%s** ↔ Ⓓ **%.0f**  (%+.2f%%)"
      % (format(meta["Ⓕ"]["n"], ","), meta["Ⓓ"]["n"],
         100.0 * (meta["Ⓓ"]["n"] - meta["Ⓕ"]["n"]) / max(meta["Ⓕ"]["n"], 1)))
    P("   Ⓕ 가 빼는 건 **«상관된»**(종가가 피벗 아래) 후보 · Ⓓ 는 **«무작위»** ⇒ 중복제거가 «다르게» 이어진다")
    if meta["Ⓓ"]["n"] < meta["Ⓕ"]["n"]:
        P("   ⇒ ★ **Ⓓ 의 «최종» 거래가 «더» 적다 ⇒ Ⓓ 가 「빼는 «비용»」을 «더» 문다**")
        P("   ⇒ **Ⓕ−Ⓓ 가 «위»로 치우친다 = «확인에 «유리»»한 방향이다**")
    else:
        P("   ⇒ ★ **Ⓕ 의 «최종» 거래가 «더» 적다 ⇒ Ⓕ−Ⓓ 가 «아래»로 치우친다 = «확인에 «불리»»**")
    P("")
    P("🚨🚨 **그리고 «거른 양»이 α 와 «전혀» 다르다 — 「보다 낫다」를 «못» 쓰는 이유다:**")
    P("   Ⓕ  중복제거 «전» **%s / %s = %.1f%%** 를 «거른다»"
      % (format(preF, ","), format(nall, ","), 100.0 * preF / nall))
    P("   α 0.65% (`165`)  **5,825 / 24,995 = 23.3%** 를 «거른다»")
    P("   ⇒ ★ **Ⓕ 가 «두 배 넘게» 거른다** ⇒ **«강도»가 «전혀» 다르다**")
    P("   ⇒ ⛔ **「확인이 α «보다» 낫다」를 «쓰지 않는다».** 「**«각각» «얼마»를 «남기나»**」로만 적는다")
    P("   ⇒ ⛔ **«단가»(거른 한 건당 %p) «금지»** — 유형 68 이다")
    P("")
    P("🚨 **사전등록 ㉱ 가 «돌리기 «전»»에 «반증»됐다 — 그대로 적는다:**")
    P("   ㉱ 「Ⓕ 는 «덜» 거를 것」  →  🔴 **실측 «50.8%» vs α «23.3%» — «두 배 넘게» 거른다**")
    P("   ★ 그리고 **«근거» 자체가 «다른 것»을 비교했다** —")
    P("     「`165` 의 5일 «풀백률» 70.4% vs Ⓕ 는 «하루»뿐」은 **«풀백률»** 비교이고,")
    P("     맞는 비교는 **「α «대비» 거르는 «양»」**이었다")
    P("   ⇒ ★ **「예상이 틀렸다」와 「«근거»가 «다른 것»을 쟀다」는 «다른» 잘못**이고, «둘 다» 적는다")
    P("```", flush=True)

    P("")
    P("## 1. 팔 넷")
    P("")
    P("| 팔 | 거래 | 세후 총액(중앙) | 연 환산 | 📏폭 | 낙폭 중앙 | 회복 |")
    P("|---|---:|---:|---:|---:|---:|---:|")
    for nm in ("①", "Ⓕ", "Ⓕ′", "Ⓓ"):
        v = out[nm]
        mm = st.median([a[0] for a in v])
        P("| **%s** | %.0f | %.0f만 | **%+.2f%%** | %.2f | %+.1f%% | %.1f년 |"
          % (nm, meta[nm]["n"], mm, acc.cagr(mm, YRS), spread(v),
             st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0))

    P("")
    P("## 2. 🚨 **분해**")
    P("")
    P("```")
    P("★★ **세 수를 «이렇게» 읽는다:**")
    P("   **Ⓕ′−Ⓓ** = 「확인으로 «거른» 값」 = **«시점 불가»**(정보는 있으나 장중엔 못 씀)")
    P("   **Ⓕ−Ⓕ′** = 「하루 «늦게» 사는 값」")
    P("   **Ⓕ−Ⓓ**  = **「실제로 «남는» 것」 ← «집행 가능»한 «유일한» 수**")
    P("```")
    P("")
    P("| 짝 | 차 | **95% CI** | 판정 |")
    P("|---|---:|---|:--|")
    rows = (("**Ⓕ′−Ⓓ**「확인으로 «거른»」", "Ⓕ′", "Ⓓ"),
            ("**Ⓕ−Ⓕ′**「하루 «늦게» 사는」", "Ⓕ", "Ⓕ′"),
            ("**Ⓕ−Ⓓ** «남는 것» ★", "Ⓕ", "Ⓓ"),
            ("Ⓕ−① «따로»", "Ⓕ", "①"))
    for lab, x, y in rows:
        mu, lo, hi = dif(x, y)
        if lo > DELTA:
            vd = "✅ **Δ «보다» 강하게 남긴다**"
        elif lo > 0 and hi > DELTA:
            vd = "**4b** 🚨 **CI 가 Δ 를 «걸침»**"
        elif lo > 0:
            vd = "**4a** 진짜인데 **«확실히» Δ 미만**"
        elif hi < 0 and mu <= -DELTA:
            vd = "🚨 **«거꾸로»다 — 확인이 «해롭다»**"
        elif hi < 0:
            vd = "⚠️ 음수이나 **Δ 미만**"
        else:
            vd = "🚨 **못 가린다**"
        P("| %s | **%+.3f%%p** | [%+.3f, %+.3f] | %s |" % (lab, mu, lo, hi, vd))
    P("")
    P("```")
    P("🚨 **«두 축»을 «같이» 읽는 판정표 — 「Ⓕ−①」 칸이 «없어» «돌리기 전»에 «넣었다»**")
    P("   (161·162 에 이어 **「«안 바라는» 칸이 «없다」의 «세 번째»**. 다만 이번엔 **«돌리기 «전»»**이다)")
    P("")
    fd, fdlo, _fdhi = dif("Ⓕ", "Ⓓ")
    f1, _f1lo, f1hi = dif("Ⓕ", "①")
    P("| Ⓕ−Ⓓ | Ⓕ−① | 적을 문장 |")
    P("|---|---|---|")
    P("| > 0 | > 0 | 「확인이 «값을 한다»」 |")
    P("| > 0 | −Δ < · < 0 | 「«고를 줄»은 «알지만» «작게» 손해」 |")
    P("| **> 0** | **≤ −Δ** | 🚨 **「«고를 줄»은 «알아도» — «쓸 수 «없다»»」** |")
    P("| ≈ 0 | — | 「무작위와 «구분 안 됨»」 |")
    P("| < 0 | — | 🚨 「**«거꾸로»다**」 |")
    P("")
    if fdlo <= 0:
        cell = ("🚨 **「무작위와 «구분 안 됨»」**" if _fdhi >= 0
                else "🚨 **「«거꾸로»다」**")
    elif f1hi > 0:
        cell = "✅ **「확인이 «값을 한다»」**"
    elif f1 > -DELTA:
        cell = "⚠️ **「«고를 줄»은 «알지만» «작게» 손해」**"
    else:
        cell = "🚨 **「«고를 줄»은 «알아도» — «쓸 수 «없다»»」**(거르는 «값»이 «고르는 값»을 «압도»)"
    P("⇒ **Ⓕ−Ⓓ = %+.3f%%p · Ⓕ−① = %+.3f%%p  →  %s**" % (fd, f1, cell))
    P("")
    P("★ **합 검산**(씨앗별 차의 평균이라 «더해져야» 한다):")
    a1 = dif("Ⓕ", "Ⓕ′")[0]
    a2 = dif("Ⓕ′", "Ⓓ")[0]
    a3 = dif("Ⓕ", "Ⓓ")[0]
    P("   (Ⓕ−Ⓕ′) + (Ⓕ′−Ⓓ) = %+.3f  vs  Ⓕ−Ⓓ = %+.3f   차 **%+.4f**" % (a1 + a2, a3, a1 + a2 - a3))
    P("")
    P("**MD★ — 노출을 «분포»로** · 문턱은 **«두 단계»**")
    e = meta["Ⓓ"]["expo_d"]
    P("   ① **%.1f%%** · Ⓕ **%.1f%%** · Ⓕ′ **%.1f%%** · Ⓓ **%.1f ~ %.1f%%**(중앙 **%.1f%%**)"
      % (meta["①"]["expo"], meta["Ⓕ"]["expo"], meta["Ⓕ′"]["expo"], min(e), max(e), st.median(e)))
    P("   ⇒ 주 판정 짝 **Ⓕ↔Ⓓ 노출 차 %+.1f%%p**" % (meta["Ⓕ"]["expo"] - st.median(e)))
    P("   🚨 **문턱은 «안» 만든다** — 「노출 Δ%p ↔ 성적 Δ%p」 환산이 «안 된다»")
    P("   ✅ **«수»를 적고 「이 값으로 «못 정한다」** — «빈칸»이 아니라 «측정된 미결»")
    P("")
    P("**위험 축 «둘»**(낙폭 «중앙» · 📏폭) · 「위험 «하나»만 나쁨」 칸을 «미리»:")
    P("   자산 «이김» + 위험 «하나»만 나쁨  →  「맞바꿈 — 사용자 «선택»」")
    P("   자산 «짐»   + 위험 «하나»만 나쁨  →  ⛔ 「**선택지가 «아니다». «진» 것이다**」")
    P("")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ **「확인이 α «보다» 낫다」** — 거른 «양»이 %.1f%% vs 23.3%% 로 «강도»가 다르다"
      % (100.0 * preF / nall))
    P("   ⛔ **Ⓕ′ 의 수를 «전략 성적»으로** — «시점 불가»다")
    P("   ⛔ 「원전이 맞다/틀리다」 · ⛔ 🇰🇷 `05`·한국 판정을 «근거»로")
    P("   ✅ **「조합(종가 확인 «+» α)은 «안 쟀다» — 원전도 «혹은»이라 했다」**")
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
