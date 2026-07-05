# 미너비니 정산표 페이지(A단계) 설계 문서

- 작성일: 2026-07-05
- 선행: C단계(계산 로직·CLI·`scorecard.json`) 완료·master 반영 — `docs/superpowers/specs/2026-07-05-scorecard-design.md` §9
- 관련 메모리: [[trading-scorecard]], [[plain-language-explanations]], [[match-scope-to-target-page]], [[doc-logic-sync]]

## 1. 목적

C단계에서 만든 `public/data/scorecard.json`(계산 완료된 정산표)을 **웹 화면으로 보여주는 전용 페이지**를 만든다. 계산은 하지 않는다 — 읽어서 렌더만 한다. 미너비니 트레이딩 삼각형·월별 확인표·왕복거래 목록을 순수익/총수익 토글로 본다.

## 2. 범위

- **경로**: `/stocks/scorecard` — StocksTabs에 "정산표" 탭 추가(미너비니 SEPA 파이프라인과 한 묶음).
- **읽는 데이터**: `public/data/scorecard.json` **하나만**. 다른 파일·계산 로직 무접촉.
- **안 하는 것**: 계산·집계 재구현 금지(전부 `scorecard.json`에 있음). 장부 편집 UI 없음. 기존 `/journal`(혼합 173건)과 무관.

## 3. 데이터 흐름

- `page.tsx`(서버 컴포넌트, async): `readJson<Scorecard>("scorecard.json")`로 읽음. 없거나 파싱 실패 → `null` → 안내 카드 렌더.
- 읽은 `Scorecard` 객체를 클라이언트 컴포넌트 `<ScorecardView data={sc} />`에 그대로 전달.
- `ScorecardView`(`"use client"`): `순수익/총수익` 토글 상태 `basis: "net" | "gross"` 보유(기본 `"net"`). JSON에 이미 있는 `sc.overall[basis]`·`sc.monthly[basis]`를 골라 렌더 — 재계산 없음.
- 타입은 `src/lib/scorecard.ts`가 export하는 `Scorecard`(및 하위 `OverallStats`/`MonthlyTable`/`MonthlyRow`/`Trade`/`OpenPosition`)를 **import해서 사용**(중복 정의 금지, [[doc-logic-sync]]).

## 4. 화면 구성 (위 → 아래)

### 4.1 머리말
- 제목 "미너비니 정산표", 부제에 `generated_at`·`strategy`·전체 거래건수(`overall.net.trade_count`).
- **토글**: `[순수익] [총수익]` 두 버튼(활성 강조). 기본 순수익.

### 4.2 트레이딩 삼각형 (요약)
- 큰 스탯 카드 3개: **승률**(`win_rate`) · **평균수익**(`avg_win`) · **평균손실**(`avg_loss`).
- 보조 줄: **성공/실패 비율**(`payoff_ratio`) · **조정 후 비율**(`adj_payoff_ratio`, 1 미만이면 "우위 없음" 톤) · **기대수익**(`expectancy`, 음수면 경고 톤).
- 최대수익/최대손실(`max_win`/`max_loss` — 종목명·%) 작게 병기.
- 값이 `null`이면 `-`.

### 4.3 RBA 카드
- `rba.avg_win_net` → `recommended_max_stop_pct` vs `current_default_stop_pct`.
- 문장: "평균수익 X% → 권장 최대 손절 Y% (현재 기본 Z%)". `status`가 `too_wide`면 경고색, `ok`면 정상색, `unknown`(거래 0건)이면 회색 안내.

### 4.4 진단 경고
- `diagnostics.warnings[]`가 비어있지 않으면 ⚠️ 리스트. 비어있으면 섹션 생략.

### 4.5 월별 확인표
- `monthly[basis]` — 책 그림 4-2 8컬럼 표: 월 · 평균수익 · 평균손실 · 승률 · 총거래수 · 최대수익 · 최대손실 · 수익일수 · 손실일수.
- 각 월 행 + 맨 아래 **"평균" 행**(`monthly[basis].average`, 강조 스타일). `null` 셀은 `-`.
- 가로 스크롤 컨테이너로 좁은 화면 대응.

