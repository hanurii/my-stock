# /stocks/sepa SEPA 멀티 패턴 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SEPA 파이프라인 산출(트렌드 1단계 + VCP·파워플레이·3C 패턴)을 패턴별 섹션으로 보여주는 `/stocks/sepa` 페이지를 만든다. 각 섹션은 만족(🔴돌파/🟢진입임박) + 곧 만족할(🟡예의주시) 종목을 노출한다.

**Architecture:** 기존 `trend-template/page.tsx` 패턴을 따른다 — 서버 컴포넌트가 `public/data` JSON을 `fs`로 읽고, 순수 분류 로직(`sepaPatterns.ts`, vitest 테스트)으로 종목을 티어 분류·정렬한 뒤, 컬럼 설정으로 구동되는 클라이언트 정렬 테이블(`SepaPatternTable.tsx`)로 패턴별 섹션을 렌더한다. 패턴은 레지스트리로 확장(설정 1줄 + 컬럼).

**Tech Stack:** Next.js 16 App Router, React, TypeScript, Tailwind(테마 토큰), Material Symbols 아이콘. 테스트: vitest(신규 도입, node 환경).

## Global Constraints

- 데이터 **읽기 전용**: `public/data`의 SEPA JSON을 수정/생성/커밋하지 않는다. 데이터 갱신·머지는 별도 트랙.
- 파일 없거나 깨지면 **graceful**: 그 섹션만 자리표시, 페이지·빌드는 안 깨짐. (트렌드 파일만 없으면 페이지 전체 안내.)
- **예의주시 임계 `WATCH_PCT = 12`** (모듈 상수, 한 곳).
- 티어 규칙(확정): 🔴 `detected && status==="breakout"` / 🟢 `detected && status==="actionable"` / 🟡 `(detected && status==="forming")` 또는 `(status!=="failed" && pivot_price!=null && 0≤pct_to_pivot≤12 && structureOk)` / 그 외 숨김.
- `pct_to_pivot` 부호: `(pivot − 종가)/pivot×100`. 양수 = 종가가 피벗 아래.
- 티어 내 정렬: 티어(🔴→🟢→🟡) → `abs(pct_to_pivot)` 오름차순 → `rs` 내림차순.
- `structureOk`: VCP=`num_contractions≥2`, 파워플레이=`flag_length_days>0`, 기본=`pivot_price!=null`.
- 기존 페이지·빌드 무영향: `next build` 성공, `eslint` 통과, 공유 컴포넌트 무수정(StocksTabs는 탭 1개 추가만).
- 기존 코드 스타일 준수: 테마 토큰(`surface-container-low`, `on-surface`, `ghost-border`, `text-on-surface-variant`), `material-symbols-outlined` 아이콘, 한국어 UI 문구.

---

### Task 1: vitest 도입 + 순수 분류 모듈 `sepaPatterns.ts`

티어 분류·정렬·섹션 빌드·패턴 레지스트리를 담는 프레임워크 비의존 순수 모듈과 그 단위 테스트. vitest를 프로젝트에 처음 도입한다(이 테스트가 첫 사용처라 설정을 이 태스크에 포함).

**Files:**
- Modify: `package.json` (devDependency `vitest` + `"test": "vitest run"` 스크립트)
- Create: `vitest.config.ts`
- Create: `src/app/stocks/sepa/sepaPatterns.ts`
- Test: `src/app/stocks/sepa/sepaPatterns.test.ts`

**Interfaces:**
- Consumes: 없음(순수).
- Produces (later tasks 의존):
  - `type Tier = "breakout" | "actionable" | "watch"`
  - `type PatternStatus = "breakout" | "actionable" | "forming" | "failed"`
  - `interface RawCandidate { code: string; name: string; market: string; current_price: number; rs: number | null; status?: string; pivot_price?: number | null; pct_to_pivot?: number | null; [k: string]: unknown }`
  - `interface ClassifiedRow { code: string; name: string; market: string; current_price: number; rs: number | null; status: string; pivot_price: number | null; pct_to_pivot: number | null; tier: Tier; raw: RawCandidate }`
  - `interface PatternColumn { key: string; label: string; kind: "pct" | "price" | "int" | "ratio" | "days" | "tight" }`
  - `interface PatternConfig { id: string; label: string; file: string; detectField: string; structureOk: (raw: RawCandidate) => boolean; columns: PatternColumn[] }`
  - `interface SectionResult { rows: ClassifiedRow[]; counts: { breakout: number; actionable: number; watch: number } }`
  - `const WATCH_PCT = 12`
  - `function classify(c: { detected: boolean; status: string; pivot_price: number | null; pct_to_pivot: number | null; structureOk: boolean }, watchPct?: number): Tier | null`
  - `function sortRows(rows: ClassifiedRow[]): void` (in-place)
  - `function buildSection(candidates: RawCandidate[] | null | undefined, config: PatternConfig, watchPct?: number): SectionResult`
  - `const PATTERNS: { vcp: PatternConfig; powerplayTrend: PatternConfig; powerplayAll: PatternConfig; threeC: PatternConfig }`
  - formatters: `fmtPct(n, digits?)`, `fmtPrice(n)`, `fmtCell(value, kind)`

