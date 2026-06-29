# find-vcp-history Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 트렌드 통과 종목(기본: find-vcp에서 base_too_short로 빠진 30종목)의 과거 1년을 매 거래일 as-of로 되짚어, 기존 `evaluate_vcp`가 짚어낸 "VCP→돌파" 이벤트·돌파 후 결과·종목 분류를 산출하는 검증 도구 `find-vcp-history`.

**Architecture:** 순수 부품 `scripts/canslim_lib/vcp_history.py`(`evaluate_vcp`를 과거 시계열에 반복 적용하는 as-of 리플레이 + 이벤트 탐지/결과/분류)를 TDD로 만들고, CLI `scripts/screen_vcp_history.py`가 종목별로 돌려 `public/data/sepa-vcp-history.json`을 쓴다. 새 판정 로직 없이 기존 검출기를 재사용한다.

**Tech Stack:** Python 3.11+, pytest 9.x, 기존 `canslim_lib.vcp.evaluate_vcp` + `canslim_lib.ohlcv_matrix.get_series`.

**Spec:** `docs/superpowers/specs/2026-06-29-find-vcp-history-design.md`

## Global Constraints

- 새 판정 로직 금지 — 반드시 기존 `evaluate_vcp`(파라미터 동일)만 호출(검증 전제).
- 입력 기본 = `sepa-vcp-candidates.json`의 `reason=="base_too_short"` 종목. `--all`=all_pass, `--codes`=임의.
- 출력 = `sepa-vcp-history.json` 전용. 공유 파일(`sepa-vcp-candidates.json`/`trend-template-*`) 무접촉. 컷오프 금지. 자동 commit 금지.
- 환각 금지: 모든 이벤트 근거(날짜·피벗·수축)와 분류 사유를 출력 JSON에 포함.
- 집계 수익률에는 반드시 생존자-편향 경고(`caveat`) 문구를 출력 JSON과 콘솔에 포함.
- 기본 파라미터: scan_days=250, confirm_lookback=5, recent_days=10, stop_pct=8.0, target_pct=20.0. VCP 임계값은 DEFAULT_PARAMS(lookback_days=120, zigzag_pct=8.0, max_final_depth=10.0, breakout_vol_mult=1.4, near_pivot_pct=5.0).
- Windows 콘솔 안전: 스크립트 상단 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.

---

### Task 1: vcp_history.py — as-of 리플레이 + 돌파 이벤트 탐지

**Files:**
- Create: `scripts/canslim_lib/vcp_history.py`
- Test: `tests/test_vcp_history.py`

