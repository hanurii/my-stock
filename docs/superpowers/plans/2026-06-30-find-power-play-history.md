# find-power-play-history Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** find-vcp-history의 형제 도구 `find-power-play-history`를 추가한다 — `evaluate_power_play`를 과거 매 거래일 as-of로 재적용해, 종목별 "파워 플레이→돌파" 이벤트·돌파 후 결과·분류를 `sepa-power-play-history.json`에 산출한다.

**Architecture:** find-vcp-history를 미러링한다. 순수 부품 `canslim_lib/power_play_history.py`(replay/find_events/classify 신규 + 범용 post_breakout_outcome는 vcp_history에서 재사용), CLI `scripts/screen_power_play_history.py`, 스킬 문서. 새 판정 로직 없음 — 기존 `evaluate_power_play` 재사용(as-of 리플레이).

**Tech Stack:** Python 3 표준 라이브러리만(+ statistics). pytest. 기존 `canslim_lib/vcp_history.py`·`screen_vcp_history.py`·`tests/test_vcp_history.py` 패턴 그대로.

## Global Constraints

- 정의·근거 원본: `docs/superpowers/specs/2026-06-30-find-power-play-history-design.md`. 코드 주석 헤더에 이 경로 명시.
- **새 판정 로직 금지**: 반드시 기존 `evaluate_power_play`(scripts/canslim_lib/power_play.py)를 그대로 호출. 검출 임계값을 새로 만들지 않는다(검증의 전제).
- **공유 파일 무접촉**: 출력은 항상 `public/data/sepa-power-play-history.json`(또는 `--out`). 공유 파일 절대 안 건드림.
- **환각 금지**: 입력 종목 전부를 출력 `stocks[]`에 포함(이벤트 없으면 `no_power_play_found`·events []). 이벤트 근거(confirm_date·pivot·지표) JSON에 포함.
- **컷오프 금지**, **자동 commit/push 금지**.
- 순수 부품은 표준 라이브러리만. 한 종목 처리 실패가 전체 런을 멈추지 않게 한다(시세 없음 → `reason="no_series"`).
- `post_breakout_outcome`은 패턴 무관 범용 함수라 **vcp_history의 것을 재사용**(중복 구현 금지). `replay_power_play`/`find_breakout_events`/`classify`만 신규.
- classify 미검출 라벨은 **`no_power_play_found`**(vcp의 `no_vcp_found` 아님).
- 리플레이 기록·이벤트 근거의 검출 키는 **`pattern_detected`**(vcp의 `vcp_detected` 아님), 파워플레이 지표는 `flagpole_gain_pct`·`flag_depth_pct`(vcp의 `contractions` 아님).

---

## File Structure

| 파일 | 책임 |
|---|---|
| `scripts/canslim_lib/power_play_history.py` (생성) | 순수 부품: `replay_power_play`, `find_breakout_events`, `classify` 신규 + `post_breakout_outcome`는 vcp_history에서 import 재사용 |
| `tests/test_power_play_history.py` (생성) | 위 부품의 단위 테스트(합성 시계열) |
| `scripts/screen_power_play_history.py` (생성) | CLI: 입력 코드 결정→종목별 4단계→JSON 저장+콘솔 표 |
| `.claude/skills/find-power-play-history/SKILL.md` (생성) | 스킬 문서(find-vcp-history 톤) |

---

## Task 1: `replay_power_play` + `find_breakout_events`

as-of 리플레이와 돌파 이벤트 탐지(이음새 통합 테스트 포함)를 구현한다.

**Files:**
- Create: `scripts/canslim_lib/power_play_history.py`
- Test: `tests/test_power_play_history.py`

**Interfaces:**
- Consumes: `canslim_lib.power_play.evaluate_power_play(series, params) -> dict`(키: pattern_detected, status, pivot_price, flagpole_gain_pct, flag_depth_pct 등); `canslim_lib.vcp_history.post_breakout_outcome`(재사용 import).
- Produces:
  - `replay_power_play(series: dict, scan_days: int, params: dict | None = None) -> list[dict]` — 각 원소 키 `{date, pattern_detected, status, pivot_price, flagpole_gain_pct, flag_depth_pct}`.
  - `find_breakout_events(replay: list[dict], confirm_lookback: int = 5) -> list[dict]` — 각 이벤트 키 `{date, replay_idx, confirm_date, pivot_price, flagpole_gain_pct, flag_depth_pct}`.
  - 모듈 네임스페이스에 `post_breakout_outcome`(재export).

