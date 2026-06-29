# find-vcp — SEPA 2단계: VCP 베이스·피벗 탐지 (설계 spec)

작성일 2026-06-29 · 상태: 설계 승인됨, 구현 계획 대기

## 1. 배경·목적

마크 미너비니 SEPA(Specific Entry Point Analysis)를 한국 시장에 적용하는
파이프라인의 **2단계**. 1단계 `find-trend-template`(추세 템플릿 8조건 통과)이
"추세가 살아있는 종목"을 추렸다면, 이 단계는 그 종목들의 **차트 베이스가
미너비니 VCP(Volatility Contraction Pattern, 변동성 수축 패턴)인지**를
판별하고, **피벗(돌파 매수점)**과 **현재 진입 가능 상태**를 산출한다.

### 방법론 선택 (의도적 결정)

이 프로젝트의 자체 연구(`research/oneil-model-book/buy_timing.md`)는 한국에서
교과서 VCP/거래량 돌파가 "조용한 눌림목 재가속"보다 열위라고 본다. 그럼에도
사용자는 **미너비니 교과서에 충실한 VCP/피벗 돌파**를 이번 단계의 방법론으로
선택했다(SEPA 학습·적용 목적). 프로젝트 5신호(눌림목 재가속)는 이번 범위에서
제외하며, 추후 별도 하위 스킬로 둘 수 있다.

## 2. 범위

### 하는 것
- 입력: `public/data/sepa-trend-candidates.json`의 `all_pass == true` 종목만 분석.
- 각 종목의 일봉(OHLCV 캐시)에서 VCP 베이스를 탐지하고 지표·상태를 산출.
- 산출: `public/data/sepa-vcp-candidates.json`.

### 안 하는 것
- 수급(외인/기관 순매수) 신호 — 사용자 확정 제외(VCP 돌파 거래량은 OHLCV로 충분).
- 프로젝트 자체 5신호(눌림목 재가속) — 이번 범위 아님.
- 실제 매매·손절·비중 신호 — 후보 좁히기까지. 리스크 규칙은 다음 단계.
- 공유 파일(`trend-template-candidates.json` 등) 갱신 — 항상 전용 출력 파일.
- 자동 git commit/push.

## 3. 데이터 입력

- **OHLCV 캐시**: `.cache/ohlcv/series/<code>.json` (수정주가 일봉, 최신 400영업일).
  `find-vcp` 실행 전 `update-data`로 최신화 권장(선행 스킬).
- **대상 종목 목록**: `sepa-trend-candidates.json`의 `candidates[]` 중 `all_pass`.
- 종목당 필요한 시계열: `dates`, `closes`, `highs`, `lows`, `volumes`.

## 3.5 알고리즘 출처 (정직한 구분)

- **개념 = 마크 미너비니.** VCP·피벗·수축(contraction)·거래량 마름·"마지막
  수축 고점 돌파 시 매수"·"수축 보통 2~6회" 등 정성 원칙은 미너비니의
  『Trade Like a Stock Market Wizard』(2013)·『Think & Trade Like a
  Champion』(2016)에서 옴.
- **구체 수치·계산 규칙 = 이 프로젝트의 공학적 번역(미너비니 원전 아님).**
  미너비니는 계산식/코드를 공개한 적 없음(VCP는 눈으로 보는 정성 패턴).
  따라서 ZigZag ±8%, 단조 수렴 허용오차 ×1.15, 최종 수축 ≤10%, 돌파 거래량
  1.4배, lookback 120일 등은 정성 개념을 기계 판정으로 옮기며 고른 **기본값**일
  뿐 책의 "정답"이 아니다. ZigZag도 미너비니 것이 아닌 일반 기술적 분석 도구.
- 그래서 이 수치들은 전부 CLI 인자로 노출하고(§6), 한국 종목 백테스트 튜닝을
  후속 과제로 둔다(§9). "무엇을 찾는가"=미너비니, "어떻게 숫자로 판정하나"=구현 선택.

## 4. VCP 판정 알고리즘

### 4.1 베이스 구간 식별
1. 분석 lookback = 최근 **120거래일**(약 6개월; 너무 짧은 베이스도 잡되 과거
   추세는 trend-template이 이미 보장).
2. 베이스 시작 = lookback 내 **최고 종가(또는 고가)** 지점. 그 고점 이후
   현재까지가 후보 베이스 구간.
3. 베이스 최소 길이 = **10거래일**(이보다 짧으면 `vcp_detected=false`, 사유 기록).

### 4.2 스윙 탐지 — ZigZag(% 임계)
- 베이스 구간 종가(또는 고가/저가) 시계열에 ZigZag 적용.
- **임계값 기본 `--zigzag-pct 8`**(%): 직전 극점 대비 ±8% 이상 역행 시 새 스윙
  확정. 노이즈 제거·교대 고/저점 추출.
- 결과 = 시간순 교대 스윙점 리스트 `[(date, price, kind)]`, kind ∈ {high, low}.

### 4.3 수축(contraction) 수열
- 인접한 (스윙고 → 다음 스윙저) 쌍마다 수축 깊이 =
  `(swing_high - next_swing_low) / swing_high * 100` (%).
- 수축 리스트 = 베이스 내 모든 (고→저) 깊이를 시간순으로.

### 4.4 VCP 성립 조건
모두 만족 시 `vcp_detected = true`:
1. 수축 횟수 **T ∈ [2, 6]**.
2. **수축 단조 수렴**: 각 수축이 직전보다 얕음. 허용오차 = 직전 깊이의
   **×1.15**까지 용인(`depth[i] <= depth[i-1] * 1.15`). (완벽 단조 강요 시
   현실 베이스를 과도 탈락시키므로 완화.)
