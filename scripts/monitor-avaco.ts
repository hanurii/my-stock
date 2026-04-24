/**
 * 아바코(083930) 매도 트리거 일일 자동 모니터링 스크립트
 *
 * 추적 지표 (research JSON exit_timing 트리거 대응):
 * 1) PER 15배 돌파 / PEG 0.7 돌파 — growth-watchlist.json 스코어 기반
 * 2) 단일판매·공급계약 공시 90일 공백 — DART list API
 * 3) 대명ENG 매입액 매출의 10% 초과 — 최신 사업/분기보고서 특수관계자 거래 주석
 * 4) 중국 장비 수출 규제·OLED 보조금·BOE 투자 축소 뉴스 — Google News RSS
 *
 * 결과: public/data/research/monitor/083930.json
 * 실행: npx tsx scripts/monitor-avaco.ts
 */
import fs from "fs";
import path from "path";
import { inflateRawSync } from "zlib";

// ── .env 수동 로드 ──
try {
  const env = fs.readFileSync(path.resolve(".env"), "utf-8");
  for (const line of env.split("\n")) {
    const m = line.match(/^([A-Z_]+)=(.*)$/);
    if (m) process.env[m[1]] = m[2].trim();
  }
} catch {}

const DART_API = "https://opendart.fss.or.kr/api";
const DART_KEY = process.env.DART_API_KEY ?? "";
const CODE = "083930";
const CORP_CODE = "00442145";
const NAME = "아바코";
const DATA_DIR = path.resolve("public/data");
const MONITOR_DIR = path.join(DATA_DIR, "research", "monitor");
const OUT_FILE = path.join(MONITOR_DIR, `${CODE}.json`);

// ── 임계값 ──
const PER_THRESHOLD = 15;
const PEG_THRESHOLD = 0.7;
const ORDER_SILENCE_DAYS = 90;
const DAEMYENG_REVENUE_RATIO_THRESHOLD = 10; // %
const NEWS_LOOKBACK_DAYS = 7;

// ── 타입 ──
interface MonitorData {
  code: string;
  name: string;
  last_checked: string;
  metrics: {
    current_price: number;
    per: number;
    peg: number;
    per_threshold: { hit: boolean; value: number; threshold: number };
    peg_threshold: { hit: boolean; value: number; threshold: number };
    last_order_date: string | null;
    last_order_title: string | null;
    last_order_days_ago: number | null;
    order_silence_threshold: { hit: boolean; days: number | null; threshold: number };
    daemyeng_year: number;
    daemyeng_purchase_billion: number;
    daemyeng_revenue_billion: number;
    daemyeng_revenue_ratio_pct: number;
    daemyeng_threshold: { hit: boolean; value: number; threshold: number };
    news_hits: Array<{ keyword: string; date: string; title: string; url: string }>;
  };
  alerts: Array<{
    severity: "info" | "warn" | "bad";
    type: string;
    title: string;
    message: string;
  }>;
  sources: Array<{ label: string; ref: string }>;
}

// ── 유틸 ──
function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }
function daysBetween(a: Date, b: Date) {
  return Math.floor((b.getTime() - a.getTime()) / 86400000);
}
function kstToday(): string {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  return d.toISOString().slice(0, 10);
}
function kstNow(): string {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  return d.toISOString().replace("Z", "+09:00");
}

async function dartGet<T>(endpoint: string, params: Record<string, string>): Promise<T[] | null> {
  const url = new URL(`${DART_API}/${endpoint}.json`);
  url.searchParams.set("crtfc_key", DART_KEY);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  const res = await fetch(url.toString());
  if (!res.ok) return null;
  const json = await res.json() as { status: string; list?: T[]; message?: string };
  if (json.status === "000" && json.list) return json.list;
  if (json.status === "013") return [];
  console.warn(`  ⚠ ${endpoint}: ${json.status} ${json.message}`);
  return null;
}

// ── 1) PER/PEG: growth-watchlist.json에서 현재 스코어 기반 값 로드 ──
interface GrowthWatchStock {
  code: string;
  name: string;
  per?: number;
  peg?: number;
  current_price_at_scoring?: number;
}
function loadPerPeg(): { price: number; per: number; peg: number } | null {
  try {
    const raw = fs.readFileSync(path.join(DATA_DIR, "growth-watchlist.json"), "utf-8");
    const json = JSON.parse(raw) as { stocks?: GrowthWatchStock[] } | GrowthWatchStock[];
    const list = Array.isArray(json) ? json : (json.stocks ?? []);
    const s = list.find((x) => x.code === CODE);
    if (!s || s.per == null || s.peg == null || s.current_price_at_scoring == null) return null;
    return { price: s.current_price_at_scoring, per: s.per, peg: s.peg };
  } catch {
    return null;
  }
}

