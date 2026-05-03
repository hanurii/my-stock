"use client";

import { Fragment, useMemo, useState } from "react";
import type { MegacapStock, MegacapFXData, MegacapMarket } from "@/lib/megacap";
import { combinedScore, currencyToFXScore, formatMarketCap, formatPercent, marketLabel, currencyDisplay } from "@/lib/megacap";

interface Props {
  stocks: MegacapStock[];
  fxData: MegacapFXData | null;
}

type SortKey = "combined" | "score" | "marketCap" | "pe" | "drawdown" | "fcfYield";
type MarketFilter = "ALL" | MegacapMarket;
type SignalFilter = "ALL" | "BUFFETT" | "STRONG_BUY" | "BUY";

function fcfYield(stock: MegacapStock): number | null {
  const { freeCashflow, marketCap } = stock.metrics;
  if (freeCashflow == null || marketCap == null || marketCap <= 0) return null;
  return (freeCashflow / marketCap) * 100;
}

function drawdownPct(stock: MegacapStock): number | null {
  const { fiftyTwoWeekHigh, regularMarketPrice } = stock.metrics;
  if (fiftyTwoWeekHigh == null || regularMarketPrice == null || fiftyTwoWeekHigh <= 0) return null;
  return -((fiftyTwoWeekHigh - regularMarketPrice) / fiftyTwoWeekHigh) * 100;
}

function signalColor(label: MegacapStock["signal"]["label"]): string {
  if (label === "강한 매수") return "#10b981";
  if (label === "매수 검토") return "#fbbf24";
  if (label === "관찰") return "#94a3b8";
  return "transparent";
}

