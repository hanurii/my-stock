# -*- coding: utf-8 -*-
r"""92a — 실적을 **「공시일」 축**으로 세운 표를 만든다 + **덮개율을 잰다**.

왜 먼저 이걸 하나
-----------------
92 본검정을 설계하기 «전»에 **「그 자료가 우리 진입 시점에 있기는 한가」**를 재야 한다.
없으면 설계가 통째로 무의미하고, 있어도 «얼마나» 있는지가 표본 크기를 정한다.
🚨 [[verification-failure-modes]] 유형 18 — 관문이 정확도만 재고 «타당성»은 안 재는 자리.

규약 (90번에서 확인)
--------------------
① `date` = **SEC 제출일**. `calendardate`·`reportperiod` 로 붙이면 룩어헤드다.
② `dimension` 은 **ARQ/ART 만**. MRQ/MRT/MRY 는 «나중에 수정된» 값이라 미래를 안다.
③ 진입일 D 에 쓸 수 있는 것 = **`date < D` 인 것 중 가장 늦은 것**.
   🚨 `<=` 가 아니라 `<` 다 — 공시 «당일»에 우리가 그걸 보고 샀다고 하면 안 된다
      (장전 공시면 볼 수 있지만, 장중·장후 공시가 섞여 있어 «못 봤다» 쪽으로 둔다).

내는 것: `D:\stock-data\derived\92-fund-pit.json`
"""
from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import us_loader as U                                          # noqa: E402

DERIVED = Path(r"D:\stock-data\derived")
OUT = DERIVED / "92-fund-pit.json"
SUB = ROOT / ".cache" / "bt5y" / "sub"

DIMS = ("ARQ", "ART")

# 담을 항목 — **미너비니가 실제로 쓰는 것**에 한정한다. 나중에 «추가하지 않는다».
FIELDS = ("eps", "epsdil", "revenue", "netmargin", "grossmargin",
          "roe", "shareswadil", "de", "ncfo", "opinc")


def build():
    DERIVED.mkdir(parents=True, exist_ok=True)
    by = defaultdict(lambda: {"ARQ": [], "ART": []})
    n = kept = 0
    dimc = Counter()
    with zipfile.ZipFile(U.FUNDAMENTALS_ZIP) as z:
        nm = z.infolist()[0].filename
        rd = csv.DictReader(io.TextIOWrapper(z.open(nm), encoding="utf-8",
                                            errors="replace"))
        for r in rd:
            n += 1
            d = r.get("dimension")
            dimc[d] += 1
            if d not in DIMS:
                continue
            dt = r.get("date")
            if not dt:
                continue
            row = [dt, r.get("reportperiod") or "", r.get("calendardate") or ""]
            for f in FIELDS:
                v = r.get(f)
                try:
                    row.append(float(v) if v not in (None, "") else None)
                except ValueError:
                    row.append(None)
            by[r["ticker"]][d].append(row)
            kept += 1
            if n % 500_000 == 0:
                print("   %s만 행…" % "{:,}".format(n // 10000), flush=True)
    for t, dd in by.items():
        for d in DIMS:
            # 🚨 «제출일» 순으로 세운다. 같은 날 여러 건이면 보고기간이 늦은 것을 뒤로.
            dd[d].sort(key=lambda x: (x[0], x[1]))
    print("전체 %s행 · ARQ/ART %s행 · 종목 %d개"
          % ("{:,}".format(n), "{:,}".format(kept), len(by)), flush=True)
    print("   dimension 분포: %s" % dict(dimc), flush=True)
    OUT.write_text(json.dumps({"fields": ["date", "reportperiod", "calendardate"] + list(FIELDS),
                               "by": by}, separators=(",", ":")), encoding="utf-8")
    print("저장: %s (%.0f MB)" % (OUT, OUT.stat().st_size / 1e6), flush=True)
    return by


def load():
    d = json.loads(OUT.read_text(encoding="utf-8"))
    return d["by"], d["fields"]


def asof(rows, day):
    """진입일 `day` «전»에 나온 것 중 가장 늦은 것. 없으면 None. (이분탐색)"""
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < day:
            lo = mid + 1
        else:
            hi = mid
    return rows[lo - 1] if lo else None


def coverage():
    """★ 타당성 관문 — 2017~2026 «실제 진입»에 실적이 붙는가."""
    by, fields = load()
    ix = {f: i for i, f in enumerate(fields)}
    print("\n" + "=" * 92, flush=True)
    print("★ 덮개율 — 2017~2026 실제 진입에 «공시일 기준» 실적이 붙는가", flush=True)
    print("=" * 92, flush=True)
    tot = Counter()
    lagd = []
    nof = Counter()
    for y in range(2017, 2027):
        f = SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        for p in json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]:
            tot["경로"] += 1
            rec = by.get(p["code"])
            if not rec:
                tot["종목이 실적표에 없음"] += 1
                nof[p["code"]] += 1
                continue
            q = asof(rec["ARQ"], p["entry_date"])
            if q is None:
                tot["진입 전 공시 없음"] += 1
                continue
            tot["ARQ 붙음"] += 1
            # 신선도 — 진입일과 최근 공시일의 간격
            import datetime as dt
            a = dt.date(*map(int, q[0].split("-")))
            b = dt.date(*map(int, p["entry_date"].split("-")))
            lagd.append((b - a).days)
            # 4분기 전 값도 있어야 «전년 대비 성장률»을 만들 수 있다
            j = rec["ARQ"].index(q)
            if j >= 4 and rec["ARQ"][j - 4][ix["eps"]] is not None \
                    and q[ix["eps"]] is not None:
                tot["EPS 전년비 계산 가능"] += 1
            if j >= 4 and rec["ARQ"][j - 4][ix["revenue"]] is not None \
                    and q[ix["revenue"]] is not None:
                tot["매출 전년비 계산 가능"] += 1
            if j >= 5:
                tot["가속(2분기 비교) 가능"] += 1
    N = tot["경로"]
    for k in ("경로", "ARQ 붙음", "종목이 실적표에 없음", "진입 전 공시 없음",
              "EPS 전년비 계산 가능", "매출 전년비 계산 가능", "가속(2분기 비교) 가능"):
        print("   %-24s %9s  %6.2f%%" % (k, "{:,}".format(tot[k]), 100.0 * tot[k] / N),
              flush=True)
    if lagd:
        lagd.sort()
        n = len(lagd)
        print("\n   공시 후 며칠 만에 샀나 (신선도) — 중앙 %d일 · P25 %d · P75 %d · P90 %d · 최대 %d"
              % (lagd[n // 2], lagd[n // 4], lagd[3 * n // 4], lagd[int(n * .9)], lagd[-1]),
              flush=True)
        stale = sum(1 for x in lagd if x > 120)
        print("   🚨 120일 넘게 «묵은» 실적으로 사는 경우 %s건 (%.2f%%) — 분기 공시 주기 밖"
              % ("{:,}".format(stale), 100.0 * stale / n), flush=True)
    if nof:
        print("\n   실적표에 아예 없는 종목 %d개 · 상위 8: %s"
              % (len(nof), nof.most_common(8)), flush=True)


if __name__ == "__main__":
    if "--coverage-only" not in sys.argv:
        build()
    coverage()
