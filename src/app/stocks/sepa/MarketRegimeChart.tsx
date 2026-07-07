"use client";

import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import { type MarketRegime, downtrendSegments } from "./marketRegime";

export function MarketRegimeChart({ data }: { data: MarketRegime }) {
  if (!data || data.series.length < 2) {
    return (
      <p className="text-[11px] text-on-surface-variant/70">
        국면 데이터 없음 — build_market_regime.py 실행 필요
      </p>
    );
  }
  const segs = downtrendSegments(data.series);
  const up = data.current.uptrend;
  const tickInterval = Math.max(1, Math.floor(data.series.length / 8));
  return (
    <div>
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span
          className="text-[11px] font-medium px-2 py-0.5 rounded"
          style={{
            backgroundColor: up ? "rgba(16,185,129,0.18)" : "rgba(255,180,171,0.18)",
            color: up ? "#10b981" : "#ffb4ab",
          }}
        >
          {up ? "🟢 상승추세 (매매 ON)" : "🔴 하락추세 (매매 OFF)"}
        </span>
        <span className="text-[11px] text-on-surface-variant/70">
          {data.current.date} · 지수 {data.current.index} / 20일선 {data.current.ma20 ?? "—"}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data.series} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
          {segs.map((s, i) => (
            <ReferenceArea key={i} x1={s.x1} x2={s.x2} fill="#ff5449" fillOpacity={0.08} ifOverflow="extendDomain" />
          ))}
          <XAxis
            dataKey="date"
            tick={{ fill: "#909097", fontSize: 10 }}
            axisLine={{ stroke: "#2e3447" }}
            tickLine={false}
            interval={tickInterval}
          />
          <YAxis
            tick={{ fill: "#909097", fontSize: 10 }}
            axisLine={{ stroke: "#2e3447" }}
            tickLine={false}
            domain={["auto", "auto"]}
            width={40}
          />
          <Tooltip contentStyle={{ background: "#1a1f2e", border: "1px solid #2e3447", fontSize: 11 }} />
          <Line type="monotone" dataKey="index" stroke="#95d3ba" dot={false} strokeWidth={1.5} name="등가중지수" />
          <Line type="monotone" dataKey="ma20" stroke="#e0a458" dot={false} strokeWidth={1} strokeDasharray="4 3" name="20일선" />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="text-[10px] text-on-surface-variant/60 mt-1">
        ※ 전 종목 등가중 지수(자작·시장 폭 지표). 코스피 아님 — 대형주 강세 국면과 갈릴 수 있음.
      </p>
    </div>
  );
}
