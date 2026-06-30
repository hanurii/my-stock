# find-power-play 중첩 깃발 / 최종 타이트 수축 식별 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인됨, 구현 계획 대기
선행 spec: `2026-06-30-find-power-play-redesign-design.md`(이 문서가 §4.2 피벗 선택을 교체)

## 1. 배경·목적

재설계 검출기는 피벗을 "최근 `flag_window` 안의, 뒤에 눌림이 확인된 가장 높은
고점"으로 잡는다. 그런데 **넓은 베이스 안에 더 타이트한 최종 깃발이 중첩된**
경우(티앤엘 2021-06), 그 로직은 *넓은 베이스 천장*(→ flag_too_long/deep)이나
*돌파 스파이크*(→ flag_too_short)를 집어 **최종 타이트 수축을 못 본다**(현재
회귀에서 티앤엘 xfail).

미너비니 정의는 **"피벗 = 돌파 직전 가장 타이트한(최종) 수축의 천장"**(웹 검증:
TradingView Power Play·ChartMill). 본 작업은 피벗 선택을 이 정의에 맞게 **최종
타이트 수축 식별**로 교체한다. 미너비니 본인이 "알고리즘은 VCP를 시각적으로 못
잡는다"고 한 바로 그 부분이라([[power-play-book-examples-gaps]]) 완벽한 일반화는
목표가 아니다 — 책 예시를 잡고 거짓양성을 정직히 표기하는 것까지.

### 프로토타입 검증(FDR 실데이터, 결정의 근거)
- 케이엠더블유·화인베스틸·BBY: 기본(깃대 90%)에서 **검출 유지**.
- 티앤엘: 최종 타이트 수축(2021-05~06, ~9.4%)의 천장 32,600을 피벗으로 잡음 →
  깃대 79%라 **`--min-flagpole-gain 78`에서 검출**(기본 90에선 미검출, 의도).
- 다우데이타: **검출됨**(피벗 8,420·깃대 102%). 단 미너비니 원칙상 그 "폴"은
  *코로나 깊은 약세에서 1년 잠든 평베이스로의 회복*이지 추력(thrust)이 아니므로
  **파워 플레이가 아님**("buy strength not weakness"·"does not bottom-fish").
  → **알려진 거짓양성으로 xfail 표기**(다우와 화인을 깔끔히 가르는 건 미너비니가
  눈으로 하는 정성 판단이라 규칙화 불가).
- 라이브 70종목(기본 90): 검출 0, 사유 대부분 `no_contraction`(현재 타이트 수축
  부재 = 정상 선별성). 거짓양성 홍수 없음.

## 2. 범위

### 하는 것
- `evaluate_power_play`의 **피벗 선택을 "최종 타이트 수축 식별"로 교체**.
  반환 키 집합·CLI 골격·다운스트림(history) 인터페이스는 유지.
- 5개 책 예시 회귀를 갱신(티앤엘 xfail→파라미터 검출, 다우 xfail) + 합성 음성 테스트.

### 안 하는 것
- 깃대 게이트 완화 — 기본 90% 유지(티앤엘은 CLI로 78 낮춰야 검출).
- 다우데이타를 화인베스틸과 규칙으로 분리하는 깨지기 쉬운 휴리스틱 — 안 만듦.
- status/entry_ready 로직 변경 — 유지(선행 spec §4.6).
- 공유 파일·수급·자동 commit.

## 3. 알고리즘 (선행 §4.2 교체)

### 3.1 최종 타이트 수축 식별 (`find_pivot_contraction`)
입력: lookback(120) 내 `highs`, `lows`. 파라미터: `min_flag_days`(8),
`max_flag_days`(30), `tight_pct`(기본 18), `contraction_grace`(기본 3),
`min_flag_pullback`(3).

1. **수축 창 탐색**: 끝 인덱스 `end`를 `n-1`부터 `max(min_flag_days-1,
   n-1-contraction_grace)`까지 내려가며(=돌파 봉 grace개는 끝에서 제외), 각 `end`에서
   길이 `L`을 `min_flag_days`→`max_flag_days`로 늘리며 창 `[end-L+1, end]`의 변동폭
   `(max고−min저)/min저×100`이 `tight_pct` 이하인 한 더 길게 잡는다(가장 긴 타이트
   창). 타이트가 깨지면 멈춘다.
2. **피벗 = 그 창 안에서 '뒤에 `min_flag_pullback`% 이상 눌린' 가장 높은 고점**
   (= 저항; 돌파 봉은 뒤에 눌림이 없어 제외). 그런 후보가 없으면 다음(더 과거) `end`로.
3. 어떤 `end`에서도 못 찾으면 **`None`**(→ §3.3 `no_contraction`).

> 효과: 티앤엘의 넓은 베이스(24%) 대신 그 안의 최종 타이트 수축(9.4%) 천장을
> 피벗으로. KMW/화인/BBY는 그들의 (타이트한) 깃발이 곧 수축이라 동일하게 잡힘.

