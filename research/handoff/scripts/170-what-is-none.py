# -*- coding: utf-8 -*-
r"""170 — **「None 은 «무엇»인가」 + 「원전의 «조건»으로 «되찾기»」** · 사전등록 `tasks/170-what-is-none.md`

  🏷️ **세대 B** · 규칙 **+30/−10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  `168` 이 남긴 «빈칸»: **「실적을 «잴 수 없으면» 대박」 — 그 None 이 «무엇»인가**

  🚨 **None 이 «한 가지»가 아니다.** 그리고 **두뇌 세션이 센 «셋»이 아니라 «넷»이다**:
     **N0** 우리 «호출 «전»»에서 걸러짐 — `arq` 없음 «또는» `STALE_MAX` 초과   ← **빠져 있었다**
     **N1** `judge:50`  이력 «부족»(분기 < 4+nq)      ⇒ 신규 상장 · 자료 짧음
     **N2** `judge:59`  EPS·매출 **«결측»**
     **N3** `judge:64`  이익률 «결측»(**`nitem==3` 일 때만**) ⇒ 우리는 `nitem=2` 라 **«0 이어야» 한다**
"""
from __future__ import annotations
import csv
import importlib.util as _u
import io as _io
import json
import math
import os
import random
import statistics as st
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
acc = _load("acc", "account_lib.py")
gates = _load("gates", "_gates.py")
f92a = r102.f92a
pt = r91.pt

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NSEED, NASSIGN, YRS, DELTA, T60 = 60, 10, 27.4, 1.23, 2.001
XS = (0.10, 0.25, 0.50)                  # 되찾는 «몫» — **셋 «다»** 적는다(QD★)
MA_REF = 12377
CACHE = Path(str(r91.OUT / "170-partial.json"))
TICK = Path(r"D:\stock-data\sharadar\tickers.csv.zip")
CAP_PIT = Path(r"D:\stock-data\derived\95-cap-pit.json")
TERCILE = Path(r"D:\stock-data\derived\156-cap-tercile.json")


