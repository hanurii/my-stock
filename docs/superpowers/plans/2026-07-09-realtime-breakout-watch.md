# 실시간 돌파 감시 봇 "넓은 감시 모드" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자동매수 봇의 감시 목록을 "진입임박"만이 아니라 "예의주시(forming)"까지 넓혀, 전날 예의주시였던 종목이 장중에 돌파할 때도 실시간으로 포착·매수하게 한다.

**Architecture:** 실시간 폴링·매수 판정(피벗 돌파·거래량 페이스·추격 +3%·슬롯)은 기존 로직을 그대로 재사용한다. 새로 추가하는 것은 넓은 감시 목록을 만드는 순수 함수 `load_watchlist_broad` 하나이며, 관찰기(`verify_volume.py`)와 실봇(`runner.py`)에 `--broad` 옵트인 플래그로 연결한다.

**Tech Stack:** Python 3.12, pytest. 기존 `scripts/autobuy/` 모듈 구조.

## Global Constraints

- **옵트인**: `--broad` 미지정 시 기존 동작(진입임박만) 그대로. 기본 동작 불변.
- **감시 포함 조건**: `status ∈ {actionable, forming}` AND `pivot_price` 존재.
- **제외**: `status = breakout`, `status = failed`, `pivot_price` 없음, 파워플레이 전체종목 파일(`sepa-power-play-all-candidates.json` — `CANDIDATE_PATHS`에 애초에 없음).
- **중복 종목 우선순위**: `VCP > 3C > 파워플레이` 순으로 택 1 (경로 순서와 무관하게 패턴 랭크로 결정).
- **반환 형태**: `load_actionable`과 동일 — `[{code, name, pivot, pattern}]`.
- **거래량 신호 변경 없음**: 기존 `vol_curve` 동시간대 페이스 + `VOL_PACE_MIN` 그대로.
- **안전**: 실매수는 기존 dryrun 기본 + `--live` 이중게이트 유지. 관찰기는 읽기 전용.

---

## File Structure

- `scripts/autobuy/watchlist.py` — **수정**: `load_watchlist_broad` 함수 추가(`load_actionable` 옆에 병존).
- `tests/test_autobuy_watchlist.py` — **수정**: `load_watchlist_broad` 단위 테스트 추가.
- `scripts/autobuy/verify_volume.py` — **수정**: `run()`에 `broad` 파라미터 + `--broad` CLI 플래그(1단계 관찰기).
- `scripts/autobuy/runner.py` — **수정**: `--broad` CLI 플래그 + 감시목록 로더 분기(2단계 실봇).

---

## Task 1: `load_watchlist_broad` 함수 + 단위 테스트

**Files:**
- Modify: `scripts/autobuy/watchlist.py`
- Test: `tests/test_autobuy_watchlist.py`

**Interfaces:**
- Consumes: 없음(신규).
- Produces: `load_watchlist_broad(paths: list[str]) -> list[dict]` — 각 dict는 `{"code": str, "name": str, "pivot": float, "pattern": str}`. `verify_volume.py`·`runner.py`가 사용.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_autobuy_watchlist.py` 상단 import에 `load_watchlist_broad`를 추가하고(기존 import 옆), 파일 끝에 아래 테스트 추가:

```python
import json
from autobuy.watchlist import load_watchlist_broad


def _write(tmp_path, name, candidates):
    p = tmp_path / name
    p.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    return str(p)


def test_broad_includes_actionable_and_forming(tmp_path):
    vcp = _write(tmp_path, "sepa-vcp-candidates.json", [
        {"code": "A", "name": "에이", "status": "actionable", "pivot_price": 100.0},
        {"code": "B", "name": "비", "status": "forming", "pivot_price": 200.0},
    ])
    codes = {r["code"] for r in load_watchlist_broad([vcp])}
    assert codes == {"A", "B"}


def test_broad_excludes_breakout_failed_and_no_pivot(tmp_path):
    vcp = _write(tmp_path, "sepa-vcp-candidates.json", [
        {"code": "A", "name": "에이", "status": "breakout", "pivot_price": 100.0},
        {"code": "B", "name": "비", "status": "failed", "pivot_price": 200.0},
        {"code": "C", "name": "씨", "status": "forming", "pivot_price": None},
    ])
    assert load_watchlist_broad([vcp]) == []


def test_broad_dedup_priority_vcp_over_3c_over_pp(tmp_path):
    vcp = _write(tmp_path, "sepa-vcp-candidates.json", [
        {"code": "A", "name": "에이", "status": "forming", "pivot_price": 100.0}])
    c3 = _write(tmp_path, "sepa-3c-candidates.json", [
        {"code": "A", "name": "에이", "status": "actionable", "pivot_price": 111.0},
        {"code": "B", "name": "비", "status": "forming", "pivot_price": 222.0}])
    pp = _write(tmp_path, "sepa-power-play-candidates.json", [
        {"code": "B", "name": "비", "status": "forming", "pivot_price": 999.0}])
    out = {r["code"]: r for r in load_watchlist_broad([vcp, c3, pp])}
    assert out["A"]["pattern"] == "VCP" and out["A"]["pivot"] == 100.0
    assert out["B"]["pattern"] == "3C" and out["B"]["pivot"] == 222.0


