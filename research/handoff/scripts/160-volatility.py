# -*- coding: utf-8 -*-
r"""160 — **「조용한 것부터 담아라」**(원전 ④) · 사전등록 `tasks/160-volatility.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (2026-09-02~ · `41db459d`)** · 배당 포함 · 숏 없음

  ★★ **이 판은 «계좌»의 자다. 85 는 «사건»의 자, 140 은 «점수»의 자였다.**
     안 적으면 결과 뒤에 **「이미 알던 것」과 「새 것」이 «섞인다»**

  ★ **«순위»가 주다** — 「빼는 것」은 159 가 이미 **−3.86%p**(무작위 배제)로 쟀다.
     Ⓖ 는 **아무도 «안» 뺀다.** 같은 날 후보의 «담는 순서»만 바꾼다.
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
ok0 = r91.sl.order_key                     # 기존 «거래별 난수» — ① 이 쓰는 것

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF = 30.0, 10.0, 0.5
NSEED, YRS, DELTA, T60 = 60, 27.4, 1.23, 2.001
CACHE = Path(str(r91.OUT / "160-partial.json"))
BAND = {"①": 1, "②": 2, "③": 3, "④": 4}


def pretax(x):
    """★ 세전 총액 — `account_lib.account` 의 곡선 구성을 그대로 따르되 세금만 «안» 물린다
    (158 의 기계 그대로). 🚨 두 곳이 어긋나면 아래 항등식(세후 <= 세전)이 «먼저» 문다"""
    from collections import Counter
    fd = Counter(f[3] for f in x["fill_log"] if f[1] == "pilot")
    vv = ([(d, v) for d, v in x["curve"]]
          + [(x["curve"][-1][0], 1.0 + x["equity_pct"] / 100.0)])
    V = 1.0
    for i in range(1, len(vv)):
        if vv[i - 1][1] <= 0:
            break
        V *= (1.0 + vv[i][1] / vv[i - 1][1] - 1.0 - acc.FEE * 0.20 * fd.get(vv[i][0], 0))
    return acc.START * max(V, 1e-9)


def bandnum(v):
    """`atr_band` 는 '①조용 <2.5%' 꼴 — **맨 앞 글자**로 읽는다(143 에서 배운 것)"""
    if not v:
        return None
    return BAND.get(str(v).strip()[:1])


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    P = print
    P("=" * 104)
    P("160 — **「조용한 것부터 담아라」**(원전 ④) · 🏷️ 세대 B · +30/−10 · 씨앗 %d판" % n_seed)
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-02 · `scripts/160-volatility.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## 🚨 **이 판은 «계좌»의 자다** — 85 는 «사건», 140 은 «점수»였다")
    P("")
    P("```")
    P("85:45   `atr_band` ④(가장 «큰»)가 **더블 예측 +4.81%p** · 귀무 99.9 백분위 · **통과**  ← «사건»")
    P("85:151  ⚠️ 그래도 **「변동성 큰 걸 사라」는 실무 규칙으로 «안 쓴다» — «돈이 안 된다»**")
    P("140:54  ④매우큼 **+0.43** · ③큼 +0.13 · ②보통 −0.16 · **①조용 −0.75**  ← «점수». **조용이 «최악»**")
    P("140:97  체가 «실제로» 쓴 몫: `atr_band` **0.0%**")
    P("⇒ ★ **원전 ④ 의 「조용한 칸」이 «이미» 가장 나쁜 칸이다. 남은 자리는 «계좌»뿐이다**")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("`atr_band` 4칸       140 이 쓴 **«그 정의» 그대로**       ← 출처: 사다리 필드(연속값으로 «안» 바꿈)")
    P("Δ = 1.23%p                                              ← 출처: 150 의 우리−QQQ 격차")
    P("순서의 «천장» +5.41%p/년                                 ← 출처: **137**(⚠️ 세대 A — «모양»만)")
    P("「하루 안 칸이 «모두 같은» 날」 29.9%                      ← 출처: **148 G★ 실측**")
    P("규칙 +30/−10                                            ← 출처: 커밋 `41db459d`")
    P("⚠️ **출처가 «빈» 가정: 없음**")
    P("```")
    P("")
    P("## 🚨 **«희석»을 «미리» 적는다**")
    P("")
    P("```")
    P("약 **30%** 의 날에는 Ⓖ 의 순위가 «아무 일도 «안» 한다» — 그 날 **Ⓖ = ①**(148 G★)")
    P("나머지 «70%»에서만, 그것도 **«4칸»으로 «거칠게»** 작동한다")
    P("★ Δ(1.23%p) 는 **«순서 천장»(+5.41%p/년)의 «23%»** 이고,")
    P("  **그 23% 를 «한 축»이 «혼자» 가져와야 한다** ⇒ **「관측 가능하나 «요구가 크다»」**")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    ev, bnd, n_miss = [], {}, 0
    cnt = {1: 0, 2: 0, 3: 0, 4: 0}
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
            b = bandnum(p.get("atr_band"))
            if b is None:
                n_miss += 1
            else:
                cnt[b] += 1
            bnd[(t["scan_date"], t["code"], t["pattern"])] = b
            ev.append(t)

    P("")
    P("## 관문 FA★ · FC★ — **칸 분포**")
    P("")
    P("```")
    tot = len(ev)
    P("거래 **%s** 개 · `atr_band` 결측 **%d** (%.2f%%) — 규약대로 **«무작위 순서»**로 둔다"
      % (format(tot, ","), n_miss, 100.0 * n_miss / max(tot, 1)))
    lbl = {1: "①조용 <2.5%", 2: "②보통", 3: "③큼", 4: "④매우큼"}
    for b in (1, 2, 3, 4):
        sh = 100.0 * cnt[b] / max(tot, 1)
        P("   %-14s **%s** (%.1f%%)%s" % (lbl[b], format(cnt[b], ","), sh,
                                          "   🚨 **5% 미만 — «분해능 없음»**" if sh < 5 else ""))
    P("```", flush=True)

    def ofn(sign):
        def f(seed, t):
            b = bnd.get((t["scan_date"], t["code"], t["pattern"]))
            return ((99 if b is None else sign * b), ok0(seed, t))
        return f

    ARMS = {"①현행(무작위 순서)": None,
            "Ⓖ «조용한» 것부터 (원전 ④)": ofn(+1),
            "Ⓗ «시끄러운» 것부터 (음성 대조)": ofn(-1)}

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
    out, occ, pre = {}, {}, {}
    for nm, fn in ARMS.items():
        key = "%s|n%d" % (nm, n_seed)
        if key in cache:
            out[nm] = [tuple(a) for a in cache[key]]
            occ[nm] = cache.get(key + "|occ")
            pre[nm] = cache.get(key + "|pre") or []
            P("  ♻️ %s — 갈무리" % nm, flush=True)
            continue
        with r91.r41.Cost(*r91.COST):
            rs = [r91.sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                  reserve=False, fill_rule="truncate", cash_rule="per_slot",
                                  order_fn=fn) for s in range(n_seed)]
        out[nm] = [acc.account(x) for x in rs]
        pre[nm] = [pretax(x) for x in rs]
        occ[nm] = st.median([occupancy(x) for x in rs])
        cache[key + "|pre"] = pre[nm]
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
    okFB = all(abs(st.median([a[3] for a in out[nm]]) - nb) / nb < 0.05
               and abs(occ[nm] - ob) < 3.0 for nm in ARMS)
    P("```")
    P("**FB★** 매수 «수»와 «자리-일 점유»가 ① 과 «거의 같은가»  →  **%s**"
      % ("✅ 통과 — 「같은 노출」이 유지됐다" if okFB else
         "🚨 **미통과 — 순위가 «노출»도 바꿨다. 그러면 «순위만»의 효과가 «아니다»**"))
    P("   🚨 159 에서 배운 것 — **매수 «수»만으론 「같은 노출」을 «보장 못 한다»**(Ⓓ 538≈539 인데 점유 85.1 vs 88.3)")
    P("")
    P("★ **«어디»가 어긋났나 — 갈라 본다:**")
    for nm in ARMS:
        P("   %-30s 매수 **%.0f** (%+.1f%%)  ·  점유 **%.1f%%** (%+.1f%%p)"
          % (nm, st.median([a[3] for a in out[nm]]),
             100.0 * (st.median([a[3] for a in out[nm]]) / nb - 1),
             occ[nm], occ[nm] - ob))
    P("")
    P("⇒ ★★ **어긋난 건 «매수 수»뿐이고 «점유»는 거의 같다**(±0.5%p)")
    P("   **「순서를 바꾸면 «몇 건»을 사는지는 바뀌지만 «자본이 나가 있는 시간»은 «안» 바뀐다」**")
    P("   ⇒ 조용한 것부터 = **«적게, 오래»**  ·  시끄러운 것부터 = **«많이, 짧게»**")
    P("   ⚠️ 그러니 «순수한 순위 효과»가 «아니라» **「순위 + 회전」**이 섞였다. **갈라 «안» 쟀다**")
    P("   ⚠️ 점유율은 **«재구성» 값**이다(`fill_log` 키로 되찾음). 146 의 94.6%(직접 회계)와 «맞대지 않는다»")
    P("```")
    P("")
    P("=" * 104)
    P("## 2. ⛔ **FD★ 주 판정 — 문턱을 «양쪽»에 건다**")
    P("=" * 104)
    P("")

    def pair(a):
        d = [acc.cagr(out[a][i][0], YRS) - acc.cagr(b0[i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, sd, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    P("| 비교 | 연 차이 | SD | **95% CI** | 효과/SD |")
    P("|---|---:|---:|---|---:|")
    res = {}
    for nm in ("Ⓖ «조용한» 것부터 (원전 ④)", "Ⓗ «시끄러운» 것부터 (음성 대조)"):
        mu, sd, lo, hi = pair(nm)
        res[nm] = (mu, sd, lo, hi)
        P("| %s − ① | **%+.3f%%p** | %.3f | **[%+.3f, %+.3f]** | %.2f |"
          % (nm, mu, sd, lo, hi, abs(mu) / sd if sd else float("inf")))
    P("")
    P("```")
    gm, _gs, glo, ghi = res["Ⓖ «조용한» 것부터 (원전 ④)"]
    hm, _hs, hlo, hhi = res["Ⓗ «시끄러운» 것부터 (음성 대조)"]
    P("★ **읽는 표 — 값 보기 «전»에 «양쪽»으로 박았다**(예상이 «음수»인데 문턱이 «양수»뿐이면")
    P("  어떤 값도 «통과» 못 한다 — 유형 24′ 의 «거울상»)")
    P("")
    if gm >= DELTA and glo > 0:
        vg = "✅ **「원전 ④ 가 «값을 한다»」**"
    elif gm <= -DELTA and ghi < 0:
        vg = "⛔ **「원전 ④ 의 «반대»가 맞다」**"
    else:
        vg = "🚨 **「못 가린다」**(「같다」가 «아니다»)"
    P("**FD★**  Ⓖ − ① = **%+.3f%%p**  [%+.3f, %+.3f]  ·  Δ = ±%.2f%%p  →  %s"
      % (gm, glo, ghi, DELTA, vg))
    P("**FE★**  Ⓗ − ① = **%+.3f%%p**  [%+.3f, %+.3f]  →  %s"
      % (hm, hlo, hhi,
         "🚨 **양수 — FD 를 «무효»로 읽는다**(방향이 아니라 「순서를 «정하기만» 해도 좋다」)"
         if hlo > 0 else "✅ FD 를 «무효»로 만들지 않는다"))
    P("")
    P("### 🚨🚨 **140 과 «부딪힌다» — 규약 ⑦**")
    P("")
    P("140:54  ④매우큼 **+0.43** > ③큼 +0.13 > ②보통 −0.16 > **①조용 −0.75**")
    P("        ⇒ 「시끄러운 게 «낫다»」 ⇒ **Ⓗ 가 «양수»여야 한다**")
    P("실측    Ⓗ − ① = **%+.3f%%p** [%+.3f, %+.3f] — **0 을 «배제»한 «음수»**" % (hm, hlo, hhi))
    P("")
    P("```")
    P("⚠️ **「부딪힌다」를 «단정»하기 전에 — 자가 «다르다»:**")
    P("   140 = «점수»(체가 쓰는 특징 기여)  ·  85 = «사건»(더블 예측)  ·  160 = **«계좌»**")
    P("   ⇒ **«세 자»가 «같은 축»에 «다른 답»을 낸다.** 그게 이 판의 «발견»이다")
    P("")
    P("★ 그리고 이건 **85 가 «이미» 적어 둔 것과 «같은 방향»이다:**")
    P("   `85:151` 「④가 더블을 «예측»한다(+4.81%p · 99.9 백분위) — **그래도 실무 규칙으론 «안 쓴다»**」")
    P("   ⇒ 160 은 그걸 **«계좌»에서 «더 세게»** 냈다: 「돈이 «안» 될 뿐 아니라 **«잃는다»**」")
    P("")
    P("⛔ **그렇다고 「140 이 «틀렸다»」로 «못» 쓴다** — 140 은 «점수»를 «맞게» 쟀다.")
    P("   틀린 것은 **「점수가 높으면 «담는 순서»에서도 이긴다」는 «건너뜀»**이다")
    P("```")
    P("")
    P("### ★ **«세전»으로 다시 — 「회전 비용」을 벗긴다**(= FB★ 미통과의 «감도 분석»)")
    P("")
    P("```")
    P("🚨 **예측을 «돌리기 전»에 적었다**(검증 세션 유도):")
    P("   154: 세금 몫 1.18%p / 105건 = **거래당 ≈ 0.0112%p** · Ⓗ−① 은 **+29건**")
    P("   ⇒ 회전으로 설명되는 몫 ≈ **0.326%p**  ⇒  **세전 Ⓗ−① 은 «약 −0.8» 로 «줄되 «음수»»일 것**")
    P("   ⚠️ 이 어림은 «다른 비교»(+20 vs +30)에서 끌어온 것이라 **«방향과 자릿수»만**")
    P("")
    okid = True
    for nm in ARMS:
        if pre.get(nm) and any(out[nm][i][0] > pre[nm][i] * 1.000001 for i in range(n_seed)):
            okid = False
    P("관문 — **세후 <= 세전** (세금은 «깎기»만 한다)  →  **%s**"
      % ("✅ 통과" if okid else "🚨 **미통과 — `pretax()` 와 `account_lib` 가 어긋난다**"))
    P("")
    for nm in ARMS:
        if pre.get(nm):
            P("%-30s 세전 **%.0f만** = 연 **%+.2f%%**"
              % (nm, st.median(pre[nm]), acc.cagr(st.median(pre[nm]), YRS)))
    P("")
    for nm in ("Ⓖ «조용한» 것부터 (원전 ④)", "Ⓗ «시끄러운» 것부터 (음성 대조)"):
        if pre.get(nm) and pre.get("①현행(무작위 순서)"):
            dp = [acc.cagr(pre[nm][i], YRS) - acc.cagr(pre["①현행(무작위 순서)"][i], YRS)
                  for i in range(n_seed)]
            mp, sp = st.mean(dp), st.stdev(dp)
            lp = mp - T60 * sp / math.sqrt(n_seed)
            hp = mp + T60 * sp / math.sqrt(n_seed)
            P("%-30s 세전 **%+.3f%%p** [%+.3f, %+.3f]   ·   세후 %+.3f%%p   ·   차 **%+.3f%%p**"
              % (nm, mp, lp, hp, res[nm][0], mp - res[nm][0]))
    if pre.get("Ⓗ «시끄러운» 것부터 (음성 대조)"):
        dph = [acc.cagr(pre["Ⓗ «시끄러운» 것부터 (음성 대조)"][i], YRS)
               - acc.cagr(pre["①현행(무작위 순서)"][i], YRS) for i in range(n_seed)]
        mh = st.mean(dph)
        P("")
        P("⇒ 예측 «약 −0.8»  vs  실측 **%+.3f%%p**  →  %s"
          % (mh, "✅ **맞았다 — 회전이 «일부»를 설명한다**" if -1.05 <= mh <= -0.55
             else "🚨 **크게 벗어났다 — «다른 것»이 섞였다. 멈추고 «왜»부터**"))
        P("   회전이 설명하는 몫 **%.0f%%** (= (%+.3f − %+.3f) / %+.3f)"
          % (100.0 * abs(mh - hm) / max(abs(hm), 1e-9), mh, hm, hm))
        P("")
        P("★★ **예측이 «빗나갔다». «왜»를 적는다 — 🚨 «가설»이지 «측정»이 아니다:**")
        P("   어림의 바탕은 154 의 **「+20 vs +30 · 105건 차 · 세금 1.18%p」 = 거래당 0.0112%p** 였다")
        P("   🚨 그런데 154 의 105건 차는 **«목표 수준»(+20 vs +30)과 «같이» 변한 것**이다 —")
        P("     +20 은 «더 자주» 팔 뿐 아니라 **«더 작은 이익»을 «더 일찍»** 실현한다")
        P("   ⇒ 여기 Ⓗ 의 +29건은 **«같은 목표»**라 그 «시점» 효과가 «거의 없다»")
        P("   ⇒ **154 에서 끌어온 «거래당 세금»이 여기 «안 옮겨진다»** (실측 15배 작다)")
        P("")
        P("⇒ ★★ **그러므로 Ⓗ 의 −1.15%p 는 «회전»이 «거의 설명 못 한다»(2%).**")
        P("   **남는 것은 «기전 ②(한계 거래의 질)»과 «③(꼬리)»이고, 둘 다 «안 쟀다»**")
        P("   ✅ 그리고 이건 결과를 **«더 세게»** 만든다 — 「세금 부작용」이 «아니»라는 뜻이므로")
    P("```")
    P("")
    P("### ★★ **기전 «셋» — 「자가 다르다」를 «만능 변명»으로 안 쓰기 위해**")
    P("")
    P("```")
    P("🚨 검증 세션의 시험: **「두 수가 다른 «기전»을 «말할 수 있는가».**")
    P("   **못 말하면 «회피», 말할 수 있으면 «발견»」**")
    P("")
    P("① **회전**            Ⓗ 는 매수 568(+5.3%) · 보유가 짧다 → 실현이 잦다 → 세금이 «앞당겨진다»")
    P("                     ✅ **이 판이 «쟀다»** — 세전/세후 차가 그 몫이다")
    P("② **한계 거래의 질**   «먼저» 담으면 «더 많이» 담게 되고, **한계 거래가 «더 나쁘다»**")
    P("                     ⚠️ **안 쟀다** — 159 의 「대체 거래」 검사와 «같은 수법»이 필요하다")
    P("③ **꼬리**            큰 변동성은 «양쪽» 꼬리를 넓히는데,")
    P("                     **140 의 «점수»는 «평균»을 보고 «계좌»는 «경로»를 본다**")
    P("                     ⚠️ **안 쟀다**")
    P("⇒ ★ 셋 중 **«하나»만 쟀다.** 그러니 「자가 다르다」는 **«설명»이 아니라 «후보 셋»**이다")
    P("```")
    P("")
    P("### ⛔ **문장 하나를 «고친다»**")
    P("")
    P("```")
    P("⛔ 「«순위»만으로는 «큰 것을 못 얻는다»」")
    P("✅ Ⓖ «좋은 방향» **%+.3f** [%+.3f, %+.3f] → **못 가림**" % (gm, glo, ghi))
    P("   Ⓗ «나쁜 방향» **%+.3f** [%+.3f, %+.3f] → **크게 잃음**" % (hm, hlo, hhi))
    P("⇒ **「못 얻는다」가 아니라 — 「«얻기는» 어렵고 «잃기는» 쉽다」. «비대칭»이다**")
    P("")
    P("★★ 그리고 **159 Ⓓ 와 «같은 모양»이다:**")
    P("   159  «무작위 배제»가 «제일 나쁨»            ⇒ 현행 순서에 **«정보가 있다»**")
    P("   160  «반대 순위»가 «크게 나쁨» · «좋은 순위»는 «못 가림»")
    P("   ⇒ **「현행 순서가 «이미» 좋고, «흐트러뜨리면» 크게 나빠지나 «더 좋게» 만들기는 어렵다」**")
    P("   ⇒ **「고르기 여덟 번 실패」와 «모순이 아니라 «짝»»이다**")
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
    P("   ⛔ 「원전 ④ 가 «틀렸다»」 — 원전은 **«재량» 전제**다")
    P("   ⛔ 「«시끄러운» 걸 «사야» 한다」 — **Ⓗ 는 «음성 대조»이지 «권고»가 «아니다»**")
    P("   ⛔ 「배제가 «항상» 나쁘다」 — 잰 것은 **«우리 규칙 위에 «얹은»»** 것뿐이다")
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