- [ ] **Step 1: Write the failing tests**

`tests/test_power_play_history.py`:
```python
# tests/test_power_play_history.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.power_play_history import (
    replay_power_play, find_breakout_events, post_breakout_outcome, classify,
)


def _clean_htf_with_breakout():
    """깔끔한 HTF(조용→+120% 깃대→얕은 깃발) + 물리적 신고가 돌파 봉."""
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 58, 66, 75, 85, 95, 104, 110]
    flag = [108, 106, 105, 104, 103, 105, 106, 107, 106, 105]
    closes = quiet + pole + flag + [112.0]                  # 마지막=돌파 봉
    highs = [c * 1.01 for c in closes[:-1]] + [113.0]
    lows = [c * 0.99 for c in closes[:-1]] + [111.0]
    vols = [800] * 20 + [3000] * 8 + [500] * 10 + [6000]
    dates = [f"d{i}" for i in range(len(closes))]
    return {"dates": dates, "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def test_replay_returns_one_entry_per_asof_day_with_keys():
    s = _clean_htf_with_breakout()
    rep = replay_power_play(s, scan_days=5)
    assert len(rep) == 5                               # 마지막 5 거래일
    assert rep[-1]["date"] == s["dates"][-1]           # 마지막 as-of = 마지막 날
    assert set(rep[0]) == {"date", "pattern_detected", "status",
                           "pivot_price", "flagpole_gain_pct", "flag_depth_pct"}


def test_find_breakout_events_detects_transition_with_prior_pattern():
    # 합성 replay: d3에 breakout 전환, 직전(d2)에 pattern_detected=true
    rep = [
        {"date": "d0", "pattern_detected": False, "status": "forming", "pivot_price": None, "flagpole_gain_pct": None, "flag_depth_pct": None},
        {"date": "d1", "pattern_detected": True,  "status": "forming", "pivot_price": 110.0, "flagpole_gain_pct": 120.0, "flag_depth_pct": 8.0},
        {"date": "d2", "pattern_detected": True,  "status": "actionable", "pivot_price": 110.0, "flagpole_gain_pct": 120.0, "flag_depth_pct": 8.0},
        {"date": "d3", "pattern_detected": False, "status": "breakout", "pivot_price": 110.0, "flagpole_gain_pct": 120.0, "flag_depth_pct": 8.0},
        {"date": "d4", "pattern_detected": False, "status": "breakout", "pivot_price": 110.0, "flagpole_gain_pct": 120.0, "flag_depth_pct": 8.0},
    ]
    evs = find_breakout_events(rep, confirm_lookback=5)
    assert len(evs) == 1                               # 연속 breakout(d4)은 중복 카운트 안 함
    assert evs[0]["date"] == "d3"
    assert evs[0]["replay_idx"] == 3
    assert evs[0]["confirm_date"] == "d2"              # 가장 가까운 직전 pattern_detected
    assert evs[0]["pivot_price"] == 110.0
    assert evs[0]["flagpole_gain_pct"] == 120.0
    assert evs[0]["flag_depth_pct"] == 8.0


def test_find_breakout_events_skips_breakout_without_prior_pattern():
    rep = [
        {"date": "d0", "pattern_detected": False, "status": "forming", "pivot_price": None, "flagpole_gain_pct": None, "flag_depth_pct": None},
        {"date": "d1", "pattern_detected": False, "status": "breakout", "pivot_price": 50.0, "flagpole_gain_pct": 60.0, "flag_depth_pct": 5.0},
    ]
    assert find_breakout_events(rep, confirm_lookback=5) == []


def test_integration_real_series_produces_event():
    # 실제 evaluate_power_play 를 as-of 리플레이 → 돌파일에 이벤트 1건.
    s = _clean_htf_with_breakout()
    rep = replay_power_play(s, scan_days=4)             # 마지막 4일(돌파 포함)
    evs = find_breakout_events(rep, confirm_lookback=5)
    assert len(evs) >= 1                               # 이음새가 실제 이벤트를 만든다
    assert evs[-1]["date"] == s["dates"][-1]           # 돌파일에 이벤트
    assert evs[-1]["flagpole_gain_pct"] is not None    # 근거 지표 캡처됨
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_power_play_history.py -v`
Expected: FAIL — `ImportError: cannot import name 'replay_power_play'` (모듈 없음).

