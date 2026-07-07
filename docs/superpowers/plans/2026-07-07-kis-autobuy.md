# KIS 자동매수 봇 v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SEPA 진입임박 후보가 장중 피벗을 거래량 실려 돌파할 때 KIS 실계좌로 1주 자동매수하고, 봇 감시로 −10%/+20% 청산하는 봇.

**Architecture:** 순수 판정함수(entry_signal·exit_monitor)를 핵심에 두고 TDD. 그 바깥에 후보 로더(+국면 게이트)·KIS 주문/시세 모듈·장중 러너를 얇게 붙인다. 실주문 안전을 위해 수량은 코드에 1주 하드코딩, 기본 모드는 dryrun.

**Tech Stack:** Python 3 · pytest · KIS OpenAPI(REST) · 기존 canslim_lib(kis_api·ohlcv_matrix) 재사용

## Global Constraints

- 작업 위치: 워크트리 `C:\Users\hanul\playground\my-stock-kis-autobuy`, 브랜치 `feat/kis-autobuy`(origin/master 기준).
- **주문 수량은 항상 1주 — 코드에 하드코딩. 수량 매개변수·설정 없음.** 어떤 경로로도 1주 초과 주문 불가.
- **추격 금지(하드)**: 현재가 > 피벗×1.03 이면 매수 금지(스킵). 소프트 아님.
- **매수 조건(전부 충족)**: price≥pivot · price≤pivot×1.03 · vol_pace≥1.5 · 슬롯여유 · 미보유.
- **청산**: 진입가 대비 ≤−10% 손절 / ≥+20% 목표, 시장가 매도(봇 감시).
- **기본 모드 = dryrun**(로그만, 실주문 X). `live`는 명시적 설정+실행인자 둘 다 필요.
- 신규 파일 위치: `scripts/autobuy/`. 테스트: `tests/test_autobuy_*.py`.
- 파이썬 실행 `python -X utf8`. 스펙: `docs/superpowers/specs/2026-07-07-kis-autobuy-design.md`.
- KIS 초당 20건 제한 — 기존 `kis_api._throttle` 준수.

## 파일 구조

- `scripts/autobuy/signals.py` — 순수 판정: `evaluate_entry`, `evaluate_exit`, `is_uptrend`.
- `scripts/autobuy/watchlist.py` — 후보 로드(`load_actionable`) + 국면지수(`build_ew_index`).
- `scripts/canslim_lib/kis_api.py`(수정) — 시세: `fetch_quote_with_volume`.
- `scripts/autobuy/kis_trade.py` — 주문/잔고: `place_buy_1share`·`place_sell_1share`·`inquire_holdings`(1주 하드코딩, dryrun).
- `scripts/autobuy/runner.py` — 장중 루프 조립 + 안전·상태·로깅.
- `scripts/autobuy/config.py` — 설정 상수(수량 제외).

---

### Task 1: 순수 판정 — `evaluate_entry` (TDD)

**Files:**
- Create: `scripts/autobuy/__init__.py`(빈 파일), `scripts/autobuy/signals.py`
- Test: `tests/test_autobuy_signals.py`

**Interfaces:**
- Produces: `evaluate_entry(price, pivot, acml_vol, avg50_vol, elapsed_frac, *, slots_used, slots_max, held, vol_pace_min=1.5, chase_max_pct=3.0) -> tuple[bool, str]` — 매수 여부와 사유.

- [ ] **Step 1: Write the failing tests**

`tests/test_autobuy_signals.py`:
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.signals import evaluate_entry

BASE = dict(price=1030.0, pivot=1000.0, acml_vol=300_000, avg50_vol=1_000_000,
            elapsed_frac=0.2, slots_used=0, slots_max=10, held=False)

def ev(**kw):
    return evaluate_entry(**{**BASE, **kw})

def test_all_conditions_met_buys():
    # pace = 300000/(1000000*0.2)=1.5 (>=1.5), price 1030<=1030(+3%) → buy
    assert ev() == (True, "buy")

def test_below_pivot_skips():
    assert ev(price=990.0)[0] is False and ev(price=990.0)[1] == "below_pivot"

def test_extended_over_3pct_skips():
    assert ev(price=1031.0) == (False, "extended")   # +3.1%
    assert ev(price=1030.0)[0] is True               # 정확히 +3.0% 는 허용

def test_low_volume_skips():
    assert ev(acml_vol=100_000) == (False, "low_volume")  # pace 0.5

