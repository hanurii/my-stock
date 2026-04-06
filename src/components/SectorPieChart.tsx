"use client";

import { useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { formatUSD } from "@/lib/format";

interface SectorItem {
  sector: string;
  value: number;
  weight_pct: number;
  count: number;
  names?: string[];
}

const COLORS = [
  "#e9c176", "#95d3ba", "#c084fc", "#60a5fa",
  "#f472b6", "#fb923c", "#2dd4bf", "#a78bfa",
  "#fbbf24", "#6ee7b7", "#818cf8", "#45464d",
];

function formatKRW(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}억원`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}만원`;
  return `${amount.toLocaleString()}원`;
}

export function SectorPieChart({
  sectors,
  totalValue,
  currency = "usd",
}: {
  sectors: SectorItem[];
  totalValue: number;
  currency?: "usd" | "krw" | "count";
}) {
  const formatCount = (v: number) => `${v}개 종목`;
  const fmt = currency === "count" ? formatCount : currency === "krw" ? formatKRW : formatUSD;
  const [activeIndex, setActiveIndex] = useState(-1);

  const data = sectors.map((s, i) => ({
    name: s.sector,
    value: s.value,
    pct: s.weight_pct.toFixed(1),
    count: s.count,
    names: s.names || [],
    color: COLORS[i % COLORS.length],
  }));

  const activeItem = activeIndex >= 0 ? data[activeIndex] : null;

  return (
    <div className="flex flex-col md:flex-row items-center gap-4 sm:gap-8">
      <div className="w-52 h-52 sm:w-72 sm:h-72 shrink-0 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={65}
              outerRadius={105}
              dataKey="value"
              stroke="none"
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(-1)}
            >
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.color}
                  style={{
                    transition: "all 0.3s ease",
                    opacity: activeIndex >= 0 && activeIndex !== i ? 0.3 : 1,
                    transform: activeIndex === i ? "scale(1.05)" : "scale(1)",
                    transformOrigin: "center",
                    filter: activeIndex === i ? `drop-shadow(0 0 8px ${entry.color}80)` : "none",
                  }}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {activeItem ? (
            <div className="text-center transition-all duration-300">
              <p className="text-sm text-on-surface font-medium">{activeItem.name}</p>
              <p className="text-2xl font-mono font-bold" style={{ color: activeItem.color }}>
                {activeItem.pct}%
              </p>
              <p className="text-xs text-on-surface-variant">{activeItem.count}개 종목</p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-xs text-on-surface-variant/50">Total</p>
              <p className="text-lg font-mono text-on-surface font-bold">{fmt(totalValue)}</p>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 space-y-1">
        {data.map((item, i) => (
          <div
            key={item.name}
            className="rounded-lg transition-all duration-300 cursor-default"
            style={{
              backgroundColor: activeIndex === i ? `${item.color}15` : "transparent",
              opacity: activeIndex >= 0 && activeIndex !== i ? 0.4 : 1,
            }}
            onMouseEnter={() => setActiveIndex(i)}
            onMouseLeave={() => setActiveIndex(-1)}
          >
            <div className="flex items-center justify-between py-2 px-3">
              <div className="flex items-center gap-3">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0 transition-transform duration-300"
                  style={{
                    backgroundColor: item.color,
                    transform: activeIndex === i ? "scale(1.5)" : "scale(1)",
                    boxShadow: activeIndex === i ? `0 0 6px ${item.color}80` : "none",
                  }}
                />
                <span className="text-sm text-on-surface">{item.name}</span>
                <span className="text-xs text-on-surface-variant/50">{item.count}개</span>
              </div>
              <div className="flex items-center gap-4">
                {currency !== "count" && (
                  <span className="text-sm font-mono text-on-surface">{fmt(item.value)}</span>
                )}
                <span
                  className="text-sm font-mono w-14 text-right transition-colors duration-300"
                  style={{ color: activeIndex === i ? item.color : "#909097" }}
                >
                  {item.pct}%
                </span>
              </div>
            </div>
            {activeIndex === i && item.names.length > 0 && (
              <div className="px-3 pb-2 pl-8 flex flex-wrap gap-x-2 gap-y-0.5">
                {item.names.map((n) => (
                  <span key={n} className="text-xs text-on-surface-variant/70">{n}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
