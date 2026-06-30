# find-power-play — SEPA 패턴 스킬: 파워 플레이(High Tight Flag) 탐지 (설계 spec)

작성일 2026-06-29 · 상태: 설계 승인됨, 구현 계획 대기

## 1. 배경·목적

마크 미너비니 SEPA(Specific Entry Point Analysis)를 한국 시장에 적용하는
파이프라인의 **패턴 탐지 스킬**. `find-vcp`(VCP 베이스)의 **형제 스킬**로,
같은 입력(트렌드 템플레이트 통과 종목)을 받아 미너비니의 또 다른 패턴인
**파워 플레이(Power Play = High Tight Flag, 하이 타이트 플래그)** 를 탐지한다.

파워 플레이는 미너비니가 소개한 가장 폭발적이지만 **희귀한** 패턴이다.
"조용하던 종목이 엄청난 거래량과 함께 8주 이내 100% 이상 폭등(깃대)한 뒤,
좁은 변동폭으로 얕게 횡보(깃발)하고, 거래량이 마른 직후 돌파"하는 구조.
100% 깃대 조건이 매우 빡빡하므로 트렌드 통과 종목 중에서도 극소수만 걸리는
것이 정상이다(= 의도된 선별성).

### 방법론 선택 (의도적 결정)

`find-vcp`와 동일하게, "무엇을 찾는가"=미너비니 교과서, "어떻게 숫자로
판정하나"=이 프로젝트의 공학적 번역이다. 사용자는 교과서에 충실한 기본값
(깃대 100%/8주)을 선택했다. 걸리는 종목이 적은 것은 버그가 아니라 의도이며,
완화가 필요하면 §6의 CLI 인자로 언제든 조정한다.

## 2. 범위

### 하는 것
- 입력: `public/data/sepa-trend-candidates.json`의 `all_pass == true` 종목만 분석.
- 각 종목의 일봉(OHLCV 캐시)에서 파워 플레이(깃대+깃발) 패턴을 탐지하고
  지표·상태를 산출.
- 산출: `public/data/sepa-power-play-candidates.json`.

### 안 하는 것
- VCP 베이스 탐지 — 그건 형제 스킬 `find-vcp` 영역. 이번은 파워 플레이만.
- 수급(외인/기관 순매수) 신호 — VCP와 동일하게 OHLCV 거래량으로 충분.
- 실제 매매·손절·비중 신호 — 후보 좁히기까지. 리스크 규칙은 다음 단계.
- 공유 파일(`trend-template-candidates.json` 등) 갱신 — 항상 전용 출력 파일.
- 자동 git commit/push.

## 3. 데이터 입력

- **OHLCV 캐시**: `find-vcp`와 동일 소스(수정주가 일봉). `find-power-play`
  실행 전 `update-data`로 최신화 권장(선행 스킬).
- **대상 종목 목록**: `sepa-trend-candidates.json`의 `candidates[]` 중 `all_pass`.
- 종목당 필요한 시계열: `dates`, `closes`, `highs`, `lows`, `volumes`.

## 3.5 알고리즘 출처 (정직한 구분)

- **개념·정의 = 마크 미너비니.** 아래 §4.0의 6개 정성 조건은 미너비니
  『Trade Like a Stock Market Wizard』(2013) 등에서 발췌·요약한 파워 플레이
  정의 그대로다.
- **구체 수치·계산 규칙 = 이 프로젝트의 공학적 번역(원전 아님).** "조용한
  출발", "대규모 거래량", "좁은 변동폭"을 기계 판정으로 옮기며 고른 임계값
  (조용 구간 길이/상승률 한도, 거래량 배수, 거래일 환산 등)은 책의 "정답"이
  아니라 구현 선택이다. 전부 CLI 인자로 노출하고(§6) 한국 종목 백테스트
  튜닝을 후속 과제로 둔다(§9).

## 4. 파워 플레이 판정 알고리즘

### 4.0 미너비니 정의 (발췌 요약 — 판정의 기준 원본)

