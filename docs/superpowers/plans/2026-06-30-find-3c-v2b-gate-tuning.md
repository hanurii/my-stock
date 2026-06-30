# find-3c v2b 게이트 보정 + 오라클 하니스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 책 오라클(NU·GOOG·CRUS)에 맞춰 find-3c 게이트 3값을 보정하고(min_shelf_days 5→2, max_shelf_position 66→90, min_cup_days 35→25), 그 보정을 오프라인 재현 가능한 pytest 하니스로 고정한다.

**Architecture:** `cheat.py`의 `DEFAULT_PARAMS` 값 3개만 바꾼다(게이트 로직·앵커링·스키마·상태 불변). 오라클 3종의 FDR 데이터를 커밋된 JSON fixture로 덤프하고, pytest가 그 fixture를 as-of로 슬라이스해 `evaluate_cheat`를 검증한다. 기본값 변경으로 깨지는 기존 단위 테스트는 명시 param으로 디커플하거나 데이터를 새 임계값에 맞춘다.

**Tech Stack:** Python 3, pytest, FinanceDataReader(fixture 덤프 1회용만), 기존 `canslim_lib.cheat`.

## Global Constraints

- 설계 spec: `docs/superpowers/specs/2026-06-30-find-3c-v2b-gate-tuning-design.md`.
- **변경은 `DEFAULT_PARAMS` 값 3개뿐**: `min_shelf_days` 5→**2**, `max_shelf_position` 66→**90**, `min_cup_days` 35→**25**. 게이트 if/elif 로직, 앵커링, 출력 스키마, 상태/entry_ready 로직은 **불변**.
- 오라클 하니스는 **네트워크 없이 재현**되어야 한다 → FDR 데이터를 커밋된 fixture JSON으로 고정. pytest는 FDR를 호출하지 않는다.
- 과완화 방지 불변식: 보정값으로 라이브 70종목(sepa-trend-candidates.json all_pass) 재실행 시 `pattern_count` 폭증 없음(실측 기대값 0). 폭증(>10) 시 보고·재검토.
- 게이트 **로직** 테스트는 명시 param 으로 기본값과 독립시킨다. 기본값 자체는 `test_default_params_*` 에서만 단언.
- 공유 파일 무접촉·컷오프 금지·자동 commit 금지(plan 커밋 단계는 개발용).

## File Structure

- `scripts/_dump_oracle_fixtures.py` — **신규(개발 보조).** FDR로 NU·GOOG·CRUS 데이터를 받아 fixture JSON 저장. 1회 실행.
- `tests/fixtures/oracle/NU.json`, `GOOG.json`, `CRUS.json` — **신규(커밋).** 오라클 OHLCV.
- `tests/test_cheat_oracle.py` — **신규.** fixture as-of 검증 하니스.
- `scripts/canslim_lib/cheat.py` — **수정.** `DEFAULT_PARAMS` 3값.
- `tests/test_cheat.py` — **수정.** 기본값 변경에 영향받는 테스트 갱신.
- `.claude/skills/find-3c/SKILL.md`, v1/v2a spec — doc-sync(Task 4).

---

## Task 1: 오라클 fixture 덤프 + 커밋

**Files:**
- Create: `scripts/_dump_oracle_fixtures.py`
- Create: `tests/fixtures/oracle/NU.json`, `tests/fixtures/oracle/GOOG.json`, `tests/fixtures/oracle/CRUS.json`

**Interfaces:**
- Consumes: `FinanceDataReader`.
- Produces: fixture JSON 형식 `{"ticker": str, "rows": [{"date","open","high","low","close","volume"}, ...]}` (date 오름차순, ISO 문자열).

- [ ] **Step 1: Write the dump script**

`scripts/_dump_oracle_fixtures.py`:

```python
"""find-3c 오라클 fixture 덤프(1회용 개발 보조). FDR로 NU·GOOG·CRUS OHLCV를 받아
tests/fixtures/oracle/{ticker}.json 으로 저장. pytest 는 이 fixture만 읽는다(네트워크 X).
"""
from __future__ import annotations
import json
from pathlib import Path
import FinanceDataReader as fdr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "oracle"
SPECS = {
    "NU":   ("2023-01-01", "2023-10-25"),
    "GOOG": ("2004-08-19", "2005-01-05"),
    "CRUS": ("2009-06-01", "2010-03-10"),
}


def dump(ticker: str, start: str, end: str) -> int:
    df = fdr.DataReader(ticker, start, end)
    rows = [{"date": idx.strftime("%Y-%m-%d"),
             "open": float(r["Open"]), "high": float(r["High"]),
             "low": float(r["Low"]), "close": float(r["Close"]),
             "volume": float(r["Volume"])}
            for idx, r in df.iterrows()]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{ticker}.json").write_text(
        json.dumps({"ticker": ticker, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return len(rows)


if __name__ == "__main__":
    for tk, (s, e) in SPECS.items():
        n = dump(tk, s, e)
        print(f"{tk}: {n} rows -> tests/fixtures/oracle/{tk}.json")
```

- [ ] **Step 2: Run it to produce the fixtures**

Run: `python scripts/_dump_oracle_fixtures.py`
Expected: 3줄 출력, 각 ~150–250 rows. 파일 3개 생성.

- [ ] **Step 3: Sanity-check the fixtures**

```bash
python -c "
import json
from pathlib import Path
for tk in ('NU','GOOG','CRUS'):
    d=json.load(open(f'tests/fixtures/oracle/{tk}.json',encoding='utf-8'))
    rows=d['rows']; print(tk, len(rows), rows[0]['date'], '..', rows[-1]['date'])
    assert all(k in rows[0] for k in ('date','open','high','low','close','volume'))
    # date ascending
    assert all(rows[i]['date'] <= rows[i+1]['date'] for i in range(len(rows)-1))
print('fixtures OK')
"
```
Expected: `fixtures OK`. NU last date ≥ 2023-10-19, CRUS last ≥ 2010-03-08, GOOG covers ~2004-12-23.

- [ ] **Step 4: Commit**

```bash
git add scripts/_dump_oracle_fixtures.py tests/fixtures/oracle/NU.json tests/fixtures/oracle/GOOG.json tests/fixtures/oracle/CRUS.json
git commit -m "test(find-3c): 오라클 fixture(NU·GOOG·CRUS) 덤프 + 커밋"
```

---

## Task 2: 오라클 하니스 (TDD RED — NU가 현 게이트에선 실패)

**Files:**
- Create: `tests/test_cheat_oracle.py`

**Interfaces:**
- Consumes: `tests/fixtures/oracle/*.json` (Task 1), `canslim_lib.cheat.evaluate_cheat`.
- Produces: `load_asof(ticker, date) -> series_dict`, 오라클 단언 테스트.

- [ ] **Step 1: Write the oracle harness**

`tests/test_cheat_oracle.py`:

```python
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.cheat import evaluate_cheat

FIX = Path(__file__).resolve().parent / "fixtures" / "oracle"


def load_asof(ticker: str, date: str) -> dict:
    """fixture에서 date(포함) 이하로 슬라이스한 series dict."""
    rows = json.loads((FIX / f"{ticker}.json").read_text(encoding="utf-8"))["rows"]
    rows = [r for r in rows if r["date"] <= date]
    return {"dates": [r["date"] for r in rows],
            "closes": [r["close"] for r in rows],
            "highs": [r["high"] for r in rows],
            "lows": [r["low"] for r in rows],
            "volumes": [r["volume"] for r in rows]}


# ── NU 2023-10-18: 완성/상단 치트(위치 84%, 선반 2일) — v2b에서 성립 ──
def test_oracle_nu_actionable_at_cheat():
    r = evaluate_cheat(load_asof("NU", "2023-10-18"))
    assert r["pattern_detected"] is True
    assert r["status"] == "actionable"
    assert 7.8 <= r["pivot_price"] <= 8.2     # 문서 cheat range top ~$8.03


def test_oracle_nu_breakout_next_day():
    r = evaluate_cheat(load_asof("NU", "2023-10-19"))
    assert r["status"] == "breakout"


# ── GOOG 2004-12-23: low/middle 치트 — v2a부터 성립(회귀 없음) ──
def test_oracle_goog_pattern():
    r = evaluate_cheat(load_asof("GOOG", "2004-12-23"))
    assert r["pattern_detected"] is True
    assert r["shelf_position_pct"] <= 66.0


# ── CRUS 2010-02-25: 치트를 정확히 '위치'(pattern은 borderline, 단언 안 함) ──
def test_oracle_crus_locates_cheat():
    r = evaluate_cheat(load_asof("CRUS", "2010-02-25"))
    assert r["left_rim_date"] == "2010-01-12"
    assert r["cup_low_date"] == "2010-02-05"
    assert 20 <= r["cup_depth_pct"] <= 27
    assert 7.2 <= r["pivot_price"] <= 7.6
    assert r["status"] in ("actionable", "forming", "breakout")
```

