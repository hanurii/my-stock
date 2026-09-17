# -*- coding: utf-8 -*-
r"""264 - **유니버스 견줌 ＋ 「Sharadar ↔ 야후」 «이음매» 맞춰보기** (조사 세션 2026-09-10)

  ⛔ **«짓는» 일이 «아니다**. «재는» 일이다. 스킬도 파이프라인도 «안** 만든다(설계 승인 «전»).
  ⛔ 야후에서 «대량» 수집 «안** 했다 — **20종목 · 78거래일**만 받았다.

  🔴 **사용자 결정(2026-09-10)**: 「과거 데이터는 «무조건» Sharadar」
     ⇒ ㉢(RS 흔들림)은 «내려갔다** — 유니버스를 «갈아 끼우지» 않으므로 «물음»이 사라졌다.
     ⇒ ㉠㉡ 의 «쓰임»도 바뀌었다: 「RS 를 어디서 매기나」가 아니라 **「야후로 «이을» 종목 목록」**.

  🚨 **㉣ 가 «급한» 까닭**: 규약이 어긋나면 «이음매»에서 «가짜» 움직임이 난다.
     전례 — `us_loader.py` 가 비수정↔수정 «정반대» 규약으로 가짜 하루 움직임 ≥90%p 를 940종목에 냈다.

  ★ **유형 95 를 «피했다»**: 큰 종목만 맞춰 보면 **«질 수가 «없는»» 검산**이다(분할이 «없으므로»).
     그래서 **창 «안»에서 «분할이 난» 종목을 «일부러» 넣었다** — 거기서 «갈렸다».

  읽는 것(전부 저장돼 있다):
    `.cache/universe/nasdaqtraded.txt`      2026-09-10 받음 · 13,200줄
    `.cache/sharadar/tickers.csv.zip`       2026-08-24 받음
    `.cache/universe/probe_sharadar.json`   `stocks-10Y.csv.zip` 에서 뽑은 20종목 · 2026-05-01 이후
    `.cache/universe/probe_yahoo.json`      yfinance 1.2.0 · auto_adjust=False · 같은 20종목

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/264-universe-and-seam.py
"""
from __future__ import annotations

import collections
import csv
import io
import json
import statistics as st
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
PCT = chr(37)

ROOT = Path(__file__).resolve().parents[3]
UNI = ROOT / ".cache" / "universe"
NASDAQ = UNI / "nasdaqtraded.txt"
TICKERS = ROOT / ".cache" / "sharadar" / "tickers.csv.zip"

EX = {"Q": "NASDAQ", "N": "NYSE", "A": "NYSEMKT"}
CAT = {"Domestic Common Stock", "Domestic Common Stock Primary Class"}
EXS = {"NASDAQ", "NYSE", "NYSEMKT"}
SHARADAR_END = "2026-08-21"
TODAY = "2026-09-10"


def rel(a, b):
    return abs(a - b) / max(1e-12, abs(b)) * 100.0


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))]


