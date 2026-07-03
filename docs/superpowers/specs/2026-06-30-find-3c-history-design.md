# find-3c-history — 3C 검출기 회고·검증 도구 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인됨, 구현 계획 대기
형제: `find-vcp-history`(`2026-06-29-find-vcp-history-design.md`)의 충실한 미러.

## 1. 배경·목적

`find-3c`(SEPA 패턴)는 "지금 기준" 3C만 본다. 그래서 현재 트렌드 통과 종목 70개는
대부분 *조정 없이 오른 신고가 부근 모멘텀 리더*라 `no_overhead_cup`/`cup_too_short`
로 평가돼 `pattern_count=0` 이다(v2b 검증 결과). 하지만 **그 리더들도 상승의
출발점(과거 어느 시점)에선 조정 후 회복하며 3C(컵 완성 치트)를 만들었을 가능성**이
크다. 이 도구는 그 종목들의 **과거 1년을 매 거래일 되짚어**, 우리 `evaluate_cheat`
가 그 역사 속 **"3C 완성 → 돌파" 시점을 짚어내는지** 보여준다.

**1순위 목적 = 검증.** 알고리즘이 찍은 돌파 날짜를 사용자가 차트로 열어 "진짜
3C였나"를 눈으로 대조한다. **부산물 = 분류**(이미 돌파·연장됐는지 등) + 한국 3C
사례 발굴(사용자 통찰: 한국 3C는 과거 조정·상승장 초입에 있다).

핵심 설계: `evaluate_cheat(series)`는 시계열의 *마지막 날* 기준으로 판정하므로,
**시계열을 과거 날짜 D에서 잘라 넣으면 "D 시점 판정"이 그대로 재현된다.** 새 평가
로직 없이 **기존 `evaluate_cheat`(v2b 보정본) 재사용**(as-of 리플레이).

## 2. 범위

### 하는 것
- 입력 기본 = `sepa-3c-candidates.json`의 종목 전체(현재 70). `--codes 005930,000660`
  이면 임의 지정.
- 각 종목의 OHLCV 캐시로 최근 `scan_days`(기본 250)영업일을 매일 as-of 리플레이.
- "3C→돌파" 이벤트 추출 + 돌파 후 결과 측정 + 종목 분류.
- 산출 `public/data/sepa-3c-history.json` + 콘솔 표.

### 안 하는 것
- 임계값 자동 최적화/튜닝 — *현재 검출기(v2b)를 그대로 과거에 적용*만.
- 실거래·손절·비중 신호 — 검증/회고 전용.
- 수급·공유 파일 갱신·자동 commit.
- 캐시 전체(3028) 광역 스캔 — 이번 기본은 find-3c 후보 70종(RS 필터 유지). 광역은
  후속(§9).

## 3. 데이터 입력
- OHLCV 캐시 `.cache/ohlcv/series/<code>.json`(수정주가, ~400영업일). `update-data` 선행 권장.
- 대상 코드 목록: §2 입력 규칙.
- 250영업일을 as-of로 쓰려면 각 D 이전에 lookback(250)이 있어야 하므로 캐시가 길수록
  좋다. 부족하면 가능한 만큼만 스캔하고 짧은 슬라이스는 자연 처리(base_too_short 등).

## 4. 알고리즘 (find-vcp-history 미러, evaluate_cheat 사용)

### 4.1 as-of 리플레이 (`replay_cheat`)
- `dates = series["dates"]`. 스캔 구간 = 마지막 `scan_days`(기본 250) 거래일의 인덱스.
- 각 as-of 인덱스 i에 대해 시계열을 `[:i+1]`로 잘라 `evaluate_cheat(잘린 series, params)` 호출.
- 기록: `{date, pattern_detected, status, pivot_price, cup_depth_pct, shelf_position_pct}`
  리스트(시간순). (vcp의 `contractions` 자리에 3C 기하 = 컵깊이·선반위치.)
- `evaluate_cheat`가 내부에서 마지막 `lookback_days`만 보므로 잘린 길이가 짧아도 안전.