**Interfaces:**
- Consumes: `canslim_lib.vcp.evaluate_vcp(series, params) -> dict`.
- Produces:
  - `replay_vcp(series: dict, scan_days: int, params: dict | None = None) -> list[dict]`
    — 마지막 scan_days 거래일 각각에 대해 `{date, vcp_detected, status, pivot_price, contractions}` (시간순).
  - `find_breakout_events(replay: list[dict], confirm_lookback: int = 5) -> list[dict]`
    — 각 이벤트 `{date, replay_idx, confirm_date, pivot_price, contractions}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp_history.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp_history import replay_vcp, find_breakout_events


def _series(closes):
    return {
        "dates": [f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(len(closes))],
        "closes": closes,
        "highs": [c * 1.01 for c in closes],
        "lows": [c * 0.99 for c in closes],
        "volumes": [1000] * len(closes),
    }


def test_replay_returns_one_entry_per_asof_day_with_keys():
    s = _series([100 + i for i in range(40)])
    rep = replay_vcp(s, scan_days=10)
    assert len(rep) == 10                       # 마지막 10 거래일
    assert rep[-1]["date"] == s["dates"][-1]    # 마지막 as-of = 마지막 날
    assert set(rep[0]) == {"date", "vcp_detected", "status", "pivot_price", "contractions"}


def test_find_breakout_events_detects_transition_with_prior_vcp():
    # 합성 replay: day3에 breakout 전환, 직전(day2)에 vcp_detected=true
    rep = [
        {"date": "d0", "vcp_detected": False, "status": "forming", "pivot_price": None, "contractions": []},
        {"date": "d1", "vcp_detected": True,  "status": "actionable", "pivot_price": 100.0, "contractions": [20.0, 8.0]},
        {"date": "d2", "vcp_detected": True,  "status": "actionable", "pivot_price": 100.0, "contractions": [20.0, 8.0]},
        {"date": "d3", "vcp_detected": False, "status": "breakout", "pivot_price": 100.0, "contractions": [20.0, 8.0]},
        {"date": "d4", "vcp_detected": False, "status": "breakout", "pivot_price": 100.0, "contractions": [20.0, 8.0]},
    ]
    evs = find_breakout_events(rep, confirm_lookback=5)
    assert len(evs) == 1                         # 연속 breakout(d4)은 중복 카운트 안 함
    assert evs[0]["date"] == "d3"
    assert evs[0]["replay_idx"] == 3
    assert evs[0]["confirm_date"] == "d2"        # 가장 가까운 직전 vcp_detected
    assert evs[0]["pivot_price"] == 100.0


def test_find_breakout_events_skips_breakout_without_prior_vcp():
    rep = [
        {"date": "d0", "vcp_detected": False, "status": "forming", "pivot_price": None, "contractions": []},
        {"date": "d1", "vcp_detected": False, "status": "breakout", "pivot_price": 50.0, "contractions": []},
    ]
    assert find_breakout_events(rep, confirm_lookback=5) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp_history.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'canslim_lib.vcp_history'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp_history.py
"""find-vcp-history — VCP 검출기 회고·검증 (순수 부품).

기존 evaluate_vcp 를 과거 시계열에 as-of 로 반복 적용한다(새 판정 로직 없음).
정의: docs/superpowers/specs/2026-06-29-find-vcp-history-design.md
"""
from __future__ import annotations

from canslim_lib.vcp import evaluate_vcp

_SERIES_KEYS = ("dates", "closes", "highs", "lows", "volumes", "timestamps")


def replay_vcp(series: dict, scan_days: int, params: dict | None = None) -> list[dict]:
    """마지막 scan_days 거래일 각각을 기준일로 evaluate_vcp 를 재실행.

    시계열을 [:i+1] 로 잘라 넣으면 evaluate_vcp 가 그 시점 마지막 날 기준으로 판정한다.
    """
    dates = series.get("dates") or []
    n = len(dates)
    out: list[dict] = []
    start = max(0, n - scan_days)
    for i in range(start, n):
        sub = {k: (series.get(k) or [])[: i + 1] for k in _SERIES_KEYS if series.get(k) is not None}
        r = evaluate_vcp(sub, params)
        out.append({
            "date": dates[i],
            "vcp_detected": r["vcp_detected"],
            "status": r["status"],
            "pivot_price": r["pivot_price"],
            "contractions": r["contractions"],
        })
    return out


def find_breakout_events(replay: list[dict], confirm_lookback: int = 5) -> list[dict]:
    """status 가 breakout 으로 새로 전환 + 직전 confirm_lookback 내 vcp_detected=true 인 날 = 이벤트."""
    events: list[dict] = []
    for j, cur in enumerate(replay):
        if cur["status"] != "breakout":
            continue
        if j > 0 and replay[j - 1]["status"] == "breakout":
            continue  # 같은 돌파 연속 → 첫 전환만
        confirm = None
        lo = max(0, j - confirm_lookback)
        for k in range(j - 1, lo - 1, -1):
            if replay[k]["vcp_detected"]:
                confirm = replay[k]
                break
        if confirm is None:
            continue
        events.append({
            "date": cur["date"],
            "replay_idx": j,
            "confirm_date": confirm["date"],
            "pivot_price": confirm["pivot_price"],
            "contractions": confirm["contractions"],
        })
    return events
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp_history.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp_history.py tests/test_vcp_history.py
git commit -m "feat(vcp-history): as-of 리플레이 + 돌파 이벤트 탐지 + 테스트"
```

---

### Task 2: vcp_history.py — 돌파 후 결과 + 종목 분류

