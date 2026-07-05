# 미너비니 정산표 페이지(A단계) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** C단계에서 만든 `public/data/scorecard.json`을 `/stocks/sepa/score-card` 페이지에서 순수익/총수익 토글로 보여준다(트레이딩 삼각형·RBA·진단·월별 확인표·왕복거래·열린 포지션).

**Architecture:** 서버 컴포넌트 `page.tsx`가 `scorecard.json`을 읽어(없으면 안내 카드) 클라이언트 컴포넌트 `ScorecardView`에 넘긴다. `ScorecardView`는 토글 상태만 들고, JSON에 이미 계산된 `overall[basis]`·`monthly[basis]`를 골라 렌더한다(재계산 없음). 순수 포맷 헬퍼는 `format.ts`로 분리해 vitest로 테스트.

**Tech Stack:** Next.js 16 App Router(서버/클라이언트 컴포넌트), TypeScript, Tailwind(기존 디자인 토큰), vitest(순수 헬퍼만).

**근거 스펙:** `docs/superpowers/specs/2026-07-05-scorecard-page-design.md`

## Global Constraints

- 계산 재구현 금지 — 전부 `scorecard.json`에 있음. 페이지는 **읽기·표시만**.
- 타입은 `src/lib/scorecard.ts`가 export하는 `Scorecard`(및 `OverallStats`/`MonthlyRow`/`Trade`/`OpenPosition`)를 **import**해서 씀(중복 정의 금지). import 경로 별칭 `@/lib/scorecard`(= `src/lib/scorecard`, 프로젝트에서 `@/*`→`src/*` 사용).
- **하위 컴포넌트는 모듈 스코프에 정의**(함수 컴포넌트 안에서 컴포넌트 정의 금지 — 프로젝트 lint 규칙 `react-hooks/static-components`가 막음).
- 손익 색상: 수익 `#95d3ba`, 손실 `#ffb4ab`(저널 페이지와 동일, 인라인 `style` 사용).
- `null` 지표는 `-`로 표시. 퍼센트 2자리. avg_loss/max_loss는 데이터가 양수 크기이므로 화면엔 `-X.XX%`로.
- 승/패 색칠은 **활성 기준(net/gross) 수익률**로(스펙 §4.6, `Trade.outcome`는 순전용이라 안 씀).
- 디자인 토큰: `bg-surface-container-low`, `ghost-border`, `text-on-surface`, `text-on-surface-variant`, `text-primary`, `bg-primary/15`, `font-serif`, `material-symbols-outlined`, `rounded-xl`/`rounded-lg`. 표는 `overflow-x-auto`.
- 파일 위치: `src/app/stocks/sepa/score-card/`. StocksTabs는 `src/app/stocks/StocksTabs.tsx`. `/stocks/layout.tsx`가 중첩 라우트에도 StocksTabs를 렌더하므로 탭은 이 페이지에서 자동 노출·활성화.

---

## 파일 구조

- Create: `src/app/stocks/sepa/score-card/format.ts` — 순수 포맷 헬퍼
- Create: `src/app/stocks/sepa/score-card/format.test.ts` — vitest
- Create: `src/app/stocks/sepa/score-card/ScorecardView.tsx` — `"use client"`, 토글 + 전 섹션(모듈 스코프 하위 컴포넌트)
- Create: `src/app/stocks/sepa/score-card/page.tsx` — 서버, 읽기 + 셸 + null 안내
- Modify: `src/app/stocks/StocksTabs.tsx` — 탭 1줄 추가

---

## Task 1: 포맷 헬퍼 `format.ts` (+ vitest)

**Files:**
- Create: `src/app/stocks/sepa/score-card/format.ts`
- Test: `src/app/stocks/sepa/score-card/format.test.ts`

**Interfaces:**
- Consumes: 없음
- Produces: `fmtPct`, `fmtLossPct`, `fmtSignedPct`, `fmtNum`, `fmtRatio`(각 `(n: number | null) => string`), `plColor(n: number | null): string`, 상수 `PROFIT_COLOR`/`LOSS_COLOR`

- [ ] **Step 1: 실패하는 테스트 작성**

