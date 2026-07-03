# find-3c-history Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** find-3c 후보 70종의 과거 1년을 매 거래일 as-of로 되짚어 "3C→돌파" 이벤트·돌파 후 결과·종목 분류를 산출하는 회고·검증 스킬을 만든다(기존 `evaluate_cheat` 재사용).

**Architecture:** `find-vcp-history`의 충실한 미러. 순수 부품 `cheat_history.py`(4함수, evaluate_cheat as-of 리플레이) + CLI `screen_3c_history.py` + SKILL.md. 새 판정 로직 없음.

**Tech Stack:** Python 3 (stdlib only), pytest, 기존 `canslim_lib.cheat`/`ohlcv_matrix`.

## Global Constraints

- 설계 spec: `docs/superpowers/specs/2026-06-30-find-3c-history-design.md`. 형제: `find-vcp-history`(`scripts/canslim_lib/vcp_history.py`, `scripts/screen_vcp_history.py`).
- **기존 `evaluate_cheat`(v2b) 만 호출**, 새 판정 로직 금지(검증 전제 — 다른 로직이면 검증 의미 없음).
- 순수 함수(파일/네트워크 I/O 없음), stdlib만.
- 공유 파일 무접촉, 컷오프 금지, 환각 금지(이벤트 근거 JSON 포함), 자동 commit 금지(plan 커밋 단계는 개발용).
- 입력 종목 **전부** 출력에 포함(이벤트 없으면 `no_3c_found`·events []). no-series → `reason:"no_series"`.
- 집계에 **생존자 편향 딱지** 명시(콘솔+JSON `caveat`).
- 분류 라벨: `no_3c_found` / `recent_breakout` / `re_basing` / `extended`.
- 정렬: classification(re_basing→recent_breakout→extended→no_3c_found) → rs 내림차순.

## File Structure

- `scripts/canslim_lib/cheat_history.py` — **신규.** `replay_cheat`, `find_breakout_events`, `post_breakout_outcome`, `classify`.
- `tests/test_cheat_history.py` — **신규.** 순수 함수 단위 테스트.
- `scripts/screen_3c_history.py` — **신규.** CLI 엔트리.
- `.claude/skills/find-3c-history/SKILL.md` — **신규.**
- `public/data/sepa-3c-history.json` — 런타임 산출(커밋 안 함).

---

## Task 1: 순수 부품 `cheat_history.py` + 단위 테스트

**Files:**
- Create: `scripts/canslim_lib/cheat_history.py`
- Test: `tests/test_cheat_history.py`

**Interfaces:**
- Consumes: `canslim_lib.cheat.evaluate_cheat`.
- Produces:
  - `replay_cheat(series: dict, scan_days: int, params: dict|None=None) -> list[dict]` — 각 원소 `{date, pattern_detected, status, pivot_price, cup_depth_pct, shelf_position_pct}`.
  - `find_breakout_events(replay: list[dict], confirm_lookback: int=5) -> list[dict]` — 각 이벤트 `{date, replay_idx, confirm_date, pivot_price, cup_depth_pct, shelf_position_pct}`.
  - `post_breakout_outcome(series: dict, event_date: str, stop_pct: float=8.0, target_pct: float=20.0) -> dict|None` — `{breakout_close, days_since, gain_since_pct, max_gain_pct, max_drawdown_pct, good_breakout}`.
  - `classify(events: list[dict], replay: list[dict], recent_days: int=10) -> str`.

- [ ] **Step 1: Write the failing tests**

