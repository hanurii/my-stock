# SEPA 피벗 백테스트 (2026-04-01) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 2026-04-01 시점 전 종목 point-in-time SEPA 게이트 통과 종목의 패턴 피벗 돌파를 +10%/-5% 선착으로 시뮬(돌파일 포함, 같은날 둘다=예외)하고, 승자 특징을 분석해 리포트+JSON을 낸다.

**Architecture:** 순수 로직(시뮬·특징·집계)은 `scripts/canslim_lib/pivot_backtest.py`에 두고 pytest로 검증. 오케스트레이터 `scripts/pivot_backtest.py`가 캐시 순회·트렌드 asof·패턴 검출을 엮어 이벤트를 만들고 시뮬·집계 후 JSON·리포트를 쓴다. 기존 트렌드/RS/패턴 검출 모듈을 재사용.

**Tech Stack:** Python 3 · pytest · 기존 canslim_lib(ohlcv_matrix·trend_template·vcp/power_play/cheat_history) 재사용

## Global Constraints

- 작업 위치: 워크트리 `C:\Users\hanul\playground\my-stock-pivot-bt`, 브랜치 `feat/pivot-backtest`(origin/master 기준). 모든 경로 이 워크트리 기준.
- OHLCV 캐시(`.cache`)는 정션으로 연결됨(설정 완료). 스크립트는 이 워크트리에서 실행. `.cache`는 gitignore(커밋 안 됨).
- 기준일 **D = 2026-04-01**. 전진 데이터 = 캐시 마지막(2026-07-06)까지 64거래일.
- 시뮬: 피벗 매수, target=+10%·stop=-5%, 장중 선착. **돌파일(b) 포함**. 결과 = `win|loss|ambiguous|unresolved`.
  - 돌파일: 고가≥T & 저가≤S → ambiguous / 고가≥T → win / 저가≤S만 → ambiguous(매수 전 저점) / 아니면 다음날.
  - 이후날: 고가≥T & 저가≤S → ambiguous / 고가≥T → win / 저가≤S → loss / 아니면 다음날.
  - 끝까지 → unresolved.
- 트렌드 게이트: `evaluate_trend_template`(8조건) + RS ≥ 80(as-of D 교차순위).
- 엔트리: 패턴 돌파 이벤트 중 **돌파일이 D 이하 마지막 10거래일 이내**인 최근 이벤트. 패턴(VCP/PP/3C)별로 각각 1엔트리.
- 산출: `public/data/pivot-backtest-2026-04-01.json`(커밋) + `docs/research/2026-04-01-pivot-backtest.md`(커밋). ambiguous 예외 목록 포함.
- 스펙: `docs/superpowers/specs/2026-07-07-pivot-backtest-design.md`.
- 파이썬 테스트: `python -m pytest`. 커밋 자주. TDD(순수 로직).

---

### Task 1: 순수 시뮬 + 특징 헬퍼 (`pivot_backtest.py` 로직, TDD)

**Files:**
- Create: `scripts/canslim_lib/pivot_backtest.py`
- Test: `tests/test_pivot_backtest.py`

**Interfaces:**
- Produces: `simulate_pivot_trade(series, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0) -> dict`(result·resolve_date·days_held·exit_reason·gain_at_resolve_pct·max_gain_pct·max_dd_pct); `price_bucket(p) -> str`; `rel_volume(series, idx, window=50) -> float|None`; `truncate_series(series, asof) -> dict`.

- [ ] **Step 1: Write the failing tests**

