# -*- coding: utf-8 -*-
r"""95a — 시가총액·거래대금을 **진입 «전날» 축**으로 세운다. 사전등록 `tasks/95-marketcap.md`.

🚨 관문 ① — **`date < 진입일` 인 것 중 가장 늦은 것.** 진입일 «당일» 값을 쓰면 룩어헤드다.
   [[megacap-momentum-refuted]] — **시총 하루짜리 룩어헤드만 10.1%p** 를 만든 적이 있다.
🚨 관문 ②′ — **신선도 상한 10 거래일(=14 달력일)**. 넘으면 «제외»하고 «세어서» 찍는다.

자료가 **정렬돼 있지 않다**(실측: `daily` 200만 행에 날짜 역행 33만 회).
→ 필요한 (종목, 날짜)만 **골라 담는다**. 한 번 훑고 창 밖은 버린다.

내는 것: `D:\stock-data\derived\95-cap-pit.json`
  {code: {"cap": [[date, marketcap], …], "tov": [[date, close*volume], …]}}
"""
from __future__ import annotations

import bisect
import csv
import datetime as _dt
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(r"D:\stock-data\sharadar")
DERIVED = Path(r"D:\stock-data\derived")
OUT = DERIVED / "95-cap-pit.json"
SUB = ROOT / ".cache" / "bt5y" / "sub"

YEARS = tuple(range(1999, 2027))
CAP_BACK = 14          # 시총 — 진입 전 14 달력일(≈10 거래일) 안의 것만
TOV_BACK = 40          # 거래대금 — 20 거래일 평균을 만들려면 ≈40 달력일


def _ord(d):
    return _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


def needed():
    """모든 경로의 (종목 → 진입일 서수 정렬 목록)."""
    need = defaultdict(set)
    n = 0
    for y in YEARS:
        f = SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        for p in json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]:
            need[p["code"]].add(_ord(p["entry_date"]))
            n += 1
    out = {t: sorted(s) for t, s in need.items()}
    print("경로 %s건 · 종목 %d개 · 서로 다른 (종목,진입일) %s"
          % ("{:,}".format(n), len(out), "{:,}".format(sum(len(v) for v in out.values()))),
          flush=True)
    return out


def harvest(zpath, need, back, cols, label):
    """창 안의 행만 골라 담는다. cols=(값을 만드는 함수, 필요한 열 이름들)."""
    fn, names = cols
    keep = defaultdict(list)
    rows = kept = 0
    with zipfile.ZipFile(zpath) as z:
        nm = z.infolist()[0].filename
        f = io.TextIOWrapper(z.open(nm), encoding="utf-8", errors="replace", newline="")
        hdr = f.readline().rstrip("\r\n").split(",")
        iT, iD = hdr.index("ticker"), hdr.index("date")
        idx = [hdr.index(x) for x in names]
        top = max([iT, iD] + idx) + 1
        for line in f:
            rows += 1
            r = line.split(",", top)
            t = r[iT]
            ns = need.get(t)
            if ns is None:
                continue
            d = r[iD]
            do = _ord(d)
            # 이 날짜 «뒤»에 오는 첫 진입일과의 거리가 창 안인가 (그리고 d < 진입일)
            pos = bisect.bisect_right(ns, do)
            if pos >= len(ns) or ns[pos] - do > back:
                continue
            try:
                v = fn([r[i] for i in idx])
            except (ValueError, IndexError):
                continue
            if v is None:
                continue
            keep[t].append((d, v))
            kept += 1
            if rows % 10_000_000 == 0:
                print("   %s: %s만 행 …" % (label, "{:,}".format(rows // 10000)), flush=True)
    for t in keep:
        keep[t].sort()
    print("   %s: 전체 %s행 → **담은 것 %s행** · 종목 %d개"
          % (label, "{:,}".format(rows), "{:,}".format(kept), len(keep)), flush=True)
    return keep


def main() -> int:
    DERIVED.mkdir(parents=True, exist_ok=True)
    need = needed()

    def _cap(v):
        x = float(v[0]) if v[0] not in ("", None) else None
        return x if (x is not None and x > 0) else None

    def _tov(v):
        c, q = float(v[0]), float(v[1])
        return c * q if (c > 0 and q > 0) else None

    print("\n① 시가총액 (daily.csv.zip · 진입 전 %d일 창)" % CAP_BACK, flush=True)
    cap = harvest(SRC / "daily.csv.zip", need, CAP_BACK, (_cap, ["marketcap"]), "daily")

    print("\n② 거래대금 = 종가 × 거래량 (stocks.csv.zip · 진입 전 %d일 창)" % TOV_BACK, flush=True)
    tov = harvest(SRC / "stocks.csv.zip", need, TOV_BACK, (_tov, ["close", "volume"]), "stocks")

    out = {}
    for t in set(cap) | set(tov):
        out[t] = {"cap": cap.get(t, []), "tov": tov.get(t, [])}
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("\n저장: %s (%.0f MB)" % (OUT, OUT.stat().st_size / 1e6), flush=True)

    # ── 관문 ⑥ 덮개율을 «세어서» 찍는다 ──────────────────────────────────
    miss = Counter()
    lags = []
    for t, ns in need.items():
        rec = out.get(t)
        cs = rec["cap"] if rec else []
        ds = [d for d, _v in cs]
        for no in ns:
            if not ds:
                miss["시총 자료 없음"] += 1
                continue
            i = bisect.bisect_left(ds, _dt.date.fromordinal(no).isoformat()) - 1
            if i < 0:
                miss["진입 전 시총 없음"] += 1
                continue
            lag = no - _ord(ds[i])
            if lag > CAP_BACK:
                miss["시총이 %d일 넘게 묵음" % CAP_BACK] += 1
                continue
            lags.append(lag)
    tot = sum(len(v) for v in need.values())
    print("\n관문 ⑥ 덮개율 — (종목,진입일) %s 중" % "{:,}".format(tot), flush=True)
    print("   **시총이 붙는 것 %s (%.2f%%)**"
          % ("{:,}".format(len(lags)), 100.0 * len(lags) / tot), flush=True)
    for k, v in miss.most_common():
        print("   제외 %-22s %s (%.2f%%)" % (k, "{:,}".format(v), 100.0 * v / tot), flush=True)
    if lags:
        lags.sort()
        print("   시총 신선도 — 중앙 %d일 · P90 %d일 · 최대 %d일"
              % (lags[len(lags) // 2], lags[int(len(lags) * .9)], lags[-1]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
