# find-power-play 중첩 깃발(최종 타이트 수축) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `evaluate_power_play`의 피벗 선택을 "최근 가장 타이트한 수축의 천장"(`find_pivot_contraction`)으로 교체해, 넓은 베이스 안에 중첩된 최종 타이트 깃발(티앤엘)을 잡는다.

**Architecture:** 신규 순수 함수 `find_pivot_contraction`가 최근 타이트 수축 창을 찾아 그 안의 '뒤에 눌림 확인된 가장 높은 고점'을 피벗 인덱스로 반환. `evaluate_power_play`가 `find_flagpole` 대신 이를 호출(깃대 저점은 인라인 계산). 깃대 90%/14주·하드게이트 3개·status·반환 키는 유지. 5개 책 예시 회귀 갱신(티앤엘 gain 78 검출, 다우 xfail) + 합성 음성 가드.

**Tech Stack:** Python 3 표준 라이브러리(검출기). pytest. 회귀 픽스처는 기존 `tests/fixtures/power_play_examples.json`(FDR 스냅샷) 재사용.

## Global Constraints

- 정의·근거: `docs/superpowers/specs/2026-06-30-find-power-play-nested-flag-design.md`.
- **인터페이스 유지**: `evaluate_power_play(series, params)->dict` 반환 키 집합 불변, CLI 골격·다운스트림(history) 무변경.
- **피벗 = 최근 타이트 수축 천장**: `find_pivot_contraction`이 담당. 하드 게이트 3개(깃대 gain≥90·깃발 깊이≤20·깃발 길이 8~30)·소프트 신호·status는 선행 redesign과 동일.
- **기본 깃대 게이트 90% 유지**(완화 안 함). 티앤엘은 `--min-flagpole-gain 78`에서만 검출.
- **reason**: `no_contraction` 추가. 나머지(`no_data/no_series/base_too_short/pole_gain_too_small/flag_too_short/flag_too_long/flag_too_deep/eval_error:*`) 유지.
- **파라미터**: `tight_pct`(18)·`contraction_grace`(3) 추가, `flag_window`(및 `--flag-window`) 제거. `find_flagpole` 함수·기존 단위테스트는 **남긴다**(spec §4, 참조용; evaluate에선 더는 호출 안 함).
- 표준 라이브러리만(검출기). 공유 파일 무접촉·자동 commit 안 함.
- **다우데이타 거짓양성은 정직히 xfail**로 드러낸다(숨기지 않음). 합성 음성 테스트가 진짜 음성 가드.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `scripts/canslim_lib/power_play.py` (수정) | `find_pivot_contraction` 신규 + `DEFAULT_PARAMS`(tight_pct·contraction_grace 추가, flag_window 제거) + `evaluate_power_play` 피벗 교체 |
| `tests/test_power_play.py` (수정) | `find_pivot_contraction` 단위테스트 + default_params 갱신 + evaluate 테스트 점검 |
| `scripts/screen_power_play.py` (수정) | `--flag-window` 제거 → `--tight-pct`·`--contraction-grace` |
| `scripts/screen_power_play_history.py` (수정) | 동일 CLI 인자 갱신 |
| `tests/test_power_play_examples.py` (수정) | 티앤엘 gain78 검출·다우 xfail·합성 음성 |
| `.claude/skills/find-power-play/SKILL.md` (수정) | 문구 동기화 |

---

## Task 1: `find_pivot_contraction` + 파라미터 추가 (순수 추가)

이 태스크는 **순수 추가**(새 함수 + 새 파라미터)라 `evaluate_power_play`를 안 건드리고 기존 테스트는 그대로 통과한다.

**Files:**
- Modify: `scripts/canslim_lib/power_play.py`
- Test: `tests/test_power_play.py`

**Interfaces:**
- Produces: `find_pivot_contraction(highs, lows, min_len, max_len, tight_pct, grace, pb_pct) -> int | None` — 최근 타이트 수축 창의 '뒤에 pb_pct% 이상 눌린 가장 높은 고점' 인덱스(피벗). 수축 없으면 `None`. `DEFAULT_PARAMS`에 `tight_pct:18.0`, `contraction_grace:3` 추가, `flag_window` 키 제거.

