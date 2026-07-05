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