`tests/test_cheat_history.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.cheat_history import (
    replay_cheat, find_breakout_events, post_breakout_outcome, classify,
)


def _rep(*tuples):
    """(status, pattern_detected) 튜플들로 replay 리스트 생성(date=d0..)."""
    return [{"date": f"d{i}", "status": s, "pattern_detected": p,
             "pivot_price": 10.0, "cup_depth_pct": 20.0, "shelf_position_pct": 50.0}
            for i, (s, p) in enumerate(tuples)]


def test_find_breakout_events_catches_confirmed_breakout():
    # forming/actionable(치트 확인) ... 그 뒤 breakout 새 전환 → 이벤트 1건.
    rep = _rep(("forming", False), ("actionable", True), ("actionable", True),
               ("breakout", False), ("breakout", False))
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert len(ev) == 1
    assert ev[0]["date"] == "d3"          # 첫 breakout 전환일
    assert ev[0]["confirm_date"] == "d2"  # 직전 pattern_detected=True 최근일
    assert ev[0]["replay_idx"] == 3


def test_find_breakout_events_requires_confirm():
    # breakout 이지만 직전 confirm_lookback 내 pattern_detected=True 없음 → 이벤트 0.
    rep = _rep(("forming", False), ("forming", False), ("breakout", False))
    assert find_breakout_events(rep, confirm_lookback=5) == []


def test_find_breakout_events_dedup_consecutive():
    # 연속 breakout 은 첫 전환만.
    rep = _rep(("actionable", True), ("breakout", False), ("breakout", False), ("breakout", False))
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert len(ev) == 1 and ev[0]["date"] == "d1"


def test_classify_no_3c_found_when_no_events():
    rep = _rep(("forming", False), ("forming", False))
    assert classify([], rep, recent_days=10) == "no_3c_found"


def test_classify_recent_breakout():
    rep = _rep(*[("forming", False)]*5, ("actionable", True), ("breakout", False))
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert classify(ev, rep, recent_days=10) == "recent_breakout"


def test_classify_extended():
    # 돌파 후 한참(>recent_days) 상승, 새 치트 없음.
    rep = _rep(("actionable", True), ("breakout", False), *[("forming", False)]*15)
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert classify(ev, rep, recent_days=10) == "extended"


def test_classify_re_basing():
    # 돌파 후 새 치트(pattern_detected=True) 재출현 + 마지막 forming/actionable.
    rep = _rep(("actionable", True), ("breakout", False), *[("forming", False)]*12,
               ("actionable", True), ("actionable", True))
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert classify(ev, rep, recent_days=10) == "re_basing"


def test_post_breakout_outcome_numbers():
    # 돌파일 종가 100. 이후 high 130(+30%), 종가 최저 95(-5%), 마지막 종가 120(+20%).
    series = {"dates": ["d0", "d1", "d2", "d3"],
              "closes": [100.0, 110.0, 95.0, 120.0],
              "highs":  [101.0, 130.0, 100.0, 122.0],
              "lows":   [99.0, 108.0, 94.0, 118.0],
              "volumes": [1, 1, 1, 1]}
    o = post_breakout_outcome(series, "d0", stop_pct=8.0, target_pct=20.0)
    assert o["breakout_close"] == 100.0
    assert o["days_since"] == 3
    assert o["gain_since_pct"] == 20.0
    assert o["max_gain_pct"] == 30.0
    assert o["max_drawdown_pct"] == -5.0
    assert o["good_breakout"] is True       # +20% high 도달 전 -8% low 미접촉


def test_post_breakout_outcome_stop_before_target():
    # 먼저 -8% 손절(low 92) 후 나중에 +20% → good_breakout False(손절 먼저).
    series = {"dates": ["d0", "d1", "d2"],
              "closes": [100.0, 95.0, 125.0],
              "highs":  [101.0, 98.0, 130.0],
              "lows":   [99.0, 92.0, 120.0],
              "volumes": [1, 1, 1]}
    o = post_breakout_outcome(series, "d0", stop_pct=8.0, target_pct=20.0)
    assert o["good_breakout"] is False


def test_replay_cheat_shape():
    # 작은 시계열로 replay 가 올바른 길이·키를 내는지(evaluate_cheat 실호출).
    closes = [10 + (i % 3) for i in range(60)]
    series = {"dates": [f"2026-01-{i+1:03d}" for i in range(60)],
              "closes": closes, "highs": [c*1.01 for c in closes],
              "lows": [c*0.99 for c in closes], "volumes": [1000]*60}
    rep = replay_cheat(series, scan_days=10)
    assert len(rep) == 10
    for r in rep:
        assert set(r) >= {"date", "pattern_detected", "status", "pivot_price",
                          "cup_depth_pct", "shelf_position_pct"}
    assert rep[-1]["date"] == "2026-01-060"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_cheat_history.py -v`
Expected: FAIL — `ModuleNotFoundError: canslim_lib.cheat_history`.

- [ ] **Step 3: Write `cheat_history.py`**

`scripts/canslim_lib/cheat_history.py`:

```python
"""find-3c-history — 3C 검출기 회고·검증 (순수 부품).

기존 evaluate_cheat(v2b)를 과거 시계열에 as-of 로 반복 적용한다(새 판정 로직 없음).
정의: docs/superpowers/specs/2026-06-30-find-3c-history-design.md
"""
from __future__ import annotations

from canslim_lib.cheat import evaluate_cheat

_SERIES_KEYS = ("dates", "closes", "highs", "lows", "volumes", "timestamps")


def replay_cheat(series: dict, scan_days: int, params: dict | None = None) -> list[dict]:
    """마지막 scan_days 거래일 각각을 기준일로 evaluate_cheat 를 재실행.

    시계열을 [:i+1] 로 잘라 넣으면 evaluate_cheat 가 그 시점 마지막 날 기준으로 판정한다.
    """
    dates = series.get("dates") or []
    n = len(dates)
    out: list[dict] = []
    start = max(0, n - scan_days)
    for i in range(start, n):
        sub = {k: (series.get(k) or [])[: i + 1] for k in _SERIES_KEYS if series.get(k) is not None}
        r = evaluate_cheat(sub, params)
        out.append({
            "date": dates[i],
            "pattern_detected": r["pattern_detected"],
            "status": r["status"],
            "pivot_price": r["pivot_price"],
            "cup_depth_pct": r["cup_depth_pct"],
            "shelf_position_pct": r["shelf_position_pct"],
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
            "cup_depth_pct": confirm["cup_depth_pct"],
            "shelf_position_pct": confirm["shelf_position_pct"],
        })
    return events


def post_breakout_outcome(series: dict, event_date: str,
                          stop_pct: float = 8.0, target_pct: float = 20.0) -> dict | None:
    """돌파일 이후 성과: 수익률·최대수익·최대손실·목표달성. event_date 없으면 None."""
    dates = series.get("dates") or []
    closes = series.get("closes") or []
    highs = series.get("highs") or []
    lows = series.get("lows") or []
    try:
        idx = dates.index(event_date)
    except ValueError:
        return None
    bc = closes[idx]
    if not bc:
        return None
    after_h, after_c = highs[idx + 1:], closes[idx + 1:]
    after_l = lows[idx + 1:]
    gain_since = (closes[-1] - bc) / bc * 100.0
    max_gain = max(((h - bc) / bc * 100.0 for h in after_h), default=0.0)
    max_dd = min(((c - bc) / bc * 100.0 for c in after_c), default=0.0)
    # good_breakout: 손절은 intrabar low, 목표는 intrabar high(체결 가정). 같은 바면 손절 우선.
    good = False
    for h, l in zip(after_h, after_l):
        if (l - bc) / bc * 100.0 <= -stop_pct:
            good = False
            break
        if (h - bc) / bc * 100.0 >= target_pct:
            good = True
            break
    return {
        "breakout_close": round(bc, 2),
        "days_since": len(dates) - 1 - idx,
        "gain_since_pct": round(gain_since, 2),
        "max_gain_pct": round(max_gain, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "good_breakout": good,
    }


def classify(events: list[dict], replay: list[dict], recent_days: int = 10) -> str:
    """돌파 후 종목 상태 분류.

    no_3c_found(이벤트 없음) / recent_breakout(days_since<=recent_days) /
    re_basing(이후 pattern_detected 재출현 + 마지막 forming/actionable) / extended(그 외).
    """
    if not events:
        return "no_3c_found"
    idx = events[-1]["replay_idx"]
    days_since = (len(replay) - 1) - idx
    if days_since <= recent_days:
        return "recent_breakout"
    later = any(replay[k].get("pattern_detected") for k in range(idx + 1, len(replay)))
    if later and replay[-1].get("status") in ("forming", "actionable"):
        return "re_basing"
    return "extended"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_cheat_history.py -v`
