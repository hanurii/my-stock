/**
 * 바이오주 자동 스크리닝 — 7대 기준 기반
 *
 * 한국 상장 바이오 기업 전체를 대상으로:
 * 1) KIPRIS 특허, PubMed/Semantic Scholar 논문, ClinicalTrials.gov 임상,
 *    DART 공시/임원/지분, Naver 재무 데이터를 수집
 * 2) scoreBio()로 채점
 * 3) A 트랙(안정형) + B 트랙(유망형) 분류
 * 4) B 트랙 기술 상세 조사
 *
 * 사용법: npx tsx scripts/screen-bio.ts [--force]
 */
import fs from "fs";
import path from "path";
import { scoreBio, getGrade, type BioStockInput, type ScoredResult, type ScoreDetail } from "../src/lib/scoring";
import type {
  ConferenceLevel, HighestPhase, LicenseOutTier, TerminationHistory,
  ContractStructure, CeoBackground, ExitSignal,
} from "../src/lib/scoring";
import { loadCorpCodeMap } from "./fetch-shareholder-returns";

// ── 설정 ──

const NAVER_LIST = "https://m.stock.naver.com/api/stocks/marketValue";
const NAVER_API = "https://m.stock.naver.com/api/stock";
const DART_API = "https://opendart.fss.or.kr/api";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
const HEADERS = { "User-Agent": UA };

const DART_API_KEY = process.env.DART_API_KEY ?? "";
const KIPRIS_API_KEY = process.env.KIPRIS_API_KEY ?? "";
const NCBI_API_KEY = process.env.NCBI_API_KEY ?? "";

const DATA_DIR = path.resolve("public/data");
const OUTPUT_FILE = path.join(DATA_DIR, "bio-watchlist.json");
const CACHE_FILE = path.join(DATA_DIR, ".bio-cache.json");
const OVERRIDES_FILE = path.join(DATA_DIR, "bio-manual-overrides.json");
const ALIASES_FILE = path.join(DATA_DIR, "bio-company-aliases.json");

const FORCE = process.argv.includes("--force");
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24시간 (기본)
const KIPRIS_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7일 (KIPRIS 월 1000건 제한)

const TOP20_PHARMA = [
  // 영문명
  "pfizer", "roche", "genentech", "novartis", "merck", "msd", "j&j", "janssen", "johnson",
  "abbvie", "sanofi", "astrazeneca", "gsk", "glaxo", "bristol-myers", "bms",
  "eli lilly", "lilly", "amgen", "gilead", "bayer", "takeda", "novo nordisk",
  "boehringer", "biogen", "regeneron", "moderna", "vertex",
  // 한글명 (DART 공시 제목에서 매칭)
  "화이자", "로슈", "제넨텍", "노바티스", "머크", "얀센", "존슨앤존슨", "존슨앤드존슨",
  "애브비", "사노피", "아스트라제네카", "글락소", "브리스톨", "일라이릴리", "릴리",
  "암젠", "길리어드", "바이엘", "다케다", "노보노디스크", "베링거", "바이오젠",
  "리제네론", "모더나", "버텍스",
];

const BIO_SECTOR_KEYWORDS = /바이오|제약|의약|생명과학|셀|젠|팜|메디|진단|항체|세포치료|헬스케어/;

// ── 유틸 ──

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }
function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function parseNum(s: string | undefined | null): number {
  if (!s || s === "-" || s === "") return 0;
  const m = s.replace(/,/g, "").match(/-?[\d.]+/);
  return m ? Number(m[0]) || 0 : 0;
}
function parseMarketCap(str: string): number {
  let total = 0;
  const joMatch = str.match(/([\d,]+)조/);
  const eokMatch = str.match(/([\d,]+)억/);
  if (joMatch) total += parseNum(joMatch[1]) * 10000;
  if (eokMatch) total += parseNum(eokMatch[1]);
  return total;
}

async function fetchWithRetry(url: string, opts: RequestInit = {}, maxRetries = 3): Promise<Response> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch(url, opts);
      if (res.ok || res.status === 404) return res;
      if (res.status === 429) {
        console.warn(`  ⏳ Rate limited, waiting ${5 * (i + 1)}s...`);
        await sleep(5000 * (i + 1));
        continue;
      }
      if (i === maxRetries - 1) return res;
    } catch (e) {
      if (i === maxRetries - 1) throw e;
      await sleep(2000);
    }
  }
  throw new Error(`Max retries: ${url}`);
}

// ── 캐시 ──

interface CacheEntry { data: unknown; fetched_at: number; }
type CacheStore = Record<string, Record<string, CacheEntry>>;

let cache: CacheStore = {};

function loadCache() {
  try {
    if (fs.existsSync(CACHE_FILE)) cache = JSON.parse(fs.readFileSync(CACHE_FILE, "utf-8"));
  } catch { cache = {}; }
}

function saveCache() {
  fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2));
}

function getCached<T>(code: string, source: string): T | null {
  if (FORCE) return null;
  const entry = cache[code]?.[source];
  if (!entry) return null;
  const ttl = source === "kipris" ? KIPRIS_CACHE_TTL_MS : CACHE_TTL_MS;
  if (Date.now() - entry.fetched_at > ttl) return null;
  return entry.data as T;
}