def test_broad_priority_independent_of_path_order(tmp_path):
    vcp = _write(tmp_path, "sepa-vcp-candidates.json", [
        {"code": "A", "name": "에이", "status": "forming", "pivot_price": 100.0}])
    c3 = _write(tmp_path, "sepa-3c-candidates.json", [
        {"code": "A", "name": "에이", "status": "actionable", "pivot_price": 111.0}])
    # 3C를 먼저 넘겨도 VCP가 이겨야 함
    out = {r["code"]: r for r in load_watchlist_broad([c3, vcp])}
    assert out["A"]["pattern"] == "VCP"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_autobuy_watchlist.py -v`
Expected: `ImportError` 또는 `AttributeError: ... load_watchlist_broad` 로 실패.

- [ ] **Step 3: 최소 구현 작성**

`scripts/autobuy/watchlist.py`의 `load_actionable` 함수 바로 아래에 추가:

```python
_PATTERN_RANK = {"VCP": 0, "3C": 1, "PP": 2}


def load_watchlist_broad(paths):
    """넓은 감시 목록 — status in {actionable, forming} & pivot 있는 것 로드(돌파·실패 제외).
    같은 code가 여러 패턴에 있으면 VCP > 3C > 파워플레이 우선순위로 택 1(경로 순서 무관).
    반환 [{code,name,pivot,pattern}] — load_actionable과 동일 형태.

    load_actionable(진입임박만)과 달리 예의주시(forming)까지 포함해, 전날 forming이던 종목이
    장중에 돌파할 때도 실시간으로 잡을 수 있게 한다. entry_ready는 요구하지 않는다."""
    best = {}  # code -> (rank, entry)
    for p in paths:
        try:
            d = json.loads(open(p, encoding="utf-8").read())
        except Exception:
            continue
        pat = "VCP" if "vcp" in p else "3C" if "3c" in p else "PP" if "power" in p else "?"
        rank = _PATTERN_RANK.get(pat, 99)
        for c in d.get("candidates", []):
            if c.get("status") in ("actionable", "forming") and c.get("pivot_price"):
                code = c["code"]
                if code not in best or rank < best[code][0]:
                    best[code] = (rank, {"code": code, "name": c.get("name"),
                                         "pivot": float(c["pivot_price"]), "pattern": pat})
    return [entry for _, entry in best.values()]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_autobuy_watchlist.py -v`
Expected: 새 테스트 4개 + 기존 테스트 모두 PASS.

- [ ] **Step 5: 실데이터 스모크 확인**

Run:
```bash
python -c "import sys; sys.path.insert(0,'scripts'); from autobuy import watchlist as w; from autobuy.config import CANDIDATE_PATHS as P; print('broad', len(w.load_watchlist_broad(P)), '| actionable', len(w.load_actionable(P)))"
```
Expected: `broad N | actionable M` 형태로 출력되고 **N ≥ M**(넓은 목록이 진입임박보다 크거나 같음).

- [ ] **Step 6: 커밋**

```bash
git add scripts/autobuy/watchlist.py tests/test_autobuy_watchlist.py
git commit -m "feat(autobuy): load_watchlist_broad — 예의주시까지 포함한 넓은 감시 목록"
```

---

## Task 2: `--broad` 관찰기 연결 (1단계 — 읽기 전용)

**Files:**
- Modify: `scripts/autobuy/verify_volume.py`

**Interfaces:**
- Consumes: `watchlist.load_watchlist_broad(paths)` (Task 1).
- Produces: `verify_volume.run(once, slots, interval, broad)` — `broad=True`면 넓은 목록으로 관찰.

- [ ] **Step 1: `run()`에 `broad` 파라미터 추가 + 로더 분기**

`scripts/autobuy/verify_volume.py`의 `def run(once=False, slots=None, interval=0):` 를 다음으로 교체:

```python
def run(once=False, slots=None, interval=0, broad=False):
```

같은 함수 안의 감시목록 로딩 라인:
```python
    wl = watchlist.load_actionable(CANDIDATE_PATHS)
```
를 다음으로 교체:
```python
    wl = (watchlist.load_watchlist_broad(CANDIDATE_PATHS) if broad
          else watchlist.load_actionable(CANDIDATE_PATHS))
```

- [ ] **Step 2: 시작 출력에 모드 표시**

같은 함수의 시작 출력 라인:
```python
    print(f"=== 거래량 매수 검증 관찰기 · 감시 {len(wl)}종목 · 슬롯 {cfg['SLOTS']} · 국면 {note} ===")
```
를 다음으로 교체:
```python
    mode_tag = "넓은 감시(진입임박+예의주시)" if broad else "진입임박만"
    print(f"=== 거래량 매수 검증 관찰기 · {mode_tag} · 감시 {len(wl)}종목 · 슬롯 {cfg['SLOTS']} · 국면 {note} ===")
