# VCP 검출기 재설계 (evaluate_vcp in-place) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `evaluate_vcp`(scripts/canslim_lib/vcp.py)의 베이스·피벗·수축·거래량·돌파 로직을 직접 교체해 진짜 미너비니 VCP(정답 예시 5건)를 인식·돌파 포착하게 만든다.

**Architecture:** 새 순수 부품(`volume_ma`, `adaptive_zigzag`, `find_contraction_chain`, `_is_breakout`)을 vcp.py에 추가하고 `evaluate_vcp`가 이들로 재작성된다(반환 키 불변). 적응형 ZigZag로 타이트 수축을 잡고, 피벗=마지막 수축 고점(최소저항선), 거래량은 50일선 기준(우측 마름 하드게이트), 돌파=첫돌파+양봉+거래량터짐+피벗근접. 임계값은 6예시·70종목으로 보정.

**Tech Stack:** Python 3.11+, pytest 9.x. 검증=FDR(예시 과거 일봉)+캐시(70종목).

**Spec:** `docs/superpowers/specs/2026-06-30-vcp-detector-v2-design.md`

## Global Constraints

- **반환 키 불변**: vcp_detected, num_contractions, contractions, base_length_days, base_depth_pct, pivot_price, pct_to_pivot, volume_dryup_ratio, tightness_pct, status, swings, reason, entry_ready — 제거·이름변경 금지(find-vcp/find-vcp-history/vcp-audit가 그대로 읽음).
- **파라미터**: 기존 `breakout_vol_mult`(1.4)·`near_pivot_pct`(5.0)·`contraction_tol`(1.15)·`lookback_days`(120)·`min_base_days`(10) 재사용. 신규 키 **`zigzag_k`(기본 4.0)·`dry_max`(기본 0.7)** 만 추가. 기존 키 `zigzag_pct`·`max_final_depth`·`base_vol_cap`는 DEFAULT_PARAMS에 남겨두되 미사용(callers 안 깨지게).
- **피벗 = 최소저항선** = 마지막(최신·가장 타이트) 수축의 고점.
- **적응형 수축 임계 하한 없음** — 베이스 변동성에 비례. "2~6회·수렴"이 잡음 필터.
- **거래량 50일선 기준**: 우측 마름(≤dry_max) = 하드게이트. 수축별 감소는 소프트(게이트 아님).
- **돌파 거래량 터짐 필수**(50선×breakout_vol_mult). 조용한 돌파(메리츠) 미발화 수용.
- **성공선**: 메리츠 뺀 5예시(194480·014680·030210×2·220260) 인식+돌파 + 70종목 회귀 가드.
- 검출기 직접 수정이라 v1 무수정 원칙 없음. 단 머지 전 검증 통과 필수.

---

### Task 1: vcp.py — volume_ma + adaptive_zigzag

**Files:**
- Modify: `scripts/canslim_lib/vcp.py` (DEFAULT_PARAMS에 zigzag_k·dry_max 추가; 함수 추가)
- Test: `tests/test_vcp.py`

**Interfaces:**
- Produces: `volume_ma(volumes: list[float], window: int = 50) -> list[float]` (trailing MA, 부분창 허용).
- Produces: `adaptive_zigzag(values: list[float], k: float = 4.0) -> list[tuple[int,float,str]]` — 베이스 변동성에 비례한 임계로 기존 `zigzag` 호출.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp.py 에 추가
from canslim_lib.vcp import volume_ma, adaptive_zigzag, zigzag


def test_volume_ma_trailing():
    assert volume_ma([10, 20, 30, 40, 50], window=3) == [10, 15, 20, 30, 40]