**Files:**
- Modify: `scripts/canslim_lib/vcp_history.py`
- Test: `tests/test_vcp_history.py`

**Interfaces:**
- Consumes: Task 1 함수들.
- Produces:
  - `post_breakout_outcome(series: dict, event_date: str, stop_pct: float = 8.0, target_pct: float = 20.0) -> dict | None`
    — `{breakout_close, days_since, gain_since_pct, max_gain_pct, max_drawdown_pct, good_breakout}` (event_date 없으면 None).
  - `classify(events: list[dict], replay: list[dict], recent_days: int = 10) -> str`
    — `no_vcp_found | recent_breakout | re_basing | extended`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp_history.py 에 추가
from canslim_lib.vcp_history import post_breakout_outcome, classify


def test_post_breakout_outcome_numbers():
    # 돌파일 종가 100, 이후 110(+10%)·95(-5%)·130(+30%)
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
    assert o["gain_since_pct"] == 30.0           # (130-100)/100
    assert o["max_gain_pct"] == 32.0             # 최고가 132
    assert o["max_drawdown_pct"] == -5.0         # 최저종가 95
    assert o["good_breakout"] is True            # -8% 닿기 전 +20%(132) 도달


def test_post_breakout_outcome_missing_date_returns_none():
    s = {"dates": ["d0"], "closes": [100.0], "highs": [100.0], "lows": [100.0], "volumes": [1]}
    assert post_breakout_outcome(s, "zzz") is None


def test_classify_branches():
    assert classify([], [], recent_days=10) == "no_vcp_found"
    # 최근 돌파: 이벤트가 replay 끝에서 days_since<=recent_days
    rep = [{"vcp_detected": False, "status": "breakout"}] * 12
    ev_recent = [{"replay_idx": 9}]              # len-1-9 = 2 <= 10
    assert classify(ev_recent, rep, recent_days=10) == "recent_breakout"
    # 연장: 오래 전 돌파, 이후 새 vcp 없음
    ev_old = [{"replay_idx": 0}]                 # days_since = 11 > 10
    rep_ext = [{"vcp_detected": False, "status": "extended_dummy"}] * 12
    assert classify(ev_old, rep_ext, recent_days=10) == "extended"
    # 재베이스: 오래 전 돌파 후 vcp_detected 재출현 + 마지막 forming
    rep_reb = [{"vcp_detected": False, "status": "breakout"}] * 12
    rep_reb[5] = {"vcp_detected": True, "status": "forming"}
    rep_reb[-1] = {"vcp_detected": False, "status": "forming"}
    assert classify(ev_old, rep_reb, recent_days=10) == "re_basing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp_history.py -k "outcome or classify" -v`
Expected: FAIL — `ImportError: cannot import name 'post_breakout_outcome'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp_history.py 에 추가
def post_breakout_outcome(series: dict, event_date: str,
                          stop_pct: float = 8.0, target_pct: float = 20.0) -> dict | None:
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
    after_h, after_l, after_c = highs[idx + 1:], lows[idx + 1:], closes[idx + 1:]
    gain_since = (closes[-1] - bc) / bc * 100.0
    max_gain = max(((h - bc) / bc * 100.0 for h in after_h), default=0.0)
    max_dd = min(((c - bc) / bc * 100.0 for c in after_c), default=0.0)
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
    if not events:
        return "no_vcp_found"
    idx = events[-1]["replay_idx"]
    days_since = (len(replay) - 1) - idx
    if days_since <= recent_days:
        return "recent_breakout"
    later_vcp = any(replay[k].get("vcp_detected") for k in range(idx + 1, len(replay)))
    if later_vcp and replay[-1].get("status") in ("forming", "actionable"):
        return "re_basing"
    return "extended"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp_history.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp_history.py tests/test_vcp_history.py
git commit -m "feat(vcp-history): 돌파 후 결과 + 종목 분류 + 테스트"
```

---

### Task 3: screen_vcp_history.py — CLI 오케스트레이터

**Files:**
- Create: `scripts/screen_vcp_history.py`

