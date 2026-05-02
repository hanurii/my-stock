/**
 * 외국인 자본 흐름 — 20영업일 백필 스크립트
 *
 * 데이터 소스: finance.naver.com/item/frgn.nhn (HTML 스크레이핑)
 *  - 종목 1페이지당 20영업일치 외인 순매수량 데이터 제공
 *  - dealTrendInfos(5영업일)로는 부족하므로 백필용으로 별도 운용
 *
 * 출력: public/data/foreign-flow.json (sector.daily 갱신)
 *
 * 매일 실행하지 않음. 데이터가 비어있거나 사용자가 명시적으로 백필을 요청할 때만 실행.
 *
 * 사용법: npx tsx scripts/backfill-foreign-flow.ts
 */
import fs from "fs";
import path from "path";

const FRGN_URL = (code: string, page: number) =>
  `https://finance.naver.com/item/frgn.nhn?code=${code}&page=${page}`;
// 시장(KOSPI/KOSDAQ)별 일별 투자자 매매동향 (단위: 백만원)
//   sosok=01 → KOSPI, sosok=02 → KOSDAQ
const INVESTOR_TREND_URL = (sosok: "01" | "02", bizdate: string, page: number) =>
  `https://finance.naver.com/sise/investorDealTrendDay.nhn?bizdate=${bizdate}&sosok=${sosok}&page=${page}`;
const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15";

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "public", "data");
const OUTPUT_PATH = path.join(DATA_DIR, "foreign-flow.json");
const WATCHLIST_PATH = path.join(DATA_DIR, "watchlist.json");

const KEEP_DAYS = 60;
const TARGET_PAGES = 1; // page 1당 20영업일

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

interface WatchlistStock {
  code: string;
  name: string;
  sector?: string;
}

interface FrgnRow {
  date: string;          // YYYY-MM-DD
  closePrice: number;    // 원
  foreignNet: number;    // 외인 순매수 주식수 (음수=매도)
}

// "+4,504,491" / "-1,400,484" → number
function parseSignedNumber(raw: string): number | null {
  const cleaned = raw.replace(/[,\s]/g, "");
  if (!/^[+-]?\d+(\.\d+)?$/.test(cleaned)) return null;
  return parseFloat(cleaned);
}

// "2026.04.27" → "2026-04-27"
function dotDateToISO(dotted: string): string {
  return dotted.replace(/\./g, "-");
}

