# -*- coding: utf-8 -*-
"""89v — **축 수정이 «충분한가».** 검증 세션. (두뇌 물음 ①)

두뇌 세션이 「제일 약하다」고 적은 자리다. 물음을 둘로 가른다:

  (가) **`fltRt` 가 분할일에 «조정된» 값인가?**  ← 여기가 전부다
       조정된 값이면  분할일 fltRt ≈ 0 인데 원시 종가는 −80% → A 축이 «옳다»
       조정 «안» 된 값이면 분할일 fltRt ≈ −80% → A 축이 **가짜 −80% 를 품는다**
       🚨 이건 「축을 맞췄나」가 아니라 **「맞춘 축이 옳은가」**다. 89 는 앞엣것만 봤다.

  (나) A 축이 «경로»의 복원 규약과 같은가?
       → **사실 같을 필요가 없다.** 89 는 이제 비율을 «A 안»에서만 만든다.
          A 가 «스스로» 옳으면 그만이다. 그래도 대조로 잰다 — 어긋나면 (가)가 의심스럽다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/89v-axis.py
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r89", HERE / "89-korea-entry-predictors.py")
r89 = _u.module_from_spec(_s)
_s.loader.exec_module(r89)


def hr(t):
    print("\n" + "=" * 98, flush=True)
    print(t, flush=True)
    print("=" * 98, flush=True)


def main() -> int:
    # 89 의 main 과 «같은 방식»으로 진입과 경로를 만든다
    import json
    by = {}
    for y in r89.YEARS:
        f = r89.SUB / ("krpath_%d.json" % y)
        by[y] = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    r89.r41.TARGET_FILL, r89.r41.STOP_FILL = "limit", "market"
    ev, _b = r89.r41.replay(by, lambda p: r89.r41.resolve_half_then_trail(
        p, r89.STOP, 20.0))
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by.values() for p in ps}
    for e in ev:
        p = pmap.get((e["scan_date"], e["code"], e.get("pattern", "")))
        if p:
            e["entry_px"] = p["entry_price"]
    print("진입 %d건 · 경로 %d개" % (len(ev), len(pmap)), flush=True)
    ser = r89.load_pdata()

    # ── (가) fltRt 가 조정값인가 ────────────────────────────────────────
    hr("(가) 🚨 **`fltRt` 가 분할일에 «조정된» 값인가** — A 축의 «옳음»이 여기 걸려 있다")
    print("  분할·병합 의심일 = |원시 종가 비율 − fltRt| > 3%p 인 날", flush=True)
    print("  그날 **fltRt 가 작으면(≈0) 조정값 → A 축 옳음**", flush=True)
    print("      **fltRt 도 크면(원시와 비슷) 미조정 → A 축이 가짜 낙폭을 품음**\n", flush=True)
    rows, big_f, small_f = [], 0, 0
    for code, x in ser.items():
        c, f = x["c"], x["f"]
        for i in range(1, len(c)):
            if c[i - 1] <= 0:
                continue
            raw = (c[i] / c[i - 1] - 1.0) * 100.0
            if abs(raw - f[i]) > 3.0:
                rows.append((code, x["d"][i], raw, f[i]))
                if abs(f[i]) > 15.0:
                    big_f += 1
                else:
                    small_f += 1
    n = len(rows)
    print("  의심일 **%d건** (종목 %d개)" % (n, len({r[0] for r in rows})), flush=True)
    if not n:
        print("  → 의심일이 없다. 이 자료에는 분할 흔적이 «없다».", flush=True)
        return 0
    print("  그중 fltRt 가 **|15%%| 이하(=조정된 것으로 보임)  %d건 (%.1f%%)**"
          % (small_f, 100.0 * small_f / n), flush=True)
    print("        fltRt 도 **|15%%| 초과(=미조정 의심)      %d건 (%.1f%%)**"
          % (big_f, 100.0 * big_f / n), flush=True)
    ext = sorted(rows, key=lambda r: abs(r[2]))[-12:]
    print("\n  원시 낙폭이 가장 큰 12건 — «그날 fltRt» 를 나란히 본다:", flush=True)
    print("  %-9s %-12s %11s %11s %s" % ("종목", "날짜", "원시 비율", "fltRt", "판정"),
          flush=True)
    for code, d, raw, fl in reversed(ext):
        v = "**미조정 🚨**" if abs(fl) > 15 else "조정됨 ✅"
        print("  %-9s %-12s %+10.2f%% %+10.2f%% %s" % (code, d, raw, fl, v), flush=True)
    # 🚨 위 |15%| 분류는 «약한 자»다 — 한국 상한가가 ±30% 라 −24% 도 «진짜 하루»일 수 있다.
    #    옳은 자: **`fltRt` 가 일일 제한(±30%)을 «넘는 날»이 있는가.**
    #    미조정이면 분할일에 fltRt 가 −80% / +4900% 같은 값이 «반드시» 나온다.
    allf = [v for x in ser.values() for v in x["f"]]
    over = [v for v in allf if abs(v) > 31.0]
    rawover = sum(1 for _c, _d, raw, _f in rows if abs(raw) > 31.0)
    print("\n  ★ **더 엄한 자** — `fltRt` 가 일일 제한 ±30%% 를 넘는 날:", flush=True)
    print("     전체 %d 값 중 **%d건 (%.4f%%)**  ·  같은 의심일의 «원시» 비율은 %d건이 넘는다"
          % (len(allf), len(over), 100.0 * len(over) / max(1, len(allf)), rawover),
          flush=True)
    if over:
        o = sorted(over, key=abs)
        print("     넘은 값 예: %s" % (["%+.1f%%" % v for v in o[-5:]],), flush=True)
    ok = len(over) == 0
    print("\n  → **%s**" % ("`fltRt` 는 «조정값»이다. A 축이 옳다 ✅" if ok else
                            "🚨 «미조정» 이 섞여 있다. A 축이 가짜 낙폭을 품는다"), flush=True)

    # ── (나) A 축 vs 경로 축 ───────────────────────────────────────────
    hr("(나) A 축의 126일 비율이 «경로»의 126일 비율과 맞나 (대조)")
    print("  🚨 «같을 필요는 없다» — 89 는 이제 비율을 A 안에서만 만든다.", flush=True)
    print("     그래도 크게 어긋나면 (가)를 의심해야 하므로 잰다.\n", flush=True)
    diff, n_cmp, bad, n_short = [], 0, [], 0
    for t in ev:
        code = t["code"]
        s = ser.get(code)
        p = pmap.get((t["scan_date"], code, t.get("pattern", "")))
        if not s or not p:
            continue
        k = bisect.bisect_left(s["d"], t["entry_date"])
        if k < 300:
            continue
        try:
            j = p["d"].index(t["entry_date"])
        except ValueError:
            continue
        # 🚨 경로는 «돌파 언저리»만 담아 126일 역사가 없다 → 겹치는 만큼만 본다
        m = min(j - 1, k - 1, 60)
        if m < 10:
            n_short += 1
            continue
        a = s["A"][k - 1] / s["A"][k - 1 - m]
        b = p["c"][j - 1] / p["c"][j - 1 - m]
        if a <= 0 or b <= 0:
            continue
        n_cmp += 1
        r = abs(a / b - 1.0) * 100
        diff.append(r)
        if r > 2.0:
            bad.append((code, t["entry_date"], a, b, r))
    if not n_cmp:
        print("  🚨 비교할 짝이 없다.", flush=True)
        return 0
    d = sorted(diff)
    print("  비교 **%d건** — 어긋남 중앙 %.3f%% · P90 %.3f%% · P99 %.3f%% · 최대 %.2f%%"
          % (n_cmp, d[n_cmp // 2], d[int(n_cmp * .90)], d[int(n_cmp * .99)], d[-1]),
          flush=True)
    print("  **2%% 넘게 어긋난 것 %d건 (%.2f%%)**" % (len(bad), 100.0 * len(bad) / n_cmp),
          flush=True)
    if bad:
        print("\n  가장 크게 어긋난 8건:", flush=True)
        for code, dt, a, b, r in sorted(bad, key=lambda x: -x[4])[:8]:
            print("    %-9s %-12s A축 %.4f · 경로 %.4f · 차 **%.1f%%** (배수 %.2f)"
                  % (code, dt, a, b, r, a / b), flush=True)
    print("\n  ★ 89 첫 판(오염)에서는 **9.87%%** 가 2%% 넘게 어긋났다.", flush=True)
    print("    지금 %.2f%% 면 축 수정이 «먹었다».  여전히 크면 안 먹은 것이다."
          % (100.0 * len(bad) / n_cmp), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
