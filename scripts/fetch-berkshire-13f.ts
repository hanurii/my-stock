/**
 * 버크셔 해서웨이 13F 포트폴리오 데이터 수집 스크립트
 *
 * SEC EDGAR API에서 최신 13F-HR 보고서를 가져와 파싱하고,
 * 이전 분기 대비 변화를 계산하여 JSON으로 저장합니다.
 *
 * 사용법: npx tsx scripts/fetch-berkshire-13f.ts
 */
import fs from "fs";
import path from "path";

// ── 설정 ──

const CIK = "0001067983"; // Berkshire Hathaway
const SUBMISSIONS_URL = `https://data.sec.gov/submissions/CIK${CIK}.json`;
const ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data/1067983";
const UA = "my-stock-app contact@example.com";
const REQUEST_DELAY_MS = 500;
const MAX_HISTORY = 4;

const OUTPUT_PATH = path.join(process.cwd(), "public", "data", "berkshire-13f.json");

// ── 타입 ──

interface Holding {
  rank: number;
  name: string;
  name_kr: string | null;
  ticker: string | null;
  cusip: string;
  title_of_class: string;
  value: number;
  shares: number;
  weight_pct: number;
  sector: string | null;
}

interface ChangeEntry {
  name: string;
  ticker: string | null;
  cusip: string;
  current_shares: number;
  previous_shares: number;
  current_value: number;
  change_pct: number;
  current_weight_pct: number;
}

interface SectorAllocation {
  sector: string;
  value: number;
  weight_pct: number;
  count: number;
}

interface HistoricalFiling {
  accession_number: string;
  filing_date: string;
  report_period: string;
  total_value: number;
  total_positions: number;
  top5: { name: string; ticker: string | null; weight_pct: number }[];
}

interface Berkshire13FData {
  generated_at: string;
  is_new: boolean;
  new_label_until?: string;
  latest: {
    accession_number: string;
    filing_date: string;
    report_period: string;
    total_value: number;
    total_positions: number;
    holdings: Holding[];
    changes: {
      new_buys: ChangeEntry[];
      increased: ChangeEntry[];
      decreased: ChangeEntry[];
      exits: ChangeEntry[];
    };
    sectors: SectorAllocation[];
    concentration: { top5_pct: number; top10_pct: number };
  };
  history: HistoricalFiling[];
  cash_trend: CashDataPoint[];
}

// ── CUSIP → 티커/섹터 매핑 ──

