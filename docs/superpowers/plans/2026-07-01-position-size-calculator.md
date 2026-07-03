# 포지션 크기 계산기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/stocks/sepa` 페이지에 미너비니 리스크 규칙 기반 포지션 크기·손절 라인 계산기 섹션을 추가한다.

**Architecture:** 기존 SEPA 페이지 패턴을 따른다 — 순수 계산 로직(`positionSizing.ts`, vitest 테스트)을 클라이언트 컴포넌트(`PositionSizeCalculator.tsx`)가 호출하고, 서버 컴포넌트 `page.tsx`가 정적 규칙 + 계산기 섹션을 렌더한다.

**Tech Stack:** Next.js 16 App Router, React, TypeScript, Tailwind(테마 토큰), vitest.

## Global Constraints

- 균등 분할(1/N) 가정. 커스텀 비중·실진입가 입력은 범위 밖(YAGNI).
- 핵심 공식: **계좌 위험(%) = 포지션 비중(%) × 손절 라인(%)**.
- 미너비니 상수(정확값): `ACCOUNT_RISK_MIN=1.25`, `ACCOUNT_RISK_MAX=2.5`, `MAX_STOP_PCT=10`, `MAX_POSITION_PCT=50`, `BEST_POSITION_PCT=25`, `MAX_STOCKS=12` (모두 총자본 대비 % 또는 개수).
- 손절 권장: 하한 `min(10, 1.25×N)`, 상한 `min(10, 2.5×N)` (%).
- 순수 로직은 프레임워크 비의존(React/Next import 금지) — node-env vitest로 로드.
- 기존 페이지·빌드 무영향: `next build` 성공, `eslint`·`tsc` 클린.
- UI 관례: 테마 토큰(`surface-container-low`, `on-surface`, `on-surface-variant`, `ghost-border`), `material-symbols-outlined` 아이콘, 한국어.
- 작업 위치: `my-stock-master` 워크트리(master 체크아웃, 완전한 node_modules 설치됨). 검증은 `npm run test`·`npx tsc --noEmit`·`npm run build`.

---

### Task 1: 순수 계산 모듈 `positionSizing.ts`

미너비니 상수 + `computePositionSizing` + 원화 포맷터 `fmtKRW`. vitest로 테스트.

**Files:**
- Create: `src/app/stocks/sepa/positionSizing.ts`
- Test: `src/app/stocks/sepa/positionSizing.test.ts`

**Interfaces:**
- Consumes: 없음(순수).
- Produces (Task 2 의존):
  - 상수: `ACCOUNT_RISK_MIN`, `ACCOUNT_RISK_MAX`, `MAX_STOP_PCT`, `MAX_POSITION_PCT`, `BEST_POSITION_PCT`, `MAX_STOCKS` (number)
  - `interface PositionSizing { valid: boolean; positionAmount: number; positionWeightPct: number; stopLowPct: number; stopHighPct: number; lossAtLow: number; lossAtHigh: number; riskAtLowPct: number; riskAtHighPct: number; warnings: string[] }`
  - `function computePositionSizing(capital: number, numStocks: number): PositionSizing`
  - `function fmtKRW(n: number): string`

- [ ] **Step 1: 실패 테스트 작성**

