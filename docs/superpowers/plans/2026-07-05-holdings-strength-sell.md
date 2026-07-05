# 보유 종목 강세 매도(과열·절정) 신호 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보유 종목 점검 카드에 미너비니 "강세에 팔아라" 과열·절정 신호 4종을 추가하고, 카드를 접기/펼치기로 단순화한다.

**Architecture:** `sell_rules.py`에 순수 함수 `evaluate_climax`(게이트 + 신호 4종)를 추가해 `evaluate_holding`이 `strength` 필드를 반환하게 한다. 페이지는 결과 JSON을 읽어 네이티브 `<details>`로 접힘(요약 점수판)/펼침(전체 나열)을 렌더한다. 백엔드는 TDD(pytest), 화면 요약 로직은 순수 헬퍼로 분리해 vitest로 검증한다.

**Tech Stack:** Python 3(pytest) · Next.js App Router(서버 컴포넌트) · TypeScript · Tailwind v4 · vitest

## Global Constraints

- 작업 위치: 워크트리 `C:\Users\hanul\playground\my-stock-strength-sell`, 브랜치 `feat/sepa-strength-sell`(origin/master 기준). 모든 경로는 이 워크트리 기준.
- 화면은 **서버 렌더 전용, 클라이언트 JS 없음** — 접기/펼치기는 네이티브 `<details>/<summary>` + Tailwind `group-open:`(코드베이스 기존 관례, 예: `src/app/bio/BioView.tsx`).
- 확장 게이트는 **새로 만들지 않고** 기존 `extension_pct`와 동일한 `(현재/피벗-1)*100 ≥ 5` 를 쓴다.
- 강세 전용 색 = 로즈 `#f5a9ce`(bg `rgba(245,169,206,0.14)`, border `rgba(245,169,206,0.34)`). 매집(초록)·약세(빨강)와 구분.
- 판정은 2단계: 확장 상태에서 신호 1개↑ 발화 → `sell_into_strength`, 0 → `none`. 미확장 → `not_extended`, 피벗 없음 → `na`.
- 신호 4종만(네트-뉴): `climax_run` · `blowoff_day` · `exhaustion_gap` · `distribution`. 상승일 세기·가격 상승률은 매집·MVP가 담당(중복 금지).
- 카피는 평이한 한국어. 기존 파일 스타일(주석·명명)을 따른다.
- TDD, 커밋 자주. 파이썬 테스트: `python -m pytest`, 프론트 테스트: `npx vitest run`.
- 스펙: `docs/superpowers/specs/2026-07-05-holdings-strength-sell-design.md`.

---

### Task 1: 상수 + `sig_climax_run`(절정 분출)

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (상수 블록: 기존 `MVP_P_MIN` 아래 / 함수: `evaluate_accumulation` 위)
- Test: `tests/test_sell_rules.py`

**Interfaces:**
- Consumes: 기존 `make_series` 테스트 헬퍼, 일봉 dict(`closes` 등).
- Produces: `sig_climax_run(series) -> {"id","status","detail"}`; status ∈ `fired|clear|pending`. 상수 `EXT_GATE_PCT, CLIMAX_MIN_W, CLIMAX_25_MAX_W, CLIMAX_70_MAX_W, CLIMAX_25_GAIN, CLIMAX_70_GAIN`.

- [ ] **Step 1: Write the failing tests**

`tests/test_sell_rules.py` 하단에 추가:

```python
from canslim_lib.sell_rules import sig_climax_run


def test_climax_run_fires_25pct():
    s = make_series([100.0] * 20 + [130.0])          # 최근 창 +30%
    r = sig_climax_run(s)
    assert r["status"] == "fired" and "25%+" in r["detail"]


def test_climax_run_fires_strong_70pct():
    s = make_series([100.0] * 20 + [175.0])          # 최근 창 +75% → 폭발적
    r = sig_climax_run(s)
    assert r["status"] == "fired" and "70%+" in r["detail"]


def test_climax_run_clear_when_mild():
    s = make_series([100.0] * 20 + [108.0])          # +8%
    assert sig_climax_run(s)["status"] == "clear"


def test_climax_run_pending_when_short():
    s = make_series([100.0, 101.0, 102.0])           # 창 하한 미만
    assert sig_climax_run(s)["status"] == "pending"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sell_rules.py -k climax_run -v`
Expected: FAIL — `ImportError: cannot import name 'sig_climax_run'`

- [ ] **Step 3: Add constants**

`sell_rules.py`의 `MVP_P_MIN = 0.20` 줄 바로 아래에 추가:

```python
# --- 강세 매도(과열·절정) 감시 ---
EXT_GATE_PCT    = 5.0     # 확장 게이트: (현재/피벗-1)*100 ≥ 5
CLIMAX_MIN_W    = 5       # 절정 분출 관찰 창 하한(거래일)
CLIMAX_25_MAX_W = 15      # +25% 판정 창 상한
CLIMAX_70_MAX_W = 10      # +70% 판정 창 상한
CLIMAX_25_GAIN  = 0.25    # 5~15일 상승률 문턱
CLIMAX_70_GAIN  = 0.70    # 5~10일 상승률 문턱
BLOWOFF_RECENT  = 3       # 최대 상승일/변동폭이 "최근"으로 인정되는 거래일
BLOWOFF_MIN_DAYS = 5      # blowoff 판정 최소 돌파후 거래일
GAP_RECENT      = 3       # 소진성 갭이 "최근"으로 인정되는 거래일
DISTRIB_WINDOW  = 10      # 분산(반전·처닝) trailing 관찰 거래일
CHURN_MOVE_PCT  = 0.01    # 처닝: 종가 변화 절대값 < 1%
```

- [ ] **Step 4: Implement `sig_climax_run`**

`evaluate_accumulation` 정의 바로 위에 추가:

```python
def sig_climax_run(series):
    """S1 절정 분출: 최근 종가 trailing 상승률(5~15일 +25% / 5~10일 +70%)."""
    rid = "climax_run"
    closes = series["closes"]
    n = len(closes)
    best = None  # (w, r) — 25% 이상 중 최대
    for w in range(CLIMAX_MIN_W, CLIMAX_25_MAX_W + 1):
        if n - 1 - w < 0:
            continue
        base = closes[n - 1 - w]
        if not base:
            continue
        r = closes[-1] / base - 1
        if w <= CLIMAX_70_MAX_W and r >= CLIMAX_70_GAIN:
            return {"id": rid, "status": "fired",
                    "detail": f"최근 {w}거래일 +{r * 100:.0f}% — 폭발적 분출(70%+)"}
        if r >= CLIMAX_25_GAIN and (best is None or r > best[1]):
            best = (w, r)
    if best is not None:
        w, r = best
        return {"id": rid, "status": "fired",
                "detail": f"최근 {w}거래일 +{r * 100:.0f}% — 절정 구간(25%+)"}
    if n - 1 - CLIMAX_MIN_W < 0:
        return {"id": rid, "status": "pending", "detail": "데이터 부족"}
    return {"id": rid, "status": "clear", "detail": "절정 분출 없음"}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_sell_rules.py -k climax_run -v`
Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): sig_climax_run 절정 분출 + 강세 감시 상수"
```

---

### Task 2: `sig_blowoff_day`(최대 상승일·변동폭)

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (`sig_climax_run` 아래)
- Test: `tests/test_sell_rules.py`

**Interfaces:**
- Consumes: 일봉 dict, 돌파 인덱스 `bi`.
- Produces: `sig_blowoff_day(series, bi) -> {"id","status","detail"}`.

- [ ] **Step 1: Write the failing tests**

```python
from canslim_lib.sell_rules import sig_blowoff_day


def test_blowoff_fires_when_biggest_up_day_recent():
    s = make_series([100, 101, 102, 103, 104, 105, 120])  # 마지막 날 최대 상승
    r = sig_blowoff_day(s, 0)
    assert r["status"] == "fired" and "최대 상승일" in r["detail"]


def test_blowoff_clear_when_biggest_up_day_old():
    s = make_series([100, 120, 121, 122, 123, 124, 125])  # 최대 상승이 초반
    assert sig_blowoff_day(s, 0)["status"] == "clear"


def test_blowoff_pending_when_few_days():
    s = make_series([100, 101, 102])                       # 돌파후 <5일
    assert sig_blowoff_day(s, 0)["status"] == "pending"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sell_rules.py -k blowoff -v`
Expected: FAIL — `cannot import name 'sig_blowoff_day'`

- [ ] **Step 3: Implement**

```python
def sig_blowoff_day(series, bi):
    """S2 최대 상승일/변동폭이 최근 BLOWOFF_RECENT일 안에 출현(막판 폭발)."""
    rid = "blowoff_day"
    closes, highs, lows = series["closes"], series["highs"], series["lows"]
    n = len(closes)
    start = bi + 1
    if n - start < BLOWOFF_MIN_DAYS:
        return {"id": rid, "status": "pending",
                "detail": f"돌파 후 {max(n - start, 0)}거래일 — 판정 전"}
    best_g = (None, -1.0)   # (idx, gain)
    best_r = (None, -1.0)   # (idx, range)
    for i in range(start, n):
        if closes[i - 1]:
            g = closes[i] / closes[i - 1] - 1
            if g > best_g[1]:
                best_g = (i, g)
        if closes[i]:
            rng = (highs[i] - lows[i]) / closes[i]
            if rng > best_r[1]:
                best_r = (i, rng)
    recent_lo = n - BLOWOFF_RECENT

    def when(i):
        k = (n - 1) - i
        return "오늘" if k == 0 else ("어제" if k == 1 else f"{k}일 전")

    gi, gv = best_g
    if gi is not None and gi >= recent_lo:
        return {"id": rid, "status": "fired",
                "detail": f"구간 최대 상승일 +{gv * 100:.0f}%이 {when(gi)} 출현"}
    ri, rv = best_r
    if ri is not None and ri >= recent_lo:
        return {"id": rid, "status": "fired",
                "detail": f"구간 최대 변동폭 {rv * 100:.0f}%가 {when(ri)} 출현"}
    return {"id": rid, "status": "clear", "detail": "막판 최대 상승/변동 아님"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sell_rules.py -k blowoff -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): sig_blowoff_day 최대 상승일·변동폭"
```

---

### Task 3: `sig_exhaustion_gap`(소진성 갭)

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (`sig_blowoff_day` 아래)
- Test: `tests/test_sell_rules.py`

**Interfaces:**
- Produces: `sig_exhaustion_gap(series) -> {"id","status","detail"}`.

- [ ] **Step 1: Write the failing tests**

```python
from canslim_lib.sell_rules import sig_exhaustion_gap


def test_exhaustion_gap_fires_on_recent_up_gap():
    s = make_series([100.0, 101.0, 102.0, 110.0],
                    highs=[101.0, 102.0, 103.0, 113.0],
                    lows=[99.0, 100.0, 101.0, 111.0])   # 마지막날 저가>전일 고가
    r = sig_exhaustion_gap(s)
    assert r["status"] == "fired" and "갭" in r["detail"]


def test_exhaustion_gap_clear_without_gap():
    s = make_series([100.0, 101.0, 102.0, 103.0])       # 기본 고저 = 겹침(갭 없음)
    assert sig_exhaustion_gap(s)["status"] == "clear"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sell_rules.py -k exhaustion_gap -v`
Expected: FAIL — `cannot import name 'sig_exhaustion_gap'`

- [ ] **Step 3: Implement**

```python
def sig_exhaustion_gap(series):
    """S3 소진성 갭: 최근 GAP_RECENT일 내 상승 갭(당일 저가 > 전일 고가)."""
    rid = "exhaustion_gap"
    highs, lows = series["highs"], series["lows"]
    n = len(highs)
    if n < 2:
        return {"id": rid, "status": "pending", "detail": "데이터 부족"}
    lo = max(1, n - GAP_RECENT)
    for i in range(n - 1, lo - 1, -1):
        if lows[i] is not None and highs[i - 1] is not None and lows[i] > highs[i - 1]:
            k = (n - 1) - i
            w = "오늘" if k == 0 else ("어제" if k == 1 else f"{k}일 전")
            return {"id": rid, "status": "fired",
                    "detail": f"{w} 상승 갭(전일 고가 위 출발)"}
    return {"id": rid, "status": "clear", "detail": "최근 상승 갭 없음"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sell_rules.py -k exhaustion_gap -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): sig_exhaustion_gap 소진성 갭"