const CUSIP_MAP: Record<string, { ticker: string; sector: string; name_kr: string }> = {
  // Top holdings
  "037833100": { ticker: "AAPL", sector: "Technology", name_kr: "애플" },
  "025816109": { ticker: "AXP", sector: "Financials", name_kr: "아메리칸 익스프레스" },
  "060505104": { ticker: "BAC", sector: "Financials", name_kr: "뱅크오브아메리카" },
  "191216100": { ticker: "KO", sector: "Consumer Staples", name_kr: "코카콜라" },
  "166764100": { ticker: "CVX", sector: "Energy", name_kr: "셰브론" },
  "674599105": { ticker: "OXY", sector: "Energy", name_kr: "옥시덴탈 페트롤리엄" },
  "615369105": { ticker: "MCO", sector: "Financials", name_kr: "무디스" },
  "H1467J104": { ticker: "CB", sector: "Financials", name_kr: "처브" },
  "500754106": { ticker: "KHC", sector: "Consumer Staples", name_kr: "크래프트 하인즈" },
  "23918K108": { ticker: "DVA", sector: "Healthcare", name_kr: "다비타" },
  "501044101": { ticker: "KR", sector: "Consumer Staples", name_kr: "크로거" },
  "829933100": { ticker: "SIRI", sector: "Communication", name_kr: "시리우스XM" },
  "57636Q104": { ticker: "MA", sector: "Financials", name_kr: "마스터카드" },
  "92826C839": { ticker: "V", sector: "Financials", name_kr: "비자" },
  "21036P108": { ticker: "STZ", sector: "Consumer Staples", name_kr: "컨스텔레이션 브랜즈" },
  "14040H105": { ticker: "COF", sector: "Financials", name_kr: "캐피탈원" },
  "91324P102": { ticker: "UNH", sector: "Healthcare", name_kr: "유나이티드헬스" },
  "25754A201": { ticker: "DPZ", sector: "Consumer Discretionary", name_kr: "도미노피자" },
  "02005N100": { ticker: "ALLY", sector: "Financials", name_kr: "앨라이 파이낸셜" },
  "G0403H108": { ticker: "AON", sector: "Financials", name_kr: "에이온" },
  "670346105": { ticker: "NUE", sector: "Materials", name_kr: "뉴코어" },
  "530909308": { ticker: "LLYVK", sector: "Communication", name_kr: "리버티 라이브" },
  "526057104": { ticker: "LEN", sector: "Consumer Discretionary", name_kr: "레나" },
  "73278L105": { ticker: "POOL", sector: "Consumer Discretionary", name_kr: "풀 코퍼레이션" },
  "546347105": { ticker: "LPX", sector: "Materials", name_kr: "루이지애나 퍼시픽" },
  "530909100": { ticker: "LLYVA", sector: "Communication", name_kr: "리버티 라이브" },
  "650111107": { ticker: "NYT", sector: "Communication", name_kr: "뉴욕타임스" },
  "422806208": { ticker: "HEI", sector: "Industrials", name_kr: "헤이코" },
  "404119982": { ticker: "HEI.A", sector: "Industrials", name_kr: "헤이코" },
  "404119974": { ticker: "HEI", sector: "Industrials", name_kr: "헤이코" },
  "531229755": { ticker: "FWONA", sector: "Communication", name_kr: "리버티 미디어" },
  "16119P108": { ticker: "CHTR", sector: "Communication", name_kr: "차터 커뮤니케이션즈" },
  "512816109": { ticker: "LAMR", sector: "Real Estate", name_kr: "라마 광고" },
  "G0176J109": { ticker: "ALLE", sector: "Industrials", name_kr: "알레지온" },
  "62944T105": { ticker: "NVR", sector: "Consumer Discretionary", name_kr: "NVR" },
  "47233W109": { ticker: "JEF", sector: "Financials", name_kr: "제프리스" },
  "25243Q205": { ticker: "DEO", sector: "Consumer Staples", name_kr: "디아지오" },
  "G9001E102": { ticker: "LILAK", sector: "Communication", name_kr: "리버티 라틴아메리카" },
  "526057302": { ticker: "LEN.B", sector: "Consumer Discretionary", name_kr: "레나" },
  "G9001E128": { ticker: "LILA", sector: "Communication", name_kr: "리버티 라틴아메리카" },
  "047726302": { ticker: "BATRA", sector: "Communication", name_kr: "애틀랜타 브레이브스" },
  // Additional known
  "172967424": { ticker: "C", sector: "Financials", name_kr: "씨티그룹" },
  "172967G88": { ticker: "C", sector: "Financials", name_kr: "씨티그룹" },
  "437076102": { ticker: "HCA", sector: "Healthcare", name_kr: "HCA 헬스케어" },
  "023135106": { ticker: "AMZN", sector: "Consumer Discretionary", name_kr: "아마존" },
  "02079K305": { ticker: "GOOGL", sector: "Communication", name_kr: "알파벳(구글)" },
  "02079K107": { ticker: "GOOG", sector: "Communication", name_kr: "알파벳(구글)" },
  "68389X105": { ticker: "ORCL", sector: "Technology", name_kr: "오라클" },
  "742718109": { ticker: "PG", sector: "Consumer Staples", name_kr: "P&G" },
  "742718301": { ticker: "PG", sector: "Consumer Staples", name_kr: "P&G" },
  "882508104": { ticker: "TXN", sector: "Technology", name_kr: "텍사스 인스트루먼츠" },
  "45866F104": { ticker: "ICE", sector: "Financials", name_kr: "인터콘티넨탈 거래소" },
  "30231G102": { ticker: "XOM", sector: "Energy", name_kr: "엑슨모빌" },
  "74460D109": { ticker: "PSX", sector: "Energy", name_kr: "필립스66" },
  "635017106": { ticker: "NU", sector: "Financials", name_kr: "누뱅크" },
  "808513105": { ticker: "SCHW", sector: "Financials", name_kr: "찰스슈왑" },
  "718546104": { ticker: "PFE", sector: "Healthcare", name_kr: "화이자" },
  "126650100": { ticker: "CVS", sector: "Healthcare", name_kr: "CVS헬스" },
  "228227100": { ticker: "CRM", sector: "Technology", name_kr: "세일즈포스" },
  "00724F101": { ticker: "ADBE", sector: "Technology", name_kr: "어도비" },
  "594918104": { ticker: "MSFT", sector: "Technology", name_kr: "마이크로소프트" },
  "92343V104": { ticker: "VRSN", sector: "Technology", name_kr: "베리사인" },
  "31620M106": { ticker: "FIS", sector: "Technology", name_kr: "피델리티 내셔널" },
  "87612E106": { ticker: "TMUS", sector: "Communication", name_kr: "T-모바일" },
  "254687106": { ticker: "DIS", sector: "Communication", name_kr: "디즈니" },
  "544248108": { ticker: "LOW", sector: "Consumer Discretionary", name_kr: "로우스" },
  "580589109": { ticker: "MCD", sector: "Consumer Discretionary", name_kr: "맥도날드" },
  "756109104": { ticker: "RCL", sector: "Consumer Discretionary", name_kr: "로열캐리비안" },
  "655044105": { ticker: "NKE", sector: "Consumer Discretionary", name_kr: "나이키" },
  "907818108": { ticker: "UPS", sector: "Industrials", name_kr: "UPS" },
  "369604301": { ticker: "GE", sector: "Industrials", name_kr: "GE 에어로스페이스" },
  "822582102": { ticker: "SHEL", sector: "Energy", name_kr: "셸" },
  "29379V103": { ticker: "ENB", sector: "Energy", name_kr: "엔브리지" },
  "92343E102": { ticker: "VRSN", sector: "Technology", name_kr: "베리사인" },
};

