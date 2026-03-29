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
}

// ── CUSIP → 티커/섹터 매핑 ──

const CUSIP_MAP: Record<string, { ticker: string; sector: string }> = {
  // Top holdings
  "037833100": { ticker: "AAPL", sector: "Technology" },
  "025816109": { ticker: "AXP", sector: "Financials" },
  "060505104": { ticker: "BAC", sector: "Financials" },
  "191216100": { ticker: "KO", sector: "Consumer Staples" },
  "166764100": { ticker: "CVX", sector: "Energy" },
  "674599105": { ticker: "OXY", sector: "Energy" },
  "615369105": { ticker: "MCO", sector: "Financials" },
  "H1467J104": { ticker: "CB", sector: "Financials" },
  "500754106": { ticker: "KHC", sector: "Consumer Staples" },
  "23918K108": { ticker: "DVA", sector: "Healthcare" },
  "501044101": { ticker: "KR", sector: "Consumer Staples" },
  "829933100": { ticker: "SIRI", sector: "Communication" },
  "57636Q104": { ticker: "MA", sector: "Financials" },
  "92826C839": { ticker: "V", sector: "Financials" },
  "21036P108": { ticker: "STZ", sector: "Consumer Staples" },
  "14040H105": { ticker: "COF", sector: "Financials" },
  "91324P102": { ticker: "UNH", sector: "Healthcare" },
  "25754A201": { ticker: "DPZ", sector: "Consumer Discretionary" },
  "02005N100": { ticker: "ALLY", sector: "Financials" },
  "G0403H108": { ticker: "AON", sector: "Financials" },
  "670346105": { ticker: "NUE", sector: "Materials" },
  "530909308": { ticker: "LLYVK", sector: "Communication" },
  "526057104": { ticker: "LEN", sector: "Consumer Discretionary" },
  "73278L105": { ticker: "POOL", sector: "Consumer Discretionary" },
  "546347105": { ticker: "LPX", sector: "Materials" },
  "530909100": { ticker: "LLYVA", sector: "Communication" },
  "650111107": { ticker: "NYT", sector: "Communication" },
  "422806208": { ticker: "HEI", sector: "Industrials" },
  "404119982": { ticker: "HEI.A", sector: "Industrials" },
  "404119974": { ticker: "HEI", sector: "Industrials" },
  "531229755": { ticker: "FWONA", sector: "Communication" },
  "16119P108": { ticker: "CHTR", sector: "Communication" },
  "512816109": { ticker: "LAMR", sector: "Real Estate" },
  "G0176J109": { ticker: "ALLE", sector: "Industrials" },
  "62944T105": { ticker: "NVR", sector: "Consumer Discretionary" },
  "47233W109": { ticker: "JEF", sector: "Financials" },
  "25243Q205": { ticker: "DEO", sector: "Consumer Staples" },
  "G9001E102": { ticker: "LILAK", sector: "Communication" },
  "526057302": { ticker: "LEN.B", sector: "Consumer Discretionary" },
  "G9001E128": { ticker: "LILA", sector: "Communication" },
  "047726302": { ticker: "BATRA", sector: "Communication" },
  // Additional known
  "172967424": { ticker: "C", sector: "Financials" },
  "172967G88": { ticker: "C", sector: "Financials" },
  "437076102": { ticker: "HCA", sector: "Healthcare" },
  "023135106": { ticker: "AMZN", sector: "Consumer Discretionary" },
  "02079K305": { ticker: "GOOGL", sector: "Communication" },
  "02079K107": { ticker: "GOOG", sector: "Communication" },
  "68389X105": { ticker: "ORCL", sector: "Technology" },
  "742718109": { ticker: "PG", sector: "Consumer Staples" },
  "742718301": { ticker: "PG", sector: "Consumer Staples" },
  "882508104": { ticker: "TXN", sector: "Technology" },
  "45866F104": { ticker: "ICE", sector: "Financials" },
  "30231G102": { ticker: "XOM", sector: "Energy" },
  "74460D109": { ticker: "PSX", sector: "Energy" },
  "635017106": { ticker: "NU", sector: "Financials" },
  "808513105": { ticker: "SCHW", sector: "Financials" },
  "718546104": { ticker: "PFE", sector: "Healthcare" },
  "126650100": { ticker: "CVS", sector: "Healthcare" },
  "228227100": { ticker: "CRM", sector: "Technology" },
  "00724F101": { ticker: "ADBE", sector: "Technology" },
  "594918104": { ticker: "MSFT", sector: "Technology" },
  "92343V104": { ticker: "VRSN", sector: "Technology" },
  "31620M106": { ticker: "FIS", sector: "Technology" },
  "87612E106": { ticker: "TMUS", sector: "Communication" },
  "254687106": { ticker: "DIS", sector: "Communication" },
  "544248108": { ticker: "LOW", sector: "Consumer Discretionary" },
  "580589109": { ticker: "MCD", sector: "Consumer Discretionary" },
  "756109104": { ticker: "RCL", sector: "Consumer Discretionary" },
  "655044105": { ticker: "NKE", sector: "Consumer Discretionary" },
  "907818108": { ticker: "UPS", sector: "Industrials" },
  "369604301": { ticker: "GE", sector: "Industrials" },
  "822582102": { ticker: "SHEL", sector: "Energy" },
  "29379V103": { ticker: "ENB", sector: "Energy" },
  "92343E102": { ticker: "VRSN", sector: "Technology" },
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
    decreased: decreased.sort((a, b) => a.change_pct - b.change_pct),
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

// ── 메인 ──

async function main() {
  const filing = await findLatest13F();
  if (!filing) {
    console.log("❌ 13F-HR 공시를 찾을 수 없습니다");
    return;
  }

  console.log(`\n📋 최신 13F-HR`);
  console.log(`   Accession: ${filing.accessionNumber}`);
  console.log(`   Filing Date: ${filing.filingDate}`);
  console.log(`   Report Period: ${filing.reportDate}`);

  // 이전 데이터 로드
  let prevData: Berkshire13FData | null = null;
  if (fs.existsSync(OUTPUT_PATH)) {
    prevData = JSON.parse(fs.readFileSync(OUTPUT_PATH, "utf-8")) as Berkshire13FData;

    // 동일 Filing이면 조기 종료
    if (prevData.latest.accession_number === filing.accessionNumber) {
      console.log("\n✅ 이미 최신 Filing 반영됨 — 업데이트 불필요");
      return;
    }
  }

  await sleep(REQUEST_DELAY_MS);

  // Holdings XML 파싱
  const xml = await fetchInfoTableXml(filing.accessionNumber);
  const rawHoldings = parseHoldingsXml(xml);
  console.log(`\n📊 파싱 완료: ${rawHoldings.length}개 항목 (합산 전)`);

  const holdings = aggregateByCusip(rawHoldings);
  const totalValue = holdings.reduce((s, h) => s + h.value, 0);
  console.log(`   합산 후: ${holdings.length}개 포지션, 총 $${(totalValue / 1e9).toFixed(1)}B`);

  // 변화 계산
  const previousHoldings = prevData?.latest.holdings || [];
  const changes = computeChanges(holdings, previousHoldings);

  console.log(`\n📈 포트폴리오 변화:`);
  console.log(`   신규 매수: ${changes.new_buys.length}개`);
  console.log(`   비중 확대: ${changes.increased.length}개`);
  console.log(`   비중 축소: ${changes.decreased.length}개`);
  console.log(`   전량 매도: ${changes.exits.length}개`);

  // 섹터/집중도
  const sectors = computeSectors(holdings);
  const concentration = computeConcentration(holdings);

  console.log(`\n🏛️ 집중도: Top5 ${concentration.top5_pct}%, Top10 ${concentration.top10_pct}%`);

  // 히스토리 관리
  const history: HistoricalFiling[] = [];
  if (prevData) {
    // 이전 latest를 히스토리로 이동
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
    // 기존 히스토리 추가 (최대 MAX_HISTORY개)
    history.push(...prevData.history.slice(0, MAX_HISTORY - 1));
  }

  // 결과 저장
  const result: Berkshire13FData = {
    generated_at: new Date().toISOString().split("T")[0],
    latest: {
      accession_number: filing.accessionNumber,
      filing_date: filing.filingDate,
      report_period: filing.reportDate,
      total_value: totalValue,
      total_positions: holdings.length,
      holdings,
      changes,
      sectors,
      concentration,
    },
    history,
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(result, null, 2) + "\n", "utf-8");
  console.log(`\n💾 저장 완료: ${OUTPUT_PATH}`);
}

main().catch((err) => {
  console.error("스크립트 실행 실패:", err);
  process.exitCode = 1;
});