def test_adaptive_zigzag_catches_tight_swings_that_fixed8_misses():
    # 타이트 시계열(스윙 ~4%): 고정 8%는 수축을 못 잡고, 적응형은 잡는다
    closes = [100, 104, 100, 96, 100, 104, 100, 96, 100, 104]
    fixed = [k for _, _, k in zigzag(closes, 8.0)]
    adapt = [k for _, _, k in adaptive_zigzag(closes, k=2.0)]
    # 고정 8%는 교대 스윙이 거의 없음(시작/끝 정도), 적응형은 더 많은 교대 스윙
    assert adapt.count("high") + adapt.count("low") > fixed.count("high") + fixed.count("low")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp.py -k "volume_ma or adaptive" -v`
Expected: FAIL — `ImportError: cannot import name 'volume_ma'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp.py — DEFAULT_PARAMS에 두 키 추가
#     "zigzag_k": 4.0,
#     "dry_max": 0.7,
# (기존 키는 그대로 둠)

# 함수 추가 (zigzag 정의 아래)
def volume_ma(volumes: list[float], window: int = 50) -> list[float]:
    out: list[float] = []
    for i in range(len(volumes)):
        seg = volumes[max(0, i - window + 1):i + 1]
        out.append(sum(seg) / len(seg) if seg else 0.0)
    return out


def adaptive_zigzag(values: list[float], k: float = 4.0) -> list[tuple[int, float, str]]:
    """베이스 변동성(평균 일간 절대등락%)에 비례한 임계로 zigzag 실행. 하한 없음."""
    n = len(values)
    if n < 2:
        return zigzag(values, 8.0)
    rets = [abs(values[i] / values[i - 1] - 1) * 100.0 for i in range(1, n) if values[i - 1]]
    vol = (sum(rets) / len(rets)) if rets else 0.0
    thr = k * vol if vol > 0 else 8.0
    return zigzag(values, thr)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp.py -k "volume_ma or adaptive" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp.py tests/test_vcp.py
git commit -m "feat(vcp): volume_ma + adaptive_zigzag (적응형 수축 임계)"
```

---

### Task 2: vcp.py — find_contraction_chain (베이스·피벗=최소저항선)

**Files:**
- Modify: `scripts/canslim_lib/vcp.py`
- Test: `tests/test_vcp.py`

**Interfaces:**
- Consumes: swings(=adaptive_zigzag 결과).
- Produces: `find_contraction_chain(swings, tol: float = 1.15) -> dict | None` —
  `{"base_start": int, "pivot": float, "depths": list[float], "count": int}` 또는 수축 쌍 없으면 None.
  base_start = 끝쪽 *수렴하는 수축 연쇄*의 첫 수축 고점 인덱스. pivot = 그 연쇄 마지막 수축의 고점(최소저항선).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp.py 에 추가
from canslim_lib.vcp import find_contraction_chain


def test_find_contraction_chain_pivot_is_last_high_and_shrinks():
    # 수축 깊이 25% → 13% → 7% (수렴), 마지막 수축 고점=피벗
    swings = [
        (0, 100.0, "high"), (5, 75.0, "low"),
        (10, 90.0, "high"), (15, 78.3, "low"),
        (20, 88.0, "high"), (25, 81.8, "low"),
    ]
    r = find_contraction_chain(swings, tol=1.15)
    assert r["count"] == 3
    assert r["base_start"] == 0          # 첫 수축 고점 인덱스
    assert r["pivot"] == 88.0            # 마지막 수축 고점 = 최소저항선
    assert r["depths"][0] > r["depths"][-1]


def test_find_contraction_chain_none_without_pairs():
    assert find_contraction_chain([(0, 100.0, "high")], tol=1.15) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp.py -k contraction_chain -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp.py 에 추가
def find_contraction_chain(swings: list[tuple[int, float, str]], tol: float = 1.15) -> dict | None:
    """끝쪽의 수렴하는 (고→저) 수축 연쇄. base_start=첫 수축 고점, pivot=마지막 수축 고점."""
    pairs = []  # (hi_idx, hi_price, lo_idx, lo_price, depth%)
    for a, b in zip(swings, swings[1:]):
        if a[2] == "high" and b[2] == "low" and a[1] > 0:
            pairs.append((a[0], a[1], b[0], b[1], (a[1] - b[1]) / a[1] * 100.0))
    if not pairs:
        return None
    chain = [pairs[-1]]
    for prev in reversed(pairs[:-1]):
        # 시간순으로 깊이가 얕아지는(수렴) 동안만 연쇄에 포함: later <= prev*tol
        if chain[0][4] <= prev[4] * tol:
            chain.insert(0, prev)
        else:
            break
    return {
        "base_start": chain[0][0],
        "pivot": round(chain[-1][1], 2),
        "depths": [round(c[4], 2) for c in chain],
        "count": len(chain),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp.py -k contraction_chain -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp.py tests/test_vcp.py
git commit -m "feat(vcp): find_contraction_chain (베이스·피벗=최소저항선)"
```

