# 보유 종목 양면 성적표 — 매집 신호 + MVP + 확장 + watch 등급 설계

날짜: 2026-07-05
상태: 설계 확정(사용자 승인 완료 — 목업 기준) · 스펙 리뷰 대기
선행: `2026-07-05-holdings-rules-v2-design.md`(위반 규칙 v2, 프로덕션 반영 완료)
목업(승인본): https://claude.ai/code/artifact/9f2b4bdd-4acb-4226-aac1-c01ad6d6e82f
  "보유 종목 점검 — 양면 성적표"(카드 레이아웃·툴팁·배지·watch 마크의 시각 정본)

## 목적

현재 보유 점검은 **위반(빨간불)만** 본다. 여기에 미너비니 책 1장의 **"정상 행동(매집 신호)"**
축을 더해 **양면 성적표**로 만든다. 두 축은 독립이다:

| 축 | 뜻 | 답하는 질문 |
|----|----|-------------|
| 위반(기존) | 리스크 | "줄이거나 도망칠까?" |
| **매집 신호(신규)** | 매집·강도 | "계획대로 잘 가나? 확신 갖고 보유?" |

추가로 **확장(피벗 대비 상승폭)** 표시와, 기존 🟡 소프트 신호를 정식 **watch 등급**으로 승격한다.

## 개념 근거 (웹 확인 포함)

- **MVP(Momentum·Volume·Price)** = 돌파 후 15일에 M·V·P 동시 충족 → 대형 기관 매집 강신호
  ("사기 힘든 주식"). **매집 신호**이지 "지금 사라"가 아니다.
- **확장(Extended)** ≠ MVP. 주가가 피벗(매수 지점)에서 너무 멀리(+10%↑) 벗어난 **위치**.
  신규 진입엔 추격이라 손익비가 나쁨. 좋은 주식이어도 확장될 수 있다.
- 관계(D. Ryan): MVP인데 **이미 확장**이면 뒤늦은 신호(단기 과열). 우리는 **이미 보유**한
  종목을 보므로 확장은 "사지 마라"가 아니라 **참고**다.
- 출처: ChartMill "Think & Trade Like a Champion Part 2"(MVP: M 12/15·V +25%·P +20%),
  finermarketpoints SEPA/VCP 가이드(확장 추격 금지).

## 사용자 확정 사항

- 명칭은 "확신도"가 아니라 **"매집 신호"**.
- **등급(강/중/약) 없음** → 각 조건을 **체크리스트(✓/○/―)** 로.
- MVP는 이모지가 아니라 **텍스트 `MVP` 배지**. M·V·P 셋 다 충족 시 신호 배지 옆에 표시.
- **확장% 칩**과 MVP 배지를 **둘 다** 유지(둘은 다른 개념).
- 매집 신호·MVP 각 항목에 **호버 툴팁**(상세 설명). 숫자는 라벨과 함께("상승 12 · 하락 3").
- 확장 반전 경고 로직은 이번 범위 밖(YAGNI) — 확장은 % 표시로만.

## 아키텍처 (기존 v2 위에 얹기)

순수 판정 모듈 `sell_rules.py`에 함수 2개 추가 + 소프트 케이스 2곳을 watch로 변경.
실행 스크립트가 결과를 JSON에 추가. 페이지가 새 필드를 렌더. 신호(🔴🟠🟢)·위반 개수
로직은 **무변경**(매집 신호·MVP·확장·watch는 위반으로 세지 않는다).

```
sell_rules.py
  + evaluate_accumulation(series, bi)  → 매집 신호 3종
  + evaluate_mvp(series, bi)           → M·V·P
  ~ rule_consecutive_lower_lows: 저거래량 저점경신 pass→watch
  ~ rule_breakout_failure: 유예 관찰중 pass→watch
  ~ evaluate_holding: 반환에 accumulation·mvp·extension_pct 추가
screen_holdings_feedback.py            → 그대로(evaluate_holding 결과를 직렬화)
SepaHoldingsSection.tsx                → 배지·매집 패널·툴팁·watch 렌더(목업대로)
```

## 데이터 스키마 추가 (`sepa-holdings-feedback.json` 종목마다)

