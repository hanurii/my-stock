# -*- coding: utf-8 -*-
"""61a — 섹터 판정에 쓸 **월말 종가 패널**을 한 번만 만든다.

Sharadar 가격 CSV(1.1GB)를 **한 번** 흘려보내며 `(티커, 연월) -> 그 달 마지막 종가` 만 남긴다.
🚨 **분할조정 종가(`close`)를 쓴다** — 한국 `fltRt` 복원본과 같은 성질(M38 규약).
내는 것: `.cache/bt5y/out/61-monthly-us.json`
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / ".cache" / "sharadar" / "stocks-10Y.csv.zip"
TIC = ROOT / ".cache" / "sharadar" / "tickers.csv.zip"
OUT = ROOT / ".cache" / "bt5y" / "out" / "61-monthly-us.json"


def main() -> int:
    # ── 섹터 라벨 ────────────────────────────────────────────────────────
    sect = {}
    with zipfile.ZipFile(TIC) as z:
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

    # ── 월말 종가 (한 번만 훑는다) ───────────────────────────────────────
    mo = {}
    rows = 0
    with zipfile.ZipFile(SRC) as z:
        n = z.namelist()[0]
        with z.open(n) as f:
            rd = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
            head = next(rd)
            iT, iD, iC = head.index("ticker"), head.index("date"), head.index("close")
            for row in rd:
                rows += 1
                if rows % 20_000_000 == 0:
                    print("  %d백만행" % (rows // 1_000_000), flush=True)
                try:
                    c = float(row[iC])
                except (ValueError, IndexError):
                    continue
                if c <= 0:
                    continue
                t, d = row[iT], row[iD]
                ym = d[:7]
                cur = mo.setdefault(t, {})
                prev = cur.get(ym)
                # 그 달의 «마지막» 날짜를 남긴다
                if prev is None or d > prev[0]:
                    cur[ym] = (d, c)
    print("전체 %d행 · 티커 %d개" % (rows, len(mo)), flush=True)

    packed = {t: {ym: v[1] for ym, v in sorted(d.items())} for t, d in mo.items()}
    OUT.write_text(json.dumps({"sector": sect, "monthly": packed},
                              ensure_ascii=False), encoding="utf-8")
    print("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
