/**
 * 매도 트리거 자동 모니터 — 공통 수집 모듈
 *
 * 종목 무관 데이터 수집 함수들. 모든 함수는 실패 시 null/빈배열 반환(throw 안 함).
 */
import fs from "fs";
import path from "path";
import { inflateRawSync } from "zlib";
import type { CollectorBundle } from "./types";

// ── 환경 ──
const DART_API = "https://opendart.fss.or.kr/api";

export function loadEnv() {
  try {
    const env = fs.readFileSync(path.resolve(".env"), "utf-8");
    for (const line of env.split("\n")) {
      const m = line.match(/^([A-Z_]+)=(.*)$/);
      if (m && !process.env[m[1]]) process.env[m[1]] = m[2].trim();
    }
  } catch {}
}

// ── 유틸 ──
export function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
export function daysBetween(a: Date, b: Date) {
  return Math.floor((b.getTime() - a.getTime()) / 86400000);
}
export function kstNow(): string {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  return d.toISOString().replace("Z", "+09:00");
}
export function fmtYmd(d: Date): string {
  return d.toISOString().slice(0, 10).replace(/-/g, "");
}

// ── DART API wrapper ──
export async function dartGet<T>(
  endpoint: string,
  params: Record<string, string>,
): Promise<T[] | null> {
  const KEY = process.env.DART_API_KEY ?? "";
  if (!KEY) return null;
  const url = new URL(`${DART_API}/${endpoint}.json`);
  url.searchParams.set("crtfc_key", KEY);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  const res = await fetch(url.toString());
  if (!res.ok) return null;
  const json = (await res.json()) as { status: string; list?: T[]; message?: string };
  if (json.status === "000" && json.list) return json.list;
  if (json.status === "013") return [];
  console.warn(`  ⚠ ${endpoint}: ${json.status} ${json.message}`);
  return null;
}

// ── ZIP / HTML 파싱 ──
export function parseZip(buf: Buffer): Array<{ name: string; data: Buffer }> {
  let eocd = -1;
  for (let i = buf.length - 22; i >= 0; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) {
      eocd = i;
      break;
    }
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

export function extractText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/g, " ")
    .replace(/<style[\s\S]*?<\/style>/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

interface DartListItem {
  rcept_dt: string;
  rcept_no: string;
  report_nm: string;
}

// ── 1) 시세·밸류에이션: growth-watchlist 또는 watchlist ──
interface StockEntry {
  code: string;
  per?: number | null;
  peg?: number | null;
  pbr?: number | null;
  current_price_at_scoring?: number;
  foreign_ownership?: number | null;
}

export async function collectValuation(code: string): Promise<CollectorBundle["valuation"]> {
  const dataDir = path.resolve("public/data");
  const candidates: Array<{ file: string; key: string }> = [
    { file: "growth-watchlist.json", key: "growth-watchlist" },
    { file: "watchlist.json", key: "watchlist" },
  ];
  for (const { file, key } of candidates) {
    try {
      const raw = fs.readFileSync(path.join(dataDir, file), "utf-8");
      const json = JSON.parse(raw);
      const list: StockEntry[] = Array.isArray(json) ? json : json.stocks ?? [];
      const s = list.find((x) => x.code === code);
      if (s) {
        return {
          source: key,
          price: s.current_price_at_scoring ?? null,
          per: s.per ?? null,
          peg: s.peg ?? null,
          pbr: s.pbr ?? null,
          foreign_ratio: s.foreign_ownership ?? null,
          dividend_yield: null,
        };
      }
    } catch {}
  }
  // 폴백: 워치리스트 미등재 종목(예: GS) → 네이버 m.stock 직접 조회
  return fetchValuationFromNaver(code);
}

async function fetchValuationFromNaver(
  code: string,
): Promise<CollectorBundle["valuation"]> {
  try {
    const url = `https://m.stock.naver.com/api/stock/${code}/integration`;
    const res = await fetch(url, { headers: { "user-agent": "Mozilla/5.0" } });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      totalInfos?: Array<{ code: string; value: string }>;
    };
    const get = (k: string) => json.totalInfos?.find((t) => t.code === k)?.value ?? "";
    const num = (s: string): number | null => {
      const cleaned = s.replace(/[,%원배]/g, "").trim();
      if (!cleaned) return null;
      const n = Number(cleaned);
      return isNaN(n) ? null : n;
    };
    return {
      source: "naver-m-stock",
      price: num(get("lastClosePrice")),
      per: num(get("per")),
      peg: null,
      pbr: num(get("pbr")),
      foreign_ratio: num(get("foreignRate")),
      dividend_yield: num(get("dividendYieldRatio")),
    };
  } catch {
    return null;
  }
}

// ── 2) 단일판매·공급계약 공백 ──
export async function collectSupplyContractGap(
  corp_code: string,
  lookback_days: number,
): Promise<CollectorBundle["supply_gap"]> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
    page_count: "100",
  });
  if (!list) return null;
  for (const item of list) {
    const nm = item.report_nm ?? "";
    if (nm.includes("단일판매") && nm.includes("공급계약")) {
      const d = item.rcept_dt;
      const iso = `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
      const days_ago = daysBetween(new Date(iso), today);
      return { last_date: iso, last_title: nm.trim(), days_ago, rcept_no: item.rcept_no };
    }
  }
  // 6개월 내 공시 없음 → 6개월+ 공백 표시
  return { last_date: null, last_title: null, days_ago: lookback_days, rcept_no: null };
}

// ── 3) 분기 영업이익률 (가장 최근 정기보고서 기준) ──
async function fetchLatestPeriodicReport(
  corp_code: string,
): Promise<{ rcept_no: string; report_nm: string; bsns_year: number; reprt_code: string } | null> {
  const today = new Date();
  const oneYrAgo = new Date(today.getTime() - 365 * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(oneYrAgo),
    end_de: fmtYmd(today),
    pblntf_ty: "A",
    page_count: "20",
  });
  if (!list) return null;
  for (const item of list) {
    const nm = item.report_nm.trim();
    let reprt_code: string | null = null;
    if (nm.includes("사업보고서")) reprt_code = "11011";
    else if (nm.includes("반기보고서")) reprt_code = "11012";
    else if (nm.includes("3분기")) reprt_code = "11014";
    else if (nm.includes("1분기")) reprt_code = "11013";
    if (!reprt_code) continue;
    // 보고서 명에서 (yyyy.mm) 추출
    const yearMatch = nm.match(/\((20\d{2})\./);
    const bsns_year = yearMatch ? Number(yearMatch[1]) : new Date().getFullYear() - 1;
    return { rcept_no: item.rcept_no, report_nm: nm, bsns_year, reprt_code };
  }
  return null;
}

export async function collectQuarterlyOpMargin(
  corp_code: string,
): Promise<CollectorBundle["op_margin"]> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  const list = await dartGet<{ account_nm: string; thstrm_amount: string; sj_div: string }>(
    "fnlttSinglAcntAll",
    {
      corp_code,
      bsns_year: String(report.bsns_year),
      reprt_code: report.reprt_code,
      fs_div: "CFS",
    },
  );
  if (!list) return null;
  let revenue = 0;
  let op_profit = 0;
  for (const row of list) {
    if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
    const name = row.account_nm?.trim() ?? "";
    const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
    if (isNaN(v)) continue;
    if (
      revenue === 0 &&
      (name === "매출액" || name === "수익(매출액)" || name === "영업수익" || name === "매출")
    ) {
      revenue = v;
    }
    if (op_profit === 0 && (name === "영업이익" || name === "영업이익(손실)")) {
      op_profit = v;
    }
  }
  if (revenue === 0) return null;
  const op_margin_pct = (op_profit / revenue) * 100;
  return {
    year: report.bsns_year,
    revenue,
    op_profit,
    op_margin_pct: Number(op_margin_pct.toFixed(2)),
    rcept_no: report.rcept_no,
  };
}

// ── 4) 임원·주요주주 거래 ──
export async function collectInsiderTrades(
  corp_code: string,
  lookback_days: number,
  name_keywords: string[] = [],
): Promise<Array<{ date: string; title: string; rcept_no: string }>> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
    page_count: "100",
  });
  if (!list) return [];
  const out: Array<{ date: string; title: string; rcept_no: string }> = [];
  for (const item of list) {
    const nm = item.report_nm ?? "";
    if (
      nm.includes("임원ㆍ주요주주") ||
      nm.includes("최대주주등소유주식") ||
      nm.includes("거래계획보고서") ||
      nm.includes("임원ㆍ주요주주특정증권")
    ) {
      // 키워드 필터 (있을 때만)
      if (name_keywords.length > 0) {
        if (!name_keywords.some((k) => nm.includes(k))) {
          // 제목에 키워드 없으면 일단 포함 (DART 제목에 보통 인물명 미포함이라 포괄)
        }
      }
      const d = item.rcept_dt;
      out.push({
        date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`,
        title: nm.trim(),
        rcept_no: item.rcept_no,
      });
    }
  }
  return out;
}

// ── 5) 5% 대량보유 변동 ──
export async function collectMajorHolderChanges(
  corp_code: string,
  lookback_days: number,
): Promise<Array<{ date: string; title: string; rcept_no: string }>> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
    page_count: "100",
  });
  if (!list) return [];
  const out: Array<{ date: string; title: string; rcept_no: string }> = [];
  for (const item of list) {
    const nm = item.report_nm ?? "";
    if (nm.includes("주식등의대량보유") || nm.includes("대량보유상황보고")) {
      const d = item.rcept_dt;
      out.push({
        date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`,
        title: nm.trim(),
        rcept_no: item.rcept_no,
      });
    }
  }
  return out;
}

// ── 6) 자사주 취득·소각·처분 ──
export async function collectStockBuybackEvents(
  corp_code: string,
  lookback_days: number,
): Promise<Array<{ date: string; title: string; rcept_no: string; type: string }>> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
    page_count: "100",
  });
  if (!list) return [];
  const out: Array<{ date: string; title: string; rcept_no: string; type: string }> = [];
  for (const item of list) {
    const nm = item.report_nm ?? "";
    let type: string | null = null;
    if (nm.includes("자기주식취득") || nm.includes("자기주식 취득")) type = "acquire";
    else if (nm.includes("주식소각") || nm.includes("자기주식소각")) type = "cancel";
    else if (nm.includes("자기주식처분") || nm.includes("자기주식 처분")) type = "dispose";
    if (!type) continue;
    const d = item.rcept_dt;
    out.push({
      date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`,
      title: nm.trim(),
      rcept_no: item.rcept_no,
      type,
    });
  }
  return out;
}

