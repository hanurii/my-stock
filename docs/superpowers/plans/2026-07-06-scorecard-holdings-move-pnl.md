# 정산표 — 보유 점검 이동 + 총 손익(실현 금액) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보유 종목 점검 섹션을 정산표 페이지로 옮기고, 완결 거래의 실현 순손익 합계(원)를 순/총 토글 연동 헤드라인 타일로 추가한다.

**Architecture:** `scorecard.ts`가 완결 거래마다 원 손익(`net_won`/`gross_won`)을 산출하고 `computeOverall`이 basis별 합계(`total_won`)를 노출한다. `ScorecardView`가 그 값을 타일로 표시하고, 정산표 페이지가 `SepaHoldingsSection`을 함께 렌더한다. 기존 `/stocks/sepa`에선 보유 섹션을 제거한다.

**Tech Stack:** TypeScript · Next.js App Router(서버/클라이언트 컴포넌트) · Tailwind v4 · vitest

## Global Constraints

- 작업 위치: 워크트리 `C:\Users\hanul\playground\my-stock-scorecard-pl`, 브랜치 `feat/scorecard-holdings-pnl`(origin/master 기준). 모든 경로는 이 워크트리 기준.
- `node_modules`가 없으면 첫 빌드/테스트 전에 `npm install` 실행.
- 총 손익은 **실현 손익만**(완결 왕복거래), **순/총 토글**(`basis`)을 따라감. 미실현·거래별 원 칼럼은 범위 밖.
- 원 표기: `fmtSignedWon` — `+`/`-` 부호 + 천단위 콤마 + `원`. 이익 초록(`PROFIT_COLOR`)·손실 빨강(`LOSS_COLOR`)·0은 중립.
- 보유 섹션은 `/stocks/sepa`에서 **완전히 제거**하고 정산표 페이지에서만 렌더.
- 카피 평이한 한국어, 기존 파일 스타일. TDD, 커밋 자주.
- 파이썬 없음. 프론트 테스트: `npx vitest run`, 타입체크/빌드: `npm run build`.
- 스펙: `docs/superpowers/specs/2026-07-06-scorecard-holdings-move-pnl-design.md`.

---

### Task 1: `scorecard.ts` — 원 손익 필드 + 합계 (TDD)

**Files:**
- Modify: `src/lib/scorecard.ts` (Trade 타입 `:15`, `buildTrade` 반환 `:61-70`, OverallStats 타입 `:123-128`, `computeOverall` empty `:134-138`·return `:158-170`)
- Test: `src/lib/scorecard.test.ts`

**Interfaces:**
- Consumes: 기존 `matchTrades`, `computeOverall`, 타입 `Fill`/`Trade`, 테스트 헬퍼 `buy`/`sell`.
- Produces: `Trade.gross_won: number`, `Trade.net_won: number`; `OverallStats.total_won: number`.

- [ ] **Step 1: Write the failing tests**

`src/lib/scorecard.test.ts` 하단에 추가:

```ts
describe("원 손익(net_won/gross_won/total_won)", () => {
  it("완결 거래의 net_won/gross_won", () => {
    const { trades } = matchTrades([
      buy("2026-07-01", "T", 100, 10, { fees: 10 }),
      sell("2026-07-02", "T", 120, 10, { fees: 12, tax: 24 }),
    ]);
    expect(trades[0].gross_won).toBe(200); // (120-100)*10
    expect(trades[0].net_won).toBe(154);   // (1200-36) - (1000+10)
  });
  it("손실 거래는 net_won < 0", () => {
    const { trades } = matchTrades([
      buy("2026-07-01", "L", 100, 10, { fees: 10 }),
      sell("2026-07-02", "L", 90, 10, { fees: 9, tax: 18 }),
    ]);
    expect(trades[0].gross_won).toBe(-100);
    expect(trades[0].net_won).toBe(-137); // (900-27) - (1000+10)
  });
  it("computeOverall.total_won: basis별 합계", () => {
    const { trades } = matchTrades([
      buy("2026-07-01", "T", 100, 10, { fees: 10 }),
      sell("2026-07-02", "T", 120, 10, { fees: 12, tax: 24 }),
      buy("2026-07-01", "L", 100, 10, { fees: 10 }),
      sell("2026-07-02", "L", 90, 10, { fees: 9, tax: 18 }),
    ]);
    expect(computeOverall(trades, "net").total_won).toBe(17);   // 154 - 137
    expect(computeOverall(trades, "gross").total_won).toBe(100); // 200 - 100
  });
  it("거래 0건이면 total_won === 0", () => {
    expect(computeOverall([], "net").total_won).toBe(0);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/lib/scorecard.test.ts -t "원 손익"`