- [ ] **Step 1: Write the failing tests**

`tests/test_power_play.py`에 추가, 그리고 `test_default_params_has_required_keys`를 교체:
```python
from canslim_lib.power_play import find_pivot_contraction  # (상단 import에 합쳐도 됨)


def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_flagpole_gain", "max_flagpole_days",
              "min_flag_days", "max_flag_days", "max_flag_depth",
              "breakout_vol_mult", "near_pivot_pct", "min_total_days",
              "min_flag_pullback", "tight_pct", "contraction_grace"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_flagpole_gain"] == 90.0
    assert DEFAULT_PARAMS["max_flagpole_days"] == 70
    assert DEFAULT_PARAMS["tight_pct"] == 18.0
    assert DEFAULT_PARAMS["contraction_grace"] == 3
    assert "flag_window" not in DEFAULT_PARAMS


def test_find_pivot_contraction_picks_final_tight_over_wide_base():
    # 앞부분 넓은 변동(고가 130까지) + 뒤 10봉 타이트 수축(고가 108, 범위 ~9%).
    # 피벗은 옛 넓은 천장(130/125)이 아니라 최종 타이트 수축 천장(108)이어야 한다.
    highs = [120, 130, 110, 125, 108, 108, 107, 108, 106, 108, 107, 108, 106, 107, 103]
    lows  = [100, 108,  98, 103,  99, 100, 101, 102, 100, 101, 102, 100, 101, 102,  99]
    fhi = find_pivot_contraction(highs, lows, min_len=8, max_len=30,
                                 tight_pct=18.0, grace=3, pb_pct=3.0)
    assert fhi is not None
    assert highs[fhi] == 108            # 타이트 수축 천장
    assert highs[fhi] not in (130, 125)  # 옛 넓은 천장 아님


def test_find_pivot_contraction_none_when_no_tight_window():
    # 계속 큰 폭으로 출렁여 어떤 최근 창도 타이트(≤tight_pct)하지 않음 → None
    highs = [100, 130, 105, 135, 108, 140, 110, 145, 112, 150, 115, 155]
    lows  = [80, 100,  82, 102,  84, 104,  86, 106,  88, 108,  90, 110]
    fhi = find_pivot_contraction(highs, lows, min_len=8, max_len=30,
                                 tight_pct=8.0, grace=3, pb_pct=3.0)
    assert fhi is None


def test_find_pivot_contraction_excludes_fresh_breakout_bar():
    # 타이트 수축(고가 110) 뒤 마지막 봉이 신고가 130로 돌파.
    # 피벗은 돌파봉(130, 뒤에 눌림 없음)이 아니라 수축 천장(110)이어야 한다.
    highs = [108, 110, 107, 109, 108, 110, 106, 109, 108, 110, 130]
    lows  = [100, 101,  99, 100,  98, 101,  97, 100,  99, 101, 125]
    fhi = find_pivot_contraction(highs, lows, min_len=8, max_len=30,
                                 tight_pct=18.0, grace=3, pb_pct=3.0)
    assert fhi is not None
    assert highs[fhi] == 110        # 신고가 130 아님
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_power_play.py -k "find_pivot_contraction or default_params" -v`
Expected: FAIL — `ImportError: cannot import name 'find_pivot_contraction'` / `flag_window` 단언 등.

- [ ] **Step 3: Write minimal implementation**

`scripts/canslim_lib/power_play.py`의 `DEFAULT_PARAMS`에서 `"flag_window": 45,` 줄을 삭제하고, 대신 추가:
```python
    "tight_pct": 18.0,
    "contraction_grace": 3,
```

