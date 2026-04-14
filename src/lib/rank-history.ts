export interface RankSnapshot {
  t: string;
  ranks: Record<string, [number, number]>; // code -> [rank, score]
}

export interface RankHistory {
  updated_at: string;
  snapshots: RankSnapshot[];
}

export interface StockTrendPoint {
  t: string;
  rank: number;
  score: number;
}

export function getStockTrend(history: RankHistory | null, code: string): StockTrendPoint[] {
  if (!history) return [];
  return history.snapshots
    .filter((s) => s.ranks[code])
    .map((s) => ({ t: s.t, rank: s.ranks[code][0], score: s.ranks[code][1] }));
}
