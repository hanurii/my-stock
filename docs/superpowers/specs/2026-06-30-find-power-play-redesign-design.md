# find-power-play 검출기 재설계 — 최근 깃발 중심 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인됨, 구현 계획 대기
원본 검출기 spec: `2026-06-29-find-power-play-design.md`(이 문서가 §4 알고리즘을 대체)

## 1. 배경·목적

미너비니 파워 플레이(High Tight Flag) 책 예시 5종(케이엠더블유·다우데이타·
화인베스틸·티앤엘·BBY)을 FDR 실데이터로 대조한 결과, 현재 `evaluate_power_play`
가 **5개를 전부 놓쳤다**([[power-play-book-examples-gaps]]). 막은 원인이 임계값이
아니라 **로직이 엉뚱한 걸 측정**하는 데 있었다:
- 피벗을 *120일 전체 최고가*로 잡아 무관한 옛 고점에 잠김(화인 3,165).
- "조용한 출발"을 깃대 바닥 한가운데서 재 급등주를 오판(케이엠 77%).
- "대량거래"를 깃대 *상승구간*만 봐 *돌파일*에 터지는 케이스 놓침(BBY).
- strict 100%/8주가 책 실제 예시보다 빡빡(BBY 34%/8주=+135%/13주, 티앤엘 41%).

웹 검증 결과 미너비니 본인은 **"피벗 = 돌파 직전 가장 타이트한 (최근) 수축
구간의 최고가, 그 위로 돌파 시 매수"** 로 정의한다(TradingView Power Play
Indicator·FinerMarketPoints VCP 체크리스트·ChartMill). 즉 **피벗은 최근 깃발의
천장**이지 장기 최고가가 아니다. 본 재설계는 검출의 중심을 이 정의에 맞춘다.

**매수점 = 깃발 돌파**(사용자 확정). "조용한 베이스를 뚫는 폴 *시작*" 매수형
(다우데이타)은 이번 범위 밖 — 의도적 미검출.

## 2. 범위

### 하는 것
- 기존 `evaluate_power_play(series, params) -> dict`를 **인터페이스 동일하게
  유지한 채 내부 로직 교체**(in-place). `find-power-play`·`find-power-play-history`
  ·CLI는 호출부 변경 없음(검출기 거동만 개선).
- 5개 책 예시를 영구 회귀 픽스처로 못박아 검증.

### 안 하는 것
- 인터페이스(반환 키 집합)·CLI 골격 변경 — 유지.
- "폴 시작형"(다우데이타) 매수 모델링 — 범위 밖.
- 수급·공유 파일·자동 commit — 기존 SEPA 불변 원칙 유지.

## 3. 데이터 입력
- OHLCV: 기존과 동일(캐시 일봉). 과거 책 예시 검증은 FDR로 받은 데이터를
  **스냅샷 픽스처**로 커밋(테스트 네트워크 비의존, §8).

## 4. 재설계 알고리즘 (원본 §4 대체)

### 4.1 분석 구간
- lookback = 최근 **120거래일**(데이터 확보용, 유지).

### 4.2 피벗 = 최근 깃발의 천장 (핵심 변경)
- **피벗 후보 탐색을 최근 `flag_window`(기본 45거래일≈9주)로 한정**한다(과거
  전체가 아님). 이 창 안에서 **그 뒤로 `min_flag_pullback`%(기본 3) 이상 눌린
  가장 높은 고점**을 `flag_high`(=피벗)로 잡는다. (돌파 봉이 피벗을 가로채지
  않는 기존 로직 유지; 후보 없으면 창 내 최고가 폴백.)
- 효과: 무관한 옛 고점(화인 3,165, 80거래일 전) **자동 배제** + 날짜 민감도 완화.
- `flag_high` 바 인덱스 = `fhi`.

### 4.3 깃대(flagpole)
- **깃대 시작 저점** = `fhi` 직전 `max_flagpole_days`(**기본 70거래일=14주**) 구간
  안의 최저 저점(`pole_start_idx`, `pole_start_low`).