- [ ] **Step 2: Run — expect NU tests to FAIL (current gates 5/66), others PASS**

Run: `python -m pytest tests/test_cheat_oracle.py -v`
Expected: `test_oracle_nu_actionable_at_cheat` **FAIL**(현 기본값 min_shelf_days=5라
NU 선반 2일 → shelf_too_short → pattern_detected=False). `test_oracle_nu_breakout_next_day`
는 status=breakout 이라 PASS 가능. `test_oracle_goog_pattern`·`test_oracle_crus_locates_cheat`
PASS. → NU pattern 테스트의 RED 가 Task 3의 보정으로 GREEN 이 되는 게 목표.

> 만약 NU pattern 테스트가 이미 PASS면 기본값이 이미 보정된 것 — Task 3가 불필요한지
> 확인. (현 코드 기준 기본값 5/66/35이므로 FAIL 이 정상.)

- [ ] **Step 3: Commit (RED 하니스)**

```bash
git add tests/test_cheat_oracle.py
git commit -m "test(find-3c): 오라클 검증 하니스(NU pattern은 현 게이트서 RED)"
```

---

## Task 3: 게이트 보정 (DEFAULT_PARAMS 3값) + 영향 단위 테스트 갱신 (GREEN)

**Files:**
- Modify: `scripts/canslim_lib/cheat.py` (`DEFAULT_PARAMS`)
- Modify: `tests/test_cheat.py` (영향받는 4개 지점)

**Interfaces:**
- Consumes: 없음(값 변경).
- Produces: 새 기본값 `min_shelf_days=2`, `max_shelf_position=90`, `min_cup_days=25`.

- [ ] **Step 1: Update the affected unit tests in `tests/test_cheat.py` FIRST (so they encode the new defaults)**

(1) `test_default_params_has_required_keys` 의 값 단언을 교체:
```python
    assert DEFAULT_PARAMS["min_cup_depth"] == 12.0
    assert DEFAULT_PARAMS["max_shelf_position"] == 90.0
    assert DEFAULT_PARAMS["min_shelf_days"] == 2
    assert DEFAULT_PARAMS["min_cup_days"] == 25
```

(2) `test_evaluate_rejects_shelf_too_high_in_cup` — 기본값(90)으론 84% 선반이 통과하므로
**명시 param 으로 게이트 로직을 검증**하도록 마지막 호출을 교체:
```python
    r = evaluate_cheat(_series(closes, vols=[1000]*25 + [2000]*12 + [500]*10),
                       {"max_shelf_position": 66})
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_high_in_cup"
```

(3) `test_evaluate_rejects_short_cup_base` — 새 기본값(min_cup_days=25)에서 `cup_too_short`
를 확실히 트립하도록 데이터를 교체(전체 n≥40, 옛 peak를 뒤쪽에 둬 cup_base<25):
```python
def test_evaluate_rejects_short_cup_base():
    # 앞을 길게(낮게) 패딩해 n>=40 이면서, 옛 peak(global max)를 뒤쪽에 둬
    # cup_base_days = (n-1) - left_rim_idx < 25 → cup_too_short.
    pre = [60 + i * 0.02 for i in range(22)]      # 60~60.42, 22봉(peak보다 낮음)
    rim = [98, 99, 100, 99, 98]                   # peak(global max) at idx 24
    decline = [96, 90, 84, 80]
    bottom = [76, 77]
    recovery = [80, 84, 88, 90]
    shelf = [89, 88, 89, 88, 89, 88]
    closes = pre + rim + decline + bottom + recovery + shelf  # 22+5+4+2+4+6 = 43
    r = evaluate_cheat(_series(closes, vols=[1000]*len(closes)))
    # left_rim_idx=24, n=43 → cup_base_days=18 < 25
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_short"
```

