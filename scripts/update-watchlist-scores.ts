/**
 * 워치리스트 & 오일전문가 포트폴리오 시세 자동 업데이트 스크립트
 *
 * - 국내 종목: 네이버 금융 API (PER/PBR/배당수익률 직접 조회)
 * - 해외 종목: Yahoo Finance v10 quoteSummary (crumb/cookie 인증)
 * - 동일 종목은 한 번만 조회하여 양쪽에 재활용
 * - 점수 변화 시 previous_score/previous_rank/grade_change_reason 자동 갱신
 *
 * 사용법: npx tsx scripts/update-watchlist-scores.ts
 */
import fs from "fs";
import path from "path";
import {
  scoreDomestic,
  scoreOverseas,
  scoreGrowth,
  getGrade,
  type DomesticStockInput,
  type OverseasStockInput,
  type GrowthStockInput,
  type ScoredResult,
} from "../src/lib/scoring";

// ── 설정 ──

const NAVER_API = "https://m.stock.naver.com/api/stock";
const YAHOO_SUMMARY = "https://query2.finance.yahoo.com/v10/finance/quoteSummary";
const YAHOO_CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb";
const YAHOO_COOKIE_URL = "https://fc.yahoo.com/curveball";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
const REQUEST_DELAY_MS = 1000;

// ── 타입 ──

interface MarketData {
  price?: number;
  per: number | null;
  pbr: number;
  dividend_yield: number;
  market_cap?: number | null;         // 시가총액 (억원)
  foreign_ownership?: number | null;  // 외국인 보유비중 (%)
}

interface StockBase {
  code: string;
  name: string;
  per: number | null;
  pbr: number;
  dividend_yield: number;
  scored_at: string;
  current_price_at_scoring?: number;
  previous_score?: number;
  previous_rank?: number;
  grade_change_reason?: string;
  [key: string]: unknown;
}

// Yahoo 심볼 매핑 (코드 → Yahoo 심볼)
const YAHOO_SYMBOL_MAP: Record<string, string> = {
  "PBR.A": "PBR-A",
  "LGEN": "LGEN.L",
  "AV.": "AV.L",
};

// ── 유틸 ──

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const fmt = (n: number | null | undefined): string =>
  n == null ? "—" : n.toLocaleString();

const diff = (a: number | null, b: number | null): string => {
  if (a == null || b == null) return "—";
  const d = b - a;
  const sign = d >= 0 ? "+" : "";
  return `${sign}${d.toFixed(2)}`;
};

function parseNumber(value: string | undefined): number | null {
  if (!value) return null;
  const cleaned = value.replace(/[^0-9.\-]/g, "");
  const num = parseFloat(cleaned);
  return isNaN(num) ? null : num;
}

// ── 네이버 금융 API (국내) ──

async function fetchFromNaver(code: string): Promise<MarketData | null> {
  try {
    // basic API에서 오늘 종가 조회
    const basicRes = await fetch(`${NAVER_API}/${code}/basic`, {
      headers: { "User-Agent": UA },
    });
    const basicJson = basicRes.ok ? await basicRes.json() : null;
    const todayClose = basicJson?.closePrice
      ? parseNumber(String(basicJson.closePrice))
      : null;

    // integration API에서 PER/PBR/배당수익률 조회
    const url = `${NAVER_API}/${code}/integration`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;

    const json = await res.json();
    const infos: { key: string; value: string }[] = json.totalInfos || [];
    const get = (key: string) => infos.find((i) => i.key === key)?.value;

    // 오늘 종가 우선, 없으면 전일 종가
    const finalPrice = todayClose || parseNumber(get("전일"));
    if (!finalPrice) return null;

    let per = parseNumber(get("PER"));
    let pbr = parseNumber(get("PBR"));
    const dividendYield = parseNumber(get("배당수익률"));

    // PER/PBR이 N/A인 경우 finance/annual에서 직접 계산
    if (per == null || pbr == null || pbr === 0) {
      const fallback = await fetchFundamentalsFromNaver(code, finalPrice);
      if (fallback) {
        if (per == null && fallback.per != null) per = fallback.per;
        if ((pbr == null || pbr === 0) && fallback.pbr > 0) pbr = fallback.pbr;
      }
    }

    // 시가총액: "73조 7,046억" → 억원 단위로 파싱
    const marketCapStr = get("시총");
    let marketCap: number | null = null;
    if (marketCapStr) {
      let total = 0;
      const joMatch = marketCapStr.match(/([\d,]+)조/);
      const eokMatch = marketCapStr.match(/([\d,]+)억/);
      if (joMatch) total += parseFloat(joMatch[1].replace(/,/g, "")) * 10000;
      if (eokMatch) total += parseFloat(eokMatch[1].replace(/,/g, ""));
      if (total > 0) marketCap = Math.round(total);
    }

    // 외국인 보유비중: "49.89%" → 49.89
    const foreignOwnership = parseNumber(get("외인소진율"));

    return { price: finalPrice, per, pbr: pbr ?? 0, dividend_yield: dividendYield ?? 0, market_cap: marketCap, foreign_ownership: foreignOwnership };
  } catch {
    return null;
  }
}

