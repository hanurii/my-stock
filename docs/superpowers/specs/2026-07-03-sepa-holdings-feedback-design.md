# SEPA 보유 종목 점검(매도 규칙 위반 피드백) 설계

날짜: 2026-07-03
상태: 설계 확정 대기 (사용자 리뷰 전)

## 목적

/stocks/sepa 페이지에서 피벗 돌파로 매수한 종목이 "계속 들고 있어도 되는지"를 매일 알려주는
섹션을 추가한다. 마크 미너비니의 돌파 후 위반(violation) 규칙 6가지를 검사해,
손절선(-4%)에 닿기 전에 조기 매도 신호를 켠다.

근거 조사: 『Think & Trade Like a Champion』 요약 자료 (ChartMill Part 2,
The Trader's Journey 북리뷰). 사용자 확정 사항:
- 연속 저저점 규칙은 저점이 아니라 **종가** 기준으로 판정
- 위반 **1개**부터 조기 매도 신호, **위반 개수**를 함께 표시해 심각도 표현
- 하락일 우세와 나쁜 마감 우세는 **하나의 규칙으로 통합**
- 스쿼트(돌파 실패)를 새 규칙으로 추가
- 손절선은 당분간 **-4%** (SEPA 신뢰가 쌓이면 -10%로 상향 예정)

## 전체 구조 (3조각)

```
public/data/sepa-holdings.json        ← 사용자가 직접 관리하는 매수 목록 (입력)
        │
scripts/screen_holdings_feedback.py   ← 점검 스크립트 (일봉 캐시 + SEPA 후보 파일 읽음)
  └─ scripts/canslim_lib/sell_rules.py  ← 규칙 판정 순수 함수 (pytest 대상)
        │
public/data/sepa-holdings-feedback.json ← 판정 결과 (출력)
        │
src/app/stocks/sepa/page.tsx           ← "보유 종목 점검" 섹션 렌더링
  └─ src/app/stocks/sepa/SepaHoldingsSection.tsx (표시 전용 컴포넌트)
```

시세 캐시(.cache/ohlcv)는 서버(로컬)에만 있으므로, 기존 SEPA 패턴들과 동일하게
"스크립트가 JSON을 만들고 페이지는 읽기만" 하는 구조를 따른다.

## 입력 파일: public/data/sepa-holdings.json

사용자가 매수·매도 때마다 직접 고치는 파일. 초기값은 실제 매수 내역 4건.

```json
{
  "stop_loss_pct_default": -4,
  "holdings": [
    { "code": "036800", "name": "나이스정보통신", "buy_datetime": "2026-07-01 09:31:32", "buy_price": 29700, "quantity": 435 },
    { "code": "271560", "name": "오리온",         "buy_datetime": "2026-07-02 09:07:53", "buy_price": 138500, "quantity": 72 },
    { "code": "010955", "name": "S-Oil우",        "buy_datetime": "2026-07-03 09:06:02", "buy_price": 57900, "quantity": 172 },
    { "code": "005430", "name": "한국공항",       "buy_datetime": "2026-07-03 14:15:54", "buy_price": 87500, "quantity": 114 }
  ]
}
```

- 종목별 `stop_loss_pct` 를 적으면 기본값(-4) 대신 그 값을 쓴다.
- 매도하면 항목을 지우면 된다 (이력 보존은 이 기능 범위 밖).

## 기준점: 돌파일과 피벗

규칙 판정의 기준점은 **돌파일**이다 (매수일이 아님 — 미너비니 규칙은 돌파를 기준으로 봄).

- 피벗 가격: `sepa-vcp-candidates.json` 에서 해당 종목의 `pivot_price` 를 먼저 찾고,
  없으면 `sepa-power-play-candidates.json`, 그것도 없으면 피벗 없음.
- 돌파일: 매수일로부터 거슬러 최대 20거래일 안에서, "전일 종가 ≤ 피벗 < 당일 종가"
  인 가장 최근 날. 못 찾으면(피벗 없음 포함) **매수일을 기준점으로 대체**하고
  결과에 `breakout_date_estimated: true` 를 표시.
- 매수일 당일 장중 매수이므로, 매수일도 돌파일 후보에 포함한다.

## 6가지 규칙 판정 (sell_rules.py)

입력: 일봉 배열(dates/opens/highs/lows/closes/volumes), 돌파일 인덱스, 피벗 가격(없을 수 있음).
각 규칙의 반환: `violation`(위반) / `pass`(통과) / `pending`(판정 유보 — 날이 더 필요) /
`na`(판정 불가 — 피벗 없음 등) + 한 줄 사유(detail).

50일 평균 거래량 = 해당 판정일 직전 50거래일 거래량 평균 (판정일 제외).

| # | id | 규칙 | 판정 기준 |
|---|----|------|-----------|
| 1 | low_volume_breakout | 저거래량 돌파 | 돌파일 거래량 < 50일 평균 → 위반. 평균의 1.0~1.5배는 통과지만 detail에 "정상 돌파(1.5배+)에 못 미침" 명시. 돌파일이 추정(=매수일 대체)이면 그 날 기준으로 동일 판정 |
| 2 | heavy_volume_pullback | 대량 거래 후퇴 | 돌파일 다음 날부터: 종가가 전일 종가보다 낮으면서 거래량 ≥ 50일 평균 × 1.5 인 날이 하나라도 있으면 위반 (가장 심한 날을 detail로) |
| 3 | consecutive_lower_closes | 연속 저저점 (종가 기준) | 돌파일 다음 날부터: **종가 < 전일 저가** 인 날이 3일 연속이면 위반. 2일 연속 진행 중이면 통과 + detail에 "2일째 진행 중" 경고 |
| 4 | close_below_ma | 이평선 아래 마감 | 돌파일 다음 날부터: 종가 < 20일 이동평균 인 날이 있으면 위반. 종가 < 50일 이동평균이면서 거래량 ≥ 평균 × 1.5 인 날이 있으면 detail에 "심각(50일선+대량)" 표기 (위반 1건으로 집계) |
| 5 | weak_days_dominant | 하락일·나쁜 마감 우세 (통합) | 돌파일 다음 날부터 5거래일 이상 지나야 판정(그 전엔 pending). 하락일 수 > 상승일 수 **또는** 나쁜 마감 수 > 좋은 마감 수 → 위반. 나쁜 마감 = 종가가 당일 고저 범위의 아래 절반(종가 < (고+저)/2). 고가=저가인 날은 어느 쪽에도 세지 않음. 보합일(종가=전일 종가)도 세지 않음 |
| 6 | squat | 스쿼트 (돌파 실패) | 돌파일 다음 날부터: 종가가 피벗 아래로 되돌아온 날이 있으면 위반. 피벗이 없으면 na |

돌파일 다음 날 데이터가 아직 없으면(오늘 돌파·매수) 2~6번은 pending.

## 종합 신호

우선순위 순서대로:

1. 🔴 **손절** (`stop_loss`): 현재가 ≤ 매수가 × (1 + 손절%/100). 규칙과 무관하게 최우선.
2. 🟠 **조기 매도 신호** (`early_sell`): 위반 1개 이상. **위반 개수를 함께 표시**
   (예: "조기 매도 신호 · 위반 3건") — 개수가 많을수록 심각.
3. 🟢 **정상 보유** (`hold`): 위반 0개.

pending/na는 위반 개수에 넣지 않는다.

## 출력 파일: public/data/sepa-holdings-feedback.json

```json
{
  "generated_at": "...", "asof": "2026-07-03", "stop_loss_pct_default": -4,
  "holdings": [
    {
      "code": "036800", "name": "나이스정보통신", "market": "KOSDAQ",
      "buy_date": "2026-07-01", "buy_price": 29700, "quantity": 435,
      "current_price": 30200, "profit_pct": 1.68,
      "stop_loss_pct": -4, "stop_price": 28512, "pct_to_stop": -5.59,
      "pivot_price": 28800.0, "pivot_source": "vcp",
      "breakout_date": "2026-07-01", "breakout_date_estimated": false,
      "signal": "hold", "violation_count": 0,
      "rules": [
        { "id": "low_volume_breakout", "status": "pass", "detail": "돌파일 거래량 2.1배" },
        ...6개...
      ]
    }
  ]
}
```

`pct_to_stop` = 손절가까지 남은 거리(%) = (손절가/현재가 − 1) × 100 (음수 = 아직 여유).

## 페이지 표시 (src/app/stocks/sepa/)

- 위치: "1단계 트렌드 템플릿 통과" 요약 카드 **바로 아래**, 패턴 섹션들 위.
- 새 컴포넌트 `SepaHoldingsSection.tsx` (서버 렌더 전용, 정렬 등 상호작용 없음).
- 종목별 카드 1장: 상단에 종목명 + 신호 배지(🔴 손절 / 🟠 조기 매도 신호 · 위반 N건 /
  🟢 정상 보유), 매수일·매수가 → 현재가·수익률, 손절선까지 거리.
  아래에 6개 규칙 목록: ✓ 통과 / ✗ 위반 / ― 유보·불가 + 한 줄 사유.
- 스타일: 기존 관례(`bg-surface-container-low rounded-xl ghost-border p-4`,
  serif 제목 + material-symbols 아이콘, 신호 배지는 기존 TIER_META 색상 계열).
- `sepa-holdings-feedback.json` 이 없거나 holdings가 비어 있으면 섹션 자체를 숨긴다.

## 테스트

- `tests/test_sell_rules.py` (pytest, 기존 test_vcp.py 관례): 가짜 일봉으로 6개 규칙
  각각 위반/통과 케이스 + pending(5거래일 미만, 돌파 다음날 없음) + na(피벗 없음) +
  돌파일 탐지(정상 탐지 / 못 찾아 매수일 대체) + 종합 신호(손절 우선, 위반 개수).
- 실행 검증: 실제 4종목으로 스크립트를 돌려 결과 JSON과 페이지 렌더링 확인.

## 운영

- 실행: `python scripts/screen_holdings_feedback.py` (표준 실행이 sepa-holdings.json 전체).
- 시세는 update-data 가 갱신하는 기존 캐시를 그대로 읽는다 (추가 수집 없음).
- /sepa 오케스트레이터 정기 순서 편입은 이번 범위 밖 (추후 스킬 문서 수정으로 가능).

## 범위 밖 (YAGNI)

- 매도 이력·수익률 추적, 분할 매도 제안, 알림(푸시), 장중 실시간 판정,
  journal.json 통합, 규칙 파라미터 UI 조정.
