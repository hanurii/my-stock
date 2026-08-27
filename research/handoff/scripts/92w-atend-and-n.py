# -*- coding: utf-8 -*-
r"""92w — 94 를 돌리기 «전»에 두 가지를 «공짜로» 재 둔다. (검증 세션 `fb21b5a0`)

① **`at_end` 비율** — 목표·손절 어느 것도 안 닿고 «경로가 끝나» 마지막 종가로 정산된 비율.
   `41-round1-exits.py` 가 이렇게 결착한다:
       return (d[n-1], "unresolved", [(d[n-1], 1.0, g(c[n-1]))], True, …)
   **빠지는 게 아니라 마지막 프린트로 정산된다 — 손실이 사라지지 않는다.** ✅
   🚨 **그런데 적자 회사에선 «낙관» 쪽이다** — 파산은 대개 거래정지 → 상폐로 가고
      **마지막 프린트가 0 이 아니다.** 잔존가치와의 차이만큼 장부가 후하게 잡히고,
      **방향이 92 의 통과 칸에 «유리»하다.**
   → `roe 1분위` 가 나머지보다 크게 높으면 **그 칸 성과의 상당 부분이 «자료가 끝나서» 난 값**이다.

② **층화 표의 «사건 수»** — 앞 판(92v)은 n 만 찍고 «사건 수»를 안 찍었다.
   ①조용·④매우큼이 음수라 「뒤집힌 U 자」로 보이는데, **사건이 몇 개인지 모르면
   «중간에서만 값을 한다»인지 «꼬리가 널뛴 것»(유형 19′)인지 못 가린다.**

🚨 **여기서 «실현 수익»은 안 잰다.** 그건 94 의 결과 변수이고, 등록 «전»에 보면 그때 창이 사라진다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                       # noqa: E402

_s = _u.spec_from_file_location("m92", HERE / "92-us-fundamentals.py")
m = _u.module_from_spec(_s)
_s.loader.exec_module(m)


def build_with_end(years, d0, d1, fund):
    """92.build 와 «같은» 절차 + `at_end` 를 함께 담는다."""
    by0 = {}
    for y in years:
        f = m.SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
        by0[y] = [p for p in ps if d0 <= p["entry_date"] <= d1]
    rows = []
    for y in sorted(by0):
        open_until = {}
        for p in by0[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=m.r91.STOP,
                                 target=m.r91.TARGET, shares=(1.0,), add_stop="floor_entry")
            mk = t["masks"][()]
            open_until[c] = mk["resolve_date"] or p["entry_date"]
            epx = p.get("entry_price") or p.get("entry_px")
            hs = p.get("h") or []
            if not epx or not hs:
                continue
            rec = fund.get(c)
            if not rec:
                continue
            arq = rec["ARQ"]
            j = m.asof_idx(arq, p["entry_date"])
            if j < 0:
                continue
            lag = m._ord(p["entry_date"]) - m._ord(arq[j][0])
            if lag > m.STALE_MAX or j < 5:
                continue
            f8 = m.feats_at(arq, j)
            art = rec.get("ART") or []
            k = m.asof_idx(art, p["entry_date"]) if art else -1
            if k >= 0 and m._ord(p["entry_date"]) - m._ord(art[k][0]) <= m.STALE_MAX:
                v = art[k][m.IX["roe"]]
                f8["roe"] = m.NAN if m._nan(v) else v
            f8["_band"] = p.get("atr_band")
            mfe = (max(hs) / epx - 1.0) * 100.0
            rows.append((f8, 1.0 if mfe >= m.TARGET else 0.0,
                         1.0 if mfe >= m.DOUBLE else 0.0,
                         bool(mk.get("at_end")), mk.get("result"), len(hs)))
    return rows


def main() -> int:
    print("=" * 104, flush=True)
    print("92w — ① at_end(경로 끝 정산) 비율   ② 층화 표의 «사건 수»   (서술 · 판정에 안 씀)",
          flush=True)
    print("=" * 104, flush=True)
    fund = json.loads(m.FUND.read_text(encoding="utf-8"))["by"]
    packs = []
    for lab, (d0, d1), yrs in (("고르기", m.PICK, range(1999, 2013)),
                               ("판정①", m.TEST1, range(2012, 2018)),
                               ("판정②", m.TEST2, range(2017, 2027))):
        packs.append((lab, build_with_end(tuple(yrs), d0, d1, fund)))
        print("  %s 진입 %s" % (lab, "{:,}".format(len(packs[-1][1]))), flush=True)

    rowsP = packs[0][1]
    fq, want, _nc = (lambda t: (t[2], 0, t[1]))(m.cells_for(rowsP, "roe"))
    fd, wantd, _ = (lambda t: (t[2], 4, t[1]))(m.cells_for(rowsP, "dilution"))

    print("\n" + "=" * 104, flush=True)
    print("① at_end — «목표·손절 어느 것도 안 닿고 경로가 끝나» 마지막 종가로 정산된 비율", flush=True)
    print("   %-8s %-16s %8s %10s %10s" % ("창", "무리", "n", "at_end", "결과 미결"), flush=True)
    print("   " + "-" * 60, flush=True)
    for lab, rows in packs:
        groups = [("전체", lambda r: True),
                  ("roe 1분위", lambda r: fq(r[0]["roe"]) == want),
                  ("roe 나머지", lambda r: fq(r[0]["roe"]) != want and not m._nan(r[0]["roe"])),
                  ("dilution 5분위", lambda r: fd(r[0]["dilution"]) == wantd)]
        for gn, gf in groups:
            g = [r for r in rows if gf(r)]
            if not g:
                continue
            ae = sum(1 for r in g if r[3]) / len(g)
            un = sum(1 for r in g if r[4] == "unresolved") / len(g)
            print("   %-8s %-16s %8s %9.2f%% %9.2f%%"
                  % (lab, gn, "{:,}".format(len(g)), 100 * ae, 100 * un), flush=True)
        print("   " + "-" * 60, flush=True)

    print("\n" + "=" * 104, flush=True)
    print("② 층화 표 — 더블 도달률에 «사건 수»를 함께 (92v 가 빠뜨린 줄)", flush=True)
    for lab, rows in packs:
        print("\n   ### %s" % lab, flush=True)
        bc = sorted({r[0]["_band"] for r in rows if r[0]["_band"]})
        for bk in bc:
            g = [r for r in rows if r[0]["_band"] == bk and not m._nan(r[0]["roe"])]
            ins = [r for r in g if fq(r[0]["roe"]) == want]
            out = [r for r in g if fq(r[0]["roe"]) != want]
            if len(ins) < 30 or len(out) < 30:
                print("      %-12s (칸이 작아 못 잼: 안 %d · 밖 %d)" % (bk, len(ins), len(out)),
                      flush=True)
                continue
            pi, po = st.mean(r[2] for r in ins), st.mean(r[2] for r in out)
            ei, eo = sum(r[2] for r in ins), sum(r[2] for r in out)
            print("      %-12s 안 %5.2f%% (n=%5d · **사건 %4d**) vs 밖 %5.2f%% (n=%5d · 사건 %4d)"
                  "   차 %+5.2f%%p" % (bk, 100 * pi, len(ins), int(ei),
                                       100 * po, len(out), int(eo), 100 * (pi - po)), flush=True)
    print("\n  🚨 사건이 «수십 개»면 그 칸의 차는 못 읽는다(유형 19′). 「뒤집힌 U 자」로 읽기 전에 본다.",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
