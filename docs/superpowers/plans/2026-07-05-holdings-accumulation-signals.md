# 보유 종목 양면 성적표 (매집 신호 + MVP + 확장 + watch) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보유 점검(위반 축) 위에 미너비니 "매집 신호" 축(체크리스트 3종 + MVP 배지 + 확장% + 🟡 watch 등급)을 더해 양면 성적표를 만든다.

**Architecture:** 순수 판정 모듈 `sell_rules.py`에 `evaluate_accumulation`·`evaluate_mvp` 두 함수를 추가하고 소프트 케이스 2곳을 `watch`로 승격, `evaluate_holding` 반환에 `accumulation`·`mvp`·`extension_pct`를 더한다. 실행 스크립트는 무변경(결과를 그대로 직렬화). 페이지 `SepaHoldingsSection.tsx`가 배지·매집 패널·호버 툴팁·watch 마크를 렌더한다. 신호(🔴🟠🟢)·위반 개수 로직은 불변.

**Tech Stack:** Python 3(표준 라이브러리), pytest, Next.js 서버 컴포넌트(TSX, Tailwind), Markdown.

## Global Constraints

- 작업 위치: worktree `C:/Users/hanul/playground/my-stock-holdings-accum`, 브랜치 `feat/holdings-accumulation`. **다른 경로/브랜치 금지.**
- 규칙은 6개 그대로. `evaluate_holding`의 `rules` 배열 순서·인덱스 고정: [2]=consecutive_lower_lows, [5]=breakout_failure.
- `rules[].status` 허용값에 **`watch` 추가** → {violation, pass, pending, na, watch}. `violation_count`는 여전히 `status=="violation"`만 셈. 신호 우선순위 stop_loss > early_sell(violation_count≥1) > hold **불변**.
- **매집 신호·MVP·확장·watch 무엇도 `violation_count`·`signal`을 바꾸지 않는다.**
- 창: 매집 신호·MVP 모두 돌파 후 15거래일(`bi+1 … bi+15`). 매집 신호는 15일 지나면 첫 15일로 고정, 미만이면 진행 중 부분 계산. MVP는 `elapsed<15`면 전체 `pending`.
- 상수: `ACCUM_WINDOW=15`, `MVP_WINDOW=15`, `MVP_M_MIN=12`, `MVP_V_MULT=1.25`, `MVP_P_MIN=0.20`, `UP_STREAK_IDEAL=7`, `TIGHT_DAY_PCT=0.01`.
- 매집 신호 status: `met`/`unmet`/`pending`. MVP status: `yes`/`no`/`pending`.
- 페이지 시각 정본(레이아웃·툴팁·배지·watch 마크): 목업 https://claude.ai/code/artifact/9f2b4bdd-4acb-4226-aac1-c01ad6d6e82f
- 커밋 메시지 말미: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- 스펙: `docs/superpowers/specs/2026-07-05-holdings-accumulation-signals-design.md`.

---

### Task 1: 🟡 소프트 신호를 watch 상태로 승격

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (규칙③ 저거래량 저점경신 반환, 규칙⑥ 유예 반환)
- Test: `tests/test_sell_rules.py` (해당 pass 단언 3건을 watch로 갱신)

**Interfaces:**
- Produces: `rule_consecutive_lower_lows`·`rule_breakout_failure`가 소프트 케이스에서 `status:"watch"` 반환.

- [ ] **Step 1: 기존 테스트를 watch로 갱신(=먼저 실패시키기)**

`tests/test_sell_rules.py`에서 아래 3개 단언을 변경한다.
`test_rule3_pass_lower_lows_but_light_volume`의 본문에서 `== "pass"`를 `== "watch"`로:
```python
    assert r["status"] == "watch"
    assert "🟡" in r["detail"]
```
`test_rule6_pass_quiet_squat_within_grace`의 `== "pass"`를 `== "watch"`로:
```python
    assert r["status"] == "watch"
    assert "관찰중" in r["detail"]
```
`test_evaluate_holding_intraday_squat_flow`의 `r["rules"][5]["status"] == "pass"`를:
```python
    assert r["rules"][5]["status"] == "watch"
    assert "관찰중" in r["rules"][5]["detail"]
```

- [ ] **Step 2: 실패 확인**

Run: `cd C:/Users/hanul/playground/my-stock-holdings-accum && python -m pytest tests/test_sell_rules.py -k "rule3_pass_lower_lows_but_light_volume or rule6_pass_quiet_squat_within_grace or intraday_squat_flow" -v`
Expected: FAIL (현재 코드가 "pass" 반환).

