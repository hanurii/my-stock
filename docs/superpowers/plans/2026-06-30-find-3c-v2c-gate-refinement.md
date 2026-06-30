# find-3c v2c 게이트 재보정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 오라클 8종에 맞춰 find-3c 게이트를 재보정한다 — `min_cup_days` 25→17(짧은 치트컵), 신규 `min_shelf_position`(25) 게이트로 V자 반등 거부 — 확장된 pytest 오라클로 고정.

**Architecture:** `cheat.py`의 `DEFAULT_PARAMS` 값 1개 변경 + 1개 추가, `evaluate_cheat` 게이트 체인에 `shelf_too_low_in_cup` 1개 삽입(앵커링·상태·스키마 불변). 오라클 fixture 5종 추가 + 하니스 단언 확장. 기본값 변경에 영향받는 단위 테스트 갱신.

**Tech Stack:** Python 3, pytest, FinanceDataReader(fixture 덤프만).

## Global Constraints

- 설계 spec: `docs/superpowers/specs/2026-06-30-find-3c-v2c-gate-refinement-design.md`.
- 변경: `min_cup_days` 25→**17**, 신규 `min_shelf_position`=**25.0**, 신규 게이트 `shelf_too_low_in_cup`. 게이트 순서: `... shelf_too_loose → shelf_too_low_in_cup → shelf_too_high_in_cup → volume_not_drying`.
- 앵커링·상태·entry_ready·출력 스키마·다른 게이트 로직·다른 DEFAULT_PARAMS 값은 **불변**.
- 오라클 하니스는 네트워크 없이 재현(커밋된 fixture). pytest는 FDR 호출 안 함.
- 과완화 방지: 보정값으로 라이브 70종목 `pattern_count` 폭증 없음(기대 0).
- 진양폴리는 **의도적 미검출**(reason `shelf_too_loose`로 단언 — 정직 고정).
- 게이트 로직 테스트는 명시 param 으로 기본값과 독립. 기본값은 `test_default_params_*`에서만 단언.
- 공유 파일 무접촉·컷오프 금지·자동 commit 금지(plan 커밋 단계는 개발용).

## File Structure
- `scripts/canslim_lib/cheat.py` — DEFAULT_PARAMS + 게이트 1개 추가.
- `scripts/_dump_oracle_fixtures.py` — 5종 추가.
- `tests/fixtures/oracle/{JBLU,AAPL,089970,000150,010640}.json` — 신규(커밋).
- `tests/test_cheat_oracle.py` — 단언 5개 추가.
- `tests/test_cheat.py` — 영향 테스트 갱신 + 신규 low-shelf 테스트.
- `scripts/screen_3c.py`·`scripts/screen_3c_history.py` — `--min-shelf-position` 추가.
- 문서: spec 포인터 + SKILL 2종.

---

## Task 1: 오라클 fixture 5종 추가

**Files:**
- Modify: `scripts/_dump_oracle_fixtures.py`
- Create: `tests/fixtures/oracle/JBLU.json`, `AAPL.json`, `089970.json`, `000150.json`, `010640.json`

**Interfaces:**
- Consumes: FinanceDataReader.
- Produces: 동일 fixture 형식 `{"ticker","rows":[{date,open,high,low,close,volume}]}`.

- [ ] **Step 1: Add the 5 entries to the SPECS dict**

`scripts/_dump_oracle_fixtures.py`의 `SPECS` 딕셔너리에 추가:
```python
    "JBLU":   ("2013-10-01", "2014-11-07"),
    "AAPL":   ("2003-08-01", "2004-08-16"),
    "089970": ("2020-03-01", "2021-03-22"),
    "000150": ("2020-07-01", "2021-07-06"),
    "010640": ("2020-12-01", "2021-12-10"),
```
(end 날짜는 각 저자 피벗을 포함하도록 넉넉히. FDR 가 end 직전까지 줄 수 있으니 +2~3일 여유.)

- [ ] **Step 2: Run the dump**

Run: `python scripts/_dump_oracle_fixtures.py`
Expected: 기존 3 + 신규 5 = 8줄 출력, 각 fixture 생성. (NU/GOOG/CRUS 재덤프돼도 동일 — 무해.)

- [ ] **Step 3: Sanity-check the new fixtures cover the pivot dates**

```bash
python -c "
import json
need = {'JBLU':'2014-11-03','AAPL':'2004-08-12','089970':'2021-03-19','000150':'2021-07-02','010640':'2021-12-08'}
for tk,piv in need.items():
    rows=json.load(open(f'tests/fixtures/oracle/{tk}.json',encoding='utf-8'))['rows']
    ds=[r['date'] for r in rows]
    assert any(d<=piv for d in ds) and ds[-1]>=piv, (tk, ds[0], ds[-1], piv)
    assert all(ds[i]<=ds[i+1] for i in range(len(ds)-1)), tk
    print(tk, len(rows), ds[0],'..',ds[-1], 'covers', piv)
print('new fixtures OK')
"
```
Expected: 5줄 + `new fixtures OK`. 각 fixture 마지막 날짜 ≥ 해당 피벗.

