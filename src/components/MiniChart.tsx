"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface MiniChartProps {
  data: { 날짜: string; 종가: number }[];
  color?: string;
  height?: number;
}

export function MiniChart({
  data,
  color = "#95d3ba",
  height = 200,
}: MiniChartProps) {
  if (!data || data.length < 2) return null;

  // 데이터 포인트가 많을 때 X축 라벨 간격 조절
  const tickInterval = data.length > 200
    ? Math.floor(data.length / 8)  // 장기 월별: ~8개 라벨
    : data.length > 50
      ? Math.floor(data.length / 10)
      : undefined; // 단기: 기본

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <XAxis
          dataKey="날짜"
          tick={{ fill: "#909097", fontSize: 10 }}
          axisLine={{ stroke: "#2e3447" }}
          tickLine={false}
          interval={tickInterval}
        />
        <YAxis
          domain={["auto", "auto"]}
          tick={{ fill: "#909097", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={55}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "rgba(46, 52, 71, 0.9)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(69, 70, 77, 0.15)",
            borderRadius: "8px",
            color: "#dce1fb",
            fontSize: "12px",
          }}
          formatter={(value) => [Number(value).toLocaleString(), "값"]}
        />
        <Line
          type="monotone"
          dataKey="종가"
          stroke={color}
          strokeWidth={data.length > 100 ? 1.5 : 2}
          dot={false}
          activeDot={{ r: 4, fill: color }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
