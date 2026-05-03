"use client";

interface Holding {
  code: string;
  name: string;
  eval_amount: number;
  category?: "dividend" | "growth" | "etf";
}

interface TargetStrategy {
  dividend: number;
  growth: number;
  description?: string;
}

interface Props {
  holdings: Holding[];
  cash: number;
  totalAssets: number;
  targetStrategy?: TargetStrategy;
}

const CATEGORY_LABEL: Record<string, string> = {
  dividend: "배당주",
  growth: "성장주",
  etf: "ETF",
  uncategorized: "미분류",
};

const CATEGORY_COLOR: Record<string, string> = {
  dividend: "#d4b483",
  growth: "#6ea8fe",
  etf: "#95d3ba",
  uncategorized: "#9ca3af",
};

const SINGLE_STOCK_LIMIT_PCT = 20;
const SINGLE_STOCK_WARN_PCT = 25;

type Status = "ok" | "warn" | "danger";

function formatMoney(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}억`;
  if (amount >= 1e4) return `${Math.round(amount / 1e4)}만`;
  return amount.toLocaleString();
}

function StatusBadge({ status }: { status: Status }) {
  const config = {
    ok: { label: "정상", color: "#95d3ba", icon: "check_circle" },
    warn: { label: "주의", color: "#d4b483", icon: "warning" },
    danger: { label: "경고", color: "#ffb4ab", icon: "error" },
  }[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold"
      style={{ backgroundColor: `${config.color}20`, color: config.color }}
    >
      <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>
        {config.icon}
      </span>
      {config.label}
    </span>
  );
}

export function PortfolioStrategyFeedback({
  holdings,
  cash,
  totalAssets,
  targetStrategy,
}: Props) {
  const totalEval = holdings.reduce((s, h) => s + h.eval_amount, 0);
  if (totalEval === 0 || !targetStrategy) return null;

  // 카테고리별 집계
  const categoryTotals: Record<string, number> = {
    dividend: 0,
    growth: 0,
    etf: 0,
    uncategorized: 0,
  };
  for (const h of holdings) {
    const cat = h.category || "uncategorized";
    categoryTotals[cat] = (categoryTotals[cat] || 0) + h.eval_amount;
  }

  const dividendPct = (categoryTotals.dividend / totalEval) * 100;
  const growthPct = (categoryTotals.growth / totalEval) * 100;
  const etfPct = (categoryTotals.etf / totalEval) * 100;
  const uncategorizedPct = (categoryTotals.uncategorized / totalEval) * 100;

  const targetDividendPct = targetStrategy.dividend * 100;
  const targetGrowthPct = targetStrategy.growth * 100;

  const dividendDeviation = dividendPct - targetDividendPct; // 음수 = 미달
  const growthDeviation = growthPct - targetGrowthPct; // 양수 = 초과

  // 단일 종목 집중도
  const concentratedStocks = holdings
    .map((h) => ({
      ...h,
      weightPct: (h.eval_amount / totalEval) * 100,
    }))
    .filter((h) => h.weightPct > SINGLE_STOCK_LIMIT_PCT)
    .sort((a, b) => b.weightPct - a.weightPct);

  // 현금 비중
  const cashPct = totalAssets > 0 ? (cash / totalAssets) * 100 : 0;

  // 상태 결정
  const maxConcentration =
    concentratedStocks.length > 0 ? concentratedStocks[0].weightPct : 0;

  let status: Status = "ok";
  if (
    maxConcentration > SINGLE_STOCK_WARN_PCT ||
    Math.abs(growthDeviation) > 30 ||
    Math.abs(dividendDeviation) > 30
  ) {
    status = "danger";
  } else if (
    maxConcentration > SINGLE_STOCK_LIMIT_PCT ||
    Math.abs(growthDeviation) > 15 ||
    Math.abs(dividendDeviation) > 15
  ) {
    status = "warn";
  }

  // 한 줄 진단
  let headline = "포트폴리오가 목표 전략과 잘 일치합니다.";
  if (status === "danger") {
    if (maxConcentration > SINGLE_STOCK_WARN_PCT) {
      headline = `단일 종목 집중도 위험: ${concentratedStocks[0].name} ${concentratedStocks[0].weightPct.toFixed(1)}%`;
    } else if (growthDeviation > 30) {
      headline = `성장주 비중이 목표 대비 +${growthDeviation.toFixed(0)}%p 초과 — 즉시 조정 권고`;
    } else if (dividendDeviation < -30) {
      headline = `배당주 비중이 목표 대비 ${dividendDeviation.toFixed(0)}%p 미달 — 즉시 조정 권고`;
    }
  } else if (status === "warn") {
    if (growthDeviation > 15) {
      headline = `성장주 비중이 목표 대비 +${growthDeviation.toFixed(0)}%p 초과 — 점진적 조정 필요`;
    } else if (dividendDeviation < -15) {
      headline = `배당주 비중이 목표 대비 ${dividendDeviation.toFixed(0)}%p 미달 — 점진적 조정 필요`;
    } else if (maxConcentration > SINGLE_STOCK_LIMIT_PCT) {
      headline = `${concentratedStocks[0].name} 단일 비중 ${concentratedStocks[0].weightPct.toFixed(1)}% — 분산 권고`;
    }
  }

  // 권고 액션 생성
  const recommendations: string[] = [];
  for (const stock of concentratedStocks) {
    const excess = stock.weightPct - SINGLE_STOCK_LIMIT_PCT;
    const trimAmount = (excess / 100) * totalEval;
    recommendations.push(
      `${stock.name} 비중을 ${SINGLE_STOCK_LIMIT_PCT}% 이하로 트리밍 (약 ${formatMoney(trimAmount)}원 매도 시 비중 ${SINGLE_STOCK_LIMIT_PCT}% 도달)`,
    );
  }
  if (dividendDeviation < -10) {
    const needed = ((targetDividendPct - dividendPct) / 100) * totalEval;
    recommendations.push(
      `배당주 비중 회복을 위해 약 ${formatMoney(needed)}원 추가 매수 또는 다른 카테고리에서 전환 필요`,
    );
  }
  if (growthDeviation > 10) {
    recommendations.push(
      `신규 자금은 성장주가 아닌 배당주로 우선 배분`,
    );
  }
  if (cashPct < 3 && totalAssets > 0) {
    recommendations.push(
      `현금 비중 ${cashPct.toFixed(1)}% — 비상금 및 매수 여력 확보를 위해 일부 익절·배당 적립 권고`,
    );
  }
  if (recommendations.length === 0) {
    recommendations.push("현재 비중을 유지하면서 정기적으로 점검");
  }

  // 표시할 카테고리 행
  const rows = [
    {
      key: "dividend",
      pct: dividendPct,
      target: targetDividendPct,
      deviation: dividendDeviation,
      amount: categoryTotals.dividend,
    },
    {
      key: "growth",
      pct: growthPct,
      target: targetGrowthPct,
      deviation: growthDeviation,
      amount: categoryTotals.growth,
    },
    {
      key: "etf",
      pct: etfPct,
      target: null as number | null,
      deviation: null as number | null,
      amount: categoryTotals.etf,
    },
  ];
  if (uncategorizedPct > 0) {
    rows.push({
      key: "uncategorized",
      pct: uncategorizedPct,
      target: null,
      deviation: null,
      amount: categoryTotals.uncategorized,
    });
  }

  return (
    <div className="bg-surface-container-low rounded-xl ghost-border p-6 sm:p-8 mb-8">
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-1.5">
            Strategy Check
          </p>
          <h4 className="text-xl font-serif text-on-surface tracking-tight">
            포트폴리오 전략 점검
          </h4>
          {targetStrategy.description && (
            <p className="text-xs text-on-surface-variant/60 mt-1">
              목표: {targetStrategy.description}
            </p>
          )}
        </div>
        <StatusBadge status={status} />
      </div>

      {/* 한 줄 진단 */}
      <div
        className="rounded-xl p-4 mb-6"
        style={{
          backgroundColor:
            status === "danger"
              ? "#ffb4ab15"
              : status === "warn"
                ? "#d4b48315"
                : "#95d3ba15",
        }}
      >
        <p
          className="text-base font-medium"
          style={{
            color:
              status === "danger"
                ? "#ffb4ab"
                : status === "warn"
                  ? "#d4b483"
                  : "#95d3ba",
          }}
        >
          {headline}
        </p>
      </div>

      {/* 카테고리 비중: 현재 vs 목표 */}
      <div className="mb-6">
        <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-3">
          카테고리 비중 (주식 평가액 기준)
        </p>
        <div className="space-y-3">
          {rows.map((r) => {
            const color = CATEGORY_COLOR[r.key];
            const label = CATEGORY_LABEL[r.key];
            const hasTarget = r.target != null;
            const isOver = r.deviation != null && r.deviation > 5;
            const isUnder = r.deviation != null && r.deviation < -5;
            return (
              <div key={r.key}>
                <div className="flex items-baseline justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-sm font-medium text-on-surface">
                      {label}
                    </span>
                    <span className="text-xs text-on-surface-variant/50 font-mono">
                      {formatMoney(r.amount)}원
                    </span>
                  </div>
                  <div className="flex items-baseline gap-3">
                    <span
                      className="text-base font-mono font-bold"
                      style={{ color }}
                    >
                      {r.pct.toFixed(1)}%
                    </span>
                    {hasTarget && (
                      <span className="text-xs text-on-surface-variant/50 font-mono">
                        목표 {r.target}%
                      </span>
                    )}
                    {hasTarget && r.deviation != null && (
                      <span
                        className="text-xs font-mono"
                        style={{
                          color: isOver
                            ? "#ffb4ab"
                            : isUnder
                              ? "#ffb4ab"
                              : "#95d3ba",
                        }}
                      >
                        {r.deviation > 0 ? "+" : ""}
                        {r.deviation.toFixed(1)}%p
                      </span>
                    )}
                  </div>
                </div>
                {/* 진행 바 */}
                <div className="relative h-2 bg-surface-container/50 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(r.pct, 100)}%`,
                      backgroundColor: color,
                    }}
                  />
                  {hasTarget && r.target != null && (
                    <div
                      className="absolute top-[-2px] bottom-[-2px] w-0.5"
                      style={{
                        left: `${r.target}%`,
                        backgroundColor: "#ffffff80",
                      }}
                      title={`목표 ${r.target}%`}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 단일 종목 집중도 */}
      {concentratedStocks.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span
              className="material-symbols-outlined text-base"
              style={{ color: "#ffb4ab" }}
            >
              warning
            </span>
            <p className="text-xs uppercase tracking-wider text-on-surface-variant/50">
              단일 종목 집중도 (한도 {SINGLE_STOCK_LIMIT_PCT}% 초과)
            </p>
          </div>
          <div className="space-y-2">
            {concentratedStocks.map((s) => (
              <div
                key={s.code}
                className="flex items-center justify-between p-3 rounded-xl"
                style={{ backgroundColor: "#ffb4ab10" }}
              >
                <div>
                  <p className="text-sm font-medium text-on-surface">
                    {s.name}
                    <span className="text-xs text-on-surface-variant/50 ml-2 font-mono">
                      {s.code}
                    </span>
                  </p>
                  <p className="text-xs text-on-surface-variant/60 mt-0.5">
                    한도 +{(s.weightPct - SINGLE_STOCK_LIMIT_PCT).toFixed(1)}%p
                    초과
                  </p>
                </div>
                <p
                  className="text-xl font-mono font-bold"
                  style={{ color: "#ffb4ab" }}
                >
                  {s.weightPct.toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 권고 액션 */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span
            className="material-symbols-outlined text-base text-primary"
          >
            lightbulb
          </span>
          <p className="text-xs uppercase tracking-wider text-on-surface-variant/50">
            권고 액션
          </p>
        </div>
        <ul className="space-y-2">
          {recommendations.map((rec, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-sm text-on-surface-variant leading-relaxed"
            >
              <span className="text-primary-dim mt-1">•</span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