- **깃대 상승률** `flagpole_gain_pct` = `(flag_high − pole_start_low)/
  pole_start_low × 100`. **하드 게이트: ≥ `min_flagpole_gain`(기본 90)**.
  불충족 시 reason `pole_gain_too_small`.
- 기간은 탐지 구간을 14주로 한정했으므로 구조적으로 ≤14주 보장.
- 비고: 14주 창이 BBY(+135%/13주)·티앤엘(+109%/14주)의 "크지만 느린" 깃대를 포착.

### 4.4 깃발(flag) 판정 — 하드 게이트
깃발 구간 = `fhi` 이후 현재까지.
1. **길이** `flag_length_days`: `≥ min_flag_days`(8) AND `≤ max_flag_days`(30=6주).
   미달 `flag_too_short` / 초과 `flag_too_long`.
2. **깊이** `flag_depth_pct` = `(flag_high − 깃발 내 최저저점)/flag_high × 100`
   `≤ max_flag_depth`(기본 20; 저가주 CLI 25). 초과 `flag_too_deep`.
3. **돌파 전 거래량 마름** `volume_dryup_ratio` = 최근 5거래일 평균 거래량 /
   깃대 상승 구간 평균 거래량 `pole_vol_avg`. `≤ 1.0` 이어야 함. 안 마르면
   `volume_not_drying`.

### 4.5 하드 게이트 vs 보고용 소프트 신호 (핵심 변경)
`pattern_detected = true` ⟺ **4개 하드 게이트** 모두 충족:
(1) 깃대 ≥90%(§4.3) · (2) 깃발 깊이(§4.4-2) · (3) 깃발 길이(§4.4-1) ·
(4) 돌파 전 거래량 마름(§4.4-3).

**보고용 소프트 신호** — 출력에 포함하되 **게이트 아님**(순위·참고용):
- `pre_pole_gain_pct`("조용한 출발") — 미너비니도 소프트 표현. 케이엠 오판 주범 제거.
- `flagpole_vol_ratio`("깃대 상승구간 거래량") — 돌파 거래량(§4.6)이 실질 커버. BBY 구제.
- `tightness_pct` — 종전대로 보고용.

→ reason 집합에서 **`not_quiet_before_pole`·`pole_volume_weak` 제거**(더는 게이트
아님). "말기 베이스 제외" 보호는 1단계 RS≥80 + 깃대 ≤14주 + 타이트 깃발이 대신함.

### 4.6 피벗·상태 판정 (기존 규칙 유지)
- **`pole_vol_avg`** = 깃대 상승 구간 평균 거래량(돌파·dryup 분모로 일관).
- **`pct_to_pivot`** = `(flag_high − 현재종가)/flag_high × 100`.
- **`status`**:
  - `breakout`: 종가 > 피벗 AND 당일 거래량 ≥ `pole_vol_avg × breakout_vol_mult`
    (1.4). ← BBY식 "돌파일 대량거래"가 여기서 핵심 역할.
  - `actionable`: `0 ≤ pct_to_pivot ≤ near_pivot_pct`(5) AND `volume_dryup_ratio ≤ 1.0`.
  - `failed`: 깃발 깊이 초과 또는 종가 < 깃발 저점.
  - `forming`: 그 외.
- **`entry_ready`** = `pattern_detected AND status ∈ {breakout, actionable}` (유지).

## 5. 출력 스키마 (반환 키 집합 유지)
기존 키 그대로 유지. 의미만 일부 변경:
- `pre_pole_gain_pct`, `flagpole_vol_ratio`, `tightness_pct` = **보고용**(이제
  `pattern_detected`에 영향 없음).
- `reason` 가능값: `no_data / no_series / base_too_short / pole_gain_too_small /
  flag_too_short / flag_too_long / flag_too_deep / volume_not_drying /
  eval_error:*` (← `not_quiet_before_pole`·`pole_volume_weak` 삭제).
