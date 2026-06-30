# find-power-play 검출기 재설계 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `evaluate_power_play`를 미너비니 정의("피벗=최근 가장 타이트한 깃발 천장")에 맞춰 재설계해, 책 예시 4/5(케이엠더블유·화인베스틸·BBY 검출, 다우데이타 미검출; 티앤엘은 알려진 한계 xfail)를 잡게 한다.

**Architecture:** 인터페이스(반환 키 집합·CLI 골격) 유지한 채 내부 로직 교체. `find_flagpole`에 `flag_window`(최근 깃발 한정 피벗 탐색) 추가, 깃대 90%/14주, 하드게이트 3개(깃대 gain·깃발 깊이·깃발 길이)로 축소하고 조용·깃대거래량·dryup은 보고용 소프트로 강등. 5개 책 예시를 FDR 스냅샷 픽스처로 회귀.

**Tech Stack:** Python 3 표준 라이브러리(검출기). 픽스처 생성에만 FinanceDataReader(1회, 결과 커밋). pytest.

## Global Constraints

- 정의·근거: `docs/superpowers/specs/2026-06-30-find-power-play-redesign-design.md`.
- **인터페이스 유지**: `evaluate_power_play(series, params)->dict` 반환 키 집합 불변, CLI 골격 불변(호출부 무변경).
- **하드 게이트 3개**: (1) `flagpole_gain_pct ≥ min_flagpole_gain`(90) · (2) `flag_depth_pct ≤ max_flag_depth`(20) · (3) `min_flag_days(8) ≤ flag_length_days ≤ max_flag_days(30)`. 그 외(조용·깃대거래량·dryup·tightness)는 **계산·출력하되 게이트 아님**.
- **reason 가능값**: `no_data / no_series / base_too_short / pole_gain_too_small / flag_too_short / flag_too_long / flag_too_deep / eval_error:*`. (`not_quiet_before_pole`·`pole_volume_weak`·`volume_not_drying` **삭제**)
- **피벗 = 최근 `flag_window`(45) 안의, 그 뒤로 `min_flag_pullback`(3)% 이상 눌린 가장 높은 고점**. `flag_window=None`이면 기존 동작(전체 구간) — Task 1 하위호환.
- **기본값**: `min_flagpole_gain 90`, `max_flagpole_days 70`, `flag_window 45` 신규. 나머지 기본 유지.
- 표준 라이브러리만(검출기). 공유 파일 무접촉·자동 commit 안 함.
- 검증: 5개 책 예시는 **피벗±윈도 스캔**(검출일이 윈도 내 1일이라도 있으면 OK). 티앤엘은 **xfail**(중첩 깃발, spec §9 후속).

---

## File Structure

| 파일 | 책임 |
|---|---|
| `scripts/canslim_lib/power_play.py` (수정) | `DEFAULT_PARAMS` 신규값 + `find_flagpole`에 `flag_window` + `evaluate_power_play` 게이트 재설계 |
| `tests/test_power_play.py` (수정) | 삭제 reason 테스트 제거, 기본값·게이트 변경 반영 |
| `scripts/screen_power_play.py` (수정) | `--flag-window` 등 인자·기본값 갱신 |
| `scripts/screen_power_play_history.py` (수정) | `--flag-window` 인자 추가(같은 검출기) |
| `scripts/_gen_pp_example_fixtures.py` (생성) | FDR로 5개 예시 OHLCV 1회 받아 스냅샷 JSON 생성(커밋용) |
| `tests/fixtures/power_play_examples.json` (생성, 커밋) | 5개 예시 스냅샷 |
| `tests/test_power_play_examples.py` (생성) | 5개 책 예시 회귀(피벗±윈도 스캔, 티앤엘 xfail) |
| `.claude/skills/find-power-play/SKILL.md` (수정) | 조건 문구 동기화 |

---

## Task 1: `find_flagpole`에 `flag_window` + `DEFAULT_PARAMS` 신규값

**Files:**
- Modify: `scripts/canslim_lib/power_play.py`
- Test: `tests/test_power_play.py`

