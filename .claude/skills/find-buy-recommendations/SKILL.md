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

## 실행 (2줄 — 추천 산출 + 살아있는 검증 원장 갱신)
```
python scripts/screen_buy_recommendations.py
python scripts/track_buy_recommendations.py
```
- 산출: `public/data/sepa-buy-recommendations.json` (오늘 추천)
      + `public/data/sepa-buy-rec-ledger.json` (원장 — 과거 추천의 전방 성과 누적 결착)
- 콘솔: 초수익 점수순 상위 종목 표 + 살아있는 검증 요약(점수 구간별 실전 성과).

### 살아있는 검증(track_)
매일 추천을 원장에 기록하고 전방 성과(최대상승·+20/-10·경과일)를 OHLCV로 재결착 →
"4+점 추천이 실제로 대박나나"를 실데이터로 누적 검증. **몇 달 쌓여야 유의미**(단기 스냅샷은
조정·변동성 노이즈). 익스텐디드까지 포함돼 있어 실전 해석은 진입권 배지 기준으로.

### 옵션
- `--min-score N` : 포함 최소 점수(기본 3; 0~1점=검증상 엣지 없어 제외).
- `--out PATH` : 출력 경로 변경.

## 결과 확인
- **초수익 잠재력 점수(0~6)**: 직전 상승폭(100%+=2·50~100%=1, 최강 예측자)·RS(90+=2·80+=1)·
  RS선 신고가(주가÷지수 선이 최근 10일 내 신고가=+1)·RS선 선행(RS선이 주가보다 먼저 신고가=+1).
- **정렬 = 점수 내림차순(동점 RS)**. 매수 타이밍(`entry_tier`: ready/near/far)은 배지로
  **표시만** — 정렬엔 반영 안 함(사용자 확정: 초수익 점수 순수).
- **검출된 후보만 채점**(forming·failed 제외) = `/stocks/sepa` 페이지 표시와 일치.
- 각 종목: `superperf_score`, `score_reasons`, `prior_adv_pct`, `dist_52wh`, `pattern`, `entry_tier`,
  `gate_near`(관문 임박 — 트렌드 이평선 ①⑤만 미달 종목 표시, 페이지 ⏳배지·정렬 무관여),
  `gate_near_reasons`(미달 사유 목록, 예 `"⑤ 50일선 -2.3%"` — 트렌드 산출에서 그대로 승계,
  페이지 종목코드 줄에 표시).
- **청산 부담 N/M**: 실제 슬롯 `strategy_params.POSITION_KRW`(=1,000만, 투자금 늘리면 여기만 수정)
  기준. **N** = `burden_pct` = 1,000만원 매수 시 최근 20일 평균 거래대금(`adv_20d_eok`) 대비 %,
  **M** = `split_risk_krw` = ADV20×5% = 분할매도 가능성 시작 금액(이 금액까지는 🟢).
  밴드(`liquidity`): 🟢ok N<5 · 🟡caution 5≤N<30 · 🔴danger N≥30 — 실측 손절 34왕복 슬리피지 기준
  (<5% 비용≈0, ≥30% 실통증: 에스에스알 32%·로스웰 72%). 분모가 ADV50이 아닌 ADV20인 이유:
  실측 손절일 거래대금 중앙값=ADV20의 1.02배, ADV50은 대양금속 유동성 붕괴(11.9억→5.7억)를 가림.
  구 필드 `adv_50d_eok`·`position_pct_of_adv`·`one_day_exit`는 하위 호환 유지.
  에스에스알·로스웰 청산 불능 사고 후 도입(26-08-08), N/M 개편 26-08-17.
  파일 상단 `position_krw`에 기준 금액 기록.
- **🚫 기관 수요 유보**: `sepa-demand-watchlist.json`(사용자 직접 관리)에 등록된 종목은 숨기지
  않고 **순위만 제외**(점수 무관 최하단 + `demand_watch` 필드 부착 → 페이지 딤드 표시).
  한국공항 반복 손절 사례(저거래량 돌파+분산 거래량 = 기관 매집 부재) 후 도입(26-08-08).
  기관 수요가 붙으면 목록에서 항목을 제거해 복귀시킨다.

## 안 하는 것
- 전 종목 스캔(검출된 후보만) · 후보/공유 파일 갱신 · 자동 commit(부모 `sepa`가 커밋).
- 패턴은 점수에 미반영(진입 시점용). FDR 지수 수집 실패 시 RS·상승폭만으로 채점(폴백).