- [ ] **Step 3: Write minimal implementation**

`scripts/canslim_lib/power_play_history.py`:
```python
"""find-power-play-history — 파워 플레이 검출기 회고·검증 (순수 부품).

기존 evaluate_power_play 를 과거 시계열에 as-of 로 반복 적용한다(새 판정 로직 없음).
post_breakout_outcome 는 패턴 무관 범용 함수라 vcp_history 의 것을 재사용한다(DRY).
정의: docs/superpowers/specs/2026-06-30-find-power-play-history-design.md
"""
from __future__ import annotations

from canslim_lib.power_play import evaluate_power_play
from canslim_lib.vcp_history import post_breakout_outcome  # noqa: F401  패턴 무관 범용 — 재사용·재export

_SERIES_KEYS = ("dates", "closes", "highs", "lows", "volumes", "timestamps")


def replay_power_play(series: dict, scan_days: int, params: dict | None = None) -> list[dict]:
    """마지막 scan_days 거래일 각각을 기준일로 evaluate_power_play 를 재실행.

    시계열을 [:i+1] 로 잘라 넣으면 evaluate_power_play 가 그 시점 마지막 날 기준으로 판정한다.
    """
    dates = series.get("dates") or []
    n = len(dates)
    out: list[dict] = []
    start = max(0, n - scan_days)
    for i in range(start, n):
        sub = {k: (series.get(k) or [])[: i + 1] for k in _SERIES_KEYS if series.get(k) is not None}
        r = evaluate_power_play(sub, params)
        out.append({
            "date": dates[i],
            "pattern_detected": r["pattern_detected"],
            "status": r["status"],
            "pivot_price": r["pivot_price"],
            "flagpole_gain_pct": r["flagpole_gain_pct"],
            "flag_depth_pct": r["flag_depth_pct"],
        })
    return out


def find_breakout_events(replay: list[dict], confirm_lookback: int = 5) -> list[dict]:
    """status 가 breakout 으로 새로 전환 + 직전 confirm_lookback 내 pattern_detected=true 인 날 = 이벤트."""
    events: list[dict] = []
    for j, cur in enumerate(replay):
        if cur["status"] != "breakout":
            continue
        if j > 0 and replay[j - 1]["status"] == "breakout":
            continue  # 같은 돌파 연속 → 첫 전환만
        confirm = None
        lo = max(0, j - confirm_lookback)
        for k in range(j - 1, lo - 1, -1):
            if replay[k]["pattern_detected"]:
                confirm = replay[k]
                break
        if confirm is None:
            continue
        events.append({
            "date": cur["date"],
            "replay_idx": j,
            "confirm_date": confirm["date"],
            "pivot_price": confirm["pivot_price"],
            "flagpole_gain_pct": confirm["flagpole_gain_pct"],
            "flag_depth_pct": confirm["flag_depth_pct"],
        })
    return events
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_power_play_history.py -v`
Expected: PASS (4 tests). 만약 `test_integration_real_series_produces_event`가 이벤트 0이면 합성 픽스처(`_clean_htf_with_breakout`)를 조정 — evaluate_power_play 가 돌파 직전 어느 as-of 날에 `pattern_detected=true`를 내고 마지막 날 `status=breakout`을 내야 한다. **검출 로직은 건드리지 말 것**(픽스처 숫자만). 디버그: `python -c "import sys;sys.path.insert(0,'scripts');from canslim_lib.power_play_history import replay_power_play; ..."`로 replay 각 날의 status/pattern_detected를 찍어 확인.

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/power_play_history.py tests/test_power_play_history.py
git commit -m "feat(pp-history): replay_power_play + find_breakout_events (as-of 리플레이)"
```

---

## Task 2: `classify` + `post_breakout_outcome` 재사용 검증

종목 분류(`classify`)를 추가하고, 재사용한 `post_breakout_outcome`이 이 모듈 import 경로로도 정상 동작하는지 고정한다.

**Files:**
- Modify: `scripts/canslim_lib/power_play_history.py`
- Test: `tests/test_power_play_history.py`

**Interfaces:**
- Consumes: Task 1의 모듈; `post_breakout_outcome`(vcp_history 재사용, 이미 import됨).
- Produces: `classify(events: list[dict], replay: list[dict], recent_days: int = 10) -> str` — 반환 `"no_power_play_found" | "recent_breakout" | "re_basing" | "extended"`.

- [ ] **Step 1: Write the failing tests**

`tests/test_power_play_history.py`에 추가:
```python
def test_classify_branches():
    assert classify([], [], recent_days=10) == "no_power_play_found"
    # 최근 돌파: 이벤트가 replay 끝에서 days_since<=recent_days
    rep = [{"pattern_detected": False, "status": "breakout"}] * 12
    ev_recent = [{"replay_idx": 9}]                    # len-1-9 = 2 <= 10
    assert classify(ev_recent, rep, recent_days=10) == "recent_breakout"
    # 연장: 오래 전 돌파, 이후 새 패턴 없음
    ev_old = [{"replay_idx": 0}]                       # days_since = 11 > 10
    rep_ext = [{"pattern_detected": False, "status": "extended_dummy"}] * 12
    assert classify(ev_old, rep_ext, recent_days=10) == "extended"
    # 재베이스: 오래 전 돌파 후 pattern_detected 재출현 + 마지막 forming
    rep_reb = [{"pattern_detected": False, "status": "breakout"}] * 12
    rep_reb[5] = {"pattern_detected": True, "status": "forming"}
    rep_reb[-1] = {"pattern_detected": False, "status": "forming"}
    assert classify(ev_old, rep_reb, recent_days=10) == "re_basing"


