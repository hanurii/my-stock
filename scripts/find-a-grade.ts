/**
 * A등급 저평가 우량주 후보 탐색 스크립트
 *
 * 1단계: Naver Finance에서 KOSPI 전 종목 코드 수집
 * 2단계: 각 종목 PER/PBR/배당수익률 조회
 * 3단계: Cat1(저평가) + Cat2(배당) 부분 점수 계산
 * 4단계: 최대 가능 점수 80+(A등급) 후보 필터링
 */

const NAVER_LIST = "https://m.stock.naver.com/api/stocks/marketValue";
const NAVER_DETAIL = "https://m.stock.naver.com/api/stock";
const HEADERS = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" };

interface StockBasic { itemCode: string; stockName: string; }

interface Candidate {
  code: string;
  name: string;
  per: number | null;
  pbr: number;
  dividendYield: number;
  cat1: number;
  divScore: number;
  maxScore: number;
  note: string;
}

// ── 채점 함수 ──

function calcCat1(per: number | null, pbr: number) {
  let perScore = 0;
  if (per == null) perScore = 0;
  else if (per < 5) perScore = 20;
  else if (per < 8) perScore = 15;
  else if (per < 10) perScore = 10;
  else perScore = 5;

  let pbrScore = 0;
  if (pbr < 0.3) pbrScore = 5;
  else if (pbr < 0.6) pbrScore = 4;
  else if (pbr < 1.0) pbrScore = 3;
  else pbrScore = 0;

  // 낙관 가정: profit_sustainable=true(5), single_listed=true(5)
  return perScore + pbrScore + 10;
}

function calcDivScore(dy: number) {
  if (dy > 7) return 10;
  if (dy > 5) return 7;
  if (dy > 3) return 5;
  return 2;
}

// Cat2 나머지 최대: 분기배당(5)+배당10년(5)+자사주5년(7)+소각>2%(8)+자사주없음(5)=30
// Cat3 최대: very_high(10)+excellent(10)+global(5)=25
const CAT2_REST_MAX = 30;
const CAT3_MAX = 25;

// ── 전 종목 코드 수집 ──

async function getAllStockCodes(market: string): Promise<StockBasic[]> {
  const all: StockBasic[] = [];
  let page = 1;
  while (true) {
    const res = await fetch(`${NAVER_LIST}/${market}?page=${page}&pageSize=100`, { headers: HEADERS });
    if (!res.ok) break;
    const json = await res.json();
    const stocks = json.stocks || [];
    if (stocks.length === 0) break;
    for (const s of stocks) {
      if (s.stockEndType === "stock") {
        all.push({ itemCode: s.itemCode, stockName: s.stockName });
      }
    }
    page++;
    if (stocks.length < 100) break;
  }
  return all;
}

// ── 개별 종목 PER/PBR/배당 조회 ──

async function getStockFinancials(code: string): Promise<{ per: number | null; pbr: number | null; dy: number } | null> {
  try {
    const res = await fetch(`${NAVER_DETAIL}/${code}/integration`, { headers: HEADERS });
    if (!res.ok) return null;
    const json = await res.json();
    const str = JSON.stringify(json);

    let per: number | null = null;
    let pbr: number | null = null;
    let dy = 0;

    const perM = str.match(/"code":"per","key":"PER","value":"([\d,.]+)배"/);
    if (perM) per = parseFloat(perM[1].replace(/,/g, ""));

    const pbrM = str.match(/"code":"pbr","key":"PBR","value":"([\d,.]+)배"/);
    if (pbrM) pbr = parseFloat(pbrM[1].replace(/,/g, ""));

    const dyM = str.match(/"code":"dividendYieldRatio","key":"배당수익률","value":"([\d,.]+)%"/);
    if (dyM) dy = parseFloat(dyM[1].replace(/,/g, ""));

    return { per, pbr, dy };
  } catch {
    return null;
  }
}

// ── 배치 조회 (동시 요청 제한) ──

async function batchFetch<T, R>(items: T[], fn: (item: T) => Promise<R>, concurrency: number): Promise<R[]> {
  const results: R[] = [];
  for (let i = 0; i < items.length; i += concurrency) {
    const batch = items.slice(i, i + concurrency);
    const batchResults = await Promise.all(batch.map(fn));
    results.push(...batchResults);
    if (i + concurrency < items.length) {
      process.stdout.write(`\r  ${Math.min(i + concurrency, items.length)}/${items.length} 조회 중...`);
    }
  }
  return results;
}

// ── 메인 ──

