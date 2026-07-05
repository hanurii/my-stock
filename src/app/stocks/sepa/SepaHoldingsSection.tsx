// 보유 종목 점검 — 미너비니 매도 규칙 위반 피드백 (서버 렌더 전용, 상호작용 없음)

import type { ReactNode } from "react";

export interface HoldingRule {
  id: string;
  status: "violation" | "pass" | "pending" | "na" | "watch";
  detail: string;
}
export interface AccumulationSignal { id: string; status: "met" | "unmet" | "pending"; detail: string; }
export interface Accumulation { window: string; elapsed: number; signals: AccumulationSignal[]; }
export interface MvpCheck { ok: boolean | null; detail: string; }
export interface Mvp { status: "yes" | "no" | "pending"; m: MvpCheck; v: MvpCheck; p: MvpCheck; }
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
  extension_pct?: number | null;
  accumulation?: Accumulation;
  mvp?: Mvp;
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
  watch: { mark: "🟡", cls: "text-[#fbbf24]" },
};

const ACC_MARK: Record<AccumulationSignal["status"], { mark: string; cls: string }> = {
  met: { mark: "✓", cls: "text-[#34d399]" },
  unmet: { mark: "○", cls: "text-on-surface-variant/50" },
  pending: { mark: "―", cls: "text-on-surface-variant/40" },
};
const ACC_META: Record<string, { label: string; tip: string }> = {
  up_days_dominant: { label: "상승일 우세", tip: "돌파 후 15거래일 중 상승 마감일이 하락 마감일보다 많으면 충족. 기관 매집 정황. 숫자 = 상승 · 하락 마감일." },
  quality_closes: { label: "양질의 종가", tip: "그날 고저 범위의 상단 절반에서 마감(좋은 마감)한 날이 하단 절반 마감(나쁜 마감)보다 많으면 충족. 변동폭 1% 미만 tight 눌림은 나쁜 마감서 제외." },
  up_streak_7: { label: "연속 상승 7일↑", tip: "상승 마감이 며칠 연속됐는지의 최고 기록. 7~8일 이상을 미너비니는 가장 이상적 신호로 봄." },
};
const MVP_META = {
  m: { label: "M 모멘텀", tip: "돌파 후 15일 중 상승 마감이 12일 이상이면 충족." },
  v: { label: "V 거래량", tip: "돌파 후 15일 평균 거래량이 돌파 직전 15일 평균 대비 25% 이상 늘면 충족." },
  p: { label: "P 가격", tip: "돌파 후 15일간 최고 종가가 돌파일 종가 대비 20% 이상 오르면 충족." },
} as const;

function fmtWon(v?: number | null): string {
  return v == null ? "-" : Math.round(v).toLocaleString();
}

export function SepaHoldingsSection({ data }: { data: HoldingsFeedbackFile | null }) {
  const holdings = data?.holdings ?? [];
  if (holdings.length === 0) return null;
  const Tip = ({ tip, children }: { tip: string; children: ReactNode }) => (
    <span className="relative group cursor-help outline-none" tabIndex={0}>
      <span className="border-b border-dotted border-on-surface-variant/40">{children}</span>
      <span role="tooltip"
        className="pointer-events-none absolute left-0 bottom-full mb-2 w-56 max-w-[74vw] z-30
                   rounded-lg border border-outline-variant/30 bg-surface-container p-2.5 text-[11px]
                   font-normal leading-relaxed text-on-surface shadow-lg opacity-0 invisible
                   transition-opacity group-hover:opacity-100 group-hover:visible group-focus:opacity-100 group-focus:visible">
        {tip}
      </span>
    </span>
  );
  const mvpMark = (ok: boolean | null) =>
    ok === true ? ACC_MARK.met : ok === false ? ACC_MARK.unmet : ACC_MARK.pending;
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
                <div className="flex flex-wrap gap-1.5 justify-end">
                  <span
                    className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                    style={{ backgroundColor: meta.bg, color: meta.fg }}
                  >
                    {badgeLabel}
                  </span>
                  {h.mvp?.status === "yes" && (
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded tracking-wide"
                      style={{ backgroundColor: "rgba(167,139,250,0.16)", color: "#a78bfa",
                               border: "1px solid rgba(167,139,250,0.42)" }}>MVP</span>
                  )}
                  {h.extension_pct != null && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                      style={{ backgroundColor: "rgba(148,163,184,0.12)", color: "#94a3b8" }}>
                      확장 {h.extension_pct > 0 ? "+" : ""}{h.extension_pct}%
                    </span>
                  )}
                </div>
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
              {h.accumulation && (
                <div className="pt-2 border-t border-outline-variant/10">
                  <div className="text-[10px] font-bold tracking-wider text-on-surface-variant/50 mb-1.5 uppercase">
                    매집 신호 <span className="font-normal normal-case text-on-surface-variant/70">· {h.accumulation.window}{h.accumulation.elapsed < 15 ? " 진행중" : ""}</span>
                  </div>
                  <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                    {h.accumulation.signals.map((sg) => {
                      const m = ACC_MARK[sg.status]; const meta = ACC_META[sg.id];
                      return (
                        <li key={sg.id} className="flex gap-1.5 leading-relaxed">
                          <span className={`${m.cls} font-bold shrink-0`}>{m.mark}</span>
                          <span className="text-on-surface-variant">
                            <Tip tip={meta?.tip ?? ""}><span className="text-on-surface">{meta?.label ?? sg.id}</span></Tip>{" "}
                            <span className="text-on-surface-variant/70">{sg.detail}</span>
                          </span>
                        </li>
                      );
                    })}
                    {h.mvp && (["m", "v", "p"] as const).map((k) => {
                      const c = h.mvp![k]; const mk = mvpMark(c.ok); const meta = MVP_META[k];
                      return (
                        <li key={k} className="flex gap-1.5 leading-relaxed">
                          <span className={`${mk.cls} font-bold shrink-0`}>{mk.mark}</span>
                          <span className="text-on-surface-variant">
                            <Tip tip={meta.tip}><span className="text-on-surface">{meta.label}</span></Tip>{" "}
                            <span className="text-on-surface-variant/70">{c.detail}</span>
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
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