---

### Task 3: vcp.py — _is_breakout (첫돌파+양봉+거래량터짐+근접)

**Files:**
- Modify: `scripts/canslim_lib/vcp.py`
- Test: `tests/test_vcp.py`

**Interfaces:**
- Produces: `_is_breakout(closes, opens, vols, ma50, pivot, p) -> bool` — 마지막 바가 돌파인가:
  첫돌파(전일종가≤피벗 & 당일종가>피벗) AND 양봉(종가>시가) AND 거래량≥ma50×breakout_vol_mult AND (종가−피벗)/피벗 ≤ near_pivot_pct.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vcp.py 에 추가
from canslim_lib.vcp import _is_breakout


def test_is_breakout_clean_true():
    closes = [95.0, 104.0]; opens = [96.0, 100.0]; vols = [100.0, 300.0]; ma50 = [150.0, 150.0]
    p = {"breakout_vol_mult": 1.4, "near_pivot_pct": 5.0}
    # 전일95≤100, 당일104>100(첫돌파), 양봉(104>100), vol300≥150×1.4=210, 연장4%≤5
    assert _is_breakout(closes, opens, vols, ma50, pivot=100.0, p=p) is True


def test_is_breakout_quiet_volume_false():
    closes = [95.0, 104.0]; opens = [96.0, 100.0]; vols = [100.0, 120.0]; ma50 = [150.0, 150.0]
    p = {"breakout_vol_mult": 1.4, "near_pivot_pct": 5.0}
    # 거래량 120 < 210 → 조용한 돌파라 False
    assert _is_breakout(closes, opens, vols, ma50, pivot=100.0, p=p) is False


def test_is_breakout_extended_false():
    closes = [108.0, 120.0]; opens = [107.0, 109.0]; vols = [100.0, 300.0]; ma50 = [150.0, 150.0]
    p = {"breakout_vol_mult": 1.4, "near_pivot_pct": 5.0}
    # 전일108>100이라 첫돌파 아님(이미 위) → False
    assert _is_breakout(closes, opens, vols, ma50, pivot=100.0, p=p) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp.py -k is_breakout -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/canslim_lib/vcp.py 에 추가
def _is_breakout(closes, opens, vols, ma50, pivot, p) -> bool:
    i = len(closes) - 1
    if pivot is None or i < 1:
        return False
    if not (closes[i] > pivot and closes[i - 1] <= pivot):   # 첫돌파
        return False
    if not (closes[i] > opens[i]):                            # 양봉
        return False
    m = ma50[i] if i < len(ma50) else None
    if not (m and vols[i] >= m * p["breakout_vol_mult"]):     # 거래량 터짐
        return False
    if (closes[i] - pivot) / pivot * 100.0 > p["near_pivot_pct"]:  # 피벗 근접
        return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vcp.py -k is_breakout -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp.py tests/test_vcp.py
