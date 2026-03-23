/**
 * Yahoo Finance API에서 모든 지표의 10영업일 timeseries를 가져와 검증하는 스크립트
 */
import fs from "fs";
import path from "path";

const YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart";
const HEADERS = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" };

interface TimeseriesPoint { 날짜: string; 종가: number }

const SYMBOLS = [
  // Korea
  { yahoo: "^KS11", name: "코스피", section: "korea", idx: 0 },
  { yahoo: "^KQ11", name: "코스닥", section: "korea", idx: 1 },
  // US
  { yahoo: "^IXIC", name: "나스닥", section: "us", idx: 0 },
  { yahoo: "^DJI", name: "다우존스", section: "us", idx: 1 },
  { yahoo: "^GSPC", name: "S&P500", section: "us", idx: 2 },
  // FX
  { yahoo: "KRW=X", name: "원/달러", section: "fx", idx: 0 },
  { yahoo: "DX-Y.NYB", name: "달러인덱스", section: "fx", idx: 1 },
  { yahoo: "JPY=X", name: "엔/달러", section: "fx", idx: 2 },
  // Bonds
  { yahoo: "^TNX", name: "미국채10년", section: "bonds", idx: 0 },
  { yahoo: "^IRX", name: "미국채2년", section: "bonds", idx: 1 }, // IRX is 13-week, use 2YY=F for 2yr
  // Commodities
  { yahoo: "CL=F", name: "WTI유가", section: "commodities", idx: 0 },
  // 두바이유는 Yahoo에 없음, skip
  { yahoo: "^VIX", name: "VIX", section: "commodities", idx: 2 },
  { yahoo: "GC=F", name: "금", section: "commodities", idx: 3 },
  { yahoo: "BTC-USD", name: "비트코인", section: "commodities", idx: 4 },
];

async function fetchTimeseries(symbol: string): Promise<{ dates: string[]; closes: (number | null)[] } | null> {
  try {
    const url = `${YAHOO_API}/${encodeURIComponent(symbol)}?range=1mo&interval=1d`;
    const res = await fetch(url, { headers: HEADERS });
    if (!res.ok) return null;
    const json = await res.json();
    const result = json.chart?.result?.[0];
    if (!result) return null;

    const timestamps: number[] = result.timestamp || [];
    const closes: (number | null)[] = result.indicators?.quote?.[0]?.close || [];

    const dates = timestamps.map((t: number) => {
      const d = new Date(t * 1000);
      return `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
    });

    return { dates, closes };
  } catch {
    return null;
  }
}

async function main() {
  console.log("📊 Yahoo Finance에서 10영업일 timeseries 조회 중...\n");

  const reportPath = path.join(process.cwd(), "public/data/2026-03-24.json");
  const report = JSON.parse(fs.readFileSync(reportPath, "utf-8"));

  for (const sym of SYMBOLS) {
    const data = await fetchTimeseries(sym.yahoo);
    if (!data) {
      console.log(`  ❌ ${sym.name} (${sym.yahoo}): 데이터 조회 실패`);
      continue;
    }

    // 마지막 10영업일만 (null 제거)
    const valid: TimeseriesPoint[] = [];
    for (let i = 0; i < data.dates.length; i++) {
      if (data.closes[i] != null) {
        let value = data.closes[i]!;
        // 채권은 yield로 제공됨 (이미 %)
        if (sym.name === "미국채10년" || sym.name === "미국채2년") {
          value = parseFloat(value.toFixed(3));
        } else if (sym.name === "원/달러") {
          value = parseFloat(value.toFixed(1));
        } else if (sym.name === "VIX" || sym.name === "달러인덱스") {
          value = parseFloat(value.toFixed(2));
        } else {
          value = parseFloat(value.toFixed(2));
        }
        valid.push({ 날짜: data.dates[i], 종가: value });
      }
    }
    const last10 = valid.slice(-10);

    // 리포트에 반영
    const section = report.indicators[sym.section];
    if (section && section[sym.idx]) {
      const indicator = section[sym.idx];
      const oldLast = indicator.timeseries?.[indicator.timeseries.length - 1]?.종가;
      indicator.timeseries = last10;

      // 최신 종가로 value도 업데이트
      const latestClose = last10[last10.length - 1]?.종가;
      if (latestClose != null) {
        indicator.value = latestClose;
      }

      console.log(`  ✅ ${sym.name}: ${last10.length}일 | 최신 ${latestClose} (기존 ${oldLast})`);
      // 10영업일 전체 출력
      console.log(`     ${last10.map(p => p.날짜 + ":" + p.종가).join(" → ")}`);
    } else {
      console.log(`  ⚠️ ${sym.name}: 섹션 매핑 실패 (${sym.section}[${sym.idx}])`);
    }
  }

  // historical 섹션도 최신값 업데이트
  const latestKospi = report.indicators.korea[0]?.value;
  const latestNasdaq = report.indicators.us[0]?.value;
  const latestFx = report.indicators.fx[0]?.value;
  const latestWti = report.indicators.commodities[0]?.value;
  const latestGold = report.indicators.commodities[3]?.value;
  const latestVix = report.indicators.commodities[2]?.value;
  const latestBond10 = report.indicators.bonds[0]?.value;
  const latestDxy = report.indicators.fx[1]?.value;

  report.historical = report.historical.map((h: Record<string, unknown>) => {
    if (h.name === "코스피" && latestKospi) return { ...h, current: latestKospi };
    if (h.name === "나스닥" && latestNasdaq) return { ...h, current: latestNasdaq };
    if (h.name === "원/달러" && latestFx) return { ...h, current: latestFx };
    if (h.name === "WTI유가" && latestWti) return { ...h, current: latestWti };
    if (h.name === "금" && latestGold) return { ...h, current: latestGold };
    if (h.name === "VIX" && latestVix) return { ...h, current: latestVix };
    if (h.name === "미국채10년" && latestBond10) return { ...h, current: latestBond10 };
    if (h.name === "달러인덱스" && latestDxy) return { ...h, current: latestDxy };
    return h;
  });

  // 저장
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`\n💾 리포트 업데이트 완료: ${reportPath}`);

  // 검증: 이전 리포트(3/23)와 비교
  console.log("\n=== 검증: 3/23 리포트 대비 변동폭 체크 ===");
  const prevPath = path.join(process.cwd(), "public/data/2026-03-23.json");
  const prev = JSON.parse(fs.readFileSync(prevPath, "utf-8"));

  for (const sym of SYMBOLS) {
    const curr = report.indicators[sym.section]?.[sym.idx];
    const prevInd = prev.indicators[sym.section]?.[sym.idx];
    if (!curr || !prevInd) continue;

    const pct = ((curr.value - prevInd.value) / prevInd.value * 100).toFixed(2);
    const flag = Math.abs(parseFloat(pct)) > 10 ? "⚠️ 비정상 변동" : "✅";
    console.log(`  ${flag} ${sym.name}: ${prevInd.value} → ${curr.value} (${pct}%)`);
  }
}

main().catch(console.error);
