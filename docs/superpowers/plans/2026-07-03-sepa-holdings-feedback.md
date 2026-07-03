# SEPA 보유 종목 점검(매도 규칙 위반 피드백) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** /stocks/sepa 페이지에 보유 종목의 미너비니 매도 규칙 위반 6가지를 매일 점검해 조기 매도 신호를 표시하는 섹션을 추가한다.

**Architecture:** 사용자가 관리하는 `public/data/sepa-holdings.json`(매수 목록)을 입력으로, `scripts/screen_holdings_feedback.py`가 일봉 캐시(`ohlcv_matrix.get_series`)와 SEPA 후보 파일의 피벗을 읽어 규칙을 판정하고 `public/data/sepa-holdings-feedback.json`을 생성한다. 판정 로직은 `scripts/canslim_lib/sell_rules.py` 순수 모듈(pytest 대상). 페이지는 결과 JSON을 읽어 서버 렌더 전용 컴포넌트로 표시한다.

**Tech Stack:** Python 3 (stdlib only), pytest, Next.js App Router 서버 컴포넌트, Tailwind.

**Spec:** `docs/superpowers/specs/2026-07-03-sepa-holdings-feedback-design.md`

## Global Constraints

- 손절 기본값 **-4%** (`stop_loss_pct_default: -4`), 종목별 `stop_loss_pct` 로 덮어쓰기 가능.
- 조기 매도 신호는 위반 **1개**부터, 배지에 **위반 개수** 표시.
- 규칙 판정 기준점은 **돌파일** (못 찾으면 매수일 대체 + `breakout_date_estimated: true`).
- 50일 평균 거래량 = 판정일 **직전** 최대 50거래일 평균 (판정일 제외, 표본 5일 미만이면 판정 불가).
- 대량 거래 기준 = 평균 × **1.5**.
- 페이지는 읽기 전용: 시세 캐시(.cache/ohlcv)는 서버 로컬에만 있으므로 모든 계산은 파이썬 스크립트에서.
- 주석·출력 문구는 기존 스크립트 관례(한국어) 유지.

## File Structure

| 파일 | 역할 |
|---|---|
| `scripts/canslim_lib/sell_rules.py` | 신규 — 규칙 판정 순수 함수 (돌파일 탐지, 6개 규칙, 종합) |
| `tests/test_sell_rules.py` | 신규 — pytest 단위 테스트 |
| `scripts/screen_holdings_feedback.py` | 신규 — 점검 스크립트 (입출력·피벗 조인) |
| `public/data/sepa-holdings.json` | 신규 — 매수 목록 (사용자 관리, 실제 4종목으로 초기화) |
| `public/data/sepa-holdings-feedback.json` | 신규 — 스크립트 산출물 |
| `src/app/stocks/sepa/SepaHoldingsSection.tsx` | 신규 — 표시 전용 서버 컴포넌트 |
| `src/app/stocks/sepa/page.tsx` | 수정 — 결과 파일 읽기 + 섹션 렌더 (1단계 요약 아래) |

---

### Task 1: sell_rules.py 골격 — 평균 거래량 + 돌파일 탐지

**Files:**
- Create: `scripts/canslim_lib/sell_rules.py`
- Test: `tests/test_sell_rules.py`

**Interfaces:**
- Consumes: `ohlcv_matrix.get_series()` 형태 dict — `{"dates": [str], "closes": [float], "highs": [float], "lows": [float], "volumes": [float]}` (오름차순 일봉)
- Produces:
  - `avg_volume(volumes: list, i: int, window: int = 50, min_days: int = 5) -> float | None`
  - `find_breakout_index(series: dict, buy_date: str, pivot_price: float | None) -> tuple[int, bool]` — (돌파일 인덱스, 추정 여부)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_sell_rules.py` 생성:

```python
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.sell_rules import avg_volume, find_breakout_index


def make_series(closes, volumes=None, highs=None, lows=None):
    """오름차순 일봉 dict 생성. 기본 고저 = 종가 ±1%, 거래량 1000."""
    n = len(closes)
    d0 = date(2026, 1, 1)
    dates = [(d0 + timedelta(days=i)).isoformat() for i in range(n)]
    return {
        "dates": dates,
        "closes": list(closes),
        "highs": list(highs) if highs else [c * 1.01 for c in closes],
        "lows": list(lows) if lows else [c * 0.99 for c in closes],
        "volumes": list(volumes) if volumes else [1000.0] * n,
    }


# --- avg_volume ---

def test_avg_volume_excludes_current_day():
    vols = [1000.0] * 10 + [9999.0]  # 판정일(마지막)은 평균에서 제외
    assert avg_volume(vols, 10) == 1000.0


def test_avg_volume_none_when_insufficient_sample():
    assert avg_volume([1000.0] * 3, 3) is None  # 직전 3일 < min_days 5


def test_avg_volume_caps_window_at_50():
    vols = [2000.0] * 30 + [1000.0] * 50 + [1.0]
    assert avg_volume(vols, 80) == 1000.0  # 직전 50일만


# --- find_breakout_index ---

def test_find_breakout_detects_pivot_cross():
    closes = [100.0] * 10 + [106.0, 107.0]  # index 10에서 피벗 105 상향 돌파
    s = make_series(closes)
    bi, estimated = find_breakout_index(s, s["dates"][-1], 105.0)
    assert bi == 10
    assert estimated is False