- [ ] **Step 3: 구현 — 두 반환의 status 변경**

`rule_consecutive_lower_lows`의 저거래량 저점경신 반환(현재 `status:"pass"` + "🟡경고")을 watch로:
```python
    if rawmax >= LOWER_LOW_RUN:
        return {"id": rid, "status": "watch",
                "detail": f"🟡경고: 저점경신 {rawmax}회(거래량 낮음)"}
```
`rule_breakout_failure`의 유예 관찰중 반환(현재 `status:"pass"` + "🟡 반전 회복 관찰중")을 watch로:
```python
    if elapsed <= SQUAT_GRACE_DAYS:
        return {"id": rid, "status": "watch",
                "detail": f"🟡 반전 회복 관찰중 (D+{elapsed}/{SQUAT_GRACE_DAYS})"}
```
(다른 반환·"연속 저저점 없음"·"피벗 위 유지"·"반전 회복(피벗 위 복귀)"·위반 반환은 그대로.)

- [ ] **Step 4: 통과 확인 + 전체 회귀**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: 전부 PASS. (신호 테스트는 watch를 위반으로 안 세므로 hold/early_sell 불변.)

- [ ] **Step 5: 커밋**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): 🟡 소프트 신호(저거래량 저점경신·유예 스쿼트)를 watch 상태로 승격

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `evaluate_accumulation` — 매집 신호 3종

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (상수 + 새 함수)
- Test: `tests/test_sell_rules.py` (새 테스트 블록)

**Interfaces:**
- Produces: `evaluate_accumulation(series, bi) -> {"window": str, "elapsed": int, "signals": [{"id","status","detail"} × 3]}`. id = `up_days_dominant`/`quality_closes`/`up_streak_7`. status ∈ met/unmet/pending.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_sell_rules.py` 하단에 추가(import는 파일 상단 `from canslim_lib.sell_rules import ...`에 `evaluate_accumulation` 추가):
```python
from canslim_lib.sell_rules import evaluate_accumulation


def test_accum_up_days_and_quality_met():
    # 돌파(30) 후 상승 우세 + 상단 마감 우세
    closes = [100.0] * 31 + [102.0, 104.0, 103.5, 106.0]
    highs = [c * 1.005 for c in closes]           # 종가가 고저 중간보다 위(좋은 마감)
    lows = [c * 0.98 for c in closes]
    s = make_series(closes, highs=highs, lows=lows)
    r = evaluate_accumulation(s, 30)
    ids = {x["id"]: x["status"] for x in r["signals"]}
    assert ids["up_days_dominant"] == "met"       # 상승 3 · 하락 1
    assert ids["quality_closes"] == "met"
    assert r["elapsed"] == 4 and r["window"] == "D+4/15"


def test_accum_up_streak_7_met_and_window_locks_at_15():
    # 돌파 후 8일 연속 상승 → streak met, 16일 이상이면 창 고정("15일 완료")
    closes = [100.0] * 31 + [100.0 + i for i in range(1, 20)]
    s = make_series(closes)
    r = evaluate_accumulation(s, 30)
    ids = {x["id"]: x["status"] for x in r["signals"]}
    assert ids["up_streak_7"] == "met"
    assert r["window"] == "15일 완료"


def test_accum_pending_when_no_post_breakout_days():
    s = make_series([100.0] * 31)
    r = evaluate_accumulation(s, 30)
    assert all(x["status"] == "pending" for x in r["signals"])


