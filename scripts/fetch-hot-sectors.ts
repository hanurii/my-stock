/**
 * 핫 섹터/테마 수집 스크립트
 *
 * 데이터 소스:
 *  - Naver chart API (api.stock.naver.com): 일봉 110일 + 주봉 30주 (가격·거래량)
 *  - Naver integration API (m.stock.naver.com): 5일 3주체 순매수 + 시총
 *  - Naver finance.naver.com/item/frgn.naver: 60일 외인·기관 일별 순매수 (HTML 스크래핑)
 *  - Yahoo Finance v8 chart: 글로벌 SPDR 섹터 ETF 1년치
 *  - 매일경제·한국경제 RSS: 키워드 멘션 카운트
 *
 * 출력: public/data/hot-sectors.json (요약) + public/data/hot-sectors-history.json (로테이션 스냅샷 누적)
 *
 * 사용법: npx tsx scripts/fetch-hot-sectors.ts
 */
import fs from "fs";
import path from "path";
import {
  GLOBAL_SECTOR_ETFS,
  KOREA_SECTOR_SEEDS,
  KOREA_THEME_SEEDS,
  SECTOR_ETFS,
  THEME_ETFS,
  SCORE_THRESHOLDS,
  type ETFCandidate,
} from "./hot-sectors-config";
import type {
  HotSectorsData,
  HotClassification,
  KoreanSector,
  KoreanTheme,
  GlobalSector,
  RotationSnapshot,
  ScoreBreakdown,
} from "../src/lib/hot-sectors";

// ── 설정 ──
const UA_MOBILE =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1";
const UA_DESKTOP =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36";
const REFERER_M = "https://m.stock.naver.com/";
const REFERER_FN = "https://finance.naver.com/";
const YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart";

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "public", "data");
const OUTPUT_PATH = path.join(DATA_DIR, "hot-sectors.json");
const HISTORY_PATH = path.join(DATA_DIR, "hot-sectors-history.json");
const NEWS_HISTORY_PATH = path.join(DATA_DIR, "hot-sectors-news-history.json");

const MK_RSS = ["https://www.mk.co.kr/rss/30100041", "https://www.mk.co.kr/rss/50200011"];
const HK_RSS = ["https://www.hankyung.com/feed/economy", "https://www.hankyung.com/feed/finance"];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// ── 유틸 ──
function getKST(): { date: string; iso: string } {
  const now = new Date();
  const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  const date = kst.toISOString().split("T")[0];
  const hh = String(kst.getUTCHours()).padStart(2, "0");
  const mm = String(kst.getUTCMinutes()).padStart(2, "0");
  const ss = String(kst.getUTCSeconds()).padStart(2, "0");
  return { date, iso: `${date} ${hh}:${mm}:${ss}` };
}

function parseSignedNumber(raw: string | undefined | null): number | null {
  if (raw == null) return null;
  const cleaned = String(raw).replace(/[,\s%]/g, "");
  if (!/^[+-]?\d+(\.\d+)?$/.test(cleaned)) return null;
  return parseFloat(cleaned);
}

function bizdateToISO(b: string): string {
  return `${b.slice(0, 4)}-${b.slice(4, 6)}-${b.slice(6, 8)}`;
}

// percentile rank: returns 0~100
function percentileRank(values: number[], target: number): number {
  if (values.length === 0) return 50;
  let count = 0;
  for (const v of values) if (v <= target) count++;
  return Math.round((count / values.length) * 100);
}

// ── Naver chart API: 일봉 N일 ──
interface DailyCandle {
  date: string;       // YYYY-MM-DD
  close: number;
  volume: number;     // 주식수
  tradingValueBillion: number;  // 거래대금 (억원, close × volume / 1e8)
}

async function fetchDailyCandles(code: string, count: number = 110): Promise<DailyCandle[] | null> {
  try {
    const url = `https://api.stock.naver.com/chart/domestic/item/${code}?periodType=dayCandle&count=${count}`;
    const res = await fetch(url, { headers: { "User-Agent": UA_MOBILE, Referer: REFERER_M } });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      priceInfos?: Array<{
        localDate?: string;
        closePrice?: number;
        accumulatedTradingVolume?: number;
      }>;
    };
    const arr = json.priceInfos;
    if (!arr || !Array.isArray(arr)) return null;
    const out: DailyCandle[] = [];
    for (const p of arr) {
      if (!p.localDate || p.closePrice == null) continue;
      const close = p.closePrice;
      const vol = p.accumulatedTradingVolume ?? 0;
      out.push({
        date: bizdateToISO(p.localDate),
        close,
        volume: vol,
        tradingValueBillion: (close * vol) / 1e8,
      });
    }
    return out.sort((a, b) => (a.date < b.date ? -1 : 1));
  } catch {
    return null;
  }
}

// ── Naver chart API: 주봉 30주 (6M 수익률용) ──
async function fetchWeeklyCandles(code: string, count: number = 30): Promise<DailyCandle[] | null> {
  try {
    const url = `https://api.stock.naver.com/chart/domestic/item/${code}?periodType=weekCandle&count=${count}`;
    const res = await fetch(url, { headers: { "User-Agent": UA_MOBILE, Referer: REFERER_M } });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      priceInfos?: Array<{ localDate?: string; closePrice?: number; accumulatedTradingVolume?: number }>;
    };
    const arr = json.priceInfos;
    if (!arr) return null;
    return arr
      .filter((p) => p.localDate && p.closePrice != null)
      .map((p) => ({
        date: bizdateToISO(p.localDate!),
        close: p.closePrice!,
        volume: p.accumulatedTradingVolume ?? 0,
        tradingValueBillion: (p.closePrice! * (p.accumulatedTradingVolume ?? 0)) / 1e8,
      }))
      .sort((a, b) => (a.date < b.date ? -1 : 1));
  } catch {
    return null;
  }
}

// ── Naver integration API: 시총 + 5일 3주체 순매수 (수량) + 종목명 ──
interface IntegrationData {
  marketSumBillion: number | null;
  stockName: string;
  recent5d: Array<{
    date: string;
    foreignerQuant: number;
    organQuant: number;
    individualQuant: number;
    closePrice: number;
  }>;
}

