# 거래량 매수 실시간 검증 관찰기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실전 봇의 매수 판정(`evaluate_entry`)을 그대로 재사용해, 감시 후보를 실시간으로 판정하고 후보별 사유를 상세 출력하는 읽기 전용 관찰기(`scripts/autobuy/verify_volume.py`)를 만든다 — 국면 게이트는 이 도구에서만 끄고, 주문은 물리적으로 불가능.

**Architecture:** 세 층으로 분리. (1) 순수 판정 조립 `observe_sweep` — 합성 입력으로 전수 테스트, 실제 매수 판정은 `signals.evaluate_entry` 재사용. (2) 순수 렌더 `_fmt_block` — 한 사이클 출력 블록 문자열 생성, 테스트 가능. (3) 라이브 오케스트레이터 `run`/`main` — 감시목록 로드·KIS 실시간 조회·반복 스윕·파일 로그(수동 스모크로 확인). `kis_trade`를 import하지 않아 실주문 불가.

**Tech Stack:** Python 3.12, 표준 라이브러리 + `canslim_lib.kis_api`/`ohlcv_matrix`, `autobuy.signals`/`watchlist`/`config`. pytest.

## Global Constraints

- 파일 경로: 신규 `scripts/autobuy/verify_volume.py`, 테스트 `tests/test_autobuy_verify_volume.py`.
- **판정 로직 재구현 금지** — 매수 여부는 반드시 `autobuy.signals.evaluate_entry` 호출 결과를 사용.
- **`kis_trade` import 금지** — 이 파일은 주문 함수를 절대 참조하지 않는다(실주문 물리적 차단).
- 실전 봇 무변경 — `config.py`·`runner.py`·`signals.py`·상태파일을 수정하지 않는다(읽기/재사용만).
- avg50/피벗/거래량 pace는 실전 봇과 **동일 입력**: avg50 = `ohlcv_matrix.get_series(code)` 마지막 50 volume 평균, 피벗 = `sepa-*-candidates.json`, 누적거래량 = `kis_api.fetch_quote_with_volume`.
- pace 표시식 = `acml_vol / (avg50 * elapsed_frac)` (표시 전용, 임계 비교는 `evaluate_entry` 내부가 수행).
- 판정 사유는 후보당 한 개(우선순위: already_held→no_slot→below_pivot→extended→no_baseline→low_volume). no_quote(조회 실패)는 관찰기 자체 사유.
- `elapsed_frac`는 실전 `runner._elapsed_frac`과 동일식: 09:00 기준 경과초 / (6.5*3600), clamp [1e-6, 1.0].
- Windows: 실행은 `python -X utf8 ...`, 출력은 UTF-8.
- 테스트는 `sys.path.insert(0, .../scripts)` 후 `from autobuy.verify_volume import ...` (기존 autobuy 테스트와 동일 패턴).
- 커밋 메시지 말미:
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```

---

### Task 1: 순수 판정 조립 `observe_sweep` + `_elapsed_frac`

**Files:**
- Create: `scripts/autobuy/verify_volume.py`
- Test: `tests/test_autobuy_verify_volume.py`

**Interfaces:**
- Consumes: `autobuy.signals.evaluate_entry(price, pivot, acml_vol, avg50_vol, elapsed_frac, *, slots_used, slots_max, held, vol_pace_min, chase_max_pct) -> (bool, str)` (기존 함수).
- Produces:
  - `_elapsed_frac(now: datetime) -> float`
  - `observe_sweep(quotes_by_code: dict[str, dict], candidates: list[dict], avg50_by_code: dict[str, float], held_sim: set[str], skip: set[str], cfg: dict, elapsed_frac: float, in_buy_window: bool = True) -> tuple[list[dict], list[dict]]`
    - `quotes_by_code`: `{code: {"current": float, "acml_vol": float}}` (없는 code = 조회 실패).
    - 반환 `rows`: 후보별 `{"code","name","price","pivot","pct","pace","why"}` (why ∈ buy/already_held/no_slot/below_pivot/extended/no_baseline/low_volume/no_quote).
    - 반환 `buys`: 이번 스윕 매수 `{"code","name","price","pace"}`.
    - 부작용: `held_sim`·`skip`를 제자리(in place) 갱신(매수 종목 held_sim 추가, extended 종목 skip 추가). 슬롯 상한은 `cfg["SLOTS"]`.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_autobuy_verify_volume.py`