def test_accum_tight_day_not_counted_as_bad_close():
    # 하단 마감이지만 일중 변동폭 <1% (tight) → 나쁜 마감서 제외
    closes = [100.0] * 31 + [101.0, 101.05, 101.1]
    highs = [c * 1.0002 for c in closes]          # 범위 ~0.02% < 1%
    lows = [c * 0.9998 for c in closes]
    s = make_series(closes, highs=highs, lows=lows)
    r = evaluate_accumulation(s, 30)
    q = next(x for x in r["signals"] if x["id"] == "quality_closes")
    assert "나쁜 0" in q["detail"]                 # tight day는 bad 미포함
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py -k accum -v`
Expected: FAIL (`ImportError: cannot import name 'evaluate_accumulation'`).

- [ ] **Step 3: 구현**

`sell_rules.py` 상수 블록에 추가:
```python
ACCUM_WINDOW = 15           # 매집 신호·MVP 관찰 창(거래일)
UP_STREAK_IDEAL = 7         # 연속 상승 이상적 기준(미너비니)
TIGHT_DAY_PCT = 0.01        # 일중 변동폭 <1% = tight day(나쁜 마감 제외)
```
새 함수 추가(파일 하단, `evaluate_holding` 앞):
```python
def evaluate_accumulation(series, bi):
    """돌파 후 첫 ACCUM_WINDOW 거래일 매집 신호 3종(등급 없이 체크리스트).
    창은 15일 지나면 첫 15일로 고정, 미만이면 진행 중 부분 계산."""
    closes, highs, lows = series["closes"], series["highs"], series["lows"]
    n = len(closes)
    elapsed = (n - 1) - bi
    end = min(bi + ACCUM_WINDOW, n - 1)          # 첫 15일로 고정
    has_days = end >= bi + 1
    window = f"{ACCUM_WINDOW}일 완료" if elapsed >= ACCUM_WINDOW else f"D+{max(elapsed,0)}/{ACCUM_WINDOW}"
    up = down = good = bad = 0
    streak = max_streak = 0
    for i in range(bi + 1, end + 1):
        if closes[i] > closes[i - 1]:
            up += 1; streak += 1; max_streak = max(max_streak, streak)
        elif closes[i] < closes[i - 1]:
            down += 1; streak = 0
        else:
            streak = 0
        rng = highs[i] - lows[i]
        if rng > 0 and closes[i] and (rng / closes[i]) >= TIGHT_DAY_PCT:
            mid = (highs[i] + lows[i]) / 2
            if closes[i] > mid:
                good += 1
            elif closes[i] < mid:
                bad += 1

    def st(cond, data_ok):
        return "met" if cond else ("unmet" if data_ok else "pending")

    signals = [
        {"id": "up_days_dominant", "status": st(up > down, up + down > 0),
         "detail": f"상승 {up} · 하락 {down}"},
        {"id": "quality_closes", "status": st(good > bad, good + bad > 0),
         "detail": f"좋은 {good} · 나쁜 {bad}"},
        {"id": "up_streak_7",
         "status": ("met" if max_streak >= UP_STREAK_IDEAL else ("unmet" if has_days else "pending")),
         "detail": f"최고 {max_streak}일"},
    ]
    return {"window": window, "elapsed": elapsed, "signals": signals}
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -k accum -v`
Expected: PASS (4개).

- [ ] **Step 5: 커밋**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): evaluate_accumulation — 매집 신호 3종(상승우세·양질종가·연속7일)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `evaluate_mvp` — M·V·P 감별

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (상수 + 새 함수)
- Test: `tests/test_sell_rules.py` (새 테스트 블록)

**Interfaces:**
- Produces: `evaluate_mvp(series, bi) -> {"status": "yes"|"no"|"pending", "m": {"ok","detail"}, "v": {...}, "p": {...}}`. ok ∈ {True, False, None}.

- [ ] **Step 1: 실패 테스트 작성**

import에 `evaluate_mvp` 추가 후:
```python
from canslim_lib.sell_rules import evaluate_mvp


def _mvp_series():
    # 직전 15일 거래량 1000, 돌파 후 15일: 12일 상승 + 거래량 2000(2배) + 최고 종가 +25%
    pre = [100.0] * 16                     # index 0..15 (bi=15)
    post_up = [100.0 + 2 * (i + 1) for i in range(12)]   # 12일 상승 → 최고 +24~
    post = post_up + [post_up[-1] - 1, post_up[-1] - 2, post_up[-1] + 3]  # 3일 혼합, 마지막 신고가
    closes = pre + post
    vols = [1000.0] * 16 + [2000.0] * 15
    return make_series(closes, volumes=vols), 15


def test_mvp_yes_when_all_three_met():
    s, bi = _mvp_series()
    r = evaluate_mvp(s, bi)
    assert r["status"] == "yes"
    assert r["m"]["ok"] and r["v"]["ok"] and r["p"]["ok"]


def test_mvp_pending_before_15_days():
    closes = [100.0] * 16 + [101.0, 102.0, 103.0]   # bi=15, 경과 3일
    s = make_series(closes)
    r = evaluate_mvp(s, 15)
    assert r["status"] == "pending"
    assert r["m"]["ok"] is None