async function fetchIntegration(code: string): Promise<IntegrationData | null> {
  try {
    const url = `https://m.stock.naver.com/api/stock/${code}/integration`;
    const res = await fetch(url, { headers: { "User-Agent": UA_MOBILE, Referer: REFERER_M } });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      stockName?: string;
      totalInfos?: Array<{ code?: string; key?: string; value?: string }>;
      dealTrendInfos?: Array<{
        bizdate?: string;
        foreignerPureBuyQuant?: string;
        organPureBuyQuant?: string;
        individualPureBuyQuant?: string;
        closePrice?: string;
      }>;
    };

    // 시총 추출 - totalInfos에서 "marketValue" 또는 한글 라벨 검색
    let marketSumBillion: number | null = null;
    if (json.totalInfos) {
      for (const t of json.totalInfos) {
        if (t.code === "marketValue" || t.key === "시가총액") {
          const v = t.value;
          if (v) {
            // "419조 5,840억" / "1조 234억" / "2,345억" 형식 파싱
            const m = String(v).match(/(?:(\d+(?:,\d+)*)\s*조)?\s*(\d+(?:,\d+)*)?\s*억/);
            if (m) {
              const jo = m[1] ? parseInt(m[1].replace(/,/g, ""), 10) : 0;
              const eok = m[2] ? parseInt(m[2].replace(/,/g, ""), 10) : 0;
              marketSumBillion = jo * 10000 + eok;
            }
          }
          break;
        }
      }
    }

    const recent5d: IntegrationData["recent5d"] = [];
    for (const it of json.dealTrendInfos ?? []) {
      if (!it.bizdate) continue;
      const f = parseSignedNumber(it.foreignerPureBuyQuant ?? null) ?? 0;
      const o = parseSignedNumber(it.organPureBuyQuant ?? null) ?? 0;
      const i = parseSignedNumber(it.individualPureBuyQuant ?? null) ?? 0;
      const cp = parseSignedNumber(it.closePrice ?? null) ?? 0;
      recent5d.push({
        date: bizdateToISO(it.bizdate),
        foreignerQuant: f,
        organQuant: o,
        individualQuant: i,
        closePrice: cp,
      });
    }
    return { marketSumBillion, stockName: json.stockName ?? code, recent5d };
  } catch {
    return null;
  }
}

// ── Naver finance.naver.com/item/frgn.naver: 60일 외인+기관 일별 순매수 (HTML 스크래핑) ──
//
// 페이지당 20일치, 3페이지 = 60일.
// 컬럼: 날짜 | 종가 | 등락 | 등락률 | 거래량 | 기관순매매(주식수) | 외국인순매매(주식수) | 외인보유주식수 | 외인보유율
// 개인 순매수 = -(외국인 + 기관) 추정 (전체 순매수 합 = 0 가정)
interface InvestorDayPoint {
  date: string;
  foreignerQuant: number;   // 주식수 (음수 가능)
  organQuant: number;       // 주식수
  closePrice: number;
}

async function fetchFrgnPage(code: string, page: number): Promise<InvestorDayPoint[]> {
  const url = `https://finance.naver.com/item/frgn.naver?code=${code}&page=${page}`;
  const res = await fetch(url, { headers: { "User-Agent": UA_DESKTOP, Referer: REFERER_FN } });
  if (!res.ok) return [];
  const buf = Buffer.from(await res.arrayBuffer());
  const html = new TextDecoder("euc-kr").decode(buf);

  // 행 단위로 매칭: "2026.05.04...232,500...[등락]...[등락률]...[거래량]...+4,335,045 (기관)...+5,214,979 (외인)..."
  const rows = html.match(/(2026|2025|2024)\.\d{2}\.\d{2}[\s\S]{0,1500}?<\/tr>/g);
  if (!rows) return [];
  const out: InvestorDayPoint[] = [];
  for (const row of rows) {
    const dateMatch = row.match(/(2026|2025|2024)\.(\d{2})\.(\d{2})/);
    if (!dateMatch) continue;
    const date = `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`;

    // 모든 숫자 추출 (콤마+부호+퍼센트 포함)
    // 행 구조: 종가, 등락폭, 등락%, 거래량, 기관순매매, 외인순매매, 외인보유, 외인보유율
    const numbers = row.match(/<span[^>]*>\s*([+-]?[\d,]+(?:\.\d+)?%?)\s*<\/span>/g);
    if (!numbers || numbers.length < 7) continue;

    const cleaned = numbers
      .map((n) => n.replace(/<[^>]+>/g, "").trim())
      .filter((n) => n.length > 0);

    // 인덱스: 0=종가, 1=등락, 2=등락%, 3=거래량, 4=기관순매매, 5=외인순매매, 6=외인보유, 7=외인보유%
    if (cleaned.length < 6) continue;
    const closePrice = parseSignedNumber(cleaned[0]);
    const organQuant = parseSignedNumber(cleaned[4]);
    const foreignerQuant = parseSignedNumber(cleaned[5]);
    if (closePrice == null || organQuant == null || foreignerQuant == null) continue;
    out.push({ date, foreignerQuant, organQuant, closePrice });
  }
  return out;
}

async function fetchInvestorHistory(code: string, pages: number = 3): Promise<InvestorDayPoint[]> {
  const all: InvestorDayPoint[] = [];
  for (let p = 1; p <= pages; p++) {
    try {
      const rows = await fetchFrgnPage(code, p);
      all.push(...rows);
    } catch {
      // skip
    }
    await sleep(150);
  }
  // dedupe by date
  const map = new Map<string, InvestorDayPoint>();
  for (const r of all) map.set(r.date, r);
  return Array.from(map.values()).sort((a, b) => (a.date < b.date ? -1 : 1));
}

// ── Yahoo Finance: 글로벌 ETF ──
interface YahooSeries {
  closes: number[];
  timestamps: number[];
}

