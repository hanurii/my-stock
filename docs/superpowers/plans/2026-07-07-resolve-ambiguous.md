# 분봉 기반 예외 판정기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백테스트 예외(ambiguous) 50건을 KIS 과거 1분봉으로 되짚어 승/패로 확정하고, 백테스트 JSON·리포트를 갱신한다.

**Architecture:** 순수 판정 로직(`_daily_first_touch` 추출 + `resolve_minute_trade`)은 `pivot_backtest.py`에 두고 pytest. 과거 1분봉 수집·캐시는 `minute_bars.py`. 오케스트레이터 `resolve_ambiguous.py`가 예외 이벤트를 분봉으로 판정→재집계→리포트 재생성. 정션 금지 — `.env`·`.cache`는 주 작업트리 절대경로 참조.

**Tech Stack:** Python 3 · pytest · KIS OpenAPI(FHKST03010230) · 기존 pivot_backtest/kis_api 재사용

## Global Constraints

- 작업 위치: 워크트리 `C:\Users\hanul\playground\my-stock-resolve-amb`, 브랜치 `feat/resolve-ambiguous`(origin/master 기준).
- **정션 절대 금지.** 오케스트레이터·minute_bars 는 `MAIN = Path(r"C:\Users\hanul\playground\my-stock")` 절대경로로 `.env`(로드)·`.cache/min_daily`(쓰기)를 참조. 어느 워크트리에서 실행해도 동일 대상.
- 판정 규칙: 진입 = 피벗 첫 도달 분(`h ≥ pivot`). 진입 후 당일 선착(`h≥T` win / `l≤S` loss / 같은 분 둘다 = ambiguous `same_minute`). 당일 미결 → 이튿날부터 **일반 보유일** 일봉 선착(`_daily_first_touch`, 돌파일 특례 없음). 분봉 없음/진입 없음 → ambiguous.
- `T = pivot×1.10`, `S = pivot×0.95`.
- 대상 파일: `public/data/pivot-backtest-2026-04-01.json` 의 `ambiguous` 50건.
- 스펙: `docs/superpowers/specs/2026-07-07-resolve-ambiguous-minute-design.md`.
- 파이썬 테스트 `python -m pytest`. TDD(순수 로직). 커밋 자주. KIS 호출은 스로틀링.

---

### Task 1: `_daily_first_touch` 추출 + `simulate_pivot_trade` 리팩터 (TDD, 무행동변화)

**Files:**
- Modify: `scripts/canslim_lib/pivot_backtest.py`
- Test: `tests/test_pivot_backtest.py`

**Interfaces:**
- Produces: `_daily_first_touch(series, b, start_idx, pivot, target_pct=10.0, stop_pct=5.0) -> dict` (일반 보유일 선착; both→ambiguous·high≥T→win·low≤S→loss·끝→unresolved; 결과 창 metadata 는 [b, i]).
- `simulate_pivot_trade` 는 동작 불변(리팩터만).

- [ ] **Step 1: Write the failing tests**

`tests/test_pivot_backtest.py` 하단에 추가(기존 `mk` 헬퍼 재사용):

```python
from canslim_lib.pivot_backtest import _daily_first_touch


def test_daily_first_touch_stop_only_is_loss_not_ambiguous():
    # start_idx 부터는 '일반 보유일' — 저가만 -5% 면 loss(돌파일 특례 없음)
    s = mk(highs=[104.0, 104.0], lows=[99.0, 94.0])
    r = _daily_first_touch(s, 0, 0, 100.0)
    assert r["result"] == "loss"


def test_daily_first_touch_both_is_ambiguous():
    s = mk(highs=[111.0, 104.0], lows=[94.0, 99.0])
    assert _daily_first_touch(s, 0, 0, 100.0)["result"] == "ambiguous"


def test_daily_first_touch_target_and_unresolved():
    s = mk(highs=[111.0], lows=[99.0])
    assert _daily_first_touch(s, 0, 0, 100.0)["result"] == "win"
    s2 = mk(highs=[104.0, 105.0], lows=[99.0, 100.0], closes=[103.0, 104.0])
    assert _daily_first_touch(s2, 0, 0, 100.0)["result"] == "unresolved"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pivot_backtest.py -k daily_first_touch -v`
Expected: FAIL — `cannot import name '_daily_first_touch'`.

- [ ] **Step 3: Add `_daily_first_touch` and refactor `simulate_pivot_trade`**