// ── 2) 최근 공급계약 공시 ──
interface DartListItem {
  rcept_dt: string;   // YYYYMMDD
  rcept_no: string;
  report_nm: string;
}
async function fetchLastSupplyContract(): Promise<{ date: string; title: string; rcept_no: string } | null> {
  // 최근 6개월 내 '단일판매ㆍ공급계약' 공시 조회
  const today = new Date();
  const sixMonthsAgo = new Date(today.getTime() - 180 * 86400 * 1000);
  const fmt = (d: Date) => d.toISOString().slice(0, 10).replace(/-/g, "");
  const list = await dartGet<DartListItem>("list", {
    corp_code: CORP_CODE,
    bgn_de: fmt(sixMonthsAgo),
    end_de: fmt(today),
    page_count: "100",
  });
  if (!list) return null;
  // 최신순(DART 기본 desc)이므로 첫 매칭 반환
  for (const item of list) {
    const nm = item.report_nm ?? "";
    if (nm.includes("단일판매") && nm.includes("공급계약")) {
      const d = item.rcept_dt;
      const iso = `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
      return { date: iso, title: nm.trim(), rcept_no: item.rcept_no };
    }
  }
  return null;
}

// ── 3) 대명ENG 매입 / 매출 비율 (최신 사업/분기보고서 주석 파싱) ──
function parseZip(buf: Buffer): Array<{ name: string; data: Buffer }> {
  let eocd = -1;
  for (let i = buf.length - 22; i >= 0; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) return [];
  const cdOff = buf.readUInt32LE(eocd + 16);
  const cdEntries = buf.readUInt16LE(eocd + 10);
  const entries: Array<{ name: string; data: Buffer }> = [];
  let off = cdOff;
  for (let i = 0; i < cdEntries; i++) {
    if (buf.readUInt32LE(off) !== 0x02014b50) break;
    const compMethod = buf.readUInt16LE(off + 10);
    const compSize = buf.readUInt32LE(off + 20);
    const nameLen = buf.readUInt16LE(off + 28);
    const extraLen = buf.readUInt16LE(off + 30);
    const commentLen = buf.readUInt16LE(off + 32);
    const localHdr = buf.readUInt32LE(off + 42);
    const name = buf.subarray(off + 46, off + 46 + nameLen).toString("utf-8");
    const lNameLen = buf.readUInt16LE(localHdr + 26);
    const lExtraLen = buf.readUInt16LE(localHdr + 28);
    const dataStart = localHdr + 30 + lNameLen + lExtraLen;
    const raw = buf.subarray(dataStart, dataStart + compSize);
    const data = compMethod === 8 ? inflateRawSync(raw) : Buffer.from(raw);
    entries.push({ name, data });
    off += 46 + nameLen + extraLen + commentLen;
  }
  return entries;
}

function extractText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/g, " ")
    .replace(/<style[\s\S]*?<\/style>/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

async function fetchLatestReport(): Promise<{ rcept_no: string; report_nm: string; text: string } | null> {
  // 최근 1년 사업·분기·반기보고서 중 가장 최신
  const today = new Date();
  const oneYrAgo = new Date(today.getTime() - 365 * 86400 * 1000);
  const fmt = (d: Date) => d.toISOString().slice(0, 10).replace(/-/g, "");
  const list = await dartGet<DartListItem>("list", {
    corp_code: CORP_CODE,
    bgn_de: fmt(oneYrAgo),
    end_de: fmt(today),
    pblntf_ty: "A", // 정기공시
    page_count: "20",
  });
  if (!list) return null;
  const target = list.find((x) => /(사업보고서|분기보고서|반기보고서)/.test(x.report_nm));
  if (!target) return null;
  const url = `${DART_API}/document.xml?crtfc_key=${DART_KEY}&rcept_no=${target.rcept_no}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  const buf = Buffer.from(await res.arrayBuffer());
  const entries = parseZip(buf);
  const main = entries.reduce((max, e) => e.data.length > (max?.data.length || 0) ? e : max,
    null as null | { name: string; data: Buffer });
  if (!main) return null;
  return { rcept_no: target.rcept_no, report_nm: target.report_nm.trim(), text: extractText(main.data.toString("utf-8")) };
}

/** 특수관계자 거래 주석에서 대명ENG 매입액 + 전체 매출액 추출.
 *  실패 시 기존 JSON 값 유지. */
function parseDaemyeng(text: string): { year: number | null; purchase: number | null; revenue: number | null } {
  // "(주)대명ENG" 주변 "재화의 매입" 테이블 찾기
  // 사업보고서 주석 표 형식: "재화의 매입, 특수관계자거래 ... 합계"
  // 간단 휴리스틱: 패턴 매칭으로 대명ENG와 가장 가까운 금액(원 단위) 추출
  const result = { year: null as number | null, purchase: null as number | null, revenue: null as number | null };

  // 매출액: "매출액" 또는 "수익(매출액)" 다음 큰 숫자
  const revMatch = text.match(/매출액[^0-9]*?([0-9,]{9,})/);
  if (revMatch) {
    const v = Number(revMatch[1].replace(/,/g, ""));
    if (v > 1e10) result.revenue = v; // 100억 이상이면 유효
  }

  // 대명ENG 매입: "대명ENG" 검색 후 주변 2000자 내 "재화의 매입" 관련 가장 가까운 큰 숫자
  const idx = text.indexOf("대명ENG");
  if (idx > 0) {
    const window = text.slice(Math.max(0, idx - 500), Math.min(text.length, idx + 2000));
    // "재화의 매입" 패턴 주변 숫자
    const buyIdx = window.indexOf("재화의 매입");
    if (buyIdx >= 0) {
      // 대명ENG가 다른 특수관계자들과 한 줄에 있을 수 있음. 순서 기반 추출은 난이도 높음.
      // 간략 버전: window 안에서 "대명ENG" 앞뒤 숫자 중 100억 이상 값 수집
      const nums = Array.from(window.matchAll(/([0-9]{1,3}(?:,[0-9]{3}){2,})/g))
        .map((m) => Number(m[1].replace(/,/g, "")))
        .filter((n) => n > 1e10 && n < 1e13); // 100억 ~ 10조
      if (nums.length) {
        // 가장 큰 값(대체로 매입액) 선택 — 2025년 대명ENG 31,183,549,200원 예상
        result.purchase = Math.max(...nums);
      }
    }
  }

  // 보고기준연도 추출 — 사업보고서 제목 or 기준일
  const yearMatch = text.match(/(2024|2025|2026)년\s*12월\s*31일/);
  if (yearMatch) result.year = Number(yearMatch[1]);

  return result;
}

// ── 4) 뉴스 모니터링 (Google News RSS) ──
const NEWS_KEYWORDS = [
  "중국 디스플레이 장비 수출 규제",
  "중국 OLED 보조금",
  "BOE 8.6세대 투자 축소",
];

async function fetchNewsHits(): Promise<MonitorData["metrics"]["news_hits"]> {
  const hits: MonitorData["metrics"]["news_hits"] = [];
  const cutoff = new Date(Date.now() - NEWS_LOOKBACK_DAYS * 86400 * 1000);
  for (const kw of NEWS_KEYWORDS) {
    const url = `https://news.google.com/rss/search?q=${encodeURIComponent(kw)}&hl=ko&gl=KR&ceid=KR:ko`;
    try {
      const res = await fetch(url, { headers: { "user-agent": "Mozilla/5.0" } });
      if (!res.ok) continue;
      const xml = await res.text();
      // <item><title>...</title><link>...</link><pubDate>Wed, 23 Apr 2026 06:00:00 GMT</pubDate></item>
      const items = Array.from(xml.matchAll(/<item>([\s\S]*?)<\/item>/g));
      for (const m of items.slice(0, 10)) {
        const block = m[1];
        const title = block.match(/<title>(?:<!\[CDATA\[)?([^<\]]+)/)?.[1]?.trim();
        const link = block.match(/<link>([^<]+)<\/link>/)?.[1]?.trim();
        const pub = block.match(/<pubDate>([^<]+)<\/pubDate>/)?.[1]?.trim();
        if (!title || !pub) continue;
        const pubDate = new Date(pub);
        if (isNaN(pubDate.getTime()) || pubDate < cutoff) continue;
        hits.push({
          keyword: kw,
          date: pubDate.toISOString().slice(0, 10),
          title,
          url: link ?? "",
        });
      }
    } catch (e) {
      console.warn(`  ⚠ 뉴스 조회 실패 (${kw}):`, (e as Error).message);
    }
    await sleep(500);
  }
  return hits;
}

// ── 메인 ──
async function main() {
  if (!DART_KEY) {
    console.error("❌ DART_API_KEY 환경변수가 없습니다.");
    process.exit(1);
  }
  console.log(`📊 ${NAME}(${CODE}) 매도 트리거 모니터링 시작 — ${kstNow()}`);

  if (!fs.existsSync(MONITOR_DIR)) fs.mkdirSync(MONITOR_DIR, { recursive: true });

  // ── 1) PER/PEG ──
  const valPerPeg = loadPerPeg() ?? { price: 0, per: 0, peg: 0 };
  console.log(`  • PER ${valPerPeg.per}, PEG ${valPerPeg.peg} @ ${valPerPeg.price.toLocaleString()}원`);

  // ── 2) 최근 공급계약 ──
  const contract = await fetchLastSupplyContract();
  await sleep(300);
  let daysAgo: number | null = null;
  if (contract) {
    daysAgo = daysBetween(new Date(contract.date), new Date());
    console.log(`  • 최신 공급계약: ${contract.date} (${daysAgo}일 전) — ${contract.title}`);
  } else {
    console.log(`  • 최근 6개월 공급계약 공시 없음`);
  }

  // ── 3) 대명ENG 매입 비율 ──
  //   우선 기존 JSON에 저장된 값 유지 (최신 보고서 파싱 성공 시 갱신)
  //   fallback 기본값: 2025년 감사보고서 기준
  let daemyengYear = 2025;
  let daemyengPurchase = 31_183_549_200; // 원
  let daemyengRevenue = 398_100_000_000; // 3,981억 (growth-watchlist 기반)
  try {
    const existing = JSON.parse(fs.readFileSync(OUT_FILE, "utf-8")) as MonitorData;
    if (existing?.metrics?.daemyeng_year) {
      daemyengYear = existing.metrics.daemyeng_year;
      daemyengPurchase = existing.metrics.daemyeng_purchase_billion * 1e8; // 억 → 원
      daemyengRevenue = existing.metrics.daemyeng_revenue_billion * 1e8;
    }
  } catch {}

  // 최신 보고서 파싱 시도
  const report = await fetchLatestReport();
  await sleep(300);
  if (report) {
    const parsed = parseDaemyeng(report.text);
    if (parsed.year && parsed.purchase && parsed.revenue) {
      console.log(`  • 보고서 ${report.rcept_no}(${report.report_nm}) 파싱 성공: ${parsed.year}년 대명ENG ${(parsed.purchase / 1e8).toFixed(1)}억 / 매출 ${(parsed.revenue / 1e8).toFixed(1)}억`);
      daemyengYear = parsed.year;
      daemyengPurchase = parsed.purchase;
      daemyengRevenue = parsed.revenue;
    } else {
      console.log(`  • 보고서 ${report.rcept_no}(${report.report_nm}) 파싱 불완전 — 기존 값 유지`);
    }
  }
  const daemyengRatio = (daemyengPurchase / daemyengRevenue) * 100;
  console.log(`  • 대명ENG ${daemyengYear}년 매입 ${(daemyengPurchase / 1e8).toFixed(1)}억 / 매출의 ${daemyengRatio.toFixed(2)}%`);

  // ── 4) 뉴스 ──
  console.log(`  • 뉴스 RSS 조회 중...`);
  const newsHits = await fetchNewsHits();
  console.log(`  • 뉴스 매칭 ${newsHits.length}건 (최근 ${NEWS_LOOKBACK_DAYS}일)`);

  // ── 알림 생성 ──
  const alerts: MonitorData["alerts"] = [];

  if (valPerPeg.per >= PER_THRESHOLD) {
    alerts.push({
      severity: "bad",
      type: "per_over",
      title: `PER ${PER_THRESHOLD}배 돌파`,
      message: `현재 PER ${valPerPeg.per.toFixed(2)}배 — 부분 익절 트리거 도달`,
    });
  }
  if (valPerPeg.peg >= PEG_THRESHOLD) {
    alerts.push({
      severity: "bad",
      type: "peg_over",
      title: `PEG ${PEG_THRESHOLD} 돌파`,
      message: `현재 PEG ${valPerPeg.peg.toFixed(2)} — 부분 익절 트리거 도달`,
    });
  }
  if (daysAgo != null && daysAgo >= ORDER_SILENCE_DAYS) {
    alerts.push({
      severity: "warn",
      type: "order_silence",
      title: `공급계약 공시 공백 ${ORDER_SILENCE_DAYS}일 초과`,
      message: `최근 공시 ${contract?.date}로부터 ${daysAgo}일 경과 — 부분 익절 트리거 도달`,
    });
  }
  if (daemyengRatio >= DAEMYENG_REVENUE_RATIO_THRESHOLD) {
    alerts.push({
      severity: "bad",
      type: "daemyeng_over",
      title: `대명ENG 매입 매출의 ${DAEMYENG_REVENUE_RATIO_THRESHOLD}% 초과`,
      message: `${daemyengYear}년 ${daemyengRatio.toFixed(2)}% — 부분 익절 트리거 도달`,
    });
  } else if (daemyengRatio >= 8) {
    alerts.push({
      severity: "warn",
      type: "daemyeng_close",
      title: `대명ENG 매입 비율 임계 근접`,
      message: `${daemyengYear}년 ${daemyengRatio.toFixed(2)}% (임계 ${DAEMYENG_REVENUE_RATIO_THRESHOLD}% 대비)`,
    });
  }
  if (newsHits.length > 0) {
    alerts.push({
      severity: "info",
      type: "news_keyword_hit",
      title: `규제·투자 축소 키워드 뉴스 ${newsHits.length}건`,
      message: `최근 ${NEWS_LOOKBACK_DAYS}일 내 키워드 매칭. 상세는 하단 리스트 확인`,
    });
  }

  if (alerts.length === 0) {
    alerts.push({
      severity: "info",
      type: "all_clear",
      title: "모든 매도 트리거 범위 내",
      message: "현재 지표·공시·뉴스 기준 즉각 매도 사유 없음. 보유 유지.",
    });
  }

  // ── 저장 ──
  const out: MonitorData = {
    code: CODE,
    name: NAME,
    last_checked: kstNow(),
    metrics: {
      current_price: valPerPeg.price,
      per: valPerPeg.per,
      peg: valPerPeg.peg,
      per_threshold: { hit: valPerPeg.per >= PER_THRESHOLD, value: valPerPeg.per, threshold: PER_THRESHOLD },
      peg_threshold: { hit: valPerPeg.peg >= PEG_THRESHOLD, value: valPerPeg.peg, threshold: PEG_THRESHOLD },
      last_order_date: contract?.date ?? null,
      last_order_title: contract?.title ?? null,
      last_order_days_ago: daysAgo,
      order_silence_threshold: { hit: daysAgo != null && daysAgo >= ORDER_SILENCE_DAYS, days: daysAgo, threshold: ORDER_SILENCE_DAYS },
      daemyeng_year: daemyengYear,
      daemyeng_purchase_billion: Number((daemyengPurchase / 1e8).toFixed(1)),
      daemyeng_revenue_billion: Number((daemyengRevenue / 1e8).toFixed(1)),
      daemyeng_revenue_ratio_pct: Number(daemyengRatio.toFixed(2)),
      daemyeng_threshold: { hit: daemyengRatio >= DAEMYENG_REVENUE_RATIO_THRESHOLD, value: Number(daemyengRatio.toFixed(2)), threshold: DAEMYENG_REVENUE_RATIO_THRESHOLD },
      news_hits: newsHits,
    },
    alerts,
    sources: [
      { label: "PER/PEG 스코어", ref: "public/data/growth-watchlist.json" },
      { label: "단일판매·공급계약 공시", ref: "DART list API (corp_code 00442145)" },
      { label: "대명ENG 매입 비율", ref: report ? `DART ${report.rcept_no} (${report.report_nm})` : "기존 저장값" },
      { label: "뉴스 RSS", ref: "news.google.com/rss/search (3 키워드)" },
    ],
  };

  fs.writeFileSync(OUT_FILE, JSON.stringify(out, null, 2), "utf-8");
  console.log(`✅ 저장 완료: ${OUT_FILE}`);
  console.log(`   알림 ${alerts.length}건 (${alerts.map((a) => a.severity).join(", ")})`);
}

main().catch((e) => { console.error(e); process.exit(1); });