async function fetchYahooSeries(symbol: string): Promise<YahooSeries | null> {
  try {
    const url = `${YAHOO_API}/${encodeURIComponent(symbol)}?range=1y&interval=1d`;
    const res = await fetch(url, { headers: { "User-Agent": UA_DESKTOP } });
    if (!res.ok) return null;
    const json = await res.json();
    const r = json.chart?.result?.[0];
    if (!r) return null;
    const closes = (r.indicators?.quote?.[0]?.close ?? []).filter(
      (x: number | null): x is number => x != null,
    );
    const timestamps = r.timestamp ?? [];
    return { closes, timestamps };
  } catch {
    return null;
  }
}

function calcReturn(closes: number[], lookback: number): number | null {
  if (closes.length < lookback + 1) return null;
  const last = closes[closes.length - 1];
  const old = closes[closes.length - 1 - lookback];
  if (!last || !old) return null;
  return ((last / old - 1) * 100);
}

function calcReturnFromIdx(closes: number[], idx: number): number | null {
  if (closes.length < 2 || idx < 0 || idx >= closes.length) return null;
  const last = closes[closes.length - 1];
  const old = closes[idx];
  if (!last || !old) return null;
  return ((last / old - 1) * 100);
}

// ── 종목 단위 메트릭 산출 ──
interface StockMetrics {
  code: string;
  name: string;
  marketCapBillion: number;
  perf_5d: number | null;
  perf_20d: number | null;
  perf_60d: number | null;
  perf_3m: number | null;
  perf_6m: number | null;
  // 60일 누적 순매수 금액 (억원, 일별 수량 × 종가)
  foreign_60d_billion: number;
  organ_60d_billion: number;
  individual_60d_billion: number;
  foreign_5d_billion: number;
  organ_5d_billion: number;
  individual_5d_billion: number;
  // 거래대금
  volume_recent_60d_billion: number;
  volume_prev_60d_billion: number;
  volume_5d_billion: number;
}

async function fetchStockMetrics(code: string): Promise<StockMetrics | null> {
  // 병렬 호출
  const [daily, weekly, integration, investorHist] = await Promise.all([
    fetchDailyCandles(code, 110),
    fetchWeeklyCandles(code, 30),
    fetchIntegration(code),
    fetchInvestorHistory(code, 3),
  ]);
  if (!daily || daily.length < 21 || !integration) return null;

  const closes = daily.map((d) => d.close);
  const perf_5d = calcReturn(closes, 5);
  const perf_20d = calcReturn(closes, 20);
  const perf_60d = calcReturn(closes, 60);
  // 3M ~ 63 영업일
  const perf_3m = calcReturn(closes, Math.min(63, closes.length - 1));
  // 6M = 주봉 26주 (6개월) 또는 일봉 oldest-to-current fallback
  let perf_6m: number | null = null;
  if (weekly && weekly.length >= 27) {
    const wcloses = weekly.map((w) => w.close);
    perf_6m = calcReturnFromIdx(wcloses, wcloses.length - 27);
  } else if (closes.length > 60) {
    // fallback: oldest available daily (~5.5M)
    perf_6m = calcReturnFromIdx(closes, 0);
  }

  // 60일 누적 3주체 순매수 금액 (억원)
  // investorHist에 있는 외인+기관 일별 수량 × 종가
  // 개인 = -(외인 + 기관) 추정
  let foreign_60d = 0;
  let organ_60d = 0;
  let individual_60d = 0;
  for (const day of investorHist.slice(-60)) {
    const f = (day.foreignerQuant * day.closePrice) / 1e8;
    const o = (day.organQuant * day.closePrice) / 1e8;
    foreign_60d += f;
    organ_60d += o;
    individual_60d += -(f + o);
  }
  // 5일 누적: integration의 dealTrendInfos
  let foreign_5d = 0;
  let organ_5d = 0;
  let individual_5d = 0;
  for (const day of integration.recent5d) {
    foreign_5d += (day.foreignerQuant * day.closePrice) / 1e8;
    organ_5d += (day.organQuant * day.closePrice) / 1e8;
    individual_5d += (day.individualQuant * day.closePrice) / 1e8;
  }

  // 거래대금 (억원)
  const volume_5d = daily.slice(-5).reduce((s, d) => s + d.tradingValueBillion, 0);
  const volume_recent_60 = daily.slice(-60).reduce((s, d) => s + d.tradingValueBillion, 0);
  // 직전 60D는 daily가 110일이라 [0..50] 구간 (50일치만 가능하면 그 만큼)
  const prevSlice = daily.slice(0, Math.max(0, daily.length - 60));
  const volume_prev_60 =
    prevSlice.length > 0
      ? (prevSlice.reduce((s, d) => s + d.tradingValueBillion, 0) / prevSlice.length) * 60
      : 0;

  return {
    code,
    name: integration.stockName,
    marketCapBillion: integration.marketSumBillion ?? 0,
    perf_5d,
    perf_20d,
    perf_60d,
    perf_3m,
    perf_6m,
    foreign_60d_billion: foreign_60d,
    organ_60d_billion: organ_60d,
    individual_60d_billion: individual_60d,
    foreign_5d_billion: foreign_5d,
    organ_5d_billion: organ_5d,
    individual_5d_billion: individual_5d,
    volume_recent_60d_billion: volume_recent_60,
    volume_prev_60d_billion: volume_prev_60,
    volume_5d_billion: volume_5d,
  };
}

// ── 섹터/테마 시총가중 집계 ──
interface AggregateMetrics {
  perf_5d: number | null;
  perf_20d: number | null;
  perf_60d: number | null;
  perf_3m: number | null;
  perf_6m: number | null;
  foreign_60d_billion: number;
  organ_60d_billion: number;
  individual_60d_billion: number;
  foreign_5d_billion: number;
  organ_5d_billion: number;
  individual_5d_billion: number;
  volume_recent_60d_billion: number;
  volume_prev_60d_billion: number;
  volume_5d_billion: number;
  three_investor_alignment_60d: 0 | 1 | 2 | 3;
  stock_count: number;
  top_stocks: Array<{ code: string; name: string; perf_5d: number | null; perf_60d: number | null }>;
}

