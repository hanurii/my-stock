# 보유 매도규칙 v2 (규칙 확장 + check-holdings 스킬화) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보유 종목 매도규칙 점검을 오라클(WAGE·OUTR)로 보정해 강화하고(규칙③ 저가·거래량 게이트, 규칙⑥ 스쿼트+거래량 비대칭 통합), `/sepa` 파이프라인에서 자동 실행되도록 `check-holdings` 스킬로 정식화한다.

**Architecture:** 순수 판정 모듈 `sell_rules.py`(6개 규칙 함수 + `evaluate_holding`)를 수정하고, 실행 스크립트 `screen_holdings_feedback.py`는 빈 목록에서 정상 종료하도록 손본다. 페이지는 라벨 2줄만 정정. 새 스킬 문서 + `/sepa` 오케스트레이터 편입. 판정 로직은 pytest(합성 케이스 + 실데이터 오라클 픽스처)로 검증.

**Tech Stack:** Python 3(표준 라이브러리만), pytest, Next.js/TSX(라벨 문자열만), Markdown 스킬 문서.

## Global Constraints

- 작업 위치: worktree `C:/Users/hanul/playground/my-stock-holdings-rules`, 브랜치 `feat/holdings-rules-v2`. **다른 경로/브랜치 건드리지 말 것.**
- 규칙은 **6개 유지**. `evaluate_holding`의 `rules` 배열 순서·인덱스 고정: [0]low_volume_breakout [1]heavy_volume_pullback [2]**consecutive_lower_lows** [3]close_below_ma [4]weak_days_dominant [5]**breakout_failure**.
- 규칙 반환 상태는 `violation` / `pass` / `pending` / `na` **4개만**. 새 상태 추가 금지. 🟡 소프트 경고는 `pass` + detail 텍스트로 표현.
- 50일 평균 거래량 = `avg_volume(vols, i)` (판정일 직전 최대 50거래일, 판정일 제외, 표본<5면 None). 기존 함수 그대로 사용.
- 상수: `LOWER_LOW_RUN = 3`, `SQUAT_GRACE_DAYS = 10`.
- 커밋 메시지 말미: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- 스펙: `docs/superpowers/specs/2026-07-05-holdings-rules-v2-design.md`.

---

### Task 1: 규칙③ 저점경신 — 저가 기준 + 거래량 게이트로 재작성

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (상수 `LOWER_CLOSE_RUN`→`LOWER_LOW_RUN`; `rule_consecutive_lower_closes`→`rule_consecutive_lower_lows`; `evaluate_holding`의 rules[2] 호출)
- Test: `tests/test_sell_rules.py` (import 줄 + 규칙③ 테스트 블록 교체)

**Interfaces:**
- Produces: `rule_consecutive_lower_lows(series, bi) -> {"id": "consecutive_lower_lows", "status", "detail"}`

- [ ] **Step 1: 기존 규칙③ 테스트를 저가 기준으로 교체 (실패하는 새 테스트 작성)**

`tests/test_sell_rules.py`에서 import 줄(78행 부근)의 `rule_consecutive_lower_closes`를 `rule_consecutive_lower_lows`로 바꾼다:

```python
from canslim_lib.sell_rules import (
    rule_low_volume_breakout,
    rule_heavy_volume_pullback,
    rule_consecutive_lower_lows,
)
```

그리고 `--- 규칙 ③ ...` 헤더부터 `test_rule3_pass_when_run_broken` 끝까지(기존 3개 테스트)를 아래로 교체한다:

