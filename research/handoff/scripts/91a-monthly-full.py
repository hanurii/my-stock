# -*- coding: utf-8 -*-
"""91a — 섹터 월말 종가 패널을 **전체 이력(1997~2026)**으로 다시 만든다.

61a 와 «같은 계산»이고 자료만 넓혔다.
🚨 **기존 `61-monthly-us.json` 을 덮지 않는다** — 그 파일 위에서 +298.44% 가 나왔고,
   덮으면 옛 결과가 재현 불가가 된다([[provenance-audit-2026-08]] 의 처방).
   내는 것: `.cache/bt5y/out/91-monthly-us-full.json`

★ 관문 — 겹치는 구간(2016-12~2026-08)이 **옛 파일과 완전히 같아야 한다.**
  같은 원본 행에서 같은 계산을 하므로 «달라지면» 자료가 바뀐 것이다.
  (유형 2′ 의 예외 자리 — 여기서는 「완전 일치」가 «검사 대상»이다.)
"""
from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import us_loader as U                                          # noqa: E402

OUT = ROOT / ".cache" / "bt5y" / "out" / "91-monthly-us-full.json"
OLD = ROOT / ".cache" / "bt5y" / "out" / "61-monthly-us.json"


def main() -> int:
    sect = {}
    with zipfile.ZipFile(U.TICKERS_ZIP) as z:
        n = z.namelist()[0]
        with z.open(n) as f:
            for r in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8",
                                                     errors="replace")):
                if r.get("table") != "SEP":
                    continue
                s = (r.get("sector") or "").strip()
                if s and r.get("ticker"):
                    sect.setdefault(r["ticker"], s)
    print("섹터 라벨 %d 종목" % len(sect), flush=True)

    mo, rows = {}, 0
    print("가격 훑기: %s" % U.STOCKS_ZIP.name, flush=True)
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        n = z.namelist()[0]
        with z.open(n) as f:
            rd = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
            head = next(rd)
            iT, iD, iC = head.index("ticker"), head.index("date"), head.index("close")
            for row in rd:
                rows += 1
                t, d = row[iT], row[iD]
                if t not in sect:
                    continue
                try:
                    c = float(row[iC])
                except (ValueError, IndexError):
                    continue
                if c <= 0:
                    continue
                k = mo.setdefault(t, {})
                ym = d[:7]
                # 그 달 «마지막» 거래일의 종가 — 행이 (티커, 날짜) 순이라 덮어쓰면 된다.
                # 🚨 순서를 믿지 않는다: 날짜를 함께 담아 «더 늦은 날»만 받는다.
                p = k.get(ym)
                if p is None or d >= p[0]:
                    k[ym] = (d, c)
                if rows % 5_000_000 == 0:
                    print("   %s만 행…" % "{:,}".format(rows // 10000), flush=True)
    monthly = {t: {ym: v[1] for ym, v in d.items()} for t, d in mo.items()}
    print("행 %s · 월말 패널 %d 종목" % ("{:,}".format(rows), len(monthly)), flush=True)

    OUT.write_text(json.dumps({"monthly": monthly, "sector": sect},
                              separators=(",", ":")), encoding="utf-8")
    print("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6), flush=True)

    # ── 관문: 겹치는 구간이 옛 파일과 같은가 ────────────────────────────
    if OLD.exists():
        o = json.loads(OLD.read_text(encoding="utf-8"))
        om = o["monthly"]
        same = diff = miss = 0
        ex = []
        for t, d in om.items():
            nd = monthly.get(t)
            if nd is None:
                miss += len(d)
                continue
            for ym, v in d.items():
                nv = nd.get(ym)
                if nv is None:
                    miss += 1
                elif abs(nv - v) <= 1e-9 * max(1.0, abs(v)):
                    same += 1
                else:
                    diff += 1
                    if len(ex) < 5:
                        ex.append((t, ym, v, nv))
        tot = same + diff + miss
        print("\n★ 관문 — 옛 파일과 겹치는 칸 %s개" % "{:,}".format(tot), flush=True)
        print("   같음 %s · 다름 %s · 새 파일에 없음 %s"
              % ("{:,}".format(same), "{:,}".format(diff), "{:,}".format(miss)),
              flush=True)
        for t, ym, v, nv in ex:
            print("   예: %s %s  옛 %.6f → 새 %s" % (t, ym, v, nv), flush=True)
        print("   판정: %s" % ("통과" if diff == 0 and miss == 0 else "🚨 어긋남 — 왜인지부터"),
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
