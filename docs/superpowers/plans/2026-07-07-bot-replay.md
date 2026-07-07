# 봇 리플레이 모드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 과거 특정일을 KIS 자동매수 봇의 실제 판정 로직에 분봉으로 흘려보내 그날의 매수·매도를 봇 로그 형식으로 재현한다.

**Architecture:** 분봉 리플레이의 순수 핵심 2개(`replay_day_minutes`·`resolve_forward_daily`)를 TDD로 만들고, 그 바깥에 후보 생성(재사용)·오케스트레이터(분봉수집·국면·조립·로그출력)를 얇게 붙인다. 봇의 실제 함수(evaluate_entry/exit·is_uptrend)를 재사용해 로직을 재구현하지 않는다.

**Tech Stack:** Python 3 · pytest · 기존 canslim_lib(minute_bars·ohlcv_matrix)·autobuy(signals·config)·pivot_backtest 재사용

## Global Constraints

- 작업 위치: 워크트리 `C:\Users\hanul\playground\my-stock-bot-replay`, 브랜치 `feat/bot-replay`(origin/master eefed88).
- **봇 로직 재사용**: `autobuy.signals.evaluate_entry`·`evaluate_exit`, `autobuy.config.CFG`. 판정 재구현 금지.
- 매수 판정 = **분 종가를 현재가로**, 청산 = **분 고/저 터치**(+20% 익절 / −10% 손절, 손절 우선).
- 청산은 **결착까지**: D 당일 분봉 → 미청산분은 D+1부터 일봉 선착.
- 신규매수는 09:05~15:20(CFG MARKET_OPEN~NEW_BUY_UNTIL) 분만. 슬롯(10)·추격+3% 하드·1종목1포지션.
- **정션 금지**: `.cache`·후보 JSON은 주 작업트리(`C:\Users\hanul\playground\my-stock`) 절대경로 참조.
- 신규 파일 `scripts/autobuy/replay.py`. 테스트 `tests/test_autobuy_replay.py`. 실행 `python -X utf8`.
- 스펙: `docs/superpowers/specs/2026-07-07-bot-replay-design.md`.

## 파일 구조

- `scripts/autobuy/replay.py` — 순수(`_elapsed_frac`·`replay_day_minutes`·`resolve_forward_daily`) + 후보생성(`build_candidates_asof`) + 오케스트레이터(`run`·CLI).

---

### Task 1: 순수 핵심 — `replay_day_minutes` (분봉 리플레이, TDD)

**Files:**
- Create: `scripts/autobuy/replay.py`
- Test: `tests/test_autobuy_replay.py`

**Interfaces:**
- Consumes: `autobuy.signals.evaluate_entry`(price, pivot, acml_vol, avg50_vol, elapsed_frac, *, slots_used, slots_max, held, vol_pace_min, chase_max_pct) -> (bool, reason).
- Produces: `_elapsed_frac(t: str) -> float`; `replay_day_minutes(minutes_by_code, candidates, avg50_by_code, cfg) -> tuple[list[dict], dict]` — (events, open_positions). event: `{"t","code","name","action":"buy"|"sell","price","reason"?, "pace"?}`. open: `{code: {"entry_price","name"}}`.

- [ ] **Step 1: Write the failing tests**

`tests/test_autobuy_replay.py`:
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.replay import replay_day_minutes, _elapsed_frac

CFG = {"SLOTS": 10, "VOL_PACE_MIN": 1.5, "CHASE_MAX_PCT": 3.0, "TARGET_PCT": 20.0,
       "STOP_PCT": 10.0, "MARKET_OPEN": "0905", "NEW_BUY_UNTIL": "1520"}

def bar(t, o, h, l, c, v):
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v}

def test_elapsed_frac():
    assert _elapsed_frac("090000") <= 1e-5 + 1e-6   # 개장=0 근처
    assert abs(_elapsed_frac("153000") - 1.0) < 1e-9  # 마감=1.0
    assert 0.2 < _elapsed_frac("102000") < 0.25       # 10:20 ~ 0.205

def test_buy_on_pivot_cross_with_volume():
    # 피벗 1000, avg50=1000. 09:30(ef≈0.077) 종가 1010(+1%,피벗위·+3%이내),
    # 그 분까지 누적거래량 200 → pace=200/(1000*0.077)=2.6 ≥1.5 → 매수
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 200)]}
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    buys = [e for e in ev if e["action"] == "buy"]
    assert len(buys) == 1 and buys[0]["code"] == "A" and buys[0]["price"] == 1010
    assert "A" in held