function aggregateStocks(stocks: StockMetrics[]): AggregateMetrics {
  if (stocks.length === 0) {
    return {
      perf_5d: null, perf_20d: null, perf_60d: null, perf_3m: null, perf_6m: null,
      foreign_60d_billion: 0, organ_60d_billion: 0, individual_60d_billion: 0,
      foreign_5d_billion: 0, organ_5d_billion: 0, individual_5d_billion: 0,
      volume_recent_60d_billion: 0, volume_prev_60d_billion: 0, volume_5d_billion: 0,
      three_investor_alignment_60d: 0, stock_count: 0, top_stocks: [],
    };
  }
  const totalCap = stocks.reduce((s, x) => s + x.marketCapBillion, 0) || 1;
  const w = (k: keyof StockMetrics): number | null => {
    let sum = 0;
    let weight = 0;
    for (const x of stocks) {
      const v = x[k] as number | null;
      if (v == null) continue;
      sum += v * x.marketCapBillion;
      weight += x.marketCapBillion;
    }
    return weight > 0 ? sum / weight : null;
  };

  const sum = (k: keyof StockMetrics): number =>
    stocks.reduce((s, x) => s + ((x[k] as number) || 0), 0);

  const foreign_60d = sum("foreign_60d_billion");
  const organ_60d = sum("organ_60d_billion");
  const individual_60d = sum("individual_60d_billion");
  const alignment = (
    (foreign_60d > 0 ? 1 : 0) + (organ_60d > 0 ? 1 : 0) + (individual_60d > 0 ? 1 : 0)
  ) as 0 | 1 | 2 | 3;

  // top stocks by 60D perf
  const top = [...stocks]
    .filter((s) => s.perf_60d != null)
    .sort((a, b) => (b.perf_60d ?? 0) - (a.perf_60d ?? 0))
    .slice(0, 5)
    .map((s) => ({ code: s.code, name: s.name, perf_5d: s.perf_5d, perf_60d: s.perf_60d }));

  return {
    perf_5d: w("perf_5d"),
    perf_20d: w("perf_20d"),
    perf_60d: w("perf_60d"),
    perf_3m: w("perf_3m"),
    perf_6m: w("perf_6m"),
    foreign_60d_billion: Math.round(foreign_60d * 10) / 10,
    organ_60d_billion: Math.round(organ_60d * 10) / 10,
    individual_60d_billion: Math.round(individual_60d * 10) / 10,
    foreign_5d_billion: Math.round(sum("foreign_5d_billion") * 10) / 10,
    organ_5d_billion: Math.round(sum("organ_5d_billion") * 10) / 10,
    individual_5d_billion: Math.round(sum("individual_5d_billion") * 10) / 10,
    volume_recent_60d_billion: Math.round(sum("volume_recent_60d_billion")),
    volume_prev_60d_billion: Math.round(sum("volume_prev_60d_billion")),
    volume_5d_billion: Math.round(sum("volume_5d_billion")),
    three_investor_alignment_60d: alignment,
    stock_count: stocks.length,
    top_stocks: top,
  };
}

// ── RSS 뉴스 키워드 멘션 ──
interface NewsItem {
  title: string;
  date: Date;
}

async function fetchAllNews(daysBack: number = 14): Promise<NewsItem[]> {
  const cutoff = new Date(Date.now() - daysBack * 24 * 3600 * 1000);
  const items: NewsItem[] = [];
  for (const url of [...MK_RSS, ...HK_RSS]) {
    try {
      const res = await fetch(url, { headers: { "User-Agent": UA_DESKTOP } });
      if (!res.ok) continue;
      const xml = await res.text();
      const its = xml.match(/<item>[\s\S]*?<\/item>/g) ?? [];
      for (const it of its) {
        const title =
          it.match(/<title>[\s\S]*?CDATA\[(.*?)\]\]/)?.[1] ||
          it.match(/<title>(.*?)<\/title>/)?.[1] || "";
        const dateStr = it.match(/<pubDate>(.*?)<\/pubDate>/)?.[1] || "";
        const d = new Date(dateStr);
        if (isNaN(d.getTime()) || d < cutoff) continue;
        items.push({ title, date: d });
      }
      await sleep(300);
    } catch {
      continue;
    }
  }
  return items;
}

function countMentionsToday(news: NewsItem[], keywords: string[]): number {
  if (news.length === 0 || keywords.length === 0) return 0;
  const re = new RegExp(keywords.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "i");
  let today = 0;
  const dayMs = 24 * 3600 * 1000;
  const now = Date.now();
  for (const n of news) {
    if (!re.test(n.title)) continue;
    if (now - n.date.getTime() <= dayMs) today++;
  }
  return today;
}

interface NewsHistoryFile {
  // key: name(섹터/테마), value: { date(YYYY-MM-DD): mention_count }
  series: Record<string, Record<string, number>>;
  meta: { last_updated: string; days_kept: number };
}

function loadNewsHistory(): NewsHistoryFile {
  try {
    return JSON.parse(fs.readFileSync(NEWS_HISTORY_PATH, "utf-8")) as NewsHistoryFile;
  } catch {
    return { series: {}, meta: { last_updated: "", days_kept: 30 } };
  }
}

function saveNewsHistory(file: NewsHistoryFile, today: string, kstIso: string): void {
  // 30일 이상은 컷
  const cutoff = new Date(Date.now() - 30 * 24 * 3600 * 1000)
    .toISOString().split("T")[0];
  for (const name of Object.keys(file.series)) {
    const m = file.series[name];
    for (const d of Object.keys(m)) if (d < cutoff) delete m[d];
  }
  file.meta.last_updated = kstIso;
  fs.writeFileSync(NEWS_HISTORY_PATH, JSON.stringify(file, null, 2), "utf-8");
}

// 현재 시점 5D vs 직전 5D 멘션 변화율. 누적된 시계열 기반. null이면 비교 불가.
function newsMentionChange5d(history: Record<string, number>): number | null {
  const today = new Date().toISOString().split("T")[0];
  const dayMs = 24 * 3600 * 1000;
  const todayTs = new Date(today).getTime();

  let recent = 0;
  let prev = 0;
  let recentDays = 0;
  let prevDays = 0;
  for (const [d, count] of Object.entries(history)) {
    const dt = new Date(d).getTime();
    const ageDays = Math.round((todayTs - dt) / dayMs);
    if (ageDays >= 0 && ageDays <= 4) {
      recent += count;
      recentDays++;
    } else if (ageDays >= 5 && ageDays <= 9) {
      prev += count;
      prevDays++;
    }
  }
  // 직전 5일치 데이터가 3일 미만이면 비교 불가
  if (prevDays < 3) return null;
  if (prev === 0) return recent === 0 ? 0 : null;
  return Math.round(((recent - prev) / prev) * 100);
}

