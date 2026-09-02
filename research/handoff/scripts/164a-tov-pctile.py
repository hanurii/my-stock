# -*- coding: utf-8 -*-
r"""164a — **거래대금의 «시점» 백분위** (164 의 부품)

  🚨 「고정 문턱」은 **«시점 편향»**이다 — 거래대금은 시간이 갈수록 커지므로
     **「유동성 «나쁜» 것」이 「«옛날» 것」이 된다**  ← `159` 에서 «주가»로 «똑같이» 겪었다
  ✅ 그래서 **「그날 «전체 상장사» 분포 안에서의 «백분위»」**를 쓴다(156a·159a 와 «같은 모양»)

  🚨 **자 «하나»로 통일한다**(유형 67):
     `stocks.csv` 의 **`closeunadj × volume`** = «그날 실제로 오간 달러»
     ⛔ `95-cap-pit.json` 의 `tov` 는 **못 쓴다** — 종목 **8,032** 개뿐이고 «부분 구간»만 있어
        «단면»이 «안» 된다(156 에서 「8,032 를 «전체»로 읽은」 바로 그 자리)

  🚨 **`scan_date`(진입 «전»)**로 잰다 — 돌파일 거래량은 «장전»에 «모른다»
     ⇒ 룩어헤드가 «구조적»으로 «불가능»하다

  내는 것: `D:/stock-data/derived/164-tov-pctile.json`
     {"pair": {"코드|스캔일": 백분위}, "n": {날짜: 종목수}, "miss": ..., "tot": ...}
"""
from __future__ import annotations
import csv
import importlib.util as _u
import io as _io
import json
import sys
import zipfile
from array import array
from bisect import bisect_left
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SRC = Path(r"D:\stock-data\sharadar\stocks.csv.zip")
OUT = Path("D:/stock-data/derived/164-tov-pctile.json")
D0, D1 = "1999-01-01", "2026-08-31"


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main() -> int:
    r91 = _load("r91", "91-us-out-of-sample.py")
    P = print
    P("=" * 96)
    P("164a — **거래대금의 «시점» 백분위**(164 의 부품)")
    P("=" * 96)
    P("")
    P("```")
    P("자      **`closeunadj × volume`** = 그날 «실제로 오간 달러»   ← 자 «하나»로 통일(유형 67)")
    P("시점    **`scan_date`**(진입 «전»)                            ← 룩어헤드가 «구조적»으로 불가")
    P("단면    «그날 행이 있는 종목 «전부»»                          ← 156a·159a 와 «같은 논거»")
    P("⛔ `95-cap-pit.json` 의 `tov` 는 **안 쓴다** — 8,032 종목·«부분 구간»이라 «단면»이 안 된다")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        tuple(range(1999, 2027)), "1999-04-01", "2026-08-21",
        "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    want = {}
    for y in sorted(by2):
        for p in by2[y]:
            want.setdefault(p["scan_date"], set()).add(p["code"])
    npair = sum(len(v) for v in want.values())
    P("")
    P("  필요한 짝 **%s** (스캔일 %s 개)" % (format(npair, ","), format(len(want), ",")), flush=True)

    per, got, rows = {}, {}, 0
    with zipfile.ZipFile(SRC) as z:
        with z.open(z.namelist()[0]) as f:
            rd = csv.reader(_io.TextIOWrapper(f, encoding="utf-8", newline=""))
            hdr = next(rd)
            i_t, i_d = hdr.index("ticker"), hdr.index("date")
            i_u, i_v = hdr.index("closeunadj"), hdr.index("volume")
            for row in rd:
                rows += 1
                d = row[i_d]
                if not (D0 <= d <= D1):
                    continue
                try:
                    tv = float(row[i_u]) * float(row[i_v])
                except ValueError:
                    continue
                if tv <= 0:
                    continue
                per.setdefault(d, array("d")).append(tv)
                w = want.get(d)
                if w and row[i_t] in w:
                    got[row[i_t] + "|" + d] = tv
                if rows % 10_000_000 == 0:
                    P("     … %s 행" % format(rows, ","), flush=True)

    P("")
    P("  훑은 행 **%s** · 거래일 **%s** · 하루 종목 %s ~ %s"
      % (format(rows, ","), format(len(per), ","),
         format(min(len(v) for v in per.values()), ","),
         format(max(len(v) for v in per.values()), ",")), flush=True)

    for d in per:
        per[d] = sorted(per[d])
    pair = {}
    for k, tv in got.items():
        v = per[k.split("|")[1]]
        pair[k] = bisect_left(v, tv) / len(v)

    P("  얻은 짝 **%s / %s** (**%.1f%%**)  ·  못 찾은 짝 **%s**"
      % (format(len(pair), ","), format(npair, ","),
         100.0 * len(pair) / max(npair, 1), format(npair - len(pair), ",")))
    q = sorted(pair.values())
    P("  후보의 백분위 분포 — P10 **%.3f** · 중앙 **%.3f** · P90 **%.3f**"
      % (q[len(q) // 10], q[len(q) // 2], q[9 * len(q) // 10]))
    P("  ★ 중앙이 0.5 «보다 높으면» 우리 후보가 «이미» 유동성 «위쪽»에 쏠려 있다는 뜻이다")
    OUT.write_text(json.dumps(
        {"pair": pair, "n": {d: len(v) for d, v in per.items()},
         "miss": npair - len(pair), "tot": npair}), encoding="utf-8")
    P("")
    P("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