// ── 7) CB/BW/EB·증자 결정 ──
export async function collectCapitalIssuance(
  corp_code: string,
  lookback_days: number,
): Promise<Array<{ date: string; title: string; rcept_no: string }>> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
    page_count: "100",
  });
  if (!list) return [];
  const out: Array<{ date: string; title: string; rcept_no: string }> = [];
  for (const item of list) {
    const nm = item.report_nm ?? "";
    if (
      nm.includes("전환사채") ||
      nm.includes("신주인수권부사채") ||
      nm.includes("교환사채") ||
      nm.includes("유상증자")
    ) {
      const d = item.rcept_dt;
      out.push({
        date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`,
        title: nm.trim(),
        rcept_no: item.rcept_no,
      });
    }
  }
  return out;
}

// ── 8) 사업보고서 특수관계자 매입 비율 ──
async function fetchReportText(corp_code: string): Promise<{
  rcept_no: string;
  report_nm: string;
  bsns_year: number;
  reprt_code: string;
  text: string;
} | null> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  const url = `${DART_API}/document.xml?crtfc_key=${process.env.DART_API_KEY}&rcept_no=${report.rcept_no}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  const buf = Buffer.from(await res.arrayBuffer());
  const entries = parseZip(buf);
  const main = entries.reduce(
    (max, e) => (e.data.length > (max?.data.length || 0) ? e : max),
    null as null | { name: string; data: Buffer },
  );
  if (!main) return null;
  return { ...report, text: extractText(main.data.toString("utf-8")) };
}

function parseRelatedPartyPurchase(text: string, partner_name: string): number | null {
  // "재화의 매입" 행 숫자 시퀀스 파싱
  const m = text.match(
    /재화의\s*매입[,、\s]*특수관계자거래[\s]*((?:[0-9,]+\s+){2,12}[0-9,]+)/,
  );
  if (!m) return null;
  const nums = m[1]
    .trim()
    .split(/\s+/)
    .map((s) => Number(s.replace(/,/g, "")))
    .filter((n) => !isNaN(n));
  if (nums.length < 3) return null;
  // 합계 열 식별 (마지막 = 나머지 합 ±1%)
  const last = nums[nums.length - 1];
  const rest = nums.slice(0, -1);
  const sumRest = rest.reduce((a, b) => a + b, 0);
  let candidates: number[];
  if (last > 0 && Math.abs(sumRest - last) / Math.max(last, 1) < 0.01) {
    candidates = rest;
  } else {
    candidates = nums;
  }
  // partner_name 검증: 텍스트에 partner 이름이 등장하면 가장 큰 비영값을 partner 매입으로 간주
  if (!text.includes(partner_name)) return null;
  const nonZero = candidates.filter((n) => n > 0);
  if (!nonZero.length) return null;
  return Math.max(...nonZero);
}

function parseReportYear(text: string, fallback: number): number {
  const byDate = text.match(/(20\d{2})년\s*12월\s*31일/);
  if (byDate) return Number(byDate[1]);
  const byBsns = text.match(/(20\d{2})\.12/);
  if (byBsns) return Number(byBsns[1]);
  return fallback;
}

async function fetchAnnualRevenue(corp_code: string, year: number): Promise<number | null> {
  const list = await dartGet<{ account_nm: string; thstrm_amount: string; sj_div: string }>(
    "fnlttSinglAcntAll",
    {
      corp_code,
      bsns_year: String(year),
      reprt_code: "11011",
      fs_div: "CFS",
    },
  );
  if (!list) return null;
  for (const row of list) {
    if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
    const name = row.account_nm?.trim() ?? "";
    if (
      name === "매출액" ||
      name === "수익(매출액)" ||
      name === "영업수익" ||
      name === "매출"
    ) {
      const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
      if (v > 1e10) return v;
    }
  }
  return null;
}

export async function collectRelatedPartyPurchase(
  corp_code: string,
  partner_name: string,
): Promise<CollectorBundle["related_party"]> {
  const report = await fetchReportText(corp_code);
  if (!report) return null;
  const purchase = parseRelatedPartyPurchase(report.text, partner_name);
  const year = parseReportYear(report.text, report.bsns_year);
  const revenue = await fetchAnnualRevenue(corp_code, year);
  if (!purchase || !revenue) return null;
  const ratio_pct = (purchase / revenue) * 100;
  return {
    year,
    purchase,
    revenue,
    ratio_pct: Number(ratio_pct.toFixed(2)),
    rcept_no: report.rcept_no,
    report_nm: report.report_nm,
  };
}

// ── 9-1) 계열사 거래 매출 비율 (SK하이닉스 등 대기업 모니터링용) ──
async function fetchDocumentText(rcept_no: string): Promise<string | null> {
  const KEY = process.env.DART_API_KEY ?? "";
  if (!KEY) return null;
  const url = `${DART_API}/document.xml?crtfc_key=${KEY}&rcept_no=${rcept_no}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  const buf = Buffer.from(await res.arrayBuffer());
  const entries = parseZip(buf);
  if (!entries.length) return null;
  // 가장 큰 파일이 본문
  const main = entries.reduce(
    (max, e) => (e.data.length > (max?.data.length || 0) ? e : max),
    null as null | { name: string; data: Buffer },
  );
  if (!main) return null;
  return extractText(main.data.toString("utf-8"));
}

/** 내부 함수 — 지정 기간 [start, end] 동안 계열사 거래 합계·매출 비율 계산 */
async function fetchAffiliateTransactionsPeriod(
  corp_code: string,
  start: Date,
  end: Date,
): Promise<{
  ratio_pct: number | null;
  total_million: number;
  revenue_million: number | null;
  transaction_count: number;
  rcept_nos: string[];
} | null> {
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(start),
    end_de: fmtYmd(end),
    page_count: "100",
  });
  if (!list) return null;

  // 정정공시는 동일 거래라 중복 — 정정의 원공시 제외 후 가장 최신본만 채택
  // 1) 동일 corp/거래기간 그룹의 가장 최근 공시만 사용. 단순화: '[기재정정]'·'정정'·'변경' 표기는 신규 공시로 취급하되
  //    같은 날(rcept_dt) 같은 종류의 비-정정 공시가 있으면 정정본만 사용.
  const sameDayOriginal = new Set<string>(); // 같은 날 정정·원본이 동시에 있을 때 원본 제외용
  const candidates = list.filter(
    (item) =>
      (item.report_nm.includes("특수관계인") && item.report_nm.includes("내부거래")) ||
      item.report_nm.includes("동일인등출자계열회사") ||
      item.report_nm.includes("동일인 등 출자 계열회사"),
  );
  for (const item of candidates) {
    if (item.report_nm.includes("[기재정정]") || item.report_nm.includes("정정")) {
      // 같은 날 같은 거래 종류의 원본 공시는 제외
      const baseType = item.report_nm.includes("내부거래")
        ? "internal"
        : "affiliate";
      sameDayOriginal.add(`${item.rcept_dt}_${baseType}`);
    }
  }
  const targets = candidates.filter((item) => {
    if (item.report_nm.includes("[기재정정]") || item.report_nm.includes("정정")) return true;
    const baseType = item.report_nm.includes("내부거래") ? "internal" : "affiliate";
    return !sameDayOriginal.has(`${item.rcept_dt}_${baseType}`);
  });

  if (targets.length === 0) {
    return {
      ratio_pct: 0,
      total_million: 0,
      revenue_million: null,
      transaction_count: 0,
      rcept_nos: [],
    };
  }

  let totalMillion = 0;
  let revenueMillion = 0;
  const usedRceptNos: string[] = [];

  for (const item of targets) {
    const text = await fetchDocumentText(item.rcept_no);
    await sleep(300);
    if (!text) continue;

    // 매출액(A) 추출 — "직전사업연도매출액(A) 86,852,117"
    const revMatch = text.match(/직전사업연도매출액[^0-9]*([0-9,]{6,})/);
    if (revMatch) {
      const rev = Number(revMatch[1].replace(/,/g, ""));
      if (rev > revenueMillion) revenueMillion = rev;
    }

    // 패턴 ① 특수관계인 내부거래: "3. 총거래금액 <숫자>"
    const totalMatch = text.match(/3\.\s*총거래금액\s*([\d,]+)/);
    if (totalMatch) {
      const v = Number(totalMatch[1].replace(/,/g, ""));
      if (v > 0) {
        totalMillion += v;
        usedRceptNos.push(item.rcept_no);
        continue;
      }
    }

    // 패턴 ② 출자계열사 거래변경: "동일인 등 출자 계열회사와의 상품ㆍ용역 거래금액 ... 합계액(D=B+C) 매출액대비(D/A, %) <회사명> [매출] [매입] [합계] [%]"
    // 매출(B)+매입(C)=합계(D) 행을 찾아 매출+매입 합산. 정확한 행만 가져오기 위해 [%] 직후 수치를 검증
    const tableSection = text.match(
      /매출액\(B\)\s*매입액\(C\)\s*합계액\(D=B\+C\)\s*매출액대비\(D\/A,\s*%\)([\s\S]{0,500})/,
    );
    if (tableSection) {
      // 행 패턴: "회사명 [숫자/-] [숫자/-] [숫자] [퍼센트]%"
      const rows = Array.from(
        tableSection[1].matchAll(/([가-힣ㆍ\s\(\)\.\-A-Za-z0-9]+?)\s+([\d,\-]+)\s+([\d,\-]+)\s+([\d,]+)\s+([\d.]+)%/g),
      );
      let captured = false;
      for (const m of rows) {
        const sumStr = m[4].replace(/[,]/g, "");
        const sum = Number(sumStr);
        const pct = Number(m[5]);
        if (sum > 0 && pct > 0 && pct < 100) {
          totalMillion += sum;
          captured = true;
        }
      }
      if (captured) {
        usedRceptNos.push(item.rcept_no);
        continue;
      }
    }
    // fallback 패턴 제거 — 매출액 자체를 거래금액으로 오인하는 false-positive 방지
  }

  return {
    ratio_pct: revenueMillion > 0 ? Number(((totalMillion / revenueMillion) * 100).toFixed(3)) : null,
    total_million: totalMillion,
    revenue_million: revenueMillion || null,
    transaction_count: usedRceptNos.length,
    rcept_nos: usedRceptNos,
  };
}

/** 공용 래퍼 — 현재 기간 + 전년 동기 비교로 YoY 증가율까지 반환 */
export async function collectAffiliateTransactionRatio(
  corp_code: string,
  lookback_days: number,
): Promise<CollectorBundle["affiliate_transactions"]> {
  const today = new Date();
  const currentStart = new Date(today.getTime() - lookback_days * 86400_000);
  const prevEnd = new Date(currentStart.getTime() - 1);
  const prevStart = new Date(prevEnd.getTime() - lookback_days * 86400_000);

  const [current, previous] = await Promise.all([
    fetchAffiliateTransactionsPeriod(corp_code, currentStart, today),
    fetchAffiliateTransactionsPeriod(corp_code, prevStart, prevEnd),
  ]);
  if (!current) return null;

  const yoy_change_pp =
    current.ratio_pct != null && previous?.ratio_pct != null
      ? Number((current.ratio_pct - previous.ratio_pct).toFixed(3))
      : null;
  const yoy_change_pct =
    current.total_million > 0 && previous && previous.total_million > 0
      ? Number(
          (
            ((current.total_million - previous.total_million) / previous.total_million) *
            100
          ).toFixed(2),
        )
      : null;

  return {
    ratio_pct: current.ratio_pct,
    total_million: current.total_million,
    revenue_million: current.revenue_million,
    transaction_count: current.transaction_count,
    period_days: lookback_days,
    rcept_nos: current.rcept_nos,
    previous_ratio_pct: previous?.ratio_pct ?? null,
    previous_total_million: previous?.total_million ?? null,
    yoy_change_pp,
    yoy_change_pct,
  };
}

// ── 9-2) 최대주주·특수관계인 보유 비율 추적 ──
/** 가장 최근 정기보고서의 최대주주 현황에서 shareholder_name의 보유 비율 조회.
 *  분기·반기·사업보고서 갱신 시점에만 변동 감지 가능(실시간 X).
 */
export async function collectMajorShareholderRatio(
  corp_code: string,
  shareholder_name: string,
): Promise<CollectorBundle["major_shareholder"]> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  const list = await dartGet<{
    nm: string;
    bsis_posesn_stock_qota_rt: string;
    trmend_posesn_stock_qota_rt: string;
    relate: string;
  }>("hyslrSttus", {
    corp_code,
    bsns_year: String(report.bsns_year),
    reprt_code: report.reprt_code,
  });
  if (!list) return null;
  // shareholder_name 또는 relate='최대주주'인 행 우선
  const target =
    list.find((r) => r.nm?.includes(shareholder_name)) ??
    list.find((r) => r.relate?.includes("최대주주") && !r.relate?.includes("특수관계"));
  if (!target) {
    return {
      shareholder_name,
      year: report.bsns_year,
      start_ratio: null,
      end_ratio: null,
      change_pp: null,
      rcept_no: report.rcept_no,
    };
  }
  const start = Number(String(target.bsis_posesn_stock_qota_rt).replace(/,/g, ""));
  const end = Number(String(target.trmend_posesn_stock_qota_rt).replace(/,/g, ""));
  const change_pp =
    !isNaN(start) && !isNaN(end) ? Number((end - start).toFixed(3)) : null;
  return {
    shareholder_name: target.nm?.trim() ?? shareholder_name,
    year: report.bsns_year,
    start_ratio: isNaN(start) ? null : start,
    end_ratio: isNaN(end) ? null : end,
    change_pp,
    rcept_no: report.rcept_no,
  };
}

// ── 9-3) 자사주 소각 공시 공백 (최근 N일 내 '주식소각결정' 가장 최근 건) ──
export async function collectBuybackCancellationGap(
  corp_code: string,
  lookback_days: number,
): Promise<CollectorBundle["buyback_cancellation_gap"]> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  // 공시량이 많은 대기업(예: 현대차 1년 482건)은 page_count=100으로 부족 →
  // page_no로 순차 조회하면서 매칭 발견 시 즉시 종료. max_pages=10으로 1,000건까지 커버.
  const KEY = process.env.DART_API_KEY ?? "";
  const matches = (nm: string) =>
    nm.includes("주식소각결정") ||
    nm.includes("자기주식소각") ||
    (nm.includes("주요사항보고서") && nm.includes("소각"));

  const MAX_PAGES = 10;
  for (let page = 1; page <= MAX_PAGES; page++) {
    const url = new URL(`${DART_API}/list.json`);
    url.searchParams.set("crtfc_key", KEY);
    url.searchParams.set("corp_code", corp_code);
    url.searchParams.set("bgn_de", fmtYmd(since));
    url.searchParams.set("end_de", fmtYmd(today));
    url.searchParams.set("page_count", "100");
    url.searchParams.set("page_no", String(page));
    const res = await fetch(url.toString());
    if (!res.ok) break;
    const json = (await res.json()) as {
      status: string;
      list?: DartListItem[];
      total_page?: number;
    };
    if (json.status !== "000" || !json.list || json.list.length === 0) break;
    for (const item of json.list) {
      if (matches(item.report_nm ?? "")) {
        const d = item.rcept_dt;
        const iso = `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
        return {
          last_date: iso,
          last_title: item.report_nm.trim(),
          days_ago: daysBetween(new Date(iso), today),
          rcept_no: item.rcept_no,
        };
      }
    }
    if (json.total_page && page >= json.total_page) break;
  }
  // lookback_days 내 소각 공시 없음 → 공백 = lookback_days
  return {
    last_date: null,
    last_title: null,
    days_ago: lookback_days,
    rcept_no: null,
  };
}