def test_mvp_no_when_price_short():
    # M·V 충족해도 P<20%면 no
    pre = [100.0] * 16
    post = [100.0 + 0.5 * (i + 1) for i in range(15)]   # 최고 +7.5%
    s = make_series(pre + post, volumes=[1000.0] * 16 + [2000.0] * 15)
    r = evaluate_mvp(s, 15)
    assert r["status"] == "no"
    assert r["p"]["ok"] is False
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py -k mvp -v`
Expected: FAIL (`ImportError: cannot import name 'evaluate_mvp'`).

- [ ] **Step 3: 구현**

`sell_rules.py` 상수 블록에 추가:
```python
MVP_M_MIN = 12              # M: 15일 중 상승 마감 최소일
MVP_V_MULT = 1.25           # V: 창 평균 거래량 / 직전 15일 평균 최소배
MVP_P_MIN = 0.20            # P: 창 최고 종가 상승률 최소
```
새 함수 추가(`evaluate_accumulation` 뒤):
```python
def evaluate_mvp(series, bi):
    """돌파 후 ACCUM_WINDOW 거래일 MVP(M·V·P). 15일 미경과면 전체 pending."""
    closes, vols = series["closes"], series["volumes"]
    n = len(closes)
    elapsed = (n - 1) - bi
    end = min(bi + ACCUM_WINDOW, n - 1)
    win_closes = closes[bi + 1:end + 1]
    p_gain = (max(win_closes) / closes[bi] - 1) if (win_closes and closes[bi]) else None
    p_detail = f"+{p_gain * 100:.0f}%" if p_gain is not None else "—"
    if elapsed < ACCUM_WINDOW:
        return {"status": "pending",
                "m": {"ok": None, "detail": f"{max(elapsed, 0)}/{ACCUM_WINDOW}일 (판정 전)"},
                "v": {"ok": None, "detail": "판정 전"},
                "p": {"ok": None, "detail": p_detail}}
    w = range(bi + 1, bi + ACCUM_WINDOW + 1)     # 확정 15일 창
    up = sum(1 for i in w if closes[i] > closes[i - 1])
    m_ok = up >= MVP_M_MIN
    win_vol = [vols[i] for i in w if vols[i] is not None]
    prior = [vols[i] for i in range(max(0, bi - ACCUM_WINDOW), bi) if vols[i] is not None]
    if len(prior) >= 5 and win_vol:
        v_ratio = (sum(win_vol) / len(win_vol)) / (sum(prior) / len(prior))
        v_ok = v_ratio >= MVP_V_MULT
        v_detail = f"직전 대비 {v_ratio:.1f}배"
    else:
        v_ok, v_detail = None, "거래량 표본 부족"
    p_ok = (p_gain is not None) and (p_gain >= MVP_P_MIN)
    status = "yes" if (m_ok and v_ok and p_ok) else "no"
    return {"status": status,
            "m": {"ok": m_ok, "detail": f"{up}/{ACCUM_WINDOW}일 상승"},
            "v": {"ok": v_ok, "detail": v_detail},
            "p": {"ok": p_ok, "detail": p_detail}}
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/test_sell_rules.py -k mvp -v`
Expected: PASS (3개).

- [ ] **Step 5: 커밋**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): evaluate_mvp — M(12/15)·V(직전×1.25)·P(+20%) 감별

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `evaluate_holding` 배선 + `extension_pct`

**Files:**
- Modify: `scripts/canslim_lib/sell_rules.py` (`evaluate_holding` 반환)
- Test: `tests/test_sell_rules.py`

**Interfaces:**
- Consumes: `evaluate_accumulation`, `evaluate_mvp`(Task 2·3).
- Produces: `evaluate_holding(...)` 반환 dict에 `"extension_pct"`(float|None), `"accumulation"`(dict), `"mvp"`(dict) 추가. 기존 키·signal·violation_count 불변.

- [ ] **Step 1: 실패 테스트 작성**
```python
def test_evaluate_holding_adds_accumulation_mvp_extension():
    s = _clean_series()   # 대량 돌파 후 얕은 상승(위반 없음)
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    assert "accumulation" in r and "signals" in r["accumulation"]
    assert r["mvp"]["status"] in ("yes", "no", "pending")
    # 현재가 108, 피벗 105 → 확장 +2.9%
    assert r["extension_pct"] == round((108.0 / 105.0 - 1) * 100, 1)
    # 신호·위반 개수는 불변(추가 필드가 영향 없음)
    assert r["signal"] == "hold" and r["violation_count"] == 0


