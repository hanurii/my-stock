/**
 * 거시경제 리포트 데이터 수집 스크립트
 *
 * GitHub Actions에서 매일 06:30 KST에 실행.
 * Yahoo Finance 시계열 + 매일경제/한국경제 RSS 뉴스를 수집하여
 * draft 리포트 JSON을 생성한다.
 * 분석 섹션(briefing, scenario 등)은 직전 리포트 값을 유지하며,
 * 스케줄 트리거(Claude)가 새로 채워넣는다.
 *
 * 사용법: npx tsx scripts/collect-report-data.ts
 */
import fs from "fs";
import path from "path";

// ── 설정 ──

const YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";

// 매일경제 RSS (경제, 증권)
const MK_RSS_URLS = [
  "https://www.mk.co.kr/rss/30100041",
  "https://www.mk.co.kr/rss/50200011",
];
// 한국경제 RSS (경제, 증권)
const HK_RSS_URLS = [
  "https://www.hankyung.com/feed/economy",
  "https://www.hankyung.com/feed/finance",
];

const SYMBOLS = [
  { yahoo: "^KS11", name: "코스피", section: "korea" },
  { yahoo: "^KQ11", name: "코스닥", section: "korea" },
  { yahoo: "^IXIC", name: "나스닥", section: "us" },
  { yahoo: "^DJI", name: "다우존스", section: "us" },
  { yahoo: "^GSPC", name: "S&P500", section: "us" },
  { yahoo: "KRW=X", name: "원/달러", section: "fx" },
  { yahoo: "DX-Y.NYB", name: "달러인덱스", section: "fx" },
  { yahoo: "JPY=X", name: "엔/달러", section: "fx" },
  { yahoo: "^TNX", name: "미국채10년", section: "bonds" },
  { yahoo: "^IRX", name: "미국채2년", section: "bonds" },
  { yahoo: "CL=F", name: "WTI유가", section: "commodities" },
  { yahoo: "BZ=F", name: "브렌트유", section: "commodities" },
  { yahoo: "^VIX", name: "VIX", section: "commodities" },
  { yahoo: "GC=F", name: "금", section: "commodities" },
  { yahoo: "BTC-USD", name: "비트코인", section: "commodities" },
];

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

// ── 유틸 ──

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function getKSTDate(): { date: string; weekday: string; generated_at: string } {
  const now = new Date();
  const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  const date = kst.toISOString().split("T")[0];
  const weekday = WEEKDAYS[kst.getUTCDay()];
  const hh = String(kst.getUTCHours()).padStart(2, "0");
  const mm = String(kst.getUTCMinutes()).padStart(2, "0");
  return { date, weekday, generated_at: `${date} ${hh}:${mm}:00` };
}

function roundValue(name: string, value: number): number {
  if (/채|IRX|TNX/.test(name)) return parseFloat(value.toFixed(3));
  if (/달러인덱스|VIX/.test(name)) return parseFloat(value.toFixed(2));
  if (/원/.test(name)) return parseFloat(value.toFixed(1));
  return parseFloat(value.toFixed(2));
}

// ── Yahoo Finance ──

interface TimeseriesPoint {
  날짜: string;
  종가: number;
}