// ── 9-4) 오너 일가 매도 탐지 ('최대주주등소유주식변동신고서' 본문 파싱) ──
/** 본문에서 특정 성명 섹션의 시간외매매·장내매도 감소 행을 추출 */
function parseFamilyTrades(
  text: string,
  familyNames: string[],
): Array<{ name: string; date: string; kind: string; prev: number; diff: number; post: number }> {
  const out: Array<{ name: string; date: string; kind: string; prev: number; diff: number; post: number }> = [];
  for (const name of familyNames) {
    // "성명 NAME 생년월일" 또는 "NAME 생년월일" (최대주주변동 신고서 표 내 구조 가변)
    const anchor = new RegExp(`(?:성명\\s+)?${name}\\s+생년월일`);
    const match = anchor.exec(text);
    if (!match) continue;
    const start = match.index;
    // 다음 인물 성명까지 또는 2500자
    const rest = text.slice(start + name.length);
    const nextIdx = rest.search(/(?:성명\s+)?[가-힣]{2,4}\s+생년월일/);
    const section = text.slice(
      start,
      start + name.length + (nextIdx > 50 ? nextIdx : 2500),
    );
    // 매도 행 패턴: "2026-04-13 시간외매매(-)|장내매도(-) 보통주식|종류주식 <전> -<diff> <후>"
    const tradeRe =
      /(\d{4}-\d{2}-\d{2})\s+(시간외매매\([-−]\)|장내매도\([-−]\)|장내매도|시간외매매|시간외처분|증여\([-−]\)|상속\([-−]\))\s+(?:보통주식|종류주식|주식)?\s*([\d,]+)\s+(-[\d,]+)\s+([\d,]+)/g;
    for (const m of section.matchAll(tradeRe)) {
      const diff = Number(m[4].replace(/,/g, ""));
      if (diff >= 0) continue; // 매도만
      out.push({
        name,
        date: m[1],
        kind: m[2].trim(),
        prev: Number(m[3].replace(/,/g, "")),
        diff,
        post: Number(m[5].replace(/,/g, "")),
      });
    }
  }
  return out;
}

export async function collectInsiderFamilyTrades(
  corp_code: string,
  lookback_days: number,
  family_names: string[],
): Promise<CollectorBundle["insider_family_trades"]> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
    page_count: "100",
  });
  if (!list) return null;
  // 최대주주등소유주식변동신고서 + 임원·주요주주특정증권등소유상황보고서 (본문에 일가 이름 포함된 것만)
  const relevant = list.filter((x) => {
    const nm = x.report_nm ?? "";
    return nm.includes("최대주주등소유주식") || nm.includes("임원ㆍ주요주주");
  });

  const trades: Array<{
    date: string;
    name: string;
    kind: string;
    prev_shares: number;
    diff_shares: number;
    post_shares: number;
    rcept_no: string;
  }> = [];
  const seen = new Set<string>(); // (name + date + diff) 중복 방지

  for (const item of relevant) {
    const text = await fetchDocumentText(item.rcept_no);
    await sleep(250);
    if (!text) continue;
    // 본문에 일가 이름 하나라도 나오지 않으면 스킵
    if (!family_names.some((n) => text.includes(n))) continue;
    const parsed = parseFamilyTrades(text, family_names);
    for (const t of parsed) {
      const key = `${t.name}_${t.date}_${t.diff}`;
      if (seen.has(key)) continue;
      seen.add(key);
      trades.push({
        date: t.date,
        name: t.name,
        kind: t.kind,
        prev_shares: t.prev,
        diff_shares: t.diff,
        post_shares: t.post,
        rcept_no: item.rcept_no,
      });
    }
  }

  const total_shares_sold = trades.reduce((s, t) => s + Math.abs(t.diff_shares), 0);
  return {
    lookback_days,
    total_shares_sold,
    total_amount_estimate: null, // 가격 정보 없음 — 향후 확장 가능
    trades: trades.sort((a, b) => (a.date < b.date ? 1 : -1)), // 최신순
  };
}