`tests/test_pivot_backtest.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.pivot_backtest import (
    simulate_pivot_trade, price_bucket, rel_volume, truncate_series,
)


def mk(highs, lows, closes=None, dates=None, volumes=None):
    n = len(highs)
    closes = closes or [(highs[i] + lows[i]) / 2 for i in range(n)]
    dates = dates or [f"2026-04-{i+1:02d}" for i in range(n)]
    return {"dates": dates, "closes": closes, "opens": list(closes),
            "highs": list(highs), "lows": list(lows),
            "volumes": volumes or [1000.0] * n}


def test_breakout_day_target_is_win():
    # 돌파일(b=0) 고가가 +10% 도달, 저가는 피벗 위 → win
    s = mk(highs=[112.0, 100.0], lows=[100.0, 99.0], dates=["2026-04-01", "2026-04-02"])
    r = simulate_pivot_trade(s, 0, 100.0)
    assert r["result"] == "win" and r["days_held"] == 0


def test_breakout_day_stop_only_is_ambiguous():
    # 돌파일 저가만 -5% 이하(고가는 +10% 미만) → ambiguous(매수 전 저점)
    s = mk(highs=[104.0, 104.0], lows=[94.0, 96.0])
    r = simulate_pivot_trade(s, 0, 100.0)
    assert r["result"] == "ambiguous" and r["exit_reason"] == "stop_on_breakout_day"


def test_breakout_day_both_is_ambiguous():
    s = mk(highs=[112.0, 104.0], lows=[94.0, 96.0])
    r = simulate_pivot_trade(s, 0, 100.0)
    assert r["result"] == "ambiguous" and "both" in r["exit_reason"]


def test_later_day_win_and_loss():
    # b=0 은 무결착, 1일차 고가만 +10% → win
    s = mk(highs=[103.0, 111.0], lows=[99.0, 101.0])
    assert simulate_pivot_trade(s, 0, 100.0)["result"] == "win"
    # 1일차 저가만 -5% → loss
    s2 = mk(highs=[103.0, 104.0], lows=[99.0, 94.0])
    r2 = simulate_pivot_trade(s2, 0, 100.0)
    assert r2["result"] == "loss" and r2["days_held"] == 1


def test_later_day_both_is_ambiguous():
    s = mk(highs=[103.0, 111.0], lows=[99.0, 94.0])
    assert simulate_pivot_trade(s, 0, 100.0)["result"] == "ambiguous"


def test_unresolved_reports_gain():
    s = mk(highs=[103.0, 104.0, 105.0], lows=[99.0, 98.0, 100.0],
           closes=[102.0, 103.0, 104.0])
    r = simulate_pivot_trade(s, 0, 100.0)
    assert r["result"] == "unresolved" and r["gain_at_resolve_pct"] == 4.0


def test_price_bucket_and_rel_volume():
    assert price_bucket(1500) == "<2천"
    assert price_bucket(12000) == "1~2만"
    assert price_bucket(80000) == "5만+"
    s = mk(highs=[1]*60, lows=[1]*60, volumes=[100.0]*50 + [200.0]*10)
    assert rel_volume(s, 55, window=50) == 2.0  # 직전 50일 평균 100, 당일 200


def test_truncate_series():
    s = mk(highs=[1, 2, 3], lows=[1, 2, 3], dates=["2026-04-01", "2026-04-02", "2026-04-03"])
    t = truncate_series(s, "2026-04-02")
    assert t["dates"] == ["2026-04-01", "2026-04-02"] and len(t["closes"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pivot_backtest.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` (pivot_backtest 없음).

- [ ] **Step 3: Implement `pivot_backtest.py`**

`scripts/canslim_lib/pivot_backtest.py`:

```python
# scripts/canslim_lib/pivot_backtest.py
"""SEPA 피벗 백테스트 순수 로직 — 시뮬·특징·집계.
정의: docs/superpowers/specs/2026-07-07-pivot-backtest-design.md
"""
from __future__ import annotations

PRICE_BUCKETS = [(2000, "<2천"), (5000, "2~5천"), (10000, "5~1만"),
                 (20000, "1~2만"), (50000, "2~5만"), (float("inf"), "5만+")]


def price_bucket(p: float) -> str:
    for hi, label in PRICE_BUCKETS:
        if p < hi:
            return label
    return "5만+"


def rel_volume(series, idx, window=50):
    """idx일 거래량 ÷ 직전 window 거래일 평균(idx 제외). 표본/데이터 없으면 None."""
    vols = series["volumes"]
    lo = max(0, idx - window)
    sample = [v for v in vols[lo:idx] if v]
    if not sample or vols[idx] is None:
        return None
    return round(vols[idx] / (sum(sample) / len(sample)), 2)


def truncate_series(series, asof: str) -> dict:
    """dates <= asof 로 모든 배열을 자른 새 series dict."""
    dates = series["dates"]
    keep = sum(1 for d in dates if d <= asof)
    return {k: (v[:keep] if isinstance(v, list) else v) for k, v in series.items()}


def _result(result, series, b, i, pivot, reason):
    closes, highs, lows, dates = (series["closes"], series["highs"],
                                  series["lows"], series["dates"])
    seg_h = [h for h in highs[b:i + 1] if h is not None]
    seg_l = [l for l in lows[b:i + 1] if l is not None]
    max_gain = (max(seg_h) / pivot - 1) * 100 if seg_h else 0.0
    max_dd = (min(seg_l) / pivot - 1) * 100 if seg_l else 0.0
    return {
        "result": result,
        "resolve_date": dates[i],
        "days_held": i - b,
        "exit_reason": reason,
        "gain_at_resolve_pct": round((closes[i] / pivot - 1) * 100, 2),
        "max_gain_pct": round(max_gain, 2),
        "max_dd_pct": round(max_dd, 2),
    }


def simulate_pivot_trade(series, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0):
    """피벗 매수 후 +target%/-stop% 선착 판정. 돌파일 포함, 같은날 둘다=ambiguous."""
    highs, lows = series["highs"], series["lows"]
    n = len(series["closes"])
    T = pivot * (1 + target_pct / 100)
    S = pivot * (1 - stop_pct / 100)
    b = breakout_idx
    for i in range(b, n):
        hi, lo = highs[i], lows[i]
        hit_t = hi is not None and hi >= T
        hit_s = lo is not None and lo <= S
        if i == b:
            if hit_t and hit_s:
                return _result("ambiguous", series, b, i, pivot, "both_same_day_breakout")
            if hit_t:
                return _result("win", series, b, i, pivot, "target")
            if hit_s:
                return _result("ambiguous", series, b, i, pivot, "stop_on_breakout_day")
        else:
            if hit_t and hit_s:
                return _result("ambiguous", series, b, i, pivot, "both_same_day")
            if hit_t:
                return _result("win", series, b, i, pivot, "target")
            if hit_s:
                return _result("loss", series, b, i, pivot, "stop")
    return _result("unresolved", series, b, n - 1, pivot, "open")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pivot_backtest.py -v`
Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/pivot_backtest.py tests/test_pivot_backtest.py
git commit -m "feat(pivot-backtest): simulate_pivot_trade + 특징 헬퍼(순수 로직·TDD)"
```

---

### Task 2: 집계 (`aggregate`) — 특징 구간별 승률 (TDD)

**Files:**
- Modify: `scripts/canslim_lib/pivot_backtest.py`
- Test: `tests/test_pivot_backtest.py`

**Interfaces:**
- Consumes: 이벤트 dict 목록(각 `{result, pattern, market, price_bucket, rel_vol_bucket, rs_bucket, ...}`).
- Produces: `tally(events) -> dict`(n·win·loss·ambiguous·unresolved·win_rate_resolved); `group_win_rate(events, key) -> dict[bucket -> tally]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_pivot_backtest.py` 하단에 추가:

```python
from canslim_lib.pivot_backtest import tally, group_win_rate


def _ev(result, **kw):
    return {"result": result, **kw}


def test_tally_counts_and_resolved_win_rate():
    evs = [_ev("win"), _ev("win"), _ev("loss"), _ev("ambiguous"), _ev("unresolved")]
    t = tally(evs)
    assert t["n"] == 5 and t["win"] == 2 and t["loss"] == 1
    assert t["ambiguous"] == 1 and t["unresolved"] == 1
    # 결착 승률 = 승/(승+패) = 2/3
    assert t["win_rate_resolved"] == round(2 / 3 * 100, 1)


def test_tally_no_resolved_is_none():
    assert tally([_ev("ambiguous"), _ev("unresolved")])["win_rate_resolved"] is None


