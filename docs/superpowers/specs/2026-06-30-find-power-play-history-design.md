# find-power-play-history — 파워 플레이 검출기 회고·검증 도구 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인됨, 구현 계획 대기

## 1. 배경·목적

`find-power-play`는 "지금 기준"의 파워 플레이(깃대+깃발+돌파)만 본다. 그래서
현재 70개 후보 중 패턴 0개가 나오는데(교과서 100% 깃대가 희귀), 이 중 상당수는
**과거에 이미 파워 플레이를 거쳐 돌파했을 수 있다**(지금은 이미 연장돼 패턴이
안 보일 뿐). 이 도구는 그 종목들의 **과거 1년을 매 거래일 되짚어**, 우리
`evaluate_power_play`가 그 종목 역사 속 **"파워 플레이 완성 → 돌파" 시점을
짚어내는지** 보여준다.

**1순위 목적 = 검증.** 알고리즘이 찍은 돌파 날짜를 사용자가 차트로 열어 "진짜
파워 플레이였나"를 눈으로 대조한다. **부산물 = 분류**(이미 돌파·연장됐는지 등).

핵심 설계: `evaluate_power_play(series)`는 시계열의 *마지막 날* 기준으로
판정하므로, **시계열을 과거 날짜 D에서 잘라 넣으면 "D 시점 판정"이 그대로
재현된다.** 새 평가 로직 없이 **기존 `evaluate_power_play` 재사용**(as-of
리플레이). find-vcp-history와 같은 구조의 형제 도구.

## 2. 범위

### 하는 것
- 입력 기본 = `sepa-power-play-candidates.json`의 **전체 후보 종목**(파일 전체).
  `--codes 005930,000660`이면 임의 지정. (vcp-history의 `--all`은 기본이 이미
  전체이므로 불필요 — 두지 않는다.)
- 각 종목의 OHLCV 캐시로 최근 250영업일을 매일 as-of 리플레이.
- "파워 플레이→돌파" 이벤트 추출 + 돌파 후 결과 측정 + 종목 분류.
- 산출 `public/data/sepa-power-play-history.json` + 콘솔 표.

### 안 하는 것
- 임계값 자동 최적화/튜닝 — 이번엔 *현재 검출기를 그대로 과거에 적용*만.
- 실거래·손절·비중 신호 — 검증/회고 전용.
- 수급·공유 파일 갱신·자동 commit.
- 새 판정 로직 — `evaluate_power_play` 재사용(다른 로직이면 검증 의미 없음).

## 3. 데이터 입력
- OHLCV 캐시 `.cache/ohlcv/series/<code>.json` (수정주가, ~400영업일).
  `update-data` 선행 권장.
- 대상 코드 목록: 위 §2 입력 규칙(기본 전체 후보).
- **의존성**: `evaluate_power_play`(= `scripts/canslim_lib/power_play.py`,
  find-power-play 산출물). 이 도구는 find-power-play 위에 쌓인다.
- 250영업일을 as-of로 쓰려면 각 D 이전에 lookback(120)이 있어야 하므로 캐시
  ~370영업일 필요(보유 400이면 충분). 부족하면 가능한 만큼만 스캔하고 사유 기록.

## 4. 알고리즘

### 4.1 as-of 리플레이 (`replay_power_play`)
- `dates = series["dates"]`. 스캔 구간 = 마지막 `scan_days`(기본 250) 거래일의 인덱스.
- 각 as-of 인덱스 i에 대해, 시계열을 `[:i+1]`로 잘라
  `evaluate_power_play(잘린 series, params)` 호출.
- 기록: `{date, pattern_detected, status, pivot_price, flagpole_gain_pct,
  flag_depth_pct}` 리스트(시간순).
- 참고: `evaluate_power_play`가 내부에서 마지막 120일만 보므로 잘린 길이가
  lookback보다 짧아도 안전(짧으면 `base_too_short` 등으로 자연 처리).

### 4.2 돌파 이벤트 탐지 (`find_breakout_events`)
as-of 리플레이를 시간순으로 훑어, 다음을 만족하는 날 D를 **돌파 이벤트**로 본다:
1. `status(D) == "breakout"`,
2. `status(D-1) != "breakout"` (새 전환 — 같은 돌파를 중복 카운트 방지),
3. 직전 `confirm_lookback`(기본 5거래일) 안에 `pattern_detected == true`였던 날이
   하나라도 있음 (= 돌파 직전에 진짜 파워 플레이가 성립했다).
