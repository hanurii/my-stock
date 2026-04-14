"use client";

import { useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { StockTrendPoint } from "@/lib/rank-history";

interface Props {
  trend: StockTrendPoint[];
  stockName: string;
  totalStocks: number;
  onClose: () => void;
}

export function RankTrendModal({ trend, stockName, totalStocks, onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const data = trend.map((p) => ({
    날짜: p.t.replace("T", " "),
    순위: p.rank,
    점수: p.score,
  }));

  const ranks = trend.map((p) => p.rank);
  const minRank = Math.min(...ranks);
  const maxRank = Math.max(...ranks);
  const domainTop = Math.max(1, minRank - 1);
  const domainBottom = Math.min(totalStocks, maxRank + 1);

  const tickInterval = data.length > 20
    ? Math.floor(data.length / 8)
    : data.length > 10
      ? Math.floor(data.length / 6)
      : undefined;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[#1a1e2e] border border-[#2e3447] rounded-xl p-5 w-[90vw] max-w-[520px] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-[#dce1fb]">{stockName} — 순위 추이</h3>
          <button
            onClick={onClose}
            className="text-[#909097] hover:text-[#dce1fb] transition-colors text-lg leading-none"
          >
            ✕
          </button>
        </div>

        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <XAxis
              dataKey="날짜"
              tick={{ fill: "#909097", fontSize: 10 }}
              axisLine={{ stroke: "#2e3447" }}
              tickLine={false}
              interval={tickInterval}
            />
            <YAxis
              yAxisId="rank"
              reversed
              domain={[domainTop, domainBottom]}
              tick={{ fill: "#909097", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={30}
              label={{ value: "순위", angle: -90, position: "insideLeft", fill: "#909097", fontSize: 10 }}
              allowDecimals={false}
            />
            <YAxis
              yAxisId="score"
              orientation="right"
              domain={[0, 100]}
              tick={{ fill: "#909097", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={30}
              label={{ value: "점수", angle: 90, position: "insideRight", fill: "#909097", fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(46, 52, 71, 0.95)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(69, 70, 77, 0.15)",
                borderRadius: "8px",
                color: "#dce1fb",
                fontSize: "12px",
              }}
              formatter={(value, name) => {
                if (name === "순위") return [`${value}위`, "순위"];
                return [`${value}점`, "점수"];
              }}
            />
            <Line
              yAxisId="rank"
              type="monotone"
              dataKey="순위"
              stroke="#6eedb5"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#6eedb5" }}
            />
            <Line
              yAxisId="score"
              type="monotone"
              dataKey="점수"
              stroke="#7c8aff"
              strokeWidth={1.5}
              strokeDasharray="4 2"
              dot={false}
              activeDot={{ r: 3, fill: "#7c8aff" }}
            />
          </LineChart>
        </ResponsiveContainer>

        <div className="flex items-center gap-4 mt-3 text-[10px] text-[#909097]">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-0.5 bg-[#6eedb5] rounded" /> 순위 (낮을수록 좋음)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-0.5 bg-[#7c8aff] rounded border-dashed" /> 점수
          </span>
        </div>
      </div>
    </div>
  );
}