def test_post_breakout_outcome_reused_numbers():
    # 재사용한 vcp_history.post_breakout_outcome 가 이 모듈 import 경로로도 동일 동작.
    s = {
        "dates": ["d0", "d1", "d2", "d3"],
        "closes": [100.0, 110.0, 95.0, 130.0],
        "highs":  [100.0, 112.0, 96.0, 132.0],
        "lows":   [100.0, 108.0, 94.0, 128.0],
        "volumes": [1, 1, 1, 1],
    }
    o = post_breakout_outcome(s, "d0", stop_pct=8.0, target_pct=20.0)
    assert o["breakout_close"] == 100.0
    assert o["days_since"] == 3
    assert o["gain_since_pct"] == 30.0
    assert o["max_gain_pct"] == 32.0
    assert o["max_drawdown_pct"] == -5.0
    assert o["good_breakout"] is True


def test_post_breakout_outcome_missing_date_returns_none():
    s = {"dates": ["d0"], "closes": [100.0], "highs": [100.0], "lows": [100.0], "volumes": [1]}
    assert post_breakout_outcome(s, "zzz") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_power_play_history.py::test_classify_branches -v`
Expected: FAIL — `ImportError`/`cannot import name 'classify'` 또는 `AttributeError`(아직 classify 없음). (post_breakout 테스트는 import는 되지만 classify import 실패로 모듈 전체가 collection 에러날 수 있음 — classify 추가 후 함께 통과.)

- [ ] **Step 3: Write minimal implementation**

`scripts/canslim_lib/power_play_history.py`에 추가:
```python
def classify(events: list[dict], replay: list[dict], recent_days: int = 10) -> str:
    """돌파 후 종목 상태 분류.

    "no_power_play_found" - 돌파 이벤트 없음
    "recent_breakout" - 최근 돌파(days_since <= recent_days)
    "re_basing" - 오래 전 돌파 후 pattern 재출현 중(마지막 status forming/actionable)
    "extended" - 오래 전 돌파 후 계속 상승세(새 패턴 없음)
    """
    if not events:
        return "no_power_play_found"
    idx = events[-1]["replay_idx"]
    days_since = (len(replay) - 1) - idx
    if days_since <= recent_days:
        return "recent_breakout"
    later = any(replay[k].get("pattern_detected") for k in range(idx + 1, len(replay)))
    if later and replay[-1].get("status") in ("forming", "actionable"):
        return "re_basing"
    return "extended"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_power_play_history.py -v`
Expected: PASS (Task 1의 4 + 신규 3 = 7 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/power_play_history.py tests/test_power_play_history.py
git commit -m "feat(pp-history): classify + post_breakout_outcome 재사용 검증"
```

---

## Task 3: CLI 엔트리 `screen_power_play_history.py`

