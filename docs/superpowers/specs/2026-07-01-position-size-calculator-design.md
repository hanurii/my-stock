# 포지션 크기 계산기 (미너비니 기준) — 설계 spec

작성일 2026-07-01 · 상태: 설계 승인됨 · 대상: `/stocks/sepa` 페이지 신규 섹션

## 1. 배경·목적

`/stocks/sepa` 페이지에 **포지션 크기·손절 라인 계산기**를 추가한다. 마크 미너비니의 리스크 관리 규칙에 따라, 사용자가 총 투입금액과 매수 종목 수를 넣으면 **포지션당 분배금액**과 **권장 손절 라인(%)**을 실시간으로 알려준다. 기존 페이지의 서버 컴포넌트 + 순수 로직 + 클라이언트 컴포넌트 분리 패턴(`sepaPatterns.ts`/`SepaPatternTable.tsx`)을 그대로 따른다.

## 2. 미너비니 리스크 관리 규칙 (정적 참고로 페이지에 표시)

- 한 번의 매매에서 **총 자본의 1.25~2.50%만 위험**에 노출
- **최대 손절 10%** (그 이상은 손절)
- 손실은 **평균 5~6%를 초과하지 않음**
- 한 종목 **포지션 크기 50% 초과 금지**
- 최고의 종목엔 총포지션의 **20~25%**
- **최대 종목 수 10~12개**

## 3. 핵심 공식

> **계좌 위험(%) = 포지션 비중(%) × 손절 라인(%)**

균등 분할(1/N)을 가정한다(승인된 v1 결정 — 커스텀 비중은 범위 밖).

- 포지션 비중 `w% = 100 / N`
- 목표 계좌 위험 `r%`에 필요한 손절 = `r / w% × 100 = r × N`
- 따라서 위험 1.25~2.5%를 맞추는 손절 = `1.25×N ~ 2.5×N (%)`, 단 **최대 손절 10% 캡** 적용

## 4. 계산 로직 (순수 함수 `computePositionSizing`)

**상수 (미너비니):**
- `ACCOUNT_RISK_MIN = 1.25`, `ACCOUNT_RISK_MAX = 2.5` (총자본 대비 %)
- `MAX_STOP_PCT = 10`
- `MAX_POSITION_PCT = 50`, `BEST_POSITION_PCT = 25`
- `MAX_STOCKS = 12`

**입력:** `{ capital: number; numStocks: number }`

**출력 `PositionSizing`:**
- `positionAmount = capital / N`
- `positionWeightPct = 100 / N`
- `stopLowPct = min(MAX_STOP_PCT, ACCOUNT_RISK_MIN × N)` — 위험 하한(1.25%)용 손절
- `stopHighPct = min(MAX_STOP_PCT, ACCOUNT_RISK_MAX × N)` — 위험 상한(2.5%)용 손절(보통 10% 캡)
- `lossAtLow = positionAmount × stopLowPct / 100` (1종목 손실액, 원)
- `lossAtHigh = positionAmount × stopHighPct / 100`
- `riskAtLowPct = positionWeightPct × stopLowPct / 100` (계좌 위험 %)
- `riskAtHighPct = positionWeightPct × stopHighPct / 100`
- `warnings: string[]`

**경고 규칙 (입력이 미너비니 규칙 위반/주의 시):**
- `positionWeightPct > MAX_POSITION_PCT` (50): `"한 종목 비중이 50%를 초과합니다 — 분산 부족(미너비니 최대 50%)."`
- else if `positionWeightPct > BEST_POSITION_PCT` (25): `"포지션 비중이 25%를 초과합니다 — 최고 종목도 20~25% 권장."`
- `numStocks > MAX_STOCKS` (12): `"종목 수가 12개를 초과합니다 — 미너비니 권장 10~12개."`
- `riskAtHighPct < ACCOUNT_RISK_MIN` (1.25): `"비중이 작아 10% 손절에도 계좌 위험이 1.25% 미만입니다(보수적 — 위험 여력 있음)."`

