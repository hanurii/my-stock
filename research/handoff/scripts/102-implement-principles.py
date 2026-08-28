# -*- coding: utf-8 -*-
"""102 — **이 목록의 원칙을 구현한다** (100번 단계 B · 사전등록 `tasks/102`, 커밋 2ca71230)

사용자 지시 1번 · 사용자 선택 ㉠(공매도 제외) · 검증 세션 ①(「최대 충실」이라 부르지 말고 «분모»를 적어라)

# 새로 켜는 셋 — 사전등록에 못 박은 그대로
```
㉠ code33   이익·매출·이익률 «셋»이 **3분기 연속 가속**. 후보 단계에서 거른다
            🚨 92 의 `code33` 은 **다른 정의**였다(EPS·매출 «둘»이 +30% 인 분기가 2연속).
               등록한 쪽(3분기 가속)으로 간다. **둘은 같은 이름의 다른 규칙**이다
㉡ earn     예측 발표일 = **작년 같은 분기 공시일 + 365일**(올해 실제일을 쓰면 룩어헤드)
            그 **5거래일 전**에 평가이익이 **+10% 미만**이면 판다
            🚨 두 숫자는 «우리가» 정했다 — 원전은 「이익 쿠션이 두텁지 않으면」이라고만 한다
            구현: 경로의 일봉 배열을 그날에서 «자른다» → 그날 «종가»에 판 것과 같다
㉢ working  그날 «이전»에 이미 청산된 후보 거래 중 **최근 60거래일** 청산분의 **합산 손익 > 0**
            이면 그날 매수 허용. 아니면 **신규 매수만** 안 한다(보유는 유지)
            🚨 15번(「내 최근 4~5건」)과 **합치지 않는다** — 합치면 현금에서 영영 못 나온다
```

# 관문
```
⑭ code33 이 `asof` 로 공시일 «미만»만 보는가            ⑮ 예측 발표일이 «작년 것»만 쓰는가
⑯ working 이 그날 «이전에 청산된» 것만 보는가            ⑰ **셋 다 끈 판이 91 정본과 소수점까지 같은가**
⑱ 판마다 «진입 수»를 찍는다                              ⑲ 문턱마다 «재는 줄»이 있는가
```
"""
from __future__ import annotations

import bisect
import datetime as _dt
import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                          # noqa: E402

_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
_s2 = _u.spec_from_file_location("f92a", HERE / "92a-fundamentals-index.py")
f92a = _u.module_from_spec(_s2)
_s2.loader.exec_module(f92a)

OUT = r91.OUT
D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
BLOCKS = (("닷컴 1999~2001", "1999-04-01", "2001-12-31"),
          ("2002~2017", "2002-01-01", "2017-08-31"),
          ("2018~2026", "2017-09-01", "2026-08-21"))
SPY_CAGR = {"닷컴 1999~2001": -3.29, "2002~2017": 7.04, "2018~2026": 15.27}
YRS = {"닷컴 1999~2001": 2.75, "2002~2017": 15.66, "2018~2026": 8.96}
A_PASS = 55.0

STALE_MAX = 180            # 92 와 같은 신선도 상한
EARN_LEAD = 5              # ㉡ — 발표 예측일 «몇 거래일 전»에 파나  🚨 우리가 정했다
EARN_CUSH = 10.0           # ㉡ — 평가이익이 이 «미만»이면 판다 (%)  🚨 우리가 정했다
WORK_WIN = 60              # ㉢ — 최근 «몇 거래일» 청산분을 보나     🚨 우리가 정했다
NAN = float("nan")


def _nan(v):
    return v is None or v != v


def _ord(d):
    return _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


# ═════════════════════════════════════════════════════════════════════════
# ㉠ code33 — 셋이 «3분기 연속 가속»
# ═════════════════════════════════════════════════════════════════════════
def _yoy(cur, prev):
    if _nan(cur) or _nan(prev) or prev is None or prev <= 0:
        return NAN
    return cur / prev - 1.0


