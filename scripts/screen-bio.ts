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
import type {
  ConferenceLevel, HighestPhase, LicenseOutTier, TerminationHistory,
  ContractStructure, CeoBackground, ExitSignal, DisclosureHonesty, FundQuality,
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
const CRIS_API_KEY = process.env.CRIS_API_KEY ?? "";
const CRIS_API_KEY_ENCODED = "fXJ6ry%2FJVib9COG4WZcL35kCAeiVb%2BPJa%2FTswKpwh4NxBNU6MF35DBBtnjc00TVRDY9hb%2BnubRWuIMrrdpFX2w%3D%3D";
const CRIS_LIST = "https://apis.data.go.kr/1352159/crisinfodataview/list";
const CRIS_DETAIL = "https://apis.data.go.kr/1352159/crisinfodataview/detail";

const DATA_DIR = path.resolve("public/data");
const OUTPUT_FILE = path.join(DATA_DIR, "bio-watchlist.json");
const CACHE_FILE = path.join(DATA_DIR, ".bio-cache.json");
const OVERRIDES_FILE = path.join(DATA_DIR, "bio-manual-overrides.json");
const ALIASES_FILE = path.join(DATA_DIR, "bio-company-aliases.json");

const FORCE = process.argv.includes("--force");
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24시간 (기본: DART공시, Naver재무 등 자주 변하는 데이터)
const CACHE_TTL_15D_MS = 15 * 24 * 60 * 60 * 1000; // 15일 (ClinicalTrials, PubMed 등 중간 빈도)
const CACHE_TTL_30D_MS = 30 * 24 * 60 * 60 * 1000; // 30일 (KIPRIS 특허 — 월 1000건 제한, 거의 안 변함)

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

// ── 병명 매핑 ──

const DISEASE_MAP: [RegExp, string][] = [
  [/cancer|carcinoma|tumor|tumour|neoplasm|leukemia|leukaemia|lymphoma|melanoma|sarcoma|myeloma|glioblastoma|glioma|breast|colon|colorectal|hepatocellular|pancrea|gastric|stomach|bladder|prostate|ovarian|cervical|endometrial|thyroid|esophag|cholangiocarcinoma|mesothelioma|neuroblastoma|non.?small.?cell|small.?cell|nsclc|sclc/i, "암"],
  [/alzheimer|dementia|cognitive decline/i, "치매"],
  [/diabetes|diabetic|glycem|t2dm|type.?2.?d/i, "당뇨"],
  [/heart|cardiac|cardiovascular|coronary|atrial|heart failure|hypertension|arrhythmia/i, "심혈관"],
  [/hepatitis|nash|nafld|liver.?(?:disease|fibrosis|cirrhosis)/i, "간질환"],
  [/arthritis|osteoarthritis|rheumatoid/i, "관절염"],
  [/asthma|copd|pulmonary fibrosis|respiratory/i, "호흡기"],
  [/depression|anxiety|bipolar|schizophrenia|psychiatric|adhd/i, "정신건강"],
  [/obesity|metabolic syndrome/i, "비만/대사"],
  [/hiv|covid|influenza|infection|infectious|sepsis|bacterial|viral|fungal/i, "감염병"],
  [/autoimmune|lupus|crohn|colitis|psoriasis|dermatitis|multiple sclerosis|myasthenia/i, "자가면역"],
  [/pain|neuropath|migraine|fibromyalgia/i, "통증"],
  [/eye|ophthalm|macular|retinal|glaucoma/i, "안과"],
  [/kidney|nephro|dialysis|renal/i, "신장"],
  [/parkinson|huntington|als|amyotrophic|neurodegen/i, "신경퇴행"],
  [/stroke|cerebrovascular/i, "뇌혈관"],
  [/anemia|haemophilia|hemophilia|thrombocytopenia|blood/i, "혈액"],
  [/allergy|atopic|urticaria/i, "알레르기"],
  [/lung|pulmonary/i, "폐"],
];

function mapDiseaseCategory(indication: string): string {
  for (const [regex, category] of DISEASE_MAP) {
    if (regex.test(indication)) return category;
  }
  return "기타";
}

const ACTIVE_STATUSES = new Set(["RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"]);

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

const CACHE_TTL_MAP: Record<string, number> = {
  kipris: CACHE_TTL_30D_MS,       // 특허: 30일 (거의 안 변함, 월 1000건 제한)
  papers: CACHE_TTL_15D_MS,       // 논문: 15일
  clinical: CACHE_TTL_15D_MS,     // 임상: 15일
  conference: CACHE_TTL_15D_MS,   // 학회: 15일
  dart_deals: CACHE_TTL_MS,       // DART 공시: 24시간 (수시 공시)
  management: CACHE_TTL_15D_MS,   // 임원/지분: 15일
  cash_runway: CACHE_TTL_MS,      // 재무: 24시간
};

function getCached<T>(code: string, source: string): T | null {
  if (FORCE) return null;
  const entry = cache[code]?.[source];
  if (!entry) return null;
  const ttl = CACHE_TTL_MAP[source] ?? CACHE_TTL_MS;
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
  milestone_ratio?: number;
  disclosure_honesty?: DisclosureHonesty;
  fund_quality?: FundQuality;
  clinical_hype?: boolean;
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

interface PatentData { domestic: number; pct: number; titles: string[]; }

async function fetchPatents(name: string, code: string): Promise<PatentData> {
  const cached = getCached<PatentData>(code, "kipris");
  if (cached) return cached;

  let domestic = 0, pct = 0;
  const titles: string[] = [];
  try {
    // 1페이지로 전체 건수 확인
    const url = `http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch?ServiceKey=${encodeURIComponent(KIPRIS_API_KEY)}&applicant=${encodeURIComponent(name)}&numOfRows=1&pageNo=1`;
    const res = await fetchWithRetry(url);
    if (res.ok) {
      const text = await res.text();
      if (text.includes("<resultCode>00</resultCode>")) {
        const totalMatch = text.match(/<totalCount>(\d+)<\/totalCount>/);
        domestic = totalMatch ? parseInt(totalMatch[1]) : 0;
      }
    }
  } catch (e) {
    console.warn(`  ⚠ KIPRIS 실패 (${name}):`, (e as Error).message);
  }

  const result: PatentData = { domestic, pct, titles };
  if (domestic > 0 || pct > 0) {
    setCache(code, "kipris", result);
  }
  return result;
}

// 2상/3상 파이프라인이 있는 기업만 전체 특허 제목 수집 (키워드 매칭용)
async function fetchPatentTitles(name: string, code: string): Promise<string[]> {
  // 이미 titles가 캐시에 있으면 재사용
  const cached = getCached<PatentData>(code, "kipris");
  if (cached?.titles && cached.titles.length > 0) return cached.titles;

  const titles: string[] = [];
  try {
    let pageNo = 1;
    let totalPages = 1;
    while (pageNo <= totalPages && pageNo <= 10) { // 최대 500건
      const url = `http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch?ServiceKey=${encodeURIComponent(KIPRIS_API_KEY)}&applicant=${encodeURIComponent(name)}&numOfRows=50&pageNo=${pageNo}`;
      const res = await fetchWithRetry(url);
      if (!res.ok) break;
      const text = await res.text();
      if (!text.includes("<resultCode>00</resultCode>")) break;

      // 전체 건수에서 페이지 수 계산
      if (pageNo === 1) {
        const totalMatch = text.match(/<totalCount>(\d+)<\/totalCount>/);
        const total = totalMatch ? parseInt(totalMatch[1]) : 0;
        totalPages = Math.ceil(total / 50);
      }

      // 제목 추출
      const re = /<inventionTitle>([^<]+)<\/inventionTitle>/g;
      let m: RegExpExecArray | null;
      while ((m = re.exec(text)) !== null) titles.push(m[1]);

      pageNo++;
      await sleep(300);
    }
  } catch (e) {
    console.warn(`  ⚠ KIPRIS 제목 수집 실패 (${name}):`, (e as Error).message);
  }

  // 캐시 업데이트
  if (titles.length > 0) {
    const existing = getCached<PatentData>(code, "kipris");
    setCache(code, "kipris", { domestic: existing?.domestic ?? titles.length, pct: existing?.pct ?? 0, titles });
  }

  return titles;
}

// 파이프라인 기술 키워드로 특허 제목 매칭
function matchPatentsByKeywords(titles: string[], keywords: string[]): number {
  if (titles.length === 0 || keywords.length === 0) return 0;
  const lowerKeywords = keywords.map(k => k.toLowerCase());
  return titles.filter(t => {
    const lt = t.toLowerCase();
    return lowerKeywords.some(k => lt.includes(k));
  }).length;
}

// 임상시험 제목+적응증에서 특허 검색 키워드 추출
function extractPatentKeywords(trialName: string, indication: string): string[] {
  const keywords: string[] = [];
  const combined = `${trialName} ${indication}`.toLowerCase();

  // 약물 코드명 (CT-P44, SP-8203, GX-188E 등)
  const codeMatch = combined.match(/\b([a-z]{1,4}[-]?[a-z]?\d{2,5}[a-z]?)\b/gi);
  if (codeMatch) keywords.push(...codeMatch);

  // 성분명 매핑 (흔한 바이오 의약품)
  const DRUG_KEYWORDS: [RegExp, string[]][] = [
    [/daratumumab|darzalex/i, ["CD38", "다라투무맙", "daratumumab", "골수종"]],
    [/pembrolizumab|keytruda/i, ["PD-1", "PD1", "펨브롤리주맙", "면역관문", "pembrolizumab"]],
    [/ocrelizumab|ocrevus/i, ["CD20", "오크렐리주맙", "다발성경화", "ocrelizumab"]],
    [/lazertinib/i, ["EGFR", "레이저티닙", "lazertinib", "티로신키나제"]],
    [/empagliflozin/i, ["SGLT2", "엠파글리플로진", "empagliflozin", "당뇨"]],
    [/pioglitazone/i, ["피오글리타존", "pioglitazone", "인슐린", "당뇨"]],
    [/hyaluron/i, ["히알루론", "hyaluron", "관절"]],
    [/otaplimastat/i, ["오타플리마스타트", "otaplimastat", "MMP", "뇌졸중"]],
    [/candesartan|amlodipine|indapamide/i, ["칸데사르탄", "암로디핀", "고혈압"]],
    [/carnitine|godex/i, ["카르니틴", "carnitine", "오로트산", "고덱스", "지방간"]],
    [/galinpepimut|gps|wt1/i, ["WT1", "galinpepimut", "GPS", "백혈병", "면역"]],
    [/efepoetin|epo/i, ["에포에틴", "EPO", "적혈구", "빈혈", "에리스로포이에틴"]],
    [/vaccine|백신/i, ["백신", "vaccine", "면역"]],
    [/antibody|항체/i, ["항체", "antibody"]],
  ];

  for (const [pattern, kws] of DRUG_KEYWORDS) {
    if (pattern.test(combined)) keywords.push(...kws);
  }

  // 적응증에서 핵심 질환명 추출
  const DISEASE_KW: [RegExp, string[]][] = [
    [/myeloma/i, ["골수종", "myeloma"]],
    [/lung.?cancer|nsclc/i, ["폐암", "lung cancer"]],
    [/leukemia|leukaemia/i, ["백혈병", "leukemia"]],
    [/multiple.?sclerosis/i, ["다발성경화", "sclerosis"]],
    [/stroke/i, ["뇌졸중", "stroke"]],
    [/kidney|renal|ckd/i, ["신장", "kidney", "신부전"]],
    [/liver|hepat|nafld/i, ["간", "liver", "지방간"]],
    [/head.?and.?neck|hnscc/i, ["두경부", "head and neck"]],
    [/osteoarthritis/i, ["골관절염", "관절"]],
    [/hypertension/i, ["고혈압", "hypertension"]],
    [/diabetes|t2dm/i, ["당뇨", "diabetes"]],
  ];

  for (const [pattern, kws] of DISEASE_KW) {
    if (pattern.test(combined)) keywords.push(...kws);
  }

  // 중복 제거
  return [...new Set(keywords)];
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
  withdrawn_terminated_count: number;
  successful_completion_count: number;
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

  const result: ClinicalData = { highest_phase: "none", pipeline_count: 0, results_transparency: 0, pipelines: [], withdrawn_terminated_count: 0, successful_completion_count: 0 };

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
      result.withdrawn_terminated_count = result.pipelines.filter(
        p => p.status === "WITHDRAWN" || p.status === "TERMINATED"
      ).length;
      result.successful_completion_count = result.pipelines.filter(
        p => p.status === "COMPLETED" && p.hasResults
      ).length;
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

// ── Phase 2g: DART 최대주주 — 펀드/VC 감지 ──

const FUND_KEYWORDS = ["투자조합", "벤처", "캐피탈", "PEF", "사모", "펀드", "인베스트"];

async function detectFundPresence(corpCode: string, code: string): Promise<boolean> {
  const cached = getCached<boolean>(code, "fund_detect");
  if (cached !== null && cached !== undefined) return cached;
  if (!corpCode) { setCache(code, "fund_detect", false); return false; }

  try {
    const year = new Date().getFullYear() - 1;
    const url = `${DART_API}/hyslrChgSttus.json?crtfc_key=${DART_API_KEY}&corp_code=${corpCode}&bsns_year=${year}&reprt_code=11011`;
    const res = await fetchWithRetry(url);
    if (res.ok) {
      const json = await res.json();
      if (json.status === "000" && json.list) {
        const hasFund = json.list.some((sh: { nm?: string }) =>
          FUND_KEYWORDS.some(kw => (sh.nm || "").includes(kw))
        );
        setCache(code, "fund_detect", hasFund);
        return hasFund;
      }
    }
  } catch (e) {
    console.warn(`  ⚠ DART 주주 실패 (${corpCode}):`, (e as Error).message);
  }

  setCache(code, "fund_detect", false);
  return false;
}

// ── CRIS 임상연구정보서비스 수집 ──

interface CrisListItem {
  trial_id: string;
  source_name_kr: string;
  primary_sponsor_kr: string;
  scientific_title_kr: string;
  scientific_title_en: string;
  type_enrolment_kr: string;
  date_enrolment: string;
  results_date_completed: string;
  phase_kr: string;
  study_type_kr: string;
  i_freetext_kr: string;
}

const CRIS_ACTIVE_STATUSES = new Set(["대상자 모집 중", "대상자 모집 전", "예정"]);

function extractPhaseFromTitle(titleEn: string): "PHASE2" | "PHASE3" | null {
  if (/phase\s*(3|iii)\b/i.test(titleEn)) return "PHASE3";
  if (/phase\s*(2|ii)\b/i.test(titleEn)) return "PHASE2";
  return null;
}

async function fetchCrisTrials(bioCompanyNames: Map<string, { code: string; name: string; market: string; marketCap: number }>): Promise<{
  trial_id: string;
  company: { code: string; name: string; market: string; market_cap: number };
  title_kr: string;
  title_en: string;
  indication_kr: string;
  phase: "PHASE2" | "PHASE3";
  status: string;
  start_date: string;
  est_completion: string;
  data_source: "cris";
}[]> {
  if (!CRIS_API_KEY) {
    console.log("  ⚠ CRIS_API_KEY 미설정 — CRIS 수집 건너뜀");
    return [];
  }

  const searches = ["Phase 2", "Phase II", "Phase 3", "Phase III"];
  const seen = new Set<string>(); // trial_id 중복 제거
  const matched: CrisListItem[] = [];

  for (const query of searches) {
    let pageNo = 1;
    let totalPages = 1;

    while (pageNo <= totalPages) {
      try {
        const url = `${CRIS_LIST}?serviceKey=${encodeURIComponent(CRIS_API_KEY)}&resultType=JSON&numOfRows=50&pageNo=${pageNo}&srchWord=${encodeURIComponent(query)}`;
        const res = await fetchWithRetry(url);
        if (!res.ok) break;
        const json = await res.json();
        if (json.resultCode !== "00") break;

        const total = json.totalCount || 0;
        totalPages = Math.ceil(total / 50);
        const items: CrisListItem[] = json.items || [];

        for (const item of items) {
          if (seen.has(item.trial_id)) continue;
          seen.add(item.trial_id);

          // 바이오 기업 매칭 (source_name_kr 또는 primary_sponsor_kr)
          const src = (item.source_name_kr || "") + "|" + (item.primary_sponsor_kr || "");
          for (const [companyName] of bioCompanyNames) {
            if (src.includes(companyName)) {
              matched.push(item);
              break;
            }
          }
        }
      } catch (e) {
        console.warn(`  ⚠ CRIS list 실패 (${query} p${pageNo}):`, (e as Error).message);
      }
      pageNo++;
      await sleep(300);
    }
    console.log(`  CRIS "${query}": ${seen.size}건 수집`);
  }

  console.log(`  CRIS 바이오 기업 매칭: ${matched.length}건`);

  // detail API로 상세 조회 (모집상태, 적응증 등)
  const results: Awaited<ReturnType<typeof fetchCrisTrials>> = [];

  for (const item of matched) {
    const phase = extractPhaseFromTitle(item.scientific_title_en);
    if (!phase) continue;

    try {
      const detailUrl = `${CRIS_DETAIL}?serviceKey=${CRIS_API_KEY_ENCODED}&resultType=JSON&crisNumber=${item.trial_id}`;
      const res = await fetchWithRetry(detailUrl);
      if (!res.ok) continue;
      const detail = await res.json();

      const recruitmentStatus = detail.recruitment_status_kr || "";
      // 진행 중인 것만
      if (!CRIS_ACTIVE_STATUSES.has(recruitmentStatus) && recruitmentStatus !== "실제등록") continue;

      // 펀딩 기업에서 매칭된 기업 찾기
      const fundingNames = (detail.funding_items || []).map((f: { source_name_kr?: string }) => f.source_name_kr || "");
      const sponsorNames = (detail.sponsor_items || []).map((s: { primary_sponsor_kr?: string }) => s.primary_sponsor_kr || "");
      const allNames = [...fundingNames, ...sponsorNames].join("|");

      let matchedCompany: { code: string; name: string; market: string; market_cap: number } | null = null;
      for (const [companyName, info] of bioCompanyNames) {
        if (allNames.includes(companyName)) {
          matchedCompany = { code: info.code, name: info.name, market: info.market, market_cap: info.marketCap };
          break;
        }
      }
      if (!matchedCompany) continue;

      // 적응증 추출
      const condition = detail.hc_freetext_kr || detail.health_condition_kr || "";

      results.push({
        trial_id: item.trial_id,
        company: matchedCompany,
        title_kr: item.scientific_title_kr || "",
        title_en: item.scientific_title_en || "",
        indication_kr: condition,
        phase,
        status: recruitmentStatus,
        start_date: item.date_enrolment || "",
        est_completion: item.results_date_completed || "",
        data_source: "cris",
      });
    } catch (e) {
      console.warn(`  ⚠ CRIS detail 실패 (${item.trial_id}):`, (e as Error).message);
    }
    await sleep(300);
  }

  return results;
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

  // Phase 2: 외부 API 수집
  console.log("\n📊 Phase 2: 데이터 수집");

  interface CollectedBio {
    code: string; name: string; market: string; marketCap: number; price: number;
    patent_domestic: number; patent_pct: number;
    pubmed_count: number; high_if_papers: number; total_citations: number;
    conference_level: ConferenceLevel | null;
    license_out_tier: LicenseOutTier; termination_history: TerminationHistory;
    contract_structure: ContractStructure | null; milestone_ratio: number | null;
    ceo_background: CeoBackground;
    pipelines: PipelineInfo[];
  }

  const collected: CollectedBio[] = [];
  const BATCH_SIZE = 5;

  async function processStock(stock: BioStock, idx: number): Promise<CollectedBio> {
    const corpCode = corpMap.get(stock.code) || "";
    const nameEn = getEnglishName(stock.code, stock.name);
    const override = overrides[stock.code] || {};

    const [patents, clinical, deals, mgmt, , conferenceFromNews] = await Promise.all([
      fetchPatents(stock.name, stock.code),
      fetchClinicalTrials(nameEn, stock.code),
      fetchDartDeals(corpCode, stock.code),
      fetchManagement(corpCode, stock.code),
      fetchCashRunway(stock.code),
      fetchConferenceLevel(stock.name, stock.code),
    ]);

    const conferenceLevel: ConferenceLevel | null = override.conference_level ?? conferenceFromNews ?? null;
    const ceoBg: CeoBackground = override.ceo_background ?? mgmt.ceo_background;

    // 통계
    patents.domestic > 0 ? stats.kipris.ok++ : stats.kipris.fail++;
    clinical.pipeline_count > 0 ? stats.clinical.ok++ : stats.clinical.fail++;
    deals.license_out_tier !== "none" ? stats.dart.ok++ : stats.dart.fail++;

    console.log(`  [${idx}/${bioStocks.length}] ${stock.name} — 파이프라인 ${clinical.pipeline_count}개`);

    return {
      code: stock.code, name: stock.name, market: stock.market,
      marketCap: stock.marketCap, price: stock.price,
      patent_domestic: patents.domestic, patent_pct: patents.pct,
      pubmed_count: 0, high_if_papers: 0, total_citations: 0, // Phase 2.5에서 채움
      conference_level: conferenceLevel,
      license_out_tier: deals.license_out_tier, termination_history: deals.termination_history,
      contract_structure: override.contract_structure ?? null,
      milestone_ratio: override.milestone_ratio ?? null,
      ceo_background: ceoBg,
      pipelines: clinical.pipelines,
    };
  }

  // 배치 병렬 실행
  for (let i = 0; i < bioStocks.length; i += BATCH_SIZE) {
    const batch = bioStocks.slice(i, i + BATCH_SIZE);
    const results = await Promise.all(
      batch.map((stock, bi) => processStock(stock, i + bi + 1))
    );
    collected.push(...results);
    if (i + BATCH_SIZE < bioStocks.length) await sleep(500);
  }

  // Phase 3: 임상 2상/3상 진행 중인 파이프라인만 선별
  console.log("\n🔬 Phase 3: 임상 2상/3상 진행 중 파이프라인 선별");

  interface ActivePipeline {
    company: CollectedBio;
    pipeline: PipelineInfo;
  }

  const activePipelines: ActivePipeline[] = [];
  for (const s of collected) {
    for (const pl of s.pipelines) {
      const isPhase23 = pl.phase === "PHASE2" || pl.phase === "PHASE3";
      const isActive = ACTIVE_STATUSES.has(pl.status);
      if (isPhase23 && isActive) {
        activePipelines.push({ company: s, pipeline: pl });
      }
    }
  }

  console.log(`  CT.gov 2상/3상 진행 중: ${activePipelines.length}건 (${new Set(activePipelines.map(a => a.company.code)).size}개 기업)`);

  // Phase 3-CRIS: CRIS 임상연구정보서비스에서 추가 수집
  console.log("\n🇰🇷 Phase 3-CRIS: 한국 임상연구정보서비스 수집");

  // 바이오 기업 이름 → 정보 매핑 (CRIS에서 기업명 매칭용)
  const bioCompanyMap = new Map<string, { code: string; name: string; market: string; marketCap: number }>();
  for (const s of bioStocks) {
    bioCompanyMap.set(s.name, { code: s.code, name: s.name, market: s.market, marketCap: s.marketCap });
  }

  const crisTrials = await fetchCrisTrials(bioCompanyMap);
  console.log(`  CRIS 2상/3상 진행 중: ${crisTrials.length}건`);

  // CRIS 결과를 activePipelines와 동일한 형태로 병합
  // CRIS에서 온 기업의 기존 collected 데이터를 찾거나 빈 데이터 생성
  for (const ct of crisTrials) {
    const existing = collected.find(c => c.code === ct.company.code);
    const pl: PipelineInfo = {
      nctId: ct.trial_id, // KCT 번호
      title: ct.title_kr || ct.title_en,
      indication: ct.indication_kr || ct.title_en,
      phase: ct.phase,
      status: ct.status === "대상자 모집 중" ? "RECRUITING" : ct.status === "실제등록" ? "ACTIVE_NOT_RECRUITING" : "NOT_YET_RECRUITING",
      startDate: ct.start_date,
      completionDate: ct.est_completion,
      hasResults: false,
    };

    if (existing) {
      activePipelines.push({ company: existing, pipeline: pl });
    } else {
      // collected에 없는 기업은 빈 데이터로 추가
      const stub: CollectedBio = {
        code: ct.company.code, name: ct.company.name, market: ct.company.market,
        marketCap: ct.company.market_cap, price: 0,
        patent_domestic: 0, patent_pct: 0,
        pubmed_count: 0, high_if_papers: 0, total_citations: 0,
        conference_level: null,
        license_out_tier: "none" as LicenseOutTier, termination_history: "none" as TerminationHistory,
        contract_structure: null, milestone_ratio: null,
        ceo_background: "unknown" as CeoBackground,
        pipelines: [],
      };
      collected.push(stub);
      activePipelines.push({ company: stub, pipeline: pl });
    }
  }

  console.log(`  통합 2상/3상: ${activePipelines.length}건 (${new Set(activePipelines.map(a => a.company.code)).size}개 기업)`);

  // Phase 3.5: 선별된 파이프라인의 기업에 대해 논문 데이터 수집
  const companiesWithPipelines = [...new Set(activePipelines.map(a => a.company.code))];
  console.log(`\n📄 Phase 3.5: 논문 데이터 순차 수집 (${companiesWithPipelines.length}개 기업)`);

  for (const code of companiesWithPipelines) {
    const s = collected.find(c => c.code === code)!;
    const nameEn = getEnglishName(s.code, s.name);
    const papers = await fetchPapers(nameEn, s.code);
    s.pubmed_count = papers.pubmed_count;
    s.high_if_papers = papers.high_if_papers;
    s.total_citations = papers.total_citations;
    papers.pubmed_count > 0 ? stats.papers.ok++ : stats.papers.fail++;
    await sleep(1500);
  }

  // Phase 3.7: 파이프라인 기업의 특허 제목 수집 (키워드 매칭용)
  const pipelineCompanyCodes = [...new Set(activePipelines.map(a => a.company.code))];
  console.log(`\n📜 Phase 3.7: 특허 제목 수집 (${pipelineCompanyCodes.length}개 기업)`);

  const patentTitlesMap = new Map<string, string[]>();
  for (const code of pipelineCompanyCodes) {
    const s = collected.find(c => c.code === code);
    if (!s) continue;
    const titles = await fetchPatentTitles(s.name, s.code);
    patentTitlesMap.set(code, titles);
    console.log(`  ${s.name}: ${titles.length}건 제목 수집`);
  }

  // Phase 4: 기술 상세 조사 + 경쟁 분석
  console.log("\n🔍 Phase 4: 기술 상세 조사");

  interface OutputPipeline {
    nct_id: string;
    data_source: "ct.gov" | "cris";
    company: { code: string; name: string; market: string; market_cap: number };
    trial_name: string;
    indication: string;
    disease_category: string;
    phase: string;
    status: string;
    start_date: string;
    est_completion: string;
    tech_summary_en: string;
    competing_phase3_count: number;
    quality: {
      patent_matched_count: number;
      patent_search_keywords: string[];
      high_if_papers: number;
      total_citations: number;
      conference_level: string | null;
      has_results_posted: boolean;
      bigpharma_deal: { tier: string; terminated: boolean };
      contract_structure: string | null;
      milestone_ratio: number | null;
      ceo_background: string;
      phase1_cleared: boolean;
    };
  }

  const outputPipelines: OutputPipeline[] = [];
  for (const { company: s, pipeline: pl } of activePipelines) {
    const isCris = pl.nctId.startsWith("KCT");
    console.log(`  ${isCris ? "🇰🇷" : "🌐"} ${s.name} — ${pl.title.slice(0, 50)}...`);
    const techDetail = isCris ? { tech_summary: "", tech_detail: "", market_impact: "", global_exclusivity: { competing_trials: 0, patent_scope: "", uniqueness: "" } } : await fetchTechDetail(pl);

    const patentTitles = patentTitlesMap.get(s.code) || [];
    const patentKeywords = extractPatentKeywords(pl.title, pl.indication);
    const patentMatchedCount = matchPatentsByKeywords(patentTitles, patentKeywords);

    outputPipelines.push({
      nct_id: pl.nctId,
      data_source: isCris ? "cris" : "ct.gov",
      company: { code: s.code, name: s.name, market: s.market, market_cap: s.marketCap },
      trial_name: pl.title,
      indication: pl.indication,
      disease_category: mapDiseaseCategory(pl.indication),
      phase: pl.phase,
      status: pl.status,
      start_date: pl.startDate,
      est_completion: pl.completionDate,
      tech_summary_en: techDetail.tech_summary,
      competing_phase3_count: techDetail.global_exclusivity.competing_trials,
      quality: {
        patent_matched_count: patentMatchedCount,
        patent_search_keywords: patentKeywords,
        high_if_papers: s.high_if_papers,
        total_citations: s.total_citations,
        conference_level: s.conference_level,
        has_results_posted: pl.hasResults,
        bigpharma_deal: { tier: s.license_out_tier, terminated: s.termination_history === "terminated" },
        contract_structure: s.contract_structure,
        milestone_ratio: s.milestone_ratio,
        ceo_background: s.ceo_background,
        phase1_cleared: true, // 2상/3상이면 1상 통과
      },
    });
    await sleep(500);
  }

  // 캐시 저장
  saveCache();

  // Phase 5: 출력
  console.log("\n💾 Phase 5: 결과 저장");

  // 3상 우선, 같은 단계면 병명 알파벳순
  outputPipelines.sort((a, b) => {
    const phaseOrder: Record<string, number> = { PHASE3: 0, PHASE2: 1 };
    const pDiff = (phaseOrder[a.phase] ?? 9) - (phaseOrder[b.phase] ?? 9);
    if (pDiff !== 0) return pDiff;
    return a.disease_category.localeCompare(b.disease_category);
  });

  const output = {
    scanned_at: today(),
    total_scanned: bioStocks.length,
    active_pipeline_count: outputPipelines.length,
    data_sources: {
      kipris: stats.kipris,
      papers: stats.papers,
      clinical: stats.clinical,
      dart: stats.dart,
    },
    pipelines: outputPipelines,
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
  console.log(`  ✓ ${OUTPUT_FILE} 저장 완료`);

  console.log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("✅ 스크리닝 완료");
  console.log(`  전체 스캔: ${bioStocks.length}개`);
  console.log(`  2상/3상 진행 중: ${outputPipelines.length}건`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

main().catch((e) => {
  console.error("❌ 오류:", e);
  process.exit(1);
});