def test_group_win_rate_by_key():
    evs = [_ev("win", pattern="VCP"), _ev("loss", pattern="VCP"),
           _ev("win", pattern="3C")]
    g = group_win_rate(evs, "pattern")
    assert g["VCP"]["n"] == 2 and g["VCP"]["win_rate_resolved"] == 50.0
    assert g["3C"]["win"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pivot_backtest.py -k "tally or group_win_rate" -v`
Expected: FAIL — `ImportError` (tally/group_win_rate 없음).

- [ ] **Step 3: Implement**

`pivot_backtest.py`에 추가:

```python
def tally(events) -> dict:
    """결과별 개수 + 결착(win/loss) 승률."""
    n = len(events)
    c = {"win": 0, "loss": 0, "ambiguous": 0, "unresolved": 0}
    for e in events:
        c[e["result"]] = c.get(e["result"], 0) + 1
    resolved = c["win"] + c["loss"]
    wr = round(c["win"] / resolved * 100, 1) if resolved else None
    return {"n": n, **c, "win_rate_resolved": wr}


def group_win_rate(events, key) -> dict:
    """key 값별 tally. key 값이 None/누락이면 '미상' 버킷."""
    groups: dict[str, list] = {}
    for e in events:
        groups.setdefault(e.get(key) or "미상", []).append(e)
    return {k: tally(v) for k, v in sorted(groups.items())}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pivot_backtest.py -v`
Expected: 전부 PASS(11개).

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/pivot_backtest.py tests/test_pivot_backtest.py
git commit -m "feat(pivot-backtest): tally·group_win_rate 집계(TDD)"
```

---

### Task 3: 오케스트레이터 `scripts/pivot_backtest.py` — 이벤트 생성 + JSON

**Files:**
- Create: `scripts/pivot_backtest.py`

**Interfaces:**
- Consumes: `ohlcv_matrix.get_series`; `trend_template.evaluate_trend_template`; `screen_trend_template._compute_rs_for_all`; `pykrx_universe.fetch_universe_with_cap`; `vcp_history`/`power_play_history`/`cheat_history`의 `replay_*`·`find_breakout_events`; Task1·2의 `pivot_backtest` 로직.
- Produces: `public/data/pivot-backtest-2026-04-01.json` = `{params, generated_at, summary, by_pattern, by_feature, events[], ambiguous[]}`.

- [ ] **Step 1: Write the orchestrator**

`scripts/pivot_backtest.py`:

```python
# scripts/pivot_backtest.py
"""SEPA 피벗 백테스트 오케스트레이터 (단일 기준일 스냅샷).
실행: python scripts/pivot_backtest.py --asof 2026-04-01
정의: docs/superpowers/specs/2026-07-07-pivot-backtest-design.md
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import ohlcv_matrix  # noqa: E402
from canslim_lib.trend_template import evaluate_trend_template  # noqa: E402
from canslim_lib.pivot_backtest import (  # noqa: E402
    simulate_pivot_trade, price_bucket, rel_volume, truncate_series,
    tally, group_win_rate,
)
from canslim_lib import vcp_history, power_play_history, cheat_history  # noqa: E402
from screen_trend_template import _compute_rs_for_all  # noqa: E402
from canslim_lib.pykrx_universe import fetch_universe_with_cap  # noqa: E402

KST = timezone(timedelta(hours=9))
RS_MIN = 80
ENTRY_WINDOW = 10   # 돌파일이 asof 이하 마지막 10거래일 이내
SCAN_DAYS = 250
PATTERNS = [("VCP", vcp_history.replay_vcp, vcp_history.find_breakout_events),
            ("PP", power_play_history.replay_power_play, power_play_history.find_breakout_events),
            ("3C", cheat_history.replay_cheat, cheat_history.find_breakout_events)]


def rs_bucket(rs):
    if rs is None:
        return "미상"
    return "95~100" if rs >= 95 else "90~94" if rs >= 90 else "80~89"


def relvol_bucket(rv):
    if rv is None:
        return "미상"
    return "3+" if rv >= 3 else "2~3" if rv >= 2 else "1.5~2" if rv >= 1.5 else "1~1.5" if rv >= 1 else "<1"


def run(asof: str) -> dict:
    universe = fetch_universe_with_cap("ALL")
    meta = {u["code"]: u for u in universe}
    codes = sorted(meta.keys())
    print(f"유니버스 {len(codes)}종목 · 기준일 {asof}")

    # 1) as-of 시계열 수집 + RS 계산
    asof_series, rows = {}, []
    for code in codes:
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            continue
        st = truncate_series(s, asof)
        if len(st["closes"]) < 200:      # 트렌드/RS 최소 데이터
            continue
        asof_series[code] = (s, st)
        rows.append({"code": code, "closes": st["closes"], "ok": True})
    rs_map = _compute_rs_for_all(rows)   # {code: {rs, ...}}
    print(f"시계열 확보 {len(asof_series)} · RS 산출 {sum(1 for v in rs_map.values() if v.get('rs'))}")

    # 2) 트렌드 게이트 → 3) 패턴 돌파 → 4) 시뮬
    events, ambiguous = [], []
    n_pass = 0
    for code, (full, st) in asof_series.items():
        rs = (rs_map.get(code) or {}).get("rs")
        tt = evaluate_trend_template(st["closes"], rs=rs, rs_min=RS_MIN)
        if not tt["pass"]:
            continue
        n_pass += 1
        last10 = set(st["dates"][-ENTRY_WINDOW:])
        for pname, replay_fn, events_fn in PATTERNS:
            rep = replay_fn(st, SCAN_DAYS, None)
            for ev in events_fn(rep):
                if ev["date"] not in last10:
                    continue
                pivot = ev["pivot_price"]
                if not pivot:
                    continue
                bi = full["dates"].index(ev["date"])
                sim = simulate_pivot_trade(full, bi, pivot)
                rec = {
                    "code": code, "name": meta[code].get("name", code),
                    "market": meta[code].get("market"), "pattern": pname,
                    "breakout_date": ev["date"], "pivot": round(pivot, 2),
                    "rs": rs, "price_bucket": price_bucket(pivot),
                    "rel_vol": rel_volume(full, bi), **sim,
                }
                rec["rel_vol_bucket"] = relvol_bucket(rec["rel_vol"])
                rec["rs_bucket"] = rs_bucket(rs)
                events.append(rec)
                if sim["result"] == "ambiguous":
                    ambiguous.append(rec)
    print(f"트렌드 통과 {n_pass} · 엔트리 이벤트 {len(events)} · ambiguous {len(ambiguous)}")

    by_feature = {k: group_win_rate(events, k)
                  for k in ("pattern", "market", "price_bucket", "rel_vol_bucket", "rs_bucket")}
    return {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": {"asof": asof, "target_pct": 10, "stop_pct": 5,
                   "rs_min": RS_MIN, "entry_window": ENTRY_WINDOW,
                   "forward_last": full["dates"][-1] if asof_series else None},
        "summary": tally(events),
        "by_pattern": group_win_rate(events, "pattern"),
        "by_feature": by_feature,
        "events": events,
        "ambiguous": ambiguous,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default="2026-04-01")
    args = ap.parse_args()
    out = run(args.asof)
    p = ROOT / "public" / "data" / f"pivot-backtest-{args.asof}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"💾 저장: {p.relative_to(ROOT)}")
    s = out["summary"]
    print(f"\n총 {s['n']} · 승 {s['win']} 패 {s['loss']} 예외 {s['ambiguous']} 미결 {s['unresolved']} "
          f"· 결착승률 {s['win_rate_resolved']}%")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-run on a tiny slice**

먼저 소규모로 임포트·배선이 맞는지 확인. 임시로 `fetch_universe_with_cap("ALL")` 대신 앞 200종목만 돌려보려면 `codes = sorted(meta.keys())[:200]` 로 잠깐 바꿔 실행 후 되돌린다. 실행:
Run: `python scripts/pivot_backtest.py --asof 2026-04-01`
Expected: 오류 없이 `유니버스 … · RS 산출 …`, `트렌드 통과 … · 엔트리 이벤트 …`, `💾 저장:` 출력. (임포트/배선 문제가 있으면 여기서 드러남 → 고친다. 200종목 슬라이스로 확인했으면 전체로 되돌린다.)

- [ ] **Step 3: Full run → JSON 생성**

Run: `python scripts/pivot_backtest.py --asof 2026-04-01`
Expected: `public/data/pivot-backtest-2026-04-01.json` 생성. 콘솔에 총계·결착승률.

- [ ] **Step 4: Sanity 확인**

Run:
```bash
python -c "import json; d=json.load(open('public/data/pivot-backtest-2026-04-01.json',encoding='utf-8')); print('events', len(d['events']), '| summary', d['summary']); print('by_pattern', {k:v['win_rate_resolved'] for k,v in d['by_pattern'].items()})"
```
Expected: events > 0, summary 총계 합이 n과 일치, by_pattern 승률 출력. (events 0이면 엔트리 창/게이트를 점검 — 예: ENTRY_WINDOW·RS_MIN·SCAN_DAYS. 원인 로그를 보고 조정하되 스펙 파라미터(RS80·window10)는 유지.)

- [ ] **Step 5: Commit**

```bash
git add scripts/pivot_backtest.py public/data/pivot-backtest-2026-04-01.json
git commit -m "feat(pivot-backtest): 오케스트레이터 + 2026-04-01 결과 JSON"
```

---

### Task 4: 리포트 생성 + 인사이트

**Files:**
- Create: `scripts/pivot_backtest_report.py`
- Create(생성물): `docs/research/2026-04-01-pivot-backtest.md`

**Interfaces:**
- Consumes: `public/data/pivot-backtest-2026-04-01.json`.

- [ ] **Step 1: Write the report generator**

`scripts/pivot_backtest_report.py`:

```python
# scripts/pivot_backtest_report.py
"""pivot-backtest JSON → 마크다운 리포트."""
from __future__ import annotations
import json, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
ASOF = "2026-04-01"
IN = ROOT / "public" / "data" / f"pivot-backtest-{ASOF}.json"
OUT = ROOT / "docs" / "research" / f"{ASOF}-pivot-backtest.md"


def wr(t):
    return "-" if t["win_rate_resolved"] is None else f"{t['win_rate_resolved']}%"


def table(title, groups):
    rows = [f"### {title}\n", "| 구간 | n | 승 | 패 | 예외 | 미결 | 결착승률 |",
            "|---|--:|--:|--:|--:|--:|--:|"]
    for k, t in groups.items():
        rows.append(f"| {k} | {t['n']} | {t['win']} | {t['loss']} | {t['ambiguous']} | {t['unresolved']} | {wr(t)} |")
    return "\n".join(rows) + "\n"


def main():
    d = json.loads(IN.read_text(encoding="utf-8"))
    p, s = d["params"], d["summary"]
    L = []
    L.append(f"# SEPA 피벗 백테스트 — {ASOF} 스냅샷\n")
    L.append(f"> 생성 {d['generated_at']} · 기준일 {p['asof']} · 전진 마지막 {p['forward_last']} "
             f"· 목표 +{p['target_pct']}% / 손절 -{p['stop_pct']}% · RS≥{p['rs_min']}\n")
    L.append(f"**총 {s['n']}건** — 승 {s['win']} · 패 {s['loss']} · 예외(ambiguous) {s['ambiguous']} "
             f"· 미결(unresolved) {s['unresolved']} · **결착 승률 {wr(s)}**\n")
    L.append("> 결착 승률 = 승 / (승+패). 예외=일봉으로 선착 판별 불가(분봉 확인 필요), 미결=창 내 미도달.\n")
    L.append(table("패턴별", d["by_pattern"]))
    for label, key in [("시장", "market"), ("가격대", "price_bucket"),
                       ("돌파일 상대거래량", "rel_vol_bucket"), ("RS 구간", "rs_bucket")]:
        L.append(table(label, d["by_feature"][key]))
    # 인사이트: 결착 표본 ≥ 5 인 버킷 중 승률 최고/최저
    cand = []
    for key, groups in d["by_feature"].items():
        for k, t in groups.items():
            if t["win"] + t["loss"] >= 5 and t["win_rate_resolved"] is not None:
                cand.append((t["win_rate_resolved"], key, k, t))
    if cand:
        cand.sort(reverse=True)
        hi, lo = cand[0], cand[-1]
        L.append("## 인사이트 (결착 n≥5 버킷)\n")
        L.append(f"- **최고 승률**: {hi[1]}={hi[2]} → {hi[0]}% (n {hi[3]['n']})")
        L.append(f"- **최저 승률**: {lo[1]}={lo[2]} → {lo[0]}% (n {lo[3]['n']})\n")
    # 예외 목록(분봉 확인 요청)
    L.append("## ⚠️ 예외(ambiguous) — 분봉 확인 필요\n")
    L.append("일봉으론 같은 날 +10%·-5% 선착 순서를 못 가림. 분봉으로 직접 확인해 승/패 확정 요망.\n")
    L.append("| 종목 | 패턴 | 돌파일 | 피벗 | 사유 |")
    L.append("|---|---|---|--:|---|")
    for e in d["ambiguous"]:
        L.append(f"| {e['name']}({e['code']}) | {e['pattern']} | {e['breakout_date']} | {e['pivot']:,.0f} | {e['exit_reason']} |")
    L.append("\n## 한계\n- 전진 64거래일·단일 기준일·단일 국면 → 일반화 금지.\n"
             "- 잔존 생존자 편향(2024-11 이전 상폐주 없음).\n- 먼 기간·다중 기준일은 후속 과제.\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"💾 저장: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate the report**

Run: `python scripts/pivot_backtest_report.py`
Expected: `docs/research/2026-04-01-pivot-backtest.md` 생성. 오류 없음.

- [ ] **Step 3: Eyeball the report**

Run: `sed -n '1,40p' docs/research/2026-04-01-pivot-backtest.md`
Expected: 요약·패턴별·특징별 표·인사이트·예외 목록이 채워져 있음.

- [ ] **Step 4: Commit**

```bash
git add scripts/pivot_backtest_report.py docs/research/2026-04-01-pivot-backtest.md
git commit -m "feat(pivot-backtest): 리포트 생성기 + 2026-04-01 리포트"
```

---

## Self-Review

**1. Spec coverage**
- 전 종목 point-in-time + 트렌드 게이트(RS80) → Task 3(as-of RS·evaluate_trend_template). ✅
- 패턴 돌파([D-10,D]) VCP·PP·3C → Task 3(replay_*+find_breakout_events, last10 필터). ✅
- +10%/-5% 선착·돌파일 포함·ambiguous → Task 1(simulate_pivot_trade) + 테스트. ✅
- 승자 특징(가격대·거래량·RS·패턴·시장) → Task 1(price_bucket·rel_volume) + Task 3(버킷) + Task 2(group_win_rate). ✅
- 산출 JSON + 리포트(예외 목록·한계) → Task 3·4. ✅
- 기준일 2026-04-01·전진 64거래일 → params·orchestrator. ✅

**2. Placeholder scan** — 실제 코드·명령·기대출력만. "TBD" 없음. ✅

**3. Type consistency**
- `simulate_pivot_trade(series, breakout_idx, pivot, ...)` 반환 키(result·resolve_date·days_held·exit_reason·gain_at_resolve_pct·max_gain_pct·max_dd_pct) — Task1 정의 ↔ Task3 `**sim` 병합 ↔ Task4 리포트(exit_reason 사용) 일치. ✅
- `tally`/`group_win_rate` 반환(n·win·loss·ambiguous·unresolved·win_rate_resolved) — Task2 ↔ Task3 by_pattern/by_feature ↔ Task4 wr()/table() 일치. ✅
- 이벤트 rec 키(code·name·market·pattern·breakout_date·pivot·rs·price_bucket·rel_vol·rel_vol_bucket·rs_bucket) — Task3 생성 ↔ Task4 ambiguous 표(name·code·pattern·breakout_date·pivot·exit_reason) 일치. ✅
- 재사용 API 시그니처: `evaluate_trend_template(closes, rs, rs_min)`·`_compute_rs_for_all(rows)`·`replay_*(series, scan_days, params)`·`find_breakout_events(replay)` — 코드베이스 확인 완료. ✅

> 통합 위험(실행 시 드러남, 리뷰 루프가 잡음): `fetch_universe_with_cap` 오프라인 여부, `_compute_rs_for_all` 임포트, 이벤트 0건 시 창/게이트 튜닝. Task3 스모크런에서 확인.

---

## Execution Handoff

순서: Task 1(시뮬·특징) → 2(집계) — 순수/TDD. 3(오케스트레이터, 스모크→전체 실행) → 4(리포트). 3·4는 캐시 정션 필요(설정됨).
