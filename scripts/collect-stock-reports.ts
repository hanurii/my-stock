/**
 * 상위 성장주 종목 리서치 리포트 수집 스크립트
 *
 * 상위 15개 종목에 대해:
 * - 채점 요약 (강점/약점)
 * - 주주환원 현황
 * - 최근 뉴스 (매경/한경)
 * - DART 최근 공시
 * - 리스크 플래그
 *
 * 사용법: npx tsx scripts/collect-stock-reports.ts
 */
import fs from "fs";
import path from "path";
import {
  scoreGrowth,
  type GrowthStockInput,
  type ShareholderReturnData as ScoringShReturn,
} from "../src/lib/scoring";

// ── 설정 ──

const DART_API = "https://opendart.fss.or.kr/api";
const DART_API_KEY = process.env.DART_API_KEY ?? "";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
const DATA_DIR = path.resolve("public/data");
const OUTPUT_FILE = path.join(DATA_DIR, "stock-reports.json");
const TOP_N = 15;
const REQUEST_DELAY_MS = 500;

// ── 타입 ──

interface ScoreDetail {
  item: string;
  basis: string;
  score: number;
  max: number;
  cat: number;
}

interface NewsItem {
  title: string;
  link: string;
  source: string;
  date: string;
}

interface DartDisclosure {
  title: string;
  link: string;
  date: string;
  type: string;
}

interface StockReport {
  code: string;
  name: string;
  sector: string;
  score: number;
  grade: string;
  cat1: number;
  cat2: number;
  cat3: number;
  highlights: string;
  catalyst: string;
  strengths: string[];
  weaknesses: string[];
  shareholder_summary: {
    cancellation_years: number;
    dividend_history: { year: number; dps: number | null }[];
    dilutive_count: number;
    dilutive_types: Record<string, number>;
  };
  news: NewsItem[];
  disclosures: DartDisclosure[];
  risk_flags: string[];
}

// ── 유틸 ──

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function dateNDaysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
}

// ── A. 채점 요약 (강점/약점 추출) ──

function extractStrengthsWeaknesses(details: ScoreDetail[]): { strengths: string[]; weaknesses: string[] } {
  // cat 0(금리 감점), cat 4(주주환원 보정) 제외 — 순수 종목 지표만
  const items = details.filter((d) => d.cat >= 1 && d.cat <= 3 && d.max > 0);

  const scored = items.map((d) => ({
    label: `${d.item}: ${d.basis}`,
    ratio: d.score / d.max,
    score: d.score,
    max: d.max,
  }));

  scored.sort((a, b) => b.ratio - a.ratio);
  const strengths = scored.slice(0, 3).map((s) => s.label);

  scored.sort((a, b) => a.ratio - b.ratio);
  const weaknesses = scored.slice(0, 3).map((s) => s.label);

  // 감점 항목도 약점에 추가
  const penalties = details.filter((d) => d.score < 0);
  for (const p of penalties) {
    if (weaknesses.length < 3) {
      weaknesses.push(`${p.item}: ${p.basis} (${p.score}점)`);
    }
  }

  return { strengths: strengths.slice(0, 3), weaknesses: weaknesses.slice(0, 3) };
}

// ── B. 주주환원 현황 ──

const DILUTIVE_TYPES = new Set([
  "전환권행사", "신주인수권행사", "유상증자(제3자배정)",
  "주식매수선택권행사", "상환권행사",
]);

interface RawShStock {
  code: string;
  treasury_stock: { year: number; cancelled: number }[];
  dividends: { year: number; dps: number | null }[];
  capital_changes: { type: string }[];
}

function extractShareholderSummary(sh: RawShStock | undefined) {
  if (!sh) {
    return { cancellation_years: 0, dividend_history: [], dilutive_count: 0, dilutive_types: {} };
  }
  const cancellationYears = sh.treasury_stock.filter((t) => t.cancelled > 0).length;
  const dividendHistory = sh.dividends
    .filter((d) => d.year < new Date().getFullYear())
    .sort((a, b) => b.year - a.year)
    .slice(0, 5);
  const dilutiveEvents = sh.capital_changes.filter((c) => DILUTIVE_TYPES.has(c.type));
  const dilutiveTypes: Record<string, number> = {};
  for (const e of dilutiveEvents) {
    dilutiveTypes[e.type] = (dilutiveTypes[e.type] || 0) + 1;
  }
  return {
    cancellation_years: cancellationYears,
    dividend_history: dividendHistory,
    dilutive_count: dilutiveEvents.length,
    dilutive_types: dilutiveTypes,
  };
}

// ── C. 뉴스 수집 ──