function setCache(code: string, source: string, data: unknown) {
  if (!cache[code]) cache[code] = {};
  cache[code][source] = { data, fetched_at: Date.now() };
}

// ── 수동 보정 & 영문명 매핑 ──

interface ManualOverride {
  conference_level?: ConferenceLevel;
  contract_structure?: ContractStructure;
  ceo_background?: CeoBackground;
  notes?: string;
}

interface CompanyAlias {
  names_en: string[];
  pipeline_keywords?: string[];
}

function loadOverrides(): Record<string, ManualOverride> {
  try { return JSON.parse(fs.readFileSync(OVERRIDES_FILE, "utf-8")); } catch { return {}; }
}

function loadAliases(): Record<string, CompanyAlias> {
  try { return JSON.parse(fs.readFileSync(ALIASES_FILE, "utf-8")); } catch { return {}; }
}

// ── Phase 1: 바이오 종목 목록 수집 ──

interface BioStock { code: string; name: string; market: string; marketCap: number; price: number; sector: string; }

// 바이오 업종 코드 (Naver integration API의 industryCode)
const BIO_INDUSTRY_CODES = new Set([
  "261", // 제약
  "262", // 의료정밀
  "286", // 의약품 (알테오젠 등)
]);

async function collectBioStocks(): Promise<BioStock[]> {
  console.log("\n🔬 Phase 1: 바이오 종목 목록 수집");

  // Step 1: 전 종목 수집 (시총순)
  const allStocks: { code: string; name: string; market: string; cap: number; price: number }[] = [];
  for (const market of ["KOSPI", "KOSDAQ"]) {
    let page = 1;
    while (true) {
      const res = await fetch(`${NAVER_LIST}/${market}?page=${page}&pageSize=100`, { headers: HEADERS });
      if (!res.ok) break;
      const json = await res.json();
      const stocks = json.stocks || [];
      if (stocks.length === 0) break;
      for (const s of stocks) {
        if (s.stockEndType !== "stock") continue;
        const capStr: string = s.marketValueHangeul || s.marketValue || "0";
        const cap = parseMarketCap(capStr);
        if (cap >= 300) {
          allStocks.push({ code: s.itemCode, name: s.stockName, market, cap, price: parseNum(s.closePrice || s.closePriceRaw) });
        }
      }
      page++;
      if (stocks.length < 100) break;
    }
  }
  console.log(`  전체 종목: ${allStocks.length}개 (시총 300억+)`);

  // Step 2: 이름 기반 1차 필터 + industryCode 기반 2차 필터
  // 이름에 바이오 키워드가 포함된 종목은 바로 통과
  const nameFiltered: typeof allStocks = [];
  const needIndustryCheck: typeof allStocks = [];

  for (const s of allStocks) {
    if (BIO_SECTOR_KEYWORDS.test(s.name)) {
      nameFiltered.push(s);
    } else {
      needIndustryCheck.push(s);
    }
  }
  console.log(`  이름 기반 1차 필터: ${nameFiltered.length}개`);

  // industryCode로 바이오 업종 확인 (배치 병렬)
  console.log(`  업종 코드 확인 중... (${needIndustryCheck.length}개)`);
  const industryFiltered: typeof allStocks = [];
  const INDUSTRY_BATCH = 10;

  for (let i = 0; i < needIndustryCheck.length; i += INDUSTRY_BATCH) {
    const batch = needIndustryCheck.slice(i, i + INDUSTRY_BATCH);
    const results = await Promise.all(batch.map(async (s) => {
      try {
        const res = await fetch(`${NAVER_API}/${s.code}/integration`, { headers: HEADERS });
        if (!res.ok) return null;
        const json = await res.json();
        if (BIO_INDUSTRY_CODES.has(json.industryCode)) return s;
      } catch { /* ignore */ }
      return null;
    }));
    industryFiltered.push(...results.filter((r): r is NonNullable<typeof r> => r !== null));
    if (i + INDUSTRY_BATCH < needIndustryCheck.length) await sleep(300);
  }
  console.log(`  업종 코드 2차 필터: ${industryFiltered.length}개`);

  // 합치기 + 중복 제거
  const codeSet = new Set<string>();
  const all: BioStock[] = [];
  for (const s of [...nameFiltered, ...industryFiltered]) {
    if (codeSet.has(s.code)) continue;
    codeSet.add(s.code);
    all.push({ code: s.code, name: s.name, market: s.market, marketCap: s.cap, price: s.price, sector: "" });
  }

  console.log(`  ✓ ${all.length}개 바이오 종목 수집 완료`);
  return all;
}

// ── Phase 2g: 학회 발표 뉴스 크롤링 ──

const CONFERENCE_ORAL_KEYWORDS = /oral presentation|구두 발표|구두발표|late.?breaking|keynote|초청 연사|초청연사|plenary/i;
const CONFERENCE_POSTER_KEYWORDS = /poster presentation|포스터 발표|포스터발표|e-poster/i;
const TOP4_CONFERENCES = /ASCO|ASH|AACR|ESMO/i;