- [ ] **Step 4: Commit**

```bash
git add scripts/_dump_oracle_fixtures.py tests/fixtures/oracle/JBLU.json tests/fixtures/oracle/AAPL.json tests/fixtures/oracle/089970.json tests/fixtures/oracle/000150.json tests/fixtures/oracle/010640.json
git commit -m "test(find-3c): 오라클 fixture 5종 추가(JBLU·AAPL·브이엠·두산·진양폴리)"
```

---

## Task 2: 오라클 하니스 확장 (TDD RED — 브이엠·두산이 현 게이트서 실패)

**Files:**
- Modify: `tests/test_cheat_oracle.py`

**Interfaces:**
- Consumes: Task 1 fixtures, `load_asof`(기존), `evaluate_cheat`.

- [ ] **Step 1: Append the 5 oracle assertions**

`tests/test_cheat_oracle.py` 끝에 추가:
```python
# ── v2c 확장 오라클 ──────────────────────────────────────────────
def test_oracle_jblu_pattern():
    r = evaluate_cheat(load_asof("JBLU", "2014-11-03"))
    assert r["pattern_detected"] is True
    assert 11.0 <= r["pivot_price"] <= 12.5
    assert 25 <= r["shelf_position_pct"] <= 90


def test_oracle_aapl_pattern():
    r = evaluate_cheat(load_asof("AAPL", "2004-08-12"))
    assert r["pattern_detected"] is True
    assert 80 <= r["shelf_position_pct"] <= 92


def test_oracle_vm_pattern():   # 브이엠 089970
    r = evaluate_cheat(load_asof("089970", "2021-03-19"))
    assert r["pattern_detected"] is True
    assert 20000 <= r["pivot_price"] <= 21500
    assert 40 <= r["shelf_position_pct"] <= 55


def test_oracle_doosan_pattern():   # 두산 000150
    r = evaluate_cheat(load_asof("000150", "2021-07-02"))
    assert r["pattern_detected"] is True
    assert 90000 <= r["pivot_price"] <= 105000


def test_oracle_jinyang_known_miss():   # 진양폴리 010640 — 의도적 미검출(느슨 선반)
    r = evaluate_cheat(load_asof("010640", "2021-12-08"))
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_loose"
```

- [ ] **Step 2: Run — 브이엠·두산 FAIL(현 min_cup_days=25), 나머지 PASS**

Run: `python -m pytest tests/test_cheat_oracle.py -v`
Expected: `test_oracle_vm_pattern`·`test_oracle_doosan_pattern` **FAIL**(현재 cup_too_short).
`test_oracle_jblu_pattern`·`test_oracle_aapl_pattern`·`test_oracle_jinyang_known_miss` PASS.
> JBLU/AAPL/진양폴리가 FAIL 하면 fixture 날짜·값 문제 — 실제 evaluate_cheat 출력을 보고하고
> assert 임계값이 컨트롤러 검증치(JBLU 피벗 11.73·위치68 / AAPL 위치90 / 진양폴리 shelf_too_loose)와
> 맞는지 확인. 단언을 약화시키지 말고 BLOCKED 로 보고.

- [ ] **Step 3: Commit (RED)**

```bash
git add tests/test_cheat_oracle.py
git commit -m "test(find-3c): v2c 오라클 단언 5종(브이엠·두산은 현 게이트서 RED)"
```

---

## Task 3: 게이트 재보정 (DEFAULT_PARAMS + 신규 게이트) — GREEN

**Files:**
- Modify: `scripts/canslim_lib/cheat.py`
- Modify: `tests/test_cheat.py`
- Modify: `scripts/screen_3c.py`, `scripts/screen_3c_history.py` (CLI 인자)

**Interfaces:**
- Produces: `min_cup_days`=17, 신규 `min_shelf_position`=25.0, 신규 reason `shelf_too_low_in_cup`.

- [ ] **Step 1: Update affected unit tests FIRST (encode new defaults + new gate)**

`tests/test_cheat.py`:

(1) `test_default_params_has_required_keys` — 키 목록에 `"min_shelf_position"` 추가, 값 단언 추가:
```python
    assert DEFAULT_PARAMS["min_cup_days"] == 17
    assert DEFAULT_PARAMS["min_shelf_position"] == 25.0
```
(min_shelf_days==2, max_shelf_position==90.0 단언은 그대로 유지.)

