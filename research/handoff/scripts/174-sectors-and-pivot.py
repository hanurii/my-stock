# -*- coding: utf-8 -*-
r"""174 ④⑤ — **「주도 3업종은 «고정»인가」 · 「피벗 = «전일 고점»인가」** — 🚨 **«판정» «없는» «묘사»**

  ⛔ **사전등록이 «없다». 그리고 그게 «맞다»** — «팔»도 «문턱»도 «이긴다/진다»도 «없다**

  🔎 **읽은 자리**(명령·자리를 «같은 줄»에):
     `sed -n '44,80p' 61b-matched-null.py`      · 자리 `research/handoff/scripts`
     `sed -n '120,133p' 83-mar15-walkthrough.py`
     `sed -n '196,209p' scripts/canslim_lib/vcp.py` · `cheat.py:72,125` · `power_play.py:52,106`
"""
from __future__ import annotations
import csv
import importlib.util as _u
import io as _io
import json
import os
import statistics as st
import sys
import zipfile
from bisect import bisect_left
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SRC = Path(r"D:\stock-data\sharadar\stocks.csv.zip")
OUT = Path("D:/stock-data/derived/174-prevhigh.json")


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _shift(d, k):
    import datetime
    y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    return (datetime.date(y, m, dd) + datetime.timedelta(days=k)).isoformat()