// ── 유틸 ──

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function fetchJSON(url: string): Promise<unknown> {
  const res = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
  return res.json();
}

async function fetchText(url: string): Promise<string> {
  const res = await fetch(url, { headers: { "User-Agent": UA } });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
  return res.text();
}

function cleanName(name: string): string {
  return name
    .replace(/\s+/g, " ")
    .replace(/\bCORP\b/i, "Corp")
    .replace(/\bINC\b/i, "Inc")
    .replace(/\bLTD\b/i, "Ltd")
    .replace(/\bCO\b/i, "Co")
    .replace(/\bHLDGS\b/i, "Holdings")
    .replace(/\bGRP\b/i, "Group")
    .trim();
}

// ── SEC EDGAR 데이터 수집 ──

interface RawHolding {
  nameOfIssuer: string;
  titleOfClass: string;
  cusip: string;
  value: number; // dollars (SEC reports in $1000s, we convert)
  shares: number;
}

async function findLatest13F(): Promise<{
  accessionNumber: string;
  filingDate: string;
  reportDate: string;
} | null> {
  console.log("📡 SEC EDGAR Submissions API 조회...");
  const data = await fetchJSON(SUBMISSIONS_URL) as {
    filings: {
      recent: {
        accessionNumber: string[];
        filingDate: string[];
        reportDate: string[];
        form: string[];
        primaryDocument: string[];
      };
    };
  };

  const recent = data.filings.recent;
  for (let i = 0; i < recent.form.length; i++) {
    if (recent.form[i] === "13F-HR") {
      return {
        accessionNumber: recent.accessionNumber[i],
        filingDate: recent.filingDate[i],
        reportDate: recent.reportDate[i],
      };
    }
  }
  return null;
}

