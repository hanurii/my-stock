# 정산표 — 보유 점검 섹션 이동 + 총 손익(실현 금액) 칸 설계

날짜: 2026-07-06
상태: 설계 확정 대기 (사용자 리뷰 전)
기준 브랜치: `feat/scorecard-holdings-pnl` (origin/master 기준)

## 목적

두 가지 변경:
1. **보유 종목 점검 섹션을 정산표 페이지로 이동** — `/stocks/sepa`에서 빼고 `/stocks/sepa/score-card`로 옮긴다.
2. **총 손익(실현 금액, 원) 칸 추가** — 미너비니 원칙으로 매매한 완결 거래의 실제 순손익 합계를 정산표 상단에 한 줄로 보여준다.

## 사용자 확정 사항

- 총 손익은 **한 칸(단일 숫자)** 으로 단순하게.
- **실현 손익만** — 체결장부(scorecard-fills)의 **완결된 왕복거래**만 집계. 아직 안 판 종목의 평가이익(미실현)은 제외.
- 기존 **순/총 토글**을 따라간다(순수익=수수료·세금 차감, 총수익=가격만).
- 보유 점검은 `/stocks/sepa`에선 **완전히 제거**.

## 데이터 흐름 (기존 재사용)

```
public/data/scorecard-fills.json  ─ npm run scorecard ─→ scorecard.json ─→ ScorecardView (총 손익 칸)
public/data/sepa-holdings-feedback.json ───────────────────────────────→ SepaHoldingsSection (이동)
                                                                            둘 다 score-card/page.tsx가 읽음
```

정산표 계산(`computeScorecard`)은 이미 완결 거래마다 원 단위 `netCost = buyVal + buyFees`,
`netProceeds = sellVal − (sellFees + tax)`를 내부에서 구한다. 지금은 퍼센트만 노출 → 원 손익을 추가 노출한다.

## 변경 1: 백엔드 `src/lib/scorecard.ts`

### `Trade` 타입에 원 손익 필드 추가

```ts
export type Trade = {
  // ...기존 필드...
  gross_pct: number; net_pct: number;
  gross_won: number;   // 신규: sellVal − buyVal (가격만)
  net_won: number;     // 신규: netProceeds − netCost (수수료·세금 차감)
  // ...
};
```

완결 거래 계산부에서 두 값을 채운다(이미 있는 `buyVal/sellVal/netCost/netProceeds` 사용):
- `gross_won = round(sellVal − buyVal)`
- `net_won = round(netProceeds − netCost)`
(반올림은 기존 `round2`/정수 관례를 따르되, 원은 정수로 `Math.round`.)

### `OverallStats`에 총 손익 합계 추가

```ts
export type OverallStats = {
  // ...기존...
  total_won: number;   // 신규: 완결 거래 원 손익 합계(basis에 맞는 값)
};
```

`computeOverall(trades, basis)`에서:
- `total_won = sum(trades, (t) => basis === "net" ? t.net_won : t.gross_won)`

→ `scorecard.overall.net.total_won` / `scorecard.overall.gross.total_won` 로 노출되어, 화면 토글이 그대로 선택.

## 변경 2: 포맷 헬퍼 `src/app/stocks/sepa/score-card/format.ts`

원 서명 포맷 추가(기존 `plColor` 재사용):

```ts
export function fmtSignedWon(n: number | null): string {
  return n == null ? "-" : `${n >= 0 ? "+" : ""}${Math.round(n).toLocaleString()}원`;
}
```

## 변경 3: 화면 `src/app/stocks/sepa/score-card/ScorecardView.tsx`

기존 `basis` 토글 바로 아래(트레이딩 삼각형 위)에 **총 손익 헤드라인 타일** 하나 추가:

- 라벨: `총 손익 (실현)` + 부제 `완결 거래 · {basis === "net" ? "순수익" : "총수익"} 기준`
- 값: `fmtSignedWon(o.total_won)` — 색은 `plColor(o.total_won)`(이익 초록/손실 빨강). tabular-nums, 큰 글씨.
- 거래 0건이면 `o.total_won === 0` → `+0원`(또는 "완결 거래 없음") 처리.
- 기존 카드 스타일(`bg-surface-container-low rounded-xl ghost-border p-4`) 재사용.

`o`는 이미 `data.overall[basis]`라 토글에 자동 반응.

## 변경 4: 정산표 페이지 `src/app/stocks/sepa/score-card/page.tsx`

- `sepa-holdings-feedback.json`도 읽는다(`HoldingsFeedbackFile`, `SepaHoldingsSection`에서 타입 import).
- 렌더: `<ScorecardView>` **아래에** `<SepaHoldingsSection data={holdingsFeedback} />` 를 형제로 스택.
  (정산표 통계가 먼저, 보유 점검이 아래. 순서는 리뷰에서 조정 가능.)
- 파일이 이미 파일 읽기 실패를 `null`로 처리하므로 동일 패턴으로 holdings도 `null` 허용.

## 변경 5: 기존 페이지 `src/app/stocks/sepa/page.tsx`

- `<SepaHoldingsSection data={holdingsFeedback} />` 렌더 제거.
- 그 데이터 로드(`holdingsFeedback` readJson)와 이제 안 쓰는 import 제거.
- 나머지(트렌드 요약·패턴 섹션·포지션 계산기·용어) 불변.

## 변경 6: 테스트 `src/lib/scorecard.test.ts`

- 알려진 fill 세트(매수/매도)로 `net_won`·`gross_won`이 (netProceeds−netCost)·(sellVal−buyVal)과 일치하는지.
- `computeOverall`의 `total_won`이 완결 거래 원 손익 합계(basis별)와 일치하는지.
- 손실 거래에서 `net_won < 0` 확인.

## 산출물 재생성

`npm run scorecard` 재실행 → `scorecard.json`에 `gross_won/net_won/total_won` 채워짐. 페이지는 읽기만.

## 범위 밖

- **미실현 손익**(열린 포지션 현재가 평가) — 이번 제외. 원하면 별도 슬라이스(열린 포지션 현재가 소스 정리 필요: 정산표 체결장부와 보유 목록의 종목 집합이 달라 정합성 작업 수반).
- 거래별 원 손익 칼럼·월별 원 합계 — 이번은 총합 한 줄만.