const RSS_FEEDS = [
  { urls: ["https://www.mk.co.kr/rss/30100041", "https://www.mk.co.kr/rss/50200011"], source: "매일경제" },
  { urls: ["https://www.hankyung.com/feed/economy", "https://www.hankyung.com/feed/finance"], source: "한국경제" },
];

async function fetchNewsForStock(stockName: string): Promise<NewsItem[]> {
  const allItems: NewsItem[] = [];
  // 종목명에서 검색용 키워드 추출 (짧은 이름은 그대로, 긴 이름은 앞부분)
  const keyword = stockName.length > 4 ? stockName.substring(0, 4) : stockName;

  for (const feed of RSS_FEEDS) {
    for (const url of feed.urls) {
      try {
        const res = await fetch(url, { headers: { "User-Agent": UA } });
        if (!res.ok) continue;
        const xml = await res.text();

        const items = xml.match(/<item>[\s\S]*?<\/item>/g) || [];
        for (const item of items) {
          const title =
            item.match(/<title>[\s\S]*?CDATA\[(.*?)\]\]/)?.[1] ||
            item.match(/<title>(.*?)<\/title>/)?.[1] || "";
          const link =
            item.match(/<link>[\s\S]*?CDATA\[(.*?)\]\]/)?.[1] ||
            item.match(/<link>(.*?)<\/link>/)?.[1] || "";
          const pubDateStr = item.match(/<pubDate>(.*?)<\/pubDate>/)?.[1] || "";
          const pubDate = new Date(pubDateStr);
          if (isNaN(pubDate.getTime())) continue;

          // 종목명 포함 기사만
          if (!title.includes(keyword)) continue;

          allItems.push({
            title,
            link,
            source: feed.source,
            date: pubDate.toISOString().split("T")[0],
          });
        }
        await sleep(REQUEST_DELAY_MS);
      } catch { continue; }
    }
  }

  // 중복 제거 + 최신순 정렬
  const unique: NewsItem[] = [];
  for (const item of allItems.sort((a, b) => b.date.localeCompare(a.date))) {
    if (!unique.some((u) => u.title.substring(0, 15) === item.title.substring(0, 15))) {
      unique.push(item);
    }
  }
  return unique.slice(0, 5);
}

// ── D. DART 공시 ──

interface DartListItem {
  corp_name: string;
  report_nm: string;
  rcept_no: string;
  rcept_dt: string;
  pblntf_ty: string;
  pblntf_detail_ty: string;
}

