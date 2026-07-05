// 보유 종목 점검 — 미너비니 매도 규칙 위반 피드백 (서버 렌더 전용, 상호작용 없음)

export interface HoldingRule {
  id: string;
  status: "violation" | "pass" | "pending" | "na";
  detail: string;
}
export interface HoldingFeedback {
  code: string;
  name: string;
  market?: string | null;
  buy_date: string;
  buy_price: number;
  quantity?: number;
  stop_loss_pct: number;
  pivot_price?: number | null;
  pivot_source?: string | null;
  current_price?: number;
  profit_pct?: number;
  stop_price?: number;
  pct_to_stop?: number;
  breakout_date?: string;
  breakout_date_estimated?: boolean;
  signal: "stop_loss" | "early_sell" | "hold" | "no_data";
  violation_count: number;
  rules: HoldingRule[];
}
export interface HoldingsFeedbackFile {
  generated_at?: string;
  asof?: string;
  holdings?: HoldingFeedback[];
}

const RULE_LABELS: Record<string, string> = {
  low_volume_breakout: "① 저거래량 돌파",
  heavy_volume_pullback: "② 대량 거래 후퇴",
  consecutive_lower_lows: "③ 연속 저저점(거래량)",
  close_below_ma: "④ 이평선 아래 마감",
  weak_days_dominant: "⑤ 하락일·나쁜 마감 우세",
  breakout_failure: "⑥ 돌파 실패(스쿼트)",
};

const SIGNAL_META: Record<HoldingFeedback["signal"], { label: string; bg: string; fg: string }> = {
  stop_loss: { label: "🔴 손절", bg: "rgba(255,180,171,0.18)", fg: "#ffb4ab" },
  early_sell: { label: "🟠 조기 매도 신호", bg: "rgba(251,146,60,0.18)", fg: "#fb923c" },
  hold: { label: "🟢 정상 보유", bg: "rgba(16,185,129,0.18)", fg: "#34d399" },
  no_data: { label: "⚫ 데이터 없음", bg: "rgba(148,163,184,0.18)", fg: "#94a3b8" },
};

const STATUS_MARK: Record<HoldingRule["status"], { mark: string; cls: string }> = {
  violation: { mark: "✗", cls: "text-[#ffb4ab]" },
  pass: { mark: "✓", cls: "text-[#34d399]" },
  pending: { mark: "―", cls: "text-on-surface-variant/50" },
  na: { mark: "―", cls: "text-on-surface-variant/50" },
};

function fmtWon(v?: number | null): string {
  return v == null ? "-" : Math.round(v).toLocaleString();
}

export function SepaHoldingsSection({ data }: { data: HoldingsFeedbackFile | null }) {
  const holdings = data?.holdings ?? [];
  if (holdings.length === 0) return null;
  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">monitor_heart</span>
        보유 종목 점검
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">
          매도 규칙 위반 감시 · 기준일 {data?.asof ?? "-"}
        </span>
      </h3>
      <div className="grid gap-4 sm:grid-cols-2">
        {holdings.map((h) => {
          const meta = SIGNAL_META[h.signal] ?? SIGNAL_META.no_data;
          const badgeLabel =
            h.signal === "early_sell" ? `${meta.label} · 위반 ${h.violation_count}건` : meta.label;
          return (
            <div key={h.code} className="bg-surface-container-low rounded-xl ghost-border p-4 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="font-bold text-on-surface">
                  {h.name}
                  <span className="text-xs font-normal text-on-surface-variant/50 ml-1.5">{h.code}</span>
                </div>
                <span
                  className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                  style={{ backgroundColor: meta.bg, color: meta.fg }}
                >
                  {badgeLabel}
                </span>
              </div>
              <div className="text-xs text-on-surface-variant space-y-0.5">
                <p>
                  {h.buy_date} 매수 {fmtWon(h.buy_price)}원 → 현재 {fmtWon(h.current_price)}원{" "}
                  <strong style={{ color: (h.profit_pct ?? 0) >= 0 ? "#34d399" : "#ffb4ab" }}>
                    {h.profit_pct != null ? `${h.profit_pct > 0 ? "+" : ""}${h.profit_pct}%` : "-"}
                  </strong>
                </p>
                <p className="text-on-surface-variant/70">
                  손절선 {fmtWon(h.stop_price)}원({h.stop_loss_pct}%) · 손절까지{" "}
                  {h.pct_to_stop != null ? `${h.pct_to_stop}%` : "-"} · 돌파일 {h.breakout_date ?? "-"}
                  {h.breakout_date_estimated ? " (매수일 추정)" : ""}
                </p>
              </div>
              {h.rules.length > 0 && (
                <ul className="text-[11px] space-y-1 pt-2 border-t border-outline-variant/10">
                  {h.rules.map((r) => {
                    const sm = STATUS_MARK[r.status] ?? STATUS_MARK.na;
                    return (
                      <li key={r.id} className="flex gap-1.5 leading-relaxed">
                        <span className={`${sm.cls} font-bold shrink-0`}>{sm.mark}</span>
                        <span className="text-on-surface-variant">
                          <strong className={r.status === "violation" ? "text-[#ffb4ab]" : "text-on-surface"}>
                            {RULE_LABELS[r.id] ?? r.id}
                          </strong>{" "}
                          — {r.detail}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