// ── 점수 계산 ──
function computeScores(
  agg: AggregateMetrics,
  newsChange5d: number | null,
  allReturns60d: number[],
  allVolumeSpikes5d: number[],
  allReturns5d: number[],
  allReturns20d: number[],
): {
  realHotScore: number;
  shortMomentumScore: number;
  breakdown: ScoreBreakdown;
  fakeSignals: string[];
  classification: HotClassification;
  volume_sustain_ratio: number | null;
  volume_5d_spike_ratio: number | null;
} {
  // Trend Consistency: 20D, 60D, 3M, 6M 양수 개수 (4개 중)
  const trendCount = [agg.perf_20d, agg.perf_60d, agg.perf_3m, agg.perf_6m]
    .filter((v) => v != null && v > 0).length;
  const trendScore = (trendCount / 4) * 100;

  // Three investor: alignment 0~3 → 0/40/70/100
  const triScore = { 0: 0, 1: 40, 2: 70, 3: 100 }[agg.three_investor_alignment_60d];

  // Sustained volume
  const sustainRatio =
    agg.volume_prev_60d_billion > 0
      ? agg.volume_recent_60d_billion / agg.volume_prev_60d_billion
      : null;
  const sustainScore = sustainRatio == null
    ? 50
    : sustainRatio >= SCORE_THRESHOLDS.VOLUME_SUSTAIN_HIGH
      ? 100
      : sustainRatio >= 1.0
        ? 50 + ((sustainRatio - 1) / 0.3) * 50
        : Math.max(0, sustainRatio * 50);

  // Return 60D percentile
  const ret60dPct =
    agg.perf_60d == null ? 50 : percentileRank(allReturns60d, agg.perf_60d);

  // News-to-price decoupling
  // 뉴스 거의 없는데 가격 양호하면 ↑, 뉴스만 폭증인데 가격은 미미하면 ↓
  // newsChange5d가 null이면 데이터 부족 → 중립 50점
  let decoupleScore = 50;
  const p60 = agg.perf_60d ?? 0;
  if (newsChange5d != null) {
    if (newsChange5d < 50 && p60 > 5) decoupleScore = 90;
    else if (newsChange5d < 100 && p60 > 0) decoupleScore = 70;
    else if (newsChange5d > 200 && Math.abs(p60) < 5) decoupleScore = 10;
    else decoupleScore = 50;
  }

  const realHotScore = Math.round(
    0.30 * trendScore +
    0.25 * triScore +
    0.20 * sustainScore +
    0.15 * ret60dPct +
    0.10 * decoupleScore,
  );

  // 거래대금 5D 스파이크 비율 (직전 60D 일평균 대비)
  const spike5d =
    agg.volume_recent_60d_billion > 0 && agg.volume_5d_billion > 0
      ? (agg.volume_5d_billion / 5) / (agg.volume_recent_60d_billion / 60)
      : null;
  const spikePct = spike5d == null ? 50 : percentileRank(allVolumeSpikes5d, spike5d);

  // Short Momentum
  const ret5dPct = agg.perf_5d == null ? 50 : percentileRank(allReturns5d, agg.perf_5d);
  const ret20dPct = agg.perf_20d == null ? 50 : percentileRank(allReturns20d, agg.perf_20d);
  const shortMomentumScore = Math.round(0.5 * ret5dPct + 0.3 * ret20dPct + 0.2 * spikePct);

  // FakeHot 시그널
  const fake: string[] = [];
  // 단기 스파이크
  if (
    (agg.perf_5d ?? 0) >= SCORE_THRESHOLDS.FAKE_SHORT_SPIKE_PCT &&
    Math.abs(agg.perf_60d ?? 0) <= SCORE_THRESHOLDS.FAKE_60D_FLAT_PCT
  ) {
    fake.push("단기 스파이크");
  }
  // 개인 단독 주도
  if (agg.foreign_60d_billion < 0 && agg.individual_60d_billion > 0) {
    fake.push("개인 단독 주도");
  }
  // 거래대금 단발성 폭증
  if (
    spike5d != null &&
    sustainRatio != null &&
    spike5d >= SCORE_THRESHOLDS.FAKE_VOLUME_5D_RATIO &&
    sustainRatio < SCORE_THRESHOLDS.FAKE_VOLUME_20D_RATIO
  ) {
    fake.push("거래대금 단발성 폭증");
  }
  // 뉴스 디커플링 (변화율이 측정 가능할 때만)
  if (
    newsChange5d != null &&
    newsChange5d >= SCORE_THRESHOLDS.FAKE_NEWS_SURGE_PCT &&
    Math.abs(agg.perf_60d ?? 0) < SCORE_THRESHOLDS.FAKE_NEWS_DECOUPLE_PRICE_PCT
  ) {
    fake.push("뉴스 디커플링");
  }

  // 분류
  let classification: HotClassification = "neutral";
  if (realHotScore >= SCORE_THRESHOLDS.REAL_HOT && fake.length === 0 && shortMomentumScore >= 50) {
    classification = "real_hot";
  } else if (realHotScore >= SCORE_THRESHOLDS.REAL_HOT && fake.length <= 2) {
    classification = "real_hot_warning";
  } else if (
    shortMomentumScore >= SCORE_THRESHOLDS.EMERGING_SHORT_MOMENTUM &&
    realHotScore < SCORE_THRESHOLDS.REAL_HOT &&
    agg.three_investor_alignment_60d >= 2 &&
    (agg.perf_60d ?? 0) >= -5
  ) {
    classification = "emerging";
  } else if (
    shortMomentumScore >= SCORE_THRESHOLDS.EMERGING_SHORT_MOMENTUM &&
    realHotScore < 50 &&
    agg.foreign_60d_billion < 0
  ) {
    classification = "short_burst";
  } else if (
    (agg.perf_6m ?? 0) >= SCORE_THRESHOLDS.COOLING_6M &&
    (agg.perf_20d ?? 0) <= 0 &&
    agg.foreign_5d_billion < 0
  ) {
    classification = "cooling";
  } else if (
    realHotScore >= SCORE_THRESHOLDS.IN_PROGRESS_MIN &&
    fake.length <= 1
  ) {
    classification = "in_progress";
  } else if (fake.length >= 2) {
    classification = "fake_hot";
  }

  return {
    realHotScore,
    shortMomentumScore,
    breakdown: {
      trend_consistency: Math.round(trendScore),
      three_investor: triScore,
      sustained_volume: Math.round(sustainScore),
      return_60d_pct: ret60dPct,
      news_decoupling: decoupleScore,
    },
    fakeSignals: fake,
    classification,
    volume_sustain_ratio: sustainRatio == null ? null : Math.round(sustainRatio * 100) / 100,
    volume_5d_spike_ratio: spike5d == null ? null : Math.round(spike5d * 100) / 100,
  };
}

