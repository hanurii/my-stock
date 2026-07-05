# 미너비니 정산표(Trading Scorecard) 구현 계획 — C단계

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 미너비니 원칙 거래만 담는 체결 장부에서 왕복거래를 자동 집계해, 평균수익·평균손실·승률·손익비·기대수익·보유일수(월별 확인표 + 트레이딩 요약 2뷰)를 계산하는 순수 TS 모듈과 CLI를 만든다.

**Architecture:** 순수 계산 모듈 `src/lib/scorecard.ts`(체결→왕복거래 매칭 + 지표 계산)를 만들고, CLI `scripts/build-scorecard.ts`가 이를 호출해 터미널 출력 + `public/data/scorecard.json` 저장. A단계 페이지가 나중에 같은 모듈을 재사용(로직 1벌).

**Tech Stack:** TypeScript(ESM), vitest(단위 테스트), `npx tsx`(CLI 실행, 레포 관례), Node 24.

**근거 스펙:** `docs/superpowers/specs/2026-07-05-scorecard-design.md`

## Global Constraints

- 언어: **TypeScript ESM**. 모듈은 `import`/`export` 사용(레포 `src/lib/*.ts`·`scripts/*.ts` 관례).
- 테스트: **vitest**, 파일은 `src/**/*.test.ts` 여야 감지됨(`vitest.config.ts` include). 실행 `npx vitest run <파일>`.
- 스크립트 실행: **`npx tsx scripts/<name>.ts`** (레포 CI 관례). tsx는 미설치이나 npx가 받아옴. 오프라인이라 실패하면 먼저 `npm i -D tsx`.
- 모든 % 지표는 **순수익(net)·총수익(gross) 두 기준** 모두 계산. avg_loss·max_loss.pct는 **양수 크기**로 저장.
- 승/패 분류: 지표를 계산하는 **해당 기준의 수익률 > 0 이면 win, ≤ 0 이면 loss**(본전 0은 loss).
- 반올림: 퍼센트·비율은 **소수 2자리**(`round2`), 보유일수는 **정수**(`Math.round`). 값이 없으면 `null`(표시층에서 `-`).
- 기존 `journal.json`(173건)·`sepa-holdings.json`은 읽거나 수정하지 않는다(전략 혼합 금지). 단 Task 5의 시드 데이터로 현재 보유 4종목의 매수 체결만 참조 복사.
- 날짜: `date`는 `"YYYY-MM-DD [HH:MM:SS]"`. 월 귀속·보유일수는 앞 10자(YYYY-MM-DD)만 사용.

---

## 파일 구조

- Create: `src/lib/scorecard.ts` — 타입 + `matchTrades` + `computeOverall` + `computeMonthly` + `computeScorecard`(순수 함수, 파일·화면 모름)
- Create: `src/lib/scorecard.test.ts` — 단위 테스트(vitest). 각 Task가 describe 블록 추가
- Create: `scripts/build-scorecard.ts` — CLI(파일 IO + 터미널 출력)
- Create: `public/data/scorecard-fills.json` — 입력 장부(시드)
- Generate: `public/data/scorecard.json` — 산출물(CLI가 씀)
- Modify: `package.json` — `"scorecard"` 스크립트 추가

---

## Task 1: 타입 + `matchTrades` (체결 → 왕복거래 매칭)

**Files:**
- Create: `src/lib/scorecard.ts`
- Test: `src/lib/scorecard.test.ts`

**Interfaces:**
- Consumes: 없음(최초 태스크)
- Produces:
  - 타입 `Fill`, `Trade`, `OpenPosition`, `MatchResult`
  - `export function matchTrades(fills: Fill[]): MatchResult`
  - 내부 헬퍼 `round2`, `mean`, `daysBetween`, `dateOnly`(같은 파일에서 이후 태스크가 재사용)

- [ ] **Step 1: 실패하는 테스트 작성**

`src/lib/scorecard.test.ts` 생성:

```ts
import { describe, it, expect } from "vitest";
import { matchTrades, type Fill } from "./scorecard";

const buy = (date: string, code: string, price: number, qty: number, extra: Partial<Fill> = {}): Fill =>
  ({ date, code, name: code, side: "buy", price, qty, ...extra });
const sell = (date: string, code: string, price: number, qty: number, extra: Partial<Fill> = {}): Fill =>
  ({ date, code, name: code, side: "sell", price, qty, ...extra });

describe("matchTrades", () => {
  it("단순 왕복: 매수1 매도1 → 1거래, 수익률·보유일수·win", () => {
    const { trades, open, errors } = matchTrades([
      buy("2026-01-05", "A", 100, 100),
      sell("2026-01-08", "A", 110, 100),
    ]);
    expect(errors).toEqual([]);
    expect(open).toEqual([]);
    expect(trades).toHaveLength(1);
    const t = trades[0];
    expect(t.avg_buy).toBe(100);
    expect(t.avg_sell).toBe(110);
    expect(t.gross_pct).toBe(10);
    expect(t.net_pct).toBe(10);
    expect(t.hold_days).toBe(3);
    expect(t.outcome).toBe("win");
    expect(t.month).toBe("2026-01");
    expect(t.buy_qty).toBe(100);
    expect(t.sell_qty).toBe(100);
  });

  it("수수료·세금: 순수익률이 총수익률보다 낮다", () => {
    const { trades } = matchTrades([
      buy("2026-01-05", "A", 100, 100, { fees: 100 }),
      sell("2026-01-08", "A", 110, 100, { fees: 100, tax: 200 }),
    ]);
    expect(trades[0].gross_pct).toBe(10);
    expect(trades[0].net_pct).toBe(5.94); // (10700/10100-1)*100
  });

  it("분할 매수(피라미딩): 가중평균 매수가", () => {
    const { trades } = matchTrades([
      buy("2026-01-05", "A", 100, 100),
      buy("2026-01-06", "A", 120, 100),
      sell("2026-01-10", "A", 130, 200),
    ]);
    expect(trades).toHaveLength(1);
    expect(trades[0].avg_buy).toBe(110);
    expect(trades[0].gross_pct).toBe(18.18);
    expect(trades[0].buy_qty).toBe(200);
  });

  it("분할 익절: 가중평균 매도가·마지막 매도일 기준 보유일수", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 200),
      sell("2026-01-05", "A", 120, 100),
      sell("2026-01-11", "A", 140, 100),
    ]);
    expect(trades).toHaveLength(1);
    expect(trades[0].avg_sell).toBe(130);
    expect(trades[0].gross_pct).toBe(30);
    expect(trades[0].close_date).toBe("2026-01-11");
    expect(trades[0].hold_days).toBe(10);
    expect(trades[0].sell_qty).toBe(200);
  });

  it("재진입 분리: 청산 후 재매수 → 2개 독립 거래", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 100),
      sell("2026-01-02", "A", 110, 100),
      buy("2026-01-05", "A", 200, 100),
      sell("2026-01-06", "A", 180, 100),
    ]);
    expect(trades).toHaveLength(2);
    expect(trades[0].outcome).toBe("win");
    expect(trades[1].outcome).toBe("loss");
    expect(trades[1].gross_pct).toBe(-10);
  });

  it("미청산: 매수만 있으면 open에만, 통계 제외", () => {
    const { trades, open } = matchTrades([buy("2026-01-01", "A", 100, 100)]);
    expect(trades).toEqual([]);
    expect(open).toHaveLength(1);
    expect(open[0]).toMatchObject({ code: "A", qty: 100, avg_buy: 100, open_date: "2026-01-01" });
  });

  it("엣지: 보유수량 초과 매도 → errors, 해당 종목 제외", () => {
    const { trades, errors } = matchTrades([
      buy("2026-01-01", "A", 100, 100),
      sell("2026-01-02", "A", 110, 150),
    ]);
    expect(trades).toEqual([]);
    expect(errors.length).toBe(1);
    expect(errors[0]).toContain("A");
  });

  it("손절 규율: 계획 손절폭 초과 손실 → stop_violation true", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 100, { stop: 95 }), // 계획 -5%
      sell("2026-01-02", "A", 90, 100),               // 실제 -10%
    ]);
    expect(trades[0].outcome).toBe("loss");
    expect(trades[0].stop_violation).toBe(true);
  });

  it("손절 규율: 손절가 있어도 수익이면 위반 아님", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 100, { stop: 95 }),
      sell("2026-01-02", "A", 110, 100),
    ]);
    expect(trades[0].stop_violation).toBe(false);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: FAIL — `Failed to resolve import "./scorecard"` 또는 `matchTrades is not a function`

- [ ] **Step 3: 최소 구현 작성**

`src/lib/scorecard.ts` 생성:

```ts
// 미너비니 정산표 — 순수 계산 모듈 (파일·화면 모름)

export type Fill = {
  date: string; code: string; name: string;
  side: "buy" | "sell";
  price: number; qty: number;
  fees?: number; tax?: number;
  stop?: number; setup?: string; note?: string;
};

export type Trade = {
  code: string; name: string;
  open_date: string; close_date: string;
  avg_buy: number; avg_sell: number;
  gross_pct: number; net_pct: number;
  hold_days: number;
  outcome: "win" | "loss";
  month: string; // YYYY-MM (청산월)
  buy_qty: number; sell_qty: number;
  stop?: number; stop_violation?: boolean; setup?: string;
};

export type OpenPosition = { code: string; name: string; qty: number; avg_buy: number; open_date: string };
export type MatchResult = { trades: Trade[]; open: OpenPosition[]; errors: string[] };

// ---- 헬퍼 (이후 태스크 재사용) ----
export function round2(x: number): number { return Math.round(x * 100) / 100; }
export function mean(xs: number[]): number { return xs.reduce((s, v) => s + v, 0) / xs.length; }
export function dateOnly(s: string): string { return s.slice(0, 10); }
export function daysBetween(a: string, b: string): number {
  const da = Date.parse(a + "T00:00:00Z");
  const db = Date.parse(b + "T00:00:00Z");
  return Math.round((db - da) / 86_400_000);
}
const sum = <T,>(xs: T[], f: (x: T) => number) => xs.reduce((s, x) => s + f(x), 0);

