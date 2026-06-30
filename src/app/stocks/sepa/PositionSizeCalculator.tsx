"use client";

import { useState } from "react";
import { computePositionSizing, fmtKRW } from "./positionSizing";

export function PositionSizeCalculator() {
  const [capital, setCapital] = useState<number>(150_000_000);
  const [numStocks, setNumStocks] = useState<number>(5);
  const r = computePositionSizing(capital, numStocks);
  const stopLabel =
    r.stopLowPct === r.stopHighPct
      ? `${r.stopLowPct.toFixed(2)}%`
      : `${r.stopLowPct.toFixed(2)}% ~ ${r.stopHighPct.toFixed(2)}%`;
  const lossLabel =
    r.lossAtLow === r.lossAtHigh
      ? fmtKRW(r.lossAtLow)
      : `${fmtKRW(r.lossAtLow)} ~ ${fmtKRW(r.lossAtHigh)}`;

  return (
    <div className="space-y-3">
      {/* 입력 */}
      <div className="flex flex-wrap gap-3 items-end text-xs">
        <label className="flex flex-col gap-1">
          <span className="text-on-surface-variant/70">총 투입금액(원)</span>
          <input
            type="number"
            min={0}
            step={1_000_000}
            value={capital}
            onChange={(e) => setCapital(Math.max(0, Number(e.target.value) || 0))}
            className="w-48 bg-surface-container rounded px-2 py-1.5 text-on-surface text-right ghost-border"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-on-surface-variant/70">종목 수</span>
          <input
            type="number"
            min={1}
            max={50}
            step={1}
            value={numStocks}
            onChange={(e) => setNumStocks(Math.max(0, Math.floor(Number(e.target.value) || 0)))}
            className="w-24 bg-surface-container rounded px-2 py-1.5 text-on-surface text-right ghost-border"
          />
        </label>
        {capital > 0 && (
          <span className="text-on-surface-variant/50 self-center pb-1.5">= {fmtKRW(capital)}</span>
        )}
      </div>

      {!r.valid ? (
        <p className="text-on-surface-variant/60 text-sm">총 투입금액과 종목 수를 입력하세요.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-surface-container-low rounded-lg p-3 ghost-border">
            <p className="text-[11px] text-on-surface-variant/70 mb-1">포지션당 분배</p>
            <p className="text-lg font-serif font-bold text-on-surface">{fmtKRW(r.positionAmount)}</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-0.5">비중 {r.positionWeightPct.toFixed(1)}%</p>
          </div>
          <div className="bg-surface-container-low rounded-lg p-3 ghost-border">
            <p className="text-[11px] text-on-surface-variant/70 mb-1">권장 손절 라인</p>
            <p className="text-lg font-serif font-bold" style={{ color: "#e9c176" }}>{stopLabel}</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-0.5">
              계좌 위험 {r.riskAtLowPct.toFixed(2)}% ~ {r.riskAtHighPct.toFixed(2)}%
            </p>
          </div>
          <div className="bg-surface-container-low rounded-lg p-3 ghost-border">
            <p className="text-[11px] text-on-surface-variant/70 mb-1">1종목 최대 손실(손절 시)</p>
            <p className="text-lg font-serif font-bold" style={{ color: "#ffb4ab" }}>{lossLabel}</p>
            <p className="text-[11px] text-on-surface-variant/60 mt-0.5">손절 {stopLabel} 기준</p>
          </div>
        </div>
      )}

      {r.warnings.length > 0 && (
        <ul className="space-y-1">
          {r.warnings.map((w, i) => (
            <li key={i} className="text-[11px] text-amber-300 flex items-start gap-1">
              <span className="material-symbols-outlined text-[14px] leading-none">warning</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
