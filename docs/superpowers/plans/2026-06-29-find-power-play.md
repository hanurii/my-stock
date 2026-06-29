# find-power-play (High Tight Flag) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** find-vcp의 형제 스킬 `find-power-play`를 추가한다 — 트렌드 통과 종목에서 미너비니 파워 플레이(High Tight Flag) 패턴을 탐지해 `sepa-power-play-candidates.json`에 산출한다.

**Architecture:** find-vcp와 동일 구조를 미러링한다. 순수 평가 부품 `canslim_lib/power_play.py`(합성 시계열로 단위 테스트), CLI 엔트리 `scripts/screen_power_play.py`(입력 로드→종목별 평가→JSON+콘솔 요약), 스킬 문서 `.claude/skills/find-power-play/SKILL.md`. 알고리즘: 깃대(8주 내 100%↑·대규모 거래량·조용한 출발) + 깃발(6주↓·조정 ≤20%·돌파 전 거래량 마름).

**Tech Stack:** Python 3 (표준 라이브러리만), pytest. 기존 `canslim_lib/vcp.py`·`screen_vcp.py`·`tests/test_vcp.py` 패턴 그대로.

## Global Constraints

- 정의·근거 원본: `docs/superpowers/specs/2026-06-29-find-power-play-design.md`. 코드 주석 헤더에 이 경로 명시(개념=미너비니, 수치=공학적 번역).
- **공유 파일 무접촉**: `public/data/trend-template-candidates.json` 등 공유 파일을 절대 건드리지 않는다. 출력은 항상 `public/data/sepa-power-play-candidates.json`(또는 `--out`).
- **컷오프 금지**: 시총·거래대금·가격 컷오프를 추가하지 않는다.
- **환각 금지**: 모든 종목을 출력에 포함(불성립도 `reason`과 함께). 콘솔 수치는 그대로 보고.
- **자동 commit/push 안 함** (실행 시 사용자 판단).
- 순수 함수 부품은 표준 라이브러리만 사용(numpy/pandas 금지 — vcp.py와 동일).
- 한 종목 평가 오류가 전체 런을 멈추지 않게 종목별 try/except로 감싼다(`reason="eval_error:<타입>"`).
- reason 코드(전체): `no_data` / `no_series` / `base_too_short` / `pole_gain_too_small` / `pole_volume_weak` / `not_quiet_before_pole` / `flag_too_short` / `flag_too_long` / `flag_too_deep` / `volume_not_drying` / `eval_error:*`.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `scripts/canslim_lib/power_play.py` (생성) | 순수 평가 부품: `DEFAULT_PARAMS`, `find_flagpole(...)`, `evaluate_power_play(series, params)` |
| `tests/test_power_play.py` (생성) | 위 부품의 단위 테스트(합성 시계열) |
| `scripts/screen_power_play.py` (생성) | CLI 엔트리: 입력 로드→평가→JSON 저장+콘솔 요약 |
| `.claude/skills/find-power-play/SKILL.md` (생성) | 스킬 문서(find-vcp SKILL.md 톤) |

---

## Task 1: `find_flagpole` 헬퍼 + `DEFAULT_PARAMS`

깃대 탐지(가장 까다로운 경계 처리)를 독립 순수 함수로 분리하고 단위 테스트한다.

**Files:**
- Create: `scripts/canslim_lib/power_play.py`
- Test: `tests/test_power_play.py`

**Interfaces:**
- Produces:
  - `DEFAULT_PARAMS: dict` — 키: `lookback_days, min_total_days, min_flagpole_gain, max_flagpole_days, pole_vol_mult, quiet_window, max_pre_pole_gain, min_flag_days, max_flag_days, max_flag_depth, breakout_vol_mult, near_pivot_pct`.
  - `find_flagpole(highs: list[float], lows: list[float], max_flagpole_days: int) -> dict` — `flag_high`(구간 최고 고가) 지점과 그 직전 `max_flagpole_days` 경계 안의 최저 저점을 찾는다. 반환 키: `flag_high_idx, flag_high, pole_start_idx, pole_start_low, flagpole_gain_pct, flagpole_days`. 데이터 부족(고점이 구간 시작이라 깃대 형성 불가) 시 `flagpole_gain_pct=0.0`.

- [ ] **Step 1: Write the failing tests**