**Interfaces:**
- Produces: `find_flagpole(highs, lows, max_flagpole_days, min_flag_pullback=None, flag_window=None) -> dict` (반환 키 동일). `flag_window`가 정수면 피벗 후보 탐색을 최근 `flag_window`개로 한정; `None`이면 기존 전체구간(하위호환). `DEFAULT_PARAMS`에 `flag_window:45`, `min_flagpole_gain:90.0`, `max_flagpole_days:70`.

- [ ] **Step 1: Write the failing tests**

`tests/test_power_play.py`의 `test_default_params_has_required_keys`를 아래로 교체(기존 함수 본문 수정), 그리고 새 테스트 추가:
```python
def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_flagpole_gain", "max_flagpole_days",
              "pole_vol_mult", "quiet_window", "max_pre_pole_gain",
              "min_flag_days", "max_flag_days", "max_flag_depth",
              "breakout_vol_mult", "near_pivot_pct", "min_total_days",
              "min_flag_pullback", "flag_window"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_flagpole_gain"] == 90.0
    assert DEFAULT_PARAMS["max_flagpole_days"] == 70
    assert DEFAULT_PARAMS["flag_window"] == 45


def test_find_flagpole_flag_window_restricts_pivot_to_recent():
    # 옛 고점(인덱스1=200)과 최근 깃발 천장(인덱스 12=110)이 공존.
    # flag_window=8 이면 최근 8봉만 보므로 피벗은 옛 200이 아니라 최근 110.
    highs = [50, 200, 60, 55, 58, 57, 59, 58, 100, 110, 104, 102, 101, 103]
    lows  = [48, 150, 58, 53, 56, 55, 57, 56,  98, 108, 100,  99,  98, 100]
    fp = find_flagpole(highs, lows, max_flagpole_days=70, min_flag_pullback=3.0, flag_window=6)
    assert fp["flag_high"] == 110          # 최근 창의 깃발 천장
    # flag_window=None(하위호환)이면 전체 최고가(200)
    fp_all = find_flagpole(highs, lows, max_flagpole_days=70, min_flag_pullback=3.0)
    assert fp_all["flag_high"] == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_power_play.py::test_default_params_has_required_keys tests/test_power_play.py::test_find_flagpole_flag_window_restricts_pivot_to_recent -v`
Expected: FAIL — `flag_window` 키 없음 / `find_flagpole()`가 `flag_window` 인자 모름(TypeError).

- [ ] **Step 3: Write minimal implementation**

`scripts/canslim_lib/power_play.py`의 `DEFAULT_PARAMS` 값 3개 수정:
```python
    "min_flagpole_gain": 90.0,
    "max_flagpole_days": 70,
```
그리고 `DEFAULT_PARAMS` 딕셔너리에 `"flag_window": 45,` 추가(예: `min_flag_pullback` 줄 다음).