// ── 9) 외부 법인(모회사 등) 공시 추적 ──
export async function collectExternalCorpDisclosures(
  external_corp_code: string,
  lookback_days: number,
  keywords: string[] = [],
): Promise<Array<{ date: string; title: string; rcept_no: string }>> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code: external_corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
    page_count: "100",
  });
  if (!list) return [];
  const out: Array<{ date: string; title: string; rcept_no: string }> = [];
  for (const item of list) {
    const nm = item.report_nm ?? "";
    if (keywords.length === 0 || keywords.some((k) => nm.includes(k))) {
      const d = item.rcept_dt;
      out.push({
        date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`,
        title: nm.trim(),
        rcept_no: item.rcept_no,
      });
    }
  }
  return out;
}

// ── 9-5) 동종 그룹 평균 PBR 대비 프리미엄 (4대 금융지주 비교 등) ──
export function collectPeerPbrPremium(
  target_code: string,
  peer_codes: string[],
): CollectorBundle["peer_pbr_premium"] {
  if (!peer_codes.length) return null;
  const dataDir = path.resolve("public/data");
  const candidates = ["growth-watchlist.json", "watchlist.json"];
  let target_pbr: number | null = null;
  const peerPbrs: Array<{ code: string; pbr: number }> = [];
  const allCodes = new Set([target_code, ...peer_codes]);
  const found = new Set<string>();
  for (const file of candidates) {
    if (found.size === allCodes.size) break;
    try {
      const raw = fs.readFileSync(path.join(dataDir, file), "utf-8");
      const json = JSON.parse(raw);
      const list: StockEntry[] = Array.isArray(json) ? json : json.stocks ?? [];
      for (const s of list) {
        if (!allCodes.has(s.code) || found.has(s.code)) continue;
        if (typeof s.pbr !== "number") continue;
        if (s.code === target_code) target_pbr = s.pbr;
        else peerPbrs.push({ code: s.code, pbr: s.pbr });
        found.add(s.code);
      }
    } catch {}
  }
  if (target_pbr == null || peerPbrs.length === 0) {
    return {
      target_pbr,
      peer_avg_pbr: null,
      premium_pp: null,
      peers_used: peerPbrs.map((p) => p.code),
    };
  }
  const peer_avg_pbr = peerPbrs.reduce((s, p) => s + p.pbr, 0) / peerPbrs.length;
  const premium_pp = Number((target_pbr - peer_avg_pbr).toFixed(3));
  return {
    target_pbr,
    peer_avg_pbr: Number(peer_avg_pbr.toFixed(3)),
    premium_pp,
    peers_used: peerPbrs.map((p) => p.code),
  };
}

// ── 9-6) 분기배당 QoQ 변화율 (DART alotMatter 기반) ──
/** 가장 최근 정기보고서의 alotMatter API에서 주당 현금배당금(분기) 추출.
 *  분기배당 종목용 — 직전 분기 대비 변화율 계산.
 */
export async function collectDividendTrend(
  corp_code: string,
): Promise<CollectorBundle["dividend_trend"]> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  // 최근 보고서 + 직전 보고서(같은 사업연도 직전 분기 또는 전년도 동분기)
  const list = await dartGet<{
    se: string;
    thstrm: string;
    frmtrm: string;
    lwfr: string;
  }>("alotMatter", {
    corp_code,
    bsns_year: String(report.bsns_year),
    reprt_code: report.reprt_code,
  });
  if (!list) return null;

  // se(구분) 행이 다양: "주당 현금배당금(원)", "주당현금배당금(원)", "보통주" 등
  // 보통주 분기배당 우선 — 행 이름에 "현금배당" + "(원)" + "보통" 또는 "주당" 포함하는 첫 행
  const dividendRow = list.find((r) => {
    const se = (r.se ?? "").replace(/\s/g, "");
    return (
      (se.includes("주당현금배당금") || se.includes("주당배당금")) &&
      !se.includes("우선주") &&
      !se.includes("종류주")
    );
  }) ?? list.find((r) => (r.se ?? "").includes("주당") && (r.se ?? "").includes("배당"));

  if (!dividendRow) {
    return {
      latest_dps: null,
      prev_dps: null,
      qoq_change_pct: null,
      latest_record_date: null,
      rcept_no: report.rcept_no,
    };
  }
  const parseAmount = (s: string): number | null => {
    if (!s) return null;
    const n = Number(s.replace(/,/g, ""));
    return isNaN(n) ? null : n;
  };
  const latest = parseAmount(dividendRow.thstrm);
  const prev = parseAmount(dividendRow.frmtrm);
  const qoq_change_pct =
    latest != null && prev != null && prev > 0
      ? Number((((latest - prev) / prev) * 100).toFixed(2))
      : null;
  return {
    latest_dps: latest,
    prev_dps: prev,
    qoq_change_pct,
    latest_record_date: report.report_nm,
    rcept_no: report.rcept_no,
  };
}

// ── 9-7) 외국인 순매수 누적 추적 (네이버 dealTrendInfos 일별 누적) ──
/** 네이버 모바일 통합 API의 dealTrendInfos(최근 5거래일)를 매 실행마다 history JSON에 누적.
 *  최근 N(=20) 거래일 외국인 순매수량 합계를 반환.
 *  history 워밍업 기간(<10일) 동안은 null 반환.
 */
interface ForeignHistoryEntry {
  date: string;
  net_buy_shares: number;
  hold_ratio: number | null;
}

export async function collectForeignNetBuyTrend(
  code: string,
  window_days: number = 20,
  warmup_min: number = 10,
): Promise<CollectorBundle["foreign_net_buy"]> {
  const histDir = path.resolve("public/data/research/monitor/_history");
  if (!fs.existsSync(histDir)) fs.mkdirSync(histDir, { recursive: true });
  const histPath = path.join(histDir, `${code}-foreign.json`);
  let history: ForeignHistoryEntry[] = [];
  try {
    history = JSON.parse(fs.readFileSync(histPath, "utf-8")) as ForeignHistoryEntry[];
  } catch {}

  // 네이버 API 호출
  try {
    const url = `https://m.stock.naver.com/api/stock/${code}/integration`;
    const res = await fetch(url, { headers: { "user-agent": "Mozilla/5.0" } });
    if (res.ok) {
      const json = (await res.json()) as {
        dealTrendInfos?: Array<{
          bizdate: string;
          foreignerPureBuyQuant: string;
          foreignerHoldRatio?: string;
        }>;
      };
      for (const row of json.dealTrendInfos ?? []) {
        const ymd = row.bizdate;
        if (!/^\d{8}$/.test(ymd)) continue;
        const iso = `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`;
        const sharesRaw = String(row.foreignerPureBuyQuant ?? "").replace(/[+,]/g, "");
        const shares = Number(sharesRaw);
        if (isNaN(shares)) continue;
        const ratio = row.foreignerHoldRatio
          ? Number(String(row.foreignerHoldRatio).replace(/[%,]/g, ""))
          : null;
        const existing = history.find((h) => h.date === iso);
        if (existing) {
          existing.net_buy_shares = shares;
          existing.hold_ratio = ratio;
        } else {
          history.push({
            date: iso,
            net_buy_shares: shares,
            hold_ratio: isNaN(ratio as number) ? null : ratio,
          });
        }
      }
    }
  } catch (e) {
    console.warn(`  ⚠ ${code} 네이버 외국인 시세 조회 실패: ${(e as Error).message}`);
  }

  // 정렬 + 최근 60일 한도 유지
  history.sort((a, b) => (a.date < b.date ? -1 : 1));
  if (history.length > 60) history = history.slice(-60);
  fs.writeFileSync(histPath, JSON.stringify(history, null, 2), "utf-8");

  const recent = history.slice(-window_days);
  if (recent.length < warmup_min) {
    return {
      cumulative_20d_shares: null,
      days_count: recent.length,
      latest_date: recent.at(-1)?.date ?? null,
    };
  }
  const cumulative = recent.reduce((s, r) => s + r.net_buy_shares, 0);
  return {
    cumulative_20d_shares: cumulative,
    days_count: recent.length,
    latest_date: recent.at(-1)?.date ?? null,
  };
}

// ── 9-8) 분기 순이익 (분기 적자 전환 감지용) ──
/** fnlttSinglAcntAll에서 당기순이익 추출. 은행지주 등 매출 개념이 약한 업종용.
 *  account_id가 ifrs-full_ProfitLoss이면 가장 정확(은행: "연결당기순이익").
 *  fallback으로 account_nm 키워드 매칭.
 */
export async function collectQuarterlyNetIncome(
  corp_code: string,
): Promise<CollectorBundle["quarterly_net_income"]> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  const list = await dartGet<{
    account_nm: string;
    account_id?: string;
    thstrm_amount: string;
    sj_div: string;
  }>("fnlttSinglAcntAll", {
    corp_code,
    bsns_year: String(report.bsns_year),
    reprt_code: report.reprt_code,
    fs_div: "CFS",
  });
  if (!list) return null;
  let net_income: number | null = null;
  // 1순위: account_id == ifrs-full_ProfitLoss
  for (const row of list) {
    if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
    if (row.account_id === "ifrs-full_ProfitLoss") {
      const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
      if (!isNaN(v)) {
        net_income = v;
        break;
      }
    }
  }
  // 2순위: 계정명 매칭
  if (net_income == null) {
    const targets = [
      "당기순이익",
      "당기순이익(손실)",
      "분기순이익",
      "분기순이익(손실)",
      "반기순이익",
      "반기순이익(손실)",
      "연결당기순이익",
      "연결분기순이익",
      "연결반기순이익",
    ];
    for (const row of list) {
      if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
      const name = row.account_nm?.trim() ?? "";
      if (targets.includes(name)) {
        const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
        if (!isNaN(v)) {
          net_income = v;
          break;
        }
      }
    }
  }
  if (net_income == null) return null;
  // 단위는 원 — 억원 단위로 환산
  const period = `${report.bsns_year}-${
    report.reprt_code === "11013" ? "Q1" : report.reprt_code === "11012" ? "H1" : report.reprt_code === "11014" ? "Q3" : "FY"
  }`;
  return {
    period,
    net_income_billion: Math.round(net_income / 1e8),
    rcept_no: report.rcept_no,
  };
}

// ── 9-9) 자사주 매입 프로그램 종합 상태 ──
/** 취득결정·취득결과보고·소각결정 3종 공시를 통합 추적하여 가장 최근 활동일·상태·gap을 산출.
 *
 *  단순 `취득결정 후 경과일`보다 정밀한 이유:
 *  - 취득결정 공시 후 매입은 보통 2~3개월간 진행되므로 "60일 후속 부재"가 곧바로 매도 신호는 아님.
 *  - 매입 종료 후 취득결과보고서 또는 소각결정이 정상적으로 따라붙는데, 이 후속이 끊긴 시점이 신호.
 *  - 따라서 마지막 활동(어떤 종류든) 기준 days_ago + 단계별 status를 조합해 판단해야 함.
 *
 *  status 결정 규칙(가장 최근 공시 기준):
 *  - active: 마지막 공시가 취득결정·결과·소각 중 어떤 것이라도 30일 이내 → 진행 중
 *  - cooldown: 31~90일 → 정상 후속 대기 구간
 *  - post_cooldown: 91~180일 → 후속 발표 지연(warn)
 *  - abandoned: 181일+ → 프로그램 사실상 중단(bad)
 *
 *  대기업(공시량 많은 경우)을 위해 페이지네이션 사용 (max 10 페이지 = 1,000건).
 */
export async function collectBuybackProgramStatus(
  corp_code: string,
  lookback_days: number,
): Promise<CollectorBundle["buyback_program_status"]> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const KEY = process.env.DART_API_KEY ?? "";

  const classify = (nm: string): "acquire" | "result" | "cancel" | null => {
    if (nm.includes("주식소각결정") || nm.includes("자기주식소각")) return "cancel";
    if (nm.includes("주요사항보고서") && nm.includes("소각")) return "cancel";
    if (nm.includes("자기주식취득결과") || nm.includes("자기주식 취득 결과")) return "result";
    if (nm.includes("자사주취득결과")) return "result";
    if (
      nm.includes("자기주식취득") ||
      nm.includes("자기주식 취득") ||
      (nm.includes("주요사항보고서") && nm.includes("자기주식") && nm.includes("취득"))
    )
      return "acquire";
    return null;
  };

  let acquire_count = 0;
  let result_count = 0;
  let cancel_count = 0;
  let latest: {
    iso: string;
    title: string;
    kind: "acquire" | "result" | "cancel";
    rcept_no: string;
  } | null = null;

  const MAX_PAGES = 10;
  for (let page = 1; page <= MAX_PAGES; page++) {
    const url = new URL(`${DART_API}/list.json`);
    url.searchParams.set("crtfc_key", KEY);
    url.searchParams.set("corp_code", corp_code);
    url.searchParams.set("bgn_de", fmtYmd(since));
    url.searchParams.set("end_de", fmtYmd(today));
    url.searchParams.set("page_count", "100");
    url.searchParams.set("page_no", String(page));
    const res = await fetch(url.toString());
    if (!res.ok) break;
    const json = (await res.json()) as {
      status: string;
      list?: DartListItem[];
      total_page?: number;
    };
    if (json.status !== "000" || !json.list || json.list.length === 0) break;
    for (const item of json.list) {
      const kind = classify(item.report_nm ?? "");
      if (!kind) continue;
      if (kind === "acquire") acquire_count++;
      else if (kind === "result") result_count++;
      else if (kind === "cancel") cancel_count++;
      const d = item.rcept_dt;
      const iso = `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
      // DART list는 최신순이지만 페이지 간 순서 보장 위해 최신값 비교 유지
      if (!latest || iso > latest.iso) {
        latest = {
          iso,
          title: (item.report_nm ?? "").trim(),
          kind,
          rcept_no: item.rcept_no,
        };
      }
    }
    if (json.total_page && page >= json.total_page) break;
  }

  if (!latest) {
    return {
      last_date: null,
      last_title: null,
      last_kind: null,
      days_ago: lookback_days,
      status: "abandoned",
      rcept_no: null,
      acquire_count: 0,
      result_count: 0,
      cancel_count: 0,
    };
  }

  const days_ago = daysBetween(new Date(latest.iso), today);
  const status: "active" | "cooldown" | "post_cooldown" | "abandoned" =
    days_ago <= 30
      ? "active"
      : days_ago <= 90
        ? "cooldown"
        : days_ago <= 180
          ? "post_cooldown"
          : "abandoned";

  return {
    last_date: latest.iso,
    last_title: latest.title,
    last_kind: latest.kind,
    days_ago,
    status,
    rcept_no: latest.rcept_no,
    acquire_count,
    result_count,
    cancel_count,
  };
}

// ── 9-9b) 자사 corp_code DART 공시 키워드 매칭 ──
/** 자사 정성 신호(PF 손실·자본 규제 후퇴·주주환원 정책 변경 등) 자동 감지용.
 *  config의 disclosure_keyword_groups을 그대로 받아 그룹별로 매칭된 공시 리스트 반환.
 *  external_corp_disclosures와 차이: 외부 법인이 아닌 **자사 corp_code** 기준이며,
 *  하나의 공시가 여러 그룹 키워드와 매치될 수 있도록 multi-tag 구조.
 */
export async function collectDisclosureKeywordHits(
  corp_code: string,
  lookback_days: number,
  groups: Array<{ name: string; label: string; keywords: string[] }>,
): Promise<CollectorBundle["disclosure_keyword_hits"]> {
  if (!groups.length) {
    return { period_days: lookback_days, groups: {} };
  }
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const KEY = process.env.DART_API_KEY ?? "";

  // 결과 컨테이너 초기화
  const out: Record<
    string,
    {
      label: string;
      keywords: string[];
      hits: Array<{ date: string; title: string; rcept_no: string; matched: string[] }>;
    }
  > = {};
  for (const g of groups) {
    out[g.name] = { label: g.label, keywords: g.keywords, hits: [] };
  }

  const MAX_PAGES = 10;
  // 동일 rcept_no가 여러 그룹에 매치될 수 있으므로 그룹별 dedup만
  const seenByGroup: Record<string, Set<string>> = {};
  for (const g of groups) seenByGroup[g.name] = new Set();

  for (let page = 1; page <= MAX_PAGES; page++) {
    const url = new URL(`${DART_API}/list.json`);
    url.searchParams.set("crtfc_key", KEY);
    url.searchParams.set("corp_code", corp_code);
    url.searchParams.set("bgn_de", fmtYmd(since));
    url.searchParams.set("end_de", fmtYmd(today));
    url.searchParams.set("page_count", "100");
    url.searchParams.set("page_no", String(page));
    const res = await fetch(url.toString());
    if (!res.ok) break;
    const json = (await res.json()) as {
      status: string;
      list?: DartListItem[];
      total_page?: number;
    };
    if (json.status !== "000" || !json.list || json.list.length === 0) break;
    for (const item of json.list) {
      const nm = item.report_nm ?? "";
      const d = item.rcept_dt;
      const iso = `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
      for (const g of groups) {
        const matched = g.keywords.filter((k) => nm.includes(k));
        if (matched.length === 0) continue;
        if (seenByGroup[g.name].has(item.rcept_no)) continue;
        seenByGroup[g.name].add(item.rcept_no);
        out[g.name].hits.push({
          date: iso,
          title: nm.trim(),
          rcept_no: item.rcept_no,
          matched,
        });
      }
    }
    if (json.total_page && page >= json.total_page) break;
  }

  // 각 그룹 hits을 최신순 정렬
  for (const name of Object.keys(out)) {
    out[name].hits.sort((a, b) => (a.date < b.date ? 1 : -1));
  }

  return { period_days: lookback_days, groups: out };
}