async function fetchFundamentalsFromNaver(
  code: string,
  price: number,
): Promise<{ per: number | null; pbr: number } | null> {
  try {
    const url = `${NAVER_API}/${code}/finance/annual`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;

    const json = await res.json();
    const periods = json.financeInfo?.trTitleList as
      | { key: string; isConsensus: string }[]
      | undefined;
    const rows = json.financeInfo?.rowList as
      | { title: string; columns: Record<string, { value: string }> }[]
      | undefined;
    if (!periods || !rows) return null;

    const confirmed = [...periods].filter((p) => p.isConsensus === "N").pop();
    if (!confirmed) return null;

    const getValue = (title: string): number | null => {
      const row = rows.find((r) => r.title === title);
      return parseNumber(row?.columns[confirmed.key]?.value);
    };

    const eps = getValue("EPS");
    const bps = getValue("BPS");
    const per = eps && eps > 0 ? parseFloat((price / eps).toFixed(2)) : null;
    const pbr = bps && bps > 0 ? parseFloat((price / bps).toFixed(2)) : 0;

    if (per != null || pbr > 0) {
      console.log(
        `   📈 finance/annual fallback (${confirmed.key}): EPS ${fmt(eps)} BPS ${fmt(bps)} → PER ${fmt(per)} PBR ${pbr}`,
      );
    }
    return { per, pbr };
  } catch {
    return null;
  }
}

/**
 * 네이버 finance/annual에서 전년 영업이익률을 조회
 * 확정 실적 기간 중 마지막에서 두 번째(= 전년) 영업이익률을 반환
 */
async function fetchPrevYearOpMargin(code: string): Promise<number | null> {
  try {
    const url = `${NAVER_API}/${code}/finance/annual`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;

    const json = await res.json();
    const periods = json.financeInfo?.trTitleList as
      | { key: string; isConsensus: string }[]
      | undefined;
    const rows = json.financeInfo?.rowList as
      | { title: string; columns: Record<string, { value: string }> }[]
      | undefined;
    if (!periods || !rows) return null;

    // 확정 실적만 필터 (컨센서스 제외)
    const confirmed = periods.filter((p) => p.isConsensus === "N");
    if (confirmed.length < 2) return null;

    // 마지막에서 두 번째 = 전년
    const prevYear = confirmed[confirmed.length - 2];

    // "영업이익률" 행 찾기
    const opMarginRow = rows.find((r) => r.title === "영업이익률");
    if (!opMarginRow) return null;

    const value = parseNumber(opMarginRow.columns[prevYear.key]?.value);
    if (value != null) {
      console.log(`   📊 전년 영업이익률 (${prevYear.key}): ${value}%`);
    }
    return value;
  } catch {
    return null;
  }
}

// ── Yahoo Finance API (해외) ──

let yahooCookie: string | null = null;
let yahooCrumb: string | null = null;

async function initYahooAuth(): Promise<boolean> {
  try {
    // Step 1: Get cookie
    const cookieRes = await fetch(YAHOO_COOKIE_URL, {
      headers: { "User-Agent": UA },
      redirect: "manual",
    });
    const setCookie = cookieRes.headers.get("set-cookie");
    if (setCookie) {
      yahooCookie = setCookie.split(";")[0];
    }

    // Step 2: Get crumb
    const crumbRes = await fetch(YAHOO_CRUMB_URL, {
      headers: {
        "User-Agent": UA,
        ...(yahooCookie ? { Cookie: yahooCookie } : {}),
      },
    });
    yahooCrumb = await crumbRes.text();

    return !!yahooCookie && !!yahooCrumb;
  } catch {
    return false;
  }
}

