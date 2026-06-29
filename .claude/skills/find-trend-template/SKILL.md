---
name: find-trend-template
description: >
  SEPA 종목 발굴의 첫 관문. Minervini 트렌드 템플레이트 8조건을 만족하는
  KOSPI+KOSDAQ 종목을 RS 80(SEPA 실전 기준)으로 추려 SEPA 전용 후보 파일
  (sepa-trend-candidates.json)에 저장한다. 공유 trend-template-candidates.json·
  make-hero·페이지 데이터는 일절 건드리지 않는다. 사용자가 "/find-trend-template",
  "SEPA 1단계", "추세 통과 종목 찾아줘", "트렌드 템플레이트로 SEPA 후보 추려줘"
  등을 요청할 때 사용.
---

# find-trend-template — SEPA 1단계: 추세 선별

SEPA(Specific Entry Point Analysis) 종목을 찾는 파이프라인의 **첫 단계**.
마크 미너비니의 **트렌드 템플레이트 8조건**을 만족하는 종목만 남겨, 이후
하위 스킬(베이스/VCP 분석 등)의 입력이 될 **SEPA 전용 후보 리스트**를 만든다.

이 스킬은 **얇은 빌딩블록**이다 — 스크리너 1단계만 실행하고, C 점수·코드33·
자동 commit 같은 일은 하지 않는다.

## 정의 원본 (트렌드 템플레이트 8조건)

`research/oneil-model-book/trend_template.md` 가 정의 원본. 요약:

1. 주가가 150일·200일 이평선 위
2. 150일 이평선이 200일 이평선 위
3. 200일 이평선이 최소 1개월(이상적으로 4~5개월) 상승 추세
4. 50일 이평선이 150일·200일 이평선 위
5. 주가가 50일 이평선 위
6. 주가가 52주 신저가보다 최소 30% 위
7. 주가가 52주 신고가의 25% 안 (가까울수록 좋음)
8. RS(상대강도) ≥ 합격선 — **이 스킬 기본 80** (SEPA 실전 기준)

## 불변 원칙

- **공유 파일 무접촉**: `public/data/trend-template-candidates.json` 을 절대
  덮어쓰지 않는다(make-hero·`/stocks/trend-template` 페이지가 RS 70으로 공유
  중인 파일). 반드시 `--out` 으로 SEPA 전용 파일에만 쓴다.
- **컷오프 금지**: 시총·거래대금·가격 컷오프를 추가하지 않는다
  ([screener-no-cutoff] 메모리 준수).
- **환각 금지**: 통과 종목 수·RS 등은 콘솔 출력 그대로 보고. 추측·요약 금지.

## 사전 조건

- **최신 데이터로 돌리려면 먼저 `update-data` 스킬 실행** — OHLCV 시세 행렬을
  최신 영업일까지 갱신한다(캐시 삭제 없음). 안 돌리면 행렬에 마지막으로 쌓인
  날짜 기준으로 선별됨.
- `.env` 의 `DATA_GO_KR_KEY` (공공데이터 일봉 — OHLCV 행렬 필수).
- OHLCV 행렬이 최초 1회 백필돼 있어야 함. 비어 있으면 첫 실행이 ~400영업일을
  채우느라 느림(`pwsh -File scripts/canslim_parallel.ps1` 한 번이면 채워짐).
  이후엔 행렬 캐시 hit 으로 빠름.
- 평가 부품: `scripts/canslim_lib/trend_template.py`.

## 실행 절차 (1줄)

```
python scripts/screen_trend_template.py --rs-min 80 --out public/data/sepa-trend-candidates.json --save
```

- 산출: `public/data/sepa-trend-candidates.json`
  (구조는 기존 candidates JSON과 동일: `candidates[]`, `market_status`,
  `all_pass_count`, `rs_min` 등)
- 소요: ~1분 (행렬 캐시 hit 시), 첫 실행/캐시 비운 직후 ~3-5분.

### 옵션

- `--rs-min 70` : 정의서 기본선으로 완화(미너비니 책 기준). SEPA 실전은 80 권장.
- `--market KOSPI` / `--market KOSDAQ` : 한 시장만.
- `--asof YYYY-MM-DD` : 과거 시점 기준(룩어헤드 방지 백테스트용).

## 결과 확인

- 콘솔의 `✨ 8개 모두 통과: N종목` — 보통 RS 80 기준이면 정의서 70보다 종목 수
  적음. 강세장에서 수십~100여 종목.
- 산출 JSON 의 `market_status` 가 `Stage 2`(상승 추세장)인지 — 약세장이면
  통과 종목이 급감하는 게 정상.
- `candidates[].all_pass == true` 인 종목이 SEPA 다음 단계 입력.

## 다음 단계 (SEPA 파이프라인)

이 스킬 통과 종목은 SEPA의 다음 하위 스킬(베이스/VCP 패턴 분석, 진입 시점
분석 등)의 입력이 된다. 트렌드 템플레이트는 **"추세가 살아있는 종목"** 만
남기는 관문이고, 실제 매수 시점은 다음 단계에서 정성·패턴 분석으로 좁힌다.

## 안 하는 것

- C 점수·코드33 산출 — 그건 기존 `trend-template` 스킬(풀 파이프라인) 영역.
- 공유 `trend-template-candidates.json` 갱신 — 항상 `--out` 으로 분리.
- 자동 git commit/push — SEPA 단일 단계라 배포는 부모 `sepa` 스킬/사용자 판단.
- 자동 매매 신호 — 추세 관문일 뿐, 진입 결정은 다음 단계.
