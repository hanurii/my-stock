/**
 * 외국인 자본 흐름 수집 스크립트
 *
 * 데이터 소스: Naver 모바일 API (m.stock.naver.com / api.stock.naver.com)
 *  - 시장 일별 외인 순매수: /api/index/{KOSPI,KOSDAQ}/integration → dealTrendInfo.foreignValue (단위: 백만원)
 *  - 종목 일별 외인 순매수량: /api/stock/{code}/integration → dealTrendInfos[*] (5영업일치)
 *
 * 출력: public/data/foreign-flow.json
 *
 * 매일 1회 실행하며 시계열을 누적한다 (overwrite하지 않고 merge).
 * KRX data.krx.co.kr 엔드포인트는 LOGOUT 응답으로 차단되어 사용하지 않음.
 *
 * 사용법: npx tsx scripts/fetch-foreign-flow.ts
 */
import fs from "fs";
import path from "path";

const NAVER_INDEX_INTEGRATION = (code: "KOSPI" | "KOSDAQ") =>
  `https://m.stock.naver.com/api/index/${code}/integration`;
const NAVER_STOCK_INTEGRATION = (code: string) =>
  `https://m.stock.naver.com/api/stock/${code}/integration`;
const UA_MOBILE =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1";
const REFERER = "https://m.stock.naver.com/";

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "public", "data");
const OUTPUT_PATH = path.join(DATA_DIR, "foreign-flow.json");
const WATCHLIST_PATH = path.join(DATA_DIR, "watchlist.json");

const KEEP_DAYS = 60;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function getKST(): { date: string; iso: string } {
  const now = new Date();
  const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  const date = kst.toISOString().split("T")[0];
  const hh = String(kst.getUTCHours()).padStart(2, "0");
  const mm = String(kst.getUTCMinutes()).padStart(2, "0");
  const ss = String(kst.getUTCSeconds()).padStart(2, "0");
  return { date, iso: `${date} ${hh}:${mm}:${ss}` };
}

// "+11,832" / "-19,496" / "0" → number (그대로 유지: 백만원 단위)
function parseSignedNumber(raw: string | undefined | null): number | null {
  if (raw == null) return null;
  const cleaned = String(raw).replace(/[,\s]/g, "");
  if (!/^[+-]?\d+(\.\d+)?$/.test(cleaned)) return null;
  return parseFloat(cleaned);
}

// "20260424" → "2026-04-24"
function bizdateToISO(bizdate: string): string {
  return `${bizdate.slice(0, 4)}-${bizdate.slice(4, 6)}-${bizdate.slice(6, 8)}`;
}

// ── 시장 일별 외인 순매수 (오늘 1포인트) ──

interface MarketSnapshot {
  date: string;            // YYYY-MM-DD
  kospi_billion: number;   // 단위: 억원
  kosdaq_billion: number;
  total_billion: number;
}

async function fetchMarketSnapshot(): Promise<MarketSnapshot | null> {
  const fetchOne = async (code: "KOSPI" | "KOSDAQ") => {
    const res = await fetch(NAVER_INDEX_INTEGRATION(code), {
      headers: { "User-Agent": UA_MOBILE, Referer: REFERER },
    });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      dealTrendInfo?: { bizdate?: string; foreignValue?: string };
    };
    const info = json.dealTrendInfo;
    if (!info?.bizdate || info.foreignValue == null) return null;
    const valMillion = parseSignedNumber(info.foreignValue);
    if (valMillion == null) return null;
    return { bizdate: info.bizdate, valMillion };
  };

  const [kospi, kosdaq] = await Promise.all([fetchOne("KOSPI"), fetchOne("KOSDAQ")]);
  if (!kospi || !kosdaq) return null;
  if (kospi.bizdate !== kosdaq.bizdate) {
    console.warn(`[market] bizdate mismatch: KOSPI=${kospi.bizdate} KOSDAQ=${kosdaq.bizdate}`);
  }

  // 백만원 → 억원 환산: ÷100
  const kospiBn = kospi.valMillion / 100;
  const kosdaqBn = kosdaq.valMillion / 100;
  return {
    date: bizdateToISO(kospi.bizdate),
    kospi_billion: Math.round(kospiBn * 10) / 10,
    kosdaq_billion: Math.round(kosdaqBn * 10) / 10,
    total_billion: Math.round((kospiBn + kosdaqBn) * 10) / 10,
  };
}