`tests/test_power_play.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.power_play import DEFAULT_PARAMS, find_flagpole


def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_flagpole_gain", "max_flagpole_days",
              "pole_vol_mult", "quiet_window", "max_pre_pole_gain",
              "min_flag_days", "max_flag_days", "max_flag_depth",
              "breakout_vol_mult", "near_pivot_pct", "min_total_days"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_flagpole_gain"] == 100.0
    assert DEFAULT_PARAMS["max_flagpole_days"] == 40


def test_find_flagpole_detects_doubling():
    # 저점 50에서 시작해 110까지(+120%) 오른 뒤, 100 근처 고점이 인덱스 5
    highs = [52, 70, 90, 105, 110, 111, 108, 106, 104]
    lows  = [50, 66, 86, 100, 105, 106, 100, 98, 96]
    fp = find_flagpole(highs, lows, max_flagpole_days=40)
    # 구간 최고 고가는 인덱스 5(111)
    assert fp["flag_high_idx"] == 5
    assert fp["flag_high"] == 111
    # 깃대 시작 저점은 50(인덱스 0)
    assert fp["pole_start_low"] == 50
    assert fp["pole_start_idx"] == 0
    # (111-50)/50*100 = 122%
    assert abs(fp["flagpole_gain_pct"] - 122.0) < 1e-6
    assert fp["flagpole_days"] == 5


def test_find_flagpole_respects_window_cap():
    # 아주 오래된 저점(인덱스0=10)은 40일 경계 밖이면 무시되고,
    # 경계 안 최저점만 깃대 시작으로 잡힌다.
    highs = [12] + [40]*45 + [80]   # 고점은 마지막(인덱스46)
    lows  = [10] + [38]*45 + [70]
    fp = find_flagpole(highs, lows, max_flagpole_days=40)
    assert fp["flag_high_idx"] == 46
    # 경계 = 46-40 = 6 이후의 최저 저점(38), 10이 아님
    assert fp["pole_start_low"] == 38
    assert fp["flagpole_days"] <= 40
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: FAIL — `ImportError: cannot import name 'DEFAULT_PARAMS'` / module not found.

- [ ] **Step 3: Write minimal implementation**

`scripts/canslim_lib/power_play.py`:
```python
"""미너비니 파워 플레이(High Tight Flag) 평가 부품 (순수 함수).

개념(깃대·깃발·조용한 출발·거래량 마름)=마크 미너비니. 구체 수치·계산규칙=이
프로젝트의 공학적 번역(원전 아님).
정의·근거: docs/superpowers/specs/2026-06-29-find-power-play-design.md
"""
from __future__ import annotations

DEFAULT_PARAMS: dict = {
    "lookback_days": 120,
    "min_total_days": 20,
    "min_flagpole_gain": 100.0,
    "max_flagpole_days": 40,
    "pole_vol_mult": 1.5,
    "quiet_window": 20,
    "max_pre_pole_gain": 30.0,
    "min_flag_days": 8,
    "max_flag_days": 30,
    "max_flag_depth": 20.0,
    "breakout_vol_mult": 1.4,
    "near_pivot_pct": 5.0,
}


