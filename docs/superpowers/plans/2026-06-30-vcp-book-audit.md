# VCP 책 충실도 감사 (vcp-audit) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** find-vcp의 VCP 검출기가 미너비니 책 규칙(선행급등·수축·수축별 거래량·50일선 마름·돌파)을 얼마나 충실히 구현하는지 종목별 "성적표"로 진단하는 읽기전용 도구를 만든다.

**Architecture:** 순수 부품 `scripts/canslim_lib/vcp_audit.py`(책 5축 계산 + 캐시/FDR 데이터 로더)를 TDD로 만들고, CLI `scripts/screen_vcp_audit.py`가 검출기가 찾은 6종목 + 사용자 정답 예시를 받아 `public/data/sepa-vcp-audit.json` + 콘솔 성적표를 낸다. 베이스·피벗·수축·검출기 평결은 기존 `evaluate_vcp`/`zigzag`/`find_contractions` 재사용.

**Tech Stack:** Python 3.11+, pytest 9.x, FinanceDataReader(과거 일봉), 기존 `canslim_lib.vcp` / `canslim_lib.ohlcv_matrix`.

**Spec:** `docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md`

## Global Constraints

- 검출기·find-vcp·find-vcp-history·공유 파일 **무수정**(읽기전용 진단). 컷오프 금지. 자동 commit 금지.
- 모든 거래량 판정은 **거래량 50일 이동평균(trailing rolling)** 기준(책 정의). 현 검출기의 전/후반 1/3 비교를 쓰지 않는다.
- 새 VCP 판정 로직 금지 — 베이스/피벗/수축/검출기 평결은 기존 `evaluate_vcp`·`zigzag`·`find_contractions` 재사용.
- 환각 금지: 모든 축 값·날짜·근거를 출력 JSON에 포함.
- 기본 임계값(전부 CLI 인자, 정답 예시로 보정 예정): min_advance=25.0, mono_tol=1.15, dry_max=0.7, breakout_vol=1.4, near=5.0, vol_ma_window=50, prior_lookback=60, right_frac=0.34, lookback_days=120, zigzag_pct=8.0, base_vol_cap=50.
- 데이터 로딩 2원화: start/end 없으면 캐시(`ohlcv_matrix.get_series`), 있으면 FDR fetch(start−80영업일 버퍼). FDR 실패 시 그 항목만 skip+사유.
- Windows 콘솔: 스크립트 상단 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.

---

### Task 1: vcp_audit.py — 거래량 50일MA + 선행급등

**Files:**
- Create: `scripts/canslim_lib/vcp_audit.py`
- Test: `tests/test_vcp_audit.py`

**Interfaces:**
- Produces: `volume_ma(volumes: list[float], window: int = 50) -> list[float]` — trailing MA(부분창 허용).
- Produces: `audit_prior_advance(closes: list[float], b0: int, lookback: int = 60) -> dict` — `{value_pct, days, low_price}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp_audit.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp_audit import volume_ma, audit_prior_advance


def test_volume_ma_trailing_window():
    vols = [10, 20, 30, 40, 50]
    ma = volume_ma(vols, window=3)
    # i0=10, i1=(10+20)/2=15, i2=(10+20+30)/3=20, i3=(20+30+40)/3=30, i4=40
    assert ma[0] == 10
    assert ma[1] == 15
    assert ma[2] == 20
    assert ma[3] == 30
    assert ma[4] == 40


def test_audit_prior_advance_low_to_basestart():
    # 저점 100(idx2) → 베이스시작 150(idx6): +50%, 4거래일
    closes = [120, 110, 100, 110, 130, 145, 150, 148]
    r = audit_prior_advance(closes, b0=6, lookback=60)
    assert abs(r["value_pct"] - 50.0) < 1e-9
    assert r["days"] == 4
    assert r["low_price"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp_audit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'canslim_lib.vcp_audit'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp_audit.py
"""VCP 책 충실도 감사 (순수 부품 + 데이터 로더).

검출기(evaluate_vcp)가 미너비니 책 VCP 규칙을 얼마나 충실히 구현하는지 숫자로
렌더링한다. 모든 거래량 판정은 거래량 50일 이동평균 기준(책 정의).
정의: docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md
"""
from __future__ import annotations


def volume_ma(volumes: list[float], window: int = 50) -> list[float]:
    """거래량 trailing 이동평균. 초반(창 미만)은 가용분 평균(부분창)."""
    out: list[float] = []
    for i in range(len(volumes)):
        lo = max(0, i - window + 1)
        seg = volumes[lo:i + 1]
        out.append(sum(seg) / len(seg) if seg else 0.0)
    return out


def audit_prior_advance(closes: list[float], b0: int, lookback: int = 60) -> dict:
    """베이스 시작 직전 lookback 내 최저 종가 → 베이스시작 상승%·기간."""
    lo_i = max(0, b0 - lookback)
    window = closes[lo_i:b0 + 1]
    if not window:
        return {"value_pct": None, "days": None, "low_price": None}
    low = min(window)
    low_idx = lo_i + window.index(low)
    adv = (closes[b0] - low) / low * 100.0 if low else None
    return {
        "value_pct": round(adv, 2) if adv is not None else None,
        "days": b0 - low_idx,
        "low_price": round(low, 2),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp_audit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp_audit.py tests/test_vcp_audit.py
git commit -m "feat(vcp-audit): 거래량 50일MA + 선행급등 + 테스트"
```

