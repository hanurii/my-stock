import { getForeignFlowData, type TrendLabel } from "@/lib/foreign-flow";
import { ForeignFlowMarketChart } from "@/components/ForeignFlowMarketChart";
import { ForeignFlowSectorBars } from "@/components/ForeignFlowSectorBars";

export const dynamic = "force-static";

function formatBillion(v: number): string {
  const sign = v >= 0 ? "+" : "−";
  const abs = Math.abs(v);
  if (abs >= 10000) return `${sign}${(abs / 10000).toFixed(2)}조`;
  if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(1)}천억`;
  return `${sign}${Math.round(abs)}억`;
}

function trendColor(trend: TrendLabel): string {
  if (trend === "강한 매수" || trend === "매수 우위") return "text-primary";
  if (trend === "강한 매도" || trend === "매도 우위") return "text-error";
  return "text-on-surface-variant";
}

function SummaryCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: string;
}) {
  return (
    <div className="glass-card rounded-lg ghost-border p-4 sm:p-5">
      <p className="text-[11px] uppercase tracking-[0.18em] text-on-surface-variant mb-2">
        {label}
      </p>
      <p className={`text-xl sm:text-2xl font-serif tracking-tight ${highlight ?? "text-on-surface"}`}>
        {value}
      </p>
      {sub ? <p className="text-xs text-on-surface-variant mt-1">{sub}</p> : null}
    </div>
  );
}

export default function ForeignFlowPage() {
  const data = getForeignFlowData();

  if (!data) {
    return (
      <div className="space-y-8">
        <header>
          <h1 className="text-3xl sm:text-4xl font-serif text-primary tracking-tight">
            외인 자본 흐름
          </h1>
          <p className="text-sm text-on-surface-variant mt-2">
            한국 시장 외국인 투자자 자금 추세
          </p>
        </header>
        <section className="glass-card rounded-xl ghost-border p-6 text-on-surface-variant">
          데이터가 아직 수집되지 않았습니다. <code>scripts/fetch-foreign-flow.ts</code>를 실행해 주세요.
        </section>
      </div>
    );
  }

  const { meta, market, sectors } = data;
  const lastDate =
    market.daily.length > 0 ? market.daily[market.daily.length - 1].date : "—";
  const accumulatedDays = market.daily.length;
  const sectorAvailableDays = new Set(sectors.daily.map((p) => p.date)).size;

  return (
    <div className="space-y-10 sm:space-y-14">
      {/* Header */}
      <header>
        <h1 className="text-3xl sm:text-4xl font-serif text-primary tracking-tight">
          외인 자본 흐름
        </h1>
        <p className="text-sm text-on-surface-variant mt-2">
          한국 시장 외국인 투자자 자금 추세 · 최근 영업일 <span className="text-on-surface">{lastDate}</span>
        </p>
        <p className="text-[11px] text-on-surface-variant/70 mt-1">
          데이터 출처: Naver Finance Mobile API · 갱신: {meta.last_updated} (KST)
        </p>
      </header>

      {/* Summary cards */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <SummaryCard
          label="20일 누적 (전체)"
          value={formatBillion(market.summary.cum_20d_billion)}
          highlight={
            market.summary.cum_20d_billion >= 0 ? "text-primary" : "text-error"
          }
          sub={`코스피 ${formatBillion(market.summary.kospi_cum_20d_billion)} · 코스닥 ${formatBillion(market.summary.kosdaq_cum_20d_billion)}`}
        />
        <SummaryCard
          label="60일 누적 (전체)"
          value={formatBillion(market.summary.cum_60d_billion)}
          highlight={
            market.summary.cum_60d_billion >= 0 ? "text-primary" : "text-error"
          }
        />
        <SummaryCard
          label="코스피 추세 (20일)"
          value={market.summary.kospi_trend_20d}
          highlight={trendColor(market.summary.kospi_trend_20d)}
        />
        <SummaryCard
          label="코스닥 추세 (20일)"
          value={market.summary.kosdaq_trend_20d}
          highlight={trendColor(market.summary.kosdaq_trend_20d)}
        />
      </section>

      {/* Market daily chart */}
      <section className="glass-card rounded-xl ghost-border p-5 sm:p-8">
        <div className="flex items-center gap-3 mb-5">
          <span className="material-symbols-outlined text-primary text-2xl">
            trending_up
          </span>
          <div>
            <h2 className="text-xl font-serif text-on-surface tracking-tight">
              일별 외인 순매수 추이
            </h2>
            <p className="text-xs text-on-surface-variant mt-0.5">
              일별 모드: 하루 순매수 금액 · 누적 모드: 기간 합산 추세
            </p>
          </div>
        </div>
        <ForeignFlowMarketChart daily={market.daily} />
        {accumulatedDays < 20 ? (
          <p className="text-[11px] text-on-surface-variant/70 mt-3 text-right">
            데이터 누적 {accumulatedDays}일째 / 목표 60일
          </p>
        ) : null}
      </section>

      {/* Sector flow */}
      <section className="glass-card rounded-xl ghost-border p-5 sm:p-8">
        <div className="flex items-start gap-3 mb-5">
          <span className="material-symbols-outlined text-primary text-2xl">
            account_tree
          </span>
          <div className="flex-1">
            <h2 className="text-xl font-serif text-on-surface tracking-tight">
              업종별 자금 흐름
            </h2>
            <p className="text-xs text-on-surface-variant mt-0.5">
              워치리스트 {meta.watchlist_stocks}종목 기준 외인 순매수 누적 (외인 순매수량 × 종가)
            </p>
          </div>
        </div>
        <ForeignFlowSectorBars
          cum20d={sectors.cum_20d}
          cum60d={sectors.cum_60d}
          availableDays={sectorAvailableDays}
        />
      </section>

      {/* Footer */}
      <footer className="text-[11px] text-on-surface-variant/70 leading-relaxed">
        ⚠️ 본 데이터는 워치리스트 종목군에 한한 외인 자금 흐름 집계로, 한국 시장 전체를 대표하지 않을 수 있습니다.
        Naver Finance에서 제공하는 일별 외인 순매수량을 기반으로 산출되며, 학습 목적의 참고 자료입니다.
        {meta.last_error ? <span className="block mt-1 text-error/70">최근 오류: {meta.last_error}</span> : null}
      </footer>
    </div>
  );
}