// ── ETF 코드 검증 (Naver integration로 실재 확인) ──
async function verifyETFs(etfs: ETFCandidate[]): Promise<ETFCandidate[]> {
  const verified: ETFCandidate[] = [];
  for (const etf of etfs) {
    try {
      const res = await fetch(`https://m.stock.naver.com/api/stock/${etf.code}/integration`, {
        headers: { "User-Agent": UA_MOBILE, Referer: REFERER_M },
      });
      if (res.ok) {
        const json = await res.json();
        if (json && json.stockName) verified.push({ ...etf, name: json.stockName });
      }
    } catch {
      // skip
    }
    await sleep(80);
  }
  return verified;
}

// ── 메인 ──
async function main() {
  const kst = getKST();
  console.log(`[hot-sectors] start ${kst.iso} KST`);

  // 1) 모든 고유 종목 코드 수집 (섹터 + 테마)
  const allCodesSet = new Set<string>();
  for (const s of KOREA_SECTOR_SEEDS) for (const c of s.stock_codes) allCodesSet.add(c);
  for (const t of KOREA_THEME_SEEDS) for (const c of t.stock_codes) allCodesSet.add(c);
  const allCodes = Array.from(allCodesSet);
  console.log(`[stocks] unique codes: ${allCodes.length}`);

  // 2) 종목 메트릭 병렬 수집 (10개씩 배치)
  const stockMap = new Map<string, StockMetrics>();
  let failed = 0;
  const batchSize = 8;
  for (let i = 0; i < allCodes.length; i += batchSize) {
    const batch = allCodes.slice(i, i + batchSize);
    const results = await Promise.all(batch.map((code) => fetchStockMetrics(code).catch(() => null)));
    results.forEach((r, idx) => {
      if (r) stockMap.set(batch[idx], r);
      else {
        failed++;
        console.warn(`  fail: ${batch[idx]}`);
      }
    });
    console.log(`  [${Math.min(i + batchSize, allCodes.length)}/${allCodes.length}] done`);
    await sleep(200);
  }

  // 3) 글로벌 ETF 메트릭
  console.log(`[global] fetching ${GLOBAL_SECTOR_ETFS.length + 1} ETFs`);
  const globalSeries = new Map<string, YahooSeries>();
  for (const e of GLOBAL_SECTOR_ETFS) {
    const s = await fetchYahooSeries(e.ticker);
    if (s) globalSeries.set(e.ticker, s);
    await sleep(150);
  }
  const spy = await fetchYahooSeries("SPY");

  // 4) 뉴스 RSS + 누적 시계열 갱신
  console.log(`[news] fetching RSS`);
  const news = await fetchAllNews(14).catch(() => []);
  console.log(`  collected ${news.length} items`);
  const newsHistory = loadNewsHistory();
  for (const seed of KOREA_SECTOR_SEEDS) {
    const today = countMentionsToday(news, seed.news_keywords);
    if (!newsHistory.series[`sector:${seed.wics_name}`]) {
      newsHistory.series[`sector:${seed.wics_name}`] = {};
    }
    newsHistory.series[`sector:${seed.wics_name}`][kst.date] = today;
  }
  for (const seed of KOREA_THEME_SEEDS) {
    const today = countMentionsToday(news, seed.news_keywords);
    if (!newsHistory.series[`theme:${seed.name}`]) {
      newsHistory.series[`theme:${seed.name}`] = {};
    }
    newsHistory.series[`theme:${seed.name}`][kst.date] = today;
  }
  saveNewsHistory(newsHistory, kst.date, kst.iso);

  // 5) 섹터 집계 (1차 — alignment 등 계산)
  const sectorAggs: Array<{ seed: typeof KOREA_SECTOR_SEEDS[number]; agg: AggregateMetrics }> = [];
  for (const seed of KOREA_SECTOR_SEEDS) {
    const stocks = seed.stock_codes.map((c) => stockMap.get(c)).filter((x): x is StockMetrics => !!x);
    sectorAggs.push({ seed, agg: aggregateStocks(stocks) });
  }
  const themeAggs: Array<{ seed: typeof KOREA_THEME_SEEDS[number]; agg: AggregateMetrics }> = [];
  for (const seed of KOREA_THEME_SEEDS) {
    const stocks = seed.stock_codes.map((c) => stockMap.get(c)).filter((x): x is StockMetrics => !!x);
    themeAggs.push({ seed, agg: aggregateStocks(stocks) });
  }

  // 6) percentile 분포 풀 만들기 (모든 섹터+테마 기준)
  const allReturns60d = [...sectorAggs, ...themeAggs]
    .map((x) => x.agg.perf_60d)
    .filter((v): v is number => v != null);
  const allReturns20d = [...sectorAggs, ...themeAggs]
    .map((x) => x.agg.perf_20d)
    .filter((v): v is number => v != null);
  const allReturns5d = [...sectorAggs, ...themeAggs]
    .map((x) => x.agg.perf_5d)
    .filter((v): v is number => v != null);
  const allVolumeSpikes5d = [...sectorAggs, ...themeAggs]
    .map((x) => {
      const v = x.agg;
      return v.volume_recent_60d_billion > 0 && v.volume_5d_billion > 0
        ? (v.volume_5d_billion / 5) / (v.volume_recent_60d_billion / 60)
        : null;
    })
    .filter((v): v is number => v != null);

  // 7) 섹터/테마 점수 + 분류
  const koreaSectors: KoreanSector[] = [];
  for (const { seed, agg } of sectorAggs) {
    const sectorHist = newsHistory.series[`sector:${seed.wics_name}`] ?? {};
    const newsChange = newsMentionChange5d(sectorHist);
    const newsToday = sectorHist[kst.date] ?? 0;
    const sc = computeScores(agg, newsChange, allReturns60d, allVolumeSpikes5d, allReturns5d, allReturns20d);
    koreaSectors.push({
      wics_name: seed.wics_name,
      gics_mapped: seed.gics_mapped,
      stock_count: agg.stock_count,
      perf_5d: agg.perf_5d == null ? null : Math.round(agg.perf_5d * 10) / 10,
      perf_20d: agg.perf_20d == null ? null : Math.round(agg.perf_20d * 10) / 10,
      perf_60d: agg.perf_60d == null ? null : Math.round(agg.perf_60d * 10) / 10,
      perf_3m: agg.perf_3m == null ? null : Math.round(agg.perf_3m * 10) / 10,
      perf_6m: agg.perf_6m == null ? null : Math.round(agg.perf_6m * 10) / 10,
      foreign_60d_billion: agg.foreign_60d_billion,
      organ_60d_billion: agg.organ_60d_billion,
      individual_60d_billion: agg.individual_60d_billion,
      foreign_5d_billion: agg.foreign_5d_billion,
      organ_5d_billion: agg.organ_5d_billion,
      individual_5d_billion: agg.individual_5d_billion,
      three_investor_alignment_60d: agg.three_investor_alignment_60d,
      volume_recent_60d_billion: agg.volume_recent_60d_billion,
      volume_prev_60d_billion: agg.volume_prev_60d_billion,
      volume_sustain_ratio: sc.volume_sustain_ratio,
      volume_5d_spike_ratio: sc.volume_5d_spike_ratio,
      news_mention_change_5d: newsChange,
      news_mention_today: newsToday,
      real_hot_score: sc.realHotScore,
      short_momentum_score: sc.shortMomentumScore,
      score_breakdown: sc.breakdown,
      fake_hot_signals: sc.fakeSignals,
      classification: sc.classification,
      etf_options: [], // 아래에서 verify
      top_stocks: agg.top_stocks,
    });
  }

  const koreaThemes: KoreanTheme[] = [];
  for (const { seed, agg } of themeAggs) {
    const themeHist = newsHistory.series[`theme:${seed.name}`] ?? {};
    const newsChange = newsMentionChange5d(themeHist);
    const newsToday = themeHist[kst.date] ?? 0;
    const sc = computeScores(agg, newsChange, allReturns60d, allVolumeSpikes5d, allReturns5d, allReturns20d);
    // 테마는 임계값 더 엄격
    let cls = sc.classification;
    if (cls === "real_hot" && sc.realHotScore < SCORE_THRESHOLDS.REAL_HOT_THEME) {
      cls = "real_hot_warning";
    }
    koreaThemes.push({
      theme_name: seed.name,
      stock_codes: seed.stock_codes,
      news_keywords: seed.news_keywords,
      stock_count: agg.stock_count,
      perf_5d: agg.perf_5d == null ? null : Math.round(agg.perf_5d * 10) / 10,
      perf_20d: agg.perf_20d == null ? null : Math.round(agg.perf_20d * 10) / 10,
      perf_60d: agg.perf_60d == null ? null : Math.round(agg.perf_60d * 10) / 10,
      perf_3m: agg.perf_3m == null ? null : Math.round(agg.perf_3m * 10) / 10,
      perf_6m: agg.perf_6m == null ? null : Math.round(agg.perf_6m * 10) / 10,
      foreign_60d_billion: agg.foreign_60d_billion,
      organ_60d_billion: agg.organ_60d_billion,
      individual_60d_billion: agg.individual_60d_billion,
      foreign_5d_billion: agg.foreign_5d_billion,
      organ_5d_billion: agg.organ_5d_billion,
      individual_5d_billion: agg.individual_5d_billion,
      three_investor_alignment_60d: agg.three_investor_alignment_60d,
      volume_recent_60d_billion: agg.volume_recent_60d_billion,
      volume_prev_60d_billion: agg.volume_prev_60d_billion,
      volume_sustain_ratio: sc.volume_sustain_ratio,
      volume_5d_spike_ratio: sc.volume_5d_spike_ratio,
      news_mention_change_5d: newsChange,
      news_mention_today: newsToday,
      real_hot_score: sc.realHotScore,
      short_momentum_score: sc.shortMomentumScore,
      score_breakdown: sc.breakdown,
      fake_hot_signals: sc.fakeSignals,
      classification: cls,
      etf_options: [], // 아래
      representative_stocks: agg.top_stocks,
      in_watchlist: [],
    });
  }

  // 8) ETF 코드 검증 (배치)
  console.log(`[etf] verifying`);
  for (const sec of koreaSectors) {
    const candidates = SECTOR_ETFS[sec.wics_name] ?? [];
    sec.etf_options = await verifyETFs(candidates);
  }
  for (const thm of koreaThemes) {
    const candidates = THEME_ETFS[thm.theme_name] ?? [];
    thm.etf_options = await verifyETFs(candidates);
  }

  // 9) 워치리스트 cross-reference (테마)
  try {
    const wl = JSON.parse(
      fs.readFileSync(path.join(DATA_DIR, "watchlist.json"), "utf-8"),
    ) as { stocks?: Array<{ code: string }> };
    const watchSet = new Set((wl.stocks ?? []).map((s) => s.code));
    for (const t of koreaThemes) {
      t.in_watchlist = t.stock_codes.filter((c) => watchSet.has(c));
    }
  } catch {
    // ignore
  }

  // 10) 글로벌 섹터 출력
  const globalSectors: GlobalSector[] = GLOBAL_SECTOR_ETFS.map((e) => {
    const s = globalSeries.get(e.ticker);
    if (!s) {
      return {
        ticker: e.ticker,
        gics_name: e.gics_name,
        gics_name_kr: e.gics_name_kr,
        perf_5d: null, perf_20d: null, perf_60d: null,
        perf_3m: null, perf_6m: null, perf_ytd: null,
      };
    }
    const c = s.closes;
    const ytdIdx = (() => {
      // YTD: 올해 첫 영업일 index 찾기
      const startOfYear = new Date(new Date().getFullYear(), 0, 1).getTime() / 1000;
      const idx = s.timestamps.findIndex((t) => t >= startOfYear);
      return idx >= 0 ? idx : 0;
    })();
    return {
      ticker: e.ticker,
      gics_name: e.gics_name,
      gics_name_kr: e.gics_name_kr,
      perf_5d: round1(calcReturn(c, 5)),
      perf_20d: round1(calcReturn(c, 20)),
      perf_60d: round1(calcReturn(c, 60)),
      perf_3m: round1(calcReturn(c, 63)),
      perf_6m: round1(calcReturn(c, 126)),
      perf_ytd: round1(calcReturnFromIdx(c, ytdIdx)),
    };
  });

  const spyPerf = (() => {
    if (!spy) {
      return { perf_5d: null, perf_20d: null, perf_60d: null, perf_3m: null, perf_6m: null, perf_ytd: null };
    }
    const c = spy.closes;
    const ytdIdx = (() => {
      const startOfYear = new Date(new Date().getFullYear(), 0, 1).getTime() / 1000;
      const idx = spy.timestamps.findIndex((t) => t >= startOfYear);
      return idx >= 0 ? idx : 0;
    })();
    return {
      perf_5d: round1(calcReturn(c, 5)),
      perf_20d: round1(calcReturn(c, 20)),
      perf_60d: round1(calcReturn(c, 60)),
      perf_3m: round1(calcReturn(c, 63)),
      perf_6m: round1(calcReturn(c, 126)),
      perf_ytd: round1(calcReturnFromIdx(c, ytdIdx)),
    };
  })();

  // 11) 로테이션 스냅샷 — 히스토리 파일에 누적
  const todaySnapshot: RotationSnapshot = {
    label: "current",
    date: kst.date,
    sectors: koreaSectors.map((s) => ({
      name: s.wics_name,
      real_hot_score: s.real_hot_score,
      classification: s.classification,
    })),
  };
  let history: { snapshots: Array<RotationSnapshot & { date: string }> } = { snapshots: [] };
  try {
    history = JSON.parse(fs.readFileSync(HISTORY_PATH, "utf-8"));
  } catch {
    // first run
  }
  // 같은 날짜는 덮어쓰기
  history.snapshots = (history.snapshots ?? []).filter((s) => s.date !== kst.date);
  history.snapshots.push({ ...todaySnapshot, label: "current" });
  // 180일 이상은 컷
  const cutoffDate = new Date(Date.now() - 200 * 24 * 3600 * 1000)
    .toISOString().split("T")[0];
  history.snapshots = history.snapshots.filter((s) => s.date >= cutoffDate);
  history.snapshots.sort((a, b) => (a.date < b.date ? -1 : 1));
  fs.writeFileSync(HISTORY_PATH, JSON.stringify(history, null, 2), "utf-8");

  // 6m_ago / 3m_ago / 1m_ago / current 추출
  function findSnapshotByDaysAgo(days: number): RotationSnapshot | null {
    const targetDate = new Date(Date.now() - days * 24 * 3600 * 1000)
      .toISOString().split("T")[0];
    // 가장 가까운 과거 스냅샷
    let best: typeof history.snapshots[number] | null = null;
    for (const s of history.snapshots) {
      if (s.date <= targetDate) {
        if (!best || s.date > best.date) best = s;
      }
    }
    return best;
  }
  const snapshots: RotationSnapshot[] = [];
  const sn6 = findSnapshotByDaysAgo(180);
  const sn3 = findSnapshotByDaysAgo(90);
  const sn1 = findSnapshotByDaysAgo(30);
  if (sn6) snapshots.push({ ...sn6, label: "6m_ago" });
  if (sn3) snapshots.push({ ...sn3, label: "3m_ago" });
  if (sn1) snapshots.push({ ...sn1, label: "1m_ago" });
  snapshots.push(todaySnapshot);

  // transitions: 1m_ago → current 사이에 점수가 가장 많이 떨어진 섹터 → 가장 많이 오른 섹터
  const transitions: HotSectorsData["rotation"]["transitions"] = [];
  if (sn1) {
    const prevMap = new Map(sn1.sectors.map((s) => [s.name, s.real_hot_score]));
    const deltas = todaySnapshot.sectors.map((s) => ({
      name: s.name,
      delta: s.real_hot_score - (prevMap.get(s.name) ?? s.real_hot_score),
    }));
    deltas.sort((a, b) => a.delta - b.delta);
    const cooling = deltas.slice(0, 2).filter((d) => d.delta < -5);
    const heating = deltas.slice(-2).reverse().filter((d) => d.delta > 5);
    for (const c of cooling) {
      for (const h of heating) {
        transitions.push({
          from_name: c.name,
          to_name: h.name,
          flow_direction: "heating",
          score_delta: h.delta - c.delta,
        });
      }
    }
  }

  // 정렬
  koreaSectors.sort((a, b) => b.real_hot_score - a.real_hot_score);
  koreaThemes.sort((a, b) => b.real_hot_score - a.real_hot_score);

  const output: HotSectorsData = {
    meta: {
      last_updated: kst.iso,
      source: "Naver Mobile + finance.naver.com + Yahoo Finance",
      backfill_days: 180,
      failed_count: failed,
    },
    korea_sectors: { sectors: koreaSectors },
    korea_themes: { themes: koreaThemes },
    global_sectors: { sectors: globalSectors, spy_perf: spyPerf },
    rotation: { snapshots, transitions },
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2), "utf-8");
  console.log(
    `[done] sectors=${koreaSectors.length}, themes=${koreaThemes.length}, global=${globalSectors.length}, failed=${failed}`,
  );
  console.log(`[done] saved → ${OUTPUT_PATH}`);
}

function round1(v: number | null): number | null {
  if (v == null) return null;
  return Math.round(v * 10) / 10;
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