- `params` 블록에 `flag_window` 추가, `min_flagpole_gain` 90·`max_flagpole_days`
  70 반영. `quiet_window`·`pole_vol_mult`·`max_pre_pole_gain`는 소프트 신호
  계산에만 쓰이고 게이트엔 안 쓰임(출력 params엔 유지 가능).

## 6. 구성 요소
- **`scripts/canslim_lib/power_play.py`** — `evaluate_power_play` 내부 재작성
  (`find_flagpole`를 flag_window 한정 피벗 탐색으로 수정/대체). 표준 라이브러리만.
- **`scripts/screen_power_play.py`** — `--flag-window` 등 신규 인자 노출, 기본값 갱신.
- **`scripts/screen_power_play_history.py`** — 동일 검출기를 쓰므로 자동 반영.
  파워플레이 임계 인자 목록에 `--flag-window` 추가.
- **`tests/test_power_play.py`** — 게이트 변경 반영해 갱신(삭제된 reason 테스트
  제거/수정).
- **`tests/test_power_play_examples.py`**(신규) — 5개 책 예시 스냅샷 회귀.
- 스펙·SKILL.md 문구 동기화([doc-logic-sync]).

### CLI 인자(갱신)
- 기존 + `--flag-window`(45), `--min-flagpole-gain`(90), `--max-flagpole-days`(70).
- 소프트화된 `--max-pre-pole-gain`·`--pole-vol-mult`는 보고값 계산용으로 유지하되
  게이트 아님(문서 명시).

## 7. 불변 원칙 (유지)
- 공유 파일 무접촉, 컷오프 금지, 환각 금지(근거 JSON), 자동 commit 안 함.
- 인터페이스 유지(반환 키 집합·CLI 골격) — 호출부 무변경.
- 개념=미너비니, 수치=공학적 번역. 전 임계값 CLI 노출.

## 8. 검증 계획
- **5개 책 예시 회귀(`test_power_play_examples.py`)**: 각 종목의 피벗 구간
  OHLCV를 **FDR로 1회 받아 스냅샷 JSON 픽스처로 커밋**(네트워크 비의존). 각 예시를
  피벗 시점에 as-of(`series[:i+1]`)로 `evaluate_power_play` 실행하여:
  - 케이엠더블유(2019-07-10)·화인베스틸(2020-05-25)·BBY(1997-12초)·티앤엘
    (2021-06-16): `pattern_detected==True` AND 피벗이 실제 깃발 천장과 일치
    (오차 허용범위 내), 그 시점/직후 `status ∈ {actionable, breakout}`.
  - 다우데이타(2020-05-07): `pattern_detected==False`(폴 시작형, 의도적 미검출).
  - 픽스처가 한 종목이라도 기대와 다르면 **로직 우선 점검**(임계값 땜질 금지),
    설계 자체가 어긋나면 spec으로 회귀.
- **합성 단위 테스트 갱신**: 깔끔한 HTF→detected, 깃대<90%→pole_gain_too_small,
  깃발>깊이→flag_too_deep, 깃발 길이 위반, 거래량 안 마름→volume_not_drying,
  돌파→breakout, entry_ready 게이팅 불변식. (삭제된 reason 테스트 제거.)
- **풀런 비교**: 트렌드 통과 70종목 재실행 → 검출 수가 0에서 증가하는지, 늘어난
  종목이 합리적인지(타이트 깃발+90% 깃대) 육안 확인.

## 9. 미해결/후속
- "폴 시작형"(다우데이타식, 조용한 베이스 돌파 매수) 별도 패턴으로 후속 가능.
- 소프트 신호(조용·깃대거래량)를 순위 점수로 합성하는 랭킹은 후속.
- `flag_window`·`min_flagpole_gain` 등 기본값의 한국 종목 백테스트 튜닝은 후속.
- find-power-play-history도 새 검출기로 재실행 시 과거 이벤트가 늘어남(검증 도구로 더 유용).