### 4.2 돌파 이벤트 탐지 (`find_breakout_events`)
as-of 리플레이를 시간순으로 훑어, 다음을 만족하는 날 D를 **돌파 이벤트**로 본다:
1. `status(D) == "breakout"`,
2. `status(D-1) != "breakout"` (새 전환 — 같은 돌파 중복 카운트 방지),
3. 직전 `confirm_lookback`(기본 5거래일) 안에 `pattern_detected == true`였던 날이
   하나라도 있음 (= 돌파 직전에 진짜 3C 치트 베이스가 확인됐다).
- 이벤트 근거 캡처: `date`, `replay_idx`, **확인일(직전 pattern_detected=true였던 가장
  가까운 날)의** `confirm_date`·`pivot_price`·`cup_depth_pct`·`shelf_position_pct`.

### 4.3 돌파 후 결과 (`post_breakout_outcome`) — find-vcp-history와 동일
이벤트 날짜 이후 바들로 측정:
- `breakout_close`(돌파일 종가), `days_since`(이벤트~마지막일 거래일 수),
- `gain_since_pct` = `(마지막 종가 − breakout_close)/breakout_close*100`,
- `max_gain_pct` = 이벤트 이후 `max(high)` 기준 최대 상승 %,
- `max_drawdown_pct` = 이벤트 이후 종가 기준 최저 하락 %(음수),
- `good_breakout` = 손절(intrabar low ≤ −`stop_pct`)에 닿기 *전에* 목표(intrabar
  high ≥ +`target_pct`)에 도달하면 true(같은 바면 손절 우선·보수적).

### 4.4 종목 분류 (`classify`) — 우선순위 순
- 이벤트 0개 → **`no_3c_found`** (검출기 미스 의심 또는 진짜 패턴 없음).
- 가장 최근 이벤트(`replay_idx`) 기준 `days_since = (len(replay)−1) − idx`:
  1. `days_since <= recent_days`(기본 10) → **`recent_breakout`**.
  2. 그 이벤트 *이후* 리플레이에서 `pattern_detected==true`가 다시 나타났고 마지막
     status가 forming/actionable → **`re_basing`** (돌파 후 2차 치트 베이스).
  3. 그 외 → **`extended`** (예전에 돌파·상승, 지금 한참 위 = 추격 늦음).

### 4.5 집계 (참고용, 생존자 편향 경고)
- `n_with_events`, `n_no_3c_found`, `total_events`.
- 이벤트 전체의 `gain_since_pct`·`max_gain_pct` 중앙값, `good_breakout` 비율.
- **출력·콘솔에 명시 딱지**: "⚠️ 이 집계는 RS 상위 트렌드 통과 종목(승자)만 본
  결과라 생존자 편향으로 과대평가됨. 검출기 신뢰의 *보조 지표*일 뿐, 결정적 검증은
  이벤트 날짜를 차트로 눈 대조하는 것." ([[doppelganger-survivor-bias]]·
  [[equity-curve-hindsight-pivot]] 메모리 정신과 일치.)

## 5. 출력 스키마
`public/data/sepa-3c-history.json`:
```jsonc
{
  "generated_at": "2026-06-30 22:00",
  "asof": "2026-06-30",
  "source": "sepa-3c-candidates.json",
  "input_filter": "all",                    // 또는 "codes"
  "scan_days": 250,
  "params": { "min_shelf_days": 2, "max_shelf_position": 90, "min_cup_days": 25,
              "lookback_days": 250, "confirm_lookback": 5, "recent_days": 10,
              "stop_pct": 8, "target_pct": 20 },
  "caveat": "집계 수익률은 생존자 편향으로 과대 — 보조 지표. 결정적 검증은 차트 눈 대조.",
  "summary": {
    "n_stocks": 70, "n_with_events": 0, "n_no_3c_found": 0, "total_events": 0,
    "agg": { "median_gain_since_pct": null, "median_max_gain_pct": null, "good_breakout_rate": null }
  },
  "stocks": [
    {
      "code": "...", "name": "...", "market": "KOSDAQ", "rs": 95,
      "classification": "extended",
      "num_events": 1,
      "most_recent_event_date": "2026-02-10",
      "events": [
        { "date": "2026-02-10", "confirm_date": "2026-02-07",
          "pivot_price": 0, "cup_depth_pct": 23.5, "shelf_position_pct": 58.0,
          "breakout_close": 0, "days_since": 90, "gain_since_pct": 0,
          "max_gain_pct": 0, "max_drawdown_pct": 0, "good_breakout": true }
      ]
    },
    {
      "code": "...", "name": "...", "market": "KOSPI", "rs": 88,
      "classification": "no_3c_found",
      "num_events": 0, "most_recent_event_date": null, "events": [],
      "reason": "no_series"
    }
  ]
}
```
- no-series(시세 없음) 종목은 이벤트 없이 `classification: "no_3c_found"` +
  `"reason": "no_series"` 키 추가.