def test_skip_extended_over_3pct():
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1040, 1045, 1035, 1040, 500)]}  # +4% → extended
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    assert [e for e in ev if e["action"] == "buy"] == [] and "A" not in held

def test_low_volume_no_buy():
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 50)]}  # pace 낮음
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    assert [e for e in ev if e["action"] == "buy"] == []

def test_exit_target_then_stop_after_entry():
    # 진입(09:30 @1010) 후 10:00 고가 1212(+20% of 1010=1212) → 익절
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 300),
                  bar("100000", 1100, 1220, 1090, 1200, 100)]}
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    sells = [e for e in ev if e["action"] == "sell"]
    assert len(sells) == 1 and sells[0]["reason"] == "익절" and "A" not in held

def test_stop_hit():
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 300),
                  bar("100000", 1000, 1005, 900, 905, 100)]}  # 저가 900 ≤ 1010*0.9=909 → 손절
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    sells = [e for e in ev if e["action"] == "sell"]
    assert len(sells) == 1 and sells[0]["reason"] == "손절"

def test_slot_limit_pace_priority():
    cfg = {**CFG, "SLOTS": 1}
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"},
             {"code": "B", "name": "비", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 200)],   # pace 2.6
            "B": [bar("093000", 1005, 1012, 1004, 1010, 500)]}   # pace 6.5 (우선)
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0, "B": 1000.0}, cfg)
    buys = [e for e in ev if e["action"] == "buy"]
    assert len(buys) == 1 and buys[0]["code"] == "B"   # pace 높은 B만
```

- [ ] **Step 2: Run to verify fail**

Run: `python -X utf8 -m pytest tests/test_autobuy_replay.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'autobuy.replay'`.

- [ ] **Step 3: Implement** — `scripts/autobuy/replay.py`:
```python
"""봇 리플레이 — 과거 특정일 분봉을 봇 판정 로직에 흘려 매수·매도를 재현.
순수 핵심(replay_day_minutes·resolve_forward_daily)은 합성 입력으로 테스트 가능."""
from __future__ import annotations


def _elapsed_frac(t: str) -> float:
    """t='HHMMSS' → 09:00~15:30(6.5h) 경과 비율(1e-6~1.0)."""
    s = int(t[:2]) * 3600 + int(t[2:4]) * 60 + int(t[4:6]) - 9 * 3600
    return max(1e-6, min(1.0, s / (6.5 * 3600)))


def replay_day_minutes(minutes_by_code, candidates, avg50_by_code, cfg):
    """D일 분봉을 분 단위로 흘려 봇 판정. 반환 (events, open_positions).
    매수=분 종가로 evaluate_entry, 청산=분 고/저 터치(손절 우선). 신규매수는 매수창만."""
    from autobuy.signals import evaluate_entry
    bar_at = {c["code"]: {b["t"]: b for b in minutes_by_code.get(c["code"], [])} for c in candidates}
    all_t = sorted({b["t"] for m in minutes_by_code.values() for b in m})
    cumvol = {c["code"]: 0.0 for c in candidates}
    held, skip, events = {}, set(), []
    for t in all_t:
        ef, hm = _elapsed_frac(t), t[:4]
        for c in candidates:                         # 누적거래량(모든 후보, 매 분)
            b = bar_at[c["code"]].get(t)
            if b:
                cumvol[c["code"]] += b["v"]
        for code in list(held):                      # 청산(보유) — 분 고/저, 손절 우선
            b = bar_at[code].get(t)
            if not b:
                continue
            ep = held[code]["entry_price"]
            if b["l"] <= ep * (1 - cfg["STOP_PCT"] / 100):
                events.append({"t": t, "code": code, "name": held[code]["name"],
                               "action": "sell", "reason": "손절", "price": round(ep * (1 - cfg["STOP_PCT"] / 100), 2)})
                del held[code]
            elif b["h"] >= ep * (1 + cfg["TARGET_PCT"] / 100):
                events.append({"t": t, "code": code, "name": held[code]["name"],
                               "action": "sell", "reason": "익절", "price": round(ep * (1 + cfg["TARGET_PCT"] / 100), 2)})
                del held[code]
        if not (cfg["MARKET_OPEN"] <= hm <= cfg["NEW_BUY_UNTIL"]):
            continue
        fire = []                                    # 신규매수 판정
        for c in candidates:
            code = c["code"]
            if code in held or code in skip:
                continue
            b = bar_at[code].get(t)
            if not b:
                continue
            price = b["c"]
            av = avg50_by_code.get(code, 0)
            ok, why = evaluate_entry(price, c["pivot"], cumvol[code], av, ef,
                                     slots_used=len(held), slots_max=cfg["SLOTS"], held=False,
                                     vol_pace_min=cfg["VOL_PACE_MIN"], chase_max_pct=cfg["CHASE_MAX_PCT"])
            if why == "extended":
                skip.add(code)
            if ok:
                fire.append((cumvol[code] / (av * ef), c, price))
        for pace, c, price in sorted(fire, key=lambda x: -x[0]):
            if len(held) >= cfg["SLOTS"]:
                break
            held[c["code"]] = {"entry_price": price, "name": c["name"]}
            events.append({"t": t, "code": c["code"], "name": c["name"],
                           "action": "buy", "price": price, "pace": round(pace, 1)})
    return events, held
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -X utf8 -m pytest tests/test_autobuy_replay.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**
```bash
git add scripts/autobuy/replay.py tests/test_autobuy_replay.py
git commit -m "feat(bot-replay): replay_day_minutes 분봉 리플레이 순수핵심(TDD)"
```

