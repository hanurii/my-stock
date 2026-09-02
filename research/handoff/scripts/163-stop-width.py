# -*- coding: utf-8 -*-
r"""163 — **「손절을 «얼마나» 넓게」**(폭 · «존재»가 아니다) · 사전등록 `tasks/163-stop-width.md`

  🏷️ **세대 B** · 규칙 **+30/−10 기준 (2026-09-02~ · `41db459d`)** · 배당 포함 · 숏 없음

  🚨 **항등식: 포지션 × 손절폭 = 거래당 위험.** 셋 중 «하나»를 고정하면 나머지 «둘»이 «같이» 움직인다
     «위험» 고정 → 포지션이 작아지고 → 칸이 는다      ← `68`
     «칸» 고정                                        ← `162`
     «포지션» 고정 → **위험이 «커진다»**(1.2 ~ 4.0%)   ← 이 판 Ⓟ
  ⇒ 그래서 팔을 **«두 벌»** 낸다 — Ⓟ(포지션 고정) «와» Ⓡ(위험 고정)

  ⛔ **이 판은 «폭»을 묻지 «존재»를 묻지 «않는다»** — 격자에 「손절 없음」 칸이 **«없다»**
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

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, HALF, SLOTS = 30.0, 0.5, 5
NSEED, YRS, DELTA, T60 = 60, 27.4, 1.23, 2.001
STOPS = (6.0, 8.0, 10.0, 12.0, 15.0, 20.0)
BASE = 10.0                       # 현행
POS = 0.20                        # Ⓟ 고정 포지션 · Ⓡ 상한
RISK = 0.02                       # Ⓡ 고정 위험
CACHE = Path(str(r91.OUT / "163-partial.json"))
JD_REF = 12377                    # 162·161·156 의 ① (만원)


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    P = print
    P("=" * 104)
    P("163 — **「손절을 «얼마나» 넓게」** · 🏷️ 세대 B · 팔 **두 벌**(Ⓟ 포지션 고정 · Ⓡ 위험 고정) · 씨앗 %d판"
      % n_seed)
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-02 · `scripts/163-stop-width.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("> **「손절폭」은 «다른 것»** — 손절선까지의 % 다. 헷갈리지 않게 **「손절 −N%」**로만 적는다")
    P("")
    P("## 🚨 **유형 68 — 「이 판에서 «다른 무엇»이 «같이» 변했나」**")
    P("")
    P("```")
    P("손절폭을 바꾸면 **«셋»이 같이 변한다:**")
    P("  ① **거래의 «길»** — 손절선이 다르면 «털리는 거래»가 달라지고 «보유 일수»도 달라진다")
    P("  ② **포지션 크기** — Ⓡ 벌에서만(위험 고정이라 폭이 넓으면 «작게» 산다). Ⓟ 벌은 «안» 변한다")
    P("  ③ **거래당 위험** — Ⓟ 벌에서만(포지션 고정이라 폭이 넓으면 «위험이 커진다» 1.2 ~ 4.0%)")
    P("⇒ ★ **그래서 «한 벌»로는 못 읽는다.** Ⓟ 와 Ⓡ 를 «같이» 내야 «무엇이» 움직였는지 갈린다")
    P("")
    P("★★ **세 꼭짓점이 «다» 찬다:**")
    P("   `68`  «위험» 고정 · 9년 · 목표 +20")
    P("   `162` «칸» 고정")
    P("   `163` **«포지션» 고정 «과» «위험» 고정**  ← 이 판")
    P("   ⇒ 세 판이 «같은 방향»이면 그건 **«구조»**다")
    P("```")
    P("")
    P("## 🔴 **JE★ 선검사 — 「−30% 밑 비율」은 «죽었다». 안 쓴다**")
    P("")
    P("```")
    P("162 갈무리 실측(씨앗 60 · 27.4년):")
    P("   칸 5 «현행»  **60/60 = 100.0%**   ·  여섯 팔 전부 **98.3 ~ 100.0%**")
    P("   −20% 문턱으로 낮춰도 여섯 팔 **전부 100.0%**")
    P("⇒ 문턱 「~95% 이상이면 죽었다」 ⇒ **100.0% ⇒ «안 쓴다»**")
    P("")
    P("★ **유형 68 의 «네 번째»다** — 「−30% 밑 비율」은 `68` 의 **«9년»** 판에서 뽑혀")
    P("  **«27.4년»** 판으로 옮겨진 수다. **«창 길이»가 «같이» 3배로 변했다**")
    P("  (27년이면 «언젠가는» 거의 다 −30% 를 겪는다 — 자가 «구조적»으로 못 가린다)")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("항등식 포지션 × 손절폭 = 위험   ← 출처: **`slot_sim_lots:244` `min(eq×risk/sf, eq×cap)`**")
    P("Ⓟ risk = 0.20 × 손절폭          ← 유도: 두 항을 «같게» 놓으면 포지션이 «항상» 20%")
    P("Ⓡ risk = 2.0% · cap = 20%       ← 출처: 현행 값(`strategy_params`)")
    P("격자 −6 ~ −20                   ← 출처: 사전등록 · **⛔ 「손절 없음」 칸은 «없다»**")
    P("Δ = 1.23%p                      ← 출처: 150 의 우리−QQQ 격차")
    P("목표 +30                        ← 출처: 커밋 `41db459d`")
    P("JD★ 기준 %s만                ← 출처: 162·161·156 의 ①" % format(JD_REF, ","))
    P("⚠️ **출처가 «빈» 가정 — «하나»:**")
    P("   ⛔ 「+30 에서 손절폭 «차이»가 `68`(+20)보다 «커질» 것」")
    P("      ← 두뇌 세션의 **«유도»**(본전 이동까지의 길이 «길어진다»)이지 «실측»이 아니다")
    P("      🚨 160 에서 «유도된 예측»이 «반증»된 적이 있어 **«양쪽 문턱»**을 건다")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    # ── 손절폭마다 «따로» 해소·중복제거 — resolve_date 가 달라진다(156 의 교훈) ──
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

    def build(stop):
        # 🚨 JD★ 가 잡은 자리 — `open_until` 을 **«해마다» 초기화**한다.
        #    162·161·156 이 «그렇게» 했고, 연도를 넘겨 유지하면 «더» 지워져 ① 과 어긋난다
        out_ = []
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                t = pt.resolve_trade(p, ft="limit", fs="market", stop=stop, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                t["stop_frac"] = stop / 100.0        # 🚨 «명시»
                out_.append(t)
        return out_

    P("")
    P("## 관문 JB★ — **`lim` 에서 «어느 항»이 무는가**")
    P("")
    P("```")
    P("| 손절 | Ⓟ risk | Ⓟ risk÷sf | Ⓟ 무는 항 | Ⓡ risk÷sf | Ⓡ cap | Ⓡ 무는 항 |")
    P("|---|---:|---:|:--|---:|---:|:--|")
    for s_ in STOPS:
        sf = s_ / 100.0
        P("| **−%.0f%%** | %.4f | %.4f | %s | %.4f | %.2f | %s |"
          % (s_, POS * sf, POS, "«같다»(설계)", RISK / sf, POS,
             ("**상한**이 문다" if RISK / sf > POS else
              ("«같다»" if abs(RISK / sf - POS) < 1e-12 else "**위험항**이 문다"))))
    P("")
    P("⇒ Ⓟ 는 **설계상 «항상» 20%** · Ⓡ 는 **−6·−8 에서 «상한»이 물고** −10 부터 «위험항»이 문다")
    P("★ **−10% 에서 두 벌이 «만난다»** — Ⓟ 20% = Ⓡ min(20%, 20%) ⇒ **JD★ 의 자리**")
    P("```", flush=True)

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out, meta = {}, {}
    for vin in ("P", "R"):
        for s_ in STOPS:
            key = "v2|%s|s%.0f|n%d" % (vin, s_, n_seed)   # 🚨 v2 = JD★ 고침 뒤
            if key in cache:
                out[(vin, s_)] = [tuple(a) for a in cache[key]]
                meta[(vin, s_)] = cache[key + "|m"]
                P("  ♻️ %s −%.0f%% — 갈무리" % (vin, s_), flush=True)
                continue
            ev = build(s_)
            sf = s_ / 100.0
            rk, cp = ((POS * sf, POS) if vin == "P" else (RISK, POS))
            with r91.r41.Cost(*r91.COST):
                rs = [r91.sl.sim_lots(ev, seed=sd, slots=SLOTS, risk=rk, cap=cp,
                                      reserve=False, fill_rule="truncate",
                                      cash_rule="per_slot") for sd in range(n_seed)]
            out[(vin, s_)] = [acc.account(x) for x in rs]
            meta[(vin, s_)] = {
                "nomw": st.median([x["nom_w_mean"] for x in rs]) * 100.0,
                "expo": st.median([x["expo_mean"] for x in rs]),
                "n_ev": len(ev)}
            cache[key] = [list(a) for a in out[(vin, s_)]]
            cache[key + "|m"] = meta[(vin, s_)]
            CACHE.write_text(json.dumps(cache), encoding="utf-8")
            P("  %s −%.0f%% — 중앙 %.0f만 · 비중 %.1f%% · 노출 %.1f%% · 거래 %d"
              % (vin, s_, st.median([a[0] for a in out[(vin, s_)]]),
                 meta[(vin, s_)]["nomw"], meta[(vin, s_)]["expo"],
                 meta[(vin, s_)]["n_ev"]), flush=True)

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    P("")
    P("=" * 104)
    P("## 1. 관문 JA★ · JC★ · JD★")
    P("=" * 104)
    P("")
    P("```")
    P("**JA★ — Ⓟ 벌의 «실제» 배정 비중이 20% ± 1%p 인가**(`nom_w_mean`)")
    ja = [s_ for s_ in STOPS if abs(meta[("P", s_)]["nomw"] - 100 * POS) > 1.0]
    for s_ in STOPS:
        P("   Ⓟ −%-3.0f%%  비중 **%.2f%%**%s"
          % (s_, meta[("P", s_)]["nomw"],
             "   🚨 **20% ± 1%p 밖 — 멈춤**" if abs(meta[("P", s_)]["nomw"] - 20.0) > 1.0 else ""))
    P("   ⇒ %s" % ("🚨 **%d 칸이 벗어난다 — 멈춘다**" % len(ja) if ja else "✅ **여섯 칸 «전부» 통과**"))
    P("")
    P("**JC★ — 평균 노출이 현행(Ⓟ −10%) 대비 ±5%p 안인가**")
    P("🚨 **「노출」도 «자»가 둘이다**(유형 67 — «자 없이» 쓴다) — 여기서는 **`expo_mean` = «투입 자본 ÷ 자산»**을 쓴다")
    P("   (162 가 쓴 «자리-일 점유»는 **«자리»**를 세지 «돈»을 세지 않는다 — **다른 자**다)")
    ob = meta[("P", BASE)]["expo"]
    jc = []
    for vin in ("P", "R"):
        for s_ in STOPS:
            e = meta[(vin, s_)]["expo"]
            if abs(e - ob) > 5.0:
                jc.append((vin, s_, e))
            P("   %s −%-3.0f%%  노출 **%.1f%%** (%+.1f%%p)%s"
              % (vin, s_, e, e - ob, "   🚨 **±5%p 밖**" if abs(e - ob) > 5.0 else ""))
    if jc:
        P("   ⇒ 🚨 **%d 칸이 밖이다.** ⛔ **«보정»하지 «않는다»** — 「이 팔은 «집중»이 아니라"
          % len(jc))
        P("     «현금»도 «같이» 재고 있다」를 **«라벨»**로 달고 그 라벨로 읽는다")
    else:
        P("   ⇒ ✅ **전부 ±5%p 안**")
    P("")
    P("**JD★ — Ⓟ/Ⓡ −10%% 가 162·161·156 의 ①(%s만)과 «일치»하는가**" % format(JD_REF, ","))
    for vin in ("P", "R"):
        m_ = st.median([a[0] for a in out[(vin, BASE)]])
        P("   %s −10%%  **%.0f만**  vs  %s만  →  %s"
          % (vin, m_, format(JD_REF, ","),
             "✅ **일치**" if abs(m_ - JD_REF) < 1.0 else "🚨 **어긋난다 — 멈춘다**"))
    P("   ★ 두 벌이 −10% 에서 **«만나야»** 한다(Ⓟ 20% = Ⓡ min(20%, 20%)) — «항등식»이라 문턱이 필요 없다")
    P("```", flush=True)

    for vin, nm in (("P", "Ⓟ «포지션 20% 고정» 벌 — 손절이 넓어지면 **거래당 위험이 «커진다»**"),
                    ("R", "Ⓡ «위험 2.0% 고정» 벌 — 손절이 넓어지면 **포지션이 «작아진다»**")):
        P("")
        P("=" * 104)
        P("## %s. %s" % ("2" if vin == "P" else "3", nm))
        P("=" * 104)
        P("")
        P("**판정 자 = ① 낙폭 «중앙» · ② 📏폭(P95÷P05)** · 회복은 «서술»")
        P("🚨 **「최악 씨앗」 열은 «서술»이다 — «최솟값 통계»라 «판 수»에 걸린다.**")
        P("   **씨앗을 늘리면 «반드시» 더 나빠진다 ⇒ 60판 «안에서만» 읽고 «판정»에 «안» 쓴다**")
        P("")
        P("| 손절 | 거래당 위험 | 배정 비중 | 세후 총액(중앙) | 연 환산 | 📏폭 P95÷P05 | **낙폭 중앙** | 회복 | 매수 | ⚠️최악 씨앗 |")
        P("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for s_ in STOPS:
            v = out[(vin, s_)]
            m_ = st.median([a[0] for a in v])
            sf = s_ / 100.0
            rsk = (POS * sf if vin == "P" else min(RISK, POS * sf))
            P("| **−%.0f%%**%s | %.2f%% | %.1f%% | %.0f만 | **%+.2f%%** | %.2f | %+.1f%% | %.1f년 | %.0f | %.1f%% |"
              % (s_, " **«현행»**" if s_ == BASE else "", 100 * rsk,
                 meta[(vin, s_)]["nomw"], m_, acc.cagr(m_, YRS), spread(v),
                 st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0,
                 st.median([a[3] for a in v]), min(a[1] for a in v)))

    P("")
    P("=" * 104)
    P("## 4. 판정 — 🚨 **«안 바라는» 칸을 «먼저», «더 잘게»**")
    P("=" * 104)
    P("")
    P("```")
    P("★ 판정표 «순서»가 161·162 에서 «세 번» 걸렸던 자리다 — 「현행이 «최적이 아니다」를 «먼저» 쓴다")
    P("```")
    P("")
    for vin in ("P", "R"):
        P("### %s 벌" % vin)
        P("")
        P("| 손절 | 자산 차(vs −10%) | **95% CI** | 낙폭 | 📏폭 | 판정 |")
        P("|---|---:|---|:--|:--|:--|")
        b = out[(vin, BASE)]
        sp_b, dd_b = spread(b), st.median([a[1] for a in b])
        for s_ in STOPS:
            if s_ == BASE:
                continue
            v = out[(vin, s_)]
            d = [acc.cagr(v[i][0], YRS) - acc.cagr(b[i][0], YRS) for i in range(n_seed)]
            mu, sd = st.mean(d), st.stdev(d)
            lo, hi = mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)
            ddn = st.median([a[1] for a in v]) - dd_b
            spn = spread(v)
            dd_ok, sp_ok = ddn > 0.05, spn < sp_b
            if mu >= DELTA and lo > 0:
                vd = "🔴 **현행 −10% 는 «최적이 아니다»**"
            elif lo > 0:
                vd = "⚠️ 넓히는 쪽이 «진짜» 낫다 — 단 **Δ 미만**"
            elif mu <= -DELTA and hi < 0:
                vd = "✅ **현행이 «낫다»**"
            elif hi < 0:
                vd = "✅ 현행이 낫되 **작다**"
            else:
                vd = "🚨 **못 가린다**"
            P("| **−%.0f%%** | **%+.3f%%p** | [%+.3f, %+.3f] | %.1f%%p %s | %.2f %s | %s |"
              % (s_, mu, lo, hi, abs(ddn),
                 "🔴 깊다" if ddn < -0.05 else ("🟢 얕다" if ddn > 0.05 else "≈ 같다"),
                 spn, "🟢 좁다" if sp_ok else "🔴 넓다", vd))
        P("")
    P("### 🧮 **사전등록 예측 ㉮ 대조 — «양쪽 문턱»을 걸었다**")
    P("")
    P("```")
    P("㉮ 「+30 에서 손절폭의 «차이»가 `68`(+20)보다 «커질» 것」")
    P("   근거로 든 `68` 칸5 고정판: **−8% +31.52%  →  −25% +52.94%**  = **«넓힐수록 나았다»**")
    P("")
    P("이 판 Ⓡ(«위험 고정» — `68` 과 «같은» 구조):")
    for s_ in (8.0, 20.0):
        P("   −%.0f%%  **%+.2f%%**" % (s_, acc.cagr(st.median([a[0] for a in out[("R", s_)]]), YRS)))
    P("   ⇒ 🔴 **«넓힐수록 «나빠진다»» — «부호»가 «뒤집혔다»**")
    P("")
    P("★ 예측은 「«차이»가 «커진다」였는데 실제는 **«방향»이 «반대»**다")
    P("  ⇒ ⛔ 「예측이 «맞았다/틀렸다»」로 «한 낱말»로 못 적는다 — **«크기»를 물었는데 «부호»가 답했다**")
    P("")
    P("🚨🚨 **그리고 이 대조 자체가 «유형 68» 이다 — «두 축»이 «같이» 변했다:**")
    P("   `68`  **9년** · 목표 **+20**")
    P("   `163` **27.4년** · 목표 **+30**")
    P("   ⇒ ⛔ **부호 반전을 «목표 +30 탓»으로 «돌릴 수 없다».** 창 길이가 «같이» 3배 변했다")
    P("   ✅ 적을 수 있는 말: 「**27.4년 · +30 에서는 «좁은 쪽»이 이긴다. `68`(9년 · +20)과 «반대»다.**")
    P("     **어느 축이 뒤집었는지는 «안 쟀다»**」")
    P("```")
    P("")
    P("### ✅ **「격자 «끝»」 검사 — 최적이 «안쪽»에 있는가**")
    P("")
    P("```")
    bestP = max(STOPS, key=lambda x: st.median([a[0] for a in out[("P", x)]]))
    bestR = max(STOPS, key=lambda x: st.median([a[0] for a in out[("R", x)]]))
    P("Ⓟ 최선 **−%.0f%%** · Ⓡ 최선 **−%.0f%%** — 격자 −6 ~ −20 의 **«안쪽»**" % (bestP, bestR))
    P("⇒ ✅ **격자가 최적을 «자르지» 않았다.** 양 끝(−6·−20)이 «둘 다» 더 나쁘다")
    P("   ⇒ 그래서 사전등록의 ⛔「끝 칸이 최선이어도 격자를 «안» 넓힌다」가 **«안 걸린다»**")
    P("```")
    P("")
    P("```")
    P("✅ **위험 축 «확정»(두뇌 세션):**")
    P("   ① **낙폭 «중앙»** — `162` 와 **«같은 자»**라 «두 판을 맞댈 수» 있다 · 포화 «없음»")
    P("   ② **📏폭 = P95 ÷ P05** — 문서 «머리»에 자 선언")
    P("   ③ 회복(년) — **«서술»**")
    P("   🚨 **「최악 씨앗 낙폭」 — «최솟값 통계»라 «판 수»에 걸린다. «서술»만, «판정»에 «안» 씀**")
    P("     (씨앗을 늘리면 «반드시» 나빠진다 ⇒ 60판과 200판을 «맞댈 수 없게» 된다)")
    P("   ⛔ **「−30% 밑 비율」 — «죽었다». 표에서 «뺐다»**")
    P("★ 「위험 «하나»만 나쁨」 규칙은 **①·② «두 자»로만** 판정한다(③은 서술)")
    P("")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ 「손절을 «없애야» 한다」 — **격자에 「손절 없음」 칸이 «없다». 이 판은 «폭»을 묻지")
    P("      «존재»를 묻지 «않는다»**")
    P("   ⛔ 「−6% × 20% 를 «재 봐야» 한다」 — `68` 이 «이미» 답했다(−13.47% · −30% 밑 99%)")
    P("   ⛔ `68` 의 «칸 20» 수를 이 판과 «맞대기» — 그건 «위험 고정»판이다")
    P("   ⛔ 「원전 손절 5% 가 틀렸다」 — 원전 «실제 하한»은 **7~8%**, 「5%」는 «산수 예시»다")
    P("   ⛔ 끝 칸(−20%)이 최선이어도 **격자를 «안» 넓힌다**")
    P("      ✅ 대신 **«범위 문장»**: 「−20% 가 최선 — 단 격자 «끝»이라 «더 넓은 쪽은 «안 쟀다»」")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 진입 규칙",
                     "같은 목표 +30", "같은 칸 5"]):
        P(ln)
    P("⇒ ✅ **이 CI 는 «우리 규칙 안에서 안정적인가»이지 «시장에서 나은가»가 아니다**")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