// ── 종목별 5영업일 외인 순매수 → sector 일별 집계 ──

interface SectorDailyPoint {
  date: string;
  sector: string;
  net_buy_billion: number;   // 억원
}

interface WatchlistStock {
  code: string;
  name: string;
  sector?: string;
}

async function fetchStockDealTrends(code: string): Promise<
  Array<{ date: string; foreignBuyShares: number; closePrice: number }> | null
> {
  try {
    const res = await fetch(NAVER_STOCK_INTEGRATION(code), {
      headers: { "User-Agent": UA_MOBILE, Referer: REFERER },
    });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      dealTrendInfos?: Array<{
        bizdate?: string;
        foreignerPureBuyQuant?: string;
        closePrice?: string;
      }>;
    };
    const arr = json.dealTrendInfos;
    if (!arr || !Array.isArray(arr)) return null;
    const out: Array<{ date: string; foreignBuyShares: number; closePrice: number }> = [];
    for (const it of arr) {
      if (!it.bizdate) continue;
      const fb = parseSignedNumber(it.foreignerPureBuyQuant ?? null);
      const cp = parseSignedNumber(it.closePrice ?? null);
      if (fb == null || cp == null) continue;
      out.push({ date: bizdateToISO(it.bizdate), foreignBuyShares: fb, closePrice: cp });
    }
    return out;
  } catch {
    return null;
  }
}

async function fetchSectorDailyFromWatchlist(): Promise<{
  daily: SectorDailyPoint[];
  stockCount: number;
  failedCount: number;
}> {
  let watchlist: { stocks?: WatchlistStock[] } = {};
  try {
    watchlist = JSON.parse(fs.readFileSync(WATCHLIST_PATH, "utf-8"));
  } catch (e) {
    console.error("[sector] failed to read watchlist.json:", e);
    return { daily: [], stockCount: 0, failedCount: 0 };
  }
  const stocks = (watchlist.stocks ?? []).filter((s) => s.code && s.sector);
  console.log(`[sector] aggregating ${stocks.length} watchlist stocks`);

  // sector → date → cumulative net buy (백만원)
  const agg = new Map<string, Map<string, number>>();
  let failed = 0;

  for (let i = 0; i < stocks.length; i++) {
    const s = stocks[i];
    const trends = await fetchStockDealTrends(s.code);
    if (!trends) {
      failed++;
      console.warn(`  [${i + 1}/${stocks.length}] ${s.code} ${s.name} — fetch failed`);
    } else {
      for (const t of trends) {
        // 외인 순매수 금액 (원 단위) = 주식수 × 종가 → 백만원으로 환산: ÷ 1_000_000
        const netMillion = (t.foreignBuyShares * t.closePrice) / 1_000_000;
        const sectorKey = s.sector!;
        if (!agg.has(sectorKey)) agg.set(sectorKey, new Map());
        const dayMap = agg.get(sectorKey)!;
        dayMap.set(t.date, (dayMap.get(t.date) ?? 0) + netMillion);
      }
    }
    // rate limit
    await sleep(120);
  }

  // 백만원 → 억원
  const daily: SectorDailyPoint[] = [];
  for (const [sector, dayMap] of agg) {
    for (const [date, valMillion] of dayMap) {
      daily.push({
        date,
        sector,
        net_buy_billion: Math.round((valMillion / 100) * 10) / 10,
      });
    }
  }
  return { daily, stockCount: stocks.length, failedCount: failed };
}

// ── 추세 라벨 ──

type TrendLabel = "강한 매수" | "매수 우위" | "보합" | "매도 우위" | "강한 매도";

function labelTrend(cumBillion: number, scale: 1 | 3): TrendLabel {
  // 임계치 (억원): 보합 ±1000, 매수 우위 ±10000(1조), 강한 매수 그 이상. scale=3은 60일 기준 ×3
  const t1 = 1000 * scale;
  const t2 = 10000 * scale;
  if (cumBillion >= t2) return "강한 매수";
  if (cumBillion >= t1) return "매수 우위";
  if (cumBillion <= -t2) return "강한 매도";
  if (cumBillion <= -t1) return "매도 우위";
  return "보합";
}

// ── 출력 스키마 ──