Expected: FAIL — `gross_won`/`net_won`/`total_won` undefined (또는 타입 에러).

- [ ] **Step 3: Add fields to the `Trade` type**

`src/lib/scorecard.ts:15` 의 `  gross_pct: number; net_pct: number;` 바로 아래 줄 추가:

```ts
  gross_won: number; net_won: number;
```

- [ ] **Step 4: Populate them in `buildTrade`**

`buildTrade` 반환 객체(`:65`)의 `gross_pct: round2(grossPct), net_pct: netPctR,` 바로 아래 줄 추가:

```ts
    gross_won: Math.round(sellVal - buyVal),
    net_won: Math.round(netProceeds - netCost),
```

- [ ] **Step 5: Add `total_won` to the `OverallStats` type**

`src/lib/scorecard.ts:128` 의 `  trade_count: number; win_count: number; loss_count: number;` 바로 아래 줄 추가:

```ts
  total_won: number;
```

- [ ] **Step 6: Populate `total_won` in `computeOverall`**

(a) `empty` 객체(`:137`)의 `... trade_count: 0, win_count: 0, loss_count: 0,` 뒤에 추가:

```ts
    total_won: 0,
```

(b) 실제 반환 객체(`:169`)의 `trade_count: n, win_count: wins.length, loss_count: losses.length,` 뒤에 추가:

```ts
    total_won: trades.reduce((s, t) => s + (basis === "net" ? t.net_won : t.gross_won), 0),
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: 신규 4개 포함 전부 PASS.

- [ ] **Step 8: Commit**

```bash
git add src/lib/scorecard.ts src/lib/scorecard.test.ts
git commit -m "feat(scorecard): 완결 거래 원 손익(net_won/gross_won) + total_won 합계"
```

---

### Task 2: `format.ts` — `fmtSignedWon` (TDD)

**Files:**
- Modify: `src/app/stocks/sepa/score-card/format.ts`
- Test: `src/app/stocks/sepa/score-card/format.test.ts`

**Interfaces:**
- Produces: `fmtSignedWon(n: number | null): string`.

- [ ] **Step 1: Write the failing test**

`src/app/stocks/sepa/score-card/format.test.ts` 하단(마지막 `});` 앞 describe 안 또는 새 it)에 추가. import 줄에 `fmtSignedWon` 추가:

```ts
  it("fmtSignedWon: 부호+천단위+원 / null은 -", () => {
    expect(fmtSignedWon(154)).toBe("+154원");
    expect(fmtSignedWon(-533186)).toBe("-533,186원");
    expect(fmtSignedWon(0)).toBe("+0원");
    expect(fmtSignedWon(null)).toBe("-");
  });
