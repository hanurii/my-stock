"use client";

import { MiniChart } from "./MiniChart";
import type { ReportData } from "@/lib/data";

interface ChartsSectionProps {
  report: ReportData;
}

// 지표별 고정 차트 색상 (상승/하락 색상과 겹치지 않는 고유 색상)
const chartColors: Record<string, string> = {
  "코스피": "#c084fc",     // 보라
  "나스닥": "#60a5fa",     // 하늘
  "원/달러": "#f472b6",    // 핑크
  "미국채10년": "#fb923c", // 오렌지
  "WTI유가": "#a78bfa",    // 라벤더
  "두바이유": "#2dd4bf",   // 틸
  "VIX": "#fbbf24",        // 앰버
  "금": "#34d399",         // 민트
  "달러인덱스": "#818cf8", // 인디고
};

const shortTermKeys = ["코스피", "나스닥", "원/달러", "미국채10년", "WTI유가", "두바이유", "VIX"];

export function ChartsSection({ report }: ChartsSectionProps) {
  const allIndicators = [
    ...report.indicators.korea,
    ...report.indicators.us,
    ...report.indicators.fx,
    ...report.indicators.bonds,
    ...report.indicators.commodities,
  ];

  return (
    <div className="space-y-12">
      {/* 단기 추세 */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
          Short-term Trend
        </h3>
        <p className="text-sm text-on-surface-variant mb-6">최근 약 10영업일 추세</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {shortTermKeys.map((key) => {
            const ind = allIndicators.find((i) => i.name === key);
            if (!ind || !ind.timeseries || ind.timeseries.length < 2) return null;

            const lineColor = chartColors[key] || "#909097";
            const changeColor = ind.change > 0 ? "text-[#ffb4ab]" : ind.change < 0 ? "text-[#6ea8fe]" : "text-on-surface-variant";

            return (
              <div key={key} className="bg-surface-container-low rounded-xl p-5 ghost-border">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-base font-medium text-on-surface">{key}</h4>
                  <span className={`text-sm font-mono ${changeColor}`}>
                    {ind.value.toLocaleString()} ({ind.change > 0 ? "+" : ""}{ind.change.toFixed(2)}%)
                  </span>
                </div>
                <MiniChart data={ind.timeseries} color={lineColor} height={150} />
                <p className="text-sm text-on-surface-variant mt-3 leading-relaxed">{ind.comment}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* 장기 추세 */}
      {report.longterm_charts && report.longterm_charts.length > 0 && (
        <section>
          <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
            Long-term Trend
          </h3>
          <p className="text-sm text-on-surface-variant mb-6">연도별 장기 추세 (30~50년)</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {report.longterm_charts.map((chart) => {
              if (!chart.timeseries || chart.timeseries.length < 3) return null;

              // 월별 데이터 그대로 사용 (부드러운 곡선)
              const sampled = chart.timeseries;
              const current = chart.timeseries[chart.timeseries.length - 1];

              // historical에서 같은 이름의 판단 매칭
              const hist = report.historical?.find((h) => h.name === chart.name);
              const judgment = hist?.judgment || "";
              const firstChar = judgment.codePointAt(0);
              let dotColor = "#909097";
              if (firstChar === 0x1F534) dotColor = "#ffb4ab";
              else if (firstChar === 0x1F7E1) dotColor = "#e9c176";
              else if (firstChar === 0x1F7E2) dotColor = "#95d3ba";
              else if (firstChar === 0x1F535) dotColor = "#6ea8fe";
              const judgmentText = judgment.replace(/^(\u{1F534}|\u{1F7E1}|\u{1F7E2}|\u{1F535}|\u{26AA})\s*/u, "");

              return (
                <div key={chart.name} className="bg-surface-container-low rounded-xl p-5 ghost-border">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h4 className="text-base font-medium text-on-surface">{chart.name}</h4>
                      <p className="text-xs text-on-surface-variant">
                        {chart.start_year} — {chart.end_year}
                      </p>
                    </div>
                    <span className="text-sm font-mono text-primary">
                      {current.종가.toLocaleString()} {chart.unit}
                    </span>
                  </div>
                  <MiniChart data={sampled} color={chartColors[chart.name] || "#909097"} height={160} />
                  {judgmentText && (
                    <div className="flex items-start gap-2 mt-3">
                      <span className="mt-0.5 shrink-0 w-2 h-2 rounded-full" style={{ backgroundColor: dotColor }} />
                      <p className="text-xs leading-relaxed" style={{ color: dotColor }}>
                        {judgmentText}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* 장기 추세 종합 판단 */}
          {report.historical && report.historical.length > 0 && (() => {
            const highItems = report.historical.filter((h) => {
              const fc = h.judgment.codePointAt(0);
              return fc === 0x1F534; // 🔴
            }).map((h) => h.name);

            const lowItems = report.historical.filter((h) => {
              const fc = h.judgment.codePointAt(0);
              return fc === 0x1F7E2; // 🟢
            }).map((h) => h.name);

            if (highItems.length === 0 && lowItems.length === 0) return null;

            return (
              <div className="bg-surface-container rounded-xl p-6 ghost-border mt-6">
                <h4 className="text-lg font-serif text-primary mb-4">장기 추세 종합 판단</h4>
                {highItems.length > 0 && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-2 h-2 rounded-full bg-[#ffb4ab] shrink-0" />
                    <p className="text-base text-on-surface-variant">
                      <span className="text-on-surface font-medium">역사적 고점 부근:</span>{" "}
                      {highItems.join(", ")}
                    </p>
                  </div>
                )}
                {lowItems.length > 0 && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-2 h-2 rounded-full bg-[#95d3ba] shrink-0" />
                    <p className="text-base text-on-surface-variant">
                      <span className="text-on-surface font-medium">역사적 저점 부근:</span>{" "}
                      {lowItems.join(", ")}
                    </p>
                  </div>
                )}
                <p className="text-base text-on-surface-variant mt-4 leading-relaxed border-l-2 border-primary/20 pl-4">
                  {highItems.length >= 3
                    ? "다수의 지표가 역사적 고점 부근에 있어 과열 또는 인플레이션 재점화 리스크가 존재합니다. 포트폴리오 리스크 관리에 유의해야 합니다."
                    : highItems.length >= 1
                      ? "일부 지표가 역사적 고점 부근에 있습니다. 해당 자산군의 밸류에이션 부담을 점검하세요."
                      : "대부분의 지표가 역사적 중간 또는 저점 범위에 있어 극단적 리스크 신호는 감지되지 않습니다."}
                </p>
              </div>
            );
          })()}
        </section>
      )}
    </div>
  );
}