```python
# --- 규칙 ③ 연속 저저점 (저가 < 전일 저가 + 거래량 ≥ 50일 평균) ---

def test_rule3_violation_three_vol_backed_lower_lows():
    # 저가가 3일 연속 하락 + 각 날 거래량이 50일 평균(1000) 이상
    lows = [99.0] * 50 + [98.0, 97.0, 96.0]          # 마지막 3일 저점경신
    closes = [100.0] * 50 + [99.0, 98.0, 97.0]
    vols = [1000.0] * 50 + [1200.0, 1300.0, 1400.0]  # 거래량 붙음
    s = make_series(closes, volumes=vols, lows=lows)
    r = rule_consecutive_lower_lows(s, 49)
    assert r["status"] == "violation"
    assert "거래량 붙은 저점경신" in r["detail"]


def test_rule3_pass_lower_lows_but_light_volume():
    # 저점경신 3연속이지만 거래량이 평균 미만 → 위반 아님(🟡경고)
    lows = [99.0] * 50 + [98.0, 97.0, 96.0]
    closes = [100.0] * 50 + [99.0, 98.0, 97.0]
    vols = [1000.0] * 50 + [700.0, 800.0, 600.0]     # 거래량 낮음
    s = make_series(closes, volumes=vols, lows=lows)
    r = rule_consecutive_lower_lows(s, 49)
    assert r["status"] == "pass"
    assert "🟡" in r["detail"]


def test_rule3_pass_two_vol_backed_lower_lows():
    # 거래량 붙은 저점경신이 2일뿐 → 위반 아님
    lows = [99.0] * 50 + [98.0, 97.0, 99.5]          # 3일째는 저점경신 아님
    closes = [100.0] * 50 + [99.0, 98.0, 100.0]
    vols = [1000.0] * 50 + [1200.0, 1300.0, 1400.0]
    s = make_series(closes, volumes=vols, lows=lows)
    assert rule_consecutive_lower_lows(s, 49)["status"] == "pass"


def test_rule3_pending_no_post_breakout_days():
    s = make_series([100.0] * 51)
    assert rule_consecutive_lower_lows(s, 50)["status"] == "pending"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd C:/Users/hanul/playground/my-stock-holdings-rules && python -m pytest tests/test_sell_rules.py -k rule3 -v`
Expected: FAIL — `ImportError: cannot import name 'rule_consecutive_lower_lows'`

- [ ] **Step 3: sell_rules.py 구현**

상수 교체 (파일 상단 `LOWER_CLOSE_RUN = 3` → ):

```python
LOWER_LOW_RUN = 3           # 연속 저점경신(저가 기준) 위반 기준 일수
```

`rule_consecutive_lower_closes` 함수 전체를 아래로 교체:

```python
def rule_consecutive_lower_lows(series, bi):
    """규칙③ 연속 저저점(저가 기준+거래량): 돌파 후 '저가<전일 저가'이고
    거래량 ≥ 50일 평균인 날이 3거래일 연속이면 위반. 거래량 낮은 저점경신은
    위반이 아니라 🟡경고로만 표시(미너비니 WAGE 사례)."""
    rid = "consecutive_lower_lows"
    lows, vols, dates = series["lows"], series["volumes"], series["dates"]
    n = len(lows)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    qrun = qmax = 0          # 거래량 붙은 저점경신 연속
    qend = None
    rawrun = rawmax = 0      # 거래량 무관 저점경신 연속(경고용)
    for i in range(bi + 1, n):
        is_ll = lows[i] < lows[i - 1]
        rawrun = rawrun + 1 if is_ll else 0
        rawmax = max(rawmax, rawrun)
        avg = avg_volume(vols, i)
        qualified = (is_ll and avg is not None and vols[i] is not None
                     and vols[i] >= avg)
        qrun = qrun + 1 if qualified else 0
        if qrun > qmax:
            qmax, qend = qrun, i
    if qmax >= LOWER_LOW_RUN:
        return {"id": rid, "status": "violation",
                "detail": f"거래량 붙은 저점경신 {qmax}일 연속 (~{dates[qend]})"}
    if rawmax >= LOWER_LOW_RUN:
        return {"id": rid, "status": "pass",
                "detail": f"🟡경고: 저점경신 {rawmax}회(거래량 낮음)"}
    return {"id": rid, "status": "pass", "detail": "연속 저저점 없음"}
```

`evaluate_holding` 내부 rules 리스트에서 규칙③ 호출을 교체:

```python
        rule_consecutive_lower_lows(series, bi),
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -k rule3 -v`
Expected: PASS (4개)

- [ ] **Step 5: 커밋**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): 규칙③ 저점경신 저가기준+거래량 게이트로 재작성(WAGE 오라클)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 규칙⑥ 스쿼트+거래량 비대칭 통합 (`rule_breakout_failure`)

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (상수 `SQUAT_GRACE_DAYS` 추가; `rule_squat`→`rule_breakout_failure` 재작성; `evaluate_holding`의 rules[5] 호출)
- Test: `tests/test_sell_rules.py` (import 줄 + 규칙⑥ 테스트 블록 + evaluate_holding 스쿼트 흐름 테스트 교체)

**Interfaces:**
- Consumes: `find_breakout_index`(기존), `avg_volume`(기존)
- Produces: `rule_breakout_failure(series, bi, pivot_price, breakout_confirmed=True) -> {"id": "breakout_failure", "status", "detail"}`

- [ ] **Step 1: 규칙⑥ 테스트 교체 (실패하는 새 테스트)**