def test_evaluate_holding_extension_null_without_pivot():
    s = _clean_series()
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=None)
    assert r["extension_pct"] is None
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_sell_rules.py -k "adds_accumulation_mvp_extension or extension_null" -v`
Expected: FAIL (KeyError: 'accumulation').

- [ ] **Step 3: 구현 — 반환에 3필드 추가**

`evaluate_holding`에서 `violation_count = ...` 계산 뒤, return 직전에 추가:
```python
    accumulation = evaluate_accumulation(series, bi)
    mvp = evaluate_mvp(series, bi)
    extension_pct = (round((current / pivot_price - 1) * 100, 1)
                     if pivot_price else None)
```
그리고 return dict 끝에 세 키 추가(기존 키 유지):
```python
        "rules": rules,
        "extension_pct": extension_pct,
        "accumulation": accumulation,
        "mvp": mvp,
    }
```

- [ ] **Step 4: 통과 + 전체 회귀**

Run: `python -m pytest tests/test_sell_rules.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 커밋**

```bash
git add scripts/canslim_lib/sell_rules.py tests/test_sell_rules.py
git commit -m "feat(sell-rules): evaluate_holding 반환에 accumulation·mvp·extension_pct 배선(신호 불변)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: MVP 실 winner 오라클(실데이터 확신 테스트)

**Files:**
- Create: `tests/fixtures/oracle_mvp_winner.json`
- Modify: `tests/test_sell_rules_oracle.py`

**Interfaces:**
- Consumes: `evaluate_mvp`, `find_breakout_index`.

- [ ] **Step 1: 실 winner에서 MVP 창 찾아 픽스처 생성**

로컬 OHLCV 캐시에서 강한 급등 이력이 있는 한국 종목의 일봉으로 "돌파 후 15일 M·V·P 충족" 구간을 찾는다. 아래 스크립트를 스크래치에 저장 후 실행(메인 캐시 읽기 전용):
```python
import json, sys
from pathlib import Path
REPO = Path(r"C:/Users/hanul/playground/my-stock-holdings-accum")
sys.path.insert(0, str(REPO / "scripts"))
from canslim_lib.sell_rules import evaluate_mvp, find_breakout_index
import importlib.util
spec = importlib.util.spec_from_file_location("om", REPO/"scripts/canslim_lib/ohlcv_matrix.py")
# 메인 dir 캐시 사용: 필요한 종목 series 를 미리 복사해 둔다(아래 참고).
CANDS = ["019170", "096530", "247540", "091990", "066970"]  # 신풍제약·씨젠·에코프로비엠·셀트리온헬스케어·엘앤에프
from canslim_lib import ohlcv_matrix
for code in CANDS:
    s = ohlcv_matrix.get_series(code)
    if not s: 
        print(code, "no series"); continue
    dates, closes = s["dates"], s["closes"]
    # 각 날을 돌파일로 가정하고 그 뒤 15일 MVP 판정 — yes 나오는 첫 구간을 스냅샷
    for bi in range(60, len(dates) - 16):
        sub = {k: v[:bi + 16] for k, v in s.items()}
        r = evaluate_mvp(sub, bi)
        if r["status"] == "yes":
            lo = max(0, bi - 20)
            fix = {k: s[k][lo:bi + 16] for k in ("dates", "opens", "highs", "lows", "closes", "volumes")}
            (REPO/"tests/fixtures/oracle_mvp_winner.json").write_text(
                json.dumps({"code": code, "bi_in_fixture": bi - lo, **fix}, ensure_ascii=False), encoding="utf-8")
            print("MVP winner:", code, dates[bi], "→", r); sys.exit(0)
print("no MVP window found in candidates")
```
캐시 준비(메인 dir → worktree, 읽기 전용 복사):
```bash
MAIN="C:/Users/hanul/playground/my-stock/.cache/ohlcv"; WT="C:/Users/hanul/playground/my-stock-holdings-accum/.cache/ohlcv"
mkdir -p "$WT/series"; for c in 019170 096530 247540 091990 066970; do cp "$MAIN/series/$c.json" "$WT/series/" 2>/dev/null; done; cp "$MAIN/foreign.json" "$WT/" 2>/dev/null; echo done
```
Run: 스크립트 실행 → `MVP winner: <code> <date>` 출력 + `tests/fixtures/oracle_mvp_winner.json` 생성.
**만약 후보 5종 모두 실패**하면(캐시에 없음/구간 없음): 후보를 몇 개 더 넣어 재시도하되, 15분 내 못 찾으면 **이 태스크를 건너뛰고 그 사실을 보고**한다(합성 테스트 Task 3이 정확성 게이트 — 실 오라클은 확신 보강용).

- [ ] **Step 2: 오라클 테스트 작성**

`tests/test_sell_rules_oracle.py`에 추가:
```python
def test_mvp_real_winner_qualifies():
    p = FIX / "oracle_mvp_winner.json"
    if not p.exists():
        import pytest
        pytest.skip("MVP winner fixture 미생성(캐시 부재) — 합성 테스트로 커버")
    from canslim_lib.sell_rules import evaluate_mvp
    d = json.loads(p.read_text(encoding="utf-8"))
    r = evaluate_mvp(d, d["bi_in_fixture"])
    assert r["status"] == "yes"
    assert r["m"]["ok"] and r["v"]["ok"] and r["p"]["ok"]
