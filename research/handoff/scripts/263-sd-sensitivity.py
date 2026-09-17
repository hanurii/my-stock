# -*- coding: utf-8 -*-
r"""263 - **「옛 SD 에 기댄다」 흠을 «닫는다» — 민감도 · 식 «뒤집기» · z/t 통일**

  🔎 **검증 2차가 «허락»한 까닭**: 「반쪽 배제」는 «점추정·SD·세전세후» 셋에 «민감»한데,
     「필요 «햇수»」는 **SD «하나»**에만 달린 **«자릿수»** 물음이다(`233` 정본 — 「도구의 «성질»은 «옮긴다»」).
     ⇒ 그래도 **「«어디»까지 «틀려도» «되는가」를 «보여야»** 한다. 이 판이 «그것»이다.

  ⛔ **새 백테스트 «없다**. 저장된 지수 계열을 «읽고» 나머지는 «산술»이다.
  ✅ **검증·두뇌의 «어림»을 «베끼지» 않는다** — 「SD×0.5 ≈ 2,150」·「1.82%p」·「수십 %p」를
     **«식»에 넣어 «다시»** 낸다.

  🚨 **z / t 가 «섞였다»(검증이 잡음)**:
       13.38(CI 반폭) = **t**(25).975 x SD ÷ √26
       18.20(경계 Δ)  = **z**(1.96 + 0.8416) x SD ÷ √26
     ⇒ ✅ **t 로 «통일»한다.** 그리고 **「필요 햇수」는 n 이 «커서» t → z 로 «모인다»**는 것을
        **«주장»이 아니라 «출력값»**으로 «보인다»(되돌이 셈).

  🚨 **경계 Δ 18.20 과 「필요 SD」 1.82 는 «자릿수»가 «닮았는데» «다른» 것**이다.
     ⇒ **«떼어» 놓고 «이름»을 «다르게»** 적는다(검증 주의).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/263-sd-sensitivity.py
"""
from __future__ import annotations

import importlib.util as _u
import math
import statistics as st
import sys
from pathlib import Path

from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
PCT = chr(37)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r109 = _load("r109", "109-index-stop.py")

SD_DIFF = 33.1236        # `.cache/bt5y/out/152-resolution.json` 전체 27.4년 QQQ 짝차이 SD
N_OBS = 26               # 같은 json 의 n — 온전한 달력해
Y0, Y1 = 2000, 2025
POWER, ALPHA = 0.80, 0.05


def val_at(ds, vs, d):
    """`152-resolution.py` 의 것과 «같은» 자 — 그 날 «이하» 마지막 값."""
    lo, hi = 0, len(ds) - 1
    if ds[0] > d:
        return None
    while lo < hi:
        m = (lo + hi + 1) // 2
        if ds[m] <= d:
            lo = m
        else:
            hi = m - 1
    return vs[lo]


def annual(ds, vs, y0, y1):
    """온전한 달력해만 — `152-resolution.py` 의 `annual` 을 «그대로» 옮김."""
    out = {}
    for y in range(y0, y1 + 1):
        if not (ds[0] <= "%d-01-01" % y and ds[-1] >= "%d-12-31" % y):
            continue
        a = val_at(ds, vs, "%d-01-01" % y)
        b = val_at(ds, vs, "%d-12-31" % y)
        if a and b and a > 0:
            out[y] = b / a - 1.0
    return out


def need_z(sd, delta):
    """`152v-judge.py:34` 와 «같은» 식 — 정규분포 계수."""
    k = stats.norm.ppf(1.0 - ALPHA / 2.0) + stats.norm.ppf(POWER)
    return (k * sd / abs(delta)) ** 2


def need_t(sd, delta, it=60):
    """같은 물음을 **t** 로 — n 이 계수를 바꾸므로 «되돌이»로 푼다."""
    n = need_z(sd, delta)
    for _ in range(it):
        df = max(1.0, n - 1.0)
        k = stats.t.ppf(1.0 - ALPHA / 2.0, df) + stats.t.ppf(POWER, df)
        n2 = (k * sd / abs(delta)) ** 2
        if abs(n2 - n) < 1e-6:
            return n2
        n = n2
    return n