async function fetchInfoTableXml(accessionNumber: string): Promise<string> {
  const accNoHyphens = accessionNumber.replace(/-/g, "");
  const indexUrl = `${ARCHIVES_BASE}/${accNoHyphens}/index.json`;

  console.log("📡 Filing index 조회...");
  const indexData = await fetchJSON(indexUrl) as {
    directory: { item: { name: string; type: string }[] };
  };

  // information table XML 파일 찾기
  const xmlDoc = indexData.directory.item.find(
    (item) =>
      item.name.endsWith(".xml") &&
      item.name !== "primary_doc.xml" &&
      !item.name.endsWith("-index.xml"),
  );

  if (!xmlDoc) throw new Error("Information table XML을 찾을 수 없습니다");

  const xmlUrl = `${ARCHIVES_BASE}/${accNoHyphens}/${xmlDoc.name}`;
  console.log(`📡 Holdings XML 다운로드: ${xmlDoc.name}`);
  await sleep(REQUEST_DELAY_MS);
  return fetchText(xmlUrl);
}

function parseHoldingsXml(xml: string): RawHolding[] {
  const holdings: RawHolding[] = [];

  // 네임스페이스 제거
  const cleaned = xml.replace(/<\/?\w+:/g, (m) => m.replace(/\w+:/, ""));

  // <infoTable> 엔트리 파싱
  const entryRegex = /<infoTable>([\s\S]*?)<\/infoTable>/g;
  let match;

  while ((match = entryRegex.exec(cleaned)) !== null) {
    const entry = match[1];

    const getTag = (tag: string): string => {
      const m = entry.match(new RegExp(`<${tag}>([^<]*)</${tag}>`));
      return m ? m[1].trim() : "";
    };

    const name = getTag("nameOfIssuer");
    const title = getTag("titleOfClass");
    const cusip = getTag("cusip");
    const value = parseInt(getTag("value"), 10) || 0;
    const shares = parseInt(getTag("sshPrnamt"), 10) || 0;

    if (name && cusip) {
      holdings.push({
        nameOfIssuer: name,
        titleOfClass: title,
        cusip,
        value, // SEC 13F XML value is already in dollars
        shares,
      });
    }
  }

  return holdings;
}

function aggregateByCusip(raw: RawHolding[]): Holding[] {
  const map = new Map<string, { name: string; title: string; cusip: string; value: number; shares: number }>();

  for (const h of raw) {
    const existing = map.get(h.cusip);
    if (existing) {
      existing.value += h.value;
      existing.shares += h.shares;
    } else {
      map.set(h.cusip, {
        name: cleanName(h.nameOfIssuer),
        title: h.titleOfClass,
        cusip: h.cusip,
        value: h.value,
        shares: h.shares,
      });
    }
  }

  const totalValue = Array.from(map.values()).reduce((s, h) => s + h.value, 0);

  const holdings: Holding[] = Array.from(map.values())
    .sort((a, b) => b.value - a.value)
    .map((h, i) => {
      const info = CUSIP_MAP[h.cusip];
      return {
        rank: i + 1,
        name: h.name,
        name_kr: info?.name_kr ?? null,
        ticker: info?.ticker ?? null,
        cusip: h.cusip,
        title_of_class: h.title,
        value: h.value,
        shares: h.shares,
        weight_pct: totalValue > 0 ? parseFloat(((h.value / totalValue) * 100).toFixed(2)) : 0,
        sector: info?.sector ?? null,
      };
    });

  // 매핑 안 된 CUSIP 로깅
  const unmapped = holdings.filter((h) => !h.ticker);
  if (unmapped.length > 0) {
    console.log(`\n⚠️ 매핑 안 된 CUSIP ${unmapped.length}개:`);
    unmapped.forEach((h) => console.log(`   ${h.cusip} — ${h.name} ($${(h.value / 1e6).toFixed(0)}M)`));
  }

  return holdings;
}