git commit -m "feat(vcp): _is_breakout (첫돌파+양봉+거래량터짐+근접)"
```

---

### Task 4: vcp.py — evaluate_vcp 재작성 (통합)

**Files:**
- Modify: `scripts/canslim_lib/vcp.py` (evaluate_vcp 본문 교체)
- Test: `tests/test_vcp.py` (기존 evaluate_vcp 테스트를 새 로직에 맞게 갱신)

**Interfaces:**
- Consumes: Task1~3 부품 + 기존 `_mean`.
- Produces: `evaluate_vcp(series, params=None) -> dict` (반환 키 불변).

새 로직(spec §4):
- lookback 슬라이스 → adaptive_zigzag → find_contraction_chain.
- chain None이면 reason="no_contraction_chain".
- 베이스=base_start..끝. ma50=volume_ma(vols,50).
- vcp_detected = (2≤count≤6) AND (수렴) AND (우측 마름: 베이스 우측 1/3 min(vol/ma50)≤dry_max).
- 수축별 거래량 감소는 계산은 하되 게이트 아님.
- status: _is_breakout → breakout / 수렴위반·베이스저점이탈 → failed / 피벗근접+dryup≤1 → actionable / else forming.
- entry_ready = vcp_detected AND status∈{breakout,actionable}.

- [ ] **Step 1: Write/Update the failing test**

```python
# tests/test_vcp.py — 기존 evaluate_vcp 테스트를 아래로 교체/갱신(합성은 새 로직에 맞게 조정 허용)
from canslim_lib.vcp import evaluate_vcp


def _vcp_series():
    # 수렴 수축 + 우측 거래량 마름 + 거래량 터지는 첫돌파(마지막 바)
    base = [100, 92, 84, 78.3, 82, 88, 87, 84, 81.8, 84, 87, 88]   # 수축 수렴, 피벗≈88
    closes = [60, 70, 80, 95] + base + [88.5]                       # 마지막 바: 88 첫돌파
    n = len(closes)
    opens = [c * 0.99 for c in closes]; opens[-1] = 88.0            # 마지막 양봉(88.5>88)
    highs = [c * 1.01 for c in closes]; lows = [c * 0.99 for c in closes]
    vols = [3000] * 4 + [1500, 1500, 1500] + [600] * (len(base) - 3) + [6000]  # 우측 마름+돌파 폭증
    assert len(vols) == n
    dates = [f"2026-{1+i//28:02d}-{1+i%28:02d}" for i in range(n)]
    return {"dates": dates, "closes": closes, "opens": opens, "highs": highs, "lows": lows, "volumes": vols}


def test_evaluate_vcp_recognizes_and_breaks_out():
    r = evaluate_vcp(_vcp_series())
    assert r["vcp_detected"] is True
    assert r["pivot_price"] is not None
    assert r["status"] == "breakout"
    assert r["entry_ready"] is True


def test_evaluate_vcp_short_base_rejected():
    s = {"dates": ["d"]*5, "closes": [100,99,100,98,99], "opens": [100]*5,
         "highs": [101]*5, "lows": [98]*5, "volumes": [1]*5}
    r = evaluate_vcp(s)
    assert r["vcp_detected"] is False
    assert r["reason"] in ("base_too_short", "no_contraction_chain")
```

> 합성 시계열이 새 임계(zigzag_k·dry_max 기본값)로 의도대로 안 나오면 **시계열 수치를 조정**해
> vcp_detected=True·status=breakout을 만들 것(단정 의도 유지). 알고리즘은 Task1~3 부품을 쓰되
> evaluate_vcp 본문은 자유.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vcp.py -k "recognizes or short_base" -v`
Expected: FAIL (기존 evaluate_vcp가 새 단정 불충족)

- [ ] **Step 3: Replace evaluate_vcp body**