Create `src/app/stocks/sepa/positionSizing.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { computePositionSizing, fmtKRW } from "./positionSizing";

describe("computePositionSizing", () => {
  it("기준 예시: 1.5억 · 5종목", () => {
    const r = computePositionSizing(150_000_000, 5);
    expect(r.valid).toBe(true);
    expect(r.positionAmount).toBe(30_000_000);
    expect(r.positionWeightPct).toBe(20);
    expect(r.stopLowPct).toBe(6.25);
    expect(r.stopHighPct).toBe(10);
    expect(r.lossAtLow).toBe(1_875_000);
    expect(r.lossAtHigh).toBe(3_000_000);
    expect(r.riskAtLowPct).toBeCloseTo(1.25, 6);
    expect(r.riskAtHighPct).toBeCloseTo(2.0, 6);
    expect(r.warnings).toEqual([]);
  });

  it("N=4: 비중 25%, 경고 없음, 손절 5~10%", () => {
    const r = computePositionSizing(100_000_000, 4);
    expect(r.positionWeightPct).toBe(25);
    expect(r.stopLowPct).toBe(5);
    expect(r.stopHighPct).toBe(10);
    expect(r.riskAtLowPct).toBeCloseTo(1.25, 6);
    expect(r.riskAtHighPct).toBeCloseTo(2.5, 6);
    expect(r.warnings).toEqual([]);
  });

  it("N=2: 비중 50% → '>25% 권장 초과' 경고", () => {
    const r = computePositionSizing(100_000_000, 2);
    expect(r.positionWeightPct).toBe(50);
    expect(r.stopLowPct).toBe(2.5);
    expect(r.stopHighPct).toBe(5);
    expect(r.warnings.some((w) => w.includes("25%"))).toBe(true);
    expect(r.warnings.some((w) => w.includes("50%"))).toBe(false);
  });

  it("N=1: 비중 100% → '50% 초과' 경고", () => {
    const r = computePositionSizing(100_000_000, 1);
    expect(r.positionWeightPct).toBe(100);
    expect(r.warnings.some((w) => w.includes("50%"))).toBe(true);
  });

  it("N=15: '>12개' + '보수적'(10% 손절도 위험<1.25%) 경고, 손절 10% 캡", () => {
    const r = computePositionSizing(150_000_000, 15);
    expect(r.stopLowPct).toBe(10);
    expect(r.stopHighPct).toBe(10);
    expect(r.riskAtHighPct).toBeLessThan(1.25);
    expect(r.warnings.some((w) => w.includes("12개"))).toBe(true);
    expect(r.warnings.some((w) => w.includes("보수적"))).toBe(true);
  });

  it("유효성: capital 0 / numStocks 0 → valid false", () => {
    expect(computePositionSizing(0, 5).valid).toBe(false);
    expect(computePositionSizing(150_000_000, 0).valid).toBe(false);
    expect(computePositionSizing(-1, 5).valid).toBe(false);
  });

  it("소수 종목 수는 내림(floor)", () => {
    const r = computePositionSizing(150_000_000, 5.9);
    expect(r.positionWeightPct).toBe(20); // floor(5.9)=5
  });
});

describe("fmtKRW", () => {
  it("억·만원 단위", () => {
    expect(fmtKRW(150_000_000)).toBe("1억 5,000만원");
    expect(fmtKRW(30_000_000)).toBe("3,000만원");
    expect(fmtKRW(1_875_000)).toBe("187.5만원");
    expect(fmtKRW(100_000_000)).toBe("1억원");
    expect(fmtKRW(0)).toBe("0원");
    expect(fmtKRW(5_000)).toBe("5,000원");
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd /c/Users/hanul/playground/my-stock-master && npm run test`
Expected: FAIL — `Cannot find module './positionSizing'`.

- [ ] **Step 3: `positionSizing.ts` 구현**

Create `src/app/stocks/sepa/positionSizing.ts`:

```ts
// 미너비니 리스크 규칙 기반 포지션 크기·손절 계산 (순수 로직, 프레임워크 비의존).
// 핵심: 계좌 위험(%) = 포지션 비중(%) × 손절 라인(%). 균등 분할(1/N) 가정.

export const ACCOUNT_RISK_MIN = 1.25;  // 한 매매 최소 권장 위험(총자본 %)
export const ACCOUNT_RISK_MAX = 2.5;   // 한 매매 최대 권장 위험(총자본 %)
export const MAX_STOP_PCT = 10;        // 최대 손절(%)
export const MAX_POSITION_PCT = 50;    // 한 종목 최대 비중(%)
export const BEST_POSITION_PCT = 25;   // 최고 종목 권장 상한(%)
export const MAX_STOCKS = 12;          // 최대 종목 수

export interface PositionSizing {
  valid: boolean;
  positionAmount: number;     // 포지션당 분배금액(원)
  positionWeightPct: number;  // 포지션 비중(%) = 100/N
  stopLowPct: number;         // 손절 하한(%) — 위험 1.25%용
  stopHighPct: number;        // 손절 상한(%) — 위험 2.5%용(보통 10% 캡)
  lossAtLow: number;          // 손절 하한에서 1종목 손실액(원)
  lossAtHigh: number;         // 손절 상한에서 1종목 손실액(원)
  riskAtLowPct: number;       // 손절 하한에서 계좌 위험(%)
  riskAtHighPct: number;      // 손절 상한에서 계좌 위험(%)
  warnings: string[];
}

export function computePositionSizing(capital: number, numStocks: number): PositionSizing {
  const n = Math.floor(numStocks);
  if (!(capital > 0) || !(n >= 1)) {
    return {
      valid: false, positionAmount: 0, positionWeightPct: 0,
      stopLowPct: 0, stopHighPct: 0, lossAtLow: 0, lossAtHigh: 0,
      riskAtLowPct: 0, riskAtHighPct: 0, warnings: [],
    };
  }

  const positionWeightPct = 100 / n;
  const positionAmount = capital / n;
  const stopLowPct = Math.min(MAX_STOP_PCT, ACCOUNT_RISK_MIN * n);
  const stopHighPct = Math.min(MAX_STOP_PCT, ACCOUNT_RISK_MAX * n);
  const lossAtLow = (positionAmount * stopLowPct) / 100;
  const lossAtHigh = (positionAmount * stopHighPct) / 100;
  const riskAtLowPct = (positionWeightPct * stopLowPct) / 100;
  const riskAtHighPct = (positionWeightPct * stopHighPct) / 100;

  const warnings: string[] = [];
  if (positionWeightPct > MAX_POSITION_PCT) {
    warnings.push("한 종목 비중이 50%를 초과합니다 — 분산 부족(미너비니 최대 50%).");
  } else if (positionWeightPct > BEST_POSITION_PCT) {
    warnings.push("포지션 비중이 25%를 초과합니다 — 최고 종목도 20~25% 권장.");
  }
  if (n > MAX_STOCKS) {
    warnings.push("종목 수가 12개를 초과합니다 — 미너비니 권장 10~12개.");
  }
  if (riskAtHighPct < ACCOUNT_RISK_MIN) {
    warnings.push("비중이 작아 10% 손절에도 계좌 위험이 1.25% 미만입니다(보수적 — 위험 여력 있음).");
  }

  return {
    valid: true, positionAmount, positionWeightPct,
    stopLowPct, stopHighPct, lossAtLow, lossAtHigh,
    riskAtLowPct, riskAtHighPct, warnings,
  };
}

// 원화를 억·만원 단위로 읽기 쉽게. 1만원 미만은 원 단위.
export function fmtKRW(n: number): string {
  if (!(n > 0)) return "0원";
  if (n < 1e4) return `${Math.round(n).toLocaleString()}원`;
  const eok = Math.floor(n / 1e8);
  const man = Math.round(((n - eok * 1e8) / 1e4) * 10) / 10;
  const parts: string[] = [];
  if (eok > 0) parts.push(`${eok.toLocaleString()}억`);
  if (man > 0) parts.push(`${man.toLocaleString()}만`);
  return `${parts.join(" ")}원`;
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd /c/Users/hanul/playground/my-stock-master && npm run test`
Expected: 신규 테스트 전부 PASS (기존 `sepaPatterns.test.ts` 21건도 그대로 PASS).

- [ ] **Step 5: 타입·린트 확인**

Run: `cd /c/Users/hanul/playground/my-stock-master && npx tsc --noEmit && npx eslint src/app/stocks/sepa/positionSizing.ts`
Expected: 에러 없음.

- [ ] **Step 6: 커밋**

```bash
git add src/app/stocks/sepa/positionSizing.ts src/app/stocks/sepa/positionSizing.test.ts
git commit -m "feat(sepa): 포지션 크기·손절 계산 순수 모듈 + vitest"
```

---

### Task 2: 계산기 컴포넌트 + 페이지 섹션

`PositionSizeCalculator.tsx`(클라이언트, 덤 렌더러)와 `page.tsx` 섹션(정적 규칙 + 계산기). 단위 테스트 없음(프로젝트 React 테스트 환경 부재 — 로직은 Task 1에서 검증). tsc/eslint/build로 검증.

**Files:**
- Create: `src/app/stocks/sepa/PositionSizeCalculator.tsx`
- Modify: `src/app/stocks/sepa/page.tsx` (import + 섹션 추가)