---

### Task 2: vcp_audit.py — 수축·수축별 거래량·마른점

**Files:**
- Modify: `scripts/canslim_lib/vcp_audit.py`
- Test: `tests/test_vcp_audit.py`

**Interfaces:**
- Consumes: `canslim_lib.vcp.zigzag`, `canslim_lib.vcp.find_contractions`.
- Produces:
  - `audit_contractions(base_closes, zigzag_pct, mono_tol) -> dict` — `{depths, count, shrinking, swings}`.
  - `audit_contraction_volumes(base_vols, base_ma50, swings, mono_tol) -> dict` — `{per:[{depth_pair_idx, vol_vs_ma50_pct}], decreasing, last_below_ma50}`.
  - `audit_dry_point(base_vols, base_ma50, base_dates, right_frac) -> dict` — `{min_vol_vs_ma50_pct, date}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp_audit.py 에 추가
from canslim_lib.vcp_audit import (
    audit_contractions, audit_contraction_volumes, audit_dry_point,
)


def test_audit_contractions_depths_and_shrinking():
    base = [100, 95, 88, 80, 84, 90, 92, 88, 85, 86]  # 고100→저80(-20%), 고92→저85(-7.6%)
    r = audit_contractions(base, zigzag_pct=8.0, mono_tol=1.15)
    assert r["count"] >= 2
    assert r["depths"][0] > r["depths"][-1]
    assert r["shrinking"] is True


def test_audit_contraction_volumes_decreasing_and_below_ma50():
    # 수축 2개: 첫 구간 거래량 MA50의 120%, 둘째 60% → 감소 & 둘째 50일선 하회
    base_vols  = [120, 120, 60, 60]
    base_ma50  = [100, 100, 100, 100]
    swings = [(0, 100.0, "high"), (1, 80.0, "low"), (2, 90.0, "high"), (3, 82.0, "low")]
    r = audit_contraction_volumes(base_vols, base_ma50, swings, mono_tol=1.15)
    assert len(r["per"]) == 2
    assert abs(r["per"][0]["vol_vs_ma50_pct"] - 120.0) < 1e-6
    assert abs(r["per"][1]["vol_vs_ma50_pct"] - 60.0) < 1e-6
    assert r["decreasing"] is True
    assert r["last_below_ma50"] is True


def test_audit_dry_point_min_on_right():
    base_vols  = [100, 90, 80, 40, 70]   # 우측 1/3 ~ 마지막 한두 개
    base_ma50  = [100, 100, 100, 100, 100]
    base_dates = ["d0", "d1", "d2", "d3", "d4"]
    r = audit_dry_point(base_vols, base_ma50, base_dates, right_frac=0.5)
    assert r["min_vol_vs_ma50_pct"] == 40.0
    assert r["date"] == "d3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp_audit.py -k "contraction or dry" -v`