// ── 변화 계산 ──

function computeChanges(
  current: Holding[],
  previous: Holding[],
): Berkshire13FData["latest"]["changes"] {
  const prevMap = new Map(previous.map((h) => [h.cusip, h]));
  const currMap = new Map(current.map((h) => [h.cusip, h]));

  const new_buys: ChangeEntry[] = [];
  const increased: ChangeEntry[] = [];
  const decreased: ChangeEntry[] = [];
  const exits: ChangeEntry[] = [];

  for (const curr of current) {
    const prev = prevMap.get(curr.cusip);
    if (!prev) {
      new_buys.push({
        name: curr.name,
        ticker: curr.ticker,
        cusip: curr.cusip,
        current_shares: curr.shares,
        previous_shares: 0,
        current_value: curr.value,
        change_pct: 100,
        current_weight_pct: curr.weight_pct,
      });
    } else if (curr.shares > prev.shares) {
      const changePct = prev.shares > 0 ? ((curr.shares - prev.shares) / prev.shares) * 100 : 100;
      increased.push({
        name: curr.name,
        ticker: curr.ticker,
        cusip: curr.cusip,
        current_shares: curr.shares,
        previous_shares: prev.shares,
        current_value: curr.value,
        change_pct: parseFloat(changePct.toFixed(1)),
        current_weight_pct: curr.weight_pct,
      });
    } else if (curr.shares < prev.shares) {
      const changePct = prev.shares > 0 ? ((curr.shares - prev.shares) / prev.shares) * 100 : 0;
      decreased.push({
        name: curr.name,
        ticker: curr.ticker,
        cusip: curr.cusip,
        current_shares: curr.shares,
        previous_shares: prev.shares,
        current_value: curr.value,
        change_pct: parseFloat(changePct.toFixed(1)),
        current_weight_pct: curr.weight_pct,
      });
    }
  }

  for (const prev of previous) {
    if (!currMap.has(prev.cusip)) {
      exits.push({
        name: prev.name,
        ticker: prev.ticker,
        cusip: prev.cusip,
        current_shares: 0,
        previous_shares: prev.shares,
        current_value: 0,
        change_pct: -100,
        current_weight_pct: 0,
      });
    }
  }

  return {
    new_buys: new_buys.sort((a, b) => b.current_value - a.current_value),
    increased: increased.sort((a, b) => b.current_value - a.current_value),
    decreased: decreased.sort((a, b) => b.current_value - a.current_value),
    exits: exits.sort((a, b) => b.previous_shares - a.previous_shares),
  };
}

// ── 섹터/집중도 ──

function computeSectors(holdings: Holding[]): SectorAllocation[] {
  const map = new Map<string, { value: number; count: number }>();
  const totalValue = holdings.reduce((s, h) => s + h.value, 0);

  for (const h of holdings) {
    const sector = h.sector || "기타";
    const existing = map.get(sector) || { value: 0, count: 0 };
    existing.value += h.value;
    existing.count++;
    map.set(sector, existing);
  }

  return Array.from(map.entries())
    .map(([sector, data]) => ({
      sector,
      value: data.value,
      weight_pct: totalValue > 0 ? parseFloat(((data.value / totalValue) * 100).toFixed(1)) : 0,
      count: data.count,
    }))
    .sort((a, b) => b.value - a.value);
}

