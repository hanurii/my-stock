import fs from "fs";
import path from "path";

export type TrendLabel = "강한 매수" | "매수 우위" | "보합" | "매도 우위" | "강한 매도";

export interface MarketDailyPoint {
  date: string;            // YYYY-MM-DD
  kospi_billion: number;   // 억원
  kosdaq_billion: number;
  total_billion: number;
}

export interface SectorDailyPoint {
  date: string;
  sector: string;
  net_buy_billion: number;
}

export interface SectorCumPoint {
  sector: string;
  net_buy_billion: number;
}

export interface ForeignFlowData {
  meta: {
    last_updated: string;
    source: string;
    period_days: number;
    sector_basis: string;
    watchlist_stocks: number;
    failed_stocks: number;
    last_error?: string;
  };
  market: {
    daily: MarketDailyPoint[];
    summary: {
      cum_20d_billion: number;
      cum_60d_billion: number;
      kospi_cum_20d_billion: number;
      kosdaq_cum_20d_billion: number;
      trend_20d: TrendLabel;
      trend_60d: TrendLabel;
      kospi_trend_20d: TrendLabel;
      kosdaq_trend_20d: TrendLabel;
    };
  };
  sectors: {
    daily: SectorDailyPoint[];
    cum_1d: SectorCumPoint[];
    cum_3d: SectorCumPoint[];
    cum_7d: SectorCumPoint[];
    cum_20d: SectorCumPoint[];
    cum_60d: SectorCumPoint[];
  };
}

const FILE_PATH = path.join(process.cwd(), "public", "data", "foreign-flow.json");

// 기존 JSON에 cum_1d가 없을 때 daily의 가장 최근 영업일을 sector별로 합산해 채워준다.
function deriveCum1d(daily: SectorDailyPoint[]): SectorCumPoint[] {
  if (daily.length === 0) return [];
  const allDates = Array.from(new Set(daily.map((p) => p.date))).sort();
  const latest = allDates[allDates.length - 1];
  const m = new Map<string, number>();
  for (const p of daily) {
    if (p.date !== latest) continue;
    m.set(p.sector, (m.get(p.sector) ?? 0) + p.net_buy_billion);
  }
  return Array.from(m.entries())
    .map(([sector, v]) => ({ sector, net_buy_billion: Math.round(v * 10) / 10 }))
    .sort((a, b) => b.net_buy_billion - a.net_buy_billion);
}

export function getForeignFlowData(): ForeignFlowData | null {
  try {
    const raw = fs.readFileSync(FILE_PATH, "utf-8");
    const parsed = JSON.parse(raw) as ForeignFlowData & {
      sectors: ForeignFlowData["sectors"] & { cum_1d?: SectorCumPoint[] };
    };
    if (!parsed.sectors.cum_1d) {
      parsed.sectors.cum_1d = deriveCum1d(parsed.sectors.daily);
    }
    return parsed;
  } catch {
    return null;
  }
}