Expected: FAIL — `ImportError: cannot import name 'audit_contractions'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp_audit.py 에 추가
from canslim_lib.vcp import zigzag, find_contractions  # noqa: E402


def audit_contractions(base_closes: list[float], zigzag_pct: float, mono_tol: float) -> dict:
    swings = zigzag(base_closes, zigzag_pct)
    depths = [round(d, 2) for d in find_contractions(swings)]
    T = len(depths)
    shrinking = all(depths[i] <= depths[i - 1] * mono_tol for i in range(1, T)) if T >= 2 else False
    return {"depths": depths, "count": T, "shrinking": shrinking, "swings": swings}


def _seg_mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def audit_contraction_volumes(base_vols, base_ma50, swings, mono_tol) -> dict:
    """각 (고→다음저) 수축 구간의 평균거래량 / 그 구간 평균ma50 (%)."""
    per = []
    for a, b in zip(swings, swings[1:]):
        if a[2] == "high" and b[2] == "low":
            i, j = a[0], b[0]
            v = _seg_mean(base_vols[i:j + 1])
            m = _seg_mean(base_ma50[i:j + 1])
            pct = round(v / m * 100.0, 2) if (v is not None and m) else None
            per.append({"vol_vs_ma50_pct": pct})
    vals = [p["vol_vs_ma50_pct"] for p in per if p["vol_vs_ma50_pct"] is not None]
    decreasing = all(vals[i] <= vals[i - 1] for i in range(1, len(vals))) if len(vals) >= 2 else False
    last_below = (vals[-1] < 100.0) if vals else False
    return {"per": per, "decreasing": decreasing, "last_below_ma50": last_below}


def audit_dry_point(base_vols, base_ma50, base_dates, right_frac: float) -> dict:
    """베이스 우측(right_frac 비율) 구간에서 min(거래량/ma50)와 그 날짜."""
    n = len(base_vols)
    start = max(0, int(n * (1 - right_frac)))
    best_pct, best_date = None, None
    for k in range(start, n):
        m = base_ma50[k]
        if not m:
            continue
        pct = base_vols[k] / m * 100.0
        if best_pct is None or pct < best_pct:
            best_pct, best_date = pct, base_dates[k] if k < len(base_dates) else None
    return {"min_vol_vs_ma50_pct": round(best_pct, 2) if best_pct is not None else None,
            "date": best_date}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp_audit.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp_audit.py tests/test_vcp_audit.py
git commit -m "feat(vcp-audit): 수축·수축별 거래량·마른점 (50일선 기준) + 테스트"
```

---

### Task 3: vcp_audit.py — 돌파 감사 + 항목 종합

**Files:**
- Modify: `scripts/canslim_lib/vcp_audit.py`
- Test: `tests/test_vcp_audit.py`

**Interfaces:**
- Consumes: Task 1·2 함수, `canslim_lib.vcp.evaluate_vcp`.
- Produces:
  - `audit_breakout(series, pivot, b1, ma50, params) -> dict` — `{pivot, detector_flags, clean_candidates, pass}`.
  - `audit_item(series, b0, b1, params, meta) -> dict` — 한 종목 성적표(spec §7 `items[]`).

규칙(spec §6):
- `audit_breakout`: b1 이후(끝까지) 종가>피벗인 날들에 대해 각 날의 `vol_vs_ma50_pct`,
  `up_candle`(종가>시가), `extension_pct`((종가−피벗)/피벗×100), `first_cross`(전일종가≤피벗) 계산.
  - `clean_candidates` = first_cross AND up_candle AND vol_vs_ma50≥breakout_vol×100 AND extension≤near.
  - `detector_flags` = 현 검출기 규칙(종가>피벗 AND 거래량≥base_vol_avg×breakout_vol)인 날 목록.
    base_vol_avg = base 마지막 base_vol_cap개 거래량 평균(검출기와 동일).
  - `pass` = clean_candidates 비어있지 않음.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp_audit.py 에 추가
from canslim_lib.vcp_audit import audit_breakout