1. **대규모 거래량을 수반한** 폭발적 급등으로 주가가 **8주 이내 100% 이상 상승**
   (깃대). 이미 상당히 오른 **말기(late-stage) 베이스** 종목은 보통 제외.
   최상의 대상은 **1단계에서 조용히 횡보하다가 갑자기 폭발**하는 종목.
2. 폭발 이후 **3~6주**(일부는 10~12일) 동안 **20% 이상 조정 없이**(저가주 예외
   최대 25%) **좁은 변동폭으로 횡보**(깃발).
3. 깃발 조정이 고가 대비 **10% 이내면 이미 타이트**한 상태이므로, VCP식 변동성
   수축이 별도로 나타나지 않아도 된다 → **타이트는 합격 게이트가 아님**(보고용).
4. 폭발적 급등은 **횡보 구간을 지난 후**에 일어난다(=조용한 출발).
5. 깃발은 비교적 좁은 구간, 조정폭 **20~25% 이내**.
6. 베이스 안에서(대개 **돌파 며칠 전**) **거래량이 크게 줄어든다**.

→ 성립 6조건 = **(깃대)** ①100%↑ ②8주↓ ③대규모 거래량 ④조용한 출발
+ **(깃발)** ⑤6주↓·10~12일↑ ⑥조정 ≤20% + 돌파 전 거래량 마름.

### 4.1 분석 구간(lookback)

- lookback = 최근 **120거래일**(약 6개월). 깃대(≤8주=40거래일) + 깃발(≤6주=
  30거래일) + 조용한 출발 확인 구간(~20~40거래일)을 모두 담기 충분.

### 4.2 깃발 고점·깃대 탐지

1. **깃발 고점(flag_high) = 피벗(돌파 매수점)** = **"뒤에 눌림이 나온 가장 높은
   고점"**. 단순 "구간 최고 고가"가 아니다.
   > **중요(돌파가 잡히려면):** 교과서적 돌파일(신고가로 깃발 천장을 뚫는 날)은
   > 그날 고가가 곧 구간 신고가가 된다. 피벗을 "구간 최고 고가"로 잡으면 피벗이
   > **돌파 봉 자신**으로 옮겨가 "종가 > 피벗"이 영영 성립하지 않고(자기보다 높을
   > 수 없으므로) 깃발 길이도 0이 되어 패턴이 미검출된다. find-vcp가 피벗을
   > "마지막 **확정된** 스윙 고점(진행 중 봉 제외)"으로 잡는 것과 같은 이유로,
   > 여기서도 피벗을 **그 뒤로 되돌림(눌림)이 확인된 고점**으로 한정한다. 현재
   > 돌파 봉은 "뒤에 눌림 없음"이라 피벗 후보가 아니며, 직전 깃발 천장이 피벗으로
   > 남아 **돌파(breakout)가 정상 인식**된다.
   - 구현: 피벗 후보 = `min(이후 저가들) ≤ 고가 × (1 − min_flag_pullback/100)` 를
     만족하는 고점(= 그 뒤로 `min_flag_pullback`%(기본 3) 이상 눌린 고점). 후보 중
     **가장 높은 고가**가 `flag_high`. (후보가 없으면 구간 최고 고가로 폴백.)
   - `min_flag_pullback`(기본 3%)은 CLI 인자로 노출. 매우 타이트한 깃발은 이 값을
     낮춰 잡는다.
2. **깃대 시작 저점(pole_start_low)** = `flag_high` 직전 `≤max_flagpole_days`
   (기본 40거래일) 구간 안의 최저 저점.
3. **깃대 상승률** `flagpole_gain_pct` = `(flag_high − pole_start_low)/
   pole_start_low × 100`. **≥ `min_flagpole_gain`(기본 100)** 이어야 함.
4. **깃대 기간** `flagpole_days` = `pole_start_low`→`flag_high` 거래일 수.
   탐지 구간을 `flag_high` 직전 `max_flagpole_days`(기본 40=8주)로 한정했으므로
   `flagpole_days ≤ 8주`는 **구조적으로 항상 보장**된다(별도 reason 불필요).