def find_flagpole(highs: list[float], lows: list[float], max_flagpole_days: int) -> dict:
    """구간 최고 고가(깃발 고점)와 그 직전 max_flagpole_days 경계 안의 최저
    저점(깃대 시작)을 찾아 상승률·기간을 계산한다."""
    n = len(highs)
    flag_high_idx = max(range(n), key=lambda i: highs[i])
    flag_high = highs[flag_high_idx]
    window_start = max(0, flag_high_idx - max_flagpole_days)
    # 깃발 고점 바는 제외하고 그 이전 구간에서 최저 저점 탐색
    search_end = flag_high_idx  # exclusive 상한
    if search_end <= window_start:
        # 고점이 구간 시작 → 깃대 형성 불가
        return {
            "flag_high_idx": flag_high_idx, "flag_high": flag_high,
            "pole_start_idx": flag_high_idx, "pole_start_low": flag_high,
            "flagpole_gain_pct": 0.0, "flagpole_days": 0,
        }
    pole_start_idx = min(range(window_start, search_end), key=lambda i: lows[i])
    pole_start_low = lows[pole_start_idx]
    gain = (flag_high - pole_start_low) / pole_start_low * 100.0 if pole_start_low > 0 else 0.0
    return {
        "flag_high_idx": flag_high_idx, "flag_high": flag_high,
        "pole_start_idx": pole_start_idx, "pole_start_low": pole_start_low,
        "flagpole_gain_pct": gain, "flagpole_days": flag_high_idx - pole_start_idx,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/power_play.py tests/test_power_play.py
git commit -m "feat(power-play): find_flagpole 깃대 탐지 + DEFAULT_PARAMS"
```

---

## Task 2: `evaluate_power_play` — 패턴 판정·지표·상태

깃대·깃발 6조건 판정, 지표 산출, 상태(breakout/actionable/forming/failed)·entry_ready·reason을 한 함수로 구현한다(상태가 detection 중간값을 공유하므로 분리하지 않음).

**Files:**
- Modify: `scripts/canslim_lib/power_play.py`
- Test: `tests/test_power_play.py`

**Interfaces:**
- Consumes: `find_flagpole(...)`, `DEFAULT_PARAMS` (Task 1).
- Produces: `evaluate_power_play(series: dict, params: dict | None = None) -> dict`.
  - `series` 키: `dates, closes, highs, lows, volumes`.
  - 반환 키: `pattern_detected, entry_ready, flagpole_gain_pct, flagpole_days, flagpole_vol_ratio, pre_pole_gain_pct, flag_length_days, flag_depth_pct, pivot_price, pct_to_pivot, volume_dryup_ratio, tightness_pct, status, reason, pole_start_date, flag_high_date`.

- [ ] **Step 1: Write the failing tests**

`tests/test_power_play.py`에 추가:
```python
from canslim_lib.power_play import evaluate_power_play


def _series(closes, highs=None, lows=None, vols=None):
    n = len(closes)
    highs = highs if highs is not None else [c * 1.01 for c in closes]
    lows = lows if lows is not None else [c * 0.99 for c in closes]
    vols = vols if vols is not None else [1000] * n
    dates = [f"2026-01-{i+1:03d}" for i in range(n)]
    return {"dates": dates, "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def _clean_htf():
    """조용(20일 저변동) → 8주 내 +120% 깃대(대량거래) → 좁고 얕은 깃발(~10%)."""
    quiet = [50 + (i % 2) for i in range(20)]          # 50~51 횡보(조용)
    pole = [52, 58, 66, 75, 85, 95, 104, 110]          # 50→110 (+120%), 8일
    flag = [108, 106, 105, 104, 103, 105, 106, 107, 106, 105]  # 고점110 대비 ~5.5% 얕은 깃발
    closes = quiet + pole + flag
    highs = [c * 1.01 for c in closes]
    lows = [c * 0.99 for c in closes]
    # 거래량: 조용 낮음(800) → 깃대 대량(3000) → 깃발 마름(500)
    vols = [800]*len(quiet) + [3000]*len(pole) + [500]*len(flag)
    return {"dates": [f"d{i}" for i in range(len(closes))],
            "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def test_evaluate_detects_clean_htf():
    r = evaluate_power_play(_clean_htf())
    assert r["pattern_detected"] is True
    assert r["reason"] is None
    assert r["flagpole_gain_pct"] >= 100.0
    assert r["flag_depth_pct"] <= 20.0
    assert r["flagpole_vol_ratio"] >= 1.5
    assert r["pivot_price"] is not None


def test_evaluate_rejects_short_total_series():
    r = evaluate_power_play(_series([100, 101, 99, 102, 100]))
    assert r["pattern_detected"] is False
    assert r["reason"] == "base_too_short"


def test_evaluate_rejects_weak_flagpole_gain():
    s = _clean_htf()
    # 깃대 상승률만 죽인다: 깃대를 +30%짜리로 교체(저점50→고점65)
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 55, 58, 60, 62, 63, 64, 65]
    flag = [64, 63, 62, 63, 64, 63, 62, 63, 64, 63]
    closes = quiet + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*10)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "pole_gain_too_small"


def test_evaluate_rejects_weak_pole_volume():
    s = _clean_htf()
    # 깃대 거래량을 조용 구간과 동일하게(800) → 대량거래 조건 실패
    s["volumes"] = [800]*20 + [800]*8 + [500]*10
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "pole_volume_weak"


def test_evaluate_rejects_not_quiet_before_pole():
    # 폭등 직전 20일이 이미 +50% 상승(말기 베이스) → not_quiet_before_pole
    pre = [50 + i*1.3 for i in range(20)]   # 50→약74.7 (+49%)
    pole = [76, 84, 92, 100, 110, 120, 130, 150]   # 74.7→150 추가 폭등
    flag = [148, 146, 145, 144, 145, 146, 147, 146, 145, 144]
    closes = pre + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*10)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "not_quiet_before_pole"


def test_evaluate_rejects_deep_flag():
    s = _clean_htf()
    # 깃발 저점을 깊게: 110고점 대비 -30% (77)까지 빠짐
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 58, 66, 75, 85, 95, 104, 110]
    flag = [105, 98, 90, 82, 77, 80, 85, 88, 90, 92]   # 깊은 조정 ~30%
    closes = quiet + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*10)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "flag_too_deep"


def test_evaluate_rejects_too_long_flag():
    s = _clean_htf()
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 58, 66, 75, 85, 95, 104, 110]
    flag = [106]*35   # 6주(30일) 초과 횡보
    closes = quiet + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*35)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "flag_too_long"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: FAIL — `ImportError: cannot import name 'evaluate_power_play'`.

- [ ] **Step 3: Write minimal implementation**

