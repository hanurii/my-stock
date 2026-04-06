"use client";

import { useState } from "react";

interface HoldingRow {
  name: string;
  invested: number;
  evalAmount: number;
  profitAmount: number;
  profitPct: number;
}

interface SectorRow {
  sector: string;
  count: number;
  invested: number;
  evalAmount: number;
  profit: number;
  profitPct: number;
  holdings: HoldingRow[];
}

function fmt(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}억`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}만`;
  return amount.toLocaleString();
}

const POS = "#95d3ba";
const NEG = "#ffb4ab";

export function SectorProfitTable({ sectors }: { sectors: SectorRow[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const totalInvested = sectors.reduce((s, r) => s + r.invested, 0);
  const totalEval = sectors.reduce((s, r) => s + r.evalAmount, 0);
  const totalProfit = sectors.reduce((s, r) => s + r.profit, 0);
  const totalProfitPct = totalInvested > 0 ? (totalProfit / totalInvested) * 100 : 0;

  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-2 px-3 py-2 text-xs uppercase tracking-wider text-on-surface-variant/50">
        <span>섹터</span>
        <span className="w-20 text-right">투입금액</span>
        <span className="w-20 text-right">평가금액</span>
        <span className="w-20 text-right">수익금</span>
        <span className="w-16 text-right">수익률</span>
      </div>

      {sectors.map((row) => {
        const isOpen = expanded === row.sector;
        const color = row.profit >= 0 ? POS : NEG;
        return (
          <div key={row.sector}>
            <div
              className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-2 px-3 py-3 rounded-lg transition-all duration-200 cursor-pointer hover:bg-surface-container-low"
              style={{ backgroundColor: isOpen ? "var(--surface-container-low)" : "transparent" }}
              onClick={() => setExpanded(isOpen ? null : row.sector)}
            >
              <div className="flex items-center gap-2">
                <span
                  className="material-symbols-outlined text-sm text-on-surface-variant/50 transition-transform duration-200"
                  style={{ transform: isOpen ? "rotate(90deg)" : "rotate(0deg)" }}
                >
                  chevron_right
                </span>
                <span className="text-sm text-on-surface font-medium">{row.sector}</span>
                <span className="text-xs text-on-surface-variant/40">{row.count}개</span>
              </div>
              <span className="w-20 text-right text-sm font-mono text-on-surface-variant">
                {fmt(row.invested)}
              </span>
              <span className="w-20 text-right text-sm font-mono text-on-surface">
                {fmt(row.evalAmount)}
              </span>
              <span className="w-20 text-right text-sm font-mono font-bold" style={{ color }}>
                {row.profit >= 0 ? "+" : ""}{fmt(row.profit)}
              </span>
              <span className="w-16 text-right text-sm font-mono font-bold" style={{ color }}>
                {row.profitPct >= 0 ? "+" : ""}{row.profitPct.toFixed(1)}%
              </span>
            </div>

            {isOpen && (
              <div className="ml-8 mr-3 mb-2 space-y-0.5">
                {row.holdings.map((h) => {
                  const hColor = h.profitAmount >= 0 ? POS : NEG;
                  return (
                    <div
                      key={h.name}
                      className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-2 px-3 py-1.5 rounded text-xs"
                    >
                      <span className="text-on-surface-variant">{h.name}</span>
                      <span className="w-20 text-right font-mono text-on-surface-variant/60">
                        {fmt(h.invested)}
                      </span>
                      <span className="w-20 text-right font-mono text-on-surface-variant">
                        {fmt(h.evalAmount)}
                      </span>
                      <span className="w-20 text-right font-mono" style={{ color: hColor }}>
                        {h.profitAmount >= 0 ? "+" : ""}{fmt(h.profitAmount)}
                      </span>
                      <span className="w-16 text-right font-mono" style={{ color: hColor }}>
                        {h.profitPct >= 0 ? "+" : ""}{h.profitPct.toFixed(1)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}

      {/* 합계 */}
      <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-2 px-3 py-3 border-t border-on-surface-variant/10 mt-2">
        <span className="text-sm text-on-surface font-bold">합계</span>
        <span className="w-20 text-right text-sm font-mono text-on-surface-variant font-bold">
          {fmt(totalInvested)}
        </span>
        <span className="w-20 text-right text-sm font-mono text-on-surface font-bold">
          {fmt(totalEval)}
        </span>
        <span
          className="w-20 text-right text-sm font-mono font-bold"
          style={{ color: totalProfit >= 0 ? POS : NEG }}
        >
          {totalProfit >= 0 ? "+" : ""}{fmt(totalProfit)}
        </span>
        <span
          className="w-16 text-right text-sm font-mono font-bold"
          style={{ color: totalProfitPct >= 0 ? POS : NEG }}
        >
          {totalProfitPct >= 0 ? "+" : ""}{totalProfitPct.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}