def test_no_slot_skips():
    assert ev(slots_used=10) == (False, "no_slot")

def test_already_held_skips():
    assert ev(held=True) == (False, "already_held")

def test_zero_baseline_skips():
    assert ev(avg50_vol=0) == (False, "no_baseline")
    assert ev(elapsed_frac=0) == (False, "no_baseline")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -X utf8 -m pytest tests/test_autobuy_signals.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'autobuy'`.

- [ ] **Step 3: Implement**

`scripts/autobuy/__init__.py`: 빈 파일.
`scripts/autobuy/signals.py`:
```python
"""자동매수 봇 순수 판정 함수 — 실시간 시세/거래량으로 매수·청산·국면을 판정.
부작용 없음(주문·네트워크 없음) → 합성 입력으로 전수 테스트 가능."""
from __future__ import annotations


def evaluate_entry(price, pivot, acml_vol, avg50_vol, elapsed_frac, *,
                   slots_used, slots_max, held,
                   vol_pace_min=1.5, chase_max_pct=3.0):
    """돌파+거래량pace+추격상한(하드)+슬롯+미보유 전부 충족 시 (True,"buy").
    반환: (매수여부, 사유). 사유: buy|already_held|no_slot|below_pivot|extended|no_baseline|low_volume."""
    if held:
        return (False, "already_held")
    if slots_used >= slots_max:
        return (False, "no_slot")
    if price < pivot:
        return (False, "below_pivot")
    if price > pivot * (1 + chase_max_pct / 100):
        return (False, "extended")            # 추격 금지 — 하드 상한
    if avg50_vol <= 0 or elapsed_frac <= 0:
        return (False, "no_baseline")
    vol_pace = acml_vol / (avg50_vol * elapsed_frac)
    if vol_pace < vol_pace_min:
        return (False, "low_volume")
    return (True, "buy")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -X utf8 -m pytest tests/test_autobuy_signals.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/autobuy/__init__.py scripts/autobuy/signals.py tests/test_autobuy_signals.py
git commit -m "feat(autobuy): evaluate_entry 순수 판정(TDD)"
```

---

### Task 2: 순수 판정 — `evaluate_exit` (TDD)

**Files:**
- Modify: `scripts/autobuy/signals.py`
- Test: `tests/test_autobuy_signals.py`

**Interfaces:**
- Produces: `evaluate_exit(price, entry_price, *, target_pct=20.0, stop_pct=10.0) -> tuple[bool, str]` — 청산 여부와 사유(stop|target|hold).

- [ ] **Step 1: Write the failing tests** (같은 테스트 파일에 추가)

```python
from autobuy.signals import evaluate_exit

def test_exit_stop():
    assert evaluate_exit(900.0, 1000.0) == (True, "stop")     # -10%
    assert evaluate_exit(901.0, 1000.0) == (False, "hold")    # -9.9%

def test_exit_target():
    assert evaluate_exit(1200.0, 1000.0) == (True, "target")  # +20%
    assert evaluate_exit(1199.0, 1000.0) == (False, "hold")

def test_exit_hold_between():
    assert evaluate_exit(1050.0, 1000.0) == (False, "hold")
```

- [ ] **Step 2: Run to verify fail**

Run: `python -X utf8 -m pytest tests/test_autobuy_signals.py -k exit -v`
Expected: FAIL — `cannot import name 'evaluate_exit'`.

- [ ] **Step 3: Implement** — `signals.py` 에 추가:
```python
def evaluate_exit(price, entry_price, *, target_pct=20.0, stop_pct=10.0):
    """진입가 대비 -stop% 손절 / +target% 목표 선착. 반환 (매도여부, stop|target|hold).
    손절 우선(같은 틱에 둘 다면 손절)."""
    if price <= entry_price * (1 - stop_pct / 100):
        return (True, "stop")
    if price >= entry_price * (1 + target_pct / 100):
        return (True, "target")
    return (False, "hold")