export function MegacapTable({ stocks, fxData }: Props) {
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL");
  const [signalFilter, setSignalFilter] = useState<SignalFilter>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("combined");
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let arr = stocks;
    if (marketFilter !== "ALL") arr = arr.filter((s) => s.market === marketFilter);
    if (signalFilter === "BUFFETT") arr = arr.filter((s) => s.is_buffett_candidate);
    if (signalFilter === "STRONG_BUY") arr = arr.filter((s) => s.signal.label === "강한 매수");
    if (signalFilter === "BUY") arr = arr.filter((s) => s.signal.label === "강한 매수" || s.signal.label === "매수 검토");

    const sorted = [...arr].sort((a, b) => {
      if (sortKey === "combined") return combinedScore(b, fxData) - combinedScore(a, fxData);
      if (sortKey === "score") return b.scores.total - a.scores.total;
      if (sortKey === "marketCap") return (b.metrics.marketCap ?? 0) - (a.metrics.marketCap ?? 0);
      if (sortKey === "pe") {
        const ap = a.metrics.trailingPE ?? Infinity;
        const bp = b.metrics.trailingPE ?? Infinity;
        return ap - bp;
      }
      if (sortKey === "drawdown") {
        const ad = drawdownPct(a) ?? 0;
        const bd = drawdownPct(b) ?? 0;
        return ad - bd; // 더 큰 하락이 위로
      }
      if (sortKey === "fcfYield") {
        const ay = fcfYield(a) ?? -1;
        const by = fcfYield(b) ?? -1;
        return by - ay;
      }
      return 0;
    });
    return sorted;
  }, [stocks, marketFilter, signalFilter, sortKey, fxData]);

  const SortBtn = ({ k, label }: { k: SortKey; label: string }) => (
    <button
      onClick={() => setSortKey(k)}
      className={`px-2.5 py-1 rounded-md text-xs transition-all ${
        sortKey === k ? "bg-primary/15 text-primary" : "text-on-surface-variant/70 hover:bg-surface-container/50"
      }`}
    >
      {label}
    </button>
  );

  const toggleRow = (ticker: string) => {
    setExpandedTicker((prev) => (prev === ticker ? null : ticker));
  };

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex gap-1 rounded-md bg-surface-container-low p-1">
          {(["ALL", "US", "KR", "JP", "CN", "EU", "OTHER"] as MarketFilter[]).map((m) => (
            <button
              key={m}
              onClick={() => setMarketFilter(m)}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                marketFilter === m ? "bg-primary/15 text-primary" : "text-on-surface-variant/70 hover:bg-surface-container/50"
              }`}
            >
              {m === "ALL" ? "전체" : m}
            </button>
          ))}
        </div>
        <div className="flex gap-1 rounded-md bg-surface-container-low p-1">
          {([
            { k: "ALL" as SignalFilter, label: "모든 종목" },
            { k: "BUFFETT" as SignalFilter, label: "버핏 후보 (≥70)" },
            { k: "BUY" as SignalFilter, label: "매수 시그널" },
            { k: "STRONG_BUY" as SignalFilter, label: "강한 매수만" },
          ]).map((f) => (
            <button
              key={f.k}
              onClick={() => setSignalFilter(f.k)}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                signalFilter === f.k ? "bg-primary/15 text-primary" : "text-on-surface-variant/70 hover:bg-surface-container/50"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-xs text-on-surface-variant/60">정렬:</span>
        <SortBtn k="combined" label="종합 점수" />
        <SortBtn k="score" label="종목 점수" />
        <SortBtn k="marketCap" label="시총" />
        <SortBtn k="pe" label="PER" />
        <SortBtn k="drawdown" label="고점대비 하락률" />
        <SortBtn k="fcfYield" label="잉여현금수익률" />
        <span className="text-xs text-on-surface-variant/40 ml-auto">{filtered.length}종목</span>
      </div>

      {/* Table */}
      <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                <th className="text-center px-2 pb-3 pt-4 font-normal w-8">#</th>
                <th className="text-left px-3 pb-3 pt-4 font-normal">종목</th>
                <th className="text-left px-3 pb-3 pt-4 font-normal hidden md:table-cell">시장</th>
                <th className="text-right px-3 pb-3 pt-4 font-normal hidden md:table-cell">시총</th>
                <th className="text-right px-3 pb-3 pt-4 font-normal">PER</th>
                <th className="text-right px-3 pb-3 pt-4 font-normal hidden lg:table-cell">현금수익률</th>
                <th className="text-right px-3 pb-3 pt-4 font-normal hidden lg:table-cell">고점대비</th>
                <th className="text-right px-3 pb-3 pt-4 font-normal">점수</th>
                <th className="text-right px-3 pb-3 pt-4 font-normal hidden md:table-cell">환율</th>
                <th className="text-right px-3 pb-3 pt-4 font-normal">종합</th>
                <th className="text-center px-3 pb-3 pt-4 font-normal">시그널</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, idx) => {
                const fxScore = currencyToFXScore(s.currency, fxData);
                const combined = s.scores.total + fxScore;
                const fcfY = fcfYield(s);
                const dd = drawdownPct(s);
                const isExpanded = expandedTicker === s.ticker;
                const sigColor = signalColor(s.signal.label);

                return (
                  <Fragment key={s.ticker}>
                    <tr
                      onClick={() => toggleRow(s.ticker)}
                      className={`hover:bg-surface-container/30 transition-colors cursor-pointer ${
                        s.is_buffett_candidate ? "bg-primary/5" : ""
                      }`}
                    >
                      <td className="text-center px-2 py-2.5 font-mono text-on-surface-variant text-xs">{idx + 1}</td>
                      <td className="px-3 py-2.5">
                        <div className="font-medium text-on-surface text-sm">{s.name_kr}</div>
                        <div className="text-[11px] font-mono text-on-surface-variant/60">{s.ticker}</div>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-on-surface-variant hidden md:table-cell">
                        {marketLabel(s.market)}
                      </td>
                      <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell text-xs">
                        {formatMarketCap(s.metrics.marketCap, s.currency)}
                      </td>
                      <td className="text-right px-3 py-2.5 font-mono text-on-surface text-xs">
                        {s.metrics.trailingPE != null ? s.metrics.trailingPE.toFixed(1) : "—"}
                        {s.metrics.forwardPE != null && (
                          <div className="text-[10px] text-on-surface-variant/60">
                            예상 {s.metrics.forwardPE.toFixed(1)}
                          </div>
                        )}
                      </td>
                      <td className="text-right px-3 py-2.5 font-mono hidden lg:table-cell text-xs"
                        style={{ color: fcfY != null && fcfY >= 5 ? "#34d399" : undefined }}>
                        {fcfY != null ? `${fcfY.toFixed(1)}%` : "—"}
                      </td>
                      <td className="text-right px-3 py-2.5 font-mono hidden lg:table-cell text-xs"
                        style={{ color: dd != null && dd <= -20 ? "#34d399" : undefined }}>
                        {formatPercent(dd, 1)}
                      </td>
                      <td className="text-right px-3 py-2.5 font-mono font-bold"
                        style={{ color: s.scores.total >= 70 ? "#34d399" : s.scores.total >= 50 ? "#fbbf24" : "#94a3b8" }}>
                        {s.scores.total.toFixed(0)}
                      </td>
                      <td className="text-right px-3 py-2.5 font-mono hidden md:table-cell text-xs"
                        style={{ color: fxScore > 0 ? "#34d399" : fxScore < 0 ? "#fb923c" : "#94a3b8" }}>
                        {fxScore >= 0 ? "+" : ""}{fxScore}
                      </td>
                      <td className="text-right px-3 py-2.5 font-mono font-bold text-primary">
                        {combined.toFixed(0)}
                      </td>
                      <td className="text-center px-3 py-2.5">
                        {s.signal.label && (
                          <span
                            className="inline-block px-2 py-0.5 rounded text-[10px] font-medium"
                            style={{
                              backgroundColor: `${sigColor}20`,
                              color: sigColor,
                              border: `1px solid ${sigColor}40`,
                            }}
                          >
                            {s.signal.label}
                          </span>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="bg-surface-container/20">
                        <td colSpan={11} className="px-6 py-4">
                          <ExpandedDetail stock={s} fxScore={fxScore} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ExpandedDetail({ stock, fxScore }: { stock: MegacapStock; fxScore: number }) {
  const { metrics, scores, signal, price_history } = stock;
  const fcfY = fcfYield(stock);
  const dd = drawdownPct(stock);
  const symbol = currencyDisplay(stock.currency);

  return (
    <div className="space-y-4">
      {/* 점수 분해 */}
      <div>
        <h4 className="text-xs uppercase tracking-wider text-on-surface-variant/60 mb-2">기둥별 점수 분해 (총 100점)</h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <ScoreBar label="사업 실력" value={scores.quality} max={40} color="#6ea8fe" />
          <ScoreBar label="경제적 해자" value={scores.moat} max={20} color="#c084fc" />
          <ScoreBar label="자본 운용력" value={scores.capital} max={20} color="#34d399" />
          <ScoreBar label="가격 매력" value={scores.valuation} max={20} color="#fbbf24" />
        </div>
      </div>

      {/* 핵심 지표 */}
      <div>
        <h4 className="text-xs uppercase tracking-wider text-on-surface-variant/60 mb-2">핵심 지표</h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <Metric label="현재가" value={metrics.regularMarketPrice != null ? `${symbol}${metrics.regularMarketPrice.toLocaleString()}` : "—"} />
          <Metric label="자기자본이익률(ROE)" value={metrics.returnOnEquity != null ? `${(metrics.returnOnEquity * 100).toFixed(1)}%` : "—"} />
          <Metric label="영업이익률" value={metrics.operatingMargins != null ? `${(metrics.operatingMargins * 100).toFixed(1)}%` : "—"} />
          <Metric label="순이익률" value={metrics.profitMargins != null ? `${(metrics.profitMargins * 100).toFixed(1)}%` : "—"} />
          <Metric label="기업가치/EBITDA" value={metrics.enterpriseToEbitda != null ? metrics.enterpriseToEbitda.toFixed(1) : "—"} />
          <Metric label="주가순자산비율(PBR)" value={metrics.priceToBook != null ? metrics.priceToBook.toFixed(1) : "—"} />
          <Metric label="배당수익률" value={metrics.dividendYield != null ? `${(metrics.dividendYield * 100).toFixed(2)}%` : "—"} />
          <Metric label="배당성향" value={metrics.payoutRatio != null ? `${(metrics.payoutRatio * 100).toFixed(0)}%` : "—"} />
          <Metric label="주당순이익 성장률" value={metrics.earningsGrowth != null ? formatPercent(metrics.earningsGrowth * 100) : "—"} />
          <Metric label="매출 성장률" value={metrics.revenueGrowth != null ? formatPercent(metrics.revenueGrowth * 100) : "—"} />
          <Metric label="부채비율" value={metrics.debtToEquity != null ? `${metrics.debtToEquity.toFixed(0)}%` : "—"} />
          <Metric label="잉여현금수익률" value={fcfY != null ? `${fcfY.toFixed(2)}%` : "—"} />
        </div>
      </div>

      {/* 5년 가격 위치 + 분할매수 트리거 */}
      <div className="grid sm:grid-cols-2 gap-4">
        {price_history && (
          <div>
            <h4 className="text-xs uppercase tracking-wider text-on-surface-variant/60 mb-2">5년 가격 위치</h4>
            <div className="bg-surface-container/30 rounded-lg p-3 text-xs">
              <div className="flex justify-between mb-1.5">
                <span className="text-on-surface-variant">5년 최저</span>
                <span className="font-mono">{symbol}{price_history.low_5y.toLocaleString()}</span>
              </div>
              <div className="relative h-2 bg-surface-container rounded-full overflow-hidden mb-1.5">
                <div
                  className="absolute top-0 h-full bg-primary"
                  style={{ width: `${price_history.percentile_5y}%` }}
                />
                <div
                  className="absolute top-0 w-1 h-full bg-on-surface"
                  style={{ left: `${price_history.percentile_5y}%` }}
                />
              </div>
              <div className="flex justify-between mb-1.5">
                <span className="text-on-surface-variant">5년 최고</span>
                <span className="font-mono">{symbol}{price_history.high_5y.toLocaleString()}</span>
              </div>
              <div className="text-center mt-2 text-on-surface-variant">
                현재 5년 위치: <span className="font-bold text-primary">{price_history.percentile_5y.toFixed(0)}%</span>
                {" / "}
                고점 대비 <span className={price_history.pct_from_high < -10 ? "text-emerald-400 font-bold" : ""}>
                  {formatPercent(price_history.pct_from_high)}
                </span>
              </div>
            </div>
          </div>
        )}
        <div>
          <h4 className="text-xs uppercase tracking-wider text-on-surface-variant/60 mb-2">분할매수 트리거 ({signal.triggers_met}/3)</h4>
          <div className="bg-surface-container/30 rounded-lg p-3 text-xs space-y-1.5">
            <Trigger met={signal.pe_below_avg} label="향후 12개월 예상 PER이 현재 PER보다 15%↑ 낮음 (실적 개선 신호)" />
            <Trigger met={signal.drawdown_20} label="52주 신고가 대비 -20% 이상 하락" />
            <Trigger met={signal.fcf_yield_high} label="잉여현금수익률 ≥ 5% (시총 대비 충분한 현금 창출)" />
            <div className="pt-1.5 mt-1.5 border-t border-on-surface-variant/10 text-on-surface-variant">
              환율 가산점: <span className={fxScore > 0 ? "text-emerald-400 font-bold" : fxScore < 0 ? "text-orange-400 font-bold" : ""}>
                {fxScore >= 0 ? "+" : ""}{fxScore}점
              </span>
              {" "}({stock.currency} 기준)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ScoreBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = (value / max) * 100;
  return (
    <div className="bg-surface-container/30 rounded-lg p-2.5">
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-on-surface-variant">{label}</span>
        <span className="font-mono font-bold" style={{ color }}>{value.toFixed(1)}/{max}</span>
      </div>
      <div className="h-1.5 bg-surface-container rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-on-surface-variant/60">{label}</div>
      <div className="font-mono font-medium text-on-surface mt-0.5">{value}</div>
    </div>
  );
}

function Trigger({ met, label }: { met: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="material-symbols-outlined text-base"
        style={{ color: met ? "#34d399" : "#475569" }}>
        {met ? "check_circle" : "radio_button_unchecked"}
      </span>
      <span className={met ? "text-on-surface" : "text-on-surface-variant/50"}>{label}</span>
    </div>
  );
}