```python
import sys, pathlib, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.verify_volume import observe_sweep, _elapsed_frac

CFG = {"SLOTS": 10, "VOL_PACE_MIN": 1.5, "CHASE_MAX_PCT": 3.0}

def _cand(code, name="종목", pivot=1000.0):
    return {"code": code, "name": name, "pivot": pivot, "pattern": "VCP"}

def _q(current, acml):
    return {"current": current, "acml_vol": acml}

def test_elapsed_frac():
    d = datetime.datetime
    assert _elapsed_frac(d(2026, 7, 8, 9, 0, 0)) <= 1e-5 + 1e-6      # 개장≈0
    assert abs(_elapsed_frac(d(2026, 7, 8, 15, 30, 0)) - 1.0) < 1e-9  # 마감=1.0
    assert 0.2 < _elapsed_frac(d(2026, 7, 8, 10, 20, 0)) < 0.25       # 10:20≈0.205

def test_buy_on_pivot_cross_with_volume():
    # 피벗1000, avg50=1000, ef=0.1 → pace=acml/(1000*0.1). acml=300 → pace 3.0≥1.5, 가격1010(+1%,+3%이내) → 매수
    cands = [_cand("A")]
    held, skip = set(), set()
    rows, buys = observe_sweep({"A": _q(1010, 300)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1)
    assert len(buys) == 1 and buys[0]["code"] == "A"
    assert "A" in held
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "buy"

def test_low_volume_no_buy():
    cands = [_cand("A")]
    held, skip = set(), set()
    rows, buys = observe_sweep({"A": _q(1010, 50)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1)  # pace 0.5
    assert buys == [] and "A" not in held
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "low_volume"

def test_extended_over_3pct_added_to_skip():
    cands = [_cand("A")]
    held, skip = set(), set()
    rows, buys = observe_sweep({"A": _q(1040, 500)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1)  # +4%
    assert buys == [] and "A" in skip
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "extended"

def test_extended_skip_is_sticky_next_sweep():
    # 한 번 extended로 skip되면, 다음 스윕에 가격이 +3% 이내로 돌아와도 계속 extended 표시·미매수
    cands = [_cand("A")]
    held, skip = set(), set()
    observe_sweep({"A": _q(1040, 500)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1)   # skip 편입
    rows, buys = observe_sweep({"A": _q(1010, 500)}, cands, {"A": 1000.0}, held, skip, CFG, 0.2)
    assert buys == []
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "extended"

def test_below_pivot():
    cands = [_cand("A")]
    rows, buys = observe_sweep({"A": _q(970, 500)}, cands, {"A": 1000.0}, set(), set(), CFG, 0.1)  # -3%
    assert buys == []
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "below_pivot"

def test_already_held_skipped():
    cands = [_cand("A")]
    held = {"A"}
    rows, buys = observe_sweep({"A": _q(1010, 300)}, cands, {"A": 1000.0}, held, set(), CFG, 0.1)
    assert buys == []
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "already_held"

def test_no_quote_row():
    cands = [_cand("A")]
    rows, buys = observe_sweep({}, cands, {"A": 1000.0}, set(), set(), CFG, 0.1)  # 조회 실패
    assert buys == []
    r = [r for r in rows if r["code"] == "A"][0]
    assert r["why"] == "no_quote" and r["price"] is None

def test_slot_limit_pace_priority():
    cfg = {**CFG, "SLOTS": 1}
    cands = [_cand("A"), _cand("B")]
    held, skip = set(), set()
    # A pace=acml/(1000*0.1): acml 200 → 2.0. B acml 600 → 6.0(우선). 둘 다 +1%
    rows, buys = observe_sweep({"A": _q(1010, 200), "B": _q(1010, 600)}, cands,
                               {"A": 1000.0, "B": 1000.0}, held, skip, cfg, 0.1)
    assert len(buys) == 1 and buys[0]["code"] == "B"      # pace 높은 B만
    assert held == {"B"}
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "no_slot"

def test_outside_buy_window_no_commit():
    # in_buy_window=False면 판정은 보이되 실제 매수(held 편입)는 안 함
    cands = [_cand("A")]
    held, skip = set(), set()
    rows, buys = observe_sweep({"A": _q(1010, 300)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1,
                               in_buy_window=False)
    assert buys == [] and "A" not in held
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "buy"   # 조건은 충족(창밖이라 미체결)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -X utf8 -m pytest tests/test_autobuy_verify_volume.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'autobuy.verify_volume'`