`find_flagpole` 시그니처·피벗 탐색을 교체:
```python
def find_flagpole(highs: list[float], lows: list[float], max_flagpole_days: int,
                  min_flag_pullback: float | None = None,
                  flag_window: int | None = None) -> dict:
    """깃발 천장(피벗)과 그 직전 max_flagpole_days 경계 안의 최저 저점(깃대 시작)을
    찾아 상승률·기간을 계산한다.

    flag_window 가 주어지면 피벗 후보 탐색을 최근 flag_window 개 봉으로 한정한다
    (미너비니: 피벗=최근 가장 타이트한 깃발 천장 → 무관한 옛 고점 배제). None 이면
    전체 구간(하위호환). min_flag_pullback 가 주어지면 '그 뒤로 그만큼(%) 이상 눌린'
    고점만 후보(돌파 봉이 피벗을 가로채지 않음).
    """
    if not highs or not lows:
        return {"flag_high_idx": 0, "flag_high": 0.0,
                "pole_start_idx": 0, "pole_start_low": 0.0,
                "flagpole_gain_pct": 0.0, "flagpole_days": 0}
    n = len(highs)
    lo = max(0, n - flag_window) if flag_window is not None else 0
    if min_flag_pullback is None:
        flag_high_idx = max(range(lo, n), key=lambda i: highs[i])
    else:
        pb = min_flag_pullback / 100.0
        cand = [i for i in range(lo, n - 1)
                if min(lows[i + 1:]) <= highs[i] * (1 - pb)]
        flag_high_idx = (max(cand, key=lambda i: highs[i]) if cand
                         else max(range(lo, n), key=lambda i: highs[i]))
    flag_high = highs[flag_high_idx]
    window_start = max(0, flag_high_idx - max_flagpole_days)
    search_end = flag_high_idx
    if search_end <= window_start:
        return {"flag_high_idx": flag_high_idx, "flag_high": flag_high,
                "pole_start_idx": flag_high_idx, "pole_start_low": flag_high,  # sentinel: no valid pole start
                "flagpole_gain_pct": 0.0, "flagpole_days": 0}
    pole_start_idx = min(range(window_start, search_end), key=lambda i: lows[i])
    pole_start_low = lows[pole_start_idx]
    gain = (flag_high - pole_start_low) / pole_start_low * 100.0 if pole_start_low > 0 else 0.0
    return {"flag_high_idx": flag_high_idx, "flag_high": flag_high,
            "pole_start_idx": pole_start_idx, "pole_start_low": pole_start_low,
            "flagpole_gain_pct": gain, "flagpole_days": flag_high_idx - pole_start_idx}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: 신규 2테스트 PASS. 기존 `find_flagpole` 테스트(3·4-인자 호출, `flag_window` 미지정)는 **하위호환으로 그대로 PASS**해야 한다. (단, `evaluate_power_play` 관련 일부 기존 테스트는 Task 2에서 손볼 때까지 실패할 수 있음 — Task 1에서는 `find_flagpole`·`DEFAULT_PARAMS` 테스트만 확인하고, evaluate 테스트가 깨지면 Task 2에서 정리한다. Task 1 커밋 전 `pytest -k "find_flagpole or default_params"`로 해당군만 green 확인.)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/power_play.py tests/test_power_play.py
git commit -m "feat(pp-redesign): find_flagpole flag_window(최근 깃발 한정) + 기본값 90%/70d"
```

---

## Task 2: `evaluate_power_play` 게이트 재설계 (하드 3 / 소프트 강등)

**Files:**
- Modify: `scripts/canslim_lib/power_play.py`
- Test: `tests/test_power_play.py`

**Interfaces:**
- Consumes: Task 1의 `find_flagpole(..., flag_window=)`, `DEFAULT_PARAMS`.
- Produces: 재설계된 `evaluate_power_play`. 반환 키 집합 불변. `pattern_detected`는 **하드게이트 3개**(gain/depth/length)로만 결정. `pre_pole_gain_pct`·`flagpole_vol_ratio`·`volume_dryup_ratio`·`tightness_pct`는 **계산·출력하되 게이트 아님**. reason에서 not_quiet/pole_volume_weak/volume_not_drying 삭제.

- [ ] **Step 1: Write the failing test**