```python
def evaluate_vcp(series: dict, params: dict | None = None) -> dict:
    p = {**DEFAULT_PARAMS, **(params or {})}
    lb = p["lookback_days"]
    closes = (series.get("closes") or [])[-lb:]
    highs = (series.get("highs") or [])[-lb:]
    lows = (series.get("lows") or [])[-lb:]
    vols = (series.get("volumes") or [])[-lb:]
    opens = (series.get("opens") or [])[-lb:]
    dates = (series.get("dates") or [])[-lb:]

    base: dict = {
        "vcp_detected": False, "num_contractions": 0, "contractions": [],
        "base_length_days": 0, "base_depth_pct": None, "pivot_price": None,
        "pct_to_pivot": None, "volume_dryup_ratio": None, "tightness_pct": None,
        "status": "forming", "swings": [], "reason": None, "entry_ready": False,
    }
    if len(closes) < p["min_base_days"]:
        base["reason"] = "no_data" if not closes else "base_too_short"
        return base

    swings = adaptive_zigzag(closes, p["zigzag_k"])
    base["swings"] = [{"date": dates[i] if i < len(dates) else None, "price": round(pr, 2), "kind": k}
                      for i, pr, k in swings]
    chain = find_contraction_chain(swings, p["contraction_tol"])
    if not chain:
        base["reason"] = "no_contraction_chain"
        return base

    bs = chain["base_start"]; depths = chain["depths"]; T = chain["count"]; pivot = chain["pivot"]
    base["num_contractions"] = T
    base["contractions"] = depths
    base["base_length_days"] = len(closes) - bs
    bl = lows[bs:]; bv = vols[bs:]
    ma50 = volume_ma(vols, 50)
    base_ma50 = ma50[bs:]
    last_close = closes[-1]

    base["pivot_price"] = pivot
    if pivot:
        base["pct_to_pivot"] = round((pivot - last_close) / pivot * 100.0, 2)
    base["volume_dryup_ratio"] = (round((_mean(vols[-5:]) or 0.0) / ma50[-1], 3) if ma50 and ma50[-1] else None)
    tight = _mean([(highs[i] - lows[i]) / closes[i] * 100.0 for i in range(len(closes))[-10:] if closes[i]])
    base["tightness_pct"] = round(tight, 2) if tight is not None else None

    cond_count = 2 <= T <= 6
    cond_mono = all(depths[i] <= depths[i - 1] * p["contraction_tol"] for i in range(1, T)) if T >= 2 else False
    third = max(1, len(bv) // 3)
    right_ratios = [bv[i] / base_ma50[i] for i in range(len(bv))[-third:] if i < len(base_ma50) and base_ma50[i]]
    dry_min = min(right_ratios) if right_ratios else 9.9
    cond_dry = dry_min <= p["dry_max"]
    base["vcp_detected"] = bool(cond_count and cond_mono and cond_dry)
    if base["vcp_detected"]:
        base["base_depth_pct"] = round(max(depths), 2)
    else:
        base["reason"] = ("contraction_count_not_2_6" if not cond_count
                          else "not_monotone_contraction" if not cond_mono
                          else "volume_not_drying")

    base_low = min(bl) if bl else last_close
    mono_violated = T >= 2 and depths[-1] > depths[-2] * p["contraction_tol"]
    if _is_breakout(closes, opens, vols, ma50, pivot, p):
        base["status"] = "breakout"
    elif mono_violated or last_close < base_low:
        base["status"] = "failed"
    elif (base["pct_to_pivot"] is not None and 0 <= base["pct_to_pivot"] <= p["near_pivot_pct"]
          and (base["volume_dryup_ratio"] if base["volume_dryup_ratio"] is not None else 9.9) <= 1.0):
        base["status"] = "actionable"
    else:
        base["status"] = "forming"
    base["entry_ready"] = bool(base["vcp_detected"] and base["status"] in ("breakout", "actionable"))
    return base
```
또한 DEFAULT_PARAMS에 `"zigzag_k": 4.0, "dry_max": 0.7` 가 있어야 함(Task1서 추가됨).

- [ ] **Step 4: Run full vcp test suite**