---

### Task 2: 순수 핵심 — `resolve_forward_daily` (미청산 결착, TDD)

**Files:**
- Modify: `scripts/autobuy/replay.py`
- Test: `tests/test_autobuy_replay.py`

**Interfaces:**
- Produces: `resolve_forward_daily(open_positions, series_by_code, entry_date, *, target_pct=20.0, stop_pct=10.0) -> list[dict]` — D+1부터 일봉 선착. event: `{"date","code","name","action":"sell","reason":"익절"|"손절","price"}` 또는 `{"code","name","action":"unresolved","reason"}`.

- [ ] **Step 1: Write failing tests** (같은 파일에 추가)
```python
from autobuy.replay import resolve_forward_daily

def _series(dates, highs, lows):
    return {"dates": dates, "highs": highs, "lows": lows}

def test_forward_target():
    op = {"A": {"entry_price": 1000.0, "name": "에이"}}
    s = {"A": _series(["d0", "d1", "d2"], [1010, 1100, 1210], [990, 1050, 1150])}  # d2 고 1210≥1200
    ev = resolve_forward_daily(op, s, "d0")
    assert ev[0]["action"] == "sell" and ev[0]["reason"] == "익절" and ev[0]["date"] == "d2"

def test_forward_stop():
    op = {"A": {"entry_price": 1000.0, "name": "에이"}}
    s = {"A": _series(["d0", "d1"], [1010, 1050], [990, 890])}  # d1 저 890≤900
    ev = resolve_forward_daily(op, s, "d0")
    assert ev[0]["reason"] == "손절" and ev[0]["date"] == "d1"

def test_forward_unresolved():
    op = {"A": {"entry_price": 1000.0, "name": "에이"}}
    s = {"A": _series(["d0", "d1"], [1010, 1050], [990, 950])}  # 결착 안됨
    ev = resolve_forward_daily(op, s, "d0")
    assert ev[0]["action"] == "unresolved"

def test_forward_no_data():
    ev = resolve_forward_daily({"A": {"entry_price": 1000.0, "name": "에이"}}, {}, "d0")
    assert ev[0]["action"] == "unresolved" and ev[0]["reason"] == "no_data"
```

- [ ] **Step 2: Run to verify fail** — `python -X utf8 -m pytest tests/test_autobuy_replay.py -k forward -v` → cannot import.