```

---

### Task 4: `sig_distribution`(분산 정황)

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (`sig_exhaustion_gap` 아래)
- Test: `tests/test_sell_rules.py`

**Interfaces:**
- Consumes: 기존 `avg_volume`, `HEAVY_VOL_MULT`.
- Produces: `sig_distribution(series, bi) -> {"id","status","detail"}`.

- [ ] **Step 1: Write the failing tests**

```python
from canslim_lib.sell_rules import sig_distribution


def test_distribution_fires_biggest_volume_down_day():
    s = make_series([100.0, 101.0, 100.0], volumes=[1000.0, 1000.0, 5000.0])
    r = sig_distribution(s, 0)                 # 최대 거래량(마지막)이 하락 마감
    assert r["status"] == "fired" and "최대 거래량" in r["detail"]


def test_distribution_fires_churning():
    closes = [100.0] * 55
    vols = [1000.0] * 54 + [2000.0]            # 마지막날 대량인데 종가 변화 0%
    s = make_series(closes, volumes=vols)
    r = sig_distribution(s, 50)
    assert r["status"] == "fired" and "처닝" in r["detail"]


def test_distribution_fires_reversal_day():
    closes = [100.0] * 51 + [102.0, 104.0, 106.0, 104.0]
    highs = [101.0] * 51 + [103.0, 105.0, 107.0, 110.0]  # 마지막날 장중 신고가
    lows = [99.0] * 51 + [101.0, 103.0, 105.0, 103.0]
    vols = [1000.0] * 52 + [9000.0, 1000.0, 3000.0]      # 최대량은 up day(52), 마지막날 대량 반전
    s = make_series(closes, volumes=vols, highs=highs, lows=lows)
    r = sig_distribution(s, 50)
    assert r["status"] == "fired" and "반전" in r["detail"]


def test_distribution_clear():
    closes = [100.0 + i for i in range(55)]    # 완만한 상승, 대량·반전 없음
    s = make_series(closes)
    assert sig_distribution(s, 50)["status"] == "clear"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sell_rules.py -k distribution -v`
Expected: FAIL — `cannot import name 'sig_distribution'`

- [ ] **Step 3: Implement**

```python
def sig_distribution(series, bi):
    """S4 분산 정황: (c)돌파 후 최대 거래량 하락일 / (a)대량 반전 / (b)처닝."""
    rid = "distribution"
    closes, highs = series["closes"], series["highs"]
    vols, dates = series["volumes"], series["dates"]
    n = len(closes)
    if bi + 1 >= n:
        return {"id": rid, "status": "pending", "detail": "돌파 다음 날 데이터 없음"}
    # (c) 돌파 후 구간의 최대 거래량 날이 하락 마감?
    span = [i for i in range(bi, n) if vols[i] is not None]
    if span:
        vmax_i = max(span, key=lambda i: vols[i])
        if vmax_i >= 1 and closes[vmax_i] < closes[vmax_i - 1]:
            return {"id": rid, "status": "fired",
                    "detail": f"{dates[vmax_i]} 최대 거래량으로 하락"}
    # (a)(b) 최근 DISTRIB_WINDOW일 반전 / 처닝
    lo = max(bi + 1, n - DISTRIB_WINDOW)
    for i in range(lo, n):
        avg = avg_volume(vols, i)
        if avg is None or vols[i] is None or vols[i] < HEAVY_VOL_MULT * avg:
            continue
        if highs[i] > highs[i - 1] and closes[i] < closes[i - 1]:
            return {"id": rid, "status": "fired",
                    "detail": f"{dates[i]} 대량 거래 반전(장중 고점→하락 마감)"}
        if closes[i - 1] and abs(closes[i] / closes[i - 1] - 1) < CHURN_MOVE_PCT:
            return {"id": rid, "status": "fired",
                    "detail": f"{dates[i]} 처닝(대량인데 가격 진전 없음)"}
    return {"id": rid, "status": "clear", "detail": "반전·처닝·최대량 하락 없음"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sell_rules.py -k distribution -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): sig_distribution 분산 정황(반전·처닝·최대량 하락)"
```

---

### Task 5: `evaluate_climax` 게이트·집계 + `evaluate_holding` 배선

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (`sig_distribution` 아래에 `evaluate_climax`; `evaluate_holding` 반환부; 파일 상단 docstring)
- Test: `tests/test_sell_rules.py`

**Interfaces:**
- Consumes: `sig_climax_run`, `sig_blowoff_day`, `sig_exhaustion_gap`, `sig_distribution`.
- Produces: `evaluate_climax(series, bi, pivot_price) -> {"signal","extended","gate_detail","count","signals"}`; `evaluate_holding(...)` 반환 dict에 `"strength"` 키 추가.

- [ ] **Step 1: Write the failing tests**

```python
from canslim_lib.sell_rules import evaluate_climax, evaluate_holding


def _extended_series():
    # 피벗 100, 현재 150 → 확장 +50%, 최근 창 +50% 절정
    return make_series([100.0] * 30 + [150.0])


def test_evaluate_climax_na_without_pivot():
    r = evaluate_climax(_extended_series(), 0, None)
    assert r["signal"] == "na" and r["signals"] == []


def test_evaluate_climax_not_extended_below_gate():
    s = make_series([100.0] * 30 + [103.0])      # 피벗 100 → +3% < 5%
    r = evaluate_climax(s, 0, 100.0)
    assert r["signal"] == "not_extended" and r["extended"] is False and r["signals"] == []


def test_evaluate_climax_sell_when_extended_and_fires():
    r = evaluate_climax(_extended_series(), 0, 100.0)
    assert r["signal"] == "sell_into_strength" and r["extended"] is True
    assert r["count"] >= 1 and len(r["signals"]) == 4