async function fetchFrgnPage(code: string, page: number): Promise<FrgnRow[]> {
  const res = await fetch(FRGN_URL(code, page), {
    headers: { "User-Agent": UA, Referer: "https://finance.naver.com/" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const buf = await res.arrayBuffer();
  const html = new TextDecoder("euc-kr").decode(new Uint8Array(buf));

  const rowMatches = html.match(/<tr[^>]*>[\s\S]*?<\/tr>/g) ?? [];
  const rows: FrgnRow[] = [];
  for (const r of rowMatches) {
    const text = r
      .replace(/<[^>]+>/g, "|")
      .replace(/&nbsp;/g, " ")
      .replace(/[\s ]+/g, " ")
      .replace(/\|+/g, "|")
      .replace(/^\||\|$/g, "");
    const dateMatch = text.match(/(\d{4}\.\d{2}\.\d{2})/);
    if (!dateMatch) continue;
    const parts = text.split("|").map((p) => p.trim()).filter(Boolean);
    // 컬럼: 날짜, 종가, 등락구분, 등락폭, %변화, 거래량, 기관순매매, 외인순매매, 보유주식수, 보유율
    if (parts.length < 8) continue;
    const close = parseSignedNumber(parts[1]);
    const foreignNet = parseSignedNumber(parts[7]);
    if (close == null || foreignNet == null) continue;
    rows.push({
      date: dotDateToISO(dateMatch[1]),
      closePrice: close,
      foreignNet,
    });
  }
  return rows;
}

interface MarketDailyRow {
  date: string;            // YYYY-MM-DD
  foreignerMillion: number; // 백만원
}

// 시장별 (KOSPI/KOSDAQ) 일별 외인 순매수 백필 — page=1당 ~16영업일
async function fetchMarketBackfill(sosok: "01" | "02"): Promise<MarketDailyRow[]> {
  const today = new Date();
  const kst = new Date(today.getTime() + 9 * 60 * 60 * 1000);
  const bizdate = kst.toISOString().slice(0, 10).replace(/-/g, "");
  const all: MarketDailyRow[] = [];
  for (let p = 1; p <= 2; p++) {
    const res = await fetch(INVESTOR_TREND_URL(sosok, bizdate, p), {
      headers: { "User-Agent": UA, Referer: "https://finance.naver.com/" },
    });
    if (!res.ok) break;
    const buf = await res.arrayBuffer();
    const html = new TextDecoder("euc-kr").decode(new Uint8Array(buf));
    const rowMatches = html.match(/<tr[^>]*>[\s\S]*?<\/tr>/g) ?? [];
    let rowsThisPage = 0;
    for (const r of rowMatches) {
      const text = r
        .replace(/<[^>]+>/g, "|")
        .replace(/&nbsp;/g, " ")
        .replace(/[\s ]+/g, " ")
        .replace(/\|+/g, "|")
        .replace(/^\||\|$/g, "");
      const dateMatch = text.match(/(\d{2})\.(\d{2})\.(\d{2})/);
      if (!dateMatch) continue;
      const parts = text.split("|").map((s) => s.trim()).filter(Boolean);
      // 컬럼: 날짜, 개인, 외국인, 기관계, ...
      if (parts.length < 4) continue;
      const foreigner = parseSignedNumber(parts[2]);
      if (foreigner == null) continue;
      const yy = dateMatch[1];
      const mm = dateMatch[2];
      const dd = dateMatch[3];
      const fullYear = parseInt(yy, 10) >= 50 ? `19${yy}` : `20${yy}`;
      all.push({ date: `${fullYear}-${mm}-${dd}`, foreignerMillion: foreigner });
      rowsThisPage++;
    }
    if (rowsThisPage === 0) break;
    await sleep(120);
  }
  // dedupe
  const seen = new Set<string>();
  const out: MarketDailyRow[] = [];
  for (const r of all) {
    if (seen.has(r.date)) continue;
    seen.add(r.date);
    out.push(r);
  }
  return out.sort((a, b) => (a.date < b.date ? -1 : 1));
}

async function fetchStockBackfill(code: string): Promise<FrgnRow[]> {
  const all: FrgnRow[] = [];
  for (let p = 1; p <= TARGET_PAGES; p++) {
    const rows = await fetchFrgnPage(code, p);
    if (rows.length === 0) break;
    all.push(...rows);
    if (p < TARGET_PAGES) await sleep(80);
  }
  // dedupe by date
  const seen = new Set<string>();
  const unique: FrgnRow[] = [];
  for (const r of all) {
    if (seen.has(r.date)) continue;
    seen.add(r.date);
    unique.push(r);
  }
  return unique;
}

interface SectorDailyPoint {
  date: string;
  sector: string;
  net_buy_billion: number;
}

interface ForeignFlowOutput {
  meta: {
    last_updated: string;
    source: string;
    period_days: number;
    sector_basis: string;
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
    daily: SectorDailyPoint[];
    cum_1d: Array<{ sector: string; net_buy_billion: number }>;
    cum_3d: Array<{ sector: string; net_buy_billion: number }>;
    cum_7d: Array<{ sector: string; net_buy_billion: number }>;
    cum_20d: Array<{ sector: string; net_buy_billion: number }>;
    cum_60d: Array<{ sector: string; net_buy_billion: number }>;
  };
}

type TrendLabel = "강한 매수" | "매수 우위" | "보합" | "매도 우위" | "강한 매도";

function labelTrend(cumBillion: number, scale: 1 | 3): TrendLabel {
  const t1 = 1000 * scale;
  const t2 = 10000 * scale;
  if (cumBillion >= t2) return "강한 매수";
  if (cumBillion >= t1) return "매수 우위";
  if (cumBillion <= -t2) return "강한 매도";
  if (cumBillion <= -t1) return "매도 우위";
  return "보합";
}

function getKST(): { date: string; iso: string } {
  const now = new Date();
  const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  const date = kst.toISOString().split("T")[0];
  const hh = String(kst.getUTCHours()).padStart(2, "0");
  const mm = String(kst.getUTCMinutes()).padStart(2, "0");
  const ss = String(kst.getUTCSeconds()).padStart(2, "0");
  return { date, iso: `${date} ${hh}:${mm}:${ss}` };
}

function summarizeSectors(daily: SectorDailyPoint[]) {
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

function summarizeMarket(
  daily: ForeignFlowOutput["market"]["daily"],
): ForeignFlowOutput["market"]["summary"] {
  const last20 = daily.slice(-20);
  const last60 = daily.slice(-60);
  const sum = (
    arr: typeof daily,
    k: "kospi_billion" | "kosdaq_billion" | "total_billion",
  ) => arr.reduce((acc, p) => acc + p[k], 0);
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

async function main() {
  const kst = getKST();
  console.log(`[backfill-foreign-flow] start ${kst.iso} KST`);

  // 1) 시장(KOSPI/KOSDAQ) 일별 외인 순매수 백필
  console.log(`[backfill] fetching market daily (KOSPI + KOSDAQ)`);
  const [kospiRows, kosdaqRows] = await Promise.all([
    fetchMarketBackfill("01").catch((e) => {
      console.warn(`  [market] KOSPI failed:`, (e as Error).message);
      return [] as MarketDailyRow[];
    }),
    fetchMarketBackfill("02").catch((e) => {
      console.warn(`  [market] KOSDAQ failed:`, (e as Error).message);
      return [] as MarketDailyRow[];
    }),
  ]);
  const kospiMap = new Map(kospiRows.map((r) => [r.date, r.foreignerMillion]));
  const kosdaqMap = new Map(kosdaqRows.map((r) => [r.date, r.foreignerMillion]));
  const allMarketDates = Array.from(
    new Set([...kospiMap.keys(), ...kosdaqMap.keys()]),
  ).sort();
  const freshMarketDaily = allMarketDates.map((date) => {
    const k = (kospiMap.get(date) ?? 0) / 100; // 백만원 → 억원
    const q = (kosdaqMap.get(date) ?? 0) / 100;
    return {
      date,
      kospi_billion: Math.round(k * 10) / 10,
      kosdaq_billion: Math.round(q * 10) / 10,
      total_billion: Math.round((k + q) * 10) / 10,
    };
  });
  console.log(`[backfill] market daily: ${freshMarketDaily.length} unique days`);

  // 2) 워치리스트 sector 백필
  const wl = JSON.parse(fs.readFileSync(WATCHLIST_PATH, "utf-8")) as {
    stocks?: WatchlistStock[];
  };
  const stocks = (wl.stocks ?? []).filter((s) => s.code && s.sector);
  console.log(`[backfill] aggregating ${stocks.length} watchlist stocks (20영업일)`);

  // sector → date → 외인 순매수 누계 (백만원)
  const agg = new Map<string, Map<string, number>>();
  let failed = 0;

  for (let i = 0; i < stocks.length; i++) {
    const s = stocks[i];
    try {
      const rows = await fetchStockBackfill(s.code);
      if (rows.length === 0) {
        failed++;
        console.warn(`  [${i + 1}/${stocks.length}] ${s.code} ${s.name} — no rows`);
      } else {
        for (const r of rows) {
          // 외인 순매수 금액(원) = 주식수 × 종가 → ÷1,000,000 = 백만원
          const netMillion = (r.foreignNet * r.closePrice) / 1_000_000;
          const key = s.sector!;
          if (!agg.has(key)) agg.set(key, new Map());
          const dayMap = agg.get(key)!;
          dayMap.set(r.date, (dayMap.get(r.date) ?? 0) + netMillion);
        }
        if ((i + 1) % 10 === 0) {
          console.log(`  [${i + 1}/${stocks.length}] processed`);
        }
      }
    } catch (e) {
      failed++;
      console.warn(`  [${i + 1}/${stocks.length}] ${s.code} ${s.name} — ${(e as Error).message}`);
    }
    await sleep(150);
  }

  // 백만원 → 억원
  const freshDaily: SectorDailyPoint[] = [];
  for (const [sector, dayMap] of agg) {
    for (const [date, valMillion] of dayMap) {
      freshDaily.push({
        date,
        sector,
        net_buy_billion: Math.round((valMillion / 100) * 10) / 10,
      });
    }
  }
  console.log(`[backfill] fresh sector points: ${freshDaily.length}`);

  // 기존 파일 로드 + merge
  let existing: ForeignFlowOutput | null = null;
  try {
    existing = JSON.parse(fs.readFileSync(OUTPUT_PATH, "utf-8")) as ForeignFlowOutput;
  } catch {
    existing = null;
  }

  // sector daily merge: fresh (20일치)가 우선
  const mergedMap = new Map<string, SectorDailyPoint>();
  for (const p of existing?.sectors.daily ?? []) {
    mergedMap.set(`${p.date}|${p.sector}`, p);
  }
  for (const p of freshDaily) {
    mergedMap.set(`${p.date}|${p.sector}`, p);
  }
  const allDates = Array.from(new Set(Array.from(mergedMap.values()).map((p) => p.date))).sort();
  const keepSet = new Set(allDates.slice(-KEEP_DAYS));
  const mergedSectorDaily = Array.from(mergedMap.values())
    .filter((p) => keepSet.has(p.date))
    .sort((a, b) =>
      a.date === b.date ? a.sector.localeCompare(b.sector) : a.date < b.date ? -1 : 1,
    );

  const sectorsSummary = summarizeSectors(mergedSectorDaily);

  // market daily merge: fresh가 우선, 60일 윈도우
  const marketMap = new Map<string, ForeignFlowOutput["market"]["daily"][number]>();
  for (const p of existing?.market.daily ?? []) marketMap.set(p.date, p);
  for (const p of freshMarketDaily) marketMap.set(p.date, p);
  const marketDaily = Array.from(marketMap.values())
    .sort((a, b) => (a.date < b.date ? -1 : 1))
    .slice(-KEEP_DAYS);
  const marketSummary = summarizeMarket(marketDaily);

  const output: ForeignFlowOutput = {
    meta: {
      last_updated: kst.iso,
      source: existing?.meta.source ?? "Naver Mobile",
      period_days: KEEP_DAYS,
      sector_basis: "watchlist",
      watchlist_stocks: stocks.length,
      failed_stocks: failed,
    },
    market: { daily: marketDaily, summary: marketSummary },
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
  const uniqueDays = new Set(mergedSectorDaily.map((p) => p.date)).size;
  console.log(
    `[done] sectors.daily=${mergedSectorDaily.length}, unique days=${uniqueDays}, cum_20d=${sectorsSummary.cum_20d.length}, failed=${failed}/${stocks.length}`,
  );
  console.log(`[done] saved → ${OUTPUT_PATH}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
