/**
 * 성장주 자동 스크리닝 — 분기 전체 스캔
 *
 * 코스피+코스닥 전체에서 성장주 후보를 자동 선별.
 * 1차 필터: 시총 500억+, PER 양수, 스팩/리츠 제외
 * 2차 상세: finance/annual에서 성장률 + 컨센서스 추출
 * 3차 점수: scoreGrowthScreen()으로 채점, 상위 저장
 *
 * 사용법: npx tsx scripts/screen-growth-full.ts
 */
import fs from "fs";
import path from "path";
import {
  scoreGrowthScreen,
  getGrade,
  getGradeColor,
  getInterestRatePenalty,
  type GrowthScreenInput,
  type ScoredResult,
} from "../src/lib/scoring";

// ── 설정 ──

const NAVER_LIST = "https://m.stock.naver.com/api/stocks/marketValue";
const NAVER_API = "https://m.stock.naver.com/api/stock";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
const HEADERS = { "User-Agent": UA };
const DATA_DIR = path.resolve("public/data");
const OUTPUT_FILE = path.join(DATA_DIR, "growth-candidates.json");
const BASE_RATE = 2.75; // 기준금리

// ── 유틸 ──

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

function parseNum(s: string | undefined | null): number {
  if (!s || s === "-" || s === "") return 0;
  return Number(s.replace(/,/g, "")) || 0;
}

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ── Step 1: 전 종목 코드 수집 ──

interface StockBasic { code: string; name: string; }

async function getAllStockCodes(market: string): Promise<StockBasic[]> {
  const all: StockBasic[] = [];
  let page = 1;
  while (true) {
    const res = await fetch(`${NAVER_LIST}/${market}?page=${page}&pageSize=100`, { headers: HEADERS });
    if (!res.ok) break;
    const json = await res.json();
    const stocks = json.stocks || [];
    if (stocks.length === 0) break;
    for (const s of stocks) {
      if (s.stockEndType === "stock") {
        all.push({ code: s.itemCode, name: s.stockName });
      }
    }
    page++;
    if (stocks.length < 100) break;
  }
  return all;
}

// ── Step 2: 1차 필터 (integration API — PER/시총/외국인) ──

interface Phase1Data {
  code: string;
  name: string;
  market: string;
  per: number | null;
  pbr: number;
  dividend_yield: number;
  market_cap: number;
  foreign_ownership: number;
  price: number;
}

const EXCLUDE_PATTERN = /스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$/;

function parseMarketCap(str: string): number {
  let total = 0;
  const joMatch = str.match(/([\d,]+)조/);
  const eokMatch = str.match(/([\d,]+)억/);
  if (joMatch) total += parseNum(joMatch[1]) * 10000;
  if (eokMatch) total += parseNum(eokMatch[1]);
  return total;
}

async function fetchPhase1(code: string): Promise<Omit<Phase1Data, "code" | "name" | "market"> | null> {
  try {
    const res = await fetch(`${NAVER_API}/${code}/integration`, { headers: HEADERS });
    if (!res.ok) return null;
    const json = await res.json();
    const str = JSON.stringify(json);

    let per: number | null = null;
    let pbr = 0;
    let dividendYield = 0;
    let marketCap = 0;
    let foreignOwnership = 0;
    let price = 0;

    const perM = str.match(/"code":"per","key":"PER","value":"([\d,.]+)배"/);
    if (perM) per = parseFloat(perM[1].replace(/,/g, ""));

    const pbrM = str.match(/"code":"pbr","key":"PBR","value":"([\d,.]+)배"/);
    if (pbrM) pbr = parseFloat(pbrM[1].replace(/,/g, ""));

    const dyM = str.match(/"code":"dividendYieldRatio","key":"배당수익률","value":"([\d,.]+)%"/);
    if (dyM) dividendYield = parseFloat(dyM[1].replace(/,/g, ""));

    const capM = str.match(/"code":"marketValue","key":"시총","value":"([^"]+)"/);
    if (capM) marketCap = parseMarketCap(capM[1]);

    const foreignM = str.match(/"code":"foreignRatio","key":"외인소진율","value":"([\d,.]+)%"/);
    if (foreignM) foreignOwnership = parseFloat(foreignM[1].replace(/,/g, ""));

    const priceM = str.match(/"code":"closePrice","key":"전일","value":"([\d,]+)원"/);
    if (priceM) price = parseNum(priceM[1]);
    if (!price) {
      // basic API fallback
      try {
        const basicRes = await fetch(`${NAVER_API}/${code}/basic`, { headers: HEADERS });
        if (basicRes.ok) {
          const basicJson = await basicRes.json();
          price = parseNum(basicJson.closePrice);
        }
      } catch { /* ignore */ }
    }

    return { per, pbr, dividend_yield: dividendYield, market_cap: marketCap, foreign_ownership: foreignOwnership, price };
  } catch {
    return null;
  }
}

