/**
 * DART OpenAPI 주주환원 데이터 수집 스크립트
 *
 * 워치리스트 종목들의 주주환원 현황을 자동 조회:
 * - 자사주 취득/소각 이력
 * - 배당 이력 (최근 5년)
 * - 유상증자/CB/BW 발행 이력 (증자 내역)
 * - 최대주주 지분 변동
 *
 * 사용법: npx tsx scripts/fetch-shareholder-returns.ts
 */
import fs from "fs";
import path from "path";

// ── 설정 ──

const DART_API = "https://opendart.fss.or.kr/api";
const DART_API_KEY = process.env.DART_API_KEY ?? "";
const REQUEST_DELAY_MS = 500; // DART API 부하 방지
const DATA_DIR = path.resolve("public/data");
const OUTPUT_FILE = path.join(DATA_DIR, "shareholder-returns.json");

// 조회 연도 범위 (최근 5년)
const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i);
// 보고서 코드: 연간만 조회 (사업보고서)
const REPRT_CODE = "11011";

// ── 타입 ──

interface CorpCodeEntry {
  corp_code: string;
  corp_name: string;
  stock_code: string;
}

interface TreasuryStock {
  bsns_year: string;
  change_qy_acqs: string;  // 취득 주식수
  change_qy_dsps: string;  // 처분 주식수
  change_qy_incnr: string; // 소각 주식수
  bsis_qy: string;         // 기초 잔량
  trmend_qy: string;       // 기말 잔량
  stock_knd: string;        // 주식 종류
  acqs_mth1: string;        // 취득방법 대분류
}

interface DividendInfo {
  bsns_year: string;
  se: string;            // 구분
  thstrm: string;        // 당기
  frmtrm: string;        // 전기
  lwfr: string;          // 전전기
  stock_knd: string;     // 주식 종류
}

interface StockIssuance {
  bsns_year: string;
  isu_dcrs_de: string;   // 발행/감소 일자
  isu_dcrs_stle: string; // 발행/감소 형태
  isu_dcrs_stock_kn: string; // 종류
  isu_dcrs_qy: string;  // 수량
  isu_dcrs_mstvdv_fval_amount: string; // 액면가
  isu_dcrs_mstvdv_amount: string;      // 발행가
}

interface MajorShareholder {
  bsns_year: string;
  nm: string;            // 최대주주명
  bsis_posesn_stock_co: string; // 기초 주식수
  bsis_posesn_stock_qota_rt: string; // 기초 지분율
  trmend_posesn_stock_co: string;    // 기말 주식수
  trmend_posesn_stock_qota_rt: string; // 기말 지분율
  rm: string;            // 비고
}

// 최종 출력 타입
interface ShareholderReturnData {
  code: string;
  name: string;
  corp_code: string;
  treasury_stock: {
    year: number;
    acquired: number;
    disposed: number;
    cancelled: number;  // 소각
    remaining: number;
  }[];
  dividends: {
    year: number;
    dps: number | null;            // 1주당 배당금
    dividend_yield: number | null; // 배당수익률(%)
    payout_ratio: number | null;   // 배당성향(%)
  }[];
  capital_changes: {
    year: number;
    date: string;
    type: string;    // 유상증자, CB, BW 등
    quantity: number;
    price: number;
  }[];
  major_shareholder: {
    year: number;
    name: string;
    start_ratio: number | null;
    end_ratio: number | null;
  }[];
}

// ── 유틸 ──

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseNum(s: string | undefined | null): number {
  if (!s || s === "-") return 0;
  return Number(s.replace(/,/g, "")) || 0;
}

function parseRatio(s: string | undefined | null): number | null {
  if (!s || s === "-") return null;
  const n = Number(s.replace(/,/g, ""));
  return isNaN(n) ? null : n;
}

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ── DART API 호출 ──