```

- [ ] **Step 3: 실행**

Run: `python -m pytest tests/test_sell_rules_oracle.py -v`
Expected: PASS(픽스처 있으면 검증, 없으면 skip).

- [ ] **Step 4: 커밋**

```bash
git add tests/test_sell_rules_oracle.py tests/fixtures/oracle_mvp_winner.json
git commit -m "test(sell-rules): MVP 실 winner 오라클(있으면 검증, 없으면 skip)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: 페이지 — 타입 + watch 마크 + MVP/확장 배지

**Files:**
- Modify: `src/app/stocks/sepa/SepaHoldingsSection.tsx`

**Interfaces:**
- Consumes: JSON 필드 `extension_pct`·`accumulation`·`mvp`·`rules[].status:"watch"`(Task 1·4 산출).
- Produces: 배지 렌더 + 확장된 타입(Task 7이 매집 패널에서 `AccumulationSignal`·`Mvp` 타입 사용).

- [ ] **Step 1: 타입 확장 + watch 마크 + 배지 추가**

`HoldingRule.status` 유니온에 `"watch"` 추가:
```tsx
export interface HoldingRule {
  id: string;
  status: "violation" | "pass" | "pending" | "na" | "watch";
  detail: string;
}
```
`HoldingFeedback` 인터페이스에 세 필드 + 보조 타입 추가(파일 상단 인터페이스 영역):
```tsx
export interface AccumulationSignal { id: string; status: "met" | "unmet" | "pending"; detail: string; }
export interface Accumulation { window: string; elapsed: number; signals: AccumulationSignal[]; }
export interface MvpCheck { ok: boolean | null; detail: string; }
export interface Mvp { status: "yes" | "no" | "pending"; m: MvpCheck; v: MvpCheck; p: MvpCheck; }
```
`HoldingFeedback`에 추가:
```tsx
  extension_pct?: number | null;
  accumulation?: Accumulation;
  mvp?: Mvp;
```
`STATUS_MARK`에 watch 추가:
```tsx
  watch: { mark: "🟡", cls: "text-[#fbbf24]" },
```
badges 영역(신호 배지 `<span … >{badgeLabel}</span>` 바로 뒤, 같은 부모 안)에 MVP 배지 + 확장 칩 추가:
```tsx
              {h.mvp?.status === "yes" && (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded tracking-wide"
                  style={{ backgroundColor: "rgba(167,139,250,0.16)", color: "#a78bfa",
                           border: "1px solid rgba(167,139,250,0.42)" }}>MVP</span>
              )}
              {h.extension_pct != null && (
                <span className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                  style={{ backgroundColor: "rgba(148,163,184,0.12)", color: "#94a3b8" }}>
                  확장 {h.extension_pct > 0 ? "+" : ""}{h.extension_pct}%
                </span>
              )}
```
(신호 배지가 홀로 오른쪽에 있던 구조라면, 신호 배지와 이 둘을 `flex flex-wrap gap-1.5 justify-end` 컨테이너로 감싼다.)

- [ ] **Step 2: 타입체크**

Run: `cd C:/Users/hanul/playground/my-stock-holdings-accum && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -i "SepaHoldingsSection" || echo "이 파일 신규 오류 없음"`
Expected: `이 파일 신규 오류 없음`. (무관 파일의 기존 오류는 무시.)

- [ ] **Step 3: 커밋**