**Interfaces:**
- Consumes: `canslim_lib.vcp_history`(Task 1·2), `canslim_lib.vcp.DEFAULT_PARAMS`, `canslim_lib.ohlcv_matrix.get_series`.
- Produces: `public/data/sepa-vcp-history.json` (spec §5 스키마).

- [ ] **Step 1: Write the script**

```python
# scripts/screen_vcp_history.py
"""find-vcp-history — VCP 검출기 회고·검증.

입력: public/data/sepa-vcp-candidates.json (기본 reason==base_too_short 종목)
출력: public/data/sepa-vcp-history.json
정의: docs/superpowers/specs/2026-06-29-find-vcp-history-design.md
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
from canslim_lib.vcp import DEFAULT_PARAMS  # noqa: E402
from canslim_lib.vcp_history import (  # noqa: E402
    replay_vcp, find_breakout_events, post_breakout_outcome, classify,
)

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-vcp-candidates.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-vcp-history.json"
CAVEAT = ("집계 수익률은 RS90+ 승자 종목만 본 결과라 생존자 편향으로 과대평가됨. "
          "검출기 신뢰의 보조 지표일 뿐, 결정적 검증은 이벤트 날짜를 차트로 눈 대조하는 것.")
CLASS_ORDER = {"re_basing": 0, "recent_breakout": 1, "extended": 2, "no_vcp_found": 3}


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def run(args, out_path: Path) -> None:
    in_path = Path(args.inp) if args.inp else IN_PATH
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.exists():
        print(f"❌ 입력 파일 없음: {in_path.relative_to(ROOT)}\n"
              f"   먼저 find-vcp 를 실행해 sepa-vcp-candidates.json 을 생성하세요.")
        sys.exit(1)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    cands = data.get("candidates", [])
    by_code = {c["code"]: c for c in cands}

    if args.codes:
        codes = [x.strip() for x in args.codes.split(",") if x.strip()]
        filt = "codes"
    elif args.all:
        codes = [c["code"] for c in cands]
        filt = "all"
    else:
        codes = [c["code"] for c in cands if c.get("reason") == "base_too_short"]
        filt = "base_too_short"

    params = {
        "lookback_days": args.lookback_days, "zigzag_pct": args.zigzag_pct,
        "max_final_depth": args.max_final_depth, "breakout_vol_mult": args.breakout_vol_mult,
        "near_pivot_pct": DEFAULT_PARAMS["near_pivot_pct"],
    }

    stocks = []
    for code in codes:
        meta = by_code.get(code, {})
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            stocks.append({"code": code, "name": meta.get("name"), "market": meta.get("market"),
                           "rs": meta.get("rs"), "classification": "no_vcp_found",
                           "num_events": 0, "most_recent_event_date": None, "events": [],
                           "reason": "no_series"})
            continue
        rep = replay_vcp(s, args.scan_days, params)
        raw = find_breakout_events(rep, args.confirm_lookback)
        events = []
        for e in raw:
            o = post_breakout_outcome(s, e["date"], args.stop_pct, args.target_pct) or {}
            events.append({**e, **o})
            events[-1].pop("replay_idx", None)
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
        "n_no_vcp_found": sum(1 for st in stocks if st["classification"] == "no_vcp_found"),
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

    print(f"\n[VCP-history] 입력 {summary['n_stocks']}종목({filt}) | "
          f"이벤트보유 {summary['n_with_events']} · 미검출 {summary['n_no_vcp_found']} | "
          f"총 이벤트 {summary['total_events']}")
    for st in stocks:
        ev = st["events"][-1] if st["events"] else None
        tail = (f"최근 {ev['date']} 피벗 {ev['pivot_price']} → 현재 {ev.get('gain_since_pct')}% "
                f"(최대 {ev.get('max_gain_pct')}%, {ev.get('days_since')}일 경과)") if ev else "-"
        print(f"  [{st['classification']:15s}] {st['code']} {str(st['name'])[:12]:12s} "
              f"RS{st.get('rs')} | {tail}")
    agg = summary["agg"]
    print(f"\n[집계·참고용] 돌파후 수익률 중앙 {agg['median_gain_since_pct']}% · "
          f"최대 중앙 {agg['median_max_gain_pct']}% · good_breakout율 {agg['good_breakout_rate']}")
    print(f"⚠️ {CAVEAT}")


def main():
    ap = argparse.ArgumentParser(description="find-vcp-history — VCP 검출기 회고·검증")
    ap.add_argument("--in", dest="inp", default=None, help=f"입력(default {IN_PATH.name})")
    ap.add_argument("--out", dest="out", default=None, help=f"출력(default {OUT_PATH.name})")
    ap.add_argument("--all", action="store_true", help="all_pass 전체(기본은 base_too_short)")
    ap.add_argument("--codes", default=None, help="임의 코드 목록 쉼표구분 (예 005930,000660)")
    ap.add_argument("--ticker", default=None, help="단일 종목 디버그(저장 안 함)")
    ap.add_argument("--scan-days", type=int, default=250)
    ap.add_argument("--confirm-lookback", type=int, default=5)
    ap.add_argument("--recent-days", type=int, default=10)
    ap.add_argument("--stop-pct", type=float, default=8.0)
    ap.add_argument("--target-pct", type=float, default=20.0)
    ap.add_argument("--lookback-days", type=int, default=DEFAULT_PARAMS["lookback_days"])
    ap.add_argument("--zigzag-pct", type=float, default=DEFAULT_PARAMS["zigzag_pct"])
    ap.add_argument("--max-final-depth", type=float, default=DEFAULT_PARAMS["max_final_depth"])
    ap.add_argument("--breakout-vol-mult", type=float, default=DEFAULT_PARAMS["breakout_vol_mult"])
    args = ap.parse_args()
    if args.ticker:
        args.codes = args.ticker
    out_path = (Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out) if args.out else OUT_PATH
    run(args, out_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-run single ticker (no save)**

Run: `python -X utf8 scripts/screen_vcp_history.py --ticker 005930`
Expected: `[VCP-history]` 요약 + 삼성전자 한 줄 + 집계·⚠️ 경고. 에러 없음. 저장 라인 없음.

- [ ] **Step 3: Full run (base_too_short 30종목)**

Run: `python -X utf8 scripts/screen_vcp_history.py`
Expected: `💾 저장: ...sepa-vcp-history.json` + 30종목 분류 표 + 집계 + ⚠️ 경고. classification 분포가 합리적(상당수 extended 예상).

- [ ] **Step 4: Sanity-check output**

Run:
```bash
python -X utf8 -c "import json,collections;d=json.load(open('public/data/sepa-vcp-history.json',encoding='utf-8'));print('filter',d['input_filter'],'n',len(d['stocks']),'caveat?',bool(d['caveat']));print(collections.Counter(s['classification'] for s in d['stocks']))"
```
Expected: `filter base_too_short`, n=30(현재), caveat 존재(True), classification Counter 출력. 분포 합 = n.

- [ ] **Step 5: Commit**

```bash
git add scripts/screen_vcp_history.py public/data/sepa-vcp-history.json
git commit -m "feat(vcp-history): screen_vcp_history CLI + 첫 산출"
```

---

### Task 4: find-vcp-history 스킬 문서

**Files:**
- Create: `.claude/skills/find-vcp-history/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: find-vcp-history
description: >
  VCP 검출기 회고·검증 도구. find-vcp 에서 base_too_short 로 빠진(신고가 직진) 종목들의
  과거 1년을 매 거래일 as-of 로 되짚어, 기존 evaluate_vcp 가 짚어낸 "VCP→돌파" 이벤트·
  돌파 후 결과·종목 분류(extended/recent_breakout/re_basing/no_vcp_found)를 sepa-vcp-
  history.json 에 산출한다. 집계 수익률은 생존자 편향 경고와 함께 참고용. 사용자가
  "/find-vcp-history", "VCP 검증", "과거 돌파 짚어줘", "이 종목 이미 돌파했나" 등을 요청할 때 사용.