function buildTrade(code: string, name: string, buys: Fill[], sells: Fill[], openDate: string, closeDate: string): Trade {
  const buyVal = sum(buys, (b) => b.price * b.qty);
  const buyQty = sum(buys, (b) => b.qty);
  const sellVal = sum(sells, (s) => s.price * s.qty);
  const sellQty = sum(sells, (s) => s.qty);
  const avgBuy = buyVal / buyQty;
  const avgSell = sellVal / sellQty;
  const grossPct = (avgSell / avgBuy - 1) * 100;

  const buyFees = sum(buys, (b) => b.fees ?? 0);
  const sellCosts = sum(sells, (s) => (s.fees ?? 0) + (s.tax ?? 0));
  const netCost = buyVal + buyFees;
  const netProceeds = sellVal - sellCosts;
  const netPct = (netProceeds / netCost - 1) * 100;

  const outcome: "win" | "loss" = netPct > 0 ? "win" : "loss";
  const firstStop = buys[0]?.stop;
  let stopViolation: boolean | undefined;
  if (firstStop != null) {
    const plannedPct = (firstStop / avgBuy - 1) * 100;
    stopViolation = outcome === "loss" && netPct < plannedPct - 1e-9;
  }

  return {
    code, name,
    open_date: openDate, close_date: closeDate,
    avg_buy: round2(avgBuy), avg_sell: round2(avgSell),
    gross_pct: round2(grossPct), net_pct: round2(netPct),
    hold_days: daysBetween(openDate, closeDate),
    outcome, month: closeDate.slice(0, 7),
    buy_qty: buyQty, sell_qty: sellQty,
    stop: firstStop, stop_violation: stopViolation, setup: buys[0]?.setup,
  };
}