`pivot_backtest.py` 에서 `simulate_pivot_trade` 를 다음으로 교체하고, 그 위에 `_daily_first_touch` 추가:

```python
def _daily_first_touch(series, b, start_idx, pivot, target_pct=10.0, stop_pct=5.0):
    """일반 보유일 선착(돌파일 특례 없음): start_idx..끝.
    both→ambiguous, high≥T→win, low≤S→loss, 끝까지 미도달→unresolved.
    결과 metadata 창은 [b, i]. simulate_pivot_trade(i>b)·resolve 재개가 공유."""
    highs, lows = series["highs"], series["lows"]
    n = len(series["closes"])
    T = pivot * (1 + target_pct / 100)
    S = pivot * (1 - stop_pct / 100)
    for i in range(start_idx, n):
        hi, lo = highs[i], lows[i]
        hit_t = hi is not None and hi >= T
        hit_s = lo is not None and lo <= S
        if hit_t and hit_s:
            return _result("ambiguous", series, b, i, pivot, "both_same_day")
        if hit_t:
            return _result("win", series, b, i, pivot, "target")
        if hit_s:
            return _result("loss", series, b, i, pivot, "stop")
    return _result("unresolved", series, b, n - 1, pivot, "open")


def simulate_pivot_trade(series, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0):
    """피벗 매수 후 +target%/-stop% 선착. 돌파일 포함, 같은날 둘다/돌파일 손절만=ambiguous."""
    highs, lows = series["highs"], series["lows"]
    T = pivot * (1 + target_pct / 100)
    S = pivot * (1 - stop_pct / 100)
    b = breakout_idx
    hi, lo = highs[b], lows[b]
    hit_t = hi is not None and hi >= T
    hit_s = lo is not None and lo <= S
    if hit_t and hit_s:
        return _result("ambiguous", series, b, b, pivot, "both_same_day_breakout")
    if hit_t:
        return _result("win", series, b, b, pivot, "target")
    if hit_s:
        return _result("ambiguous", series, b, b, pivot, "stop_on_breakout_day")
    return _daily_first_touch(series, b, b + 1, pivot, target_pct, stop_pct)
```

- [ ] **Step 4: Run the full test file (동작 불변 확인)**

Run: `python -m pytest tests/test_pivot_backtest.py -v`
Expected: 전부 PASS — 기존 simulate_pivot_trade 테스트(돌파일 win/stop/both, 이후날 win/loss/both, unresolved) + 신규 _daily_first_touch 3개. (리팩터가 동작을 바꾸지 않았음을 기존 테스트가 보증.)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/pivot_backtest.py tests/test_pivot_backtest.py
git commit -m "refactor(pivot-backtest): _daily_first_touch 추출(로직 1벌) — simulate 동작 불변"
```

---

### Task 2: `resolve_minute_trade` (TDD)

**Files:**
- Modify: `scripts/canslim_lib/pivot_backtest.py`
- Test: `tests/test_pivot_backtest.py`

**Interfaces:**
- Consumes: `_daily_first_touch`(Task 1).
- Produces: `resolve_minute_trade(minutes, daily, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0) -> dict` (`result: win|loss|ambiguous`, `resolved_by: minute|daily`, `entry_time`, `resolve_date`, `reason`).
  - `minutes`: 돌파 당일 1분봉 오름차순 리스트 `[{"t","o","h","l","c","v"}]`.

- [ ] **Step 1: Write the failing tests**

```python
from canslim_lib.pivot_backtest import resolve_minute_trade


def _daily(dates, highs, lows, closes=None):
    n = len(dates)
    closes = closes or [(highs[i] + lows[i]) / 2 for i in range(n)]
    return {"dates": dates, "closes": closes, "opens": list(closes),
            "highs": list(highs), "lows": list(lows), "volumes": [1.0] * n}


def _min(rows):  # rows: [(t,h,l)] → 분봉 dict 리스트
    return [{"t": t, "o": h, "h": h, "l": l, "c": (h + l) / 2, "v": 1.0} for t, h, l in rows]


def test_minute_entry_then_target_is_win():
    # 피벗 100 도달(체결) 후 +10% 먼저 → win
    m = _min([("0901", 98, 97), ("0902", 100, 99), ("0903", 111, 105)])
    d = _daily(["2026-03-20"], [111], [97])
    r = resolve_minute_trade(m, d, 0, 100.0)
    assert r["result"] == "win" and r["resolved_by"] == "minute" and r["entry_time"] == "0902"


