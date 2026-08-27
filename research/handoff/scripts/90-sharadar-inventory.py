# -*- coding: utf-8 -*-
"""90 — Sharadar 전체 이력 재고 검산.

목적: 「무엇이 얼마나 있는가」를 **세어서** 적는다. 자료를 쓰기 «전»에 한다.
🚨 [[verification-failure-modes]] 질문 12 — 숫자에 넷(값·커밋된 스크립트·커밋된 입력·정의).
   이 파일이 그 「커밋된 스크립트」다.
"""
import io
import os
import sys
import zipfile
from collections import Counter

D = os.environ.get("SHARADAR_DIR", r"D:\stock-data\sharadar")

# 표 → (티커 열, 날짜 열)  ※ 열 «이름»으로 찾는다(자리로 찾으면 조용히 틀린다)
SPEC = {
    "stocks":          ("ticker", "date"),
    "daily":           ("ticker", "date"),
    "fundamentals":    ("ticker", "date"),      # date = «공시일»(SEC 제출일)
    "actions":         ("ticker", "date"),
    "events":          ("ticker", "date"),
    "metrics":         ("ticker", "date"),
    "sp500":           ("ticker", "date"),
    "holdings_ticker": ("ticker", "date"),
    "tickers":         ("ticker", None),
}


def scan(table, tcol, dcol):
    p = os.path.join(D, table + ".csv.zip")
    if not os.path.exists(p):
        return {"table": table, "err": "파일 없음"}
    n = 0
    lo, hi = "9999", "0000"
    tick = set()
    byyear = Counter()
    extra = Counter()
    with zipfile.ZipFile(p) as z:
        nm = z.infolist()[0].filename
        f = io.TextIOWrapper(z.open(nm), encoding="utf-8", newline="")
        hdr = f.readline().rstrip("\r\n").split(",")
        ti = hdr.index(tcol)
        di = hdr.index(dcol) if dcol else None
        # 부가 축: fundamentals 는 dimension 분포를 함께 센다
        xi = hdr.index("dimension") if "dimension" in hdr else None
        for line in f:
            # ★ 값에 콤마가 든 열(name 등)이 뒤에 있으므로 **앞쪽 열만** split 한다.
            parts = line.split(",", max(ti, di or 0, xi or 0) + 1)
            n += 1
            tick.add(parts[ti])
            if di is not None:
                d = parts[di]
                if d < lo:
                    lo = d
                if d > hi:
                    hi = d
                byyear[d[:4]] += 1
            if xi is not None:
                extra[parts[xi]] += 1
    return {"table": table, "rows": n, "tickers": len(tick),
            "lo": lo if dcol else "-", "hi": hi if dcol else "-",
            "byyear": byyear, "extra": extra}


if __name__ == "__main__":
    only = sys.argv[1:] or list(SPEC)
    for t in only:
        tcol, dcol = SPEC[t]
        r = scan(t, tcol, dcol)
        if "err" in r:
            print("%-16s 🚨 %s" % (t, r["err"]), flush=True)
            continue
        print("%-16s 행 %12s · 종목 %6s · %s ~ %s"
              % (t, "{:,}".format(r["rows"]), "{:,}".format(r["tickers"]),
                 r["lo"], r["hi"]), flush=True)
        if r["byyear"]:
            ys = sorted(r["byyear"])
            head = " ".join("%s:%s" % (y, "{:,}".format(r["byyear"][y])) for y in ys[:6])
            tail = " ".join("%s:%s" % (y, "{:,}".format(r["byyear"][y])) for y in ys[-4:])
            print("     앞: %s" % head, flush=True)
            print("     뒤: %s" % tail, flush=True)
        if r["extra"]:
            print("     dimension: %s" % dict(r["extra"]), flush=True)