```

- [ ] **Step 4: Run all signal tests**

Run: `python -X utf8 -m pytest tests/test_autobuy_signals.py -v`
Expected: 전부 pass(Task1 7 + Task2 3).

- [ ] **Step 5: Commit**
```bash
git add scripts/autobuy/signals.py tests/test_autobuy_signals.py
git commit -m "feat(autobuy): evaluate_exit 순수 판정(TDD)"
```

---

### Task 3: 국면 게이트 `is_uptrend` + 후보 로더 (TDD)

**Files:**
- Modify: `scripts/autobuy/signals.py` (`is_uptrend`)
- Create: `scripts/autobuy/watchlist.py` (`load_actionable`, `build_ew_index`)
- Test: `tests/test_autobuy_signals.py`, `tests/test_autobuy_watchlist.py`

**Interfaces:**
- Produces: `is_uptrend(closes, ma=20) -> bool` (순수). `load_actionable(paths) -> list[dict]` (code·name·pivot·pattern, code 중복제거). `build_ew_index(get_series, codes) -> list[float]` (등가중 지수 종가열, 국면판정 입력).

- [ ] **Step 1: Write failing tests**

`tests/test_autobuy_signals.py` 에 추가:
```python
from autobuy.signals import is_uptrend

def test_is_uptrend():
    assert is_uptrend([1,2,3,4,5,6,7,8,9,10]*3, ma=20) is True     # 우상향
    assert is_uptrend(list(range(30,0,-1)), ma=20) is False        # 우하향
    assert is_uptrend([100]*10, ma=20) is False                    # 데이터<ma → 판단불가=False(보수)
```

`tests/test_autobuy_watchlist.py`:
```python
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.watchlist import load_actionable, build_ew_index

def test_load_actionable(tmp_path):
    f = tmp_path / "sepa-vcp-candidates.json"
    f.write_text(json.dumps({"candidates": [
        {"code": "005930", "name": "삼성전자", "status": "actionable", "pivot_price": 70000.0},
        {"code": "000660", "name": "SK", "status": "forming", "pivot_price": 50000.0},   # 제외
        {"code": "005930", "name": "삼성전자", "status": "actionable", "pivot_price": 70000.0},  # 중복
    ]}, ensure_ascii=False), encoding="utf-8")
    out = load_actionable([str(f)])
    assert len(out) == 1 and out[0]["code"] == "005930" and out[0]["pivot"] == 70000.0

def test_build_ew_index():
    # 두 종목 상승 → 지수 상승
    series = {"A": {"dates": ["d1","d2","d3"], "closes": [100,110,121]},
              "B": {"dates": ["d1","d2","d3"], "closes": [50,55,60.5]}}
    idx = build_ew_index(lambda c: series.get(c), ["A","B"])
    assert len(idx) == 3 and idx[-1] > idx[0]
```

- [ ] **Step 2: Run to verify fail**

Run: `python -X utf8 -m pytest tests/test_autobuy_watchlist.py tests/test_autobuy_signals.py -k "uptrend or actionable or ew_index" -v`
Expected: FAIL(import/name 없음).

- [ ] **Step 3: Implement**

`signals.py` 에 추가:
```python
def is_uptrend(closes, ma=20):
    """지수 종가열 최신값이 ma일 이동평균 위면 상승추세(=매매 ON). 데이터 부족 시 False(보수)."""
    if len(closes) < ma:
        return False
    return closes[-1] > sum(closes[-ma:]) / ma
```

`scripts/autobuy/watchlist.py`:
```python
"""오늘 감시할 진입임박 후보 로드 + 국면지수(등가중) 구성."""
from __future__ import annotations
import json


def load_actionable(paths):
    """sepa-*-candidates.json 들에서 status=='actionable' & pivot 있는 것 로드.
    code 중복 제거(첫 등장 유지). 반환 [{code,name,pivot,pattern}]."""
    seen, out = set(), []
    for p in paths:
        try:
            d = json.loads(open(p, encoding="utf-8").read())
        except Exception:
            continue
        pat = "VCP" if "vcp" in p else "3C" if "3c" in p else "PP" if "power" in p else "?"
        for c in d.get("candidates", []):
            if c.get("status") == "actionable" and c.get("pivot_price") and c["code"] not in seen:
                seen.add(c["code"])
                out.append({"code": c["code"], "name": c.get("name"),
                            "pivot": float(c["pivot_price"]), "pattern": pat})
    return out