// ── 9-10) 보통주-우선주 디스카운트율 (네이버 종가 기반, 우선주 모니터링용) ──
/** 두 종목의 전일 종가를 네이버 m.stock에서 직접 받아 디스카운트율 계산.
 *  discount_pct = (1 - pref_price / common_price) * 100 — 양수일수록 우선주가 더 저평가.
 */
async function fetchNaverLastClose(
  code: string,
): Promise<{ price: number | null; as_of: string | null }> {
  try {
    const url = `https://m.stock.naver.com/api/stock/${code}/integration`;
    const res = await fetch(url, { headers: { "user-agent": "Mozilla/5.0" } });
    if (!res.ok) return { price: null, as_of: null };
    const json = (await res.json()) as {
      totalInfos?: Array<{ code: string; key: string; value: string }>;
      dealTrendInfos?: Array<{ bizdate: string }>;
    };
    const lastClose = (json.totalInfos ?? []).find((t) => t.code === "lastClosePrice");
    if (!lastClose) return { price: null, as_of: null };
    const price = Number(String(lastClose.value).replace(/[,\s]/g, ""));
    const ymd = json.dealTrendInfos?.[0]?.bizdate;
    const as_of =
      ymd && /^\d{8}$/.test(ymd) ? `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}` : null;
    return { price: isNaN(price) ? null : price, as_of };
  } catch (e) {
    console.warn(`  ⚠ ${code} 네이버 종가 조회 실패: ${(e as Error).message}`);
    return { price: null, as_of: null };
  }
}