- 이벤트 근거 캡처: `date`, 돌파일 종가 `breakout_close`, 그리고 **확인일(직전
  pattern_detected=true였던 가장 가까운 날)의** `pivot_price`·`flagpole_gain_pct`·
  `flag_depth_pct`.

### 4.3 돌파 후 결과 (`post_breakout_outcome`)
이벤트 날짜 이후 바들로 측정 (vcp_history와 **완전 동일 로직**):
- `days_since` = 이벤트~마지막일 거래일 수(연장 정도).
- `gain_since_pct` = `(마지막 종가 − breakout_close)/breakout_close*100`.
- `max_gain_pct` = 이벤트 이후 `max(high)` 기준 최대 상승 %.
- `max_drawdown_pct` = 이벤트 이후 종가 기준 최저점까지 하락 % (음수).
- `good_breakout` = 손절(intrabar low가 `−stop_pct`)에 닿기 *전에* 목표(intrabar
  high가 `+target_pct`)에 도달하면 true. 같은 바에서 둘 다 닿으면 **손절 우선**
  (보수적). 손절폭 `−stop_pct`(8)·목표 `+target_pct`(20)는 파라미터.

### 4.4 종목 분류 (`classify`) — 우선순위 순
- 이벤트 0개 → **`no_power_play_found`** (검출기 미스 의심 또는 진짜 패턴 없음).
- 가장 최근 이벤트 기준:
  1. `days_since <= recent_days`(기본 10) → **`recent_breakout`**.
  2. 그 이벤트 *이후* 바에서 `pattern_detected==true`가 다시 나타났고 마지막
     status가 forming/actionable → **`re_basing`** (돌파 후 2차 베이스).
  3. 그 외 → **`extended`** (예전에 돌파·상승, 지금 한참 위 = 추격 늦음).

### 4.5 집계 (참고용, 생존자 편향 경고)
- `n_with_events`, `n_no_power_play_found`, `total_events`.
- 이벤트 전체의 `gain_since_pct`·`max_gain_pct` 중앙값, `good_breakout` 비율.
- **출력·콘솔에 명시 딱지**: "⚠️ 이 집계는 추세 통과(RS 강세) 종목만 본 결과라
  생존자 편향으로 과대평가됨. 검출기 신뢰의 *보조 지표*일 뿐, 결정적 검증은
  이벤트 날짜를 차트로 눈 대조하는 것."
  ([doppelganger-survivor-bias]·[equity-curve-hindsight-pivot] 메모리 정신과 일치.)

## 5. 출력 스키마
`public/data/sepa-power-play-history.json`:
```jsonc
{
  "generated_at": "2026-06-30 22:00",
  "asof": "2026-06-29",
  "source": "sepa-power-play-candidates.json",
  "input_filter": "all",                     // 기본 전체. "codes" 도 가능
  "scan_days": 250,
  "params": { "min_flagpole_gain": 100, "max_flagpole_days": 40, "pole_vol_mult": 1.5,
              "max_pre_pole_gain": 30, "min_flag_pullback": 3, "min_flag_days": 8,
              "max_flag_days": 30, "max_flag_depth": 20, "breakout_vol_mult": 1.4,
              "near_pivot_pct": 5, "lookback_days": 120,
              "confirm_lookback": 5, "recent_days": 10, "stop_pct": 8, "target_pct": 20 },
  "caveat": "집계 수익률은 생존자 편향으로 과대 — 보조 지표. 결정적 검증은 차트 눈 대조.",
  "summary": {
    "n_stocks": 70, "n_with_events": 0, "n_no_power_play_found": 0, "total_events": 0,
    "agg": { "median_gain_since_pct": null, "median_max_gain_pct": null, "good_breakout_rate": null }
  },
  "stocks": [
    {
      "code": "095610", "name": "테스", "market": "KOSDAQ", "rs": 99,
      "classification": "extended",
      "num_events": 1,
      "most_recent_event_date": "2026-04-10",
      "events": [
        { "date": "2026-04-10", "confirm_date": "2026-04-09",
          "pivot_price": 0, "flagpole_gain_pct": 132.0, "flag_depth_pct": 14.2,
          "breakout_close": 0, "days_since": 52, "gain_since_pct": 0,
          "max_gain_pct": 0, "max_drawdown_pct": 0, "good_breakout": true }
      ]
    },
    {
      "code": "000660", "name": "SK하이닉스", "market": "KOSPI", "rs": 95,
      "classification": "no_power_play_found",
      "num_events": 0,
      "most_recent_event_date": null,
      "events": [],
      "reason": "no_series"
    }
  ]
}
```
- 각 이벤트 객체에는 `"confirm_date"` 키가 있으며, 돌파 직전에
  `pattern_detected=true`였던 가장 가까운 날짜(= 이벤트 근거)를 나타낸다.
