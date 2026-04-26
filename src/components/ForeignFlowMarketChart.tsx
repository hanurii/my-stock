"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { useMemo, useState } from "react";
import type { MarketDailyPoint } from "@/lib/foreign-flow";

type Series = "kospi" | "kosdaq" | "total";
type Window = 20 | 60;

interface Props {
  daily: MarketDailyPoint[];
}

const SERIES_KEY: Record<Series, keyof MarketDailyPoint> = {
  kospi: "kospi_billion",
  kosdaq: "kosdaq_billion",
  total: "total_billion",
};

const SERIES_LABEL: Record<Series, string> = {
  kospi: "코스피",
  kosdaq: "코스닥",
  total: "전체 (코스피+코스닥)",
};

function formatBillionShort(v: number): string {
  if (Math.abs(v) >= 10000) return `${(v / 10000).toFixed(1)}조`;
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}천억`;
  return `${Math.round(v)}억`;
}

function formatBillionTooltip(v: number): string {
  return `${v.toLocaleString("ko-KR", { maximumFractionDigits: 1 })}억원`;
}

function formatDateShort(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${parseInt(m, 10)}/${parseInt(d, 10)}`;
}

export function ForeignFlowMarketChart({ daily }: Props) {
  const [series, setSeries] = useState<Series>("total");
  const [windowDays, setWindowDays] = useState<Window>(20);

  const sliced = useMemo(
    () => daily.slice(-windowDays),
    [daily, windowDays],
  );

  const chartData = useMemo(() => {
    const key = SERIES_KEY[series];
    let cumulative = 0;
    return sliced.map((p) => {
      const v = p[key] as number;
      cumulative += v;
      return {
        date: formatDateShort(p.date),
        net: v,
        cumulative: Math.round(cumulative * 10) / 10,
      };
    });
  }, [sliced, series]);

  if (daily.length === 0) {
    return (
      <div className="text-on-surface-variant text-sm py-12 text-center">
        시장 일별 외인 순매수 데이터가 아직 없습니다. 매일 자동 수집을 통해 누적됩니다.
      </div>
    );
  }

  return (
    <div>
      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex gap-1 rounded-md bg-surface-container-low p-1">
          {(["kospi", "kosdaq", "total"] as Series[]).map((s) => (
            <button
              key={s}
              onClick={() => setSeries(s)}
              className={`px-3 py-1.5 text-xs rounded transition-colors ${
                series === s
                  ? "bg-primary text-on-primary font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {SERIES_LABEL[s]}
            </button>
          ))}
        </div>
        <div className="flex gap-1 rounded-md bg-surface-container-low p-1 ml-auto">
          {([20, 60] as Window[]).map((w) => (
            <button
              key={w}
              onClick={() => setWindowDays(w)}
              className={`px-3 py-1.5 text-xs rounded transition-colors ${
                windowDays === w
                  ? "bg-primary text-on-primary font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              최근 {w}일
            </button>
          ))}
        </div>
      </div>

      {sliced.length < 2 ? (
        <div className="text-on-surface-variant text-sm py-12 text-center">
          현재 누적된 데이터: {sliced.length}일 · 의미 있는 추세 표시까지 자료가 더 필요합니다.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart
            data={chartData}
            margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
          >
            <XAxis
              dataKey="date"
              tick={{ fill: "#909097", fontSize: 11 }}
              axisLine={{ stroke: "#2e3447" }}
              tickLine={false}
              interval={Math.max(0, Math.floor(chartData.length / 10) - 1)}
            />
            <YAxis
              yAxisId="left"
              tick={{ fill: "#909097", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={56}
              tickFormatter={(v: number) => formatBillionShort(v)}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: "#95d3ba", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={56}
              tickFormatter={(v: number) => formatBillionShort(v)}
            />
            <ReferenceLine yAxisId="left" y={0} stroke="#45464d" strokeDasharray="3 3" />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(46, 52, 71, 0.95)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(69, 70, 77, 0.3)",
                borderRadius: "8px",
                color: "#dce1fb",
                fontSize: "12px",
              }}
              formatter={(value, name) => {
                const num = typeof value === "number" ? value : Number(value);
                const label = name === "net" ? "일별 순매수" : "누적";
                return [formatBillionTooltip(num), label];
              }}
            />
            <Bar yAxisId="left" dataKey="net" name="net" radius={[2, 2, 0, 0]}>
              {chartData.map((d, i) => (
                <Cell key={i} fill={d.net >= 0 ? "#e9c176" : "#ffb4ab"} />
              ))}
            </Bar>
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="cumulative"
              name="cumulative"
              stroke="#95d3ba"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#95d3ba" }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      <div className="flex items-center justify-end gap-4 mt-3 text-[11px] text-on-surface-variant">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm" style={{ background: "#e9c176" }} />
          순매수
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm" style={{ background: "#ffb4ab" }} />
          순매도
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5" style={{ background: "#95d3ba" }} />
          누적
        </span>
      </div>
    </div>
  );
}