def test_evaluate_climax_none_when_extended_no_signal():
    # 확장은 됐지만 절정·막판·갭·분산 없음: 한 번에 올라 이후 완전 횡보
    s = make_series([100.0] + [150.0] * 40)      # 피벗 100, 현재 150(+50%), 최근 창 0%
    r = evaluate_climax(s, 0, 100.0)
    assert r["extended"] is True and r["signal"] == "none" and r["count"] == 0


def test_evaluate_holding_includes_strength():
    s = _extended_series()
    r = evaluate_holding(s, s["dates"][0], 100.0, -4, pivot_price=100.0)
    assert "strength" in r and r["strength"]["signal"] in {
        "sell_into_strength", "none", "not_extended", "na"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sell_rules.py -k "evaluate_climax or includes_strength" -v`
Expected: FAIL — `cannot import name 'evaluate_climax'`

- [ ] **Step 3: Implement `evaluate_climax`**

`sig_distribution` 아래에 추가:

```python
def evaluate_climax(series, bi, pivot_price):
    """강세 매도(과열·절정) 감시. 확장(extension ≥ EXT_GATE_PCT)일 때만 4종 평가.
    반환: signal(sell_into_strength|none|not_extended|na)·extended·gate_detail·count·signals."""
    current = series["closes"][-1]
    if pivot_price is None:
        return {"signal": "na", "extended": False,
                "gate_detail": "피벗 없음 — 판정 불가", "count": 0, "signals": []}
    ext = (current / pivot_price - 1) * 100
    if ext < EXT_GATE_PCT:
        return {"signal": "not_extended", "extended": False,
                "gate_detail": f"확장 {ext:+.1f}% < {EXT_GATE_PCT:.0f}%",
                "count": 0, "signals": []}
    signals = [
        sig_climax_run(series),
        sig_blowoff_day(series, bi),
        sig_exhaustion_gap(series),
        sig_distribution(series, bi),
    ]
    count = sum(1 for s in signals if s["status"] == "fired")
    return {"signal": "sell_into_strength" if count >= 1 else "none",
            "extended": True,
            "gate_detail": f"확장 {ext:+.1f}% ≥ {EXT_GATE_PCT:.0f}%",
            "count": count, "signals": signals}
```

- [ ] **Step 4: Wire into `evaluate_holding`**

`evaluate_holding` 안에서 `mvp = evaluate_mvp(series, bi)` 다음 줄에 추가:

```python
    strength = evaluate_climax(series, bi, pivot_price)
```

그리고 반환 dict의 마지막 `"mvp": mvp,` 뒤에 한 줄 추가:

```python
        "mvp": mvp,
        "strength": strength,
    }
```

- [ ] **Step 5: Update docstring reference**

`sell_rules.py` 상단 docstring의 `정의:` 줄 아래에 한 줄 추가:

```python
강세 매도 트랙 정의: docs/superpowers/specs/2026-07-05-holdings-strength-sell-design.md
```

- [ ] **Step 6: Run the full sell_rules test file**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: 모든 테스트 PASS (기존 + 신규)

- [ ] **Step 7: Commit**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): evaluate_climax 게이트·집계 + evaluate_holding에 strength 배선"
```

---

### Task 6: 결과 JSON 재생성

**Files:**
- Modify(생성물): `public/data/sepa-holdings-feedback.json`

**Interfaces:**
- Consumes: `scripts/screen_holdings_feedback.py`(변경 없음 — `evaluate_holding`이 `strength`를 인라인 반환).

- [ ] **Step 1: Run the screener**

Run: `python scripts/screen_holdings_feedback.py`
Expected: `💾 저장: public/data/sepa-holdings-feedback.json (기준일 ...)` 출력, 오류 없음.

- [ ] **Step 2: Verify strength field present**

Run:
```bash
python -c "import json; d=json.load(open('public/data/sepa-holdings-feedback.json',encoding='utf-8')); [print(h['name'], h['strength']['signal']) for h in d['holdings']]"
```
Expected: 4종목 모두 출력, 현재 보유는 확장 <5%라 전부 `not_extended`(피벗 없는 종목은 `na`).

- [ ] **Step 3: Commit**

```bash
git add public/data/sepa-holdings-feedback.json
git commit -m "data(holdings): strength 필드 포함 결과 재생성"
```

---

### Task 7: 화면 요약 헬퍼 `holdingsSummary.ts` + vitest

**Files:**
- Create: `src/app/stocks/sepa/holdingsSummary.ts`
- Test: `src/app/stocks/sepa/holdingsSummary.test.ts`

**Interfaces:**
- Consumes: `SepaHoldingsSection`이 export할 타입 `Accumulation, Mvp, HoldingRule, Strength`(Task 8에서 export 추가; 여기선 `import type`).
- Produces: `accumTally(acc?, mvp?) -> {met,total,complete}`; `ruleTally(rules) -> {pass,violation,watch,pending}`; `strengthTally(s?) -> {fired,total} | null`.

- [ ] **Step 1: Write the failing tests**

`src/app/stocks/sepa/holdingsSummary.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { accumTally, ruleTally, strengthTally } from "./holdingsSummary";

describe("accumTally", () => {
  it("counts met accumulation + ok mvp out of 6", () => {
    const acc = { window: "15일 완료", elapsed: 15, signals: [
      { id: "a", status: "met", detail: "" },
      { id: "b", status: "met", detail: "" },
      { id: "c", status: "unmet", detail: "" }] };
    const mvp = { status: "yes", m: { ok: true, detail: "" },
      v: { ok: true, detail: "" }, p: { ok: true, detail: "" } };
    expect(accumTally(acc as never, mvp as never)).toEqual({ met: 5, total: 6, complete: true });
  });
  it("marks incomplete when elapsed < 15", () => {
    expect(accumTally({ window: "", elapsed: 2, signals: [] } as never, undefined).complete).toBe(false);
  });
});

describe("ruleTally", () => {
  it("tallies by status", () => {
    const rules = [
      { id: "1", status: "pass", detail: "" }, { id: "2", status: "violation", detail: "" },
      { id: "3", status: "watch", detail: "" }, { id: "4", status: "pending", detail: "" },
      { id: "5", status: "na", detail: "" }];
    expect(ruleTally(rules as never)).toEqual({ pass: 1, violation: 1, watch: 1, pending: 2 });
  });
});

describe("strengthTally", () => {
  it("returns null when not extended", () => {
    expect(strengthTally({ signal: "not_extended", extended: false,
      gate_detail: "", count: 0, signals: [] })).toBeNull();
  });
  it("returns fired/total when extended", () => {
    expect(strengthTally({ signal: "sell_into_strength", extended: true, gate_detail: "",
      count: 2, signals: [{}, {}, {}, {}] as never })).toEqual({ fired: 2, total: 4 });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/app/stocks/sepa/holdingsSummary.test.ts`
