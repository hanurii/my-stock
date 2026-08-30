# -*- coding: utf-8 -*-
"""117 — **「쓸 수 있다」고 나온 세 조각을 «같이» 켠다** (사전등록 · 값 보기 «전»)

지금까지 하나씩만 봤다. **완전 조합 8칸**으로 «같이» 켠다.

# 세 조각
```
① 성장 둔화 필터   103 의 최선 칸 — 「1분기·이익매출이 «꺾인» 회사는 안 산다 · 자료 없으면 그냥 산다」
                   확인: 「떨어진 무리」가 「남긴 무리」보다 −0.804%p · **0 배제** (103b)
② 연패 축소        115 — 「3연패→½ · 5연패→¼」
                   확인: 낙폭 −45.2 → −30.3% · **동전 격자의 5배**(X★·Z★ 통과, Y★ 미통과)
③ 지수 숏          108 — 「SPY 가 200일선 아래면 계좌의 20% 를 숏」(차입 연 2%)
                   확인: 무작위 숏보다 +1.02%p · 단 «안 하는 것»보다는 +0.21%p 뿐
```
🚨 **①③ 의 숫자와 ② 의 숫자가 «전부 우리» 것이다.** 원전은 «방향»만 준다.

# 🚨 방향을 «먼저» 적는다
```
㉮ 낙폭은 «크게» 줄 것이다 — ② 가 혼자서 −45.2 → −30.3 을 했다
㉯ 수익은 바탕과 «비슷하거나 조금 아래»일 것이다 — ① 이 조금 올리고 ② 가 조금 깎는다
㉰ 🚨 **A★(지수를 이긴다)는 못 넘을 것으로 본다** —
   2002~2017 에 **+3.88%p** 가 필요한데 셋을 합쳐도 그만큼 안 나올 것으로 본다
㉱ 🚨 **가산적이지 «않을» 것이다** — ① 이 매수를 줄이고 ② 가 크기를 줄이면 «겹친다»
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **A**★ | 전부 켠 판이 **세 구간 모두** SPY 연평균을 이긴다 |
| **B**★ | 전부 켠 판의 **수익÷낙폭**이 **네 구간 모두** 바탕보다 크다 |
| **C** | 가산성 — 세 조각의 «몫»의 합이 전체와 맞는가 (서술 · 문턱 없음) |
| **D** | 8칸을 «전부» 적고 투입율을 같이 찍는다 |

**A★·B★ 를 둘 다** 넘어야 「셋을 합치면 값을 한다」다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim_lots as sl                                        # noqa: E402
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
_t = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_t)
_t.loader.exec_module(r102)
_v = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_v)
_v.loader.exec_module(r103)
_w = _u.spec_from_file_location("r108", HERE / "108-short-index.py")
r108 = _u.module_from_spec(_w)
_w.loader.exec_module(r108)
r41, f92a = r91.r41, r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
WIN = (("전체", "1999-04-01", "2026-08-21", 27.4),
       ("닷컴", "1999-04-01", "2001-12-31", 2.75),
       ("2002~2017", "2002-01-01", "2017-08-31", 15.66),
       ("2018~2026", "2017-09-01", "2026-08-21", 8.96))
SPYC = {"전체": 8.60, "닷컴": -3.29, "2002~2017": 7.04, "2018~2026": 15.27}
SHORT_SIZE, BORROW = 0.20, 2.0        # 🚨 우리가 정한 값 (108)


def f_streak(recent, seed, t):
    """② 3연패→½ · 5연패→¼."""
    s = 0
    for w in reversed(recent):
        if w:
            break
        s += 1
    return 0.25 if s >= 5 else (0.5 if s >= 3 else 1.0)


def run(ev, fn, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot",
                            size_fn=fn, recent_n=20) for s in range(n_seed)]


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 100
    print("=" * 112, flush=True)
    print("117 — **세 조각을 «같이» 켠다** · 완전 조합 8칸 · 100판", flush=True)
    print("=" * 112, flush=True)
    print("🚨 값 보기 «전» 예상: 낙폭은 크게 줄고 수익은 바탕과 비슷 ·", flush=True)
    print("   **A★(지수를 이긴다)는 못 넘을 것** · **가산적이지 «않을» 것**\n", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    # ── ① 성장 둔화 필터 ────────────────────────────────────────────
    by_f = {}
    n_drop = 0
    for y in sorted(by2):
        keep = []
        for p in by2[y]:
            rec = fund.get(p["code"])
            arq = (rec or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is False:
                n_drop += 1
                continue
            keep.append(p)
        by_f[y] = keep
    ev_base, _x, _y = r91.replay(by2)
    ev_filt, _x, _y = r91.replay(by_f)
    print("① 성장 둔화 필터 — 매수 %s → **%s** (%s건 뺌)\n"
          % ("{:,}".format(len(ev_base)), "{:,}".format(len(ev_filt)),
             "{:,}".format(len(ev_base) - len(ev_filt))), flush=True)

    # ── ③ 숏 준비 ───────────────────────────────────────────────────
    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}

    print("  %-14s %s" % ("칸 (①②③)", "구간별 [연평균 · 낙폭 · 수익÷낙폭 · 투입율]"), flush=True)
    print("  " + "-" * 96, flush=True)
    res = {}
    cache = {}
    for f1 in (0, 1):
        for f2 in (0, 1):
            ev_src = ev_filt if f1 else ev_base
            key = (f1, f2)
            if key not in cache:
                cache[key] = {}
                for lab, a0, b0, yrs in WIN:
                    e = [t for t in ev_src if a0 <= t["entry_date"] <= b0]
                    cache[key][lab] = run(e, f_streak if f2 else None, n_seed)
            for f3 in (0, 1):
                nm = "%s%s%s" % ("①" if f1 else "·", "②" if f2 else "·", "③" if f3 else "·")
                cells, rec = [], {}
                for lab, a0, b0, yrs in WIN:
                    rs = cache[key][lab]
                    outs = []
                    for x in rs:
                        if f3:
                            o = r108.overlay(x["curve"], x["equity_pct"], None, spy_ret, on,
                                             SHORT_SIZE, BORROW, a0, b0)
                        else:
                            o = r108.overlay(x["curve"], x["equity_pct"], None, spy_ret, on,
                                             0.0, 0.0, a0, b0)
                        if o:
                            outs.append(o)
                    tot = sorted(o[0] for o in outs)
                    med = tot[len(tot) // 2]
                    cg = (med ** (1 / yrs) - 1) * 100
                    md = st.median(o[1] for o in outs) * 100
                    ex = st.median(x["expo_mean"] for x in rs)
                    rec[lab] = {"cagr": cg, "mdd": md, "rr": abs(cg / md) if md else 0.0,
                                "expo": ex, "beat": cg > SPYC[lab]}
                    cells.append("%s %+6.2f%%%s %5.1f%% %5.3f %3.0f%%"
                                 % (lab, cg, "✅" if cg > SPYC[lab] else "❌", md,
                                    rec[lab]["rr"], ex))
                res[nm] = rec
                print("  %-14s %s" % (nm, "  ".join(cells)), flush=True)

    # ── 판정 ─────────────────────────────────────────────────────────
    print("\n" + "=" * 112, flush=True)
    full, base = res["①②③"], res["···"]
    A = all(full[l]["beat"] for l in full if l != "전체")
    B = all(full[l]["rr"] > base[l]["rr"] for l in full)
    print("  **A★** 전부 켠 판이 «세 구간 모두» SPY 를 이기는가 → **%s**"
          % ("통과" if A else "미통과"), flush=True)
    print("        %s" % (" · ".join("%s %+.2f vs %+.2f%s" % (l, full[l]["cagr"], SPYC[l],
                                                              "✅" if full[l]["beat"] else "❌")
                                     for l, _a, _b, _y in WIN)), flush=True)
    print("  **B★** 전부 켠 판의 수익÷낙폭이 «네 구간 모두» 바탕보다 큰가 → **%s**"
          % ("통과" if B else "미통과"), flush=True)
    print("        %s" % (" · ".join("%s %.3f vs %.3f%s" % (l, full[l]["rr"], base[l]["rr"],
                                                            "✅" if full[l]["rr"] > base[l]["rr"]
                                                            else "❌")
                                     for l, _a, _b, _y in WIN)), flush=True)

    # C — 가산성
    print("\n  **C** 가산성 — 세 조각의 «몫»의 합이 전체와 맞는가", flush=True)
    for lab, _a, _b, _y in WIN:
        s1 = res["①··"][lab]["rr"] - base[lab]["rr"]
        s2 = res["·②·"][lab]["rr"] - base[lab]["rr"]
        s3 = res["··③"][lab]["rr"] - base[lab]["rr"]
        tot = full[lab]["rr"] - base[lab]["rr"]
        print("     %-10s ① %+6.3f · ② %+6.3f · ③ %+6.3f  ‖ 합 %+6.3f  vs  전체 %+6.3f"
              % (lab, s1, s2, s3, s1 + s2 + s3, tot), flush=True)

    print("\n  → **셋을 합치면 값을 하는가: %s**" % ("예" if (A and B) else "**아니오**"),
          flush=True)
    (r91.OUT / "117-combine.json").write_text(
        json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 117-combine.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