`src/app/stocks/sepa/score-card/format.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { fmtPct, fmtLossPct, fmtSignedPct, fmtNum, fmtRatio, plColor, PROFIT_COLOR, LOSS_COLOR } from "./format";

describe("format helpers", () => {
  it("fmtPct: 2자리 % / null은 -", () => {
    expect(fmtPct(4.88)).toBe("4.88%");
    expect(fmtPct(0)).toBe("0.00%");
    expect(fmtPct(null)).toBe("-");
  });
  it("fmtLossPct: 양수 크기를 -X% 로 / null은 -", () => {
    expect(fmtLossPct(5.62)).toBe("-5.62%");
    expect(fmtLossPct(null)).toBe("-");
  });
  it("fmtSignedPct: 부호 붙임 / null은 -", () => {
    expect(fmtSignedPct(7.56)).toBe("+7.56%");
    expect(fmtSignedPct(-5.62)).toBe("-5.62%");
    expect(fmtSignedPct(0)).toBe("+0.00%");
    expect(fmtSignedPct(null)).toBe("-");
  });
  it("fmtNum / fmtRatio", () => {
    expect(fmtNum(3)).toBe("3");
    expect(fmtNum(0)).toBe("0");
    expect(fmtNum(null)).toBe("-");
    expect(fmtRatio(2.28)).toBe("2.28");
    expect(fmtRatio(null)).toBe("-");
  });
  it("plColor: >0 수익색, <=0 손실색, null은 상속", () => {
    expect(plColor(5)).toBe(PROFIT_COLOR);
    expect(plColor(-5)).toBe(LOSS_COLOR);
    expect(plColor(0)).toBe(LOSS_COLOR);
    expect(plColor(null)).toBe("inherit");
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npx vitest run src/app/stocks/sepa/score-card/format.test.ts`
Expected: FAIL — `Failed to resolve import "./format"`

- [ ] **Step 3: 최소 구현 작성**

`src/app/stocks/sepa/score-card/format.ts`:

```ts
export const PROFIT_COLOR = "#95d3ba";
export const LOSS_COLOR = "#ffb4ab";

export function fmtPct(n: number | null): string {
  return n == null ? "-" : `${n.toFixed(2)}%`;
}
export function fmtLossPct(n: number | null): string {
  return n == null ? "-" : `-${n.toFixed(2)}%`;
}
export function fmtSignedPct(n: number | null): string {
  return n == null ? "-" : `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}
export function fmtNum(n: number | null): string {
  return n == null ? "-" : String(n);
}
export function fmtRatio(n: number | null): string {
  return n == null ? "-" : n.toFixed(2);
}
export function plColor(n: number | null): string {
  if (n == null) return "inherit";
  return n > 0 ? PROFIT_COLOR : LOSS_COLOR;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/app/stocks/sepa/score-card/format.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/app/stocks/sepa/score-card/format.ts src/app/stocks/sepa/score-card/format.test.ts
git commit -m "feat(scorecard-page): format.ts 포맷 헬퍼(+vitest)"
```

---

## Task 2: `ScorecardView.tsx` (클라이언트, 토글 + 전 섹션)

**Files:**
- Create: `src/app/stocks/sepa/score-card/ScorecardView.tsx`

**Interfaces:**
- Consumes: `Scorecard`/`OverallStats`/`MonthlyRow`/`Trade`/`OpenPosition` (from `@/lib/scorecard`), `format.ts` 헬퍼(Task 1)
- Produces: `export function ScorecardView({ data }: { data: Scorecard })` — page.tsx(Task 3)가 마운트

이 태스크는 표시 컴포넌트라 프로젝트 관례상 **단위 테스트 없음**. 검증은 Task 3에서 `tsc`+`build`+렌더. 하위 컴포넌트(`StatCard`/`MonthlyRowView`)는 **모듈 스코프**에 둔다(lint 규칙).

- [ ] **Step 1: 컴포넌트 작성**

`src/app/stocks/sepa/score-card/ScorecardView.tsx`:

```tsx
"use client";

import { useState } from "react";
import type { Scorecard, OverallStats, MonthlyRow, Trade, OpenPosition } from "@/lib/scorecard";
import { fmtPct, fmtLossPct, fmtSignedPct, fmtNum, fmtRatio, plColor, PROFIT_COLOR, LOSS_COLOR } from "./format";

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-surface-container-low rounded-xl ghost-border p-4">
      <p className="text-xs text-on-surface-variant/60">{label}</p>
      <p className="text-2xl font-mono font-bold mt-1" style={color ? { color } : undefined}>{value}</p>
      {sub && <p className="text-[11px] text-on-surface-variant/50 mt-1">{sub}</p>}
    </div>
  );
}

const MONTH_COLS = "grid grid-cols-9 gap-2 px-3 py-2 text-right text-sm";

