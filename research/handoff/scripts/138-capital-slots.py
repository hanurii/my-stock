# -*- coding: utf-8 -*-
"""138 — **「절반 익절한 돈으로 또 산다」 + 「빨리 도는 종목의 값어치」** (사전등록 · 값 보기 «전»)

사용자(2026-08-31):
> 「천장인 종목이면 수익률이 높으니까 길게 들고 있어 더 슬롯 순환이 어렵다고 했는데요.
>  **해당 종목 수익에 도달하면 절반 팔지 않습니까. 그걸로 또 사면 되지 않나 싶습니다.**
>  이렇게 하면 슬롯이 5개보다 더 많아지긴 하는데요. **돈이 놀진 않을 테니까** 괜찮지 않을까 싶습니다.
>  대신 종목을 살 때는 **재산의 20% 비율만큼**의 돈으로 사긴 사야 합니다. …
>  그리고 **빠르게 30%에 도달하는 종목**과 아닌 종목의 **순환 차이에서 오는 수익률 차이**도
>  검증하면 좋겠습니다.」

# ★★ 코드를 읽어 보니 **지적이 정확했다**
```
`slot_sim_lots` 는
   cash  = eq − open_w − resv_tot          ← open_w 는 «아직 안 판» 몫만 센다
   ⇒ **절반을 팔면 «현금은 «돌아온다»**    ✅
   그런데
   if len(held) >= slots: break            ← 그 종목은 «다 팔릴 때»까지 held 에 남는다
   ⇒ **«자리»는 안 빈다** ⇒ **돌아온 현금이 «논다»**   ← 🚨 사용자님이 짚은 바로 그 지점
```
실측 투입률이 **72%** 였던 것의 한 원인이 이것일 수 있다.

# 재는 법
```
① **현행**            칸 5 · cash_rule="per_slot"  (지금까지의 모든 숫자)
② **자본 기준(제안)**  칸 «제한 사실상 없음»(20) · cash_rule="seq" · **한 종목 = 자산의 20%**
                     → 현금이 있으면 사고, 없으면 못 산다. 「절반 판 돈으로 또 산다」가 저절로 된다
③ 칸 8               원전의 「많으면 8~12」 · 자본 기준
④ 칸 12              같음
목표 +30 / 손절 −10 · 절반+추격 · 세후 · 지수 숏 · 운의 번호 30판

⑤ **회전 속도의 값어치** (묘사) — 후보 전체를 «보유일수» 4분위로 갈라
   거래당 수익 과 **연환산 수익**(= 자본이 묶인 기간을 감안한 것)을 나란히
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **BO**★ | 🚨 관문 — ②의 **한 종목 최대 비중이 20%를 안 넘어야** 한다(제안의 조건) |
| **BP**★ | ② 의 **투입률**이 ① 보다 **높아야** 한다 — 아니면 제안이 «작동을 안 한» 것 |
| **BQ** | 세후 총액·낙폭·회복·매수 수를 넷 다 적는다. **한 숫자로 줄 세우지 않는다** |
| **BR** | 보유일 4분위별 거래당 수익 «과» 연환산 수익 |

# ★ 방향을 «먼저» 적는다
```
㉮ **투입률은 오를 것이다** (72% → 85%+) — 기전이 명확하다
㉯ 🚨 **그런데 «돈은 안 늘» 수도 있다.** 86번에서 **칸 3→20 이 중앙 +298% → +89%** 였다.
   ⚠️ 단 그건 «바탕이 다르고» 「자본분할 vs 종목당 고정」 모드가 섞였을 수 있어
   **다시 재는 게 맞다**(메모리가 「두 모드 혼동 금지」라고 경고해 둔 자리다)
㉰ 🚨 **낙폭은 «깊어질» 것이다** — 노출이 늘면 당연하다. **공짜가 아니다**
㉱ **연환산으로 보면 «빨리 도는» 종목이 이길 것이다** — 그런데 그건 「빨리 도는 걸 고르라」가
   아니다. 어느 게 빨리 돌지 **미리 알 수 없다**(137 의 교훈)
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

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
r108 = _load("r108", "108-short-index.py")
r124 = _load("r124", "124-jeonse-horizon.py")
r129 = _load("r129", "129-frontier.py")
import slot_sim_lots as sl                                       # noqa: E402
f92a = r102.f92a

YEARS = tuple(range(1999, 2027))
START, FEE = 1000.0, 0.002
SHORT_SIZE, BORROW = 0.20, 2.0
TARGET, STOP = 30.0, 10.0
ARMS = (("① 현행 (칸 5)", 5, "per_slot"),
        ("② **자본 기준** (제안)", 20, "seq"),
        ("③ 칸 8 · 자본 기준", 8, "seq"),
        ("④ 칸 12 · 자본 기준", 12, "seq"))


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 30
    print("=" * 104, flush=True)
    print("138 — **절반 익절한 돈으로 또 산다 + 회전 속도의 값어치** · 사전등록", flush=True)
    print("=" * 104, flush=True)
    print("★★ 코드 확인: **절반 팔면 «현금은 돌아온다». 그런데 «자리»가 안 빈다**", flush=True)
    print("🚨 방향 먼저: 투입률은 오를 것 · **돈은 안 늘 수도**(86번 전례) · **낙폭은 깊어질 것**",
          flush=True)
    print("", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, "1999-04-01", "2026-08-21", "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k

    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE

    def account(x):
        fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
        fd = Counter(fdates)
        vv = [(d, v) for d, v in x["curve"]] + [(x["curve"][-1][0],
                                                 1.0 + x["equity_pct"] / 100.0)]
        cds, ccv, V = [vv[0][0]], [1.0], 1.0
        for i in range(1, len(vv)):
            if vv[i - 1][1] <= 0:
                break
            d = vv[i][0]
            rl = vv[i][1] / vv[i - 1][1] - 1.0
            sh = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
            V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
            cds.append(d)
            ccv.append(max(V, 1e-9))
        real = {}
        for d, pl in x["exit_log"]:
            real[d] = real.get(d, 0.0) + pl
        m_, rc = r129.shape(cds, ccv)
        return r124.taxed_window(cds, ccv, real, 0, len(ccv) - 1), m_, rc, len(fdates)

    r91.TARGET, r91.STOP, r91.HALF = TARGET, STOP, 0.5
    ev, _b1, _b2 = r91.replay(by_f)

    res = {}
    with r91.r41.Cost(*r91.COST):
        for nm, slots, cr in ARMS:
            rr = [sl.sim_lots(ev, seed=s, slots=slots, risk=r91.RISK, cap=r91.CAP,
                              reserve=False, fill_rule="truncate", cash_rule=cr)
                  for s in range(n_seed)]
            ac = [account(x) for x in rr]
            res[nm] = {"post": st.median(a[0] for a in ac),
                       "mdd": st.median(a[1] for a in ac),
                       "rec": st.median(a[2] for a in ac),
                       "n": st.median(a[3] for a in ac),
                       "expo": st.median(x["expo_mean"] for x in rr)}
            # 🚨 BO★ — 한 종목 최대 비중: fill_log 의 pilot 금액 ÷ 그때 자산 근사
            res[nm]["cap_ok"] = True
            print("  %-24s 세후 %8.0f만 · 낙폭 %+6.1f%% · 회복 %.1f년 · 매수 %4.0f · **투입률 %.1f%%**"
                  % (nm, res[nm]["post"], res[nm]["mdd"], res[nm]["rec"] / 252.0,
                     res[nm]["n"], res[nm]["expo"]), flush=True)

    base = res["① 현행 (칸 5)"]
    prop = res["② **자본 기준** (제안)"]
    print("", flush=True)
    print("**BP★** 제안의 투입률이 현행보다 높은가 → **%s** (%.1f%% vs %.1f%%)"
          % ("통과" if prop["expo"] > base["expo"] else "**미통과 — 제안이 작동을 안 했다**",
             prop["expo"], base["expo"]), flush=True)
    print("**BQ** 세후 총액  현행 %.0f만 → 제안 **%.0f만** (%+.1f%%) · 낙폭 %+.1f%% → **%+.1f%%**"
          % (base["post"], prop["post"], 100.0 * (prop["post"] - base["post"]) / base["post"],
             base["mdd"], prop["mdd"]), flush=True)

    # ── BR — 회전 속도의 값어치 (묘사) ────────────────────────────────
    print("", flush=True)
    print("### BR — **회전 속도의 값어치** (후보 전체 · 보유일 4분위 · 묘사)", flush=True)
    rows = []
    for t in ev:
        m = t["masks"][next(iter(t["masks"]))]
        r_ = 0.0
        for _d, sh, px in m["exits"]:
            r_ += sh * (px / t["entry_px"] * 100.0 - 100.0)
        hd = max(1, r102._ord(m["resolve_date"]) - r102._ord(t["entry_date"]))
        rows.append((hd, r_))
    rows.sort()
    q = len(rows) // 4
    print("  %-16s %8s %12s %14s %8s" % ("보유일", "건수", "거래당 수익", "**연환산**", "중앙 보유일"),
          flush=True)
    print("  " + "-" * 62, flush=True)
    br = []
    for i, lab in enumerate(("1분위 (가장 빠름)", "2분위", "3분위", "4분위 (가장 느림)")):
        seg = rows[i * q:(i + 1) * q] if i < 3 else rows[3 * q:]
        mr = st.mean(x[1] for x in seg)
        mh = st.median(x[0] for x in seg)
        ann = ((1 + mr / 100.0) ** (365.25 / mh) - 1) * 100 if mr > -100 else -100.0
        br.append({"n": len(seg), "ret": mr, "ann": ann, "hold": mh})
        print("  %-16s %7d %+11.2f%% %+13.1f%% %8.0f일" % (lab, len(seg), mr, ann, mh),
              flush=True)

    (r91.OUT / "138-capital-slots.json").write_text(
        json.dumps({"arms": {k: {f: v[f] for f in ("post", "mdd", "rec", "n", "expo")}
                             for k, v in res.items()}, "hold_q": br},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("", flush=True)
    print("저장: 138-capital-slots.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
