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
import { type MarketRegime, downtrendSegments, regimeStreak } from "./marketRegime";

export function MarketRegimeChart({ data }: { data: MarketRegime }) {
  if (!data || data.series.length < 2) {
    return (
      <p className="text-[11px] text-on-surface-variant/70">
        등가중 지수 데이터 없음 — build_market_regime.py 실행 필요
      </p>
    );
  }
  const segs = downtrendSegments(data.series);
  // 카테고리 x축에서 단일-하루 구간(x1===x2)은 폭 0이라 안 그려짐 → x2를 다음 날짜로 확장해 렌더.
  const nextDate = new Map<string, string>();
  data.series.forEach((p, i) => {
    if (i + 1 < data.series.length) nextDate.set(p.date, data.series[i + 1].date);
  });
  const up = data.current.uptrend;
  const streak = regimeStreak(data.series);
  // 검증(2025-05~2026-08, 전환 19회): 상승 전환의 절반이 1~2일 만에 꺼짐. 3일 연속
  // 확인이 가짜 전환 9/9를 걸러내고 잃는 상승일은 7%뿐 → 확인 충족 시점부터 신규 진입.
  const confirmed = up === true && streak >= 3;
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
        {streak > 0 && (
          <span
            className="text-[11px] font-medium px-2 py-0.5 rounded tabular-nums"
            title="상승 전환의 절반은 1~2일 만에 꺼짐(15개월 실측). 3일 연속 확인 후 신규 진입 권장 — 확인 후 평균 12.8일 더 지속"
            style={{
              backgroundColor: confirmed
                ? "rgba(16,185,129,0.18)"
                : up
                  ? "rgba(233,193,118,0.16)"
                  : "rgba(255,180,171,0.12)",
              color: confirmed ? "#10b981" : up ? "#e9c176" : "#ffb4ab",
            }}
          >
            {up
              ? confirmed
                ? `상승 ${streak}일째 · 3일 확인 ✓`
                : `상승 ${streak}일째 · 확인 중 (${streak}/3일)`
              : `하락 ${streak}일째`}
          </span>
        )}
        <span className="text-[11px] text-on-surface-variant/70">
          {data.current.date} · 지수 {data.current.index} / 20일선 {data.current.ma20 ?? "—"}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data.series} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
          {segs.map((s, i) => (
            <ReferenceArea
              key={i}
              x1={s.x1}
              x2={s.x1 === s.x2 ? nextDate.get(s.x2) ?? s.x2 : s.x2}
              fill="#ff5449"
              fillOpacity={0.08}
              ifOverflow="extendDomain"
            />
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
          <Tooltip contentStyle={{ backgroundColor: "rgba(46,52,71,0.9)", backdropFilter: "blur(20px)", border: "1px solid #2e3447", borderRadius: 8, color: "#dce1fb", fontSize: 11 }} />
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
