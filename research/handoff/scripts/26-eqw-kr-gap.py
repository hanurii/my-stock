# -*- coding: utf-8 -*-
"""26 · 「공백 포함」 9%p 가 **신규상장 첫날**에서 오는지 **거래정지 복귀**에서 오는지 가른다.

- new   : 창 안에서 그 종목이 **처음 나타난 날** (신규상장 또는 창 시작)
- resume: 전에 나온 적 있는데 **어제는 없던** 날 (거래정지 복귀·자료 공백)
- normal: 어제도 오늘도 있는 날
"""
from __future__ import annotations

import json
import re
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / ".cache" / "pdata"
EXCLUDE = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN = re.compile("^9[0-9]{5}$")
S, E = "20210201", "20260821"


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def main():
    files = sorted(x for x in P.glob("price_*.json") if S <= x.stem[6:] <= E)
    ever, prev = set(), set()
    eq = {"normal": 1.0, "with_resume": 1.0, "with_all": 1.0}
    buckets = {"new": [], "resume": []}
    first_file = True
    for p in files:
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = []
        cur = set()
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ") or FOREIGN.match(code):
                continue
            if EXCLUDE.search(r.get("itmsNm") or ""):
                continue
            c = num(r.get("clpr"))
            if not c or c <= 0:
                continue
            cur.add(code)
            f = num(r.get("fltRt"))
            if f is None:
                continue
            kind = ("normal" if code in prev
                    else ("new" if code not in ever else "resume"))
            if first_file:
                kind = "normal" if code in prev else "skip"
            rows.append((kind, f / 100.0))
        for key, keep in (("normal", ("normal",)),
                          ("with_resume", ("normal", "resume")),
                          ("with_all", ("normal", "resume", "new"))):
            v = [r for k, r in rows if k in keep]
            if v:
                eq[key] *= (1 + sum(v) / len(v))
        for k in ("new", "resume"):
            buckets[k].extend(r for kk, r in rows if kk == k)
        ever |= cur
        prev = cur
        first_file = False
    print("정상만(내 정본)                 %+9.2f%%" % ((eq["normal"] - 1) * 100))
    print("+ 거래정지 복귀 포함            %+9.2f%%" % ((eq["with_resume"] - 1) * 100))
    print("+ 신규상장 첫날까지 포함        %+9.2f%%" % ((eq["with_all"] - 1) * 100))
    print("")
    for k in ("new", "resume"):
        v = buckets[k]
        if not v:
            continue
        v2 = sorted(v)
        print("%-7s 관측 %5d · 중앙 %+7.2f%% · 평균 %+7.2f%% · P90 %+8.2f%% · 최대 %+9.2f%%"
              % (k, len(v), v2[len(v2) // 2] * 100, st.mean(v) * 100,
                 v2[int(len(v2) * 0.9)] * 100, v2[-1] * 100))


if __name__ == "__main__":
    main()