Run: `python -m pytest tests/test_vcp.py -v`
Expected: PASS (Task1~3 + 새 evaluate_vcp 테스트 모두). 기존에 있던 옛 evaluate_vcp 단정(옛 로직 가정)은 새 동작에 맞게 **갱신/삭제**한다 — 단 의미 있는 단정만 남길 것(환각 테스트 금지). 합성이 안 맞으면 Step1 주석대로 시계열 조정.

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/vcp.py tests/test_vcp.py
git commit -m "feat(vcp): evaluate_vcp 재작성 — 적응형 베이스/피벗(최소저항선)+50선 거래량+첫돌파"
```

---

### Task 5: 보정 + 검증 (6예시 + 70종목 회귀 가드)

**Files:**
- Modify: `scripts/canslim_lib/vcp.py` (DEFAULT_PARAMS 임계 보정만)
- (읽기) `public/data/vcp_examples.json`, `public/data/sepa-trend-candidates.json`

**목표:** 임계값(zigzag_k, dry_max, breakout_vol_mult, near_pivot_pct, contraction_tol)을 보정해
**5예시 인식+돌파** + **70종목 회귀 가드**를 동시에 만족.

- [ ] **Step 1: 6예시 검증 스크립트 실행 (인식)**

vcp-audit는 같은 evaluate_vcp를 쓰므로 자동 반영. 6예시 인식 확인:
```bash
python -X utf8 scripts/screen_vcp_audit.py --no-detector
python -X utf8 -c "import json;d=json.load(open('public/data/sepa-vcp-audit.json',encoding='utf-8'));[print(it['code'],it.get('name'),'vcp=',it['detector_verdict']['vcp_detected']) for it in d['items']]"
```
기대: 5예시(194480·014680·030210×2·220260) `vcp=True`. 메리츠(138040)는 무관.

- [ ] **Step 2: 돌파 발화 검증 (정답일 as-of)**

각 예시의 breakout_date as-of로 evaluate_vcp를 돌려 status==breakout 확인:
```bash
python -X utf8 - <<'PY'
import sys, json; sys.path.insert(0,'scripts')
from canslim_lib import vcp
from canslim_lib.vcp_audit import load_series
ex=json.load(open('public/data/vcp_examples.json',encoding='utf-8'))['examples']
for e in ex:
    if e['code']=='138040':  # 메리츠 제외
        continue
    s=load_series(e['code'], e.get('start'), (e.get('breakout_date') or e['end']))
    import bisect
    j=bisect.bisect_right(s['dates'], e['breakout_date'])-1
    sub={k:s[k][:j+1] for k in ('dates','closes','opens','highs','lows','volumes')}
    r=vcp.evaluate_vcp(sub)
    print(e['note'], e['breakout_date'], '-> status', r['status'], 'vcp', r['vcp_detected'], 'pivot', r['pivot_price'])
