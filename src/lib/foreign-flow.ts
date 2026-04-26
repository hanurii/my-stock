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
    cum_20d: SectorCumPoint[];
    cum_60d: SectorCumPoint[];
  };
}

const FILE_PATH = path.join(process.cwd(), "public", "data", "foreign-flow.json");

export function getForeignFlowData(): ForeignFlowData | null {
  try {
    const raw = fs.readFileSync(FILE_PATH, "utf-8");
    return JSON.parse(raw) as ForeignFlowData;
  } catch {
    return null;
  }
}
