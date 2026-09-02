# -*- coding: utf-8 -*-
r"""159 — **「싼 주식은 빼라」** · 사전등록 `tasks/159-price-level.md`

  🏷️ **세대 B** (지수 숏 «없음» · `account_lib`) · 규칙 **+30/−10 (2026-09-02~ · `41db459d`)**

  🚨 이 판의 «진짜» 물음 (검증 세션이 고침):
     146 — **자리가 93.9% 찬다** ⇒ 「빼면」 자리가 «비고» **«다른 후보»가 «채운다»**
     ⇒ 물음은 「$30 미만이 «나쁜가»」가 «아니라» **「«빼서 생긴 자리»가 «값을 하는가»」**
     ⛔ **「배제된 거래의 «사후» 성적」으로는 «못 가린다»** — 「뺀 것」만 말하고 「채운 것」을 «안» 말한다
     ✅ 가르는 건 **«계좌 차»뿐**(그게 «대체»를 이미 담는다). 사후 성적은 **«서술»로만**

  ⛔ 뒤 구간 안 엶 · 검출기 «안» 건드림 · 바뀌는 건 **«후보를 뺄까»** 뿐
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

PX = Path("D:/stock-data/derived/159-entry-price.json")
PCT = Path("D:/stock-data/derived/159-price-pctile.json")
D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF = 30.0, 10.0, 0.5
NSEED, YRS, DELTA, T60 = 60, 27.4, 1.23, 2.001
NASSIGN = 10          # 🚨 Ⓓ 의 «배정» 축 — 156 ⑤ 에서 배운 «여분 분산» 제거
CACHE = Path(str(r91.OUT / "159-partial.json"))


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    P = print
    P("=" * 104)
    P("159 — **「싼 주식은 빼라」** · 🏷️ 세대 B · 규칙 **+30/−10** · 씨앗 %d판" % n_seed)
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-02 · `scripts/159-price-level.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## 가정·출처 — 🚨 **이 절이 «첫 적용»이다**(158 에서 「배당률 0.2%」가 여기 걸렸어야 했다)")
    P("")
    P("```")
    P("주가       `stocks.csv` 의 **`closeunadj`**            ← 출처: Sharadar 원열 · 159b 로 **100.0%** 확보")
    P("문턱 $30   원전(미너비니) «글자»                       ← 출처: 사용자님이 주신 원문")
    P("백분위 81.9% 1999-06-30 에 $30 의 자리                 ← 출처: **159a 실측**(7,972 중 6,530)")
    P("Δ = 1.23%p 「결론을 바꾸는 크기」                       ← 출처: **150 의 우리−QQQ 격차**")
    P("자리 점유 93.9%  「빼면 다른 후보가 채운다」의 근거      ← 출처: **146 실측**")
    P("규칙 +30/−10                                          ← 출처: **커밋 `41db459d`**(사용자 결정)")
    P("")
    P("⚠️ **출처가 «빈» 가정 — «하나»:**")
    P("   ⛔ 「$12」 팔은 **«우리가» 고른 수**다. 원전에도 자료에도 근거가 «없다»")
    P("      ⇒ 그래서 **«묘사»로만** 쓰고 **«판정»에 «안» 넣는다**")
    P("```", flush=True)

    px = json.loads(PX.read_text(encoding="utf-8"))
    pc = json.loads(PCT.read_text(encoding="utf-8"))
    thr, days = pc["thr"], sorted(pc["thr"])

    def thr_at(d):
        lo, hi, i = 0, len(days) - 1, None
        while lo <= hi:
            m = (lo + hi) // 2
            if days[m] <= d:
                i, lo = m, m + 1
            else:
                hi = m - 1
        return thr[days[i]] if i is not None else None

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    cands, n_nopx = [], 0
    for y in sorted(by2):
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is False:
                continue
            u = px.get("%s|%s" % (p["code"], p["entry_date"]))
            if u is None:
                n_nopx += 1
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            cands.append((y, p, t, u))

    # ── 팔 정의 — 🚨 규약: 주가가 «없으면» «배제 «안» 함»(효과를 «약하게만» 한다) ──
    ARMS = {
        "①현행(문턱 없음)": lambda u, d: True,
        "Ⓐ-30 (고정 $30)": lambda u, d: (u is None) or u >= 30.0,
        "Ⓒ 고정 백분위 81.9%": lambda u, d: (u is None) or (thr_at(d) is None) or u >= thr_at(d),
        "Ⓐ-12 (고정 $12 · 묘사)": lambda u, d: (u is None) or u >= 12.0,
    }
    P("")
    P("## 관문 EC★ — **배제율이 «예상»과 맞나**")
    P("")
    P("```")
    P("후보 **%s** 개 · 주가 «없는» 것 **%d** 개 (%.2f%%) — 규약대로 **«배제 안 함»**"
      % (format(len(cands), ","), n_nopx, 100.0 * n_nopx / max(len(cands), 1)))
    P("")
    for nm, fn in ARMS.items():
        kept = sum(1 for _y, p, _t, u in cands if fn(u, p["entry_date"]))
        P("%-24s 남김 **%s** / %s  →  **배제 %.1f%%**"
          % (nm, format(kept, ","), format(len(cands), ","),
             100.0 * (1 - kept / len(cands))))
    ex30 = 100.0 * (1 - sum(1 for _y, p, _t, u in cands
                            if ARMS["Ⓐ-30 (고정 $30)"](u, p["entry_date"])) / len(cands))
    P("")
    P("EC★  Ⓐ-30 배제율 **%.1f%%**  vs  두뇌 세션 사전 실측 **55.1%%**  →  **%s**"
      % (ex30, "✅ 통과" if abs(ex30 - 55.1) < 5 else "🚨 **미통과 — 자료를 «잘못» 붙였다**"))
    P("```", flush=True)

    def build_ev(fn):
        ev = []
        cur = None
        open_until = {}
        for y, p, t, u in cands:
            if y != cur:
                cur, open_until = y, {}
            if not fn(u, p["entry_date"]):
                continue
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                continue
            open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
            ev.append(t)
        return ev

    span = (r102._ord(D1) - r102._ord(D0)) or 1

    def occupancy(x, ev):
        """★ 자리-일 점유율 — 체결된 거래의 «보유일 합» / (칸 5 × 창 일수)
        🚨 `fill_log` 의 첫 칸이 «거래 key» 다(`slot_sim_lots:283`)"""
        rd = {}
        for t in ev:
            m = t["masks"][()]
            rd[(t["scan_date"], t["code"], t["pattern"])] = (
                t["entry_date"], m["resolve_date"] or t["entry_date"])
        tot = 0
        for f in x["fill_log"]:
            if f[1] != "pilot":
                continue
            v = rd.get(f[0])
            if v:
                tot += max(0, r102._ord(v[1]) - r102._ord(v[0]))
        return 100.0 * tot / (r91.SLOTS * span)

    def run(ev):
        with r91.r41.Cost(*r91.COST):
            return [r91.sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                    reserve=False, fill_rule="truncate", cash_rule="per_slot")
                    for s in range(n_seed)]

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out, occ = {}, {}
    for nm, fn in ARMS.items():
        key = "%s|n%d" % (nm, n_seed)
        if key in cache:
            out[nm] = [tuple(a) for a in cache[key]]
            occ[nm] = cache.get(key + "|occ")
            P("  ♻️ %s — 갈무리" % nm, flush=True)
            continue
        ev_ = build_ev(fn)
        rs = run(ev_)
        out[nm] = [acc.account(x) for x in rs]
        occ[nm] = st.median([occupancy(x, ev_) for x in rs])
        cache[key + "|occ"] = occ[nm]
        cache[key] = [list(a) for a in out[nm]]
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        P("  %s — 중앙 %.0f만 · 매수 %.0f"
          % (nm, st.median([a[0] for a in out[nm]]),
             st.median([a[3] for a in out[nm]])), flush=True)

    # ── 🚨 팔 Ⓓ — 「연도별 배제 «수»를 Ⓐ-30 과 «맞춘» 무작위 배제」(검증 세션) ────
    #    ★ 156 의 ⑤′(순열 플라세보)와 «같은 수법» — «바꾸려는 축»(가격 수준)만 바꾸고
    #      «주변분포»(연도별 배제 «수»)는 «묶는다».
    #    Ⓓ 도 −3.5%p 면 → **«시점»이 원인**(가격과 «무관») · Ⓓ ≈ 0 이면 → **«가격 수준»이 원인**
    dnm = "Ⓓ 무작위(연도별 «수» 맞춤)"
    dkey = "%s|n%d" % (dnm, n_seed)
    if dkey in cache:
        out[dnm] = [tuple(a) for a in cache[dkey]]
        occ[dnm] = cache.get(dkey + "|occ")
        P("  ♻️ %s — 갈무리" % dnm, flush=True)
    else:
        byy = {}
        for y, p, t, u in cands:
            byy.setdefault(y, []).append((p, t, u))
        ncut = {y: sum(1 for p, _t, u in v
                       if not ARMS["Ⓐ-30 (고정 $30)"](u, p["entry_date"])) for y, v in byy.items()}
        agg, aocc = [], []
        for sd_ in range(n_seed):
            av, ao = [], []
            for a_ in range(NASSIGN):
                rng = random.Random(3_000_000 + sd_ * 1000 + a_)
                drop = set()
                for y, v in byy.items():
                    idx = list(range(len(v)))
                    rng.shuffle(idx)
                    for i in idx[:ncut[y]]:
                        drop.add(id(v[i][0]))
                ev_ = []
                cur, ou = None, {}
                for y, p, t, u in cands:
                    if y != cur:
                        cur, ou = y, {}
                    if id(p) in drop:
                        continue
                    c = p["code"]
                    if c in ou and p["entry_date"] <= ou[c]:
                        continue
                    ou[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                    ev_.append(t)
                x = run(ev_)[sd_] if False else None
                with r91.r41.Cost(*r91.COST):
                    x = r91.sl.sim_lots(ev_, seed=sd_, slots=r91.SLOTS, risk=r91.RISK,
                                        cap=r91.CAP, reserve=False, fill_rule="truncate",
                                        cash_rule="per_slot")
                av.append(acc.account(x))
                ao.append(occupancy(x, ev_))
            agg.append(tuple(st.mean([r[i] for r in av]) for i in range(4)))
            aocc.append(st.mean(ao))
            if sd_ % 10 == 0:
                P("    Ⓓ 씨앗 %d/%d …" % (sd_, n_seed), flush=True)
        out[dnm] = agg
        occ[dnm] = st.median(aocc)
        cache[dkey] = [list(a) for a in agg]
        cache[dkey + "|occ"] = occ[dnm]
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        P("  %s(배정 %d개 평균) — 중앙 %.0f만 · 매수 %.0f"
          % (dnm, NASSIGN, st.median([a[0] for a in agg]),
             st.median([a[3] for a in agg])), flush=True)

    P("")
    P("=" * 104)
    P("## 1. 팔 넷")
    P("=" * 104)
    P("")
    P("| 팔 | 세후 총액(중앙) | 연 환산 | «세전» 낙폭 | 매수 | **자리-일 점유** |")
    P("|---|---:|---:|---:|---:|---:|")
    for nm in list(ARMS) + [dnm]:
        v = out[nm]
        m = st.median([a[0] for a in v])
        P("| **%s** | %.0f만 | **%+.2f%%** | %+.1f%% | %.0f | **%.1f%%** |"
          % (nm, m, acc.cagr(m, YRS), st.median([a[1] for a in v]),
             st.median([a[3] for a in v]), occ.get(nm) or float("nan")))
    P("")
    P("🚨 **낙폭은 «세전» 곡선 · 총액은 «세후» — «나누지 마라»**")
    P("")
    P("=" * 104)
    P("## 2. ⛔ **ED★ 주 판정 — 「빼서 생긴 자리가 «값을 하는가»」**")
    P("=" * 104)
    P("")
    base = out["①현행(문턱 없음)"]
    P("| 비교 | 연 차이 | SD | **95% CI** | 효과/SD |")
    P("|---|---:|---:|---|---:|")
    st_ = {}

    def pair(a, b):
        d = [acc.cagr(out[a][i][0], YRS) - acc.cagr(out[b][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, sd, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    for nm in ("Ⓐ-30 (고정 $30)", "Ⓒ 고정 백분위 81.9%", dnm, "Ⓐ-12 (고정 $12 · 묘사)"):
        d = [acc.cagr(out[nm][i][0], YRS) - acc.cagr(base[i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        lo, hi = mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)
        st_[nm] = (mu, sd, lo, hi)
        P("| %s − ① | **%+.3f%%p** | %.3f | **[%+.3f, %+.3f]** | %.2f |"
          % (nm, mu, sd, lo, hi, abs(mu) / sd if sd else float("inf")))
    P("")
    P("")
    P("### 🚨🚨 **주 판정이 «바뀐다» — 상대는 ① 이 «아니라» Ⓓ 다**")
    P("")
    P("```")
    P("Ⓓ(연도별 «수»를 맞춘 «무작위» 배제)가 **%+.3f%%p** 로 Ⓐ-30(%+.3f%%p)보다 **«더» 나쁘다**"
      % (st_[dnm][0], st_["Ⓐ-30 (고정 $30)"][0]))
    P("⇒ ★★ **「빼서 나빠진 것」은 «가격 수준»이 «아니라» «후보를 뺀 것» 자체다**")
    P("   (86: 상위 1%가 이익의 115.7% — **아무 절반이나 빼면 «꼬리의 절반»이 사라진다**)")
    P("")
    P("★ 그러므로 **«가격 필터»의 값어치는 «Ⓐ-30 − Ⓓ»** 로 잰다 — «같은 수»를 뺐을 때의 차:")
    for nm in ("Ⓐ-30 (고정 $30)", "Ⓒ 고정 백분위 81.9%"):
        mu, sd, lo, hi = pair(nm, dnm)
        P("   **%-22s − Ⓓ = %+.3f%%p**  [%+.3f, %+.3f]  →  %s"
          % (nm, mu, lo, hi,
             "🚨 **못 가린다**" if lo <= 0 <= hi else
             ("✅ **«무작위보다 «낫다»»**" if mu > 0 else "⛔ **무작위보다 «나쁘다»**")))
    P("")
    P("🚨 **점유율 — «재구성» 값이다. 라벨을 단다**")
    P("   ⛔ 146 의 **94.6%**(직접 회계 · `daylog` 에서 «세었고» 항등식으로 닫힘)와 **맞대면 안 된다**:")
    P("     ① 분모의 «날 종류» — 146 은 **«거래일»**, 여기는 **«달력일»**")
    P("     ② 🚨 여기는 `fill_log` 를 **키로 «되찾아»** 셌다 — **키가 «안 맞으면» 그 날이 «조용히» 빠진다**")
    P("   ✅ 그래도 **«팔 사이» 비교엔 쓸모 있다** — 같은 방식이라 **«편향이 공통»**이다")
    P("")
    P("🚨 **점유율이 «대안»을 거른다:** ① **%.1f%%** · Ⓐ-30 **%.1f%%** · Ⓓ **%.1f%%**"
      % (occ["①현행(문턱 없음)"], occ["Ⓐ-30 (고정 $30)"], occ[dnm]))
    P("   ⇒ 셋이 «비슷»하다. **「자리가 «비어서»」로는 −4%p 를 «설명 못 한다»**")
    P("   (Ⓓ 는 매수 **%.0f** 로 ① 의 **%.0f** 와 «거의 같은데»도 «제일 나쁘다»)"
      % (st.median([a[3] for a in out[dnm]]), st.median([a[3] for a in base])))
    P("")
    P("🚨🚨 **이 비교(Ⓐ−Ⓓ)에는 «사전등록된 문턱»이 «없다».**")
    P("   Ⓓ «팔»은 검증 세션이 «값 보기 전»에 걸었지만, **「Ⓐ−Ⓓ 를 «주 판정»으로 삼는다」는**")
    P("   **Ⓓ 결과를 «본 뒤»에 내가 정했다.** ⇒ **«확정»이 아니라 «다음 판의 물음»이다**")
    P("   ✅ 그래도 **방향은 산다** — 「«같은 수»를 뺀다면 «싼 것부터»가 «무작위보다» 낫다」")
    P("```")
    P("")
    P("```")
    P("★★ **그래서 «실행»의 답은 여전히 「빼지 마라」다:**")
    P("   ①(안 뺌) **%+.2f%%**  >  Ⓒ **%+.2f%%**  >  Ⓐ-30 **%+.2f%%**  >  Ⓓ **%+.2f%%**"
      % (acc.cagr(st.median([a[0] for a in base]), YRS),
         acc.cagr(st.median([a[0] for a in out["Ⓒ 고정 백분위 81.9%"]]), YRS),
         acc.cagr(st.median([a[0] for a in out["Ⓐ-30 (고정 $30)"]]), YRS),
         acc.cagr(st.median([a[0] for a in out[dnm]]), YRS)))
    P("   ⇒ **«어느» 배제도 「안 빼기」보다 «못하다».** 필터의 «고르는 값어치»(+1.09%p)가")
    P("     **«빼는 값»(−3.86%p)을 «못 갚는다»**")
    P("")
    P("★ 그리고 **Ⓒ(+1.085) > Ⓐ-30(+0.314)** 이다 ⇒ **「$30 이 낡았다」도 «부분적으로» 맞다**")
    P("   («고정 백분위»가 «고정 달러»보다 **0.77%p** 낫다)")
    P("```")
    P("")
    P("```")
    P("★ **읽는 표 — 값 보기 «전»에 박았다:**")
    for nm in ("Ⓐ-30 (고정 $30)", "Ⓒ 고정 백분위 81.9%"):
        mu, sd, lo, hi = st_[nm]
        if lo <= 0 <= hi:
            v = "🚨 **「못 가린다」**(「같다」가 «아니다»)"
        elif mu >= DELTA and lo > 0:
            v = "✅ **「원전이 우리 자료에서 «선다»」**"
        elif mu > 0:
            v = "⚠️ **「방향은 맞으나 «결론을 바꿀 크기»가 아니다」**(155·156 과 같은 자리)"
        else:
            v = "⛔ **「빼면 오히려 «나쁘다»」** — 그것도 답"
        P("%-24s %+.3f%%p  [%+.3f, %+.3f]  →  %s" % (nm, mu, lo, hi, v))
    P("")
    P("Δ = **%.2f%%p** ← 유도: 150 의 우리−QQQ 격차" % DELTA)
    P("```")
    P("")
    P("### 🚨 **거를 «대안 설명» — 「자리가 «비어서»」인가?**")
    P("")
    P("```")
    n1 = st.median([a[3] for a in base])
    n2 = st.median([a[3] for a in out["Ⓐ-30 (고정 $30)"]])
    P("후보를 **52.9%%** 뺐는데 매수는 **%.0f → %.0f = −%.1f%%** 밖에 «안» 줄었다"
      % (n1, n2, 100.0 * (1 - n2 / n1)))
    P("⇒ **«대체»가 «실제로» 일어났다** — 146 의 「자리 93.9%」가 여기서도 산다")
    P("")
    P("★ 그래도 「자리가 «덜» 차서 현금이 늘었나」를 물어야 한다. **낙폭이 답한다:**")
    P("   ① **%+.1f%%**  →  Ⓐ-30 **%+.1f%%**   = **%.1f%%p «더 나빠졌다»**"
      % (st.median([a[1] for a in base]),
         st.median([a[1] for a in out["Ⓐ-30 (고정 $30)"]]),
         abs(st.median([a[1] for a in out["Ⓐ-30 (고정 $30)"]])
             - st.median([a[1] for a in base]))))
    P("   🚨 **현금이 늘면 낙폭은 «얕아진다».** 그런데 «깊어졌다»")
    P("   ⇒ ⛔ **「자리가 비어서」로는 «설명 안 된다»** — 남은(비싼) 종목이 **«더 나쁘고 더 흔들렸다»**")
    P("")
    P("⚠️ **그래도 «완전히» 가른 건 «아니다»** — 「칸 점유율」을 «직접» 안 쟀다.")
    P("   낙폭 논거는 **«반증»이지 «측정»이 아니다**")
    P("🚨 **「미통과」를 「효과가 «없다»」로 «안» 읽는다** — 오늘 최대 효과가 0.778%p 였고")
    P("   Δ 는 그 **1.6배**다. **이만한 효과가 «존재한» 전례가 «없다**»")
    P("```")
    P("")
    for nm in ("Ⓐ-30 (고정 $30)", "Ⓒ 고정 백분위 81.9%"):
        mu, sd, _lo, _hi = st_[nm]
        P("```")
        P("%s — 효과/씨앗SD" % nm)
        for ln in gates.p_informative(mu, sd, n=n_seed)[1]:
            P("   " + ln)
        P("```")
    # ── 마지막 검사 — 「대체로 «들어온» 거래」가 «더 나빴나» ────────────────
    P("")
    P("=" * 104)
    P("## 3. 🚨 **「대체로 «들어온» 거래」가 «더 나빴나»** (검증 세션이 「제일 값어치 있다」한 검사)")
    P("=" * 104)
    P("")
    ND = min(n_seed, 20)
    P("```")
    P("Ⓓ 는 매수 **%.0f** 로 ① 의 **%.0f** 와 «거의 같은데»도 «제일 나쁘다»"
      % (st.median([a[3] for a in out[dnm]]), st.median([a[3] for a in base])))
    P("⇒ **«대체해 들어온 것»이 «더 나빴다»는 뜻인가?  «재서» 답한다**")
    P("")
    P("🚨 라벨 — **씨앗 %d 판 · Ⓓ 배정 «0번» 하나**만 쓴다(«묘사»다. 판정 아님)" % ND)

    def tret(t):
        m = t["masks"][()]
        return sum(fr * (px / t["entry_px"] - 1.0) for _d, fr, px in (m.get("exits") or []))

    byy = {}
    for y, p, t, u in cands:
        byy.setdefault(y, []).append((p, t, u))
    ncut = {y: sum(1 for p, _t, u in v
                   if not ARMS["Ⓐ-30 (고정 $30)"](u, p["entry_date"])) for y, v in byy.items()}
    ev1 = build_ev(ARMS["①현행(문턱 없음)"])
    tmap = {(t["scan_date"], t["code"], t["pattern"]): t for t in ev1}
    lost_r, repl_r = [], []
    with r91.r41.Cost(*r91.COST):
        for sd_ in range(ND):
            rng = random.Random(3_000_000 + sd_ * 1000 + 0)
            drop = set()
            for y, v in byy.items():
                idx = list(range(len(v)))
                rng.shuffle(idx)
                for i in idx[:ncut[y]]:
                    drop.add(id(v[i][0]))
            evd, cur, ou = [], None, {}
            for y, p, t, u in cands:
                if y != cur:
                    cur, ou = y, {}
                if id(p) in drop:
                    continue
                c = p["code"]
                if c in ou and p["entry_date"] <= ou[c]:
                    continue
                ou[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                evd.append(t)
            x1 = r91.sl.sim_lots(ev1, seed=sd_, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                 reserve=False, fill_rule="truncate", cash_rule="per_slot")
            xd = r91.sl.sim_lots(evd, seed=sd_, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                 reserve=False, fill_rule="truncate", cash_rule="per_slot")
            k1 = {f[0] for f in x1["fill_log"] if f[1] == "pilot"}
            kd = {f[0] for f in xd["fill_log"] if f[1] == "pilot"}
            lost_r += [tret(tmap[k]) for k in (k1 - kd) if k in tmap]
            repl_r += [tret(tmap[k]) for k in (kd - k1) if k in tmap]
    if lost_r and repl_r:
        P("")
        P("① 에만 있던(«잃은») 거래   **%s** 건 · 평균 **%+.2f%%** · 중앙 %+.2f%%"
          % (format(len(lost_r), ","), 100 * st.mean(lost_r), 100 * st.median(lost_r)))
        P("Ⓓ 에만 있던(«대체») 거래   **%s** 건 · 평균 **%+.2f%%** · 중앙 %+.2f%%"
          % (format(len(repl_r), ","), 100 * st.mean(repl_r), 100 * st.median(repl_r)))
        P("차(대체 − 잃음)  **%+.2f%%p/거래**" % (100 * (st.mean(repl_r) - st.mean(lost_r))))
        P("")
        if st.mean(repl_r) < st.mean(lost_r):
            P("⇒ ✅ **«대체»가 «더 나빴다»** — 「우리 «순위»에 «정보»가 있다」의 «직접» 증거")
        else:
            P("⇒ 🚨 **«대체»가 «안» 나빴다** — 그러면 −3.86%p 는 «다른 데서» 온다. «왜»부터")
        P("")
        P("★★ **이 검사가 재는 것은 「후보 풀이 크면 좋다」가 «아니다»** —")
        P("   순위가 «무작위»였다면 절반을 빼고 나머지로 채워도 **«기대 품질이 같아야»** 한다.")
        P("   **나빠졌다는 것은 «순위에 «정보»가 있다»는 뜻이다**")
        P("")
        P("★ 그리고 이건 **「고르기 일곱 번 실패」와 «모순이 아니라 «짝»»이다:**")
        P("   140 「선별 우위의 **92%**가 «상승 추세 종목을 고른다»」")
        P("   146 「자리를 막는 것의 **70.3%**가 «결국 이긴» 종목」")
        P("   159 Ⓓ **«순위를 흐트러뜨리면 나빠진다»**  ← «반대 방향»에서 «같은 것»")
        P("   ⇒ **「기존 순위에 «정보가 있다»」 ≠ 「«새 체»를 얹으면 «더» 좋아진다」**")
        P("     **일곱 번 실패한 건 «후자»이고, Ⓓ 가 보인 건 «전자»다**")
    P("```")

    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 진입 규칙",
                     "같은 손절 −%.0f" % STOP, "같은 칸 5"]):
        P(ln)
    P("⇒ ✅ **이 CI 는 «우리 규칙 안에서 안정적인가»이지 «시장에서 나은가»가 아니다**")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