PY
```
기대: 5예시 모두 돌파일 as-of `status=='breakout'`.

- [ ] **Step 3: 70종목 회귀 가드**

```bash
python -X utf8 scripts/screen_vcp.py --out public/data/_vcp_regcheck.json
python -X utf8 -c "import json;d=json.load(open('public/data/_vcp_regcheck.json',encoding='utf-8'));print('vcp_count',d['vcp_count'],'entry_ready',d['entry_ready_count'],'dist',d['status_distribution'],'n',len(d['candidates']))"
rm public/data/_vcp_regcheck.json
```
베이스라인(수정 전): vcp_count 3 · entry_ready 0 · breakout5·actionable1·forming59·failed5.
가드: vcp_count·breakout가 비합리적으로 폭증(예: 수십~수백)하지 않을 것. (적당히 늘어나는 건 정상 — 검출기가 더 잘 잡으니까.)

- [ ] **Step 4: 임계 보정 루프**

Step1~3가 동시에 만족 안 되면 DEFAULT_PARAMS의 `zigzag_k`(↑면 임계↑·수축 굵게, ↓면 잘게), `dry_max`,
`near_pivot_pct`, `contraction_tol`을 조정하며 Step1~3 재실행. 권장 탐색: zigzag_k ∈ [2,6],
dry_max ∈ [0.6,0.9], near_pivot_pct ∈ [3,8]. **5예시 인식+돌파 우선, 그다음 회귀 가드.**
- 만족하는 값 세트를 찾으면 DEFAULT_PARAMS에 반영.
- 단위 테스트(`python -m pytest tests/test_vcp.py -q`)가 여전히 통과하는지 확인(합성 시계열이 임계
  변화에 깨지면 합성 조정).
- **둘 다 도저히 동시 만족 못 하면**(예: 5예시 인식하려니 70종목 폭증) 중단하고 보고 —
  알고리즘 구조 보완이 필요한 신호(컨트롤러/사용자 에스컬레이션).

- [ ] **Step 5: 보정 결과 커밋**

```bash
git add scripts/canslim_lib/vcp.py tests/test_vcp.py
git commit -m "feat(vcp): 임계 보정 — 5예시 인식+돌파 통과 + 70종목 회귀 가드"
```
커밋 메시지에 최종 임계값과 5예시/70종목 결과를 요약.

---

### Task 6: 문서 동기화 (doc-logic-sync)

**Files:**
- Modify: `docs/superpowers/specs/2026-06-30-vcp-detector-v2-design.md` (최종 임계값·결과 §9에 기록)
- Modify: `.claude/skills/find-vcp/SKILL.md` (돌파 정의가 바뀌었으면 "결과 보는 법"의 status 설명 갱신)
- (확인) `scripts/screen_vcp.py` — `--zigzag-pct`·`--max-final-depth`가 이제 무효임을 help에 명시(또는 제거). 동작 깨짐 없으면 표기만.

- [ ] **Step 1: 스펙·스킬 문구 갱신**

spec §9(미해결/후속) 아래에 "최종 채택 임계값(zigzag_k=…, dry_max=…, …)과 검증 결과(5예시 인식+돌파, 70종목 vcp_count …)" 한 단락 추가. find-vcp SKILL.md의 status/돌파 설명이 새 정의(첫돌파+양봉+거래량터짐+근접·적응형 수축·최소저항선 피벗)와 어긋나면 그 문장만 갱신.

- [ ] **Step 2: screen_vcp.py CLI help 표기**

`--zigzag-pct`/`--max-final-depth` argument의 help에 `(현재 미사용 — evaluate_vcp 재설계로 적응형 전환)` 추가. 인자 제거는 하지 않음(callers/스크립트 깨짐 방지).

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-06-30-vcp-detector-v2-design.md .claude/skills/find-vcp/SKILL.md scripts/screen_vcp.py
git commit -m "docs(vcp): 검출기 재설계 문서 동기화 (스펙 결과·find-vcp 스킬·CLI 표기)"
```

---

## Self-Review 결과 (작성자 점검)

- **Spec 커버리지**: §4.1 베이스/피벗(Task2) · §4.2 적응형 수축(Task1) · §4.3 거래량 50선·우측마름 하드/수축별 소프트(Task4) · §4.4 돌파(Task3) · §4.5 스키마 불변(Task4 Global Constraints) · §5 검증하네스(Task5) · §7 머지 기준(Task5) · §8 검증(Task1~5) · [[doc-logic-sync]](Task6) 모두 태스크 존재.
- **타입 일관성**: volume_ma/adaptive_zigzag/find_contraction_chain/_is_breakout 시그니처가 정의(Task1~3)와 evaluate_vcp 사용처(Task4) 일치. 반환 키 13종 불변(Task4 base dict).
- **파라미터**: 신규 zigzag_k·dry_max만 추가, 기존 breakout_vol_mult·near_pivot_pct·contraction_tol 재사용 → callers(screen_vcp params) 안 깨짐. zigzag_pct·max_final_depth는 잔존·미사용(Task6서 표기).
- **경험적 리스크(정직)**: Task5는 TDD가 아닌 *보정 루프* — 합성 단위테스트(Task1~4)는 메커니즘을 잠그고, 5예시/70종목 동시 만족은 임계 탐색으로 달성. 동시 만족 불가 시 Task5 Step4대로 에스컬레이션(알고리즘 구조 보완은 별도 라운드).
