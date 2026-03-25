/**
 * 거시경제 리포트 데이터 수집 스크립트
 *
 * GitHub Actions에서 매일 06:30 KST에 실행.
 * Yahoo Finance 시계열 + 매일경제 RSS 뉴스를 수집하여
 * draft 리포트 JSON을 생성한다.
 * 분석 섹션(briefing, scenario 등)은 비워두고,
 * 스케줄 트리거(Claude)가 채워넣는다.
 *
 * 사용법: npx tsx scripts/collect-report-data.ts
 */
import fs from "fs";
import path from "path";

// ── 설정 ──

const YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart";
const MK_RSS_IDS = ["30100041", "50200011"]; // 경제, 증권
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";

const SYMBOLS = [
  { yahoo: "^KS11", name: "코스피", section: "korea", idx: 0 },
  { yahoo: "^KQ11", name: "코스닥", section: "korea", idx: 1 },
  { yahoo: "^IXIC", name: "나스닥", section: "us", idx: 0 },
  { yahoo: "^DJI", name: "다우존스", section: "us", idx: 1 },
  { yahoo: "^GSPC", name: "S&P500", section: "us", idx: 2 },
  { yahoo: "KRW=X", name: "원/달러", section: "fx", idx: 0 },
  { yahoo: "DX-Y.NYB", name: "달러인덱스", section: "fx", idx: 1 },
  { yahoo: "JPY=X", name: "엔/달러", section: "fx", idx: 2 },
  { yahoo: "^TNX", name: "미국채10년", section: "bonds", idx: 0 },
  { yahoo: "^IRX", name: "미국채2년", section: "bonds", idx: 1 },
  { yahoo: "CL=F", name: "WTI유가", section: "commodities", idx: 0 },
  { yahoo: "^VIX", name: "VIX", section: "commodities", idx: 2 },
  { yahoo: "GC=F", name: "금", section: "commodities", idx: 3 },
  { yahoo: "BTC-USD", name: "비트코인", section: "commodities", idx: 4 },
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

    const timestamps: number[] = result.timestamp || [];
    const closes: (number | null)[] = result.indicators?.quote?.[0]?.close || [];

    const valid: TimeseriesPoint[] = [];
    for (let i = 0; i < timestamps.length; i++) {
      if (closes[i] != null) {
        const d = new Date(timestamps[i] * 1000);
        const dateStr = `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
        valid.push({ 날짜: dateStr, 종가: roundValue(name, closes[i]!) });
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

// ── 매일경제 RSS ──

interface NewsItem {
  제목: string;
  링크: string;
  출처: string;
  날짜: string;
}

async function fetchMKNews(): Promise<NewsItem[]> {
  const allItems: { title: string; link: string; date: Date; dateStr: string }[] = [];

  // 전날 오전 7시 KST 이후만 수집
  const now = new Date();
  const kstNow = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  const yesterday7am = new Date(kstNow);
  yesterday7am.setUTCDate(yesterday7am.getUTCDate() - 1);
  yesterday7am.setUTCHours(7 - 9, 0, 0, 0); // KST 7am = UTC -2 (previous day)

  for (const rssId of MK_RSS_IDS) {
    try {
      const res = await fetch(`https://www.mk.co.kr/rss/${rssId}`, {
        headers: { "User-Agent": UA },
      });
      if (!res.ok) continue;
      const xml = await res.text();

      const items = xml.match(/<item>[\s\S]*?<\/item>/g) || [];
      for (const item of items) {
        const title = item.match(/CDATA\[(.*?)\]\]/)?.[1] || "";
        const link = item.match(/<link>[\s\S]*?CDATA\[(.*?)\]\]/)?.[1] || "";
        const pubDateStr = item.match(/<pubDate>(.*?)<\/pubDate>/)?.[1] || "";
        const category = item.match(/<category>[\s\S]*?CDATA\[(.*?)\]\]/)?.[1] || "";

        // 경제/증시와 무관한 카테고리 제외
        if (/연예|스포츠|라이프|문화|오피니언/.test(category)) continue;

        const pubDate = new Date(pubDateStr);
        if (isNaN(pubDate.getTime())) continue;
        if (pubDate < yesterday7am) continue;

        const dateStr = pubDate.toISOString().split("T")[0];
        allItems.push({ title, link, date: pubDate, dateStr });
      }
      await sleep(500);
    } catch {
      continue;
    }
  }

  // 최신순 정렬 후 경제 핵심 키워드로 필터링
  const keywords = /증시|코스피|코스닥|환율|원달러|유가|WTI|금리|FOMC|금값|채권|인플레|GDP|CPI|경기|수출|무역|이란|전쟁|트럼프|연준|파월|주가|반등|급락|하락|상승|외국인|기관/;

  const filtered = allItems
    .filter((item) => keywords.test(item.title))
    .sort((a, b) => b.date.getTime() - a.date.getTime());

  // 중복 제거 (제목 유사도)
  const unique: typeof filtered = [];
  for (const item of filtered) {
    const isDup = unique.some(
      (u) => item.title.substring(0, 15) === u.title.substring(0, 15),
    );
    if (!isDup) unique.push(item);
  }

  return unique.slice(0, 8).map((item) => ({
    제목: item.title,
    링크: item.link,
    출처: "매일경제",
    날짜: item.dateStr,
  }));
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

    const indicator = indicators[sym.section]?.[sym.idx];
    if (!indicator) {
      console.log(`  ⚠️ ${sym.name}: 섹션 매핑 실패`);
      failCount++;
      continue;
    }

    const oldValue = indicator.value;
    indicator.timeseries = data.timeseries;
    indicator.value = data.latest;

    // change 계산 (전일 대비)
    if (data.prevClose && data.prevClose !== 0) {
      indicator.change = parseFloat(
        (((data.latest - data.prevClose) / data.prevClose) * 100).toFixed(2),
      );
    }

    // weekly_change 계산 (5영업일 전 대비)
    if (data.timeseries.length >= 6) {
      const weekAgo = data.timeseries[data.timeseries.length - 6].종가;
      if (weekAgo !== 0) {
        indicator.weekly_change = parseFloat(
          (((data.latest - weekAgo) / weekAgo) * 100).toFixed(2),
        );
      }
    }

    console.log(
      `  ✅ ${sym.name}: ${oldValue} → ${data.latest} (${data.timeseries.length}일)`,
    );
    successCount++;
    await sleep(500);
  }

  console.log(`\n   ${successCount}개 성공, ${failCount}개 실패\n`);

  // ── 2. 매일경제 RSS 뉴스 수집 ──
  console.log("2️⃣ 매일경제 RSS 뉴스 수집");
  const news = await fetchMKNews();
  console.log(`  ${news.length}개 기사 수집`);
  news.forEach((n) => console.log(`  · ${n.날짜} | ${n.제목.substring(0, 50)}`));

  // ── 3. spread 계산 ──
  const bond10 = indicators.bonds?.[0]?.value ?? prev.spread["10년물"];
  const bond2 = indicators.bonds?.[1]?.value ?? prev.spread["3개월물"];
  const spread = {
    "10년물": bond10,
    "3개월물": bond2,
    "금리차": parseFloat((bond10 - bond2).toFixed(3)),
    "상태": bond10 > bond2 ? "정상" : "역전",
  };

  // ── 4. historical current 값 업데이트 ──
  const historical = JSON.parse(JSON.stringify(prev.historical));
  const valueMap: Record<string, number> = {
    "코스피": indicators.korea[0]?.value,
    "코스닥": indicators.korea[1]?.value,
    "나스닥": indicators.us[0]?.value,
    "S&P500": indicators.us[2]?.value,
    "원/달러": indicators.fx[0]?.value,
    "WTI유가": indicators.commodities[0]?.value,
    "금": indicators.commodities[3]?.value,
    "VIX": indicators.commodities[2]?.value,
    "미국채10년": indicators.bonds[0]?.value,
    "달러인덱스": indicators.fx[1]?.value,
    "비트코인": indicators.commodities[4]?.value,
  };
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

    // === 분석 섹션 (스케줄 트리거가 채울 영역) ===
    briefing: "",
    scenario: { 코드: "", 시나리오: "", 해석: "", 대응: "" },

    // === 데이터 섹션 (스크립트가 채운 영역) ===
    indicators,
    spread,
    causal_chain: "",
    investment_direction: "",
    news,
    cpi_gdp: prev.cpi_gdp,
    divergence: "",
    asset_recommendation: "",
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
