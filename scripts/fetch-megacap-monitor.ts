/**
 * 메가캡 우량주 모니터 — 데이터 수집 스크립트
 *
 * Yahoo Finance crumb 인증으로 글로벌 메가캡 100종목의 풀 메트릭 수집.
 * 시장별 시총 상위 자동 선정 후 4-Pillar 스코어카드 산정.
 *
 * 출력: public/data/megacap-monitor.json
 *
 * 사용법: npx tsx scripts/fetch-megacap-monitor.ts
 */
import fs from "fs";
import path from "path";
import { UNIVERSE_CANDIDATES, MARKET_QUOTAS, type UniverseCandidate } from "./megacap-universe";

const ROOT = path.resolve(__dirname, "..");
const OUTPUT_PATH = path.join(ROOT, "public", "data", "megacap-monitor.json");

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
const REQUEST_DELAY_MS = 250;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// ── Crumb 인증 ──

async function getYahooCrumb(): Promise<{ cookie: string; crumb: string } | null> {
  try {
    const fcRes = await fetch("https://fc.yahoo.com", {
      headers: { "User-Agent": UA },
      redirect: "manual",
    });
    const setCookie = fcRes.headers.get("set-cookie");
    if (!setCookie) return null;
    const match = setCookie.match(/A3=[^;]+/);
    if (!match) return null;
    const cookie = match[0];

    const crumbRes = await fetch("https://query1.finance.yahoo.com/v1/test/getcrumb", {
      headers: { "User-Agent": UA, Cookie: cookie },
    });
    if (!crumbRes.ok) return null;
    const crumb = await crumbRes.text();
    if (!crumb || crumb.includes("Unauthorized")) return null;

    return { cookie, crumb };
  } catch (e) {
    console.error("[crumb] auth failed:", e);
    return null;
  }
}

// ── Yahoo 응답 타입 (사용 필드만) ──

interface YahooRaw { raw?: number; fmt?: string }

interface QuoteSummaryResult {
  summaryDetail?: {
    trailingPE?: YahooRaw;
    forwardPE?: YahooRaw;
    marketCap?: YahooRaw;
    fiftyTwoWeekHigh?: YahooRaw;
    fiftyTwoWeekLow?: YahooRaw;
    dividendYield?: YahooRaw;
    payoutRatio?: YahooRaw;
    fiftyDayAverage?: YahooRaw;
    twoHundredDayAverage?: YahooRaw;
  };
  defaultKeyStatistics?: {
    priceToBook?: YahooRaw;
    enterpriseToEbitda?: YahooRaw;
    trailingEps?: YahooRaw;
    forwardEps?: YahooRaw;
  };
  financialData?: {
    returnOnEquity?: YahooRaw;
    operatingMargins?: YahooRaw;
    profitMargins?: YahooRaw;
    freeCashflow?: YahooRaw;
    operatingCashflow?: YahooRaw;
    totalCash?: YahooRaw;
    totalDebt?: YahooRaw;
    debtToEquity?: YahooRaw;
    earningsGrowth?: YahooRaw;
    revenueGrowth?: YahooRaw;
  };
  price?: {
    regularMarketPrice?: YahooRaw;
    currency?: string;
    longName?: string;
    shortName?: string;
  };
}

async function fetchQuoteSummary(
  ticker: string,
  auth: { cookie: string; crumb: string },
): Promise<QuoteSummaryResult | null> {
  const modules = "summaryDetail,defaultKeyStatistics,financialData,price";
  const url = `https://query2.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(ticker)}?modules=${modules}&crumb=${encodeURIComponent(auth.crumb)}`;
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": UA, Cookie: auth.cookie },
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json?.quoteSummary?.result?.[0] ?? null;
  } catch {
    return null;
  }
}

interface PriceHistory {
  prices: number[];          // 월별 종가
  high_5y: number;
  low_5y: number;
  avg_5y: number;
  current: number;
  pct_from_high: number;     // % below 5y high (negative)
  percentile_5y: number;     // 0~100, 5y range 내 위치
}