- [ ] **Step 1: vitest 설치 + 스크립트**

`package.json`의 `scripts`에 `"test": "vitest run"` 추가하고, `devDependencies`에 vitest를 추가한다. 명령:

Run: `cd /c/Users/hanul/playground/my-stock && npm install -D vitest@^3`
Expected: `vitest` 가 devDependencies에 추가됨(설치 성공). 이후 `package.json` scripts에 수동으로 `"test": "vitest run"` 한 줄을 추가(아래 Step 5에서 테스트 실행에 사용).

`package.json` scripts 블록을 다음처럼 만든다(기존 줄 유지, test만 추가):

```json
  "scripts": {
    "dev": "next dev",
    "preview": "next build && next start",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "test": "vitest run"
  },
```

- [ ] **Step 2: vitest 설정 파일**

Create `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
```

- [ ] **Step 3: 실패 테스트 작성**

Create `src/app/stocks/sepa/sepaPatterns.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import {
  classify,
  sortRows,
  buildSection,
  PATTERNS,
  WATCH_PCT,
  type ClassifiedRow,
  type RawCandidate,
} from "./sepaPatterns";

const base = { detected: true, structureOk: true, pivot_price: 100, pct_to_pivot: 5 };

describe("classify", () => {
  it("WATCH_PCT 상수는 12", () => {
    expect(WATCH_PCT).toBe(12);
  });
  it("detected + breakout → 🔴 breakout", () => {
    expect(classify({ ...base, status: "breakout", pct_to_pivot: -8 })).toBe("breakout");
  });
  it("detected + actionable → 🟢 actionable", () => {
    expect(classify({ ...base, status: "actionable" })).toBe("actionable");
  });
  it("detected + forming → 🟡 watch (피벗 거리 무관)", () => {
    expect(classify({ ...base, status: "forming", pct_to_pivot: 50 })).toBe("watch");
  });
  it("미검출 + forming + 피벗 0~12% 근접 + 구조 → 🟡 watch", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: 8 })).toBe("watch");
  });
  it("경계: pct_to_pivot 정확히 12 → 포함(watch)", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: 12 })).toBe("watch");
  });
  it("경계: pct_to_pivot 12.01 → 숨김(null)", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: 12.01 })).toBeNull();
  });
  it("경계: pct_to_pivot 0 → 포함, 음수(미검출) → 숨김", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: 0 })).toBe("watch");
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: -0.01 })).toBeNull();
  });
  it("미검출 + 근접하지만 구조 미형성 → 숨김", () => {
    expect(classify({ detected: false, structureOk: false, status: "forming", pivot_price: 100, pct_to_pivot: 5 })).toBeNull();
  });
  it("failed → 숨김", () => {
    expect(classify({ ...base, status: "failed" })).toBeNull();
    expect(classify({ detected: false, structureOk: true, status: "failed", pivot_price: 100, pct_to_pivot: 3 })).toBeNull();
  });
  it("피벗 없음 + 미검출 → 숨김", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: null, pct_to_pivot: null })).toBeNull();
  });
  it("미검출 breakout(피벗 위, pct 음수) → 근접 아님 → 숨김", () => {
    expect(classify({ detected: false, structureOk: true, status: "breakout", pivot_price: 100, pct_to_pivot: -8 })).toBeNull();
  });
});

function row(over: Partial<ClassifiedRow>): ClassifiedRow {
  return {
    code: "0", name: "n", market: "KOSPI", current_price: 1, rs: 50,
    status: "forming", pivot_price: 100, pct_to_pivot: 5, tier: "watch",
    raw: {} as RawCandidate, ...over,
  };
}

describe("sortRows", () => {
  it("티어 우선(🔴→🟢→🟡), 동률은 피벗 거리(절댓값) 가까운 순, 그다음 RS 내림차순", () => {
    const rows = [
      row({ code: "watchFar", tier: "watch", pct_to_pivot: 10, rs: 90 }),
      row({ code: "breakoutA", tier: "breakout", pct_to_pivot: -20, rs: 50 }),
      row({ code: "breakoutB", tier: "breakout", pct_to_pivot: -2, rs: 50 }),
      row({ code: "actionable", tier: "actionable", pct_to_pivot: 1, rs: 70 }),
      row({ code: "watchNearLowRs", tier: "watch", pct_to_pivot: 3, rs: 40 }),
      row({ code: "watchNearHighRs", tier: "watch", pct_to_pivot: 3, rs: 95 }),
    ];
    sortRows(rows);
    expect(rows.map((r) => r.code)).toEqual([
      "breakoutB",       // 🔴 abs 2
      "breakoutA",       // 🔴 abs 20
      "actionable",      // 🟢
      "watchNearHighRs", // 🟡 abs 3, rs 95
      "watchNearLowRs",  // 🟡 abs 3, rs 40
      "watchFar",        // 🟡 abs 10
    ]);
  });
});

describe("buildSection", () => {
  it("null 후보 → 빈 결과", () => {
    const r = buildSection(null, PATTERNS.vcp);
    expect(r.rows).toEqual([]);
    expect(r.counts).toEqual({ breakout: 0, actionable: 0, watch: 0 });
  });

  it("VCP: detectField·structureOk 적용, 숨김 제외, 카운트", () => {
    const cands: RawCandidate[] = [
      { code: "A", name: "a", market: "KOSPI", current_price: 1, rs: 90, status: "breakout", pivot_price: 100, pct_to_pivot: -5, vcp_detected: true, num_contractions: 3 },
      { code: "B", name: "b", market: "KOSDAQ", current_price: 1, rs: 80, status: "actionable", pivot_price: 100, pct_to_pivot: 2, vcp_detected: true, num_contractions: 2 },
      { code: "C", name: "c", market: "KOSPI", current_price: 1, rs: 70, status: "forming", pivot_price: 100, pct_to_pivot: 7, vcp_detected: false, num_contractions: 2 },
      { code: "D-hidden", name: "d", market: "KOSPI", current_price: 1, rs: 60, status: "forming", pivot_price: 100, pct_to_pivot: 7, vcp_detected: false, num_contractions: 1 }, // 구조 미형성(수축<2) → 숨김
      { code: "E-hidden", name: "e", market: "KOSPI", current_price: 1, rs: 60, status: "failed", pivot_price: 100, pct_to_pivot: 1, vcp_detected: false, num_contractions: 3 },
    ];
    const r = buildSection(cands, PATTERNS.vcp);
    expect(r.rows.map((x) => x.code)).toEqual(["A", "B", "C"]);
    expect(r.counts).toEqual({ breakout: 1, actionable: 1, watch: 1 });
    expect(r.rows[0].tier).toBe("breakout");
  });

  it("파워플레이: flag_length_days>0 이 structureOk", () => {
    const cands: RawCandidate[] = [
      { code: "P", name: "p", market: "KOSDAQ", current_price: 1, rs: 88, status: "forming", pivot_price: 100, pct_to_pivot: 6, pattern_detected: false, flag_length_days: 8 },
      { code: "Q-hidden", name: "q", market: "KOSDAQ", current_price: 1, rs: 88, status: "forming", pivot_price: 100, pct_to_pivot: 6, pattern_detected: false, flag_length_days: 0 },
    ];
    const r = buildSection(cands, PATTERNS.powerplayTrend);
    expect(r.rows.map((x) => x.code)).toEqual(["P"]);
  });
});
```

