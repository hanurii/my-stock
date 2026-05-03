// ── 타입 (스크립트와 일치) ──

export interface MegacapMetrics {
  marketCap: number | null;
  trailingPE: number | null;
  forwardPE: number | null;
  fiftyTwoWeekHigh: number | null;
  fiftyTwoWeekLow: number | null;
  dividendYield: number | null;
  payoutRatio: number | null;
  priceToBook: number | null;
  enterpriseToEbitda: number | null;
  trailingEps: number | null;
  forwardEps: number | null;
  returnOnEquity: number | null;
  operatingMargins: number | null;
  profitMargins: number | null;
  freeCashflow: number | null;
  operatingCashflow: number | null;
  debtToEquity: number | null;
  earningsGrowth: number | null;
  revenueGrowth: number | null;
  regularMarketPrice: number | null;
  longName: string | null;
}

export interface MegacapPriceHistory {
  high_5y: number;
  low_5y: number;
  avg_5y: number;
  pct_from_high: number;
  percentile_5y: number;
}

export interface MegacapPillarScores {
  quality: number;
  moat: number;
  capital: number;
  valuation: number;
  total: number;
}

export interface MegacapBuySignal {
  triggers_met: number;
  pe_below_avg: boolean;
  drawdown_20: boolean;
  fcf_yield_high: boolean;
  label: "강한 매수" | "매수 검토" | "관찰" | null;
}

export type MegacapMarket = "US" | "KR" | "JP" | "CN" | "EU" | "OTHER";
export type MegacapCurrency = "USD" | "KRW" | "JPY" | "CNY" | "HKD" | "EUR" | "TWD" | "INR" | "GBP";

export interface MegacapShareholderReturn {
  buybacks_ttm: number;
  dividends_ttm: number;
  total_return_ttm: number;
  yield_pct: number;
  asOfDate: string | null;
}

export interface MegacapStock {
  ticker: string;
  name: string;
  name_kr: string;
  market: MegacapMarket;
  currency: MegacapCurrency;
  sector: string | null;
  metrics: MegacapMetrics;
  price_history: MegacapPriceHistory | null;
  shareholder_return: MegacapShareholderReturn | null;
  scores: MegacapPillarScores;
  signal: MegacapBuySignal;
  is_buffett_candidate: boolean;
}

export interface MegacapMonitorData {
  generated_at: string;
  total_universe_candidates: number;
  total_selected: number;
  market_breakdown: Record<string, number>;
  buffett_candidates_count: number;
  signal_count: number;
  errors: string[];
  stocks: MegacapStock[];
}

export interface MegacapFXRate {
  currency: string;
  symbol: string;
  label: string;
  current: number;
  avg_5y: number;
  std_5y: number;
  z_score: number;
  fx_score: number;
  fx_label: string;
  pct_from_avg: number;
  history_points: number;
}

export interface MegacapFXData {
  generated_at: string;
  rates: MegacapFXRate[];
}

// ── 통화 → 시장 매핑 (combined_score 계산용) ──

export function currencyToFXScore(
  currency: MegacapCurrency,
  fxData: MegacapFXData | null,
): number {
  if (!fxData) return 0;
  if (currency === "KRW") return 0; // 한국 종목은 환율 무관
  const rate = fxData.rates.find((r) => r.currency === currency);
  return rate?.fx_score ?? 0;
}

export function combinedScore(stock: MegacapStock, fxData: MegacapFXData | null): number {
  const fx = currencyToFXScore(stock.currency, fxData);
  return stock.scores.total + fx;
}

// ── 포맷터 ──

export function formatMarketCap(amount: number | null, currency: MegacapCurrency): string {
  if (amount == null) return "—";
  const symbol = currencyDisplay(currency);
  if (currency === "KRW" || currency === "JPY") {
    if (amount >= 1e12) return `${symbol}${(amount / 1e12).toFixed(1)}조`;
    if (amount >= 1e8) return `${symbol}${(amount / 1e8).toFixed(0)}억`;
    return `${symbol}${amount.toLocaleString()}`;
  }
  if (amount >= 1e12) return `${symbol}${(amount / 1e12).toFixed(2)}T`;
  if (amount >= 1e9) return `${symbol}${(amount / 1e9).toFixed(1)}B`;
  if (amount >= 1e6) return `${symbol}${(amount / 1e6).toFixed(0)}M`;
  return `${symbol}${amount.toLocaleString()}`;
}

export function currencyDisplay(currency: MegacapCurrency): string {
  return {
    USD: "$",
    KRW: "₩",
    JPY: "¥",
    CNY: "¥",
    HKD: "HK$",
    EUR: "€",
    TWD: "NT$",
    INR: "₹",
    GBP: "£",
  }[currency];
}

export function marketLabel(market: MegacapMarket): string {
  return {
    US: "🇺🇸 미국",
    KR: "🇰🇷 한국",
    JP: "🇯🇵 일본",
    CN: "🇨🇳 중국",
    EU: "🇪🇺 유럽",
    OTHER: "🌎 기타",
  }[market];
}

export function formatPercent(value: number | null, digits: number = 1): string {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
}