```

그리고 파일 최상단 import를 다음으로 교체:

```ts
import { fmtPct, fmtLossPct, fmtSignedPct, fmtNum, fmtRatio, plColor, fmtSignedWon, PROFIT_COLOR, LOSS_COLOR } from "./format";
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/app/stocks/sepa/score-card/format.test.ts -t fmtSignedWon`
Expected: FAIL — `fmtSignedWon` not exported.

- [ ] **Step 3: Implement**

`src/app/stocks/sepa/score-card/format.ts` 의 `plColor` 함수 아래에 추가:

```ts
export function fmtSignedWon(n: number | null): string {
  return n == null ? "-" : `${n >= 0 ? "+" : ""}${Math.round(n).toLocaleString()}원`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/app/stocks/sepa/score-card/format.test.ts`
Expected: PASS (기존 + 신규).

- [ ] **Step 5: Commit**

```bash
git add src/app/stocks/sepa/score-card/format.ts src/app/stocks/sepa/score-card/format.test.ts
git commit -m "feat(scorecard): fmtSignedWon 원 손익 포맷 헬퍼"
```

---

### Task 3: `ScorecardView` — 총 손익 타일

**Files:**
- Modify: `src/app/stocks/sepa/score-card/ScorecardView.tsx` (import 줄; 헤더/토글 블록 `:95` 아래 삽입)

**Interfaces:**
- Consumes: `data.overall[basis].total_won`(Task 1), `fmtSignedWon`(Task 2), 기존 `PROFIT_COLOR`/`LOSS_COLOR`.

- [ ] **Step 1: Import `fmtSignedWon`**

`ScorecardView.tsx` 상단 `./format` import 줄에 `fmtSignedWon`을 추가한다(기존 import 목록에 삽입). 예: 기존이
`import { fmtPct, fmtLossPct, fmtSignedPct, fmtNum, fmtRatio, plColor, PROFIT_COLOR, LOSS_COLOR } from "./format";`
이면 `plColor,` 뒤에 `fmtSignedWon,`를 넣는다.

- [ ] **Step 2: Insert the total-P/L tile**

`ScorecardView.tsx`에서 머리말+토글 블록의 닫는 `</div>`(스펙상 `:95`, `{!hasTrades ? (` 바로 위)와 `{!hasTrades ? (` 사이에 삽입:

```tsx
      {/* 총 손익 (실현 금액) */}
      <div className="bg-surface-container-low rounded-xl ghost-border p-4 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-xs text-on-surface-variant/60">총 손익 (실현)</p>
          <p className="text-[11px] text-on-surface-variant/50">
            완결 거래 · {basis === "net" ? "순수익" : "총수익"} 기준
          </p>
        </div>
        <p
          className="text-2xl sm:text-3xl font-bold tabular-nums"
          style={{ color: o.total_won > 0 ? PROFIT_COLOR : o.total_won < 0 ? LOSS_COLOR : "inherit" }}
        >
          {fmtSignedWon(o.total_won)}
        </p>
      </div>
```

- [ ] **Step 3: Typecheck + build**

Run: `npm run build`
Expected: 성공, 0 타입 에러. (`o.total_won`이 Task 1의 `OverallStats.total_won`으로 해결됨.)

- [ ] **Step 4: Commit**

```bash
git add src/app/stocks/sepa/score-card/ScorecardView.tsx
git commit -m "feat(scorecard): 총 손익(실현 금액) 헤드라인 타일 — 순/총 토글 연동"
```

---

### Task 4: 보유 점검 섹션 이동 (정산표 페이지 추가 · SEPA 페이지 제거)

**Files:**
- Modify(전체 교체): `src/app/stocks/sepa/score-card/page.tsx`
- Modify: `src/app/stocks/sepa/page.tsx` (import `:7`, holdings 로드 `:86`, 렌더 `:148` 제거)

**Interfaces:**
- Consumes: `SepaHoldingsSection`, 타입 `HoldingsFeedbackFile`(`../SepaHoldingsSection`), `sepa-holdings-feedback.json`.

- [ ] **Step 1: Replace `score-card/page.tsx`**

`src/app/stocks/sepa/score-card/page.tsx` 전체를 다음으로 교체:

```tsx
import fs from "fs/promises";
import path from "path";
import type { Scorecard } from "@/lib/scorecard";
import { ScorecardView } from "./ScorecardView";
import { SepaHoldingsSection, type HoldingsFeedbackFile } from "../SepaHoldingsSection";

async function readJson<T>(filename: string): Promise<T | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", filename);
    return JSON.parse(await fs.readFile(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

export default async function ScorecardPage() {
  const data = await readJson<Scorecard>("scorecard.json");
  const holdings = await readJson<HoldingsFeedbackFile>("sepa-holdings-feedback.json");
  return (
    <div className="space-y-10">
      {data ? (
        <ScorecardView data={data} />
      ) : (
        <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-sm text-on-surface-variant/70">
          정산표 데이터가 없습니다. <code className="text-xs">npm run scorecard</code> 실행 후 생성됩니다.
        </div>
      )}
      <SepaHoldingsSection data={holdings} />
    </div>
  );
}
```

(`SepaHoldingsSection`은 holdings가 `null`/빈 배열이면 `null`을 반환하므로 안전하다.)

- [ ] **Step 2: Remove holdings from `sepa/page.tsx`**

`src/app/stocks/sepa/page.tsx`에서 다음 3곳 제거:
- `:7` import 줄 통째 삭제: `import { SepaHoldingsSection, type HoldingsFeedbackFile } from "./SepaHoldingsSection";`
- `:86` 데이터 로드 줄 통째 삭제: `const holdingsFeedback = await readJson<HoldingsFeedbackFile>("sepa-holdings-feedback.json");`
- `:148` 렌더 줄 통째 삭제: `<SepaHoldingsSection data={holdingsFeedback} />`

다른 줄은 건드리지 않는다.

- [ ] **Step 3: Typecheck + build**

Run: `npm run build`
Expected: 성공, 0 타입 에러(미사용 import/변수 경고도 없음 — 3곳 모두 제거됨). `/stocks/sepa`·`/stocks/sepa/score-card` 두 라우트 모두 컴파일.

- [ ] **Step 4: Regression-test**

Run: `npx vitest run src/app/stocks/sepa src/lib/scorecard.test.ts`
Expected: 전부 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/app/stocks/sepa/score-card/page.tsx src/app/stocks/sepa/page.tsx
git commit -m "feat(sepa): 보유 종목 점검 섹션을 정산표 페이지로 이동"
```

---

### Task 5: 정산표 데이터 재생성

**Files:**
- Modify(생성물): `public/data/scorecard.json`

**Interfaces:**
- Consumes: `scripts/build-scorecard.ts`(변경 없음), `public/data/scorecard-fills.json`(기존).

- [ ] **Step 1: Regenerate**

Run: `npm run scorecard`
Expected: `저장됨: ...scorecard.json` 출력, 오류 없음.

- [ ] **Step 2: Verify won fields present**

Run:
```bash
node -e "const d=require('./public/data/scorecard.json'); console.log('net_won 예시:', d.trades[0]?.net_won, '| overall.net.total_won:', d.overall.net.total_won, '| overall.gross.total_won:', d.overall.gross.total_won);"
```
Expected: `net_won 예시:`에 정수, `overall.net.total_won`·`overall.gross.total_won` 정수 출력(완결 4건 기준).

- [ ] **Step 3: Confirm only scorecard.json changed**

Run: `git status --short public/data/`
Expected: `M public/data/scorecard.json` 만.

- [ ] **Step 4: Commit**

```bash
git add public/data/scorecard.json
git commit -m "data(scorecard): total_won 포함 정산표 재생성"
```

---

## Self-Review

**1. Spec coverage**
- 보유 점검 이동(정산표 추가 + SEPA 제거) → Task 4. ✅
- 총 손익 실현 금액 + 순/총 토글 → Task 1(total_won basis별) + Task 3(타일). ✅
- 포맷 헬퍼 fmtSignedWon → Task 2. ✅
- 단위테스트(net_won/gross_won/total_won/손실 음수/0건) → Task 1·2. ✅
- scorecard.json 재생성 → Task 5. ✅
- 범위 밖(미실현·거래별 칼럼) → 태스크 없음(의도적). ✅

**2. Placeholder scan** — "TBD/TODO/적절히" 없음. 모든 코드 스텝에 실제 코드·명령·기대 출력 포함. ✅

**3. Type consistency**
- `Trade.gross_won/net_won`(Task 1) ↔ `buildTrade` 채움(Task 1) ↔ `computeOverall`의 `t.net_won`/`t.gross_won` 참조(Task 1) 일치. ✅
- `OverallStats.total_won`(Task 1) ↔ `ScorecardView`의 `o.total_won`(Task 3) 일치. ✅
- `fmtSignedWon`(Task 2) ↔ format.test import(Task 2) ↔ ScorecardView import·사용(Task 3) 일치. ✅
- `HoldingsFeedbackFile`·`SepaHoldingsSection`(`../SepaHoldingsSection`) — 정산표 페이지에서 상대경로 `../` 정확(score-card는 sepa의 하위 디렉토리). ✅

---

## Execution Handoff

순서: Task 1(백엔드+테스트) → 2(포맷+테스트) → 3(타일, 1·2 의존) → 4(이동) → 5(재생성, 1 의존). 각 태스크는 독립 테스트/빌드로 검증.