def build_ew_index(get_series, codes):
    """등가중 시장지수 종가열 — 각 날짜 평균 일간수익을 누적. get_series(code)->{dates,closes}."""
    from collections import defaultdict
    rs, rc = defaultdict(float), defaultdict(int)
    for code in codes:
        s = get_series(code)
        if not s:
            continue
        ds, cl = s.get("dates") or [], s.get("closes") or []
        for i in range(1, len(cl)):
            if cl[i] and cl[i - 1] and 0.5 < cl[i] / cl[i - 1] < 1.5:
                rs[ds[i]] += cl[i] / cl[i - 1] - 1
                rc[ds[i]] += 1
    lvl, out = 1.0, []
    for dt in sorted(rs):
        lvl *= (1 + rs[dt] / rc[dt])
        out.append(lvl)
    return out
```

- [ ] **Step 4: Run tests**

Run: `python -X utf8 -m pytest tests/test_autobuy_signals.py tests/test_autobuy_watchlist.py -v`
Expected: 전부 pass.

- [ ] **Step 5: Commit**
```bash
git add scripts/autobuy/signals.py scripts/autobuy/watchlist.py tests/test_autobuy_watchlist.py tests/test_autobuy_signals.py
git commit -m "feat(autobuy): is_uptrend 국면판정 + 후보 로더/등가중지수(TDD)"
```

---

### Task 4: KIS 거래량 포함 현재가 조회 (기존 kis_api 확장)

**Files:**
- Modify: `scripts/canslim_lib/kis_api.py` (신규 함수 추가, 기존 함수 무수정)
- Test: 실 KIS 스모크(단위테스트 아님 — 네트워크 의존)

**Interfaces:**
- Produces: `fetch_quote_with_volume(code, token=None) -> dict|None` — `{"current": float, "acml_vol": float}` (inquire-price FHKST01010100 의 stck_prpr·acml_vol). 실패 시 None.

- [ ] **Step 1: Implement** — `kis_api.py` 에 `fetch_integrated_price` 아래 추가(같은 요청 패턴·`_throttle`·헤더 재사용):
```python
def fetch_quote_with_volume(code: str, token: str | None = None) -> dict | None:
    """현재가 + 당일 누적거래량 — inquire-price(FHKST01010100) output 의 stck_prpr·acml_vol.
    자동매수 봇의 거래량 pace 계산용."""
    if token is None:
        token = get_access_token()
    if not token:
        return None
    qs = _urlparse.urlencode({"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code})
    url = f"{_base_url()}/uapi/domestic-stock/v1/quotations/inquire-price?{qs}"
    headers = {"content-type": "application/json", "authorization": f"Bearer {token}",
               "appkey": os.environ.get("KIS_APP_KEY", ""), "appsecret": os.environ.get("KIS_APP_SECRET", ""),
               "tr_id": "FHKST01010100", "custtype": "P"}
    for attempt in range(3):
        _throttle()
        try:
            with _urlreq.urlopen(_urlreq.Request(url, headers=headers), timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            time.sleep(0.3 * (attempt + 1)); continue
        if data.get("rt_cd") == "0":
            o = data.get("output") or {}
            try:
                return {"current": float(o["stck_prpr"]), "acml_vol": float(o["acml_vol"])}
            except (KeyError, ValueError, TypeError):
                return None
        if data.get("msg_cd") == "EGW00201":
            time.sleep(1.0); continue
        return None
    return None
```

- [ ] **Step 2: 스모크(실 KIS, 안전한 읽기)**

`.env` 로드 후:
Run:
```bash
python -X utf8 -c "import os,sys; sys.path.insert(0,'scripts'); [os.environ.setdefault(*l.strip().split('=',1)) for l in open('.env',encoding='utf-8') if '=' in l and not l.startswith('#')]; from canslim_lib import kis_api as k; print(k.fetch_quote_with_volume('005930'))"
```
Expected: `{'current': <삼성전자 현재가>, 'acml_vol': <당일 누적거래량>}` (장중이면 실시간, 장마감 후면 종가/당일 최종). None 이면 인증/TR 점검.

- [ ] **Step 3: Commit**
```bash
git add scripts/canslim_lib/kis_api.py
git commit -m "feat(autobuy): kis_api.fetch_quote_with_volume(현재가+누적거래량)"
```

---

### Task 5: KIS 주문/잔고 모듈 — 1주 하드코딩·dryrun (안전 최우선)

**Files:**
- Create: `scripts/autobuy/kis_trade.py`
- Test: dryrun 단위테스트 + (사용자 게이트) 실계좌 1주 스모크

**Interfaces:**
- Consumes: `kis_api.get_access_token`, `_base_url`, `_throttle`.
- Produces: `place_buy_1share(code, mode="dryrun") -> dict`, `place_sell_1share(code, mode="dryrun") -> dict`, `inquire_holdings() -> list[dict]`(보유 [{code, qty, avg_price}]).

**주의(구현자):** 실전 주문 TR·파라미터는 **KIS Developers 문서와 `github.com/koreainvestment/open-trading-api` 예제로 정확 확인**할 것. 아래는 알려진 구조(현금매수 `TTTC0802U`·매도 `TTTC0801U`·잔고 `TTTC8434R`·해시키 `/uapi/hashkey`, 실전 도메인). **수량은 함수 내부 `"1"` 하드코딩 — 인자로 받지 않는다.**

- [ ] **Step 1: dryrun 단위테스트**

`tests/test_autobuy_kis_trade.py`:
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy import kis_trade

def test_dryrun_buy_no_network():
    r = kis_trade.place_buy_1share("005930", mode="dryrun")
    assert r["mode"] == "dryrun" and r["code"] == "005930" and r["qty"] == 1 and r["ok"] is True

def test_dryrun_sell_no_network():
    r = kis_trade.place_sell_1share("005930", mode="dryrun")
    assert r["mode"] == "dryrun" and r["qty"] == 1 and r["ok"] is True
```

- [ ] **Step 2: Run to verify fail** — `python -X utf8 -m pytest tests/test_autobuy_kis_trade.py -v` → FAIL(모듈 없음).

- [ ] **Step 3: Implement** `scripts/autobuy/kis_trade.py`:
```python
"""KIS 국내주식 주문/잔고 — 자동매수 봇 전용. 안전 최우선.
수량은 항상 1주(하드코딩). dryrun 모드는 실주문 없이 로그용 dict 반환."""
from __future__ import annotations
import json, os, urllib.request as _u
from canslim_lib import kis_api

ORD_QTY = "1"   # ★ 절대 변경/매개변수화 금지 — 1주 상한

def _order(code: str, side: str, mode: str) -> dict:
    base = {"code": code, "side": side, "qty": 1, "mode": mode}
    if mode != "live":
        return {**base, "ok": True, "note": "dryrun(주문 안 냄)"}
    token = kis_api.get_access_token()
    if not token:
        return {**base, "ok": False, "error": "no_token"}
    tr = "TTTC0802U" if side == "buy" else "TTTC0801U"   # 구현자: KIS 문서로 확인
    body = {"CANO": os.environ["KIS_ACCOUNT"], "ACNT_PRDT_CD": os.environ.get("KIS_ACNT_PRDT", "01"),
            "PDNO": code, "ORD_DVSN": "01", "ORD_QTY": ORD_QTY, "ORD_UNPR": "0"}  # 01=시장가
    payload = json.dumps(body)
    url = f"{kis_api._base_url()}/uapi/domestic-stock/v1/trading/order-cash"
    headers = {"content-type": "application/json", "authorization": f"Bearer {token}",
               "appkey": os.environ["KIS_APP_KEY"], "appsecret": os.environ["KIS_APP_SECRET"],
               "tr_id": tr, "custtype": "P", "hashkey": _hashkey(payload)}
    kis_api._throttle()
    try:
        with _u.urlopen(_u.Request(url, data=payload.encode(), headers=headers), timeout=8) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {**base, "ok": d.get("rt_cd") == "0", "resp": d}
    except Exception as e:
        return {**base, "ok": False, "error": f"{type(e).__name__}"}

def _hashkey(payload: str) -> str:
    url = f"{kis_api._base_url()}/uapi/hashkey"
    headers = {"content-type": "application/json", "appkey": os.environ["KIS_APP_KEY"],
               "appsecret": os.environ["KIS_APP_SECRET"]}
    with _u.urlopen(_u.Request(url, data=payload.encode(), headers=headers), timeout=8) as r:
        return json.loads(r.read().decode("utf-8")).get("HASH", "")

def place_buy_1share(code: str, mode: str = "dryrun") -> dict:
    return _order(code, "buy", mode)

def place_sell_1share(code: str, mode: str = "dryrun") -> dict:
    return _order(code, "sell", mode)

def inquire_holdings() -> list[dict]:
    """보유 종목 [{code, qty, avg_price}]. 실패 시 빈 리스트. (TR TTTC8434R — 구현자 확인)"""
    token = kis_api.get_access_token()
    if not token:
        return []
    # ... KIS 잔고조회 TTTC8434R GET 구현(문서 확인). output1 파싱 → code(pdno)/qty(hldg_qty)/avg(pchs_avg_pric).
    # 실패·빈 응답 → [] 반환.
    return _inquire_holdings_impl(token)
```
(구현자: `_inquire_holdings_impl`은 KIS 잔고 TR 문서대로 GET 구현. output1 을 `[{"code":r["pdno"],"qty":int(r["hldg_qty"]),"avg_price":float(r["pchs_avg_pric"])} for r in ...]` 로 매핑, 예외 시 [].)

- [ ] **Step 4: dryrun 테스트 통과 확인**

Run: `python -X utf8 -m pytest tests/test_autobuy_kis_trade.py -v`
Expected: 2 passed (네트워크 없이).

- [ ] **Step 5: Commit (dryrun까지만)**
```bash
git add scripts/autobuy/kis_trade.py tests/test_autobuy_kis_trade.py
git commit -m "feat(autobuy): KIS 주문/잔고 모듈 — 1주 하드코딩·dryrun"
```

> ⚠️ **실계좌 1주 스모크(live)는 이 태스크에서 자동 실행하지 않는다.** `KIS_ACCOUNT` 등 실계좌 설정과 사용자의 명시적 승인 후, 사용자가 직접 유동성 큰 소액주 1주 매수→즉시 매도로 주문경로를 검증한다.

---

### Task 6: 설정·안전·상태 (config + safety + state)

**Files:**
- Create: `scripts/autobuy/config.py`, `scripts/autobuy/state.py`
- Test: `tests/test_autobuy_state.py`

**Interfaces:**
- Produces: `config.CFG`(SLOTS·VOL_PACE_MIN·CHASE_MAX_PCT·TARGET_PCT·STOP_PCT·POLL_SEC·REGIME_FILTER·MODE — **수량 없음**). `state.load()/save(positions)`·`state.kill_switch_on()`·`state.log(event)`.

- [ ] **Step 1: state 테스트**

`tests/test_autobuy_state.py`:
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy import state

def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_PATH", tmp_path / "positions.json")
    state.save([{"code": "005930", "entry_price": 70000.0}])
    assert state.load()[0]["code"] == "005930"

def test_kill_switch(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "KILL_PATH", tmp_path / "KILL")
    assert state.kill_switch_on() is False
    (tmp_path / "KILL").write_text("stop")
    assert state.kill_switch_on() is True
```

- [ ] **Step 2: Run to verify fail** → 모듈 없음.

- [ ] **Step 3: Implement**

`scripts/autobuy/config.py`:
```python
"""자동매수 봇 설정. 주문 수량은 여기에 없다(항상 1주, kis_trade에 하드코딩)."""
from pathlib import Path
BASE = Path(r"C:\Users\hanul\playground\my-stock")   # 후보 JSON·캐시가 있는 주 작업트리
CFG = {
    "SLOTS": 10,            # 동시 보유 상한(10~20)
    "VOL_PACE_MIN": 1.5,
    "CHASE_MAX_PCT": 3.0,  # 하드
    "TARGET_PCT": 20.0, "STOP_PCT": 10.0,
    "POLL_SEC": 4,
    "REGIME_FILTER": True,
    "MODE": "dryrun",      # dryrun | live — live 전환은 실행인자로도 재확인
    "MARKET_OPEN": "0905", "NEW_BUY_UNTIL": "1520", "MARKET_CLOSE": "1530",
}
CANDIDATE_PATHS = [str(BASE / "public" / "data" / f"sepa-{p}-candidates.json")
                   for p in ("vcp", "3c", "power-play")]
```

`scripts/autobuy/state.py`:
```python
"""봇 상태(보유 포지션)·킬스위치·로그. 파일 기반."""
from __future__ import annotations
import json, datetime
from pathlib import Path
_DIR = Path(__file__).resolve().parent / "_run"
_DIR.mkdir(exist_ok=True)
STATE_PATH = _DIR / "positions.json"
KILL_PATH = _DIR / "KILL"
LOG_PATH = _DIR / "autobuy.log"

def load() -> list[dict]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def save(positions: list[dict]) -> None:
    STATE_PATH.write_text(json.dumps(positions, ensure_ascii=False), encoding="utf-8")

def kill_switch_on() -> bool:
    return KILL_PATH.exists()

def log(event: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"{ts} {event}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
```

- [ ] **Step 4: Run tests** → pass.
- [ ] **Step 5: Commit**
```bash
git add scripts/autobuy/config.py scripts/autobuy/state.py tests/test_autobuy_state.py
git commit -m "feat(autobuy): config(수량 제외)·state(보유·킬스위치·로그)"
```

---

### Task 7: 러너 조립 + dryrun 통합 실행

**Files:**
- Create: `scripts/autobuy/runner.py`
- Test: dryrun 통합 실행(로그 육안) — 순수 로직은 Task1~3에서 검증됨

**Interfaces:**
- Consumes: 전 태스크 전부.

- [ ] **Step 1: Implement `scripts/autobuy/runner.py`**
```python
"""장중 자동매수 봇 러너 — 조립만. 판정은 signals, 주문은 kis_trade, 상태는 state.
실행: python -X utf8 scripts/autobuy/runner.py            # dryrun(기본)
      python -X utf8 scripts/autobuy/runner.py --live      # 실주문(명시)
"""
from __future__ import annotations
import argparse, os, sys, time, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # scripts/
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from autobuy.config import CFG, CANDIDATE_PATHS, BASE
from autobuy import signals, state, kis_trade, watchlist
sys.path.insert(0, str(BASE / "scripts"))
from canslim_lib import ohlcv_matrix, kis_api
ohlcv_matrix.SERIES_DIR = BASE / ".cache" / "ohlcv" / "series"
# .env 로드(주 작업트리)
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k, v)


def _elapsed_frac(now: datetime.datetime) -> float:
    op = now.replace(hour=9, minute=0, second=0, microsecond=0)
    total = 6.5 * 3600
    return max(1e-6, min(1.0, (now - op).total_seconds() / total))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="실주문(미지정 시 dryrun)")
    mode = "live" if ap.parse_args().live else CFG["MODE"]
    state.log(f"=== 자동매수 봇 시작 mode={mode} slots={CFG['SLOTS']} ===")

    # 국면 게이트
    codes_all = [p.stem for p in (BASE / ".cache" / "ohlcv" / "series").glob("*.json")]
    if CFG["REGIME_FILTER"]:
        idx = watchlist.build_ew_index(ohlcv_matrix.get_series, codes_all)
        if not signals.is_uptrend(idx, 20):
            state.log("국면=하락추세(지수<20MA) → 오늘 매매 OFF. 종료."); return
        state.log("국면=상승추세 → 가동")

    wl = watchlist.load_actionable(CANDIDATE_PATHS)
    avg50 = {}
    for c in wl:
        s = ohlcv_matrix.get_series(c["code"])
        vols = [v for v in (s.get("volumes") or [])[-50:] if v] if s else []
        avg50[c["code"]] = (sum(vols) / len(vols)) if vols else 0
    state.log(f"감시목록 {len(wl)}종목")

    positions = {p["code"]: p for p in state.load()}
    skip = set()   # 추격 초과 등 그날 영구 스킵
    while True:
        if state.kill_switch_on():
            state.log("KILL 스위치 감지 → 신규매수 중단"); break
        now = datetime.datetime.now(); hm = now.strftime("%H%M")
        if hm >= CFG["MARKET_CLOSE"]:
            state.log("장마감 → 종료"); break
        ef = _elapsed_frac(now)
        # 청산 감시(보유)
        for code, pos in list(positions.items()):
            q = kis_api.fetch_quote_with_volume(code)
            if not q: continue
            sell, why = signals.evaluate_exit(q["current"], pos["entry_price"],
                                              target_pct=CFG["TARGET_PCT"], stop_pct=CFG["STOP_PCT"])
            if sell:
                r = kis_trade.place_sell_1share(code, mode=mode)
                state.log(f"매도 {code} {why} @{q['current']} → {r.get('ok')}")
                positions.pop(code, None); state.save(list(positions.values()))
        # 신규 매수(신호 초과 시 pace 높은 순)
        if hm < CFG["NEW_BUY_UNTIL"] and hm >= CFG["MARKET_OPEN"]:
            cands = []
            for c in wl:
                if c["code"] in positions or c["code"] in skip: continue
                q = kis_api.fetch_quote_with_volume(c["code"])
                if not q: continue
                ok, why = signals.evaluate_entry(
                    q["current"], c["pivot"], q["acml_vol"], avg50[c["code"]], ef,
                    slots_used=len(positions), slots_max=CFG["SLOTS"], held=False,
                    vol_pace_min=CFG["VOL_PACE_MIN"], chase_max_pct=CFG["CHASE_MAX_PCT"])
                if why == "extended": skip.add(c["code"])
                if ok:
                    pace = q["acml_vol"] / (avg50[c["code"]] * ef)
                    cands.append((pace, c, q))
            for pace, c, q in sorted(cands, key=lambda x: -x[0]):
                if len(positions) >= CFG["SLOTS"]: break
                r = kis_trade.place_buy_1share(c["code"], mode=mode)
                if r.get("ok"):
                    positions[c["code"]] = {"code": c["code"], "entry_price": q["current"]}
                    state.save(list(positions.values()))
                    state.log(f"매수 {c['code']} {c['name']} @{q['current']} pace{pace:.1f} → {mode}")
        time.sleep(CFG["POLL_SEC"])
    state.log("=== 종료 ===")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: dryrun 통합 실행(로그 육안, 실주문 없음)**

Run(장중이 아니어도 국면·감시목록·판정 흐름 확인 가능; 장마감 후면 즉시 "장마감→종료"):
```bash
python -X utf8 scripts/autobuy/runner.py
```
Expected: 로그에 `mode=dryrun`·국면 판정·감시목록 N종목 출력. 매수 로그가 뜨면 `→ dryrun`(실주문 아님). 에러 없이 종료.

- [ ] **Step 3: 전체 테스트 재확인**

Run: `python -X utf8 -m pytest tests/test_autobuy_*.py -v`
Expected: 전부 pass.

- [ ] **Step 4: Commit**
```bash
git add scripts/autobuy/runner.py
git commit -m "feat(autobuy): 러너 조립 + dryrun 통합"
```

---

## Self-Review

**1. Spec coverage**
- 자동매수 1주(조건 충족) → Task1(entry_signal)·Task5(1주 주문)·Task7(러너). ✅
- 청산 −10%/+20% 봇 감시 → Task2(exit)·Task7. ✅
- 추격 하드 +3% → Task1(extended)·Global. ✅ · 거래량 pace≥1.5 → Task1. ✅
- 국면 게이트(지수>20MA) → Task3(is_uptrend·build_ew_index)·Task7. ✅
- 후보 로더(actionable·pivot) → Task3. ✅
- 1주 하드코딩(수량 인자·설정 없음) → Task5(ORD_QTY)·Task6(config에 수량 없음)·Global. ✅
- 안전: dryrun 기본·킬스위치·상한·로깅 → Task5(dryrun)·Task6(state)·Task7(kill/시간가드/slots). ✅
- 실계좌 1주 스모크는 사용자 게이트(자동실행 X) → Task5 말미 명시. ✅

**2. Placeholder scan** — 순수 로직(1~3)·config·state·러너는 완전한 코드. KIS 주문 TR·잔고파싱(Task5)은 "KIS 문서 확인" 통합지시(외부 API 파라미터라 불가피) — 구조·수량하드코딩·dryrun은 완비. 이는 placeholder가 아니라 integration 검증 단계.

**3. Type consistency**
- `evaluate_entry(...) -> (bool,str)` Task1 정의 ↔ Task7 소비 일치(why=="extended" 스킵, ok시 매수). ✅
- `evaluate_exit(price,entry_price) -> (bool,str)` Task2 ↔ Task7. ✅
- `fetch_quote_with_volume -> {current,acml_vol}` Task4 ↔ Task7(q["current"]·q["acml_vol"]). ✅
- `load_actionable -> [{code,name,pivot,pattern}]` Task3 ↔ Task7(c["code"]·c["pivot"]·c["name"]). ✅
- `place_buy/sell_1share(code,mode) -> {ok,...}` Task5 ↔ Task7(r.get("ok")). ✅
- `build_ew_index(get_series,codes) -> [float]` Task3 ↔ Task7(is_uptrend 입력). ✅

> 통합 위험(실행서 확인): KIS 주문 TR/파라미터 정확성(Task5 스모크는 사용자 게이트), 장중이 아니면 매수경로 미발화(장중 dryrun으로 최종 확인 필요).

---

## Execution Handoff

순서: Task1(entry)→2(exit)→3(국면·로더) 순수/TDD 먼저. 4(시세)→5(주문,dryrun)→6(설정·상태)→7(러너) 통합. 실계좌 live는 dryrun 충분 검증 후 사용자 승인으로만.