- [ ] **Step 3: 최소 구현** — `scripts/autobuy/verify_volume.py` 생성(이 태스크 범위: 상단 docstring + `_elapsed_frac` + `observe_sweep`)

```python
"""거래량 매수 실시간 검증 관찰기 — 실전 봇 판정(evaluate_entry)을 그대로 재사용해
감시 후보를 실시간 판정하고 후보별 사유를 출력. 읽기 전용(주문 없음, kis_trade 미import).
순수 핵심 observe_sweep/_fmt_block은 합성 입력으로 테스트 가능."""
from __future__ import annotations


def _elapsed_frac(now) -> float:
    """datetime now → 09:00~15:30(6.5h) 경과 비율. 실전 runner._elapsed_frac과 동일식."""
    op = now.replace(hour=9, minute=0, second=0, microsecond=0)
    return max(1e-6, min(1.0, (now - op).total_seconds() / (6.5 * 3600)))


def observe_sweep(quotes_by_code, candidates, avg50_by_code, held_sim, skip, cfg,
                  elapsed_frac, in_buy_window=True):
    """한 사이클 후보 판정. 실제 매수 여부는 signals.evaluate_entry 재사용.
    반환 (rows, buys). held_sim·skip는 제자리 갱신. 슬롯 상한 cfg['SLOTS'].
    in_buy_window=False면 판정·표시는 하되 매수 커밋(held 편입) 안 함(실전 봇 매수창 밖)."""
    from autobuy.signals import evaluate_entry
    rows, fire = [], []
    slots_used = len(held_sim)   # 실전 러너처럼 스윕 시작 시점 슬롯수로 판정, 커밋 때 상한 재확인
    for c in candidates:
        code, pivot, name = c["code"], c["pivot"], c["name"]
        q = quotes_by_code.get(code)
        if not q:
            rows.append({"code": code, "name": name, "price": None, "pivot": pivot,
                         "pct": None, "pace": None, "why": "no_quote"})
            continue
        price, acml, av = q["current"], q["acml_vol"], avg50_by_code.get(code, 0)
        pace = acml / (av * elapsed_frac) if (av > 0 and elapsed_frac > 0) else 0.0
        pct = (price / pivot - 1) * 100 if pivot else None
        held = code in held_sim
        # 그날 스킵(extended)은 sticky — 가격 돌아와도 계속 스킵
        if code in skip and not held:
            rows.append({"code": code, "name": name, "price": price, "pivot": pivot,
                         "pct": pct, "pace": pace, "why": "extended"})
            continue
        ok, why = evaluate_entry(price, pivot, acml, av, elapsed_frac,
                                 slots_used=slots_used, slots_max=cfg["SLOTS"], held=held,
                                 vol_pace_min=cfg["VOL_PACE_MIN"], chase_max_pct=cfg["CHASE_MAX_PCT"])
        if why == "extended":
            skip.add(code)
        rows.append({"code": code, "name": name, "price": price, "pivot": pivot,
                     "pct": pct, "pace": pace, "why": ("already_held" if held else why)})
        if ok and in_buy_window and not held:
            fire.append((pace, c, price))
    buys = []
    row_by_code = {r["code"]: r for r in rows}
    for pace, c, price in sorted(fire, key=lambda x: -x[0]):
        if len(held_sim) >= cfg["SLOTS"]:
            break
        held_sim.add(c["code"])
        buys.append({"code": c["code"], "name": c["name"], "price": price, "pace": round(pace, 1)})
        row_by_code[c["code"]]["why"] = "buy"
    return rows, buys
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -X utf8 -m pytest tests/test_autobuy_verify_volume.py -q`
Expected: PASS (10 passed)

- [ ] **Step 5: 커밋**

