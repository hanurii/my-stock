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

export function collectValuation(code: string): CollectorBundle["valuation"] {
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
        };
      }
    } catch {}
  }
  return null;
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

/** 직전 N일 동안 corp_code의 '특수관계인 내부거래' + '동일인등 출자계열회사 상품용역거래' 공시 합계 / 매출 비율.
 *  단위는 모두 백만원. 같은 분기 정정공시 중복 위험은 본 단순 누적 모델에서는 감수(공시 갯수와 함께 표시).
 */
export async function collectAffiliateTransactionRatio(
  corp_code: string,
  lookback_days: number,
): Promise<CollectorBundle["affiliate_transactions"]> {
  const today = new Date();
  const since = new Date(today.getTime() - lookback_days * 86400_000);
  const list = await dartGet<DartListItem>("list", {
    corp_code,
    bgn_de: fmtYmd(since),
    end_de: fmtYmd(today),
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
      period_days: lookback_days,
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
    period_days: lookback_days,
    rcept_nos: usedRceptNos,
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

// ── 10) Google News RSS ──
export async function collectNewsHits(
  keywords: string[],
  lookback_days: number,
): Promise<Array<{ keyword: string; date: string; title: string; url: string }>> {
  const hits: Array<{ keyword: string; date: string; title: string; url: string }> = [];
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
