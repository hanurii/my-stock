# -*- coding: utf-8 -*-
r"""161 — **「돌파일 «종가가 강한» 것을 사라」**(원전 ⑤) · 사전등록 `tasks/161-strong-close.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (2026-09-02~ · `41db459d`)** · 배당 포함 · 숏 없음

  🚨 원전 ⑤ 는 **«세 가지 다른 것»**이다:
     Ⓐ 글자 그대로 「«돌파일» 종가가 강한 것을 산다」
        ⛔ **«현재의» 장전 예약 방식에서 «집행 불가»** — 그날 종가를 «모르는 채» 산다
     Ⓑ 순위 번안 「«전날» 종가가 강한 것부터」        ✅ 가능 (2단계)
     Ⓒ 청산 번안 「그날 종가가 약하면 다음 날 판다」    ✅ 가능 (2단계)

  ★★ **이 판(1단계)은 Ⓐ 를 «먼저» 잰다. 작으면 «거기서 닫는다»** — Ⓑ·Ⓒ 를 «안» 돌린다.
  🚨 **Ⓐ 의 수는 «전략 성적»이 «아니다»:**
     ## **「장전 예약 대신 «종가를 보고» 샀다면 «얼마»를 더 벌 수 있었나」**
     ⇒ 사용자께 **「집행 방식을 «바꿀 값어치»가 있는가」**에 «수»를 드리는 것이다
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
f92a = r102.f92a
pt = r91.pt
ok0 = r91.sl.order_key

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF = 30.0, 10.0, 0.5
NSEED, YRS, DELTA, T60 = 60, 27.4, 1.23, 2.001
CACHE = Path(str(r91.OUT / "161-partial.json"))


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    P = print
    P("=" * 104)
    P("161 — **「돌파일 종가가 «강한» 것을 사라」**(원전 ⑤) · **1단계 = «천장»** · 씨앗 %d판" % n_seed)
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-02 · `scripts/161-strong-close.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## 🚨 **이 판이 재는 것은 «전략 성적»이 «아니다»**")
    P("")
    P("```")
    P("Ⓐ 는 **«진입일 종가»**를 보고 순서를 정한다 — **«그날 종가를 모르는 채» 사는 우리 방식으론 «집행 불가»**")
    P("⇒ 그러므로 Ⓐ 의 수가 답하는 물음은 «하나»뿐이다:")
    P("   ## **「장전 예약 대신 «종가를 보고» 샀다면 «얼마»를 더 벌 수 있었나」**")
    P("⛔ **«전략 성적»으로 «안» 쓴다** — 종가를 보고 사려면 «장중에 사람이 붙어야» 한다")
    P("★ **작게 나오면 그게 «제일 값진» 결과다** — 「미래를 «조금 아는» 축조차 작다」면 길이 «완전히» 닫힌다")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("종가 강도 `cr = (close − low)/(high − low)`   ← 출처: 원전 ⑤ 의 «글자»(「종가가 강하다」)")
    P("진입일 바 `d[0] == entry_date`                ← 출처: **실측 24,995 / 24,995 «전부»**")
    P("Δ = 1.23%p                                   ← 출처: 150 의 우리−QQQ 격차")
    P("규칙 +30/−10                                 ← 출처: 커밋 `41db459d`")
    P("1단계 문턱: Ⓐ−① < Δ 면 «닫는다»               ← 출처: 사전등록 GD★")
    P("점유율은 «재구성» 값                          ← 출처: 159·160 에서 «라벨» 붙임")
    P("")
    P("⚠️ **출처가 «빈» 가정 — «하나»:**")
    P("   ⛔ 「Ⓐ(천장)는 «클» 것」 ← **두뇌 세션이 «출처 없는 머릿속 그림»이라 «스스로» 표시**")
    P("      (137 의 +5.41%p 는 «순서 «전체»»의 천장이고 이 판은 «종가 강도 «하나»»라 **«다른 축»**)")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    ev, cr, n_miss, n_bad = [], {}, 0, 0
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
            # ── GH★ 전수 날짜 관문 — «항등식»이라 문턱이 «필요 없다» ──────────
            if p["d"][0] != p["entry_date"]:
                n_bad += 1
            hi_, lo_, cl_ = p["h"][0], p["l"][0], p["c"][0]
            k = (t["scan_date"], t["code"], t["pattern"])
            if hi_ is None or lo_ is None or cl_ is None or hi_ <= lo_:
                n_miss += 1
                cr[k] = None
            else:
                cr[k] = (cl_ - lo_) / (hi_ - lo_)
            ev.append(t)

    P("")
    P("## 🚨 관문 GH★ — **전수 «날짜» 관문**(「몇 개 중 몇 개」가 «아니라» «전부»)")
    P("")
    P("```")
    P("Ⓐ 가 쓴 바의 날짜가 **진입일과 «같은가»** — 거래 **%s** 개 «전수»" % format(len(ev), ","))
    P("어긋난 것 **%d 개**  →  **%s**"
      % (n_bad, "✅ **통과**" if n_bad == 0 else "🚨 **멈춘다 — 하나라도 어긋나면 «안 간다»**"))
    P("★ «상관»과 달리 **«못 새어 나간다»** — 통계가 아니라 **«사실»**이다")
    P("🚨 그리고 Ⓐ 는 **«일부러»** 진입일 바를 쓴다 — **그게 «천장»의 정의**다(룩어헤드가 «목적»)")
    P("")
    P("`cr` 결측(high == low) **%d 개** (%.2f%%) — 규약대로 **«무작위 순서»**로 둔다"
      % (n_miss, 100.0 * n_miss / max(len(ev), 1)))
    vals = [v for v in cr.values() if v is not None]
    vals.sort()
    P("`cr` 분포 — P10 **%.3f** · 중앙 **%.3f** · P90 **%.3f**"
      % (vals[int(len(vals) * .1)], st.median(vals), vals[int(len(vals) * .9)]))
    P("```", flush=True)
    if n_bad:
        return 3

    def ofn(sign):
        def f(seed, t):
            v = cr.get((t["scan_date"], t["code"], t["pattern"]))
            return ((2.0 if v is None else sign * v), ok0(seed, t))
        return f

    ARMS = {"①현행(무작위 순서)": None,
            "Ⓐ «천장» — 종가 «강한» 것부터": ofn(-1),
            "Ⓐ′ «바닥» — 종가 «약한» 것부터": ofn(+1)}

    span = (r102._ord(D1) - r102._ord(D0)) or 1
    rd = {(t["scan_date"], t["code"], t["pattern"]):
          (t["entry_date"], t["masks"][()]["resolve_date"] or t["entry_date"]) for t in ev}

    def occupancy(x):
        tot_ = 0
        for f in x["fill_log"]:
            if f[1] != "pilot":
                continue
            v = rd.get(f[0])
            if v:
                tot_ += max(0, r102._ord(v[1]) - r102._ord(v[0]))
        return 100.0 * tot_ / (r91.SLOTS * span)

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out, occ = {}, {}
    for nm, fn in ARMS.items():
        key = "%s|n%d" % (nm, n_seed)
        if key in cache:
            out[nm] = [tuple(a) for a in cache[key]]
            occ[nm] = cache.get(key + "|occ")
            P("  ♻️ %s — 갈무리" % nm, flush=True)
            continue
        with r91.r41.Cost(*r91.COST):
            rs = [r91.sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                  reserve=False, fill_rule="truncate", cash_rule="per_slot",
                                  order_fn=fn) for s in range(n_seed)]
        out[nm] = [acc.account(x) for x in rs]
        occ[nm] = st.median([occupancy(x) for x in rs])
        cache[key] = [list(a) for a in out[nm]]
        cache[key + "|occ"] = occ[nm]
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        P("  %s — 중앙 %.0f만 · 매수 %.0f · 점유 %.1f%%"
          % (nm, st.median([a[0] for a in out[nm]]),
             st.median([a[3] for a in out[nm]]), occ[nm]), flush=True)

    P("")
    P("=" * 104)
    P("## 1. 팔 셋 — **아무도 «안» 뺐다. 담는 «순서»만 다르다**")
    P("=" * 104)
    P("")
    P("| 팔 | 세후 총액(중앙) | 연 환산 | «세전» 낙폭 | 매수 | **자리-일 점유** |")
    P("|---|---:|---:|---:|---:|---:|")
    for nm in ARMS:
        v = out[nm]
        m = st.median([a[0] for a in v])
        P("| **%s** | %.0f만 | **%+.2f%%** | %+.1f%% | %.0f | **%.1f%%** |"
          % (nm, m, acc.cagr(m, YRS), st.median([a[1] for a in v]),
             st.median([a[3] for a in v]), occ[nm]))
    P("")
    b0 = out["①현행(무작위 순서)"]
    nb, ob = st.median([a[3] for a in b0]), occ["①현행(무작위 순서)"]
    P("```")
    P("**GC★** 순위 팔의 매수 «수»·«점유»가 ① 과 «거의 같은가»")
    for nm in ARMS:
        P("   %-30s 매수 **%.0f** (%+.1f%%)  ·  점유 **%.1f%%** (%+.1f%%p)"
          % (nm, st.median([a[3] for a in out[nm]]),
             100.0 * (st.median([a[3] for a in out[nm]]) / nb - 1),
             occ[nm], occ[nm] - ob))
    P("🚨 어긋나면 **«순위만»의 효과가 «아니다»** — 160 에서 「순서를 바꾸면 «몇 건»은 바뀌나")
    P("   «자본이 나가 있는 시간»은 «안» 바뀐다」를 봤다")
    P("```")
    P("")
    P("=" * 104)
    P("## 2. ⛔ **GD★ · GF★ — 1단계 판정**")
    P("=" * 104)
    P("")

    def pair(a):
        d = [acc.cagr(out[a][i][0], YRS) - acc.cagr(b0[i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, sd, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("| 비교 | 연 차이 | SD | **95% CI** | 효과/SD |")
    P("|---|---:|---:|---|---:|")
    res = {}
    for nm in ("Ⓐ «천장» — 종가 «강한» 것부터", "Ⓐ′ «바닥» — 종가 «약한» 것부터"):
        mu, sd, lo, hi = pair(nm)
        res[nm] = (mu, sd, lo, hi)
        P("| %s − ① | **%+.3f%%p** | %.3f | **[%+.3f, %+.3f]** | %.2f |"
          % (nm, mu, sd, lo, hi, abs(mu) / sd if sd else float("inf")))
    P("")
    am, _as, alo, ahi = res["Ⓐ «천장» — 종가 «강한» 것부터"]
    bm, _bs, blo, bhi = res["Ⓐ′ «바닥» — 종가 «약한» 것부터"]
    P("```")
    P("**GF★ — 문턱을 «양쪽»에 건다**(예상이 어느 부호든 «통과» 가능해야 한다)")
    P("")
    P("🚨 **사전등록 표에 «구멍»이 있었다 — 내가 «메웠다»:**")
    P("   표는 「≥+Δ」 · 「≤−Δ」 · **「그 사이 = 못 가린다」** 셋뿐이었다.")
    P("   그런데 **「그 사이」에 «두 경우»가 있다** — **CI 가 0 을 «물면» 「못 가린다」**,")
    P("   **CI 가 0 을 «배제»하면 «효과는 «진짜»인데 «작다»»**. **다른 문장**이다")
    P("   ⇒ 아래 판정은 **그 둘을 «갈라»** 적는다")
    if am >= DELTA and alo > 0:
        va = "✅ **「값을 한다」 — 2단계(Ⓑ·Ⓒ)로 «간다»**"
    elif am <= -DELTA and ahi < 0:
        va = "⛔ **「«반대»가 맞다」**"
    elif alo > 0:
        va = ("⚠️ **「방향은 맞으나 «결론을 바꿀 크기»가 아니다」**"
              " — 🚨 **CI 가 0 을 «배제»하므로 「못 가린다」가 «아니다»**")
    elif ahi < 0:
        va = "⚠️ **「«반대» 방향이나 «결론을 바꿀 크기»가 아니다」**"
    else:
        va = "🚨 **「못 가린다」**(「같다」가 «아니다»)"
    P("**Ⓐ − ①** = **%+.3f%%p**  [%+.3f, %+.3f]  ·  Δ = ±%.2f%%p  →  %s"
      % (am, alo, ahi, DELTA, va))
    P("**Ⓐ′ − ①** = **%+.3f%%p** [%+.3f, %+.3f]  (음성 대조 — «반대 방향»이 «양수»면 FD 를 «무효»로)"
      % (bm, blo, bhi))
    P("")
    P("**GD★ — 1단계 문턱: Ⓐ−① 이 +%.2f%%p «미만»이면 Ⓑ·Ⓒ 를 «안» 돌리고 «닫는다»" % DELTA)
    if am < DELTA:
        P("   ⇒ 🔴 **%+.3f%%p < +%.2f%%p  →  «여기서 닫는다». Ⓑ·Ⓒ 를 «안» 돌린다**" % (am, DELTA))
        P("")
        P("   ## ★★ **그리고 이게 «제일 값진» 결과다:**")
        P("   ## **「미래를 «조금 아는» 축(진입일 종가)조차 «천장»이 %+.2f%%p 다.**" % am)
        P("   ## **  «집행 방식을 바꿔도» 그 이상은 «못 얻는다»」**")
        P("   ⇒ ⛔ 「장중에 사람이 붙어 종가를 보고 사자」의 **«값어치»가 여기서 «위로» 막힌다**")
    else:
        P("   ⇒ ✅ **%+.3f%%p >= +%.2f%%p  →  2단계(Ⓑ 순위 번안 · Ⓒ 청산 번안)로 «간다»**" % (am, DELTA))
    P("```")
    P("")
    for nm in res:
        P("```")
        P("%s — 효과/씨앗SD" % nm)
        for ln in gates.p_informative(res[nm][0], res[nm][1], n=n_seed)[1]:
            P("   " + ln)
        P("```")
    P("")
    P("```")
    P("⛔ **못 쓸 말**")
    P("   ⛔ 「원전 ⑤ 가 «틀렸다»」 — 원전은 **«재량» 전제**다")
    P("   ⛔ 「종가를 보고 «사야» 한다」 — Ⓐ 는 **«집행 불가»**다")
    P("   ⛔ **Ⓐ 의 수를 «전략 성적»으로** — 그건 **«집행 방식의 값»**이다")
    P("   🚨 **N 조항** — 「«다른 자»를 «시도하면» N 이 «는다». 그때 «다중비교를 다시 갚는다»」")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 진입 규칙",
                     "같은 손절 −%.0f" % STOP, "같은 칸 5", "**같은 거래 집합**(아무도 «안» 뺌)"]):
        P(ln)
    P("⇒ ✅ **이 CI 는 «우리 규칙 안에서 안정적인가»이지 «시장에서 나은가»가 아니다**")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