import 줄(185행 부근)에서 `rule_squat`→`rule_breakout_failure`:

```python
from canslim_lib.sell_rules import (
    rule_close_below_ma,
    rule_weak_days_dominant,
    rule_breakout_failure,
)
```

`--- 규칙 ⑥ 스쿼트 ---` 헤더부터 `test_rule6_same_day_squat_violation` 끝까지 교체:

```python
# --- 규칙 ⑥ 돌파 실패 (스쿼트 + 거래량 비대칭 통합) ---

def test_rule6_violation_volume_backed_break_ignores_grace():
    # 돌파 다음 날 피벗 아래로 되밀림 + 거래량 > 돌파일 → 유예 무시 위반
    closes = [100.0] * 30 + [106.0, 103.0]
    vols = [1000.0] * 30 + [500.0, 900.0]   # 돌파일 500 < 되밀림일 900
    s = make_series(closes, volumes=vols)
    r = rule_breakout_failure(s, 30, 105.0)
    assert r["status"] == "violation"
    assert "거래량 동반" in r["detail"]


def test_rule6_pass_quiet_squat_within_grace():
    # 조용한 스쿼트(거래량 ≤ 돌파일) + 유예(10거래일) 이내 → 관찰중(pass)
    closes = [100.0] * 30 + [106.0, 103.0]
    vols = [1000.0] * 30 + [2000.0, 800.0]  # 되밀림일 800 < 돌파일 2000
    s = make_series(closes, volumes=vols)
    r = rule_breakout_failure(s, 30, 105.0)
    assert r["status"] == "pass"
    assert "관찰중" in r["detail"]


def test_rule6_violation_quiet_squat_past_grace():
    # 조용한 스쿼트인데 유예(10거래일) 초과도 피벗 아래 → 위반
    closes = [100.0] * 30 + [106.0] + [103.0] * 12  # 돌파 후 12일 내내 아래
    vols = [1000.0] * 30 + [2000.0] + [800.0] * 12
    s = make_series(closes, volumes=vols)
    r = rule_breakout_failure(s, 30, 105.0)
    assert r["status"] == "violation"
    assert "유예 초과" in r["detail"]


def test_rule6_pass_reversal_recovery():
    # 스쿼트 후 최근 종가가 피벗 위로 복귀 → pass
    closes = [100.0] * 30 + [106.0, 103.0, 107.0]
    vols = [1000.0] * 30 + [2000.0, 800.0, 900.0]
    s = make_series(closes, volumes=vols)
    r = rule_breakout_failure(s, 30, 105.0)
    assert r["status"] == "pass"
    assert "회복" in r["detail"]


def test_rule6_pass_holds_above_pivot():
    closes = [100.0] * 30 + [106.0, 107.0]
    s = make_series(closes)
    assert rule_breakout_failure(s, 30, 105.0)["status"] == "pass"


def test_rule6_na_without_pivot():
    s = make_series([100.0] * 32)
    assert rule_breakout_failure(s, 30, None)["status"] == "na"


def test_rule6_na_when_breakout_not_confirmed():
    closes = [100.0] * 30 + [101.0, 102.0]  # 피벗 105 미돌파
    s = make_series(closes)
    r = rule_breakout_failure(s, 30, 105.0, breakout_confirmed=False)
    assert r["status"] == "na"
```

이어서, 아래쪽 `evaluate_holding` 관련 스쿼트 흐름 테스트 2개를 새 동작에 맞게 교체한다.
`test_evaluate_holding_intraday_squat_flow`를 다음으로 교체(당일 조용 스쿼트 → 관찰중 pass):

```python
def test_evaluate_holding_intraday_squat_flow():
    # 장중 돌파(고가 106>피벗 105) 후 당일 조용히 아래 마감 → 돌파 확인 + 관찰중(pass)
    closes = [100.0] * 60 + [103.0]
    highs = [c * 1.01 for c in closes[:60]] + [106.0]
    s = make_series(closes, highs=highs)
    r = evaluate_holding(s, s["dates"][60], 103.0, -4.0, pivot_price=105.0)
    assert r["breakout_date_estimated"] is False
    assert r["rules"][5]["status"] == "pass"
    assert "관찰중" in r["rules"][5]["detail"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py -k "rule6 or squat_flow" -v`
Expected: FAIL — `ImportError: cannot import name 'rule_breakout_failure'`

- [ ] **Step 3: sell_rules.py 구현**

상수 추가(파일 상단 상수 블록):