### 4.6 왕복거래 목록
- `sc.trades` 각 행: 종목명 · `open_date`~`close_date` · **수익률(활성 기준: `net_pct` 또는 `gross_pct`)** · `hold_days` · `setup`(있으면) · `stop_violation`이면 "손절위반" 배지.
- **승/패 색칠**: 활성 기준 수익률 > 0 → 수익색, ≤ 0 → 손실색. (`Trade.outcome`는 순전용이라 안 씀 — C단계 스펙 §9 노트.)
- 거래 0건이면 "아직 청산된 거래가 없습니다" 안내.

### 4.7 열린 포지션 (미청산)
- `sc.open_positions`가 있으면 별도 작은 표: 종목 · 수량 · 평균매수가 · 진입일. "실현 통계 제외" 문구로 4.2~4.6과 구분.
- 없으면 섹션 생략.

## 5. 구성 파일

- `src/app/stocks/scorecard/page.tsx` — 서버 컴포넌트. `readJson` + 셸(제목/래퍼) + `<ScorecardView>` 마운트 + null 안내 카드.
- `src/app/stocks/scorecard/ScorecardView.tsx` — `"use client"`. 토글 상태 + 4.1~4.7 전 섹션 렌더. `Scorecard` 타입 import.
- `src/app/stocks/scorecard/format.ts` — 순수 포맷 헬퍼: `fmtPct(n: number | null): string`(예: `4.88` → `"4.88%"`, `null` → `"-"`), `fmtNum(n: number | null): string`, `fmtRatio(n: number | null): string`. **vitest 테스트 대상**.
- `src/app/stocks/StocksTabs.tsx` 수정 — 탭 배열에 정산표 1줄 추가.

**결정 근거(파일 분리)**: 서버(데이터 읽기)와 클라이언트(토글·렌더)를 나누는 건 Next.js 제약이자 기존 SEPA 페이지 패턴. 포맷 헬퍼를 별도 순수 모듈로 빼는 이유는 프로젝트 관례상 **React 컴포넌트는 단위 테스트 안 하고 순수 로직만 테스트**하기 때문 — 최소한의 로직(널→`-`·퍼센트 포맷)이라도 vitest로 고정한다.

## 6. 디자인

기존 페이지 토큰 재사용: `bg-surface-container-low`, `ghost-border`, `text-on-surface`/`text-on-surface-variant`, `text-primary`, `font-serif`(제목), `material-symbols-outlined` 아이콘, `rounded-xl`/`rounded-lg`. 수익=긍정색, 손실=경고/에러색은 기존 SEPA/저널 페이지의 손익 표기 관례를 따른다. 표는 `overflow-x-auto`로 모바일 대응.

## 7. 엣지 케이스

- `scorecard.json` 없음/파싱 실패 → 안내 카드("정산표 데이터가 없습니다. `npm run scorecard` 실행 후 생성됩니다").
- 청산거래 0건(전부 미청산) → 요약/월별/거래목록 자리에 "아직 청산된 거래 없음", 열린 포지션만 표시. (지표는 `null` → `-`.)
- 월별 표 특정 셀 `null` → `-`.
- `open_positions` 빈 배열 → 4.7 생략.

## 8. 검증

- `format.ts` vitest 단위 테스트: 퍼센트 포맷, `null`→`-`, 정수/비율 포맷, 음수 부호.
- `npx tsc --noEmit` 클린(특히 `Scorecard` 타입 import 정합).
- `npm run build` 성공, `/stocks/scorecard` 정적 라우트 생성 확인.
- 실제 렌더 확인: 현재 `scorecard.json`(실거래 3건)이 삼각형·월별표·거래목록에 정확히 표시되고 토글이 순↔총 전환하는지.

## 9. YAGNI (지금 안 함)

- 장부(체결) 편집/입력 UI — 파일 직접 관리.
- 셋업별(VCP/파워플레이/3C) 분리 뷰 — 데이터에 태그만, 화면 분리는 나중.
- 차트/그래프(recharts) — 표·카드로 충분. 필요해지면 별도.
- 기간 필터·정렬 상호작용 — 거래 소수라 불필요.