- `stocks`는 입력 종목 전부 포함(이벤트 없으면 `no_3c_found`·events []).
- 정렬: `classification`(re_basing → recent_breakout → extended → no_3c_found) → rs 내림차순.

## 6. 구성 요소
- **`scripts/canslim_lib/cheat_history.py`** (순수, 단위 테스트 가능):
  `replay_cheat(series, scan_days, params) -> list[dict]`,
  `find_breakout_events(replay, confirm_lookback) -> list[dict]`,
  `post_breakout_outcome(series, event_date, stop_pct=8.0, target_pct=20.0) -> dict | None`,
  `classify(events, replay, recent_days) -> str`.
  `evaluate_cheat`(기존 v2b)만 호출, 새 판정 로직 없음.
- **`scripts/screen_3c_history.py`** — CLI: 입력 코드 결정 → 종목별 위 4단계 →
  JSON 저장 + 콘솔 표(종목별 분류·최근 이벤트, 끝에 집계+딱지).
- 산출: `public/data/sepa-3c-history.json`.
- **`.claude/skills/find-3c-history/SKILL.md`**.

### CLI 인자
- `--in`(default `sepa-3c-candidates.json`), `--out`(default `sepa-3c-history.json`)
- `--codes 005930,000660`(임의 종목)
- `--scan-days`(250), `--confirm-lookback`(5), `--recent-days`(10),
  `--stop-pct`(8), `--target-pct`(20)
- 3C 임계값은 `find-3c`와 동일 인자(`--min-shelf-days` 등)도 노출 — 같은 검출기를 쓰므로.
- `--ticker CODE` 단일 종목 디버그(저장 안 함, 리플레이 상세 출력).

## 7. 불변 원칙
- 공유 파일 무접촉, 컷오프 금지, 환각 금지(이벤트 근거 JSON 포함), 자동 commit 안 함.
- `update-data` 선행 권장. `find-3c`와 **동일한 검출기(v2b)** 를 쓴다(검증의 전제 —
  다른 로직이면 검증 의미 없음). [[doc-logic-sync]] 준수.

## 8. 검증 계획
- `cheat_history.py` 순수 함수 단위 테스트(합성 시계열):
  ① 명확한 3C→돌파가 들어간 시계열 → `find_breakout_events`가 그 날짜를 1건 잡음.
  ② 돌파 없는 횡보 시계열 → 이벤트 0, classify `no_3c_found`.
  ③ 돌파 후 재수축(2차 치트) 시계열 → classify `re_basing`.
  ④ `post_breakout_outcome`의 gain/max_gain/drawdown 수치 정확.
- 실데이터: 70종목 풀런 → 콘솔이 종목별 분류와 최근 이벤트를 보여주고, 집계에
  생존자-편향 딱지가 붙는지 확인. `--ticker <CODE>`로 리플레이 상세를 차트와 대조.
- (선택) 오라클 교차: 캐시에 있는 한국 종목 중 과거 3C로 launch한 사례를 `--ticker`로
  찍어 이벤트 날짜가 차트 치트 돌파와 맞는지 눈 대조.

## 9. 미해결/후속
- **캐시 광역(3028) 스캔:** RS 필터 없이 과거 3C를 넓게 발굴(잡음 ↑, 계산 ↑) — 별도 옵션/스킬.
- 더 정직한 검증(같은 종목 내 "돌파일 vs 무작위일" 돌파 후 수익률 비교)은 이번 범위 밖.
- 비위너(탈락 종목) 교차검증으로 검출기 정밀도(헛신호율) 측정은 별도 과제.
- 3C 임계값 자동 튜닝(그리드 서치)은 별도 spec.