---

# find-vcp-history — VCP 검출기 회고·검증

`find-vcp`(SEPA 2단계)에서 신고가 직진으로 `base_too_short` 처리된 종목이, 과거에
정말 VCP→돌파를 거쳤는지 **기존 검출기를 과거에 그대로 적용**해 짚어낸다.
1순위 용도 = 검출기 검증(이벤트 날짜를 차트로 눈 대조).
정의: `docs/superpowers/specs/2026-06-29-find-vcp-history-design.md`.

## 사전 조건
- 먼저 `update-data` → `find-trend-template` → `find-vcp` 를 돌려 입력
  `public/data/sepa-vcp-candidates.json` 이 있어야 한다.

## 실행
```
python scripts/screen_vcp_history.py
```
- 산출: `public/data/sepa-vcp-history.json`
- 콘솔: 종목별 분류·최근 돌파 이벤트 + 집계(⚠️ 생존자 편향 경고).

### 옵션
- `--ticker 005930` : 단일 종목(저장 안 함).
- `--all` : all_pass 전체(기본은 base_too_short만). `--codes 005930,000660` : 임의.
- `--scan-days 250` `--confirm-lookback 5` `--recent-days 10` `--stop-pct 8` `--target-pct 20`
- VCP 임계값(`--zigzag-pct` 등)은 find-vcp 와 동일(같은 검출기를 써야 검증 의미).