// ── Step 3: 2차 상세 (finance/annual — 성장률 + 컨센서스) ──

interface Phase2Data {
  revenue_latest: number;
  revenue_prev: number;
  op_profit_latest: number;
  op_profit_prev: number;
  op_margin: number;
  op_margin_prev: number | null;
  profit_years: number;
  eps_current: number | null;
  eps_consensus: number | null;
}

async function fetchPhase2(code: string): Promise<Phase2Data | null> {
  try {
    const res = await fetch(`${NAVER_API}/${code}/finance/annual`, { headers: HEADERS });
    if (!res.ok) return null;
    const json = await res.json();

    const periods = json.financeInfo?.trTitleList as { key: string; isConsensus: string }[] | undefined;
    const rows = json.financeInfo?.rowList as { title: string; columns: Record<string, { value: string }> }[] | undefined;
    if (!periods || !rows) return null;

    // 확정 실적 기간 (최근 2개)
    const confirmed = periods.filter((p) => p.isConsensus === "N");
    const latest = confirmed[confirmed.length - 1];
    const prev = confirmed[confirmed.length - 2];
    if (!latest) return null;

    // 컨센서스 기간 (가장 가까운 미래)
    const consensus = periods.find((p) => p.isConsensus === "Y");

    const getValue = (title: string, periodKey: string): number => {
      const row = rows.find((r) => r.title === title);
      return parseNum(row?.columns[periodKey]?.value);
    };

    // 매출/영업이익
    const revLatest = getValue("매출액", latest.key);
    const revPrev = prev ? getValue("매출액", prev.key) : 0;
    const opLatest = getValue("영업이익", latest.key);
    const opPrev = prev ? getValue("영업이익", prev.key) : 0;

    // 영업이익률
    const opMargin = getValue("영업이익률", latest.key);
    const opMarginPrev = prev ? getValue("영업이익률", prev.key) : null;

    // EPS
    const epsRow = rows.find((r) => r.title === "EPS");
    const epsCurrent = epsRow ? parseNum(epsRow.columns[latest.key]?.value) : null;
    const epsConsensus = consensus && epsRow ? parseNum(epsRow.columns[consensus.key]?.value) : null;

    // 연속 흑자 연수
    let profitYears = 0;
    for (let i = confirmed.length - 1; i >= 0; i--) {
      const op = getValue("영업이익", confirmed[i].key);
      if (op > 0) profitYears++;
      else break;
    }

    return {
      revenue_latest: revLatest,
      revenue_prev: revPrev,
      op_profit_latest: opLatest,
      op_profit_prev: opPrev,
      op_margin: opMargin || 0,
      op_margin_prev: opMarginPrev,
      profit_years: profitYears,
      eps_current: epsCurrent && epsCurrent > 0 ? epsCurrent : null,
      eps_consensus: epsConsensus && epsConsensus > 0 ? epsConsensus : null,
    };
  } catch {
    return null;
  }
}

// ── 배치 처리 ──

async function batchFetch<T, R>(items: T[], fn: (item: T) => Promise<R>, concurrency: number, label: string): Promise<R[]> {
  const results: R[] = [];
  for (let i = 0; i < items.length; i += concurrency) {
    const batch = items.slice(i, i + concurrency);
    const batchResults = await Promise.all(batch.map(fn));
    results.push(...batchResults);
    process.stdout.write(`\r  ${Math.min(i + concurrency, items.length)}/${items.length} ${label}`);
  }
  process.stdout.write("\n");
  return results;
}

// ── 메인 ──

