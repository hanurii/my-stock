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

/** "재화의 매입" 행의 숫자들에서 합계 열을 식별하고, 대명ENG 개별값을 반환.
 *  규칙: 행 마지막 숫자가 합계(= 앞 숫자들의 합과 일치)이면 제거 후 나머지 중 비영 최대값을 대명ENG로 간주.
 *  아바코 특수관계자 5사(슈미드·아바텍·대명ENG·대명FA·옵티브) 중 2025년 기준 "재화의 매입"이 유의미한 곳은 대명ENG·대명FA뿐이고 대명ENG가 항상 최대.
 */
function parseDaemyengPurchase(text: string): number | null {
  // "재화의 매입, 특수관계자거래" 뒤의 숫자 시퀀스 — 최대 12개 숫자까지 허용
  // (주의: "\s+" 로 콤마 포함 숫자 토큰을 분리)
  const m = text.match(/재화의\s*매입[,、\s]*특수관계자거래[\s]*((?:[0-9,]+\s+){2,12}[0-9,]+)/);
  if (!m) return null;
  const nums = m[1]
    .trim()
    .split(/\s+/)
    .map((s) => Number(s.replace(/,/g, "")))
    .filter((n) => !isNaN(n));
  if (nums.length < 3) return null;

  // 마지막이 합계인지 검증 (오차 1% 허용 — 반올림 흡수)
  const last = nums[nums.length - 1];
  const rest = nums.slice(0, -1);
  const sumRest = rest.reduce((a, b) => a + b, 0);
  let candidates: number[];
  if (last > 0 && Math.abs(sumRest - last) / Math.max(last, 1) < 0.01) {
    candidates = rest;
  } else {
    candidates = nums;
  }
  // 0 제외 최댓값 = 대명ENG (아바코 경우 유효)
  const nonZero = candidates.filter((n) => n > 0);
  if (!nonZero.length) return null;
  return Math.max(...nonZero);
}

/** 연결 재무제표 주요계정에서 매출액 조회 (당기). 실패 시 null. */
async function fetchRevenueFromDart(bsnsYear: number): Promise<number | null> {
  const list = await dartGet<{ account_nm: string; thstrm_amount: string; sj_div: string }>(
    "fnlttSinglAcntAll",
    {
      corp_code: CORP_CODE,
      bsns_year: String(bsnsYear),
      reprt_code: "11011",
      fs_div: "CFS", // 연결
    },
  );
  if (!list) return null;
  // IS(손익계산서) 또는 CIS(포괄손익계산서)에서 매출액
  for (const row of list) {
    if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
    const name = row.account_nm?.trim() ?? "";
    if (name === "매출액" || name === "수익(매출액)" || name === "영업수익" || name === "매출") {
      const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
      if (v > 1e10) return v;
    }
  }
  return null;
}

/** 주석에서 보고 기준 연도 추출. */
function parseReportYear(text: string): number | null {
  // 우선 "2025년 12월 31일" 류
  const byDate = text.match(/(20\d{2})년\s*12월\s*31일/);
  if (byDate) return Number(byDate[1]);
  // 보고서 제목 안의 "제N기 ... 2025.12" 같은 패턴
  const byBsns = text.match(/(20\d{2})\.12/);
  if (byBsns) return Number(byBsns[1]);
  return null;
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
    const year = parseReportYear(report.text);
    const purchase = parseDaemyengPurchase(report.text);
    // 매출은 주석 파싱 대신 DART API로 직접 조회 (훨씬 정확)
    const revenue = year ? await fetchRevenueFromDart(year) : null;
    await sleep(300);

    const parts: string[] = [];
    if (year) parts.push(`year=${year}`);
    else parts.push("year=미확인");
    if (purchase) parts.push(`대명ENG=${(purchase / 1e8).toFixed(1)}억`);
    else parts.push("대명ENG=파싱실패");
    if (revenue) parts.push(`매출=${(revenue / 1e8).toFixed(1)}억`);
    else parts.push("매출=API실패");

    if (year && purchase && revenue) {
      console.log(`  • 보고서 ${report.rcept_no}(${report.report_nm}) 파싱 성공: ${parts.join(", ")}`);
      daemyengYear = year;
      daemyengPurchase = purchase;
      daemyengRevenue = revenue;
    } else {
      console.log(`  • 보고서 ${report.rcept_no}(${report.report_nm}) 파싱 불완전 (${parts.join(", ")}) — 기존 값 유지`);
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