그리고 `find_pivot_contraction`를 추가(예: `_mean` 정의 앞):
```python
def find_pivot_contraction(highs: list[float], lows: list[float], min_len: int,
                           max_len: int, tight_pct: float, grace: int,
                           pb_pct: float) -> int | None:
    """가장 최근의 '타이트 수축'(변동폭 ≤ tight_pct%) 창을 찾아, 그 안에서
    '뒤에 pb_pct% 이상 눌린 가장 높은 고점'(=저항/피벗; 돌파 봉 아님)의 인덱스를
    반환한다. 돌파 봉 grace개는 창 끝에서 제외(돌파 직전 수축을 잡기 위함).
    어떤 창도 못 찾으면 None. (미너비니: 피벗=최종 가장 타이트한 수축의 천장.)
    """
    if not highs or not lows:
        return None
    n = len(highs)
    pb = pb_pct / 100.0
    lo_end = max(min_len - 1, n - 1 - grace)
    for end in range(n - 1, lo_end - 1, -1):
        best = None
        for L in range(min_len, max_len + 1):
            st = end - L + 1
            if st < 0:
                break
            lo = min(lows[st:end + 1]); hi = max(highs[st:end + 1])
            if lo <= 0:
                continue
            rng = (hi - lo) / lo * 100.0
            if rng <= tight_pct:
                best = (st, end)        # 타이트 유지되는 한 더 길게
            else:
                break
        if best:
            st, e = best
            cand = [i for i in range(st, e + 1)
                    if i < n - 1 and min(lows[i + 1:]) <= highs[i] * (1 - pb)]
            if cand:
                return max(cand, key=lambda i: highs[i])
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_power_play.py -k "find_pivot_contraction or default_params" -v`
Expected: PASS (4 tests). 합성 픽스처가 의도를 못 짚으면(예: 피벗 인덱스가 다른 동률 고점) **단언을 본질(피벗=타이트 수축 천장, 옛 넓은 천장 아님)에 맞춰** 조정하거나 픽스처 수치를 조정(사유 기록). 로직은 spec이며 바꾸지 않는다. (참고: `evaluate` 기반 기존 테스트는 아직 `flag_window` 제거로 깨질 수 있음 — Task 2에서 정리. 이 태스크 커밋 전엔 위 `-k` 부분집합만 green 확인.)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/power_play.py tests/test_power_play.py
git commit -m "feat(pp-nested): find_pivot_contraction(최종 타이트 수축) + tight_pct/contraction_grace"
```

---

## Task 2: `evaluate_power_play` 피벗을 수축 기반으로 교체

**Files:**
- Modify: `scripts/canslim_lib/power_play.py`
- Test: `tests/test_power_play.py`

**Interfaces:**
- Consumes: `find_pivot_contraction`(Task 1), `DEFAULT_PARAMS`.
- Produces: `evaluate_power_play`가 피벗을 `find_pivot_contraction`으로 잡고, 못 찾으면 `reason="no_contraction"`. 깃대 저점은 인라인 계산. 반환 키 집합 불변.

- [ ] **Step 1: Write the failing test**

`tests/test_power_play.py`에 추가:
```python
def test_evaluate_no_contraction_reason():
    # 계속 큰 폭 출렁임 → 타이트 수축 없음 → no_contraction
    closes = [100, 130, 105, 135, 108, 140, 110, 145, 112, 150, 115, 155,
              118, 160, 120, 165, 122, 170, 124, 175, 126]
    s = _series(closes)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "no_contraction"


def test_evaluate_pivot_is_final_tight_contraction():
    # 넓은 베이스(고140) 뒤에 타이트 수축(고115)이 중첩 → 피벗=115대(넓은 140 아님)
    wide = [120, 140, 110, 135, 112]
    tight = [114, 113, 115, 112, 114, 113, 115, 112, 114, 110]   # ~타이트
    closes = wide + tight
    s = _series(closes)
    r = evaluate_power_play(s)
    # 피벗이 넓은 베이스 천장(>130)이 아니라 타이트 수축대(~116=115*1.01 근방)여야 한다
    assert r["pivot_price"] is not None
    assert r["pivot_price"] < 130
```
(`_series`는 기존 헬퍼. `_series`는 highs=종가×1.01 이므로 피벗은 종가×1.01 근방.)

- [ ] **Step 2: Run tests to verify they fail / 기존 깨짐 확인**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: 신규 2테스트 FAIL(no_contraction 없음/피벗 옛 로직). 또한 `flag_window` 제거로 `evaluate`의 `find_flagpole(... p["flag_window"])` 호출이 **KeyError** 또는 기존 evaluate 테스트 실패 — 이 태스크에서 함께 정리한다.

- [ ] **Step 3: Write minimal implementation**

`scripts/canslim_lib/power_play.py`의 `evaluate_power_play`에서 `find_flagpole` 호출 블록(아래 4줄~)을 교체. 기존:
```python
    fp = find_flagpole(highs, lows, p["max_flagpole_days"], p["min_flag_pullback"], p["flag_window"])
    fhi = fp["flag_high_idx"]
    psi = fp["pole_start_idx"]
    flag_high = fp["flag_high"]
    base["flagpole_gain_pct"] = round(fp["flagpole_gain_pct"], 2)
    base["flagpole_days"] = fp["flagpole_days"]