find-vcp-history의 `screen_vcp_history.py`를 미러링한 CLI. 입력 코드 결정→종목별 4단계→JSON 저장+콘솔 표.

**Files:**
- Create: `scripts/screen_power_play_history.py`

**Interfaces:**
- Consumes: `canslim_lib.power_play.DEFAULT_PARAMS`; `canslim_lib.power_play_history`의 `replay_power_play, find_breakout_events, post_breakout_outcome, classify`; `canslim_lib.ohlcv_matrix.get_series`.
- Produces: 실행파일(`python scripts/screen_power_play_history.py`). 출력 `public/data/sepa-power-play-history.json`.

- [ ] **Step 1: 구현 작성** (TDD 대상 아님 — I/O 스크립트, 콘솔/파일로 수동 검증)

`scripts/screen_power_play_history.py`:
```python
# scripts/screen_power_play_history.py
"""find-power-play-history — 파워 플레이 검출기 회고·검증.

입력: public/data/sepa-power-play-candidates.json (기본 전체 후보)
출력: public/data/sepa-power-play-history.json
정의: docs/superpowers/specs/2026-06-30-find-power-play-history-design.md
"""
from __future__ import annotations

import argparse
import json
import statistics
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
from canslim_lib.power_play import DEFAULT_PARAMS  # noqa: E402
from canslim_lib.power_play_history import (  # noqa: E402
    replay_power_play, find_breakout_events, post_breakout_outcome, classify,
)

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-power-play-candidates.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-power-play-history.json"
CAVEAT = ("집계 수익률은 추세 통과(RS 강세) 종목만 본 결과라 생존자 편향으로 과대평가됨. "
          "검출기 신뢰의 보조 지표일 뿐, 결정적 검증은 이벤트 날짜를 차트로 눈 대조하는 것.")
CLASS_ORDER = {"re_basing": 0, "recent_breakout": 1, "extended": 2, "no_power_play_found": 3}


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def run(args, out_path: Path) -> None:
    in_path = Path(args.inp) if args.inp else IN_PATH
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.exists():
        print(f"❌ 입력 파일 없음: {in_path.relative_to(ROOT)}\n"
              f"   먼저 find-power-play 를 실행해 sepa-power-play-candidates.json 을 생성하세요.")
        sys.exit(1)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    cands = data.get("candidates", [])
    by_code = {c["code"]: c for c in cands}

    if args.codes:
        codes = [x.strip() for x in args.codes.split(",") if x.strip()]
        filt = "codes"
    else:
        codes = [c["code"] for c in cands]
        filt = "all"

    params = {
        "lookback_days": args.lookback_days,
        "min_flagpole_gain": args.min_flagpole_gain,
        "max_flagpole_days": args.max_flagpole_days,
        "pole_vol_mult": args.pole_vol_mult,
        "max_pre_pole_gain": args.max_pre_pole_gain,
        "min_flag_pullback": args.min_flag_pullback,
        "min_flag_days": args.min_flag_days,
        "max_flag_days": args.max_flag_days,
        "max_flag_depth": args.max_flag_depth,
        "breakout_vol_mult": args.breakout_vol_mult,
        "near_pivot_pct": args.near_pivot_pct,
    }

    stocks = []
    for code in codes:
        meta = by_code.get(code, {})
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            stocks.append({"code": code, "name": meta.get("name"), "market": meta.get("market"),
                           "rs": meta.get("rs"), "classification": "no_power_play_found",
                           "num_events": 0, "most_recent_event_date": None, "events": [],
                           "reason": "no_series"})
            continue
        rep = replay_power_play(s, args.scan_days, params)
        raw = find_breakout_events(rep, args.confirm_lookback)
        events = []
        for e in raw:
            o = post_breakout_outcome(s, e["date"], args.stop_pct, args.target_pct) or {}
            ev = {**e, **o}
            ev.pop("replay_idx", None)
            events.append(ev)
        cls = classify(raw, rep, args.recent_days)
        stocks.append({"code": code, "name": meta.get("name"), "market": meta.get("market"),
                       "rs": meta.get("rs"), "classification": cls, "num_events": len(events),
                       "most_recent_event_date": events[-1]["date"] if events else None,
                       "events": events})

    stocks.sort(key=lambda x: (CLASS_ORDER.get(x["classification"], 9), -(x.get("rs") or 0)))

    all_events = [e for st in stocks for e in st["events"]]
    summary = {
        "n_stocks": len(stocks),
        "n_with_events": sum(1 for st in stocks if st["num_events"] > 0),
        "n_no_power_play_found": sum(1 for st in stocks if st["classification"] == "no_power_play_found"),
        "total_events": len(all_events),
        "agg": {
            "median_gain_since_pct": _median([e.get("gain_since_pct") for e in all_events]),
            "median_max_gain_pct": _median([e.get("max_gain_pct") for e in all_events]),
            "good_breakout_rate": (round(sum(1 for e in all_events if e.get("good_breakout")) / len(all_events), 3)
                                   if all_events else None),
        },
    }
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": data.get("asof"), "source": in_path.name, "input_filter": filt,
        "scan_days": args.scan_days,
        "params": {**params, "confirm_lookback": args.confirm_lookback, "recent_days": args.recent_days,
                   "stop_pct": args.stop_pct, "target_pct": args.target_pct},
        "caveat": CAVEAT, "summary": summary, "stocks": stocks,
    }

    if not args.ticker:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 저장: {out_path.relative_to(ROOT)}")

    print(f"\n[PP-history] 입력 {summary['n_stocks']}종목({filt}) | "
          f"이벤트보유 {summary['n_with_events']} · 미검출 {summary['n_no_power_play_found']} | "
          f"총 이벤트 {summary['total_events']}")
    for st in stocks:
        ev = st["events"][-1] if st["events"] else None
        tail = (f"최근 {ev['date']} 피벗 {ev['pivot_price']} → 현재 {ev.get('gain_since_pct')}% "
                f"(최대 {ev.get('max_gain_pct')}%, {ev.get('days_since')}일 경과)") if ev else "-"
        print(f"  [{st['classification']:18s}] {st['code']} {str(st['name'])[:12]:12s} "
              f"RS{st.get('rs')} | {tail}")
    agg = summary["agg"]
    print(f"\n[집계·참고용] 돌파후 수익률 중앙 {agg['median_gain_since_pct']}% · "
          f"최대 중앙 {agg['median_max_gain_pct']}% · good_breakout율 {agg['good_breakout_rate']}")
    print(f"⚠️ {CAVEAT}")


def main():
    ap = argparse.ArgumentParser(description="find-power-play-history — 파워 플레이 검출기 회고·검증")
    ap.add_argument("--in", dest="inp", default=None, help=f"입력(default {IN_PATH.name})")
    ap.add_argument("--out", dest="out", default=None, help=f"출력(default {OUT_PATH.name})")
    ap.add_argument("--codes", default=None, help="임의 코드 목록 쉼표구분 (예 005930,000660)")
    ap.add_argument("--ticker", default=None, help="단일 종목 디버그(저장 안 함)")
    ap.add_argument("--scan-days", type=int, default=250)
    ap.add_argument("--confirm-lookback", type=int, default=5)
    ap.add_argument("--recent-days", type=int, default=10)
    ap.add_argument("--stop-pct", type=float, default=8.0)
    ap.add_argument("--target-pct", type=float, default=20.0)
    ap.add_argument("--lookback-days", type=int, default=DEFAULT_PARAMS["lookback_days"])
    ap.add_argument("--min-flagpole-gain", type=float, default=DEFAULT_PARAMS["min_flagpole_gain"])
    ap.add_argument("--max-flagpole-days", type=int, default=DEFAULT_PARAMS["max_flagpole_days"])
    ap.add_argument("--pole-vol-mult", type=float, default=DEFAULT_PARAMS["pole_vol_mult"])
    ap.add_argument("--max-pre-pole-gain", type=float, default=DEFAULT_PARAMS["max_pre_pole_gain"])
    ap.add_argument("--min-flag-pullback", type=float, default=DEFAULT_PARAMS["min_flag_pullback"])
    ap.add_argument("--min-flag-days", type=int, default=DEFAULT_PARAMS["min_flag_days"])
    ap.add_argument("--max-flag-days", type=int, default=DEFAULT_PARAMS["max_flag_days"])
    ap.add_argument("--max-flag-depth", type=float, default=DEFAULT_PARAMS["max_flag_depth"])
    ap.add_argument("--breakout-vol-mult", type=float, default=DEFAULT_PARAMS["breakout_vol_mult"])
    ap.add_argument("--near-pivot-pct", type=float, default=DEFAULT_PARAMS["near_pivot_pct"])
    args = ap.parse_args()
    if args.ticker:
        args.codes = args.ticker
    out_path = (Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out) if args.out else OUT_PATH
    run(args, out_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: import·문법 스모크 테스트**

Run: `python -c "import sys; sys.path.insert(0,'scripts'); import screen_power_play_history; print('ok')"`
Expected: `ok` (import 에러 없음).

- [ ] **Step 3: 단일 종목 디버그**(입력 파일이 있을 때)

Run: `python scripts/screen_power_play_history.py --ticker 095610`
Expected: 저장 메시지 없이 `[PP-history]` 요약 + 종목 1줄 + 집계·딱지 출력, exit 0. (입력 파일 없으면 안내 후 Task 4 풀런에서 확인.)

- [ ] **Step 4: Commit**

```bash
git add scripts/screen_power_play_history.py
git commit -m "feat(pp-history): screen_power_play_history CLI 엔트리"
```

---

## Task 4: 스킬 문서 `SKILL.md` + 실데이터 풀런 검증

**Files:**
- Create: `.claude/skills/find-power-play-history/SKILL.md`

**Interfaces:**
- Consumes: `scripts/screen_power_play_history.py` (Task 3).

- [ ] **Step 1: SKILL.md 작성**

`.claude/skills/find-power-play-history/SKILL.md`:
```markdown
---
name: find-power-play-history
description: >
  파워 플레이 검출기 회고·검증 도구(find-vcp-history 형제). find-power-play 후보 종목의
  과거 1년을 매 거래일 as-of 로 되짚어, 기존 evaluate_power_play 가 짚어낸 "파워 플레이
  →돌파" 이벤트·돌파 후 결과·종목 분류(extended/recent_breakout/re_basing/
  no_power_play_found)를 sepa-power-play-history.json 에 산출한다. 집계 수익률은 생존자
  편향 경고와 함께 참고용. 사용자가 "/find-power-play-history", "파워플레이 검증",
  "과거에 이미 돌파했나", "이 종목 파워플레이 했었나" 등을 요청할 때 사용.