async function fetchConferenceLevel(name: string, code: string): Promise<ConferenceLevel | null> {
  const cached = getCached<ConferenceLevel | null>(code, "conference");
  if (cached !== null && cached !== undefined) return cached;

  let result = null as ConferenceLevel | null;

  try {
    // 네이버 뉴스 검색: "{종목명} ASCO OR ASH OR AACR OR ESMO 발표"
    const query = encodeURIComponent(`${name} ASCO ASH AACR ESMO 발표`);
    const url = `https://openapi.naver.com/v1/search/news.json?query=${query}&display=20&sort=date`;
    const res = await fetchWithRetry(url, {
      headers: {
        "X-Naver-Client-Id": "KbJFMYqVbbMjVnMRPGt4",
        "X-Naver-Client-Secret": "e4hnA3_kMz",
      },
    });

    if (res.ok) {
      const json = await res.json();
      const items = json.items || [];

      for (const item of items) {
        const text = `${item.title} ${item.description}`.replace(/<[^>]+>/g, "");

        if (TOP4_CONFERENCES.test(text)) {
          if (CONFERENCE_ORAL_KEYWORDS.test(text)) {
            result = "oral_top4" as ConferenceLevel;
            break;
          } else if (CONFERENCE_POSTER_KEYWORDS.test(text) && result !== "oral_top4") {
            result = "poster_top4" as ConferenceLevel;
          } else if (!result) {
            result = "other_intl" as ConferenceLevel;
          }
        }
      }
    }
  } catch (e) {
    console.warn(`  ⚠ 학회 뉴스 검색 실패 (${name}):`, (e as Error).message);
  }

  setCache(code, "conference", result);
  return result;
}

// ── Phase 2a: KIPRIS 특허 검색 ──

interface PatentData { domestic: number; pct: number; }

async function fetchPatents(name: string, code: string): Promise<PatentData> {
  const cached = getCached<PatentData>(code, "kipris");
  if (cached) return cached;

  let domestic = 0, pct = 0;
  try {
    // KIPRIS 데이터 서비스 API — 특허·실용 공개·등록공보 (numOfRows=1로 건수만 조회)
    const url = `http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch?ServiceKey=${encodeURIComponent(KIPRIS_API_KEY)}&applicant=${encodeURIComponent(name)}&numOfRows=1&pageNo=1`;
    const res = await fetchWithRetry(url);
    if (res.ok) {
      const text = await res.text();
      if (text.includes("<resultCode>00</resultCode>")) {
        const totalMatch = text.match(/<totalCount>(\d+)<\/totalCount>/);
        domestic = totalMatch ? parseInt(totalMatch[1]) : 0;
      }
    }
    // PCT 건수는 특허 패밀리 API로 추후 확인 (현재는 0)
  } catch (e) {
    console.warn(`  ⚠ KIPRIS 실패 (${name}):`, (e as Error).message);
  }

  const result = { domestic, pct };
  setCache(code, "kipris", result);
  return result;
}

// ── Phase 2b: PubMed + Semantic Scholar ──

interface PaperData { pubmed_count: number; high_if_papers: number; total_citations: number; }