async function dartGet<T>(endpoint: string, params: Record<string, string>): Promise<T[] | null> {
  const url = new URL(`${DART_API}/${endpoint}.json`);
  url.searchParams.set("crtfc_key", DART_API_KEY);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);

  const res = await fetch(url.toString());
  if (!res.ok) {
    console.warn(`  ⚠ ${endpoint} HTTP ${res.status}`);
    return null;
  }
  const json = await res.json() as { status: string; message: string; list?: T[] };

  // 000: 정상, 013: 조회된 데이터 없음
  if (json.status === "000" && json.list) return json.list;
  if (json.status === "013") return []; // 데이터 없음은 빈 배열
  if (json.status !== "000") {
    console.warn(`  ⚠ ${endpoint}: [${json.status}] ${json.message}`);
  }
  return null;
}

// ── Step 1: corp_code 매핑 다운로드 ──

async function loadCorpCodeMap(): Promise<Map<string, string>> {
  console.log("📦 corp_code 매핑 다운로드 중...");
  const url = `${DART_API}/corpCode.xml?crtfc_key=${DART_API_KEY}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`corpCode.xml 다운로드 실패: ${res.status}`);

  // ZIP 파일 → 메모리에서 압축 해제
  const zipBuffer = Buffer.from(await res.arrayBuffer());

  // ZIP을 수동 파싱 (외부 라이브러리 없이)
  const entries = parseZip(zipBuffer);
  const xmlEntry = entries.find((e) => e.name.endsWith(".xml"));
  if (!xmlEntry) throw new Error("ZIP 내 XML 파일 없음");

  const xml = xmlEntry.data.toString("utf-8");

  // 간단 XML 파싱: <list><corp_code>...</corp_code><stock_code>...</stock_code></list>
  const map = new Map<string, string>();
  const listRegex = /<list>([\s\S]*?)<\/list>/g;
  let match: RegExpExecArray | null;
  while ((match = listRegex.exec(xml)) !== null) {
    const block = match[1];
    const corpCode = block.match(/<corp_code>(\d+)<\/corp_code>/)?.[1];
    const stockCode = block.match(/<stock_code>([\d\s]*)<\/stock_code>/)?.[1]?.trim();
    if (corpCode && stockCode && stockCode.length === 6) {
      map.set(stockCode, corpCode);
    }
  }
  console.log(`  ✓ ${map.size}개 상장사 매핑 완료`);
  return map;
}

// ZIP 파서 (central directory 기반 — data descriptor 대응)
import { inflateRawSync } from "zlib";

interface ZipEntry { name: string; data: Buffer }

function parseZip(buf: Buffer): ZipEntry[] {
  // End of Central Directory (EOCD) 시그니처를 뒤에서 탐색
  let eocdOffset = -1;
  for (let i = buf.length - 22; i >= 0; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocdOffset = i; break; }
  }
  if (eocdOffset < 0) throw new Error("EOCD not found");

  const cdOffset = buf.readUInt32LE(eocdOffset + 16);   // central directory 시작
  const cdEntries = buf.readUInt16LE(eocdOffset + 10);   // 엔트리 수

  const entries: ZipEntry[] = [];
  let offset = cdOffset;

  for (let i = 0; i < cdEntries; i++) {
    if (buf.readUInt32LE(offset) !== 0x02014b50) break;
    const compressionMethod = buf.readUInt16LE(offset + 10);
    const compressedSize = buf.readUInt32LE(offset + 20);
    const nameLen = buf.readUInt16LE(offset + 28);
    const extraLen = buf.readUInt16LE(offset + 30);
    const commentLen = buf.readUInt16LE(offset + 32);
    const localHeaderOffset = buf.readUInt32LE(offset + 42);
    const name = buf.subarray(offset + 46, offset + 46 + nameLen).toString("utf-8");

    // local file header에서 실제 데이터 시작 위치 계산
    const localNameLen = buf.readUInt16LE(localHeaderOffset + 26);
    const localExtraLen = buf.readUInt16LE(localHeaderOffset + 28);
    const dataStart = localHeaderOffset + 30 + localNameLen + localExtraLen;
    const rawData = buf.subarray(dataStart, dataStart + compressedSize);

    let data: Buffer;
    if (compressionMethod === 8) {
      data = inflateRawSync(rawData);
    } else {
      data = Buffer.from(rawData);
    }
    entries.push({ name, data });
    offset += 46 + nameLen + extraLen + commentLen;
  }
  return entries;
}

// ── Step 2: 종목별 데이터 수집 ──

async function fetchTreasuryStock(corpCode: string): Promise<ShareholderReturnData["treasury_stock"]> {
  const results: ShareholderReturnData["treasury_stock"] = [];
  for (const year of YEARS) {
    const list = await dartGet<TreasuryStock>("tesstkAcqsDspsSttus", {
      corp_code: corpCode, bsns_year: String(year), reprt_code: REPRT_CODE,
    });
    await sleep(REQUEST_DELAY_MS);
    if (!list || list.length === 0) continue;
    // 보통주 총계 행만 취함
    const totalRow = list.find((r) =>
      r.stock_knd?.includes("보통주") && r.acqs_mth1?.includes("총계"));
    if (!totalRow) continue;
    const acquired = parseNum(totalRow.change_qy_acqs);
    const disposed = parseNum(totalRow.change_qy_dsps);
    const cancelled = parseNum(totalRow.change_qy_incnr);
    const remaining = parseNum(totalRow.trmend_qy);
    if (acquired || disposed || cancelled || remaining) {
      results.push({ year, acquired, disposed, cancelled, remaining });
    }
  }
  return results;
}

async function fetchDividends(corpCode: string): Promise<ShareholderReturnData["dividends"]> {
  const results: ShareholderReturnData["dividends"] = [];
  for (const year of YEARS) {
    const list = await dartGet<DividendInfo>("alotMatter", {
      corp_code: corpCode, bsns_year: String(year), reprt_code: REPRT_CODE,
    });
    await sleep(REQUEST_DELAY_MS);
    if (!list || list.length === 0) {
      results.push({ year, dps: null, dividend_yield: null, payout_ratio: null });
      continue;
    }

    let dps: number | null = null;
    let dividendYield: number | null = null;
    let payoutRatio: number | null = null;

    for (const row of list) {
      const se = row.se?.trim();
      if (!se) continue;
      // "주당 현금배당금(원)" — 보통주/우선주 두 행이 나옴, 첫 번째(보통주)만 취함
      if (dps === null && se.includes("주당") && se.includes("배당금") && se.includes("현금")) {
        const v = parseNum(row.thstrm);
        if (v > 0) dps = v;
      }
      if (dividendYield === null && se.includes("현금배당수익률")) {
        const v = parseRatio(row.thstrm);
        if (v !== null && v > 0) dividendYield = v;
      }
      if (payoutRatio === null && se.includes("배당성향")) {
        const v = parseRatio(row.thstrm);
        if (v !== null && v > 0) payoutRatio = v;
      }
    }
    results.push({ year, dps, dividend_yield: dividendYield, payout_ratio: payoutRatio });
  }
  return results;
}

async function fetchCapitalChanges(corpCode: string): Promise<ShareholderReturnData["capital_changes"]> {
  const results: ShareholderReturnData["capital_changes"] = [];
  for (const year of YEARS) {
    const list = await dartGet<StockIssuance>("irdsSttus", {
      corp_code: corpCode, bsns_year: String(year), reprt_code: REPRT_CODE,
    });
    await sleep(REQUEST_DELAY_MS);
    if (!list || list.length === 0) continue;
    for (const row of list) {
      const qty = parseNum(row.isu_dcrs_qy);
      if (qty === 0) continue;
      results.push({
        year,
        date: row.isu_dcrs_de || "",
        type: row.isu_dcrs_stle || "",
        quantity: qty,
        price: parseNum(row.isu_dcrs_mstvdv_amount),
      });
    }
  }
  return results;
}

async function fetchMajorShareholder(corpCode: string): Promise<ShareholderReturnData["major_shareholder"]> {
  const results: ShareholderReturnData["major_shareholder"] = [];
  for (const year of YEARS) {
    const list = await dartGet<MajorShareholder>("hyslrChgSttus", {
      corp_code: corpCode, bsns_year: String(year), reprt_code: REPRT_CODE,
    });
    await sleep(REQUEST_DELAY_MS);
    if (!list || list.length === 0) continue;
    // 첫 번째(최대주주) 항목만
    const top = list[0];
    if (top) {
      results.push({
        year,
        name: top.nm || "",
        start_ratio: parseRatio(top.bsis_posesn_stock_qota_rt),
        end_ratio: parseRatio(top.trmend_posesn_stock_qota_rt),
      });
    }
  }
  return results;
}

// ── 메인 ──

async function main() {
  if (!DART_API_KEY) {
    console.error("❌ DART_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.");
    process.exit(1);
  }

  // 워치리스트 로드 (성장주)
  const growthPath = path.join(DATA_DIR, "growth-watchlist.json");
  const growthData = JSON.parse(fs.readFileSync(growthPath, "utf-8"));
  const stocks: { code: string; name: string }[] = growthData.stocks
    .filter((s: { code: string }) => /^\d{6}$/.test(s.code)); // 국내 종목만

  console.log(`📊 대상 종목: ${stocks.length}개`);

  // corp_code 매핑
  const corpMap = await loadCorpCodeMap();

  const results: ShareholderReturnData[] = [];
  let idx = 0;

  for (const stock of stocks) {
    idx++;
    const corpCode = corpMap.get(stock.code);
    if (!corpCode) {
      console.warn(`  ⚠ [${idx}/${stocks.length}] ${stock.name}(${stock.code}) — corp_code 매핑 실패, 건너뜀`);
      continue;
    }
    console.log(`  [${idx}/${stocks.length}] ${stock.name}(${stock.code}) → corp_code: ${corpCode}`);

    const [treasuryStock, dividends, capitalChanges, majorShareholder] = await Promise.all([
      fetchTreasuryStock(corpCode),
      fetchDividends(corpCode),
      fetchCapitalChanges(corpCode),
      fetchMajorShareholder(corpCode),
    ]);

    results.push({
      code: stock.code,
      name: stock.name,
      corp_code: corpCode,
      treasury_stock: treasuryStock,
      dividends,
      capital_changes: capitalChanges,
      major_shareholder: majorShareholder,
    });
  }

  // 저장
  const output = {
    generated_at: today(),
    description: "DART OpenAPI 기반 주주환원 데이터 (최근 5년)",
    stocks: results,
  };
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2), "utf-8");
  console.log(`\n✅ 저장 완료: ${OUTPUT_FILE} (${results.length}개 종목)`);

  // 요약 출력
  const withTreasury = results.filter((r) => r.treasury_stock.length > 0);
  const withCancelled = results.filter((r) => r.treasury_stock.some((t) => t.cancelled > 0));
  const withDividend = results.filter((r) => r.dividends.some((d) => d.dps && d.dps > 0));
  const withCapital = results.filter((r) => r.capital_changes.length > 0);
  console.log(`\n📋 요약:`);
  console.log(`  자사주 취득 이력: ${withTreasury.length}개`);
  console.log(`  자사주 소각 이력: ${withCancelled.length}개`);
  console.log(`  배당 지급 이력: ${withDividend.length}개`);
  console.log(`  증자/CB/BW 이력: ${withCapital.length}개`);
}

main().catch((e) => {
  console.error("❌ 실행 오류:", e);
  process.exit(1);
});