**Interfaces:**
- Consumes (Task 1): `computePositionSizing`, `fmtKRW`.
- Produces: `export function PositionSizeCalculator(): JSX.Element` (page.tsx가 렌더).

- [ ] **Step 1: 컴포넌트 구현**

Create `src/app/stocks/sepa/PositionSizeCalculator.tsx`:

```tsx
"use client";

import { useState } from "react";
import { computePositionSizing, fmtKRW } from "./positionSizing";

export function PositionSizeCalculator() {
  const [capital, setCapital] = useState<number>(150_000_000);
  const [numStocks, setNumStocks] = useState<number>(5);
  const r = computePositionSizing(capital, numStocks);
  const stopLabel =
    r.stopLowPct === r.stopHighPct
      ? `${r.stopLowPct.toFixed(2)}%`
      : `${r.stopLowPct.toFixed(2)}% ~ ${r.stopHighPct.toFixed(2)}%`;
  const lossLabel =
    r.lossAtLow === r.lossAtHigh
      ? fmtKRW(r.lossAtLow)
      : `${fmtKRW(r.lossAtLow)} ~ ${fmtKRW(r.lossAtHigh)}`;

  return (
    <div className="space-y-3">
      {/* 입력 */}
      <div className="flex flex-wrap gap-3 items-end text-xs">
        <label className="flex flex-col gap-1">
          <span className="text-on-surface-variant/70">총 투입금액(원)</span>
          <input
            type="number"
            min={0}
            step={1_000_000}
            value={capital}
            onChange={(e) => setCapital(Math.max(0, Number(e.target.value) || 0))}
            className="w-48 bg-surface-container rounded px-2 py-1.5 text-on-surface text-right ghost-border"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-on-surface-variant/70">종목 수</span>
          <input
            type="number"
            min={1}
            max={50}
            step={1}
            value={numStocks}
            onChange={(e) => setNumStocks(Math.max(0, Math.floor(Number(e.target.value) || 0)))}
            className="w-24 bg-surface-container rounded px-2 py-1.5 text-on-surface text-right ghost-border"
          />
        </label>
        {capital > 0 && (
          <span className="text-on-surface-variant/50 self-center pb-1.5">= {fmtKRW(capital)}</span>
        )}
      </div>

      {!r.valid ? (
        <p className="text-on-surface-variant/60 text-sm">총 투입금액과 종목 수를 입력하세요.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-surface-container-low rounded-lg p-3 ghost-border">
            <p className="text-[11px] text-on-surface-variant/70 mb-1">포지션당 분배</p>
            <p className="text-lg font-serif font-bold text-on-surface">{fmtKRW(r.positionAmount)}</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-0.5">비중 {r.positionWeightPct.toFixed(1)}%</p>
          </div>
          <div className="bg-surface-container-low rounded-lg p-3 ghost-border">
            <p className="text-[11px] text-on-surface-variant/70 mb-1">권장 손절 라인</p>
            <p className="text-lg font-serif font-bold" style={{ color: "#e9c176" }}>{stopLabel}</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-0.5">
              계좌 위험 {r.riskAtLowPct.toFixed(2)}% ~ {r.riskAtHighPct.toFixed(2)}%
            </p>
          </div>
          <div className="bg-surface-container-low rounded-lg p-3 ghost-border">
            <p className="text-[11px] text-on-surface-variant/70 mb-1">1종목 최대 손실(손절 시)</p>
            <p className="text-lg font-serif font-bold" style={{ color: "#ffb4ab" }}>{lossLabel}</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-0.5">손절 {stopLabel} 기준</p>
          </div>
        </div>
      )}

      {r.warnings.length > 0 && (
        <ul className="space-y-1">
          {r.warnings.map((w, i) => (
            <li key={i} className="text-[11px] text-amber-300 flex items-start gap-1">
              <span className="material-symbols-outlined text-[14px] leading-none">warning</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: page.tsx에 import + 섹션 추가**

`src/app/stocks/sepa/page.tsx` 상단 import 블록에 추가(기존 `SepaPatternTable` import 아래):

```tsx
import { PositionSizeCalculator } from "./PositionSizeCalculator";
```

그리고 3C 패턴 섹션(`<PatternSection config={PATTERNS.threeC} data={threeC} />`) **바로 다음**, 용어 섹션(`{/* 용어·배지 */}`) **앞**에 새 섹션을 삽입:

```tsx
      <PatternSection config={PATTERNS.threeC} data={threeC} />

      {/* 포지션 크기 계산기 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 space-y-3">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">calculate</span>
          포지션 크기 계산기 (미너비니 기준)
        </h3>
        <ul className="text-xs text-on-surface-variant/80 space-y-0.5 list-disc list-inside">
          <li>한 매매 위험은 총 자본의 1.25~2.50%, 최대 손절 10%, 손실 평균 5~6% 이내.</li>
          <li>한 종목 비중 50% 초과 금지 · 최고 종목엔 총포지션의 20~25%.</li>
          <li>최대 종목 수 10~12개.</li>
        </ul>
        <PositionSizeCalculator />
      </section>

      {/* 용어·배지 */}
