/**
 * 메가캡 모니터 — 환율 데이터 수집
 *
 * 주요 통화의 5년 평균 KRW 환율 대비 z-score 계산.
 * 원화 강세(z<0) → 외화 종목 매수 유리 → +가산점.
 * 원화 약세(z>0) → 외화 종목 매수 불리 → -감점.
 *
 * 출력: public/data/megacap-fx.json
 *
 * 사용법: npx tsx scripts/fetch-megacap-fx.ts
 */
import fs from "fs";
import path from "path";

const ROOT = path.resolve(__dirname, "..");
const OUTPUT_PATH = path.join(ROOT, "public", "data", "megacap-fx.json");

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";

// Yahoo Finance FX 심볼 (KRW 대비)
// synthetic: USDKRW / USDXXX 형태로 합성 (CNYKRW=X 같은 직접 페어가 없을 때)
const FX_PAIRS: Array<{
  currency: string;
  label: string;
  symbol?: string;
  synthetic?: { krw: string; foreign: string };
}> = [
  { currency: "USD", symbol: "KRW=X", label: "원/달러" },
  { currency: "JPY", symbol: "JPYKRW=X", label: "원/엔" },
  { currency: "CNY", label: "원/위안", synthetic: { krw: "KRW=X", foreign: "CNY=X" } },
  { currency: "HKD", symbol: "HKDKRW=X", label: "원/홍콩달러" },
  { currency: "EUR", symbol: "EURKRW=X", label: "원/유로" },
  { currency: "TWD", symbol: "TWDKRW=X", label: "원/대만달러" },
  { currency: "GBP", symbol: "GBPKRW=X", label: "원/파운드" },
  { currency: "INR", symbol: "INRKRW=X", label: "원/루피" },
];

interface FXRate {
  currency: string;
  symbol: string;
  label: string;
  current: number;
  avg_5y: number;
  std_5y: number;
  z_score: number;
  fx_score: number;          // -20 ~ +20
  fx_label: string;          // "원화 매우 약세" 등
  pct_from_avg: number;      // 5년 평균 대비 % 차이
  history_points: number;
}

interface FXOutput {
  generated_at: string;
  rates: FXRate[];
}

async function fetchFiveYearDaily(symbol: string): Promise<{ ts: number[]; closes: number[] } | null> {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=5y&interval=1d`;
  try {
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;
    const json = await res.json();
    const result = json?.chart?.result?.[0];
    if (!result) return null;
    const ts: number[] = result.timestamp ?? [];
    const rawCloses: (number | null)[] = result.indicators?.quote?.[0]?.close ?? [];
    const tsClean: number[] = [];
    const closes: number[] = [];
    for (let i = 0; i < rawCloses.length; i++) {
      const c = rawCloses[i];
      if (c != null && c > 0) {
        tsClean.push(ts[i]);
        closes.push(c);
      }
    }
    if (closes.length === 0) return null;
    return { ts: tsClean, closes };
  } catch {
    return null;
  }
}

// USDKRW / USDXXX = XXX/KRW (합성)
function syntheticKRWRate(usdkrw: { ts: number[]; closes: number[] }, usdxxx: { ts: number[]; closes: number[] }): number[] {
  const xxxMap = new Map<number, number>();
  for (let i = 0; i < usdxxx.ts.length; i++) xxxMap.set(usdxxx.ts[i], usdxxx.closes[i]);
  const out: number[] = [];
  for (let i = 0; i < usdkrw.ts.length; i++) {
    const xxx = xxxMap.get(usdkrw.ts[i]);
    if (xxx != null && xxx > 0) {
      out.push(usdkrw.closes[i] / xxx);
    }
  }
  return out;
}

function computeZScore(values: number[]): { current: number; avg: number; std: number; z: number } {
  const current = values[values.length - 1];
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((acc, v) => acc + (v - avg) ** 2, 0) / values.length;
  const std = Math.sqrt(variance);
  const z = std === 0 ? 0 : (current - avg) / std;
  return { current, avg, std, z };
}

// z-score → FX 점수 매핑 (원화 약세 = 양수 z = 외화 매수 불리 = 마이너스 점수)
function scoreFromZ(z: number): { score: number; label: string } {
  if (z <= -1.5) return { score: 20, label: "원화 매우 강세 (외화 매수 최적)" };
  if (z <= -0.5) return { score: 10, label: "원화 강세" };
  if (z < 0.5) return { score: 0, label: "중립" };
  if (z < 1.5) return { score: -10, label: "원화 약세" };
  return { score: -20, label: "원화 매우 약세 (외화 매수 비추)" };
}

async function main() {
  console.log("[megacap-fx] start");
  const rates: FXRate[] = [];

  for (const pair of FX_PAIRS) {
    let closes: number[] | null = null;
    let resolvedSymbol = "";

    if (pair.synthetic) {
      process.stdout.write(`  ${pair.label} (synth ${pair.synthetic.krw}/${pair.synthetic.foreign}) `);
      const [krw, foreign] = await Promise.all([
        fetchFiveYearDaily(pair.synthetic.krw),
        fetchFiveYearDaily(pair.synthetic.foreign),
      ]);
      if (krw && foreign) {
        closes = syntheticKRWRate(krw, foreign);
        resolvedSymbol = `${pair.synthetic.krw}÷${pair.synthetic.foreign}`;
      }
    } else if (pair.symbol) {
      process.stdout.write(`  ${pair.label} (${pair.symbol}) `);
      const r = await fetchFiveYearDaily(pair.symbol);
      closes = r?.closes ?? null;
      resolvedSymbol = pair.symbol;
    }

    if (!closes || closes.length < 100) {
      console.log("❌ insufficient data");
      continue;
    }
    const { current, avg, std, z } = computeZScore(closes);
    const { score, label } = scoreFromZ(z);
    const pctFromAvg = ((current - avg) / avg) * 100;
    rates.push({
      currency: pair.currency,
      symbol: resolvedSymbol,
      label: pair.label,
      current: Math.round(current * 100) / 100,
      avg_5y: Math.round(avg * 100) / 100,
      std_5y: Math.round(std * 100) / 100,
      z_score: Math.round(z * 100) / 100,
      fx_score: score,
      fx_label: label,
      pct_from_avg: Math.round(pctFromAvg * 10) / 10,
      history_points: closes.length,
    });
    console.log(`${current.toFixed(2)} | μ=${avg.toFixed(2)} | z=${z.toFixed(2)} | ${score >= 0 ? "+" : ""}${score}pt`);
  }

  const output: FXOutput = {
    generated_at: new Date().toISOString().slice(0, 10),
    rates,
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2), "utf-8");
  console.log(`\n[done] ${rates.length} FX pairs saved → ${OUTPUT_PATH}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