- [ ] **Step 4: 실패 확인**

Run: `cd /c/Users/hanul/playground/my-stock && npm run test`
Expected: FAIL — `Cannot find module './sepaPatterns'` (또는 export 없음).

- [ ] **Step 5: `sepaPatterns.ts` 구현**

Create `src/app/stocks/sepa/sepaPatterns.ts`:

```ts
// SEPA 패턴 대시보드 순수 로직: 티어 분류·정렬·섹션 빌드·패턴 레지스트리.
// 프레임워크 비의존(서버/클라이언트 양쪽에서 import 가능, vitest로 단위 테스트).

export const WATCH_PCT = 12;

export type Tier = "breakout" | "actionable" | "watch";
export type PatternStatus = "breakout" | "actionable" | "forming" | "failed";

export interface RawCandidate {
  code: string;
  name: string;
  market: string;
  current_price: number;
  rs: number | null;
  status?: string;
  pivot_price?: number | null;
  pct_to_pivot?: number | null;
  [k: string]: unknown;
}

export interface ClassifiedRow {
  code: string;
  name: string;
  market: string;
  current_price: number;
  rs: number | null;
  status: string;
  pivot_price: number | null;
  pct_to_pivot: number | null;
  tier: Tier;
  raw: RawCandidate;
}

export interface PatternColumn {
  key: string;
  label: string;
  kind: "pct" | "price" | "int" | "ratio" | "days" | "tight";
}

export interface PatternConfig {
  id: string;
  label: string;
  file: string;
  detectField: string;
  structureOk: (raw: RawCandidate) => boolean;
  columns: PatternColumn[];
}

export interface SectionResult {
  rows: ClassifiedRow[];
  counts: { breakout: number; actionable: number; watch: number };
}

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

// 티어 분류. 입력은 정규화된 원시값(detected·structureOk 는 호출자가 패턴별로 계산해 전달).
export function classify(
  c: { detected: boolean; status: string; pivot_price: number | null; pct_to_pivot: number | null; structureOk: boolean },
  watchPct: number = WATCH_PCT
): Tier | null {
  if (c.detected && c.status === "breakout") return "breakout";
  if (c.detected && c.status === "actionable") return "actionable";
  if (c.detected && c.status === "forming") return "watch";
  const nearPivot =
    c.pivot_price != null &&
    c.pct_to_pivot != null &&
    c.pct_to_pivot >= 0 &&
    c.pct_to_pivot <= watchPct;
  if (c.status !== "failed" && nearPivot && c.structureOk) return "watch";
  return null;
}

const TIER_ORDER: Record<Tier, number> = { breakout: 0, actionable: 1, watch: 2 };

// 정렬: 티어(🔴→🟢→🟡) → abs(pct_to_pivot) 오름차순 → rs 내림차순. in-place.
export function sortRows(rows: ClassifiedRow[]): void {
  rows.sort((a, b) => {
    const t = TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
    if (t !== 0) return t;
    const ap = a.pct_to_pivot == null ? Infinity : Math.abs(a.pct_to_pivot);
    const bp = b.pct_to_pivot == null ? Infinity : Math.abs(b.pct_to_pivot);
    if (ap !== bp) return ap - bp;
    return (b.rs ?? -1) - (a.rs ?? -1);
  });
}

export function buildSection(
  candidates: RawCandidate[] | null | undefined,
  config: PatternConfig,
  watchPct: number = WATCH_PCT
): SectionResult {
  const rows: ClassifiedRow[] = [];
  for (const raw of candidates ?? []) {
    const detected = Boolean(raw[config.detectField]);
    const structureOk = config.structureOk(raw);
    const pivot_price = num(raw.pivot_price);
    const pct_to_pivot = num(raw.pct_to_pivot);
    const status = String(raw.status ?? "");
    const tier = classify({ detected, status, pivot_price, pct_to_pivot, structureOk }, watchPct);
    if (!tier) continue;
    rows.push({
      code: raw.code,
      name: raw.name,
      market: raw.market,
      current_price: raw.current_price,
      rs: raw.rs ?? null,
      status,
      pivot_price,
      pct_to_pivot,
      tier,
      raw,
    });
  }
  sortRows(rows);
  return {
    rows,
    counts: {
      breakout: rows.filter((r) => r.tier === "breakout").length,
      actionable: rows.filter((r) => r.tier === "actionable").length,
      watch: rows.filter((r) => r.tier === "watch").length,
    },
  };
}

// ── 포맷터 ──────────────────────────────────────────────
export function fmtPct(n: number | null, digits = 1): string {
  if (n === null || n === undefined) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

export function fmtPrice(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString();
}

export function fmtCell(value: unknown, kind: PatternColumn["kind"]): string {
  const n = num(value);
  switch (kind) {
    case "price":
      return fmtPrice(n);
    case "pct":
    case "tight":
      return fmtPct(n, 1);
    case "ratio":
      return n === null ? "—" : n.toFixed(2);
    case "int":
      return n === null ? "—" : String(Math.round(n));
    case "days":
      return n === null ? "—" : `${Math.round(n)}일`;
  }
}

// ── 패턴 레지스트리 ─────────────────────────────────────
const VCP_COLUMNS: PatternColumn[] = [
  { key: "num_contractions", label: "수축", kind: "int" },
  { key: "base_depth_pct", label: "베이스깊이", kind: "pct" },
  { key: "coil_len", label: "코일길이", kind: "int" },
  { key: "coil_dry_mean", label: "코일마름", kind: "ratio" },
  { key: "tightness_pct", label: "타이트", kind: "tight" },
];

const POWERPLAY_COLUMNS: PatternColumn[] = [
  { key: "flagpole_gain_pct", label: "깃대상승", kind: "pct" },
  { key: "flagpole_days", label: "깃대일수", kind: "days" },
  { key: "flag_depth_pct", label: "깃발깊이", kind: "pct" },
  { key: "tightness_pct", label: "타이트", kind: "tight" },
];

export const PATTERNS = {
  vcp: {
    id: "vcp",
    label: "VCP (변동성 수축)",
    file: "sepa-vcp-candidates.json",
    detectField: "vcp_detected",
    structureOk: (raw) => num(raw.num_contractions) !== null && (num(raw.num_contractions) as number) >= 2,
    columns: VCP_COLUMNS,
  },
  powerplayTrend: {
    id: "powerplay-trend",
    label: "파워 플레이 — 트렌드 통과 종목 중",
    file: "sepa-power-play-candidates.json",
    detectField: "pattern_detected",
    structureOk: (raw) => num(raw.flag_length_days) !== null && (num(raw.flag_length_days) as number) > 0,
    columns: POWERPLAY_COLUMNS,
  },
  powerplayAll: {
    id: "powerplay-all",
    label: "파워 플레이 — 전체 종목 중",
    file: "sepa-power-play-all-candidates.json",
    detectField: "pattern_detected",
    structureOk: (raw) => num(raw.flag_length_days) !== null && (num(raw.flag_length_days) as number) > 0,
    columns: POWERPLAY_COLUMNS,
  },
  threeC: {
    id: "3c",
    label: "3C (Cup Completion Cheat)",
    file: "sepa-3c-candidates.json",
    detectField: "pattern_detected",
    structureOk: (raw) => num(raw.pivot_price) !== null,
    columns: [{ key: "tightness_pct", label: "타이트", kind: "tight" }],
  },
} satisfies Record<string, PatternConfig>;
```