async function fetchPapers(nameEn: string, code: string): Promise<PaperData> {
  const cached = getCached<PaperData>(code, "papers");
  if (cached) return cached;

  let pubmed_count = 0, high_if_papers = 0, total_citations = 0;

  // PubMed 검색
  try {
    const query = encodeURIComponent(`"${nameEn}"[Affiliation]`);
    const url = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${query}&retmax=0&retmode=json&api_key=${NCBI_API_KEY}`;
    const res = await fetchWithRetry(url);
    if (res.ok) {
      const json = await res.json();
      pubmed_count = parseInt(json.esearchresult?.count || "0");
    }
  } catch (e) {
    console.warn(`  ⚠ PubMed 실패 (${nameEn}):`, (e as Error).message);
  }

  // Semantic Scholar는 Rate Limit이 매우 엄격하여 일시 비활성화
  // TODO: API 키 발급 후 재활성화 (https://www.semanticscholar.org/product/api#api-key)
  // await sleep(3000);
  // try { ... } catch { ... }

  const result = { pubmed_count, high_if_papers, total_citations };
  setCache(code, "papers", result);
  return result;
}

const HIGH_IF_JOURNALS = [
  "nature", "science", "cell", "lancet", "new england journal", "nejm",
  "jama", "bmj", "journal of clinical oncology", "jco", "blood",
  "annals of oncology", "cancer discovery", "cancer cell",
  "journal of clinical investigation", "jci", "nature medicine",
  "nature biotechnology", "nature reviews",
];

// ── Phase 2c: ClinicalTrials.gov 임상 ──

interface ClinicalData {
  highest_phase: HighestPhase;
  pipeline_count: number;
  results_transparency: number;
  pipelines: PipelineInfo[];
}

interface PipelineInfo {
  nctId: string;
  title: string;
  indication: string;
  phase: string;
  status: string;
  startDate: string;
  completionDate: string;
  hasResults: boolean;
}

function toHighestPhase(phases: string[]): HighestPhase {
  const phaseOrder: Record<string, HighestPhase> = {
    "PHASE4": "approved", "PHASE3": "phase3", "PHASE2": "phase2",
    "PHASE1": "phase1", "EARLY_PHASE1": "phase1",
  };
  for (const p of ["PHASE4", "PHASE3", "PHASE2", "PHASE1", "EARLY_PHASE1"]) {
    if (phases.includes(p)) return phaseOrder[p];
  }
  return "preclinical";
}

async function fetchClinicalTrials(nameEn: string, code: string): Promise<ClinicalData> {
  const cached = getCached<ClinicalData>(code, "clinical");
  if (cached) return cached;

  const result: ClinicalData = { highest_phase: "none", pipeline_count: 0, results_transparency: 0, pipelines: [] };

  try {
    const query = encodeURIComponent(nameEn);
    const url = `https://clinicaltrials.gov/api/v2/studies?query.spons=${query}&pageSize=50&fields=protocolSection.identificationModule|protocolSection.statusModule|protocolSection.designModule|protocolSection.conditionsModule|hasResults`;
    const res = await fetchWithRetry(url);
    if (res.ok) {
      const json = await res.json();
      const studies = json.studies || [];
      const allPhases: string[] = [];
      let hasResultsCount = 0;

      for (const s of studies) {
        const proto = s.protocolSection || {};
        const id = proto.identificationModule || {};
        const status = proto.statusModule || {};
        const design = proto.designModule || {};
        const conditions = proto.conditionsModule || {};
        const phases: string[] = design.phases || [];
        allPhases.push(...phases);

        if (s.hasResults) hasResultsCount++;

        result.pipelines.push({
          nctId: id.nctId || "",
          title: id.briefTitle || "",
          indication: (conditions.conditions || []).join(", "),
          phase: phases[0] || "N/A",
          status: status.overallStatus || "",
          startDate: status.startDateStruct?.date || "",
          completionDate: status.completionDateStruct?.date || "",
          hasResults: !!s.hasResults,
        });
      }

      result.pipeline_count = studies.length;
      result.highest_phase = studies.length > 0 ? toHighestPhase(allPhases) : "none";
      result.results_transparency = studies.length > 0 ? Math.round((hasResultsCount / studies.length) * 100) : 0;
    }
  } catch (e) {
    console.warn(`  ⚠ ClinicalTrials.gov 실패 (${nameEn}):`, (e as Error).message);
  }

  setCache(code, "clinical", result);
  return result;
}

// ── Phase 2d: DART 공시 — 기술이전/계약 ──

interface DartDealData {
  license_out_tier: LicenseOutTier;
  termination_history: TerminationHistory;
}

async function fetchDartDeals(corpCode: string, code: string): Promise<DartDealData> {
  const cached = getCached<DartDealData>(code, "dart_deals");
  if (cached) return cached;

  const result: DartDealData = { license_out_tier: "none", termination_history: "none" };
  if (!corpCode) return result;

  try {
    const threeYearsAgo = `${new Date().getFullYear() - 3}0101`;
    const url = `${DART_API}/list.json?crtfc_key=${DART_API_KEY}&corp_code=${corpCode}&bgn_de=${threeYearsAgo}&page_count=100`;
    const res = await fetchWithRetry(url);
    if (res.ok) {
      const json = await res.json();
      if (json.status === "000" && json.list) {
        const reports: { report_nm: string; rcept_no: string }[] = json.list;

        for (const r of reports) {
          const title = r.report_nm.toLowerCase();
          // 기술이전/라이센스 검색
          if (/기술이전|라이선스|라이센스|license|기술수출|기술도입/.test(title)) {
            // 빅파마 대조 (제목에서)
            if (TOP20_PHARMA.some(p => title.includes(p))) {
              result.license_out_tier = "top20";
            } else if (result.license_out_tier === "none") {
              result.license_out_tier = /해외|글로벌|global|외국/.test(title) ? "global" : "domestic";
            }
          }
          // 계약 해지/반환 검색
          if (/해지|반환|파기|종료|해제/.test(title) && /계약|기술|라이/.test(title)) {
            result.termination_history = "terminated";
          }
        }
      }
    }
  } catch (e) {
    console.warn(`  ⚠ DART 공시 실패 (${corpCode}):`, (e as Error).message);
  }

  setCache(code, "dart_deals", result);
  return result;
}

// ── Phase 2e: DART 임원현황 + 지분변동 ──

interface MgmtData {
  ceo_background: CeoBackground;
  dilution_3yr_pct: number;
  exit_signal: ExitSignal;
}

const SCIENTIST_KEYWORDS = /박사|ph\.?d|phd|연구소|연구원|r&d|교수|cso|cto|cmo|의학|약학|생명|생물|화학|의사|전문의/i;