async function main() {
  console.log("\n📊 KOSPI 전 종목 코드 수집 중...\n");
  const kospiStocks = await getAllStockCodes("KOSPI");
  console.log(`  KOSPI ${kospiStocks.length}종목 수집 완료\n`);

  console.log("📈 개별 종목 PER/PBR/배당률 조회 중...\n");
  const financials = await batchFetch(
    kospiStocks,
    async (s) => ({ ...s, fin: await getStockFinancials(s.itemCode) }),
    10, // 동시 10개
  );
  console.log(`\n\n  ${financials.filter(f => f.fin).length}종목 데이터 수집 완료\n`);

  // 필터링 및 채점
  const candidates: Candidate[] = [];

  for (const { itemCode, stockName, fin } of financials) {
    if (!fin || fin.pbr == null || fin.pbr <= 0) continue;

    const name = stockName;
    if (name.includes("스팩") || name.includes("SPAC") || name.includes("리츠") || name.includes("REIT")) continue;

    const cat1 = calcCat1(fin.per, fin.pbr);
    const divScore = calcDivScore(fin.dy);
    const maxScore = cat1 + divScore + CAT2_REST_MAX + CAT3_MAX;

    // A등급 가능(80+) + Cat1 최소 20점
    if (maxScore <= 80 || cat1 < 20) continue;

    const notes: string[] = [];
    if (fin.per != null && fin.per < 5) notes.push("PER<5");
    else if (fin.per != null && fin.per < 8) notes.push("PER<8");
    if (fin.pbr < 0.3) notes.push("PBR<0.3");
    else if (fin.pbr < 0.6) notes.push("PBR<0.6");
    if (fin.dy > 5) notes.push(`배당${fin.dy}%`);
    else if (fin.dy > 3) notes.push(`배당${fin.dy}%`);

    candidates.push({
      code: itemCode, name,
      per: fin.per, pbr: fin.pbr, dividendYield: fin.dy,
      cat1, divScore, maxScore,
      note: notes.join(" · "),
    });
  }

  candidates.sort((a, b) => b.cat1 !== a.cat1 ? b.cat1 - a.cat1 : b.dividendYield - a.dividendYield);

  // 출력
  console.log("=".repeat(95));
  console.log("  A등급(80+) 도달 가능 후보 — KOSPI (Cat1≥20 + 최대가능≥80)");
  console.log("=".repeat(95));
  console.log("");
  console.log(
    "#".padEnd(4) +
    "코드".padEnd(8) +
    "종목명".padEnd(18) +
    "PER".padEnd(10) +
    "PBR".padEnd(8) +
    "배당률".padEnd(8) +
    "Cat1".padEnd(8) +
    "최대가능".padEnd(8) +
    "비고"
  );
  console.log("-".repeat(95));

  const top = candidates.slice(0, 50);
  top.forEach((c, i) => {
    console.log(
      String(i + 1).padEnd(4) +
      c.code.padEnd(8) +
      c.name.padEnd(18) +
      (c.per != null ? `${c.per}x` : "적자").padEnd(10) +
      `${c.pbr}x`.padEnd(8) +
      `${c.dividendYield}%`.padEnd(8) +
      `${c.cat1}/35`.padEnd(8) +
      `${c.maxScore}`.padEnd(8) +
      c.note
    );
  });

  console.log(`\n총 ${candidates.length}개 후보 중 상위 ${top.length}개\n`);

  // 하이라이트
  const elite = candidates.filter(c => c.cat1 >= 30);
  if (elite.length > 0) {
    console.log("⭐ Cat1 ≥ 30 (저평가 최상위):");
    elite.forEach(c => console.log(`   ${c.name} (${c.code}) — PER ${c.per ?? "적자"}x, PBR ${c.pbr}x, 배당 ${c.dividendYield}%`));
    console.log("");
  }

  const goldZone = candidates.filter(c => c.per != null && c.per < 8 && c.dividendYield > 5 && c.pbr < 1.0);
  if (goldZone.length > 0) {
    console.log("💰 PER<8 + PBR<1.0 + 배당>5% (골든존):");
    goldZone.forEach(c => console.log(`   ${c.name} (${c.code}) — PER ${c.per}x, PBR ${c.pbr}x, 배당 ${c.dividendYield}%`));
    console.log("");
  }

  console.log("⚠️  Cat1은 단독상장+이익지속을 낙관 가정한 값입니다.");
  console.log("   실제 A등급 여부는 주주환원(Cat2) + 성장성(Cat3) 수동 확인 필요.\n");
}

main().catch(console.error);