### 4.3 조용한 베이스 / 깃대(상승) 구간 분리 — 거래량 (조건 ③④의 토대)

> **중요(구현 정합성):** 깃대 시작 저점(`pole_start_idx`)은 파워 플레이의 전형적
> 구조상 **조용한 베이스의 바닥**이며, 흔히 lookback 구간의 맨 앞쪽에 온다.
> 따라서 "저점 *직전*" 구간에서 조용·거래량을 재면 데이터가 비어 항상 실패한다.
> 대신 **저점(`pole_start_idx`)을 기준으로 그 직후를 두 구간으로 나눈다**:
> - **조용한 베이스** = `[pole_start_idx, pole_start_idx + quiet_window)`
>   (기본 `quiet_window`=20거래일; `flag_high` 를 넘지 않게 자른다). 종목이
>   바닥에서 횡보하던 구간.
> - **깃대 상승** = `[조용한 베이스 끝, flag_high]`. 바닥을 박차고 오른 급등 구간.

- **`quiet_vol_avg`** = 조용한 베이스 구간 평균 거래량(분모).
- **`pole_vol_avg`** = 깃대 상승 구간 평균 거래량(상승 구간이 비면 `[pole_start_idx,
  flag_high]` 전체로 폴백). 돌파·dryup 계산에도 이 값을 분모로 일관 사용.
- **`flagpole_vol_ratio`** = `pole_vol_avg / quiet_vol_avg`.
- 조건: `flagpole_vol_ratio ≥ pole_vol_mult`(기본 1.5) — "대규모 거래량을
  수반한 폭발"의 기계 번역. 불충족 시 reason `pole_volume_weak`.

### 4.4 조용한 출발 / 말기 베이스 제외 (조건 ④)

- **조용한 베이스 구간**(§4.3 정의)의 가격 변동폭
  `pre_pole_gain_pct` = `(구간 최고 고가 − 구간 최저 저점)/구간 최저 저점 × 100`
  이 작아야(= 폭등 전 바닥에서 조용히 횡보) 성립.
- 조건: `pre_pole_gain_pct ≤ max_pre_pole_gain`(기본 30%). 초과 시 = 바닥부터
  이미 꾸준히 오른 말기(late-stage)·연장 종목으로 보고 제외, reason
  `not_quiet_before_pole`.
- 조용한 베이스 구간이 비면(데이터 부족) 거절하지 않는다(`cond_quiet=True`).

### 4.5 깃발(횡보) 판정 (조건 ⑤⑥)

깃발 구간 = `flag_high` 이후 현재까지.
1. **길이** `flag_length_days`:
   - `≥ min_flag_days`(기본 8거래일 ≈ 10~12일 케이스 허용)
   - `≤ max_flag_days`(기본 30거래일 = 6주)
   - 미달 시 `flag_too_short`, 초과 시 `flag_too_long`.
2. **깊이** `flag_depth_pct` = `(flag_high − 깃발 내 최저저점)/flag_high × 100`.
   - `≤ max_flag_depth`(기본 **20**; 저가주 예외 CLI로 25). 초과 시 `flag_too_deep`.
3. **거래량 마름** `volume_dryup_ratio` = 최근 5거래일 평균 거래량 / 깃대 상승
   구간 평균 거래량(`pole_vol_avg`, §4.3). 깃발 후반(돌파 전) 거래량이 줄어야
   함 → 성립 조건은 `≤ 1.0`(§4.6 actionable 게이트와 동일 경계). 안 마르면
   `volume_not_drying`.
4. **타이트(`tightness_pct`)** = 최근 10거래일 (고−저)/종가 평균(%). **보고용
   지표로만 기록**, 합격 게이트로 쓰지 않는다(§4.0-3 근거).

`pattern_detected = true` ⟺ 위 §4.2~4.5의 **6개 성립 조건**을 모두 충족.
불충족 시 `pattern_detected=false` + `reason`(첫 불충족 조건) 기록.