`scripts/canslim_lib/power_play.py`에 추가:
```python
def _mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def evaluate_power_play(series: dict, params: dict | None = None) -> dict:
    """파워 플레이(High Tight Flag) 종합 판정."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    lb = p["lookback_days"]
    closes = (series.get("closes") or [])[-lb:]
    highs = (series.get("highs") or [])[-lb:]
    lows = (series.get("lows") or [])[-lb:]
    vols = (series.get("volumes") or [])[-lb:]
    dates = (series.get("dates") or [])[-lb:]

    base: dict = {
        "pattern_detected": False, "entry_ready": False,
        "flagpole_gain_pct": None, "flagpole_days": None, "flagpole_vol_ratio": None,
        "pre_pole_gain_pct": None, "flag_length_days": None, "flag_depth_pct": None,
        "pivot_price": None, "pct_to_pivot": None, "volume_dryup_ratio": None,
        "tightness_pct": None, "status": "forming", "reason": None,
        "pole_start_date": None, "flag_high_date": None,
    }
    n = len(closes)
    if n == 0:
        base["reason"] = "no_data"
        return base
    if n < p["min_total_days"]:
        base["reason"] = "base_too_short"
        return base

    fp = find_flagpole(highs, lows, p["max_flagpole_days"])
    fhi = fp["flag_high_idx"]
    psi = fp["pole_start_idx"]
    flag_high = fp["flag_high"]
    base["flagpole_gain_pct"] = round(fp["flagpole_gain_pct"], 2)
    base["flagpole_days"] = fp["flagpole_days"]
    base["pole_start_date"] = dates[psi] if psi < len(dates) else None
    base["flag_high_date"] = dates[fhi] if fhi < len(dates) else None
    base["pivot_price"] = round(flag_high, 2)

    # --- 깃발 지표 ---
    flag_lows = lows[fhi:]
    flag_low = min(flag_lows) if flag_lows else flag_high
    flag_len = (n - 1) - fhi
    flag_depth = (flag_high - flag_low) / flag_high * 100.0 if flag_high > 0 else 0.0
    base["flag_length_days"] = flag_len
    base["flag_depth_pct"] = round(flag_depth, 2)

    # --- 거래량 지표 ---
    pole_vol_avg = _mean(vols[psi:fhi + 1]) or 0.0
    quiet_start = max(0, psi - p["quiet_window"])
    quiet_vols = vols[quiet_start:psi] if psi > quiet_start else []
    quiet_vol_avg = _mean(quiet_vols)
    base["flagpole_vol_ratio"] = (
        round(pole_vol_avg / quiet_vol_avg, 3) if quiet_vol_avg else None
    )
    base["volume_dryup_ratio"] = (
        round((_mean(vols[-5:]) or 0.0) / pole_vol_avg, 3) if pole_vol_avg else None
    )
    tight = _mean(
        [(highs[i] - lows[i]) / closes[i] * 100.0 for i in range(n)[-10:] if closes[i]]
    )
    base["tightness_pct"] = round(tight, 2) if tight is not None else None

    # --- 조용한 출발(말기 베이스 제외) ---
    quiet_highs = highs[quiet_start:psi] if psi > quiet_start else []
    quiet_lows = lows[quiet_start:psi] if psi > quiet_start else []
    if quiet_highs and quiet_lows and min(quiet_lows) > 0:
        pre_gain = (max(quiet_highs) - min(quiet_lows)) / min(quiet_lows) * 100.0
        base["pre_pole_gain_pct"] = round(pre_gain, 2)
        cond_quiet = pre_gain <= p["max_pre_pole_gain"]
    else:
        cond_quiet = True  # 폭등 직전 데이터 부족 → 의심의 이익(거절 안 함)

    # --- 6조건 판정 ---
    cond_gain = fp["flagpole_gain_pct"] >= p["min_flagpole_gain"]
    cond_pole_vol = (
        base["flagpole_vol_ratio"] is not None
        and base["flagpole_vol_ratio"] >= p["pole_vol_mult"]
    )
    cond_flag_min = flag_len >= p["min_flag_days"]
    cond_flag_max = flag_len <= p["max_flag_days"]
    cond_flag_depth = flag_depth <= p["max_flag_depth"]
    cond_dryup = base["volume_dryup_ratio"] is not None and base["volume_dryup_ratio"] < 1.0

    if not cond_gain:
        base["reason"] = "pole_gain_too_small"
    elif not cond_pole_vol:
        base["reason"] = "pole_volume_weak"
    elif not cond_quiet:
        base["reason"] = "not_quiet_before_pole"
    elif not cond_flag_min:
        base["reason"] = "flag_too_short"
    elif not cond_flag_max:
        base["reason"] = "flag_too_long"
    elif not cond_flag_depth:
        base["reason"] = "flag_too_deep"
    elif not cond_dryup:
        base["reason"] = "volume_not_drying"
    else:
        base["pattern_detected"] = True

    # --- 피벗·상태 ---
    last_close = closes[-1]
    last_vol = vols[-1] if vols else 0.0
    base["pct_to_pivot"] = round((flag_high - last_close) / flag_high * 100.0, 2) if flag_high > 0 else None
    if last_close > flag_high and pole_vol_avg and last_vol >= pole_vol_avg * p["breakout_vol_mult"]:
        base["status"] = "breakout"
    elif flag_depth > p["max_flag_depth"] or last_close < flag_low:
        base["status"] = "failed"
    elif (
        base["pct_to_pivot"] is not None
        and 0 <= base["pct_to_pivot"] <= p["near_pivot_pct"]
        and (base["volume_dryup_ratio"] if base["volume_dryup_ratio"] is not None else 9.9) <= 1.0
    ):
        base["status"] = "actionable"
    else:
        base["status"] = "forming"
    base["entry_ready"] = bool(
        base["pattern_detected"] and base["status"] in ("breakout", "actionable")
    )
    return base
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: PASS (이전 3 + 신규 7 = 10 tests). 실패 시 합성 시계열 수치를 조정하지 말고 먼저 어느 조건이 어긋났는지 `--ticker` 식 디버그처럼 반환 dict를 출력해 원인 파악(테스트가 의도한 reason과 실제 reason 비교).

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/power_play.py tests/test_power_play.py
git commit -m "feat(power-play): evaluate_power_play 6조건 판정·상태·근거"
```