async function fetchManagement(corpCode: string, code: string): Promise<MgmtData> {
  const cached = getCached<MgmtData>(code, "management");
  if (cached) return cached;

  const result: MgmtData = { ceo_background: "unknown", dilution_3yr_pct: 0, exit_signal: "none" };
  if (!corpCode) return result;

  const year = new Date().getFullYear() - 1; // 최근 사업보고서

  // 임원 현황
  try {
    const url = `${DART_API}/exctvSttus.json?crtfc_key=${DART_API_KEY}&corp_code=${corpCode}&bsns_year=${year}&reprt_code=11011`;
    const res = await fetchWithRetry(url);
    if (res.ok) {
      const json = await res.json();
      if (json.status === "000" && json.list) {
        for (const exec of json.list) {
          const career: string = (exec.main_career || "").toLowerCase();
          const position: string = (exec.ofcps || "").toLowerCase();
          const duty: string = (exec.chrg_job || "").toLowerCase();
          const isCeo = position.includes("대표") || duty.includes("대표");
          const isCto = /cto|기술|연구|개발/.test(duty);

          if (isCeo && SCIENTIST_KEYWORDS.test(career)) {
            result.ceo_background = "scientist";
          } else if (isCto && SCIENTIST_KEYWORDS.test(career) && result.ceo_background !== "scientist") {
            result.ceo_background = "cto_scientist";
          } else if (isCeo && result.ceo_background === "unknown") {
            result.ceo_background = "professional";
          }
        }
      }
    }
  } catch (e) {
    console.warn(`  ⚠ DART 임원 실패 (${corpCode}):`, (e as Error).message);
  }

  await sleep(300);

  // CB/BW/유상증자 공시로 희석률 추정 (3년)
  try {
    const threeYearsAgo = `${new Date().getFullYear() - 3}0101`;
    const url = `${DART_API}/list.json?crtfc_key=${DART_API_KEY}&corp_code=${corpCode}&bgn_de=${threeYearsAgo}&pblntf_ty=B&page_count=100`;
    const res = await fetchWithRetry(url);
    if (res.ok) {
      const json = await res.json();
      if (json.status === "000" && json.list) {
        let dilutiveEvents = 0;
        let majorSale = false;
        for (const r of json.list) {
          const t = r.report_nm;
          if (/전환사채|신주인수권|유상증자/.test(t) && /발행|결정/.test(t)) dilutiveEvents++;
          if (/임원.*처분|대표.*매도|최대주주.*변경/.test(t)) majorSale = true;
        }
        // 희석률은 이벤트 수로 근사 추정 (정확한 주식수는 사업보고서 파싱 필요)
        result.dilution_3yr_pct = dilutiveEvents * 8; // 이벤트당 약 8% 추정
        result.exit_signal = majorSale ? "major" : "none";
      }
    }
  } catch (e) {
    console.warn(`  ⚠ DART 지분 실패 (${corpCode}):`, (e as Error).message);
  }

  setCache(code, "management", result);
  return result;
}

// ── Phase 2f: Naver 재무 — 현금 런웨이 ──

async function fetchCashRunway(code: string): Promise<number | null> {
  const cached = getCached<number | null>(code, "cash_runway");
  if (cached !== null && cached !== undefined) return cached;

  try {
    const res = await fetch(`${NAVER_API}/${code}/finance/annual`, { headers: HEADERS });
    if (!res.ok) return null;
    const json = await res.json();
    const periods = json.financeInfo?.trTitleList as { key: string; isConsensus: string }[] | undefined;
    const rows = json.financeInfo?.rowList as { title: string; columns: Record<string, { value: string }> }[] | undefined;
    if (!periods || !rows) return null;

    const confirmed = periods.filter((p: { isConsensus: string }) => p.isConsensus === "N");
    const latest = confirmed[confirmed.length - 1];
    if (!latest) return null;

    const getVal = (title: string) => parseNum(rows.find((r: { title: string }) => r.title === title)?.columns[latest.key]?.value);
    const opProfit = getVal("영업이익");
    const debtRatio = getVal("부채비율");
    const currentRatio = getVal("당좌비율"); // 당좌비율 100% 이상 = 단기부채 상환 여유

    // 간이 런웨이 추정:
    // - 영업흑자 + 당좌비율 100%+ → 2년+
    // - 영업흑자 + 당좌비율 낮음 → 1년+
    // - 영업적자 + 당좌비율 100%+ → 1년+
    // - 영업적자 + 당좌비율 낮음 → 1년 미만
    let runway: number;
    if (opProfit > 0) {
      runway = currentRatio >= 100 ? 3 : 1.5;
    } else {
      runway = currentRatio >= 100 ? 1.5 : 0.5;
    }

    setCache(code, "cash_runway", runway);
    return runway;
  } catch {
    return null;
  }
}

// ── Phase 6: B 트랙 기술 상세 조사 ──

interface TechDetail {
  tech_summary: string;
  tech_detail: string;
  market_impact: string;
  global_exclusivity: {
    competing_trials: number;
    patent_scope: string;
    uniqueness: string;
  };
}