- no-series(시세 없음) 종목은 이벤트 없이 `classification: "no_power_play_found"`
  + `"reason": "no_series"` 키를 추가로 갖는다.
- `stocks`는 입력 종목 전부 포함(이벤트 없으면 `no_power_play_found`·events []).
- 정렬: `classification`(re_basing → recent_breakout → extended →
  no_power_play_found) → rs 내림차순.

## 6. 구성 요소
- **`scripts/canslim_lib/power_play_history.py`** (순수, 단위 테스트 가능):
  `replay_power_play(series, scan_days, params) -> list[dict]`,
  `find_breakout_events(replay, confirm_lookback) -> list[dict]`,
  `post_breakout_outcome(series, event_date, stop_pct=8.0, target_pct=20.0) -> dict | None`,
  `classify(events, replay, recent_days) -> str`.
  `evaluate_power_play`(기존)만 호출, 새 판정 로직 없음.
- **`scripts/screen_power_play_history.py`** — CLI: 입력 코드 결정 → 종목별 위
  4단계 → JSON 저장 + 콘솔 표(종목별 분류·최근 이벤트, 끝에 집계+딱지).
- 산출: `public/data/sepa-power-play-history.json`.
- **`.claude/skills/find-power-play-history/SKILL.md`**.

### CLI 인자
- `--in`(default `sepa-power-play-candidates.json`),
  `--out`(default `sepa-power-play-history.json`)
- `--codes 005930,000660`(임의 종목만; 미지정 시 파일 전체)
- `--scan-days`(250), `--confirm-lookback`(5), `--recent-days`(10),
  `--stop-pct`(8), `--target-pct`(20)
- 파워 플레이 임계값은 `find-power-play`와 동일 인자(`--min-flagpole-gain`,
  `--max-flagpole-days`, `--pole-vol-mult`, `--max-pre-pole-gain`,
  `--min-flag-pullback`, `--min-flag-days`, `--max-flag-days`, `--max-flag-depth`,
  `--breakout-vol-mult`, `--near-pivot-pct`, `--lookback-days`)도 노출 — 같은
  검출기를 쓰므로.
- `--ticker CODE` 단일 종목 디버그(저장 안 함, 리플레이 상세 출력).

## 7. 불변 원칙
- 공유 파일 무접촉, 컷오프 금지, 환각 금지(이벤트 근거 JSON 포함), 자동 commit 안 함.
- `update-data` 선행 권장. `find-power-play`와 **동일한 검출기**를 쓴다(검증의
  전제 — 다른 로직이면 검증 의미 없음). [doc-logic-sync] 준수.

## 8. 검증 계획
- `power_play_history.py` 순수 함수 단위 테스트(합성 시계열):
  ① 명확한 파워 플레이→돌파가 들어간 시계열 → `find_breakout_events`가 그 날짜를
     1건 잡음.
  ② 돌파 없는 횡보 시계열 → 이벤트 0, classify `no_power_play_found`.
  ③ 돌파 후 재형성 시계열 → classify `re_basing`.
  ④ `post_breakout_outcome`의 gain/max_gain/drawdown 수치 정확.
- 실데이터: 70종목 풀런 → 콘솔이 종목별 분류와 최근 이벤트를 보여주고, 집계에
  생존자-편향 딱지가 붙는지 확인. `--ticker 095610`으로 리플레이 상세를 차트와 대조.

## 9. 미해결/후속
- 더 정직한 검증(같은 종목 내 "돌파일 vs 무작위일" 돌파 후 수익률 비교)은
  이번 범위 밖 — 필요 시 후속 스킬. 이번은 *눈 대조 + 참고용 집계*까지.
- 비위너(탈락 종목) 교차검증으로 검출기 정밀도(헛신호율) 측정은 별도 과제.
- 파워 플레이 임계값 자동 튜닝(그리드 서치)은 별도 spec.
- find-vcp-history와 출력 통합 뷰(한 종목이 두 패턴 역사에 모두 잡힘)는 별도.