async function fetchYahoo(
  symbol: string,
  name: string,
): Promise<{ timeseries: TimeseriesPoint[]; latest: number; prevClose: number | null } | null> {
  try {
    const url = `${YAHOO_API}/${encodeURIComponent(symbol)}?range=1mo&interval=1d`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;
    const json = await res.json();
    const result = json.chart?.result?.[0];
    if (!result) return null;

    const meta = result.meta as {
      regularMarketPrice?: number;
      regularMarketTime?: number;
    } | undefined;
    const timestamps: number[] = result.timestamp || [];
    const closes: (number | null)[] = result.indicators?.quote?.[0]?.close || [];

    const valid: TimeseriesPoint[] = [];
    for (let i = 0; i < timestamps.length; i++) {
      const closeVal = closes[i];
      if (closeVal != null) {
        const d = new Date(timestamps[i] * 1000);
        const dateStr = `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
        valid.push({ 날짜: dateStr, 종가: roundValue(name, closeVal) });
      } else if (i === timestamps.length - 1 && meta?.regularMarketPrice) {
        // Yahoo Finance가 마지막 거래일의 close를 null로 반환하는 경우가 있음.
        // meta.regularMarketPrice는 항상 최신 체결가를 담고 있으므로 이를 사용.
        const d = new Date(timestamps[i] * 1000);
        const dateStr = `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
        valid.push({ 날짜: dateStr, 종가: roundValue(name, meta.regularMarketPrice) });
      }
    }

    // timestamps 배열에 아예 없는 경우: meta.regularMarketTime이 더 최신이면 추가
    if (meta?.regularMarketPrice && meta?.regularMarketTime) {
      const lastTs = timestamps[timestamps.length - 1] ?? 0;
      if (meta.regularMarketTime > lastTs) {
        const d = new Date(meta.regularMarketTime * 1000);
        const dateStr = `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
        const lastEntry = valid[valid.length - 1];
        if (!lastEntry || lastEntry.날짜 !== dateStr) {
          valid.push({ 날짜: dateStr, 종가: roundValue(name, meta.regularMarketPrice) });
        }
      }
    }

    const last10 = valid.slice(-10);
    const latest = last10[last10.length - 1]?.종가 ?? 0;
    const prevClose = last10.length >= 2 ? last10[last10.length - 2]?.종가 : null;

    return { timeseries: last10, latest, prevClose };
  } catch {
    return null;
  }
}

// ── 뉴스 RSS (매일경제 + 한국경제) ──

interface NewsItem {
  제목: string;
  링크: string;
  출처: string;
  날짜: string;
}

interface RawNewsItem {
  title: string;
  link: string;
  source: string;
  date: Date;
  dateStr: string;
}

// 경제 핵심 키워드 (포함 필터)
const NEWS_KEYWORDS =
  /증시|코스피|코스닥|환율|원달러|유가|WTI|금리|FOMC|금값|채권|인플레|GDP|CPI|경기|수출|무역|이란|전쟁|트럼프|연준|파월|주가|반등|급락|하락|상승|외국인|기관|관세|반도체|AI|석유|OPEC/;

// 불필요 기사 제외 패턴
const NEWS_EXCLUDE =
  /\[표\]|고시표|일일시세|마감시세|장마감|종목별|외국환|기준금리표|공시지가|부동산.*공시|인사|부고|칼럼|사설/;

async function fetchRssNews(
  urls: string[],
  sourceName: string,
  cutoffDate: Date,
  maxCount: number,
): Promise<RawNewsItem[]> {
  const allItems: RawNewsItem[] = [];

  for (const url of urls) {
    try {
      const res = await fetch(url, { headers: { "User-Agent": UA } });
      if (!res.ok) continue;
      const xml = await res.text();

      const items = xml.match(/<item>[\s\S]*?<\/item>/g) || [];
      for (const item of items) {
        const title =
          item.match(/<title>[\s\S]*?CDATA\[(.*?)\]\]/)?.[1] ||
          item.match(/<title>(.*?)<\/title>/)?.[1] ||
          "";
        const link =
          item.match(/<link>[\s\S]*?CDATA\[(.*?)\]\]/)?.[1] ||
          item.match(/<link>(.*?)<\/link>/)?.[1] ||
          "";
        const pubDateStr = item.match(/<pubDate>(.*?)<\/pubDate>/)?.[1] || "";
        const category =
          item.match(/<category>[\s\S]*?CDATA\[(.*?)\]\]/)?.[1] || "";

        // 카테고리 필터
        if (/연예|스포츠|라이프|문화|오피니언|부동산/.test(category)) continue;

        const pubDate = new Date(pubDateStr);
        if (isNaN(pubDate.getTime())) continue;
        if (pubDate < cutoffDate) continue;

        // 불필요 기사 제외
        if (NEWS_EXCLUDE.test(title)) continue;

        const dateStr = pubDate.toISOString().split("T")[0];
        allItems.push({ title, link, source: sourceName, date: pubDate, dateStr });
      }
      await sleep(500);
    } catch {
      continue;
    }
  }

  // 키워드 필터 → 최신순 정렬 → 중복 제거
  const filtered = allItems
    .filter((item) => NEWS_KEYWORDS.test(item.title))
    .sort((a, b) => b.date.getTime() - a.date.getTime());

  const unique: RawNewsItem[] = [];
  for (const item of filtered) {
    const isDup = unique.some(
      (u) => item.title.substring(0, 15) === u.title.substring(0, 15),
    );
    if (!isDup) unique.push(item);
  }

  return unique.slice(0, maxCount);
}

async function fetchNews(): Promise<NewsItem[]> {
  // 전날 오전 7시 KST 이후만 수집
  const now = new Date();
  const kstNow = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  const yesterday7am = new Date(kstNow);
  yesterday7am.setUTCDate(yesterday7am.getUTCDate() - 1);
  yesterday7am.setUTCHours(7 - 9, 0, 0, 0); // KST 7am = UTC -2 (previous day)

  // 매일경제 6개, 한국경제 6개 병렬 수집
  const [mkItems, hkItems] = await Promise.all([
    fetchRssNews(MK_RSS_URLS, "매일경제", yesterday7am, 6),
    fetchRssNews(HK_RSS_URLS, "한국경제", yesterday7am, 6),
  ]);

  return [...mkItems, ...hkItems].map((item) => ({
    제목: item.title,
    링크: item.link,
    출처: item.source,
    날짜: item.dateStr,
  }));
}

// ── 두바이유 (네이버 금융 스크래핑) ──

interface DubaiCrudeData {
  timeseries: TimeseriesPoint[];
  latest: number;
  prevClose: number | null;
}

async function fetchDubaiCrude(): Promise<DubaiCrudeData | null> {
  try {
    const url =
      "https://finance.naver.com/marketindex/worldDailyQuote.naver?marketindexCd=OIL_DU&fdtc=2&page=1";
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;
    const html = await res.text();

    const rows = html.match(/<tr[\s\S]*?<\/tr>/g) || [];
    const points: { date: Date; dateStr: string; value: number }[] = [];

    for (const row of rows) {
      const tds = (row.match(/<td[^>]*>([\s\S]*?)<\/td>/g) || []).map((td) =>
        td.replace(/<[^>]+>/g, "").trim(),
      );
      if (tds.length < 2) continue;
      const dateMatch = tds[0].match(/(\d{4})\.(\d{2})\.(\d{2})/);
      const value = parseFloat(tds[1].replace(/,/g, ""));
      if (!dateMatch || isNaN(value)) continue;

      const d = new Date(`${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`);
      const dateStr = `${dateMatch[2]}/${dateMatch[3]}`;
      points.push({ date: d, dateStr, value });
    }

    if (points.length === 0) return null;

    // 오래된 순 정렬 → 최근 10개
    points.sort((a, b) => a.date.getTime() - b.date.getTime());
    const last10 = points.slice(-10);
    const timeseries = last10.map((p) => ({
      날짜: p.dateStr,
      종가: parseFloat(p.value.toFixed(2)),
    }));
    const latest = timeseries[timeseries.length - 1]?.종가 ?? 0;
    const prevClose =
      timeseries.length >= 2 ? timeseries[timeseries.length - 2]?.종가 : null;

    return { timeseries, latest, prevClose };
  } catch {
    return null;
  }
}

// 리포트 발행일(YYYY-MM-DD) 기준으로 직전 거래일(MM/DD)을 반환한다.
// 토/일은 거래일이 아니므로 역순으로 평일을 찾는다.
function getExpectedLastTradingDay(reportDate: string): string {
  const d = new Date(reportDate + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() - 1);
  while (d.getUTCDay() === 0 || d.getUTCDay() === 6) {
    d.setUTCDate(d.getUTCDate() - 1);
  }
  return `${String(d.getUTCMonth() + 1).padStart(2, "0")}/${String(d.getUTCDate()).padStart(2, "0")}`;
}

// ── 메인 ──

async function main() {
  const dataDir = path.join(process.cwd(), "public", "data");
  const kst = getKSTDate();

  console.log(`📊 거시경제 리포트 데이터 수집 (${kst.date} ${kst.weekday})`);
  console.log("─".repeat(65));

  // 직전 리포트 찾기
  const files = fs.readdirSync(dataDir)
    .filter((f) => /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
    .sort()
    .reverse();
  const prevFile = files[0];
  if (!prevFile) {
    console.error("❌ 직전 리포트 파일을 찾을 수 없습니다.");
    process.exitCode = 1;
    return;
  }

  const prev = JSON.parse(fs.readFileSync(path.join(dataDir, prevFile), "utf-8"));
  console.log(`📁 직전 리포트: ${prevFile}\n`);

  // ── 1. Yahoo Finance 데이터 수집 ──
  console.log("1️⃣ Yahoo Finance 시계열 수집");

  // 직전 리포트의 indicators를 깊은 복사
  const indicators = JSON.parse(JSON.stringify(prev.indicators));
  let successCount = 0;
  let failCount = 0;

  for (const sym of SYMBOLS) {
    const data = await fetchYahoo(sym.yahoo, sym.name);
    if (!data) {
      console.log(`  ❌ ${sym.name} (${sym.yahoo}): 조회 실패 — 직전 값 유지`);
      failCount++;
      await sleep(500);
      continue;
    }

    // 이름 기반 매핑: 섹션 배열에서 name이 일치하는 지표를 찾는다
    const sectionArr = indicators[sym.section] as Record<string, unknown>[] | undefined;
    const indicator = sectionArr?.find((ind) => ind.name === sym.name);
    if (!indicator) {
      console.log(`  ⚠️ ${sym.name}: 섹션 "${sym.section}"에서 이름 매칭 실패`);
      failCount++;
      await sleep(500);
      continue;
    }

    const oldValue = indicator.value;
    indicator.timeseries = data.timeseries;
    indicator.value = data.latest;

    // change 계산 (전일 대비)
    // 채권 금리(bonds)는 bp(basis point) 단위, 그 외는 퍼센트 변동률
    const isBond = sym.section === "bonds";
    if (data.prevClose && data.prevClose !== 0) {
      indicator.change = isBond
        ? parseFloat((data.latest - data.prevClose).toFixed(3))           // %p
        : parseFloat(
            (((data.latest - data.prevClose) / data.prevClose) * 100).toFixed(2),
          );
    }

    // weekly_change 계산 (5영업일 전 대비)
    if (data.timeseries.length >= 6) {
      const weekAgo = data.timeseries[data.timeseries.length - 6].종가;
      if (weekAgo !== 0) {
        indicator.weekly_change = isBond
          ? parseFloat((data.latest - weekAgo).toFixed(3))                // %p
          : parseFloat(
              (((data.latest - weekAgo) / weekAgo) * 100).toFixed(2),
            );
      }
    }

    // 채권은 단위 표기 추가
    if (isBond) {
      indicator.change_unit = "%p";
    }

    console.log(
      `  ✅ ${sym.name}: ${oldValue} → ${data.latest} (${data.timeseries.length}일)`,
    );
    successCount++;
    await sleep(500);
  }

  console.log(`\n   ${successCount}개 성공, ${failCount}개 실패\n`);

  // ── 1-1. 코스피/코스닥 신선도 검증 ──
  // 리포트 발행일 기준 직전 거래일 데이터인지 확인.
  // 전전날 데이터가 재활용되는 경우 즉시 실패 처리.
  console.log("1️⃣-1 코스피/코스닥 신선도 검증");
  const expectedTradingDay = getExpectedLastTradingDay(kst.date);
  let staleKorea = false;
  for (const koreaInd of (indicators.korea as Record<string, unknown>[]) ?? []) {
    const ts = koreaInd.timeseries as TimeseriesPoint[] | undefined;
    const latestDate = ts?.[ts.length - 1]?.날짜;
    if (latestDate !== expectedTradingDay) {
      console.error(
        `  ❌ ${koreaInd.name}: 최신 데이터(${latestDate ?? "없음"})가 직전 거래일(${expectedTradingDay})과 불일치 — 전전날 재활용 방지를 위해 실패 처리`,
      );
      staleKorea = true;
    } else {
      console.log(`  ✅ ${koreaInd.name}: ${latestDate} (직전 거래일 일치)`);
    }
  }
  if (staleKorea) {
    process.exitCode = 1;
    return;
  }
  console.log();

  // ── 1-2. 두바이유 (네이버 금융) ──
  console.log("1️⃣-2 두바이유 (네이버 금융)");
  const dubaiData = await fetchDubaiCrude();
  const dubaiIndicator = (indicators.commodities as Record<string, unknown>[])?.find(
    (ind) => ind.name === "두바이유",
  );
  if (dubaiData && dubaiIndicator) {
    const oldValue = dubaiIndicator.value;
    dubaiIndicator.timeseries = dubaiData.timeseries;
    dubaiIndicator.value = dubaiData.latest;
    if (dubaiData.prevClose && dubaiData.prevClose !== 0) {
      dubaiIndicator.change = parseFloat(
        (((dubaiData.latest - dubaiData.prevClose) / dubaiData.prevClose) * 100).toFixed(2),
      );
    }
    if (dubaiData.timeseries.length >= 6) {
      const weekAgo = dubaiData.timeseries[dubaiData.timeseries.length - 6].종가;
      if (weekAgo !== 0) {
        dubaiIndicator.weekly_change = parseFloat(
          (((dubaiData.latest - weekAgo) / weekAgo) * 100).toFixed(2),
        );
      }
    }
    console.log(`  ✅ 두바이유: ${oldValue} → ${dubaiData.latest}`);
  } else {
    console.log(`  ❌ 두바이유: ${dubaiData ? "지표 매칭 실패" : "조회 실패"} — 직전 값 유지`);
  }
  console.log();

  // ── 2. 매일경제 + 한국경제 RSS 뉴스 수집 ──
  console.log("2️⃣ 매일경제 + 한국경제 RSS 뉴스 수집");
  const news = await fetchNews();
  const mkCount = news.filter((n) => n.출처 === "매일경제").length;
  const hkCount = news.filter((n) => n.출처 === "한국경제").length;
  console.log(`  매일경제 ${mkCount}개 + 한국경제 ${hkCount}개 = 총 ${news.length}개`);
  news.forEach((n) => console.log(`  · [${n.출처}] ${n.날짜} | ${n.제목.substring(0, 50)}`));

  // ── 3. spread 계산 ──
  const bond10 = indicators.bonds?.[0]?.value ?? prev.spread["10년물"];
  const bond2 = indicators.bonds?.[1]?.value ?? prev.spread["3개월물"];
  const spread = {
    "10년물": bond10,
    "3개월물": bond2,
    "금리차": parseFloat((bond10 - bond2).toFixed(3)),
    "상태": bond10 > bond2 ? "정상" : "역전",
  };

  // ── 4. historical current 값 업데이트 (이름 기반) ──
  const historical = JSON.parse(JSON.stringify(prev.historical));
  const allIndicators = [
    ...indicators.korea,
    ...indicators.us,
    ...indicators.fx,
    ...indicators.bonds,
    ...indicators.commodities,
  ];
  const valueMap: Record<string, number> = {};
  for (const ind of allIndicators) {
    if (ind?.name && ind?.value != null) valueMap[ind.name] = ind.value;
  }
  for (const h of historical) {
    if (valueMap[h.name] != null) h.current = valueMap[h.name];
  }

  // ── 5. draft 리포트 생성 ──
  const report = {
    meta: {
      date: kst.date,
      weekday: kst.weekday,
      generated_at: kst.generated_at,
    },

    // === 분석 섹션 (직전 리포트 유지 → 스케줄 트리거가 새로 채움) ===
    briefing: prev.briefing || "",
    scenario: prev.scenario || { 코드: "", 시나리오: "", 해석: "", 대응: "" },

    // === 데이터 섹션 (스크립트가 채운 영역) ===
    indicators,
    spread,
    causal_chain: prev.causal_chain || "",
    investment_direction: prev.investment_direction || "",
    news,
    cpi_gdp: prev.cpi_gdp,
    divergence: prev.divergence || "",
    asset_recommendation: prev.asset_recommendation || "",
    historical,
    longterm_charts: prev.longterm_charts,
  };

  // ── 6. 저장 ──
  const outPath = path.join(dataDir, `${kst.date}.json`);
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2) + "\n", "utf-8");

  console.log("\n" + "─".repeat(65));
  console.log(`💾 draft 저장: ${outPath}`);
  console.log(
    `   데이터: ✅ | 분석: ⏳ (스케줄 트리거 대기)`,
  );
}

main().catch((err) => {
  console.error("스크립트 실행 실패:", err);
  process.exitCode = 1;
});
