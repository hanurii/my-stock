---
name: trend-template
description: >
  Minervini 트렌드 템플레이트 8조건으로 KOSPI+KOSDAQ 전 종목을 거른 뒤,
  통과 종목에 CAN SLIM C 원칙 점수를 부여하고, 마지막으로 "코드 33"
  (EPS·매출·순이익률 세 지표가 모두 3분기 연속 단조 가속) 종목을 추출하는
  3단계 풀스캔 파이프라인. 사용자가 "트렌드 템플레이트 돌려줘",
  "/trend-template", "code 33 확인", "트렌드 + 캔슬림 + 가속도" 등을
  요청할 때 사용.
---

# 트렌드 템플레이트 풀 파이프라인

세 단계를 순서대로 실행해 *추세 + 펀더멘털 + 가속도* 셋 다 만족하는
"황금 후보" 종목 리스트를 만든다. 정의 원본은
`research/oneil-model-book/trend_template.md`.

## 불변 원칙

- **순서 엄수**: 1 → 2 → 3 (각 단계가 이전 단계 JSON 을 입력으로 사용).
- **컷오프 금지**: 1단계 스크리너는 시총·거래대금·가격 컷오프를 적용하지
  않는다 ([screener-no-cutoff] 메모리 준수).
- **DART 캐시 신뢰**: 과거 연도 DART 데이터는 영구 캐시. 두 번째 실행부터는
  대부분 cache hit (수십 초 단위). 첫 실행이거나 캐시 비운 직후만 느림.
- **환각 금지**: 종목이 코드 33 통과로 나타나면 그 근거 (각 가속 플래그·
  YoY 수치) 가 출력 JSON 에 다 들어있다. 추측·요약·일반화 금지.

## 사전 조건

- `.env` 에 `DART_API_KEY` 설정.
- Python 3.11+ 와 캔슬림 라이브러리 (`scripts/canslim_lib/`).

## 실행 절차

### 1단계: 전 종목 트렌드 템플레이트 스크리닝

```
python scripts/screen_trend_template.py --save
```

- 산출: `public/data/trend-template-candidates.json`
- 체크: `all_pass_count` (보통 100-200 종목), `market_status` 가 Stage 2 인지
- 소요: ~1 분 (Naver 일봉 캐시 hit 시), 첫 실행 ~3-5분

### 2단계: 통과 종목에 C 원칙 점수·게이트 부여

```
python scripts/screen_trend_template_c_score.py
```

- 산출: `public/data/trend-template-c-scored.json`
- 체크: `c_gate_pass_count`, `tier_distribution`
- 소요: ~3 분 (DART 캐시 hit 시), 첫 실행 ~5-10분

### 3단계: 코드 33 (EPS·매출·순이익률 3분기 가속) 판별 + 콘솔 출력

```
python scripts/screen_trend_template_code33.py
```

- 진입 필터: 2단계에서 C 게이트 통과 또는 C 점수 ≥ 70
- 산출: `public/data/trend-template-code33.json`
- 콘솔: 통과 종목 표 (코드·종목명·시장·시총·유통주식수·RS·C점수·각 YoY)
- 소요: 첫 실행 ~3-5분 (분기 NI fetch), 두 번째 이후 ~1분

옵션:
- `--c-min N` : 진입 C 점수 컷 (default 70)
- `--no-save` : JSON 저장 생략, 콘솔만

## 결과 해석

| 지표 | 의미 |
|---|---|
| 시가총액 (억원) | 매매 규모 판단 — 너무 작으면 진입·청산 불리 |
| 유통주식수 | pdata `lstgStCnt` (상장주식수 = 유통주식수 간주, 자사주 제외 없음) |
| RS | 1년 수익률 백분위 (1-99). 트렌드 템플레이트 기준 ≥ 70 |
| C 점수 | EPS YoY·가속·매출 3축 종합 (0~100+). 게이트는 별도 5조건 통과 |
| EPS YoY% | 최신 분기 EPS 가 전년 동기 대비 (분모 절댓값 floor 100원) |
| 매출 YoY% | 최신 분기 매출 (분모 floor 10억원) |
| 순이익률 % | 분기 순이익 / 분기 매출 |
| 순이익률 YoY‱ | 전년 동기 순이익률 대비 변화 (단위 ‱·1/10,000) |

**코드 33 통과 = 추세 강세 + 펀더멘털 가속 + 수익성 가속 셋 다 만족.**
실제 매수 결정에는 산업 사이클·경쟁 구도·최근 공시 등 정성 변수를 별도
확인할 것 (이 파이프라인은 양적 후보 좁히기 단계).

## 점수 흔들림 대응

- 같은 종목·같은 분기인데 점수가 시점에 따라 흔들리면:
  1. Naver 5분기 윈도우가 옮겨가 시계열 일부가 빠지는 자연 흔들림 — ±1~3점.
  2. DART 잠정실적이 확정으로 바뀌어 마지막 분기 EPS·매출이 변하는 경우.
- 시계열 의심 시 (예: prev_yoy 가 None) → 분기 NI/EPS/매출 시계열을 직접
  확인. 13 분기 시계열이 정상. 8 분기 등 짧으면 DART 캐시 무효화
  (`dart_cache.clear_quarter()`) 후 재실행.

## 관련 파일

- 정의: `research/oneil-model-book/trend_template.md`
- 1단계 평가 부품: `scripts/canslim_lib/trend_template.py`
- C 평가 부품: `scripts/canslim_lib/criteria.py` (evaluate_c_detailed,
  passes_c_gate, compute_c_score)
- 분기 NI: `scripts/canslim_lib/fetch.py` (fetch_dart_quarterly_ni_history)
- 캐시: `scripts/canslim_lib/dart_cache.py` (get/put_quarter_ni)

## 안 하는 것

- 자동 매매 신호 생성 — 정성 분석 별도 필요.
- 자사주 제외 유통주식수 — `lstgStCnt` 그대로 사용.
- 점수 의미 일반화 — 결과 JSON 의 raw 수치로 판단.
