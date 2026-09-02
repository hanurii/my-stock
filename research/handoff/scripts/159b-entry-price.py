# -*- coding: utf-8 -*-
r"""159b — **후보의 «진입일 실제 주가»**(`closeunadj`) (159 의 부품)

  🚨 우리 하네스의 `close` 는 «분할 조정»이라 「그때 주가」가 «아니다».
     「$30 미만 배제」를 재려면 **«그때» 실제 주가**가 있어야 한다.

  ★ 필요한 (종목, 날짜) 짝은 **158a 가 이미 만들어 뒀다**(`158-need.json`) — 그대로 쓴다.
     (사다리 적재 + 16k resolve 를 «다시» 안 한다)

  내는 것: `D:/stock-data/derived/159-entry-price.json`   {"TICKER|YYYY-MM-DD": closeunadj}
"""
from __future__ import annotations
import csv
import io as _io
import json
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path(r"D:\stock-data\sharadar\stocks.csv.zip")
NEED = Path("D:/stock-data/derived/158-need.json")
OUT = Path("D:/stock-data/derived/159-entry-price.json")


def main() -> int:
    print("=" * 96)
    print("159b — **후보의 «진입일 실제 주가»**(`closeunadj`)")
    print("=" * 96, flush=True)
    d = json.loads(NEED.read_text(encoding="utf-8"))
    need = {k: set(v) for k, v in d["need"].items()}
    npair = sum(len(v) for v in need.values())
    print("  158a 의 짝 이어받음 — **%s** 개 · 종목 **%d**"
          % (format(npair, ","), len(need)), flush=True)

    got, rows = {}, 0
    with zipfile.ZipFile(SRC) as z:
        nm = z.namelist()[0]
        with z.open(nm) as f:
            rd = csv.reader(_io.TextIOWrapper(f, encoding="utf-8", newline=""))
            hdr = next(rd)
            i_t, i_d, i_u = hdr.index("ticker"), hdr.index("date"), hdr.index("closeunadj")
            for row in rd:
                rows += 1
                s = need.get(row[i_t])
                if not s or row[i_d] not in s:
                    continue
                try:
                    u = float(row[i_u])
                except ValueError:
                    continue
                if u > 0:
                    got["%s|%s" % (row[i_t], row[i_d])] = u
                if rows % 10_000_000 == 0:
                    print("     … %s 행" % format(rows, ","), flush=True)
    print("  훑은 행 **%s** · 얻은 짝 **%s** (**%.1f%%**)"
          % (format(rows, ","), format(len(got), ","), 100.0 * len(got) / max(npair, 1)),
          flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(got, separators=(",", ":")), encoding="utf-8")
    print("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
