import fs from "fs";
import path from "path";
import { Collapsible } from "@/components/Collapsible";
import { MarkdownText } from "@/components/MarkdownText";
import { DividendSummary } from "@/components/DividendSummary";
import { PortfolioPieChart } from "@/components/PortfolioPieChart";
import { SectorPieChart } from "@/components/SectorPieChart";
import { SectorProfitTable } from "@/components/SectorProfitTable";
import { PortfolioStrategyFeedback } from "@/components/PortfolioStrategyFeedback";

interface Holding {
  code: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  profit_pct: number;
  profit_amount: number;
  eval_amount: number;
  sector?: string;
  category?: "dividend" | "growth" | "etf";
}

interface Transaction {
  id: number;
  date: string;
  type: "매수" | "매도" | "배당";
  code: string;
  name: string;
  quantity: number;
  price: number;
  total: number;
  fees?: number;
  tax?: number;
  net_amount?: number;
  reason: string;
  ai_evaluation: string;
}

interface DividendStock {
  name: string;
  dps: number;
  type: "common" | "preferred" | "etf";
  dividend_cycle?: "quarterly" | "annual";
  note?: string;
  next_dividend_date?: string;
  next_dividend_note?: string;
}

interface DividendData {
  updated_at: string;
  basis_year: number;
  stocks: Record<string, DividendStock>;
}

interface JournalData {
  updated_at: string;
  summary: {
    total_invested: number;
    total_current_value: number;
    cash?: number;
    total_assets?: number;
    realized_profit?: number;
    gross_profit?: number;
    total_fees?: number;
    total_tax?: number;
    total_cost?: number;
    net_profit?: number;
    net_profit_pct?: number;
    target_strategy?: {
      dividend: number;
      growth: number;
      description?: string;
    };
  };
  holdings: Holding[];
  transactions: Transaction[];
}

function getJournalData(): JournalData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "journal.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as JournalData;
  } catch {
    return null;
  }
}

function getDividendData(): DividendData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "dividend-data.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as DividendData;
  } catch {
    return null;
  }
}

function formatMoney(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}억`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}만`;
  return amount.toLocaleString();
}

const SECTOR_GROUP: Record<string, string> = {
  "반도체": "기술", "IT서비스": "기술", "디스플레이장비": "기술",
  "소프트웨어": "기술", "전자장비": "기술",
  "금융": "금융", "은행": "금융", "보험": "금융", "증권": "금융",
  "에너지": "에너지", "에너지기자재": "에너지",
  "자동차": "산업재", "기계": "산업재", "조선": "산업재", "건설": "산업재",
  "화학": "소재", "철강": "소재",
  "제약": "헬스케어", "바이오": "헬스케어",
  "음식료": "필수소비재", "유통": "임의소비재",
  "미디어": "커뮤니케이션", "통신": "커뮤니케이션",
};

interface SectorStat {
  evalAmount: number;
  invested: number;
  profit: number;
  count: number;
  names: string[];
  holdings: Holding[];
}

