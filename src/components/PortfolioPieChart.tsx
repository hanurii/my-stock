"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

interface PortfolioItem {
  name: string;
  value: number;
  color: string;
}

const COLORS = [
  "#e9c176", // 골드
  "#95d3ba", // 에메랄드
  "#c084fc", // 보라
  "#60a5fa", // 하늘
  "#f472b6", // 핑크
  "#fb923c", // 오렌지
  "#2dd4bf", // 틸
  "#a78bfa", // 라벤더
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
  const data: PortfolioItem[] = holdings.map((h, i) => ({
    name: h.name,
    value: h.eval_amount,
    color: COLORS[i % COLORS.length],
  }));

  if (cash && cash > 0) {
    data.push({ name: "현금 (CMA)", value: cash, color: CASH_COLOR });
  }

  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className="flex flex-col md:flex-row items-center gap-8">
      {/* Pie Chart */}
      <div className="w-64 h-64 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              dataKey="value"
              stroke="none"
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(46, 52, 71, 0.95)",
                border: "1px solid rgba(69, 70, 77, 0.15)",
                borderRadius: "8px",
                color: "#dce1fb",
                fontSize: "13px",
              }}
              formatter={(value) => [`${formatMoney(Number(value))}원`, ""]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex-1 space-y-3">
        {data.map((item, i) => {
          const pct = total > 0 ? ((item.value / total) * 100).toFixed(1) : "0";
          return (
            <div key={i} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-base text-on-surface">{item.name}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-base font-mono text-on-surface">
                  {formatMoney(item.value)}원
                </span>
                <span className="text-sm font-mono text-on-surface-variant w-14 text-right">
                  {pct}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