```

(주의: 위 `{/* 용어·배지 */}` 줄은 기존 코드의 앵커이며 중복 추가하지 말 것 — 새 섹션을 그 앞에 끼워 넣는다.)

- [ ] **Step 3: 빌드·린트 확인**

Run: `cd /c/Users/hanul/playground/my-stock-master && npx tsc --noEmit && npx eslint src/app/stocks/sepa/PositionSizeCalculator.tsx src/app/stocks/sepa/page.tsx && npm run build`
Expected: 타입·린트 에러 없음, `next build` 성공(`/stocks/sepa` 정적 라우트 포함).

- [ ] **Step 4: 수동 시각 확인**

Run: `cd /c/Users/hanul/playground/my-stock-master && npm run dev` → `http://localhost:3000/stocks/sepa`
Expected: 패턴 섹션 아래 "포지션 크기 계산기" 섹션. 기본값(1.5억·5종목) → 포지션당 3,000만원(20%), 손절 6.25%~10%, 1종목 손실 187.5만원~300만원, 위험 1.25%~2.0%, 경고 없음. 종목 수 1·2·15 등으로 바꾸면 경고/손절이 즉시 갱신.

- [ ] **Step 5: 커밋**

```bash
git add src/app/stocks/sepa/PositionSizeCalculator.tsx src/app/stocks/sepa/page.tsx
git commit -m "feat(sepa): 포지션 크기 계산기 섹션 + 미너비니 규칙 참고"
```

---

## Self-Review

**Spec coverage:**
- §2 미너비니 6규칙 정적 표시 → Task 2 Step 2 (섹션 ul) ✓
- §3 공식(위험=비중×손절) → Task 1 computePositionSizing ✓
- §4 계산 로직·상수·경고 → Task 1 Step 3 + 테스트 ✓
- §5 구성요소(positionSizing.ts/Calculator.tsx/page.tsx) → Task 1·2 ✓
- §6 레이아웃(입력→포지션/손절/손실 카드, 하한=상한 단일 표시) → Task 2 Step 1 (stopLabel/lossLabel 동일값 처리) ✓
- §7 에러·엣지(0/음수 → 안내, floor) → Task 1(valid=false) + Task 2(!r.valid 안내) ✓
- §8 테스트(기준예시·N=1/2/4/15·유효성·fmtKRW) → Task 1 Step 1 ✓
- §10 성공기준(렌더·기준예시·vitest·build) → Task 2 Step 3-4 + Task 1 ✓

**Placeholder scan:** 코드 스텝 모두 완전한 코드. Task 2는 단위 테스트 없음(프로젝트 React 테스트 환경 부재, 로직은 Task 1에서 검증 — 명시적 의도, 플레이스홀더 아님).

**Type consistency:** `PositionSizing` 필드명(positionAmount·positionWeightPct·stopLowPct·stopHighPct·lossAtLow·lossAtHigh·riskAtLowPct·riskAtHighPct·warnings·valid)이 Task 1 정의·Task 2 사용에서 동일. `computePositionSizing(capital, numStocks)`·`fmtKRW(n)` 시그니처가 Task 1 정의·Task 2 호출에서 일치.
