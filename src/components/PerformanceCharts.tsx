"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface QuarterlyData {
  quarter: string;
  revenue: number;
  operating_income: number;
  net_income: number;
  op_margin: number;
  eps: number;
}

interface YearlyData {
  year: number;
  revenue: number;
  operating_income: number;
  net_income: number;
  op_margin: number;
  eps: number;
  dps: number;
}

function formatBillion(value: number): string {
  if (!value) return "0";
  const billions = value / 1e8;
  if (billions >= 10000) return `${(billions / 10000).toFixed(1)}조`;
  return `${billions.toFixed(0)}억`;
}

const tooltipStyle = {
  backgroundColor: "rgba(46, 52, 71, 0.95)",
  border: "1px solid rgba(69, 70, 77, 0.15)",
  borderRadius: "8px",
  color: "#dce1fb",
  fontSize: "13px",
};

export function QuarterlyChart({ data }: { data: QuarterlyData[] }) {
  if (!data || data.length === 0) return null;

  const chartData = [...data].reverse().map((q) => ({
    name: q.quarter,
    "매출": q.revenue,
    "영업이익": q.operating_income,
    "순이익": q.net_income,
    "영업이익률": q.op_margin,
  }));

  return (
    <div className="space-y-6">
      {/* 매출/영업이익/순이익 바차트 */}
      <div>
        <p className="text-xs text-on-surface-variant/50 mb-3">매출 · 영업이익 · 순이익</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} barCategoryGap="20%">
            <XAxis
              dataKey="name"
              tick={{ fill: "#909097", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#909097", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={formatBillion}
              width={55}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) => [formatBillion(Number(value)), ""]}
            />
            <Legend
              wrapperStyle={{ fontSize: "12px", color: "#909097" }}
            />
            <Bar dataKey="매출" fill="#e9c176" radius={[4, 4, 0, 0]} />
            <Bar dataKey="영업이익" fill="#95d3ba" radius={[4, 4, 0, 0]} />
            <Bar dataKey="순이익" fill="#6ea8fe" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 영업이익률 라인 */}
      <div>
        <p className="text-xs text-on-surface-variant/50 mb-3">영업이익률 추이</p>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={chartData}>
            <XAxis
              dataKey="name"
              tick={{ fill: "#909097", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#909097", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
              width={45}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) => [`${value}%`, "영업이익률"]}
            />
            <Line
              type="monotone"
              dataKey="영업이익률"
              stroke="#e9c176"
              strokeWidth={2}
              dot={{ fill: "#e9c176", r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function AnnualChart({ data }: { data: YearlyData[] }) {
  if (!data || data.length === 0) return null;

  const chartData = data
    .filter((d) => d.revenue || d.operating_income || d.net_income)
    .map((d) => ({
      name: `${d.year}`,
      "매출": d.revenue,
      "영업이익": d.operating_income,
      "순이익": d.net_income,
      "EPS": d.eps,
      "배당금": d.dps,
    }));

  return (
    <div className="space-y-6">
      {/* 매출/영업이익/순이익 라인차트 */}
      <div>
        <p className="text-xs text-on-surface-variant/50 mb-3">매출 · 영업이익 · 순이익</p>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <XAxis
              dataKey="name"
              tick={{ fill: "#909097", fontSize: 11 }}
              axisLine={{ stroke: "#2e3447" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#909097", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={formatBillion}
              width={55}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) => [formatBillion(Number(value)), ""]}
            />
            <Legend wrapperStyle={{ fontSize: "12px", color: "#909097" }} />
            <Line type="monotone" dataKey="매출" stroke="#e9c176" strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="영업이익" stroke="#95d3ba" strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="순이익" stroke="#6ea8fe" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* EPS/배당금 라인차트 */}
      <div>
        <p className="text-xs text-on-surface-variant/50 mb-3">EPS · 배당금</p>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <XAxis
              dataKey="name"
              tick={{ fill: "#909097", fontSize: 11 }}
              axisLine={{ stroke: "#2e3447" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#909097", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}천`}
              width={45}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) => [`${Number(value).toLocaleString()}원`, ""]}
            />
            <Legend wrapperStyle={{ fontSize: "12px", color: "#909097" }} />
            <Line type="monotone" dataKey="EPS" stroke="#c084fc" strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="배당금" stroke="#f472b6" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