### 4.6 피벗·상태 판정 (find-vcp와 동일 규칙)

- **기준 거래량 `pole_vol_avg`** = 깃대 구간 평균 거래량(돌파·dryup 분모로 일관).
- **`pivot_price`** = `flag_high`(돌파 매수점).
- **`pct_to_pivot`** = `(pivot_price − current_close)/pivot_price × 100`
  (양수면 피벗 아래, 음수면 이미 위).
- **`status`**:
  - `breakout` : 당일 종가 > 피벗 AND 당일 거래량 ≥ `pole_vol_avg ×
    breakout_vol_mult`(기본 1.4) — "대규모 거래량 돌파".
  - `actionable` : 피벗 0~`near_pivot_pct`%(기본 5) 근접
    (`0 ≤ pct_to_pivot ≤ 5`) AND `volume_dryup_ratio ≤ 1.0` AND 유효 깃발.
  - `failed` : 깃발 깊이가 `max_flag_depth` 초과(횡보 붕괴) 또는 종가가 깃발
    저점 하향 이탈.
  - `forming` : 위 어디에도 안 들면 형성 중.
- **`entry_ready`** = `pattern_detected AND status ∈ {breakout, actionable}`.
  '살 자리' 신호는 진짜 파워 플레이 종목에만 부여(비패턴 돌파/근접은 false).

> 임계값(깃대 100%/8주·거래량 배수, 깃발 6주/20%, 조용 구간 30%, 돌파 거래량
> 1.4배, 근접 5% 등)은 전부 CLI 인자로 노출(§6). 위 숫자는 미너비니 책 기반 기본값.

## 5. 출력 스키마

`public/data/sepa-power-play-candidates.json` (find-vcp와 동일 골격):

```jsonc
{
  "generated_at": "2026-06-29 21:00",
  "asof": "2026-06-29",
  "source": "sepa-trend-candidates.json",
  "params": { "min_flagpole_gain": 100, "max_flagpole_days": 40,
              "pole_vol_mult": 1.5, "max_pre_pole_gain": 30, "min_flag_pullback": 3,
              "min_flag_days": 8, "max_flag_days": 30, "max_flag_depth": 20,
              "breakout_vol_mult": 1.4, "near_pivot_pct": 5, "lookback_days": 120 },
  "pattern_count": 0,        // pattern_detected true 개수
  "entry_ready_count": 0,    // entry_ready true 개수(진짜 패턴 + 살 자리)
  "status_distribution": { "breakout": 0, "actionable": 0, "forming": 0, "failed": 0 },
  "candidates": [
    {
      "code": "...", "name": "...", "market": "KOSDAQ",
      "current_price": 0, "rs": 99,
      "pattern_detected": true,
      "entry_ready": true,   // pattern_detected AND status ∈ {breakout, actionable}
      "flagpole_gain_pct": 132.0,    // 깃대 상승률
      "flagpole_days": 28,           // 깃대 기간(거래일)
      "flagpole_vol_ratio": 2.4,     // 깃대 거래량 / 조용 구간 거래량
      "pre_pole_gain_pct": 8.5,      // 폭등 직전 조용 구간 상승률
      "flag_length_days": 19,        // 깃발 길이(거래일)
      "flag_depth_pct": 14.2,        // 깃발 조정폭
      "pivot_price": 0,
      "pct_to_pivot": 2.1,
      "volume_dryup_ratio": 0.74,
      "tightness_pct": 3.4,          // 보고용(합격 게이트 아님)
      "status": "actionable",
      "reason": null,                // 성립 시 null; 불성립 시 첫 불충족 조건명
      "pole_start_date": "...",      // 근거
      "flag_high_date": "..."        // 근거
    }
  ]
}
```