async function fetchTechDetail(pipeline: PipelineInfo): Promise<TechDetail> {
  const detail: TechDetail = {
    tech_summary: "", tech_detail: "", market_impact: "",
    global_exclusivity: { competing_trials: 0, patent_scope: "", uniqueness: "" },
  };

  // ClinicalTrials.gov 상세 설명
  if (pipeline.nctId) {
    try {
      const url = `https://clinicaltrials.gov/api/v2/studies/${pipeline.nctId}?fields=protocolSection.descriptionModule|protocolSection.designModule`;
      const res = await fetchWithRetry(url);
      if (res.ok) {
        const json = await res.json();
        const desc = json.protocolSection?.descriptionModule || {};
        detail.tech_summary = desc.briefSummary || "";
        detail.tech_detail = desc.detailedDescription || "";
      }
    } catch { /* ignore */ }
    await sleep(500);
  }

  // 경쟁 파이프라인 수 (동일 적응증 + Phase 3)
  if (pipeline.indication) {
    try {
      const condition = encodeURIComponent(pipeline.indication.split(",")[0].trim());
      const url = `https://clinicaltrials.gov/api/v2/studies?query.cond=${condition}&filter.phase=PHASE3&pageSize=1&countTotal=true`;
      const res = await fetchWithRetry(url);
      if (res.ok) {
        const json = await res.json();
        detail.global_exclusivity.competing_trials = json.totalCount || 0;
      }
    } catch { /* ignore */ }
  }

  // 시장 파급력은 적응증 기반 간이 추정
  if (pipeline.indication) {
    detail.market_impact = `적응증: ${pipeline.indication}`;
  }

  return detail;
}

// ── DART corp_code + 영문명 매핑 ──

import { inflateRawSync } from "zlib";

async function loadCorpEngNameMap(): Promise<Map<string, string>> {
  console.log("📦 DART 영문 회사명 매핑 다운로드 중...");
  const url = `${DART_API}/corpCode.xml?crtfc_key=${DART_API_KEY}`;
  const res = await fetch(url);
  if (!res.ok) { console.warn("  ⚠ corpCode.xml 다운로드 실패"); return new Map(); }

  const buf = Buffer.from(await res.arrayBuffer());
  // ZIP 파싱 (EOCD → central directory → local file → inflate)
  const eocdIdx = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  if (eocdIdx < 0) { console.warn("  ⚠ ZIP EOCD not found"); return new Map(); }
  const cdOffset = buf.readUInt32LE(eocdIdx + 16);
  let pos = cdOffset;
  let xml = "";
  while (pos < eocdIdx) {
    const sig = buf.readUInt32LE(pos);
    if (sig !== 0x02014b50) break;
    const nameLen = buf.readUInt16LE(pos + 28);
    const extraLen = buf.readUInt16LE(pos + 30);
    const commentLen = buf.readUInt16LE(pos + 32);
    const localOff = buf.readUInt32LE(pos + 42);
    const compSize = buf.readUInt32LE(pos + 20);
    const method = buf.readUInt16LE(pos + 10);
    const lnLen = buf.readUInt16LE(localOff + 26);
    const leLen = buf.readUInt16LE(localOff + 28);
    const dataStart = localOff + 30 + lnLen + leLen;
    const raw = buf.subarray(dataStart, dataStart + compSize);
    xml = method === 8 ? inflateRawSync(raw).toString("utf-8") : raw.toString("utf-8");
    pos += 46 + nameLen + extraLen + commentLen;
  }

  const map = new Map<string, string>(); // stockCode → engName
  const listRegex = /<list>([\s\S]*?)<\/list>/g;
  let match: RegExpExecArray | null;
  while ((match = listRegex.exec(xml)) !== null) {
    const block = match[1];
    const stockCode = block.match(/<stock_code>([\d\s]*)<\/stock_code>/)?.[1]?.trim();
    const engName = block.match(/<corp_eng_name>([^<]+)<\/corp_eng_name>/)?.[1]?.trim();
    if (stockCode && stockCode.length === 6 && engName && engName.length > 1) {
      map.set(stockCode, engName);
    }
  }
  console.log(`  ✓ ${map.size}개 영문명 매핑 완료`);
  return map;
}

// ── 메인 실행 ──

