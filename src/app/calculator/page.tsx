import fs from "fs";
import path from "path";
import { MarkdownText } from "@/components/MarkdownText";

interface Metric {
  value: number | null;
  unit: string;
  label: string;
  description: string;
  judgment?: string;
}

interface StockData {
  code: string;
  name: string;
  price: number;
  basis: string;
  metrics: Record<string, Metric>;
}

interface CalculatorData {
  generated_at: string;
  source: string;
  stocks: StockData[];
}

function getCalculatorData(): CalculatorData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "calculator.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as CalculatorData;
  } catch {
    return null;
  }
}

function getJudgmentColor(judgment?: string): string {
  if (!judgment) return "#909097";
  const firstChar = judgment.codePointAt(0);
  if (firstChar === 0x1F534) return "#ffb4ab"; // 🔴
  if (firstChar === 0x1F7E1) return "#e9c176"; // 🟡
  if (firstChar === 0x1F7E2) return "#95d3ba"; // 🟢
  if (firstChar === 0x1F535) return "#6ea8fe"; // 🔵
  return "#909097";
}

function cleanJudgment(judgment?: string): string {
  if (!judgment) return "";
  return judgment.replace(/^(\u{1F534}|\u{1F7E1}|\u{1F7E2}|\u{1F535}|\u{26AA})\s*/u, "");
}

export default function CalculatorPage() {
  const data = getCalculatorData();

  if (!data) {
    return (
      <div className="py-20">
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">Financial Calculator</p>
        <h2 className="text-4xl font-serif font-bold text-on-surface tracking-tight mb-4">재무지표 계산기</h2>
        <div className="bg-surface-container-low rounded-xl p-8 ghost-border text-center">
          <p className="text-on-surface-variant">데이터가 아직 생성되지 않았습니다.</p>
        </div>
      </div>
    );
  }

  const metricKeys = ["PER", "PBR", "ROE", "EPS", "BPS", "부채비율", "영업이익률"];

  return (
    <div className="space-y-12">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Financial Calculator
        </p>
        <h2 className="text-4xl font-serif font-bold text-on-surface tracking-tight">
          재무지표 계산기
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          {data.generated_at} 기준 · 데이터 소스: {data.source === "sample" ? "샘플 데이터 (DART API 연동 전)" : "DART 공시"}
        </p>
      </section>

      {/* Ranking */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
          종합 투자 매력도 순위
        </h3>
        <p className="text-sm text-on-surface-variant mb-6">
          PER, PBR, ROE, 부채비율, 영업이익률을 종합한 점수 (100점 만점)
        </p>

        <div className="space-y-4">
          {data.stocks.map((stock, rank) => {
            const score = stock.metrics["종합점수"];
            const scoreColor = getJudgmentColor(score?.judgment);
            const scoreWidth = Math.max(0, Math.min(100, score?.value || 0));

            return (
              <div key={stock.code} className="bg-surface-container-low rounded-xl p-6 ghost-border">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <span
                      className="text-2xl font-serif font-bold w-8"
                      style={{ color: scoreColor }}
                    >
                      {rank + 1}
                    </span>
                    <div>
                      <h4 className="text-lg font-medium text-on-surface">{stock.name}</h4>
                      <p className="text-sm text-on-surface-variant">{stock.code} · {stock.price.toLocaleString()}원</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-3xl font-serif font-bold" style={{ color: scoreColor }}>
                      {score?.value}
                    </span>
                    <span className="text-base text-on-surface-variant ml-1">점</span>
                  </div>
                </div>

                {/* Score Bar */}
                <div className="mb-4">
                  <div className="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${scoreWidth}%`, backgroundColor: scoreColor }}
                    />
                  </div>
                  <p className="text-xs mt-1.5" style={{ color: scoreColor }}>
                    {cleanJudgment(score?.judgment)}
                  </p>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {metricKeys.map((key) => {
                    const m = stock.metrics[key];
                    if (!m || m.value === null) return null;
                    const color = getJudgmentColor(m.judgment);

                    return (
                      <div key={key} className="bg-surface-container/50 rounded-lg p-3">
                        <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
                          {m.label}
                        </p>
                        <p className="text-lg font-mono text-on-surface">
                          {typeof m.value === "number" ? m.value.toLocaleString() : m.value}
                          <span className="text-xs text-on-surface-variant ml-0.5">{m.unit}</span>
                        </p>
                        {m.judgment && (
                          <div className="flex items-center gap-1.5 mt-1.5">
                            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                            <p className="text-[10px] leading-tight" style={{ color }}>
                              {cleanJudgment(m.judgment)}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Basis */}
                <p className="text-[10px] text-on-surface-variant/40 mt-3">
                  데이터 기준: {stock.basis}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Legend */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <h3 className="text-base font-serif text-on-surface mb-4">지표 해석 가이드</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-on-surface font-medium mb-2">수익성 지표</p>
            <div className="space-y-2 text-on-surface-variant">
              <p><strong className="text-on-surface">EPS</strong> (주당순이익) — 1주당 벌어들이는 순이익. 높을수록 좋음.</p>
              <p><strong className="text-on-surface">ROE</strong> (자기자본이익률) — 자본 대비 순이익. 10% 이상이면 양호.</p>
              <p><strong className="text-on-surface">영업이익률</strong> — 매출 대비 영업이익. 본업의 수익성.</p>
            </div>
          </div>
          <div>
            <p className="text-on-surface font-medium mb-2">가치평가 지표</p>
            <div className="space-y-2 text-on-surface-variant">
              <p><strong className="text-on-surface">PER</strong> (주가수익비율) — 주가 ÷ EPS. 낮을수록 이익 대비 저평가.</p>
              <p><strong className="text-on-surface">PBR</strong> (주가순자산비율) — 주가 ÷ BPS. 1 미만이면 자산 대비 저평가.</p>
              <p><strong className="text-on-surface">부채비율</strong> — 부채 ÷ 자본. 100% 이하가 안정적.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