- [ ] **Step 6: 통과 확인**

Run: `cd /c/Users/hanul/playground/my-stock && npm run test`
Expected: 전부 PASS(classify·sortRows·buildSection 그룹 모두 green).

- [ ] **Step 7: 타입·린트 확인**

Run: `cd /c/Users/hanul/playground/my-stock && npx tsc --noEmit && npx eslint src/app/stocks/sepa/sepaPatterns.ts`
Expected: 에러 없음.

- [ ] **Step 8: 커밋**

```bash
git add package.json package-lock.json vitest.config.ts src/app/stocks/sepa/sepaPatterns.ts src/app/stocks/sepa/sepaPatterns.test.ts
git commit -m "feat(sepa): 티어 분류 순수 모듈 + vitest 도입"
```

---

### Task 2: 클라이언트 정렬 테이블 `SepaPatternTable.tsx`

ClassifiedRow 배열 + 패턴 컬럼 설정을 받아 티어 그룹·정렬·렌더하는 표현 컴포넌트. 로직(분류·정렬)은 Task 1에서 끝났으므로 이 컴포넌트는 "덤(dumb) 렌더러" — 시각/타입/빌드로 검증(단위 테스트 없음; jsdom 미도입).

**Files:**
- Create: `src/app/stocks/sepa/SepaPatternTable.tsx`