- [ ] **Step 3: Implement** — `replay.py` 에 추가:
```python
def resolve_forward_daily(open_positions, series_by_code, entry_date, *, target_pct=20.0, stop_pct=10.0):
    """D 마감까지 미청산 포지션을 D+1부터 일봉 선착으로 결착. 같은날 둘다면 손절 가정."""
    out = []
    for code, pos in open_positions.items():
        ep = pos["entry_price"]
        T, S = ep * (1 + target_pct / 100), ep * (1 - stop_pct / 100)
        s = series_by_code.get(code)
        if not s or entry_date not in (s.get("dates") or []):
            out.append({"code": code, "name": pos["name"], "action": "unresolved", "reason": "no_data"})
            continue
        ds, hi, lo = s["dates"], s["highs"], s["lows"]
        ni, done = ds.index(entry_date), False
        for j in range(ni + 1, len(ds)):
            if lo[j] is not None and lo[j] <= S:
                out.append({"date": ds[j], "code": code, "name": pos["name"],
                            "action": "sell", "reason": "손절", "price": round(S, 2)}); done = True; break
            if hi[j] is not None and hi[j] >= T:
                out.append({"date": ds[j], "code": code, "name": pos["name"],
                            "action": "sell", "reason": "익절", "price": round(T, 2)}); done = True; break
        if not done:
            out.append({"code": code, "name": pos["name"], "action": "unresolved", "reason": "open"})
    return out
```

- [ ] **Step 4: Run tests** — `python -X utf8 -m pytest tests/test_autobuy_replay.py -v` → 전부 pass(11).
- [ ] **Step 5: Commit**
```bash
git add scripts/autobuy/replay.py tests/test_autobuy_replay.py
git commit -m "feat(bot-replay): resolve_forward_daily 미청산 일봉 결착(TDD)"
```

---

### Task 3: 후보 생성 `build_candidates_asof` (재사용)

**Files:**
- Modify: `scripts/autobuy/replay.py`
- Test: 실 캐시 스모크(단위테스트 아님 — 유니버스·RS 의존)

**Interfaces:**
- Produces: `build_candidates_asof(asof, get_series, meta, rs_min=80) -> list[dict]` — asof 종가 기준 actionable 후보 `[{code,name,pivot,pattern}]`. (pivot_backtest_nextday_multi 의 검출 로직과 동일: 절단→RS→트렌드게이트→패턴 actionable.)

- [ ] **Step 1: Implement** — `replay.py` 에 추가(파일 상단에 지연 import):
```python
def build_candidates_asof(asof, get_series, meta, rs_min=80):
    """asof 마지막 날 status=actionable + 트렌드 통과(RS≥rs_min) 후보. meta: {code: {name,...}}."""
    from canslim_lib.trend_template import evaluate_trend_template
    from canslim_lib.pivot_backtest import truncate_series
    from canslim_lib.vcp import evaluate_vcp
    from canslim_lib.cheat import evaluate_cheat, DEFAULT_PARAMS as CH
    from canslim_lib.power_play import evaluate_power_play
    from screen_trend_template import _compute_rs_for_all
    stD = {}
    for code in meta:
        s = get_series(code)
        if not s or not s.get("closes"):
            continue
        t = truncate_series(s, asof)
        if len(t["closes"]) >= 200:
            stD[code] = t
    rs = _compute_rs_for_all([{"code": c, "closes": t["closes"], "ok": True} for c, t in stD.items()])
    def _act(t, pname):
        try:
            r = evaluate_vcp(t) if pname == "VCP" else evaluate_cheat(t, CH) if pname == "3C" else evaluate_power_play(t)
        except Exception:
            return None
        return r["pivot_price"] if r.get("status") == "actionable" and r.get("pivot_price") else None
    out, seen = [], set()
    for code, t in stD.items():
        rsv = (rs.get(code) or {}).get("rs")
        if not evaluate_trend_template(t["closes"], rs=rsv, rs_min=rs_min)["pass"]:
            continue
        for pname in ("VCP", "3C", "PP"):
            pv = _act(t, pname)
            if pv is not None and code not in seen:
                seen.add(code)
                out.append({"code": code, "name": meta[code].get("name", code), "pivot": float(pv), "pattern": pname})
    return out
```
(주의: `_compute_rs_for_all`·`fetch_universe_with_cap` 은 `scripts/` 가 sys.path 에 있어야 import 됨 — 오케스트레이터가 처리.)