async function main() {
  console.log("📊 성장주 자동 스크리닝 시작\n");

  // Step 1: 전 종목 수집
  console.log("1️⃣ 종목 코드 수집...");
  const kospi = await getAllStockCodes("KOSPI");
  console.log(`  KOSPI: ${kospi.length}종목`);
  const kosdaq = await getAllStockCodes("KOSDAQ");
  console.log(`  KOSDAQ: ${kosdaq.length}종목`);

  const allStocks = [
    ...kospi.map((s) => ({ ...s, market: "KOSPI" })),
    ...kosdaq.map((s) => ({ ...s, market: "KOSDAQ" })),
  ].filter((s) => !EXCLUDE_PATTERN.test(s.name));
  console.log(`  유효 종목: ${allStocks.length}개 (스팩/리츠/ETF 제외)\n`);

  // Step 2: 1차 필터 (integration API)
  console.log("2️⃣ 1차 필터 (시총/PER 조회)...");
  const phase1Results = await batchFetch(
    allStocks,
    async (s) => {
      const data = await fetchPhase1(s.code);
      return { ...s, data };
    },
    10,
    "조회 중...",
  );

  const phase1Passed = phase1Results.filter((r) => {
    if (!r.data) return false;
    if (r.data.market_cap < 500) return false; // 500억 미만 제외
    if (r.data.per == null || r.data.per <= 0) return false; // 적자 제외
    return true;
  });
  console.log(`  1차 통과: ${phase1Passed.length}개 (시총 500억+ & 흑자)\n`);

  // Step 3: 2차 상세 (finance/annual)
  console.log("3️⃣ 2차 상세 조회 (성장률/컨센서스)...");
  const phase2Results = await batchFetch(
    phase1Passed,
    async (s) => {
      const detail = await fetchPhase2(s.code);
      await sleep(100); // 약간의 딜레이
      return { ...s, detail };
    },
    5,
    "상세 조회 중...",
  );

  // Step 4: 점수 계산
  console.log("\n4️⃣ 점수 계산 중...");
  const scored: (GrowthScreenInput & ScoredResult & { market: string })[] = [];

  for (const r of phase2Results) {
    if (!r.data || !r.detail) continue;
    if (r.detail.op_profit_latest <= 0) continue; // 최근 영업적자 제외

    const input: GrowthScreenInput = {
      code: r.code,
      name: r.name,
      market: r.market,
      per: r.data.per,
      pbr: r.data.pbr,
      market_cap: r.data.market_cap,
      foreign_ownership: r.data.foreign_ownership,
      dividend_yield: r.data.dividend_yield,
      current_price: r.data.price,
      revenue_latest: r.detail.revenue_latest,
      revenue_prev: r.detail.revenue_prev,
      op_profit_latest: r.detail.op_profit_latest,
      op_profit_prev: r.detail.op_profit_prev,
      op_margin: r.detail.op_margin,
      op_margin_prev: r.detail.op_margin_prev,
      profit_years: r.detail.profit_years,
      eps_current: r.detail.eps_current,
      eps_consensus: r.detail.eps_consensus,
    };

    const result = scoreGrowthScreen(input, BASE_RATE);
    scored.push({ ...input, ...result, market: r.market });
  }

  // 등급순 → 점수순 정렬
  const gradeOrder: Record<string, number> = { A: 0, B: 1, C: 2, D: 3 };
  scored.sort((a, b) => {
    const gd = (gradeOrder[a.grade] ?? 9) - (gradeOrder[b.grade] ?? 9);
    return gd !== 0 ? gd : b.score - a.score;
  });

  // 상위 30개 + Top 10 표시
  const top30 = scored.slice(0, 30);

  console.log(`\n✅ 채점 완료: ${scored.length}개 종목\n`);
  console.log("🏆 Top 10:");
  top30.slice(0, 10).forEach((s, i) => {
    const consensus = s.eps_consensus ? `컨센서스 EPS ${s.eps_consensus.toLocaleString()}` : "컨센서스 없음";
    console.log(`  ${(i + 1).toString().padStart(2)}. [${s.grade}] ${s.name.padEnd(14)} ${String(s.score).padStart(3)}점  ${s.market}  시총${s.market_cap.toLocaleString()}억  ${consensus}`);
  });

  console.log("\n📋 11~30위:");
  top30.slice(10).forEach((s, i) => {
    console.log(`  ${(i + 11).toString().padStart(2)}. [${s.grade}] ${s.name.padEnd(14)} ${String(s.score).padStart(3)}점  ${s.market}`);
  });

  // 저장
  const output = {
    scanned_at: today(),
    base_rate: BASE_RATE,
    total_scanned: allStocks.length,
    filter_passed: phase1Passed.length,
    scored_count: scored.length,
    candidates: top30.map((s) => ({
      code: s.code,
      name: s.name,
      market: s.market,
      score: s.score,
      grade: s.grade,
      cat1: s.cat1,
      cat2: s.cat2,
      cat3: s.cat3,
      details: s.details,
      market_cap: s.market_cap,
      per: s.per,
      pbr: s.pbr,
      dividend_yield: s.dividend_yield,
      foreign_ownership: s.foreign_ownership,
      current_price: s.current_price,
      revenue_latest: s.revenue_latest,
      revenue_prev: s.revenue_prev,
      op_profit_latest: s.op_profit_latest,
      op_profit_prev: s.op_profit_prev,
      op_margin: s.op_margin,
      op_margin_prev: s.op_margin_prev,
      profit_years: s.profit_years,
      eps_current: s.eps_current,
      eps_consensus: s.eps_consensus,
      is_top10: scored.indexOf(s) < 10,
    })),
    excluded: [] as { code: string; name: string; reason: string }[],
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2), "utf-8");
  console.log(`\n💾 저장 완료: ${OUTPUT_FILE}`);
}

main().catch((e) => {
  console.error("❌ 실행 오류:", e);
  process.exit(1);
});
