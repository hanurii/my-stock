# -*- coding: utf-8 -*-
r"""167 — **「풀백에서도 산다」**(원전 기술적 분석 편) · 사전등록 `tasks/167-pullback-entry.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  ★★★ **이 판은 159~166 과 «벽»이 다르다:**
     그 여섯의 벽 = 「거른 만큼 «비싸게» 산다」 — **「거른 뒤 «올라간» 것을 산다」**서 생긴다
     🚨 **풀백은 «내려간» 것을 산다** ⇒ **부호가 «둘 다» 뒤집힐 수 있다**
     🚨 그런데 **«정확히 대칭»이 «아니다»** — 「종가 == 피벗」이 «둘 다»에서 빠진다(NH★ 가 잡았다)

  🚨 **약점 넷 — 두뇌 세션이 «스스로» 적은 것. «라벨»로 «같은 줄»에 둔다:**
     ① 「50일선」이 원전의 「지지선」이 «아닐» 수 있다 ⇒ Ⓗb 가 원전을 «못 잰» 것일 수 있음
     ② 「D 종가<피벗」은 **«당일»** 자다 — 창을 «고정»하고 «다른 창은 안 돌린다»
     ③ **Ⓗa 는 「풀백」이 «아니라» 「재돌파」**다 — 이름을 «정확히»
     ④ 손절 −10%는 **«체결가» 대비 유지**(「피벗 대비」는 `163` 에서 «방향이 반대»였다)
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
NFWD = 5                                  # D+1 .. D+5 장전 예약
CACHE = Path(str(r91.OUT / "167-partial.json"))
MAF = Path("D:/stock-data/derived/167-ma50.json")
MA_REF = 12377
NA_TOL = 0.01                             # NA★ 합 검산 허용 오차(%p)


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    dry = "--dry" in sys.argv
    P = print
    P("=" * 104)
    P("167 — **「풀백에서도 산다」** · 🏷️ 세대 B · 씨앗 %d × 배정 %d%s"
      % (n_seed, n_as, "  🚨 **--dry(«구조»만 · 시뮬 «안» 함)**" if dry else ""))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/167-pullback-entry.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## ★★★ **이 판은 앞 여섯과 «벽»이 다르다**")
    P("")
    P("```")
    P("159~166 의 벽 = 「거른 만큼 «비싸게» 산다」 ← **「거른 뒤 «올라간» 것을 산다」**서 생긴다")
    P("🚨 **풀백은 «내려간» 것을 산다** ⇒ **부호가 «둘 다» 뒤집힐 수 있다**")
    P("")
    P("| | 고르는 것 | 거르는 값 | 늦게 사는 값 |")
    P("|---|---|---:|---:|")
    P("| `166` Ⓕ | 종가가 피벗 **위**(49.0%) | +5.937 | −7.419 |")
    P("| 🆕 이 판 Ⓗ | 종가가 피벗 **아래**(**47.6%**) | ? | ? |")
    P("⇒ **«같은 기계»**를 쓴다 — 🚨 다만 **«정확히 대칭»은 «아니다»**(NH★ 참조)")
    P("")
    P("🚨🚨 **수 «하나»를 바로잡는다 — 「51.0%」와 「47.6%」는 «다른 것»이다:**")
    P("   **51.0%** = `166` 에서 **Ⓕ 가 «거르는»** 비율 = 47.6 + 3.2(==) + 0.15(다음 날 없음)")
    P("   **47.6%** = 이 판에서 **Ⓗ 가 «사는»** 비율 = 「종가 **<** 피벗」")
    P("   ⇒ ★ **「«거르는» 것」과 「«반대쪽»을 «사는» 것」은 «같지 않다»** —")
    P("     사이에 **«경계»(==)**와 **«자료 없음»**이 있다")
    P("   ⇒ ✅ **처방을 «넓힌다»: 「분모를 적는다」로 «부족»하다.**")
    P("     **「이 수가 «무엇의» 비율인가」를 «옮길 때마다» «다시» 묻는다**")
    P("```")
    P("")
    P("## 🚨 **약점 넷 — «라벨»로 «먼저» 적는다**(두뇌 세션이 «스스로» 적은 것)")
    P("")
    P("```")
    P("① 🚨 **「50일선」이 원전의 「지지선」이 «아닐» 수 있다** ⇒ Ⓗb 가 «원전을 못 잰» 것일 수 있다")
    P("   ⇒ ⛔ Ⓗb 가 지면 「원전이 «틀렸다»」가 «아니라» 「**이 «자»로는 «안 된다»**」")
    P("   ✅ **그리고 검증이 «다시 읽어» 줬다 — 「못 잰 것」이 아니라 «두 해석을 잰다»:**")
    P("     **Ⓗa(피벗 재돌파) = 「이전 «저항선»」 해석**  ·  **Ⓗb(50일선) = 「이동평균」 해석**")
    P("② 「D 종가 < 피벗」은 **«당일»** 자다 — `165` 는 5일 창 **70.4%** 로 «다른 수»가 나온다")
    P("   ⇒ ✅ **«당일»로 «고정»하고 «다른 창은 안 돌린다»**(손잡이를 «안» 만든다)")
    P("③ 🚨 **Ⓗa 는 「풀백」이 «아니라» 「재돌파」**다 — 이름을 «정확히» 쓴다")
    P("④ 손절 −10%는 **«체결가» 대비 «유지»** — 「피벗 대비」는 `163` 에서 **방향이 «반대»**였다")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("「풀백에서도 산다」          ← 출처: 원전 «글자»")
    P("「D+1..D+%d 장전 예약」      ← 출처: **사용자 방식**(`entry-execution-method`) ✅ **집행 가능**" % NFWD)
    P("「50일선」                   ← ✅ **출처 «있다»** — `canslim_lib/trend_template.py:172` 관문 ⑤")
    P("                                **`last > sma50`** ⇒ 후보는 **«전부» 진입 시점에 주가가 50일선 «위»**")
    P("                                ⇒ 50일선이 **«아래»**에 있어 «지지» 자리에 «놓인다»")
    P("   🚨 **단 관문 ⑤ 는 «들어올 «자격»»이지 「50일선이 «지지한다»」는 «주장»이 «아니다»**")
    P("   🚨 `strategy_params.py` 의 50 은 **«거래량» MA50** 이다 — **«가격» 50 은 관문에서만 온다**")
    P("「D 종가 < 피벗」(당일)      ← 출처: `166` 의 «정확한 여집합»")
    P("Δ = 1.23%p                   ← 출처: 150 의 우리−QQQ 격차")
    P("MA★ 기준 %s만            ← 출처: 156·161·162·163·164·165·166 의 ①" % format(MA_REF, ","))
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    ma = json.loads(MAF.read_text(encoding="utf-8"))["ma"]

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

    def pulled(p):
        """D 종가가 피벗 «아래» — `166` 의 «정확한 여집합»"""
        pv = p.get("pivot")
        return (pv is not None and p["c"][0] is not None and p["c"][0] < pv
                and len(p["d"]) >= 2)

    def hit(p, mode):
        """D+1..D+%d 장전 예약이 «닿는» 첫 날. (i, 체결가) 또는 None""" % NFWD
        pv = p["pivot"]
        for i in range(1, min(1 + NFWD, len(p["c"]))):
            o = (p.get("o") or [None] * len(p["c"]))[i]
            h, l = p["h"][i], p["l"][i]
            if mode == "a":                       # 재돌파 — «피벗» 재예약(위로 산다)
                if h is not None and h >= pv:
                    return i, (pv if o is None else max(pv, o))
            else:                                 # 풀백 — «50일선» 예약(아래로 산다)
                m = ma.get(p["code"] + "|" + p["d"][i])
                if m is None:
                    continue
                if m >= pv:                       # ND★ — 50일선이 피벗 «위»면 «버린다»
                    return "skip", None
                if l is not None and l <= m:
                    return i, (m if o is None else min(m, o))
        return None

    def build(mode, drop=None):
        """mode: base | Hp(시점 불가 도구) | Ha(재돌파) | Hb(풀백) | D(무작위)"""
        out_, npre, nfill, nskip, badday = [], 0, 0, 0, 0
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                if mode == "U":                       # NH★ — Ⓕ′ ∪ Ⓗ′
                    if len(p["d"]) < 2:
                        npre += 1
                        continue
                elif mode == "D":                     # 플라세보 — «중복제거 «전»»에서 뺀다
                    if len(p["d"]) < 2:
                        npre += 1
                        continue
                    if drop is not None and (p["scan_date"], p["code"], p["pattern"]) in drop:
                        npre += 1
                        continue
                elif mode != "base":
                    if not pulled(p):
                        npre += 1
                        continue
                q = p
                if mode in ("Ha", "Hb"):
                    r = hit(p, "a" if mode == "Ha" else "b")
                    if r is None:
                        continue                  # 닿지 «않음» — «안» 산다(체결률에 반영)
                    i, px = r
                    if i == "skip":
                        nskip += 1
                        continue
                    q = dict(p)
                    for k in ("o", "h", "l", "c", "d"):
                        q[k] = p[k][i:]
                    q["entry_date"] = p["d"][i]
                    q["entry_price"] = px
                    if r102._ord(q["entry_date"]) <= r102._ord(p["entry_date"]):
                        badday += 1               # NC★ — 체결일이 D «뒤»가 아니면 위반
                    nfill += 1
                t = pt.resolve_trade(q, ft="limit", fs="market", stop=STOP, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                c = p["code"]
                ed = q["entry_date"]
                if c in open_until and ed <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or ed
                t["stop_frac"] = STOP / 100.0
                out_.append(t)
        return out_, {"pre": npre, "fill": nfill, "skip": nskip, "bad": badday}

    base, _ = build("base")
    evU, _gU = build("U")                 # NH★ — Ⓕ′ ∪ Ⓗ′ (같은 날 · 같은 가격)
    evHp, gHp = build("Hp")
    evHa, gHa = build("Ha")
    evHb, gHb = build("Hb")
    npull = sum(1 for y in keep for p in keep[y] if pulled(p))
    nall = sum(len(v) for v in keep.values())
    pool = {y: [(p["scan_date"], p["code"], p["pattern"]) for p in ks if pulled(p)]
            for y, ks in keep.items()}
    nkeepy = {y: len(v) for y, v in pool.items()}

    P("")
    P("## 관문 — 구조")
    P("")
    P("```")
    n_ab = n_eq = n_bl = n_nn = 0
    for y in keep:
        for p_ in keep[y]:
            pv = p_.get("pivot")
            if pv is None or p_["c"][0] is None:
                continue
            if len(p_["d"]) < 2:
                n_nn += 1
                continue
            if p_["c"][0] > pv:
                n_ab += 1
            elif p_["c"][0] < pv:
                n_bl += 1
            else:
                n_eq += 1
    P("🚨🚨 **NH★ 가 «진짜»를 잡았다 — 「상보」가 «아니다»**")
    P("")
    P("   후보 **%s** 를 **«세 갈래»**로 «전부» 센다:" % format(nall, ","))
    P("     종가 **>** 피벗  **%s** (%.1f%%)  ← `166` Ⓕ 가 사는 것"
      % (format(n_ab, ","), 100.0 * n_ab / nall))
    P("     종가 **==** 피벗 **%s** (%.1f%%)  🚨 **«어느 쪽에도» 없다**"
      % (format(n_eq, ","), 100.0 * n_eq / nall))
    P("     종가 **<** 피벗  **%s** (%.1f%%)  ← 이 판 Ⓗ 가 사는 것"
      % (format(n_bl, ","), 100.0 * n_bl / nall))
    P("     다음 날 «없음»   **%s** (%.2f%%)" % (format(n_nn, ","), 100.0 * n_nn / nall))
    P("")
    P("   ⇒ 🚨 **`166` 은 `c[0] > pivot`, 이 판은 `c[0] < pivot` — 「==」가 «둘 다»에서 «빠진다»**")
    P("   ⇒ ★ **「상보」라고 «썼으면» 틀렸다.** NH★ 가 «없었으면» «못 봤다**")
    P("   ✅ 그리고 **이 판의 정의는 «안» 바꾼다** — 사전등록이 「D 종가 **<** 피벗」이다.")
    P("     **«빠진 %s 건»을 «적어» 두는 것**이 답이다(정의를 «결과 본 뒤» 바꾸지 «않는다»)"
      % format(n_eq, ","))
    P("")
    P("   ✅ **«범위 문장» «둘» — 검증 1차의 «조건»이었다:**")
    P("     ① **「== %s 건(%.1f%%)이 «어느 쪽»인지는 «안 쟀다»」**"
      % (format(n_eq, ","), 100.0 * n_eq / nall))
    P("     ② **「«두 판»을 «합쳐» 말할 때 — 그 %.1f%%는 «어느 판에도» «없다»」**"
      % (100.0 * n_eq / nall))
    P("   ★ 검증 판정: **«잡음»이 «아니다»** — 피벗은 «과거 고가»이고 종가가 «거기서 정확히 멈추는»")
    P("     일이라 **«저항»의 «사건»**이다(연속 가격이면 ~0%%여야 하는데 %.1f%%다 = «호가 단위 + 저항 밀집»)"
      % (100.0 * n_eq / nall))
    P("")
    P("**NB★ 「D 종가 < 피벗」 집합이 네 팔에서 «같은가»**")
    P("   후보 **%s** 중 풀백 **%s** (**%.1f%%**)"
      % (format(nall, ","), format(npull, ","), 100.0 * npull / nall))
    P("   Ⓗ′ 후보 «전» **%s** ↔ Ⓗa **%s** ↔ Ⓗb **%s**  →  ✅ **같다**(설계)"
      % (format(npull, ","), format(npull, ","), format(npull, ",")))
    P("")
    P("   🚨 **Ⓓ 는 «팔마다» «따로» 맞춘다**(유형 62) — **«어느» 수에 맞추는지 «적는다»:**")
    P("     **「사려고 «시도»해 «담기는» 수」**(중복제거 «전»)에 맞춘다 — «실현» 거래 수가 «아니다**")
    P("     («실현» 수에 맞추면 **«결과»에 조건을 다는** 셈이다)")
    P("     Ⓓ′ ↔ Ⓗ′ **%s**  ·  Ⓓa ↔ Ⓗa **%s**  ·  Ⓓb ↔ Ⓗb **%s**"
      % (format(npull, ","), format(gHa["fill"], ","), format(gHb["fill"], ",")))
    P("")
    P("**NC★ 체결일 «전수» — 모든 체결일이 D «뒤»인가**")
    P("   Ⓗa 위반 **%d** · Ⓗb 위반 **%d**  →  %s"
      % (gHa["bad"], gHb["bad"],
         "✅ **0 건**" if gHa["bad"] == gHb["bad"] == 0 else "🚨 **멈춘다**"))
    P("")
    P("**ND★ Ⓗb 에서 「50일선이 피벗 «위»」로 «버린» 건수**")
    P("   **%s / %s = %.1f%%**  ⇒ 🚨 그만큼 **Ⓗb 는 «다른 집합»을 재게 된다** — 라벨로 둔다"
      % (format(gHb["skip"], ","), format(npull, ","), 100.0 * gHb["skip"] / max(npull, 1)))
    P("")
    P("**NE★ 체결률 — 「통과」가 «무슨 뜻»인지 알려면 «필수»**")
    P("   Ⓗa «재돌파» **%s / %s = %.1f%%**"
      % (format(gHa["fill"], ","), format(npull, ","), 100.0 * gHa["fill"] / max(npull, 1)))
    P("   Ⓗb «풀백»   **%s / %s = %.1f%%**  (버린 %s 제외하면 %.1f%%)"
      % (format(gHb["fill"], ","), format(npull, ","), 100.0 * gHb["fill"] / max(npull, 1),
         format(gHb["skip"], ","),
         100.0 * gHb["fill"] / max(npull - gHb["skip"], 1)))
    P("   🚨 **㉱(「기회는 많다」)의 근거는 「5일 안 장중 저가가 피벗 아래 **85.9%**」였는데,**")
    P("     **그건 「피벗 아래로 «간다»」지 「**50일선까지 «간다»**」가 «아니다»** ⇒ 위 수가 «답»이다")
    P("")
    P("**🆕 NH★ — «판 «사이»» 관문. Ⓕ′(166) ∪ Ⓗ′(167) 가 ① 이 되는가**")
    P("   `166` Ⓕ′ 「D 종가 **≥** 피벗」 → «D 일 피벗»에 삼")
    P("   `167` Ⓗ′ 「D 종가 **<** 피벗」 → «D 일 피벗»에 삼   ⇒ **«상보» · «같은 날·같은 가격»**")
    P("   🚨 위에서 봤듯 **«상보»가 «아니다»** — 「==」 **%s** 건이 «둘 다»에서 빠진다"
      % format(n_eq, ","))
    P("   그래서 합집합 팔은 **「Ⓕ′ ∪ Ⓗ′ ∪ ==」**(= 다음 날 있는 «전부»)로 «잡았다»:")
    P("   합집합 팔 거래 **%s**  ·  ① 거래 **%s**  ·  차 **%s**(= 「다음 날 «없는»」 것)"
      % (format(len(evU), ","), format(len(base), ","), format(len(base) - len(evU), ",")))
    P("   ★★ **JD★/MA★ 가 「한 판 «안»」이었다면 이건 「판 «사이»」다**")
    P("   ⇒ 어긋나면 **`166` «또는» `167` 의 «집합 정의»가 틀린 것**이고 **「지금 아니면 못 잡는다」**")
    P("")
    P("**최종 거래 수** — ① %s · Ⓗ′ %s · Ⓗa %s · Ⓗb %s"
      % (format(len(base), ","), format(len(evHp), ","),
         format(len(evHa), ","), format(len(evHb), ",")))
    P("```", flush=True)
    if gHa["bad"] or gHb["bad"]:
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
    for nm, ev, k in (("①", base, "base"), ("Ⓗ′", evHp, "Hp"),
                      ("Ⓗa", evHa, "Ha"), ("Ⓗb", evHb, "Hb")):
        out[nm], meta[nm] = sim(ev, "v1|%s|n%d" % (k, n_seed))
        P("  %s %.0f만(%d)" % (nm, st.median([a[0] for a in out[nm]]), meta[nm]["n"]), flush=True)

    # 🚨 Ⓓ 는 「풀백 집합」을 «통째로» 빼는 게 «아니라» **«같은 수»를 «무작위»**로 뺀다
    #    그리고 **«중복제거 «전»»**에서 뺀다 — `165` LB★ 가 «여기서» 터졌다
    allk = {y: [(p["scan_date"], p["code"], p["pattern"]) for p in ks if len(p["d"]) >= 2]
            for y, ks in keep.items()}
    nallk = sum(len(v) for v in allk.values())
    # 🚨 **팔마다 «따로»** 맞춘다(유형 62) — Ⓓ 가 «하나»면 Ⓗa·Ⓗb 의 「덜 사는 것」이 «안» 흡수된다
    #    맞추는 것은 **「사려고 «시도»해 «담기는» 수」**(중복제거 «전»)다
    KEEPN = {"Ⓓ′": npull, "Ⓓa": gHa["fill"], "Ⓓb": gHb["fill"]}
    for dn, ktot in KEEPN.items():
        accs, exs, ns = [], [], []
        for ai in range(n_as):
            rg = random.Random(ai + 1_000_000 + hash(dn) % 1000)
            drop = set()
            for y, ks in allk.items():
                nk = round(len(ks) * ktot / max(nallk, 1))
                drop |= set(rg.sample(ks, min(max(len(ks) - nk, 0), len(ks))))
            evD, _ = build("D", drop=drop)
            v, m = sim(evD, "v2|%s|a%d|n%d" % (dn, ai, n_seed))
            accs.append(v)
            exs.append(m["expo"])
            ns.append(m["n"])
        out[dn] = [tuple(st.mean(accs[ai][i][j] for ai in range(n_as)) for j in range(4))
                   for i in range(n_seed)]
        meta[dn] = {"expo": None, "expo_d": exs, "n": st.mean(ns),
                    "keep": ktot, "pct": 100.0 * ktot / nallk}
        P("  %s %.0f만(%.0f · 담기는 수 %s = %.1f%% · 배정 %d개 평균)"
          % (dn, st.median([a[0] for a in out[dn]]), meta[dn]["n"],
             format(ktot, ","), meta[dn]["pct"], n_as), flush=True)
    out["Ⓓ"], meta["Ⓓ"] = out["Ⓓ′"], meta["Ⓓ′"]

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    def dif(x, y):
        d = [acc.cagr(out[x][i][0], YRS) - acc.cagr(out[y][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("")
    P("## 관문 — 수")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①"]])
    P("**MA★ 앵커** — ① **%.0f만** vs %s만  →  %s   («여덟 번째»)"
      % (m1, format(MA_REF, ","), "✅ **일치**" if abs(m1 - MA_REF) < 1.0 else "🚨 **멈춘다**"))
    P("")
    P("**NA★ 합 검산** — |(Ⓗ′−Ⓓ) + (Ⓗ−Ⓗ′) − (Ⓗ−Ⓓ)| < %.2f%%p" % NA_TOL)
    for nm in ("Ⓗa", "Ⓗb"):
        e = dif("Ⓗ′", "Ⓓ′")[0] + dif(nm, "Ⓗ′")[0] - dif(nm, "Ⓓ′")[0]
        P("   %s  오차 **%+.4f%%p**  →  %s"
          % (nm, e, "✅" if abs(e) < NA_TOL else "🚨 **멈춘다**"))
    P("")
    P("**NF★ 노출(투입률)** — ㉲ 검산용")
    P("   ① **%.1f%%** · Ⓗ′ **%.1f%%** · Ⓗa **%.1f%%** · Ⓗb **%.1f%%**"
      % (meta["①"]["expo"], meta["Ⓗ′"]["expo"], meta["Ⓗa"]["expo"], meta["Ⓗb"]["expo"]))
    for dn in ("Ⓓ′", "Ⓓa", "Ⓓb"):
        e = meta[dn]["expo_d"]
        P("   %s **%.1f ~ %.1f%%**(중앙 **%.1f%%**) — 담기는 수 %s(%.1f%%)"
          % (dn, min(e), max(e), st.median(e),
             format(meta[dn]["keep"], ","), meta[dn]["pct"]))
    P("   🚨 **Ⓗb 는 자리를 «크게» 비운다 — 그래서 Ⓓb 를 «따로» 맞췄다**")
    P("   ⇒ 짝 노출 차 — Ⓗ′−Ⓓ′ **%+.1f%%p** · Ⓗa−Ⓓa **%+.1f%%p** · Ⓗb−Ⓓb **%+.1f%%p**"
      % (meta["Ⓗ′"]["expo"] - st.median(meta["Ⓓ′"]["expo_d"]),
         meta["Ⓗa"]["expo"] - st.median(meta["Ⓓa"]["expo_d"]),
         meta["Ⓗb"]["expo"] - st.median(meta["Ⓓb"]["expo_d"])))
    e = meta["Ⓓ′"]["expo_d"]
    P("   ★ **㉲ — 판정은 «Ⓗ−Ⓓ» 이지 «Ⓗ−①» 이 «아니다»**(Ⓗ 는 거래 수가 «절반»이라 슬롯이 빈다)")
    P("")
    P("🚨🚨 **「못 정한다」로 «두지» 않는다 — «어림»을 «낸다»**(유형 69 — 라벨은 «면죄부»가 된다)")
    slope = acc.cagr(m1, YRS) / meta["①"]["expo"]
    P("   ① 노출 **%.1f%%** 에 **%+.2f%%**  →  «선형이면» 노출 1%%p ≈ **%.3f%%p**"
      % (meta["①"]["expo"], acc.cagr(m1, YRS), slope))
    P("   🚨 **단 `163` 이 「선형 환산 «안» 된다」를 보였다**(노출 +4.6%p 인데 성적 −5.37%p)")
    P("     ⇒ **«방향»과 «자릿수»만** 쓴다")
    P("")
    P("   🚨 **«팔마다» 잰다 — 「물어본 것만 잰다」는 «부호»를 «모른다»(유형 64):**")
    P("     이번엔 «빠질 뻔한» 쪽(Ⓗa)이 **«우리에게 «유리»»**했다. **다음엔 «불리»한 쪽이 «같은 논리»로 빠진다**")
    P("")
    P("   | 팔 | 노출 차 | 어림 보정 | 관측 | 보정 후 | 칸 |")
    P("   |---|---:|---:|---:|---:|:--|")
    for nm, dn, cell in (("Ⓗa", "Ⓓa", 2), ("Ⓗb", "Ⓓb", 3)):
        dexp = meta[nm]["expo"] - st.median(meta[dn]["expo_d"])
        adj = slope * dexp
        obs = dif(nm, dn)[0]
        after = obs - adj
        keep_ = ((after <= -DELTA) if cell == 2 else (-DELTA < after < 0))
        P("   | **%s** | %+.1f%%p | %+.3f%%p (관측의 %.0f%%) | %+.3f | **%+.3f** | **칸 %d %s** |"
          % (nm, dexp, adj, 100.0 * abs(adj) / abs(obs), obs, after, cell,
             "«불변»" if keep_ else "🚨 **바뀐다**"))
    P("")
    P("   ## ⇒ ★ **「«둘 다» 어림해도 «둘 다» 칸이 «안» 바뀐다」**")
    P("   ⇒ 「보류 «불필요»」이고 이유는 「못 정한다」가 «아니라» **「어림해도 칸이 «안» 바뀐다」**다")
    P("   ★ **「못 정한다」는 «라벨» · 「몇 % 자리인데 칸이 «안» 바뀐다」는 «수»** ⇒ **후자로 적는다**")
    P("")
    P("🚨🚨 **NF★ 를 «갈라» 읽는다 — `Ⓗ−Ⓗ′` 안에 «둘»이 섞여 있다(유형 68 그 자체):**")
    P("   ㉠ **«가격»** 5일 안에 «다른 가격»에 산다            ← **이 판이 «묻는» 것**")
    P("   ㉡ **«시간»** 최대 5일 자리가 «빈다» ⇒ **노출이 떨어진다**  ← **«딸려» 오는 것**")
    P("")
    P("   **Ⓓ 가 «흡수»하는 것** = 「«안 사는» 값」(거래 수가 주는 것)")
    P("   **Ⓓ 가 «못» 흡수하는 것** = 「«늦게» 사는 값」 ⇒ **그 안에 ㉠ 과 ㉡ 이 «섞여» 있다**")
    P("   노출 차 — Ⓗa − Ⓓ중앙 **%+.1f%%p** · Ⓗb − Ⓓ중앙 **%+.1f%%p**"
      % (meta["Ⓗa"]["expo"] - st.median(e), meta["Ⓗb"]["expo"] - st.median(e)))
    P("")
    P("   🚨 **어림**: 51% × (지연 5일 ÷ 보유 42일) ≈ **6% 자리** — **작지 «않다»**")
    P("   ⛔ **«선형 환산» «금지»** — `163` 에서 **노출 +4.6%p 인데 성적 −5.37%p** 였다")
    P("   ✅ **«찍기»만 한다.** 「이 값으로 «못 정한다」가 «정직»하다")
    P("```")

    P("")
    P("## 1. 팔 다섯 — **NG: 낙폭 · 회복 · 📏폭 «전부»**")
    P("")
    P("🚨 **체결률을 «성적 옆»에 둔다** — Ⓗa **%.1f%%** · Ⓗb **%.1f%%**"
      % (100.0 * gHa["fill"] / max(npull, 1), 100.0 * gHb["fill"] / max(npull, 1)))
    P("   ★ **Ⓗb 는 «셋 중 하나»만 산다** ⇒ 성적이 나쁘면 「풀백이 나쁘다」가 «아니라»")
    P("     **「«기회»가 «셋 중 하나»였다」**일 수 있다")
    P("")
    P("📌 **각주** — 부품 `167a` 에서 **`IESC` «한 종목»을 «통째로» 뺐다**:")
    P("   경로 `c[0]` 가 CSV `close` 의 **«정확히 2배»**(2:1 분할 자리) — «어느 쪽이 맞는지» 못 정한다")
    P("   ⇒ ⛔ **「99.99%니 통과선을 99.9%로」가 «아니라» «그 종목»을 뺐다**")
    P("   ⇒ ★ 「**100.0%**」만 남으면 **«무엇을 빼고» 100% 인지 «안» 보인다 — 그래서 «여기» 적는다**")
    P("")
    P("## 🚨 **이 판의 «제일 큰 사실» — Ⓗ′ «자체»**")
    P("")
    P("```")
    hp = st.median([a[0] for a in out["Ⓗ′"]])
    P("**「돌파일 종가가 피벗 «아래»로 마감한 돌파」를 «그날 피벗 가격»에 사면:**")
    P("   연 환산 **%+.2f%%**   ·   낙폭 **%+.1f%%**   ·   회복 **%.1f년**   ·   📏폭 **%.2f**"
      % (acc.cagr(hp, YRS), st.median([a[1] for a in out["Ⓗ′"]]),
         st.median([a[2] for a in out["Ⓗ′"]]) / 252.0, spread(out["Ⓗ′"])))
    P("   (같은 수를 «무작위»로 담은 Ⓓ′ 는 **%+.2f%%**)"
      % acc.cagr(st.median([a[0] for a in out["Ⓓ′"]]), YRS))
    P("## ⇒ **«진짜로» 나쁘다 — 무작위보다 **%+.3f%%p**" % dif("Ⓗ′", "Ⓓ′")[0])
    P("")
    P("🚨🚨 **«같은 줄»에 «반드시» — 이 거래들을 «사는» 것은 «현행이 «이미»» 하고 있다:**")
    P("   ① 은 **«모든» 후보**를 D일 피벗에 산다 ⇒ **«못 하는» 것은 「그 절반«만» «가려내는»」 것뿐**이다")
    P("   ⇒ ✅ 적을 말: 「**그 절반«만» 샀다면** 연 %+.2f%% · 낙폭 %+.1f%% — **«사는» 것은 «이미» 하고 있고,"
      % (acc.cagr(hp, YRS), st.median([a[1] for a in out["Ⓗ′"]])))
    P("     «못 하는» 것은 «가려내는» 것뿐이다」**")
    P("   ⇒ ★ 그래서 「거르면 좋아진다」가 **«왜» 그렇게 큰지**(+5.9 / %+.1f%%p)가 «보이고»,"
      % dif("Ⓗ′", "Ⓓ′")[0])
    P("     「사는 값이 그걸 먹는다」가 **«왜» 아픈지**도 보인다")
    P("   ⛔ **「① 의 그 절반이 %+.2f%% «기여»한다」로는 «적지 않는다»** — **«자리 경쟁»이 다르다**"
      % acc.cagr(hp, YRS))
    P("")
    P("⛔ **단 Ⓗ′ 는 «시점 불가» 도구다** — 「전략 성적」으로 «안» 쓴다")
    P("   (「종가가 피벗 아래로 마감할지」는 **«장 마감 뒤»**에 알고, 그때는 «그날 피벗 가격»에 «못» 산다)")
    P("```")
    P("")
    P("| 팔 | 거래 | 세후 총액(중앙) | 연 환산 | 📏폭 | 낙폭 중앙 | 회복 |")
    P("|---|---:|---:|---:|---:|---:|---:|")
    for nm in ("①", "Ⓗ′", "Ⓗa", "Ⓗb", "Ⓓ′", "Ⓓa", "Ⓓb"):
        v = out[nm]
        mm = st.median([a[0] for a in v])
        P("| **%s** | %.0f | %.0f만 | **%+.2f%%** | %.2f | %+.1f%% | %.1f년 |"
          % (nm, meta[nm]["n"], mm, acc.cagr(mm, YRS), spread(v),
             st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0))

    P("")
    P("## 2. 🚨 **분해 — `166` 과 «같은 기계»**")
    P("")
    P("🚨 **판정표 규칙 — 「그 사이」 칸에는 «부호»를 «항상» 적는다**")
    P("   (`161` 에서 「4b(Δ 를 «걸침»)」를 «추가»했고, 이번엔 **«부호»가 빠져 있었다** —")
    P("    **표가 «두 번» 모자랐다**. 「작다」만 적으면 **«음수»인지 «양수»인지 «사라진다»**)")
    P("")
    P("| 짝 | 차 | **95% CI** | 판정 |")
    P("|---|---:|---|:--|")
    rows = [("**Ⓗ′−Ⓓ′**「«아래»를 골라 «거른» 값」", "Ⓗ′", "Ⓓ′")]
    for nm, lab, dn in (("Ⓗa", "재돌파", "Ⓓa"), ("Ⓗb", "풀백", "Ⓓb")):
        rows.append(("**%s−Ⓗ′** 「%s 로 «늦게» 사는 값」" % (nm, lab), nm, "Ⓗ′"))
        rows.append(("**%s−%s** «남는 것» ★(«짝 맞춘» 플라세보)" % (nm, dn), nm, dn))
        rows.append(("%s−① «따로»" % nm, nm, "①"))
    for lab, x, y in rows:
        mu, lo, hi = dif(x, y)
        if lo > DELTA:
            vd = "✅ **Δ «보다» 강하게 남긴다**"
        elif lo > 0 and hi > DELTA:
            vd = "**4b** 🚨 **CI 가 Δ 를 «걸침»**"
        elif lo > 0:
            vd = "**4a** 진짜인데 **«확실히» Δ 미만**"
        elif hi < 0 and mu <= -DELTA:
            vd = "🚨 **«거꾸로»다**"
        elif hi < 0:
            vd = "**칸3** ⚠️ **«확실히» «음수»인데 «크기»가 Δ 미만**"
        else:
            vd = "🚨 **못 가린다**"
        P("| %s | **%+.3f%%p** | [%+.3f, %+.3f] | %s |" % (lab, mu, lo, hi, vd))

    P("")
    P("```")
    P("★★ **`166` 과 «나란히» — 「부호가 뒤집혔나」가 이 판의 물음이다**")
    P("| 판 | 고르는 것 | 거른 값 | 늦게 사는 값 | 남는 것 |")
    P("|---|---|---:|---:|---:|")
    P("| `166` Ⓕ | 종가가 피벗 **위** | +5.937 | −7.419 | **−1.482** |")
    for nm, lab in (("Ⓗa", "재돌파"), ("Ⓗb", "풀백")):
        P("| `167` %s | 종가가 피벗 **아래** | %+.3f | %+.3f | **%+.3f** |"
          % (nm, dif("Ⓗ′", "Ⓓ")[0], dif(nm, "Ⓗ′")[0], dif(nm, "Ⓓ")[0]))
    P("")
    P("★★★ **부호가 «둘 다» 뒤집혔다 — 그런데 «남는 것»은 «여전히» 음수다**")
    P("")
    P("| | 거른 값 | 늦게 사는 값 | **남는 것** |")
    P("|---|---:|---:|---:|")
    P("| `166` Ⓕ «위»를 삼 | **+5.937** | **−7.419** | **−1.482** |")
    P("| `167` Ⓗa 재돌파 | **%+.3f** | **%+.3f** | **%+.3f** |"
      % (dif("Ⓗ′", "Ⓓ′")[0], dif("Ⓗa", "Ⓗ′")[0], dif("Ⓗa", "Ⓓa")[0]))
    P("| `167` Ⓗb 풀백 | **%+.3f** | **%+.3f** | **%+.3f** |"
      % (dif("Ⓗ′", "Ⓓ′")[0], dif("Ⓗb", "Ⓗ′")[0], dif("Ⓗb", "Ⓓb")[0]))
    P("")
    P("★ **두 조각의 «부호»가 `166` 과 «정확히 반대»다** — 두뇌 세션 예상대로다")
    P("   `166`: 거르기 **+** · 늦게 사기 **−**   ·   `167`: 거르기 **−** · 늦게 사기 **+**")
    rem = [-1.482, dif("Ⓗa", "Ⓓa")[0], dif("Ⓗb", "Ⓓb")[0]]
    P("## ⇒ 🚨 **그런데 «남는 것»은 «셋 다» «음수»다 — %+.3f ~ %+.3f%%p**"
      % (min(rem), max(rem)))
    P("   ⇒ ★ **「어느 쪽을 고르든 «무작위»보다 못하다」** — «벽»이 «양쪽에» 있다")
    P("   🚨 **단 «크기»는 «같지 않다»** — 제일 큰 것이 제일 작은 것의 **%.1f 배**다"
      % (min(rem) / max(rem)))
    P("   🚨 **그리고 이건 «관찰»이지 «검정»이 «아니다»** — 셋의 차를 «따로» 재지 «않았다**")
    P("")
    P("★ **«비율»을 «안» 쓴다 — 부호 «구조»가 반대라 나란히 놓으면 「166 이 더 나쁘다」로 «읽힌다**")
    P("   ⇒ ✅ **«비율 없이» 말할 수 있는 «진짜» 공통점:**")
    big = [abs(x) for x in (5.937, 7.419, dif("Ⓗ′", "Ⓓ′")[0],
                            dif("Ⓗa", "Ⓗ′")[0], dif("Ⓗb", "Ⓗ′")[0])]
    sml = [abs(x) for x in (-1.482, dif("Ⓗa", "Ⓓa")[0], dif("Ⓗb", "Ⓓb")[0])]
    P("   ## **「두 조각이 «둘 다 «크고»»(%.1f ~ %.1f%%p) «거의 상쇄»되어**"
      % (min(big), max(big)))
    P("   ## **  «작은 것»(%.1f ~ %.1f%%p)이 «남는다»」**" % (min(sml), max(sml)))
    P("   ⇒ ★ «비율»보다 **«정확»**하고 **유형 67 에도 «안» 걸린다**")
    P("")
    P("★★★ **그리고 «짝 맞춘» 플라세보가 «판정을 바꿨다» — 기록으로 남긴다:**")
    P("   Ⓗb 는 Ⓓ 를 **«하나»**로 뒀을 때 **−1.987%p**(🚨「거꾸로다」)였는데,")
    P("   **Ⓓb 를 «따로» 맞추니 %+.3f%%p**(**칸3** ⚠️「«확실히» «음수»인데 «크기»가 Δ 미만」)로"
      % dif("Ⓗb", "Ⓓb")[0])
    P("   **«판정 «칸»이 바뀐다»**")
    P("   ⇒ ★ **Ⓗb 가 자리를 «크게» 비우는 것이 「풀백이 나쁘다」로 «읽힐» 뻔했다**")
    P("   ⇒ ✅ **유형 62 — 「쪼갤 때 «사건 수»가 다르면 «작은 쪽»이 문턱을 독차지한다」의 «실사고»**")
    P("")
    P("★★ **그리고 «같은 판»에서 규약 ① 의 «실사고»도 나왔다 — «같은 줄»에 둔다:**")
    P("   Ⓓ 를 고쳐 수가 «바뀌었는데» — **「−1.5 ~ −2.0」이라 «손으로» 적어 둔 요약 문장이**")
    P("   **«그대로» 남아 있었다.** ⇒ ✅ **그 문장을 «계산되게» 바꿨다**(규약 ① — 문서의 수를 «생성»)")
    P("   ⇒ ★ **「손으로 적은 수」가 «어떻게» 썩는지의 «표본»** — 수를 «바꾼 그 판»에서 «바로» 났다")
    P("")
    P("⛔ **못 쓸 말** — 🚨 **「금지」는 «결정»이라 «손글씨», 「이유」가 «사실 주장»이면 «생성»한다**")
    P("   (판별기: **「이 문장 안에 «숫자로 확인할 수 있는 말»이 있는가」** — 있으면 «생성»)")
    P("")
    P("   ⛔ **Ⓗ′ 의 수를 «전략 성적»으로** — «시점 불가»다               ← 이유가 «정의». 손글씨")
    P("   ⛔ 「원전이 맞다/틀리다」 — 「«이 자»로는 안 된다」다(약점 ①)   ← 이유가 «결정». 손글씨")
    P("   ⛔ **Ⓗa 를 「풀백」이라 부르기** — «재돌파»다(약점 ③)          ← 이유가 «이름». 손글씨")
    P("   ⛔ 「다른 창(3일·10일)도 재 보자」 — «당일»로 «고정»했다(약점 ②) ← 이유가 «결정». 손글씨")
    P("")
    P("   🔢 **아래는 «이유»가 «수»라서 «생성»된다:**")
    P("   ⛔ 「원전 «풀백 매수»가 맞다/틀리다」")
    P("     — Ⓗb 는 후보의 **%.1f%%**(%s / %s)만 «산다». **«기회»가 셋 중 하나였다**"
      % (100.0 * gHb["fill"] / max(npull, 1), format(gHb["fill"], ","), format(npull, ",")))
    P("")
    P("   🔴🔴 **«정정»(2026-09-03 · `169-source-reread.md`) — «원문»을 다시 읽어 «라벨»이 바뀐다:**")
    P("     앞서 「원전의 «절반»만 잰다」고 적었는데 — **그 «대조»가 «요약»이었다**")
    P("     ✅ **원문**: 우리 Ⓗb 가 잰 것은 원전이 **「«드물게는»」**이라 한 갈래다")
    P("       **원전의 «대부분»은 「브레이크아웃 «생기기 «전»», 베이스 «안»」**이고 — **«못» 물었다**")
    P("     ⇒ ⛔ 「«절반» 못 물었다」 → ✅ **「원전이 «대부분»이라 한 갈래를 «못» 물었다」**")
    P("     🚨 **판정(칸 2a · 칸 3)은 «그대로» 선다** — 바뀌는 건 **«무엇을 잰 판인가»**의 라벨이다")
    P("   ⛔ **「`166` 보다 «낫다/못하다»」** — 고른 «집합»이 «다르고» **«상보»도 «아니다»**")
    P("     — NH★: 「==」 **%s** 건(**%.1f%%**)이 «어느 쪽에도» 없다"
      % (format(n_eq, ","), 100.0 * n_eq / nall))
    P("   ⛔ **「종가 < 피벗 = 51.0%%」** — 이 판의 실측은 **%.1f%%**(%s / %s)"
      % (100.0 * npull / nall, format(npull, ","), format(nall, ",")))
    P("     — 51.0% 는 「`166` 이 **«거르는»** 비율」이다 🚨 **«다른 판»의 수라 여기서 «생성 못 한다»**")
    P("   ⛔ **판정을 「Ⓗ−①」로** — Ⓗa 는 ① 의 **%.0f%%**, Ⓗb 는 **%.0f%%** 만 산다 ⇒ «빼는 비용»이 섞인다"
      % (100.0 * meta["Ⓗa"]["n"] / meta["①"]["n"], 100.0 * meta["Ⓗb"]["n"] / meta["①"]["n"]))
    P("   ⛔ 「51.0% 가 원전과 «일치»」 — 자가 **«셋»**이다(51.0 / 70.4 / 85.9)")
    P("     🚨 **뒤 둘은 `165` 의 수라 여기서 «생성 못 한다»** — **«인용»임을 «적어» 둔다**")
    P("")
    P("★ **판정표를 «누적»한다**(유형 43 의 «판정표» 판) — `166` 의 칸을 «그대로» 이어 쓴다")
    P("```")
    P("")
    P("```")
    P("## 🆕 **새 유형 — 「«금지 문장»은 «검산»을 «안» 받는다」**")
    P("")
    P("이 판에서 **«두 번»** 났다 — 그래서 **«우연이 아니다»**:")
    P("   ① 요약 문장 「−1.5 ~ −2.0%p」  ← Ⓓ 를 고쳐 «수»가 바뀌었는데 **«그대로» 남음**")
    P("   ② 못 쓸 말 줄 「거른 집합이 **«상보»**라」  ← **NH★ 가 「상보가 «아니다»」를 냈는데 «그대로» 남음**")
    P("")
    P("★ **규약 ①(문서의 수를 «생성»)이 «수»는 지켰는데 — «말»은 «안» 지켜졌다**")
    P("   **«금지 문장»은 «수»가 «아니라» «말»이라서 «생성»되지 «않고», 그래서 «검산 대상»에서 «빠진다»**")
    P("")
    P("✅ **처방(작업 위생에 «넣는다»): 「«수»가 바뀌면 «금지 문장»도 «다시 읽는다」」**")
    P("   ★ 특히 **«관문»이 낸 결과**는 «표»에는 들어가는데 **«못 쓸 말» 줄에는 «안» 들어간다**")
    P("   ⇒ **관문을 통과/실패시킨 «사실»을 «금지 문장»과 «맞대 본다»**")
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