`tests/test_power_play.py`에서 — (a) 아래 3개 테스트를 **삭제**(게이트가 사라진 reason을 검증하므로): `test_evaluate_rejects_weak_pole_volume`, `test_evaluate_rejects_not_quiet_before_pole`, `test_evaluate_rejects_volume_not_drying`. (b) 다음 테스트를 **추가**:
```python
def test_evaluate_gates_are_three_hard_only():
    # 깃대 거래량 약하고(소프트) 조용출발 큰(소프트) 시계열이라도, 하드 3개
    # (깃대≥90·깊이≤20·길이 8~30)만 충족하면 detected=True 여야 한다.
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 58, 66, 75, 85, 95, 104, 110]              # +120%
    flag = [108, 106, 105, 104, 103, 105, 106, 107, 106, 105]
    closes = quiet + pole + flag
    # 거래량을 '안 마르게'(돌파 전에도 높게) + 깃대 거래량도 약하게 만들어도 detected.
    vols = [3000] * 20 + [3000] * 8 + [3000] * 10
    s = _series(closes, vols=vols)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is True
    assert r["reason"] is None
    # 소프트 신호는 출력되지만 게이트 아님
    assert "volume_dryup_ratio" in r and "pre_pole_gain_pct" in r and "flagpole_vol_ratio" in r


def test_evaluate_reason_set_has_no_removed_gates():
    # 어떤 입력이든 삭제된 reason 은 절대 안 나온다(여러 합성 입력 스모크).
    removed = {"not_quiet_before_pole", "pole_volume_weak", "volume_not_drying"}
    for closes in ([100, 101, 99, 102, 100],                     # 너무 짧음
                   _clean_htf()["closes"],                        # 깔끔 HTF
                   [50 + (i % 2) for i in range(20)] + [52, 55, 58, 60, 62, 63, 64, 65] + [64, 63, 62, 63, 64, 63, 62, 63]):  # 약한 깃대
        r = evaluate_power_play(_series(closes))
        assert r["reason"] not in removed
```
(`_series`·`_clean_htf` 헬퍼는 기존 파일에 있음.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_power_play.py::test_evaluate_gates_are_three_hard_only tests/test_power_play.py::test_evaluate_reason_set_has_no_removed_gates -v`
Expected: FAIL — 현재 코드는 cond_pole_vol/cond_quiet/cond_dryup 게이트가 살아 있어 `test_evaluate_gates_are_three_hard_only`가 (거래량 안 마름 → volume_not_drying 또는 약한 깃대거래량 → pole_volume_weak로) detected=False 가 되거나, reason에 삭제대상이 남는다.

- [ ] **Step 3: Write minimal implementation**

`scripts/canslim_lib/power_play.py`의 `evaluate_power_play`에서:

(a) `find_flagpole` 호출에 `flag_window` 전달:
```python
    fp = find_flagpole(highs, lows, p["max_flagpole_days"], p["min_flag_pullback"], p["flag_window"])
```

(b) "조용한 출발" 블록에서 `cond_quiet` 제거(`pre_pole_gain_pct` 계산은 보고용으로 유지):
```python
    # --- 조용한 출발(보고용 소프트 신호 — 게이트 아님): 조용한 베이스 구간 변동폭 ---
    if quiet_highs and quiet_lows and min(quiet_lows) > 0:
        pre_gain = (max(quiet_highs) - min(quiet_lows)) / min(quiet_lows) * 100.0
        base["pre_pole_gain_pct"] = round(pre_gain, 2)
```
(else 분기 삭제 — cond_quiet 더는 없음. `flagpole_vol_ratio`·`volume_dryup_ratio`·
`tightness_pct` 계산 블록은 그대로 두되 보고용임.)

(c) 판정 블록을 하드 3게이트로 교체(cond_pole_vol·cond_quiet·cond_dryup 및 해당
reason 분기 삭제):
```python
    # --- 하드 게이트 3개 판정 (조용·깃대거래량·dryup 는 소프트, 게이트 아님) ---
    cond_gain = fp["flagpole_gain_pct"] >= p["min_flagpole_gain"]
    cond_flag_min = flag_len >= p["min_flag_days"]
    cond_flag_max = flag_len <= p["max_flag_days"]
    cond_flag_depth = flag_depth <= p["max_flag_depth"]

    if not cond_gain:
        base["reason"] = "pole_gain_too_small"
    elif not cond_flag_min:
        base["reason"] = "flag_too_short"
    elif not cond_flag_max:
        base["reason"] = "flag_too_long"
    elif not cond_flag_depth:
        base["reason"] = "flag_too_deep"
    else:
        base["pattern_detected"] = True
```
(d) 피벗·상태(`status`)·`entry_ready` 블록은 **그대로 유지**(변경 없음).

- [ ] **Step 4: Run full file to verify**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: 전체 PASS. 기존 테스트 중 결과가 바뀌는 것이 있으면(예: `test_evaluate_detects_clean_htf`가 소프트화로 여전히 detected여야 함) 합성 픽스처가 아니라 **기대값을 새 게이트에 맞게** 점검. 단 하드 3게이트의 *의도*는 spec이며 로직은 바꾸지 않는다. `test_evaluate_rejects_weak_flagpole_gain`(약한 깃대 +30%<90 → pole_gain_too_small), `test_evaluate_rejects_deep_flag`, `test_evaluate_rejects_too_long_flag`, `test_evaluate_rejects_short_flag`, 상태 테스트들은 그대로 통과해야 한다. 통과 못 하면 반환 dict를 출력해 실제 reason/status를 확인하고 픽스처 숫자만 조정(사유 기록).

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/power_play.py tests/test_power_play.py
git commit -m "feat(pp-redesign): evaluate 하드게이트 3개 + 조용·깃대거래량·dryup 소프트 강등"
```

---

## Task 3: CLI `--flag-window` 노출 (screen_power_play / history)

**Files:**
- Modify: `scripts/screen_power_play.py`
- Modify: `scripts/screen_power_play_history.py`

**Interfaces:**
- Consumes: `DEFAULT_PARAMS`(flag_window 포함).
- Produces: 두 CLI 모두 `--flag-window` 인자 노출 + `params` 딕셔너리에 `flag_window` 포함. 기본값은 `DEFAULT_PARAMS`에서.

- [ ] **Step 1: 구현** (I/O 스크립트 — 스모크로 검증)

`scripts/screen_power_play.py`:
- argparse에 추가(다른 `--max-pre-pole-gain` 줄 근처):
```python
    ap.add_argument("--flag-window", type=int, default=DEFAULT_PARAMS["flag_window"])
```
- `run()`의 `params` 딕셔너리에 추가:
```python
        "flag_window": args.flag_window,
```

`scripts/screen_power_play_history.py`:
- argparse에 동일하게 `--flag-window` 추가:
```python
    ap.add_argument("--flag-window", type=int, default=DEFAULT_PARAMS["flag_window"])
```
- `run()`의 `params` 딕셔너리에 `"flag_window": args.flag_window,` 추가.

- [ ] **Step 2: 스모크 import + 단일 종목**

Run: `python -c "import sys; sys.path.insert(0,'scripts'); import screen_power_play, screen_power_play_history; print('ok')"`
Expected: `ok`.
Run: `python scripts/screen_power_play.py --ticker 005930 --flag-window 45`
Expected: `[파워플레이 요약]` 출력, exit 0, 저장 안 함.

- [ ] **Step 3: Commit**

```bash
git add scripts/screen_power_play.py scripts/screen_power_play_history.py
git commit -m "feat(pp-redesign): CLI --flag-window 노출(screen_power_play/history)"
```

---

## Task 4: 책 예시 스냅샷 픽스처 + 회귀 테스트

**Files:**
- Create: `scripts/_gen_pp_example_fixtures.py`
- Create: `tests/fixtures/power_play_examples.json` (스크립트 산출, 커밋)
- Create: `tests/test_power_play_examples.py`

**Interfaces:**
- Consumes: `evaluate_power_play`.
- Produces: 5개 책 예시 회귀(피벗±윈도 스캔). 케이엠/화인/BBY 검출, 다우 미검출, 티앤엘 xfail.

- [ ] **Step 1: 픽스처 생성 스크립트 작성 후 1회 실행(FDR 네트워크)**

`scripts/_gen_pp_example_fixtures.py`:
```python
# scripts/_gen_pp_example_fixtures.py
"""책 파워플레이 예시 5종의 OHLCV를 FDR로 1회 받아 스냅샷 픽스처로 저장.
산출 tests/fixtures/power_play_examples.json 은 커밋되어 테스트가 네트워크 없이 돈다.
재생성: python scripts/_gen_pp_example_fixtures.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import FinanceDataReader as fdr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "power_play_examples.json"

# (이름, 코드, fetch시작, fetch끝, 피벗(저자), 기대검출, 비고)
CASES = [
    ("케이엠더블유", "032500", "2018-12-01", "2019-07-20", "2019-07-10", True, ""),
    ("화인베스틸", "133820", "2019-11-01", "2020-06-05", "2020-05-25", True, ""),
    ("티앤엘", "340570", "2021-01-04", "2021-06-25", "2021-06-16", False, "xfail:중첩깃발 후속"),
    ("다우데이타", "032190", "2019-08-01", "2020-05-15", "2020-05-07", False, "폴시작형 의도적 미검출"),
    ("BBY", "BBY", "1997-05-01", "1997-12-15", "1997-12-01", True, "분할조정"),
]


def main():
    stocks = []
    for name, code, s, e, pivot, expect, note in CASES:
        df = fdr.DataReader(code, s, e)
        dates = [d.strftime("%Y-%m-%d") for d in df.index]
        pv = pivot if pivot in dates else next(d for d in dates if d >= pivot)
        stocks.append({
            "name": name, "code": code, "pivot_date": pv,
            "expect_detected": expect, "note": note,
            "series": {
                "dates": dates,
                "closes": [round(float(x), 3) for x in df["Close"].tolist()],
                "highs": [round(float(x), 3) for x in df["High"].tolist()],
                "lows": [round(float(x), 3) for x in df["Low"].tolist()],
                "volumes": [int(x) for x in df["Volume"].tolist()],
            },
        })
        print(f"  {name} {code}: {len(dates)}봉, 피벗 {pv}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"cases": stocks}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"💾 저장: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
```

Run: `python scripts/_gen_pp_example_fixtures.py`
Expected: 5종 봉수 출력 + `💾 저장: tests\fixtures\power_play_examples.json`. (FDR 네트워크 필요. 실패 시 재시도. BBY가 안 받아지면 보고.)

- [ ] **Step 2: 회귀 테스트 작성**

`tests/test_power_play_examples.py`:
```python
# tests/test_power_play_examples.py
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib.power_play import evaluate_power_play  # noqa: E402

FIX = json.loads((Path(__file__).resolve().parents[1] / "tests" / "fixtures"
                  / "power_play_examples.json").read_text(encoding="utf-8"))
CASES = {c["code"]: c for c in FIX["cases"]}


def _detect_in_window(case, before=7, after=3):
    """피벗 −before ~ +after 거래일 중 pattern_detected=True 인 날이 있으면 (날짜, 결과) 반환."""
    s = case["series"]
    dates = s["dates"]
    ip = dates.index(case["pivot_date"])
    for i in range(max(0, ip - before), min(len(dates), ip + after + 1)):
        sub = {k: v[: i + 1] for k, v in s.items()}
        r = evaluate_power_play(sub)
        if r["pattern_detected"]:
            return dates[i], r
    return None, None


@pytest.mark.parametrize("code", ["032500", "133820", "BBY"])
def test_book_examples_detected_near_pivot(code):
    case = CASES[code]
    day, r = _detect_in_window(case)
    assert day is not None, f"{case['name']}: 피벗 윈도 내 미검출"
    assert r["status"] in ("actionable", "breakout")
    # 피벗이 실제 깃발 천장 근방(현재가가 피벗 ±15% 안)
    assert -15 <= (r["pct_to_pivot"] or 0) <= 15


def test_dauda_pole_start_type_not_detected():
    # 다우데이타: 폴 시작형 → 윈도 내 미검출이 정상
    day, _ = _detect_in_window(CASES["032190"])
    assert day is None


@pytest.mark.xfail(reason="티앤엘 중첩 깃발(최종 타이트 수축 미식별) — spec §9 후속", strict=False)
def test_tnl_nested_flag_detected():
    day, _ = _detect_in_window(CASES["340570"])
    assert day is not None
```

- [ ] **Step 3: 실행해 통과 확인**

Run: `python -m pytest tests/test_power_play_examples.py -v`
Expected: `test_book_examples_detected_near_pivot[032500/133820/BBY]` PASS, `test_dauda_...` PASS, `test_tnl_...` **XFAIL**(기대된 실패). 만약 케이엠/화인/BBY가 미검출이면 검출기 로직(Task 1·2)을 점검(spec §8 — 임계값 땜질 금지). 프로토타입에서 4/5는 검증됨 — 어긋나면 구현이 프로토타입과 다른 것이니 대조.

- [ ] **Step 4: Commit**

```bash
git add scripts/_gen_pp_example_fixtures.py tests/fixtures/power_play_examples.json tests/test_power_play_examples.py
git commit -m "test(pp-redesign): 책 예시 5종 스냅샷 회귀(4/5 + 티앤엘 xfail)"
```

---

## Task 5: SKILL.md 동기화 + 풀런 점검

**Files:**
- Modify: `.claude/skills/find-power-play/SKILL.md`

- [ ] **Step 1: SKILL.md 문구 동기화**

`.claude/skills/find-power-play/SKILL.md`를 읽고, 옵션·결과 설명을 재설계에 맞춰 수정:
- 옵션에 `--flag-window 45`(피벗=최근 깃발 천장 탐색 창) 추가, `--min-flagpole-gain 90`·`--max-flagpole-days 70`로 기본값 갱신.
- "안 하는 것"/설명에서 조용·깃대거래량·dryup이 **보고용(게이트 아님)** 임을 명시, 하드게이트는 깃대 90%·깃발 깊이·깃발 길이 3개임을 명시.
- 깃대 "8주 내 100%" 문구 → "14주 내 90%(미너비니 본인 예시 BBY는 13주/135%)"로 정정.
- (있다면) reason 목록에서 not_quiet_before_pole·pole_volume_weak·volume_not_drying 제거.

- [ ] **Step 2: 실데이터 풀런 점검**

Run: `python scripts/screen_power_play.py`
Expected: `💾 저장` + `[파워플레이 요약]` 출력. 재설계로 **검출 수가 0에서 증가**하는지 확인(타이트 깃발+90% 깃대 종목). 오류 없이 종료. 늘어난 종목 수·entry_ready 수를 보고(환각 없이 콘솔 그대로).

- [ ] **Step 3: 전체 테스트 회귀**

Run: `python -m pytest tests/test_power_play.py tests/test_power_play_examples.py -v`
Expected: 전부 PASS(티앤엘만 XFAIL).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/find-power-play/SKILL.md public/data/sepa-power-play-candidates.json
git commit -m "docs(pp-redesign): SKILL 동기화 + 재설계 풀런 산출"
```
(산출 JSON 커밋 부담되면 SKILL.md만.)

---

## Self-Review

**1. Spec coverage:**
- §4.2 피벗=최근 flag_window → Task 1(find_flagpole flag_window).
- §4.3 깃대 90%/70d → Task 1(기본값) + Task 2(호출 시 flag_window 전달).
- §4.4·4.5 하드 3게이트·소프트 강등·reason 삭제 → Task 2.
- §4.6 status/entry_ready 유지 → Task 2(d, 변경 없음 명시).
- §5 출력 키 유지·params에 flag_window → Task 2·Task 3.
- §6 CLI --flag-window → Task 3.
- §8 5예시 회귀(스냅샷·윈도 스캔·티앤엘 xfail) → Task 4.
- §7 인터페이스 유지·SKILL 동기화 → Task 3(호출부 무변경)·Task 5.
- §9 후속(티앤엘 중첩깃발) → Task 4 xfail로 추적.

**2. Placeholder scan:** 모든 코드 스텝 실제 코드 포함. "적절히" 류 없음.

**3. Type consistency:** `find_flagpole`의 5번째 인자 `flag_window`를 Task 2 호출이 그대로 사용. `DEFAULT_PARAMS["flag_window"]`를 Task 2(evaluate)·Task 3(CLI 둘 다)·Task 4 무관. 삭제 reason(not_quiet/pole_volume_weak/volume_not_drying)을 Task 2가 제거하고 Task 2 테스트(`test_evaluate_reason_set_has_no_removed_gates`)가 검증. 반환 키 집합은 불변(소프트 신호 키도 계속 출력).

**참고(엣지):** `find_flagpole`의 cand 리스트는 `range(lo, n-1)`라 `flag_window`가 작아 `lo>=n-1`이면 빈 리스트 → 폴백 `max(range(lo,n))`. `flag_window=None`(하위호환)이면 `lo=0`로 기존과 완전히 동일. 프로토타입에서 케이엠 깃대가 303%(70일 창이 깊은 저점 포착)로 과대평가되나 검출은 정상 — spec §9 looseness 후속.