```bash
git add src/app/stocks/sepa/SepaHoldingsSection.tsx
git commit -m "feat(sepa-page): 보유 카드에 watch(🟡) 마크 + MVP 배지 + 확장% 칩

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: 페이지 — 매집 신호 패널 + 호버 툴팁

**Files:**
- Modify: `src/app/stocks/sepa/SepaHoldingsSection.tsx`

**Interfaces:**
- Consumes: `Accumulation`·`Mvp` 타입 + 데이터(Task 6).

- [ ] **Step 1: 툴팁 헬퍼 + 라벨/설명 맵 + 매집 패널 추가**

파일 상단(컴포넌트 밖)에 설명 맵과 마크 맵 추가:
```tsx
const ACC_MARK: Record<AccumulationSignal["status"], { mark: string; cls: string }> = {
  met: { mark: "✓", cls: "text-[#34d399]" },
  unmet: { mark: "○", cls: "text-on-surface-variant/50" },
  pending: { mark: "―", cls: "text-on-surface-variant/40" },
};
const ACC_META: Record<string, { label: string; tip: string }> = {
  up_days_dominant: { label: "상승일 우세", tip: "돌파 후 15거래일 중 상승 마감일이 하락 마감일보다 많으면 충족. 기관 매집 정황. 숫자 = 상승 · 하락 마감일." },
  quality_closes: { label: "양질의 종가", tip: "그날 고저 범위의 상단 절반에서 마감(좋은 마감)한 날이 하단 절반 마감(나쁜 마감)보다 많으면 충족. 변동폭 1% 미만 tight 눌림은 나쁜 마감서 제외." },
  up_streak_7: { label: "연속 상승 7일↑", tip: "상승 마감이 며칠 연속됐는지의 최고 기록. 7~8일 이상을 미너비니는 가장 이상적 신호로 봄." },
};
const MVP_META = {
  m: { label: "M 모멘텀", tip: "돌파 후 15일 중 상승 마감이 12일 이상이면 충족." },
  v: { label: "V 거래량", tip: "돌파 후 15일 평균 거래량이 돌파 직전 15일 평균 대비 25% 이상 늘면 충족." },
  p: { label: "P 가격", tip: "돌파 후 15일간 최고 종가가 돌파일 종가 대비 20% 이상 오르면 충족." },
} as const;
```
컴포넌트 함수 안, 반환 JSX 밖에 툴팁·행 헬퍼 추가:
```tsx
  const Tip = ({ tip, children }: { tip: string; children: React.ReactNode }) => (
    <span className="relative group cursor-help outline-none" tabIndex={0}>
      <span className="border-b border-dotted border-on-surface-variant/40">{children}</span>
      <span role="tooltip"
        className="pointer-events-none absolute left-0 bottom-full mb-2 w-56 max-w-[74vw] z-30
                   rounded-lg border border-outline-variant/30 bg-surface-container p-2.5 text-[11px]
                   font-normal leading-relaxed text-on-surface shadow-lg opacity-0 invisible
                   transition-opacity group-hover:opacity-100 group-hover:visible group-focus:opacity-100 group-focus:visible">
        {tip}
      </span>
    </span>
  );
  const mvpMark = (ok: boolean | null) =>
    ok === true ? ACC_MARK.met : ok === false ? ACC_MARK.unmet : ACC_MARK.pending;