def code33_ok(arq, j, ix, nq=3):
    """`arq[j]` 가 진입 직전 공시일 때, **셋이 3분기 연속 가속**인가.

    가속(q) = 「q 의 전년동기대비 성장률」 > 「q−1 의 전년동기대비 성장률」
    3분기 연속 = j, j−1, j−2 가 «모두» 가속
    → 필요한 과거 분기: j−2 의 전년동기(j−6) 와 그 직전(j−7) → **j >= 7**
    이익률은 성장률이 아니라 «수준»이므로 «확대»로 본다 (m[q] > m[q-4]).
    """
    if j < 4 + nq:
        return None                                     # 판정 불가 — 「거짓」과 갈라 센다
    def g(k, f):
        return arq[k][ix[f]] if 0 <= k < len(arq) else None
    for q in range(j, j - nq, -1):
        e_now, e_prev = _yoy(g(q, "eps"), g(q - 4, "eps")), _yoy(g(q - 1, "eps"), g(q - 5, "eps"))
        r_now, r_prev = _yoy(g(q, "revenue"), g(q - 4, "revenue")), \
            _yoy(g(q - 1, "revenue"), g(q - 5, "revenue"))
        m_now, m_base = g(q, "netmargin"), g(q - 4, "netmargin")
        if _nan(e_now) or _nan(e_prev) or _nan(r_now) or _nan(r_prev) \
                or _nan(m_now) or _nan(m_base):
            return None                                 # 판정 불가
        if not (e_now > e_prev and r_now > r_prev and m_now > m_base):
            return False
    return True


# ═════════════════════════════════════════════════════════════════════════
# ㉡ 실적 발표 «전» 매도 — 경로를 «자른다»
# ═════════════════════════════════════════════════════════════════════════
def predict_earn_dates(arq, entry_date):
    """진입일 «전»에 이미 나온 공시들만 써서, 앞으로의 발표일을 «예측»한다.

    🚨 관문 ⑮ — **올해 실제 공시일을 안 본다.** 「작년 같은 분기 + 365일」만 쓴다.
    """
    o_e = _ord(entry_date)
    out = []
    for r in arq:
        if r[0] >= entry_date:                          # 진입일 이후 공시는 «안 본다»
            break
        p = _ord(r[0]) + 365
        if p > o_e:
            out.append(p)
    return sorted(out)


def apply_earn_exit(p, arq):
    """예측 발표일 EARN_LEAD 거래일 «전»에 이익이 EARN_CUSH 미만이면 그날 자른다."""
    preds = predict_earn_dates(arq, p["entry_date"])
    if not preds:
        return p, False
    ds, cs = p["d"], p["c"]
    epx = p.get("entry_price") or p.get("entry_px")
    if not epx:
        return p, False
    ords = [_ord(x) for x in ds]
    for pd_ in preds:
        i = bisect.bisect_left(ords, pd_) - EARN_LEAD   # 예측일 «5거래일 전»
        if i <= 0:
            continue
        if i >= len(ds):
            break
        if (cs[i] / epx - 1.0) * 100.0 < EARN_CUSH:
            q = dict(p)
            for k in ("d", "o", "h", "l", "c"):
                q[k] = p[k][:i + 1]                     # 그날 «종가»에 판 것과 같다
            return q, True
        # 쿠션이 두터우면 «안 팔고» 다음 발표를 본다
    return p, False