(4) 나머지 테스트(`test_find_cheat_shelf_*` 는 min_shelf_days=5 명시 호출이라 무관,
`test_evaluate_detects_clean_3c_v2`·`test_evaluate_rejects_loose_shelf`·
`test_evaluate_rejects_volume_not_drying`·상태 테스트·`shelf_position` 불변식·
`test_evaluate_rejects_new_high_no_overhead_cup` 는 새 기본값에서도 의도대로 통과)
는 **변경하지 않는다**. Step 4에서 전부 green 인지로 확인.

- [ ] **Step 2: Run — these unit tests now FAIL against the still-old defaults**

Run: `python -m pytest tests/test_cheat.py::test_default_params_has_required_keys tests/test_cheat.py::test_evaluate_rejects_short_cup_base -v`
Expected: FAIL(아직 `cheat.py` 기본값이 5/66/35라 단언 불일치). 이게 Step 3을 부르는 RED.

- [ ] **Step 3: Change the three `DEFAULT_PARAMS` values in `cheat.py`**

`scripts/canslim_lib/cheat.py` 의 `DEFAULT_PARAMS` 에서 세 값만 교체:
```python
    "min_cup_days": 25,        # was 35  (치트는 컵 완성 전 일찍 발동)
    "min_shelf_days": 2,       # was 5   (치트 멈춤은 짧다: NU 2일)
    "max_shelf_position": 90.0,  # was 66.0 (완성 치트 포함)
```
(다른 키·값은 그대로. `min_shelf_days` 는 `find_cheat_shelf` 의 `no_overhead_cup`
가드에도 쓰이며 기본 인자 `min_shelf_days: int = 5` 는 evaluate_cheat 가 항상
`p["min_shelf_days"]` 로 넘기므로 실효값은 2가 된다 — 함수 기본 인자 자체는 변경 불필요하지만,
혼선을 막기 위해 시그니처 기본도 `= 2` 로 맞춘다.)

`find_cheat_shelf` 시그니처 기본 인자도 정합성 위해 교체:
```python
def find_cheat_shelf(highs, lows, min_shelf_pullback=None, min_shelf_days=2):
```

- [ ] **Step 4: Run the full cheat test suite + oracle harness — all GREEN**

Run: `python -m pytest tests/test_cheat.py tests/test_cheat_oracle.py -v`
Expected: 전부 PASS. 특히 `test_oracle_nu_actionable_at_cheat` 가 이제 GREEN.
한 테스트라도 실패하면 그 테스트의 **데이터/명시 param** 을 조정(게이트 로직·기본값은
Step 3에서 확정 — 변경 금지). `_clean_3c_v2` 가 여전히 pattern_detected=True 인지 확인.

- [ ] **Step 5: Commit**

```bash
git add scripts/canslim_lib/cheat.py tests/test_cheat.py
git commit -m "feat(find-3c): v2b 게이트 보정(shelf_days 2·position 90·cup_days 25) — 오라클 GREEN"
```

---

## Task 4: 라이브 재실행 + 과완화 점검 + 문서 동기화

**Files:**
- Modify: `.claude/skills/find-3c/SKILL.md`
- Modify: `docs/superpowers/specs/2026-06-30-find-3c-design.md`, `...-v2-anchoring-design.md` (게이트 기본값 포인터)
- (런타임 산출) `public/data/sepa-3c-candidates.json`

**Interfaces:**
- Consumes: Task 3의 보정된 기본값.
- Produces: 갱신된 문서.

- [ ] **Step 1: Re-run live and check for over-loosening**

```bash
python scripts/screen_3c.py
python -c "
import json
d=json.load(open('public/data/sepa-3c-candidates.json',encoding='utf-8'))
print('pattern', d['pattern_count'], 'entry_ready', d['entry_ready_count'], 'dist', d['status_distribution'])
from collections import Counter
print('reasons', Counter(c.get('reason') for c in d['candidates']))
assert d['pattern_count'] <= 10, f'OVER-LOOSENED: pattern_count={d[\"pattern_count\"]} — 보정값 재검토'
print('no over-loosening (pattern_count <= 10)')
"
```
Expected: `pattern_count` 가 폭증하지 않음(실측 기대 0). >10 이면 BLOCKED 로 보고하고
보정값을 재검토. 0~소수면 정상(한국 트렌드 통과 종목엔 3C가 드묾).