---

## Task 3: `evaluate_power_play` 상태 검증 (breakout / actionable / failed)

Task 2에서 status 로직을 구현했으니, 상태 전이를 명시적으로 고정하는 테스트를 추가한다(회귀 방지).

**Files:**
- Test: `tests/test_power_play.py`

**Interfaces:**
- Consumes: `evaluate_power_play(...)` (Task 2).

- [ ] **Step 1: Write the failing tests**

`tests/test_power_play.py`에 추가:
```python
def test_status_breakout_on_pivot_break_with_volume():
    s = _clean_htf()
    # 피벗(고점 110) 위로 종가 돌파 + 대량거래 1일 추가
    s["closes"].append(113.0)
    s["highs"].append(114.0)
    s["lows"].append(112.0)
    s["volumes"].append(6000)   # pole 평균(3000)의 1.4배 이상
    s["dates"].append("dN")
    r = evaluate_power_play(s)
    assert r["status"] == "breakout"
    assert r["entry_ready"] == (r["pattern_detected"] and r["status"] in ("breakout", "actionable"))


def test_status_failed_on_flag_breakdown():
    s = _clean_htf()
    # 깃발 저점을 깊게 깨고 종가가 그 아래로 → failed
    s["closes"].append(70.0)
    s["highs"].append(72.0)
    s["lows"].append(69.0)
    s["volumes"].append(2000)
    s["dates"].append("dN")
    r = evaluate_power_play(s)
    assert r["status"] == "failed"


def test_status_actionable_near_pivot_with_dryup():
    s = _clean_htf()
    # 마지막 종가가 피벗(110) 0~5% 아래 + 거래량 마름 유지
    s["closes"].append(107.0)   # (110-107)/110 = 2.7%
    s["highs"].append(108.0)
    s["lows"].append(106.0)
    s["volumes"].append(500)
    s["dates"].append("dN")
    r = evaluate_power_play(s)
    assert r["status"] == "actionable"
    assert 0 <= r["pct_to_pivot"] <= 5
```

- [ ] **Step 2: Run tests to verify they fail (or pass immediately)**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: 이미 Task 2에서 status 로직이 구현됐으므로 PASS 할 수 있다. 만약 FAIL 하면 해당 status 분기의 조건(피벗 비교·거래량 배수·near_pivot_pct)을 Task 2 구현과 대조해 고친다. (테스트가 통과하도록 합성 수치만 현실적으로 조정 가능 — 단, status 로직 자체의 의도는 spec §4.6 기준.)

- [ ] **Step 3: (구현 변경이 필요하면) 최소 수정**

status 분기가 테스트 의도와 어긋나면 `scripts/canslim_lib/power_play.py`의 해당 분기만 수정. 어긋나지 않으면 변경 없음.

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: PASS (13 tests).

- [ ] **Step 5: Commit**

```bash
git add tests/test_power_play.py scripts/canslim_lib/power_play.py
git commit -m "test(power-play): 상태 전이(breakout/actionable/failed) 회귀 테스트"
```

---

## Task 4: CLI 엔트리 `screen_power_play.py`

find-vcp의 `screen_vcp.py`를 미러링한 CLI. 입력 로드→종목별 평가(오류 격리)→JSON 저장+콘솔 요약.

**Files:**
- Create: `scripts/screen_power_play.py`

**Interfaces:**
- Consumes: `canslim_lib.power_play.evaluate_power_play`, `DEFAULT_PARAMS`; `canslim_lib.ohlcv_matrix.get_series(code)`.
- Produces: 실행파일(`python scripts/screen_power_play.py`). 출력 `public/data/sepa-power-play-candidates.json`.

- [ ] **Step 1: 구현 작성** (TDD 대상 아님 — I/O 스크립트, 콘솔/파일 출력으로 수동 검증)