def main() -> int:
    P("# 264 - 유니버스 견줌과 이음매 맞춰보기")
    P("")
    P("> 조사 세션 2026-09-10 · " + BQ
      + "research/handoff/scripts/264-universe-and-seam.py" + BQ)
    P("> 재는 일이다. 아무것도 짓지 않았다. 야후에서는 20종목 78거래일만 받았다.")
    P("")
    P("---")
    P("")

    # ── 1. 나스닥 목록을 우리 규칙으로 ─────────────────
    P("## 1. 나스닥 공식 목록을 우리 규칙으로 걸러 보면")
    P("")
    rows, H = [], None
    for i, ln in enumerate(NASDAQ.read_text(encoding="utf-8").splitlines()):
        p = ln.split("|")
        if i == 0:
            H = p
            continue
        if len(p) == len(H):
            rows.append(dict(zip(H, p)))
    a = [r for r in rows if r["Test Issue"] != "Y"]
    b = [r for r in a if r["ETF"] != "Y"]
    d = [r for r in b if r["Listing Exchange"] in EX]
    P("| 단계 | 남은 수 | 줄어든 수 |")
    P("|---|---:|---:|")
    prev = None
    for nm, s in (("받은 그대로", rows), ("테스트 종목 제외", a),
                  ("ETF 제외", b), ("NASDAQ·NYSE·NYSEMKT 만", d)):
        P("| %s | %s | %s |" % (nm, format(len(s), ","),
                                "" if prev is None else format(prev - len(s), ",")))
        prev = len(s)
    P("")
    cc = collections.Counter(EX[r["Listing Exchange"]] for r in d)
    P("거래소별로는 " + " · ".join("%s %s" % (k, format(v, ",")) for k, v in cc.most_common()) + " 다.")
    P("")
    P("### 못 거른 것 — 차이의 출처는 여기다")
    P("")
    P("백테스트 유니버스 규칙은 이렇다"
      + "(" + BQ + "research/handoff/results/25-us-universe.md:283-284" + BQ + ").")
    P("")
    P("```")
    P("category 가 Domestic Common Stock 또는 Domestic Common Stock Primary Class")
    P("exchange 가 NASDAQ, NYSE, NYSEMKT")
    P("siccode 가 6770(SPAC) 이 아님")
    P("```")
    P("")
    P("나스닥 목록에는 이 중 어느 것도 없다. 그래서 못 거른 것이 셋이다.")
    P("")
    P("- 우선주 · ADR · 캐나다 종목 · 2차 클래스를 못 나눈다. 열이 없다.")
    P("- SPAC 을 못 뺀다. SIC 코드가 없다.")
    P("- 워런트와 유닛도 못 뺀다. 종목 이름 글자로 추측할 수는 있으나 그건 다른 자다.")
    P("")

    # ── 2. Sharadar 와 겹침 ────────────────────────────
    P("---")
    P("")
    P("## 2. Sharadar 와 얼마나 겹치나")
    P("")
    with zipfile.ZipFile(TICKERS).open("tickers.csv") as f:
        tk = [r for r in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
              if r["table"] == "SEP"]
    sh = [r for r in tk
          if r["category"] in CAT and r["exchange"] in EXS and r["siccode"] != "6770"]
    live = [r for r in sh if r["isdelisted"] == "N"]
    NAS = set(r["Symbol"] for r in d)
    SH = set(r["ticker"] for r in live)
    P("| 무엇 | 수 |")
    P("|---|---:|")
    P("| Sharadar SEP 표 전체 | %s |" % format(len(tk), ","))
    P("| 우리 규칙을 통과하는 것 (상폐 포함) | %s |" % format(len(sh), ","))
    P("| 그 중 살아 있는 것 | **%s** |" % format(len(live), ","))
    P("| 나스닥 목록을 걸러 남은 것 | %s |" % format(len(NAS), ","))
    P("| 양쪽에 다 있는 것 | **%s** |" % format(len(SH & NAS), ","))
    P("| Sharadar 에만 있는 것 | %s |" % format(len(SH - NAS), ","))
    P("| 나스닥 목록에만 있는 것 | %s |" % format(len(NAS - SH), ","))
    P("")
    P("### 5,667 과 견주면")
    P("")
    P("백테스트가 쓴 5,667 은 27.4년 창 안에 한 번이라도 있었던 종목이다. 상폐 1,603개를 담는다.")
    P("여기 나온 %s 는 지금 살아 있는 것만이다. 두 수는 다른 자다."
      % format(len(live), ","))
    P("그래서 「%s 대 5,667」로 견주면 안 된다." % format(len(live), ","))
    P("")
    P("### Sharadar 에만 있는 %d개" % len(SH - NAS))
    P("")
    dd = {r["ticker"]: r for r in live}
    only = sorted(SH - NAS)
    lp = collections.Counter(dd[t]["lastpricedate"][:7] for t in only)
    P("전부 lastpricedate 가 " + " · ".join("%s (%d개)" % (k, v) for k, v in lp.most_common())
      + " 다.")
    P("Sharadar 자료가 끝나는 날과 같다. 표본을 보면 이렇다.")
    P("")
    P("| 티커 | 이름 | 거래소 |")
    P("|---|---|---|")
    for t in only[:8]:
        P("| %s | %s | %s |" % (t, dd[t]["name"][:36], dd[t]["exchange"]))
    P("")
    P("Sharadar 를 받은 날은 08-24 이고 나스닥 목록은 09-10 자다.")
    P("그 사이 20일에 상장폐지되거나 이름이 바뀌었을 수 있다. 확인하지 않았다.")
    P("어림으로 「상폐다」라고 적지 않는다.")
    P("")

    # ── 3. 이음매 ──────────────────────────────────────
    P("---")
    P("")
    P("## 3. 이음매 — 야후의 어느 열이 Sharadar 와 맞나")
    P("")
    P("| 무엇 | 값 |")
    P("|---|---|")
    P("| Sharadar 가격 자료가 끝나는 날 | %s |" % SHARADAR_END)
    P("| 오늘 | %s |" % TODAY)
    P("| 비는 날 | 20일 (거래일로는 13~14일) |")
    P("")
    SHP = json.loads((UNI / "probe_sharadar.json").read_text(encoding="utf-8"))
    YAH = json.loads((UNI / "probe_yahoo.json").read_text(encoding="utf-8"))
    BIG = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "JPM", "XOM")
    agg = collections.defaultdict(list)
    per = {}
    for t, rows_ in SHP.items():
        S = {r[0]: r for r in rows_}
        y = YAH.get(t) or {}
        cc2, ca, cu, vv = [], [], [], []
        for dte, (yc, yac, yv) in y.items():
            if dte not in S or yc is None:
                continue
            _, _so, sc, sv, sca, scu = S[dte]
            cc2.append(rel(sc, yc))
            ca.append(rel(sc, yac))
            cu.append(rel(scu, yc))
            if yv:
                vv.append(rel(sv, yv))
        if cc2:
            per[t] = (cc2, ca, cu, vv)
            grp = "big" if t in BIG else "split"
            agg[grp + "_close"] += cc2
            agg[grp + "_adj"] += ca
            agg[grp + "_unadj"] += cu
            agg[grp + "_vol"] += vv
    P("맞춰 본 것은 20종목 78거래일이다. 열 개는 큰 종목이고,")
    P("열 개는 창 안에서 주식 분할이 일어난 종목이다.")
    P("분할 종목을 일부러 넣은 까닭은, 분할이 없으면 두 자료가 어차피 같아서")
    P("질 수가 없는 검산이 되기 때문이다.")
    P("")
    P("차이는 모두 상대오차 백분율이다.")
    P("")
    P("| 묶음 | 견준 것 | 중앙 | P90 | 최대 |")
    P("|---|---|---:|---:|---:|")
    NM = {"close": "Sharadar close 대 야후 Close",
          "adj": "Sharadar close 대 야후 Adj Close",
          "unadj": "Sharadar closeunadj 대 야후 Close",
          "vol": "Sharadar volume 대 야후 Volume"}
    for grp, lab in (("big", "분할 없는 큰 종목 10"), ("split", "분할 난 종목 10")):
        for k in ("close", "adj", "unadj", "vol"):
            v = agg[grp + "_" + k]
            if not v:
                continue
            P("| %s | %s | %.3f | %.3f | %.3f |"
              % (lab, NM[k], st.median(v), q(v, 0.9), max(v)))
    P("")
    P(F3)
    P("답 1. 분할이 없는 종목에서는 Sharadar close 와 야후 Close 가 그대로 맞는다.")
    P("      중앙 0.000, 최대 %.3f 다." % max(agg["big_close"]))
    P("      Adj Close 는 아니다. 배당만큼 벌어지고 최대 %.3f 까지 간다."
      % max(agg["big_adj"]))
    P("")
    P("답 2. 분할이 난 종목은 갈린다. 열 중 여덟은 야후도 분할을 반영해 그대로 맞는데,")
    P("      둘은 반영하지 않아 분할 배수만큼 통째로 어긋난다.")
    P(F3)
    P("")
    P("### 분할 종목 열 개를 하나씩")
    P("")
    P("분할이 반영되기 전 날짜만 골라서 봤다. 그 날들에서 Sharadar 의 두 열은 서로 다르므로,")
    P("야후 Close 가 어느 쪽과 맞는지가 갈린다.")
    P("")
    P("| 티커 | 분할 전 날 수 | 야후가 맞는 쪽 | 어긋난 크기 |")
    P("|---|---:|---|---:|")
    ok_n = bad = []
    ok_n, bad = 0, []
    for t in sorted(SHP):
        if t in BIG:
            continue
        S = {r[0]: r for r in SHP[t]}
        y = YAH.get(t) or {}
        pre = [(dte, S[dte]) for dte in S
               if abs(S[dte][2] / max(1e-9, S[dte][5]) - 1.0) > 1e-6]
        pa, pb = [], []
        for dte, r in pre:
            yc = (y.get(dte) or [None])[0]
            if yc is None:
                continue
            pa.append(rel(r[2], yc))
            pb.append(rel(r[5], yc))
        if not pa:
            P("| %s | 0 | 창 안에 분할 전 날이 없다 | |" % t)
            continue
        if st.median(pa) < st.median(pb):
            ok_n += 1
            P("| %s | %d | close (분할 반영된 값) | %.3f%s |"
              % (t, len(pa), st.median(pa), PCT))
        else:
            bad.append(t)
            P("| %s | %d | **closeunadj (원값)** | **%.0f%s** |"
              % (t, len(pa), st.median(pa), PCT))
    P("")
    P("열 중 %d개는 야후가 분할을 반영했고, %d개는 반영하지 않았다."
      % (ok_n, len(bad)))
    P("반영하지 않은 것은 " + " · ".join(bad) + " 다.")
    P("")
    P("### 어긋난 둘을 펼쳐 보면")
    P("")
    for t in ("CCG", "ASBP"):
        if t not in SHP:
            continue
        S = sorted(SHP[t])
        y = YAH.get(t) or {}
        first = S[0]
        _, _so, sc, _sv, _sca, scu = first
        yc = (y.get(first[0]) or [None])[0]
        after = [r for r in S if abs(r[2] / max(1e-9, r[5]) - 1.0) < 1e-6]
        P("- %s: %s 에 Sharadar close 가 %.4f, closeunadj 가 %.4f 다. 야후 Close 는 %.4f 다."
          % (t, first[0], sc, scu, yc if yc else float("nan")))
        P("  배수가 정확히 %.1f 배다. 분할이 반영된 첫날은 %s 다."
          % (sc / max(1e-9, scu), after[0][0] if after else "창 안에 없음"))
    P("")
    P("### 거래량은 맞지 않는다")
    P("")
    P("큰 종목에서도 중앙은 0 인데 최대가 %.1f" % max(agg["big_vol"]) + PCT + " 다.")
    P("대부분의 날은 정확히 같고 며칠만 크게 벌어진다. 벌어지는 날은 Sharadar 쪽이 늘 더 작다.")
    P("")
    P("| 티커 | 날짜 | Sharadar | 야후 | 차이 |")
    P("|---|---|---:|---:|---:|")
    shown = 0
    for t in ("JPM", "XOM", "AAPL", "AMZN"):
        if t not in SHP:
            continue
        S = {r[0]: r for r in SHP[t]}
        y = YAH.get(t) or {}
        w = []
        for dte, (yc, yac, yv) in y.items():
            if dte in S and yv:
                w.append((rel(S[dte][3], yv), dte, S[dte][3], yv))
        w.sort(reverse=True)
        for e in w[:1]:
            P("| %s | %s | %s | %s | %.1f%s |"
              % (t, e[1], format(int(e[2]), ","), format(int(e[3]), ","), e[0], PCT))
            shown += 1
    P("")
    P("왜 그런지는 모른다. 이 판은 원인을 재지 않았다.")
    P("")

    # ── 4 ─────────────────────────────────────────────
    P("---")
    P("")
    P("## 4. 그래서 설계의 첫 칸에 무엇이 놓이나")
    P("")
    P("정하는 것은 내 몫이 아니다. 수만 놓는다.")
    P("")
    P("- 이어 붙일 가격 열은 야후 Close 다. Adj Close 가 아니다.")
    P("- 다만 분할이 난 종목에서는 그 규칙이 깨진다. 야후 Close 가 조정되지 않은 값이었다.")
    P("  이음매 앞뒤로 분할이 있으면 배수만큼 가짜 움직임이 생긴다.")
    P("- 거래량은 규약이 다르다. 진입 문턱이 평균 거래량을 쓰므로 그냥 이으면 안 된다.")
    P("")
    P("## 이 판이 못 한 것")
    P("")
    P("- 20종목 78거래일만 봤다. 전수가 아니다.")
    P("- 분할 종목 10개는 모두 소형주 역분할이다. 대형주 정방향 분할은 안 봤다.")
    P("- 거래량이 왜 벌어지는지 안 쟀다. 원인을 적지 않는다.")
    P("- Sharadar 에만 있는 25개가 상폐인지 이름이 바뀐 것인지 확인하지 않았다.")
    P("- 나스닥 목록으로는 우선주·ADR·SPAC 을 못 걸렀다. 그래서 위 7,478 은")
    P("  우리 규칙을 다 건 수가 아니다.")
    P("")
    P("커밋은 두뇌 몫입니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