- [ ] **Step 2: Update SKILL.md "현재 한계" note**

`.claude/skills/find-3c/SKILL.md` 의 `## 현재 한계 (v2a)` 절을 교체:
```markdown
## 현재 한계 / 적용 범위 (v2b)
- 게이트는 미너비니 책 3C 예시 **NU·GOOG·CRUS** 실데이터로 보정됨
  (min_shelf_days 2·max_shelf_position 90·min_cup_days 25). 셋 다 컵·치트 피벗을
  정확히 짚으며 NU·GOOG는 패턴 성립으로 검증(`tests/test_cheat_oracle.py`).
- **현재 한국 트렌드 통과 라이브 = `pattern_count` 0(또는 극소수).** 버그가 아니라
  **입력 집단 특성**이다: 트렌드 통과 종목은 *조정 없이 오른 신고가 부근 모멘텀
  리더*라, "옛 고점에서 조정 후 회복 중"인 3C와 구조적으로 반대다(대부분
  `no_overhead_cup`·`cup_too_short`).
- **한국 3C는 과거 조정·상승장 초입 종목에 있으며**, 이를 발굴하는 건
  `find-3c-history`(과거 매 거래일 as-of 회고, Phase 3)의 몫이다.
```

- [ ] **Step 3: Add v2b pointer to the gate-default mentions in v1/v2a specs**

`docs/superpowers/specs/2026-06-30-find-3c-design.md` 와
`...-find-3c-v2-anchoring-design.md` 의 기본값(컵 기간 35·선반 위치 66·선반 길이 5)이
언급된 곳 근처에 한 줄 포인터 추가(각 파일 1곳):
```markdown
> **갱신(v2b):** 게이트 기본값은 책 오라클 보정으로 min_shelf_days=2·
> max_shelf_position=90·min_cup_days=25 로 변경됨. 근거:
> `2026-06-30-find-3c-v2b-gate-tuning-design.md`.
```

- [ ] **Step 4: Verify docs + commit**

```bash
python -c "t=open('.claude/skills/find-3c/SKILL.md',encoding='utf-8').read(); assert t.startswith('---') and 'name: find-3c' in t; print('SKILL OK')"
git add .claude/skills/find-3c/SKILL.md docs/superpowers/specs/2026-06-30-find-3c-design.md docs/superpowers/specs/2026-06-30-find-3c-v2-anchoring-design.md
git commit -m "docs(find-3c): v2b 게이트 보정 반영 — SKILL 적용범위 + spec 포인터"
```

---

## Self-Review (작성자 점검)

**1. Spec coverage:**
- §2 게이트 보정 3값 → Task 3 Step 3. ✓
- §2.1 오라클 결과(NU/GOOG pattern, CRUS locate) → Task 2 하니스 단언. ✓
- §2.2 과완화 방지 불변식 → Task 4 Step 1(pattern_count ≤ 10 assert). ✓
- §3 오라클 하니스(fixture + pytest, 오프라인) → Task 1(fixture)·Task 2(harness). ✓
- §4 영향 단위 테스트 갱신(명시 param 디커플) → Task 3 Step 1. ✓
- §5 정직한 문서 → Task 4 Step 2-3. ✓

**2. Placeholder scan:** 모든 step 에 실제 코드/명령/기대출력. Task 3 Step 4의 데이터
미세조정은 의도된 TDD(로직·기본값 동결 명시). ✓

**3. Type consistency:** `load_asof` 반환 dict 키(dates/closes/highs/lows/volumes)가
`evaluate_cheat` 입력과 일치. fixture JSON 키(date/open/high/low/close/volume)가 덤프
스크립트·load_asof 에서 일치. `DEFAULT_PARAMS` 키 이름(min_shelf_days·max_shelf_position·
min_cup_days)이 cheat.py·test_default_params 에서 일치. 단언 임계값(NU 7.8~8.2·CRUS
7.2~7.6·cup_depth 20~27)이 §2 실측치와 정합. ✓