(2) `test_evaluate_rejects_short_cup_base` — 새 기본값 17 과 독립시키려 **명시 param**으로:
```python
    r = evaluate_cheat(_series(closes, vols=[1000]*len(closes)), {"min_cup_days": 25})
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_short"
```
(기존 데이터 cup_base=18 < 25 → cup_too_short. 기본값 17 변경과 무관해짐.)

(3) **신규** `test_evaluate_rejects_low_shelf` 추가(선반이 바닥 직후 = 위치<25):
```python
def test_evaluate_rejects_low_shelf():
    # 옛 peak 100 → 가파른 하락 바닥 60(컵40%) → 바닥 직후 64 부근 즉시 반등(위치~10%).
    rim = [98, 99, 100, 99, 98]
    decline = [98 - i * (38 / 19) for i in range(20)]     # 98 → ~60
    bottom = [60, 61, 60, 61]
    shelf = [64, 63, 64, 63, 64, 63, 64, 63, 64, 63]      # 바닥 바로 위 64(위치 ~10%)
    closes = rim + decline + bottom + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*25 + [2000]*4 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_low_in_cup"
```

- [ ] **Step 2: Run those — FAIL against still-old code**

Run: `python -m pytest tests/test_cheat.py::test_default_params_has_required_keys tests/test_cheat.py::test_evaluate_rejects_low_shelf -v`
Expected: FAIL(아직 `min_shelf_position` 키 없음·게이트 없음). RED.

- [ ] **Step 3: Edit `cheat.py` — DEFAULT_PARAMS + new gate**

(a) `DEFAULT_PARAMS`에서:
```python
    "min_cup_days": 17,         # was 25 (치트는 컵 완성 전 일찍 발동)
```
그리고 `max_shelf_position` 줄 근처에 추가:
```python
    "min_shelf_position": 25.0,  # 신규: 선반이 바닥 직후 V자 반등이 아니어야(치트는 회복 중간 이상)
```

(b) `evaluate_cheat` 게이트 판정부에서 `cond_shelf_pos` 줄을 두 개로 분리:
기존:
```python
    cond_shelf_pos = shelf_position <= p["max_shelf_position"]
```
교체:
```python
    cond_shelf_pos_lo = shelf_position >= p["min_shelf_position"]
    cond_shelf_pos_hi = shelf_position <= p["max_shelf_position"]
```
그리고 if/elif 체인에서 `shelf_too_loose` 다음, `shelf_too_high_in_cup` 앞에 삽입(+ 기존
`cond_shelf_pos`→`cond_shelf_pos_hi`):
```python
    elif not cond_shelf_depth:
        base["reason"] = "shelf_too_loose"
    elif not cond_shelf_pos_lo:
        base["reason"] = "shelf_too_low_in_cup"
    elif not cond_shelf_pos_hi:
        base["reason"] = "shelf_too_high_in_cup"
    elif not cond_dryup:
        base["reason"] = "volume_not_drying"
```
(다른 게이트·앵커링·상태·스키마 불변.)

- [ ] **Step 4: Add `--min-shelf-position` to both CLIs**

`scripts/screen_3c.py`와 `scripts/screen_3c_history.py` 둘 다:
- argparse 에 추가(다른 `--max-shelf-position` 줄 근처):
```python
    ap.add_argument("--min-shelf-position", type=float, default=DEFAULT_PARAMS["min_shelf_position"])
```
- params dict 에 추가:
```python
        "min_shelf_position": args.min_shelf_position,
```

- [ ] **Step 5: Run full suite + oracle — all GREEN**

Run: `python -m pytest tests/test_cheat.py tests/test_cheat_oracle.py tests/test_cheat_history.py -v`
Expected: 전부 PASS. 특히 `test_oracle_vm_pattern`·`test_oracle_doosan_pattern` GREEN,
`test_evaluate_rejects_low_shelf` GREEN, 진양폴리 known-miss 유지. 한 테스트라도 실패 시
**데이터/명시 param** 만 조정(게이트 로직·기본값 동결). `_clean_3c_v2`가 여전히 pattern=True 인지 확인.

- [ ] **Step 6: Commit**

```bash
git add scripts/canslim_lib/cheat.py tests/test_cheat.py scripts/screen_3c.py scripts/screen_3c_history.py
git commit -m "feat(find-3c): v2c 게이트 재보정 — min_cup_days 17 + shelf_too_low_in_cup 게이트 — 오라클 GREEN"
```

---

## Task 4: 라이브·history 재실행 + 과완화 점검 + 문서 동기화

**Files:**
- Modify: `.claude/skills/find-3c/SKILL.md`, `.claude/skills/find-3c-history/SKILL.md`
- Modify: `docs/superpowers/specs/2026-06-30-find-3c-v2b-gate-tuning-design.md`(포인터)
- Modify: `docs/superpowers/notes/2026-06-30-find-3c-oracle-examples.md`(8종 결론)

