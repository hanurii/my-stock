# -*- coding: utf-8 -*-
r"""265 - **이음매 «창» 안의 분할 ＋ 섞어 쓰면 유동성 문턱이 «갈리나»** (조사 세션 2026-09-10)

  🔴 **두뇌가 «좁혀» 준 물음**: 우리는 야후를 «역사»로 «안** 쓴다. **13거래일**만 쓴다.
     ⇒ ★ 「«같은» 과거 날짜에서 두 자료가 다르다」는 **«안** 걸린다**.
     ⇒ ⇒ 걸리는 것은 **「Sharadar 가 «끝난» 2026-08-21 «뒤»에 «일어난» 분할」** 하나다.

  ⛔ **㉡(분할 전수에서 몇 %가 어긋나나)는 «내려갔다»** — 우리가 «안** 쓰는 구간이다(YAGNI).
     ✅ 다만 「2/10 은 표본이 «열»뿐이라 «비율»을 «못» 쓴다」는 `264` 에 «그대로» 남겼다.

  🚨 **거래량은 «까닭»을 «파지» 않는다** — **「«결정»이 «바뀌나»」**를 잰다(두뇌 지시).
     ⇒ 자: **`backtest_volatility_pilot_us.py:58` `MIN_TURNOVER_EOK = 5.0`(억원)**
        미국 셈: **`:533` close x volume x USD_KRW(1300) / 1e8 의 «50일» 평균** · 최소 20일

  ★ **«교란»을 «따로» 뺐다**: 「Sharadar 08-21 판 vs 섞은 오늘 판」은 **«규약»과 «때»가 «같이»** 움직인다.
     ⇒ **「야후«만» 오늘 판 vs 섞은 오늘 판」**을 «같이» 내면 — **«때»가 «묶이고» «규약»만 남는다**.

  💰 **어림 기록**: 분할 훑기 「90초~5분」 → **실제 192초**. ⛔ 오늘 처음으로 «범위 안»에 들었다.

  읽는 것(전부 저장돼 있다):
    `.cache/universe/seam_splits.json`     yfinance `.splits` · 4,039종목 · 08-22~09-10
    `.cache/universe/sharadar_recent.json` `stocks-10Y.csv.zip` 에서 2026-06-01 이후
    `.cache/universe/yahoo_recent.json`    yfinance · 같은 유니버스 · 2026-06-01 이후

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/265-seam-window.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
PCT = chr(37)

UNI = Path(__file__).resolve().parents[3] / ".cache" / "universe"
END = "2026-08-21"
TODAY = "2026-09-10"
WIN, MIND = 50, 20
EOK, KRW = 5.0, 1300.0
THR = EOK * 1e8 / KRW


def avg_dollar(s):
    if len(s) < MIND:
        return None
    w = s[-WIN:]
    return sum(c * v for _d, c, v in w) / len(w)


def main() -> int:
    P("# 265 - 이음매 창 안의 분할과 유동성 문턱")
    P("")
    P("> 조사 세션 2026-09-10 · " + BQ
      + "research/handoff/scripts/265-seam-window.py" + BQ)
    P("> 아무것도 짓지 않았다. 재기만 했다.")
    P("")
    P("---")
    P("")
    P("## 1. 이음매 창 안에서 분할이 난 종목")
    P("")
    P("물음은 좁다. 우리는 야후를 역사로 쓰지 않고 " + END + " 뒤 13거래일만 쓴다.")
    P("그러니 걸리는 것은 그 창 안에서 일어난 분할 하나뿐이다.")
    P("Sharadar 의 과거 값은 " + END + " 까지 알려진 분할로만 맞춰져 있고,")
    P("야후의 오늘 값은 그 뒤 분할까지 반영돼 있기 때문이다.")
    P("")
    d = json.loads((UNI / "seam_splits.json").read_text(encoding="utf-8"))
    found = d["found"]
    P("| 무엇 | 값 |")
    P("|---|---|")
    P("| 본 유니버스 | %s개 (Sharadar 규칙과 나스닥 목록에 다 있는 것) |"
      % format(d["universe_n"], ","))
    P("| 본 창 | 2026-08-22 ~ %s |" % TODAY)
    P("| 쓴 것 | yfinance 의 분할 사건. 시세는 안 받았다 |")
    P("| 분할이 난 종목 | **%d개** |" % len(found))
    P("")
    P(F3)
    P("0 이 아니다. 지금 그대로 이으면 %d개에서 배수만큼 가짜 계단이 생긴다." % len(found))
    P(F3)
    P("")
    P("| 티커 | 날짜 | 비율 | 어느 쪽 |")
    P("|---|---|---:|---|")
    fwd = []
    for t in sorted(found):
        for dte, r in found[t]:
            kind = "정방향 분할" if r > 1 else "역분할 1 대 %.0f" % (1.0 / r)
            if r > 1:
                fwd.append(t)
            P("| %s | %s | %.4f | %s |" % (t, dte, r, kind))
    P("")
    P("스물아홉 중 셋이 정방향 분할이다: " + " · ".join(fwd) + " 다.")
    P("나머지는 소형주 역분할이다.")
    P("")
    P("APH 는 대형주다. 이 하나만으로도 이음매를 그냥 이으면 안 된다.")
    P("")
    P("### 이 답이 말하지 않는 것")
    P("")
    P("- 오늘 그렇다는 뜻이다. 앞으로도 안전하다는 뜻이 아니다.")
    P("  분할은 계속 일어나므로 이을 때마다 이 창을 다시 봐야 한다.")
    P("- 창이 짧을수록 걸릴 것이 적다. 지금 창은 13~14거래일이다.")
    P("")

    # ── 2 ────────────────────────────────────────────
    P("---")
    P("")
    P("## 2. 섞어 쓰면 유동성 문턱을 넘고 못 넘는 종목이 달라지나")
    P("")
    P("문턱은 이렇다.")
    P("")
    P("```")
    P("50일 평균 거래대금 >= %.1f억원" % EOK)
    P("미국은 close x volume x %.0f / 1e8 로 환산한다" % KRW)
    P("  -> 하루 거래대금 %s달러" % format(int(THR), ","))
    P("```")
    P("")
    P("출처: " + BQ + "scripts/backtest_volatility_pilot_us.py:58" + BQ
      + " 와 " + BQ + ":533" + BQ + " · 창 50일 · 최소 20일")
    P("")
    SHR = json.loads((UNI / "sharadar_recent.json").read_text(encoding="utf-8"))
    YAH = json.loads((UNI / "yahoo_recent.json").read_text(encoding="utf-8"))
    res = {}
    for t in set(SHR) & set(YAH):
        sh = [x for x in SHR[t] if x[0] <= END]
        tail = [x for x in YAH[t] if x[0] > END]
        a, b, c = avg_dollar(sh), avg_dollar((sh + tail)[-WIN:]), avg_dollar(YAH[t])
        if None in (a, b, c):
            continue
        res[t] = (a, b, c, len(tail))
    P("견줄 수 있는 종목은 %s개다." % format(len(res), ","))
    tl = sorted(v[3] for v in res.values())
    P("이은 꼬리는 거의 모두 12거래일이다. %d개는 12일이고, 꼬리가 아예 없는 종목이 %d개 있다."
      % (sum(1 for x in tl if x == 12), sum(1 for x in tl if x == 0)))
    P("꼬리가 없는 둘은 야후에 " + END + " 뒤 값이 없다. 그 둘에서는 나와 가가 같은 값이라")
    P("아래 견줌에 아무 기여를 하지 않는다.")
    P("")
    P("세 가지로 재고 서로 견준다.")
    P("")
    P("| 이름 | 무엇 |")
    P("|---|---|")
    P("| 가 | Sharadar 만 · %s 까지 50일 |" % END)
    P("| 나 | 섞음 · 오늘까지 50일 (야후 꼬리 + Sharadar 앞부분) |")
    P("| 다 | 야후 만 · 오늘까지 50일 |")
    P("")

    def cross(i, j):
        inn = [t for t, v in res.items() if v[i] < THR <= v[j]]
        out = [t for t, v in res.items() if v[j] < THR <= v[i]]
        return inn, out, (sum(1 for v in res.values() if v[i] >= THR),
                          sum(1 for v in res.values() if v[j] >= THR))

    P("| 견줌 | 통과 종목 수 | 새로 들어옴 | 빠짐 | 합 | 비율 |")
    P("|---|---|---:|---:|---:|---:|")
    rows = []
    for i, j, lab in ((0, 1, "가 -> 나"), (2, 1, "다 -> 나"), (0, 2, "가 -> 다")):
        inn, out, (pa, pb) = cross(i, j)
        rows.append((lab, inn, out))
        P("| %s | %s -> %s | %d | %d | **%d** | %.2f%s |"
          % (lab, format(pa, ","), format(pb, ","), len(inn), len(out),
             len(inn) + len(out), 100.0 * (len(inn) + len(out)) / len(res), PCT))
    P("")
    P(F3)
    P("두뇌가 물은 것은 가 대 나다. %d개가 갈린다."
      % (len(rows[0][1]) + len(rows[0][2])))
    P("그런데 그 대부분은 이어 붙인 탓이 아니라 20일이 지난 탓이다.")
    P("")
    P("때를 묶고 규약만 남기면 (다 대 나) %d개다."
      % (len(rows[1][1]) + len(rows[1][2])))
    P("때만 움직이고 규약을 묶으면 (가 대 다) %d개다."
      % (len(rows[2][1]) + len(rows[2][2])))
    P(F3)
    P("")
    P("이어 붙이는 것 자체가 바꾸는 종목은 %d개다. %s개 중 %.2f%s 다."
      % (len(rows[1][1]) + len(rows[1][2]), format(len(res), ","),
         100.0 * (len(rows[1][1]) + len(rows[1][2])) / len(res), PCT))
    P("")
    P("| 티커 | 어느 쪽으로 |")
    P("|---|---|")
    for t in sorted(rows[1][1]):
        P("| %s | 섞으면 문턱을 넘게 된다 |" % t)
    for t in sorted(rows[1][2]):
        P("| %s | 섞으면 문턱 아래로 내려간다 |" % t)
    P("")
    P("### 평균 자체는 얼마나 움직이나")
    P("")
    dd = [abs(v[1] - v[2]) / max(1e-9, v[2]) * 100.0 for v in res.values()]
    P("나와 다의 평균 거래대금 차이는 중앙 %.3f%s, P90 %.2f%s, 최대 %.1f%s 다."
      % (st.median(dd), PCT, sorted(dd)[int(0.9 * len(dd))], PCT, max(dd), PCT))
    P("평균이 이만큼 움직여도 문턱을 가로지르는 종목은 %d개뿐이다."
      % (len(rows[1][1]) + len(rows[1][2])))
    P("문턱에서 멀리 떨어진 종목이 대부분이기 때문이다.")
    P("")
    P("곁으로 남기는 관측이 하나 있다. 거래량이 벌어질 때는 Sharadar 쪽이 늘 더 작았다"
      + "(" + BQ + "264-universe-and-seam.md" + BQ + ").")
    P("왜 그런지는 재지 않았으므로 까닭을 적지 않는다.")
    P("")

    # ── 3 ────────────────────────────────────────────
    P("---")
    P("")
    P("## 3. 정리")
    P("")
    P("| 물음 | 답 |")
    P("|---|---|")
    P("| 이음매 창에 분할이 있나 | 있다. %d개 |" % len(found))
    P("| 섞으면 유동성 판정이 달라지나 | 규약 탓으로 달라지는 것은 %d개 (%.2f%s) |"
      % (len(rows[1][1]) + len(rows[1][2]),
         100.0 * (len(rows[1][1]) + len(rows[1][2])) / len(res), PCT))
    P("")
    P("분할 쪽은 손을 대야 하고, 거래량 쪽은 그냥 이어도 판정이 거의 안 바뀐다.")
    P("어느 쪽을 어떻게 다룰지는 내가 정할 일이 아니다.")
    P("")
    P("## 이 판이 못 한 것")
    P("")
    P("- 야후가 분할을 제대로 반영했는지는 이 판에서 안 봤다."
      + " " + BQ + "264" + BQ + " 에서 열 개 중 둘이 어긋났다.")
    P("  그 둘이 왜 어긋났는지도 안 쟀다.")
    P("- 상장폐지된 종목은 유니버스에 없다. 살아 있는 것만 봤다.")
    P("- 문턱 5억원은 한국 자료에서 나온 값을 환율로 옮긴 것이다. 미국에서 다시 정한 적이 없다.")
    P("- 환율 1300 은 고정값이다. 실제 환율로 다시 재지 않았다.")
    P("- 「거래량이 벌어질 때 Sharadar 가 더 작다」의 까닭을 안 쟀다.")
    P("- 문턱이 갈린 다섯 중 FEED 는 1절의 분할 목록에도 있다. 두 흠이 겹친 종목이다.")
    P("  나머지 넷은 분할과 무관하다.")
    P("")
    P("커밋은 두뇌 몫입니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