def main():
    r91 = _load("r91", "91-us-out-of-sample.py")
    r61 = _load("r61", "61-selection-leaders.py")
    r61b = _load("r61b", "61b-matched-null.py")
    P = print
    P("=" * 104)
    P("174 ④⑤ — **주도 업종은 «고정»인가 · 피벗은 «전일 고점»인가** · 🚨 **«판정» «없는» «묘사»**")
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/174-sectors-and-pivot.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## ⛔ **사전등록이 «없다» — 그리고 그게 «맞다**")
    P("")
    P("```")
    P("**«판정»이 «없다»** — 팔도 문턱도 «이긴다/진다»도 «없다**  ⇒  **「코드 읽기 + 한 번 훑기」**다")
    P("🚨 그래서 **Δ 도 CI 도 «안» 쓴다**")
    P("자리 `%s`" % os.getcwd().replace("\\\\", "/"))
    P("```")
    P("")
    P("=" * 104)
    P("## ④ **「주도 3업종」이 «고정»인가 «시점»마다 «다시» 뽑히나**")
    P("=" * 104)
    P("")
    P("```")
    P("🔎 `sed -n '44,80p' 61b-matched-null.py` — **내가 «직접» 읽었다**")
    P("")
    P("    def month_returns(monthly, sector, months, lookback=6):")
    P("        base = r61.prev_ym(ym, lookback)        ← **ym 의 «6달 전»**")
    P("        a, b = d.get(base), d.get(ym)           ← **ym 까지의 «과거»만**")
    P("")
    P("    def make_flags(mret, sector, …):")
    P("        smean = {s: mean(...) for s, lst in bysec.items() if len(lst) >= 5}")
    P("        sec_top[ym] = set(sorted(smean, key=lambda s: -smean[s])[:TOP_SECTORS])")
    P("")
    P("    (쓰는 곳) `83:126`  ym = r61.prev_ym(SCAN[:7], 1)    ← **진입 달의 «직전» 달**")
    P("")
    P("## ⇒ ✅ **«고정»이 «아니다». «달»마다 «다시» 뽑힌다**")
    P("   ㉠ 자 = **「그 달까지의 «6개월» 수익률」의 업종 «평균»**  ·  상위 **%d** 업종"
      % r61.TOP_SECTORS)
    P("   ㉡ 기준 달 = **진입 달의 «직전» 달** ⇒ **진입 시점에 «아는» 것만 쓴다**")
    P("   ㉢ ## **⇒ «룩어헤드»가 «아니다»** — 헤드라인은 «걸리지» 않는다")
    P("")
    P("🚨 **그런데 «남는» 것 «하나» — «섹터 라벨» «자체»는 «시점»이 «아니다**")
    P("   `sector` 는 **«한 벌»**(스냅숏)이다 — 「그때 그 회사가 «어느» 업종이었나」가 «아니라**")
    P("   **「«지금» 어느 업종인가」**다 ⇒ **업종이 «바뀐» 회사는 «틀린» 칸에 들어간다**")
    P("   ⇒ 🚨 **«작은» 룩어헤드다. «크기»는 «안» 쟀다**(업종 변경이 «얼마나» 잦은지)")
    P("   ★ `156` 의 「8,032 를 «전체»로」와 **«같은 갈래»** — 「스냅숏을 «시점»처럼 쓴다」")
    P("```", flush=True)

    pack = json.loads((r91.OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    del pack
    months = sorted({m for d in monthly.values() for m in d})
    sec_top, _in_pct = r61b.make_flags(r61b.month_returns(monthly, sector, months), sector)

    P("")
    P("## ④㉡ **«연도별»로 «어느» 업종이 뽑혔나 — 「테마가 «바뀌는가»」**")
    P("")
    P("```")
    yrs = sorted({m[:4] for m in sec_top})
    P("| 해 | 12월 기준 «주도 %d업종» | 그 해 «달»마다 뽑힌 업종 «가짓수» |" % r61.TOP_SECTORS)
    P("|---|---|---:|")
    chg = []
    prev = None
    for y in yrs:
        ms = sorted(m for m in sec_top if m[:4] == y)
        uni = set()
        for m in ms:
            uni |= sec_top[m]
        last = sorted(sec_top[ms[-1]])
        P("| %s | %s | **%d** |" % (y, ", ".join(last), len(uni)))
        if prev is not None:
            chg.append(len(set(last) - set(prev)))
        prev = last
    P("")
    P("⇒ 해가 바뀔 때 **12월 기준 3업종 중 «바뀐» 수** — 중앙 **%d** · 최소 %d · 최대 %d"
      % (st.median(chg), min(chg), max(chg)))
    P("⇒ 한 해 «안»에서도 뽑힌 업종 «가짓수»가 **%d ~ %d** 개다"
      % (min(len({s for m in sorted(x for x in sec_top if x[:4] == y) for s in sec_top[m]})
             for y in yrs),
         max(len({s for m in sorted(x for x in sec_top if x[:4] == y) for s in sec_top[m]})
             for y in yrs)))
    P("")
    P("## ⇒ ★ **「테마가 «바뀐다」」가 «수»로 보인다** — 원전의 「«현재 주기»의 테마」와 «닮았다**")
    P("🚨 **「닮았다」는 «이야기»다** — 원전이 말한 「테마」가 **«업종»**인지는 **«모른다»**")
    P("```", flush=True)

    P("")
    P("=" * 104)
    P("## ⑤ **「피벗」이 «무엇»인가 — 🚨 «검출기»마다 «다르다**")
    P("=" * 104)
    P("")
    P("```")
    P("🔎 **내가 «직접» 읽었다:**")
    P("")
    P("| 검출기 | 피벗 | «자» | 자리 |")
    P("|---|---|---|---|")
    P("| **VCP** | `max(seg)` — **코일의 «종가» 최고치** | 🚨 **«종가»** | `vcp.py:192,204,287,300` |")
    P("| **3C**  | `shelf_high = highs[…]` | **«장중 고가»** | `cheat.py:72,125` |")
    P("| **PP**  | `flag_high  = highs[…]` | **«장중 고가»** | `power_play.py:52,106` |")
    P("")
    P("## ⇒ 🚨🚨 **«우리» 안에서 «자»가 «둘»이다 — VCP 는 «종가», 3C·PP 는 «고가»**")
    P("   ⇒ ★ **유형 67 이 «우리 검출기» 안에 «있다»**")
    P("   ⇒ 🚨 그래서 **「피벗」을 «한 낱말»로 쓰면 «세 검출기»를 «뭉갠다»**")
    P("")
    P("✅ **VCP 의 «다른» 갈래도 확인했다** — `find_contraction_chain` 의 `pivot`(수축 고점)은")
    P("   **`pivot_price` 로 «안» 나간다**(`vcp.py:287` 이 **코일** 피벗만 쓴다) ⇒ **갈래는 «둘»이 아니라 «하나»**")
    P("")
    P("🚨 그리고 **원전은 「«전일» 고점」**이라 했다 — **우리 셋 «다» 「«전일»」이 «아니다»**")
    P("   VCP=코일 «구간»의 종가 최고 · 3C=«선반» 고가 · PP=«깃발» 고가 ⇒ **«구간»의 최고지 «전일»이 아니다**")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        tuple(range(1999, 2027)), "1999-04-01", "2026-08-21",
        "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2

    want, win = {}, {}
    for y in by2:
        for p in by2[y]:
            if p.get("pivot") is None:
                continue
            want.setdefault(p["code"], []).append((p["entry_date"], p["pivot"], p["pattern"]))
            lo, hi = _shift(p["entry_date"], -14), p["entry_date"]
            a = win.get(p["code"])
            win[p["code"]] = (min(a[0], lo), max(a[1], hi)) if a else (lo, hi)

    if OUT.exists():
        ph = json.loads(OUT.read_text(encoding="utf-8"))
        P("")
        P("  ♻️ 전일 고가 — 갈무리 %s 짝" % format(len(ph), ","), flush=True)
    else:
        ser, rows = {}, 0
        with zipfile.ZipFile(SRC) as z:
            with z.open(z.namelist()[0]) as f:
                rd = csv.reader(_io.TextIOWrapper(f, encoding="utf-8", newline=""))
                hd = next(rd)
                i_t, i_d, i_h = hd.index("ticker"), hd.index("date"), hd.index("high")
                for row in rd:
                    rows += 1
                    w = win.get(row[i_t])
                    if w is None or not (w[0] <= row[i_d] <= w[1]):
                        continue
                    try:
                        ser.setdefault(row[i_t], []).append((row[i_d], float(row[i_h])))
                    except ValueError:
                        pass
                    if rows % 15_000_000 == 0:
                        P("     … %s 행" % format(rows, ","), flush=True)
        ph = {}
        for t, v in ser.items():
            v.sort()
            ds = [x[0] for x in v]
            for ed, _pv, _pt in want.get(t, []):
                i = bisect_left(ds, ed)
                if i > 0:
                    ph[t + "|" + ed] = v[i - 1][1]
        OUT.write_text(json.dumps(ph), encoding="utf-8")
        P("")
        P("  전일 고가 짝 **%s** 저장" % format(len(ph), ","), flush=True)

    P("")
    P("## ⑤㉡ **「피벗 ÷ «전일» 고점」의 «분포» — «검출기»마다 «갈라»**")
    P("")
    P("```")
    by_pat, n_miss = {}, 0
    for t, lst in want.items():
        for ed, pv, pat in lst:
            h = ph.get(t + "|" + ed)
            if h is None or h <= 0:
                n_miss += 1
                continue
            by_pat.setdefault(pat, []).append(pv / h)
    tot = sum(len(v) for v in by_pat.values())
    P("짝 **%s** · 전일 고가 «없음» **%s** (**%.2f%%**)"
      % (format(tot, ","), format(n_miss, ","), 100.0 * n_miss / max(tot + n_miss, 1)))
    P("")
    P("| 검출기 | n | 중앙 | P10 | P90 | **«정확히» 1.0** |")
    P("|---|---:|---:|---:|---:|---:|")
    for pat in sorted(by_pat):
        v = sorted(by_pat[pat])
        n = len(v)
        eq = sum(1 for x in v if abs(x - 1.0) < 1e-9)
        P("| **%s** | %s | **%.4f** | %.4f | %.4f | **%s** (%.2f%%) |"
          % (pat, format(n, ","), v[n // 2], v[n // 10], v[9 * n // 10],
             format(eq, ","), 100.0 * eq / n))
    allv = sorted(x for v in by_pat.values() for x in v)
    eq_all = sum(1 for x in allv if abs(x - 1.0) < 1e-9)
    P("| **합** | %s | **%.4f** | %.4f | %.4f | **%s** (**%.2f%%**) |"
      % (format(len(allv), ","), allv[len(allv) // 2], allv[len(allv) // 10],
         allv[9 * len(allv) // 10], format(eq_all, ","), 100.0 * eq_all / len(allv)))
    P("")
    P("## ⇒ **「같은 자인가」 — %s**"
      % ("✅ **거의 같다**" if eq_all > 0.5 * len(allv) else
         "🔴 **«같은 자»가 «아니다»** — 「정확히 1.0」이 **%.2f%%**뿐이다"
         % (100.0 * eq_all / len(allv))))
    P("   중앙 **%.4f** ⇒ 피벗이 전일 고점의 **%.1f%%** 자리다" % (allv[len(allv) // 2],
                                                          100 * allv[len(allv) // 2]))
    P("")
    P("🚨 **「전일 고가」의 «자»** — `stocks.csv` 의 `high`(**분할 조정**)를 썼다")
    P("   경로의 `pivot` 도 **같은 조정**이어야 «비»가 «말이 된다** —")
    P("   `167a` 에서 **`c[0]` == CSV `close`** 를 «전수» 확인했으므로 **«같은 자»다**(IESC 한 종목 제외)")
    P("```")
    P("")
    P("```")
    P("🚨 **이 판이 «못» 하는 것:**")
    P("   ⛔ **«판정»** — 팔도 문턱도 «없다**")
    P("   ⛔ 「피벗 «자»를 «통일»하자」 — **«안» 쟀다**(바꾸면 «검출기»가 «다른 것»이 된다)")
    P("   ⛔ 「원전이 맞다/틀리다」 — 원전의 「테마」가 **«업종»**인지 **«모른다»**")
    P("   ⛔ 「섹터 라벨 룩어헤드가 «작다」」 — **«크기»를 «안» 쟀다**")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