function MonthRow({ row, isAvg }: { row: MonthlyRow; isAvg?: boolean }) {
  return (
    <div className={`${MONTH_COLS} ${isAvg ? "font-bold bg-surface-container-low rounded-lg" : "border-t border-outline/10"}`}>
      <span className="text-left">{row.month}</span>
      <span style={{ color: plColor(row.avg_win) }}>{fmtPct(row.avg_win)}</span>
      <span style={{ color: row.avg_loss == null ? undefined : LOSS_COLOR }}>{fmtLossPct(row.avg_loss)}</span>
      <span>{fmtPct(row.win_rate)}</span>
      <span>{row.trades}</span>
      <span style={{ color: plColor(row.max_win) }}>{fmtPct(row.max_win)}</span>
      <span style={{ color: row.max_loss == null ? undefined : LOSS_COLOR }}>{fmtLossPct(row.max_loss)}</span>
      <span>{fmtNum(row.win_days)}</span>
      <span>{fmtNum(row.loss_days)}</span>
    </div>
  );
}

function TradeRow({ trade, basis }: { trade: Trade; basis: "net" | "gross" }) {
  const pct = basis === "net" ? trade.net_pct : trade.gross_pct;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-t border-outline/10">
      <div className="flex items-center gap-2">
        <span className="font-medium text-on-surface">{trade.name}</span>
        {trade.setup && <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">{trade.setup}</span>}
        {trade.stop_violation && <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: LOSS_COLOR + "22", color: LOSS_COLOR }}>손절위반</span>}
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-on-surface-variant/60">{trade.open_date} ~ {trade.close_date} ({trade.hold_days}일)</span>
        <span className="font-mono font-bold w-20 text-right" style={{ color: plColor(pct) }}>{fmtSignedPct(pct)}</span>
      </div>
    </div>
  );
}

function OpenRow({ pos }: { pos: OpenPosition }) {
  return (
    <div className="flex items-center justify-between gap-2 px-4 py-2 border-t border-outline/10 text-sm">
      <span className="font-medium text-on-surface">{pos.name}</span>
      <span className="text-on-surface-variant/60">{pos.qty}주 · 평균 {pos.avg_buy.toLocaleString()}원 · {pos.open_date}</span>
    </div>
  );
}