interface ForeignFlowOutput {
  meta: {
    last_updated: string;        // KST iso "2026-04-26 17:30:00"
    source: "Naver Mobile";
    period_days: number;
    sector_basis: "watchlist";
    watchlist_stocks: number;
    failed_stocks: number;
    last_error?: string;
  };
  market: {
    daily: Array<{
      date: string;
      kospi_billion: number;
      kosdaq_billion: number;
      total_billion: number;
    }>;
    summary: {
      cum_20d_billion: number;
      cum_60d_billion: number;
      kospi_cum_20d_billion: number;
      kosdaq_cum_20d_billion: number;
      trend_20d: TrendLabel;
      trend_60d: TrendLabel;
      kospi_trend_20d: TrendLabel;
      kosdaq_trend_20d: TrendLabel;
    };
  };
  sectors: {
    daily: SectorDailyPoint[];           // 모든 sector × 모든 영업일
    cum_1d: Array<{ sector: string; net_buy_billion: number }>;
    cum_3d: Array<{ sector: string; net_buy_billion: number }>;
    cum_7d: Array<{ sector: string; net_buy_billion: number }>;
    cum_20d: Array<{ sector: string; net_buy_billion: number }>;
    cum_60d: Array<{ sector: string; net_buy_billion: number }>;
  };
}

function readExisting(): ForeignFlowOutput | null {
  try {
    if (!fs.existsSync(OUTPUT_PATH)) return null;
    return JSON.parse(fs.readFileSync(OUTPUT_PATH, "utf-8")) as ForeignFlowOutput;
  } catch {
    return null;
  }
}

function mergeMarketDaily(
  existing: ForeignFlowOutput["market"]["daily"],
  todaySnapshot: MarketSnapshot | null,
): ForeignFlowOutput["market"]["daily"] {
  const map = new Map<string, MarketSnapshot>();
  for (const p of existing) map.set(p.date, p);
  if (todaySnapshot) map.set(todaySnapshot.date, todaySnapshot);
  const sorted = Array.from(map.values()).sort((a, b) => (a.date < b.date ? -1 : 1));
  return sorted.slice(-KEEP_DAYS);
}

function mergeSectorDaily(
  existing: SectorDailyPoint[],
  fresh: SectorDailyPoint[],
): SectorDailyPoint[] {
  // key: date|sector. fresh가 우선.
  const map = new Map<string, SectorDailyPoint>();
  for (const p of existing) map.set(`${p.date}|${p.sector}`, p);
  for (const p of fresh) map.set(`${p.date}|${p.sector}`, p);
  // 60일 윈도우 컷
  const allDates = Array.from(new Set(Array.from(map.values()).map((p) => p.date))).sort();
  const keepSet = new Set(allDates.slice(-KEEP_DAYS));
  return Array.from(map.values())
    .filter((p) => keepSet.has(p.date))
    .sort((a, b) => (a.date === b.date ? a.sector.localeCompare(b.sector) : a.date < b.date ? -1 : 1));
}

function summarizeMarket(daily: MarketSnapshot[]): ForeignFlowOutput["market"]["summary"] {
  const last20 = daily.slice(-20);
  const last60 = daily.slice(-60);
  const sum = (arr: MarketSnapshot[], k: keyof MarketSnapshot) =>
    arr.reduce((acc, p) => acc + (typeof p[k] === "number" ? (p[k] as number) : 0), 0);

  const cum20 = sum(last20, "total_billion");
  const cum60 = sum(last60, "total_billion");
  const kospi20 = sum(last20, "kospi_billion");
  const kosdaq20 = sum(last20, "kosdaq_billion");
  return {
    cum_20d_billion: Math.round(cum20 * 10) / 10,
    cum_60d_billion: Math.round(cum60 * 10) / 10,
    kospi_cum_20d_billion: Math.round(kospi20 * 10) / 10,
    kosdaq_cum_20d_billion: Math.round(kosdaq20 * 10) / 10,
    trend_20d: labelTrend(cum20, 1),
    trend_60d: labelTrend(cum60, 3),
    kospi_trend_20d: labelTrend(kospi20, 1),
    kosdaq_trend_20d: labelTrend(kosdaq20, 1),
  };
}

