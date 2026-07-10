---
name: find-buy-recommendations
description: >
  SEPA 매수 추천 리스트. 검출된 VCP/3C/파워플레이 후보 중 '초수익 잠재력 점수'
  (직전 상승폭·RS·RS선 신고가·RS선 선행 — 방법충실 돌파 백테스트로 검증)를 매겨
  점수순으로 정렬해 sepa-buy-recommendations.json 에 저장한다. 후보 JSON·OHLCV
  캐시·시장지수(FDR)만 사용, 공유/후보 파일 무접촉·자동커밋 없음. 사용자가
  "/find-buy-recommendations", "매수 추천 리스트", "초수익 후보 뽑아줘",
  "오늘 뭐 살까", "SEPA 추천" 등을 요청할 때 사용.
---

# find-buy-recommendations — 매수 추천 리스트(초수익 잠재력 순)

검출된 SEPA 후보(VCP/3C/파워플레이) 중 **초수익 잠재력**이 높은 순으로 매수 추천을
뽑는다. 점수 정의·검증 근거: `scripts/canslim_lib/superperf.py`
(방법충실 돌파 백테스트 2022~2026 — **점수 4+ = 6개월 내 더블(+100%) 도달률 36%** vs 0~1점 15%).

## 사전 조건
- 먼저 `find-vcp` · `find-power-play` · `find-3c` 실행(검출된 후보 파일 존재).
- 입력: `public/data/sepa-{vcp,power-play,power-play-all,3c}-candidates.json`.

## 실행 (1줄)
```
python scripts/screen_buy_recommendations.py
```
- 산출: `public/data/sepa-buy-recommendations.json`
- 콘솔: 초수익 점수순 상위 종목 표(점수·근거·RS·직전상승·매수배지).

### 옵션
- `--min-score N` : 포함 최소 점수(기본 3; 0~1점=검증상 엣지 없어 제외).
- `--out PATH` : 출력 경로 변경.

## 결과 확인
- **초수익 잠재력 점수(0~6)**: 직전 상승폭(100%+=2·50~100%=1, 최강 예측자)·RS(90+=2·80+=1)·
  RS선 신고가(주가÷지수 선이 최근 10일 내 신고가=+1)·RS선 선행(RS선이 주가보다 먼저 신고가=+1).
- **정렬 = 점수 내림차순(동점 RS)**. 매수 타이밍(`entry_tier`: ready/near/far)은 배지로
  **표시만** — 정렬엔 반영 안 함(사용자 확정: 초수익 점수 순수).
- **검출된 후보만 채점**(forming·failed 제외) = `/stocks/sepa` 페이지 표시와 일치.
- 각 종목: `superperf_score`, `score_reasons`, `prior_adv_pct`, `dist_52wh`, `pattern`, `entry_tier`.

## 안 하는 것
- 전 종목 스캔(검출된 후보만) · 후보/공유 파일 갱신 · 자동 commit(부모 `sepa`가 커밋).
- 패턴은 점수에 미반영(진입 시점용). FDR 지수 수집 실패 시 RS·상승폭만으로 채점(폴백).