# ═════════════════════════════════════════════════════════════════════════
# ㉢ 「돌파가 «먹히는가»」 — 날짜별 허용/불허
# ═════════════════════════════════════════════════════════════════════════
def working_map(by, all_dates):
    """그날 «이전»에 청산된 후보 거래의 최근 WORK_WIN 거래일 합산 손익 > 0 인가.

    🚨 관문 ⑯ — 청산일이 그날 «미만»인 것만 쓴다. 진행 중인 것은 «안 본다».
    """
    ev = []
    for y in sorted(by):
        for q in by[y]:
            t = pt.resolve_trade(q, ft="limit", fs="market", stop=r91.STOP,
                                 target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
            m = t["masks"][()]
            rd = m["resolve_date"] or q["entry_date"]
            epx = t["entry_px"]
            if not epx or not m["exits"]:
                continue
            # 실현 손익(%) — 청산 조각을 «비중»으로 평균한다
            w = sum(x[1] for x in m["exits"]) or 1.0
            px = sum(x[1] * x[2] for x in m["exits"]) / w
            ev.append((rd, (px / epx - 1.0) * 100.0))
    ev.sort()
    rds = [e[0] for e in ev]
    ok = {}
    for n, d in enumerate(all_dates):                   # 🚨 index() 를 쓰면 O(n^2) 이다
        j = bisect.bisect_left(rds, d)                  # 청산일 < d 인 것까지
        k = bisect.bisect_left(rds, all_dates[max(0, n - WORK_WIN)])
        s = sum(e[1] for e in ev[k:j])
        ok[d] = (j > k) and (s > 0)
    return ok


# ═════════════════════════════════════════════════════════════════════════
def build_variants(by2, fund, ixf):
    """일곱 판의 경로 묶음을 만든다. 🚨 «진입 전»에 거른다(91 §load_ladder 경고)."""
    # 🚨 `fields` 에 'date' 가 **이미 들어 있다**. +1 로 밀면 한 칸씩 어긋나
    #    eps 자리에서 epsdil 을, revenue 자리에서 netmargin 을 읽는다.
    #    **자릿수 검산이 잡았다** — revenue 가 0.268 로 나왔다(매출일 수 없는 값).
    ix = {f: i for i, f in enumerate(ixf)}
    assert ixf[0] == "date" and ix["eps"] == 3, ixf
    stats = defaultdict(Counter)

    # ── ㉠ code33 통과 집합 ────────────────────────────────────────────
    keep33 = set()
    for y in sorted(by2):
        for p in by2[y]:
            rec = fund.get(p["code"])
            key = (y, p["code"], p["entry_date"], p["pattern"])
            if not rec or not rec.get("ARQ"):
                stats["code33"]["실적표 없음"] += 1
                continue
            arq = rec["ARQ"]
            r = f92a.asof(arq, p["entry_date"])
            if r is None:
                stats["code33"]["진입 전 공시 없음"] += 1
                continue
            j = arq.index(r)
            if _ord(p["entry_date"]) - _ord(r[0]) > STALE_MAX:
                stats["code33"]["공시가 묵음"] += 1
                continue
            for nq in (1, 2, 3):
                vv = code33_ok(arq, j, ix, nq)
                stats["code33 진단"]["%d분기 %s" % (nq, {None: "불가", True: "통과",
                                                       False: "떨어짐"}[vv])] += 1
            v = code33_ok(arq, j, ix)
            if v is None:
                stats["code33"]["과거 분기 부족"] += 1
            elif v:
                stats["code33"]["통과"] += 1
                keep33.add(key)
            else:
                stats["code33"]["떨어짐"] += 1

    # ── ㉢ 날짜 허용 표 ────────────────────────────────────────────────
    all_dates = sorted({p["entry_date"] for y in by2 for p in by2[y]})
    wmap = working_map({y: list(v) for y, v in by2.items()}, all_dates)
    stats["working"]["허용된 날"] = sum(1 for d in all_dates if wmap.get(d))
    stats["working"]["막힌 날"] = sum(1 for d in all_dates if not wmap.get(d))

    def make(use33, useE, useW):
        out = {}
        for y in sorted(by2):
            lst = []
            for p in by2[y]:
                key = (y, p["code"], p["entry_date"], p["pattern"])
                if use33 and key not in keep33:
                    continue
                if useW and not wmap.get(p["entry_date"], True):
                    continue
                if useE:
                    rec = fund.get(p["code"])
                    arq = (rec or {}).get("ARQ") or []
                    if arq:
                        p, cut = apply_earn_exit(p, arq)
                        if cut and not (use33 or useW):
                            stats["earn"]["잘림(㉡만 켠 판 기준)"] += 1
                lst.append(p)
            out[y] = lst
        return out

    V = {}
    V["바탕(91 정본)"] = make(0, 0, 0)
    V["㉠ code33 만"] = make(1, 0, 0)
    V["㉡ 실적전매도 만"] = make(0, 1, 0)
    V["㉢ 돌파먹힘 만"] = make(0, 0, 1)
    V["★ 셋 전부"] = make(1, 1, 1)
    V["전부−㉠"] = make(0, 1, 1)
    V["전부−㉡"] = make(1, 0, 1)
    V["전부−㉢"] = make(1, 1, 0)
    return V, stats


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else r91.N_SEED
    print("=" * 112, flush=True)
    print("102 — 이 목록의 원칙을 구현한다 · 사전등록 tasks/102 (2ca71230) · seed %d" % n_seed,
          flush=True)
    print("=" * 112, flush=True)
    print("🚨 23개 중 **14개** 구현. 못 한 9개의 사유는 사전등록 §1 에 있다.", flush=True)
    print("🚨 새로 켜는 셋 중 «둘»에 우리가 정한 숫자가 있다 (5거래일·+10%·60거래일)\n", flush=True)

    (_b0, _b1, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2
    fund, ixf = f92a.load()
    print("경로(사다리 ②) %s · 실적표 종목 %s\n"
          % ("{:,}".format(sum(len(v) for v in by2.values())), "{:,}".format(len(fund))),
          flush=True)

    V, stats = build_variants(by2, fund, ixf)
    for k in ("code33", "earn", "working"):
        if stats[k]:
            print("  [%s] %s" % (k, " · ".join("%s %s" % (a, "{:,}".format(b))
                                               for a, b in stats[k].most_common())), flush=True)
    print("", flush=True)

    # ── 관문 ⑰ — 셋 다 끈 판이 91 정본과 «소수점까지» 같은가 ──────────
    ev_b, _x, _y = r91.replay(V["바탕(91 정본)"])
    ev_ref, _x, _y = r91.replay(by2)
    same = len(ev_b) == len(ev_ref)
    print("관문 ⑰ 셋 다 끈 판이 91 정본과 같은가 → **%s** (진입 %d vs %d)"
          % ("통과" if same else "🚨 미통과 — 멈춘다", len(ev_b), len(ev_ref)), flush=True)
    if not same:
        return 3

    res = {}
    print("\n  %-18s %7s  %s" % ("판", "진입", "창별 [자산중앙 · 연환산 · 짝차 · 이기는판]"),
          flush=True)
    print("  " + "-" * 104, flush=True)
    base = {}
    for name, by in V.items():
        ev, _b, _t = r91.replay(by)
        cells = []
        res[name] = {"n_entry": len(ev), "win": {}}
        for lab, a, b in BLOCKS:
            e = [t for t in ev if a <= t["entry_date"] <= b]
            rs = r91.sim(e, n_seed)
            eq = [x["equity_pct"] for x in rs]
            med = st.median(eq)
            cg = ((1 + med / 100.0) ** (1 / YRS[lab]) - 1) * 100
            if name.startswith("바탕"):
                base[lab] = eq
                dif, w, mde = 0.0, 50.0, 0.0
            else:
                d = sorted(x - y for x, y in zip(eq, base[lab]))
                dif = st.median(d)
                w = 100.0 * sum(1 for v in d if v > 0) / n_seed
                mde = 2.8 * st.pstdev(d) / (n_seed ** 0.5)
            res[name]["win"][lab] = {"med": med, "cagr": cg, "dif": dif, "win": w,
                                     "mde": mde, "spy": SPY_CAGR[lab],
                                     "beat_spy": cg > SPY_CAGR[lab],
                                     "mdd": st.median(x["mdd_pct"] for x in rs),
                                     "expo": st.median(x["expo_mean"] for x in rs)}
            cells.append("%s %+.2f%%%s %+5.1f%%p %4.1f%%"
                         % (lab.split()[0], cg, "✅" if cg > SPY_CAGR[lab] else "❌", dif, w))
        print("  %-18s %7s  %s" % (name, "{:,}".format(len(ev)), "  ".join(cells)), flush=True)

    # ── 판정 ─────────────────────────────────────────────────────────
    print("\n" + "=" * 112, flush=True)
    a = res["★ 셋 전부"]["win"]
    h = all(a[l]["beat_spy"] for l in a)
    i_ = a["2002~2017"]["win"] > A_PASS
    print("  **H★** 셋 전부가 «세 창 모두» SPY 를 이기는가 → %s  (%s)"
          % ("통과" if h else "**미통과**",
             " · ".join("%s %+.2f vs SPY %+.2f" % (l.split()[0], a[l]["cagr"], a[l]["spy"])
                        for l in a)), flush=True)
    print("  **I★** 2002~2017 에서 바탕보다 이기는 판 > %.0f%% → %s  (%.1f%% · 짝차 %+.2f%%p · MDE %.1f)"
          % (A_PASS, "통과" if i_ else "**미통과**", a["2002~2017"]["win"],
             a["2002~2017"]["dif"], a["2002~2017"]["mde"]), flush=True)
    print("  → **1번의 답: %s**" % ("예" if (h and i_) else "**아니오**"), flush=True)

    # ── J — 원칙마다 «몫». 🚨 셋을 «전부» 적는다. 「가장 큰 것」을 안 고른다 ──
    print("\n  ★ J — 원칙마다 «몫» (전부 켠 판 − 그것만 뺀 판) · **셋을 전부 적는다**", flush=True)
    tot = {}
    for lab, _a, _b in BLOCKS:
        parts = []
        s = 0.0
        for nm, key in (("㉠ code33", "전부−㉠"), ("㉡ 실적전매도", "전부−㉡"),
                        ("㉢ 돌파먹힘", "전부−㉢")):
            v = a[lab]["dif"] - res[key]["win"][lab]["dif"]
            s += v
            parts.append("%s %+6.2f%%p" % (nm, v))
        tot[lab] = (s, a[lab]["dif"])
        print("     %-16s %s   ‖ 합 %+7.2f%%p  vs  전체 %+7.2f%%p"
              % (lab, " · ".join(parts), s, a[lab]["dif"]), flush=True)
    print("     (합 ≠ 전체 이면 원칙들이 «서로 얽혀» 있다는 뜻 — 가산성 점검)", flush=True)

    (OUT / "102-implement-principles.json").write_text(
        json.dumps({"res": res, "stats": {k: dict(v) for k, v in stats.items()},
                    "H": h, "I": i_, "n_seed": n_seed},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 102-implement-principles.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