def test_find_breakout_falls_back_to_buy_date_when_no_cross():
    closes = [100.0] * 12  # 피벗 105를 넘은 날 없음
    s = make_series(closes)
    bi, estimated = find_breakout_index(s, s["dates"][5], 105.0)
    assert bi == 5
    assert estimated is True


def test_find_breakout_no_pivot_uses_buy_date():
    s = make_series([100.0] * 12)
    bi, estimated = find_breakout_index(s, s["dates"][7], None)
    assert bi == 7
    assert estimated is True


def test_find_breakout_buy_date_between_trading_days():
    # 매수일이 휴장일이면 그 이전 마지막 거래일을 매수일로 취급
    s = make_series([100.0] * 5)
    bi, estimated = find_breakout_index(s, "2026-12-31", None)
    assert bi == 4  # 마지막 거래일
    assert estimated is True
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'canslim_lib.sell_rules'`

- [ ] **Step 3: 최소 구현**

`scripts/canslim_lib/sell_rules.py` 생성:

```python
# scripts/canslim_lib/sell_rules.py
"""매수 후 미너비니 매도 규칙 위반(violation) 판정 순수 모듈.

입력: ohlcv_matrix.get_series() 형태의 일봉 dict (dates/closes/highs/lows/volumes)
정의: docs/superpowers/specs/2026-07-03-sepa-holdings-feedback-design.md
"""
from __future__ import annotations

HEAVY_VOL_MULT = 1.5        # 대량 거래 기준(직전 50일 평균 대비)
STRONG_BREAKOUT_MULT = 1.5  # 정상 돌파 거래량 기준
LOWER_CLOSE_RUN = 3         # 연속 저저점(종가<전일 저가) 위반 기준 일수
MIN_TREND_DAYS = 5          # 하락일·나쁜 마감 우세 판정 최소 경과 거래일
BREAKOUT_LOOKBACK = 20      # 매수일에서 돌파일을 찾는 최대 소급 거래일


def avg_volume(volumes, i, window=50, min_days=5):
    """i일 직전 최대 window 거래일 평균 거래량(판정일 제외). 표본 부족 시 None."""
    lo = max(0, i - window)
    sample = [v for v in volumes[lo:i] if v]
    if len(sample) < min_days:
        return None
    return sum(sample) / len(sample)


def find_breakout_index(series, buy_date, pivot_price):
    """매수일에서 최대 BREAKOUT_LOOKBACK 거래일 소급해
    '전일 종가 <= 피벗 < 당일 종가' 인 가장 최근 날을 찾는다.
    반환: (index, estimated) — 못 찾으면 매수일 인덱스(estimated=True).
    """
    dates, closes = series["dates"], series["closes"]
    buy_idx = 0
    for i in range(len(dates) - 1, -1, -1):
        if dates[i] <= buy_date:
            buy_idx = i
            break
    if pivot_price is None:
        return buy_idx, True
    lo = max(1, buy_idx - BREAKOUT_LOOKBACK + 1)
    for i in range(buy_idx, lo - 1, -1):
        if closes[i] > pivot_price and closes[i - 1] <= pivot_price:
            return i, False
    return buy_idx, True
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sepa): sell_rules 순수 모듈 골격 — 평균 거래량·돌파일 탐지"
```

---

### Task 2: 규칙 ①②③ — 저거래량 돌파 · 대량 거래 후퇴 · 연속 저저점

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (함수 추가)
- Test: `tests/test_sell_rules.py` (테스트 추가)

**Interfaces:**
- Consumes: Task 1의 `avg_volume`, series dict, `bi`(돌파일 인덱스)
- Produces: 각 규칙 함수는 `{"id": str, "status": "violation"|"pass"|"pending"|"na", "detail": str}` 반환
  - `rule_low_volume_breakout(series, bi) -> dict`
  - `rule_heavy_volume_pullback(series, bi) -> dict`
  - `rule_consecutive_lower_closes(series, bi) -> dict`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_sell_rules.py`에 추가:

```python
from canslim_lib.sell_rules import (
    rule_low_volume_breakout,
    rule_heavy_volume_pullback,
    rule_consecutive_lower_closes,
)


# --- 규칙 ① 저거래량 돌파 ---

def test_rule1_violation_below_average_volume():
    vols = [1000.0] * 30 + [800.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "violation"


def test_rule1_pass_but_weak_between_1x_and_1p5x():
    vols = [1000.0] * 30 + [1200.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "pass"
    assert "1.5배" in r["detail"]  # 정상 돌파 기준 미달 경고 문구


def test_rule1_pass_strong_volume():
    vols = [1000.0] * 30 + [2100.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "pass"
    assert "1.5배" not in r["detail"]


def test_rule1_pending_insufficient_history():
    s = make_series([100.0] * 3)
    assert rule_low_volume_breakout(s, 2)["status"] == "pending"


# --- 규칙 ② 대량 거래 후퇴 ---

def test_rule2_violation_down_close_on_heavy_volume():
    closes = [100.0] * 30 + [106.0, 103.0]   # 돌파(30) 후 하락 마감
    vols = [1000.0] * 31 + [1800.0]          # 하락일 거래량 1.8배
    s = make_series(closes, volumes=vols)
    r = rule_heavy_volume_pullback(s, 30)
    assert r["status"] == "violation"


def test_rule2_pass_down_close_on_light_volume():
    closes = [100.0] * 30 + [106.0, 103.0]
    vols = [1000.0] * 31 + [900.0]
    s = make_series(closes, volumes=vols)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pass"


def test_rule2_pass_heavy_volume_but_up_close():
    closes = [100.0] * 30 + [106.0, 109.0]
    vols = [1000.0] * 31 + [3000.0]
    s = make_series(closes, volumes=vols)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pass"


def test_rule2_pending_no_post_breakout_days():
    s = make_series([100.0] * 31)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pending"


# --- 규칙 ③ 연속 저저점 (종가 < 전일 저가) ---

def test_rule3_violation_three_consecutive_closes_below_prior_low():
    # 저가 = 종가*0.99. 97<99, 94<96.03, 91<93.06 → 3일 연속
    closes = [100.0] * 30 + [106.0, 97.0, 94.0, 91.0]
    s = make_series(closes)
    r = rule_consecutive_lower_closes(s, 30)
    assert r["status"] == "violation"


def test_rule3_two_day_run_is_pass_with_warning():
    closes = [100.0] * 30 + [106.0, 97.0, 94.0]  # 2일 연속 진행 중
    s = make_series(closes)
    r = rule_consecutive_lower_closes(s, 30)
    assert r["status"] == "pass"
    assert "2일" in r["detail"]


def test_rule3_pass_when_run_broken():
    # 2일 연속 후 반등 → 위반 아님
    closes = [100.0] * 30 + [106.0, 97.0, 94.0, 98.0]
    s = make_series(closes)
    r = rule_consecutive_lower_closes(s, 30)
    assert r["status"] == "pass"
    assert "2일" not in r["detail"]
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: FAIL — `ImportError: cannot import name 'rule_low_volume_breakout'`

- [ ] **Step 3: 구현** — `sell_rules.py`에 추가:

```python
def rule_low_volume_breakout(series, bi):
    """규칙① 저거래량 돌파: 돌파일 거래량 < 50일 평균이면 위반."""
    rid = "low_volume_breakout"
    vols = series["volumes"]
    avg = avg_volume(vols, bi)
    if avg is None or not vols[bi]:
        return {"id": rid, "status": "pending", "detail": "거래량 표본 부족"}
    ratio = vols[bi] / avg
    if ratio < 1.0:
        return {"id": rid, "status": "violation",
                "detail": f"돌파일 거래량 {ratio:.1f}배 — 평균에도 못 미침"}
    if ratio < STRONG_BREAKOUT_MULT:
        return {"id": rid, "status": "pass",
                "detail": f"돌파일 거래량 {ratio:.1f}배 — 정상 돌파(1.5배+)에는 못 미침"}
    return {"id": rid, "status": "pass", "detail": f"돌파일 거래량 {ratio:.1f}배"}