`scripts/screen_power_play.py`:
```python
# scripts/screen_power_play.py
"""find-power-play — SEPA 패턴: 트렌드 통과 종목의 파워 플레이(High Tight Flag) 탐지.

입력: public/data/sepa-trend-candidates.json (all_pass 종목)
출력: public/data/sepa-power-play-candidates.json
정의: docs/superpowers/specs/2026-06-29-find-power-play-design.md
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
from canslim_lib.power_play import evaluate_power_play, DEFAULT_PARAMS  # noqa: E402

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-trend-candidates.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-power-play-candidates.json"
STATUS_ORDER = {"breakout": 0, "actionable": 1, "forming": 2, "failed": 3}

EMPTY = {
    "pattern_detected": False, "entry_ready": False, "status": "forming",
    "flagpole_gain_pct": None, "flagpole_days": None, "flagpole_vol_ratio": None,
    "pre_pole_gain_pct": None, "flag_length_days": None, "flag_depth_pct": None,
    "pivot_price": None, "pct_to_pivot": None, "volume_dryup_ratio": None,
    "tightness_pct": None, "pole_start_date": None, "flag_high_date": None,
}


def run(args, out_path: Path) -> None:
    in_path = Path(args.inp) if args.inp else IN_PATH
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.exists():
        print(f"❌ 입력 파일 없음: {in_path.relative_to(ROOT)}\n"
              f"   먼저 find-trend-template 을 실행해 sepa-trend-candidates.json 을 생성하세요.")
        sys.exit(1)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    passers = [c for c in data.get("candidates", []) if c.get("all_pass")]
    if args.ticker:
        passers = [c for c in passers if c.get("code") == args.ticker]

    params = {
        "lookback_days": args.lookback_days,
        "min_flagpole_gain": args.min_flagpole_gain,
        "max_flagpole_days": args.max_flagpole_days,
        "pole_vol_mult": args.pole_vol_mult,
        "max_pre_pole_gain": args.max_pre_pole_gain,
        "min_flag_days": args.min_flag_days,
        "max_flag_days": args.max_flag_days,
        "max_flag_depth": args.max_flag_depth,
        "breakout_vol_mult": args.breakout_vol_mult,
        "near_pivot_pct": args.near_pivot_pct,
    }
    out_cands = []
    for c in passers:
        code = c["code"]
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            r = {**EMPTY, "reason": "no_series"}
        else:
            try:
                r = evaluate_power_play(s, params)
            except Exception as e:  # 한 종목 오류가 전체 런을 멈추지 않게
                r = {**EMPTY, "status": "failed", "reason": f"eval_error:{type(e).__name__}"}
        out_cands.append({
            "code": code, "name": c.get("name"), "market": c.get("market"),
            "current_price": c.get("current_price"), "rs": c.get("rs"),
            **r,
        })

    out_cands.sort(key=lambda x: (
        0 if x.get("entry_ready") else 1,
        STATUS_ORDER.get(x["status"], 9),
        x["pct_to_pivot"] if x["pct_to_pivot"] is not None else 1e9,
    ))
    dist = {k: sum(1 for x in out_cands if x["status"] == k)
            for k in ("breakout", "actionable", "forming", "failed")}
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": data.get("asof"),
        "source": in_path.name,
        "params": {**DEFAULT_PARAMS, **params},
        "pattern_count": sum(1 for x in out_cands if x["pattern_detected"]),
        "entry_ready_count": sum(1 for x in out_cands if x.get("entry_ready")),
        "status_distribution": dist,
        "candidates": out_cands,
    }

    if not args.ticker:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 저장: {out_path.relative_to(ROOT)}")

    er = output["entry_ready_count"]
    print(f"\n[파워플레이 요약] 입력 {len(passers)}종목 | 패턴 {output['pattern_count']} | "
          f"진입가능(entry_ready) {er} | "
          f"breakout {dist['breakout']} · actionable {dist['actionable']} · "
          f"forming {dist['forming']} · failed {dist['failed']}")
    shown = [x for x in out_cands if x.get("entry_ready")]
    if not shown:
        print("  (진입 가능 종목 없음 — 파워플레이 성립 + 돌파/근접 동시 충족 없음)")
    for x in shown:
        print(f"  [{x['status']:10s}] {x['code']} {str(x['name'])[:12]:12s} "
              f"깃대 {x['flagpole_gain_pct']}%/{x['flagpole_days']}d "
              f"깃발 {x['flag_depth_pct']}%/{x['flag_length_days']}d "
              f"피벗 {x['pivot_price']} → {x['pct_to_pivot']}%")


def main():
    ap = argparse.ArgumentParser(description="find-power-play — 파워 플레이(High Tight Flag) 탐지")
    ap.add_argument("--in", dest="inp", default=None, help=f"입력(default {IN_PATH.name})")
    ap.add_argument("--out", dest="out", default=None, help=f"출력(default {OUT_PATH.name})")
    ap.add_argument("--ticker", default=None, help="단일 종목 디버그(저장 안 함)")
    ap.add_argument("--lookback-days", type=int, default=DEFAULT_PARAMS["lookback_days"])
    ap.add_argument("--min-flagpole-gain", type=float, default=DEFAULT_PARAMS["min_flagpole_gain"])
    ap.add_argument("--max-flagpole-days", type=int, default=DEFAULT_PARAMS["max_flagpole_days"])
    ap.add_argument("--pole-vol-mult", type=float, default=DEFAULT_PARAMS["pole_vol_mult"])
    ap.add_argument("--max-pre-pole-gain", type=float, default=DEFAULT_PARAMS["max_pre_pole_gain"])
    ap.add_argument("--min-flag-days", type=int, default=DEFAULT_PARAMS["min_flag_days"])
    ap.add_argument("--max-flag-days", type=int, default=DEFAULT_PARAMS["max_flag_days"])
    ap.add_argument("--max-flag-depth", type=float, default=DEFAULT_PARAMS["max_flag_depth"])
    ap.add_argument("--breakout-vol-mult", type=float, default=DEFAULT_PARAMS["breakout_vol_mult"])
    ap.add_argument("--near-pivot-pct", type=float, default=DEFAULT_PARAMS["near_pivot_pct"])
    args = ap.parse_args()
    if args.out:
        out_path = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    else:
        out_path = OUT_PATH
    run(args, out_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 단일 종목 디버그로 동작 확인** (입력 파일이 있을 때)

Run: `python scripts/screen_power_play.py --ticker <트렌드통과_종목코드>`
Expected: 저장 메시지 없이 콘솔에 `[파워플레이 요약]` 줄 출력. 오류 없이 종료(exit 0).
(입력 파일이 없으면 먼저 update-data → find-trend-template 실행이 필요하다는 안내가 정상. 그 경우 이 스텝은 SKILL.md 작성 후 Task 5 풀런에서 확인.)

- [ ] **Step 3: import·문법 스모크 테스트**

Run: `python -c "import sys; sys.path.insert(0,'scripts'); import screen_power_play; print('ok')"`
Expected: `ok` (import 에러 없음).

- [ ] **Step 4: Commit**

```bash
git add scripts/screen_power_play.py
git commit -m "feat(power-play): screen_power_play CLI 엔트리"
```

---

## Task 5: 스킬 문서 `SKILL.md` + 실데이터 풀런 검증

**Files:**
- Create: `.claude/skills/find-power-play/SKILL.md`

**Interfaces:**
- Consumes: `scripts/screen_power_play.py` (Task 4).

- [ ] **Step 1: SKILL.md 작성**

`.claude/skills/find-power-play/SKILL.md`:
```markdown
---
name: find-power-play
description: >
  SEPA 패턴 스킬(find-vcp 형제). 1단계(find-trend-template) 통과 종목의 일봉에서
  미너비니 파워 플레이(Power Play = High Tight Flag)를 탐지한다 — 8주 내 100%↑
  대량거래 폭등(깃대) + 얕고 좁은 횡보(깃발) + 돌파 전 거래량 마름. 피벗·진입상태
  (breakout/actionable/forming/failed)를 산출해 sepa-power-play-candidates.json
  에 저장한다. OHLCV 캐시만 사용, 수급·공유 파일 무접촉. 사용자가 "/find-power-play",
  "파워 플레이 찾아줘", "하이 타이트 플래그", "깃발 패턴" 등을 요청할 때 사용.