- [ ] **Step 2: 스모크(실 캐시, 4/1 기준)** — 오케스트레이터 없이 직접:
Run(주 작업트리 캐시·유니버스 사용):
```bash
python -X utf8 -c "import sys; from pathlib import Path; MAIN=Path(r'C:\Users\hanul\playground\my-stock'); sys.path.insert(0,'scripts'); from canslim_lib import ohlcv_matrix; ohlcv_matrix.SERIES_DIR=MAIN/'.cache'/'ohlcv'/'series'; from canslim_lib.pykrx_universe import fetch_universe_with_cap; from autobuy.replay import build_candidates_asof; meta={u['code']:u for u in fetch_universe_with_cap('ALL')}; c=build_candidates_asof('2026-04-01', ohlcv_matrix.get_series, meta); print('후보', len(c), c[:3])"
```
Expected: `후보 117 [...]` 정도(4/1 actionable 고유종목 ~117 — [[sepa-nextday-breakout-findings]] 검증치와 일치). 몇 분 소요(RS·검출).

- [ ] **Step 3: Commit**
```bash
git add scripts/autobuy/replay.py
git commit -m "feat(bot-replay): build_candidates_asof 후보 생성(재사용)"
```

---

### Task 4: 오케스트레이터 + CLI + 통합 실행

**Files:**
- Modify: `scripts/autobuy/replay.py` (`run`·`main`)
- 산출(선택): `public/data/bot-replay-<date>.json`

**Interfaces:**
- Consumes: 전 태스크 + `canslim_lib.minute_bars.fetch_day_minutes`, `ohlcv_matrix.get_series`, `autobuy.config.CFG`, `autobuy.watchlist.build_ew_index`·`is_uptrend`, `fetch_universe_with_cap`.