```bash
git add scripts/autobuy/verify_volume.py tests/test_autobuy_verify_volume.py
git commit -m "feat(autobuy): 거래량 검증 관찰기 순수 판정 코어 observe_sweep

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 순수 렌더 `_fmt_block`

**Files:**
- Modify: `scripts/autobuy/verify_volume.py` (함수 추가)
- Test: `tests/test_autobuy_verify_volume.py` (테스트 추가)

**Interfaces:**
- Consumes: Task 1의 `rows`/`buys` 구조.
- Produces: `_fmt_block(now_str: str, elapsed_frac: float, held_count: int, slots_max: int, cand_count: int, regime_note: str, rows: list[dict], buys: list[dict], in_buy_window: bool) -> str` — 한 사이클 출력 블록 문자열. 헤더(시각·경과·슬롯·감시수) + 국면참고 한 줄 + ★매수 요약 + 후보별 판정행(pace 내림차순). 매수창 밖이면 헤더에 표기.

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_autobuy_verify_volume.py` 하단에 추가

```python
from autobuy.verify_volume import _fmt_block

def test_fmt_block_contains_key_parts():
    rows = [
        {"code": "000660", "name": "SK하이닉스", "price": 183500, "pivot": 182000,
         "pct": 0.82, "pace": 2.13, "why": "buy"},
        {"code": "042700", "name": "한미반도체", "price": 41500, "pivot": 40000,
         "pct": 3.75, "pace": 1.8, "why": "extended"},
        {"code": "006400", "name": "삼성SDI", "price": None, "pivot": 41000,
         "pct": None, "pace": None, "why": "no_quote"},
    ]
    buys = [{"code": "000660", "name": "SK하이닉스", "price": 183500, "pace": 2.1}]
    out = _fmt_block("14:03:20", 0.77, 1, 10, 3, "하락추세(지수<20MA)", rows, buys, True)
    assert "14:03:20" in out
    assert "1/10" in out                 # 슬롯 held/max
    assert "하락추세" in out             # 국면 참고
    assert "★매수" in out and "000660" in out
    assert "한미반도체" in out and "extended" in out
    assert "no_quote" in out             # 조회 실패도 표시

def test_fmt_block_outside_window_marks_header():
    out = _fmt_block("15:25:00", 0.99, 0, 10, 0, "상승추세", [], [], False)
    assert "매수창" in out               # 창 밖 표기
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -X utf8 -m pytest tests/test_autobuy_verify_volume.py -k fmt_block -q`
Expected: FAIL — `cannot import name '_fmt_block'`

- [ ] **Step 3: 최소 구현** — `verify_volume.py`에 `observe_sweep` 아래에 추가

```python
def _fmt_block(now_str, elapsed_frac, held_count, slots_max, cand_count,
               regime_note, rows, buys, in_buy_window):
    """한 사이클 출력 블록 문자열. rows는 pace 내림차순 정렬해 표시."""
    win = "" if in_buy_window else "  [매수창 밖 — 신규매수 안 함]"
    lines = [f"=== {now_str} (장 경과 {elapsed_frac*100:.0f}%) · 슬롯 {held_count}/{slots_max} · "
             f"감시 {cand_count}종목{win} ==="]
    lines.append(f"[국면 참고: {regime_note} — 게이트 아님(관찰만)]")
    if buys:
        tag = " · ".join(f"{b['code']} {b['name']} @{b['price']} pace{b['pace']}" for b in buys)
        lines.append(f"★매수 발생({len(buys)}): {tag}")
    lines.append("--- 후보별 판정 ---")
    for r in sorted(rows, key=lambda x: (x["pace"] is None, -(x["pace"] or 0))):
        if r["price"] is None:
            lines.append(f"{r['code']} {r['name']}  (조회 실패)  ✗ {r['why']}")
            continue
        mark = "★" if r["why"] == "buy" else ("▷" if r["why"] == "already_held" else "✗")
        lines.append(f"{r['code']} {r['name']}  {r['price']} / {r['pivot']}  "
                     f"{r['pct']:+.1f}%  pace{r['pace']:.1f}  {mark} {r['why']}")
    return "\n".join(lines)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -X utf8 -m pytest tests/test_autobuy_verify_volume.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: 커밋**

```bash
git add scripts/autobuy/verify_volume.py tests/test_autobuy_verify_volume.py
git commit -m "feat(autobuy): 검증 관찰기 출력 블록 렌더 _fmt_block

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 라이브 오케스트레이터 `run` + CLI `main`

**Files:**
- Modify: `scripts/autobuy/verify_volume.py` (`run`·`main`·모듈 실행부 추가)