export function ScorecardView({ data }: { data: Scorecard }) {
  const [basis, setBasis] = useState<"net" | "gross">("net");
  const o: OverallStats = data.overall[basis];
  const monthly = data.monthly[basis];
  const hasTrades = o.trade_count > 0;
  const rba = data.rba;
  const rbaColor = rba.status === "too_wide" ? LOSS_COLOR : rba.status === "ok" ? PROFIT_COLOR : "inherit";

  return (
    <div className="space-y-8">
      {/* 머리말 + 토글 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">scoreboard</span>미너비니 정산표
          </h2>
          <p className="text-sm text-on-surface-variant/70 mt-1">
            {data.generated_at} 기준 · 전략 {data.strategy} · 청산거래 {data.overall.net.trade_count}건
          </p>
        </div>
        <div className="flex gap-1 bg-surface-container-low rounded-lg p-1 ghost-border">
          {(["net", "gross"] as const).map((b) => (
            <button
              key={b}
              onClick={() => setBasis(b)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                basis === b ? "bg-primary/15 text-primary shadow-sm" : "text-on-surface-variant/60 hover:text-on-surface-variant"
              }`}
            >
              {b === "net" ? "순수익" : "총수익"}
            </button>
          ))}
        </div>
      </div>

      {!hasTrades ? (
        <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-sm text-on-surface-variant/70">
          아직 청산된 거래가 없습니다. 매도까지 완료된 거래가 쌓이면 여기에 성적표가 표시됩니다.
        </div>
      ) : (
        <>
          {/* 트레이딩 삼각형 */}
          <section className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <StatCard label="승률" value={fmtPct(o.win_rate)} sub={`${o.win_count}승 ${o.loss_count}패 / ${o.trade_count}건`} />
              <StatCard label="평균수익" value={fmtPct(o.avg_win)} color={o.avg_win == null ? undefined : PROFIT_COLOR} />
              <StatCard label="평균손실" value={fmtLossPct(o.avg_loss)} color={o.avg_loss == null ? undefined : LOSS_COLOR} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <StatCard label="성공/실패 비율" value={fmtRatio(o.payoff_ratio)} sub="평균수익 ÷ 평균손실" />
              <StatCard label="조정 후 비율" value={fmtRatio(o.adj_payoff_ratio)} sub={o.adj_payoff_ratio == null ? undefined : o.adj_payoff_ratio < 1 ? "1 미만 — 수학적 우위 없음" : "1 이상 — 수학적 우위 있음"} />
              <StatCard label="기대수익 (거래당)" value={fmtSignedPct(o.expectancy)} color={plColor(o.expectancy)} />
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-on-surface-variant/60 px-1">
              {o.max_win && <span>최대수익 <b style={{ color: PROFIT_COLOR }}>{fmtPct(o.max_win.pct)}</b> ({o.max_win.name})</span>}
              {o.max_loss && <span>최대손실 <b style={{ color: LOSS_COLOR }}>{fmtLossPct(o.max_loss.pct)}</b> ({o.max_loss.name})</span>}
              <span>수익 유지 {fmtNum(o.win_days)}일 · 손실 유지 {fmtNum(o.loss_days)}일</span>
            </div>
          </section>

          {/* RBA 카드 */}
          <section className="bg-surface-container-low rounded-xl ghost-border p-4">
            <p className="text-xs text-on-surface-variant/60 mb-1">RBA — 결과 기반 권장 손절폭</p>
            <p className="text-sm text-on-surface">
              평균수익 <b>{fmtPct(rba.avg_win_net)}</b> → 권장 최대 손절 <b style={{ color: rbaColor }}>{fmtPct(rba.recommended_max_stop_pct)}</b>
              {" "}(현재 기본 {rba.current_default_stop_pct}%,{" "}
              <span style={{ color: rbaColor }}>{rba.status === "too_wide" ? "손절이 너무 넓음" : rba.status === "ok" ? "적정" : "거래 부족"}</span>)
            </p>
          </section>

          {/* 진단 경고 */}
          {data.diagnostics.warnings.length > 0 && (
            <section className="bg-surface-container-low rounded-xl ghost-border p-4">
              <p className="text-xs text-on-surface-variant/60 mb-2">진단</p>
              <ul className="space-y-1">
                {data.diagnostics.warnings.map((w, i) => (
                  <li key={i} className="text-sm text-on-surface flex gap-2"><span>⚠️</span><span>{w}</span></li>
                ))}
              </ul>
            </section>
          )}

          {/* 월별 확인표 */}
          <section>
            <h3 className="text-lg font-serif font-bold text-on-surface mb-2">월별 확인표</h3>
            <div className="bg-surface-container-low rounded-xl ghost-border overflow-x-auto">
              <div className="min-w-[640px]">
                <div className={`${MONTH_COLS} text-xs text-on-surface-variant/60`}>
                  <span className="text-left">월</span><span>평균수익</span><span>평균손실</span><span>승률</span>
                  <span>거래</span><span>최대수익</span><span>최대손실</span><span>수익일</span><span>손실일</span>
                </div>
                {monthly.rows.map((r) => <MonthRow key={r.month} row={r} />)}
                <MonthRow row={monthly.average} isAvg />
              </div>
            </div>
          </section>

          {/* 왕복거래 목록 */}
          <section>
            <h3 className="text-lg font-serif font-bold text-on-surface mb-2">왕복거래</h3>
            <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
              {data.trades.map((t, i) => <TradeRow key={`${t.code}-${t.close_date}-${i}`} trade={t} basis={basis} />)}
            </div>
          </section>
        </>
      )}

      {/* 열린 포지션 (미청산) */}
      {data.open_positions.length > 0 && (
        <section>
          <h3 className="text-lg font-serif font-bold text-on-surface mb-2">열린 포지션 <span className="text-xs font-normal text-on-surface-variant/50">(미청산 · 실현 통계 제외)</span></h3>
          <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
            {data.open_positions.map((p) => <OpenRow key={p.code} pos={p} />)}
          </div>
        </section>
      )}
    </div>
  );
}
```

> 구현 시 주의: import한 헬퍼(`fmtNum` 등)·타입이 모두 실제로 사용되는지 최종 점검(미사용 import는 eslint 에러). 월 행 렌더는 `MonthRow`가 담당한다.

- [ ] **Step 2: 타입/린트 점검**

Run: `npx tsc --noEmit`
Expected: 클린(특히 `@/lib/scorecard` import 정합, `OverallStats`/`MonthlyRow`/`Trade`/`OpenPosition` 필드명 일치).

Run: `npx eslint src/app/stocks/sepa/score-card/ScorecardView.tsx`
Expected: 에러 없음(하위 컴포넌트가 모듈 스코프라 `react-hooks/static-components` 미발생, 미사용 변수 없음).

- [ ] **Step 3: 커밋**

```bash
git add src/app/stocks/sepa/score-card/ScorecardView.tsx
git commit -m "feat(scorecard-page): ScorecardView — 토글·삼각형·RBA·진단·월별표·거래목록·열린포지션"
```

---

## Task 3: 서버 페이지 `page.tsx` + StocksTabs 탭

**Files:**
- Create: `src/app/stocks/sepa/score-card/page.tsx`
- Modify: `src/app/stocks/StocksTabs.tsx`

**Interfaces:**
- Consumes: `ScorecardView`(Task 2), `Scorecard`(from `@/lib/scorecard`)
- Produces: 라우트 `/stocks/sepa/score-card`, StocksTabs에 정산표 탭

- [ ] **Step 1: 페이지 작성**

`src/app/stocks/sepa/score-card/page.tsx`:

```tsx
import fs from "fs/promises";
import path from "path";
import type { Scorecard } from "@/lib/scorecard";
import { ScorecardView } from "./ScorecardView";