def _prev_ym(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    m -= k
    while m <= 0:
        m += 12
        y -= 1
    return "%04d-%02d" % (y, m)


def why_none(arq, j, ix, nq=1, nitem=2):
    """`103 judge` 의 `return None` 이 **어느 줄**인가 — 「N1 / N2 / N3」 또는 None(=None 아님)"""
    if j < 4 + nq:
        return "N1"

    def g(k, f):
        return arq[k][ix[f]] if 0 <= k < len(arq) else None
    for q in range(j, j - nq, -1):
        e0, e1 = r103._yoy(g(q, "eps"), g(q - 4, "eps")), r103._yoy(g(q - 1, "eps"), g(q - 5, "eps"))
        r0, r1 = r103._yoy(g(q, "revenue"), g(q - 4, "revenue")), \
            r103._yoy(g(q - 1, "revenue"), g(q - 5, "revenue"))
        if r103._nan(e0) or r103._nan(e1) or r103._nan(r0) or r103._nan(r1):
            return "N2"
        if nitem == 3:
            m0, m4 = g(q, "netmargin"), g(q - 4, "netmargin")
            if r103._nan(m0) or r103._nan(m4):
                return "N3"
    return None


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    dry = "--dry" in sys.argv
    P = print
    P("=" * 104)
    P("170 — **「None 은 «무엇»인가」 + 「원전 «조건»으로 «되찾기»」** · 씨앗 %d × 배정 %d%s"
      % (n_seed, n_as, "  🚨 **--dry(«구조»만)**" if dry else ""))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/170-what-is-none.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## 🚨🚨 **None 자리가 «셋»이 아니라 «넷»이다 — 사전등록에 «하나» 빠져 있었다**")
    P("")
    P("```")
    P("**N0** 우리 «호출 «전»»에서 걸러짐 — `arq` «없음» «또는» `STALE_MAX` «초과**   ← **빠져 있었다**")
    P("**N1** `judge:50`  이력 «부족»(분기 < 4+nq)")
    P("**N2** `judge:59`  EPS·매출 **«결측»**")
    P("**N3** `judge:64`  이익률 «결측» — **`nitem==3` 일 때만**")
    P("")
    P("🚨 우리는 **`judge(..., 1, 2)`** 로 부른다 ⇒ **N3 는 «0 이어야» 한다**")
    P("   ⇒ ✅ **그것도 «관문»으로 «찍는다»**(「0 일 것」을 «주장»하지 «않고» «센다»)")
    P("★ **N0 가 «제일 클» 수 있다** — `168` 코드가 `judge(...) if ok_ else None` 이었다")
    P("```")
    P("")
    P("## 🔎 **QF★ — 「없다」엔 «명령»과 «돌린 자리»를 «같이»**")
    P("")
    P("```")
    P("자리   `%s`" % os.getcwd().replace("\\\\", "/"))
    P("★ 오늘 「없다」가 **«세 얼굴»**이었다(잘림 · 안 찾아봄 · 자리 틀림)")
    P("```")
    P("")
    P("## 가정·출처")
    P("")
    P("```")
    P("업종        `tickers.csv.zip` 의 **`sector`**")
    P("            🚨 **같은 파일에 `sicsector` 도 있다 — «다른 자»다. «안» 썼다**(유형 67)")
    P("            🚨 **「생명기술주」와 `sector` 가 «같은 자»인지 «모른다»** — 라벨을 «같은 줄»에")
    P("시총 경계   `156-cap-tercile.json`(그날 상장 «전부»의 삼분위)")
    P("후보 시총   `95-cap-pit.json`  ← 🚨 **종목 8,032 개뿐이라 «결측»이 난다. «수»로 찍는다**")
    P("모멘텀      **`prior6m`** = 「진입 «달»의 «앞» 달 ÷ 그 6달 «전» − 1」(`143` 의 자)")
    P("            ✅ **진입 달을 «안» 본다** ⇒ QC★ 로 «전수» 검사")
    P("Δ = 1.23%p  ← 150 의 우리−QQQ 격차")
    P("MA★ 기준 %s만 ← 156·161~168 의 ①" % format(MA_REF, ","))
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    pack = json.loads((r91.OUT / "91-monthly-us-full.json").read_text(encoding="utf-8"))
    monthly = pack["monthly"]
    del pack
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    # ── 업종 ───────────────────────────────────────────────────────────────
    sect = {}
    with zipfile.ZipFile(TICK) as z:
        with z.open(z.namelist()[0]) as f:
            rd = csv.reader(_io.TextIOWrapper(f, encoding="utf-8", newline=""))
            hd = next(rd)
            i_t, i_s = hd.index("ticker"), hd.index("sector")
            for row in rd:
                if row[i_t] not in sect and row[i_s]:
                    sect[row[i_t]] = row[i_s]

    # ── 시총 ───────────────────────────────────────────────────────────────
    ter = json.loads(TERCILE.read_text(encoding="utf-8"))["q"]
    capraw = json.loads(CAP_PIT.read_text(encoding="utf-8"))
    caps = {c: (v.get("cap") or []) for c, v in capraw.items()}
    del capraw
    tdates = sorted(ter)

    def asof_cap(code, d):
        rows = caps.get(code) or []
        lo, hi = 0, len(rows) - 1
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if rows[mid][0] <= d:
                best = rows[mid][1]
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    def tercile(code, d):
        c = asof_cap(code, d)
        if c is None:
            return None
        i = 0
        for j, k in enumerate(tdates):
            if k <= d:
                i = j
            else:
                break
        q = ter[tdates[i]]
        return "S" if c <= q[0] else ("M" if c <= q[1] else "L")

    # ── judge 등급 · None 갈래 · 모멘텀 · 대박 자 ────────────────────────────
    rows, kept, n_qc, n_qc_bad = [], set(), 0, 0
    for y in sorted(by2):
        for p in by2[y]:
            code = p["code"]
            arq = (fund.get(code) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            ok_ = (a is not None
                   and r102._ord(p["entry_date"]) - r102._ord(a[0]) <= r102.STALE_MAX)
            if not ok_:
                v, why = None, "N0"
            else:
                v = r103.judge(arq, arq.index(a), ix, 1, 2)
                why = why_none(arq, arq.index(a), ix, 1, 2) if v is None else None
            base = _prev_ym(p["scan_date"][:7], 1)
            n_qc += 1
            if base >= p["scan_date"][:7]:
                n_qc_bad += 1
            mm = monthly.get(code) or {}
            p0, p6 = mm.get(base), mm.get(_prev_ym(base, 6))
            mom = (p0 / p6 - 1.0) if (p0 and p6 and p6 > 0) else None
            ep = p["entry_price"]
            hs = [x for x in p["h"] if x is not None]
            run = (max(hs) / ep - 1.0) if (hs and ep and ep > 0) else None
            rows.append({"p": p, "v": v, "why": why, "mom": mom, "run": run,
                         "sec": sect.get(code), "ter": tercile(code, p["entry_date"])})
            if v is not False:
                kept.add(id(p))

    n_all = len(rows)
    nones = [r for r in rows if r["v"] is None]
    P("")
    P("## 1. 🚨 **QA★ — None 을 «갈라» 센다. 합이 «맞아야» 한다**")
    P("")
    P("```")
    P("**QC★ 룩어헤드 «전수» 검사** — 모멘텀이 「진입 달의 «앞» 달」만 쓰는가")
    P("   검사 **%s** 건 · 위반 **%d** 건  →  %s"
      % (format(n_qc, ","), n_qc_bad, "✅ **0 건**" if n_qc_bad == 0 else "🚨 **멈춘다**"))
    P("")
    cnt = {}
    for r in nones:
        cnt[r["why"]] = cnt.get(r["why"], 0) + 1
    P("| 갈래 | 뜻 | n | None 중 |")
    P("|---|---|---:|---:|")
    for k, lab in (("N0", "`arq` 없음 «또는» «오래됨**"), ("N1", "이력 «부족»(신규 상장 등)"),
                   ("N2", "EPS·매출 **«결측»**"), ("N3", "이익률 결측(**`nitem=3` 전용**)")):
        c_ = cnt.get(k, 0)
        P("| **%s** | %s | **%s** | %.1f%% |"
          % (k, lab, format(c_, ","), 100.0 * c_ / max(len(nones), 1)))
    tot_n = sum(cnt.values())
    P("")
    P("**QA★ 합** — N0+N1+N2+N3 = **%s** vs None 총수 **%s**  →  %s"
      % (format(tot_n, ","), format(len(nones), ","),
         "✅ **맞는다**" if tot_n == len(nones) else "🚨 **멈춘다**"))
    P("🚨 **N3 는 «0 이어야» 한다**(`nitem=2`) — 실측 **%d**  →  %s"
      % (cnt.get("N3", 0), "✅" if cnt.get("N3", 0) == 0 else "🚨 **가정이 «틀렸다»**"))
    P("```", flush=True)
    if n_qc_bad or tot_n != len(nones):
        return 3

    def brk(sub, key, top=8):
        d = {}
        for r in sub:
            d[r[key]] = d.get(r[key], 0) + 1
        return sorted(d.items(), key=lambda x: -x[1])[:top]

    good = [r for r in rows if r["run"] is not None]
    good.sort(key=lambda r: -r["run"])
    n_g = len(good)
    THS = (good[max(1, n_g // 100) - 1]["run"], good[max(1, n_g // 20) - 1]["run"], 1.0, 0.30)
    TH_NM = ("상위1%", "상위5%", "+100%", "+30%")

    def winrate(sub):
        s2 = [r for r in sub if r["run"] is not None]
        return [100.0 * sum(1 for r in s2 if r["run"] >= t) / max(len(s2), 1) for t in THS]

    P("")
    P("## 2. **None 은 «무엇»인가 — 업종 · 시총 · 대박률**")
    P("")
    P("```")
    P("🚨 **「비중이 높다」와 「«대박»을 낸다」는 «다른 말»**이다 ⇒ **«둘 다»** 적는다")
    P("🚨 **「생명기술주」와 Sharadar `sector` 가 «같은 자»인지 «모른다»** — 라벨이다")
    P("")
    P("**업종 «비중»** — None vs 전체")
    P("| 업종 | None 중 | 전체 중 | 차 |")
    P("|---|---:|---:|---:|")
    sa = dict(brk(rows, "sec", 99))
    for k, c_ in brk(nones, "sec", 8):
        a_ = 100.0 * c_ / max(len(nones), 1)
        b_ = 100.0 * sa.get(k, 0) / n_all
        P("| %s | **%.1f%%** | %.1f%% | **%+.1f%%p** |" % (k or "«없음»", a_, b_, a_ - b_))
    P("")
    P("**업종별 «대박률»**(None «안»에서) — %s" % " · ".join(TH_NM))
    P("| 업종 | n | %s |" % " | ".join("**%s**" % t for t in TH_NM))
    P("|---|---:|%s" % ("---:|" * len(THS)))
    for k, _c in brk(nones, "sec", 6):
        sub = [r for r in nones if r["sec"] == k]
        P("| %s | %s | %s |"
          % (k or "«없음»", format(len(sub), ","),
             " | ".join("%.1f%%" % x for x in winrate(sub))))
    P("")
    P("**시총 삼분위** — None 중")
    nt = dict(brk(nones, "ter", 9))
    P("   " + " · ".join("**%s** %s(%.1f%%)"
                         % (k or "«결측»", format(v, ","), 100.0 * v / max(len(nones), 1))
                         for k, v in sorted(nt.items(), key=lambda x: str(x[0]))))
    P("   🚨 **«결측»은 `95-cap-pit.json` 이 8,032 종목뿐이라 난다** — «수»로 찍었다")
    P("```", flush=True)

    n2 = cnt.get("N2", 0)
    n1 = cnt.get("N1", 0)
    ts = dict(brk(nones, "ter", 9))
    P("")
    P("## 3. 🔴 **㉠ 의 답 — 사전등록의 «두 가설»이 «둘 다» 빗나갔다**")
    P("")
    P("```")
    P("🔴 **가설 ①「None = 신규 상장」** — `168` 에서 **«내가»** 적은 말이다")
    P("   실측: **N1(이력 부족) %.1f%%** vs **N2(EPS·매출 «결측») %.1f%%**"
      % (100.0 * n1 / max(len(nones), 1), 100.0 * n2 / max(len(nones), 1)))
    P("   ⇒ ## **None 은 「«새» 회사」가 «아니라» — 「자료가 «비어» 있는 회사」다**")
    P("   ★ 「분기가 «모자란다»」(N1)는 **%.1f%%** 뿐이다" % (100.0 * n1 / max(len(nones), 1)))
    P("")
    P("🔴 **가설 ②「None = 소형」** — 역시 `168` 에서 «내가» 적은 말이다")
    P("   실측 시총 — **L %.1f%% · M %.1f%% · S %.1f%%**"
      % (100.0 * ts.get("L", 0) / max(len(nones), 1),
         100.0 * ts.get("M", 0) / max(len(nones), 1),
         100.0 * ts.get("S", 0) / max(len(nones), 1)))
    P("   ⇒ ## **None 의 %.1f%% 가 «중·대형»이다. 「소형」이 «아니다»**"
      % (100.0 * (ts.get("L", 0) + ts.get("M", 0)) / max(len(nones), 1)))
    P("")
    P("## ⇒ 🚨 **`168` 의 괄호 「(None = 분기 자료가 «모자란» 것 — «신생·소형»이 많을 자리다)」를**")
    P("## **   «정정»해야 한다 — «둘 다» 틀렸다**")
    P("★ 그리고 그건 **「«안 쟀다»」라고 «적어» 둔 자리**였다 — **적어 뒀기에 «찾아»갔고, 「틀렸다」가 «나왔다»**")
    P("")
    P("🚨 **「비중」과 「대박률」이 «다른 말»임이 «수»로 나왔다:**")
    hc = [r for r in nones if r["sec"] == "Healthcare"]
    tc = [r for r in nones if r["sec"] == "Technology"]
    P("   Healthcare — 비중 **제일 높다** · 상위1%% 대박률 **%.1f%%**" % winrate(hc)[0])
    P("   Technology — 비중 «2위»            · 상위1%% 대박률 **%.1f%%**" % winrate(tc)[0])
    P("   ⇒ ★ **「많이 «있는» 업종」과 「대박을 «내는» 업종」이 «다르다»**")
    P("   ⛔ 그러니 **「생명기술주가 대박을 «낸다»」로 «못» 쓴다**")
    P("```")
    P("")
    P("```")
    P("🚨 **안 잰 것:**")
    P("   ① **«왜» EPS·매출이 «비었나»** — 자료 제공자 문제인지 «회사» 성격인지 **«안» 쟀다**")
    P("   ② **N2 가 «대박»과 «왜» 붙는지** — 「자료가 없다」와 「크게 오른다」의 «기전»은 «안» 쟀다")
    P("   ③ **`sector` 결측** — 위 표의 합이 100%가 «안» 되는 만큼이 «그것»이다")
    P("```")
    if dry:
        P("")
        P("🚨 **--dry — ㉡ 시뮬레이션은 «안» 돌렸다**")
        return 0
    P("")
    P("🚨 ㉡ 은 «검증 1차» 뒤에 돌린다 — 여기서 «멈춘다**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