function computeConcentration(holdings: Holding[]): { top5_pct: number; top10_pct: number } {
  const sorted = [...holdings].sort((a, b) => b.value - a.value);
  const total = sorted.reduce((s, h) => s + h.value, 0);
  if (total === 0) return { top5_pct: 0, top10_pct: 0 };

  const top5 = sorted.slice(0, 5).reduce((s, h) => s + h.value, 0);
  const top10 = sorted.slice(0, 10).reduce((s, h) => s + h.value, 0);

  return {
    top5_pct: parseFloat(((top5 / total) * 100).toFixed(1)),
    top10_pct: parseFloat(((top10 / total) * 100).toFixed(1)),
  };
}

// ── XBRL 현금 데이터 수집 ──

interface CashDataPoint {
  period: string;       // "2025-12-31"
  cash: number;         // Cash + Restricted Cash ($)
  cash_equivalents: number; // Cash equivalents ($)
  total_assets: number; // Total assets ($)
  cash_ratio_pct: number;  // cash / total_assets * 100
}

async function fetchCashData(): Promise<CashDataPoint[]> {
  console.log("\n📡 XBRL 현금 데이터 조회...");

  const url = `https://data.sec.gov/api/xbrl/companyfacts/CIK${CIK}.json`;
  const data = await fetchJSON(url) as { facts: Record<string, Record<string, { units: { USD: { end: string; val: number; form: string }[] } }>> };
  const usGaap = data.facts?.["us-gaap"] || {};

  function getQuarterly(tag: string): { end: string; val: number }[] {
    const units = usGaap[tag]?.units?.USD || [];
    return units
      .filter((u) => u.end >= "2023-01-01" && (u.form === "10-Q" || u.form === "10-K"))
      .sort((a, b) => b.end.localeCompare(a.end))
      .filter((u, i, arr) => i === 0 || u.end !== arr[i - 1].end)
      .slice(0, 8);
  }

  const cashData = getQuarterly("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents");
  const cashEqData = getQuarterly("CashEquivalentsAtCarryingValue");
  const assetsData = getQuarterly("Assets");

  const cashEqMap = new Map(cashEqData.map((d) => [d.end, d.val]));
  const assetsMap = new Map(assetsData.map((d) => [d.end, d.val]));

  const result: CashDataPoint[] = [];
  for (const c of cashData) {
    const assets = assetsMap.get(c.end) || 0;
    result.push({
      period: c.end,
      cash: c.val,
      cash_equivalents: cashEqMap.get(c.end) || 0,
      total_assets: assets,
      cash_ratio_pct: assets > 0 ? parseFloat(((c.val / assets) * 100).toFixed(1)) : 0,
    });
  }

  console.log(`   ✅ ${result.length}개 분기 현금 데이터 수집`);
  result.slice(0, 4).forEach((d) =>
    console.log(`   ${d.period}: Cash $${(d.cash / 1e9).toFixed(1)}B / Assets $${(d.total_assets / 1e9).toFixed(0)}B (${d.cash_ratio_pct}%)`),
  );

  return result;
}

// ── 여러 분기 13F 수집 ──

interface FilingInfo {
  accessionNumber: string;
  filingDate: string;
  reportDate: string;
}

async function findRecent13Fs(count: number): Promise<FilingInfo[]> {
  console.log("📡 SEC EDGAR Submissions API 조회...");
  const data = await fetchJSON(SUBMISSIONS_URL) as {
    filings: {
      recent: {
        accessionNumber: string[];
        filingDate: string[];
        reportDate: string[];
        form: string[];
      };
    };
  };

  const recent = data.filings.recent;
  const filings: FilingInfo[] = [];
  for (let i = 0; i < recent.form.length && filings.length < count; i++) {
    if (recent.form[i] === "13F-HR") {
      filings.push({
        accessionNumber: recent.accessionNumber[i],
        filingDate: recent.filingDate[i],
        reportDate: recent.reportDate[i],
      });
    }
  }
  return filings;
}

