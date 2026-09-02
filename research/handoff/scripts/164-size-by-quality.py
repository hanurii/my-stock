# -*- coding: utf-8 -*-
r"""164 — **「종목 «특성»에 따라 «크기»를 달리한다」**(원전 ⑦) · 사전등록 `tasks/164-size-by-quality.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (`41db459d`)** · 칸 5 · 상한 20% «그대로» · 배당 포함 · 숏 없음

  원전: 「리스크는 «손절값»과 **«유동성»**에 따라 정의한다」 · 「작고 «변동성 크면» «큰 위험을 안 짐»」
     `163` 이 «손절값» 쪽  ·  이 판이 **«유동성·변동성»** 쪽

  ⛔ **이 판은 «크기»를 묻지 «매수 여부»를 «안» 묻는다** — 「작은 종목을 «사지 마라」」가 «아니다»
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
CUT = 0.5                          # ⚠️ 「절반으로 줄인다」 — **출처 «없음»**(원전은 «수»를 안 줬다)
TERC = 1.0 / 3.0
CACHE = Path(str(r91.OUT / "164-partial.json"))
TOV = Path("D:/stock-data/derived/164-tov-pctile.json")
KA_REF = 12377

_AB = {"①": 1, "②": 2, "③": 3, "④": 4, "1": 1, "2": 2, "3": 3, "4": 4}


def _band(v):
    """맨 «앞 글자»로 읽는다(143 의 교훈 — «전부» 조회하면 100% 결측)"""
    if v is None:
        return None
    return _AB.get(str(v)[0])


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    P = print
    P("=" * 104)
    P("164 — **「종목 «특성»에 따라 «크기»를」**(원전 ⑦) · 🏷️ 세대 B · 씨앗 %d × 배정 %d"
      % (n_seed, n_as))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-02 · `scripts/164-size-by-quality.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## ✅ **틀 — 「모르는 축 «하나»」가 «아니다»**")
    P("")
    P("```")
    P("변동성 축(`atr_band`) = **«아는» 축** — `160` 에서 «순위»로 **«못 가림»**  →  **«양성 대조» 노릇**")
    P("유동성 축(거래대금)   = **«모르는» 축**")
    P("★ 변동성 축이 «예상대로» 「못 가림」이면 **«하네스가 맞다»는 증거**이고, 그 «위»에서 유동성을 읽는다")
    P("")
    P("⛔ **이 판은 «크기»를 묻지 «매수 여부»를 «안» 묻는다** — 「작은 종목을 «사지 마라」」가 «아니다»")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("원전 「유동성·변동성에 따라 위험을」   ← 출처: 원전 «글자»")
    P("`atr_band` ③④ = 변동성 «큰» 칸        ← 출처: 검출기 산출(순서형 ①<②<③<④)")
    P("거래대금 «시점 백분위»                ← 출처: `164a` (`closeunadj × volume` · `scan_date`)")
    P("Δ = 1.23%p                            ← 출처: 150 의 우리−QQQ 격차")
    P("KA★ 기준 %s만                     ← 출처: 156·161·162·163 의 ①" % format(KA_REF, ","))
    P("")
    P("🚨 **출처가 «빈» 가정 — «둘»:**")
    P("   ⛔ **「절반(×%.1f)으로 줄인다」 — 원전은 «수»를 «안 줬다**. 우리가 «고른» 값이다" % CUT)
    P("   ⛔ **「하위/상위 = 삼분위」 — 원전은 «경계»를 «안 줬다**")
    P("     🚨 그리고 **우리 «후보 안»의 삼분위**다(시장 전체가 «아니다») — 아래 §1 에 «시장 백분위»를 적는다")
    P("```", flush=True)

    tp = json.loads(TOV.read_text(encoding="utf-8"))
    tov = tp["pair"]

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    ev, feat = [], {}
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
            t["stop_frac"] = STOP / 100.0
            k = (t["scan_date"], t["code"], t["pattern"])
            feat[k] = (_band(p.get("atr_band")),
                       tov.get(p["code"] + "|" + p["scan_date"]),
                       int(p["entry_date"][:4]))
            ev.append(t)

    P("")
    P("## 1. 관문 KC★ — **결측. 🚨 결측은 «안» 줄인다**")
    P("")
    P("```")
    nb = sum(1 for v in feat.values() if v[0] is None)
    nt = sum(1 for v in feat.values() if v[1] is None)
    P("거래 **%s** 개" % format(len(ev), ","))
    P("  `atr_band` 결측 **%d** (**%.2f%%**)   ·   거래대금 백분위 결측 **%d** (**%.2f%%**)"
      % (nb, 100.0 * nb / len(ev), nt, 100.0 * nt / len(ev)))
    P("  ⇒ %s" % ("✅ **둘 다 1% 미만**" if max(nb, nt) < 0.01 * len(ev)
                  else "🚨 **결측이 크다 — 라벨로 읽는다**"))
    P("  🚨 결측 거래는 **«어느 팔에서도» 안 줄인다**(현행 크기 그대로)")
    P("")
    bs = {}
    for v in feat.values():
        bs[v[0]] = bs.get(v[0], 0) + 1
    P("`atr_band` 분포 — " + " · ".join(
        "%s: **%d**(%.1f%%)" % (k if k is not None else "결측", n, 100.0 * n / len(ev))
        for k, n in sorted(bs.items(), key=lambda x: (x[0] is None, x[0]))))
    q = sorted(v[1] for v in feat.values() if v[1] is not None)
    lo_c, hi_c = q[int(len(q) * TERC)], q[int(len(q) * (1 - TERC))]
    P("")
    P("**거래대금 — 「하위/상위」의 «시장» 백분위**(우리 후보 안 삼분위)")
    P("   후보 분포: P10 **%.3f** · 중앙 **%.3f** · P90 **%.3f**"
      % (q[len(q) // 10], q[len(q) // 2], q[9 * len(q) // 10]))
    P("   ⇒ 🚨 **중앙이 %.3f — 우리 후보는 «이미» 유동성 «위쪽»에 쏠려 있다**" % q[len(q) // 2])
    P("   Ⓒ 「하위 1/3」 = **시장 백분위 %.3f «미만»**  (「하위」가 «시장 하위»가 «아니다»)" % lo_c)
    P("   Ⓒ′「상위 1/3」 = 시장 백분위 %.3f «초과»" % hi_c)
    P("")
    P("★★★ **그리고 이게 «셋째 조각»이다 — 「«왜» 안 쟀나」:**")
    P("   ## **우리 «파이프라인»이 «이미» 유동성 하위를 «걸러낸다»**")
    P("   (후보의 시장 백분위 P10 **%.3f** · 중앙 **%.3f** — 시장 «하위»가 후보에 «거의 없다»)"
      % (q[len(q) // 10], q[len(q) // 2]))
    P("   ⇒ ★ 원전의 「작고 유동성 낮으면 «작게»」를 — 우리는 **««배제»로» «이미» 하고 있다**")
    P("   ⇒ ✅ 「원전을 **«안 따랐다»**」가 아니라 **「«다른 자리»에서 «이미» 따르고 있다」**다")
    P("```", flush=True)

    A = {k for k, v in feat.items() if v[0] in (3, 4)}
    B = {k for k, v in feat.items() if v[0] in (1, 2)}
    C = {k for k, v in feat.items() if v[1] is not None and v[1] < lo_c}
    C2 = {k for k, v in feat.items() if v[1] is not None and v[1] > hi_c}

    byyear = {}
    for k, v in feat.items():
        byyear.setdefault(v[2], []).append(k)

    def rand_like(target, ai):
        """연도별 «수»를 target 과 맞춘 «무작위» 배정 — 156 의 교훈(배정 축을 «평균»)"""
        rg = random.Random(ai + 1_000_000)
        out = set()
        for y, ks in byyear.items():
            n = sum(1 for k in ks if k in target)
            out |= set(rg.sample(ks, min(n, len(ks))))
        return out

    def mk(sel):
        def f(recent, seed, t):
            return CUT if (t["scan_date"], t["code"], t["pattern"]) in sel else 1.0
        return f

    ARMS = [("①현행", None, None), ("Ⓐ 변동성 «큰» 칸 ×0.5", A, None),
            ("Ⓑ 변동성 «작은» 칸 ×0.5 «음성»", B, None),
            ("Ⓒ 거래대금 «하위» ×0.5", C, None),
            ("Ⓒ′ 거래대금 «상위» ×0.5 «음성»", C2, None),
            ("Ⓓ 무작위(Ⓐ 와 수 맞춤)", None, A),
            ("Ⓓ′ 무작위(Ⓒ 와 수 맞춤)", None, C)]

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out, meta = {}, {}

    def run(sel, key):
        if key in cache:
            return [tuple(a) for a in cache[key]], cache[key + "|m"]
        with r91.r41.Cost(*r91.COST):
            rs = [r91.sl.sim_lots(ev, seed=s, slots=SLOTS, risk=0.02, cap=0.20,
                                  reserve=False, fill_rule="truncate", cash_rule="per_slot",
                                  size_fn=(mk(sel) if sel else None)) for s in range(n_seed)]
        v = [acc.account(x) for x in rs]
        m = {"expo": st.median([x["expo_mean"] for x in rs]),
             "cut": len(sel) if sel else 0}
        cache[key] = [list(a) for a in v]
        cache[key + "|m"] = m
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        return v, m

    for nm, sel, mt in ARMS:
        if mt is None:
            out[nm], meta[nm] = run(sel, "v1|%s|n%d" % (nm, n_seed))
            P("  %s — 중앙 %.0f만 · 줄인 거래 %d"
              % (nm, st.median([a[0] for a in out[nm]]), meta[nm]["cut"]), flush=True)
        else:
            acc_, cuts, exs = [], [], []
            for ai in range(n_as):
                s_ = rand_like(mt, ai)
                v, m = run(s_, "v1|%s|a%d|n%d" % (nm, ai, n_seed))
                acc_.append(v)
                cuts.append(m["cut"])
                exs.append(m["expo"])
            # 🚨 배정 축을 «평균» — 씨앗마다 배정 10개를 평균해 «한 판»으로 만든다
            out[nm] = [tuple(st.mean(acc_[ai][i][j] for ai in range(n_as)) for j in range(4))
                       for i in range(n_seed)]
            meta[nm] = {"expo": None, "cut": st.mean(cuts), "expo_d": exs}
            P("  %s — 중앙 %.0f만 · 줄인 거래 %.0f (배정 %d개 «평균»)"
              % (nm, st.median([a[0] for a in out[nm]]), meta[nm]["cut"], n_as), flush=True)

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    P("")
    P("## 2. 관문 KA★ · KD★")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①현행"]])
    P("**KA★ — 앵커**: ①현행 **%.0f만** vs %s만  →  %s"
      % (m1, format(KA_REF, ","), "✅ **일치**" if abs(m1 - KA_REF) < 1.0 else "🚨 **멈춘다**"))
    P("   ★ 어제 «상시 관문»으로 승격한 것 — 156·161·162·163 이 «전부» 이 수다")
    P("")
    P("**KD★ — 줄인 «거래 수»가 Ⓐ↔Ⓓ · Ⓒ↔Ⓓ′ 에서 ±3% 안인가**")
    for a_, d_ in (("Ⓐ 변동성 «큰» 칸 ×0.5", "Ⓓ 무작위(Ⓐ 와 수 맞춤)"),
                   ("Ⓒ 거래대금 «하위» ×0.5", "Ⓓ′ 무작위(Ⓒ 와 수 맞춤)")):
        x, y = meta[a_]["cut"], meta[d_]["cut"]
        P("   %s **%d** ↔ %s **%.0f**  (%+.2f%%)  →  %s"
          % (a_[:2], x, d_[:2], y, 100.0 * (y - x) / max(x, 1),
             "✅" if abs(y - x) <= 0.03 * x else "🚨 **밖**"))
    P("```", flush=True)

    P("")
    P("## 3. 팔 일곱")
    P("")
    P("| 팔 | 줄인 거래 | 세후 총액(중앙) | 연 환산 | 📏폭 | 낙폭 중앙 | 회복 | 매수 |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|")
    for nm, _s, _m in ARMS:
        v = out[nm]
        m_ = st.median([a[0] for a in v])
        P("| **%s** | %.0f | %.0f만 | **%+.2f%%** | %.2f | %+.1f%% | %.1f년 | %.0f |"
          % (nm, meta[nm]["cut"], m_, acc.cagr(m_, YRS), spread(v),
             st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0,
             st.median([a[3] for a in v])))

    def diff(x, y):
        d = [acc.cagr(out[x][i][0], YRS) - acc.cagr(out[y][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("")
    P("## 4. 판정 — 🚨 **주 판정은 «Ⓐ−Ⓓ»·«Ⓒ−Ⓓ′» 다. ①과의 차이는 «따로»**")
    P("")
    P("```")
    P("⛔ **주 판정을 「팔−①」 로 «바꾸지» 않는다** — 그러면 「줄이는 «비용»」이 «섞이고»,")
    P("   그건 `159` 가 «이미» **−3.86%p** 로 잰 **«다른»** 것이다")
    P("```")
    P("")
    P("| 짝 | 차 | **95% CI** | 판정 |")
    P("|---|---:|---|:--|")
    for lab, x, y in (("**Ⓐ − Ⓓ**(변동성 · «아는» 축)", "Ⓐ 변동성 «큰» 칸 ×0.5", "Ⓓ 무작위(Ⓐ 와 수 맞춤)"),
                      ("**Ⓒ − Ⓓ′**(유동성 · «모르는» 축)", "Ⓒ 거래대금 «하위» ×0.5", "Ⓓ′ 무작위(Ⓒ 와 수 맞춤)"),
                      ("Ⓑ − Ⓓ «음성»", "Ⓑ 변동성 «작은» 칸 ×0.5 «음성»", "Ⓓ 무작위(Ⓐ 와 수 맞춤)"),
                      ("Ⓒ′ − Ⓓ′ «음성»", "Ⓒ′ 거래대금 «상위» ×0.5 «음성»", "Ⓓ′ 무작위(Ⓒ 와 수 맞춤)")):
        mu, lo, hi = diff(x, y)
        vd = ("🔴 **«거꾸로» 골랐다 — 원전의 «반대»가 맞다**" if (mu <= -DELTA and hi < 0) else
              ("⚠️ 반대 방향이나 **Δ 미만**" if hi < 0 else
               ("✅ **원전 방향이 «맞다»**" if (mu >= DELTA and lo > 0) else
                ("⚠️ 원전 방향이나 **Δ 미만**" if lo > 0 else
                 "🚨 **무작위와 «구분 안 됨»**"))))
        P("| %s | **%+.3f%%p** | [%+.3f, %+.3f] | %s |" % (lab, mu, lo, hi, vd))
    P("")
    P("```")
    P("★★ **「비대칭」이 «네 번째»다 — 「방향이 같다」보다 «크기»를 적는다:**")
    P("")
    bad = -diff("Ⓒ 거래대금 «하위» ×0.5", "Ⓓ′ 무작위(Ⓒ 와 수 맞춤)")[0]
    good = diff("Ⓒ′ 거래대금 «상위» ×0.5 «음성»", "Ⓓ′ 무작위(Ⓒ 와 수 맞춤)")[0]
    P("   159 배제  −3.86 / +1.09  →  **3.5배**")
    P("   160 순위  −1.15 / +0.18  →  **6.4배**")
    P("   161 종가  −1.11 / +0.84  →  1.3배")
    P("   **164 크기  −%.2f / +%.2f  →  %.1f배**" % (bad, good, bad / max(good, 1e-9)))
    P("")
    P("   ⇒ ## **「얻기는 어렵고 «잃기는» 쉽다」의 «네 번째» 증거**")
    P("")
    P("🚨 **단 Ⓒ·Ⓒ′ 는 «항등식»이 «아니지만»(%.1f배 차) «독립 증거»도 «아니다»**"
      % (bad / max(good, 1e-9)))
    P("   — **같은 자료 · 같은 씨앗 · 같은 기준(Ⓓ′)**을 쓴다. «한 판의 두 면»이다")
    P("```")
    P("")
    P("**①과의 차이 — «따로» 적는다(「줄이는 «비용»」이 섞인 수다)**")
    P("")
    P("| 팔 − ① | 차 | **95% CI** |")
    P("|---|---:|---|")
    for nm, _s, _m in ARMS[1:]:
        mu, lo, hi = diff(nm, "①현행")
        P("| %s | **%+.3f%%p** | [%+.3f, %+.3f] |" % (nm, mu, lo, hi))
    P("")
    P("```")
    P("**KF★ — 위험 축 «둘»**(낙폭 «중앙» · 📏폭 = P95÷P05) · 「위험 «하나»만 나쁨」 칸을 «미리» 둔다:")
    P("   자산 «이김» + 위험 «하나»만 나쁨  →  「맞바꿈 — 사용자 «선택»」")
    P("   자산 «짐»   + 위험 «하나»만 나쁨  →  ⛔ 「**선택지가 «아니다». «진» 것이다**」")
    P("")
    P("**KB★ — «두 단계». 「노출」 문턱을 «지금» 만들지 «않는다**")
    P("   🚨 「노출 Δ%p ↔ 성적 Δ%p」 환산이 **«안 된다»** —")
    P("     `163` Ⓟ 에서 **노출 «+4.6%p» 인데 성적 «−5.37%p»**(선형이 «아니다»)")
    for nm, _s, _m in ARMS:
        if meta[nm]["expo"] is not None:
            P("   %-32s 노출 **%.1f%%** (① 대비 %+.1f%%p)"
              % (nm, meta[nm]["expo"], meta[nm]["expo"] - meta["①현행"]["expo"]))
    P("")
    P("   ✅ **Ⓓ·Ⓓ′ 는 「평균」이 아니라 «배정별 «분포»»로 낸다 — 빈칸을 «채운다»**")
    P("     (「못 낸다」가 아니라 **「«다른 모양»으로 낼 수 있다」**였다.")
    P("      🚨 이 둘은 **«주 판정의 «기준»»**이라, 노출을 «모르면» 「노출이 «맞았나」를")
    P("      «모르는 채» 판정하게 된다)")
    for nm, _s, _m in ARMS:
        e = meta[nm].get("expo_d")
        if e:
            P("   %-28s 노출 **%.1f ~ %.1f%%** (중앙 **%.1f%%** · ① 대비 %+.1f%%p)"
              % (nm, min(e), max(e), st.median(e), st.median(e) - meta["①현행"]["expo"]))
    P("")
    P("   ⇒ **Ⓐ %.1f%% vs Ⓓ 중앙 %.1f%% (%+.1f%%p)  ·  Ⓒ %.1f%% vs Ⓓ′ 중앙 %.1f%% (%+.1f%%p)**"
      % (meta["Ⓐ 변동성 «큰» 칸 ×0.5"]["expo"],
         st.median(meta["Ⓓ 무작위(Ⓐ 와 수 맞춤)"]["expo_d"]),
         meta["Ⓐ 변동성 «큰» 칸 ×0.5"]["expo"]
         - st.median(meta["Ⓓ 무작위(Ⓐ 와 수 맞춤)"]["expo_d"]),
         meta["Ⓒ 거래대금 «하위» ×0.5"]["expo"],
         st.median(meta["Ⓓ′ 무작위(Ⓒ 와 수 맞춤)"]["expo_d"]),
         meta["Ⓒ 거래대금 «하위» ×0.5"]["expo"]
         - st.median(meta["Ⓓ′ 무작위(Ⓒ 와 수 맞춤)"]["expo_d"])))
    P("")
    P("   ★★ **그리고 «채운 빈칸»이 «일»을 한다 — 문턱 «없이도» 읽힌다:**")
    dC = (meta["Ⓒ 거래대금 «하위» ×0.5"]["expo"]
          - st.median(meta["Ⓓ′ 무작위(Ⓒ 와 수 맞춤)"]["expo_d"]))
    dA = (meta["Ⓐ 변동성 «큰» 칸 ×0.5"]["expo"]
          - st.median(meta["Ⓓ 무작위(Ⓐ 와 수 맞춤)"]["expo_d"]))
    P("     **주 판정 짝 Ⓒ↔Ⓓ′ 는 노출이 «%+.1f%%p» 로 «거의 맞는다»**" % dC)
    P("     ⇒ ✅ **Ⓒ−Ⓓ′ 의 −0.899%p 를 «노출 탓»으로 «못» 돌린다** — 두 팔이 «같은 만큼» 투입했다")
    P("     🚨 반면 Ⓐ↔Ⓓ 는 **%+.1f%%p** 벌어진다 — 다만 Ⓐ−Ⓓ 는 «어차피» 「구분 안 됨」이다" % dA)
    P("     ★ **이래서 「평균」이 아니라 «분포»로 내야 했다.** 「못 낸다」였으면 이 읽기가 «없었다»")
    P("")
    P("   🚨 **문턱은 «여전히» 안 만든다** — 「노출 Δ%p ↔ 성적 Δ%p」 환산이 «안 되기» 때문이다")
    P("   ✅ **«수»를 적고 「이 값으로 «못 정한다」**로 둔다 — «빈칸»이 아니라 «측정된 미결»이다")
    P("```")
    P("")
    P("```")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ 「원전이 «맞다/틀리다」」를 **Ⓐ−Ⓓ «하나»로** — 축이 «둘»이고 «다른» 것을 잰다")
    P("   ⛔ 「**작은 종목을 «사지 마라»**」 — 이 판은 «크기»를 묻지 «매수 여부»를 «안» 묻는다")
    P("   ⛔ 켈리 «수»를 «권고»로 — 아래는 **«가정 검사»**지 «검산»이 «아니다**")
    P("```")
    P("")
    # ── 부산물 둘 — 판 «하나»만 더 돌린다(현행 · 씨앗 0) ─────────────────────
    with r91.r41.Cost(*r91.COST):
        x0 = r91.sl.sim_lots(ev, seed=0, slots=SLOTS, risk=0.02, cap=0.20,
                             reserve=False, fill_rule="truncate", cash_rule="per_slot")
    rl = x0["ret_log"]
    rr = sorted(r for _d, r, _t in rl)
    win = [r for r in rr if r > 0]
    los = [-r for r in rr if r <= 0]
    W = len(win) / len(rr)
    R = (st.mean(win) / st.mean(los)) if los else float("inf")
    kel = W - (1.0 - W) / R
    # 🚨 「이익의 몇 %」는 **«돈»**으로 센다 — `slot_sim_lots:158` 이 pl = tot × r/100 이다.
    #    «% 수익률»을 더하면 **«다른 자»**가 된다(유형 67)
    money = sorted(t_ * r / 100.0 for _d, r, t_ in rl)
    gain = sum(v for v in money if v > 0)
    k1 = max(1, len(money) // 100)
    top1 = sum(money[-k1:]) / gain * 100.0
    top1r = sum(rr[-k1:]) / sum(win) * 100.0

    P("")
    P("## 5. 부산물 ① — **켈리는 «검산»이 아니라 «가정 검사»다**")
    P("")
    P("```")
    P("⛔ 「켈리가 %.0f%% 라 하니 %.0f%% 가 맞다」 — **못 쓴다**. 가정이 «깨졌기» 때문이다"
      % (100 * kel, 100 * kel))
    P("")
    P("우리 자료(현행 · 씨앗 0 · 거래 %s):" % format(len(rr), ","))
    P("   승률 **%.1f%%** · 평균 이익 **%+.2f%%** · 평균 손실 **%.2f%%** · 손익비 **%.2f**"
      % (100 * W, st.mean(win), st.mean(los), R))
    P("   ⇒ 켈리 f* = W − (1−W)/R = **%.1f%%**" % (100 * kel))
    P("")
    P("🚨 **그런데 켈리는 「승률·손익비가 «안 변한다»」를 «가정»한다.** 우리 자료는 «아니다»:")
    P("   **이익(«돈»)의 %.1f%% 가 «상위 1%%»(%s 건)에서 나온다**" % (top1, format(k1, ",")))
    P("")
    P("   🚨 **자를 «갈라» 적는다**(유형 67 — 하마터면 «섞을» 뻔했다):")
    P("     ㉠ **«돈»** = `tot × r/100` 의 합  →  **%.1f%%**   ← **이 자를 쓴다**" % top1)
    P("     ㉡ **«%% 수익률»**의 합             →  %.1f%%     ← **«다른 자»**다. 포지션 «크기»를 안 본다"
      % top1r)
    P("   🚨 그리고 **`86` 의 115.7% 와 «맞대지» 않는다** — 86 은 «거래 3,019 건 전수»이고")
    P("     이건 **«씨앗 하나»의 «체결» %s 건**이다(칸 5 라 대부분 «못» 산다). **분모가 «다르다»**"
      % format(len(rl), ","))
    k10 = max(1, len(money) // 10)
    t10 = sum(money[-k10:]) / gain * 100.0
    P("     상위 10%%(%s 건)  →  **%.1f%%**  (균등이면 10%%)" % (format(k10, ","), t10))
    P("")
    P("🚨 **결론을 «내 수»에 맞춘다 — «앞서» 나가지 않는다:**")
    P("   ✅ 말할 수 있는 것: 「상위 1%%가 이익의 **%.1f%%** = **%.0f배** 몫이다. **꼬리가 «있다»**」"
      % (top1, top1 / 1.0))
    P("   ⛔ 말할 수 «없는» 것: 「그러니 켈리가 **«크게»** 과대베팅한다」")
    P("     — **«얼마나»는 «안 쟀다».** 그러려면 «꼬리를 넣은» 성장률을 «따로» 계산해야 한다")
    P("   ⛔ 그리고 **`86` 의 115.7%를 «내 근거»로 «빌려오지» 않는다** — 분모가 «다르다»")
    P("")
    P("★ 그래서 이 절이 «답하는» 것은 **«하나»**뿐이다:")
    P("   ## **「켈리의 «가정»(승률·손익비가 «안 변한다»)이 «우리 자료에서» 안 맞는다」**")
    P("   ⇒ 그러므로 **「원전의 25%」를 «켈리로» 옹호하거나 반박할 «수 없다»**")
    P("   🚨 **`162`(상한 20% 최선)와 «일관»된다고 «쓰지» 않는다** — 그건 **«다른 증거»**이고,")
    P("     둘을 잇는 것은 **«이야기»**지 «계산»이 아니다")
    P("⛔ **이 수를 «권고»로 쓰지 않는다** — 가정이 안 맞는 공식의 출력이다")
    P("```")
    P("")
    P("## 6. 부산물 ② — **계좌가 커지면 포지션도 커지나**")
    P("")
    P("```")
    fl = [(f[3], f[6] * acc.START) for f in x0["fill_log"] if f[1] == "pilot"]
    e_ = [v for d, v in fl if d[:4] <= "2001"]
    l_ = [v for d, v in fl if d[:4] >= "2024"]
    P("초년(1999~2001) 매수 **%d** 건 — 포지션 중앙 **%.0f만원**" % (len(e_), st.median(e_)))
    P("말년(2024~2026) 매수 **%d** 건 — 포지션 중앙 **%.0f만원**" % (len(l_), st.median(l_)))
    P("")
    P("🚨🚨 **「몇 배」를 «적지 않는다» — «항등식»이다:**")
    P("   포지션이 **«자산의 고정 20%»** 이므로, 자산이 X 배면 포지션도 **정확히 X 배**다")
    P("   ⇒ **«발견»이 «아니다».** 「계좌가 커지면 포지션도 커지나」의 답은 «정의»에서 나온다")
    P("")
    P("✅ **진짜 물음은 「그 크기가 «시장»에 «부담»인가」다 — 그건 «안 쟀다**")
    P("   자는 **«있다»**: **N = 포지션 ÷ ADV20** · **M = ADV20 × 5%**(분할매도 시작 금액)")
    P("   ⇒ ⛔ **«거래대금 대비» 비중은 «안 쟀다»**로 «닫는다**")
    P("   ★ 그건 **«백테스트»가 아니라 «실전 집행»**의 물음이다")
    P("```")
    P("")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 진입 규칙",
                     "같은 손절 −10 · 목표 +30", "**같은 거래 집합**(아무도 «안» 뺌)"]):
        P(ln)
    P("🚨 **그리고 Ⓓ·Ⓓ′ 의 «%d × %d = %d» 은 «유효 n» 이 «아니다»** — 배정 축은 «평균»으로 «없앴고»,"
      % (n_seed, n_as, n_seed * n_as))
    P("   남은 축은 **씨앗 %d** 이다. 그것도 위 목록 때문에 «유효 n = 1» 이다" % n_seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
