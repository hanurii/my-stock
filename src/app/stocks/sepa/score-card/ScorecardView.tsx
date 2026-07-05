"use client";

import { useState } from "react";
import type { Scorecard, OverallStats, MonthlyRow, Trade, OpenPosition } from "@/lib/scorecard";
import { fmtPct, fmtLossPct, fmtSignedPct, fmtNum, fmtRatio, plColor, PROFIT_COLOR, LOSS_COLOR } from "./format";

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-surface-container-low rounded-xl ghost-border p-4">
      <p className="text-xs text-on-surface-variant/60">{label}</p>
      <p className="text-2xl font-mono font-bold mt-1" style={color ? { color } : undefined}>{value}</p>
      {sub && <p className="text-[11px] text-on-surface-variant/50 mt-1">{sub}</p>}
    </div>
  );
}

const MONTH_COLS = "grid grid-cols-9 gap-2 px-3 py-2 text-right text-sm";

function MonthRow({ row, isAvg }: { row: MonthlyRow; isAvg?: boolean }) {
  return (
    <div className={`${MONTH_COLS} ${isAvg ? "font-bold bg-surface-container-low rounded-lg" : "border-t border-outline/10"}`}>
      <span className="text-left">{row.month}</span>
      <span style={{ color: plColor(row.avg_win) }}>{fmtPct(row.avg_win)}</span>
      <span style={{ color: row.avg_loss == null ? undefined : LOSS_COLOR }}>{fmtLossPct(row.avg_loss)}</span>
      <span>{fmtPct(row.win_rate)}</span>
      <span>{row.trades}</span>
      <span style={{ color: plColor(row.max_win) }}>{fmtPct(row.max_win)}</span>
      <span style={{ color: row.max_loss == null ? undefined : LOSS_COLOR }}>{fmtLossPct(row.max_loss)}</span>
      <span>{fmtNum(row.win_days)}</span>
      <span>{fmtNum(row.loss_days)}</span>
    </div>
  );
}

function TradeRow({ trade, basis }: { trade: Trade; basis: "net" | "gross" }) {
  const pct = basis === "net" ? trade.net_pct : trade.gross_pct;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-t border-outline/10">
      <div className="flex items-center gap-2">
        <span className="font-medium text-on-surface">{trade.name}</span>
        {trade.setup && <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">{trade.setup}</span>}
        {trade.stop_violation && <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: LOSS_COLOR + "22", color: LOSS_COLOR }}>손절위반</span>}
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-on-surface-variant/60">{trade.open_date} ~ {trade.close_date} ({trade.hold_days}일)</span>
        <span className="font-mono font-bold w-20 text-right" style={{ color: plColor(pct) }}>{fmtSignedPct(pct)}</span>
      </div>
    </div>
  );
}

function OpenRow({ pos }: { pos: OpenPosition }) {
  return (
    <div className="flex items-center justify-between gap-2 px-4 py-2 border-t border-outline/10 text-sm">
      <span className="font-medium text-on-surface">{pos.name}</span>
      <span className="text-on-surface-variant/60">{pos.qty}주 · 평균 {pos.avg_buy.toLocaleString()}원 · {pos.open_date}</span>
    </div>
  );
}