Expected: PASS(전부). 합성 replay 기반 테스트라 evaluate_cheat 의존이 거의 없어 안정적.
`test_replay_cheat_shape` 가 길이/키만 보므로 통과해야 함.

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/cheat_history.py tests/test_cheat_history.py
git commit -m "feat(find-3c): cheat_history.py 회고 부품(replay/events/outcome/classify) + 테스트"
```

---

## Task 2: CLI `screen_3c_history.py` + 첫 풀런

**Files:**
- Create: `scripts/screen_3c_history.py`

**Interfaces:**
- Consumes: `ohlcv_matrix.get_series`, `canslim_lib.cheat.DEFAULT_PARAMS`, `cheat_history`의 4함수.
- Produces: CLI 실행 → `public/data/sepa-3c-history.json` + 콘솔 표.

- [ ] **Step 1: Write `screen_3c_history.py`**

`scripts/screen_3c_history.py`:

```python
# scripts/screen_3c_history.py
"""find-3c-history — 3C 검출기 회고·검증.

입력: public/data/sepa-3c-candidates.json (find-3c 후보 종목)
출력: public/data/sepa-3c-history.json
정의: docs/superpowers/specs/2026-06-30-find-3c-history-design.md
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
from canslim_lib.cheat import DEFAULT_PARAMS  # noqa: E402
from canslim_lib.cheat_history import (  # noqa: E402
    replay_cheat, find_breakout_events, post_breakout_outcome, classify,
)

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-3c-candidates.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-3c-history.json"
CAVEAT = ("집계 수익률은 RS 상위 트렌드 통과 종목(승자)만 본 결과라 생존자 편향으로 과대평가됨. "
          "검출기 신뢰의 보조 지표일 뿐, 결정적 검증은 이벤트 날짜를 차트로 눈 대조하는 것.")
CLASS_ORDER = {"re_basing": 0, "recent_breakout": 1, "extended": 2, "no_3c_found": 3}


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def run(args, out_path: Path) -> None:
    in_path = Path(args.inp) if args.inp else IN_PATH
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.exists():
        print(f"❌ 입력 파일 없음: {in_path.relative_to(ROOT)}\n"
              f"   먼저 find-3c 를 실행해 sepa-3c-candidates.json 을 생성하세요.")
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
        "min_cup_depth": args.min_cup_depth, "max_cup_depth": args.max_cup_depth,
        "min_cup_days": args.min_cup_days, "min_shelf_pullback": args.min_shelf_pullback,
        "min_shelf_days": args.min_shelf_days, "max_shelf_days": args.max_shelf_days,
        "max_shelf_depth": args.max_shelf_depth, "max_shelf_position": args.max_shelf_position,
        "breakout_vol_mult": args.breakout_vol_mult, "near_pivot_pct": args.near_pivot_pct,
    }

    stocks = []
    for code in codes:
        meta = by_code.get(code, {})
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            stocks.append({"code": code, "name": meta.get("name"), "market": meta.get("market"),
                           "rs": meta.get("rs"), "classification": "no_3c_found",
                           "num_events": 0, "most_recent_event_date": None, "events": [],
                           "reason": "no_series"})
            continue
        rep = replay_cheat(s, args.scan_days, params)
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
        "n_no_3c_found": sum(1 for st in stocks if st["classification"] == "no_3c_found"),
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

    print(f"\n[3C-history] 입력 {summary['n_stocks']}종목({filt}) | "
          f"이벤트보유 {summary['n_with_events']} · 미검출 {summary['n_no_3c_found']} | "
          f"총 이벤트 {summary['total_events']}")
    for st in stocks:
        ev = st["events"][-1] if st["events"] else None
        tail = (f"최근 {ev['date']} 피벗 {ev['pivot_price']} (컵{ev.get('cup_depth_pct')}%·"
                f"선반위치{ev.get('shelf_position_pct')}%) → 현재 {ev.get('gain_since_pct')}% "
                f"(최대 {ev.get('max_gain_pct')}%, {ev.get('days_since')}일)") if ev else "-"
        print(f"  [{st['classification']:15s}] {st['code']} {str(st['name'])[:12]:12s} "
              f"RS{st.get('rs')} | {tail}")
    agg = summary["agg"]
    print(f"\n[집계·참고용] 돌파후 수익률 중앙 {agg['median_gain_since_pct']}% · "
          f"최대 중앙 {agg['median_max_gain_pct']}% · good_breakout율 {agg['good_breakout_rate']}")
    print(f"⚠️ {CAVEAT}")


def main():
    ap = argparse.ArgumentParser(description="find-3c-history — 3C 검출기 회고·검증")
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
    ap.add_argument("--min-cup-depth", type=float, default=DEFAULT_PARAMS["min_cup_depth"])
    ap.add_argument("--max-cup-depth", type=float, default=DEFAULT_PARAMS["max_cup_depth"])
    ap.add_argument("--min-cup-days", type=int, default=DEFAULT_PARAMS["min_cup_days"])
    ap.add_argument("--min-shelf-pullback", type=float, default=DEFAULT_PARAMS["min_shelf_pullback"])
    ap.add_argument("--min-shelf-days", type=int, default=DEFAULT_PARAMS["min_shelf_days"])
    ap.add_argument("--max-shelf-days", type=int, default=DEFAULT_PARAMS["max_shelf_days"])
    ap.add_argument("--max-shelf-depth", type=float, default=DEFAULT_PARAMS["max_shelf_depth"])
    ap.add_argument("--max-shelf-position", type=float, default=DEFAULT_PARAMS["max_shelf_position"])
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

- [ ] **Step 2: Single-ticker debug (저장 안 함)**

입력에서 코드 하나 얻기:
```bash
python -c "import json; d=json.load(open('public/data/sepa-3c-candidates.json',encoding='utf-8')); print([c['code'] for c in d['candidates']][:3])"
```
그 중 하나로:
```bash
python scripts/screen_3c_history.py --ticker <CODE>
```
Expected: 에러 없이 `[3C-history] ...` 요약 + 그 종목 한 줄(분류·최근 이벤트) 출력, 파일 저장 없음.

- [ ] **Step 3: Full run on the 70**

```bash
python scripts/screen_3c_history.py
```
Expected: `💾 저장: ...sepa-3c-history.json` + 분류 표 + 집계 + `⚠️` 딱지. 출력 `stocks` 길이 = 입력 candidates 수(70).

- [ ] **Step 4: Validate schema + invariants**

```bash
python -c "
import json
d=json.load(open('public/data/sepa-3c-history.json',encoding='utf-8'))
s=d['stocks']; print('stocks', len(s), 'with_events', d['summary']['n_with_events'], 'no_3c', d['summary']['n_no_3c_found'], 'events', d['summary']['total_events'])
from collections import Counter; print('class', Counter(x['classification'] for x in s))
assert 'caveat' in d and d['caveat']
assert all('classification' in x and 'events' in x for x in s)
# 이벤트 보유 종목의 이벤트는 근거 키를 가짐
for x in s:
    for e in x['events']:
        assert {'date','confirm_date','pivot_price','cup_depth_pct','shelf_position_pct'} <= set(e)
print('schema+caveat OK')
"
```
Expected: 스키마·딱지 존재, 분류 분포 출력. 이벤트가 일부 종목에서 잡히면(과거 launch 3C) 좋고, 0이어도 스키마는 정상.

- [ ] **Step 5: Commit**

```bash
git add scripts/screen_3c_history.py
git commit -m "feat(find-3c): screen_3c_history.py CLI + 첫 풀런(70종 회고)"
```

---

## Task 3: SKILL.md + 최종 검증

**Files:**
- Create: `.claude/skills/find-3c-history/SKILL.md`

**Interfaces:**
- Consumes: Task 1·2 산출물.
- Produces: `/find-3c-history` 스킬.

- [ ] **Step 1: Write the skill doc**

`.claude/skills/find-3c-history/SKILL.md`:

```markdown
---
name: find-3c-history
description: >
  3C(Cup-Completion Cheat) 검출기 회고·검증 도구(find-vcp-history 형제). find-3c
  후보 종목의 과거 1년을 매 거래일 as-of 로 되짚어, 기존 evaluate_cheat 가 짚어낸
  "3C→돌파" 이벤트·돌파 후 결과·종목 분류(extended/recent_breakout/re_basing/
  no_3c_found)를 sepa-3c-history.json 에 산출한다. 집계 수익률은 생존자 편향 경고와
  함께 참고용. 사용자가 "/find-3c-history", "3c 검증", "과거에 3c 했었나",
  "이 종목 3c 했었나" 등을 요청할 때 사용.
---

# find-3c-history — 3C 검출기 회고·검증

`find-3c` 후보 종목의 과거를 매 거래일 as-of 로 되짚어, 우리 검출기가 그 역사 속
"3C(컵 완성 치트) → 돌파" 시점을 짚어내는지 보여준다. 새 판정 로직 없이 **기존
`evaluate_cheat`(v2b) 재사용**. 정의: `docs/superpowers/specs/2026-06-30-find-3c-history-design.md`.

## 사전 조건
- **최신 데이터로 돌리려면 먼저 `update-data` → `find-trend-template` → `find-3c`** 실행.
- 입력 `public/data/sepa-3c-candidates.json` 존재(= find-3c 산출).

## 실행 (1줄)
\`\`\`
python scripts/screen_3c_history.py
\`\`\`
- 산출: `public/data/sepa-3c-history.json`
- 콘솔: 종목별 분류·최근 이벤트 표 + 집계 + 생존자 편향 딱지.

### 옵션
- `--ticker CODE` : 단일 종목 디버그(저장 안 함).
- `--codes 005930,000660` : 임의 종목.
- `--scan-days 250` : 과거 며칠을 되짚을지(거래일).
- `--confirm-lookback 5` : 돌파 직전 며칠 안에 3C 확인이 있어야 이벤트로 볼지.
- `--recent-days 10` : 최근 돌파 분류 경계.
- `--stop-pct 8` / `--target-pct 20` : good_breakout 경로 판정 손절·목표.
- 3C 임계값(`--min-shelf-days` 등)도 노출 — find-3c 와 동일 검출기.

## 결과 확인
- `classification` : `re_basing`(돌파 후 2차 치트) · `recent_breakout`(최근 돌파) ·
  `extended`(예전 돌파·연장) · `no_3c_found`(이벤트 없음).
- 각 이벤트는 `date`·`confirm_date`·`pivot_price`·`cup_depth_pct`·`shelf_position_pct`·
  돌파 후 결과(gain/max_gain/drawdown/good_breakout)를 근거로 가진다.
- **결정적 검증은 이벤트 날짜를 차트로 직접 눈 대조하는 것.** 집계 수익률은
  RS 상위 승자만 본 결과라 **생존자 편향으로 과대평가**됨(보조 지표).

## 안 하는 것
- 임계값 자동 튜닝 · 실거래 신호 · 공유 파일 갱신 · 자동 commit · 캐시 광역 스캔
  (기본은 find-3c 후보 종목만). find-3c 와 **동일한 검출기**를 써야 검증 의미가 있다.
```

- [ ] **Step 2: Verify frontmatter + full suite**

```bash
python -c "t=open('.claude/skills/find-3c-history/SKILL.md',encoding='utf-8').read(); assert t.startswith('---') and 'name: find-3c-history' in t; print('SKILL OK')"
python -m pytest tests/test_cheat.py tests/test_cheat_oracle.py tests/test_cheat_history.py -q
```
Expected: `SKILL OK` + 전체 테스트 PASS.

- [ ] **Step 3: Confirm option list matches the script**

`### 옵션`에 적은 인자가 `scripts/screen_3c_history.py` argparse 와 일치하는지 대조
(이름·기본값). 불일치 시 **스크립트가 정답** — SKILL 을 맞춘다.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/find-3c-history/SKILL.md
git commit -m "docs(find-3c): find-3c-history SKILL.md"
```

---

## Self-Review (작성자 점검)

**1. Spec coverage:**
- §4.1 replay_cheat → Task 1(replay_cheat + test_replay_cheat_shape). ✓
- §4.2 find_breakout_events(pattern_detected 확인) → Task 1(함수 + 3 테스트). ✓
- §4.3 post_breakout_outcome → Task 1(함수 + 2 테스트). ✓
- §4.4 classify(4 라벨) → Task 1(함수 + 4 테스트). ✓
- §4.5 집계 + 딱지 → Task 2(summary.agg + CAVEAT 콘솔/JSON). ✓
- §5 출력 스키마 → Task 2(output dict). ✓
- §6 구성·CLI 인자 → Task 1·2·3. ✓
- §7 불변 원칙 → Global Constraints + Task 2(no-series·전포함·딱지). ✓
- §8 검증 → Task 1 테스트 / Task 2 Step 2-4 / Task 3 Step 2. ✓

**2. Placeholder scan:** 모든 step 에 실제 코드·명령·기대출력. ✓

**3. Type consistency:** `replay_cheat` 반환 키(pattern_detected·status·pivot_price·
cup_depth_pct·shelf_position_pct)가 `find_breakout_events`·`classify` 에서 동일 소비.
`find_breakout_events` 이벤트 키(date·replay_idx·confirm_date·pivot_price·cup_depth_pct·
shelf_position_pct)가 screen_3c_history 에서 소비(replay_idx 는 pop). `post_breakout_outcome`
반환 키가 이벤트 병합·콘솔 출력과 일치. CLI 인자(min_shelf_days 등)가 DEFAULT_PARAMS
키와 일치. ✓