---

# find-power-play-history — 파워 플레이 검출기 회고·검증

`find-power-play` 후보 종목이 과거에 정말 파워 플레이→돌파를 거쳤는지 **기존
검출기를 과거에 그대로 적용**해 짚어낸다. 1순위 용도 = 검출기 검증(이벤트
날짜를 차트로 눈 대조). 정의: `docs/superpowers/specs/2026-06-30-find-power-play-history-design.md`.

## 사전 조건
- 먼저 `update-data` → `find-trend-template` → `find-power-play` 를 돌려 입력
  `public/data/sepa-power-play-candidates.json` 이 있어야 한다.

## 실행
\`\`\`
python scripts/screen_power_play_history.py
\`\`\`
- 산출: `public/data/sepa-power-play-history.json`
- 콘솔: 종목별 분류·최근 돌파 이벤트 + 집계(⚠️ 생존자 편향 경고).

### 옵션
- `--ticker 095610` : 단일 종목(저장 안 함).
- `--codes 005930,000660` : 임의 종목만(미지정 시 전체 후보).
- `--scan-days 250` `--confirm-lookback 5` `--recent-days 10` `--stop-pct 8` `--target-pct 20`
- 파워플레이 임계값(`--min-flagpole-gain` 등)은 find-power-play 와 동일(같은 검출기를 써야 검증 의미).

## 결과 보는 법
- `classification`: extended(이미 돌파·연장=추격 늦음) / recent_breakout(최근 돌파) /
  re_basing(돌파 후 2차 베이스) / no_power_play_found(검출 0=미스 의심 또는 패턴 없음).
- `events[].date` 를 차트로 열어 "진짜 파워 플레이 돌파였나" 눈으로 확인 = 진짜 검증.
- `events[].confirm_date`·`flagpole_gain_pct`·`flag_depth_pct` = 돌파 근거.
- 집계 수익률은 **생존자 편향으로 과대** — 보조 지표로만.

## 안 하는 것
- 새 판정 로직(기존 evaluate_power_play 재사용) · 임계값 자동 튜닝 · 실거래 신호 ·
  공유 파일 갱신 · 자동 commit.
```