```

- [ ] **Step 3: `--broad` CLI 플래그 추가**

`main()` 함수의 argparse 블록에서 `a = ap.parse_args()` 바로 위에 추가:
```python
    ap.add_argument("--broad", action="store_true", help="예의주시까지 넓게 감시(기본: 진입임박만)")
```
그리고 마지막 호출:
```python
    run(once=a.once, slots=a.slots, interval=a.interval)
```
를 다음으로 교체:
```python
    run(once=a.once, slots=a.slots, interval=a.interval, broad=a.broad)
```

- [ ] **Step 4: 기존 테스트 무회귀 + 문법 확인**

Run: `python -m pytest tests/ -q -k "autobuy"`
Expected: 전부 PASS(관찰기 순수함수 테스트 포함).

Run: `python -c "import sys; sys.path.insert(0,'scripts'); import ast; ast.parse(open('scripts/autobuy/verify_volume.py',encoding='utf-8').read()); print('ok')"`
Expected: `ok`.

- [ ] **Step 5: 커밋**

```bash
git add scripts/autobuy/verify_volume.py
git commit -m "feat(autobuy): verify_volume --broad — 넓은 감시로 읽기전용 관찰"
```

> **1단계 검증(코드 아님, 운영):** 실제 상승장 거래일 장중에 `python scripts/autobuy/verify_volume.py --broad` 를 돌려, 관찰 로그로 "예의주시 종목이 장중 돌파 시 잡히는지" 확인한 뒤 Task 3(실봇)로 넘어간다.

---

## Task 3: `--broad` 실봇 연결 (2단계 — dryrun 기본)

**Files:**
- Modify: `scripts/autobuy/runner.py`

**Interfaces:**
- Consumes: `watchlist.load_watchlist_broad(paths)` (Task 1).
- Produces: 없음(최종 소비자).

- [ ] **Step 1: `--broad` CLI 플래그 추가**

`scripts/autobuy/runner.py`의 `main()` 안 argparse 블록:
```python
    ap.add_argument("--live", action="store_true", help="실주문(미지정 시 dryrun)")
    args = ap.parse_args()
```
를 다음으로 교체:
```python
    ap.add_argument("--live", action="store_true", help="실주문(미지정 시 dryrun)")
    ap.add_argument("--broad", action="store_true", help="예의주시까지 넓게 감시(기본: 진입임박만)")
    args = ap.parse_args()
```

- [ ] **Step 2: 감시목록 로더 분기 + 로그**

`runner.py`의 감시목록 로딩 라인:
```python
    wl = watchlist.load_actionable(CANDIDATE_PATHS)
```
를 다음으로 교체:
```python
    if args.broad:
        wl = watchlist.load_watchlist_broad(CANDIDATE_PATHS)
        state.log("감시범위=넓음(진입임박+예의주시)")
    else:
        wl = watchlist.load_actionable(CANDIDATE_PATHS)
```

- [ ] **Step 3: 기존 테스트 무회귀 + 문법 확인**

Run: `python -m pytest tests/ -q -k "autobuy"`
Expected: 전부 PASS.

Run: `python -c "import sys; sys.path.insert(0,'scripts'); import ast; ast.parse(open('scripts/autobuy/runner.py',encoding='utf-8').read()); print('ok')"`
Expected: `ok`.

- [ ] **Step 4: dryrun 스모크 확인(선택, 장중/장외 무관하게 로딩만 확인)**

Run: `python -c "import sys; sys.path.insert(0,'scripts'); from autobuy import watchlist as w; from autobuy.config import CANDIDATE_PATHS as P; print('실봇 넓은목록', len(w.load_watchlist_broad(P)))"`
Expected: 종목 수 출력.

- [ ] **Step 5: 커밋**

```bash
git add scripts/autobuy/runner.py
git commit -m "feat(autobuy): runner --broad — 넓은 감시로 실봇 가동(dryrun 기본)"
```

> **2단계 사용 주의:** `--broad`는 1단계 관찰 검증 후에만 `--live`와 함께 쓴다. `--broad` 단독(dryrun)으로 먼저 며칠 돌려보는 것을 권장.

---

## Self-Review

**Spec coverage:**
- §3 `load_watchlist_broad`(포함/제외/우선순위/반환형태) → Task 1 ✅
- §4 1단계 관찰기 `--broad` → Task 2 ✅
- §4 2단계 실봇 `--broad` → Task 3 ✅
- §5 거래량 신호 불변 → 어떤 태스크도 vol_curve/VOL_PACE_MIN 미변경 ✅
- §7 안전(옵트인·dryrun·읽기전용) → Global Constraints + Task 2/3 주의문 ✅
- §9 범위 밖(청산·슬롯·스파이크신호·갭업·전체스캔·전체종목PP) → 어떤 태스크도 손대지 않음 ✅

**Placeholder scan:** 모든 스텝에 실제 코드/명령/기대출력 포함. 플레이스홀더 없음.

**Type consistency:** `load_watchlist_broad(paths) -> list[{code,name,pivot,pattern}]` 를 Task 1에서 정의, Task 2·3에서 동일 시그니처로 소비. `run(..., broad=False)` 시그니처 Task 2 내 일관. 일치 확인.