function summarizeSectors(daily: SectorDailyPoint[]): {
  cum_1d: ForeignFlowOutput["sectors"]["cum_1d"];
  cum_3d: ForeignFlowOutput["sectors"]["cum_3d"];
  cum_7d: ForeignFlowOutput["sectors"]["cum_7d"];
  cum_20d: ForeignFlowOutput["sectors"]["cum_20d"];
  cum_60d: ForeignFlowOutput["sectors"]["cum_60d"];
} {
  const allDates = Array.from(new Set(daily.map((p) => p.date))).sort();
  const dates1 = new Set(allDates.slice(-1));
  const dates3 = new Set(allDates.slice(-3));
  const dates7 = new Set(allDates.slice(-7));
  const dates20 = new Set(allDates.slice(-20));
  const dates60 = new Set(allDates.slice(-60));
  const sumBy = (datesSet: Set<string>) => {
    const m = new Map<string, number>();
    for (const p of daily) {
      if (!datesSet.has(p.date)) continue;
      m.set(p.sector, (m.get(p.sector) ?? 0) + p.net_buy_billion);
    }
    return Array.from(m.entries())
      .map(([sector, v]) => ({ sector, net_buy_billion: Math.round(v * 10) / 10 }))
      .sort((a, b) => b.net_buy_billion - a.net_buy_billion);
  };
  return {
    cum_1d: sumBy(dates1),
    cum_3d: sumBy(dates3),
    cum_7d: sumBy(dates7),
    cum_20d: sumBy(dates20),
    cum_60d: sumBy(dates60),
  };
}

// ── 메인 ──

async function main() {
  const kst = getKST();
  console.log(`[foreign-flow] start ${kst.iso} KST`);

  const existing = readExisting();
  let lastError: string | undefined;

  // 1) 시장 스냅샷
  const marketSnapshot = await fetchMarketSnapshot().catch((e) => {
    lastError = `market snapshot: ${String(e?.message ?? e)}`;
    return null;
  });
  if (marketSnapshot) {
    console.log(
      `[market] ${marketSnapshot.date}: KOSPI ${marketSnapshot.kospi_billion}억, KOSDAQ ${marketSnapshot.kosdaq_billion}억, 합계 ${marketSnapshot.total_billion}억`,
    );
  } else {
    lastError = (lastError ?? "") + " | market snapshot: empty";
    console.warn("[market] no snapshot today (skip)");
  }

  const mergedMarketDaily = mergeMarketDaily(existing?.market.daily ?? [], marketSnapshot);

  // 2) sector 집계
  const sectorResult = await fetchSectorDailyFromWatchlist().catch((e) => {
    lastError = (lastError ?? "") + ` | sector: ${String(e?.message ?? e)}`;
    return { daily: [] as SectorDailyPoint[], stockCount: 0, failedCount: 0 };
  });
  console.log(
    `[sector] fresh points: ${sectorResult.daily.length} (failed stocks: ${sectorResult.failedCount}/${sectorResult.stockCount})`,
  );

  const mergedSectorDaily = mergeSectorDaily(existing?.sectors.daily ?? [], sectorResult.daily);

  // 3) 요약
  const marketSummary = summarizeMarket(mergedMarketDaily);
  const sectorsSummary = summarizeSectors(mergedSectorDaily);

  const output: ForeignFlowOutput = {
    meta: {
      last_updated: kst.iso,
      source: "Naver Mobile",
      period_days: KEEP_DAYS,
      sector_basis: "watchlist",
      watchlist_stocks: sectorResult.stockCount,
      failed_stocks: sectorResult.failedCount,
      ...(lastError ? { last_error: lastError.trim() } : {}),
    },
    market: { daily: mergedMarketDaily, summary: marketSummary },
    sectors: {
      daily: mergedSectorDaily,
      cum_1d: sectorsSummary.cum_1d,
      cum_3d: sectorsSummary.cum_3d,
      cum_7d: sectorsSummary.cum_7d,
      cum_20d: sectorsSummary.cum_20d,
      cum_60d: sectorsSummary.cum_60d,
    },
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2), "utf-8");
  console.log(
    `[done] market.daily=${mergedMarketDaily.length}, sectors.daily=${mergedSectorDaily.length}, sectors.cum_20d=${sectorsSummary.cum_20d.length}`,
  );
  console.log(`[done] saved → ${OUTPUT_PATH}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