export async function collectPrefDiscount(
  pref_code: string,
  common_code: string,
): Promise<CollectorBundle["pref_discount"]> {
  const [pref, common] = await Promise.all([
    fetchNaverLastClose(pref_code),
    fetchNaverLastClose(common_code),
  ]);
  const discount_pct =
    common.price && pref.price && common.price > 0
      ? Number((((common.price - pref.price) / common.price) * 100).toFixed(2))
      : null;
  return {
    common_code,
    pref_code,
    common_price: common.price,
    pref_price: pref.price,
    discount_pct,
    as_of: pref.as_of ?? common.as_of,
  };
}

// ── 9-11) 별도 재무제표 분기 순이익 (지주사 자체 이익 추적) ──
/** fnlttSinglAcntAll에서 fs_div=OFS(별도)로 당기순이익 추출.
 *  지주사가 자회사 배당으로 자체 배당 여력을 유지하는지 모니터링하는 용도.
 *  연결 순이익이 호조여도 별도 순이익이 적자 전환하면 향후 배당 압박 신호.
 */
export async function collectSeparateQuarterlyIncome(
  corp_code: string,
): Promise<CollectorBundle["separate_quarterly_income"]> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  const list = await dartGet<{
    account_nm: string;
    account_id?: string;
    thstrm_amount: string;
    sj_div: string;
  }>("fnlttSinglAcntAll", {
    corp_code,
    bsns_year: String(report.bsns_year),
    reprt_code: report.reprt_code,
    fs_div: "OFS",
  });
  if (!list) return null;
  let net_income: number | null = null;
  for (const row of list) {
    if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
    if (row.account_id === "ifrs-full_ProfitLoss") {
      const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
      if (!isNaN(v)) {
        net_income = v;
        break;
      }
    }
  }
  if (net_income == null) {
    const targets = [
      "당기순이익",
      "당기순이익(손실)",
      "분기순이익",
      "분기순이익(손실)",
      "반기순이익",
      "반기순이익(손실)",
    ];
    for (const row of list) {
      if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
      const name = row.account_nm?.trim() ?? "";
      if (targets.includes(name)) {
        const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
        if (!isNaN(v)) {
          net_income = v;
          break;
        }
      }
    }
  }
  if (net_income == null) return null;
  const period = `${report.bsns_year}-${
    report.reprt_code === "11013"
      ? "Q1"
      : report.reprt_code === "11012"
        ? "H1"
        : report.reprt_code === "11014"
          ? "Q3"
          : "FY"
  }`;
  return {
    year: report.bsns_year,
    period,
    net_income,
    net_income_billion: Math.round(net_income / 1e8),
    rcept_no: report.rcept_no,
  };
}

// ── 9-13) 원유 시세 (Brent 기반, 정유 매크로 트리거용) ──
/** Yahoo Finance unofficial chart API에서 Brent (BZ=F) 일별 종가 fetch.
 *  GS의 두바이유 70달러 트리거를 Brent로 근사 (보통 ±2달러 swing).
 *  최근 7거래일 평균을 함께 반환해 단발성 swing 노이즈를 완충.
 */
export async function collectCrudeOilPrice(): Promise<CollectorBundle["crude_oil_price"]> {
  try {
    const url =
      "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?range=1mo&interval=1d";
    const res = await fetch(url, { headers: { "user-agent": "Mozilla/5.0" } });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      chart?: {
        result?: Array<{
          meta?: { symbol?: string };
          timestamp?: number[];
          indicators?: { quote?: Array<{ close?: Array<number | null> }> };
        }>;
      };
    };
    const result = json.chart?.result?.[0];
    if (!result) return null;
    const ts = result.timestamp ?? [];
    const closes = result.indicators?.quote?.[0]?.close ?? [];
    const series: Array<{ date: string; close: number }> = [];
    for (let i = 0; i < ts.length; i++) {
      const c = closes[i];
      if (c == null || isNaN(c)) continue;
      const date = new Date(ts[i] * 1000).toISOString().slice(0, 10);
      series.push({ date, close: Number(c.toFixed(2)) });
    }
    if (series.length === 0) return null;
    const last7 = series.slice(-7);
    const avg_7d = last7.reduce((s, x) => s + x.close, 0) / last7.length;
    const latest = series.at(-1)!;
    return {
      source: "yahoo-finance",
      symbol: result.meta?.symbol ?? "BZ=F",
      latest_close: latest.close,
      latest_date: latest.date,
      avg_7d: Number(avg_7d.toFixed(2)),
      series: last7,
    };
  } catch (e) {
    console.warn(`  ⚠ 원유 시세 조회 실패: ${(e as Error).message}`);
    return null;
  }
}

// ── 9-12) 자체 corp 채무보증결정 공시 (자회사 보증 추적) ──
/** 지주사가 자회사를 위해 발행하는 채무보증결정 공시를 lookback_days 내 카운트.
 *  자회사 부실화 시 모회사 위험 전이 신호.
 */