- [ ] **Step 1: Implement `run`·`main`** — `replay.py` 에 추가:
```python
def _prev_trading_day(cal, d):
    prior = [x for x in cal if x < d]
    return prior[-1] if prior else None


def run(entry_date, slots=None):
    import os, sys
    from pathlib import Path
    MAIN = Path(r"C:\Users\hanul\playground\my-stock")
    sys.path.insert(0, str(MAIN / "scripts"))
    from canslim_lib import ohlcv_matrix, minute_bars
    ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
    from canslim_lib.pykrx_universe import fetch_universe_with_cap
    from autobuy.config import CFG
    from autobuy import watchlist
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k, v)
    cfg = dict(CFG)
    if slots:
        cfg["SLOTS"] = slots
    meta = {u["code"]: u for u in fetch_universe_with_cap("ALL")}
    cal = ohlcv_matrix.get_series("005930")["dates"]
    scan = _prev_trading_day([d for d in cal if d <= entry_date], entry_date)
    print(f"=== 봇 리플레이 · 진입일 {entry_date} (스캔 {scan}) ===")
    # 국면 게이트(스캔일 기준)
    codes_all = [p.stem for p in (MAIN / ".cache" / "ohlcv" / "series").glob("*.json")]
    idx_full = watchlist.build_ew_index(ohlcv_matrix.get_series, codes_all)
    # scan 시점까지로 자른 지수로 판정
    scan_i = cal.index(scan) if scan in cal else len(idx_full) - 1
    if not watchlist.is_uptrend(idx_full[:scan_i + 1], 20):
        print(f"국면=하락추세(스캔일 지수<20MA) → 그날 봇은 매매 OFF."); return
    print("국면=상승추세 → 가동")
    cands = build_candidates_asof(scan, ohlcv_matrix.get_series, meta)
    print(f"감시목록 {len(cands)}종목 · 분봉 수집 중…")
    minutes, avg50 = {}, {}
    for c in cands:
        m = minute_bars.fetch_day_minutes(c["code"], entry_date)
        if m:
            minutes[c["code"]] = m
        s = ohlcv_matrix.get_series(c["code"]); vs = [v for v in (s["volumes"] or [])[-50:] if v] if s else []
        avg50[c["code"]] = (sum(vs) / len(vs)) if vs else 0
    live = [c for c in cands if c["code"] in minutes]
    events, held = replay_day_minutes(minutes, live, avg50, cfg)
    fwd = resolve_forward_daily(held, {c["code"]: ohlcv_matrix.get_series(c["code"]) for c in live}, entry_date)
    # 로그 출력(봇 형식)
    for e in sorted([x for x in events], key=lambda x: x["t"]):
        tt = f"{e['t'][:2]}:{e['t'][2:4]}"
        if e["action"] == "buy":
            print(f"{tt} 매수 {e['code']} {e['name']} @{e['price']} pace{e['pace']}")
        else:
            print(f"{tt} 매도 {e['code']} {e['reason']} @{e['price']}")
    for e in fwd:
        if e["action"] == "sell":
            print(f"{e['date']} 매도 {e['code']} {e['name']} {e['reason']} @{e['price']} (이후 일봉 결착)")
        else:
            print(f"       미청산 {e['code']} {e['name']} ({e['reason']})")
    n_buy = sum(1 for e in events if e["action"] == "buy")
    win = sum(1 for e in events if e.get("reason") == "익절") + sum(1 for e in fwd if e.get("reason") == "익절")
    loss = sum(1 for e in events if e.get("reason") == "손절") + sum(1 for e in fwd if e.get("reason") == "손절")
    unres = sum(1 for e in fwd if e["action"] == "unresolved")
    pnl = win * cfg["TARGET_PCT"] - loss * cfg["STOP_PCT"]
    print(f"\n요약: 매수 {n_buy} · 익절 {win} · 손절 {loss} · 미청산 {unres} · 합산손익 {pnl:+.0f}%p (익절+{cfg['TARGET_PCT']:.0f}/손절-{cfg['STOP_PCT']:.0f})")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="진입일 YYYY-MM-DD")
    ap.add_argument("--slots", type=int, default=None)
    a = ap.parse_args()
    run(a.date, a.slots)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 통합 실행 (강세일 실데이터)** — 4/7(강세일)로 리플레이:

Run:
```bash
python -X utf8 scripts/autobuy/replay.py --date 2026-04-07
```
Expected: `국면=상승추세 → 가동` · `감시목록 N종목` · 매수/매도 로그(있으면) · 요약. (분봉 수집에 몇 분; 무오류로 끝나면 성공. 국면이 하락이면 "매매 OFF" 로그 후 종료 — 다른 강세일로 재시도.)

- [ ] **Step 3: 전체 테스트 재확인** — `python -X utf8 -m pytest tests/test_autobuy_replay.py -v` → 11 pass.

- [ ] **Step 4: Commit**
```bash
git add scripts/autobuy/replay.py
git commit -m "feat(bot-replay): 오케스트레이터+CLI(분봉수집·국면·조립·봇로그 출력) + 통합"
```

---

## Self-Review

**1. Spec coverage**
- 진입일 D 하나 입력·스캔 D-1 → Task4(`_prev_trading_day`). ✅
- 봇 실제 함수 재사용(evaluate_entry) → Task1. ✅ · 국면 게이트(is_uptrend) → Task4. ✅
- 매수=분 종가, 청산=분 고/저 터치·손절 우선 → Task1. ✅
- 결착까지(당일 분봉→이후 일봉) → Task1(당일)+Task2(일봉). ✅
- 후보 actionable as-of(재사용) → Task3. ✅
- 봇 로그 형식 + 요약 → Task4. ✅ · 슬롯·추격+3%·매수창 → Task1(CFG). ✅

**2. Placeholder scan** — 순수 핵심(1·2)·후보생성(3)·오케스트레이터(4) 전부 완전한 코드. 외부(KIS 분봉·유니버스)는 스모크/통합 실행으로 검증.

**3. Type consistency**
- `replay_day_minutes(minutes_by_code, candidates, avg50_by_code, cfg) -> (events, held)` Task1 ↔ Task4 소비. ✅
- event `{"t","code","name","action","price","reason"?,"pace"?}` Task1 ↔ Task4 출력(e["t"]·e["action"]·e["price"]·e["reason"]·e["pace"]). ✅
- `resolve_forward_daily(open, series_by_code, entry_date) -> [event]` Task2 ↔ Task4(fwd). ✅
- `build_candidates_asof(asof, get_series, meta) -> [{code,name,pivot,pattern}]` Task3 ↔ Task4(cands)·Task1(candidates). ✅
- CFG 키(SLOTS·VOL_PACE_MIN·CHASE_MAX_PCT·TARGET_PCT·STOP_PCT·MARKET_OPEN·NEW_BUY_UNTIL) Task1/4 일치. ✅

> 통합 위험(실행서 확인): KIS 분봉 미반환 종목은 감시 제외(Task4 `live`), 국면 게이트가 강세일 아니면 조기종료(다른 날 재시도), 바쁜 날 수집 수 분.

---

## Execution Handoff

순서: Task1(분봉 리플레이)→2(일봉 결착) 순수/TDD. 3(후보생성, 스모크)→4(오케스트레이터, 통합 실행). 4의 통합 실행이 실데이터 봇로그를 뽑는 최종 산출.