export default function JournalPage() {
  const data = getJournalData();
  const dividendData = getDividendData();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
      </div>
    );
  }

  const { summary, holdings, transactions } = data;
  const hasHoldings = holdings.length > 0;
  const hasTransactions = transactions.length > 0;
  const netProfit = summary.net_profit || 0;
  const profitColor = netProfit >= 0 ? "#95d3ba" : "#ffb4ab";

  const sectorStats = new Map<string, SectorStat>();
  let totalEval = 0;
  for (const h of holdings) {
    const raw = h.sector || "기타";
    const key = raw.startsWith("ETF") ? "ETF" : (SECTOR_GROUP[raw] || raw);
    const prev = sectorStats.get(key) || { evalAmount: 0, invested: 0, profit: 0, count: 0, names: [], holdings: [] };
    prev.evalAmount += h.eval_amount;
    prev.invested += h.avg_price * h.quantity;
    prev.profit += h.profit_amount;
    prev.count += 1;
    prev.names.push(h.name);
    prev.holdings.push(h);
    sectorStats.set(key, prev);
    totalEval += h.eval_amount;
  }

  const sectorList = Array.from(sectorStats.entries())
    .map(([sector, s]) => ({
      sector,
      ...s,
      weightPct: totalEval > 0 ? (s.evalAmount / totalEval) * 100 : 0,
      profitPct: s.invested > 0 ? (s.profit / s.invested) * 100 : 0,
    }))
    .sort((a, b) => b.evalAmount - a.evalAmount);

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Trading Journal
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          매매일지
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          {data.updated_at} 기준
        </p>
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* 파트 1: 현재 보유 현황 */}
      {/* ══════════════════════════════════════════════ */}

      {/* 포트폴리오 요약 */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-6 tracking-tight">
          포트폴리오 현황
        </h3>

        {/* 자산 현황 */}
        {(summary.cash != null || hasHoldings) && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-8">
            {summary.total_assets != null && (
              <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">총 자산</p>
                <p className="text-xl sm:text-2xl font-mono text-primary font-bold break-all">
                  {formatMoney(summary.total_assets)}
                  <span className="text-sm text-on-surface-variant ml-1">원</span>
                </p>
              </div>
            )}
            <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
              <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">주식 평가액</p>
              <p className="text-xl sm:text-2xl font-mono text-on-surface font-bold break-all">
                {formatMoney(summary.total_current_value)}
                <span className="text-sm text-on-surface-variant ml-1">원</span>
              </p>
              <p className="text-xs text-on-surface-variant/40 mt-1">
                {summary.total_assets ? `${((summary.total_current_value / summary.total_assets) * 100).toFixed(0)}%` : ""}
              </p>
            </div>
            {summary.cash != null && (
              <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">현금 (CMA)</p>
                <p className="text-xl sm:text-2xl font-mono text-on-surface font-bold break-all">
                  {formatMoney(summary.cash)}
                  <span className="text-sm text-on-surface-variant ml-1">원</span>
                </p>
                <p className="text-xs text-on-surface-variant/40 mt-1">
                  {summary.total_assets ? `${((summary.cash / summary.total_assets) * 100).toFixed(0)}%` : ""}
                </p>
              </div>
            )}
            <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
              <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">순수익</p>
              <p className="text-xl sm:text-2xl font-mono font-bold break-all" style={{ color: profitColor }}>
                {netProfit >= 0 ? "+" : ""}{formatMoney(netProfit)}원
              </p>
              <p className="text-xs mt-1" style={{ color: profitColor }}>
                {(summary.net_profit_pct || 0) >= 0 ? "+" : ""}{summary.net_profit_pct || 0}%
              </p>
            </div>
          </div>
        )}

        {/* 포트폴리오 전략 점검 */}
        {hasHoldings && summary.target_strategy && (
          <PortfolioStrategyFeedback
            holdings={holdings}
            cash={summary.cash || 0}
            totalAssets={summary.total_assets || summary.total_current_value}
            targetStrategy={summary.target_strategy}
          />
        )}

        {/* 포트폴리오 비율 차트 */}
        {hasHoldings && (
          <div className="bg-surface-container-low rounded-xl p-8 ghost-border mb-8">
            <h4 className="text-lg font-serif text-on-surface mb-6">포트폴리오 구성</h4>
            <PortfolioPieChart holdings={holdings} cash={summary.cash} />
          </div>
        )}

        {/* 섹터별 비중 차트 */}
        {hasHoldings && (
          <div className="bg-surface-container-low rounded-xl p-8 ghost-border mb-8">
            <h4 className="text-lg font-serif text-on-surface mb-6">섹터별 비중</h4>
            <SectorPieChart
              sectors={sectorList.map((s) => ({
                sector: s.sector,
                value: s.evalAmount,
                weight_pct: s.weightPct,
                count: s.count,
                names: s.names,
              }))}
              totalValue={totalEval}
              currency="krw"
            />
          </div>
        )}

        {/* 섹터별 수익 현황 */}
        {hasHoldings && (
          <div className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border mb-8">
            <h4 className="text-lg font-serif text-on-surface mb-6">섹터별 수익 현황</h4>
            <SectorProfitTable
              sectors={sectorList.map((s) => ({
                sector: s.sector,
                count: s.count,
                invested: s.invested,
                evalAmount: s.evalAmount,
                profit: s.profit,
                profitPct: s.profitPct,
                holdings: [...s.holdings].sort((a, b) => b.eval_amount - a.eval_amount).map((h) => ({
                  name: h.name,
                  invested: h.avg_price * h.quantity,
                  evalAmount: h.eval_amount,
                  profitAmount: h.profit_amount,
                  profitPct: h.profit_pct,
                })),
              }))}
            />
          </div>
        )}

        {/* 수익 & 비용 요약 */}
        {hasTransactions && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4 mb-8">
            {summary.gross_profit != null && (
              <div className="bg-surface-container-low rounded-xl p-3 sm:p-5 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">매매차익</p>
                <p className="text-base sm:text-xl font-mono font-bold break-all" style={{ color: (summary.gross_profit || 0) >= 0 ? "#95d3ba" : "#ffb4ab" }}>
                  {(summary.gross_profit || 0) >= 0 ? "+" : ""}{formatMoney(summary.gross_profit || 0)}원
                </p>
                <p className="text-xs text-on-surface-variant/40 mt-1">비용 차감 전</p>
              </div>
            )}
            {summary.total_fees != null && (
              <div className="bg-surface-container-low rounded-xl p-3 sm:p-5 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">누적 수수료</p>
                <p className="text-base sm:text-xl font-mono text-[#ffb4ab] font-bold break-all">
                  -{formatMoney(summary.total_fees || 0)}원
                </p>
              </div>
            )}
            {summary.total_tax != null && (
              <div className="bg-surface-container-low rounded-xl p-3 sm:p-5 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">누적 제세금</p>
                <p className="text-base sm:text-xl font-mono text-[#ffb4ab] font-bold break-all">
                  -{formatMoney(summary.total_tax || 0)}원
                </p>
              </div>
            )}
            {summary.total_cost != null && (
              <div className="bg-surface-container-low rounded-xl p-3 sm:p-5 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">총 비용 합계</p>
                <p className="text-base sm:text-xl font-mono text-[#ffb4ab] font-bold break-all">
                  -{formatMoney(summary.total_cost || 0)}원
                </p>
              </div>
            )}
            {summary.net_profit != null && (
              <div className="bg-surface-container-low rounded-xl p-3 sm:p-5 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">순수익</p>
                <p className="text-base sm:text-xl font-mono font-bold break-all" style={{ color: profitColor }}>
                  {netProfit >= 0 ? "+" : ""}{formatMoney(netProfit)}원
                </p>
                <p className="text-xs text-on-surface-variant/40 mt-1">비용 차감 후</p>
              </div>
            )}
            {summary.net_profit_pct != null && (
              <div className="bg-surface-container-low rounded-xl p-3 sm:p-5 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">수익률</p>
                <p className="text-xl sm:text-2xl font-mono font-bold" style={{ color: profitColor }}>
                  {(summary.net_profit_pct || 0) >= 0 ? "+" : ""}{summary.net_profit_pct}%
                </p>
              </div>
            )}
          </div>
        )}

        {!hasHoldings ? (
          <div className="bg-surface-container-low rounded-xl p-10 ghost-border text-center">
            <span className="material-symbols-outlined text-primary-dim/30 text-4xl mb-4 block">account_balance_wallet</span>
            <p className="text-lg text-on-surface-variant">현재 보유 중인 종목이 없습니다</p>
          </div>
        ) : (
          <>
            {/* 보유 종목 요약 카드 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-5 mb-8">
              <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">총 투입금액</p>
                <p className="text-xl sm:text-2xl font-mono text-on-surface font-bold break-all">
                  {formatMoney(summary.total_invested)}
                  <span className="text-sm text-on-surface-variant ml-1">원</span>
                </p>
              </div>
              <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">현재 평가액</p>
                <p className="text-xl sm:text-2xl font-mono text-on-surface font-bold break-all">
                  {formatMoney(summary.total_current_value)}
                  <span className="text-sm text-on-surface-variant ml-1">원</span>
                </p>
              </div>
              <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">총 수익금</p>
                <p className="text-xl sm:text-2xl font-mono font-bold break-all" style={{ color: profitColor }}>
                  {netProfit >= 0 ? "+" : ""}{formatMoney(netProfit)}
                  <span className="text-sm ml-1">원</span>
                </p>
              </div>
              <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border">
                <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">투입 대비 수익률</p>
                <p className="text-2xl sm:text-3xl font-mono font-bold" style={{ color: profitColor }}>
                  {(summary.net_profit_pct || 0) >= 0 ? "+" : ""}{summary.net_profit_pct || 0}%
                </p>
              </div>
            </div>

            {/* 보유 종목 */}
            <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
              <div className="p-6 pb-3">
                <h4 className="text-lg font-serif text-on-surface">보유 종목</h4>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-base">
                  <thead>
                    <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                      <th className="text-left px-6 pb-3 font-normal">종목</th>
                      <th className="text-right px-4 pb-3 font-normal">수량</th>
                      <th className="text-right px-4 pb-3 font-normal">평균매수가</th>
                      <th className="text-right px-4 pb-3 font-normal">현재가</th>
                      <th className="text-right px-4 pb-3 font-normal">평가금액</th>
                      <th className="text-right px-4 pb-3 font-normal">수익금</th>
                      <th className="text-right px-6 pb-3 font-normal">수익률</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...holdings].sort((a, b) => b.eval_amount - a.eval_amount).map((h) => {
                      const pColor = h.profit_pct >= 0 ? "#95d3ba" : "#ffb4ab";
                      return (
                        <tr key={h.code} className="hover:bg-surface-container/30 transition-colors">
                          <td className="px-6 py-4">
                            <p className="font-medium text-on-surface">{h.name}</p>
                            <p className="text-sm text-on-surface-variant/50">{h.code}{h.sector ? ` · ${h.sector}` : ""}</p>
                          </td>
                          <td className="px-4 py-4 text-right font-mono text-on-surface">{h.quantity.toLocaleString()}주</td>
                          <td className="px-4 py-4 text-right font-mono text-on-surface-variant">{h.avg_price.toLocaleString()}</td>
                          <td className="px-4 py-4 text-right font-mono text-on-surface">{h.current_price.toLocaleString()}</td>
                          <td className="px-4 py-4 text-right font-mono text-on-surface">{formatMoney(h.eval_amount)}</td>
                          <td className="px-4 py-4 text-right font-mono" style={{ color: pColor }}>
                            {h.profit_amount >= 0 ? "+" : ""}{formatMoney(h.profit_amount)}
                          </td>
                          <td className="px-6 py-4 text-right font-mono font-bold" style={{ color: pColor }}>
                            {h.profit_pct >= 0 ? "+" : ""}{h.profit_pct}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* 배당 수입 예상 */}
      {/* ══════════════════════════════════════════════ */}

      {hasHoldings && dividendData && (() => {
        const dividendHoldings = holdings.map((h) => {
          const dStock = dividendData.stocks[h.code];
          return {
            code: h.code,
            name: h.name,
            quantity: h.quantity,
            avg_price: h.avg_price,
            current_price: h.current_price,
            eval_amount: h.eval_amount,
            dps: dStock?.dps ?? 0,
            stock_type: dStock?.type ?? ("common" as const),
            dividend_cycle: dStock?.dividend_cycle,
            note: dStock?.note,
            next_dividend_date: dStock?.next_dividend_date,
            next_dividend_note: dStock?.next_dividend_note,
          };
        });

        return (
          <section>
            <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
              Dividend Income
            </p>
            <h3 className="text-2xl font-serif text-on-surface mb-6 tracking-tight">
              배당 수입 예상
            </h3>
            <DividendSummary
              holdings={dividendHoldings}
              totalInvested={summary.total_invested}
              basisYear={dividendData.basis_year}
            />
          </section>
        );
      })()}

      {/* ══════════════════════════════════════════════ */}
      {/* 파트 2: 매매 히스토리 */}
      {/* ══════════════════════════════════════════════ */}

      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-6 tracking-tight">
          매매 히스토리
        </h3>

        {!hasTransactions ? (
          <div className="bg-surface-container-low rounded-xl p-10 ghost-border text-center">
            <span className="material-symbols-outlined text-primary-dim/30 text-4xl mb-4 block">history</span>
            <p className="text-lg text-on-surface-variant">아직 매매 기록이 없습니다</p>
            <p className="text-sm text-on-surface-variant/50 mt-2">매매 정보를 알려주시면 기록합니다</p>
          </div>
        ) : (
          <div className="space-y-4">
            {transactions.map((tx) => {
              const isBuy = tx.type === "매수";
              const isSell = tx.type === "매도";
              const isDividend = tx.type === "배당";
              const typeColor = isBuy ? "#6ea8fe" : isDividend ? "#d4b483" : "#95d3ba";
              const typeIcon = isBuy ? "shopping_cart" : isDividend ? "payments" : "sell";

              // 매도 시 수익/손실 계산 (같은 종목의 전체 매수 평균가 기준)
              let sellProfit = 0;
              let sellProfitPct = 0;
              if (isSell) {
                const buyTxs = transactions.filter(t => t.type === "매수" && t.code === tx.code);
                if (buyTxs.length > 0) {
                  const totalBuyQty = buyTxs.reduce((s, t) => s + t.quantity, 0);
                  const totalBuyAmt = buyTxs.reduce((s, t) => s + t.total, 0);
                  const avgBuyPrice = totalBuyQty > 0 ? totalBuyAmt / totalBuyQty : 0;
                  const costBasis = avgBuyPrice * tx.quantity;
                  const sellGross = tx.total;
                  const sellCosts = (tx.fees || 0) + (tx.tax || 0);
                  sellProfit = Math.round(sellGross - costBasis - sellCosts);
                  sellProfitPct = costBasis > 0 ? (sellProfit / costBasis) * 100 : 0;
                }
              }
              const sellProfitColor = sellProfit >= 0 ? "#95d3ba" : "#ffb4ab";

              return (
                <div key={tx.id} className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
                  <div className="p-6">
                    {/* 거래 헤더 */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: `${typeColor}15` }}>
                          <span className="material-symbols-outlined" style={{ color: typeColor }}>{typeIcon}</span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-lg font-medium text-on-surface">{tx.name}</h4>
                            <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${typeColor}20`, color: typeColor }}>
                              {tx.type}
                            </span>
                          </div>
                          <p className="text-sm text-on-surface-variant">{tx.date} · {tx.code}</p>
                        </div>
                      </div>
                      <div className="text-left sm:text-right ml-14 sm:ml-0">
                        {isDividend ? (
                          <>
                            <p className="text-xl font-mono font-bold" style={{ color: typeColor }}>
                              +{(tx.net_amount ?? tx.total).toLocaleString()}원
                            </p>
                            <p className="text-sm text-on-surface-variant">
                              gross {tx.total.toLocaleString()}원
                              {tx.tax ? ` · 세금 ${tx.tax.toLocaleString()}원` : ""}
                            </p>
                          </>
                        ) : (
                          <>
                            <p className="text-xl font-mono text-on-surface font-bold">
                              {tx.total.toLocaleString()}원
                            </p>
                            <p className="text-sm text-on-surface-variant">
                              {tx.quantity.toLocaleString()}주 × {tx.price.toLocaleString()}원
                            </p>
                            {(tx.fees || tx.tax) && (
                              <p className="text-xs text-on-surface-variant/40 mt-0.5">
                                {tx.fees ? `수수료 ${tx.fees.toLocaleString()}원` : ""}
                                {tx.fees && tx.tax ? " · " : ""}
                                {tx.tax ? `세금 ${tx.tax.toLocaleString()}원` : ""}
                              </p>
                            )}
                          </>
                        )}
                      </div>
                    </div>

                    {/* 매도 수익/손실 결과 */}
                    {isSell && sellProfit !== 0 && (
                      <div className="mb-4 p-4 rounded-xl" style={{ backgroundColor: `${sellProfitColor}10` }}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-sm" style={{ color: sellProfitColor }}>
                              {sellProfit >= 0 ? "trending_up" : "trending_down"}
                            </span>
                            <span className="text-base font-medium" style={{ color: sellProfitColor }}>
                              {sellProfit >= 0 ? "수익 실현" : "손실 실현"}
                            </span>
                          </div>
                          <div className="text-right">
                            <span className="text-xl font-mono font-bold" style={{ color: sellProfitColor }}>
                              {sellProfit >= 0 ? "+" : ""}{formatMoney(sellProfit)}원
                            </span>
                            <span className="text-sm font-mono ml-2" style={{ color: sellProfitColor }}>
                              ({sellProfitPct >= 0 ? "+" : ""}{sellProfitPct.toFixed(1)}%)
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 매매 사유 */}
                    {tx.reason && (
                      <div className="mb-3">
                        <p className="text-sm text-on-surface-variant leading-relaxed">
                          <span className="text-on-surface font-medium">매매 사유: </span>
                          {tx.reason}
                        </p>
                      </div>
                    )}

                    {/* AI 평가 */}
                    {tx.ai_evaluation && (
                      <div className="bg-surface-container/50 rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
                          <span className="text-xs text-primary font-medium">AI 매매 평가</span>
                        </div>
                        <p className="text-sm text-on-surface-variant leading-relaxed">
                          <MarkdownText>{tx.ai_evaluation}</MarkdownText>
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