export async function collectDebtGuaranteeEvents(
  corp_code: string,
  lookback_days: number,
): Promise<Array<{ date: string; title: string; rcept_no: string }>> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
    page_count: "100",
  });
  if (!list) return [];
  const out: Array<{ date: string; title: string; rcept_no: string }> = [];
  for (const item of list) {
    const nm = item.report_nm ?? "";
    if (nm.includes("타인에대한채무보증") || nm.includes("채무보증결정")) {
      const d = item.rcept_dt;
      out.push({
        date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`,
        title: nm.trim(),
        rcept_no: item.rcept_no,
      });
    }
  }
  return out;
}

// ── 10) Google News RSS + 헤드라인 시그널 분류 ──
/** 헤드라인의 부정 시그널 키워드 매핑. 현재 관찰 대상 종목에 광범위 적용. */
const HEADLINE_SIGNALS = {
  // 강한 부정: 확정적 사건·실행 완료 — 매도 트리거에 근접
  bad: [
    "공급 중단", "거래 중단", "수주 취소", "수주 실패", "공급 실패",
    "퀄 실패", "양산 실패", "라인 폐쇄", "점유율 역전",
    "블록딜 완료", "매각 완료", "분사 결정", "분사 확정",
    "계약 해지", "공장 폐쇄", "급락", "폭락",
  ],
  // 약한 부정: 진행 중·우려 신호
  warn: [
    "추격", "역전", "감소", "하락", "축소", "둔화", "약세", "부진",
    "이탈", "우려", "차질", "연기", "지연", "후퇴", "밀림", "경쟁 격화",
    "규제", "제재", "보조금 축소", "투자 축소", "투자 연기",
    "실망", "엇갈", "혼조", "불투명",
  ],
};

function classifyHeadline(title: string): {
  severity: "info" | "warn" | "bad";
  signals: string[];
} {
  const bad = HEADLINE_SIGNALS.bad.filter((k) => title.includes(k));
  if (bad.length > 0) return { severity: "bad", signals: bad };
  const warn = HEADLINE_SIGNALS.warn.filter((k) => title.includes(k));
  if (warn.length > 0) return { severity: "warn", signals: warn };
  return { severity: "info", signals: [] };
}

// ── ClinicalTrials.gov 임상 파이프라인 status 추적 ──
//
// 종목별 캐시(`.cache/clinical-pipeline-{code}.json`)에 마지막 조회 결과 보존.
// 신규 조회 시 NCT ID별 status diff → 최근 30일 누적 변경분만 카운트.
//
// 기존 screen-bio.ts:fetchClinicalTrials() 패턴을 따르되, 캐시 비교 + 변경분
// 누적이라는 모니터 목적에 맞게 단순화.
export async function collectClinicalPipelineStatus(
  stock_code: string,
  sponsor_keywords: string[],
): Promise<CollectorBundle["clinical_pipeline"]> {
  if (!sponsor_keywords || sponsor_keywords.length === 0) return null;

  const cacheDir = path.resolve(".cache");
  const cachePath = path.join(cacheDir, `clinical-pipeline-${stock_code}.json`);
  if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir, { recursive: true });

  // 1. 이전 캐시 로드 (status 비교 + 30일 윈도우 변경분 누적)
  type CacheTrial = {
    nct_id: string;
    title: string;
    indication: string;
    phase: string;
    status: string;
    last_update_date: string;
  };
  type CacheChange = {
    nct_id: string;
    title: string;
    from_status: string;
    to_status: string;
    date: string;
  };
  type CachePayload = { trials: CacheTrial[]; changes: CacheChange[] };
  let prev: CachePayload | null = null;
  try {
    if (fs.existsSync(cachePath)) {
      prev = JSON.parse(fs.readFileSync(cachePath, "utf-8")) as CachePayload;
    }
  } catch {
    prev = null;
  }

  // 2. ClinicalTrials.gov v2 API 조회 (스폰서 키워드별)
  const seen = new Set<string>();
  const trials: CacheTrial[] = [];
  const today = new Date().toISOString().slice(0, 10);

  for (const kw of sponsor_keywords) {
    const url = `https://clinicaltrials.gov/api/v2/studies?query.spons=${encodeURIComponent(
      kw,
    )}&pageSize=50&fields=protocolSection.identificationModule|protocolSection.statusModule|protocolSection.designModule|protocolSection.conditionsModule`;
    try {
      const res = await fetch(url);
      if (!res.ok) {
        console.warn(`  ⚠ ClinicalTrials.gov 조회 실패 (${kw}): ${res.status}`);
        continue;
      }
      const json = (await res.json()) as { studies?: unknown[] };
      const studies = (json.studies ?? []) as Array<{
        protocolSection?: {
          identificationModule?: { nctId?: string; briefTitle?: string };
          statusModule?: {
            overallStatus?: string;
            lastUpdatePostDateStruct?: { date?: string };
          };
          designModule?: { phases?: string[] };
          conditionsModule?: { conditions?: string[] };
        };
      }>;
      for (const s of studies) {
        const proto = s.protocolSection ?? {};
        const id = proto.identificationModule ?? {};
        const status = proto.statusModule ?? {};
        const design = proto.designModule ?? {};
        const conditions = proto.conditionsModule ?? {};
        const nctId = id.nctId ?? "";
        if (!nctId || seen.has(nctId)) continue;
        seen.add(nctId);
        const phases = design.phases ?? [];
        const phase = phases.includes("PHASE3")
          ? "PHASE3"
          : phases.includes("PHASE2")
            ? "PHASE2"
            : phases[0] ?? "N/A";
        trials.push({
          nct_id: nctId,
          title: id.briefTitle ?? "",
          indication: (conditions.conditions ?? []).join(", "),
          phase,
          status: status.overallStatus ?? "",
          last_update_date: status.lastUpdatePostDateStruct?.date ?? "",
        });
      }
    } catch (e) {
      console.warn(`  ⚠ ClinicalTrials.gov 예외 (${kw}):`, (e as Error).message);
    }
    await sleep(500);
  }

  // 3. 이전 캐시와 status 비교 → 신규 변경분 추출
  const newChanges: CacheChange[] = [];
  if (prev?.trials) {
    const prevMap = new Map(prev.trials.map((t) => [t.nct_id, t]));
    for (const t of trials) {
      const before = prevMap.get(t.nct_id);
      if (before && before.status && t.status && before.status !== t.status) {
        newChanges.push({
          nct_id: t.nct_id,
          title: t.title,
          from_status: before.status,
          to_status: t.status,
          date: today,
        });
      }
    }
  }

  // 4. 30일 윈도우로 변경 이력 통합
  const cutoff = new Date(Date.now() - 30 * 86400_000);
  const allChanges = [...(prev?.changes ?? []), ...newChanges].filter((c) => {
    const d = new Date(c.date);
    return !isNaN(d.getTime()) && d >= cutoff;
  });
  // 동일 nct_id+from→to 중복 제거 (오래된 것 우선)
  const seenChange = new Set<string>();
  const dedupedChanges: CacheChange[] = [];
  for (const c of allChanges) {
    const key = `${c.nct_id}|${c.from_status}|${c.to_status}`;
    if (seenChange.has(key)) continue;
    seenChange.add(key);
    dedupedChanges.push(c);
  }

  // 5. 캐시 저장 (다음 실행 비교용)
  try {
    fs.writeFileSync(
      cachePath,
      JSON.stringify({ trials, changes: dedupedChanges, updated_at: today }, null, 2),
      "utf-8",
    );
  } catch (e) {
    console.warn(`  ⚠ 캐시 저장 실패 (${cachePath}):`, (e as Error).message);
  }

  return {
    sponsor_keywords,
    trials,
    count: trials.length,
    recent_changes_30d: {
      count: dedupedChanges.length,
      changes: dedupedChanges,
    },
  };
}

export async function collectNewsHits(
  keywords: string[],
  lookback_days: number,
): Promise<
  Array<{
    keyword: string;
    date: string;
    title: string;
    url: string;
    severity: "info" | "warn" | "bad";
    signals: string[];
  }>
> {
  const hits: Array<{
    keyword: string;
    date: string;
    title: string;
    url: string;
    severity: "info" | "warn" | "bad";
    signals: string[];
  }> = [];
  const cutoff = new Date(Date.now() - lookback_days * 86400_000);
  for (const kw of keywords) {
    const url = `https://news.google.com/rss/search?q=${encodeURIComponent(kw)}&hl=ko&gl=KR&ceid=KR:ko`;
    try {
      const res = await fetch(url, { headers: { "user-agent": "Mozilla/5.0" } });
      if (!res.ok) continue;
      const xml = await res.text();
      const items = Array.from(xml.matchAll(/<item>([\s\S]*?)<\/item>/g));
      for (const m of items.slice(0, 10)) {
        const block = m[1];
        const title = block.match(/<title>(?:<!\[CDATA\[)?([^<\]]+)/)?.[1]?.trim();
        const link = block.match(/<link>([^<]+)<\/link>/)?.[1]?.trim();
        const pub = block.match(/<pubDate>([^<]+)<\/pubDate>/)?.[1]?.trim();
        if (!title || !pub) continue;
        const pubDate = new Date(pub);
        if (isNaN(pubDate.getTime()) || pubDate < cutoff) continue;
        const { severity, signals } = classifyHeadline(title);
        hits.push({
          keyword: kw,
          date: pubDate.toISOString().slice(0, 10),
          title,
          url: link ?? "",
          severity,
          signals,
        });
      }
    } catch (e) {
      console.warn(`  ⚠ 뉴스 조회 실패 (${kw}):`, (e as Error).message);
    }
    await sleep(500);
  }
  return hits;
}

// ── 금융사 특화 지표 (NIM·NPL·ROE) ──
//
// KB금융지주 등 은행지주의 분기·사업보고서 본문(HTML)에서 NIM/NPL/연체율/CCR을
// 정규식으로 추출. DART fnlttSinglAcntAll에 표준필드가 없는 지표라 본문 파싱이 필수.
//
// 주의:
// - 본문 형식은 회사·연도별로 미세하게 달라질 수 있어 정규식이 깨질 위험 있음.
// - 추출 실패 시 모든 값 null 반환 → metric value=null → tone="neutral"로 자동 강등.
// - source_text(매칭 컨텍스트 100자)를 항상 저장해 사후 진단 용이.

/** 그룹/은행 NIM 추출 — KB금융 사업·분기보고서 본문 형식에 맞춘 정규식 모음.
 *  진단(scripts/diagnose-kb-report.ts 2026-04-25) 결과:
 *  - 그룹 NIM: `NIM(은행+카드) 주2) 2.26 2.37 2.44` 표 형식 (% 부호 없음)
 *  - 은행 NIM: `명목순이자마진(NIM) 1.74 1.78 1.83` 표 형식 (% 부호 없음)
 *  - 또한 분기보고서에서는 `그룹 NIM 1.99%` / `은행 NIM 1.77%` 서술형도 등장 가능.
 *  여러 패턴을 우선순위로 시도, 첫 매칭 사용. */
function extractNim(text: string): {
  group_nim_pct: number | null;
  bank_nim_pct: number | null;
  source_text: string | null;
} {
  // 패턴 ① (그룹·연결): NIM(은행+카드) 표 형식이 KB의 그룹 통합 NIM
  const groupPatterns: RegExp[] = [
    // 표 형식 우선 — KB 사업보고서: "NIM(은행+카드) 주2) 2.26"
    // 괄호와 첫 수치 사이에 "주2)" 같은 비숫자+숫자 혼합 토큰이 끼어있어
    // [^0-9]만으로는 매칭이 끊긴다 → \s+\S+\s+ (공백·비공백·공백 1토큰) 사용.
    /NIM\s*\((?!순이자마진)[^)]{1,15}\)\s+\S+\s+([0-9]\.[0-9]{1,2})/,
    // 서술형 + 괄호: "NIM(은행+카드)는 1.99%" 등 lazy match
    /NIM\s*\((?!순이자마진)[^)]{1,15}\)[\s\S]{0,15}?([0-9]\.[0-9]{1,2})\s*%/,
    // 그룹/연결 수식어가 NIM 앞에 — KB 분기보고서: "그룹 NIM 1.99%"
    /(?:그룹|연결|지주)\s*(?:은\s*)?NIM[^\d%]{0,20}([0-9]\.[0-9]{1,2})\s*%/,
    /(?:그룹|연결|지주)\s*순이자마진[^\d%]{0,30}([0-9]\.[0-9]{1,2})\s*%/,
    /순이자마진\s*\(NIM\)\s*[은는]?\s*([0-9]\.[0-9]{1,2})\s*%/,
    /NIM\s*\(순이자마진\)\s*[은는:]?\s*([0-9]\.[0-9]{1,2})\s*%/,
  ];
  // 패턴 ② (은행 단독): 명목순이자마진(NIM) 표 형식이 KB국민은행 NIM
  const bankPatterns: RegExp[] = [
    // 표 형식 우선 — KB 사업보고서: "명목순이자마진(NIM) 1.74"
    /명목순이자마진\s*\(\s*NIM\s*\)[^0-9]{0,5}([0-9]\.[0-9]{1,2})/,
    /(?:국민은행|은행)\s*(?:은\s*)?NIM[^\d%]{0,20}([0-9]\.[0-9]{1,2})\s*%/,
    /(?:국민은행|은행)\s*순이자마진[^\d%]{0,30}([0-9]\.[0-9]{1,2})\s*%/,
  ];
  let groupMatch: RegExpMatchArray | null = null;
  for (const re of groupPatterns) {
    groupMatch = text.match(re);
    if (groupMatch) break;
  }
  let bankMatch: RegExpMatchArray | null = null;
  for (const re of bankPatterns) {
    bankMatch = text.match(re);
    if (bankMatch) break;
  }
  // source_text — 우선순위: 그룹 매칭 컨텍스트, 없으면 은행 매칭 컨텍스트
  let sourceText: string | null = null;
  if (groupMatch && groupMatch.index !== undefined) {
    const start = Math.max(0, groupMatch.index - 30);
    sourceText = text.slice(start, start + 130).trim();
  } else if (bankMatch && bankMatch.index !== undefined) {
    const start = Math.max(0, bankMatch.index - 30);
    sourceText = text.slice(start, start + 130).trim();
  }
  return {
    group_nim_pct: groupMatch ? Number(groupMatch[1]) : null,
    bank_nim_pct: bankMatch ? Number(bankMatch[1]) : null,
    source_text: sourceText,
  };
}

/** 시장 통계·자회사 수치·변화율(%p) 컨텍스트 — 매칭 주변에 이 키워드가 보이면 skip.
 *  진단(2026-04-25) 결과 KB 사업보고서 본문에 두 종류의 잘못된 매칭이 발생:
 *  ① "은행권의 기업대출(원화대출금)연체율은 0.59%" — 시장 평균 통계
 *  ② "원화대출 연체율은 매분기 0.01%p씩 감소" — 변화율(절대값 아님)
 *  KB 자체 데이터(표 형식 "0.28 0.29 0.22")가 우선되도록 negative match 적용. */