기존 필드 유지 + 아래 추가. `rules[].status`에 `"watch"` 값 추가.

```json
"extension_pct": 4.0,            // (현재가/피벗 − 1)×100. 피벗 없으면 null
"accumulation": {
  "window": "D+3/15",           // 15일 미만이면 "D+n/15", 이상이면 "15일 완료"
  "elapsed": 3,
  "signals": [
    { "id": "up_days_dominant", "status": "met", "detail": "상승 3 · 하락 1" },
    { "id": "quality_closes",   "status": "met", "detail": "좋은 2 · 나쁜 0" },
    { "id": "up_streak_7",      "status": "unmet", "detail": "최고 3일" }
  ]
},
"mvp": {
  "status": "pending",          // yes / no / pending(15일 전)
  "m": { "ok": null, "detail": "3/15일 (판정 전)" },
  "v": { "ok": null, "detail": "판정 전" },
  "p": { "ok": null, "detail": "+1.7%" }
}
```

`status` 값 정의:
- 매집 신호: `met`(✓) / `unmet`(○) / `pending`(―, 비교할 날이 아직 없음).
- MVP: `yes`(배지 표시) / `no` / `pending`(돌파 후 15거래일 미경과).

## 매집 신호 계산: `evaluate_accumulation(series, bi)`

창 = 돌파 다음 날부터 최대 15거래일(`bi+1 … min(bi+15, n-1)`). `elapsed = (n-1) - bi`.
15일 이상 경과하면 **첫 15일로 고정**(이후 날은 안 봄 — "출발이 좋았나"는 초기 창 질문).
15일 미만이면 진행 중 창으로 부분 계산(라이브).

세 신호(기존 `rule_weak_days_dominant`의 up/down/good/bad 계산을 재사용):

| id | 라벨 | met 조건 | detail |
|----|------|----------|--------|
| up_days_dominant | 상승일 우세 | 상승 마감일 > 하락 마감일 | `상승 U · 하락 D` |
| quality_closes | 양질의 종가 | 좋은 마감 > 나쁜 마감. 좋은=종가>(고+저)/2, 나쁜=종가<(고+저)/2. **tight day(당일 (고−저)/종가 < 1%)는 나쁜 마감서 제외**(건설적 눌림) | `좋은 G · 나쁜 B` |
| up_streak_7 | 연속 상승 7일↑ | 최고 연속 상승 마감 ≥ 7일 | `최고 S일` |

- up/down = 종가 vs 전일 종가. 보합·고가=저가 날은 각 카운트서 제외(규칙⑤와 동일).
- 비교할 날이 0일이면 해당 신호 `pending`. up_streak_7은 7일 미만이면 `unmet`(진행 가능).
- 반환: `{ "window", "elapsed", "signals": [ {id, status, detail} × 3 ] }`.

## MVP 계산: `evaluate_mvp(series, bi)`

돌파 후 15거래일 판정. `elapsed < 15`이면 전체 `status: "pending"`(각 m/v/p ok=null,
단 계산 가능한 값은 detail에 노출: 예 P는 현재까지 상승률).

`elapsed ≥ 15`일 때 창 = `bi+1 … bi+15`(15일):
- **M**: 창 내 상승 마감일 ≥ 12 → ok. detail `k/15일 상승`.
- **V**: mean(창 거래량) ≥ 1.25 × mean(돌파 직전 15일 `bi-15 … bi-1` 거래량) → ok.
  직전 표본 부족(< 5일)이면 ok=null, detail "거래량 표본 부족". detail `직전 대비 r배`.
- **P**: max(창 종가) / 종가[bi] − 1 ≥ 0.20 → ok. detail `+p%`.
- `status = "yes"` iff M·V·P 모두 ok, 아니면 `"no"`.
- 반환: `{ "status", "m": {ok, detail}, "v": {ok, detail}, "p": {ok, detail} }`.

돌파일 인덱스 `bi`는 `find_breakout_index` 결과(피벗 미돌파면 매수일 추정 = "산 이후" 기준).

## 확장: `extension_pct`

`evaluate_holding`에서 계산: 피벗 있으면 `round((current/pivot − 1)×100, 1)`, 없으면 null.
칩 표시 "확장 +N%". (경고/판정 없음 — 참고 표시.)

