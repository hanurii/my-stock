# -*- coding: utf-8 -*-
"""account_lib — **계좌를 만드는 «단 하나의» 자리** (2026-09-02 · 사용자 결정으로 신설)

# 🚨 왜 이 파일이 «필요»했나 — 오늘 가장 큰 구조 결함
```
「지수 숏」은 정본 하네스(91)에 **없었다.**
대신 **스크립트 «18개»가 각자 자기 `account()` 안에 «베껴» 갖고 있었다** —
   117 118 119 121 121b 122 123 124 127 128 129 131 132 137 138 139 152 154
⇒ 「빼자」는 결정을 내려도 **«뺄 자리»가 없었다.**
```
> ### ★ **손잡이가 «열여덟 곳»에 있으면 그건 «설정»이 아니라 «관습»이다.**
> ### ★ 그래서 「지운다」가 아니라 **「«한 자리»를 만들고 거기에 «없게» 한다」**로 고친다.

# ✅ 사용자 결정 (2026-09-02) — **지수 숏을 «뺀다»**
```
① 숏 오버레이는 **«우리 발명»**이다 — `108:1` 이 「원전 기반이 «아니다»」라고 스스로 적었다
② 원전은 「롱 아니면 **«현금»**」 ⇒ 떼면 원전과 **«덜 어긋난다»**
③ 차입료를 **«회계상 확실히»** 낸다 (0.0972%p/년 · 검정 «불필요»)
④ 150 의 지수 비교에서 **«우리 쪽에만»** 얹혀 있었다 ⇒ **불공정**
⛔ 결론은 «안 바뀐다» — 크기 +0.176%p 는 «결론을 바꾸는 크기»(1.23%p)의 **1/7** (155)
```

# ★★ 규약 ③ 「안 쓸 건 «import조차» 안 한다」를 **여기서 지킨다**
```
🚨 이 파일은 `108-short-index.py` 를 **«부르지 않는다».**
   `spy_series` 도 `short_days` 도 **이 파일 안에 «이름조차 없다».**
⇒ 「숏 크기를 0 으로 둔다」가 아니라 **«숏이라는 것이 없다»**.
   손잡이가 없으면 **«되돌릴 수도 없다»** — 그게 «구조»다 (오늘의 일곱 중 ③)
```

# 🚨 이 파일이 «안» 바꾸는 것 — 이미 «끝난» 판들
```
117~154 의 committed 결과는 **«숏이 얹힌 채»로 보고됐다. 그대로 둔다.**
⇒ 지난 스크립트를 고치면 **보고된 수와 코드가 «어긋난다»** (규약 「문서–코드 동기」)
⇒ 앞으로 나오는 판만 이 파일을 쓴다. **그래서 «세대»가 갈린다 — 섞어 쓰지 말 것.**
```
"""
from __future__ import annotations

import importlib.util as _u
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r124 = _load("r124", "124-jeonse-horizon.py")     # 세금 (한국 거주자 22% · 250만 공제)
r129 = _load("r129", "129-frontier.py")           # 낙폭·회복
# ⛔ 108(지수 숏) 은 **부르지 않는다** — 위 「규약 ③」 참조

FEE = 0.002        # 왕복 수수료·세금 근사 (매수 쪽 20% 만 여기서 뗀다 — 나머지는 41 의 Cost 안)
START = 1000.0     # 만원


def account(x, *, start_i=0, end_i=None):
    """운의 번호 한 판(`sim_lots` 산출물) → **(세후 총액, 낙폭, 회복일, 매수 수)**

    🚨 지수 숏 «없음». 롱 아니면 «현금»이다.
    start_i/end_i 를 주면 그 «구간»만 (⚠️ `108:2` — 잘라 재는 것은 따로 돌리는 것과 «다르다»).
    """
    fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
    fd = Counter(fdates)
    vv = ([(d, v) for d, v in x["curve"]]
          + [(x["curve"][-1][0], 1.0 + x["equity_pct"] / 100.0)])
    cds, ccv, V = [vv[0][0]], [1.0], 1.0
    for i in range(1, len(vv)):
        if vv[i - 1][1] <= 0:
            break
        d = vv[i][0]
        rl = vv[i][1] / vv[i - 1][1] - 1.0
        V *= (1.0 + rl - FEE * 0.20 * fd.get(d, 0))
        cds.append(d)
        ccv.append(max(V, 1e-9))
    real = {}
    for d, pl in x["exit_log"]:
        real[d] = real.get(d, 0.0) + pl
    j0 = start_i
    j1 = len(ccv) - 1 if end_i is None else min(end_i, len(ccv) - 1)
    post = r124.taxed_window(cds, ccv, real, j0, j1) if j1 > j0 else START
    mdd, rec = r129.shape(cds, ccv)
    return post, mdd, rec, len(fdates)


def cagr(total, years):
    """세후 총액(만원) → 연 환산 %."""
    return ((total / START) ** (1.0 / years) - 1.0) * 100.0