function getYahooSymbol(code: string): string {
  return YAHOO_SYMBOL_MAP[code] || code;
}

async function fetchFromYahoo(code: string, existingPbr: number): Promise<MarketData | null> {
  if (!yahooCookie || !yahooCrumb) return null;

  try {
    const symbol = getYahooSymbol(code);
    const url = `${YAHOO_SUMMARY}/${symbol}?modules=summaryDetail,defaultKeyStatistics,price&crumb=${yahooCrumb}`;
    const res = await fetch(url, {
      headers: { "User-Agent": UA, Cookie: yahooCookie },
    });
    if (!res.ok) return null;

    const json = await res.json();
    const r = json.quoteSummary?.result?.[0];
    if (!r) return null;

    const price = r.price?.regularMarketPrice?.raw;
    const pe = r.summaryDetail?.trailingPE?.raw ?? null;
    let pb = r.defaultKeyStatistics?.priceToBook?.raw ?? 0;
    const divYield = r.summaryDetail?.dividendYield?.raw ?? 0;

    // 영국 주식 PBR 단위 문제 (펜스/파운드 → 100배 이상이면 기존값 유지)
    if (pb > 100) pb = existingPbr;

    return {
      price,
      per: pe != null ? parseFloat(pe.toFixed(2)) : null,
      pbr: pb > 0 ? parseFloat(pb.toFixed(2)) : 0,
      dividend_yield: divYield > 0 ? parseFloat((divYield * 100).toFixed(2)) : 0,
    };
  } catch {
    return null;
  }
}

// ── 채점 & 순위 ──

type ScoreFn = (stocks: StockBase[]) => ScoredAll;

interface ScoredAll {
  scores: number[];
  ranks: number[];
  grades: string[];
  details: ScoredResult["details"][];
}

function scoreAllDomestic(stocks: StockBase[]): ScoredAll {
  const results = stocks.map((s) => scoreDomestic(s as unknown as DomesticStockInput));
  return buildRanks(results);
}

function scoreAllOverseas(stocks: StockBase[]): ScoredAll {
  const results = stocks.map((s) => scoreOverseas(s as unknown as OverseasStockInput));
  return buildRanks(results);
}

function makeScoreAllGrowth(baseRate: number): ScoreFn {
  return (stocks: StockBase[]) => {
    const results = stocks.map((s) => scoreGrowth(s as unknown as GrowthStockInput, baseRate));
    return buildRanks(results);
  };
}

function buildRanks(results: ScoredResult[]): ScoredAll {
  const scores = results.map((r) => r.score);
  const grades = results.map((r) => r.grade);
  const details = results.map((r) => r.details);
  const indexed = scores.map((score, i) => ({ score, i }));
  indexed.sort((a, b) => b.score - a.score);
  const ranks = new Array<number>(scores.length);
  indexed.forEach((item, rank) => { ranks[item.i] = rank + 1; });
  return { scores, ranks, grades, details };
}

/**
 * 업데이트 전후 채점 세부 항목을 비교하여
 * 실제 점수가 변한 항목만 사유로 반환
 */
function buildChangeReason(
  beforeDetails: ScoredResult["details"],
  afterDetails: ScoredResult["details"],
): string {
  const parts: string[] = [];
  for (let i = 0; i < beforeDetails.length; i++) {
    const b = beforeDetails[i];
    const a = afterDetails[i];
    if (b && a && b.score !== a.score) {
      const diff = a.score - b.score;
      const sign = diff > 0 ? "+" : "";
      parts.push(`${a.item} ${b.score}→${a.score}점(${sign}${diff})`);
    }
  }
  return parts.join(", ");
}

// ── 공통 업데이트 로직 ──

interface UpdateResult {
  updated: number;
  skipped: number;
  scoreChanges: number;
  gradeChanges: number;
  rankChanges: number;
}

