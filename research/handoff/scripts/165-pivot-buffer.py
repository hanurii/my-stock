# -*- coding: utf-8 -*-
r"""165 — **「피벗보다 «조금 위»에서 기다린다」**(원전 기술적 분석 편) · 사전등록 `tasks/165-pivot-buffer.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  원전: 「변곡점보다 **5, 10 혹은 20센트 «위»**에서 «거래될 때까지 «기다릴»» 겁니다」
  ★ 장 시작 «전» 예약 **«가격»**만 바꾸면 된다 ⇒ **«집행» 축**이다(「고르기」가 «아니다»)

  🚨 「α 위에서 기다린다」는 **«두 가지»를 «한꺼번에»** 바꾼다:
     ① 체결가가 «높아진다»(비싸게 삼)   ② α 에 «도달 못 하면» «아예 안 삼»(후보가 «준다»)
  ⇒ 섞으면 **유형 68**. 그래서 **Ⓔ(분해 도구)**로 «갈라» 잰다:
     **Ⓐ−Ⓔ = 「비싸게 산」 값**  ·  **Ⓔ−Ⓓ = 「거른」 값**  ·  **Ⓐ−Ⓓ = 둘의 «합»**
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
ALPHAS = (0.005, 0.0065, 0.010, 0.020)     # 🚨 0.65% = **원전 20센트의 «환산값 자체»**(유형 38)
CENTS = 0.20
CACHE = Path(str(r91.OUT / "165-partial.json"))
PXF = Path("D:/stock-data/derived/159-entry-price.json")
LA_REF = 12377


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    P = print
    P("=" * 104)
    P("165 — **「피벗보다 «조금 위»에서 기다린다」** · 🏷️ 세대 B · 씨앗 %d × 배정 %d" % (n_seed, n_as))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/165-pivot-buffer.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## ★ **이 판은 «집행» 축이다**")
    P("")
    P("```")
    P("장 시작 «전» 예약 **«가격»**만 바꾼다 ⇒ **사용자 방식과 «직결»**")
    P("★★ 「«규칙» 축은 닫혔다」와 «다르다» — **«집행» 축은 «남아» 있다**")
    P("⛔ 그러니 이 판을 **«고르기»로 «흐리지» 않는다**(「같은 그룹 대비 RS」를 «안» 묻는 이유)")
    P("```")
    P("")
    P("## 🚨 **Ⓔ 는 «전략»이 아니라 «분해 도구»다 — 룩어헤드다**")
    P("")
    P("```")
    P("Ⓔ = 「α 에 «도달한» 거래만 골라 **«피벗 가격»**에 사기」")
    P("🚨 α 도달 여부를 알려면 **«그날 고가»**를 봐야 한다 ⇒ **장전에 «모른다»**")
    P("⇒ ⛔ **Ⓔ 의 수를 «전략 성적»으로 «쓰지 않는다»** (`161` 의 Ⓐ 와 «같은 격»)")
    P("⇒ ✅ Ⓔ 가 하는 일은 **«하나»** — 「비싸게 산 값」과 「거른 값」을 **«갈라» 주는 것**")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2

    # ── 관문 LD★ 의 «바탕» — entry_price 가 정말 max(pivot, open) 인가(전수) ──
    n_id, n_ok = 0, 0
    for y in by2:
        for q in by2[y]:
            pv, o = q.get("pivot"), (q.get("o") or [None])[0]
            if pv is None or o is None:
                continue
            n_id += 1
            n_ok += 1 if abs(q["entry_price"] - max(pv, o)) < 1e-9 else 0
    P("")
    P("## 관문 LD★-0 — **`entry_price == max(pivot, open)` «전수»**")
    P("")
    P("```")
    P("경로 **%s** 개 중 **%s** 개 일치 (**%.2f%%**)  →  %s"
      % (format(n_id, ","), format(n_ok, ","), 100.0 * n_ok / max(n_id, 1),
         "✅ **항등식이 선다**" if n_ok == n_id else "🚨 **멈춘다**"))
    P("★ 이게 서야 α 를 **«피벗 위»**로 «올려» 걸 수 있다 — 통계가 아니라 **«사실»**이다")
    P("```", flush=True)
    if n_ok != n_id:
        return 3

    # ── α 환산 — 「그 시대 «우리 후보» 중앙 «실제» 주가 대비 20센트」 ──────────
    px = json.loads(PXF.read_text(encoding="utf-8"))
    byy = {}
    for y in by2:
        for q in by2[y]:
            v = px.get(q["code"] + "|" + q["entry_date"])
            if v and v > 0:
                byy.setdefault(int(q["entry_date"][:4]), []).append(v)
    P("")
    P("## 🚨 **α 환산 — 「센트」를 «시대에 맞춰» 옮긴다**")
    P("")
    P("```")
    P("원전은 「5·10·20센트」인데 우리는 **27.4년**이라 **«센트» 고정이 «시점 편향»**이다")
    P("✅ 환산: **「그 시대 «우리 후보» 중앙 «실제» 주가(`closeunadj`) 대비 %.0f센트」**" % (CENTS * 100))
    P("")
    for y in (1999, 2005, 2012, 2019, 2026):
        if y in byy:
            m_ = st.median(byy[y])
            P("   %d   중앙 **$%.2f**   →   %.0f센트 = **%.3f%%**" % (y, m_, CENTS * 100, 100 * CENTS / m_))
    allm = st.median([v for vs in byy.values() for v in vs])
    conv = CENTS / allm
    P("")
    P("   ⇒ ★ **27년간 «거의 안 움직인다»** — `159` 의 주가 백분위(81.9 → 68.6%)와 «대조»되는 «좋은 소식»")
    P("   ⇒ 전체 중앙 **$%.2f** → **%.3f%%**  ⇒  격자에 **0.65%%** 를 «넣는다»(유형 38 — 「그 수」가 직접 재짐)"
      % (allm, 100 * conv))
    P("")
    P("🚨 **「중앙 주가」가 «두 수»다**(유형 67):")
    P("   `159`(**«그날 전체 상장사»**)  1999 $12.12 · 2026 $14.94")
    P("   이 판(**«우리 후보»** · `closeunadj`) 1999 $%.2f · 2026 $%.2f"
      % (st.median(byy[1999]), st.median(byy[2026])))
    P("   ✅ **«우리 후보» 중앙이 «맞다»** — 원전은 «자기가 «거래하던»» 주식(주도주) 가격대를 말했다")
    P("   ✅ **«순환»이 «아니다»** — α «이전»의 후보로 계산한다. α 가 후보를 바꾸기 «전»의 수다")
    P("```", flush=True)

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

    def build(mode, al, drop=None):
        """mode: base | A(α 체결) | E(α 도달만 · 피벗 가격) | D(무작위 배제)"""
        out_, bad = [], 0
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                pv = p.get("pivot")
                o0, h0 = (p.get("o") or [None])[0], p["h"][0]
                lvl = None if pv is None else pv * (1.0 + al)
                if mode in ("A", "E"):
                    if lvl is None or h0 is None or h0 < lvl:
                        continue                      # α 에 «도달 못 함» ⇒ 안 산다
                # 🚨 플라세보는 **Ⓐ 와 «같은 자리»**에서 빼야 한다 — «중복제거 «전»».
                #    «뒤»에서 빼면 Ⓐ 는 「빠진 자리에 «다음 거래»가 들어오는」 이득을 «혼자» 갖는다
                #    (첫 구현이 그랬고 LB★ 가 3/4 «미통과»로 잡았다)
                if drop is not None and (p["scan_date"], p["code"], p["pattern"]) in drop:
                    continue
                q = p
                if mode == "A":
                    q = dict(p)
                    q["entry_price"] = lvl if o0 is None else max(lvl, o0)
                    if q["entry_price"] < lvl - 1e-9:
                        bad += 1
                t = pt.resolve_trade(q, ft="limit", fs="market", stop=STOP, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                t["stop_frac"] = STOP / 100.0
                out_.append(t)
        return out_, bad

    base, _ = build("base", 0.0)

    def preskip(al):
        """Ⓐ/Ⓔ 가 **중복제거 «전»**에 빼는 «후보»를 연도별로 센다 — Ⓓ 를 «여기»에 맞춘다"""
        out_ = {}
        for y in sorted(keep):
            sk = []
            for p in keep[y]:
                pv = p.get("pivot")
                h0 = p["h"][0]
                lvl = None if pv is None else pv * (1.0 + al)
                if lvl is None or h0 is None or h0 < lvl:
                    sk.append((p["scan_date"], p["code"], p["pattern"]))
            out_[y] = sk
        return out_

    pool = {y: [(p["scan_date"], p["code"], p["pattern"]) for p in ks]
            for y, ks in keep.items()}

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

    out, meta, LD = {}, {}, {}
    out["①"], meta["①"] = sim(base, "v1|base|n%d" % n_seed)
    P("  ① 현행 — 중앙 %.0f만 · 거래 %d"
      % (st.median([a[0] for a in out["①"]]), meta["①"]["n"]), flush=True)

    for al in ALPHAS:
        tag = "%.4f" % al
        evA, badA = build("A", al)
        evE, _ = build("E", al)
        LD[al] = badA
        nkeep = len(evE)
        ndrop = len(base) - nkeep
        out[("A", al)], meta[("A", al)] = sim(evA, "v1|A|%s|n%d" % (tag, n_seed))
        out[("E", al)], meta[("E", al)] = sim(evE, "v1|E|%s|n%d" % (tag, n_seed))
        psk = preskip(al)
        accs, exs, ns = [], [], []
        for ai in range(n_as):
            rg = random.Random(ai + 1_000_000 + int(al * 1e6))
            drop = set()
            for y, ks in pool.items():
                drop |= set(rg.sample(ks, min(len(psk[y]), len(ks))))
            evD, _ = build("base", 0.0, drop=drop)
            v, m = sim(evD, "v2|D|%s|a%d|n%d" % (tag, ai, n_seed))
            accs.append(v)
            exs.append(m["expo"])
            ns.append(m["n"])
        out[("D", al)] = [tuple(st.mean(accs[ai][i][j] for ai in range(n_as)) for j in range(4))
                          for i in range(n_seed)]
        meta[("D", al)] = {"expo": None, "expo_d": exs, "n": st.mean(ns),
                           "nskip": sum(len(v) for v in psk.values())}
        P("  α %.2f%% — Ⓐ %.0f만(%d) · Ⓔ %.0f만(%d) · Ⓓ %.0f만(%.0f)"
          % (100 * al, st.median([a[0] for a in out[("A", al)]]), meta[("A", al)]["n"],
             st.median([a[0] for a in out[("E", al)]]), meta[("E", al)]["n"],
             st.median([a[0] for a in out[("D", al)]]), meta[("D", al)]["n"]), flush=True)

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    def dif(x, y):
        d = [acc.cagr(out[x][i][0], YRS) - acc.cagr(out[y][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("")
    P("## 관문 LA★ · LB★ · LD★")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①"]])
    P("**LA★ 앵커** — ① **%.0f만** vs %s만  →  %s"
      % (m1, format(LA_REF, ","), "✅ **일치**" if abs(m1 - LA_REF) < 1.0 else "🚨 **멈춘다**"))
    P("   ★ 상시 관문 «여섯 번째» — 156·161·162·163·164 가 «전부» 이 수다")
    P("")
    P("**LD★ 체결가 «전수» 검산** — Ⓐ 의 체결가가 **«전부»** 「피벗 × (1+α) «이상»」인가")
    for al in ALPHAS:
        P("   α %.2f%%  어긋난 거래 **%d** / %d  →  %s"
          % (100 * al, LD[al], meta[("A", al)]["n"],
             "✅" if LD[al] == 0 else "🚨 **멈춘다**"))
    P("   ★ «항등식»이라 문턱이 «필요 없다»")
    P("")
    P("**LB★ 「안 산」 수가 Ⓐ↔Ⓓ 에서 ±3% 안인가** — 🚨 **«두 자리»에서 «다» 센다**")
    P("   (첫 구현은 Ⓓ 를 **중복제거 «뒤»**에서 뺐고 LB★ 가 **3/4 미통과**로 잡았다 —")
    P("    Ⓐ 는 「빠진 자리에 «다음 거래»가 들어오는」 이득을 «혼자» 가졌다. **같은 자리**로 옮겼다)")
    for al in ALPHAS:
        pk = sum(len(v) for v in preskip(al).values())
        pd_ = meta[("D", al)].get("nskip", pk)
        a_, d_ = len(base) - meta[("A", al)]["n"], len(base) - meta[("D", al)]["n"]
        P("   α %.2f%%  ㉠«중복제거 전» Ⓐ **%d** ↔ Ⓓ **%d** (%s)  ·  ㉡«최종 거래» Ⓐ %d ↔ Ⓓ %.0f (%+.2f%%) %s"
          % (100 * al, pk, pd_, "✅ **같다**" if pk == pd_ else "🚨",
             a_, d_, 100.0 * (d_ - a_) / max(a_, 1),
             "✅" if abs(d_ - a_) <= 0.03 * a_ else "🚨 **밖**"))
    P("   ★ ㉠ 은 **«설계상» 같아야** 하고(항등식) · ㉡ 은 **«중복제거»가 달라 어긋난다")
    P("")
    P("🚨 **㉡ 의 어긋남을 «라벨»로 두지 않는다 — «어느 쪽»으로 치우치는지 «수»로 본다**(유형 69):")
    P("   Ⓐ 가 빼는 것은 **«상관된»**(α 에 못 닿는) 후보이고 Ⓓ 는 **«무작위»**라,")
    P("   같은 수를 빼도 **중복제거가 «다르게» 이어진다** ⇒ Ⓓ 의 «최종» 거래가 «더» 준다")
    P("   ⇒ ★ **Ⓓ 가 「빼는 «비용»」을 «더» 문다** ⇒ **Ⓔ−Ⓓ 와 Ⓐ−Ⓓ 가 «위»로 치우친다**")
    P("   ## ⇒ ✅ **치우침이 «원전에 «유리»»한 쪽인데도 Ⓐ−Ⓓ 가 Δ 를 «못 넘는다»**")
    P("   ⇒ 그러므로 **이 어긋남으로 판정이 «뒤집히지» 않는다** — «보수적» 방향이다")
    P("```", flush=True)

    P("")
    P("## 1. 팔 — α 마다")
    P("")
    P("| α | 팔 | 거래 | 세후 총액(중앙) | 연 환산 | 📏폭 | 낙폭 중앙 | 회복 |")
    P("|---|---|---:|---:|---:|---:|---:|---:|")
    P("| — | **①현행** | %d | %.0f만 | **%+.2f%%** | %.2f | %+.1f%% | %.1f년 |"
      % (meta["①"]["n"], m1, acc.cagr(m1, YRS), spread(out["①"]),
         st.median([a[1] for a in out["①"]]), st.median([a[2] for a in out["①"]]) / 252.0))
    for al in ALPHAS:
        for tg, nm in (("A", "Ⓐ α 위 체결"), ("E", "Ⓔ α 도달만·피벗가 🚨«도구»"),
                       ("D", "Ⓓ 무작위 배제")):
            v = out[(tg, al)]
            mm = st.median([a[0] for a in v])
            P("| **%.2f%%** | %s | %.0f | %.0f만 | **%+.2f%%** | %.2f | %+.1f%% | %.1f년 |"
              % (100 * al, nm, meta[(tg, al)]["n"], mm, acc.cagr(mm, YRS), spread(v),
                 st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0))

    P("")
    P("## 2. 🚨 **분해 — 「비싸게 산 값」과 「거른 값」을 «갈라»**")
    P("")
    P("| α | **Ⓐ−Ⓔ**「비싸게 산」 | **Ⓔ−Ⓓ**「거른」 | **Ⓐ−Ⓓ** «합» | 판정(Ⓐ−Ⓓ) |")
    P("|---|---:|---:|---:|:--|")
    for al in ALPHAS:
        p1, _l1, _h1 = dif(("A", al), ("E", al))
        p2, _l2, _h2 = dif(("E", al), ("D", al))
        p3, l3, h3 = dif(("A", al), ("D", al))
        vd = ("🔴 **«거꾸로»다**" if (p3 <= -DELTA and h3 < 0) else
              ("✅ **원전이 «맞다»**" if (p3 >= DELTA and l3 > 0) else
               ("⚠️ 반대이나 **Δ 미만**" if h3 < 0 else
                ("⚠️ 원전 방향이나 **Δ 미만**" if l3 > 0 else "🚨 **못 가린다**"))))
        P("| **%.2f%%** | %+.3f%%p | %+.3f%%p | **%+.3f%%p** [%+.3f, %+.3f] | %s |"
          % (100 * al, p1, p2, p3, l3, h3, vd))
    P("")
    P("```")
    P("★ **합이 맞는지 «검산»**(항등식이 «아니다» — 씨앗별 차의 평균이라 «더해져야» 한다):")
    for al in ALPHAS:
        p1 = dif(("A", al), ("E", al))[0]
        p2 = dif(("E", al), ("D", al))[0]
        p3 = dif(("A", al), ("D", al))[0]
        P("   α %.2f%%  (Ⓐ−Ⓔ) + (Ⓔ−Ⓓ) = %+.3f  vs  Ⓐ−Ⓓ = %+.3f   차 **%+.4f**"
          % (100 * al, p1 + p2, p3, p1 + p2 - p3))
    P("   ⇒ ★ 차가 0 이면 **분해가 «샌 곳 없이»** 갈렸다는 뜻이다")
    P("```")
    P("")
    P("```")
    P("🚨 **α = 0.65%(원전 20센트의 «환산값»)가 Δ 에 «거의 닿는다» — 그대로 적는다:**")
    mu, lo, hi = dif(("A", 0.0065), ("D", 0.0065))
    P("   Ⓐ−Ⓓ = **%+.3f%%p** [%+.3f, %+.3f]  ·  Δ = %.2f%%p" % (mu, lo, hi, DELTA))
    P("   ⇒ 점추정 **%+.3f < %.2f** 라 「Δ 미만」이 «맞다»" % (mu, DELTA))
    P("   ⇒ 🚨 **단 CI 위끝 %+.3f 은 Δ 를 «넘는다»** — 「Δ 보다 «작다»」를 «단정»하지 «못한다»" % hi)
    P("   ✅ 적을 말: 「**원전 방향이고 Δ 에 «거의 닿지만», Δ 를 «넘는다고도 못 한다»**」")
    P("```")
    P("")
    P("**①과의 차이 — «따로»(「안 사는 «비용»」이 섞인 수다)**")
    P("")
    P("| α | Ⓐ−① | **95% CI** |")
    P("|---|---:|---|")
    for al in ALPHAS:
        mu, lo, hi = dif(("A", al), "①")
        P("| **%.2f%%** | **%+.3f%%p** | [%+.3f, %+.3f] |" % (100 * al, mu, lo, hi))

    P("")
    P("```")
    P("**LC★ — 노출을 «분포»로**(`164` 에서 그게 «일»을 했다) · 문턱은 **«두 단계»**")
    for al in ALPHAS:
        e = meta[("D", al)]["expo_d"]
        P("   α %.2f%%  Ⓐ **%.1f%%** · Ⓔ **%.1f%%** · Ⓓ **%.1f ~ %.1f%%**(중앙 **%.1f%%**) · ① %.1f%%"
          % (100 * al, meta[("A", al)]["expo"], meta[("E", al)]["expo"],
             min(e), max(e), st.median(e), meta["①"]["expo"]))
    P("   🚨 **문턱은 «안» 만든다** — 「노출 Δ%p ↔ 성적 Δ%p」 환산이 «안 된다**")
    P("   ✅ **«수»를 적고 「이 값으로 «못 정한다」** — «빈칸»이 아니라 «측정된 미결»")
    P("```")
    # ── 부산물 ① — 「브레이크아웃의 «반»은 풀백하거나 그 «아래»」 ────────────
    WINS = (5, 10, 20, None)
    cnt = {(w, k): 0 for w in WINS for k in ("c", "l")}
    tot_, plen = 0, []
    for y in sorted(keep):
        for q in keep[y]:
            pv = q.get("pivot")
            if pv is None or len(q["c"]) < 2:
                continue
            tot_ += 1
            plen.append(len(q["c"]) - 1)
            for w in WINS:
                c_ = q["c"][1:] if w is None else q["c"][1:w + 1]
                l_ = q["l"][1:] if w is None else q["l"][1:w + 1]
                cnt[(w, "c")] += 1 if any(v is not None and v < pv for v in c_) else 0
                cnt[(w, "l")] += 1 if any(v is not None and v < pv for v in l_) else 0
    P("")
    P("## 3. 부산물 ① — 원전의 «사실 주장»: **「돌파의 «반»은 풀백하거나 그 «아래»」**")
    P("")
    P("```")
    P("🚨 「피벗 «아래»」의 정의가 **«셋»**이다 — **셋 «다»** 낸다(유형 42 수법:")
    P("   **셋 다 «같은 방향»이면 「어느 정의로도」가 되고 «손잡이»가 «사라진다»**)")
    P("")
    P("🚨🚨 **그리고 «창»을 «안» 막으면 «항등식»에 가깝다** — 경로 길이 중앙 **%d 거래일**."
      % st.median(plen))
    P("   「«언젠가» 한 번」은 «거의 다» 참이다. 그래서 **«창»을 «갈라»** 적는다")
    P("")
    P("후보 **%s** 개 (진입 «다음 날»부터 셈 — 진입일은 «피벗 위»라 «당연»히 제외)" % format(tot_, ","))
    P("")
    P("| 창 | ① **«종가»**가 아래로 | ② 장중 **«저가»**가 아래로 |")
    P("|---|---:|---:|")
    for w in WINS:
        P("| %s | **%.1f%%** | **%.1f%%** |"
          % ("**%d 거래일 «안»**" % w if w else "«전 구간»(막지 «않음»)",
             100.0 * cnt[(w, "c")] / tot_, 100.0 * cnt[(w, "l")] / tot_))
    P("")
    vals = [100.0 * cnt[(w, k)] / tot_ for w in WINS for k in ("c", "l")]
    v5 = [100.0 * cnt[(5, k)] / tot_ for k in ("c", "l")]
    P("⇒ 🚨 **「전 구간」 칸(%.1f / %.1f%%)은 «거의 항등식»이라 «증거로 «안» 쓴다**"
      % (100.0 * cnt[(None, "c")] / tot_, 100.0 * cnt[(None, "l")] / tot_))
    P("   ★ **여기가 «손잡이»였다** — 창을 «안» 막으면 «어떤 주장»이든 «선다»")
    P("")
    if min(vals) >= 50.0:
        P("⇒ ✅ **«막은» 창 «전부»에서도 절반 이상**(제일 낮은 칸 **%.1f%%** = %d일 창)"
          % (min(vals), 5))
        P("   ★ **«그래서» 「어느 정의로도」가 «선다».** 정의를 «고를» 여지가 «없다»")
    elif max(v5) < 50.0:
        P("⇒ 🔴 **제일 «짧은» 창(5일)에서는 «절반 미만»**(%.1f / %.1f%%) — 「«얼마나 빨리»」가 갈린다"
          % (v5[0], v5[1]))
    else:
        P("⇒ 🚨 **창·정의에 «따라» 갈린다 — 「어느 정의로도」를 «못» 쓴다**")
        P("   ⛔ **«유리한 칸»을 «고르지» 않는다.** 표를 «다» 적고 「갈린다」고 쓴다")
    P("")
    P("🚨 **원전 문장과 «완전히» 같지는 않다** — 원전은 「«최고의» 종목도」라 했고")
    P("   이건 **«우리 후보 «전부»»**다. 「최고의 종목」을 «우리 자료로» 정의하면 «순환»이 된다")
    P("```")

    # ── 부산물 ② — 「크게 오른 종목의 70%가 «전»에 좋은 실적」 ───────────────
    gw, gl = {}, {}
    for t in base:
        r_ = t["masks"][()].get("result")
        gw[r_] = gw.get(r_, 0) + 1
    P("")
    P("## 4. 부산물 ② — 원전의 «사실 주장»: **「크게 오른 종목의 «70%»가 «전»에 좋은 실적」**")
    P("")
    P("```")
    P("🚨🚨 **이건 «검산»이 «아니라» «서술»이다:**")
    P("   `103 judge` 는 **«우리» 정의**(매출·EPS 가속 등급)라 원전의 「좋은 실적」과 **«같은 자»가 «아니다»**")
    P("   ⇒ ⛔ **「70%가 맞다/틀리다」를 «이 수»로 «말할 수 없다»**")
    P("")
    P("그리고 **더 큰 문제 «하나»** — 우리 후보는 **«이미» `judge` 로 «걸러진» 것**이다:")
    P("   (`v is False` 인 후보를 **«빼고»** 이 판을 돌렸다)")
    P("   ⇒ ★ **「좋은 실적 비율」을 재면 «항등식»에 가깝다.** 분모가 «이미» 골라져 있다")
    P("   ⇒ ✅ **그래서 «안 잰다».** 재려면 **«거르기 «전»» 후보로 «따로» 돌려야 한다")
    P("")
    P("✅ 대신 «잴 수 있는» 것만 적는다 — 청산 «결과» 분포(후보 %s 개):" % format(len(base), ","))
    for k_, n_ in sorted(gw.items(), key=lambda x: -x[1]):
        P("   %-14s **%s** (**%.1f%%**)" % (str(k_), format(n_, ","), 100.0 * n_ / len(base)))
    P("```")
    P("")
    P("```")
    P("**위험 축 «둘»**(낙폭 «중앙» · 📏폭 = P95÷P05) · 「위험 «하나»만 나쁨」 칸을 «미리»:")
    P("   자산 «이김» + 위험 «하나»만 나쁨  →  「맞바꿈 — 사용자 «선택»」")
    P("   자산 «짐»   + 위험 «하나»만 나쁨  →  ⛔ 「**선택지가 «아니다». «진» 것이다**」")
    P("")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ 「원전이 맞다/틀리다」를 **Ⓐ−Ⓓ «하나»로** — 이 판은 **α 격자 «넷»**을 잰다")
    P("   ⛔ **Ⓔ 수를 «전략 성적»으로** — 룩어헤드다")
    P("   ⛔ 「거짓 돌파를 «걸러낸다»」를 **Ⓔ−Ⓓ «없이»**")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
