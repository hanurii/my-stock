/**
 * 장기 월봉 차트 증분 업데이트 스크립트
 *
 * 기존 역사 데이터는 절대 삭제하지 않고, 새로운 월 데이터만 추가.
 * 현재 진행 중인 월(미완성)은 매 실행 시 최신 종가로 갱신.
 * 이미 확정된 과거 월 데이터는 변경하지 않음.
 *
 * Yahoo Finance monthly (interval=1mo, range=2y)로 최근 24개월을 가져와
 * 기존 timeseries에 없는 월만 추가.
 *
 * 실행: npx tsx scripts/update-longterm-charts.ts
 */
import fs from "fs";
import path from "path";

const YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// longterm_charts의 name과 Yahoo Finance 심볼 매핑
const CHART_SYMBOLS: { name: string; yahoo: string }[] = [
  { name: "코스피",    yahoo: "^KS11" },
  { name: "나스닥",    yahoo: "^IXIC" },
  { name: "원/달러",   yahoo: "KRW=X" },
  { name: "미국채10년", yahoo: "^TNX" },
  { name: "WTI유가",   yahoo: "CL=F" },
  { name: "금",        yahoo: "GC=F" },
  { name: "VIX",       yahoo: "^VIX" },
];

interface TimeseriesPoint {
  날짜: string; // "YYYY-MM"
  종가: number;
}

interface ChartItem {
  name: string;
  unit: string;
  start_year: string;
  end_year: string;
  timeseries: TimeseriesPoint[];
}

function roundClose(name: string, value: number): number {
  if (/채|TNX/.test(name)) return parseFloat(value.toFixed(3));
  if (/달러인덱스|VIX/.test(name)) return parseFloat(value.toFixed(2));
  if (/원/.test(name)) return parseFloat(value.toFixed(1));
  return parseFloat(value.toFixed(2));
}

/** Yahoo Finance에서 월봉 데이터 수집 (최근 2년) */
async function fetchMonthly(
  symbol: string,
  name: string,
): Promise<TimeseriesPoint[] | null> {
  try {
    const url = `${YAHOO_API}/${encodeURIComponent(symbol)}?range=2y&interval=1mo`;
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

    const points: TimeseriesPoint[] = [];
    for (let i = 0; i < timestamps.length; i++) {
      const closeVal = closes[i] ?? (i === timestamps.length - 1 ? meta?.regularMarketPrice : null);
      if (closeVal == null) continue;

      const d = new Date(timestamps[i] * 1000);
      // 월봉이므로 getUTCMonth 사용 (일봉과 달리 월 단위에서는 타임존 영향 최소)
      const yyyy = d.getUTCFullYear();
      const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
      points.push({ 날짜: `${yyyy}-${mm}`, 종가: roundClose(name, closeVal) });
    }

    return points;
  } catch {
    return null;
  }
}

async function main() {
  const dataDir = path.join(process.cwd(), "public", "data");

  console.log("📈 장기 월봉 차트 증분 업데이트");
  console.log("─".repeat(55));

  // 최신 리포트 로드
  const files = fs.readdirSync(dataDir)
    .filter((f) => /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
    .sort();

  if (files.length === 0) {
    console.error("❌ 리포트 파일 없음");
    process.exitCode = 1;
    return;
  }

  const latestPath = path.join(dataDir, files[files.length - 1]);
  const latestReport = JSON.parse(fs.readFileSync(latestPath, "utf-8"));
  const charts: ChartItem[] = latestReport.longterm_charts;

  // 현재 연도-월 (진행 중인 월 판단용)
  const now = new Date();
  const currentMonth = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;

  const updatedCharts: ChartItem[] = JSON.parse(JSON.stringify(charts)); // 깊은 복사
  let totalAdded = 0;
  let totalUpdated = 0;

  console.log();
  for (const sym of CHART_SYMBOLS) {
    const chartItem = updatedCharts.find((c) => c.name === sym.name);
    if (!chartItem) {
      console.log(`  ⚠️  ${sym.name}: longterm_charts에서 찾을 수 없음 — 건너뜀`);
      continue;
    }

    const newPoints = await fetchMonthly(sym.yahoo, sym.name);
    if (!newPoints || newPoints.length === 0) {
      console.log(`  ❌ ${sym.name} (${sym.yahoo}): 조회 실패 — 기존 데이터 유지`);
      await sleep(500);
      continue;
    }

    // 기존 날짜 집합 (O(1) 탐색용)
    const existingDates = new Map<string, number>(
      chartItem.timeseries.map((p, i) => [p.날짜, i]),
    );

    let added = 0;
    let updated = 0;

    for (const point of newPoints) {
      const existingIdx = existingDates.get(point.날짜);

      if (existingIdx === undefined) {
        // 새 월 → 추가
        chartItem.timeseries.push(point);
        existingDates.set(point.날짜, chartItem.timeseries.length - 1);
        added++;
      } else if (point.날짜 === currentMonth) {
        // 현재 진행 중인 월 → 최신 종가로 갱신
        if (chartItem.timeseries[existingIdx].종가 !== point.종가) {
          chartItem.timeseries[existingIdx].종가 = point.종가;
          updated++;
        }
      }
      // 확정된 과거 월 → 변경하지 않음
    }

    // 날짜 순 정렬 유지
    chartItem.timeseries.sort((a, b) => a.날짜.localeCompare(b.날짜));

    // end_year 업데이트
    const lastDate = chartItem.timeseries[chartItem.timeseries.length - 1]?.날짜;
    if (lastDate) {
      chartItem.end_year = lastDate.slice(0, 4);
    }

    totalAdded += added;
    totalUpdated += updated;
    const lastVal = chartItem.timeseries[chartItem.timeseries.length - 1];
    console.log(
      `  ✅ ${sym.name.padEnd(6)}: 총 ${chartItem.timeseries.length}pt` +
      `  +${added}추가  ~${updated}갱신  최신: ${lastVal?.날짜} ${lastVal?.종가}`,
    );

    await sleep(500);
  }

  // 변경 없으면 종료
  if (totalAdded === 0 && totalUpdated === 0) {
    console.log("\n✅ 추가/갱신할 데이터 없음");
    return;
  }

  // 모든 리포트 파일에 업데이트된 longterm_charts 반영
  console.log(`\n📝 ${files.length}개 리포트에 longterm_charts 반영 중...`);
  for (const file of files) {
    const filePath = path.join(dataDir, file);
    const report = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    report.longterm_charts = updatedCharts;
    fs.writeFileSync(filePath, JSON.stringify(report, null, 2) + "\n", "utf-8");
  }

  console.log("─".repeat(55));
  console.log(`📊 완료: 새 데이터 +${totalAdded}개 추가, ${totalUpdated}개 갱신`);
}

main().catch((err) => {
  console.error("스크립트 실행 실패:", err);
  process.exitCode = 1;
});