async function fetchFiveYearPriceHistory(ticker: string): Promise<PriceHistory | null> {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?range=5y&interval=1mo`;
  try {
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;
    const json = await res.json();
    const result = json?.chart?.result?.[0];
    if (!result) return null;
    const closes: (number | null)[] = result.indicators?.quote?.[0]?.close ?? [];
    const prices = closes.filter((c): c is number => c != null && c > 0);
    if (prices.length < 12) return null;
    const high = Math.max(...prices);
    const low = Math.min(...prices);
    const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
    const current = prices[prices.length - 1];
    return {
      prices,
      high_5y: high,
      low_5y: low,
      avg_5y: avg,
      current,
      pct_from_high: ((current - high) / high) * 100,
      percentile_5y: ((current - low) / (high - low)) * 100,
    };
  } catch {
    return null;
  }
}

// ── 주주환원 데이터 (자사주매입 + 배당) ──

interface ShareholderReturn {
  buybacks_ttm: number;     // 최근 회계연도 자사주매입 (절댓값, 통화는 종목 통화)
  dividends_ttm: number;    // 최근 회계연도 배당 지급 (절댓값)
  total_return_ttm: number; // 합산
  asOfDate: string | null;
}

async function fetchShareholderReturn(
  ticker: string,
  auth: { cookie: string; crumb: string },
): Promise<ShareholderReturn | null> {
  const now = Math.floor(Date.now() / 1000);
  const past = now - 90000000; // ~3년 전 (최근 회계연도 데이터 확보 목적)
  const types = "annualRepurchaseOfCapitalStock,annualCashDividendsPaid";
  const url = `https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/${encodeURIComponent(
    ticker,
  )}?type=${types}&period1=${past}&period2=${now}&crumb=${encodeURIComponent(auth.crumb)}`;
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": UA, Cookie: auth.cookie },
    });
    if (!res.ok) return null;
    const json = await res.json();
    const series: Array<{
      meta?: { type?: string[] };
      [key: string]: unknown;
    }> = json?.timeseries?.result ?? [];
    if (!series.length) return null;

    // 가장 최근 데이터 찾기
    const latestOf = (typeName: string): { value: number; asOfDate: string } | null => {
      const block = series.find((s) => s.meta?.type?.[0] === typeName);
      if (!block) return null;
      const arr = (block[typeName] as Array<{ asOfDate?: string; reportedValue?: { raw?: number } }> | undefined) ?? [];
      // asOfDate desc 정렬
      const sorted = [...arr]
        .filter((x) => x.asOfDate && x.reportedValue?.raw != null)
        .sort((a, b) => (a.asOfDate! < b.asOfDate! ? 1 : -1));
      if (!sorted.length) return null;
      return { value: sorted[0].reportedValue!.raw!, asOfDate: sorted[0].asOfDate! };
    };

    const buy = latestOf("annualRepurchaseOfCapitalStock");
    const div = latestOf("annualCashDividendsPaid");

    if (!buy && !div) return null;
    const buybacks = Math.abs(buy?.value ?? 0);
    const dividends = Math.abs(div?.value ?? 0);
    const asOfDate = buy?.asOfDate ?? div?.asOfDate ?? null;

    return {
      buybacks_ttm: buybacks,
      dividends_ttm: dividends,
      total_return_ttm: buybacks + dividends,
      asOfDate,
    };
  } catch {
    return null;
  }
}

// ── 메트릭 추출 헬퍼 ──

function v(x: YahooRaw | undefined): number | null {
  return x?.raw != null && Number.isFinite(x.raw) ? x.raw : null;
}

// ── 4-Pillar 스코어 산정 ──

interface Metrics {
  // raw
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

function extractMetrics(qs: QuoteSummaryResult): Metrics {
  const sd = qs.summaryDetail ?? {};
  const ks = qs.defaultKeyStatistics ?? {};
  const fd = qs.financialData ?? {};
  const pr = qs.price ?? {};
  return {
    marketCap: v(sd.marketCap),
    trailingPE: v(sd.trailingPE),
    forwardPE: v(sd.forwardPE),
    fiftyTwoWeekHigh: v(sd.fiftyTwoWeekHigh),
    fiftyTwoWeekLow: v(sd.fiftyTwoWeekLow),
    dividendYield: v(sd.dividendYield),
    payoutRatio: v(sd.payoutRatio),
    priceToBook: v(ks.priceToBook),
    enterpriseToEbitda: v(ks.enterpriseToEbitda),
    trailingEps: v(ks.trailingEps),
    forwardEps: v(ks.forwardEps),
    returnOnEquity: v(fd.returnOnEquity),
    operatingMargins: v(fd.operatingMargins),
    profitMargins: v(fd.profitMargins),
    freeCashflow: v(fd.freeCashflow),
    operatingCashflow: v(fd.operatingCashflow),
    debtToEquity: v(fd.debtToEquity),
    earningsGrowth: v(fd.earningsGrowth),
    revenueGrowth: v(fd.revenueGrowth),
    regularMarketPrice: v(pr.regularMarketPrice),
    longName: pr.longName ?? pr.shortName ?? null,
  };
}

// 0~max 사이로 클램핑
function clamp(v: number, max: number): number {
  return Math.max(0, Math.min(max, v));
}

// 선형 보간: x ≤ x0 → max, x ≥ x1 → 0 (또는 그 반대)
function linearScore(
  x: number | null,
  thresholds: [number, number, number, number], // x_min(0pt) → x_25 → x_50 → x_max(100pt)
  maxPoints: number,
): number {
  if (x == null) return 0;
  const [xMin, x25, x50, xMax] = thresholds;
  const ascending = xMax > xMin;
  if (ascending) {
    if (x <= xMin) return 0;
    if (x >= xMax) return maxPoints;
    if (x <= x25) return ((x - xMin) / (x25 - xMin)) * 0.25 * maxPoints;
    if (x <= x50) return (0.25 + ((x - x25) / (x50 - x25)) * 0.25) * maxPoints;
    return (0.5 + ((x - x50) / (xMax - x50)) * 0.5) * maxPoints;
  } else {
    // descending
    if (x >= xMin) return 0;
    if (x <= xMax) return maxPoints;
    if (x >= x25) return ((xMin - x) / (xMin - x25)) * 0.25 * maxPoints;
    if (x >= x50) return (0.25 + ((x25 - x) / (x25 - x50)) * 0.25) * maxPoints;
    return (0.5 + ((x50 - x) / (x50 - xMax)) * 0.5) * maxPoints;
  }
}

interface PillarScores {
  quality: number;
  moat: number;
  capital: number;
  valuation: number;
  total: number;
}

function computeScore(m: Metrics, ph: PriceHistory | null, shareholderYieldPct: number | null): PillarScores {
  // ── Quality (40점) ──
  // ROE: 5% 0pt → 10% 25%pt → 15% 50%pt → 20% max (15점)
  const roePct = (m.returnOnEquity ?? 0) * 100;
  const qROE = linearScore(roePct, [5, 10, 15, 20], 15);
  // 영업이익률: 5% 0pt → 10% → 15% → 25% max (10점)
  const opMarginPct = (m.operatingMargins ?? 0) * 100;
  const qOpMargin = linearScore(opMarginPct, [5, 10, 15, 25], 10);
  // 순이익률: 0% 0pt → 5% → 10% → 20% max (10점)
  const profitMarginPct = (m.profitMargins ?? 0) * 100;
  const qProfit = linearScore(profitMarginPct, [0, 5, 10, 20], 10);
  // 부채/자본: 200% 0pt → 100% → 75% → 50%↓ max (5점)  ※ Yahoo는 % 단위
  const dte = m.debtToEquity ?? 200;
  const qDebt = linearScore(dte, [200, 100, 75, 50], 5);
  const quality = qROE + qOpMargin + qProfit + qDebt;

  // ── Moat (20점) ──
  // 영업이익률 절대값 ≥15% → 10점 (해자 증명)
  const moatOpMargin = opMarginPct >= 25 ? 10 : opMarginPct >= 15 ? 7 : opMarginPct >= 10 ? 4 : opMarginPct >= 5 ? 2 : 0;
  // EV/EBITDA < 20 (적정 가격)
  const ev = m.enterpriseToEbitda ?? 50;
  const moatEV = ev <= 10 ? 5 : ev <= 15 ? 3.5 : ev <= 20 ? 2 : ev <= 30 ? 1 : 0;
  // P/B 적정성
  const pb = m.priceToBook ?? 50;
  const moatPB = pb <= 2 ? 5 : pb <= 5 ? 3 : pb <= 10 ? 1.5 : 0;
  const moat = moatOpMargin + moatEV + moatPB;

  // ── Capital (20점) — 자본 운용력 + 주주환원 ──
  // FCF / 시총 비율 (현금 창출력) — 0% 0pt → 3% → 5% → 8% max (7점)
  let fcfYieldPct = 0;
  if (m.freeCashflow != null && m.marketCap != null && m.marketCap > 0) {
    fcfYieldPct = (m.freeCashflow / m.marketCap) * 100;
  }
  const cFCF = linearScore(fcfYieldPct, [0, 3, 5, 8], 7);
  // 총 주주환원율 (배당 + 자사주매입) / 시총 — 단계별 (7점)
  let cShareholder = 0;
  if (shareholderYieldPct != null) {
    if (shareholderYieldPct >= 10) cShareholder = 7;
    else if (shareholderYieldPct >= 6) cShareholder = 5;
    else if (shareholderYieldPct >= 3) cShareholder = 3;
    else if (shareholderYieldPct >= 1) cShareholder = 1;
    else cShareholder = 0;
  }
  // EPS 성장률 (3점)
  const epsGrowthPct = (m.earningsGrowth ?? 0) * 100;
  const cEPS = linearScore(epsGrowthPct, [-10, 0, 8, 20], 3);
  // 매출 성장률 (3점)
  const revGrowthPct = (m.revenueGrowth ?? 0) * 100;
  const cRev = linearScore(revGrowthPct, [-5, 0, 5, 15], 3);
  const capital = cFCF + cShareholder + cEPS + cRev;

  // ── Valuation (20점) ──
  // trailingPE 절대 수준 (10점): 30 0pt → 20 → 15 → 10↓ max (역방향)
  const tpe = m.trailingPE ?? 100;
  let vPE = 0;
  if (tpe > 0 && tpe < 100) {
    if (tpe <= 10) vPE = 10;
    else if (tpe <= 15) vPE = 8;
    else if (tpe <= 20) vPE = 5;
    else if (tpe <= 25) vPE = 3;
    else if (tpe <= 30) vPE = 1.5;
    else vPE = 0;
  }
  // FCF yield (5점) — capital과 별도로 valuation에서도 체크
  const vFCF = fcfYieldPct >= 6 ? 5 : fcfYieldPct >= 4 ? 3.5 : fcfYieldPct >= 2 ? 1.5 : 0;
  // 52주/5년 드로다운 (5점) — 더 큰 하락 = 더 매력적
  let drawdownPct = 0;
  if (m.fiftyTwoWeekHigh != null && m.regularMarketPrice != null && m.fiftyTwoWeekHigh > 0) {
    drawdownPct = -((m.fiftyTwoWeekHigh - m.regularMarketPrice) / m.fiftyTwoWeekHigh) * 100;
  }
  const drawAbs = Math.abs(drawdownPct);
  const vDraw = drawAbs >= 30 ? 5 : drawAbs >= 20 ? 3.5 : drawAbs >= 10 ? 2 : drawAbs >= 5 ? 1 : 0;
  const valuation = vPE + vFCF + vDraw;

  const total = quality + moat + capital + valuation;
  return {
    quality: Math.round(quality * 10) / 10,
    moat: Math.round(moat * 10) / 10,
    capital: Math.round(capital * 10) / 10,
    valuation: Math.round(valuation * 10) / 10,
    total: Math.round(total * 10) / 10,
  };
}

// ── 분할매수 트리거 ──

interface BuySignal {
  triggers_met: number;       // 0~3
  pe_below_avg: boolean;      // forwardPE < trailingPE × 0.85 (실적 개선)
  drawdown_20: boolean;       // 52w 고점 -20% 이상
  fcf_yield_high: boolean;    // FCF yield ≥ 5%
  label: "강한 매수" | "매수 검토" | "관찰" | null;
}

function computeSignal(m: Metrics): BuySignal {
  const tpe = m.trailingPE;
  const fpe = m.forwardPE;
  const pe_below_avg = tpe != null && fpe != null && tpe > 0 && fpe > 0 && fpe < tpe * 0.85;

  let drawdown_20 = false;
  if (m.fiftyTwoWeekHigh != null && m.regularMarketPrice != null && m.fiftyTwoWeekHigh > 0) {
    const dd = ((m.fiftyTwoWeekHigh - m.regularMarketPrice) / m.fiftyTwoWeekHigh) * 100;
    drawdown_20 = dd >= 20;
  }

  let fcf_yield_high = false;
  if (m.freeCashflow != null && m.marketCap != null && m.marketCap > 0) {
    fcf_yield_high = (m.freeCashflow / m.marketCap) * 100 >= 5;
  }

  const count = (pe_below_avg ? 1 : 0) + (drawdown_20 ? 1 : 0) + (fcf_yield_high ? 1 : 0);
  let label: BuySignal["label"] = null;
  if (count >= 3) label = "강한 매수";
  else if (count === 2) label = "매수 검토";
  else if (count === 1) label = "관찰";

  return { triggers_met: count, pe_below_avg, drawdown_20, fcf_yield_high, label };
}

// ── 출력 스키마 ──

interface MegacapStock {
  ticker: string;
  name: string;             // longName
  name_kr: string;
  market: UniverseCandidate["market"];
  currency: UniverseCandidate["currency"];
  sector: string | null;
  metrics: Metrics;
  price_history: {
    high_5y: number;
    low_5y: number;
    avg_5y: number;
    pct_from_high: number;
    percentile_5y: number;
  } | null;
  shareholder_return: {
    buybacks_ttm: number;
    dividends_ttm: number;
    total_return_ttm: number;
    yield_pct: number;            // 시총 대비 % (음수 가능성 없음)
    asOfDate: string | null;
  } | null;
  scores: PillarScores;
  signal: BuySignal;
  is_buffett_candidate: boolean;
}

interface MegacapMonitorOutput {
  generated_at: string;
  total_universe_candidates: number;
  total_selected: number;
  market_breakdown: Record<string, number>;
  buffett_candidates_count: number;
  signal_count: number;
  errors: string[];
  stocks: MegacapStock[];
}

// ── USD 환산 시총 비교용 (1차 시총 정렬) ──
// 가벼운 추정용 환율: 정확한 z-score는 fetch-megacap-fx.ts에서 따로 계산
const ROUGH_USD_RATE: Record<string, number> = {
  USD: 1,
  KRW: 1 / 1480,
  JPY: 1 / 156,
  CNY: 1 / 7.2,
  HKD: 1 / 7.8,
  EUR: 1.08,
  TWD: 1 / 32,
  INR: 1 / 84,
  GBP: 1.27,
};

function marketCapInUSD(marketCap: number | null, currency: UniverseCandidate["currency"]): number {
  if (marketCap == null) return 0;
  const rate = ROUGH_USD_RATE[currency] ?? 1;
  return marketCap * rate;
}

// ── 메인 ──

async function main() {
  console.log("[megacap-monitor] start");
  console.log(`[megacap-monitor] universe candidates: ${UNIVERSE_CANDIDATES.length}`);

  const auth = await getYahooCrumb();
  if (!auth) {
    console.error("[crumb] failed to obtain authentication");
    process.exit(1);
  }
  console.log(`[crumb] obtained: ${auth.crumb.slice(0, 6)}***`);

  // 1단계: 모든 후보의 marketCap 조회 → 시장별 시총 상위 자동 선정
  const errors: string[] = [];
  const allMetrics = new Map<string, { candidate: UniverseCandidate; metrics: Metrics; qs: QuoteSummaryResult }>();

  for (let i = 0; i < UNIVERSE_CANDIDATES.length; i++) {
    const c = UNIVERSE_CANDIDATES[i];
    process.stdout.write(`  [${i + 1}/${UNIVERSE_CANDIDATES.length}] ${c.ticker} ${c.name_kr} `);
    const qs = await fetchQuoteSummary(c.ticker, auth);
    if (!qs) {
      errors.push(`${c.ticker}: quoteSummary fetch failed`);
      console.log("❌");
      await sleep(REQUEST_DELAY_MS);
      continue;
    }
    const m = extractMetrics(qs);
    if (m.marketCap == null) {
      errors.push(`${c.ticker}: marketCap missing`);
      console.log("⚠️ no marketCap");
    } else {
      const usdCap = marketCapInUSD(m.marketCap, c.currency);
      console.log(`${(usdCap / 1e9).toFixed(1)}B USD`);
    }
    allMetrics.set(c.ticker, { candidate: c, metrics: m, qs });
    await sleep(REQUEST_DELAY_MS);
  }

  // 2단계: 시장별 시총 상위 N개 선정
  const byMarket = new Map<UniverseCandidate["market"], Array<{ candidate: UniverseCandidate; metrics: Metrics; qs: QuoteSummaryResult; usdCap: number }>>();
  for (const entry of allMetrics.values()) {
    const usdCap = marketCapInUSD(entry.metrics.marketCap, entry.candidate.currency);
    const list = byMarket.get(entry.candidate.market) ?? [];
    list.push({ ...entry, usdCap });
    byMarket.set(entry.candidate.market, list);
  }

  const selected: typeof allMetrics extends Map<string, infer V> ? V[] : never = [];
  const market_breakdown: Record<string, number> = {};
  for (const [market, quota] of Object.entries(MARKET_QUOTAS) as Array<[UniverseCandidate["market"], number]>) {
    const candidates = (byMarket.get(market) ?? []).sort((a, b) => b.usdCap - a.usdCap).slice(0, quota);
    for (const c of candidates) {
      selected.push({ candidate: c.candidate, metrics: c.metrics, qs: c.qs });
    }
    market_breakdown[market] = candidates.length;
    console.log(`[selection] ${market}: ${candidates.length}/${quota}`);
  }

  console.log(`[selection] total: ${selected.length}`);

  // 3단계: 선정 종목에 대해 5년 가격 시계열 추가
  const stocks: MegacapStock[] = [];
  for (let i = 0; i < selected.length; i++) {
    const sel = selected[i];
    process.stdout.write(`  [${i + 1}/${selected.length}] ${sel.candidate.ticker} `);
    const ph = await fetchFiveYearPriceHistory(sel.candidate.ticker);
    if (!ph) {
      errors.push(`${sel.candidate.ticker}: 5y history failed`);
      process.stdout.write("hist❌ ");
    } else {
      process.stdout.write(`${ph.percentile_5y.toFixed(0)}%ile `);
    }
    await sleep(REQUEST_DELAY_MS);

    const sr = await fetchShareholderReturn(sel.candidate.ticker, auth);
    let yieldPct: number | null = null;
    if (sr && sel.metrics.marketCap != null && sel.metrics.marketCap > 0) {
      yieldPct = (sr.total_return_ttm / sel.metrics.marketCap) * 100;
      console.log(`재매입+배당 ${yieldPct.toFixed(1)}%`);
    } else {
      console.log("재매입+배당❌");
    }
    await sleep(REQUEST_DELAY_MS);

    const scores = computeScore(sel.metrics, ph, yieldPct);
    const signal = computeSignal(sel.metrics);
    const is_buffett_candidate = scores.total >= 70;

    stocks.push({
      ticker: sel.candidate.ticker,
      name: sel.metrics.longName ?? sel.candidate.name_kr,
      name_kr: sel.candidate.name_kr,
      market: sel.candidate.market,
      currency: sel.candidate.currency,
      sector: sel.candidate.sector ?? null,
      metrics: sel.metrics,
      price_history: ph
        ? {
            high_5y: Math.round(ph.high_5y * 100) / 100,
            low_5y: Math.round(ph.low_5y * 100) / 100,
            avg_5y: Math.round(ph.avg_5y * 100) / 100,
            pct_from_high: Math.round(ph.pct_from_high * 10) / 10,
            percentile_5y: Math.round(ph.percentile_5y * 10) / 10,
          }
        : null,
      shareholder_return:
        sr && yieldPct != null
          ? {
              buybacks_ttm: Math.round(sr.buybacks_ttm),
              dividends_ttm: Math.round(sr.dividends_ttm),
              total_return_ttm: Math.round(sr.total_return_ttm),
              yield_pct: Math.round(yieldPct * 100) / 100,
              asOfDate: sr.asOfDate,
            }
          : null,
      scores,
      signal,
      is_buffett_candidate,
    });
  }

  // 4단계: 정렬 (총점 내림차순) 및 출력
  stocks.sort((a, b) => b.scores.total - a.scores.total);

  const buffett_count = stocks.filter((s) => s.is_buffett_candidate).length;
  const signal_count = stocks.filter((s) => s.signal.label === "강한 매수" || s.signal.label === "매수 검토").length;

  const output: MegacapMonitorOutput = {
    generated_at: new Date().toISOString().slice(0, 10),
    total_universe_candidates: UNIVERSE_CANDIDATES.length,
    total_selected: stocks.length,
    market_breakdown,
    buffett_candidates_count: buffett_count,
    signal_count,
    errors,
    stocks,
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2), "utf-8");
  console.log(`\n[done] ${stocks.length}종목 | 버핏 후보 ${buffett_count} | 매수 시그널 ${signal_count} | 에러 ${errors.length}`);
  console.log(`[done] saved → ${OUTPUT_PATH}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