def test_minute_pre_entry_dip_ignored_then_stop_after_entry_is_loss():
    # 진입 전 저점(96, -4%지만 매수 전) 무시 → 진입 후 -5% 관통 → loss
    m = _min([("0901", 99, 94), ("0902", 100, 99), ("0903", 101, 94)])
    d = _daily(["2026-03-20"], [101], [94])
    r = resolve_minute_trade(m, d, 0, 100.0)
    assert r["result"] == "loss" and r["entry_time"] == "0902"


def test_minute_no_exit_then_resume_daily():
    # 당일 진입 후 아무것도 안 닿음 → 이튿날 일봉 +10% → win(resolved_by daily)
    m = _min([("0902", 100, 99), ("0903", 104, 99)])
    d = _daily(["2026-03-20", "2026-03-23"], [104, 111], [99, 101])
    r = resolve_minute_trade(m, d, 0, 100.0)
    assert r["result"] == "win" and r["resolved_by"] == "daily" and r["resolve_date"] == "2026-03-23"


def test_minute_same_bar_both_is_ambiguous():
    m = _min([("0902", 100, 99), ("0903", 111, 94)])  # 한 분봉에 +10%·-5% 동시
    d = _daily(["2026-03-20"], [111], [94])
    assert resolve_minute_trade(m, d, 0, 100.0)["reason"] == "same_minute"