```
교체 후:
```python
    fhi = find_pivot_contraction(highs, lows, p["min_flag_days"], p["max_flag_days"],
                                 p["tight_pct"], p["contraction_grace"], p["min_flag_pullback"])
    if fhi is None:
        base["reason"] = "no_contraction"
        return base
    flag_high = highs[fhi]
    # 깃대 저점 = 피벗 직전 max_flagpole_days 구간 최저 저점
    ws = max(0, fhi - p["max_flagpole_days"])
    if fhi <= ws:
        psi = fhi
        pole_start_low = flag_high
        flagpole_gain = 0.0
    else:
        psi = min(range(ws, fhi), key=lambda i: lows[i])
        pole_start_low = lows[psi]
        flagpole_gain = (flag_high - pole_start_low) / pole_start_low * 100.0 if pole_start_low > 0 else 0.0
    base["flagpole_gain_pct"] = round(flagpole_gain, 2)
    base["flagpole_days"] = fhi - psi
```
그리고 깃대 게이트 줄을 `fp[...]` 대신 지역변수로:
```python
    cond_gain = flagpole_gain >= p["min_flagpole_gain"]
```
(나머지 — `pole_start_date`/`flag_high_date`/`pivot_price` 설정, 깃발 지표, 소프트 신호, 나머지 게이트, status — 는 그대로. 이미 `fhi`·`psi`·`flag_high`를 쓰므로 변경 없음.)

- [ ] **Step 4: Run full file to verify**

Run: `python -m pytest tests/test_power_play.py -v`
Expected: 전체 PASS. 기존 evaluate 테스트(예 `test_evaluate_detects_clean_htf`, `test_evaluate_rejects_*`, status 테스트)는 피벗 로직이 바뀌어 결과/피벗이 달라질 수 있다 — 깨지면 반환 dict를 출력해 실제 reason/pivot을 확인하고, **하드 게이트 3개의 의도(spec)는 유지**한 채 합성 픽스처 수치만 조정(사유 기록). `_clean_htf`는 타이트한 깃발이 있으므로 여전히 detected여야 한다. (`find_flagpole`·그 단위테스트는 그대로 둔다 — 미사용이지만 spec §4대로 보존.)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/power_play.py tests/test_power_play.py
git commit -m "feat(pp-nested): evaluate 피벗을 find_pivot_contraction으로 교체 + no_contraction"
```

---

## Task 3: CLI 인자 갱신 (--flag-window 제거 → --tight-pct/--contraction-grace)

**Files:**
- Modify: `scripts/screen_power_play.py`
- Modify: `scripts/screen_power_play_history.py`

**Interfaces:**
- Consumes: `DEFAULT_PARAMS`(tight_pct·contraction_grace; flag_window 없음).

- [ ] **Step 1: 구현** (I/O 스크립트 — 스모크로 검증)

두 스크립트(`screen_power_play.py`·`screen_power_play_history.py`) 각각에서:
- argparse의 `--flag-window` 줄 **삭제**, 대신 추가:
```python
    ap.add_argument("--tight-pct", type=float, default=DEFAULT_PARAMS["tight_pct"])
    ap.add_argument("--contraction-grace", type=int, default=DEFAULT_PARAMS["contraction_grace"])
```
- `run()`의 `params` 딕셔너리에서 `"flag_window": args.flag_window,` 줄 **삭제**, 대신 추가:
```python
        "tight_pct": args.tight_pct,
        "contraction_grace": args.contraction_grace,
```

- [ ] **Step 2: 스모크 import + 단일 종목**