def mde_t(sd, n):
    """n 해가 «주어졌을» 때 가릴 수 있는 «제일 작은» 격차 — t 로."""
    df = n - 1.0
    k = stats.t.ppf(1.0 - ALPHA / 2.0, df) + stats.t.ppf(POWER, df)
    return k * sd / math.sqrt(n)


def sd_needed(delta, n):
    """식을 «뒤집는다** — 「Δ 를 n 해로 가리려면 SD 가 «얼마»여야 하나」."""
    df = n - 1.0
    k = stats.t.ppf(1.0 - ALPHA / 2.0, df) + stats.t.ppf(POWER, df)
    return abs(delta) * math.sqrt(n) / k


def main() -> int:
    kz = stats.norm.ppf(1.0 - ALPHA / 2.0) + stats.norm.ppf(POWER)
    kt = stats.t.ppf(1.0 - ALPHA / 2.0, N_OBS - 1.0) + stats.t.ppf(POWER, N_OBS - 1.0)

    P("# 263 - 옛 SD 에 기댄 표가 어디까지 견디나")
    P("")
    P("> 조사 세션 2026-09-10 · " + BQ
      + "research/handoff/scripts/263-sd-sensitivity.py" + BQ)
    P("> 새로 돌린 백테스트는 없다. 저장된 지수 계열을 읽고 나머지는 산술이다.")
    P("")
    P("---")
    P("")

    # ── 0. z / t ───────────────────────────────────────
    P("## 0. 먼저 고칠 것 — 분포가 둘 섞여 있었다")
    P("")
    P("앞서 낸 표에서 두 수가 서로 다른 분포를 썼다.")
    P("")
    P("| 수 | 무엇 | 쓴 분포 |")
    P("|---|---|---|")
    P("| 13.38" + PCT + "p | 신뢰구간 반폭 | t (자유도 25) |")
    P("| 18.20" + PCT + "p | 26개 해로 가릴 수 있는 최소 격차 | 정규 |")
    P("")
    P("t 로 통일한다. 계수는 이렇다.")
    P("")
    P("| 계수 | 값 |")
    P("|---|---|")
    P("| 정규 (1.96 + z80) | %.6f |" % kz)
    P("| t 자유도 25 (t.975 + t.80) | %.6f |" % kt)
    P("")
    P("| 수 | 정규로 | t 로 |")
    P("|---|---:|---:|")
    P("| 26개 해로 가릴 수 있는 최소 격차 | %.2f%sp | **%.2f%sp** |"
      % (kz * SD_DIFF / math.sqrt(N_OBS), PCT, mde_t(SD_DIFF, N_OBS), PCT))
    P("")
    P("18.20 이 아니라 " + ("%.2f" % mde_t(SD_DIFF, N_OBS)) + " 가 맞는 값이다.")
    P("")
    P("필요 햇수 쪽은 사정이 다르다. 답으로 나오는 햇수가 크면 자유도도 커지고,")
    P("그러면 t 계수가 정규 계수로 모인다. 주장이 아니라 수로 보인다.")
    P("")
    P("| 격차 | 정규로 낸 햇수 | t 로 되풀어 낸 햇수 | 차이 |")
    P("|---:|---:|---:|---:|")
    for d in (1.0, 8.0, 12.0, 20.0):
        a, b = need_z(SD_DIFF, d), need_t(SD_DIFF, d)
        P("| %.0f%sp | %s년 | **%s년** | %.2f%s |"
          % (d, PCT, format(int(round(a)), ","), format(int(round(b)), ","),
             100.0 * (b - a) / a, PCT))
    P("")
    P("가장 큰 차이도 " + ("%.2f" % max(
        100.0 * (need_t(SD_DIFF, d) - need_z(SD_DIFF, d)) / need_z(SD_DIFF, d)
        for d in (1.0, 8.0, 12.0, 20.0))) + PCT + " 다.")
    P("햇수 표는 t 로 다시 내도 사실상 같다. 그래도 t 값을 정본으로 쓴다.")
    P("")
    P("---")
    P("")

    # ── 1. 민감도 ──────────────────────────────────────
    P("## 1. SD 가 틀렸다면 얼마나 틀려도 되나")
    P("")
    P("이 표가 쓰는 SD 33.1236" + PCT + "p 는 +20/-10 판이고 세전이다.")
    P("현행 규칙, 세후로 다시 내면 달라질 수 있다. 얼마나 달라져야 답이 바뀌는지 본다.")
    P("")
    P("| SD 를 이만큼으로 보면 | SD 값 | 연 1" + PCT
      + "p 를 가리는 데 | 26개 해로 가릴 수 있는 최소 격차 |")
    P("|---|---:|---:|---:|")
    for f, lab in ((1.00, "지금 값"), (0.75, "3/4 로 줄여도"),
                   (0.50, "절반으로 줄여도"), (0.25, "4분의 1 로 줄여도")):
        s = SD_DIFF * f
        P("| %s | %.2f%sp | %s년 | %.2f%sp |"
          % (lab, s, PCT, format(int(round(need_t(s, 1.0))), ","), mde_t(s, N_OBS), PCT))
    P("")
    P("SD 를 4분의 1 로 줄여도 연 1" + PCT + "p 를 가리는 데 "
      + format(int(round(need_t(SD_DIFF * 0.25, 1.0))), ",") + "년이 필요하다.")
    P("우리가 가진 것은 26개 해다. 그래서 이 표의 결론은 SD 가 얼마나 틀렸든 바뀌지 않는다.")
    P("")
    P("---")
    P("")

    # ── 2. 식 뒤집기 ───────────────────────────────────
    P("## 2. 거꾸로 물으면 — SD 가 얼마여야 가려지나")
    P("")
    need = sd_needed(1.0, N_OBS)
    P("식을 뒤집는다. 연 1" + PCT + "p 를 26개 해로 가리려면 SD 가 얼마여야 하는가.")
    P("")
    P("```")
    P("SD = Δ x sqrt(n) / (t.975 + t.80) = 1.0 x sqrt(%d) / %.6f = **%.3f%sp**"
      % (N_OBS, kt, need, PCT))
    P("```")
    P("")
    P("이 값이 얼마나 작은 것인지 보려면 QQQ 혼자의 해마다 변동과 견주면 된다.")
    P("아래는 저장된 QQQ 계열에서 직접 낸 값이다.")
    P("")
    d_, c_ = r109.load("QQQ")
    cv = [v / c_[0] for v in c_]
    qa = annual(d_, cv, Y0, Y1)
    ys = sorted(qa)
    rs = [100.0 * qa[y] for y in ys]
    P("| 무엇 | 값 |")
    P("|---|---|")
    P("| 해 수 | %d개 (%d~%d) |" % (len(ys), ys[0], ys[-1]))
    P("| QQQ 연수익 평균 | %+.2f%s |" % (st.mean(rs), PCT))
    P("| QQQ 연수익 SD | **%.2f%sp** |" % (st.stdev(rs), PCT))
    P("| 제일 나쁜 해 | %+.1f%s (%d) |" % (min(rs), PCT, ys[rs.index(min(rs))]))
    P("| 제일 좋은 해 | %+.1f%s (%d) |" % (max(rs), PCT, ys[rs.index(max(rs))]))
    P("")
    P("낸 각본: " + BQ + "research/handoff/scripts/263-sd-sensitivity.py" + BQ
      + " (계열은 " + BQ + "109-index-stop.py" + BQ + " 가 읽는다)")
    P("")
    sdq = st.stdev(rs)
    P("QQQ 혼자서 해마다 %.2f%sp 씩 흔들린다." % (sdq, PCT))
    P("우리와 QQQ 차이 계열의 SD 는 %.2f" % SD_DIFF + PCT + "p 로, 그보다 크다.")
    P("")
    P("이 두 수만으로는 까닭을 못 가린다. 항등식이 이렇게 생겼기 때문이다.")
    P("")
    P("```")
    P("차이의 분산 = 우리 분산 + QQQ 분산 - 2 x 상관 x 우리SD x QQQ SD")
    P("```")
    P("")
    P("차이 SD 가 QQQ SD 보다 크다는 것은 「우리 SD 가 크다」로도 채워지고")
    P("「상관이 낮다」로도 채워진다. 둘 중 어느 쪽인지 이 수로는 못 정한다.")
    P("그래서 「잡음을 더한다」고도, 「상관이 낮다」고도 쓰지 않는다.")
    P("")
    P("### 우리 연수익 계열은 저장돼 있지 않다")
    P("")
    P("찾은 범위를 적는다. " + BQ + ".cache/bt5y/out/*.json" + BQ
      + " 332개 파일을 전부 열어")
    P("해 이름이 20개 이상 붙은 사전과 길이 24~30 인 수 배열을 찾았다. 57곳이 걸렸는데,")
    P("우리 연수익은 없었다. " + BQ + "130-yearly.json" + BQ + " 의 "
      + BQ + "per_year" + BQ + " 는 연수익처럼 보이지만")
    P("거래 건수다(" + BQ + "130-yearly.py:39" + BQ + " 가 " + BQ + "Counter" + BQ + " 로 센다).")
    P("")
    P(BQ + "152-resolution.py:218" + BQ + " 은 n, 평균, SD, 신뢰구간만 저장하고")
    P("계산 중에 만든 연수익 계열은 버린다. 그래서 우리 SD 와 상관을 직접 낼 수 없다.")
    P("내려면 다시 돌려야 한다. 여기서는 돌리지 않았다.")
    P("")
    P("### 대신 경계로 가둔다")
    P("")
    P("상관은 -1 과 1 사이이므로 항등식만으로 우리 SD 의 범위가 정해진다.")
    P("QQQ 쪽 식과 SPY 쪽 식을 겹치면 이렇다.")
    P("")
    d2, c2 = r109.load("SPY")
    sa = annual(d2, [v / c2[0] for v in c2], Y0, Y1)
    sr = [100.0 * sa[y] for y in sorted(sa)]
    sds = st.stdev(sr)
    lo_all, hi_all = 0.0, float("inf")
    P("| 견주는 지수 | 지수 연 SD | 차이 계열 SD | 우리 SD 가 들어갈 범위 |")
    P("|---|---:|---:|---|")
    for tk, b, dd in (("QQQ", sdq, SD_DIFF), ("SPY", sds, 23.8638)):
        lo, hi = max(dd - b, b - dd, 0.0), b + dd
        lo_all, hi_all = max(lo_all, lo), min(hi_all, hi)
        P("| %s | %.2f%sp | %.2f%sp | %.2f ~ %.2f%sp |" % (tk, b, PCT, dd, PCT, lo, hi, PCT))
    P("")
    P("겹치면 우리 연수익 SD 는 %.2f ~ %.2f%sp 사이다." % (lo_all, hi_all, PCT))
    P("범위가 넓어서 「우리 몫이냐 상관 몫이냐」는 이것으로 갈리지 않는다.")
    P("")

    def rho(a, b, dd):
        return (a * a + b * b - dd * dd) / (2.0 * a * b)

    P("| 우리 SD 가 이 값이면 | 우리와 QQQ 의 상관 |")
    P("|---:|---:|")
    for a in (lo_all, (lo_all + hi_all) / 2.0, sdq, hi_all):
        P("| %.2f%sp | %+.4f |" % (a, PCT, rho(a, sdq, SD_DIFF)))
    P("")
    rmax = max(rho(a, sdq, SD_DIFF) for a in (lo_all, hi_all))
    P("### 그래도 닫히는 것 하나")
    P("")
    P("우리 SD 를 몰라도 상관의 위끝은 정해진다. 위 범위 안에서 제일 큰 값이 %+.3f 다." % rmax)
    P("")
    P("그런데 연 1" + PCT + "p 를 26개 해로 가리려면 상관이 얼마여야 하는지도 항등식으로 나온다.")
    P("")
    astar = math.sqrt(sdq * sdq - need * need)
    P("| 무엇 | 값 |")
    P("|---|---|")
    P("| 우리 SD 가 들어가야 할 범위 | %.2f ~ %.2f%sp |" % (sdq - need, sdq + need, PCT))
    P("| 그때 필요한 상관 (제일 느슨하게 잡아도) | %.4f |" % rho(astar, sdq, need))
    P("| 지금 자료가 허락하는 상관의 위끝 | %+.3f |" % rmax)
    P("")
    P("필요한 상관 %.3f 는 지금 허락되는 위끝 %.3f 보다 훨씬 위다."
      % (rho(astar, sdq, need), rmax))
    P("상관 0.998 로 QQQ 를 따라간다는 것은 사실상 QQQ 를 사는 것이다.")
    P("우리 설계는 그것이 아니다. 다섯 칸에 나눠 담고, -10" + PCT + " 에서 자르고,")
    P("최대 낙폭이 -37" + PCT + " 대 QQQ -83" + PCT + " 다. 따라가지 않는 것이 설계다.")
    P("")
    P("그러니 정확히 이렇게 적어야 한다. 「어떤 방법으로도 못 가린다」가 아니라")
    P("「이 방법이 QQQ 를 그대로 따라가는 것이 아닌 한 그 길은 열리지 않는다」다.")
    P("추종에 작은 초과수익을 얹는 방법이라면 이론상 가능하다. 우리 방법이 그것이 아닐 뿐이다.")
    P("")
    P("그래서 위 햇수 표는 두 다리로 선다. 하나는 1절의 민감도이고,")
    P("다른 하나는 이 절의 항등식이다. 둘은 서로 기대지 않는다.")
    P("")
    P("### 헷갈리기 쉬운 두 수")
    P("")
    P("아래 둘은 자릿수가 닮았지만 서로 다른 것이다. 나란히 두면 안 된다.")
    P("")
    P("| 이름 | 값 | 무엇 |")
    P("|---|---|---|")
    P("| 26개 해로 가릴 수 있는 최소 격차 | %.2f%sp | 격차의 크기. 세로축 |"
      % (mde_t(SD_DIFF, N_OBS), PCT))
    P("| 연 1" + PCT + "p 를 가리는 데 필요한 SD | %.3f%sp | 잡음의 크기. 가로축 |" % (need, PCT))
    P("")
    P("두 수의 비는 %.1f 인데, 이건 우연이다. 계수 제곱을 해 수로 나눈 값과 같다."
      % (mde_t(SD_DIFF, N_OBS) / need))
    P("")
    P("---")
    P("")
    P("## 이 판이 못 한 것")
    P("")
    P("- SD 33.1236 은 여전히 +20/-10 판이고 세전이다. 다시 내지 않았다.")
    P("  대신 위 1절과 2절이 「얼마나 틀려도 되는가」를 수로 보였다.")
    P("- QQQ 연수익 SD 는 QQQ 혼자의 흔들림이지, 우리와 QQQ 차이의 SD 가 아니다.")
    P("  둘은 다른 자다. 여기서는 「필요한 SD 가 얼마나 작은 값인가」를 견주는 데만 썼다.")
    P("- 우리 연수익 SD 와 상관을 따로 못 냈다. 저장돼 있지 않아서다.")
    P("  경계로 가두었을 뿐이고, 그 범위가 넓어 「우리 몫이냐 상관 몫이냐」는 안 갈렸다.")
    P("  갈리려면 152 를 현행 규칙으로 다시 돌려야 한다. 여기서는 안 돌렸다.")
    P("- 「그러니 이 방법을 하지 마라」로 잇지 않는다. 이 판이 닫는 것은")
    P("  「더 기다리면 알게 된다」 하나뿐이다.")
    P("")
    P("커밋은 두뇌 몫입니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