## watch 등급 (C — 기존 🟡을 정식 승격)

두 소프트 케이스의 반환 `status`를 `"pass"` → `"watch"`로 변경(detail의 🟡 문구 유지):
- `rule_consecutive_lower_lows`: 저거래량 저점경신 3연속(rawmax≥3, 거래량 미달) 케이스.
- `rule_breakout_failure`: 유예 내 조용한 스쿼트("반전 회복 관찰중") 케이스.

영향:
- `violation_count`는 여전히 `status=="violation"`만 셈 → **신호(🔴🟠🟢) 로직 무변경**.
- `rules[].status` 유니온에 `"watch"` 추가(4→5개 값). 페이지 STATUS_MARK에 🟡 추가.

## 페이지: `SepaHoldingsSection.tsx` (목업이 시각 정본)

- 신호 배지 옆 badges 영역에 **`MVP` 배지**(mvp.status=="yes"일 때) + **확장 칩**("확장 +N%",
  extension_pct 있을 때) 추가.
- "매도 규칙" 패널 **위**에 **"매집 신호" 패널** 추가: 상단에 창 상태("D+3/15 진행중"/"15일 완료"),
  3개 신호(✓/○/―) 2열 + 그 아래 구분선 + MVP 3종(M/V/P, ✓/○/―).
- 각 매집·MVP 항목 + MVP 배지 + 확장 칩에 **호버 툴팁**(설명 문구). 점선 밑줄로 호버 가능 표시,
  키보드 포커스로도 노출(접근성).
- 규칙 목록 렌더에 **watch(🟡)** 마크 추가(STATUS_MARK). 숫자는 tabular-nums.
- 타입: `HoldingRule.status`에 `"watch"`, `HoldingFeedback`에 `extension_pct?`·`accumulation?`·`mvp?`.
- 데이터 없거나 no_data면 매집/ MVP/확장 미표시(기존 섹션 숨김 규칙 유지).

## 신호·범위 불변

- 매집 신호·MVP·확장·watch 무엇도 `violation_count`·`signal`을 바꾸지 않는다.
- 확장 반전 경고, 매집 신호를 손절/조기매도에 반영, 라운드트립 등은 범위 밖.

## 테스트

- **순수 함수(합성 일봉)**: `evaluate_accumulation` — 각 신호 met/unmet/pending, tight-day 제외,
  streak≥7, 15일 고정 창(16일 이상 시 첫 15일만). `evaluate_mvp` — <15일 pending, M/V/P 각
  경계(정확히 12/1.25×/+20%), 직전 표본 부족.
- **watch 회귀**: 기존 `test_sell_rules.py`에서 저거래량 저점경신·유예 스쿼트를 `pass`로
  단언하던 테스트를 `watch`로 갱신. `evaluate_holding` 신호(손절/조기매도/보유)·violation_count가
  watch에 영향 안 받음을 확인.
- **실 winner 오라클(MVP)**: MVP가 뚜렷한 한국 급등주 1종의 일봉(로컬 OHLCV 캐시 또는 FDR)
  픽스처로 mvp.status=="yes" + 세 조건 ok 검증. 종목 선정은 구현 때(위반 오라클 방식 재사용).
- **실행 검증**: 실제 보유 4종목으로 스크립트 실행 → JSON에 accumulation·mvp·extension_pct가
  기대 형태로 나오는지 + 페이지 렌더(캐시는 메인 dir에서 4종목 series 복사).

## 격리

worktree `C:/Users/hanul/playground/my-stock-holdings-accum`(브랜치 `feat/holdings-accumulation`,
base `origin/feat/stocks-sepa-page`=c248d43, v2 포함). 다른 세션과 파일 충돌 차단.
통합 경로: 지난번과 동일(→ feat/stocks-sepa-page → master).

## 범위 밖 (YAGNI)

- 확장 반전(뒤늦은 MVP=과열) 경고, 매집 신호의 신호 반영, 진입 스크리너 확장,
  tight-close를 좋은 마감으로 가산(현재는 나쁜 마감서 제외만), 알림.