export function matchTrades(fills: Fill[]): MatchResult {
  const errors: string[] = [];
  const trades: Trade[] = [];
  const open: OpenPosition[] = [];

  const byCode = new Map<string, { f: Fill; i: number }[]>();
  fills.forEach((f, i) => {
    if (!byCode.has(f.code)) byCode.set(f.code, []);
    byCode.get(f.code)!.push({ f, i });
  });

  for (const [code, list] of byCode) {
    const sorted = [...list].sort((a, b) =>
      a.f.date < b.f.date ? -1 : a.f.date > b.f.date ? 1 : a.i - b.i
    );
    let qty = 0;
    let buys: Fill[] = [];
    let sells: Fill[] = [];
    let firstBuyDate = "";
    let bad = false;

    for (const { f } of sorted) {
      if (f.side === "buy") {
        if (qty === 0) { buys = []; sells = []; firstBuyDate = dateOnly(f.date); }
        buys.push(f); qty += f.qty;
      } else {
        sells.push(f); qty -= f.qty;
        if (qty < 0) { errors.push(`${code}: 매도 수량이 보유수량 초과 (${f.date})`); bad = true; break; }
        if (qty === 0) {
          trades.push(buildTrade(code, f.name, buys, sells, firstBuyDate, dateOnly(f.date)));
          buys = []; sells = [];
        }
      }
    }
    if (bad) continue;
    if (qty > 0) {
      const buyVal = sum(buys, (b) => b.price * b.qty);
      const buyQty = sum(buys, (b) => b.qty);
      open.push({
        code, name: buys[buys.length - 1]?.name ?? code,
        qty, avg_buy: round2(buyVal / buyQty), open_date: firstBuyDate,
      });
    }
  }
  return { trades, open, errors };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: PASS (matchTrades describe 9건 모두 통과)

- [ ] **Step 5: 커밋**

```bash
git add src/lib/scorecard.ts src/lib/scorecard.test.ts
git commit -m "feat(scorecard): matchTrades — 체결→왕복거래 매칭(분할·재진입·미청산·손절규율)"
```

---

## Task 2: `computeOverall` (전체 풀링 요약 지표)

**Files:**
- Modify: `src/lib/scorecard.ts` (append)
- Test: `src/lib/scorecard.test.ts` (append)

**Interfaces:**
- Consumes: `Trade`, `round2`, `mean` (Task 1)
- Produces:
  - 타입 `MaxTrade`, `OverallStats`
  - `export function computeOverall(trades: Trade[], basis: "net" | "gross"): OverallStats`
  - `OverallStats`: `{ win_rate, avg_win, avg_loss, payoff_ratio, adj_payoff_ratio, expectancy, max_win, max_loss, win_days, loss_days }` 는 값 없으면 `null`; `trade_count, win_count, loss_count`는 숫자.
  - `MaxTrade`: `{ pct: number; code: string; name: string; date: string } | null` (pct는 양수 크기)

- [ ] **Step 1: 실패하는 테스트 작성**

`src/lib/scorecard.test.ts` 에 append:

```ts
import { computeOverall, type Trade } from "./scorecard";

// 지표 테스트용 최소 Trade 생성기 (basis별 pct와 보유일수만 의미 있음)
function mkTrade(net: number, days: number, month: string, code = "X"): Trade {
  return {
    code, name: code, open_date: `${month}-01`, close_date: `${month}-05`,
    avg_buy: 100, avg_sell: 100 * (1 + net / 100),
    gross_pct: net, net_pct: net, hold_days: days,
    outcome: net > 0 ? "win" : "loss", month,
    buy_qty: 1, sell_qty: 1,
  };
}

describe("computeOverall", () => {
  it("승률·평균수익·평균손실·손익비·조정후·기대수익·유지일수", () => {
    const trades = [
      mkTrade(10, 5, "2026-01"),
      mkTrade(20, 10, "2026-01"),
      mkTrade(-5, 8, "2026-01"),
    ];
    const o = computeOverall(trades, "net");
    expect(o.trade_count).toBe(3);
    expect(o.win_count).toBe(2);
    expect(o.loss_count).toBe(1);
    expect(o.win_rate).toBe(66.67);
    expect(o.avg_win).toBe(15);
    expect(o.avg_loss).toBe(5); // 양수 크기
    expect(o.payoff_ratio).toBe(3); // 15/5
    expect(o.adj_payoff_ratio).toBe(6); // (15*2/3)/(5*1/3)
    expect(o.expectancy).toBe(8.33); // 2/3*15 - 1/3*5
    expect(o.max_win?.pct).toBe(20);
    expect(o.max_loss?.pct).toBe(5);
    expect(o.win_days).toBe(8); // round((5+10)/2)=8
    expect(o.loss_days).toBe(8);
  });

  it("거래 0건 → 모든 지표 null, 카운트 0", () => {
    const o = computeOverall([], "net");
    expect(o).toMatchObject({ win_rate: null, avg_win: null, avg_loss: null, payoff_ratio: null, trade_count: 0 });
  });

  it("수익거래만 있으면 avg_loss·payoff null, 손실거래만 있으면 avg_win·payoff null", () => {
    expect(computeOverall([mkTrade(10, 3, "2026-01")], "net").payoff_ratio).toBe(null);
    expect(computeOverall([mkTrade(-10, 3, "2026-01")], "net").payoff_ratio).toBe(null);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: FAIL — `computeOverall is not a function`

- [ ] **Step 3: 최소 구현 작성**

`src/lib/scorecard.ts` 에 append:

```ts
export type MaxTrade = { pct: number; code: string; name: string; date: string } | null;
export type OverallStats = {
  win_rate: number | null; avg_win: number | null; avg_loss: number | null;
  payoff_ratio: number | null; adj_payoff_ratio: number | null; expectancy: number | null;
  max_win: MaxTrade; max_loss: MaxTrade;
  win_days: number | null; loss_days: number | null;
  trade_count: number; win_count: number; loss_count: number;
};

export function computeOverall(trades: Trade[], basis: "net" | "gross"): OverallStats {
  const pct = (t: Trade) => (basis === "net" ? t.net_pct : t.gross_pct);
  const n = trades.length;
  const empty: OverallStats = {
    win_rate: null, avg_win: null, avg_loss: null, payoff_ratio: null,
    adj_payoff_ratio: null, expectancy: null, max_win: null, max_loss: null,
    win_days: null, loss_days: null, trade_count: 0, win_count: 0, loss_count: 0,
  };
  if (n === 0) return empty;

  const wins = trades.filter((t) => pct(t) > 0);
  const losses = trades.filter((t) => pct(t) <= 0);
  const winRate = wins.length / n;
  const lossRate = losses.length / n;

  const avgWin = wins.length ? mean(wins.map(pct)) : null;
  const avgLoss = losses.length ? mean(losses.map((t) => -pct(t))) : null; // 양수
  const payoff = avgWin != null && avgLoss != null && avgLoss !== 0 ? avgWin / avgLoss : null;
  const adj = payoff != null && lossRate > 0 ? (avgWin! * winRate) / (avgLoss! * lossRate) : null;
  const expectancy = winRate * (avgWin ?? 0) - lossRate * (avgLoss ?? 0);

  const toMax = (arr: Trade[], mag: (t: Trade) => number): MaxTrade => {
    if (!arr.length) return null;
    const best = arr.reduce((a, b) => (mag(b) > mag(a) ? b : a));
    return { pct: round2(mag(best)), code: best.code, name: best.name, date: best.close_date };
  };

  return {
    win_rate: round2(winRate * 100),
    avg_win: avgWin != null ? round2(avgWin) : null,
    avg_loss: avgLoss != null ? round2(avgLoss) : null,
    payoff_ratio: payoff != null ? round2(payoff) : null,
    adj_payoff_ratio: adj != null ? round2(adj) : null,
    expectancy: wins.length || losses.length ? round2(expectancy) : null,
    max_win: toMax(wins, pct),
    max_loss: toMax(losses, (t) => -pct(t)),
    win_days: wins.length ? Math.round(mean(wins.map((t) => t.hold_days))) : null,
    loss_days: losses.length ? Math.round(mean(losses.map((t) => t.hold_days))) : null,
    trade_count: n, win_count: wins.length, loss_count: losses.length,
  };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: PASS (matchTrades + computeOverall 모두 통과)

- [ ] **Step 5: 커밋**

```bash
git add src/lib/scorecard.ts src/lib/scorecard.test.ts
git commit -m "feat(scorecard): computeOverall — 전체 풀링 요약(승률·손익비·조정후·기대수익)"
```

---

## Task 3: `computeMonthly` (월별 확인표 + 평균 행)

**Files:**
- Modify: `src/lib/scorecard.ts` (append)
- Test: `src/lib/scorecard.test.ts` (append)

**Interfaces:**
- Consumes: `Trade`, `round2`, `mean` (Task 1)
- Produces:
  - 타입 `MonthlyRow`, `MonthlyTable`
  - `export function computeMonthly(trades: Trade[], basis: "net" | "gross"): MonthlyTable`
  - `MonthlyRow`: `{ month, avg_win, avg_loss, win_rate, trades, max_win, max_loss, win_days, loss_days }`
  - `MonthlyTable`: `{ rows: MonthlyRow[]; average: MonthlyRow }` — average.month = `"평균"`, trades = 합계, 나머지 = 값 있는 달의 평균(퍼센트 2자리, 일수 정수). 값 없으면 `null`.

- [ ] **Step 1: 실패하는 테스트 작성**

`src/lib/scorecard.test.ts` 에 append:

```ts
import { computeMonthly } from "./scorecard";

describe("computeMonthly", () => {
  it("월별 행 + 평균행(월평균, 총거래=합계), 수익거래 0인 달은 null", () => {
    const trades = [
      mkTrade(10, 3, "2026-01", "A"),
      mkTrade(-4, 10, "2026-01", "B"),
      mkTrade(-5, 8, "2026-02", "C"), // 2월엔 수익거래 없음
    ];
    const m = computeMonthly(trades, "net");
    expect(m.rows).toHaveLength(2);

    const jan = m.rows[0];
    expect(jan.month).toBe("2026-01");
    expect(jan.avg_win).toBe(10);
    expect(jan.avg_loss).toBe(4);
    expect(jan.win_rate).toBe(50);
    expect(jan.trades).toBe(2);
    expect(jan.max_win).toBe(10);
    expect(jan.max_loss).toBe(4);
    expect(jan.win_days).toBe(3);
    expect(jan.loss_days).toBe(10);

    const feb = m.rows[1];
    expect(feb.avg_win).toBe(null);
    expect(feb.avg_loss).toBe(5);
    expect(feb.win_rate).toBe(0);
    expect(feb.max_win).toBe(null);
    expect(feb.win_days).toBe(null);
    expect(feb.loss_days).toBe(8);

    const avg = m.average;
    expect(avg.month).toBe("평균");
    expect(avg.trades).toBe(3); // 합계
    expect(avg.avg_win).toBe(10); // null 달 제외 → [10] 평균
    expect(avg.avg_loss).toBe(4.5); // [4,5] 평균
    expect(avg.win_rate).toBe(25); // [50,0] 평균
    expect(avg.max_loss).toBe(4.5);
    expect(avg.win_days).toBe(3); // [3] 평균
    expect(avg.loss_days).toBe(9); // [10,8] 평균
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: FAIL — `computeMonthly is not a function`

- [ ] **Step 3: 최소 구현 작성**

`src/lib/scorecard.ts` 에 append:

```ts
export type MonthlyRow = {
  month: string;
  avg_win: number | null; avg_loss: number | null; win_rate: number | null;
  trades: number;
  max_win: number | null; max_loss: number | null;
  win_days: number | null; loss_days: number | null;
};
export type MonthlyTable = { rows: MonthlyRow[]; average: MonthlyRow };

export function computeMonthly(trades: Trade[], basis: "net" | "gross"): MonthlyTable {
  const pct = (t: Trade) => (basis === "net" ? t.net_pct : t.gross_pct);
  const months = [...new Set(trades.map((t) => t.month))].sort();

  const rows: MonthlyRow[] = months.map((month) => {
    const mt = trades.filter((t) => t.month === month);
    const wins = mt.filter((t) => pct(t) > 0);
    const losses = mt.filter((t) => pct(t) <= 0);
    return {
      month,
      avg_win: wins.length ? round2(mean(wins.map(pct))) : null,
      avg_loss: losses.length ? round2(mean(losses.map((t) => -pct(t)))) : null,
      win_rate: round2((wins.length / mt.length) * 100),
      trades: mt.length,
      max_win: wins.length ? round2(Math.max(...wins.map(pct))) : null,
      max_loss: losses.length ? round2(Math.max(...losses.map((t) => -pct(t)))) : null,
      win_days: wins.length ? Math.round(mean(wins.map((t) => t.hold_days))) : null,
      loss_days: losses.length ? Math.round(mean(losses.map((t) => t.hold_days))) : null,
    };
  });

  const avgPct = (key: keyof MonthlyRow): number | null => {
    const vals = rows.map((r) => r[key]).filter((v): v is number => v != null);
    return vals.length ? round2(mean(vals)) : null;
  };
  const avgInt = (key: keyof MonthlyRow): number | null => {
    const vals = rows.map((r) => r[key]).filter((v): v is number => v != null);
    return vals.length ? Math.round(mean(vals)) : null;
  };

  const average: MonthlyRow = {
    month: "평균",
    avg_win: avgPct("avg_win"), avg_loss: avgPct("avg_loss"), win_rate: avgPct("win_rate"),
    trades: rows.reduce((s, r) => s + r.trades, 0),
    max_win: avgPct("max_win"), max_loss: avgPct("max_loss"),
    win_days: avgInt("win_days"), loss_days: avgInt("loss_days"),
  };
  return { rows, average };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/lib/scorecard.ts src/lib/scorecard.test.ts
git commit -m "feat(scorecard): computeMonthly — 월별 확인표(하단 평균행·- 처리)"
```

---

## Task 4: `computeScorecard` (조립 + RBA 권장손절 + 고집불통 진단)

**Files:**
- Modify: `src/lib/scorecard.ts` (append)
- Test: `src/lib/scorecard.test.ts` (append)

**Interfaces:**
- Consumes: `matchTrades`, `computeOverall`, `computeMonthly`, `round2` (Task 1~3), 타입 `Fill`, `Trade`, `OpenPosition`, `OverallStats`, `MonthlyTable`
- Produces:
  - 타입 `Scorecard`, `ScorecardParams`
  - `export function computeScorecard(fills: Fill[], params: ScorecardParams): Scorecard`
  - `ScorecardParams`: `{ rr_target: number; stop_loss_pct_default: number; generated_at: string; strategy: string }`

- [ ] **Step 1: 실패하는 테스트 작성**

`src/lib/scorecard.test.ts` 에 append:

```ts
import { computeScorecard } from "./scorecard";

describe("computeScorecard", () => {
  const params = { rr_target: 2, stop_loss_pct_default: -4, generated_at: "2026-07-05", strategy: "minervini" };

  it("net/gross 2뷰·open_positions·RBA·진단을 조립", () => {
    const sc = computeScorecard([
      buy("2026-01-01", "A", 100, 100, { stop: 90 }),
      sell("2026-01-10", "A", 130, 100), // 승 +30, 9일
      buy("2026-02-01", "B", 100, 100, { stop: 95 }), // 계획 -5%
      sell("2026-02-05", "B", 90, 100),  // 손 -10%, 위반, 4일
      buy("2026-03-01", "C", 100, 100),  // 미청산
    ], params);

    expect(sc.overall.net.trade_count).toBe(2);
    expect(sc.overall.gross.trade_count).toBe(2);
    expect(sc.monthly.net.rows).toHaveLength(2);
    expect(sc.open_positions).toHaveLength(1);
    expect(sc.open_positions[0].code).toBe("C");

    // RBA: 평균수익 30 → 권장 15, 기본 손절 4% < 15 → ok
    expect(sc.rba.avg_win_net).toBe(30);
    expect(sc.rba.recommended_max_stop_pct).toBe(15);
    expect(sc.rba.current_default_stop_pct).toBe(4);
    expect(sc.rba.status).toBe("ok");

    // 진단: 손절 위반 1건
    expect(sc.diagnostics.stop_violations).toBe(1);
    expect(sc.diagnostics.warnings.some((w) => w.includes("손절 규율 위반"))).toBe(true);

    expect(sc.generated_at).toBe("2026-07-05");
    expect(sc.strategy).toBe("minervini");
  });

  it("거래 0건이면 RBA status unknown", () => {
    const sc = computeScorecard([buy("2026-03-01", "C", 100, 100)], params);
    expect(sc.overall.net.trade_count).toBe(0);
    expect(sc.rba.status).toBe("unknown");
    expect(sc.rba.recommended_max_stop_pct).toBe(null);
  });

  it("기본 손절이 권장보다 넓으면 too_wide 경고", () => {
    // 평균수익 6 → 권장 3, 기본 손절 4 > 3 → too_wide
    const sc = computeScorecard([
      buy("2026-01-01", "A", 100, 100),
      sell("2026-01-05", "A", 106, 100),
    ], params);
    expect(sc.rba.status).toBe("too_wide");
    expect(sc.diagnostics.warnings.some((w) => w.includes("권장"))).toBe(true);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: FAIL — `computeScorecard is not a function`

- [ ] **Step 3: 최소 구현 작성**

`src/lib/scorecard.ts` 에 append:

```ts
export type ScorecardParams = {
  rr_target: number; stop_loss_pct_default: number;
  generated_at: string; strategy: string;
};

export type Scorecard = {
  generated_at: string; strategy: string;
  params: { rr_target: number; stop_loss_pct_default: number };
  trades: Trade[]; open_positions: OpenPosition[];
  monthly: { net: MonthlyTable; gross: MonthlyTable };
  overall: { net: OverallStats; gross: OverallStats };
  rba: {
    avg_win_net: number | null; recommended_max_stop_pct: number | null;
    current_default_stop_pct: number; status: "ok" | "too_wide" | "unknown";
  };
  diagnostics: {
    max_loss_gt_max_win: boolean; loss_days_ge_win_days: boolean;
    stop_violations: number; warnings: string[];
  };
  errors: string[];
};

export function computeScorecard(fills: Fill[], params: ScorecardParams): Scorecard {
  const { trades, open, errors } = matchTrades(fills);
  const overall = { net: computeOverall(trades, "net"), gross: computeOverall(trades, "gross") };
  const monthly = { net: computeMonthly(trades, "net"), gross: computeMonthly(trades, "gross") };

  const avgWinNet = overall.net.avg_win;
  const rec = avgWinNet != null ? round2(avgWinNet / params.rr_target) : null;
  const curStop = Math.abs(params.stop_loss_pct_default);
  const status: "ok" | "too_wide" | "unknown" =
    avgWinNet == null ? "unknown" : rec != null && curStop > rec ? "too_wide" : "ok";
  const rba = { avg_win_net: avgWinNet, recommended_max_stop_pct: rec, current_default_stop_pct: curStop, status };

  const warnings: string[] = [];
  const mw = overall.net.max_win, ml = overall.net.max_loss;
  const maxLossGtWin = !!(mw && ml && ml.pct > mw.pct);
  if (maxLossGtWin) warnings.push("최대손실이 최대수익보다 큽니다 — 손실은 붙들고 이익은 일찍 파는 신호");
  const wd = overall.net.win_days, ld = overall.net.loss_days;
  const lossDaysGe = wd != null && ld != null && ld >= wd;
  if (lossDaysGe) warnings.push("손실 유지일이 수익 유지일보다 깁니다 — 손실을 오래 붙들고 있습니다");
  const stopViolations = trades.filter((t) => t.stop_violation).length;
  if (stopViolations > 0) warnings.push(`손절 규율 위반 ${stopViolations}건`);
  if (status === "too_wide") warnings.push(`기본 손절 ${curStop}%가 권장 ${rec}%보다 넓습니다`);

  return {
    generated_at: params.generated_at, strategy: params.strategy,
    params: { rr_target: params.rr_target, stop_loss_pct_default: params.stop_loss_pct_default },
    trades, open_positions: open, monthly, overall, rba,
    diagnostics: { max_loss_gt_max_win: maxLossGtWin, loss_days_ge_win_days: lossDaysGe, stop_violations: stopViolations, warnings },
    errors,
  };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/lib/scorecard.test.ts`
Expected: PASS (전체 describe 통과)

- [ ] **Step 5: 커밋**

```bash
git add src/lib/scorecard.ts src/lib/scorecard.test.ts
git commit -m "feat(scorecard): computeScorecard — 조립·RBA 권장손절·고집불통 진단"
```

---

## Task 5: CLI + 입력 장부 시드 + npm 스크립트

**Files:**
- Create: `public/data/scorecard-fills.json`
- Create: `scripts/build-scorecard.ts`
- Modify: `package.json` (scripts에 `"scorecard"` 추가)
- Generate: `public/data/scorecard.json` (실행 산출물)

**Interfaces:**
- Consumes: `computeScorecard`, 타입 `Fill` (Task 1~4)
- Produces: 실행형 CLI. 단위 테스트 대신 스모크 실행으로 검증.

- [ ] **Step 1: 입력 장부 시드 작성**

`public/data/scorecard-fills.json` 생성. 현재 미너비니 보유 4종목의 **매수 체결만** 시드(청산 전이므로 모두 미청산 → 파이프라인이 "청산된 거래 0건 + 열린 포지션 4"를 잘 처리하는지 확인). 값은 `sepa-holdings.json` 기준.

```json
{
  "strategy": "minervini",
  "rr_target": 2,
  "stop_loss_pct_default": -4,
  "fills": [
    { "date": "2026-07-01 09:31:32", "code": "036800", "name": "나이스정보통신", "side": "buy", "price": 29700, "qty": 435, "stop": 28512, "setup": "VCP" },
    { "date": "2026-07-02 09:07:53", "code": "271560", "name": "오리온", "side": "buy", "price": 138500, "qty": 72, "stop": 132960 },
    { "date": "2026-07-03 09:06:02", "code": "010955", "name": "S-Oil우", "side": "buy", "price": 57900, "qty": 172, "stop": 55584 },
    { "date": "2026-07-03 14:15:54", "code": "005430", "name": "한국공항", "side": "buy", "price": 87500, "qty": 114, "stop": 84000 }
  ]
}
```

- [ ] **Step 2: CLI 작성**

`scripts/build-scorecard.ts` 생성:

```ts
/**
 * 미너비니 정산표 CLI (C단계)
 * public/data/scorecard-fills.json 읽기 → computeScorecard → 터미널 출력 + scorecard.json 저장
 * 실행: npx tsx scripts/build-scorecard.ts
 */
import fs from "fs";
import path from "path";
import { computeScorecard, type Fill } from "../src/lib/scorecard";

const DATA = path.join(process.cwd(), "public", "data");
const IN = path.join(DATA, "scorecard-fills.json");
const OUT = path.join(DATA, "scorecard.json");

const pct = (v: number | null) => (v == null ? "-" : `${v.toFixed(2)}%`);
const num = (v: number | null) => (v == null ? "-" : String(v));

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function main() {
  const raw = JSON.parse(fs.readFileSync(IN, "utf-8"));
  const fills: Fill[] = raw.fills ?? [];
  const sc = computeScorecard(fills, {
    rr_target: raw.rr_target ?? 2,
    stop_loss_pct_default: raw.stop_loss_pct_default ?? -4,
    generated_at: today(),
    strategy: raw.strategy ?? "minervini",
  });

  fs.writeFileSync(OUT, JSON.stringify(sc, null, 2), "utf-8");

  const o = sc.overall.net;
  console.log("\n===== 트레이딩 요약 (순수익 기준, 전체) =====");
  if (o.trade_count === 0) {
    console.log("아직 청산된 거래가 없습니다. (열린 포지션 " + sc.open_positions.length + "건)");
  } else {
    console.log(`거래수 ${o.trade_count}  승 ${o.win_count}  패 ${o.loss_count}`);
    console.log(`승률 ${pct(o.win_rate)}  평균수익 ${pct(o.avg_win)}  평균손실 ${pct(o.avg_loss)}`);
    console.log(`성공/실패 비율 ${num(o.payoff_ratio)}  조정후 ${num(o.adj_payoff_ratio)}  기대수익 ${pct(o.expectancy)}`);
    console.log(`수익유지일 ${num(o.win_days)}  손실유지일 ${num(o.loss_days)}`);
    console.log(`\nRBA 권장 최대 손절폭: ${pct(sc.rba.recommended_max_stop_pct)} (현재 기본 ${sc.rba.current_default_stop_pct}%, ${sc.rba.status})`);

    console.log("\n----- 월별 확인표 (순수익) -----");
    console.log("월\t평균수익\t평균손실\t승률\t거래\t최대수익\t최대손실\t수익일\t손실일");
    for (const r of sc.monthly.net.rows) {
      console.log(`${r.month}\t${pct(r.avg_win)}\t${pct(r.avg_loss)}\t${pct(r.win_rate)}\t${r.trades}\t${pct(r.max_win)}\t${pct(r.max_loss)}\t${num(r.win_days)}\t${num(r.loss_days)}`);
    }
    const a = sc.monthly.net.average;
    console.log(`평균\t${pct(a.avg_win)}\t${pct(a.avg_loss)}\t${pct(a.win_rate)}\t${a.trades}\t${pct(a.max_win)}\t${pct(a.max_loss)}\t${num(a.win_days)}\t${num(a.loss_days)}`);
  }

  if (sc.diagnostics.warnings.length) {
    console.log("\n⚠️ 진단:");
    for (const w of sc.diagnostics.warnings) console.log("  - " + w);
  }
  if (sc.errors.length) {
    console.log("\n❗ 데이터 오류:");
    for (const e of sc.errors) console.log("  - " + e);
  }
  console.log(`\n저장됨: ${OUT}`);
}

main();
```

- [ ] **Step 3: package.json 스크립트 추가**

`package.json` 의 `"scripts"` 에 한 줄 추가(기존 `"test"` 아래):

```json
    "test": "vitest run",
    "scorecard": "tsx scripts/build-scorecard.ts"
```

- [ ] **Step 4: 스모크 실행 (시드 = 미청산 4건)**

Run: `npx tsx scripts/build-scorecard.ts`
Expected: 오류 없이 실행. 출력에 "아직 청산된 거래가 없습니다. (열린 포지션 4건)". `public/data/scorecard.json` 생성됨.

검증(생성 파일 구조 확인):

Run: `node -e "const s=require('./public/data/scorecard.json'); console.log(s.open_positions.length, s.overall.net.trade_count, s.strategy)"`
Expected: `4 0 minervini`

- [ ] **Step 5: 청산 거래 포함 재검증(수동, 임시)**

임시로 `scorecard-fills.json` 에 매도 체결 한 줄을 추가해 왕복거래가 집계되는지 확인 후 **되돌린다**(시드는 미청산 4건 유지). 예: 036800 매도 추가 →

Run: `npx tsx scripts/build-scorecard.ts`
Expected: "트레이딩 요약"에 거래수 1, 승/패·승률·평균수익 출력, 월별표 1행. 확인 후 추가한 매도 줄 삭제(원복).

- [ ] **Step 6: 커밋**

```bash
git add scripts/build-scorecard.ts public/data/scorecard-fills.json public/data/scorecard.json package.json
git commit -m "feat(scorecard): CLI build-scorecard + 입력장부 시드 + npm 스크립트"
```

---

## Self-Review (작성자 점검 완료)

- **스펙 커버리지**: §3 데이터모델·매칭 → Task 1. §4.3 요약·§4.4 RBA/진단 → Task 2·4. §4.2 월별표 → Task 3. §5 산출 JSON → Task 4·5. §6 구조(모듈/CLI/JSON) → Task 1~5. §7 TDD 12시나리오 → Task 1~4 테스트에 반영(음수수량·미청산·분할·재진입·수수료·-처리·공식·손절위반 포함). §8 검산공식 → Task 2 테스트의 손익비/조정후/기대수익 수치로 못박음.
- **Placeholder 스캔**: "TBD/적절히 처리" 류 없음. 모든 코드 스텝에 실제 코드 포함.
- **타입 일관성**: `Fill`/`Trade`/`OverallStats`/`MonthlyTable`/`Scorecard` 정의(Task 1~4)와 사용처 시그니처 일치. `computeOverall`/`computeMonthly`는 `(trades, basis)`, `computeScorecard`는 `(fills, params)` 로 통일.
- **범위**: A단계(페이지)는 제외 — 별도 스펙/계획. 셋업별 분리·자동손절조정은 YAGNI(스펙 §10).
