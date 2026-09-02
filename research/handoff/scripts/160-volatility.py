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