export function ScorecardView({ data }: { data: Scorecard }) {
  const [basis, setBasis] = useState<"net" | "gross">("net");
  const o: OverallStats = data.overall[basis];
  const monthly = data.monthly[basis];
  const hasTrades = o.trade_count > 0;
  const rba = data.rba;
  const rbaColor = rba.status === "too_wide" ? LOSS_COLOR : rba.status === "ok" ? PROFIT_COLOR : "inherit";

  return (
    <div className="space-y-8">
      {/* 머리말 + 토글 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">scoreboard</span>미너비니 정산표
          </h2>
          <p className="text-sm text-on-surface-variant/70 mt-1">
            {data.generated_at} 기준 · 전략 {data.strategy} · 청산거래 {data.overall.net.trade_count}건
          </p>
        </div>
        <div className="flex gap-1 bg-surface-container-low rounded-lg p-1 ghost-border">
          {(["net", "gross"] as const).map((b) => (
            <button
              key={b}
              onClick={() => setBasis(b)}
              className={`flex flex-col items-center px-4 py-1.5 rounded-md transition-all ${
                basis === b ? "bg-primary/15 text-primary shadow-sm" : "text-on-surface-variant/60 hover:text-on-surface-variant"
              }`}
            >
              <span className="text-sm font-medium">{b === "net" ? "순수익" : "총수익"}</span>
              <span className="text-[10px] leading-tight opacity-70">{b === "net" ? "수수료·세금 차감" : "가격만"}</span>
            </button>
          ))}
        </div>
      </div>

      {!hasTrades ? (
        <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-sm text-on-surface-variant/70">
          아직 청산된 거래가 없습니다. 매도까지 완료된 거래가 쌓이면 여기에 성적표가 표시됩니다.
        </div>
      ) : (
        <>
          {/* 트레이딩 삼각형 */}
          <section className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <StatCard label="승률" value={fmtPct(o.win_rate)} sub={`${o.win_count}승 ${o.loss_count}패 / ${o.trade_count}건`} />
              <StatCard label="평균수익" value={fmtPct(o.avg_win)} color={o.avg_win == null ? undefined : PROFIT_COLOR} />
              <StatCard label="평균손실" value={fmtLossPct(o.avg_loss)} color={o.avg_loss == null ? undefined : LOSS_COLOR} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <StatCard label="성공/실패 비율" value={fmtRatio(o.payoff_ratio)} sub="평균수익 ÷ 평균손실" />
              <StatCard label="조정 후 비율" value={fmtRatio(o.adj_payoff_ratio)} sub={o.adj_payoff_ratio == null ? undefined : o.adj_payoff_ratio < 1 ? "1 미만 — 수학적 우위 없음" : "1 이상 — 수학적 우위 있음"} />
              <StatCard label="기대수익 (거래당)" value={fmtSignedPct(o.expectancy)} color={plColor(o.expectancy)} />
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-on-surface-variant/60 px-1">
              {o.max_win && <span>최대수익 <b style={{ color: PROFIT_COLOR }}>{fmtPct(o.max_win.pct)}</b> ({o.max_win.name})</span>}
              {o.max_loss && <span>최대손실 <b style={{ color: LOSS_COLOR }}>{fmtLossPct(o.max_loss.pct)}</b> ({o.max_loss.name})</span>}
              <span>수익 유지 {fmtNum(o.win_days)}일 · 손실 유지 {fmtNum(o.loss_days)}일</span>
            </div>
          </section>

          {/* RBA 카드 */}
          <section className="bg-surface-container-low rounded-xl ghost-border p-4">
            <p className="text-xs text-on-surface-variant/60 mb-1">RBA — 결과 기반 권장 손절폭</p>
            <p className="text-sm text-on-surface">
              평균수익 <b>{fmtPct(rba.avg_win_net)}</b> → 권장 최대 손절 <b style={{ color: rbaColor }}>{fmtPct(rba.recommended_max_stop_pct)}</b>
              {" "}(현재 기본 {rba.current_default_stop_pct}%,{" "}
              <span style={{ color: rbaColor }}>{rba.status === "too_wide" ? "손절이 너무 넓음" : rba.status === "ok" ? "적정" : "거래 부족"}</span>)
            </p>
          </section>

          {/* 진단 경고 */}
          {data.diagnostics.warnings.length > 0 && (
            <section className="bg-surface-container-low rounded-xl ghost-border p-4">
              <p className="text-xs text-on-surface-variant/60 mb-2">진단</p>
              <ul className="space-y-1">
                {data.diagnostics.warnings.map((w, i) => (
                  <li key={i} className="text-sm text-on-surface flex gap-2"><span>⚠️</span><span>{w}</span></li>
                ))}
              </ul>
            </section>
          )}

          {/* 월별 확인표 */}
          <section>
            <h3 className="text-lg font-serif font-bold text-on-surface mb-2">월별 확인표</h3>
            <div className="bg-surface-container-low rounded-xl ghost-border overflow-x-auto">
              <div className="min-w-[640px]">
                <div className={`${MONTH_COLS} text-xs text-on-surface-variant/60`}>
                  <span className="text-left">월</span><span>평균수익</span><span>평균손실</span><span>승률</span>
                  <span>거래</span><span>최대수익</span><span>최대손실</span><span>수익일</span><span>손실일</span>
                </div>
                {monthly.rows.map((r) => <MonthRow key={r.month} row={r} />)}
                <MonthRow row={monthly.average} isAvg />
              </div>
            </div>
          </section>

          {/* 왕복거래 목록 */}
          <section>
            <h3 className="text-lg font-serif font-bold text-on-surface mb-2">왕복거래</h3>
            <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
              {data.trades.map((t, i) => <TradeRow key={`${t.code}-${t.close_date}-${i}`} trade={t} basis={basis} />)}
            </div>
          </section>
        </>
      )}

      {/* 열린 포지션 (미청산) */}
      {data.open_positions.length > 0 && (
        <section>
          <h3 className="text-lg font-serif font-bold text-on-surface mb-2">열린 포지션 <span className="text-xs font-normal text-on-surface-variant/50">(미청산 · 실현 통계 제외)</span></h3>
          <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
            {data.open_positions.map((p) => <OpenRow key={p.code} pos={p} />)}
          </div>
        </section>
      )}
    </div>
  );
}