async function fetchAndParseHoldings(filing: FilingInfo): Promise<Holding[]> {
  const xml = await fetchInfoTableXml(filing.accessionNumber);
  const rawHoldings = parseHoldingsXml(xml);
  return aggregateByCusip(rawHoldings);
}

// ── 메인 ──

async function main() {
  const isInitialBuild = !fs.existsSync(OUTPUT_PATH);
  const filings = await findRecent13Fs(isInitialBuild ? 6 : 1);

  if (filings.length === 0) {
    console.log("❌ 13F-HR 공시를 찾을 수 없습니다");
    return;
  }

  const latestFiling = filings[0];
  console.log(`\n📋 최신 13F-HR`);
  console.log(`   Accession: ${latestFiling.accessionNumber}`);
  console.log(`   Filing Date: ${latestFiling.filingDate}`);
  console.log(`   Report Period: ${latestFiling.reportDate}`);

  // 이전 데이터 로드
  let prevData: Berkshire13FData | null = null;
  if (fs.existsSync(OUTPUT_PATH)) {
    prevData = JSON.parse(fs.readFileSync(OUTPUT_PATH, "utf-8")) as Berkshire13FData;

    // 동일 Filing이면 종료 (초기 빌드가 아닐 때만)
    // is_new 플래그는 new_label_until(오늘+14일 KST) 만료 시점에만 해제
    if (!isInitialBuild && prevData.latest.accession_number === latestFiling.accessionNumber) {
      const todayKst = new Date(Date.now() + 9 * 3600_000).toISOString().split("T")[0];
      if (prevData.is_new && prevData.new_label_until && prevData.new_label_until < todayKst) {
        prevData.is_new = false;
        fs.writeFileSync(OUTPUT_PATH, JSON.stringify(prevData, null, 2) + "\n", "utf-8");
        console.log(`\n✅ 이미 최신 Filing 반영됨 — NEW 라벨 만료 (${prevData.new_label_until} 지남)`);
      } else if (prevData.is_new && prevData.new_label_until) {
        console.log(`\n✅ 이미 최신 Filing 반영됨 — NEW 라벨 ${prevData.new_label_until}까지 유지`);
      } else {
        console.log("\n✅ 이미 최신 Filing 반영됨 — 업데이트 불필요");
      }
      return;
    }
  }

  // ── 최신 13F 파싱 ──
  await sleep(REQUEST_DELAY_MS);
  console.log(`\n${"─".repeat(50)}`);
  console.log(`📊 최신 분기 파싱: ${latestFiling.reportDate}`);
  const holdings = await fetchAndParseHoldings(latestFiling);
  if (holdings.length === 0) {
    throw new Error("Holdings가 0건입니다. SEC XML이 비정상일 수 있습니다.");
  }
  const totalValue = holdings.reduce((s, h) => s + h.value, 0);
  console.log(`   ${holdings.length}개 포지션, 총 $${(totalValue / 1e9).toFixed(1)}B`);

  // ── 이전 분기들 수집 (히스토리 구축) ──
  const history: HistoricalFiling[] = [];

  let initialChanges: Berkshire13FData["latest"]["changes"] | null = null;

  if (isInitialBuild && filings.length > 1) {
    console.log(`\n${"─".repeat(50)}`);
    console.log(`📜 이전 ${filings.length - 1}개 분기 히스토리 수집...`);

    let prevQuarterHoldings: Holding[] | null = null;

    for (let i = 1; i < filings.length; i++) {
      const f = filings[i];
      await sleep(REQUEST_DELAY_MS * 2);
      console.log(`\n   [${i}/${filings.length - 1}] ${f.reportDate} (filed ${f.filingDate})`);

      try {
        const h = await fetchAndParseHoldings(f);
        const tv = h.reduce((s, x) => s + x.value, 0);
        console.log(`   → ${h.length}개 포지션, $${(tv / 1e9).toFixed(1)}B`);

        history.push({
          accession_number: f.accessionNumber,
          filing_date: f.filingDate,
          report_period: f.reportDate,
          total_value: tv,
          total_positions: h.length,
          top5: h.slice(0, 5).map((x) => ({
            name: x.name,
            ticker: x.ticker,
            weight_pct: x.weight_pct,
          })),
        });

        // 직전 분기 보존 (변화 비교용)
        if (i === 1) prevQuarterHoldings = h;
      } catch (e) {
        console.log(`   ⚠️ 파싱 실패: ${e instanceof Error ? e.message : e}`);
      }
    }

    // 직전 분기와 비교
    if (prevQuarterHoldings) {
      initialChanges = computeChanges(holdings, prevQuarterHoldings);
      console.log(`\n📈 최신 vs 직전 분기 변화:`);
      console.log(`   신규 매수: ${initialChanges.new_buys.length}개`);
      console.log(`   비중 확대: ${initialChanges.increased.length}개`);
      console.log(`   비중 축소: ${initialChanges.decreased.length}개`);
      console.log(`   전량 매도: ${initialChanges.exits.length}개`);
    }
  }

  // 변화 계산 (기존 데이터 있으면 이전 latest와 비교)
  const previousHoldings = prevData?.latest.holdings || [];
  const changes = initialChanges
    ?? computeChanges(holdings, previousHoldings);

  if (!initialChanges && previousHoldings.length > 0) {
    console.log(`\n📈 포트폴리오 변화:`);
    console.log(`   신규 매수: ${changes.new_buys.length}개`);
    console.log(`   비중 확대: ${changes.increased.length}개`);
    console.log(`   비중 축소: ${changes.decreased.length}개`);
    console.log(`   전량 매도: ${changes.exits.length}개`);
  }

  // 섹터/집중도
  const sectors = computeSectors(holdings);
  const concentration = computeConcentration(holdings);
  console.log(`\n🏛️ 집중도: Top5 ${concentration.top5_pct}%, Top10 ${concentration.top10_pct}%`);

  // 히스토리 관리 (기존 데이터가 있는 경우)
  if (prevData && history.length === 0) {
    history.push({
      accession_number: prevData.latest.accession_number,
      filing_date: prevData.latest.filing_date,
      report_period: prevData.latest.report_period,
      total_value: prevData.latest.total_value,
      total_positions: prevData.latest.total_positions,
      top5: prevData.latest.holdings.slice(0, 5).map((h) => ({
        name: h.name,
        ticker: h.ticker,
        weight_pct: h.weight_pct,
      })),
    });
    history.push(...prevData.history.slice(0, MAX_HISTORY - 1));
  }

  // ── XBRL 현금 데이터 ──
  await sleep(REQUEST_DELAY_MS);
  const cashData = await fetchCashData();

  // 결과 저장 (새 Filing 감지 → is_new: true, new_label_until = 오늘 + 14일 KST)
  const generatedAt = new Date(Date.now() + 9 * 3600_000).toISOString().split("T")[0];
  const newLabelUntil = new Date(Date.now() + (9 + 14 * 24) * 3600_000)
    .toISOString()
    .split("T")[0];
  const result: Berkshire13FData = {
    generated_at: generatedAt,
    is_new: true,
    new_label_until: newLabelUntil,
    latest: {
      accession_number: latestFiling.accessionNumber,
      filing_date: latestFiling.filingDate,
      report_period: latestFiling.reportDate,
      total_value: totalValue,
      total_positions: holdings.length,
      holdings,
      changes,
      sectors,
      concentration,
    },
    history: history.slice(0, MAX_HISTORY),
    cash_trend: cashData,
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(result, null, 2) + "\n", "utf-8");
  console.log(`\n💾 저장 완료: ${OUTPUT_PATH}`);
}

main().catch((err) => {
  console.error("스크립트 실행 실패:", err);
  process.exitCode = 1;
});
