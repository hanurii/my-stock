# -*- coding: utf-8 -*-
r"""158a — **배당 비율표**를 만든다 (158 의 부품) · 사전등록 `tasks/158-dividend-parity.md`

  🚨 우리 주식은 `close`(분할 조정 · **배당 «미»조정**), 지수는 `closeadj`(**총수익**).
     ⇒ **자가 다르다.** 이 부품은 «다리마다» 배당 몫을 낼 «비율»을 뽑아 둔다.

  ★ 배당 몫(한 다리) = (adj_청산/adj_진입) ÷ (close_청산/close_진입) − 1
    = (r_청산 / r_진입) − 1,   r = closeadj / close
  ⇒ 그러니 **필요한 것은 (종목, 날짜) → r «하나»뿐**이다.

  ⛔ **검출기를 «한 글자도» 안 건드린다** — 시계열을 `closeadj` 로 «바꾸지 않는다».
     (배당 계수가 시간에 따라 커져 52주 신고가·이동평균·피벗이 «다 움직인다»)

  내는 것: `D:\stock-data\derived\158-divratio.json`
     {"r": {"TICKER|YYYY-MM-DD": r}, "tsla": [...], "miss": …, "n": …}
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


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
f92a = r102.f92a
pt = r91.pt

SRC = Path(r"D:\stock-data\sharadar\stocks.csv.zip")
OUT = Path(r"D:\stock-data\derived\158-divratio.json")
NEED = Path("D:/stock-data/derived/158-need.json")
# 🚨 «두 무거운 일»을 가른다 — 1단계 사다리+resolve · 2단계 stocks.csv 훑기
#    (배경 판에 «시간 한도»가 있어 한 호출에 둘 다는 «안 끝난다»)
D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF = 30.0, 10.0, 0.5


def main() -> int:
    print("=" * 96)
    print("158a — **배당 비율표** (종목·날짜 → closeadj/close)")
    print("=" * 96, flush=True)
    if NEED.exists() and "--scan" in sys.argv:
        d = json.loads(NEED.read_text(encoding="utf-8"))
        print("  ♻️ 1단계 갈무리 이어받음 — 거래 %d · 종목 %d" % (d["ntr"], len(d["need"])),
              flush=True)
        return _scan({k: set(v) for k, v in d["need"].items()}, d["ntr"])

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    # 🚨 1단계도 «한 호출»에 안 끝난다 — **해마다** 갈무리하고 이어받는다
    if NEED.exists():
        d0_ = json.loads(NEED.read_text(encoding="utf-8"))
        need = {k: set(v) for k, v in d0_["need"].items()}
        ntr, done_y = d0_["ntr"], set(d0_.get("years") or [])
        print("  ♻️ 1단계 이어받음 — 해 %d개 · 거래 %d" % (len(done_y), ntr), flush=True)
    else:
        need, ntr, done_y = {}, 0, set()
    for y in sorted(by2):
        if y in done_y:
            continue
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is False:
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            m = t["masks"][()]
            ntr += 1
            need.setdefault(t["code"], set()).add(t["entry_date"])
            for e in (m.get("exits") or []):
                need[t["code"]].add(e[0])
        done_y.add(y)
        NEED.parent.mkdir(parents=True, exist_ok=True)
        NEED.write_text(json.dumps({"need": {k: sorted(v) for k, v in need.items()},
                                    "ntr": ntr, "years": sorted(done_y)},
                                   separators=(",", ":")), encoding="utf-8")
        print("     %d 년 — 누적 거래 %d" % (y, ntr), flush=True)
    if len(done_y) < len(by2):
        print("  ⏸️ %d/%d 해 — 다시 부르면 이어서 합니다" % (len(done_y), len(by2)), flush=True)
        return 0
    npair = sum(len(v) for v in need.values())
    print("  거래 **%d** · 필요한 (종목,날짜) 짝 **%s** · 종목 **%d**"
          % (ntr, format(npair, ","), len(need)), flush=True)
    NEED.parent.mkdir(parents=True, exist_ok=True)
    NEED.write_text(json.dumps({"need": {k: sorted(v) for k, v in need.items()}, "ntr": ntr},
                               separators=(",", ":")), encoding="utf-8")
    print("  ✅ 1단계 저장 — 다시 부르면 «훑기»부터 합니다", flush=True)
    if "--need" in sys.argv:
        return 0
    return _scan(need, ntr)


def _scan(need, ntr):
    npair = sum(len(v) for v in need.values())
    print("")
    print("## 2단계 — `stocks.csv` 한 번 훑기", flush=True)

    # ── 한 번 훑기 ────────────────────────────────────────────────────────
    got, tsla, rows = {}, [], 0
    with zipfile.ZipFile(SRC) as z:
        nm = z.namelist()[0]
        with z.open(nm) as f:
            rd = csv.reader(_io.TextIOWrapper(f, encoding="utf-8", newline=""))
            hdr = next(rd)
            i_t, i_d = hdr.index("ticker"), hdr.index("date")
            i_c, i_a = hdr.index("close"), hdr.index("closeadj")
            for row in rd:
                rows += 1
                tk = row[i_t]
                if tk == "TSLA":
                    try:
                        c0, a0 = float(row[i_c]), float(row[i_a])
                        if c0 > 0:
                            tsla.append((row[i_d], a0 / c0))
                    except ValueError:
                        pass
                s = need.get(tk)
                if not s or row[i_d] not in s:
                    continue
                try:
                    c0, a0 = float(row[i_c]), float(row[i_a])
                except ValueError:
                    continue
                if c0 > 0:
                    got["%s|%s" % (tk, row[i_d])] = a0 / c0
                if rows % 5_000_000 == 0:
                    print("     … %s 행" % format(rows, ","), flush=True)
    print("  훑은 행 **%s** · 얻은 짝 **%s** (%.1f%%)"
          % (format(rows, ","), format(len(got), ","), 100.0 * len(got) / max(npair, 1)),
          flush=True)

    # ── DC★ 양성 대조 — 무배당 종목의 비가 «정확히» 1 인가 ─────────────────
    print("")
    print("## 관문 DC★ — **양성 대조: 무배당 TSLA 의 `closeadj/close` 가 «정확히» 1 인가**")
    print("```")
    if tsla:
        vs = [v for _d, v in tsla]
        off = max(abs(v - 1.0) for v in vs)
        print("TSLA %s 행 · 최대 |r−1| = **%.3e** · 5:1 분할 포함 전 구간" % (format(len(vs), ","), off))
        print("⇒ %s" % ("✅ **통과** — 이 비는 «배당만» 담는다(분할은 «안» 담는다)" if off < 1e-4
                        else "🚨 **미통과 — 이 비가 «분할»도 담는다. 맞추지 말고 «왜»부터**"))
    else:
        print("🚨 TSLA 행을 «못 찾았다» — 양성 대조 «불가»")
    print("```")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"r": got, "n_need": npair, "n_trade": ntr},
                              separators=(",", ":")), encoding="utf-8")
    print("")
    print("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