Expected: FAIL — cannot find module `./holdingsSummary`

- [ ] **Step 3: Implement helpers**

`src/app/stocks/sepa/holdingsSummary.ts`:

```ts
// 보유 점검 카드 요약(점수판) 순수 계산 — SepaHoldingsSection에서 사용
import type { Accumulation, Mvp, HoldingRule, Strength } from "./SepaHoldingsSection";

export function accumTally(acc?: Accumulation, mvp?: Mvp): { met: number; total: number; complete: boolean } {
  let met = 0;
  for (const s of acc?.signals ?? []) if (s.status === "met") met++;
  if (mvp) for (const k of ["m", "v", "p"] as const) if (mvp[k]?.ok === true) met++;
  return { met, total: 6, complete: (acc?.elapsed ?? 0) >= 15 };
}

export function ruleTally(rules: HoldingRule[]): { pass: number; violation: number; watch: number; pending: number } {
  const t = { pass: 0, violation: 0, watch: 0, pending: 0 };
  for (const r of rules) {
    if (r.status === "pass") t.pass++;
    else if (r.status === "violation") t.violation++;
    else if (r.status === "watch") t.watch++;
    else t.pending++; // pending, na
  }
  return t;
}

export function strengthTally(s?: Strength): { fired: number; total: number } | null {
  if (!s || !s.extended) return null;
  return { fired: s.count, total: s.signals.length || 4 };
}
```

> 참고: `import type`만 쓰므로 `SepaHoldingsSection`과 런타임 순환 참조가 생기지 않는다. Task 8에서 그 파일이 이 타입들을 export하기 전까지 타입 에러가 날 수 있으니, Task 8과 함께 타입체크한다.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/app/stocks/sepa/holdingsSummary.test.ts`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/app/stocks/sepa/holdingsSummary.ts src/app/stocks/sepa/holdingsSummary.test.ts
git commit -m "feat(sepa): 보유 카드 요약 점수판 헬퍼(accumTally·ruleTally·strengthTally)+vitest"
```

---

### Task 8: `SepaHoldingsSection.tsx` — 접기/펼치기 + 강세 패널

**Files:**
- Modify(전체 교체): `src/app/stocks/sepa/SepaHoldingsSection.tsx`

**Interfaces:**
- Consumes: `holdingsSummary`의 `accumTally, ruleTally, strengthTally`.
- Produces: 타입 export `StrengthSignal, Strength`(및 기존 `HoldingRule, Accumulation, Mvp` 유지); `HoldingFeedback.strength?`. UI 동작은 export 없음.

- [ ] **Step 1: Replace the file**

`src/app/stocks/sepa/SepaHoldingsSection.tsx` 전체를 아래로 교체:

```tsx
// 보유 종목 점검 — 매도 규칙 위반 + 강세 매도(과열) 감시 (서버 렌더 전용, JS 없음)
import type { ReactNode } from "react";
import { accumTally, ruleTally, strengthTally } from "./holdingsSummary";

export interface HoldingRule { id: string; status: "violation" | "pass" | "pending" | "na" | "watch"; detail: string; }
export interface AccumulationSignal { id: string; status: "met" | "unmet" | "pending"; detail: string; }
export interface Accumulation { window: string; elapsed: number; signals: AccumulationSignal[]; }
export interface MvpCheck { ok: boolean | null; detail: string; }
export interface Mvp { status: "yes" | "no" | "pending"; m: MvpCheck; v: MvpCheck; p: MvpCheck; }
export interface StrengthSignal { id: string; status: "fired" | "clear" | "pending"; detail: string; }
export interface Strength {
  signal: "sell_into_strength" | "none" | "not_extended" | "na";
  extended: boolean; gate_detail: string; count: number; signals: StrengthSignal[];
}
export interface HoldingFeedback {
  code: string; name: string; market?: string | null; buy_date: string; buy_price: number;
  quantity?: number; stop_loss_pct: number; pivot_price?: number | null; pivot_source?: string | null;
  current_price?: number; profit_pct?: number; stop_price?: number; pct_to_stop?: number;
  breakout_date?: string; breakout_date_estimated?: boolean;
  signal: "stop_loss" | "early_sell" | "hold" | "no_data"; violation_count: number; rules: HoldingRule[];
  extension_pct?: number | null; accumulation?: Accumulation; mvp?: Mvp; strength?: Strength;
}
export interface HoldingsFeedbackFile { generated_at?: string; asof?: string; holdings?: HoldingFeedback[]; }

const HEAT = "#f5a9ce";

const RULE_LABELS: Record<string, string> = {
  low_volume_breakout: "① 저거래량 돌파",
  heavy_volume_pullback: "② 대량 거래 후퇴",
  consecutive_lower_lows: "③ 연속 저저점(거래량)",
  close_below_ma: "④ 이평선 아래 마감",
  weak_days_dominant: "⑤ 하락일·나쁜 마감 우세",
  breakout_failure: "⑥ 돌파 실패(스쿼트)",
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
  watch: { mark: "🟡", cls: "text-[#fbbf24]" },
};

const ACC_MARK: Record<AccumulationSignal["status"], { mark: string; cls: string }> = {
  met: { mark: "✓", cls: "text-[#34d399]" },
  unmet: { mark: "○", cls: "text-on-surface-variant/50" },
  pending: { mark: "―", cls: "text-on-surface-variant/40" },
};
const ACC_META: Record<string, { label: string; tip: string }> = {
  up_days_dominant: { label: "상승일 우세", tip: "돌파 후 15거래일 중 상승 마감일이 하락 마감일보다 많으면 충족. 기관 매집 정황. 숫자 = 상승 · 하락 마감일." },
  quality_closes: { label: "양질의 종가", tip: "그날 고저 범위의 상단 절반에서 마감(좋은 마감)한 날이 하단 절반 마감(나쁜 마감)보다 많으면 충족. 변동폭 1% 미만 tight 눌림은 나쁜 마감서 제외." },
  up_streak_7: { label: "연속 상승 7일↑", tip: "상승 마감이 며칠 연속됐는지의 최고 기록. 7~8일 이상을 미너비니는 가장 이상적 신호로 봄." },
};
const MVP_META = {
  m: { label: "M 모멘텀", tip: "돌파 후 15일 중 상승 마감이 12일 이상이면 충족." },
  v: { label: "V 거래량", tip: "돌파 후 15일 평균 거래량이 돌파 직전 15일 평균 대비 25% 이상 늘면 충족." },
  p: { label: "P 가격", tip: "돌파 후 15일간 최고 종가가 돌파일 종가 대비 20% 이상 오르면 충족." },
} as const;

const STRENGTH_MARK: Record<StrengthSignal["status"], { mark: string; cls: string }> = {
  fired: { mark: "🔥", cls: "text-[#f5a9ce]" },
  clear: { mark: "○", cls: "text-on-surface-variant/50" },
  pending: { mark: "―", cls: "text-on-surface-variant/40" },
};
const STRENGTH_META: Record<string, { label: string; tip: string }> = {
  climax_run: { label: "절정 분출", tip: "확장 단계에서 최근 5~15일 +25%(또는 5~10일 +70%) 급등. 상승 가속 = 강세에 이익 확정 검토." },
  blowoff_day: { label: "최대 상승일·변동폭", tip: "돌파 후 최대 상승일(또는 최대 일중 변동폭)이 최근 3거래일 안에 나오면 발화. 상승 모멘텀의 마지막 폭발." },
  exhaustion_gap: { label: "소진성 갭", tip: "최근 3거래일 내 상승 갭(당일 저가가 전일 고가보다 높게 출발). 소진(exhaustion) 신호." },
  distribution: { label: "분산 정황", tip: "대량 거래 반전(장중 신고가→하락 마감) · 처닝(대량인데 가격 진전 없음) · 돌파 후 최대 거래량 하락일 중 하나." },
};

function fmtWon(v?: number | null): string {
  return v == null ? "-" : Math.round(v).toLocaleString();
}

export function SepaHoldingsSection({ data }: { data: HoldingsFeedbackFile | null }) {
  const holdings = data?.holdings ?? [];
  if (holdings.length === 0) return null;

  const Tip = ({ tip, children }: { tip: string; children: ReactNode }) => (
    <span className="relative group/tip cursor-help outline-none" tabIndex={0}>
      <span className="border-b border-dotted border-on-surface-variant/40">{children}</span>
      <span role="tooltip"
        className="pointer-events-none absolute left-0 bottom-full mb-2 w-56 max-w-[74vw] z-30
                   rounded-lg border border-outline-variant/30 bg-surface-container p-2.5 text-[11px]
                   font-normal leading-relaxed text-on-surface shadow-lg opacity-0 invisible
                   transition-opacity group-hover/tip:opacity-100 group-hover/tip:visible
                   group-focus/tip:opacity-100 group-focus/tip:visible">
        {tip}
      </span>
    </span>
  );
  const mvpMark = (ok: boolean | null) =>
    ok === true ? ACC_MARK.met : ok === false ? ACC_MARK.unmet : ACC_MARK.pending;

  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">monitor_heart</span>
        보유 종목 점검
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">
          매도 규칙 위반 · 강세 매도 감시 · 기준일 {data?.asof ?? "-"}
        </span>
      </h3>
      <div className="grid gap-3 sm:grid-cols-2">
        {holdings.map((h) => {
          const meta = SIGNAL_META[h.signal] ?? SIGNAL_META.no_data;
          const badgeLabel =
            h.signal === "early_sell" ? `${meta.label} · 위반 ${h.violation_count}건` : meta.label;
          const sellStrong = h.strength?.signal === "sell_into_strength";
          const acc = accumTally(h.accumulation, h.mvp);
          const rt = ruleTally(h.rules);
          const st = strengthTally(h.strength);

          // 접힘 점수판 텍스트/색
          const accDigest = h.accumulation
            ? acc.complete ? `${acc.met}/6` : `D+${Math.max(h.accumulation.elapsed, 0)}/15`
            : "–";
          const accCls = h.accumulation && acc.complete && acc.met > 0
            ? "text-[#34d399] font-semibold" : "text-on-surface-variant/50";
          const strDigest = st ? `발화 ${st.fired}/4`
            : h.strength?.signal === "na" ? "피벗 없음" : "확장 전";
          const strCls = st && st.fired > 0 ? "font-semibold" : "text-on-surface-variant/50";
          const weakDigest = rt.violation > 0 ? `위반 ${rt.violation}`
            : rt.watch > 0 ? `관찰 ${rt.watch}` : "위반 0";
          const weakCls = rt.violation > 0 ? "text-[#ffb4ab] font-semibold"
            : rt.watch > 0 ? "text-[#fbbf24] font-semibold" : "text-on-surface-variant/50";

          return (
            <details key={h.code} className="group bg-surface-container-low rounded-xl ghost-border open:border-outline-variant/25">
              <summary className="list-none [&::-webkit-details-marker]:hidden cursor-pointer p-4 flex flex-col gap-2.5">
                {/* 1줄: 이름 + 수익% */}
                <div className="flex items-baseline justify-between gap-2.5">
                  <div className="font-bold text-on-surface">
                    {h.name}
                    <span className="text-xs font-normal text-on-surface-variant/50 ml-1.5">{h.code}</span>
                  </div>
                  <span className="tabular-nums font-bold text-[15px] whitespace-nowrap"
                    style={{ color: (h.profit_pct ?? 0) >= 0 ? "#34d399" : "#ffb4ab" }}>
                    {h.profit_pct != null ? `${h.profit_pct > 0 ? "+" : ""}${h.profit_pct}%` : "-"}
                  </span>
                </div>
                {/* 2줄: 매수→현재 · 손절까지 + 칩 */}
                <div className="flex items-center justify-between gap-2.5 flex-wrap text-[11.5px] text-on-surface-variant tabular-nums">
                  <span>
                    {fmtWon(h.buy_price)}<span className="text-on-surface-variant/50 mx-1">→</span>{fmtWon(h.current_price)}
                    <span className="text-on-surface-variant/50 ml-2">손절까지 {h.pct_to_stop != null ? `${h.pct_to_stop}%` : "-"}</span>
                  </span>
                  <span className="flex gap-1.5">
                    {h.mvp?.status === "yes" && (
                      <span className="text-[10.5px] font-semibold px-1.5 py-0.5 rounded tracking-wide"
                        style={{ backgroundColor: "rgba(167,139,250,0.16)", color: "#a78bfa", border: "1px solid rgba(167,139,250,0.42)" }}>MVP</span>
                    )}
                    {h.extension_pct != null && (
                      <span className="text-[10.5px] font-medium px-1.5 py-0.5 rounded"
                        style={{ backgroundColor: "rgba(148,163,184,0.12)", color: "#94a3b8" }}>
                        확장 {h.extension_pct > 0 ? "+" : ""}{h.extension_pct}%
                      </span>
                    )}
                  </span>
                </div>
                {/* 3줄: 행동 배지 */}
                <div className="flex flex-wrap gap-1.5">
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                    style={{ backgroundColor: meta.bg, color: meta.fg }}>{badgeLabel}</span>
                  {sellStrong && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                      style={{ backgroundColor: "rgba(245,169,206,0.14)", color: HEAT, border: `1px solid rgba(245,169,206,0.34)` }}>
                      🔥 강세 매도 검토
                    </span>
                  )}
                </div>
                {/* 4줄: 3트랙 점수판 + 토글 */}
                <div className="flex items-center justify-between gap-2 border-t border-outline-variant/10 pt-2">
                  <div className="flex items-center gap-2.5 flex-wrap text-[11px]">
                    <span><span className="text-on-surface-variant/60">매집 </span><span className={`tabular-nums ${accCls}`}>{accDigest}</span></span>
                    <span className="w-px h-3 bg-outline-variant/30" />
                    <span><span className="text-on-surface-variant/60">강세 </span><span className={`tabular-nums ${strCls}`} style={st && st.fired > 0 ? { color: HEAT } : undefined}>{strDigest}</span></span>
                    <span className="w-px h-3 bg-outline-variant/30" />
                    <span><span className="text-on-surface-variant/60">약세 </span><span className={`tabular-nums ${weakCls}`}>{weakDigest}</span></span>
                  </div>
                  <span className="flex items-center gap-1 text-[11px] text-on-surface-variant/60 select-none whitespace-nowrap">
                    <span className="group-open:hidden">상세</span>
                    <span className="hidden group-open:inline">접기</span>
                    <span className="material-symbols-outlined text-base transition-transform group-open:rotate-180">expand_more</span>
                  </span>
                </div>
              </summary>

              {/* 펼침 본문 */}
              <div className="px-4 pb-4 flex flex-col gap-3">
                <p className="text-[11.5px] text-on-surface-variant/70 tabular-nums border-t border-outline-variant/10 pt-3">
                  손절선 {fmtWon(h.stop_price)}원({h.stop_loss_pct}%) · 돌파일 {h.breakout_date ?? "-"}
                  {h.breakout_date_estimated ? " (매수일 추정)" : ""}
                </p>

                {/* 매집 신호 */}
                {h.accumulation && (
                  <div className="pt-3 border-t border-outline-variant/10">
                    <div className="text-[10px] font-bold tracking-wider text-on-surface-variant/50 mb-2 uppercase flex items-baseline gap-1.5">
                      매집 신호 <span className="font-normal normal-case tracking-normal text-on-surface-variant/70">· {h.accumulation.window}{h.accumulation.elapsed < 15 ? " 진행중" : ""}</span>
                      <span className="ml-auto font-semibold normal-case tracking-normal text-[#34d399]/90">충족 {acc.met}/6</span>
                    </div>
                    <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                      {h.accumulation.signals.map((sg) => {
                        const m = ACC_MARK[sg.status]; const am = ACC_META[sg.id];
                        return (
                          <li key={sg.id} className="flex gap-1.5 leading-relaxed">
                            <span className={`${m.cls} font-bold shrink-0`}>{m.mark}</span>
                            <span className="text-on-surface-variant">
                              <Tip tip={am?.tip ?? ""}><span className="text-on-surface">{am?.label ?? sg.id}</span></Tip>{" "}
                              <span className="text-on-surface-variant/70">{sg.detail}</span>
                            </span>
                          </li>
                        );
                      })}
                      {h.mvp && (["m", "v", "p"] as const).map((k) => {
                        const c = h.mvp![k]; const mk = mvpMark(c.ok); const mm = MVP_META[k];
                        return (
                          <li key={k} className="flex gap-1.5 leading-relaxed">
                            <span className={`${mk.cls} font-bold shrink-0`}>{mk.mark}</span>
                            <span className="text-on-surface-variant">
                              <Tip tip={mm.tip}><span className="text-on-surface">{mm.label}</span></Tip>{" "}
                              <span className="text-on-surface-variant/70">{c.detail}</span>
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {/* 강세 매도 감시 */}
                {h.strength && (
                  <div className="pt-3" style={{ borderTop: `1px solid rgba(245,169,206,0.34)` }}>
                    <div className="text-[10px] font-bold tracking-wider mb-2 uppercase flex items-baseline gap-1.5" style={{ color: HEAT }}>
                      🔥 강세 매도 감시
                      <span className="font-normal normal-case tracking-normal text-on-surface-variant/60">· {h.strength.gate_detail}</span>
                      {st && <span className="ml-auto font-semibold normal-case tracking-normal" style={{ color: HEAT }}>발화 {st.fired}/4</span>}
                    </div>
                    {h.strength.extended ? (
                      <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                        {h.strength.signals.map((sg) => {
                          const m = STRENGTH_MARK[sg.status]; const sm = STRENGTH_META[sg.id];
                          return (
                            <li key={sg.id} className="flex gap-1.5 leading-relaxed">
                              <span className={`${m.cls} font-bold shrink-0`}>{m.mark}</span>
                              <span className="text-on-surface-variant">
                                <Tip tip={sm?.tip ?? ""}>
                                  <span style={sg.status === "fired" ? { color: HEAT } : undefined} className={sg.status === "fired" ? "" : "text-on-surface"}>{sm?.label ?? sg.id}</span>
                                </Tip>{" "}
                                <span className="text-on-surface-variant/70">{sg.detail}</span>
                              </span>
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="text-[11.5px] text-on-surface-variant/60 bg-surface-container/30 rounded-lg px-3 py-2 leading-relaxed">
                        {h.strength.signal === "na"
                          ? "피벗 없음 — 판정 불가 (약세 트랙은 매수일 기준으로 계속 감시)"
                          : `확장 전 — 대기 · ${h.strength.gate_detail}. 피벗 위 5% 이상 올라야 강세 신호를 켭니다.`}
                      </p>
                    )}
                  </div>
                )}

                {/* 약세 규칙 (전체 나열) */}
                {h.rules.length > 0 && (
                  <div className="pt-3 border-t border-outline-variant/10">
                    <div className="text-[10px] font-bold tracking-wider text-on-surface-variant/50 mb-2 uppercase flex items-baseline gap-1.5">
                      약세 규칙
                      <span className="ml-auto font-semibold normal-case tracking-normal text-on-surface-variant/70">
                        통과 {rt.pass}{rt.violation > 0 ? ` · 위반 ${rt.violation}` : ""}{rt.watch > 0 ? ` · 관찰 ${rt.watch}` : ""}
                      </span>
                    </div>
                    <ul className="text-[11px] space-y-1.5">
                      {h.rules.map((r) => {
                        const sm = STATUS_MARK[r.status] ?? STATUS_MARK.na;
                        return (
                          <li key={r.id} className="flex gap-1.5 leading-relaxed">
                            <span className={`${sm.cls} font-bold shrink-0 w-3 text-center`}>{sm.mark}</span>
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
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Typecheck + build**

Run: `npm run build`
Expected: 성공(타입 에러 0). `holdingsSummary.ts`의 타입 import가 새 export와 맞물려 통과.

- [ ] **Step 3: Re-run vitest (regression)**

Run: `npx vitest run src/app/stocks/sepa`
Expected: 기존 sepa 테스트 + `holdingsSummary.test.ts` 전부 PASS.

- [ ] **Step 4: Visual check (dev server)**

Run: `npm run dev` 후 브라우저에서 `/stocks/sepa` 열기.
Expected: 보유 카드가 접힘(이름·수익%·매수→현재·손절까지·확장칩·행동 배지·점수판)으로 표시되고, 클릭 시 매집 6·강세 매도(현재 전부 "확장 전 대기")·약세 규칙 ①~⑥ 전체가 펼쳐진다. 콘솔 에러 없음.

- [ ] **Step 5: Commit**

```bash
git add src/app/stocks/sepa/SepaHoldingsSection.tsx
git commit -m "feat(sepa): 보유 카드 접기/펼치기 + 강세 매도 감시 패널·점수판"
```

---

## Self-Review

**1. Spec coverage**

- 게이트 `extension_pct ≥ 5` 재사용 → Task 5 `evaluate_climax`. ✅
- 신호 4종(climax_run/blowoff_day/exhaustion_gap/distribution) → Task 1~4. ✅
- 데이터 shape `strength{signal,extended,gate_detail,count,signals}` → Task 5. ✅
- 접힘(요약 2줄 + 점수판) / 펼침(전체 나열 + 충족 집계) → Task 8, 점수판 계산 Task 7. ✅
- 로즈 색·인라인 툴팁(STRENGTH_META, page.tsx 미변경) → Task 8. ✅
- 결과 JSON 재생성 → Task 6. ✅
- 문서-로직 동기화(docstring 참조) → Task 5 Step 5. ✅
- 범위 밖(베이스·PER) → 계획에 태스크 없음(의도적). ✅

**2. Placeholder scan** — "TBD/TODO/적절히 처리" 등 없음. 모든 스텝에 실제 코드·명령·기대 출력 포함. ✅

**3. Type consistency**
- `sig_climax_run(series)` / `sig_blowoff_day(series, bi)` / `sig_exhaustion_gap(series)` / `sig_distribution(series, bi)` — Task 1~4 정의와 Task 5 `evaluate_climax` 호출부 시그니처 일치. ✅
- `strength` 반환 키(`signal,extended,gate_detail,count,signals`) — Task 5 정의와 Task 7/8의 TS 인터페이스 `Strength` 필드명 일치. ✅
- `accumTally/ruleTally/strengthTally` 반환 형태 — Task 7 정의와 Task 8 사용부 일치(`acc.met/acc.complete`, `rt.pass/violation/watch`, `st.fired`). ✅
- TS 타입 export(`StrengthSignal, Strength`) — Task 8에서 export, Task 7이 `import type`으로 소비. Task 7이 Task 8보다 먼저면 타입 미해결이므로, 실행 순서는 **Task 7 → Task 8 연속**으로 두고 빌드/타입체크는 Task 8 Step 2에서 함께 통과시킨다(주석 명시). ✅

---

## Execution Handoff

집계상 순서: Task 1→2→3→4→5→6(백엔드, 각자 pytest 통과) → Task 7→8(프론트, 타입체크는 8에서 함께). Task 6 재생성 JSON은 백엔드 완료 후.
