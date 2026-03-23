"use client";

import { useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

interface PortfolioItem {
  name: string;
  value: number;
  color: string;
  pct: string;
}

const COLORS = [
  "#e9c176", "#95d3ba", "#c084fc", "#60a5fa",
  "#f472b6", "#fb923c", "#2dd4bf", "#a78bfa",
];
const CASH_COLOR = "#45464d";

function formatMoney(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}억`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}만`;
  return amount.toLocaleString();
}

export function PortfolioPieChart({
  holdings,
  cash,
}: {
  holdings: { name: string; eval_amount: number }[];
  cash?: number;
}) {
  const [activeIndex, setActiveIndex] = useState(-1);

  const total = holdings.reduce((s, h) => s + h.eval_amount, 0) + (cash || 0);

  const data: PortfolioItem[] = holdings.map((h, i) => ({
    name: h.name,
    value: h.eval_amount,
    color: COLORS[i % COLORS.length],
    pct: total > 0 ? ((h.eval_amount / total) * 100).toFixed(1) : "0",
  }));

  if (cash && cash > 0) {
    data.push({
      name: "현금 (CMA)",
      value: cash,
      color: CASH_COLOR,
      pct: total > 0 ? ((cash / total) * 100).toFixed(1) : "0",
    });
  }

  const activeItem = activeIndex >= 0 ? data[activeIndex] : null;

  return (
    <div className="flex flex-col md:flex-row items-center gap-8">
      {/* Pie Chart */}
      <div className="w-72 h-72 shrink-0 relative">
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

        {/* 중앙 호버 정보 */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {activeItem ? (
            <div className="text-center transition-all duration-300">
              <p className="text-sm text-on-surface font-medium">{activeItem.name}</p>
              <p className="text-2xl font-mono font-bold" style={{ color: activeItem.color }}>
                {activeItem.pct}%
              </p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-xs text-on-surface-variant/50">총 자산</p>
              <p className="text-lg font-mono text-on-surface font-bold">{formatMoney(total)}원</p>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex-1 space-y-2">
        {data.map((item, i) => (
          <div
            key={i}
            className="flex items-center justify-between py-2.5 px-3 rounded-lg transition-all duration-300 cursor-default"
            style={{
              backgroundColor: activeIndex === i ? `${item.color}15` : "transparent",
              opacity: activeIndex >= 0 && activeIndex !== i ? 0.4 : 1,
            }}
            onMouseEnter={() => setActiveIndex(i)}
            onMouseLeave={() => setActiveIndex(-1)}
          >
            <div className="flex items-center gap-3">
              <span
                className="w-3 h-3 rounded-full shrink-0 transition-transform duration-300"
                style={{
                  backgroundColor: item.color,
                  transform: activeIndex === i ? "scale(1.5)" : "scale(1)",
                  boxShadow: activeIndex === i ? `0 0 6px ${item.color}80` : "none",
                }}
              />
              <span className="text-base text-on-surface">{item.name}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-base font-mono text-on-surface">
                {formatMoney(item.value)}원
              </span>
              <span
                className="text-sm font-mono w-14 text-right transition-colors duration-300"
                style={{ color: activeIndex === i ? item.color : "#909097" }}
              >
                {item.pct}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