- [ ] **Step 2: 실데이터 풀런**(입력 파일이 존재할 때)

Run: `python scripts/screen_power_play_history.py`
Expected:
- `💾 저장: public\data\sepa-power-play-history.json` 출력.
- `[PP-history]` 요약(입력 종목 수·이벤트보유·미검출·총 이벤트) + 종목별 분류 줄 + 집계 + ⚠️ 딱지.
- 오류로 종료하지 않음. (이벤트 수는 0~수십 — 과거 돌파가 있었던 만큼.)

입력 파일이 없으면: 먼저 `update-data` → `find-trend-template` → `find-power-play` 실행 후 재실행.

- [ ] **Step 3: 산출 JSON 구조 확인**

Read `public/data/sepa-power-play-history.json` 상단:
- `input_filter:"all"`, `params`(파워플레이 임계값 + confirm_lookback/recent_days/stop_pct/target_pct), `caveat`, `summary`(n_stocks·n_with_events·n_no_power_play_found·total_events·agg), `stocks[]`.
- `stocks[]`에 입력 종목 전부 포함, 이벤트 있는 종목의 `events[]`에 confirm_date·pivot_price·flagpole_gain_pct·flag_depth_pct·돌파후 성과 키.
- 정렬: classification(re_basing→recent_breakout→extended→no_power_play_found) → rs 내림차순.