async function readScorecard(): Promise<Scorecard | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "scorecard.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8")) as Scorecard;
  } catch {
    return null;
  }
}

export default async function ScorecardPage() {
  const data = await readScorecard();
  if (!data) {
    return (
      <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-sm text-on-surface-variant/70">
        정산표 데이터가 없습니다. <code className="text-xs">npm run scorecard</code> 실행 후 생성됩니다.
      </div>
    );
  }
  return <ScorecardView data={data} />;
}
```

- [ ] **Step 2: StocksTabs에 탭 추가**

`src/app/stocks/StocksTabs.tsx`의 `tabs` 배열 마지막(`sepa` 항목 다음)에 한 줄 추가:

```tsx
  { href: "/stocks/sepa", label: "SEPA 셋업", icon: "candlestick_chart" },
  { href: "/stocks/sepa/score-card", label: "정산표", icon: "scoreboard" },
];
```

- [ ] **Step 3: 타입·빌드·라우트 확인**

Run: `npx tsc --noEmit`
Expected: 클린.

Run: `npm run build`
Expected: 성공. 출력 라우트 목록에 `/stocks/sepa/score-card` 포함.

- [ ] **Step 4: 실제 렌더 확인 (수동)**

Run: `npm run dev` 후 브라우저 `http://localhost:3000/stocks/sepa/score-card` 접속(또는 `npm run build && npm run start`).
Expected:
- 상단 탭에 "정산표"가 보이고 활성 표시.
- 현재 `scorecard.json`(실거래 3건): 승률 33.33%, 평균수익 7.56%, 평균손실 -4.25%, 기대수익 -0.31%.
- 왕복거래 3건(타이거일렉 +7.56% 수익색, 비엠티·삼성전기 손실색), 삼성전기에 "손절위반" 없음.
- **[총수익] 토글** 클릭 → 숫자가 총수익 기준으로 바뀜(타이거 +8.08% 등), [순수익] 복귀 정상.
- 월별 확인표 2026-07 행 + 평균 행 표시.

확인 후 dev 서버 종료.

- [ ] **Step 5: 커밋**

```bash
git add src/app/stocks/sepa/score-card/page.tsx src/app/stocks/StocksTabs.tsx
git commit -m "feat(scorecard-page): /stocks/sepa/score-card 서버 페이지 + StocksTabs 정산표 탭"
```

---

## Self-Review (작성자 점검 완료)

- **스펙 커버리지**: §3 데이터흐름→Task 3 page + Task 2 ScorecardView. §4.1 머리말·토글→Task 2. §4.2 삼각형·§4.3 RBA·§4.4 진단·§4.5 월별표·§4.6 거래목록·§4.7 열린포지션→Task 2 전부. §5 파일 4개→Task 1~3. §6 디자인 토큰→전 태스크. §7 엣지(파일없음/거래0/열린포지션 없음)→page null 카드 + ScorecardView `!hasTrades` 분기 + open_positions 조건부. §8 검증→Task 1 vitest, Task 2 tsc/eslint, Task 3 build/렌더.
- **Placeholder 스캔**: 코드에 남은 미사용 스텁 `MonthlyRowView`는 본문에서 "삭제" 지시로 명시(구현자 혼동 방지). 그 외 TBD/모호 지시 없음.
- **타입 일관성**: `Scorecard.overall[basis]`→`OverallStats`(win_rate/avg_win/avg_loss/payoff_ratio/adj_payoff_ratio/expectancy/max_win/max_loss/win_days/loss_days/win_count/loss_count/trade_count) 실제 필드와 일치. `MonthlyRow`(month/avg_win/avg_loss/win_rate/trades/max_win/max_loss/win_days/loss_days) 일치. `Trade`(net_pct/gross_pct/open_date/close_date/hold_days/setup/stop_violation/name/code) 일치. `rba`(avg_win_net/recommended_max_stop_pct/current_default_stop_pct/status) 일치. `format.ts` 함수 시그니처 Task 1과 Task 2 사용처 일치.
- **범위**: 차트·필터·장부편집 없음(YAGNI). 계산 재구현 없음(읽기만).