const MARKET_STAT_SKIP_KEYWORDS = [
  "은행권",
  "은행권의",
  "기업대출(원화대출금)",
  "원화대출금)연체율",
  "시장 평균",
  "전 은행",
  "신용카드자산",
  "원화대출 연체율",
  "%p",       // 변화율 단위 — 절대 비율 아님
  "감소",
  "증가한",
  "상승한",
  "하락한",
];

/** 패턴 배열을 우선순위로 시도하면서, skip context 키워드가 매칭 주변에 보이면 다음 매칭 탐색.
 *  반환: 첫 "안전한" 매칭 또는 null. */
function findSafeMatch(
  text: string,
  patterns: RegExp[],
  skipKeywords: string[],
  contextWindow = 60,
): RegExpExecArray | null {
  for (const pattern of patterns) {
    const flags = pattern.flags.includes("g") ? pattern.flags : pattern.flags + "g";
    const re = new RegExp(pattern.source, flags);
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const start = Math.max(0, m.index - contextWindow);
      const ctx = text.slice(start, m.index + m[0].length + 10);
      if (!skipKeywords.some((k) => ctx.includes(k))) {
        return m;
      }
    }
  }
  return null;
}

/** NPL 비율 / 연체율 / CCR 추출.
 *  진단(2026-04-25) 결과:
 *  - NPL은 표 형식 `NPL비율 0.99 1.07 1.01` (% 없음) + 서술형 `0.99%` 모두 등장 — % optional.
 *  - 연체율은 시장 평균(은행권의 ... 0.59%)이 우선 매칭되는 문제 → skip 로직 적용.
 *  - CCR은 KB 본문에 직접 등장 안 함 (대손충당금전입액 만 등장 — 비율 아님). 대부분 null. */
function extractNplCcr(text: string): {
  npl_ratio_pct: number | null;
  delinquency_pct: number | null;
  ccr_pct: number | null;
  source_text: string | null;
} {
  const nplPatterns: RegExp[] = [
    // 표 형식: "NPL비율 0.99 1.07 1.01" (% 없음, 공백으로 구분)
    /NPL\s*비율\s+([0-9]\.[0-9]{1,2})(?:\s|$)/,
    // 서술형: "NPL비율... 0.99%" / "고정이하여신비율 0.99%"
    /(?:NPL\s*비율|고정이하여신비율)[^\d%]{0,20}([0-9]\.[0-9]{1,2})\s*%/,
  ];
  const delinquencyPatterns: RegExp[] = [
    // 표 형식 우선 — KB 자체 데이터: "연체율 총대출채권기준 0.28 0.29 0.22" (카테고리 강제)
    /연체율\s+(?:총대출채권기준|기업대출기준|가계대출기준)\s+([0-9]\.[0-9]{1,2})(?:\s|$)/,
    // 서술형 (% 있음): skip 키워드(원화대출·시장 평균·변화율)에 걸리지 않은 첫 매칭
    /연체율[^\d%]{0,20}([0-9]\.[0-9]{1,2})\s*%/,
  ];
  const ccrPatterns: RegExp[] = [
    /(?:CCR|대손충당금전입비율|대손비용률)[^\d%]{0,20}([0-9]\.[0-9]{1,2})\s*%/,
  ];

  const nplMatch = findSafeMatch(text, nplPatterns, MARKET_STAT_SKIP_KEYWORDS);
  const delMatch = findSafeMatch(text, delinquencyPatterns, MARKET_STAT_SKIP_KEYWORDS);
  const ccrMatch = findSafeMatch(text, ccrPatterns, MARKET_STAT_SKIP_KEYWORDS);

  let sourceText: string | null = null;
  const firstMatch = nplMatch ?? delMatch ?? ccrMatch;
  if (firstMatch) {
    const start = Math.max(0, firstMatch.index - 30);
    sourceText = text.slice(start, start + 130).trim();
  }
  return {
    npl_ratio_pct: nplMatch ? Number(nplMatch[1]) : null,
    delinquency_pct: delMatch ? Number(delMatch[1]) : null,
    ccr_pct: ccrMatch ? Number(ccrMatch[1]) : null,
    source_text: sourceText,
  };
}

/** 그룹 NIM + 은행 NIM (지주 본문이 우선, 누락분은 bank_corp_code 본문에서 보강) */
export async function collectNetInterestMargin(
  corp_code: string,
  bank_corp_code?: string,
): Promise<CollectorBundle["net_interest_margin"]> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  const text = await fetchDocumentText(report.rcept_no);
  if (!text) return null;
  const groupResult = extractNim(text);

  let bankNim = groupResult.bank_nim_pct;
  let bankSource: string | null = null;

  // 그룹 본문에 은행 NIM이 빠져있으면 자회사 본문에서 보강
  if (bankNim == null && bank_corp_code) {
    const bankReport = await fetchLatestPeriodicReport(bank_corp_code);
    if (bankReport) {
      const bankText = await fetchDocumentText(bankReport.rcept_no);
      if (bankText) {
        const bankResult = extractNim(bankText);
        bankNim = bankResult.bank_nim_pct ?? bankResult.group_nim_pct; // 은행 본문은 NIM이 그냥 "NIM"으로 적힐 수 있음
        bankSource = bankResult.source_text;
      }
    }
  }

  const period = `${report.bsns_year}-${
    report.reprt_code === "11013"
      ? "Q1"
      : report.reprt_code === "11012"
        ? "H1"
        : report.reprt_code === "11014"
          ? "Q3"
          : "FY"
  }`;
  return {
    group_nim_pct: groupResult.group_nim_pct,
    bank_nim_pct: bankNim,
    period,
    rcept_no: report.rcept_no,
    source_text: groupResult.source_text ?? bankSource,
  };
}

/** NPL 비율·연체율·CCR (지주 본문에서 추출) */
export async function collectNplRatio(
  corp_code: string,
): Promise<CollectorBundle["npl_ratio"]> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  const text = await fetchDocumentText(report.rcept_no);
  if (!text) return null;
  const result = extractNplCcr(text);
  const period = `${report.bsns_year}-${
    report.reprt_code === "11013"
      ? "Q1"
      : report.reprt_code === "11012"
        ? "H1"
        : report.reprt_code === "11014"
          ? "Q3"
          : "FY"
  }`;
  return {
    ...result,
    period,
    rcept_no: report.rcept_no,
  };
}

/** 분기 ROE (연환산) — 분기 순이익 × 4 / 자기자본 */
export async function collectRoe(
  corp_code: string,
): Promise<CollectorBundle["roe"]> {
  const report = await fetchLatestPeriodicReport(corp_code);
  if (!report) return null;
  const list = await dartGet<{
    account_nm: string;
    account_id?: string;
    thstrm_amount: string;
    sj_div: string;
  }>("fnlttSinglAcntAll", {
    corp_code,
    bsns_year: String(report.bsns_year),
    reprt_code: report.reprt_code,
    fs_div: "CFS",
  });
  if (!list) return null;

  // 자기자본 (BS) — ifrs-full_Equity 또는 "자본총계"
  let total_equity: number | null = null;
  for (const row of list) {
    if (row.sj_div !== "BS") continue;
    if (row.account_id === "ifrs-full_Equity") {
      const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
      if (!isNaN(v)) {
        total_equity = v;
        break;
      }
    }
  }
  if (total_equity == null) {
    for (const row of list) {
      if (row.sj_div !== "BS") continue;
      const name = row.account_nm?.trim() ?? "";
      if (name === "자본총계" || name === "자본 총계") {
        const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
        if (!isNaN(v)) {
          total_equity = v;
          break;
        }
      }
    }
  }

  // 분기 순이익 (IS/CIS) — collectQuarterlyNetIncome과 동일 우선순위
  let net_income: number | null = null;
  for (const row of list) {
    if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
    if (row.account_id === "ifrs-full_ProfitLoss") {
      const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
      if (!isNaN(v)) {
        net_income = v;
        break;
      }
    }
  }
  if (net_income == null) {
    const targets = [
      "당기순이익",
      "당기순이익(손실)",
      "분기순이익",
      "분기순이익(손실)",
      "반기순이익",
      "반기순이익(손실)",
      "연결당기순이익",
      "연결분기순이익",
      "연결반기순이익",
    ];
    for (const row of list) {
      if (row.sj_div !== "IS" && row.sj_div !== "CIS") continue;
      const name = row.account_nm?.trim() ?? "";
      if (targets.includes(name)) {
        const v = Number(String(row.thstrm_amount).replace(/,/g, ""));
        if (!isNaN(v)) {
          net_income = v;
          break;
        }
      }
    }
  }

  if (total_equity == null || net_income == null) {
    return {
      annualized_roe_pct: null,
      quarterly_net_income_million: net_income != null ? Math.round(net_income / 1e6) : null,
      total_equity_million: total_equity != null ? Math.round(total_equity / 1e6) : null,
      period: null,
      rcept_no: report.rcept_no,
    };
  }

  // 보고서 종류에 따라 누적 vs 단일 분기 처리
  // - reprt_code 11013 (1Q): thstrm_amount는 1분기 단일 → ×4 연환산
  // - reprt_code 11012 (반기): 누적 6개월 → ×2 연환산
  // - reprt_code 11014 (3Q): 누적 9개월 → ×4/3 연환산
  // - reprt_code 11011 (사업): 12개월 누적 → ×1
  const annualMultiplier =
    report.reprt_code === "11013"
      ? 4
      : report.reprt_code === "11012"
        ? 2
        : report.reprt_code === "11014"
          ? 4 / 3
          : 1;
  const annualized = (net_income * annualMultiplier) / total_equity * 100;

  const period = `${report.bsns_year}-${
    report.reprt_code === "11013"
      ? "Q1"
      : report.reprt_code === "11012"
        ? "H1"
        : report.reprt_code === "11014"
          ? "Q3"
          : "FY"
  }`;

  return {
    annualized_roe_pct: Number(annualized.toFixed(2)),
    quarterly_net_income_million: Math.round(net_income / 1e6),
    total_equity_million: Math.round(total_equity / 1e6),
    period,
    rcept_no: report.rcept_no,
  };
}
