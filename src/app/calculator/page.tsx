import fs from "fs";
import path from "path";
import { Collapsible } from "@/components/Collapsible";

interface QuarterlyData {
  quarter: string;
  eps: number;
  revenue: number;
  operating_income: number;
  net_income: number;
  op_margin: number;
}

interface YearlyData {
  year: number;
  eps: number;
  dps: number;
  bps: number;
  payout_ratio: number;
  per: number;
  pbr: number;
  revenue: number;
  operating_income: number;
  net_income: number;
  op_margin: number;
}

interface StockData {
  code: string;
  name: string;
  is_preferred: boolean;
  current_price: number;
  quarterly?: QuarterlyData[];
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
        <p className="text-on-surface-variant text-base">calculator.json이 아직 생성되지 않았습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Financial Statements
        </p>
        <h2 className="text-4xl font-serif font-bold text-on-surface tracking-tight">
          재무제표
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          {data.generated_at} 기준 · DART 공시 데이터 기반
        </p>
        <p className="text-sm text-on-surface-variant/60 mt-1">
          실적 발표 직후 최신 EPS로 PER을 계산합니다. 증권사 반영 전에 먼저 확인하세요.
        </p>
      </section>

      {/* 목차 */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <h3 className="text-base font-serif text-on-surface mb-4">목차</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {data.stocks.map((stock) => (
            <a
              key={stock.code}
              href={`#stock-${stock.code}`}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-container-high/50 transition-colors group"
            >
              <span className="text-primary-dim/40 group-hover:text-primary transition-colors text-sm">→</span>
              <span className="text-base text-on-surface group-hover:text-primary transition-colors">
                {stock.name}
              </span>
              {stock.is_preferred && (
                <span className="text-[10px] text-primary/50">우선주</span>
              )}
            </a>
          ))}
        </div>
      </section>

      {/* Stock Cards */}
      {data.stocks.map((stock) => {
        const sortedHistory = [...stock.history]
          .filter((h) => h.eps || h.dps || h.bps)
          .sort((a, b) => b.year - a.year);

        return (
          <section
            key={stock.code}
            id={`stock-${stock.code}`}
            className="bg-surface-container-low rounded-xl ghost-border overflow-hidden scroll-mt-8"
          >
            {/* ── Stock Header ── */}
            <div className="p-8 flex justify-between items-start">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="text-2xl font-serif text-on-surface tracking-tight">{stock.name}</h3>
                  {stock.is_preferred && (
                    <span className="text-xs uppercase tracking-wider bg-primary/10 text-primary px-2.5 py-1 rounded">
                      우선주
                    </span>
                  )}
                </div>
                <p className="text-base text-on-surface-variant mt-1.5">{stock.code}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-on-surface-variant/50 mb-1">현재 종가</p>
                <p className="text-4xl font-serif text-primary tracking-tight">
                  {stock.current_price.toLocaleString()}
                  <span className="text-lg text-on-surface-variant ml-1">원</span>
                </p>
              </div>
            </div>

            {/* ── Latest Metrics ── */}
            <div className="px-8 pb-8">
              <div className="flex items-center gap-2 mb-5">
                <h4 className="text-lg font-serif text-primary">최신 지표</h4>
                <span className="text-sm text-on-surface-variant">
                  — {stock.latest.basis_year}년 사업보고서 기준
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                {[
                  { label: "EPS", value: stock.latest.eps, unit: "원", desc: "주당순이익" },
                  { label: "PER", value: stock.latest.per, unit: "배", desc: "현재 주가 ÷ EPS" },
                  { label: "BPS", value: stock.latest.bps, unit: "원", desc: "주당순자산" },
                  { label: "PBR", value: stock.latest.pbr, unit: "배", desc: "현재 주가 ÷ BPS" },
                  { label: "배당수익률", value: stock.latest.dividend_yield, unit: "%", desc: "배당금 ÷ 현재 주가" },
                  { label: "주당배당금", value: stock.latest.dps, unit: "원", desc: "확정 배당" },
                ].map((m) => (
                  <div key={m.label} className="bg-surface-container rounded-xl p-5 ghost-border">
                    <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">{m.label}</p>
                    <p className="text-2xl font-mono text-on-surface leading-tight">
                      {m.value != null ? m.value.toLocaleString() : "—"}
                      <span className="text-sm text-on-surface-variant ml-1">{m.unit}</span>
                    </p>
                    <p className="text-xs text-on-surface-variant/40 mt-2">{m.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* ── 연도별 전체 추이 (접기/펼치기) ── */}
            {sortedHistory.length > 0 && (
              <div className="px-8 pb-8">
                <Collapsible title="연도별 전체 추이">
                  <div className="overflow-x-auto">
                    <table className="w-full text-base">
                      <thead>
                        <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                          <th className="text-left px-4 pb-3 font-normal">연도</th>
                          <th className="text-right px-4 pb-3 font-normal">매출</th>
                          <th className="text-right px-4 pb-3 font-normal">영업이익</th>
                          <th className="text-right px-4 pb-3 font-normal">영업이익률</th>
                          <th className="text-right px-4 pb-3 font-normal">EPS</th>
                          <th className="text-right px-4 pb-3 font-normal">배당금</th>
                          <th className="text-right px-4 pb-3 font-normal">배당성향</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sortedHistory.map((h, i) => (
                          <tr
                            key={h.year}
                            className={`transition-colors ${
                              i === 0 ? "bg-primary/5 hover:bg-primary/10" : "hover:bg-surface-container/30"
                            }`}
                          >
                            <td className={`px-4 py-3 font-medium ${i === 0 ? "text-primary" : "text-on-surface"}`}>
                              {h.year}
                              {i === 0 && <span className="text-xs text-primary/60 ml-2">최신</span>}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.revenue ? `${(h.revenue / 1e8).toLocaleString(undefined, { maximumFractionDigits: 0 })}억` : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.operating_income ? `${(h.operating_income / 1e8).toLocaleString(undefined, { maximumFractionDigits: 0 })}억` : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.op_margin ? `${h.op_margin}%` : "—"}
                            </td>
                            <td className={`px-4 py-3 text-right font-mono ${h.eps > 0 ? "text-on-surface" : h.eps < 0 ? "text-[#ffb4ab]" : "text-on-surface-variant/40"}`}>
                              {h.eps ? h.eps.toLocaleString() : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface">
                              {h.dps ? h.dps.toLocaleString() : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.payout_ratio ? `${h.payout_ratio}%` : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Collapsible>
              </div>
            )}
          </section>
        );
      })}

      {/* Guide */}
      <section className="bg-surface-container-low rounded-xl p-8 ghost-border">
        <h3 className="text-lg font-serif text-on-surface mb-5">사용 가이드</h3>
        <div className="space-y-4 text-base text-on-surface-variant leading-relaxed">
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
