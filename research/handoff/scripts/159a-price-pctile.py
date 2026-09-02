# -*- coding: utf-8 -*-
r"""159a — **날마다 «그날 상장 전부»의 주가 백분위 문턱** (159 의 부품)

  🚨 우리 `close` 는 «분할 조정»이라 **「그때 주가」가 «아니다»**:
     NFLX 2003-06  close **$0.17** vs closeunadj **$24.40**
  ⇒ 「$30 미만 배제」를 **`closeunadj`**(그때 실제 주가)로 재야 한다

  ★ Ⓒ 팔(손잡이 0개)에 필요한 것:
     ① 1999-06-30 에 **$30 이 몇 백분위**인가를 «한 번» 계산
     ② 그 백분위를 **«고정»**하고, 날마다 그 백분위의 **«달러 문턱»**을 낸다
     ⇒ **문턱을 «우리가» 고르지 않는다.** 「원전이 1999 에 말한 자리」를 «시대에 맞춰» 옮길 뿐

  내는 것: `D:/stock-data/derived/159-price-pctile.json`
     {"pct": 0.819, "thr": {날짜: 달러}, "n": {날짜: 종목수}, "ctl": {...}}
"""
from __future__ import annotations
import csv
import io as _io
import json
import statistics as st
import sys
import zipfile
from array import array
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path(r"D:\stock-data\sharadar\stocks.csv.zip")
OUT = Path("D:/stock-data/derived/159-price-pctile.json")
ANCHOR, ANCHOR_USD = "1999-06-30", 30.0
D0, D1 = "1999-01-01", "2026-08-31"

# ★ EB★ 양성 대조 — 🚨 «이상치를 보고 «고른»» 넷이다. «기전»용이지 «크기»용이 «아니다»
CTL = {("NFLX", "2003-06-30"), ("TSCO", "2003-06-30"),
       ("WINT", "2003-07-31"), ("GNTA1", "2003-06-30")}


def main() -> int:
    print("=" * 96)
    print("159a — **날마다 «그날 상장 전부»의 주가 백분위 문턱**")
    print("=" * 96, flush=True)
    print("")
    print("## 가정·출처")
    print("")
    print("```")
    print("자료      `stocks.csv.zip` 의 **`closeunadj`**       ← 출처 있음(Sharadar 원열)")
    print("기준일    **%s** · 기준 금액 **$%.0f**             ← 출처: 원전(미너비니) «글자»" % (ANCHOR, ANCHOR_USD))
    print("유니버스  «그날 행이 있는 종목 전부»                ← 출처: 156a 와 «같은 논거»")
    print("          (`stocks.csv` 는 상폐 «후» 행이 없다 — 156a 에서 47.1% 감소로 확인됨)")
    print("⚠️ **출처가 «빈» 가정: 없음**")
    print("```", flush=True)

    per, ctl, rows = {}, {}, 0
    with zipfile.ZipFile(SRC) as z:
        nm = z.namelist()[0]
        with z.open(nm) as f:
            rd = csv.reader(_io.TextIOWrapper(f, encoding="utf-8", newline=""))
            hdr = next(rd)
            i_t, i_d = hdr.index("ticker"), hdr.index("date")
            i_c, i_u = hdr.index("close"), hdr.index("closeunadj")
            for row in rd:
                rows += 1
                d = row[i_d]
                if not (D0 <= d <= D1):
                    continue
                try:
                    u = float(row[i_u])
                    c0 = float(row[i_c])
                except ValueError:
                    continue
                if u > 0:
                    per.setdefault(d, array("f")).append(u)
                    if (row[i_t], d[:7] + "-30") in CTL or (row[i_t], d[:7] + "-31") in CTL:
                        ctl.setdefault((row[i_t], d[:7]), (d, c0, u))
                if rows % 10_000_000 == 0:
                    print("     … %s 행" % format(rows, ","), flush=True)

    days = sorted(per)
    print("  훑은 행 **%s** · 거래일 **%s** · 하루 종목 %d ~ %d"
          % (format(rows, ","), format(len(days), ","),
             min(len(v) for v in per.values()), max(len(v) for v in per.values())), flush=True)

    # ① 기준일에 $30 이 몇 백분위인가
    base = sorted(per[ANCHOR]) if ANCHOR in per else None
    if base is None:
        cand = [d for d in days if d >= ANCHOR]
        base = sorted(per[cand[0]])
        print("  ⚠️ %s 에 행이 없어 **%s** 로 대체" % (ANCHOR, cand[0]), flush=True)
    pct = sum(1 for v in base if v < ANCHOR_USD) / len(base)
    print("")
    print("## ① 기준 — **%s 에 $%.0f 은 «%.1f 백분위»**" % (ANCHOR, ANCHOR_USD, 100 * pct))
    print("")
    print("```")
    print("그날 종목 **%s** 개 중 $%.0f 미만이 **%s** 개  →  **%.3f**"
          % (format(len(base), ","), ANCHOR_USD,
             format(sum(1 for v in base if v < ANCHOR_USD), ","), pct))
    print("⇒ ★ **이 백분위를 «고정»한다.** 문턱을 «우리가» 고르지 않는다")
    print("```")

    # ② 날마다 그 백분위의 달러 문턱
    thr = {}
    for d in days:
        v = sorted(per[d])
        i = min(len(v) - 1, int(len(v) * pct))
        thr[d] = float(v[i])
    print("")
    print("## ② 날마다의 «달러 문턱» — 고정 백분위 %.1f%%" % (100 * pct))
    print("")
    print("```")
    for y in ("1999", "2003", "2010", "2019", "2026"):
        ds = [d for d in days if d[:4] == y]
        if ds:
            print("   %s   중앙 문턱 **$%.2f**" % (y, st.median([thr[d] for d in ds])))
    print("```")

    # EB★ — 양성 대조
    print("")
    print("## 관문 EB★ — **`close` 와 `closeunadj` 가 «다르다»는 양성 대조**")
    print("")
    print("```")
    print("🚨 **이 넷은 «이상치를 보고 «고른»» 것이다 — «기전»용이지 «크기»용이 «아니다**»")
    for (tk, ym), (d, c0, u) in sorted(ctl.items()):
        print("   %-6s %s   close **$%s**  ·  closeunadj **$%.2f**  ·  비 **%.3g**"
              % (tk, d, format(c0, ",.2f") if c0 < 1e6 else "%.3g" % c0, u, c0 / u))
    print("")
    print("★ **크기»는 «무작위 표본»으로 본다**(검증 세션 실측 90,758 행):")
    print("   비의 **중앙이 «모든 해»에서 정확히 1.000** · **[0.5, 2] 밖이 16.8%**")
    print("   ⇒ ✅ 맞는 말: **「83%는 «같고» 17%가 «크게 다르다»」**  ⛔ 「전부 다르다」는 «과하다»")
    print("   🚨 그런데 **그 17%가 «분할»(성장)+«역분할»(부진)이라 «성과와 상관»된다**")
    print("     ⇒ 무작위면 «희석»만 되는데 여기선 **«한 방향»으로 튼다**")
    print("```")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"pct": pct, "thr": thr,
                               "n": {d: len(per[d]) for d in days},
                               "ctl": {"%s|%s" % k: v for k, v in ctl.items()}},
                              separators=(",", ":")), encoding="utf-8")
    print("")
    print("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