### 3.2 깃대·깃발·게이트 (선행과 동일)
- `pole_start` = 피벗 인덱스 직전 `max_flagpole_days`(70) 구간 최저 저점.
- `flagpole_gain_pct` = (피벗−pole_start_low)/pole_start_low×100, **하드 게이트 ≥90**.
- 깃발 길이/깊이·거래량 마름·tightness·소프트 신호: 선행 spec과 동일.
- 하드 게이트 3개(깃대·깃발 깊이·깃발 길이) 그대로.

### 3.3 reason 갱신
- **추가**: `no_contraction`(§3.1에서 수축 못 찾음).
- 유지: `no_data/no_series/base_too_short/pole_gain_too_small/flag_too_short/
  flag_too_long/flag_too_deep/eval_error:*`.
- (피벗이 항상 수축 천장이라 flag_too_short/long/deep은 거의 안 나오지만 가드로 유지.)

## 4. 파라미터·인터페이스
- **추가**: `tight_pct`(18), `contraction_grace`(3). CLI `--tight-pct`·`--contraction-grace`.
- **제거(피벗 경로에서 무의미)**: `flag_window`(및 `--flag-window`). 선행 redesign이
  도입했으나 수축 finder가 자체 창을 스캔하므로 더 안 쓴다.
- 유지: `min_flagpole_gain`(90)·`max_flagpole_days`(70)·`min_flag_days`(8)·
  `max_flag_days`(30)·`max_flag_depth`(20)·`min_flag_pullback`(3)·`lookback_days`(120)
  ·`breakout_vol_mult`·`near_pivot_pct`·소프트 신호용 키.
- 반환 키 집합 불변(피벗·지표·소프트 신호 동일). `find_flagpole`은 `evaluate`에서
  더는 호출 안 함 — 함수·단위테스트는 남기되(하위호환), 신규 `find_pivot_contraction`이
  피벗을 담당.

## 5. 구성 요소
- `scripts/canslim_lib/power_play.py` — `find_pivot_contraction(highs, lows, params)`
  신규(순수 함수), `evaluate_power_play`가 이를 호출하도록 교체. `DEFAULT_PARAMS`
  갱신(tight_pct·contraction_grace 추가, flag_window 제거).
- `scripts/screen_power_play.py`·`screen_power_play_history.py` — CLI 인자 갱신
  (`--flag-window` 제거, `--tight-pct`·`--contraction-grace` 추가).
- `tests/test_power_play.py` — 피벗/게이트 변경 반영, `find_pivot_contraction` 단위
  테스트 추가, `find_flagpole`·flag_window 관련 테스트 정리.
- `tests/test_power_play_examples.py` — 회귀 갱신(아래 §6).
- `.claude/skills/find-power-play/SKILL.md` — 문구 동기화.

## 6. 검증 계획
- **`find_pivot_contraction` 단위 테스트**(합성): ① 넓은 베이스+최종 타이트 수축 →
  수축 천장을 피벗으로(넓은 천장 아님), ② 타이트 수축 없음 → None, ③ 돌파 봉이
  피벗 안 됨(뒤 눌림 없는 마지막 봉 제외).
- **5개 책 예시 회귀**(`test_power_play_examples.py`, 피벗±윈도 스캔):
  - 케이엠더블유·화인베스틸·BBY: 기본(gain 90) **검출**(PASS).
  - **티앤엘**: `--min-flagpole-gain 78`(파라미터)로 **검출**(xfail→PASS). 기본 90에선
    미검출이 정상이므로, 테스트는 78 파라미터로 detected를 자산.
  - **다우데이타**: 기본에서 알고리즘이 **검출**하나 미너비니상 파워플레이 아님 →
    `assert not detected`를 **`xfail`**(알려진 거짓양성)로 표기.
  - **합성 음성**(신규): 명백히 파워 플레이가 아닌 합성 시계열(평평·약한 폴·깃발
    없음) → `not detected` **PASS**(진짜 음성 가드).
- **풀런**: 70종목 재실행 — 사유 대부분 `no_contraction`(정상 선별), 오류 없음.

## 7. 불변 원칙
- 인터페이스 유지, 공유 파일 무접촉, 환각 금지(근거 JSON), 자동 commit 안 함.
- 개념=미너비니, 수치=공학적 번역. 전 임계값 CLI 노출.
- 다우데이타 거짓양성은 **정직히 xfail**로 드러낸다(숨기지 않음).

## 8. 미해결/후속
- 다우데이타식 "회복-폴" vs 화인식 "속도형 폴" 구분 — 정성 판단 영역, 후속 연구.
- history 재실행 시 이벤트가 바뀜(더 정확한 피벗) — 검증 도구로 더 유용.
- tight_pct·contraction_grace 기본값 한국 종목 백테스트 튜닝은 후속.