---

# find-power-play — SEPA 패턴: 파워 플레이(High Tight Flag)

`find-trend-template` 통과 종목에 대해 미너비니 **파워 플레이**(폭발적 깃대 +
얕은 깃발 + 돌파)를 탐지한다. find-vcp 의 형제 스킬(같은 입력, 다른 패턴).
정의·근거: `docs/superpowers/specs/2026-06-29-find-power-play-design.md`.

## 사전 조건
- **최신 데이터로 돌리려면 먼저 `update-data` → `find-trend-template`** 실행.
- 입력 `public/data/sepa-trend-candidates.json` 존재(= find-trend-template 산출).

## 실행 (1줄)
\`\`\`
python scripts/screen_power_play.py
\`\`\`
- 산출: `public/data/sepa-power-play-candidates.json`
- 콘솔: 상태 분포 + entry_ready 종목 표(깃대 상승률·기간, 깃발 깊이·길이, 피벗).

### 옵션
- `--ticker CODE` : 단일 종목 디버그(저장 안 함).
- `--min-flagpole-gain 100` / `--max-flagpole-days 40` : 깃대(8주 내 100%↑) 튜닝.
- `--pole-vol-mult 1.5` / `--max-pre-pole-gain 30` : 대량거래·조용한 출발 튜닝.
- `--min-flag-days 8` / `--max-flag-days 30` / `--max-flag-depth 20` : 깃발 튜닝
  (저가주는 `--max-flag-depth 25`).
- `--out PATH` : 출력 경로 변경.

## 결과 확인
- `pattern_count` : 파워 플레이 6조건 성립 종목 수(100% 깃대라 희귀한 게 정상).
- `status_distribution` : breakout(돌파) · actionable(피벗 근접+거래량 마름) ·
  forming(형성 중) · failed(깃발 붕괴).
- `entry_ready` 종목이 다음 단계(리스크·진입) 후보.
- 불성립 종목도 `reason`과 함께 전부 포함(환각 방지·디버그).

## 안 하는 것
- VCP 베이스 탐지(그건 find-vcp) · 전 종목 스캔(트렌드 통과 종목만) ·
  공유 파일 갱신 · 수급 신호 · 자동 commit.
- 타이트(tightness)는 합격 게이트가 아님 — 보고용 지표(책: 조정 ≤10%면 이미
  타이트). 핵심 게이트는 깃대(100%/8주·대량거래·조용) + 깃발(6주↓·≤20%·거래량 마름).
```