def rule_heavy_volume_pullback(series, bi):
    """규칙② 대량 거래 후퇴: 돌파 후 하락 마감 + 거래량 1.5배 이상인 날이 있으면 위반."""
    rid = "heavy_volume_pullback"
    closes, vols, dates = series["closes"], series["volumes"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    worst = None  # (index, ratio)
    for i in range(bi + 1, n):
        avg = avg_volume(vols, i)
        if avg is None:
            continue
        if closes[i] < closes[i - 1] and vols[i] >= HEAVY_VOL_MULT * avg:
            ratio = vols[i] / avg
            if worst is None or ratio > worst[1]:
                worst = (i, ratio)
    if worst:
        i, ratio = worst
        return {"id": rid, "status": "violation",
                "detail": f"{dates[i]} 하락 마감 + 거래량 {ratio:.1f}배"}
    return {"id": rid, "status": "pass", "detail": "대량 거래 하락일 없음"}


def rule_consecutive_lower_closes(series, bi):
    """규칙③ 연속 저저점: 종가 < 전일 저가 가 3일 연속이면 위반 (종가 기준, 사용자 확정)."""
    rid = "consecutive_lower_closes"
    closes, lows, dates = series["closes"], series["lows"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    run = 0
    max_run, max_end = 0, None
    for i in range(bi + 1, n):
        if closes[i] < lows[i - 1]:
            run += 1
            if run > max_run:
                max_run, max_end = run, i
        else:
            run = 0
    if max_run >= LOWER_CLOSE_RUN:
        return {"id": rid, "status": "violation",
                "detail": f"종가<전일 저가 {max_run}일 연속 (~{dates[max_end]})"}
    if run == LOWER_CLOSE_RUN - 1:
        return {"id": rid, "status": "pass",
                "detail": f"경고: 종가<전일 저가 {run}일째 진행 중"}
    return {"id": rid, "status": "pass", "detail": "연속 저저점 없음"}
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sepa): 매도 규칙 ①저거래량돌파 ②대량후퇴 ③연속저저점 판정"
```

---

### Task 3: 규칙 ④⑤⑥ — 이평선 아래 마감 · 하락일/나쁜 마감 우세 · 스쿼트

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (함수 추가)
- Test: `tests/test_sell_rules.py` (테스트 추가)

**Interfaces:**
- Produces:
  - `rule_close_below_ma(series, bi) -> dict`
  - `rule_weak_days_dominant(series, bi) -> dict`
  - `rule_squat(series, bi, pivot_price) -> dict`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_sell_rules.py`에 추가:

```python
from canslim_lib.sell_rules import (
    rule_close_below_ma,
    rule_weak_days_dominant,
    rule_squat,
)


# --- 규칙 ④ 이평선 아래 마감 ---

def test_rule4_violation_close_below_ma20():
    # 60일 100 유지 → 돌파 106 → 90 급락(20일선 약 100 아래)
    closes = [100.0] * 60 + [106.0, 90.0]
    s = make_series(closes)
    r = rule_close_below_ma(s, 60)
    assert r["status"] == "violation"


def test_rule4_severe_below_ma50_on_heavy_volume():
    closes = [100.0] * 60 + [106.0, 80.0]  # 50일선(약 100)도 하회
    vols = [1000.0] * 61 + [2000.0]        # 대량 거래
    s = make_series(closes, volumes=vols)
    r = rule_close_below_ma(s, 60)
    assert r["status"] == "violation"
    assert "심각" in r["detail"]


def test_rule4_pass_holds_above_ma20():
    closes = [100.0] * 60 + [106.0, 107.0, 108.0]
    s = make_series(closes)
    assert rule_close_below_ma(s, 60)["status"] == "pass"


def test_rule4_pending_no_post_breakout_days():
    closes = [100.0] * 61
    s = make_series(closes)
    assert rule_close_below_ma(s, 60)["status"] == "pending"


# --- 규칙 ⑤ 하락일·나쁜 마감 우세 (통합) ---

def test_rule5_pending_under_five_days():
    closes = [100.0] * 30 + [106.0, 105.0, 104.0]  # 경과 2일
    s = make_series(closes)
    assert rule_weak_days_dominant(s, 30)["status"] == "pending"


def test_rule5_violation_more_down_days():
    # 경과 6일: 하락 4 · 상승 2
    closes = [100.0] * 30 + [106.0, 104.0, 102.0, 103.0, 101.0, 99.0, 100.0]
    s = make_series(closes)
    r = rule_weak_days_dominant(s, 30)
    assert r["status"] == "violation"


def test_rule5_violation_more_bad_closes():
    # 종가는 계속 오르는데(하락일 0) 매일 일중 고점에서 크게 밀려 하단 마감
    closes = [100.0] * 30 + [106.0 + i for i in range(7)]
    highs = [c * 1.01 for c in closes[:31]] + [c + 10 for c in closes[31:]]
    lows = [c * 0.99 for c in closes[:31]] + [c - 0.5 for c in closes[31:]]
    s = make_series(closes, highs=highs, lows=lows)
    r = rule_weak_days_dominant(s, 30)
    assert r["status"] == "violation"


def test_rule5_pass_up_days_dominant():
    # 경과 6일 모두 상승, 기본 고저(±1%)면 종가=중간값이라 나쁜/좋은 마감 모두 0
    closes = [100.0] * 30 + [106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0]
    s = make_series(closes)
    assert rule_weak_days_dominant(s, 30)["status"] == "pass"


# --- 규칙 ⑥ 스쿼트 ---

def test_rule6_violation_close_back_below_pivot():
    closes = [100.0] * 30 + [106.0, 103.0]  # 피벗 105 아래로 복귀 마감
    s = make_series(closes)
    assert rule_squat(s, 30, 105.0)["status"] == "violation"


def test_rule6_pass_holds_above_pivot():
    closes = [100.0] * 30 + [106.0, 107.0]
    s = make_series(closes)
    assert rule_squat(s, 30, 105.0)["status"] == "pass"


def test_rule6_na_without_pivot():
    s = make_series([100.0] * 32)
    assert rule_squat(s, 30, None)["status"] == "na"


def test_rule6_pending_no_post_breakout_days():
    closes = [100.0] * 30 + [106.0]
    s = make_series(closes)
    assert rule_squat(s, 30, 105.0)["status"] == "pending"
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: FAIL — `ImportError: cannot import name 'rule_close_below_ma'`

- [ ] **Step 3: 구현** — `sell_rules.py`에 추가:

```python
def rule_close_below_ma(series, bi):
    """규칙④ 이평선 아래 마감: 돌파 후 종가<20일선이면 위반.
    종가<50일선 + 대량 거래면 '심각' 표기(위반 1건으로 집계)."""
    rid = "close_below_ma"
    closes, vols, dates = series["closes"], series["volumes"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    first, severe, computable = None, None, False
    for i in range(bi + 1, n):
        if i + 1 < 20:
            continue  # 20일선 계산 불가
        computable = True
        ma20 = sum(closes[i - 19:i + 1]) / 20
        if closes[i] < ma20 and first is None:
            first = i
        if i + 1 >= 50:
            ma50 = sum(closes[i - 49:i + 1]) / 50
            avg = avg_volume(vols, i)
            if (closes[i] < ma50 and avg and vols[i] >= HEAVY_VOL_MULT * avg
                    and severe is None):
                severe = i
    if not computable:
        return {"id": rid, "status": "pending", "detail": "20일선 계산에 데이터 부족"}
    if severe is not None:
        return {"id": rid, "status": "violation",
                "detail": f"심각: {dates[severe]} 50일선 아래 + 대량 거래 마감"}
    if first is not None:
        return {"id": rid, "status": "violation", "detail": f"{dates[first]} 20일선 아래 마감"}
    return {"id": rid, "status": "pass", "detail": "20일선 위 유지"}


def rule_weak_days_dominant(series, bi):
    """규칙⑤ 하락일·나쁜 마감 우세(통합): 돌파 후 5거래일 이상 지난 뒤,
    하락일>상승일 또는 나쁜 마감>좋은 마감이면 위반.
    나쁜 마감 = 종가가 당일 고저 범위 아래 절반. 보합·고가=저가 날은 세지 않음."""
    rid = "weak_days_dominant"
    closes, highs, lows = series["closes"], series["highs"], series["lows"]
    n = len(closes)
    elapsed = n - (bi + 1)
    if elapsed < MIN_TREND_DAYS:
        return {"id": rid, "status": "pending",
                "detail": f"경과 {elapsed}거래일 — {MIN_TREND_DAYS}거래일부터 판정"}
    down = up = bad = good = 0
    for i in range(bi + 1, n):
        if closes[i] < closes[i - 1]:
            down += 1
        elif closes[i] > closes[i - 1]:
            up += 1
        if highs[i] > lows[i]:
            mid = (highs[i] + lows[i]) / 2
            if closes[i] < mid:
                bad += 1
            elif closes[i] > mid:
                good += 1
    counts = f"하락 {down}·상승 {up} / 나쁜마감 {bad}·좋은마감 {good}"
    if down > up or bad > good:
        return {"id": rid, "status": "violation", "detail": counts}
    return {"id": rid, "status": "pass", "detail": counts}


def rule_squat(series, bi, pivot_price):
    """규칙⑥ 스쿼트(돌파 실패): 돌파 후 종가가 피벗 아래로 복귀하면 위반."""
    rid = "squat"
    if pivot_price is None:
        return {"id": rid, "status": "na", "detail": "피벗 없음 — 판정 불가"}
    closes, dates = series["closes"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    for i in range(bi + 1, n):
        if closes[i] < pivot_price:
            return {"id": rid, "status": "violation",
                    "detail": f"{dates[i]} 종가가 피벗({pivot_price:,.0f}) 아래 복귀"}
    return {"id": rid, "status": "pass", "detail": "피벗 위 유지"}
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: 30 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sepa): 매도 규칙 ④이평선이탈 ⑤약세우세 ⑥스쿼트 판정"
```

---

### Task 4: evaluate_holding — 종합 신호(손절 우선 → 위반 개수)

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py`
- Test: `tests/test_sell_rules.py`

**Interfaces:**
- Produces: `evaluate_holding(series, buy_date: str, buy_price: float, stop_loss_pct: float, pivot_price: float | None = None) -> dict` — 키:
  `current_price, profit_pct, stop_price, pct_to_stop, breakout_date, breakout_date_estimated, signal("stop_loss"|"early_sell"|"hold"), violation_count, rules(list[dict], 6개 고정 순서)`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_sell_rules.py`에 추가:

```python
from canslim_lib.sell_rules import evaluate_holding


def _clean_series():
    """위반 없는 시나리오: 대량 거래 돌파 후 얕은 상승 유지."""
    closes = [100.0] * 60 + [106.0, 107.0, 108.0]
    vols = [1000.0] * 60 + [2000.0, 900.0, 900.0]
    return make_series(closes, volumes=vols)


def test_evaluate_holding_hold_when_clean():
    s = _clean_series()
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    assert r["signal"] == "hold"
    assert r["violation_count"] == 0
    assert r["breakout_date"] == s["dates"][60]
    assert r["breakout_date_estimated"] is False
    assert len(r["rules"]) == 6


def test_evaluate_holding_early_sell_counts_violations():
    # 저거래량 돌파(①) + 피벗 아래 복귀(⑥) → 위반 2건
    closes = [100.0] * 60 + [106.0, 103.0]
    vols = [1000.0] * 60 + [800.0, 900.0]
    s = make_series(closes, volumes=vols)
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    assert r["signal"] == "early_sell"
    assert r["violation_count"] == 2


def test_evaluate_holding_stop_loss_overrides_rules():
    # 현재가 95 <= 손절가 106*0.96=101.76 → 위반과 무관하게 손절 신호
    closes = [100.0] * 60 + [106.0, 95.0]
    s = make_series(closes)
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    assert r["signal"] == "stop_loss"
    assert r["stop_price"] == 101.76


def test_evaluate_holding_estimated_breakout_without_pivot():
    s = _clean_series()
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=None)
    assert r["breakout_date_estimated"] is True
    assert r["rules"][5]["status"] == "na"  # 스쿼트는 피벗 없어 판정 불가


def test_evaluate_holding_pct_to_stop_sign():
    s = _clean_series()
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    # 현재가 108 > 손절가 101.76 → 음수(여유)
    assert r["pct_to_stop"] < 0
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: FAIL — `ImportError: cannot import name 'evaluate_holding'`

- [ ] **Step 3: 구현** — `sell_rules.py`에 추가:

```python
def evaluate_holding(series, buy_date, buy_price, stop_loss_pct, pivot_price=None):
    """보유 1종목 종합 판정. 손절(최우선) → 위반 1개 이상 조기 매도 → 정상 보유."""
    bi, estimated = find_breakout_index(series, buy_date, pivot_price)
    current = series["closes"][-1]
    stop_price = buy_price * (1 + stop_loss_pct / 100)
    rules = [
        rule_low_volume_breakout(series, bi),
        rule_heavy_volume_pullback(series, bi),
        rule_consecutive_lower_closes(series, bi),
        rule_close_below_ma(series, bi),
        rule_weak_days_dominant(series, bi),
        rule_squat(series, bi, pivot_price),
    ]
    violation_count = sum(1 for r in rules if r["status"] == "violation")
    if current <= stop_price:
        signal = "stop_loss"
    elif violation_count >= 1:
        signal = "early_sell"
    else:
        signal = "hold"
    return {
        "current_price": current,
        "profit_pct": round((current / buy_price - 1) * 100, 2),
        "stop_price": round(stop_price, 2),
        "pct_to_stop": round((stop_price / current - 1) * 100, 2),
        "breakout_date": series["dates"][bi],
        "breakout_date_estimated": estimated,
        "signal": signal,
        "violation_count": violation_count,
        "rules": rules,
    }
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: 35 passed

- [ ] **Step 5: 기존 테스트 전체 회귀 확인**

Run: `python -m pytest tests/ -v`
Expected: 전체 passed (기존 test_vcp 등 포함)

- [ ] **Step 6: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sepa): evaluate_holding 종합 신호 — 손절 우선, 위반 개수 집계"
```

---

### Task 5: 매수 목록 파일 + 점검 스크립트

**Files:**
- Create: `public/data/sepa-holdings.json`
- Create: `scripts/screen_holdings_feedback.py`
- Output: `public/data/sepa-holdings-feedback.json` (스크립트 실행 산출)

**Interfaces:**
- Consumes: `evaluate_holding` (Task 4), `ohlcv_matrix.get_series(code)`, `sepa-vcp-candidates.json` / `sepa-power-play-candidates.json` 의 `candidates[].pivot_price`
- Produces: `sepa-holdings-feedback.json` — `{generated_at, asof, stop_loss_pct_default, holdings: [{code, name, market, buy_date, buy_price, quantity, stop_loss_pct, pivot_price, pivot_source, ...evaluate_holding 결과}]}`. 시세 없는 종목은 `signal: "no_data"` 로 포함(누락 금지).

- [ ] **Step 1: 매수 목록 파일 생성** — `public/data/sepa-holdings.json`:

```json
{
  "stop_loss_pct_default": -4,
  "holdings": [
    { "code": "036800", "name": "나이스정보통신", "buy_datetime": "2026-07-01 09:31:32", "buy_price": 29700, "quantity": 435 },
    { "code": "271560", "name": "오리온", "buy_datetime": "2026-07-02 09:07:53", "buy_price": 138500, "quantity": 72 },
    { "code": "010955", "name": "S-Oil우", "buy_datetime": "2026-07-03 09:06:02", "buy_price": 57900, "quantity": 172 },
    { "code": "005430", "name": "한국공항", "buy_datetime": "2026-07-03 14:15:54", "buy_price": 87500, "quantity": 114 }
  ]
}
```

- [ ] **Step 2: 스크립트 작성** — `scripts/screen_holdings_feedback.py`:

```python
# scripts/screen_holdings_feedback.py
"""SEPA 보유 종목 점검 — 미너비니 매도 규칙 위반 피드백.

입력: public/data/sepa-holdings.json (매수 목록, 사용자 관리)
      sepa-vcp-candidates.json / sepa-power-play-candidates.json (피벗, vcp 우선)
출력: public/data/sepa-holdings-feedback.json
정의: docs/superpowers/specs/2026-07-03-sepa-holdings-feedback-design.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import ohlcv_matrix  # noqa: E402
from canslim_lib.sell_rules import evaluate_holding  # noqa: E402

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-holdings.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-holdings-feedback.json"
SIGNAL_LABEL = {"stop_loss": "🔴 손절", "early_sell": "🟠 조기매도",
                "hold": "🟢 정상보유", "no_data": "⚫ 데이터없음"}


def load_pivots() -> dict:
    """code → {pivot, source, market}. vcp를 나중에 읽어 우선 적용."""
    out = {}
    for fname, source in (("sepa-power-play-candidates.json", "power_play"),
                          ("sepa-vcp-candidates.json", "vcp")):
        p = ROOT / "public" / "data" / fname
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for c in data.get("candidates", []):
            if c.get("pivot_price") is not None:
                out[c["code"]] = {"pivot": c["pivot_price"], "source": source,
                                  "market": c.get("market")}
    return out


def run(out_path: Path) -> None:
    if not IN_PATH.exists():
        print(f"❌ 매수 목록 없음: {IN_PATH.relative_to(ROOT)}")
        sys.exit(1)
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    default_stop = data.get("stop_loss_pct_default", -4)
    pivots = load_pivots()

    out_holdings, asof = [], None
    for h in data.get("holdings", []):
        code = h["code"]
        buy_date = h["buy_datetime"][:10]
        stop_pct = h.get("stop_loss_pct", default_stop)
        piv = pivots.get(code, {})
        base = {
            "code": code, "name": h.get("name"), "market": piv.get("market"),
            "buy_date": buy_date, "buy_price": h["buy_price"],
            "quantity": h.get("quantity"), "stop_loss_pct": stop_pct,
            "pivot_price": piv.get("pivot"), "pivot_source": piv.get("source"),
        }
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            out_holdings.append({**base, "signal": "no_data", "violation_count": 0,
                                 "rules": []})
            continue
        r = evaluate_holding(s, buy_date, h["buy_price"], stop_pct,
                             pivot_price=piv.get("pivot"))
        if asof is None or s["dates"][-1] > asof:
            asof = s["dates"][-1]
        out_holdings.append({**base, **r})

    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": asof,
        "stop_loss_pct_default": default_stop,
        "holdings": out_holdings,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"💾 저장: {out_path.relative_to(ROOT)} (기준일 {asof})\n")
    for x in out_holdings:
        label = SIGNAL_LABEL.get(x["signal"], x["signal"])
        extra = f" 위반 {x['violation_count']}건" if x["signal"] == "early_sell" else ""
        print(f"  [{label}{extra}] {x['code']} {x['name']} "
              f"매수 {x['buy_price']:,} → 현재 {x.get('current_price') or '?'} "
              f"({x.get('profit_pct', '?')}%)")
        for r in x.get("rules", []):
            mark = {"violation": "✗", "pass": "✓"}.get(r["status"], "―")
            print(f"      {mark} {r['id']}: {r['detail']}")


def main():
    ap = argparse.ArgumentParser(description="SEPA 보유 종목 매도 규칙 점검")
    ap.add_argument("--out", default=None, help=f"출력(default {OUT_PATH.name})")
    args = ap.parse_args()
    out_path = (Path(args.out) if args.out and Path(args.out).is_absolute()
                else ROOT / args.out if args.out else OUT_PATH)
    run(out_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 실행 및 결과 검증**

Run: `python scripts/screen_holdings_feedback.py`
Expected: `sepa-holdings-feedback.json` 생성, 4종목 모두 출력되고 각 6개 규칙의 판정과 사유가 보임. 매수 1~2일차라 규칙⑤는 pending이어야 정상. 결과를 눈으로 확인해 스펙과 어긋난 판정이 없는지 본다 (예: 오늘 매수한 한국공항·S-Oil우는 돌파 다음 날 데이터가 없어 ②③④⑥ pending 가능).

- [ ] **Step 4: 결과 JSON 구조 확인**

Run: `python -c "import json; d=json.load(open('public/data/sepa-holdings-feedback.json', encoding='utf-8')); print(d['asof'], len(d['holdings']), [h['signal'] for h in d['holdings']])"`
Expected: `2026-07-03 4 [...]` 형태

- [ ] **Step 5: Commit**

```bash
git add public/data/sepa-holdings.json public/data/sepa-holdings-feedback.json scripts/screen_holdings_feedback.py
git commit -m "feat(sepa): 보유 종목 점검 스크립트 + 매수 목록·피드백 데이터"
```

---

### Task 6: 페이지 섹션 — SepaHoldingsSection + page.tsx 통합

**Files:**
- Create: `src/app/stocks/sepa/SepaHoldingsSection.tsx`
- Modify: `src/app/stocks/sepa/page.tsx` (import 1줄, Promise.all 1줄, 섹션 렌더 1블록 — 1단계 요약 `</section>` 직후)

**Interfaces:**
- Consumes: `sepa-holdings-feedback.json` (Task 5 산출 스키마)
- Produces: `SepaHoldingsSection({ data: HoldingsFeedbackFile | null })` 서버 컴포넌트. 데이터 없거나 holdings 비면 `null` 반환(섹션 숨김).

- [ ] **Step 1: 컴포넌트 작성** — `src/app/stocks/sepa/SepaHoldingsSection.tsx`:

```tsx
// 보유 종목 점검 — 미너비니 매도 규칙 위반 피드백 (서버 렌더 전용, 상호작용 없음)

export interface HoldingRule {
  id: string;
  status: "violation" | "pass" | "pending" | "na";
  detail: string;
}
export interface HoldingFeedback {
  code: string;
  name: string;
  market?: string | null;
  buy_date: string;
  buy_price: number;
  quantity?: number;
  stop_loss_pct: number;
  pivot_price?: number | null;
  pivot_source?: string | null;
  current_price?: number;
  profit_pct?: number;
  stop_price?: number;
  pct_to_stop?: number;
  breakout_date?: string;
  breakout_date_estimated?: boolean;
  signal: "stop_loss" | "early_sell" | "hold" | "no_data";
  violation_count: number;
  rules: HoldingRule[];
}
export interface HoldingsFeedbackFile {
  generated_at?: string;
  asof?: string;
  holdings?: HoldingFeedback[];
}

const RULE_LABELS: Record<string, string> = {
  low_volume_breakout: "① 저거래량 돌파",
  heavy_volume_pullback: "② 대량 거래 후퇴",
  consecutive_lower_closes: "③ 연속 저저점(종가)",
  close_below_ma: "④ 이평선 아래 마감",
  weak_days_dominant: "⑤ 하락일·나쁜 마감 우세",
  squat: "⑥ 스쿼트(피벗 복귀)",
};

const SIGNAL_META: Record<HoldingFeedback["signal"], { label: string; bg: string; fg: string }> = {
  stop_loss: { label: "🔴 손절", bg: "rgba(255,180,171,0.18)", fg: "#ffb4ab" },
  early_sell: { label: "🟠 조기 매도 신호", bg: "rgba(251,146,60,0.18)", fg: "#fb923c" },
  hold: { label: "🟢 정상 보유", bg: "rgba(16,185,129,0.18)", fg: "#34d399" },
  no_data: { label: "⚫ 데이터 없음", bg: "rgba(148,163,184,0.18)", fg: "#94a3b8" },
};

const STATUS_MARK: Record<HoldingRule["status"], { mark: string; cls: string }> = {
  violation: { mark: "✗", cls: "text-[#ffb4ab]" },
  pass: { mark: "✓", cls: "text-[#34d399]" },
  pending: { mark: "―", cls: "text-on-surface-variant/50" },
  na: { mark: "―", cls: "text-on-surface-variant/50" },
};

function fmtWon(v?: number | null): string {
  return v == null ? "-" : Math.round(v).toLocaleString();
}

export function SepaHoldingsSection({ data }: { data: HoldingsFeedbackFile | null }) {
  const holdings = data?.holdings ?? [];
  if (holdings.length === 0) return null;
  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">monitor_heart</span>
        보유 종목 점검
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">
          매도 규칙 위반 감시 · 기준일 {data?.asof ?? "-"}
        </span>
      </h3>
      <div className="grid gap-4 sm:grid-cols-2">
        {holdings.map((h) => {
          const meta = SIGNAL_META[h.signal] ?? SIGNAL_META.no_data;
          const badgeLabel =
            h.signal === "early_sell" ? `${meta.label} · 위반 ${h.violation_count}건` : meta.label;
          return (
            <div key={h.code} className="bg-surface-container-low rounded-xl ghost-border p-4 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="font-bold text-on-surface">
                  {h.name}
                  <span className="text-xs font-normal text-on-surface-variant/50 ml-1.5">{h.code}</span>
                </div>
                <span
                  className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                  style={{ backgroundColor: meta.bg, color: meta.fg }}
                >
                  {badgeLabel}
                </span>
              </div>
              <div className="text-xs text-on-surface-variant space-y-0.5">
                <p>
                  {h.buy_date} 매수 {fmtWon(h.buy_price)}원 → 현재 {fmtWon(h.current_price)}원{" "}
                  <strong style={{ color: (h.profit_pct ?? 0) >= 0 ? "#34d399" : "#ffb4ab" }}>
                    {h.profit_pct != null ? `${h.profit_pct > 0 ? "+" : ""}${h.profit_pct}%` : "-"}
                  </strong>
                </p>
                <p className="text-on-surface-variant/70">
                  손절선 {fmtWon(h.stop_price)}원({h.stop_loss_pct}%) · 손절까지{" "}
                  {h.pct_to_stop != null ? `${h.pct_to_stop}%` : "-"} · 돌파일 {h.breakout_date ?? "-"}
                  {h.breakout_date_estimated ? " (매수일 추정)" : ""}
                </p>
              </div>
              {h.rules.length > 0 && (
                <ul className="text-[11px] space-y-1 pt-2 border-t border-outline-variant/10">
                  {h.rules.map((r) => {
                    const sm = STATUS_MARK[r.status] ?? STATUS_MARK.na;
                    return (
                      <li key={r.id} className="flex gap-1.5 leading-relaxed">
                        <span className={`${sm.cls} font-bold shrink-0`}>{sm.mark}</span>
                        <span className="text-on-surface-variant">
                          <strong className={r.status === "violation" ? "text-[#ffb4ab]" : "text-on-surface"}>
                            {RULE_LABELS[r.id] ?? r.id}
                          </strong>{" "}
                          — {r.detail}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: page.tsx 통합** — `src/app/stocks/sepa/page.tsx` 3곳 수정:

import 추가 (line 4 근처):

```tsx
import { SepaHoldingsSection, type HoldingsFeedbackFile } from "./SepaHoldingsSection";
```

`Promise.all` 배열 끝에 추가 (line 72-79):

```tsx
  const [trend, vcp, ppTrend, ppAll, threeC, exclusionFile, holdingsFeedback] = await Promise.all([
    readJson<TrendData>("sepa-trend-candidates.json"),
    readJson<CandidateFile>(PATTERNS.vcp.file),
    readJson<CandidateFile>(PATTERNS.powerplayTrend.file),
    readJson<CandidateFile>(PATTERNS.powerplayAll.file),
    readJson<CandidateFile>(PATTERNS.threeC.file),
    readJson<ExclusionFile>("sepa-exclusions.json"),
    readJson<HoldingsFeedbackFile>("sepa-holdings-feedback.json"),
  ]);
```

1단계 트렌드 요약 `</section>` 바로 다음, `<PatternSection config={PATTERNS.vcp}` 앞에 삽입:

```tsx
      <SepaHoldingsSection data={holdingsFeedback} />
```

- [ ] **Step 3: 타입·빌드 검증**

Run: `npx tsc --noEmit`
Expected: 오류 없음

Run: `npm run build`
Expected: 빌드 성공, `/stocks/sepa` 경로 오류 없음

- [ ] **Step 4: 렌더 확인**

`npm run dev` 실행 후 `http://localhost:3000/stocks/sepa` 를 열어 (또는 curl로 HTML 확인) "보유 종목 점검" 섹션이 1단계 요약 아래에 4종목 카드로 나오는지, 신호 배지·규칙 목록·사유가 표시되는지 확인.

- [ ] **Step 5: 전체 테스트 회귀**

Run: `python -m pytest tests/ -q && npx vitest run`
Expected: 전부 passed

- [ ] **Step 6: Commit**

```bash
git add src/app/stocks/sepa/SepaHoldingsSection.tsx src/app/stocks/sepa/page.tsx
git commit -m "feat(sepa): /stocks/sepa 보유 종목 점검 섹션 — 신호 배지 + 6규칙 판정 카드"
```

---

## Self-Review 결과

- 스펙 커버리지: 입력 파일(Task 5 Step 1), 돌파일·피벗(Task 1, 5), 6규칙(Task 2-3), 종합 신호·위반 개수(Task 4), 출력 스키마(Task 5), 페이지 표시·숨김 조건(Task 6), 테스트(Task 1-4), 실행 검증(Task 5-6) — 모두 대응 태스크 있음.
- no_data 처리: 스펙에 없던 "시세 캐시 미스" 케이스를 Task 5-6에서 `signal: "no_data"` 로 명시(종목 누락 방지).
- 타입 일관성: rule dict 키(id/status/detail), evaluate_holding 키, TSX 인터페이스 모두 동일 명칭 확인.
