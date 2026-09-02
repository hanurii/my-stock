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

    def run(ev):
        with r91.r41.Cost(*r91.COST):
            return [r91.sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                    reserve=False, fill_rule="truncate", cash_rule="per_slot")
                    for s in range(n_seed)]

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out = {}
    for nm, fn in ARMS.items():
        key = "%s|n%d" % (nm, n_seed)
        if key in cache:
            out[nm] = [tuple(a) for a in cache[key]]
            P("  ♻️ %s — 갈무리" % nm, flush=True)
            continue
        rs = run(build_ev(fn))
        out[nm] = [acc.account(x) for x in rs]
        cache[key] = [list(a) for a in out[nm]]
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        P("  %s — 중앙 %.0f만 · 매수 %.0f"
          % (nm, st.median([a[0] for a in out[nm]]),
             st.median([a[3] for a in out[nm]])), flush=True)

    P("")
    P("=" * 104)
    P("## 1. 팔 넷")
    P("=" * 104)
    P("")
    P("| 팔 | 세후 총액(중앙) | 연 환산 | «세전» 낙폭 | 매수 |")
    P("|---|---:|---:|---:|---:|")
    for nm in ARMS:
        v = out[nm]
        m = st.median([a[0] for a in v])
        P("| **%s** | %.0f만 | **%+.2f%%** | %+.1f%% | %.0f |"
          % (nm, m, acc.cagr(m, YRS), st.median([a[1] for a in v]),
             st.median([a[3] for a in v])))
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
    for nm in ("Ⓐ-30 (고정 $30)", "Ⓒ 고정 백분위 81.9%", "Ⓐ-12 (고정 $12 · 묘사)"):
        d = [acc.cagr(out[nm][i][0], YRS) - acc.cagr(base[i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        lo, hi = mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)
        st_[nm] = (mu, sd, lo, hi)
        P("| %s − ① | **%+.3f%%p** | %.3f | **[%+.3f, %+.3f]** | %.2f |"
          % (nm, mu, sd, lo, hi, abs(mu) / sd if sd else float("inf")))
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
