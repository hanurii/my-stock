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
  stop?: number | null; stop_violation?: boolean | null; setup?: string | null;
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
    stop: firstStop ?? null, stop_violation: stopViolation ?? null, setup: buys[0]?.setup ?? null,
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
    const codeTrades: Trade[] = [];

    for (const { f } of sorted) {
      if (f.side === "buy") {
        if (qty === 0) { buys = []; sells = []; firstBuyDate = dateOnly(f.date); }
        buys.push(f); qty += f.qty;
      } else {
        sells.push(f); qty -= f.qty;
        if (qty < 0) { errors.push(`${code}: 매도 수량이 보유수량 초과 (${f.date})`); bad = true; break; }
        if (qty === 0) {
          codeTrades.push(buildTrade(code, f.name, buys, sells, firstBuyDate, dateOnly(f.date)));
          buys = []; sells = [];
        }
      }
    }
    if (bad) continue;
    trades.push(...codeTrades);
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