```python
SQUAT_GRACE_DAYS = 10       # 돌파 후 반전 회복 유예(약 2주)
```

`rule_squat` 함수 전체를 아래로 교체:

```python
def rule_breakout_failure(series, bi, pivot_price, breakout_confirmed=True):
    """규칙⑥ 돌파 실패(스쿼트+거래량 비대칭 통합).
    - 거래량 동반(>돌파일) 피벗 이탈 → 유예 무시 위반(실패한 돌파).
    - 조용한 스쿼트 → 10거래일 유예 안에선 관찰중(pass), 초과하면 위반.
    - 피벗 위 복귀 → pass. 피벗/돌파 미확인 → na."""
    rid = "breakout_failure"
    if pivot_price is None:
        return {"id": rid, "status": "na", "detail": "피벗 없음 — 판정 불가"}
    if not breakout_confirmed:
        return {"id": rid, "status": "na", "detail": "피벗 돌파 미확인 — 판정 불가"}
    closes, vols, dates = series["closes"], series["volumes"], series["dates"]
    n = len(closes)
    breakout_vol = vols[bi]
    below = [i for i in range(bi, n) if closes[i] < pivot_price]
    if not below:
        return {"id": rid, "status": "pass", "detail": "피벗 위 유지"}
    # 거래량 동반 돌파 실패(비대칭) — 유예 무시, 가장 심한 날을 detail로
    worst = None
    if breakout_vol:
        for i in below:
            if vols[i] and vols[i] > breakout_vol:
                ratio = vols[i] / breakout_vol
                if worst is None or ratio > worst[1]:
                    worst = (i, ratio)
    if worst:
        i, ratio = worst
        return {"id": rid, "status": "violation",
                "detail": f"거래량 동반 돌파 실패 — {dates[i]} 거래량 {ratio:.1f}배(돌파일 대비)"}
    # 조용한 스쿼트 — 회복/유예 판정
    if closes[-1] >= pivot_price:
        return {"id": rid, "status": "pass", "detail": "스쿼트 후 반전 회복(피벗 위 복귀)"}
    elapsed = (n - 1) - bi
    if elapsed <= SQUAT_GRACE_DAYS:
        return {"id": rid, "status": "pass",
                "detail": f"🟡 반전 회복 관찰중 (D+{elapsed}/{SQUAT_GRACE_DAYS})"}
    return {"id": rid, "status": "violation",
            "detail": f"유예 초과 — 피벗 회복 실패 (D+{elapsed})"}
```

`evaluate_holding` 내부 rules 리스트에서 규칙⑥ 호출을 교체:

```python
        rule_breakout_failure(series, bi, pivot_price, breakout_confirmed=not estimated),
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -k "rule6 or squat_flow" -v`
Expected: PASS

- [ ] **Step 5: 전체 회귀 확인 (기존 evaluate_holding 테스트가 새 동작과 맞는지)**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: PASS 전부. (`test_evaluate_holding_early_sell_counts_violations`는 돌파일 800 < 되밀림일 900이라 규칙⑥ 거래량 경로로 위반 유지 → count 2 그대로.)
만약 실패하면 해당 테스트의 시나리오 거래량을 확인(돌파일 vs 되밀림일 대소)해 의도대로 맞춘다.

- [ ] **Step 6: 커밋**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): 규칙⑥ 스쿼트+거래량 비대칭 통합(유예 10일, OUTR 오라클)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 규칙④ detail 보강 — "돌파 N거래일째"

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (`rule_close_below_ma`의 20일선 이탈 detail)
- Test: `tests/test_sell_rules.py` (규칙④ 테스트에 문구 단언 1개 추가)

**Interfaces:** 변경 없음(반환 스키마 동일, detail 문자열만 확장)

- [ ] **Step 1: 실패 테스트 추가**

규칙④ 테스트 블록(`test_rule4_pass_holds_above_ma20` 뒤)에 추가:

```python
def test_rule4_detail_shows_days_after_breakout():
    closes = [100.0] * 60 + [106.0, 90.0]  # 돌파(60) 다음 날(61) 20일선 이탈
    s = make_series(closes)
    r = rule_close_below_ma(s, 60)
    assert r["status"] == "violation"
    assert "돌파 1거래일째" in r["detail"]
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py::test_rule4_detail_shows_days_after_breakout -v`
Expected: FAIL (`"돌파 1거래일째"` 없음)

- [ ] **Step 3: 구현**

`rule_close_below_ma`에서 20일선 이탈(첫 위반) 반환 줄을 교체:

```python
    if first is not None:
        return {"id": rid, "status": "violation",
                "detail": f"{dates[first]} 20일선 아래 마감 (돌파 {first - bi}거래일째)"}
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -k rule4 -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): 규칙④ detail에 '돌파 N거래일째' 표기 보강

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: 오라클 회귀 테스트 (WAGE·OUTR 실데이터 픽스처)

**Files:**
- Create: `tests/fixtures/oracle_wage.json`, `tests/fixtures/oracle_outr.json` (Tiingo 실데이터 슬라이스)
- Create: `tests/test_sell_rules_oracle.py`

**Interfaces:**
- Consumes: `evaluate_holding`(Task 1·2 산출), 픽스처 JSON(6키: dates/opens/highs/lows/closes/volumes)

- [ ] **Step 1: 픽스처 생성 (스크래치의 원시 일봉 → 슬라이스)**

이 세션 스크래치패드에 이미 받아둔 원시 파일
`.../scratchpad/raw_WAGE.json`, `raw_OUTR.json`을 필요한 구간으로 잘라 커밋용 픽스처로 만든다.
아래를 스크래치에 `_build_oracle_fixtures.py`로 저장 후 실행:

```python
import json
from pathlib import Path

SCRATCH = Path(r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/b5f4f09c-7e37-4e75-adf8-812f03e8ac64/scratchpad")
OUT = Path(r"C:/Users/hanul/playground/my-stock-holdings-rules/tests/fixtures")
OUT.mkdir(parents=True, exist_ok=True)

def slice_to(name, end):
    s = json.loads((SCRATCH / f"raw_{name}.json").read_text(encoding="utf-8"))
    keep = [i for i, d in enumerate(s["dates"]) if d <= end]
    out = {k: [s[k][i] for i in keep] for k in
           ("dates", "opens", "highs", "lows", "closes", "volumes")}
    (OUT / f"oracle_{name.lower()}.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(name, "rows", len(out["dates"]), out["dates"][0], "~", out["dates"][-1])

slice_to("WAGE", "2014-04-11")   # 돌파 03-18 + 붕괴 03-25~27 포함
slice_to("OUTR", "2014-03-31")   # 돌파 03-04 + 반전 03-06~07 포함
```

Run: `python .../scratchpad/_build_oracle_fixtures.py`
Expected: `WAGE rows ~110 2013-11-01 ~ 2014-04-11`, `OUTR rows ~100 ...`

만약 스크래치 원시 파일이 없으면(세션 재시작 등): `.env`에 `TIINGO_API_KEY`를 넣고
`scratchpad/fetch_oracle_wage_outr.py`(이미 존재)를 먼저 돌려 `raw_*.json`을 재생성한다.

- [ ] **Step 2: 오라클 테스트 작성 (실패 확인용)**

`tests/test_sell_rules_oracle.py`:

```python
"""실데이터 오라클 회귀 — 미너비니 책 예시로 규칙③·⑥ 보정 검증.
픽스처: Tiingo 상폐주 일봉 슬라이스(tests/fixtures/oracle_*.json)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib.sell_rules import evaluate_holding

FIX = Path(__file__).resolve().parent / "fixtures"


def _load(name):
    return json.loads((FIX / f"oracle_{name}.json").read_text(encoding="utf-8"))


def test_wage_lower_lows_and_breakout_failure():
    # WAGE: 03-18 극저거래량 돌파(피벗≈63) → 03-25~27 거래량 붙은 저점경신 + 붕괴
    s = _load("wage")
    r = evaluate_holding(s, "2014-03-18", 63.68, -20.0, pivot_price=63.0)
    assert r["breakout_date_estimated"] is False
    assert r["rules"][2]["status"] == "violation"   # consecutive_lower_lows
    assert r["rules"][5]["status"] == "violation"   # breakout_failure(거래량 동반)
    assert r["rules"][0]["status"] == "violation"   # low_volume_breakout(0.45배)


def test_outr_breakout_failure_volume_asymmetry():
    # OUTR: 03-04 돌파(피벗≈72.7) → 03-06·07 대량거래 반전(비대칭)
    s = _load("outr")
    r = evaluate_holding(s, "2014-03-04", 73.06, -20.0, pivot_price=72.73)
    assert r["breakout_date_estimated"] is False
    assert r["rules"][5]["status"] == "violation"   # breakout_failure
    assert "거래량 동반" in r["rules"][5]["detail"]
```

- [ ] **Step 3: 실행 (통과해야 정상 — Task 1·2 구현이 맞으면 PASS)**

Run: `python -m pytest tests/test_sell_rules_oracle.py -v`
Expected: PASS 2개. 만약 FAIL이면 픽스처의 실제 값으로 돌파 인덱스·거래량을 재확인
(WAGE 03-18 vol 148,400 / OUTR 03-04 vol 1,069,580 기준)하고 pivot 인자를 미세조정.

- [ ] **Step 4: 커밋**

```bash
git add tests/fixtures/oracle_wage.json tests/fixtures/oracle_outr.json tests/test_sell_rules_oracle.py
git commit -m "test(sell-rules): WAGE·OUTR 실데이터 오라클 회귀 테스트(규칙③·⑥)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: 페이지 라벨 정정 (RULE_LABELS 2줄)

**Files:**
- Modify: `src/app/stocks/sepa/SepaHoldingsSection.tsx` (34~41행 `RULE_LABELS`)

**Interfaces:** 렌더 로직 무변경. id 키·라벨 문자열만 교체.

- [ ] **Step 1: RULE_LABELS 교체**

두 항목을 새 id·라벨로 바꾼다:

```tsx
const RULE_LABELS: Record<string, string> = {
  low_volume_breakout: "① 저거래량 돌파",
  heavy_volume_pullback: "② 대량 거래 후퇴",
  consecutive_lower_lows: "③ 연속 저저점(거래량)",
  close_below_ma: "④ 이평선 아래 마감",
  weak_days_dominant: "⑤ 하락일·나쁜 마감 우세",
  breakout_failure: "⑥ 돌파 실패(스쿼트)",
};
```

- [ ] **Step 2: 타입체크 (있으면)**

Run: `cd C:/Users/hanul/playground/my-stock-holdings-rules && npx tsc --noEmit -p tsconfig.json 2>&1 | head -20`
Expected: 이 파일 관련 신규 오류 없음. (기존 무관 오류가 있으면 그대로 두고 이 파일만 clean 확인.)

- [ ] **Step 3: 커밋**

```bash
git add src/app/stocks/sepa/SepaHoldingsSection.tsx
git commit -m "fix(sepa-page): 보유점검 규칙 라벨 정정(③ 거래량·⑥ 돌파 실패) — id rename 반영

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: screen_holdings_feedback.py — 빈 목록 정상 종료

**Files:**
- Modify: `scripts/screen_holdings_feedback.py` (`run()` 초입의 입력 부재·빈 목록 처리)

**Interfaces:** `run(out_path)` 시그니처 유지. 입력 없음/빈 목록 → 빈 결과 JSON + `exit 0`.

- [ ] **Step 1: run() 입력 처리 교체**

`run()` 함수에서 아래 블록:

```python
    if not IN_PATH.exists():
        print(f"❌ 매수 목록 없음: {IN_PATH.relative_to(ROOT)}")
        sys.exit(1)
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
```

을 다음으로 교체:

```python
    if not IN_PATH.exists():
        print(f"⏭️  매수 목록 없음({IN_PATH.relative_to(ROOT)}) — 빈 결과로 종료")
        _write_empty(out_path)
        return
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    if not data.get("holdings"):
        print("⏭️  보유 종목 0개 — 빈 결과로 종료")
        _write_empty(out_path, data.get("stop_loss_pct_default", -4))
        return
```

그리고 `run` 함수 위에 헬퍼를 추가:

```python
def _write_empty(out_path: Path, default_stop: int = -4) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": None, "stop_loss_pct_default": default_stop, "holdings": [],
    }
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"💾 저장(빈 결과): {out_path.relative_to(ROOT)}")
```

- [ ] **Step 2: 빈 목록 동작 검증 (임시 입력으로)**

스크래치에 빈 목록을 만들고 `--out`으로 실행해 exit 0 + 빈 JSON을 확인:

```bash
cd C:/Users/hanul/playground/my-stock-holdings-rules
python - <<'PY'
import json, subprocess, sys, tempfile, os
# 빈 holdings 입력을 임시로 두고 스크립트 로직만 확인하려면, IN_PATH를 직접 비우기 어렵다.
# 대신 헬퍼를 직접 호출해 빈 결과 형식을 확인한다.
sys.path.insert(0, "scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("shf", "scripts/screen_holdings_feedback.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
out = tempfile.mktemp(suffix=".json")
m._write_empty(__import__("pathlib").Path(out))
print(json.loads(open(out, encoding="utf-8").read()))
PY
```

Expected: `{'generated_at': ..., 'asof': None, 'stop_loss_pct_default': -4, 'holdings': []}`

- [ ] **Step 3: 커밋**

```bash
git add scripts/screen_holdings_feedback.py
git commit -m "feat(holdings): 매수 목록 없음/빈 배열이면 빈 결과로 정상 종료(파이프라인 안 멈춤)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `check-holdings` 스킬 문서

**Files:**
- Create: `.claude/skills/check-holdings/SKILL.md`

**Interfaces:** find-vcp SKILL.md 관례를 따르는 얇은 실행 문서.

- [ ] **Step 1: 스킬 문서 작성**

`.claude/skills/check-holdings/SKILL.md` (아래 내용 그대로. 외곽은 4-백틱 펜스라 안쪽 3-백틱은 그대로 파일에 들어간다):

````markdown
---
name: check-holdings
description: >
  SEPA 보유 종목 매도규칙 점검. 매수 목록(sepa-holdings.json)의 각 종목을
  미너비니 돌파 후 위반 규칙 6가지(저거래량 돌파·대량 후퇴·연속 저저점·이평선
  이탈·하락일 우세·돌파 실패)로 검사해 🔴손절/🟠조기매도/🟢정상보유 신호를
  sepa-holdings-feedback.json 에 저장한다. OHLCV 캐시 + 후보 파일(피벗)만 읽고
  수급·공유 파일·페이지 코드는 건드리지 않는다. 사용자가 "/check-holdings",
  "보유 점검", "매도규칙 점검", "규칙 위반 잡아줘" 등을 요청할 때 사용.
---

# check-holdings — 보유 종목 매도규칙 점검

매수한 종목이 "계속 들고 있어도 되는지"를 미너비니 매도 규칙으로 점검한다.
정의·근거: `docs/superpowers/specs/2026-07-05-holdings-rules-v2-design.md`
(+ 최초 설계 `2026-07-03-sepa-holdings-feedback-design.md`).

## 사전 조건
- 입력 `public/data/sepa-holdings.json` (사용자가 매수·매도 때 직접 관리).
  없거나 비면 빈 결과로 정상 종료.
- 피벗 참고: `sepa-vcp-candidates.json` / `sepa-power-play-candidates.json`
  (있으면 사용, 없어도 매수 시점 스냅샷 `pivot_price`로 판정).
- 시세: `update-data`가 갱신하는 OHLCV 캐시(추가 수집 없음).

## 실행 (1줄)
```
python scripts/screen_holdings_feedback.py
```
- 산출: `public/data/sepa-holdings-feedback.json`
- 콘솔: 종목별 신호(🔴/🟠/🟢/⚫) + 위반 규칙 목록.

### 옵션
- `--out PATH` : 출력 경로 변경.

## 결과 확인 (6개 규칙)
- ① 저거래량 돌파 · ② 대량 거래 후퇴 · ③ 연속 저저점(저가+거래량) ·
  ④ 이평선 아래 마감 · ⑤ 하락일·나쁜 마감 우세 · ⑥ 돌파 실패(스쿼트+비대칭).
- 신호: 🔴 손절(현재가 ≤ 손절선) > 🟠 조기 매도(위반 ≥ 1건) > 🟢 정상 보유.
- 🟡 소프트 경고(거래량 낮은 저점경신·스쿼트 관찰중)는 위반이 아니라 detail 표기.

## 안 하는 것
- 매수 목록 편집 · 공유/수급 파일 갱신 · 페이지 코드 수정 · 자동 commit.
````

- [ ] **Step 2: 스킬 문서 존재·형식 확인**

Run: `head -12 .claude/skills/check-holdings/SKILL.md`
Expected: YAML 프론트매터(`name: check-holdings`)가 보임.

- [ ] **Step 3: 커밋**

```bash
git add .claude/skills/check-holdings/SKILL.md
git commit -m "feat(skill): check-holdings — 보유 매도규칙 점검 정식 스킬화

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: `/sepa` 오케스트레이터 편입

**Files:**
- Modify: `.claude/skills/sepa/SKILL.md` (절차에 check-holdings 단계 + 요약 줄 + 커밋 파일 추가)

**Interfaces:** 문서 지시만. 형제 패턴 스킬 다음 순서에서 check-holdings 호출.

- [ ] **Step 1: 절차 3~5단계 편집**

`sepa/SKILL.md`의 "## 절차 (순서 고정)"에서:

(1) 3단계(형제 패턴) 뒤, 4단계(요약) 앞에 새 단계 삽입:

```markdown
4. **`check-holdings` 스킬 호출** — 보유 종목 매도규칙 점검. 형제 패턴 결과
   파일(피벗)을 읽으므로 반드시 형제 실행 뒤에 돈다.
   - `sepa-holdings.json`이 없거나 비면 실패가 아니라 **건너뜀**(빈 결과로
     정상 종료 — find-3c 부재 처리와 동일 정신).
```

(2) 기존 4단계(통합 요약)를 5단계로 밀고, 요약 표에 한 줄 추가:

```markdown
   - 보유 점검: 🔴 손절 N · 🟠 조기매도 N · 🟢 정상보유 N (check-holdings 콘솔 그대로)
```

(3) 기존 5단계(커밋) 결과 파일 목록에 추가:

```markdown
   - `public/data/sepa-holdings-feedback.json`
```

(단계 번호는 4→5, 5→6으로 순차 재배치.)

- [ ] **Step 2: "안 하는 것" 문구 확인**

`sepa/SKILL.md`의 "안 하는 것"에 `find-*-history` 등이 있으나 check-holdings는
이제 정기 단계이므로 그 목록에 넣지 않는다. (변경 없음 확인만.)

- [ ] **Step 3: 커밋**

```bash
git add .claude/skills/sepa/SKILL.md
git commit -m "feat(skill): /sepa에 check-holdings 편입(형제 다음)+결과 파일 커밋 추가

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: 통합 검증 (전체 테스트 + 실데이터 4종목 실행)

**Files:** 없음(검증). 필요 시 산출물 `public/data/sepa-holdings-feedback.json` 갱신 커밋.

- [ ] **Step 1: 전체 파이썬 테스트**

Run: `cd C:/Users/hanul/playground/my-stock-holdings-rules && python -m pytest tests/test_sell_rules.py tests/test_sell_rules_oracle.py -v`
Expected: 전부 PASS.

- [ ] **Step 2: 실제 보유 4종목으로 스크립트 실행 (로컬 OHLCV 캐시 필요)**

Run: `python scripts/screen_holdings_feedback.py`
Expected: 4종목(나이스정보통신·오리온·S-Oil우·한국공항) 신호가 콘솔에 뜨고
`public/data/sepa-holdings-feedback.json`이 6개 규칙(id에 consecutive_lower_lows·
breakout_failure 포함)으로 갱신됨. (캐시가 없으면 `no_data`가 뜰 수 있음 — 그 경우
`update-data` 선행이 필요하다고 보고만 하고 넘어간다.)

- [ ] **Step 3: 산출 JSON 규칙 id 확인**

Run: `python -c "import json;d=json.load(open('public/data/sepa-holdings-feedback.json',encoding='utf-8'));print([r['id'] for r in (d['holdings'][0]['rules'] if d['holdings'] else [])])"`
Expected: `['low_volume_breakout','heavy_volume_pullback','consecutive_lower_lows','close_below_ma','weak_days_dominant','breakout_failure']`

- [ ] **Step 4: 산출물 커밋 (실행됐다면)**

```bash
git add public/data/sepa-holdings-feedback.json
git commit -m "chore(holdings): v2 규칙으로 보유 점검 결과 갱신

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 5: 완료 보고**

전체 커밋 로그(`git log --oneline feat/holdings-rules-v2`)와 테스트 결과를 요약해
보고한다. 통합(머지/PR/cherry-pick) 방법은 사용자와 별도 결정.

---

## 자체 검토 (작성자 체크리스트 결과)

- **스펙 커버리지**: 결정 A(규칙⑥ 거래량 비대칭=돌파일 비교)→Task2, B(라운드트립 보류)→해당 없음(의도적 제외), C(규칙③ 저가+3연속+거래량≥평균)→Task1, ⑥+⑦ 통합→Task2, 규칙④ 보강→Task3, 오라클→Task4, 페이지 라벨→Task5, 빈 목록→Task6, 스킬→Task7, /sepa 편입→Task8, 검증→Task9. 누락 없음.
- **플레이스홀더**: 없음(모든 코드/명령 실제 내용 기재).
- **타입/이름 일치**: `rule_consecutive_lower_lows`·`rule_breakout_failure`·id `consecutive_lower_lows`·`breakout_failure`가 sell_rules.py(Task1·2)·test(Task1·2·4)·page(Task5)·evaluate_holding rules[2]/[5]에서 일관. `SQUAT_GRACE_DAYS=10`·`LOWER_LOW_RUN=3` 상수 일관.