def test_audit_breakout_clean_vs_detector():
    # 피벗 100. b1 이후: d0 전일종가95 → d1 종가105(첫돌파·양봉·거래량2배·연장5%)
    series = {
        "dates":  ["d0", "d1", "d2"],
        "closes": [95.0, 105.0, 108.0],
        "opens":  [96.0, 101.0, 107.0],
        "highs":  [97.0, 106.0, 109.0],
        "lows":   [94.0, 100.0, 106.0],
        "volumes":[100.0, 300.0, 120.0],
    }
    ma50 = [150.0, 150.0, 150.0]   # d1 거래량 300/150 = 200%
    params = {"breakout_vol": 1.4, "near": 5.0, "base_vol_cap": 50}
    r = audit_breakout(series, pivot=100.0, b1=0, ma50=ma50, params=params)
    # d1: 첫돌파(전일95≤100), 양봉(105>101), vol 200%≥140%, 연장 5%≤5 → clean
    assert any(c["date"] == "d1" for c in r["clean_candidates"])
    assert r["pass"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp_audit.py -k breakout -v`
Expected: FAIL — `ImportError: cannot import name 'audit_breakout'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp_audit.py 에 추가
from canslim_lib.vcp import evaluate_vcp, DEFAULT_PARAMS  # noqa: E402


def audit_breakout(series, pivot, b1, ma50, params) -> dict:
    closes = series["closes"]; opens = series["opens"]; vols = series["volumes"]; dates = series["dates"]
    n = len(closes)
    if pivot is None:
        return {"pivot": None, "detector_flags": [], "clean_candidates": [], "pass": False}
    cap = params.get("base_vol_cap", 50)
    base_vols = vols[max(0, b1 - cap + 1):b1 + 1]
    base_vol_avg = (sum(base_vols) / len(base_vols)) if base_vols else 0.0
    bv = params.get("breakout_vol", 1.4); near = params.get("near", 5.0)
    detector_flags, clean = [], []
    for i in range(b1 + 1, n):
        if closes[i] <= pivot:
            continue
        m = ma50[i] if i < len(ma50) and ma50[i] else None
        vol_vs = round(vols[i] / m * 100.0, 2) if m else None
        up = closes[i] > opens[i]
        ext = round((closes[i] - pivot) / pivot * 100.0, 2)
        first = closes[i - 1] <= pivot if i > 0 else True
        rec = {"date": dates[i], "vol_vs_ma50_pct": vol_vs, "up_candle": up,
               "extension_pct": ext, "first_cross": first}
        if base_vol_avg and vols[i] >= base_vol_avg * bv:
            detector_flags.append(dates[i])
        if first and up and (vol_vs is not None and vol_vs >= bv * 100.0) and ext <= near:
            clean.append(rec)
    return {"pivot": round(pivot, 2), "detector_flags": detector_flags,
            "clean_candidates": clean, "pass": len(clean) > 0}


def audit_item(series, b0, b1, params, meta) -> dict:
    closes = series["closes"]; vols = series["volumes"]; dates = series["dates"]
    ma50 = volume_ma(vols, params.get("vol_ma_window", 50))
    base_closes = closes[b0:b1 + 1]
    base_vols = vols[b0:b1 + 1]; base_ma50 = ma50[b0:b1 + 1]; base_dates = dates[b0:b1 + 1]

    adv = audit_prior_advance(closes, b0, params.get("prior_lookback", 60))
    con = audit_contractions(base_closes, params.get("zigzag_pct", 8.0), params.get("mono_tol", 1.15))
    cvol = audit_contraction_volumes(base_vols, base_ma50, con["swings"], params.get("mono_tol", 1.15))
    dry = audit_dry_point(base_vols, base_ma50, base_dates, params.get("right_frac", 0.34))

    # 검출기 평결 + 피벗 (기존 evaluate_vcp 재사용, b1 기준)
    ev_params = {k: params.get(k, DEFAULT_PARAMS[k]) for k in
                 ("lookback_days", "zigzag_pct", "max_final_depth", "breakout_vol_mult", "near_pivot_pct")}
    sub = {k: series[k][:b1 + 1] for k in ("dates", "closes", "highs", "lows", "volumes", "opens") if series.get(k)}
    ev = evaluate_vcp(sub, ev_params)
    bo = audit_breakout(series, ev.get("pivot_price"), b1, ma50, params)

    axes = {
        "prior_advance": {**adv, "pass": (adv["value_pct"] is not None and adv["value_pct"] >= params.get("min_advance", 25.0))},
        "contractions": {"depths": con["depths"], "count": con["count"], "shrinking": con["shrinking"],
                         "pass": (2 <= con["count"] <= 6 and con["shrinking"])},
        "contraction_volumes": {**cvol, "pass": (cvol["decreasing"] and cvol["last_below_ma50"])},
        "dry_point": {**dry, "pass": (dry["min_vol_vs_ma50_pct"] is not None
                                      and dry["min_vol_vs_ma50_pct"] <= params.get("dry_max", 0.7) * 100.0)},
        "breakout": bo,
    }
    return {
        "code": meta.get("code"), "name": meta.get("name"), "source": meta.get("source"),
        "base_start": dates[b0] if b0 < len(dates) else None,
        "base_end": dates[b1] if b1 < len(dates) else None,
        "detector_verdict": {"vcp_detected": ev.get("vcp_detected"), "status_at_b1": ev.get("status")},
        "axes": axes,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp_audit.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp_audit.py tests/test_vcp_audit.py
git commit -m "feat(vcp-audit): 돌파 감사 + 항목 종합 + 테스트"
```

---

### Task 4: vcp_audit.py — 데이터 로더 (캐시 + FDR)

**Files:**
- Modify: `scripts/canslim_lib/vcp_audit.py`
- Test: `tests/test_vcp_audit.py`

**Interfaces:**
- Produces: `load_series(code, start=None, end=None, fdr_buffer_days=80) -> dict | None`
  — start/end 없으면 캐시(`ohlcv_matrix.get_series`), 있으면 FDR. 키: `dates,opens,highs,lows,closes,volumes`. 실패 시 None.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp_audit.py 에 추가
import pytest
from canslim_lib.vcp_audit import load_series


def test_load_series_cache_path():
    # 캐시에 있는 종목(빌드 환경 의존) — 없으면 skip
    s = load_series("064290")
    if s is None:
        pytest.skip("064290 캐시 없음(환경 의존)")
    for k in ("dates", "opens", "highs", "lows", "closes", "volumes"):
        assert k in s and len(s[k]) > 0


def test_load_series_fdr_path_smoke():
    # FDR 네트워크 — 실패/미설치 시 skip
    try:
        s = load_series("005930", start="2019-01-02", end="2019-06-28")
    except Exception as e:
        pytest.skip(f"FDR 사용 불가: {e}")
    if s is None:
        pytest.skip("FDR 반환 없음(네트워크/데이터)")
    assert len(s["closes"]) > 50          # 버퍼 포함 충분
    assert s["dates"][-1] <= "2019-06-28"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp_audit.py -k load_series -v`
Expected: FAIL — `ImportError: cannot import name 'load_series'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp_audit.py 에 추가
from datetime import datetime, timedelta  # noqa: E402
from canslim_lib import ohlcv_matrix  # noqa: E402


def load_series(code: str, start: str | None = None, end: str | None = None,
                fdr_buffer_days: int = 80) -> dict | None:
    """start/end 없으면 캐시, 있으면 FDR(start−버퍼~end). 키 통일."""
    if not start and not end:
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            return None
        # 캐시에 opens가 항상 있음(ohlcv_matrix). 키만 추려 반환.
        return {k: s.get(k, []) for k in ("dates", "opens", "highs", "lows", "closes", "volumes")}
    try:
        import FinanceDataReader as fdr
    except ImportError:
        return None
    # start 이전 버퍼(달력일 환산 ~1.5배)
    s_dt = datetime.strptime(start, "%Y-%m-%d") - timedelta(days=int(fdr_buffer_days * 1.5))
    try:
        df = fdr.DataReader(code, s_dt.strftime("%Y-%m-%d"), end)
    except Exception:
        return None
    if df is None or len(df) == 0:
        return None
    out = {"dates": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
    for idx, row in df.iterrows():
        out["dates"].append(str(idx.date()))
        out["opens"].append(float(row.get("Open") or row.get("Close")))
        out["highs"].append(float(row.get("High") or row.get("Close")))
        out["lows"].append(float(row.get("Low") or row.get("Close")))
        out["closes"].append(float(row["Close"]))
        v = row.get("Volume")
        out["volumes"].append(int(v) if v == v and v else 0)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp_audit.py -v`
Expected: PASS (cache/FDR 테스트는 환경에 따라 skip 가능; 나머지 통과)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp_audit.py tests/test_vcp_audit.py
git commit -m "feat(vcp-audit): 데이터 로더(캐시+FDR) + 테스트"
```

---

### Task 5: screen_vcp_audit.py — CLI + 예시 템플릿

**Files:**
- Create: `scripts/screen_vcp_audit.py`
- Create: `public/data/vcp_examples.json`

**Interfaces:**
- Consumes: `canslim_lib.vcp_audit`(Task1~4), `canslim_lib.vcp.DEFAULT_PARAMS`.
- Produces: `public/data/sepa-vcp-audit.json` (spec §7).

베이스 구간 결정:
- **예시**(vcp_examples.json 항목, start/end 있음): FDR 로드 후 b0=start의 인덱스, b1=end(또는 breakout_date)의 인덱스.
- **검출 6종목**(history의 이벤트 종목, start/end 없음): 캐시 로드 후, 이벤트 확인일을 b1로, b0 = b1 기준 lookback_days 내 최고 종가 인덱스(evaluate_vcp와 동일 규칙).

- [ ] **Step 1: Write the example template**

```json
{
  "_comment": "사용자 정답 VCP 예시. 각 항목: code(6자리), start/end(베이스 구간 YYYY-MM-DD), breakout_date(선택), pivot(선택), note(선택). 5개 이상 채워주세요.",
  "examples": [
    { "code": "000000", "start": "2019-03-01", "end": "2019-06-20", "breakout_date": "2019-06-21", "pivot": 0, "note": "예시 양식" }
  ]
}
```

- [ ] **Step 2: Write the CLI script**

```python
# scripts/screen_vcp_audit.py
"""vcp-audit — VCP 검출기 책 충실도 감사.

검출기가 찾은 종목(정밀도) + 사용자 정답 예시(재현율)를 책 5축으로 렌더링한다.
정의: docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md
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

from canslim_lib.vcp import DEFAULT_PARAMS  # noqa: E402
from canslim_lib import vcp_audit  # noqa: E402

KST = timezone(timedelta(hours=9))
HISTORY = ROOT / "public" / "data" / "sepa-vcp-history.json"
EXAMPLES = ROOT / "public" / "data" / "vcp_examples.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-vcp-audit.json"
AXES = ("prior_advance", "contractions", "contraction_volumes", "dry_point", "breakout")


def _params(args) -> dict:
    return {"min_advance": args.min_advance, "mono_tol": args.mono_tol, "dry_max": args.dry_max,
            "breakout_vol": args.breakout_vol, "near": args.near, "vol_ma_window": args.vol_ma_window,
            "prior_lookback": 60, "right_frac": 0.34, "lookback_days": DEFAULT_PARAMS["lookback_days"],
            "zigzag_pct": args.zigzag_pct, "base_vol_cap": DEFAULT_PARAMS["base_vol_cap"]}


def _idx_on_or_before(dates, target):
    cand = [i for i, d in enumerate(dates) if d <= target]
    return cand[-1] if cand else None


def run(args) -> None:
    params = _params(args)
    items = []

    # 1) 정답 예시 (FDR)
    if not args.no_examples and EXAMPLES.exists():
        ex = json.loads(EXAMPLES.read_text(encoding="utf-8")).get("examples", [])
        for e in ex:
            if str(e.get("code", "")).strip() in ("", "000000"):
                continue
            s = vcp_audit.load_series(e["code"], e.get("start"), e.get("end"))
            if not s:
                items.append({"code": e["code"], "source": "example", "note": "데이터 로드 실패(FDR)"})
                continue
            b0 = _idx_on_or_before(s["dates"], e["start"]) or 0
            b1 = _idx_on_or_before(s["dates"], e.get("breakout_date") or e["end"])
            if b1 is None:
                items.append({"code": e["code"], "source": "example", "note": "기간 인덱스 실패"})
                continue
            items.append(vcp_audit.audit_item(s, b0, b1, params,
                          {"code": e["code"], "name": e.get("note"), "source": "example"}))

    # 2) 검출기가 찾은 종목 (캐시)
    if not args.no_detector and HISTORY.exists():
        hist = json.loads(HISTORY.read_text(encoding="utf-8"))
        for st in hist.get("stocks", []):
            if st.get("num_events", 0) <= 0:
                continue
            code = st["code"]
            s = vcp_audit.load_series(code)
            if not s:
                continue
            ev_date = st["events"][-1].get("confirm_date") or st["events"][-1]["date"]
            b1 = _idx_on_or_before(s["dates"], ev_date)
            if b1 is None:
                continue
            lb = params["lookback_days"]
            lo = max(0, b1 - lb + 1)
            b0 = lo + max(range(len(s["closes"][lo:b1 + 1])), key=lambda k: s["closes"][lo + k])
            items.append(vcp_audit.audit_item(s, b0, b1, params,
                          {"code": code, "name": st.get("name"), "source": "detector"}))

    pass_counts = {ax: sum(1 for it in items if it.get("axes", {}).get(ax, {}).get("pass")) for ax in AXES}
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": params, "items": items,
        "summary": {"n_items": len(items), "axis_pass_counts": pass_counts},
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 저장: {OUT_PATH.relative_to(ROOT)}")

    print(f"\n[VCP 책 충실도 감사] {len(items)}건  (축별 통과수: " +
          " · ".join(f"{ax} {pass_counts[ax]}" for ax in AXES) + ")")
    sym = {True: "O", False: "X", None: "-"}
    for it in items:
        ax = it.get("axes")
        if not ax:
            print(f"  {it['code']} ({it.get('source')}) — {it.get('note','평가불가')}")
            continue
        flags = " ".join(f"{a}:{sym.get(ax[a].get('pass'))}" for a in AXES)
        det = it["detector_verdict"]
        print(f"  {it['code']} {str(it.get('name'))[:10]:10s} ({it['source']:8s}) | {flags} "
              f"| 검출기 vcp={det['vcp_detected']}")


def main():
    ap = argparse.ArgumentParser(description="vcp-audit — VCP 책 충실도 감사")
    ap.add_argument("--no-examples", action="store_true")
    ap.add_argument("--no-detector", action="store_true")
    ap.add_argument("--min-advance", type=float, default=25.0)
    ap.add_argument("--dry-max", type=float, default=0.7)
    ap.add_argument("--breakout-vol", type=float, default=1.4)
    ap.add_argument("--near", type=float, default=5.0)
    ap.add_argument("--mono-tol", type=float, default=1.15)
    ap.add_argument("--vol-ma-window", type=int, default=50)
    ap.add_argument("--zigzag-pct", type=float, default=DEFAULT_PARAMS["zigzag_pct"])
    run(ap.parse_args())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke-run on detector stocks (examples 비활성)**

Run: `python -X utf8 scripts/screen_vcp_audit.py --no-examples`
Expected: `💾 저장: ...sepa-vcp-audit.json` + 검출 6종목의 5축 O/X 한 줄씩 + 축별 통과수. (인텍플러스 등에서 breakout·contraction_volumes·dry_point가 X로 나오며 §3 어긋남이 드러나는지 관찰)

- [ ] **Step 4: Sanity-check output**

Run:
```bash
python -X utf8 -c "import json;d=json.load(open('public/data/sepa-vcp-audit.json',encoding='utf-8'));print('n',d['summary']['n_items'],d['summary']['axis_pass_counts'])"
```
Expected: n = 검출 이벤트 종목 수(현재 6), axis_pass_counts 출력.

- [ ] **Step 5: Commit**

```bash
git add scripts/screen_vcp_audit.py public/data/vcp_examples.json public/data/sepa-vcp-audit.json
git commit -m "feat(vcp-audit): screen_vcp_audit CLI + 예시 템플릿 + 첫 산출"
```

---

### Task 6: vcp-audit 스킬 문서

**Files:**
- Create: `.claude/skills/vcp-audit/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: vcp-audit
description: >
  find-vcp의 VCP 검출기가 미너비니 책 규칙(선행급등·수축·수축별 거래량·거래량 50일선
  마름·돌파)을 얼마나 충실히 구현하는지 종목별 5축 성적표로 진단하는 읽기전용 도구.
  검출기가 찾은 종목(정밀도) + 사용자 정답 VCP 예시(재현율, 과거 구간은 FDR로 fetch)를
  감사해 sepa-vcp-audit.json 에 저장. 검출기는 수정하지 않음(진단까지). 사용자가
  "/vcp-audit", "VCP 책 충실도", "검출기 감사", "내 예시로 검증" 등을 요청할 때 사용.
---

# vcp-audit — VCP 책 충실도 감사

VCP 검출기를 책 규칙의 숫자로 풀어 어디가 어긋나는지 진단한다(차트 눈대조 불필요).
정의: `docs/superpowers/specs/2026-06-30-vcp-book-audit-design.md`.

## 사전 조건
- 검출 종목 감사: `public/data/sepa-vcp-history.json`(= find-vcp-history 산출) 필요.
- 정답 예시 감사: `public/data/vcp_examples.json`에 예시(코드·기간) 채워야 함.
- FDR(FinanceDataReader) 설치(과거 예시 fetch용).

## 실행
```
python scripts/screen_vcp_audit.py
```
- 산출: `public/data/sepa-vcp-audit.json` + 콘솔 5축 O/X 성적표.

### 옵션
- `--no-examples` / `--no-detector` : 한쪽만.
- `--min-advance 25` `--dry-max 0.7` `--breakout-vol 1.4` `--near 5` : 통과 임계값(정답 예시로 보정).

## 결과 보는 법
- 5축: prior_advance·contractions·contraction_volumes·dry_point·breakout 각 O/X.
- 검출기 vcp 평결과 비교해 "책엔 맞는데 검출기는 놓침" 또는 "검출기는 통과인데 책 어긋남"을 찾는다.
- 모든 거래량 판정은 거래량 50일선 기준(책 정의).

## 안 하는 것
- 검출기·find-vcp 수정 · 임계값 자동 최적화 · 공유 파일 갱신 · 자동 commit.
```

- [ ] **Step 2: Verify skill discoverable**

Run: `python -c "import pathlib; t=pathlib.Path('.claude/skills/vcp-audit/SKILL.md').read_text(encoding='utf-8'); assert t.startswith('---') and 'name: vcp-audit' in t; print('skill ok')"`
Expected: `skill ok`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/vcp-audit/SKILL.md
git commit -m "docs(vcp-audit): vcp-audit 스킬 문서"
```

---

## Self-Review 결과 (작성자 점검)

- **Spec 커버리지**: §5 데이터로딩(Task4) · §6 5축(Task1~3) · §6 거래량 50일MA(Task1·전축) · §7 스키마(Task3 audit_item·Task5 CLI) · §8 구성(Task1~6) · §9 검증(Task1~4 단위테스트·Task5 풀런) 전부 태스크 존재.
- **타입 일관성**: `volume_ma/audit_prior_advance/audit_contractions/audit_contraction_volumes/audit_dry_point/audit_breakout/audit_item/load_series` 시그니처가 정의처(Task1~4)와 사용처(audit_item·CLI)에서 일치. swings는 base-상대 인덱스라 base_vols/base_ma50 슬라이스와 정렬됨.
- **재사용**: 베이스/피벗/수축/검출기평결은 evaluate_vcp·zigzag·find_contractions 호출(새 판정 로직 없음) — Global Constraints 충족.
- **미해결/관찰**: Task5 풀런에서 검출 6종목의 contraction_volumes·dry_point·breakout가 대부분 X로 나오는 게 예상(=§3 어긋남이 숫자로 확인되는 것이 이 도구의 목적). 정답 예시는 사용자 제공 후 별도 실행(구현 완료 후 요청). FDR 결손 예시는 note로 표기.