## 결과 보는 법
- `classification`: extended(이미 돌파·연장=추격 늦음) / recent_breakout(최근 돌파) /
  re_basing(돌파 후 2차 베이스) / no_vcp_found(검출 0=미스 의심 또는 패턴 없음).
- `events[].date` 를 차트로 열어 "진짜 VCP 돌파였나" 눈으로 확인 = 진짜 검증.
- 집계 수익률은 **생존자 편향으로 과대** — 보조 지표로만.

## 안 하는 것
- 새 판정 로직(기존 evaluate_vcp 재사용) · 임계값 자동 튜닝 · 실거래 신호 ·
  공유 파일 갱신 · 자동 commit.
```

- [ ] **Step 2: Verify skill is discoverable**

Run: `python -c "import pathlib; t=pathlib.Path('.claude/skills/find-vcp-history/SKILL.md').read_text(encoding='utf-8'); assert t.startswith('---') and 'name: find-vcp-history' in t; print('skill ok')"`
Expected: `skill ok`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/find-vcp-history/SKILL.md
git commit -m "docs(vcp-history): find-vcp-history 스킬 문서"
```

---

## Self-Review 결과 (작성자 점검)

- **Spec 커버리지**: §4.1 replay(Task1) · §4.2 이벤트(Task1) · §4.3 결과(Task2) · §4.4 분류(Task2) · §4.5 집계+caveat(Task3) · §5 스키마(Task3) · §6 구성(Task1~4) · §7 불변원칙(Global Constraints) · §8 검증(Task1~2 단위테스트·Task3 풀런) 전부 태스크 존재.
- **타입 일관성**: `replay_vcp/find_breakout_events/post_breakout_outcome/classify` 시그니처가 Task1·2 정의와 Task3 사용처에서 일치. 이벤트 dict 키(date/replay_idx/confirm_date/pivot_price/contractions)·결과 키(breakout_close/days_since/gain_since_pct/max_gain_pct/max_drawdown_pct/good_breakout) 일치. CLI는 `events`에서 `replay_idx`를 제거해 출력(내부용 키 노출 방지).
- **이벤트 로직 테스트 격리**: find_breakout_events/post/classify 테스트는 합성 dict로 evaluate_vcp 임계값과 분리 → 견고. replay_vcp는 키·개수만 검증(값은 evaluate_vcp 의존이라 단정 안 함).
- **미해결**: Task3 풀런의 classification 실제 분포는 데이터 의존(상당수 extended 예상). 만약 전부 no_vcp_found 로 나오면 confirm_lookback/scan_days 또는 evaluate_vcp 돌파 판정과의 상호작용 점검 필요 — Task3에서 관찰·보고.