async function main() {
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("🧬 바이오주 스크리닝 시작");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

  // Phase 0: 캐시 로드
  loadCache();
  const overrides = loadOverrides();
  const aliases = loadAliases();

  // DART corp_code 매핑 + 영문명 매핑
  const corpMap = await loadCorpCodeMap();
  const engNameMap = await loadCorpEngNameMap();

  // 영문명: aliases > DART 영문명 > 한글명 fallback
  function getEnglishName(code: string, name: string): string {
    if (aliases[code]?.names_en?.[0]) return aliases[code].names_en[0];
    const dartEng = engNameMap.get(code);
    if (dartEng) return dartEng;
    return name;
  }

  // Phase 1: 바이오 종목 목록
  const bioStocks = await collectBioStocks();

  // 데이터 수집 통계
  const stats = { kipris: { ok: 0, fail: 0 }, papers: { ok: 0, fail: 0 }, clinical: { ok: 0, fail: 0 }, dart: { ok: 0, fail: 0 }, naver: { ok: 0, fail: 0 } };

  // Phase 2: 외부 API 수집 + Phase 4: 스코어링
  console.log("\n📊 Phase 2-4: 데이터 수집 + 스코어링");

  interface ScoredBio extends BioStockInput {
    scored: ScoredResult;
    pipelines: PipelineInfo[];
    data_confidence: "high" | "medium" | "low";
  }

  const scored: ScoredBio[] = [];
  const BATCH_SIZE = 5; // 5개 종목 동시 처리 (S2는 순차이므로 안전)

  async function processStock(stock: BioStock, idx: number): Promise<ScoredBio> {
    const corpCode = corpMap.get(stock.code) || "";
    const nameEn = getEnglishName(stock.code, stock.name);
    const override = overrides[stock.code] || {};

    // 6개 API 동시 호출 (PubMed+S2 제외 — S2는 Rate Limit이 엄격하여 별도 수집)
    const [patents, clinical, deals, mgmt, runway, conferenceFromNews] = await Promise.all([
      fetchPatents(stock.name, stock.code),
      fetchClinicalTrials(nameEn, stock.code),
      fetchDartDeals(corpCode, stock.code),
      fetchManagement(corpCode, stock.code),
      fetchCashRunway(stock.code),
      fetchConferenceLevel(stock.name, stock.code),
    ]);
    // papers는 Phase 2.5에서 순차 수집 (여기선 빈 값)
    const papers: PaperData = { pubmed_count: 0, high_if_papers: 0, total_citations: 0 };

    // 통계 업데이트
    patents.domestic > 0 ? stats.kipris.ok++ : stats.kipris.fail++;
    papers.pubmed_count > 0 ? stats.papers.ok++ : stats.papers.fail++;
    clinical.pipeline_count > 0 ? stats.clinical.ok++ : stats.clinical.fail++;
    deals.license_out_tier !== "none" ? stats.dart.ok++ : stats.dart.fail++;
    runway != null ? stats.naver.ok++ : stats.naver.fail++;

    // 수동 보정 머지 (수동 > 뉴스 크롤링 > null)
    const conferenceLevel: ConferenceLevel | null = override.conference_level ?? conferenceFromNews ?? null;
    const contractStructure: ContractStructure | null = override.contract_structure ?? null;
    const ceoBg: CeoBackground = override.ceo_background ?? mgmt.ceo_background;

    // 데이터 신뢰도 계산
    let dataPoints = 0;
    if (patents.domestic > 0) dataPoints++;
    if (papers.pubmed_count > 0) dataPoints++;
    if (clinical.pipeline_count > 0) dataPoints++;
    if (deals.license_out_tier !== "none") dataPoints++;
    if (ceoBg !== "unknown") dataPoints++;
    if (runway != null) dataPoints++;
    const confidence: "high" | "medium" | "low" = dataPoints >= 4 ? "high" : dataPoints >= 2 ? "medium" : "low";

    const input: BioStockInput = {
      code: stock.code,
      name: stock.name,
      market: stock.market,
      patent_domestic: patents.domestic,
      patent_pct: patents.pct,
      pubmed_count: papers.pubmed_count,
      high_if_papers: papers.high_if_papers,
      total_citations: papers.total_citations,
      conference_level: conferenceLevel,
      highest_phase: clinical.highest_phase,
      pipeline_count: clinical.pipeline_count,
      results_transparency: clinical.results_transparency,
      license_out_tier: deals.license_out_tier,
      termination_history: deals.termination_history,
      contract_structure: contractStructure,
      ceo_background: ceoBg,
      dilution_3yr_pct: mgmt.dilution_3yr_pct,
      exit_signal: mgmt.exit_signal,
      cash_runway_years: runway,
      market_cap: stock.marketCap,
      current_price: stock.price,
    };

    const result = scoreBio(input);
    console.log(`  [${idx}/${bioStocks.length}] ${stock.name} → ${result.grade} (${result.score}점)`);

    return { ...input, scored: result, pipelines: clinical.pipelines, data_confidence: confidence };
  }

  // 배치 병렬 실행: BATCH_SIZE개씩 동시 처리
  for (let i = 0; i < bioStocks.length; i += BATCH_SIZE) {
    const batch = bioStocks.slice(i, i + BATCH_SIZE);
    const results = await Promise.all(
      batch.map((stock, bi) => processStock(stock, i + bi + 1))
    );
    scored.push(...results);
    if (i + BATCH_SIZE < bioStocks.length) await sleep(500);
  }

  // Phase 2.5: PubMed + Semantic Scholar 순차 수집 (S2 Rate Limit 보호)
  console.log("\n📄 Phase 2.5: 논문 데이터 순차 수집 (PubMed + Semantic Scholar)");
  for (let i = 0; i < scored.length; i++) {
    const s = scored[i];
    const nameEn = getEnglishName(s.code, s.name);
    const papers = await fetchPapers(nameEn, s.code);
    s.pubmed_count = papers.pubmed_count;
    s.high_if_papers = papers.high_if_papers;
    s.total_citations = papers.total_citations;
    papers.pubmed_count > 0 ? stats.papers.ok++ : stats.papers.fail++;
    // 점수 재계산
    s.scored = scoreBio(s);
    if ((i + 1) % 20 === 0) console.log(`  ${i + 1}/${scored.length} 완료`);
    await sleep(1500); // S2 Rate Limit: 5분당 100건 → 3초 간격
  }

  // 캐시 저장
  saveCache();

  // Phase 5: 트랙 분류
  console.log("\n🏷️  Phase 5: 트랙 분류");

  // A 트랙: 점수순 상위 20개
  const trackA = scored
    .sort((a, b) => b.scored.score - a.scored.score)
    .slice(0, 20)
    .map(s => ({
      code: s.code, name: s.name, market: s.market,
      score: s.scored.score, grade: s.scored.grade,
      cat1: s.scored.cat1, cat2: s.scored.cat2, cat3: s.scored.cat3,
      details: s.scored.details,
      data_confidence: s.data_confidence,
      market_cap: s.market_cap, current_price: s.current_price,
      highest_phase: s.highest_phase, pipeline_count: s.pipeline_count,
      has_bigpharma_deal: s.license_out_tier === "top20" || s.license_out_tier === "global",
    }));

  console.log(`  A 트랙 (안정형): ${trackA.length}개`);

  // B 트랙: 3개 조건 중 2개+ 충족 (임상 3상+)
  const trackBCandidates = scored.filter(s => {
    let met = 0;
    // 조건 1: 임상 3상 이상
    if (s.highest_phase === "phase3" || s.highest_phase === "approved") met++;
    // 조건 2: 빅파마 L/O 또는 학회 구두 발표
    if (s.license_out_tier === "top20" || s.license_out_tier === "global" || s.conference_level === "oral_top4") met++;
    // 조건 3: 고영향 논문
    if (s.high_if_papers >= 1 || s.total_citations >= 100) met++;
    return met >= 2;
  });

  // 출시 임박 순 정렬
  const phaseOrder: Record<string, number> = { approved: 0, phase3: 1, phase2: 2, phase1: 3, preclinical: 4, none: 5 };
  trackBCandidates.sort((a, b) => (phaseOrder[a.highest_phase] ?? 5) - (phaseOrder[b.highest_phase] ?? 5));

  console.log(`  B 트랙 (유망형): ${trackBCandidates.length}개`);

  // Phase 6: B 트랙 기술 상세 조사
  console.log("\n🔍 Phase 6: B 트랙 기술 상세 조사");

  const trackB = [];
  for (const s of trackBCandidates) {
    // 3상 이상 파이프라인만 선별
    const phase3Pipelines = s.pipelines.filter(p =>
      p.phase === "PHASE3" || p.phase === "PHASE4" || p.status === "APPROVED"
    );

    const enrichedPipelines = [];
    for (const pl of phase3Pipelines.slice(0, 3)) { // 최대 3개
      console.log(`  ${s.name} — ${pl.title.slice(0, 50)}...`);
      const techDetail = await fetchTechDetail(pl);
      enrichedPipelines.push({
        name: pl.title,
        indication: pl.indication,
        phase: pl.phase,
        phase_status: pl.status,
        start_date: pl.startDate,
        est_completion: pl.completionDate,
        milestones: {
          patent: s.patent_domestic > 0 || s.patent_pct > 0,
          publication: s.pubmed_count > 0,
          preclinical: true,
          phase1: true,
          phase2: true,
          phase3: pl.phase === "PHASE3" || pl.phase === "PHASE4" ? (pl.status === "COMPLETED" ? true : "in_progress") : false,
          nda: pl.status === "APPROVED" ? true : false,
          approved: s.highest_phase === "approved",
        },
        external_validation: [
          ...(s.license_out_tier === "top20" || s.license_out_tier === "global" ? ["bigpharma_lo"] : []),
          ...(s.conference_level === "oral_top4" ? ["asco_oral"] : []),
        ],
        filter_met: (() => { let m = 0; if (s.highest_phase === "phase3" || s.highest_phase === "approved") m++; if (s.license_out_tier === "top20" || s.license_out_tier === "global" || s.conference_level === "oral_top4") m++; if (s.high_if_papers >= 1 || s.total_citations >= 100) m++; return m; })(),
        tech_summary: techDetail.tech_summary,
        tech_detail: techDetail.tech_detail,
        market_impact: techDetail.market_impact,
        global_exclusivity: techDetail.global_exclusivity,
      });
      await sleep(500);
    }

    trackB.push({
      code: s.code, name: s.name, market: s.market,
      score: s.scored.score, grade: s.scored.grade,
      cat1: s.scored.cat1, cat2: s.scored.cat2, cat3: s.scored.cat3,
      details: s.scored.details,
      data_confidence: s.data_confidence,
      market_cap: s.market_cap, current_price: s.current_price,
      pipelines: enrichedPipelines,
    });
  }

  // Phase 7: 출력
  console.log("\n💾 Phase 7: 결과 저장");

  const output = {
    scanned_at: today(),
    total_scanned: bioStocks.length,
    data_sources: {
      kipris: stats.kipris,
      papers: stats.papers,
      clinical: stats.clinical,
      dart: stats.dart,
      naver: stats.naver,
    },
    track_a: {
      count: trackA.length,
      candidates: trackA,
    },
    track_b: {
      count: trackB.length,
      candidates: trackB,
    },
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
  console.log(`  ✓ ${OUTPUT_FILE} 저장 완료`);

  console.log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("✅ 스크리닝 완료");
  console.log(`  A 트랙: ${trackA.length}개 (점수 상위)`);
  console.log(`  B 트랙: ${trackB.length}개 (유망 파이프라인)`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

main().catch((e) => {
  console.error("❌ 오류:", e);
  process.exit(1);
});
