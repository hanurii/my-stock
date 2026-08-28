# -*- coding: utf-8 -*-
"""98 — 이동창 승률을 **판(seed)별로** 다시 잰다.

왜 다시 재나
------------
두뇌 세션이 이동창 수익을 **「해마다의 «중앙값»을 곱해서」** 만들었다.
**중앙값은 곱셈에 대해 닫히지 않는다** — `results/93-by-year.md` §4-1 에
이미 적혀 있는 한계다(곱하면 ×12.56, 실제 총수익 중앙은 ×11.65).

여기서는 **판 하나하나에서** 그 창의 수익을 내고, **판별로** S&P500 과 견주고,
**그 비율**을 본다. 순서가 다르다:

```
옛것   해마다 중앙 → 곱한다 → 창 하나에 숫자 하나 → 이긴 창을 센다
이것   판마다 곡선 → 판마다 창 수익 → 판마다 이겼나 → 그 «비율»
```

🚨 **판정 아님 · 서술이다.** 91 의 규칙을 한 글자도 안 바꾸고 산수만 다시 한다.
🚨 **이동창은 겹친다.** 3년 창 26개는 «26개의 독립 관측»이 아니다.
   창 수를 유효표본으로 읽으면 안 된다. 그래서 창 수 세기와 «판별 비율»을 따로 찍는다.
🚨 **양 끝 해는 토막이다** — 1999는 4월부터, 2026은 8/21까지. 우리도 SPY도 같은 규약.

관문
----
① 판별 연도수익의 «중앙»이 `93-by-year.json` 의 연도표와 같은가 (같은 자료·같은 규칙)
② 판별 총수익의 중앙이 93 의 `totals["2 조합"]["total"]` 과 같은가
③ 진입 수가 93 의 `n_entry` 와 같은가 (`_lean_load` 가 91 과 같은 거르기인가)
④ **옛 방식을 여기서 재현해** 두뇌 세션이 보고한 이긴 창 수(11/26 · 10/24 · 3/19)가 나오는가
   → 나와야 「무엇이 달라졌나」를 갈라 말할 수 있다. 안 나오면 «맞추지 말고 왜인지부터».

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/98-window-perseed.py
      (--quick 12판 · --reuse 저장된 판별 연도수익 재사용)
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _lean_load as ll                                       # noqa: E402

_s = _u.spec_from_file_location("r93", HERE / "93-by-year.py")
r93 = _u.module_from_spec(_s)
_s.loader.exec_module(r93)
r91 = r93.r91

OUT = ROOT / ".cache" / "bt5y" / "out"
YEARS = r93.YEARS
D0, D1 = r93.D0, r93.D1
LENS = (3, 5, 10)
CACHE = OUT / "98-window-levels.json"
# 두뇌 세션이 보고한 옛 방식 결과 — 관문 ④ 의 기대값
CLAIM = {3: (11, 26), 5: (10, 24), 10: (3, 19)}


def levels(yr):
    """연도수익률(%) → **누적 수준**. `lv[y]` = 그 해 «끝»의 배수. 시작 1.0."""
    lv, v = {}, 1.0
    for y in YEARS:
        v *= (1.0 + yr[y] / 100.0)
        lv[y] = v
    return lv


def base(lv, y0):
    """창 시작 «직전» 수준."""
    return 1.0 if y0 == YEARS[0] else lv[y0 - 1]


def win_ret(lv, y0, L):
    return (lv[y0 + L - 1] / base(lv, y0) - 1.0) * 100.0


def starts(L):
    return [y for y in YEARS if y + L - 1 <= YEARS[-1]]


def build(n_seed):
    """판별 연도수익률을 만든다. → (yr_all, tot_all, n_entry)"""
    by2, _cand, n_all = ll.load_combo(YEARS, D0, D1)
    missing = [y for y in YEARS if y not in by2]
    if missing:
        raise SystemExit("🚨 경로 파일 없음 %s" % missing)
    ev, blk, trunc = r91.replay(by2)
    del by2
    print("   경로 %d → 조합 진입 %d (막힘 %d · 잘림 %d)" % (n_all, len(ev), blk, trunc),
          flush=True)
    rs = r91.sim(ev, n_seed)
    yr_all = [r93.year_returns(x["curve"], x["equity_pct"]) for x in rs]
    tot_all = [x["equity_pct"] for x in rs]
    n_entry = len(ev)
    del rs, ev
    return yr_all, tot_all, n_entry


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else r91.N_SEED
    reuse = ("--reuse" in sys.argv) and CACHE.exists()

    print("=" * 100, flush=True)
    print("98 — 이동창 승률을 **판별로** 다시 잰다 (서술 · 판정 아님)", flush=True)
    print("=" * 100, flush=True)

    if reuse:
        pk = json.loads(CACHE.read_text(encoding="utf-8"))
        yr_all = [{y: row[i] for i, y in enumerate(YEARS)} for row in pk["year_returns"]]
        tot_all = pk["total"]
        n_entry = pk["n_entry"]
        n_seed = len(yr_all)
        print("저장분 재사용: %s (판 %d)" % (CACHE.name, n_seed), flush=True)
    else:
        print("규칙 91 그대로 · 사다리 ②(조합) · seed %d · ext 미사용" % n_seed, flush=True)
        yr_all, tot_all, n_entry = build(n_seed)
        CACHE.write_text(json.dumps(
            {"n_seed": n_seed, "n_entry": n_entry, "years": [str(y) for y in YEARS],
             "year_returns": [[yr[y] for y in YEARS] for yr in yr_all],
             "total": tot_all}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        print("저장: %s" % CACHE.name, flush=True)

    spy_yr = r93.bench_year("SPY")
    spy_lv = levels({y: (spy_yr[y] if spy_yr[y] == spy_yr[y] else 0.0) for y in YEARS})
    n_nan = sum(1 for y in YEARS if spy_yr[y] != spy_yr[y])

    med_yr = {y: st.median(d[y] for d in yr_all) for y in YEARS}
    old_lv = levels(med_yr)                       # ← 옛 방식: 연도 중앙을 곱한다
    seed_lv = [levels(d) for d in yr_all]         # ← 이것: 판마다 곱한다

    # ── 관문 ────────────────────────────────────────────────────────────
    print("", flush=True)
    print("관문", flush=True)
    ok = True
    ref = json.loads((OUT / "93-by-year.json").read_text(encoding="utf-8"))
    if quick:
        print("   ①②③ --quick 은 판 수가 달라 93 과 못 댄다. **건너뜀**", flush=True)
    else:
        bad = [(y, med_yr[y], ref["years"][str(y)]["2 조합"]) for y in YEARS
               if abs(med_yr[y] - ref["years"][str(y)]["2 조합"]) > 1e-9]
        ok &= not bad
        print("   ① 연도별 중앙 vs 93 표 — 어긋난 해 **%d** / %d %s"
              % (len(bad), len(YEARS), "" if not bad else str(bad[:3])), flush=True)
        d_tot = st.median(tot_all) - ref["totals"]["2 조합"]["total"]
        ok &= abs(d_tot) <= 1e-9
        print("   ② 총수익 중앙 %+.6f%% (93 과 차 %+.2e)" % (st.median(tot_all), d_tot),
              flush=True)
        d_n = n_entry - ref["totals"]["2 조합"]["n_entry"]
        ok &= (d_n == 0)
        print("   ③ 진입 수 %d (93 과 차 %d)" % (n_entry, d_n), flush=True)
    print("   ⋯ SPY 연도수익 결측 %d 해" % n_nan, flush=True)

    # ── 관문 ④ — 옛 방식 재현 ───────────────────────────────────────────
    print("", flush=True)
    print("   ④ **옛 방식(연도 중앙을 곱한다)을 여기서 재현** — 두뇌 세션 보고와 대는가",
          flush=True)
    old_cnt = {}
    for L in LENS:
        ss = starts(L)
        w = sum(1 for y0 in ss if win_ret(old_lv, y0, L) > win_ret(spy_lv, y0, L))
        old_cnt[L] = (w, len(ss))
        e = CLAIM[L]
        same = (w, len(ss)) == e
        ok &= same
        print("      %2d년 창 — 이긴 창 %2d / %2d   (보고 %d/%d) %s"
              % (L, w, len(ss), e[0], e[1],
                 "**일치**" if same else "🚨 **어긋남 — 맞추지 말고 왜인지부터**"),
              flush=True)
    if not ok:
        print("", flush=True)
        print("   🚨 관문 미통과. 아래 숫자는 **쓰지 마십시오**.", flush=True)

    # ── ① 판별 이기는 비율 ──────────────────────────────────────────────
    res = {}
    for L in LENS:
        ss = starts(L)
        rows = []
        for y0 in ss:
            sp = win_ret(spy_lv, y0, L)
            rr = [win_ret(lv, y0, L) for lv in seed_lv]
            frac = sum(1 for x in rr if x > sp) / len(rr)
            rows.append({"y0": y0, "y1": y0 + L - 1, "spy": sp,
                         "med": st.median(rr), "p25": sorted(rr)[len(rr) // 4],
                         "p75": sorted(rr)[3 * len(rr) // 4],
                         "old": win_ret(old_lv, y0, L), "frac": frac})
        res[L] = rows

        print("", flush=True)
        print("=" * 100, flush=True)
        print("【%d년 이동창】 창 %d개 · 판 %d개 = 판×창 %d쌍"
              % (L, len(ss), n_seed, len(ss) * n_seed), flush=True)
        print("  %-11s %11s %11s %11s %11s %8s %8s"
              % ("창", "우리 중앙", "(P25", "P75)", "S&P500", "이긴판", "옛방식"),
              flush=True)
        print("  " + "-" * 96, flush=True)
        for r in rows:
            print("  %4d~%4d   %+10.1f%% %+10.1f%% %+10.1f%% %+10.1f%% %7.1f%% %+7.1f%%"
                  % (r["y0"], r["y1"], r["med"], r["p25"], r["p75"], r["spy"],
                     100 * r["frac"], r["old"]), flush=True)
        print("  " + "-" * 96, flush=True)

        fr = [r["frac"] for r in rows]
        pooled = sum(fr) / len(fr)               # 창마다 판 수가 같으므로 평균 = 합집합 비율
        n_med = sum(1 for x in fr if x > 0.5)
        print("  ① **이기는 판 비율** — 창 평균 **%.1f%%** (= 판×창 %d쌍 중 이긴 쌍의 비율)"
              % (100 * pooled, len(ss) * n_seed), flush=True)
        print("  ② 그 비율의 «분포» — 최소 %.1f%% · P25 %.1f%% · 중앙 %.1f%% · P75 %.1f%% "
              "· 최대 %.1f%%"
              % (100 * min(fr), 100 * sorted(fr)[len(fr) // 4], 100 * st.median(fr),
                 100 * sorted(fr)[3 * len(fr) // 4], 100 * max(fr)), flush=True)
        print("     0%% 인 창 %d · 100%% 인 창 %d · 그 사이 %d "
              "(← 「판이 갈리는」 창이 몇 개인가)"
              % (sum(1 for x in fr if x == 0.0), sum(1 for x in fr if x == 1.0),
                 sum(1 for x in fr if 0.0 < x < 1.0)), flush=True)
        print("  ③ **창 세기** — 중앙 판이 이긴 창 **%d / %d** vs 옛 방식 **%d / %d**"
              % (n_med, len(ss), old_cnt[L][0], old_cnt[L][1]), flush=True)
        dif = [r for r in rows if (r["med"] > r["spy"]) != (r["old"] > r["spy"])]
        print("     두 방식이 «다르게» 센 창 **%d** 개%s"
              % (len(dif), (" — " + ", ".join("%d~%d(옛 %+.0f%% vs 중앙 %+.0f%%)"
                                              % (r["y0"], r["y1"], r["old"], r["med"])
                                              for r in dif[:6])) if dif else ""),
              flush=True)
        gap = [r["old"] - r["med"] for r in rows]
        print("     옛 방식이 «부풀린» 폭 — 중앙 %+.1f%%p · 최소 %+.1f%%p · 최대 %+.1f%%p"
              % (st.median(gap), min(gap), max(gap)), flush=True)

    # ── ④ 기간이 길수록 떨어지나 ────────────────────────────────────────
    print("", flush=True)
    print("=" * 100, flush=True)
    print("④ **「창이 길수록 이길 확률이 떨어진다」가 두 셈법에서 다 서나**", flush=True)
    print("=" * 100, flush=True)
    print("  %-8s %14s %16s %14s" % ("창 길이", "이긴 창(옛)", "**이기는 판 비율**",
                                     "이긴 창(중앙)"), flush=True)
    for L in LENS:
        fr = [r["frac"] for r in res[L]]
        print("  %-8s %8d /%3d %14.1f%% %10d /%3d"
              % ("%d년" % L, old_cnt[L][0], old_cnt[L][1], 100 * sum(fr) / len(fr),
                 sum(1 for x in fr if x > 0.5), len(fr)), flush=True)
    print("", flush=True)
    print("  🚨 창은 겹친다 — 위 «창 수»는 독립 관측 수가 아니다. "
          "10년 창 19개는 27.4년 안에서 «거의 같은 구간»을 19번 다시 센 것이다.", flush=True)
    print("  🚨 양 끝 창은 토막이다 — 1999 시작 창은 4월부터, 2026 끝 창은 8/21까지.",
          flush=True)

    # ── ④′ 같은 시작해 위에서만 ─────────────────────────────────────────
    # 🚨 위 표는 «창 길이»와 «어느 해를 덮나»가 섞여 있다. 3년 창은 2024년 시작까지 있고
    #    10년 창은 2017년 시작까지뿐이다. 셋이 «다 가진» 시작해로 잘라 다시 센다.
    common = [y for y in starts(max(LENS)) if all(y in starts(L) for L in LENS)]
    print("", flush=True)
    print("④′ **같은 시작해(%d~%d · %d개) 위에서만** — 「길이」와 「덮는 해」를 가른다"
          % (common[0], common[-1], len(common)), flush=True)
    print("  %-8s %16s %14s" % ("창 길이", "**이기는 판 비율**", "이긴 창(중앙)"), flush=True)
    sub = {}
    for L in LENS:
        fr = [r["frac"] for r in res[L] if r["y0"] in common]
        sub[L] = {"frac_mean": sum(fr) / len(fr),
                  "n_win_median": sum(1 for x in fr if x > 0.5), "n_window": len(fr)}
        print("  %-8s %14.1f%% %10d /%3d"
              % ("%d년" % L, 100 * sub[L]["frac_mean"], sub[L]["n_win_median"], len(fr)),
              flush=True)
    print("  🚨 이렇게 잘라도 창은 여전히 겹친다. 「길이」축만 맞춘 것이지 "
          "독립 관측을 만든 것이 아니다.", flush=True)

    (OUT / "98-window-perseed.json").write_text(json.dumps(
        {"n_seed": n_seed, "n_entry": n_entry, "gate_ok": bool(ok),
         "windows": {str(L): res[L] for L in LENS},
         "old_count": {str(L): old_cnt[L] for L in LENS},
         "summary": {str(L): {
             "frac_mean": sum(r["frac"] for r in res[L]) / len(res[L]),
             "n_win_median": sum(1 for r in res[L] if r["frac"] > 0.5),
             "n_win_old": old_cnt[L][0], "n_window": len(res[L])} for L in LENS},
         "common_start": {str(L): sub[L] for L in LENS}},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("", flush=True)
    print("저장: 98-window-perseed.json · %s" % CACHE.name, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