- [ ] **Step 1: Re-run live (over-loosening check)**

```bash
python scripts/screen_3c.py
python -c "
import json
d=json.load(open('public/data/sepa-3c-candidates.json',encoding='utf-8'))
print('pattern', d['pattern_count'], 'dist', d['status_distribution'])
assert d['pattern_count'] <= 10, f'OVER-LOOSENED: {d[\"pattern_count\"]}'
print('OK live pattern_count <= 10')
"
```
Expected: `pattern_count` 폭증 없음(기대 0).

- [ ] **Step 2: Re-run history (V자 감소 확인)**

```bash
python scripts/screen_3c_history.py
python -c "
import json
d=json.load(open('public/data/sepa-3c-history.json',encoding='utf-8'))
evs=[e for s in d['stocks'] for e in s['events']]
low=[e for e in evs if (e.get('shelf_position_pct') or 99) < 25]
print('total events', len(evs), '| events with pos<25', len(low))
print('classes', d['summary'])
"
```
Expected: total events·pos<25 가 v2c 전(110·24)보다 줄거나(위치 게이트로 V자 이벤트 제거)
유사. pos<25 이벤트가 거의 사라지면 정상. (확정 수치는 실행 결과 그대로 보고.)

- [ ] **Step 3: Doc-sync — SKILL 2종 + spec 포인터 + 오라클 노트**

(1) `.claude/skills/find-3c/SKILL.md` "## 현재 한계 / 적용 범위 (v2b)" 절을 v2c로 갱신:
게이트 기본값(min_cup_days 17·min_shelf_position 25·max_shelf_position 90) + "오라클
8종(NU·GOOG·JBLU·AAPL·CRUS·브이엠·두산) 검증; 진양폴리류(느슨·높은 선반)는 의도적
미검출"을 반영.
(2) `.claude/skills/find-3c-history/SKILL.md` 옵션에 `--min-shelf-position` 한 줄 추가.
(3) `docs/superpowers/specs/2026-06-30-find-3c-v2b-gate-tuning-design.md` 게이트값 언급에
v2c 포인터 1줄:
```markdown
> **갱신(v2c):** min_cup_days 25→17, 신규 min_shelf_position=25(shelf_too_low_in_cup).
> 오라클 8종 기준. 근거: 2026-06-30-find-3c-v2c-gate-refinement-design.md.
```
(4) `docs/superpowers/notes/2026-06-30-find-3c-oracle-examples.md` 끝에 8종 결론 요약 추가
(JBLU·AAPL·브이엠·두산·진양폴리·휴마나 + v2c 보정 결론).

- [ ] **Step 4: Verify + commit**

```bash
python -c "t=open('.claude/skills/find-3c/SKILL.md',encoding='utf-8').read(); assert 'name: find-3c' in t; print('SKILL OK')"
python -m pytest tests/ -q 2>&1 | tail -2
git add .claude/skills/find-3c/SKILL.md .claude/skills/find-3c-history/SKILL.md docs/superpowers/specs/2026-06-30-find-3c-v2b-gate-tuning-design.md docs/superpowers/notes/2026-06-30-find-3c-oracle-examples.md
git commit -m "docs(find-3c): v2c 반영 — SKILL 2종·spec 포인터·오라클 노트(8종)"
```

---

## Self-Review (작성자 점검)

**1. Spec coverage:**
- §2.1 min_cup_days 17 → Task 3 Step 3(a). ✓
- §2.2 min_shelf_position 25 + shelf_too_low_in_cup → Task 3 Step 3(b) + 신규 단위 테스트(Task 3 Step 1-3). ✓
- §2.3 진양폴리 known-miss → Task 2 `test_oracle_jinyang_known_miss`. ✓
- §3.2 CLI 노출 → Task 3 Step 4. ✓
- §3.3 오라클 fixture+단언 → Task 1·2. ✓
- §3.4 단위 테스트 → Task 3 Step 1. ✓
- §4 과완화 방지 → Task 4 Step 1-2. ✓
- §5 문서 → Task 4 Step 3. ✓

**2. Placeholder scan:** 모든 step 에 실제 코드/명령/기대출력. 데이터 튜닝은 TDD(로직 동결 명시). ✓

**3. Type consistency:** 신규 `min_shelf_position` 키가 DEFAULT_PARAMS·evaluate_cheat·양 CLI·
test_default_params 에서 일치. `cond_shelf_pos`→`cond_shelf_pos_hi` 리네임이 if/elif 와 일치.
신규 reason `shelf_too_low_in_cup` 가 게이트 체인·단위 테스트·(필요시)스키마 reason 목록과 일치.
오라클 단언 임계값(JBLU 피벗 11~12.5·AAPL 위치80~92·브이엠 피벗20000~21500·두산 90000~105000)이
§1 컨트롤러 검증치와 정합. ✓
