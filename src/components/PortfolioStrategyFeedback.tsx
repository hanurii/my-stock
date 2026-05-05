"use client";

interface Holding {
  code: string;
  name: string;
  eval_amount: number;
  category?: "dividend" | "growth" | "etf" | "etf_index" | "etf_hot";
}

interface TargetStrategy {
  dividend: number;
  growth?: number;
  etf_index?: number;
  etf_hot?: number;
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
  etf_index: "KOSPI 추종 ETF",
  etf_hot: "핫섹터 ETF",
  uncategorized: "미분류",
};

const CATEGORY_COLOR: Record<string, string> = {
  dividend: "#d4b483",
  growth: "#6ea8fe",
  etf: "#95d3ba",
  etf_index: "#95d3ba",
  etf_hot: "#c89dd9",
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

  // 카테고리별 집계 (legacy "etf"는 etf_index로 합산)
  const categoryTotals: Record<string, number> = {
    dividend: 0,
    growth: 0,
    etf_index: 0,
    etf_hot: 0,
    uncategorized: 0,
  };
  const categoryHoldings: Record<string, Holding[]> = {
    dividend: [],
    growth: [],
    etf_index: [],
    etf_hot: [],
    uncategorized: [],
  };
  for (const h of holdings) {
    let cat = h.category || "uncategorized";
    if (cat === "etf") cat = "etf_index"; // backward compat
    categoryTotals[cat] = (categoryTotals[cat] || 0) + h.eval_amount;
    categoryHoldings[cat].push(h);
  }

  const dividendPct = (categoryTotals.dividend / totalEval) * 100;
  const growthPct = (categoryTotals.growth / totalEval) * 100;
  const etfIndexPct = (categoryTotals.etf_index / totalEval) * 100;
  const etfHotPct = (categoryTotals.etf_hot / totalEval) * 100;
  const uncategorizedPct = (categoryTotals.uncategorized / totalEval) * 100;

  const targetDividendPct = (targetStrategy.dividend ?? 0) * 100;
  const targetGrowthPct = (targetStrategy.growth ?? 0) * 100;
  const targetEtfIndexPct = (targetStrategy.etf_index ?? 0) * 100;
  const targetEtfHotPct = (targetStrategy.etf_hot ?? 0) * 100;

  const dividendDeviation = dividendPct - targetDividendPct;
  const growthDeviation = growthPct - targetGrowthPct;
  const etfIndexDeviation = etfIndexPct - targetEtfIndexPct;
  const etfHotDeviation = etfHotPct - targetEtfHotPct;

  // 단일 종목 집중도
  const concentratedStocks = holdings
    .map((h) => ({
      ...h,
      weightPct: (h.eval_amount / totalEval) * 100,
    }))
    .filter((h) => h.weightPct > SINGLE_STOCK_LIMIT_PCT)
    .sort((a, b) => b.weightPct - a.weightPct);

  const cashPct = totalAssets > 0 ? (cash / totalAssets) * 100 : 0;

  // 상태 결정
  const maxConcentration =
    concentratedStocks.length > 0 ? concentratedStocks[0].weightPct : 0;
  const maxAbsDeviation = Math.max(
    Math.abs(dividendDeviation),
    Math.abs(growthDeviation),
    Math.abs(etfIndexDeviation),
    Math.abs(etfHotDeviation),
  );

  let status: Status = "ok";
  if (maxConcentration > SINGLE_STOCK_WARN_PCT || maxAbsDeviation > 30) {
    status = "danger";
  } else if (maxConcentration > SINGLE_STOCK_LIMIT_PCT || maxAbsDeviation > 15) {
    status = "warn";
  }

  // 한 줄 진단 (가장 큰 편차 우선)
  let headline = "포트폴리오가 목표 전략과 잘 일치합니다.";
  if (status === "danger") {
    if (maxConcentration > SINGLE_STOCK_WARN_PCT) {
      headline = `단일 종목 집중도 위험: ${concentratedStocks[0].name} ${concentratedStocks[0].weightPct.toFixed(1)}%`;
    } else if (growthDeviation > 30) {
      headline = `성장주 비중이 목표 대비 +${growthDeviation.toFixed(0)}%p 초과 — 즉시 정리 권고`;
    } else if (dividendDeviation < -30) {
      headline = `배당주 비중이 목표 대비 ${dividendDeviation.toFixed(0)}%p 미달 — 즉시 보강 권고`;
    } else if (etfIndexDeviation < -30) {
      headline = `KOSPI ETF 비중이 목표 대비 ${etfIndexDeviation.toFixed(0)}%p 미달 — 즉시 보강 권고`;
    } else if (etfHotDeviation > 30) {
      headline = `핫섹터 ETF 비중이 목표 대비 +${etfHotDeviation.toFixed(0)}%p 초과 — 즉시 축소 권고`;
    }
  } else if (status === "warn") {
    if (growthDeviation > 15) {
      headline = `성장주 비중이 목표 대비 +${growthDeviation.toFixed(0)}%p 초과 — 점진적 정리 필요`;
    } else if (dividendDeviation < -15) {
      headline = `배당주 비중이 목표 대비 ${dividendDeviation.toFixed(0)}%p 미달 — 점진적 보강 필요`;
    } else if (etfIndexDeviation < -15) {
      headline = `KOSPI ETF 비중이 목표 대비 ${etfIndexDeviation.toFixed(0)}%p 미달 — 점진적 보강 필요`;
    } else if (etfHotDeviation < -15) {
      headline = `핫섹터 ETF 비중이 목표 대비 ${etfHotDeviation.toFixed(0)}%p 미달 — 분기 진입 룰에 따라 보강 가능`;
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
      `${stock.name} 비중을 ${SINGLE_STOCK_LIMIT_PCT}% 이하로 축소 (약 ${formatMoney(trimAmount)}원 일부 매도 시 비중 ${SINGLE_STOCK_LIMIT_PCT}% 도달)`,
    );
  }
  if (dividendDeviation < -10) {
    const needed = ((targetDividendPct - dividendPct) / 100) * totalEval;
    recommendations.push(
      `배당주 비중 회복을 위해 약 ${formatMoney(needed)}원 추가 매수 또는 다른 카테고리에서 전환 필요 (한국 + 미국 배당주 혼합)`,
    );
  }
  if (growthDeviation > 10) {
    const excess = ((growthPct - targetGrowthPct) / 100) * totalEval;
    recommendations.push(
      `성장주 약 ${formatMoney(excess)}원을 분할 매도해 배당주/ETF로 전환 (한 번에 처분하지 말고 6~12개월 분할)`,
    );
  }
  if (etfIndexDeviation < -10) {
    const needed = ((targetEtfIndexPct - etfIndexPct) / 100) * totalEval;
    recommendations.push(
      `KOSPI 추종 ETF 약 ${formatMoney(needed)}원 추가 매수 (TIGER 200, KODEX 200 등)`,
    );
  }
  if (etfHotDeviation > 10) {
    recommendations.push(
      `핫섹터 ETF 비중 초과 — 익절 룰(+20/+30/트레일링) 또는 시간 손절(6개월) 점검 필요`,
    );
  }
  if (cashPct < 3 && totalAssets > 0) {
    recommendations.push(
      `현금 비중 ${cashPct.toFixed(1)}% — 비상금 및 매수 여력 확보를 위해 일부 익절·배당 적립 권고`,
    );
  }
  if (recommendations.length === 0) {
    recommendations.push("현재 비중을 유지하면서 분기 1회 리밸런싱 점검");
  }

  // 표시할 카테고리 행 (목표가 있는 카테고리 + 미분류만)
  type Row = {
    key: string;
    pct: number;
    target: number | null;
    deviation: number | null;
    amount: number;
    holdings: Holding[];
  };

  const rows: Row[] = [
    {
      key: "dividend",
      pct: dividendPct,
      target: targetDividendPct,
      deviation: dividendDeviation,
      amount: categoryTotals.dividend,
      holdings: categoryHoldings.dividend,
    },
    {
      key: "etf_index",
      pct: etfIndexPct,
      target: targetEtfIndexPct,
      deviation: etfIndexDeviation,
      amount: categoryTotals.etf_index,
      holdings: categoryHoldings.etf_index,
    },
    {
      key: "etf_hot",
      pct: etfHotPct,
      target: targetEtfHotPct,
      deviation: etfHotDeviation,
      amount: categoryTotals.etf_hot,
      holdings: categoryHoldings.etf_hot,
    },
  ];
  // 성장주는 목표가 0이거나 없을 때 "전환 대상"으로 별도 표시
  if (categoryTotals.growth > 0 || (targetStrategy.growth ?? 0) > 0) {
    rows.push({
      key: "growth",
      pct: growthPct,
      target: targetGrowthPct,
      deviation: growthDeviation,
      amount: categoryTotals.growth,
      holdings: categoryHoldings.growth,
    });
  }
  if (uncategorizedPct > 0) {
    rows.push({
      key: "uncategorized",
      pct: uncategorizedPct,
      target: null,
      deviation: null,
      amount: categoryTotals.uncategorized,
      holdings: categoryHoldings.uncategorized,
    });
  }

  return (
    <div className="bg-surface-container-low rounded-xl ghost-border p-6 sm:p-8 mb-8">
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-1.5">
            전략 점검
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

      {/* 카테고리 비중: 현재 vs 목표 + 종목 리스트 */}
      <div className="mb-6">
        <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-3">
          카테고리 비중 (주식 평가액 기준)
        </p>
        <div className="space-y-4">
          {rows.map((r) => {
            const color = CATEGORY_COLOR[r.key];
            const label = CATEGORY_LABEL[r.key];
            const hasTarget = r.target != null;
            const isOver = r.deviation != null && r.deviation > 5;
            const isUnder = r.deviation != null && r.deviation < -5;
            const isGrowthOverTarget0 =
              r.key === "growth" && (targetStrategy.growth ?? 0) === 0 && r.pct > 0;
            return (
              <div key={r.key}>
                <div className="flex items-baseline justify-between mb-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-sm font-medium text-on-surface">
                      {label}
                    </span>
                    {isGrowthOverTarget0 && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                        style={{
                          backgroundColor: "#ffb4ab20",
                          color: "#ffb4ab",
                        }}
                      >
                        전환 대상
                      </span>
                    )}
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
                  {hasTarget && r.target != null && r.target > 0 && (
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
                {/* 종목 리스트 (작은 글씨) */}
                {r.holdings.length > 0 && (
                  <p className="text-[11px] text-on-surface-variant/50 mt-1.5 leading-relaxed">
                    {[...r.holdings]
                      .sort((a, b) => b.eval_amount - a.eval_amount)
                      .map((h) => {
                        const w = ((h.eval_amount / totalEval) * 100).toFixed(1);
                        return `${h.name} (${w}%)`;
                      })
                      .join(" · ")}
                  </p>
                )}
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

      {/* 핫섹터 ETF 매매 룰 */}
      <div className="mb-6 rounded-xl p-5" style={{ backgroundColor: "#c89dd910" }}>
        <div className="flex items-center gap-2 mb-3">
          <span
            className="material-symbols-outlined text-base"
            style={{ color: "#c89dd9" }}
          >
            rule
          </span>
          <p className="text-xs uppercase tracking-wider" style={{ color: "#c89dd9" }}>
            핫섹터 ETF 매매 룰 (20% 슬롯 전용)
          </p>
        </div>
        <p className="text-[11px] text-on-surface-variant/60 mb-4 leading-relaxed">
          이 슬롯은 수익 극대화가 아니라 FOMO 통제용. 룰은 진입 전 명문화하고, 장중 결정 금지. 평일은 알림만, 결정은 주말에.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="bg-surface-container/40 rounded-lg p-3">
            <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
              ① 손절선 (필수)
            </p>
            <p className="text-sm text-on-surface font-medium">진입가 대비 -15%</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-1 leading-relaxed">
              도달 시 무조건 매도. 예외 없음. 익절선만으로는 "조금만 더" 함정.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-3">
            <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
              ② 익절선 (분할)
            </p>
            <p className="text-sm text-on-surface font-medium">+20% / +30% / 트레일링</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-1 leading-relaxed">
              +20% 1/3 매도, +30% 1/3 매도, 잔량은 고점 대비 -10% 도달 시 매도.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-3">
            <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
              ③ 시간 손절
            </p>
            <p className="text-sm text-on-surface font-medium">6개월 내 +5% 미달 시 정리</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-1 leading-relaxed">
              모멘텀 사라진 신호. 자본 회수해 다른 슬롯에 배치.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-3">
            <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
              ④ 비중 상한 (절대 룰)
            </p>
            <p className="text-sm text-on-surface font-medium">전체 자산의 20% 초과 금지</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-1 leading-relaxed">
              수익으로 25% 도달 시 5%p 즉시 매도. "잘 가니 더 넣자" 금지.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-3 sm:col-span-2">
            <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
              ⑤ 진입 룰
            </p>
            <p className="text-sm text-on-surface font-medium">분기 1회 검토 (3·6·9·12월 첫 주말)</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-1 leading-relaxed">
              6개월 모멘텀 양수일 때만 진입. 3분할 매수 (1차 50% → 1개월 후 25% → 다시 1개월 후 25%). 평일 장중 진입 금지.
            </p>
          </div>
        </div>
      </div>

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