async function updateStocks(
  stocks: StockBase[],
  fetchFn: (code: string, stock: StockBase) => Promise<MarketData | null>,
  scoreFn: ScoreFn,
  today: string,
  naverCache: Map<string, MarketData>,
): Promise<UpdateResult> {
  // Step 1: 업데이트 전 점수/순위 + 이미 오늘 업데이트된 종목 기록
  const before = scoreFn(stocks);
  const alreadyUpdatedToday = stocks.map(
    (s) => s.scored_at === today && s.previous_score != null,
  );

  // Step 2: 시세 업데이트
  let updated = 0;
  let skipped = 0;
  const prevMarketData: { per: number | null; pbr: number; div: number }[] = [];

  for (let i = 0; i < stocks.length; i++) {
    const stock = stocks[i];
    prevMarketData.push({ per: stock.per, pbr: stock.pbr, div: stock.dividend_yield });

    // 캐시 확인 (워치리스트에서 이미 조회한 국내 종목)
    let result = naverCache.get(stock.code) || null;
    if (!result) {
      result = await fetchFn(stock.code, stock);
      if (result) naverCache.set(stock.code, result);
      await sleep(REQUEST_DELAY_MS);
    } else {
      console.log(`   ♻️ 캐시 재활용`);
    }

    if (!result) {
      console.log(`\n❌ ${stock.name} (${stock.code}): 시세 조회 실패 — 건너뜀`);
      skipped++;
      continue;
    }

    const newPer = result.per ?? stock.per;
    const newPbr = result.pbr > 0 ? result.pbr : stock.pbr;
    const newDiv = result.dividend_yield;

    stock.per = newPer;
    stock.pbr = newPbr;
    stock.dividend_yield = newDiv;
    if (result.price) stock.current_price_at_scoring = result.price;
    if (result.market_cap != null) stock.market_cap = result.market_cap;
    if (result.foreign_ownership != null) stock.foreign_ownership = result.foreign_ownership;
    stock.scored_at = today;

    if ("fundamentals" in stock) delete stock.fundamentals;

    const kept: string[] = [];
    if (result.per == null) kept.push("PER");
    if (result.pbr === 0) kept.push("PBR");

    const priceStr = result.price ? `${fmt(result.price)}` : "";
    console.log(
      `\n✅ ${stock.name} (${stock.code}) ${priceStr}` +
        (kept.length > 0 ? ` ⚠️ ${kept.join("/")} 기존값 유지` : ""),
    );
    console.log(
      `   PER ${fmt(prevMarketData[i].per)} → ${fmt(newPer)} (${diff(prevMarketData[i].per, newPer)})` +
        ` | PBR ${prevMarketData[i].pbr} → ${newPbr} (${diff(prevMarketData[i].pbr, newPbr)})` +
        ` | 배당률 ${prevMarketData[i].div}% → ${newDiv}% (${diff(prevMarketData[i].div, newDiv)})`,
    );

    updated++;
  }

  // Step 3: 변화 반영
  const after = scoreFn(stocks);
  let gradeChanges = 0;
  let scoreChanges = 0;
  let rankChanges = 0;

  for (let i = 0; i < stocks.length; i++) {
    const stock = stocks[i];

    // 같은 날 중복 실행 시 previous_score/previous_rank를 덮어쓰지 않음
    // (Step 2 전에 scored_at이 이미 오늘이었는지 기준)
    if (!alreadyUpdatedToday[i]) {
      stock.previous_score = before.scores[i];
      stock.previous_rank = before.ranks[i];
    }

    const oldGrade = stock.previous_score != null ? getGrade(stock.previous_score) : before.grades[i];
    const newGrade = after.grades[i];
    const prevScore = stock.previous_score ?? before.scores[i];
    const scoreChanged = prevScore !== after.scores[i];

    if (scoreChanged) {
      const reason = buildChangeReason(
        before.details[i],
        after.details[i],
      );
      stock.grade_change_reason = reason;
      scoreChanges++;

      if (oldGrade !== newGrade) {
        gradeChanges++;
        console.log(`\n🔄 ${stock.name}: ${oldGrade}(${prevScore}점) → ${newGrade}(${after.scores[i]}점) | ${reason}`);
      } else {
        console.log(`\n📝 ${stock.name}: ${prevScore}점 → ${after.scores[i]}점 | ${reason}`);
      }
    } else if (!alreadyUpdatedToday[i]) {
      delete stock.grade_change_reason;
    }

    const prevRank = stock.previous_rank ?? before.ranks[i];
    if (prevRank !== after.ranks[i]) rankChanges++;
  }

  return { updated, skipped, scoreChanges, gradeChanges, rankChanges };
}