**Interfaces:**
- Consumes: Task 1·2의 `_elapsed_frac`·`observe_sweep`·`_fmt_block`; 실전 봇 재사용 모듈 `autobuy.config.CFG`/`CANDIDATE_PATHS`/`BASE`, `autobuy.watchlist.load_actionable`/`build_ew_index`, `autobuy.signals.is_uptrend`, `canslim_lib.ohlcv_matrix`, `canslim_lib.kis_api.fetch_quote_with_volume`.
- Produces: `run(once=False, slots=None, interval=0)` 실시간 루프; `main()` CLI(`--once`·`--slots`·`--interval`). ★매수는 `scripts/autobuy/_run/verify_volume_<YYYYMMDD>.log`에 append.

- [ ] **Step 1: 구현** — `verify_volume.py` 하단에 추가 (I/O·라이브라 자동 단위테스트 없음 — Step 2 수동 스모크로 확인)

```python
def _load_env(base):
    import os
    for line in (base / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k, v)


def _regime_note(base, ohlcv_matrix, watchlist, signals):
    """국면 참고 문자열(게이트 아님). 등가중 지수 최신값 vs 20MA."""
    codes = [p.stem for p in (base / ".cache" / "ohlcv" / "series").glob("*.json")]
    idx = watchlist.build_ew_index(ohlcv_matrix.get_series, codes)
    up = signals.is_uptrend(idx, 20)
    return "상승추세(지수≥20MA)" if up else "하락추세(지수<20MA)"


def run(once=False, slots=None, interval=0):
    import os, sys, time, datetime
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # scripts/
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from autobuy.config import CFG, CANDIDATE_PATHS, BASE
    from autobuy import signals, watchlist
    sys.path.insert(0, str(BASE / "scripts"))
    from canslim_lib import ohlcv_matrix, kis_api
    ohlcv_matrix.SERIES_DIR = BASE / ".cache" / "ohlcv" / "series"
    _load_env(BASE)

    cfg = dict(CFG)
    if slots:
        cfg["SLOTS"] = slots

    run_dir = Path(__file__).resolve().parent / "_run"
    run_dir.mkdir(exist_ok=True)
    log_path = run_dir / f"verify_volume_{datetime.datetime.now():%Y%m%d}.log"

    def _logline(s):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(s + "\n")

    wl = watchlist.load_actionable(CANDIDATE_PATHS)
    avg50 = {}
    for c in wl:
        s = ohlcv_matrix.get_series(c["code"])
        vols = [v for v in (s.get("volumes") or [])[-50:] if v] if s else []
        avg50[c["code"]] = (sum(vols) / len(vols)) if vols else 0
    note = _regime_note(BASE, ohlcv_matrix, watchlist, signals)
    print(f"=== 거래량 매수 검증 관찰기 · 감시 {len(wl)}종목 · 슬롯 {cfg['SLOTS']} · 국면 {note} ===")
    print("(읽기 전용 — 실주문 없음. 국면은 게이트 아니라 참고만)")

    held_sim, skip = set(), set()
    while True:
        now = datetime.datetime.now(); hm = now.strftime("%H%M")
        if hm >= cfg["MARKET_CLOSE"] and not once:
            print("장마감 → 종료"); break
        ef = _elapsed_frac(now)
        in_win = cfg["MARKET_OPEN"] <= hm <= cfg["NEW_BUY_UNTIL"]
        quotes = {}
        for c in wl:
            if c["code"] in held_sim:
                continue                       # 이미 시뮬 보유 → 조회 아껴 already_held로 표시만
            q = kis_api.fetch_quote_with_volume(c["code"])
            if q:
                quotes[c["code"]] = q
        # held_sim 종목도 already_held 행이 나오도록 최소 시세는 있으면 좋지만, 조회 절감 위해 생략 →
        # observe_sweep이 no_quote로 처리. held는 관찰 관심 밖이라 무방(매수 판정 검증이 목적).
        rows, buys = observe_sweep(quotes, [c for c in wl if c["code"] not in held_sim],
                                   avg50, held_sim, skip, cfg, ef, in_buy_window=in_win)
        block = _fmt_block(now.strftime("%H:%M:%S"), ef, len(held_sim), cfg["SLOTS"],
                           len(wl), note, rows, buys, in_win)
        print("\n" + block, flush=True)
        for b in buys:
            _logline(f"{now:%H:%M:%S} ★매수 {b['code']} {b['name']} @{b['price']} pace{b['pace']}")
        if once:
            break
        if interval:
            time.sleep(interval)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="거래량 매수 실시간 검증 관찰기(읽기 전용)")
    ap.add_argument("--once", action="store_true", help="한 번만 스윕하고 종료")
    ap.add_argument("--slots", type=int, default=None, help="슬롯 상한 override")
    ap.add_argument("--interval", type=int, default=0, help="스윕 사이 최소 대기(초)")
    a = ap.parse_args()
    run(once=a.once, slots=a.slots, interval=a.interval)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 수동 스모크 (오케스트레이터 배선 확인)**

Run: `python -X utf8 scripts/autobuy/verify_volume.py --once`
Expected: 크래시 없이 `=== 거래량 매수 검증 관찰기 · 감시 N종목 ...` 헤더 + `--- 후보별 판정 ---` 블록 출력. (감시 후보가 0이면 "감시 0종목"만 나옴 — 정상. KIS 키/장중 여부에 따라 조회 실패행 no_quote가 섞일 수 있음 — 정상.)
확인 포인트: (1) 예외 없이 종료 (2) 후보별 사유가 evaluate_entry 결과와 일치 (3) `_run/verify_volume_<날짜>.log`는 매수 발생 시에만 생성.

- [ ] **Step 3: 전체 테스트 재확인 (회귀 없음)**

Run: `python -X utf8 -m pytest tests/test_autobuy_verify_volume.py tests/test_autobuy_signals.py -q`
Expected: PASS (verify_volume 12 + signals 기존 통과)

- [ ] **Step 4: 커밋**

```bash
git add scripts/autobuy/verify_volume.py
git commit -m "feat(autobuy): 검증 관찰기 라이브 오케스트레이터+CLI(--once/--slots/--interval)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- 실전 판정 재사용 → Task 1 `observe_sweep`가 `evaluate_entry` 호출. ✅
- 국면 게이트 off + 참고 표시 → Task 3 `_regime_note`(게이트 아님) + `_fmt_block` 국면 줄. ✅
- 후보별 판정 전부 출력 → Task 2 `_fmt_block`. ✅
- 매수창 밖 신규매수 안 함 → Task 1 `in_buy_window` + Task 3 `in_win` 계산. ✅
- ★매수 파일 로그 → Task 3 `_logline`/`log_path`. ✅
- 슬롯·pace 우선 → Task 1 `test_slot_limit_pace_priority`. ✅
- extended sticky skip → Task 1 `test_extended_skip_is_sticky_next_sweep`. ✅
- 주문 물리 차단(`kis_trade` 미import) → 세 태스크 어디서도 import 안 함. ✅
- CLI `--once/--slots/--interval` → Task 3 `main`. ✅
- 전제(`/sepa` 후보 선행)·한계 → 문서화 사항, 코드 태스크 없음(운영 안내). ✅

**Placeholder scan:** TBD/TODO/"적절히 처리" 없음 — 모든 스텝에 실제 코드/명령/기대출력 포함. ✅

**Type consistency:** `observe_sweep`/`_fmt_block`/`_elapsed_frac` 시그니처가 Task 간 일치. `rows` 딕셔너리 키(code/name/price/pivot/pct/pace/why)가 Task 1 산출과 Task 2 소비에서 동일. `held_sim`·`skip`는 set으로 일관. ✅

## 한계 메모(실행자 참고)
- Task 3의 라이브 루프는 자동 단위테스트가 없음(라이브 KIS·시계 의존) — 순수 코어(Task 1·2)로 로직을 덮고, Task 3은 배선 스모크로만 확인. 이는 replay.py의 `run()`과 동일한 테스트 전략.
- held_sim 종목은 조회를 생략해 `already_held` 행이 안 나오고 후보 목록에서 빠짐(매수 판정 검증이 목적이라 무방). 보유 종목까지 매 사이클 보고 싶어지면 후속 개선 대상.
- pace 표시식·`_elapsed_frac`가 runner.py와 문자 중복(드리프트 위험) — 판정 자체는 `evaluate_entry` 재사용이라 충실도엔 영향 없음(스펙 한계에 기록됨).