3. **거래량 수축**: 베이스 후반 1/3 구간 평균 거래량 < 베이스 전반 1/3 구간
   평균 거래량(거래량이 마름).
4. **최종 수축 타이트**: 마지막 수축 깊이 ≤ **`--max-final-depth 10`**(%).

성립 안 하면 `vcp_detected=false` + `reason`(어느 조건 불충족) 기록.

### 4.5 피벗·상태 판정
- **기준 거래량 `base_vol_avg`** = 베이스 구간 평균 거래량(베이스가 50거래일보다
  길면 최근 50거래일). 아래 돌파·dryup 계산의 분모로 일관 사용.
- **피벗 가격 `pivot_price`** = 마지막(최신) 스윙 고점.
- **`pct_to_pivot`** = `(pivot_price - current_close) / pivot_price * 100`
  (양수면 피벗 아래, 음수면 이미 위).
- **`volume_dryup_ratio`** = 최근 5일 평균 거래량 / `base_vol_avg`.
- **`tightness_pct`** = 최근 10거래일 (고−저)/종가 평균(%) — 작을수록 타이트.
- **`status`**:
  - `breakout` : 당일 종가 > 피벗 AND 당일 거래량 ≥ `base_vol_avg` ×1.4.
  - `actionable` : 피벗 −0~5% 근접(`0 <= pct_to_pivot <= 5`) AND
    `volume_dryup_ratio <= 1.0` AND 타이트.
  - `failed` : 마지막 수축이 직전보다 깊어짐(수렴 실패) 또는 종가가 베이스
    저점 하향 이탈.
  - `forming` : 위 어디에도 안 들면 형성 중.

> 임계값(zigzag-pct, max-final-depth, 돌파 거래량 배수 1.4, 근접 5% 등)은 전부
> CLI 인자로 노출해 튜닝 가능하게 한다. 위 숫자는 미너비니 책 기반 기본값.

## 5. 출력 스키마

`public/data/sepa-vcp-candidates.json`:

```jsonc
{
  "generated_at": "2026-06-29 21:00",
  "asof": "2026-06-29",
  "source": "sepa-trend-candidates.json",
  "params": { "zigzag_pct": 8, "max_final_depth": 10, "breakout_vol_mult": 1.4,
              "lookback_days": 120 },
  "vcp_count": 0,            // vcp_detected true 개수
  "status_distribution": { "breakout": 0, "actionable": 0, "forming": 0, "failed": 0 },
  "candidates": [
    {
      "code": "240810", "name": "원익IPS", "market": "KOSDAQ",
      "current_price": 0, "rs": 99,
      "vcp_detected": true,
      "num_contractions": 3,
      "contractions": [22.5, 13.1, 7.4],     // 시간순 깊이%
      "base_length_days": 41,
      "base_depth_pct": 22.5,                // 최대(첫) 수축
      "pivot_price": 0,
      "pct_to_pivot": 2.3,
      "volume_dryup_ratio": 0.78,
      "tightness_pct": 3.1,
      "status": "actionable",
      "swings": [ {"date":"...","price":0,"kind":"high"}, ... ],  // 근거
      "reason": null          // vcp_detected=false 일 때만 사유
    }
  ]
}
```

- `candidates`는 입력 종목 전부 포함(vcp 불성립도 reason과 함께) — 환각 방지·디버그용.
- 정렬: `status`(breakout→actionable→forming→failed) → `pct_to_pivot` 오름차순.

## 6. 구성 요소(코드 구조)

- **`scripts/screen_vcp.py`** : CLI 엔트리. 입력 로드 → 종목별 평가 → JSON 저장 +
  콘솔 요약표(상태별 개수, actionable/breakout 종목 표).
- **`scripts/canslim_lib/vcp.py`** : 순수 평가 부품 — `zigzag(series, pct)`,
  `find_contractions(swings)`, `evaluate_vcp(series_dict, params) -> dict`.
  기존 `canslim_lib/trend_template.py`와 같은 부품 패턴.
- 단위 테스트 가능: `vcp.py`는 입출력이 순수 함수라 합성 시계열로 검증.

### CLI 인자(제안)
- `--in`(default `public/data/sepa-trend-candidates.json`)
- `--out`(default `public/data/sepa-vcp-candidates.json`)
- `--zigzag-pct`(8), `--max-final-depth`(10), `--breakout-vol-mult`(1.4),
  `--lookback-days`(120), `--ticker`(단일 종목 디버그)

## 7. 불변 원칙 (기존 SEPA 스킬과 동일)

- 공유 파일 무접촉, 컷오프 금지, 환각 금지(판정 근거 JSON 포함), 자동 commit 안 함.
- `update-data` 선행 권장(최신 OHLCV). `find-vcp` SKILL.md에 명시.

## 8. 검증 계획

- `vcp.py` 순수 함수 단위 테스트: 합성 시계열로 ① 수렴 수축 → vcp_detected,
  ② 확대 수축 → false, ③ 거래량 안 마름 → false, ④ 피벗 돌파 → breakout.
- 실제 입력(70 트렌드 통과 종목)으로 1회 풀런 → 콘솔 상태 분포가 합리적인지
  (대부분 forming, 소수 actionable/breakout) 눈으로 확인.
- `--ticker`로 알려진 종목 하나를 찍어 스윙·수축·피벗이 차트와 맞는지 대조.

## 9. 미해결/후속

- 임계값 기본치는 미너비니 책 기반 추정 — 한국 종목으로 백테스트 튜닝은 후속.
- 베이스 유형(컵/플랫/더블바텀) 분류는 이번 범위 밖(수축 수열만으로 VCP 판정).
- SEPA 3단계(리스크: 손절폭·비중)는 별도 spec.