function printSummary(label: string, r: UpdateResult) {
  console.log(
    `💾 ${label}: ${r.updated}개 업데이트, ${r.skipped}개 실패` +
      (r.scoreChanges > 0 ? `, ${r.scoreChanges}개 점수 변화` : "") +
      (r.gradeChanges > 0 ? ` (등급 변화 ${r.gradeChanges}개)` : "") +
      (r.rankChanges > 0 ? `, ${r.rankChanges}개 순위 변동` : ""),
  );
}

// ── 메인 ──

async function main() {
  const today = new Date().toISOString().split("T")[0];
  const naverCache = new Map<string, MarketData>();

  // ─── 1. 워치리스트 (국내) ───
  const watchlistPath = path.join(process.cwd(), "public", "data", "watchlist.json");
  const watchlistData = JSON.parse(fs.readFileSync(watchlistPath, "utf-8"));

  console.log(`\n📊 [워치리스트] 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  const watchlistResult = await updateStocks(
    watchlistData.stocks as StockBase[],
    async (code) => fetchFromNaver(code),
    scoreAllDomestic,
    today,
    naverCache,
  );

  fs.writeFileSync(watchlistPath, JSON.stringify(watchlistData, null, 2) + "\n", "utf-8");
  console.log("\n" + "─".repeat(65));
  printSummary("워치리스트", watchlistResult);

  // ─── 2. 저평가 성장주 (국내) ───
  const growthPath = path.join(process.cwd(), "public", "data", "growth-watchlist.json");
  const growthData = JSON.parse(fs.readFileSync(growthPath, "utf-8"));

  if ((growthData.stocks as StockBase[]).length > 0) {
    console.log(`\n\n📊 [저평가 성장주] 시세 업데이트 (${today})`);
    console.log("─".repeat(65));

    const baseRate = growthData.base_rate ?? 2.75;

    // 전년 영업이익률 자동 조회 (성장주 전용)
    console.log("\n📊 전년 영업이익률 조회 중...");
    for (const stock of growthData.stocks as StockBase[]) {
      const prevMargin = await fetchPrevYearOpMargin(stock.code);
      if (prevMargin != null) {
        stock.prev_year_op_margin = prevMargin;
      }
      await sleep(REQUEST_DELAY_MS);
    }

    const growthResult = await updateStocks(
      growthData.stocks as StockBase[],
      async (code) => fetchFromNaver(code),
      makeScoreAllGrowth(baseRate),
      today,
      naverCache,
    );

    console.log("\n" + "─".repeat(65));
    printSummary("저평가 성장주", growthResult);
  } else {
    console.log(`\n\n📊 [저평가 성장주] 종목 없음 — 건너뜀`);
  }

  fs.writeFileSync(growthPath, JSON.stringify(growthData, null, 2) + "\n", "utf-8");

  // ─── 3. 오일전문가 포트폴리오 ───
  const oilPath = path.join(process.cwd(), "public", "data", "oil-expert-watchlist.json");
  const oilData = JSON.parse(fs.readFileSync(oilPath, "utf-8"));

  // 2-1. 국내 종목
  console.log(`\n\n📊 [오일전문가 - 국내] 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  const oilDomesticResult = await updateStocks(
    oilData.domestic as StockBase[],
    async (code) => fetchFromNaver(code),
    scoreAllDomestic,
    today,
    naverCache,
  );

  console.log("\n" + "─".repeat(65));
  printSummary("오일전문가 국내", oilDomesticResult);

  // 2-2. 해외 종목
  console.log(`\n\n📊 [오일전문가 - 해외] 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  const yahooOk = await initYahooAuth();
  if (!yahooOk) {
    console.log("⚠️ Yahoo Finance 인증 실패 — 해외 종목 건너뜀");
  } else {
    const oilOverseasResult = await updateStocks(
      oilData.overseas as StockBase[],
      async (code, stock) => fetchFromYahoo(code, stock.pbr),
      scoreAllOverseas,
      today,
      new Map(), // 해외는 별도 캐시 (네이버 캐시와 분리)
    );

    console.log("\n" + "─".repeat(65));
    printSummary("오일전문가 해외", oilOverseasResult);
  }

  fs.writeFileSync(oilPath, JSON.stringify(oilData, null, 2) + "\n", "utf-8");

  // ─── 4. 매매일지 보유 종목 ───
  const journalPath = path.join(process.cwd(), "public", "data", "journal.json");
  const journalData = JSON.parse(fs.readFileSync(journalPath, "utf-8"));

  console.log(`\n\n📊 [매매일지] 보유 종목 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  const holdings = journalData.holdings as {
    code: string; name: string;
    quantity: number; avg_price: number;
    current_price: number; eval_amount: number;
    profit_amount: number; profit_pct: number;
    [key: string]: unknown;
  }[];

  let journalUpdated = 0;
  let journalSkipped = 0;

  for (const h of holdings) {
    // 네이버 캐시 재활용 또는 신규 조회
    let cached = naverCache.get(h.code);
    if (!cached) {
      const result = await fetchFromNaver(h.code);
      if (result) {
        naverCache.set(h.code, result);
        cached = result;
      }
      await sleep(REQUEST_DELAY_MS);
    }

    if (!cached?.price) {
      console.log(`\n❌ ${h.name} (${h.code}): 시세 조회 실패 — 건너뜀`);
      journalSkipped++;
      continue;
    }

    const prevPrice = h.current_price;
    const newPrice = cached.price;

    h.current_price = newPrice;
    h.eval_amount = newPrice * h.quantity;
    h.profit_amount = h.eval_amount - h.avg_price * h.quantity;
    h.profit_pct = parseFloat(((h.profit_amount / (h.avg_price * h.quantity)) * 100).toFixed(1));

    const priceDiff = newPrice - prevPrice;
    const sign = priceDiff >= 0 ? "+" : "";
    console.log(
      `\n✅ ${h.name} (${h.code}) ${fmt(prevPrice)}원 → ${fmt(newPrice)}원 (${sign}${fmt(priceDiff)})` +
        `\n   평가금액 ${fmt(h.eval_amount)}원 | 수익 ${fmt(h.profit_amount)}원 (${h.profit_pct}%)`,
    );

    journalUpdated++;
  }

  // 요약 갱신
  if (journalUpdated > 0) {
    const totalEval = holdings.reduce((s, h) => s + h.eval_amount, 0);
    const totalInvested = holdings.reduce((s, h) => s + h.avg_price * h.quantity, 0);
    const holdingsProfit = totalEval - totalInvested;

    journalData.summary.total_current_value = totalEval;
    journalData.summary.total_assets = totalEval + journalData.summary.cash;

    // 순수익 = 매매차익 + 보유평가손익 - 비용
    const netProfit = journalData.summary.gross_profit + holdingsProfit - journalData.summary.total_cost;
    journalData.summary.net_profit = netProfit;
    journalData.summary.net_profit_pct = parseFloat(
      ((netProfit / journalData.summary.total_invested) * 100).toFixed(1),
    );

    console.log(
      `\n📊 포트폴리오 요약: 평가액 ${fmt(totalEval)}원 | 총자산 ${fmt(journalData.summary.total_assets)}원 | 순수익률 ${journalData.summary.net_profit_pct}%`,
    );
  }

  fs.writeFileSync(journalPath, JSON.stringify(journalData, null, 2) + "\n", "utf-8");

  console.log("\n" + "─".repeat(65));
  console.log(`💾 매매일지: ${journalUpdated}개 업데이트, ${journalSkipped}개 실패`);

  console.log("\n" + "═".repeat(65));
  console.log("✨ 전체 업데이트 완료");

  const totalSkipped = watchlistResult.skipped + oilDomesticResult.skipped + journalSkipped;
  if (totalSkipped > 0) process.exitCode = 1;
}

main().catch((err) => {
  console.error("스크립트 실행 실패:", err);
  process.exitCode = 1;
});