**Interfaces:**
- Consumes (Task 1): `ClassifiedRow`, `PatternColumn`, `fmtPct`, `fmtPrice`, `fmtCell`, `Tier`.
- Produces (Task 3): `export function SepaPatternTable({ rows, columns }: { rows: ClassifiedRow[]; columns: PatternColumn[] }): JSX.Element`.

- [ ] **Step 1: 컴포넌트 구현**

Create `src/app/stocks/sepa/SepaPatternTable.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import {
  type ClassifiedRow,
  type PatternColumn,
  type Tier,
  fmtPct,
  fmtPrice,
  fmtCell,
} from "./sepaPatterns";

const TIER_META: Record<Tier, { label: string; color: string; bg: string; dot: string }> = {
  breakout: { label: "돌파", color: "#ffb4ab", bg: "rgba(255,180,171,0.15)", dot: "🔴" },
  actionable: { label: "진입임박", color: "#34d399", bg: "rgba(52,211,153,0.15)", dot: "🟢" },
  watch: { label: "예의주시", color: "#e9c176", bg: "rgba(233,193,118,0.15)", dot: "🟡" },
};

const TIER_ORDER: Record<Tier, number> = { breakout: 0, actionable: 1, watch: 2 };

function rsColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= 90) return "#10b981";
  if (n >= 80) return "#34d399";
  if (n >= 70) return "#e9c176";
  return "#ffb4ab";
}

// 피벗 대비: 0 에 가까울수록 진입 적기. 음수(이미 위)·양수(아래) 모두 |값| 작을수록 좋음.
function pivotColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  const a = Math.abs(n);
  if (a <= 3) return "#10b981";
  if (a <= 8) return "#34d399";
  if (a <= 12) return "#e9c176";
  return "#a8b5d0";
}

type SortKey = "tier" | "rs" | "pivot" | "from_pivot";

interface Props {
  rows: ClassifiedRow[];
  columns: PatternColumn[];
}

export function SepaPatternTable({ rows, columns }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("tier");
  const [sortDesc, setSortDesc] = useState(false);

  const sorted = useMemo(() => {
    const out = [...rows];
    out.sort((a, b) => {
      const get = (r: ClassifiedRow): number => {
        switch (sortKey) {
          case "tier":
            return TIER_ORDER[r.tier];
          case "rs":
            return r.rs ?? -1;
          case "pivot":
            return r.pivot_price ?? -1;
          case "from_pivot":
            return r.pct_to_pivot == null ? Infinity : Math.abs(r.pct_to_pivot);
        }
      };
      const av = get(a);
      const bv = get(b);
      const primary = sortDesc ? bv - av : av - bv;
      if (primary !== 0) return primary;
      // 보조: 티어 → 피벗 근접 → RS
      if (TIER_ORDER[a.tier] !== TIER_ORDER[b.tier]) return TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
      const ap = a.pct_to_pivot == null ? Infinity : Math.abs(a.pct_to_pivot);
      const bp = b.pct_to_pivot == null ? Infinity : Math.abs(b.pct_to_pivot);
      if (ap !== bp) return ap - bp;
      return (b.rs ?? -1) - (a.rs ?? -1);
    });
    return out;
  }, [rows, sortKey, sortDesc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc(!sortDesc);
    else {
      setSortKey(key);
      setSortDesc(key === "rs" || key === "pivot"); // RS·피벗은 큰 값 먼저, 티어·피벗거리는 작은 값 먼저
    }
  };

  const SortHeader = ({ k, label }: { k: SortKey; label: string }) => (
    <th
      onClick={() => toggleSort(k)}
      className="px-2 py-2 cursor-pointer hover:bg-surface-container-high transition-colors text-right text-[11px] font-medium text-on-surface-variant/80"
    >
      <span className="inline-flex items-center gap-0.5 justify-end">
        {label}
        {sortKey === k && (
          <span className="material-symbols-outlined text-[14px] leading-none">
            {sortDesc ? "arrow_drop_down" : "arrow_drop_up"}
          </span>
        )}
      </span>
    </th>
  );

  if (rows.length === 0) {
    return (
      <p className="text-center text-on-surface-variant/60 py-6 text-sm">
        현재 해당 종목 없음.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto bg-surface-container-low rounded-xl ghost-border">
      <table className="w-full text-xs">
        <thead className="bg-surface-container/40">
          <tr>
            <th className="px-2 py-2 text-left text-[11px] font-medium text-on-surface-variant/80 sticky left-0 bg-surface-container/40">
              종목
            </th>
            <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">시장</th>
            <SortHeader k="tier" label="상태" />
            <SortHeader k="rs" label="RS" />
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">현재가</th>
            <SortHeader k="pivot" label="피벗" />
            <SortHeader k="from_pivot" label="피벗대비" />
            {columns.map((c) => (
              <th key={c.key} className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const meta = TIER_META[r.tier];
            return (
              <tr key={r.code} className="border-t border-outline-variant/10 hover:bg-surface-container-high/50 transition-colors">
                <td className="px-2 py-2 sticky left-0 bg-surface-container-low">
                  <div className="flex flex-col">
                    <span className="text-on-surface font-medium leading-tight">{r.name}</span>
                    <span className="text-[10px] text-on-surface-variant/50 font-mono">{r.code}</span>
                  </div>
                </td>
                <td className="px-2 py-2 text-center">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${r.market === "KOSPI" ? "bg-blue-500/15 text-blue-300" : "bg-purple-500/15 text-purple-300"}`}>
                    {r.market}
                  </span>
                </td>
                <td className="px-2 py-2 text-center">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ backgroundColor: meta.bg, color: meta.color }}>
                    {meta.dot} {meta.label}
                  </span>
                </td>
                <td className="px-2 py-2 text-right font-bold" style={{ color: rsColor(r.rs) }}>
                  {r.rs ?? "—"}
                </td>
                <td className="px-2 py-2 text-right text-on-surface-variant">{fmtPrice(r.current_price)}</td>
                <td className="px-2 py-2 text-right text-on-surface-variant">{fmtPrice(r.pivot_price)}</td>
                <td className="px-2 py-2 text-right" style={{ color: pivotColor(r.pct_to_pivot) }}>
                  {fmtPct(r.pct_to_pivot, 1)}
                </td>
                {columns.map((c) => (
                  <td key={c.key} className="px-2 py-2 text-right text-on-surface-variant">
                    {fmtCell(r.raw[c.key], c.kind)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: 타입·린트 확인**

Run: `cd /c/Users/hanul/playground/my-stock && npx tsc --noEmit && npx eslint src/app/stocks/sepa/SepaPatternTable.tsx`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
git add src/app/stocks/sepa/SepaPatternTable.tsx
git commit -m "feat(sepa): 패턴 컬럼 설정 구동 정렬 테이블 컴포넌트"
```

---

### Task 3: 페이지 `page.tsx` + StocksTabs 탭

서버 컴포넌트가 SEPA 파일들을 읽어 패턴별 섹션을 렌더하고, StocksTabs에 진입 탭을 추가한다. 페이지가 실제로 도달·렌더되는 것이 이 태스크의 완성물.

**Files:**
- Create: `src/app/stocks/sepa/page.tsx`
- Modify: `src/app/stocks/StocksTabs.tsx` (`tabs` 배열에 1개 추가)

**Interfaces:**
- Consumes (Task 1·2): `PATTERNS`, `buildSection`, `type SectionResult`, `SepaPatternTable`.
- Produces: 기본 export `SepaPage` (async 서버 컴포넌트).

- [ ] **Step 1: 페이지 구현**

Create `src/app/stocks/sepa/page.tsx`:

```tsx
import fs from "fs/promises";
import path from "path";
import { SepaPatternTable } from "./SepaPatternTable";
import { PATTERNS, buildSection, type PatternConfig, type RawCandidate } from "./sepaPatterns";

interface MarketStatus {
  passed: boolean;
  value: string;
  detail: string;
}
interface TrendData {
  asof: string;
  evaluated_count: number;
  all_pass_count: number;
  market_status: MarketStatus;
}
interface CandidateFile {
  asof?: string;
  candidates?: RawCandidate[];
}

async function readJson<T>(filename: string): Promise<T | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", filename);
    return JSON.parse(await fs.readFile(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

function PatternSection({
  config,
  data,
}: {
  config: PatternConfig;
  data: CandidateFile | null;
}) {
  if (!data) {
    return (
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">pattern</span>
          {config.label}
        </h3>
        <p className="text-sm text-on-surface-variant/60 bg-surface-container-low rounded-xl ghost-border p-4">
          데이터가 아직 생성되지 않았습니다. (산출 파일 <code className="text-xs">{config.file}</code> 없음)
        </p>
      </section>
    );
  }
  const { rows, counts } = buildSection(data.candidates ?? [], config);
  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">pattern</span>
        {config.label}
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">
          🔴 {counts.breakout} · 🟢 {counts.actionable} · 🟡 {counts.watch}
        </span>
      </h3>
      <SepaPatternTable rows={rows} columns={config.columns} />
    </section>
  );
}

export default async function SepaPage() {
  const [trend, vcp, ppTrend, ppAll, threeC] = await Promise.all([
    readJson<TrendData>("sepa-trend-candidates.json"),
    readJson<CandidateFile>(PATTERNS.vcp.file),
    readJson<CandidateFile>(PATTERNS.powerplayTrend.file),
    readJson<CandidateFile>(PATTERNS.powerplayAll.file),
    readJson<CandidateFile>(PATTERNS.threeC.file),
  ]);

  if (!trend) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">SEPA 셋업</h2>
          <p className="text-sm text-on-surface-variant mt-2">
            데이터가 아직 생성되지 않았습니다. <code className="text-xs">find-trend-template</code> 스킬을 먼저 돌려주세요.
          </p>
        </header>
      </div>
    );
  }

  const asofs = Array.from(
    new Set([trend.asof, vcp?.asof, ppTrend?.asof, ppAll?.asof, threeC?.asof].filter(Boolean))
  );

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">SEPA 셋업</h2>
        <p className="text-base text-on-surface-variant mt-2">
          미너비니 SEPA — 트렌드 템플릿 1단계 통과 종목에 대해 VCP·파워 플레이 등 패턴의 돌파·진입임박·예의주시를 한눈에.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          기준일: {asofs.join(" · ")} · 트렌드 통과 {trend.all_pass_count.toLocaleString()}종목 / 평가{" "}
          {trend.evaluated_count.toLocaleString()}
        </p>
      </header>

      {/* 1단계 트렌드 요약 + KOSPI 추세 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">filter_1</span>
          1단계 트렌드 템플릿 통과 — {trend.all_pass_count.toLocaleString()}종목
          <span
            className="text-[11px] font-medium px-2 py-0.5 rounded ml-1"
            style={{
              backgroundColor: trend.market_status.passed ? "rgba(16,185,129,0.18)" : "rgba(255,180,171,0.18)",
              color: trend.market_status.passed ? "#10b981" : "#ffb4ab",
            }}
          >
            KOSPI {trend.market_status.value}
          </span>
        </h3>
        <p className="text-[11px] text-on-surface-variant/70 leading-relaxed">{trend.market_status.detail}</p>
      </section>

      <PatternSection config={PATTERNS.vcp} data={vcp} />
      <PatternSection config={PATTERNS.powerplayTrend} data={ppTrend} />
      <PatternSection config={PATTERNS.powerplayAll} data={ppAll} />
      <PatternSection config={PATTERNS.threeC} data={threeC} />

      {/* 용어·배지 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 text-xs space-y-2">
        <h3 className="text-sm font-serif font-bold text-on-surface flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-base text-primary">help_outline</span>
          상태·지표
        </h3>
        <p className="text-on-surface-variant">
          <strong style={{ color: "#ffb4ab" }}>🔴 돌파</strong>: 패턴 확정 + 당일 피벗 첫돌파 ·{" "}
          <strong style={{ color: "#34d399" }}>🟢 진입임박</strong>: 패턴 확정 + 피벗 근접·거래량 마름 ·{" "}
          <strong style={{ color: "#e9c176" }}>🟡 예의주시</strong>: 베이스 형성 중 + 피벗 12% 이내(곧 만족 가능).
        </p>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">피벗</strong>: 최소저항선(돌파 기준가). <strong className="text-on-surface">피벗대비</strong>: (피벗−현재가)/피벗 — 0에 가까울수록 진입 적기.
        </p>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">VCP</strong>: 수축 횟수·베이스 깊이·코일 길이/마름(거래량/50일선)·타이트. <strong className="text-on-surface">파워 플레이</strong>: 깃대 상승률·일수·깃발 깊이.
        </p>
        <p className="text-on-surface-variant/60 mt-1 pt-2 border-t border-outline-variant/15">
          각 섹션은 그 패턴을 만족(돌파·진입임박)하거나 곧 만족할(예의주시) 종목만 노출하며, 실패·원거리 종목은 숨깁니다. 데이터는 읽기 전용(별도 파이프라인이 생성).
        </p>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: StocksTabs에 탭 추가**

Modify `src/app/stocks/StocksTabs.tsx` — `tabs` 배열 끝(`etf-finder` 다음)에 한 줄 추가:

```tsx
  { href: "/stocks/etf-finder", label: "ETF 파인더", icon: "donut_small" },
  { href: "/stocks/sepa", label: "SEPA 셋업", icon: "candlestick_chart" },
];
```

- [ ] **Step 3: 빌드·린트 확인**

Run: `cd /c/Users/hanul/playground/my-stock && npx tsc --noEmit && npx eslint src/app/stocks/sepa/page.tsx src/app/stocks/StocksTabs.tsx && npm run build`
Expected: 타입·린트 에러 없음, `next build` 성공(`/stocks/sepa` 라우트가 빌드 산출에 포함).

- [ ] **Step 4: 수동 시각 확인**

Run: `cd /c/Users/hanul/playground/my-stock && npm run dev` 후 브라우저로 `http://localhost:3000/stocks/sepa` 접속.
Expected: 헤더(기준일·트렌드 통과 수) + 1단계 요약 + VCP 섹션(🔴/🟢/🟡 분포·정렬 표) + 파워플레이(트렌드) 섹션 + 파워플레이(전수)·3C "데이터 없음" 자리표시 + 용어 섹션. 상단 탭에 "SEPA 셋업" 노출·활성 표시. 표 머리글 클릭 시 정렬 동작. (섹션 카운트가 해당 JSON의 분포와 합리적으로 일치하는지 눈으로 대조.)

- [ ] **Step 5: 커밋**

```bash
git add src/app/stocks/sepa/page.tsx src/app/stocks/StocksTabs.tsx
git commit -m "feat(sepa): /stocks/sepa 페이지 + StocksTabs 진입 탭"
```

---

## Self-Review

**Spec coverage:**
- §2 범위·구조·확장형 → Task 1 레지스트리(PATTERNS) + Task 3 섹션 렌더 ✓
- §3 티어 규칙·정렬·structureOk·WATCH_PCT → Task 1 `classify`/`sortRows`/`PATTERNS` + 테스트 ✓
- §4 데이터 소스(4파일 + 트렌드) → Task 3 `readJson` 5개 + 파일명은 레지스트리 ✓
- §5 구성요소(page/sepaPatterns/SepaPatternTable + StocksTabs/package.json/vitest.config/test) → Task 1·2·3 모두 ✓
- §6 레이아웃(헤더·트렌드요약·섹션·용어) → Task 3 ✓
- §7 에러 처리(트렌드 없음=전체 안내, 패턴 없음=자리표시, 0건=문구, null 피벗=숨김, asof 병기) → Task 3 `PatternSection`/`readJson`/asofs + Task 2 빈 표 문구 ✓
- §8 vitest(분류기 단위 테스트, 12% 경계·정렬·structureOk) → Task 1 Step 1-3 ✓
- §9 StocksTabs 탭 → Task 3 Step 2 ✓
- §10 안 하는 것(데이터 생성·공유파일 수정 없음) → 전 태스크 읽기 전용 ✓
- §11 성공 기준(렌더·자리표시·탭·테스트·빌드) → Task 3 Step 3-4 + Task 1 ✓

**Placeholder scan:** 코드 스텝 모두 완전한 코드. "데이터가 아직 생성되지 않았습니다"는 UI 카피(트렌드 페이지 동일 문구)이지 플레이스홀더 아님. Task 2/3는 단위 테스트 대신 tsc/eslint/build/수동확인 — 프로젝트에 jsdom 없고 표현 컴포넌트라 명시적 의도(플레이스홀더 아님).

**Type consistency:** `classify`는 정규화 원시값 객체를 받고(반환 `Tier|null`), `buildSection`이 raw→정규화 매핑 후 호출 — 일관. `ClassifiedRow`/`PatternColumn`/`PatternConfig`/`SectionResult`가 Task 1 정의·Task 2 소비(`rows`,`columns`)·Task 3 소비(`buildSection`,`PATTERNS`,`config.columns`)에서 동일 철자. `PATTERNS` 키(vcp/powerplayTrend/powerplayAll/threeC)가 Task 3 import와 일치. `fmtCell(value, kind)`/`fmtPct`/`fmtPrice` 시그니처가 Task 1 정의·Task 2 사용 일치.

**Note:** Task 2·3는 TDD 단위 테스트가 없다(프로젝트에 React 테스트 환경 부재, 스펙 §8이 "분류기만 테스트, 페이지는 시각 확인"으로 명시). 모든 비자명 로직은 Task 1의 테스트된 순수 모듈에 모았고, 컴포넌트는 덤 렌더러로 유지해 tsc/eslint/build로 검증한다.