async function fetchDartDisclosures(corpCode: string): Promise<DartDisclosure[]> {
  if (!DART_API_KEY) return [];
  const bgn = dateNDaysAgo(90);
  const url = new URL(`${DART_API}/list.json`);
  url.searchParams.set("crtfc_key", DART_API_KEY);
  url.searchParams.set("corp_code", corpCode);
  url.searchParams.set("bgn_de", bgn);
  url.searchParams.set("page_count", "10");
  url.searchParams.set("sort", "date");
  url.searchParams.set("sort_mth", "desc");

  try {
    const res = await fetch(url.toString());
    if (!res.ok) return [];
    const json = await res.json() as { status: string; list?: DartListItem[] };
    if (json.status !== "000" || !json.list) return [];

    return json.list.slice(0, 5).map((d) => ({
      title: d.report_nm,
      link: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${d.rcept_no}`,
      date: `${d.rcept_dt.substring(0, 4)}-${d.rcept_dt.substring(4, 6)}-${d.rcept_dt.substring(6, 8)}`,
      type: d.pblntf_detail_ty || d.pblntf_ty || "",
    }));
  } catch {
    return [];
  }
}

// ── E. 리스크 플래그 ──

function detectRiskFlags(
  stock: GrowthStockInput,
  shSummary: StockReport["shareholder_summary"],
): string[] {
  const flags: string[] = [];
  if (shSummary.dilutive_count >= 3) flags.push("지분 희석 주의");
  if (stock.profit_status === "deficit") flags.push("적자 지속");
  if (stock.profit_status === "turning") flags.push("적자 전환 임박");
  if (stock.peg == null && stock.profit_status !== "deficit") flags.push("PEG 산출 불가 (성장성 둔화 가능)");
  if (stock.debt_ratio >= 100) flags.push("부채비율 " + stock.debt_ratio + "% (재무 부담)");
  if (stock.prev_year_op_margin != null && stock.op_margin < stock.prev_year_op_margin) {
    flags.push("영업이익률 하락 (" + stock.prev_year_op_margin + "% → " + stock.op_margin + "%)");
  }
  if (stock.op_profit_growth_3y < 0) flags.push("영업이익 역성장");
  return flags;
}

// ── 메인 ──

async function main() {
  console.log("📊 종목 리서치 리포트 수집 시작\n");

  // 데이터 로드
  const growthData = JSON.parse(fs.readFileSync(path.join(DATA_DIR, "growth-watchlist.json"), "utf-8"));
  const shData = JSON.parse(fs.readFileSync(path.join(DATA_DIR, "shareholder-returns.json"), "utf-8"));
  const baseRate = growthData.base_rate ?? 2.75;

  // 주주환원 맵 구성
  const shMap = new Map<string, RawShStock>();
  for (const s of shData.stocks) shMap.set(s.code, s);

  // ShareholderReturnData 맵 (점수 계산용)
  const shScoreMap = new Map<string, ScoringShReturn>();
  const currentYear = new Date().getFullYear();
  for (const s of shData.stocks as RawShStock[]) {
    const divs = s.dividends.filter((d) => d.year < currentYear).sort((a, b) => b.year - a.year);
    let cd = 0;
    for (const d of divs) { if (d.dps !== null && d.dps > 0) cd++; else break; }
    shScoreMap.set(s.code, {
      treasury_cancellation_years: s.treasury_stock.filter((t) => t.cancelled > 0).length,
      consecutive_dividend_years: cd,
      dilutive_event_count: s.capital_changes.filter((c) => DILUTIVE_TYPES.has(c.type)).length,
    });
  }

  // 점수 계산 + 상위 N개 추출
  const scored = growthData.stocks
    .map((s: GrowthStockInput) => ({
      ...s,
      ...scoreGrowth(s, baseRate, shScoreMap.get(s.code)),
    }))
    .sort((a: { grade: string; score: number }, b: { grade: string; score: number }) => {
      const go: Record<string, number> = { A: 0, B: 1, C: 2, D: 3 };
      const gd = (go[a.grade] ?? 9) - (go[b.grade] ?? 9);
      return gd !== 0 ? gd : b.score - a.score;
    })
    .slice(0, TOP_N);

  console.log(`📋 상위 ${scored.length}개 종목 대상:\n`);
  scored.forEach((s: { name: string; grade: string; score: number }, i: number) =>
    console.log(`  ${i + 1}. [${s.grade}] ${s.name} (${s.score}점)`));

  // corp_code 매핑 (DART 공시용)
  let corpMap = new Map<string, string>();
  if (DART_API_KEY) {
    const { loadCorpCodeMap } = await import("./fetch-shareholder-returns");
    corpMap = await loadCorpCodeMap();
  } else {
    console.warn("\n  ⚠ DART_API_KEY 미설정 — 공시 수집 건너뜀");
  }

  // 종목별 수집
  const reports: StockReport[] = [];

  for (let i = 0; i < scored.length; i++) {
    const stock = scored[i] as GrowthStockInput & { score: number; grade: string; cat1: number; cat2: number; cat3: number; details: ScoreDetail[] };
    console.log(`\n[${i + 1}/${scored.length}] ${stock.name} (${stock.code})`);

    // A. 채점 요약
    const { strengths, weaknesses } = extractStrengthsWeaknesses(stock.details);

    // B. 주주환원
    const shSummary = extractShareholderSummary(shMap.get(stock.code));

    // C. 뉴스
    console.log("  뉴스 수집...");
    const news = await fetchNewsForStock(stock.name);
    console.log(`  → ${news.length}건`);

    // D. DART 공시
    let disclosures: DartDisclosure[] = [];
    const corpCode = corpMap.get(stock.code);
    if (corpCode) {
      console.log("  DART 공시 수집...");
      disclosures = await fetchDartDisclosures(corpCode);
      console.log(`  → ${disclosures.length}건`);
      await sleep(REQUEST_DELAY_MS);
    }

    // E. 리스크 플래그
    const riskFlags = detectRiskFlags(stock, shSummary);

    reports.push({
      code: stock.code,
      name: stock.name,
      sector: stock.sector || "",
      score: stock.score,
      grade: stock.grade,
      cat1: stock.cat1,
      cat2: stock.cat2,
      cat3: stock.cat3,
      highlights: stock.highlights || "",
      catalyst: stock.catalyst || "",
      strengths,
      weaknesses,
      shareholder_summary: shSummary,
      news,
      disclosures,
      risk_flags: riskFlags,
    });
  }

  // 저장
  const output = {
    generated_at: today(),
    description: `상위 ${reports.length}개 저평가 성장주 리서치 리포트`,
    stocks: reports,
  };
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2), "utf-8");
  console.log(`\n✅ 저장 완료: ${OUTPUT_FILE} (${reports.length}개 종목)`);
}

main().catch((e) => {
  console.error("❌ 실행 오류:", e);
  process.exit(1);
});