```
그리고 rules `<ul>` **바로 앞**에 매집 신호 패널을 삽입(카드 `<div>` 안, pnl 블록과 rules 사이):
```tsx
              {h.accumulation && (
                <div className="pt-2 border-t border-outline-variant/10">
                  <div className="text-[10px] font-bold tracking-wider text-on-surface-variant/50 mb-1.5 uppercase">
                    매집 신호 <span className="font-normal normal-case text-on-surface-variant/70">· {h.accumulation.window}{h.accumulation.elapsed < 15 ? " 진행중" : ""}</span>
                  </div>
                  <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                    {h.accumulation.signals.map((sg) => {
                      const m = ACC_MARK[sg.status]; const meta = ACC_META[sg.id];
                      return (
                        <li key={sg.id} className="flex gap-1.5 leading-relaxed">
                          <span className={`${m.cls} font-bold shrink-0`}>{m.mark}</span>
                          <span className="text-on-surface-variant">
                            <Tip tip={meta?.tip ?? ""}><span className="text-on-surface">{meta?.label ?? sg.id}</span></Tip>{" "}
                            <span className="text-on-surface-variant/70">{sg.detail}</span>
                          </span>
                        </li>
                      );
                    })}
                    {h.mvp && (["m", "v", "p"] as const).map((k) => {
                      const c = h.mvp![k]; const mk = mvpMark(c.ok); const meta = MVP_META[k];
                      return (
                        <li key={k} className="flex gap-1.5 leading-relaxed">
                          <span className={`${mk.cls} font-bold shrink-0`}>{mk.mark}</span>
                          <span className="text-on-surface-variant">
                            <Tip tip={meta.tip}><span className="text-on-surface">{meta.label}</span></Tip>{" "}
                            <span className="text-on-surface-variant/70">{c.detail}</span>
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
```
(`import React from "react";`가 없으면 `React.ReactNode` 대신 파일 상단에 `import type { ReactNode } from "react";` 후 `ReactNode` 사용. 컴포넌트는 서버 컴포넌트이므로 상태/이벤트 없이 CSS-only 툴팁만 사용.)

- [ ] **Step 2: 타입체크**

Run: `npx tsc --noEmit -p tsconfig.json 2>&1 | grep -i "SepaHoldingsSection" || echo "이 파일 신규 오류 없음"`
Expected: `이 파일 신규 오류 없음`.

- [ ] **Step 3: 커밋**

```bash
git add src/app/stocks/sepa/SepaHoldingsSection.tsx
git commit -m "feat(sepa-page): 매집 신호 패널(체크리스트+MVP 3종) + 호버 툴팁

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: 통합 검증 (전체 pytest + 실 4종목 + 페이지 tsc)

**Files:** 없음(검증). 산출 `sepa-holdings-feedback.json` 갱신 커밋 가능.

- [ ] **Step 1: 전체 파이썬 테스트**

Run: `cd C:/Users/hanul/playground/my-stock-holdings-accum && python -m pytest tests/test_sell_rules.py tests/test_sell_rules_oracle.py -v`
Expected: 전부 PASS(오라클은 skip 가능).

- [ ] **Step 2: 실 4종목 스크립트 실행(캐시 복사 후)**

```bash
MAIN="C:/Users/hanul/playground/my-stock/.cache/ohlcv"; WT="C:/Users/hanul/playground/my-stock-holdings-accum/.cache/ohlcv"
mkdir -p "$WT/series"; for c in 036800 271560 010955 005430; do cp "$MAIN/series/$c.json" "$WT/series/"; done; cp "$MAIN/foreign.json" "$WT/"
cd C:/Users/hanul/playground/my-stock-holdings-accum && python scripts/screen_holdings_feedback.py
```
Expected: 콘솔에 4종목 신호. (캐시 없으면 no_data — 그 경우 update-data 필요라고 보고.)

- [ ] **Step 3: 산출 JSON에 새 필드 확인**

Run: `python -c "import json;d=json.load(open('public/data/sepa-holdings-feedback.json',encoding='utf-8'));h=d['holdings'][0] if d['holdings'] else {};print('keys:', [k for k in ('accumulation','mvp','extension_pct') if k in h]);print('acc ids:', [s['id'] for s in h.get('accumulation',{}).get('signals',[])]);print('mvp:', h.get('mvp',{}).get('status'))"`
Expected: `keys: ['accumulation', 'mvp', 'extension_pct']`, acc ids 3개, mvp status.

- [ ] **Step 4: 페이지 타입체크**

Run: `npx tsc --noEmit -p tsconfig.json 2>&1 | grep -i "SepaHoldingsSection" || echo "페이지 신규 오류 없음"`
Expected: `페이지 신규 오류 없음`.

- [ ] **Step 5: 산출물 커밋(실행됐다면) + 완료 보고**

```bash
git add public/data/sepa-holdings-feedback.json
git commit -m "chore(holdings): 매집 신호·MVP·확장 필드로 보유 점검 결과 갱신

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
`git log --oneline` + 테스트 결과 요약 보고. 통합(머지/PR)은 사용자와 별도 결정.

---

## 자체 검토

- **스펙 커버리지**: watch 승격→Task1, 매집 신호→Task2, MVP→Task3, 배선/확장→Task4, 실 오라클→Task5, 배지/타입/watch 마크→Task6, 매집 패널/툴팁→Task7, 검증→Task8. 누락 없음.
- **플레이스홀더**: 없음(모든 코드/명령 기재). Task5는 실 데이터 탐색이라 후보·폴백을 명시.
- **타입/이름 일치**: `evaluate_accumulation`/`evaluate_mvp` 반환 키(window/elapsed/signals, status/m/v/p, ok/detail)가 Task2·3·4(파이썬)와 Task6·7(TSX 인터페이스 AccumulationSignal/Accumulation/Mvp/MvpCheck)에서 일치. status 값(met/unmet/pending, yes/no/pending, watch) 일관. 상수(ACCUM_WINDOW=15 등) 일관.