Run: `python -c "import sys; sys.path.insert(0,'scripts'); import screen_power_play, screen_power_play_history; print('ok')"`
Expected: `ok` (KeyError·AttributeError 없음).
Run: `python scripts/screen_power_play.py --ticker 005930 --tight-pct 18 --contraction-grace 3`
Expected: `[파워플레이 요약]` 출력, exit 0, 저장 안 함.

- [ ] **Step 3: Commit**

```bash
git add scripts/screen_power_play.py scripts/screen_power_play_history.py
git commit -m "feat(pp-nested): CLI --flag-window 제거 → --tight-pct/--contraction-grace"
```

---

## Task 4: 책 예시 회귀 갱신 (티앤엘 검출·다우 xfail·합성 음성)

**Files:**
- Modify: `tests/test_power_play_examples.py`

**Interfaces:**
- Consumes: `evaluate_power_play`, 기존 픽스처 `tests/fixtures/power_play_examples.json`.

- [ ] **Step 1: 테스트 갱신**

`tests/test_power_play_examples.py`에서:

(a) `_detect_in_window`에 `gain_min` 파라미터를 추가(티앤엘을 78로 돌리기 위함):
```python
def _detect_in_window(case, before=7, after=3, gain_min=None):
    s = case["series"]
    dates = s["dates"]
    ip = dates.index(case["pivot_date"])
    params = {"min_flagpole_gain": gain_min} if gain_min is not None else None
    for i in range(max(0, ip - before), min(len(dates), ip + after + 1)):
        sub = {k: v[: i + 1] for k, v in s.items()}
        r = evaluate_power_play(sub, params)
        if r["pattern_detected"]:
            return dates[i], r
    return None, None
```

(b) 케이엠더블유·화인베스틸·BBY 검출 테스트는 유지(기본 gain). `test_dauda_pole_start_type_not_detected`를 **xfail로 변경**(중첩 finder가 다우의 회복-폴을 잡으므로 — 미너비니상 파워플레이 아님, 알려진 거짓양성):
```python
@pytest.mark.xfail(reason="다우데이타: 회복-폴을 finder가 잡음(미너비니상 파워플레이 아님) — 알려진 거짓양성, spec §1/§8", strict=False)
def test_dauda_pole_start_type_not_detected():
    day, _ = _detect_in_window(CASES["032190"])
    assert day is None
```

(c) 티앤엘 xfail 테스트를 **gain 78에서 검출되는 실 테스트로 교체**:
```python
def test_tnl_nested_flag_detected_at_lower_gain():
    # 티앤엘: 최종 타이트 수축(피벗 ~32,600)의 깃대는 ~79% → 기본 90 미달, 78에서 검출
    day, r = _detect_in_window(CASES["340570"], gain_min=78.0)
    assert day is not None, "티앤엘: gain 78 윈도 내 미검출"
    assert -15 <= (r["pct_to_pivot"] or 0) <= 15
```
(기존 `test_tnl_nested_flag_detected`(xfail) 함수는 삭제.)

(d) 합성 음성 가드 추가(명백히 파워 플레이 아님 → 미검출 PASS):
```python
def test_synthetic_non_powerplay_rejected():
    # 평평하게 횡보만(깃대 없음) → 절대 검출되면 안 됨
    closes = [100 + (i % 3) for i in range(140)]
    s = {"dates": [f"d{i}" for i in range(140)],
         "closes": closes, "highs": [c * 1.01 for c in closes],
         "lows": [c * 0.99 for c in closes], "volumes": [1000] * 140}
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
```

- [ ] **Step 2: 실행해 통과 확인**

Run: `python -m pytest tests/test_power_play_examples.py -v`
Expected: 케이엠/화인/BBY 검출 PASS, `test_tnl_..._at_lower_gain` PASS, `test_synthetic_non_powerplay_rejected` PASS, `test_dauda_...` **XFAIL**. 만약 케이엠/화인/BBY가 미검출이면 검출기(Task 1·2) 점검(프로토타입에서 검증됨 — 어긋나면 구현이 프로토타입과 다른 것). 티앤엘이 gain78에서도 미검출이면 반환 dict 출력해 reason 확인.

- [ ] **Step 3: Commit**

