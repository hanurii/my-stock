import fs from "fs";
import path from "path";
import { MarkdownText } from "@/components/MarkdownText";

interface YearlyData {
  year: number;
  eps: number;
  dps: number;
  bps: number;
  payout_ratio: number;
  per: number;
  pbr: number;
}

interface StockData {
  code: string;
  name: string;
  is_preferred: boolean;
  current_price: number;
  latest: {
    eps: number;
    per: number | null;
    bps: number;
    pbr: number | null;
    dps: number;
    dividend_yield: number | null;
    payout_ratio: number | null;
    basis_year: number;
  };
  history: YearlyData[];
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

export default function CalculatorPage() {
  const data = getCalculatorData();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
        <p className="text-on-surface-variant">calculator.json이 아직 생성되지 않았습니다.</p>
      </div>
    );
  }

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
          {data.generated_at} 기준 · DART 공시 데이터 기반
        </p>
        <p className="text-sm text-on-surface-variant/60 mt-1">
          실적 발표 직후 최신 EPS로 PER을 계산합니다. 증권사 반영 전에 먼저 확인하세요.
        </p>
      </section>

      {/* Stock Cards */}
      {data.stocks.map((stock) => (
        <section key={stock.code} className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
          {/* Stock Header */}
          <div className="p-6 flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-serif text-on-surface tracking-tight">{stock.name}</h3>
                {stock.is_preferred && (
                  <span className="text-[10px] uppercase tracking-wider bg-primary/10 text-primary px-2 py-0.5 rounded">
                    우선주
                  </span>
                )}
              </div>
              <p className="text-sm text-on-surface-variant mt-1">
                {stock.code} · {stock.latest.basis_year}년 사업보고서 기준
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-serif text-primary tracking-tight">
                {stock.current_price.toLocaleString()}
                <span className="text-base text-on-surface-variant ml-1">원</span>
              </p>
            </div>
          </div>

          {/* Latest Metrics */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-px bg-surface-container">
            {[
              { label: "최신 EPS", value: stock.latest.eps, unit: "원", desc: "주당순이익" },
              { label: "최신 PER", value: stock.latest.per, unit: "배", desc: "주가÷EPS" },
              { label: "최신 BPS", value: stock.latest.bps, unit: "원", desc: "주당순자산" },
              { label: "최신 PBR", value: stock.latest.pbr, unit: "배", desc: "주가÷BPS" },
              { label: "배당수익률", value: stock.latest.dividend_yield, unit: "%", desc: "배당÷주가" },
              { label: "주당배당금", value: stock.latest.dps, unit: "원", desc: "확정 배당" },
            ].map((m) => (
              <div key={m.label} className="bg-surface-container-low p-4">
                <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
                  {m.label}
                </p>
                <p className="text-lg font-mono text-on-surface">
                  {m.value != null ? m.value.toLocaleString() : "—"}
                  <span className="text-xs text-on-surface-variant ml-0.5">{m.unit}</span>
                </p>
                <p className="text-[10px] text-on-surface-variant/40 mt-0.5">{m.desc}</p>
              </div>
            ))}
          </div>

          {/* 10-Year History Table */}
          {stock.history.length > 0 && (
            <div className="p-6">
              <h4 className="text-sm font-serif text-on-surface mb-4">연도별 추이</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-on-surface-variant/50">
                      <th className="text-left px-3 pb-3 font-normal">연도</th>
                      <th className="text-right px-3 pb-3 font-normal">EPS (원)</th>
                      <th className="text-right px-3 pb-3 font-normal">배당금 (원)</th>
                      <th className="text-right px-3 pb-3 font-normal">배당성향 (%)</th>
                      <th className="text-right px-3 pb-3 font-normal">BPS (원)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stock.history.filter(h => h.eps || h.dps || h.bps).map((h) => (
                      <tr key={h.year} className="hover:bg-surface-container/30 transition-colors">
                        <td className="px-3 py-2 text-on-surface font-medium">{h.year}</td>
                        <td className={`px-3 py-2 text-right font-mono ${h.eps > 0 ? "text-on-surface" : h.eps < 0 ? "text-[#ffb4ab]" : "text-on-surface-variant/40"}`}>
                          {h.eps ? h.eps.toLocaleString() : "—"}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-on-surface">
                          {h.dps ? h.dps.toLocaleString() : "—"}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-on-surface-variant">
                          {h.payout_ratio ? `${h.payout_ratio}%` : "—"}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-on-surface-variant">
                          {h.bps ? h.bps.toLocaleString() : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      ))}

      {/* Guide */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <h3 className="text-base font-serif text-on-surface mb-4">사용 가이드</h3>
        <div className="space-y-3 text-sm text-on-surface-variant leading-relaxed">
          <p>
            <strong className="text-on-surface">최신 PER</strong> — 현재 주가를 가장 최근 공시된 EPS로 나눈 값입니다.
            실적 발표 직후 증권사보다 먼저 확인할 수 있습니다.
            PER이 낮을수록 이익 대비 주가가 저평가된 것입니다.
          </p>
          <p>
            <strong className="text-on-surface">배당수익률</strong> — 확정된 주당배당금을 현재 주가로 나눈 값입니다.
            은행 이자와 비교하여 투자 매력도를 판단할 수 있습니다.
          </p>
          <p>
            <strong className="text-on-surface">연도별 추이</strong> — 10년간 EPS와 배당금의 추세를 보면
            기업의 성장성과 주주환원 의지를 파악할 수 있습니다.
            EPS와 배당금이 꾸준히 늘어나는 기업이 좋은 기업입니다.
          </p>
        </div>
      </section>
    </div>
  );
}