- [ ] **Step 2: 실데이터 풀런** (입력 파일이 존재할 때)

Run: `python scripts/screen_power_play.py`
Expected:
- `💾 저장: public\data\sepa-power-play-candidates.json` 출력.
- `[파워플레이 요약]` 에 입력 종목 수·패턴 수·상태 분포 출력.
- 패턴/entry_ready 가 0이거나 극소수인 것이 정상(100% 깃대는 희귀). 오류로 종료하지 않음.

입력 파일이 없으면: 먼저 `update-data` → `find-trend-template`(`python scripts/screen_trend_template.py --rs-min 80 --out public/data/sepa-trend-candidates.json --save`)을 실행해 입력을 만든 뒤 재실행.

- [ ] **Step 3: 산출 JSON 구조 확인**

Read `public/data/sepa-power-play-candidates.json` 상단:
- `params`에 모든 임계값 포함, `pattern_count`/`entry_ready_count`/`status_distribution` 존재.
- `candidates[]`에 입력 종목 전부 포함(불성립도 `reason` 채워짐).
- 정렬: entry_ready 우선 → status → pct_to_pivot.

- [ ] **Step 4: 전체 테스트 재실행(회귀 확인)**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: PASS (13 tests).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/find-power-play/SKILL.md public/data/sepa-power-play-candidates.json
git commit -m "feat(power-play): find-power-play SKILL 문서 + 첫 풀런 산출"
```
(산출 JSON 커밋이 부담되면 SKILL.md만 커밋하고 산출물은 제외 가능.)

---

## Self-Review

**1. Spec coverage (spec §별 → 태스크 매핑):**
- §2 범위(입력 all_pass·출력 파일·안 하는 것) → Task 4(입력 필터·출력), Task 5(SKILL.md 안 하는 것).
- §4.1 lookback 120 → Task 2(`DEFAULT_PARAMS`, 슬라이싱).
- §4.2 깃발 고점·깃대 탐지(경계 구간 argmin) → Task 1(`find_flagpole`).
- §4.3 깃대 거래량(`flagpole_vol_ratio`, `pole_vol_mult`) → Task 2 + 테스트 `weak_pole_volume`.
- §4.4 조용한 출발(`pre_pole_gain_pct`, `max_pre_pole_gain`) → Task 2 + 테스트 `not_quiet_before_pole`.
- §4.5 깃발(길이·깊이·거래량 마름) → Task 2 + 테스트 `deep_flag`·`too_long_flag`.
- §4.5-4 타이트=보고용(게이트 아님) → Task 2(`tightness_pct`만 기록, 조건에서 제외), Task 5 문서 명시.
- §4.6 피벗·상태·entry_ready → Task 2(구현) + Task 3(상태 회귀 테스트).
- §5 출력 스키마·reason 전체·정렬 → Task 4(스키마 조립·정렬), reason은 Task 2.
- §6 코드 구조·CLI 인자 → Task 1·2(부품), Task 4(CLI 인자 전체).
- §7 불변 원칙 → Global Constraints + Task 4(공유 파일 무접촉·전 종목 포함·오류 격리).
- §8 검증 계획 → Task 1·2·3 단위 테스트(①~⑦), Task 5 풀런·`--ticker`.

**2. Placeholder scan:** "TBD/TODO/적절히 처리" 없음. 모든 코드 스텝에 실제 코드 포함. status 분기까지 전부 명시.

**3. Type consistency:** `find_flagpole` 반환 키(`flag_high_idx, flag_high, pole_start_idx, pole_start_low, flagpole_gain_pct, flagpole_days`)를 Task 2가 그대로 소비. `evaluate_power_play` 반환 키를 Task 4 `EMPTY`/콘솔/스키마가 일치 사용. `DEFAULT_PARAMS` 키와 CLI 인자명(`min_flagpole_gain` 등) 일치. reason 코드 집합(Global Constraints)과 Task 2 분기·Task 4(`no_series`,`eval_error:*`) 일치.

**참고(엣지):** `find_flagpole`은 `flag_high` 바를 깃대 탐색에서 제외(`search_end = flag_high_idx`)하므로, 최고 고가가 마지막 바(아직 깃발 미형성)면 `flag_len < min_flag_days` → `flag_too_short`로 자연 처리된다. `status` 분기의 `last_close < flag_low`는 `flag_low`가 깃발 구간 최저 저점이므로 종가가 그 아래로 마감한 붕괴를 잡는다.