```bash
git add tests/test_power_play_examples.py
git commit -m "test(pp-nested): 티앤엘 gain78 검출 + 다우 xfail(거짓양성) + 합성 음성 가드"
```

---

## Task 5: SKILL.md 동기화 + 풀런 점검

**Files:**
- Modify: `.claude/skills/find-power-play/SKILL.md`

- [ ] **Step 1: SKILL.md 문구 동기화**

`.claude/skills/find-power-play/SKILL.md`를 읽고 수정:
- 옵션에서 `--flag-window` 제거 → `--tight-pct 18`(타이트 수축 판정폭)·`--contraction-grace 3`(돌파 grace) 추가.
- 피벗 설명을 "최근 가장 타이트한 수축의 천장"으로(넓은 베이스/돌파 스파이크 아님). reason에 `no_contraction`(현재 타이트 수축 없음) 추가 언급.
- 하드 게이트 3개·소프트 신호 구분은 유지.

- [ ] **Step 2: 실데이터 풀런**

Run: `python scripts/screen_power_play.py`
Expected: `💾 저장` + `[파워플레이 요약]`. 사유 대부분 `no_contraction`(정상 — 강세주가 현재 타이트 수축 부재). 오류 없이 종료. 검출 수·entry_ready 콘솔 그대로 보고.

- [ ] **Step 3: 전체 회귀**

Run: `python -m pytest tests/test_power_play.py tests/test_power_play_examples.py tests/test_power_play_history.py -v`
Expected: 전부 PASS(다우만 XFAIL). history 테스트도 같은 검출기라 통과해야 함.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/find-power-play/SKILL.md public/data/sepa-power-play-candidates.json
git commit -m "docs(pp-nested): SKILL 동기화 + 풀런 산출"
```
(산출 JSON 커밋 부담되면 SKILL.md만.)

---

## Self-Review

**1. Spec coverage:**
- §3.1 find_pivot_contraction(타이트 창 + 뒤-눌림 피벗) → Task 1.
- §3.2 깃대 저점·게이트(gain≥90) 유지 → Task 2(인라인 폴 계산).
- §3.3 no_contraction reason → Task 2.
- §4 파라미터(tight_pct·contraction_grace 추가, flag_window 제거; find_flagpole 보존) → Task 1·2·3.
- §5 구성요소(power_play·screen×2·tests×2·SKILL) → Task 1~5.
- §6 검증(find_pivot_contraction 단위 ①②③, 5예시 회귀: 티앤엘 gain78·다우 xfail·합성 음성, 풀런) → Task 1·4·5.
- §7 인터페이스 유지·다우 정직 xfail → Global Constraints + Task 4.

**2. Placeholder scan:** "TBD/적절히" 없음. 모든 코드 스텝 실제 코드.

**3. Type consistency:** `find_pivot_contraction(highs, lows, min_len, max_len, tight_pct, grace, pb_pct) -> int|None`를 Task 2 evaluate가 그대로 호출. `DEFAULT_PARAMS` 키(tight_pct·contraction_grace)와 CLI 인자명(--tight-pct·--contraction-grace)·params 키 일치. flag_window 제거를 Task 1(DEFAULT_PARAMS)·Task 2(evaluate 호출)·Task 3(CLI) 모두 반영(순서: Task 1은 flag_window 키만 제거하되 evaluate는 Task 2에서 교체 — Task 1 직후 evaluate는 일시적으로 flag_window KeyError가 날 수 있으나 Task 1 커밋 검증은 `-k find_pivot_contraction or default_params` 부분집합만 보고, Task 2에서 evaluate 교체로 해소). 반환 키 집합 불변.

**참고(엣지):** `find_pivot_contraction`의 cand는 `range(st, e+1)`에서 `i < n-1` 조건으로 마지막 봉(돌파 봉) 제외. 수축 창을 못 찾거나 창 안에 '뒤 눌림' 고점이 없으면 None → `no_contraction`. evaluate의 `fhi <= ws`(피벗이 인덱스 0 부근) 가드로 깃대 저점 sentinel 처리. `find_flagpole`은 잔존(미사용)하지만 spec §4가 명시적으로 보존을 요구 — 최종 리뷰에서 dead-code로 보일 수 있으니 그때 사용자 판단(제거 여부)으로 둔다.