- [ ] **Step 4: 전체 테스트 재실행(회귀 확인)**

Run: `python -m pytest tests/test_power_play_history.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/find-power-play-history/SKILL.md public/data/sepa-power-play-history.json
git commit -m "feat(pp-history): find-power-play-history SKILL 문서 + 첫 풀런 산출"
```
(산출 JSON 커밋이 부담되면 SKILL.md만 커밋하고 산출물은 제외 가능.)

---

## Self-Review

**1. Spec coverage (spec §별 → 태스크 매핑):**
- §2 범위(입력 기본 전체·출력 파일·안 하는 것) → Task 3(입력 코드 결정·출력), Task 4(SKILL.md 안 하는 것).
- §4.1 as-of 리플레이(`replay_power_play`, 마지막 120일만 보므로 짧아도 안전) → Task 1.
- §4.2 돌파 이벤트(status breakout 신규전환 + 직전 confirm_lookback 내 pattern_detected) → Task 1 + 테스트(transition/skip/integration).
- §4.3 돌파 후 결과(post_breakout_outcome 재사용·동일 로직) → Task 2(재사용 검증 테스트), Task 3(이벤트별 호출).
- §4.4 분류(no_power_play_found/recent_breakout/re_basing/extended) → Task 2 + 테스트.
- §4.5 집계(생존자 편향 딱지) → Task 3(summary·CAVEAT·콘솔).
- §5 출력 스키마(키·confirm_date·no_series·정렬) → Task 3.
- §6 구성요소(부품 4종·CLI·산출 경로) → Task 1·2(부품), Task 3(CLI).
- §7 불변원칙(공유 무접촉·동일 검출기·환각금지) → Global Constraints + Task 3.
- §8 검증계획(①~④ 단위테스트 + 실데이터 풀런) → Task 1·2 테스트, Task 4 풀런.

**2. Placeholder scan:** "TBD/TODO/적절히 처리" 없음. 모든 코드 스텝에 실제 코드 포함.

**3. Type consistency:** `replay_power_play` 반환 키(date, pattern_detected, status, pivot_price, flagpole_gain_pct, flag_depth_pct)를 `find_breakout_events`·`classify`가 그대로 소비. 이벤트 키(date, replay_idx, confirm_date, pivot_price, flagpole_gain_pct, flag_depth_pct)를 Task 3 CLI가 소비(replay_idx는 pop). `classify` 반환 라벨(no_power_play_found 등)과 CLI `CLASS_ORDER`·summary 키(n_no_power_play_found) 일치. CLI `params` 키와 `DEFAULT_PARAMS`/argparse 플래그명 일치(min_flag_pullback 포함).

**참고(엣지):** `post_breakout_outcome`은 vcp_history에서 import 재사용 — 패턴 무관 범용 함수(시계열+이벤트일만 사용)라 중복 구현하지 않는다. vcp_history.py 가 트리에 존재해야 import 성공(현재 브랜치는 find-vcp-history 위에 쌓여 있어 존재함).