**유효성:** `capital ≤ 0` 또는 `numStocks < 1` 이면 계산 불가 → 출력은 0/빈 배열, 컴포넌트가 안내 문구. `numStocks` 는 정수로 처리(`Math.floor`).

**예시 (capital 150,000,000 · N 5):** positionAmount 30,000,000 · weight 20% · stopLow 6.25% · stopHigh 10% · lossAtLow 1,875,000 · lossAtHigh 3,000,000 · riskAtLow 1.25% · riskAtHigh 2.0% · warnings 없음.

## 5. 구성 요소

- `src/app/stocks/sepa/positionSizing.ts` — **순수 로직**(프레임워크 비의존): 상수 + `computePositionSizing(input)` + 한국 원화 포맷터 `fmtKRW(n)`(억·만원 단위, 예 150000000→"1억 5,000만원"). **vitest 테스트 대상.**
- `src/app/stocks/sepa/PositionSizeCalculator.tsx` — **클라이언트 컴포넌트**: 입력 2개(총금액·종목수)의 state, `computePositionSizing` 호출, 결과 카드/표 렌더. 기존 테마 토큰(`surface-container-low`·`on-surface`·`ghost-border`) 사용.
- `src/app/stocks/sepa/page.tsx` (수정) — 정적 규칙 참고 블록 + `<PositionSizeCalculator />` 섹션을 패턴 섹션들 아래에 추가.

## 6. 레이아웃

페이지 패턴 섹션들 아래, 용어 섹션 위(또는 그 근처)에 새 `<section>`:
1. 섹션 제목 "포지션 크기 계산기 (미너비니 기준)".
2. **정적 규칙 6줄** — §2 목록.
3. **계산기**: 입력행(총 투입금액 / 종목 수) → 결과:
   - 포지션당 분배금액(원) · 포지션 비중(%)
   - 손절 라인 권장: **하한~상한 %** + 각 끝의 1종목 손실액·계좌 위험% (하한=상한이면 단일 값으로 표시 — 예: 종목 수가 많아 둘 다 10%로 캡된 경우)
   - 경고 문구(있으면 강조 색)

## 7. 에러·엣지 처리

- 빈/0/음수 입력 → "총 투입금액과 종목 수를 입력하세요" 안내, 계산 숨김.
- 매우 큰 종목 수 → 경고는 뜨되 계산은 정상(비중 작음).
- 소수 종목 수 입력 → `Math.floor`로 정수화.

## 8. 테스트

`positionSizing.ts` 순수 함수를 vitest로 단위 테스트(기존 `sepaPatterns.test.ts`와 동일 러너):
- 기준 예시(1.5억·5): 모든 출력값 정확(position 3000만·stop 6.25~10·loss·risk).
- N=4(비중 25, 경고 없음, stop 5~10), N=2(비중 50, ">25 경고", stop 2.5~5), N=1(비중 100, ">50 경고"), N=15(">12 경고" + "보수적" 경고, stop 10 캡).
- 손절 10% 캡 경계(N=4에서 stopHigh=10), 보수적 경고 경계(N=9에서 riskAtHigh<1.25).
- `fmtKRW`: 150000000→"1억 5,000만원", 30000000→"3,000만원", 1875000→"187.5만원", 0→"0원".
- 유효성: capital 0 / numStocks 0 → 안전 출력.

## 9. 안 하는 것 (YAGNI)

- 커스텀(비균등) 비중 입력 — v1 범위 밖.
- 종목별 실제 진입가·손절가 입력(R-multiple 등) — 이 계산기는 자본 배분·손절% 가이드에 한정.
- 데이터 파일·서버 연동 — 순수 클라이언트 계산.
- 저장/공유/세션 — 없음.

## 10. 성공 기준

- `/stocks/sepa`에 계산기 섹션이 보이고, 총금액·종목수 입력 시 포지션 금액·손절 권장 범위·손실액·위험%·경고가 정확히 갱신.
- 기준 예시(1.5억·5종목) → 3,000만원/20%, 손절 6.25~10%, 위험 1.25~2.0% 표시.
- `positionSizing.ts` vitest 통과. tsc·`next build` 무에러, 기존 페이지·빌드 무영향.
