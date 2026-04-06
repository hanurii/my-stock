"use client";

interface DividendHolding {
  code: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  eval_amount: number;
  dps: number;
  stock_type: "common" | "preferred" | "etf";
  dividend_cycle?: "quarterly" | "annual";
  note?: string;
  next_dividend_date?: string;
  next_dividend_note?: string;
}

function formatMoney(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}억`;
  if (amount >= 1e4) return `${Math.round(amount / 1e4)}만`;
  return amount.toLocaleString();
}

function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split("-");
  return `${y}.${m}.${d}`;
}

function getDaysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

const TYPE_BADGE: Record<string, { label: string; color: string }> = {
  preferred: { label: "우선주", color: "#c084fc" },
  etf: { label: "ETF", color: "#60a5fa" },
};

export function DividendSummary({
  holdings,
  totalInvested,
  basisYear,
}: {
  holdings: DividendHolding[];
  totalInvested: number;
  basisYear: number;
}) {
  const TAX_RATE = 0.154;

  const rows = holdings
    .map((h) => {
      const annualDiv = h.dps * h.quantity;
      const yieldOnCost =
        h.avg_price > 0 ? (h.dps / h.avg_price) * 100 : 0;
      return { ...h, annualDiv, yieldOnCost };
    })
    .sort((a, b) => b.yieldOnCost - a.yieldOnCost);

  const totalAnnualDiv = rows.reduce((s, r) => s + r.annualDiv, 0);
  const afterTax = Math.round(totalAnnualDiv * (1 - TAX_RATE));
  const yieldOnInvested =
    totalInvested > 0 ? (totalAnnualDiv / totalInvested) * 100 : 0;
  const monthlyDiv = Math.round(afterTax / 12);

  return (
    <div className="space-y-6">
      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-5">
        <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
          <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">
            예상 연간 배당금
          </p>
          <p className="text-xl sm:text-2xl font-mono text-primary font-bold break-all">
            {totalAnnualDiv.toLocaleString()}
            <span className="text-sm text-on-surface-variant ml-1">원</span>
          </p>
          <p className="text-xs text-on-surface-variant/40 mt-1">
            {basisYear}년 DPS 기준 (세전)
          </p>
        </div>
        <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
          <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">
            세후 배당금
          </p>
          <p className="text-xl sm:text-2xl font-mono text-[#95d3ba] font-bold break-all">
            {afterTax.toLocaleString()}
            <span className="text-sm text-on-surface-variant ml-1">원</span>
          </p>
          <p className="text-xs text-on-surface-variant/40 mt-1">
            원천징수 15.4% 적용
          </p>
        </div>
        <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
          <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">
            투자금 대비 수익률
          </p>
          <p className="text-2xl sm:text-3xl font-mono text-on-surface font-bold">
            {yieldOnInvested.toFixed(2)}%
          </p>
        </div>
        <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
          <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">
            월평균 배당 수입
          </p>
          <p className="text-xl sm:text-2xl font-mono text-on-surface font-bold break-all">
            {monthlyDiv.toLocaleString()}
            <span className="text-sm text-on-surface-variant ml-1">원</span>
          </p>
          <p className="text-xs text-on-surface-variant/40 mt-1">세후 기준</p>
        </div>
      </div>

      {/* 종목별 배당 테이블 */}
      <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="p-6 pb-3">
          <h4 className="text-lg font-serif text-on-surface">종목별 배당 내역</h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-base">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                <th className="text-left px-6 pb-3 font-normal">종목</th>
                <th className="text-right px-4 pb-3 font-normal">수량</th>
                <th className="text-right px-4 pb-3 font-normal">DPS</th>
                <th className="text-right px-4 pb-3 font-normal">연간 배당금</th>
                <th className="text-right px-4 pb-3 font-normal">매수가 수익률</th>
                <th className="text-right px-4 pb-3 font-normal">다음 배당일</th>
                <th className="text-right px-6 pb-3 font-normal">비중</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const badge = TYPE_BADGE[r.stock_type];
                const isDimmed = r.dps === 0;
                const weightPct =
                  totalAnnualDiv > 0
                    ? ((r.annualDiv / totalAnnualDiv) * 100).toFixed(1)
                    : "0";
                const daysUntil = r.next_dividend_date
                  ? getDaysUntil(r.next_dividend_date)
                  : null;
                const isImminent = daysUntil !== null && daysUntil <= 30 && daysUntil > 0;

                return (
                  <tr
                    key={r.code}
                    className="hover:bg-surface-container/30 transition-colors"
                    style={{ opacity: isDimmed ? 0.4 : 1 }}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-on-surface">{r.name}</p>
                        {badge && (
                          <span
                            className="text-[10px] px-1.5 py-0.5 rounded font-bold"
                            style={{
                              backgroundColor: `${badge.color}20`,
                              color: badge.color,
                            }}
                          >
                            {badge.label}
                          </span>
                        )}
                      </div>
                      {r.note && (
                        <p className="text-xs text-on-surface-variant/40 mt-0.5">
                          {r.note}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-4 text-right font-mono text-on-surface">
                      {r.quantity.toLocaleString()}주
                    </td>
                    <td className="px-4 py-4 text-right font-mono text-on-surface">
                      {r.dps > 0 ? `${r.dps.toLocaleString()}원` : "-"}
                    </td>
                    <td className="px-4 py-4 text-right font-mono">
                      {r.annualDiv > 0 ? (
                        <div>
                          <p className="text-primary font-bold">{r.annualDiv.toLocaleString()}원</p>
                          {r.dividend_cycle === "quarterly" && (
                            <p className="text-xs text-on-surface-variant/50 mt-0.5">
                              회당 {Math.round(r.annualDiv / 4).toLocaleString()}원
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-primary font-bold">-</span>
                      )}
                    </td>
                    <td className="px-4 py-4 text-right font-mono text-on-surface">
                      {r.yieldOnCost > 0
                        ? `${r.yieldOnCost.toFixed(2)}%`
                        : "-"}
                    </td>
                    <td className="px-4 py-4 text-right">
                      {r.next_dividend_date ? (
                        <div>
                          <p className={`font-mono text-sm ${isImminent ? "text-primary font-bold" : "text-on-surface"}`}>
                            {formatDate(r.next_dividend_date)}
                          </p>
                          <p className="text-xs text-on-surface-variant/40 mt-0.5">
                            {r.next_dividend_note}
                            {daysUntil !== null && daysUntil > 0 && (
                              <span className={isImminent ? " text-primary" : ""}> · D-{daysUntil}</span>
                            )}
                          </p>
                        </div>
                      ) : (
                        <span className="font-mono text-on-surface-variant">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-on-surface-variant">
                      {r.annualDiv > 0 ? `${weightPct}%` : "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t border-on-surface-variant/10">
                <td className="px-6 py-4 font-serif font-medium text-on-surface">
                  합계
                </td>
                <td className="px-4 py-4" />
                <td className="px-4 py-4" />
                <td className="px-4 py-4 text-right font-mono text-primary font-bold text-lg">
                  {totalAnnualDiv.toLocaleString()}원
                </td>
                <td className="px-4 py-4 text-right font-mono text-on-surface font-bold">
                  {yieldOnInvested.toFixed(2)}%
                </td>
                <td className="px-4 py-4" />
                <td className="px-6 py-4" />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
