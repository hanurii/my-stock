"use client";

import { useState } from "react";
import type { StockTrendPoint } from "@/lib/rank-history";
import { RankTrendModal } from "./RankTrendModal";

interface Props {
  trend: StockTrendPoint[];
  stockName: string;
  totalStocks: number;
}

export function RankTrendSparkline({ trend, stockName, totalStocks }: Props) {
  const [open, setOpen] = useState(false);

  if (trend.length < 2) return null;

  const W = 56;
  const H = 18;
  const PAD = 2;

  const ranks = trend.map((p) => p.rank);
  const minR = Math.min(...ranks);
  const maxR = Math.max(...ranks);
  const range = maxR - minR || 1;

  const points = trend.map((p, i) => {
    const x = PAD + (i / (trend.length - 1)) * (W - PAD * 2);
    // Y축 반전: rank 1 = 상단
    const y = PAD + ((p.rank - minR) / range) * (H - PAD * 2);
    return `${x},${y}`;
  });

  const first = trend[0].rank;
  const last = trend[trend.length - 1].rank;
  const color = last < first ? "#6eedb5" : last > first ? "#ffb4ab" : "#909097";

  return (
    <>
      <svg
        width={W}
        height={H}
        className="cursor-pointer hover:opacity-80 transition-opacity"
        onClick={() => setOpen(true)}
      >
        <polyline
          points={points.join(" ")}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {open && (
        <RankTrendModal
          trend={trend}
          stockName={stockName}
          totalStocks={totalStocks}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