def test_minute_no_data_is_ambiguous():
    d = _daily(["2026-03-20"], [111], [94])
    r = resolve_minute_trade([], d, 0, 100.0)
    assert r["result"] == "ambiguous" and r["reason"] == "no_minute_data"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pivot_backtest.py -k "resolve_minute" -v`
Expected: FAIL — `cannot import name 'resolve_minute_trade'`.

- [ ] **Step 3: Implement**

`pivot_backtest.py` 에 추가:

```python
def resolve_minute_trade(minutes, daily, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0):
    """돌파 당일 1분봉으로 진입(피벗 첫 도달)→선착 판정. 당일 미결이면 이튿날부터 일봉 선착.
    반환: result·resolved_by·entry_time·resolve_date·reason."""
    bdate = daily["dates"][breakout_idx]
    T = pivot * (1 + target_pct / 100)
    S = pivot * (1 - stop_pct / 100)
    if not minutes:
        return {"result": "ambiguous", "resolved_by": "minute", "reason": "no_minute_data",
                "entry_time": None, "resolve_date": bdate}
    entry = next((k for k, m in enumerate(minutes) if m["h"] >= pivot), None)
    if entry is None:
        return {"result": "ambiguous", "resolved_by": "minute", "reason": "no_entry",
                "entry_time": None, "resolve_date": bdate}
    etime = minutes[entry]["t"]
    for m in minutes[entry:]:
        hit_t = m["h"] >= T
        hit_s = m["l"] <= S
        if hit_t and hit_s:
            return {"result": "ambiguous", "resolved_by": "minute", "reason": "same_minute",
                    "entry_time": etime, "resolve_date": bdate}
        if hit_t:
            return {"result": "win", "resolved_by": "minute", "reason": "target",
                    "entry_time": etime, "resolve_date": bdate}
        if hit_s:
            return {"result": "loss", "resolved_by": "minute", "reason": "stop",
                    "entry_time": etime, "resolve_date": bdate}
    res = _daily_first_touch(daily, breakout_idx, breakout_idx + 1, pivot, target_pct, stop_pct)
    return {"result": res["result"], "resolved_by": "daily", "reason": res["exit_reason"],
            "entry_time": etime, "resolve_date": res["resolve_date"]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pivot_backtest.py -v`
Expected: 전부 PASS(기존 + Task1 + resolve_minute 5개).

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/pivot_backtest.py tests/test_pivot_backtest.py
git commit -m "feat(resolve-ambiguous): resolve_minute_trade 순수 판정(TDD)"
```

---

### Task 3: `minute_bars.py` — 과거 1분봉 수집·캐시

**Files:**
- Create: `scripts/canslim_lib/minute_bars.py`

**Interfaces:**
- Consumes: `os.environ["KIS_APP_KEY"/"KIS_APP_SECRET"]`(오케스트레이터가 .env 로드), `kis_api.get_access_token`.
- Produces: `fetch_day_minutes(code: str, date: str, force=False) -> list[dict]` — 특정일 1분봉 오름차순 `[{"t"(HHMMSS),"o","h","l","c","v"}]`. 캐시 `MAIN/.cache/min_daily/<code>_<yyyymmdd>.json`. 실패 시 빈 리스트.

- [ ] **Step 1: Implement**

`scripts/canslim_lib/minute_bars.py`:

```python
# scripts/canslim_lib/minute_bars.py
"""KIS 과거 1분봉(FHKST03010230, 주식일별분봉조회) 수집 + 로컬 캐시.
검증된 페이징 로직(scripts/_fetch_min_all.py)을 과거 TR로 정리·모듈화.
캐시·인증은 주 작업트리(my-stock) 절대경로 기준(정션 금지)."""
from __future__ import annotations

import json
import os
import time
import urllib.parse as up
import urllib.request as ur
from pathlib import Path

from canslim_lib import kis_api

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
CACHE_DIR = MAIN / ".cache" / "min_daily"
BASE = "https://openapi.koreainvestment.com:9443"


def _headers() -> dict:
    return {
        "content-type": "application/json",
        "authorization": f"Bearer {kis_api.get_access_token()}",
        "appkey": os.environ["KIS_APP_KEY"],
        "appsecret": os.environ["KIS_APP_SECRET"],
        "custtype": "P",
        "tr_id": "FHKST03010230",
    }


def _call(code: str, date: str, end: str, headers: dict) -> list[dict]:
    qs = up.urlencode({
        "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code,
        "FID_INPUT_DATE_1": date, "FID_INPUT_HOUR_1": end,
        "FID_PW_DATA_INCU_YN": "Y", "FID_FAKE_TICK_INCU_YN": "N",
    })
    url = f"{BASE}/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice?{qs}"
    for _ in range(4):
        try:
            with ur.urlopen(ur.Request(url, headers=headers), timeout=10) as r:
                d = json.loads(r.read().decode("utf-8"))
            if d.get("rt_cd") == "0":
                return d.get("output2") or []
            if d.get("msg_cd") == "EGW00201":   # 초당 호출 초과
                time.sleep(0.6); continue
            return []
        except Exception:
            time.sleep(0.4)
    return []


def _dec_min(h: str) -> str | None:
    s = int(h[:2]) * 3600 + int(h[2:4]) * 60 + int(h[4:6]) - 60
    return None if s < 0 else f"{s // 3600:02d}{(s % 3600) // 60:02d}{s % 60:02d}"


def fetch_day_minutes(code: str, date: str, force: bool = False) -> list[dict]:
    """date='YYYY-MM-DD' 또는 'YYYYMMDD'. 해당일 1분봉(오름차순). 실패 시 []."""
    ymd = date.replace("-", "")
    cache = CACHE_DIR / f"{code}_{ymd}.json"
    if cache.exists() and not force:
        return json.loads(cache.read_text(encoding="utf-8"))

    headers = _headers()
    bars: dict[str, dict] = {}
    end = "153000"
    for _ in range(8):
        rows = _call(code, ymd, end, headers)
        time.sleep(0.12)
        if not rows:
            break
        for r in rows:
            t = r.get("stck_cntg_hour")
            if not t:
                continue
            bars[t] = {"t": t, "o": float(r["stck_oprc"]), "h": float(r["stck_hgpr"]),
                       "l": float(r["stck_lwpr"]), "c": float(r["stck_prpr"]),
                       "v": float(r["cntg_vol"])}
        earliest = min(bars)
        if earliest <= "090000":
            break
        nxt = _dec_min(earliest)
        if not nxt or nxt >= end:
            break
        end = nxt

    out = [bars[t] for t in sorted(bars)]
    if out:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out
```

- [ ] **Step 2: Smoke test (실 KIS 1건)**

`.env` 로드 후 예외 1건(코드 001465, 날짜 2026-03-20)으로 확인:
Run:
```bash
python -c "import os,sys; sys.path.insert(0,'scripts'); [os.environ.setdefault(*l.strip().split('=',1)) for l in open(r'C:\Users\hanul\playground\my-stock\.env',encoding='utf-8') if '=' in l and not l.startswith('#')]; from canslim_lib import minute_bars as mb; b=mb.fetch_day_minutes('001465','2026-03-20'); print('bars',len(b),'first',b[0]['t'] if b else None,'last',b[-1]['t'] if b else None,'저',min(x['l'] for x in b) if b else None,'고',max(x['h'] for x in b) if b else None)"
```
Expected: `bars` ~300+(1분봉, 09:00~15:30), 저/고가 출력(BYC우 20260320 ≈ 저 26450 · 고 29800). 캐시 파일 `.cache/min_daily/001465_20260320.json` 생성. (0 bars면 KIS 미반환 — 인증/TR 점검.)

- [ ] **Step 3: Commit**

```bash
git add scripts/canslim_lib/minute_bars.py
git commit -m "feat(resolve-ambiguous): minute_bars 과거 1분봉 수집·캐시(FHKST03010230)"
```

---

### Task 4: `resolve_ambiguous.py` 오케스트레이터 + 판정 실행

**Files:**
- Create: `scripts/resolve_ambiguous.py`
- Modify(생성물): `public/data/pivot-backtest-2026-04-01.json`, `docs/research/2026-04-01-pivot-backtest.md`

**Interfaces:**
- Consumes: `minute_bars.fetch_day_minutes`, `pivot_backtest.resolve_minute_trade`·`tally`·`group_win_rate`, `ohlcv_matrix.get_series`.

- [ ] **Step 1: Write the orchestrator**

`scripts/resolve_ambiguous.py`:

```python
# scripts/resolve_ambiguous.py
"""백테스트 예외(ambiguous) 이벤트를 과거 1분봉으로 승/패 확정 → JSON 갱신 → 리포트 재생성.
실행: python scripts/resolve_ambiguous.py [--infile public/data/pivot-backtest-2026-04-01.json]
정의: docs/superpowers/specs/2026-07-07-resolve-ambiguous-minute-design.md
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# .env(주 작업트리) 로드 → KIS 인증
for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        import os
        os.environ.setdefault(k, v)

from canslim_lib import ohlcv_matrix, minute_bars  # noqa: E402
from canslim_lib.pivot_backtest import resolve_minute_trade, tally, group_win_rate  # noqa: E402

FEATURE_KEYS = ("pattern", "market", "price_bucket", "rel_vol_bucket", "rs_bucket")


def run(infile: Path) -> None:
    d = json.loads(infile.read_text(encoding="utf-8"))
    events = d["events"]
    amb = [e for e in events if e["result"] == "ambiguous"]
    print(f"예외 {len(amb)}건 분봉 판정 시작…")

    by_id = {(e["code"], e["breakout_date"], e["pattern"]): e for e in events}
    resolved = {"win": 0, "loss": 0, "stay": 0}
    for e in amb:
        s = ohlcv_matrix.get_series(e["code"])
        if not s or e["breakout_date"] not in s["dates"]:
            e["minute_resolution"] = {"result": "ambiguous", "reason": "no_daily"}
            resolved["stay"] += 1
            continue
        bi = s["dates"].index(e["breakout_date"])
        mins = minute_bars.fetch_day_minutes(e["code"], e["breakout_date"])
        r = resolve_minute_trade(mins, s, bi, e["pivot"])
        e["minute_resolution"] = r
        if r["result"] in ("win", "loss"):
            e["result"] = r["result"]
            e["resolve_date"] = r["resolve_date"]
            e["exit_reason"] = f"minute:{r['reason']}"
            resolved[r["result"]] += 1
        else:
            resolved["stay"] += 1
        print(f"  {e['code']} {e['name']} {e['breakout_date']} → {r['result']}"
              f"({r.get('reason')},{r.get('resolved_by')})")

    # 재집계
    d["summary"] = tally(events)
    d["by_pattern"] = group_win_rate(events, "pattern")
    d["by_feature"] = {k: group_win_rate(events, k) for k in FEATURE_KEYS}
    prio = {"loss": 0, "ambiguous": 1, "win": 2, "unresolved": 3}
    by_pair = {}
    for e in events:
        k = (e["code"], e["breakout_date"])
        if k not in by_pair or prio[e["result"]] < prio[by_pair[k]["result"]]:
            by_pair[k] = e
    d["summary_stock_level"] = tally(list(by_pair.values()))
    d["unique_stock_days"] = len(by_pair)
    d["ambiguous"] = [e for e in events if e["result"] == "ambiguous"]
    d["params"]["minute_resolved"] = True

    infile.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = d["summary"]
    print(f"\n분봉 확정: 승 {resolved['win']} · 패 {resolved['loss']} · 잔여예외 {resolved['stay']}")
    print(f"갱신 요약: 총 {s['n']} · 승 {s['win']} 패 {s['loss']} 예외 {s['ambiguous']} "
          f"· 결착 {s['win_rate_resolved']}% (최악 {s['win_rate_worst']}~최선 {s['win_rate_best']}%)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="public/data/pivot-backtest-2026-04-01.json")
    args = ap.parse_args()
    run(ROOT / args.infile)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the resolver (실 KIS — 시간 소요, 필요시 백그라운드)**

Run: `python scripts/resolve_ambiguous.py`
Expected: 예외 50건 각각 판정 로그, `분봉 확정: 승 X · 패 Y · 잔여예외 Z`, 갱신 요약(예외↓·결착 범위 축소). `.cache/min_daily/*.json` 캐시 생성. (KIS 미반환 종목은 잔여예외로 남음.)

- [ ] **Step 3: Regenerate report**

Run: `python scripts/pivot_backtest_report.py`
Expected: `docs/research/2026-04-01-pivot-backtest.md` 갱신 — 예외 표 축소, 결착 승률 범위 좁아짐.

- [ ] **Step 4: Sanity 확인**

Run:
```bash
python -c "import json;d=json.load(open('public/data/pivot-backtest-2026-04-01.json',encoding='utf-8'));s=d['summary'];print('n',s['n'],'win',s['win'],'loss',s['loss'],'amb',s['ambiguous'],'resolved',s['win_rate_resolved'],'worst',s['win_rate_worst'],'best',s['win_rate_best'],'| minute_resolved',d['params'].get('minute_resolved'))"
```
Expected: `amb` 이 50보다 크게 줄고 win/loss 증가, worst~best 범위가 좁아짐, `minute_resolved True`.

- [ ] **Step 5: Commit**

```bash
git add scripts/resolve_ambiguous.py public/data/pivot-backtest-2026-04-01.json docs/research/2026-04-01-pivot-backtest.md
git commit -m "feat(resolve-ambiguous): 오케스트레이터 + 예외 분봉 확정 결과 반영"
```

---

## Self-Review

**1. Spec coverage**
- 과거 1분봉 수집·캐시(FHKST03010230, 페이징) → Task 3. ✅
- 진입=피벗 첫 도달·진입 후 선착·진입 전 저점 무시 → Task 2 `resolve_minute_trade`. ✅
- 미결 시 이튿날부터 일반 보유일 일봉 선착(돌파일 특례 없음, 공용 헬퍼) → Task 1 `_daily_first_touch` + Task 2 재개. ✅
- 같은 1분봉 동시/분봉 없음 → ambiguous 유지 → Task 2. ✅
- JSON 재집계·리포트 재생성·잔여예외만 남김 → Task 4. ✅
- 정션 금지·절대경로 .env/.cache → Task 3·4. ✅

**2. Placeholder scan** — 실제 코드·명령·기대출력만. ✅

**3. Type consistency**
- `_daily_first_touch(series, b, start_idx, pivot, ...)` — Task1 정의 ↔ simulate_pivot_trade·resolve_minute_trade 호출 일치(둘 다 b=breakout_idx, start_idx=b+1). ✅
- `resolve_minute_trade(minutes, daily, breakout_idx, pivot)` 반환(result·resolved_by·entry_time·resolve_date·reason) — Task2 정의 ↔ Task4 소비(`r["result"]`·`r["resolve_date"]`·`r["reason"]`) 일치. ✅
- `fetch_day_minutes(code, date)` → 오름차순 `[{t,o,h,l,c,v}]` — Task3 ↔ Task2 테스트 `_min` 형태·resolve의 `m["h"]/m["l"]` 일치. ✅
- `tally`/`group_win_rate` 재사용(기존) — Task4. ✅

> 통합 위험(실행 시 드러남): KIS 인증/TR·과거 보관 한계(오래된 날짜 0 bars→잔여예외), 초당 호출 제한(throttle 0.12s). Task3 스모크·Task4 실행에서 확인.

---

## Execution Handoff

순서: Task 1(추출·불변) → 2(resolve, 1 의존) — 순수/TDD. 3(minute_bars, 스모크) → 4(오케스트레이터, 실행). 3·4는 `.env`·캐시(주 작업트리 절대경로) 필요.
