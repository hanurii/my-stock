# -*- coding: utf-8 -*-
r"""167a — **후보의 D+1..D+5 «50일 이동평균»** (167 의 부품)

  🚨 저장소에 «일별 MA50» 원천이 «없다» — `82` 의 `ma50` 은 «지수»용이다
  ⇒ `stocks.csv.zip` 의 **`close`**(분할 조정)로 «직접» 만든다

  🚨 **`close` 를 쓰는 이유**: 경로의 `pivot`·`c[]` 와 **«같은 자»**여야 비교가 된다
     (`closeunadj` 는 «그때 실제 주가»라 «다른 자»다 — `159`·`164a` 에서 쓴 것)
  ✅ **항등식 검사**를 «넣는다» — 경로의 `c[0]` 이 CSV `close`(진입일)와 «같은가» «전수»

  🚨 행 정렬을 «못 믿는다**(164a 에서 확인) ⇒ 필요한 «창»만 모아 «종목별로 «정렬»»한다

  내는 것: `D:/stock-data/derived/167-ma50.json`
     {"ma": {"코드|날짜": ma50}, "id_ok": n, "id_n": n, "miss": n}
"""
from __future__ import annotations
import csv
import importlib.util as _u
import io as _io
import json
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SRC = Path(r"D:\stock-data\sharadar\stocks.csv.zip")
OUT = Path("D:/stock-data/derived/167-ma50.json")
NMA, NFWD, BACK = 50, 5, 130          # BACK = 달력일 여유(50 거래일 ≈ 70 달력일)


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _shift(d, k):
    y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    import datetime
    return (datetime.date(y, m, dd) + datetime.timedelta(days=k)).isoformat()


def main() -> int:
    r91 = _load("r91", "91-us-out-of-sample.py")
    P = print
    P("=" * 96)
    P("167a — **후보의 D+1..D+5 «50일 이동평균»**(167 의 부품)")
    P("=" * 96)
    P("")
    P("```")
    P("자     `stocks.csv.zip` 의 **`close`**(분할 조정) ← 경로의 `pivot`·`c[]` 와 **«같은 자»**")
    P("창     진입일 D 의 **%d 달력일 «전»** ~ **D+%d 달력일 «뒤»**" % (BACK, BACK))
    P("MA     **%d 거래일** 단순평균 · D+1..D+%d 각 날의 값" % (NMA, NFWD))
    P("🚨 행 정렬을 «못 믿어»(164a) **종목별로 «정렬»** 한 뒤 계산한다")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        tuple(range(1999, 2027)), "1999-04-01", "2026-08-21",
        "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2

    win, need, entry_c = {}, set(), {}
    for y in by2:
        for p in by2[y]:
            c, d0 = p["code"], p["entry_date"]
            lo, hi = _shift(d0, -BACK), _shift(d0, BACK)
            a = win.get(c)
            win[c] = (min(a[0], lo), max(a[1], hi)) if a else (lo, hi)
            for dd in p["d"][1:1 + NFWD]:
                need.add(c + "|" + dd)
            entry_c[c + "|" + d0] = p["c"][0]
    P("")
    P("  종목 **%s** · 필요한 (코드|날짜) 짝 **%s**"
      % (format(len(win), ","), format(len(need), ",")), flush=True)

    ser, rows, id_ok, id_n, mism = {}, 0, 0, 0, []
    with zipfile.ZipFile(SRC) as z:
        with z.open(z.namelist()[0]) as f:
            rd = csv.reader(_io.TextIOWrapper(f, encoding="utf-8", newline=""))
            hdr = next(rd)
            i_t, i_d, i_c = hdr.index("ticker"), hdr.index("date"), hdr.index("close")
            for row in rd:
                rows += 1
                t = row[i_t]
                w = win.get(t)
                if w is None or not (w[0] <= row[i_d] <= w[1]):
                    continue
                try:
                    cv = float(row[i_c])
                except ValueError:
                    continue
                ser.setdefault(t, []).append((row[i_d], cv))
                k = t + "|" + row[i_d]
                if k in entry_c:
                    id_n += 1
                    if abs(cv - entry_c[k]) < 1e-6 * max(abs(cv), 1.0):
                        id_ok += 1
                    else:
                        mism.append((t, row[i_d], entry_c[k], cv))
                if rows % 15_000_000 == 0:
                    P("     … %s 행" % format(rows, ","), flush=True)

    P("")
    P("## 🚨 관문 — **경로의 `c[0]` == CSV `close`(진입일)** «전수»")
    P("")
    P("```")
    P("맞춘 짝 **%s** 중 **%s** 일치 (**%.4f%%**)  ·  어긋남 **%d**"
      % (format(id_n, ","), format(id_ok, ","), 100.0 * id_ok / max(id_n, 1), len(mism)))
    P("★ 이게 서야 「50일선 vs 피벗」 비교가 **«말이 된다»**")
    P("")
    if mism:
        P("🚨 **어긋난 것을 «전부» 찍는다 — «문턱»을 «느슨하게» 하지 «않는다»:**")
        for t, d, a_, b_ in mism[:20]:
            P("   %-8s %s   경로 **%.4f**  vs  CSV **%.4f**   (상대차 **%.3f%%**)"
              % (t, d, a_, b_, 100.0 * abs(a_ - b_) / max(abs(b_), 1e-9)))
        P("")
        P("   ✅ **처방: «문턱»을 «올리는» 게 아니라 «그 종목·그 날»을 «뺀다»**")
        P("     (자료 «수정»이 있었던 자리로 보이고, «어느 쪽이 맞는지»를 «우리가 못 정한다»)")
    if len(mism) > 5:
        P("   🚨 **어긋남이 %d 건 — 「몇 개」가 아니라 «구조»다. 멈춘다**" % len(mism))
        P("```")
        return 3
    P("```", flush=True)
    badset = {t + "|" + d for t, d, _a, _b in mism}

    ma, ndrop = {}, 0
    for t, v in ser.items():
        if any(k.startswith(t + "|") for k in badset):
            ndrop += 1
            continue
        v.sort()
        cs, run = [], 0.0
        for i, (d, c) in enumerate(v):
            run += c
            if i >= NMA:
                run -= v[i - NMA][1]
            if i >= NMA - 1:
                k = t + "|" + d
                if k in need:
                    ma[k] = run / NMA
    P("")
    P("  🚨 어긋난 종목 **%d** 개를 «통째로» 뺐다(그 종목의 MA 를 «안» 만든다)" % ndrop)
    P("  얻은 MA **%s / %s** (**%.1f%%**)  ·  못 얻은 것 **%s**(50 거래일 «못 채움» 등)"
      % (format(len(ma), ","), format(len(need), ","),
         100.0 * len(ma) / max(len(need), 1), format(len(need) - len(ma), ",")))
    OUT.write_text(json.dumps({"ma": ma, "id_ok": id_ok, "id_n": id_n,
                               "mism": [list(x) for x in mism], "ndrop": ndrop,
                               "miss": len(need) - len(ma)}), encoding="utf-8")
    P("")
    P("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