- `candidates`는 입력 종목 전부 포함(불성립도 reason과 함께) — 환각 방지·디버그용.
- `reason`은 `pattern_detected=false`인 모든 경로에서 채워진다
  (no_data / no_series / base_too_short / pole_gain_too_small /
  pole_volume_weak / not_quiet_before_pole / flag_too_short / flag_too_long /
  flag_too_deep / volume_not_drying / eval_error:*).
- 정렬: `entry_ready` 우선(true→false) → `status`(breakout→actionable→
  forming→failed) → `pct_to_pivot` 오름차순.

## 6. 구성 요소(코드 구조) — find-vcp 패턴 미러링

- **`scripts/screen_power_play.py`** : CLI 엔트리. 입력 로드 → 종목별 평가 →
  JSON 저장 + 콘솔 요약표(상태별 개수, entry_ready 종목 표). 한 종목 평가
  오류가 전체 런을 멈추지 않게 종목별 try/except(`eval_error:*`).
- **`scripts/canslim_lib/power_play.py`** : 순수 평가 부품 —
  `evaluate_power_play(series_dict, params) -> dict`, 보조 함수
  (깃대 탐지/깃발 측정). 입출력 순수 함수라 합성 시계열로 단위 테스트 가능.
  기존 `canslim_lib/vcp.py`·`trend_template.py`와 같은 부품 패턴.
- **`.claude/skills/find-power-play/SKILL.md`** : find-vcp SKILL.md와 동일 톤.

### CLI 인자
- `--in`(default `public/data/sepa-trend-candidates.json`)
- `--out`(default `public/data/sepa-power-play-candidates.json`)
- `--min-flagpole-gain`(100), `--max-flagpole-days`(40), `--pole-vol-mult`(1.5),
  `--max-pre-pole-gain`(30), `--min-flag-pullback`(3), `--min-flag-days`(8),
  `--max-flag-days`(30), `--max-flag-depth`(20), `--breakout-vol-mult`(1.4),
  `--near-pivot-pct`(5), `--lookback-days`(120)
- `--ticker`(단일 종목 디버그, 저장 안 함)

## 7. 불변 원칙 (기존 SEPA 스킬과 동일)

- 공유 파일 무접촉, 컷오프 금지, 환각 금지(판정 근거 JSON 포함), 자동 commit 안 함.
- `update-data` 선행 권장(최신 OHLCV). `find-power-play` SKILL.md에 명시.
- 콘솔 출력 수치(패턴 개수·상태 분포 등)는 그대로 보고, 추측·요약 금지.

## 8. 검증 계획

- `power_play.py` 순수 함수 단위 테스트(합성 시계열):
  ① 깔끔한 HTF(조용→100%/대량거래량 깃대→얕은 좁은 깃발) → `pattern_detected`,
  ② 깃대 <100% → false(`pole_gain_too_small`),
  ③ 깃대 거래량 약함 → false(`pole_volume_weak`),
  ④ 폭등 전 이미 연장 → false(`not_quiet_before_pole`),
  ⑤ 깃발 >20% 깊음 → false(`flag_too_deep`),
  ⑥ 깃발 너무 김(>6주) → false(`flag_too_long`),
  ⑦ 피벗 돌파 + 대량거래량 → `status=breakout`.
- 실제 트렌드 통과 종목으로 1회 풀런 → 상태 분포 합리성 육안 확인(대부분
  미검출/forming, 검출은 극소수 — 100% 깃대는 희귀).
- `--ticker`로 알려진 폭등 종목 하나를 찍어 깃대·깃발·피벗이 차트와 맞는지 대조.

## 9. 미해결/후속

- 임계값 기본치는 미너비니 책 기반 추정 — 한국 종목으로 백테스트 튜닝은 후속.
- "조용한 출발"·"대규모 거래량"의 임계값(조용 구간 길이·상승률 한도·거래량
  배수)은 가장 정성적이라 백테스트 민감도 점검 후속 과제.
- find-vcp와의 결과 중복(한 종목이 두 패턴에 동시 검출) 처리·통합 뷰는 별도.
- SEPA 다음 단계(리스크: 손절폭·비중)는 별도 spec.
