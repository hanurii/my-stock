// 보유 종목 점검 — 매도 규칙 위반 + 강세 매도(과열) 감시 (서버 렌더 전용, JS 없음)
import type { ReactNode } from "react";
import { accumTally, ruleTally, strengthTally } from "./holdingsSummary";

export interface HoldingRule { id: string; status: "violation" | "pass" | "pending" | "na" | "watch"; detail: string; }
export interface AccumulationSignal { id: string; status: "met" | "unmet" | "pending"; detail: string; }
export interface Accumulation { window: string; elapsed: number; signals: AccumulationSignal[]; }
export interface MvpCheck { ok: boolean | null; detail: string; }
export interface Mvp { status: "yes" | "no" | "pending"; m: MvpCheck; v: MvpCheck; p: MvpCheck; }
export interface StrengthSignal { id: string; status: "fired" | "clear" | "pending"; detail: string; }
export interface Strength {
  signal: "sell_into_strength" | "none" | "not_extended" | "na";
  extended: boolean; gate_detail: string; count: number; signals: StrengthSignal[];
}
export interface HoldingFeedback {
  code: string; name: string; market?: string | null; buy_date: string; buy_price: number;
  quantity?: number; stop_loss_pct: number; pivot_price?: number | null; pivot_source?: string | null;
  current_price?: number; profit_pct?: number; stop_price?: number; pct_to_stop?: number;
  breakout_date?: string; breakout_date_estimated?: boolean;
  signal: "stop_loss" | "early_sell" | "hold" | "no_data"; violation_count: number; rules: HoldingRule[];
  extension_pct?: number | null; accumulation?: Accumulation; mvp?: Mvp; strength?: Strength;
}
export interface HoldingsFeedbackFile { generated_at?: string; asof?: string; holdings?: HoldingFeedback[]; }

const HEAT = "#f5a9ce";

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

const STRENGTH_MARK: Record<StrengthSignal["status"], { mark: string; cls: string }> = {
  fired: { mark: "🔥", cls: "text-[#f5a9ce]" },
  clear: { mark: "○", cls: "text-on-surface-variant/50" },
  pending: { mark: "―", cls: "text-on-surface-variant/40" },
};
const STRENGTH_META: Record<string, { label: string; tip: string }> = {
  climax_run: { label: "절정 분출", tip: "확장 단계에서 최근 5~15일 +25%(또는 5~10일 +70%) 급등. 상승 가속 = 강세에 이익 확정 검토." },
  blowoff_day: { label: "최대 상승일·변동폭", tip: "돌파 후 최대 상승일(또는 최대 일중 변동폭)이 최근 3거래일 안에 나오면 발화. 상승 모멘텀의 마지막 폭발." },
  exhaustion_gap: { label: "소진성 갭", tip: "최근 3거래일 내 상승 갭(당일 저가가 전일 고가보다 높게 출발). 소진(exhaustion) 신호." },
  distribution: { label: "분산 정황", tip: "대량 거래 반전(장중 신고가→하락 마감) · 처닝(대량인데 가격 진전 없음) · 돌파 후 최대 거래량 하락일 중 하나." },
};

function fmtWon(v?: number | null): string {
  return v == null ? "-" : Math.round(v).toLocaleString();
}

export function SepaHoldingsSection({ data }: { data: HoldingsFeedbackFile | null }) {
  const holdings = data?.holdings ?? [];
  if (holdings.length === 0) return null;

  const Tip = ({ tip, children }: { tip: string; children: ReactNode }) => (
    <span className="relative group/tip cursor-help outline-none" tabIndex={0}>
      <span className="border-b border-dotted border-on-surface-variant/40">{children}</span>
      <span role="tooltip"
        className="pointer-events-none absolute left-0 bottom-full mb-2 w-56 max-w-[74vw] z-30
                   rounded-lg border border-outline-variant/30 bg-surface-container p-2.5 text-[11px]
                   font-normal leading-relaxed text-on-surface shadow-lg opacity-0 invisible
                   transition-opacity group-hover/tip:opacity-100 group-hover/tip:visible
                   group-focus/tip:opacity-100 group-focus/tip:visible">
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
          매도 규칙 위반 · 강세 매도 감시 · 기준일 {data?.asof ?? "-"}
        </span>
      </h3>
      <div className="grid gap-3 sm:grid-cols-2">
        {holdings.map((h) => {
          const meta = SIGNAL_META[h.signal] ?? SIGNAL_META.no_data;
          const badgeLabel =
            h.signal === "early_sell" ? `${meta.label} · 위반 ${h.violation_count}건` : meta.label;
          const sellStrong = h.strength?.signal === "sell_into_strength";
          const acc = accumTally(h.accumulation, h.mvp);
          const rt = ruleTally(h.rules);
          const st = strengthTally(h.strength);

          // 접힘 점수판 텍스트/색
          const accDigest = h.accumulation
            ? acc.complete ? `${acc.met}/6` : `D+${Math.max(h.accumulation.elapsed, 0)}/15`
            : "–";
          const accCls = h.accumulation && acc.complete && acc.met > 0
            ? "text-[#34d399] font-semibold" : "text-on-surface-variant/50";
          const strDigest = !h.strength ? "–"
            : st ? `발화 ${st.fired}/${st.total}`
            : h.strength.signal === "na" ? "피벗 없음" : "확장 전";
          const strCls = st && st.fired > 0 ? "font-semibold" : "text-on-surface-variant/50";
          const weakDigest = rt.violation > 0 ? `위반 ${rt.violation}`
            : rt.watch > 0 ? `관찰 ${rt.watch}` : "위반 0";
          const weakCls = rt.violation > 0 ? "text-[#ffb4ab] font-semibold"
            : rt.watch > 0 ? "text-[#fbbf24] font-semibold" : "text-on-surface-variant/50";

          return (
            <details key={h.code} className="group bg-surface-container-low rounded-xl ghost-border open:border-outline-variant/25">
              <summary className="list-none [&::-webkit-details-marker]:hidden cursor-pointer p-4 flex flex-col gap-2.5">
                {/* 1줄: 이름 + 수익% */}
                <div className="flex items-baseline justify-between gap-2.5">
                  <div className="font-bold text-on-surface">
                    {h.name}
                    <span className="text-xs font-normal text-on-surface-variant/50 ml-1.5">{h.code}</span>
                  </div>
                  <span className="tabular-nums font-bold text-[15px] whitespace-nowrap"
                    style={{ color: (h.profit_pct ?? 0) >= 0 ? "#34d399" : "#ffb4ab" }}>
                    {h.profit_pct != null ? `${h.profit_pct > 0 ? "+" : ""}${h.profit_pct}%` : "-"}
                  </span>
                </div>
                {/* 2줄: 매수→현재 · 손절까지 + 칩 */}
                <div className="flex items-center justify-between gap-2.5 flex-wrap text-[11.5px] text-on-surface-variant tabular-nums">
                  <span>
                    {fmtWon(h.buy_price)}<span className="text-on-surface-variant/50 mx-1">→</span>{fmtWon(h.current_price)}
                    <span className="text-on-surface-variant/50 ml-2">손절까지 {h.pct_to_stop != null ? `${h.pct_to_stop}%` : "-"}</span>
                  </span>
                  <span className="flex gap-1.5">
                    {h.mvp?.status === "yes" && (
                      <span className="text-[10.5px] font-semibold px-1.5 py-0.5 rounded tracking-wide"
                        style={{ backgroundColor: "rgba(167,139,250,0.16)", color: "#a78bfa", border: "1px solid rgba(167,139,250,0.42)" }}>MVP</span>
                    )}
                    {h.extension_pct != null && (
                      <span className="text-[10.5px] font-medium px-1.5 py-0.5 rounded"
                        style={{ backgroundColor: "rgba(148,163,184,0.12)", color: "#94a3b8" }}>
                        확장 {h.extension_pct > 0 ? "+" : ""}{h.extension_pct}%
                      </span>
                    )}
                  </span>
                </div>
                {/* 3줄: 행동 배지 */}
                <div className="flex flex-wrap gap-1.5">
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                    style={{ backgroundColor: meta.bg, color: meta.fg }}>{badgeLabel}</span>
                  {sellStrong && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded whitespace-nowrap"
                      style={{ backgroundColor: "rgba(245,169,206,0.14)", color: HEAT, border: `1px solid rgba(245,169,206,0.34)` }}>
                      🔥 강세 매도 검토
                    </span>
                  )}
                </div>
                {/* 4줄: 3트랙 점수판 + 토글 */}
                <div className="flex items-center justify-between gap-2 border-t border-outline-variant/10 pt-2">
                  <div className="flex items-center gap-2.5 flex-wrap text-[11px]">
                    <span><span className="text-on-surface-variant/60">매집 </span><span className={`tabular-nums ${accCls}`}>{accDigest}</span></span>
                    <span className="w-px h-3 bg-outline-variant/30" />
                    <span><span className="text-on-surface-variant/60">강세 </span><span className={`tabular-nums ${strCls}`} style={st && st.fired > 0 ? { color: HEAT } : undefined}>{strDigest}</span></span>
                    <span className="w-px h-3 bg-outline-variant/30" />
                    <span><span className="text-on-surface-variant/60">약세 </span><span className={`tabular-nums ${weakCls}`}>{weakDigest}</span></span>
                  </div>
                  <span className="flex items-center gap-1 text-[11px] text-on-surface-variant/60 select-none whitespace-nowrap">
                    <span className="group-open:hidden">상세</span>
                    <span className="hidden group-open:inline">접기</span>
                    <span className="material-symbols-outlined text-base transition-transform group-open:rotate-180">expand_more</span>
                  </span>
                </div>
              </summary>

              {/* 펼침 본문 */}
              <div className="px-4 pb-4 flex flex-col gap-3">
                <p className="text-[11.5px] text-on-surface-variant/70 tabular-nums border-t border-outline-variant/10 pt-3">
                  손절선 {fmtWon(h.stop_price)}원({h.stop_loss_pct}%) · 돌파일 {h.breakout_date ?? "-"}
                  {h.breakout_date_estimated ? " (매수일 추정)" : ""}
                </p>

                {/* 매집 신호 */}
                {h.accumulation && (
                  <div className="pt-3 border-t border-outline-variant/10">
                    <div className="text-[10px] font-bold tracking-wider text-on-surface-variant/50 mb-2 uppercase flex items-baseline gap-1.5">
                      매집 신호 <span className="font-normal normal-case tracking-normal text-on-surface-variant/70">· {h.accumulation.window}{h.accumulation.elapsed < 15 ? " 진행중" : ""}</span>
                      <span className="ml-auto font-semibold normal-case tracking-normal text-[#34d399]/90">충족 {acc.met}/6</span>
                    </div>
                    <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                      {h.accumulation.signals.map((sg) => {
                        const m = ACC_MARK[sg.status]; const am = ACC_META[sg.id];
                        return (
                          <li key={sg.id} className="flex gap-1.5 leading-relaxed">
                            <span className={`${m.cls} font-bold shrink-0`}>{m.mark}</span>
                            <span className="text-on-surface-variant">
                              <Tip tip={am?.tip ?? ""}><span className="text-on-surface">{am?.label ?? sg.id}</span></Tip>{" "}
                              <span className="text-on-surface-variant/70">{sg.detail}</span>
                            </span>
                          </li>
                        );
                      })}
                      {h.mvp && (["m", "v", "p"] as const).map((k) => {
                        const c = h.mvp![k]; const mk = mvpMark(c.ok); const mm = MVP_META[k];
                        return (
                          <li key={k} className="flex gap-1.5 leading-relaxed">
                            <span className={`${mk.cls} font-bold shrink-0`}>{mk.mark}</span>
                            <span className="text-on-surface-variant">
                              <Tip tip={mm.tip}><span className="text-on-surface">{mm.label}</span></Tip>{" "}
                              <span className="text-on-surface-variant/70">{c.detail}</span>
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {/* 강세 매도 감시 */}
                {h.strength && (
                  <div className="pt-3" style={{ borderTop: `1px solid rgba(245,169,206,0.34)` }}>
                    <div className="text-[10px] font-bold tracking-wider mb-2 uppercase flex items-baseline gap-1.5" style={{ color: HEAT }}>
                      🔥 강세 매도 감시
                      <span className="font-normal normal-case tracking-normal text-on-surface-variant/60">· {h.strength.gate_detail}</span>
                      {st && <span className="ml-auto font-semibold normal-case tracking-normal" style={{ color: HEAT }}>발화 {st.fired}/{st.total}</span>}
                    </div>
                    {h.strength.extended ? (
                      <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                        {h.strength.signals.map((sg) => {
                          const m = STRENGTH_MARK[sg.status]; const sm = STRENGTH_META[sg.id];
                          return (
                            <li key={sg.id} className="flex gap-1.5 leading-relaxed">
                              <span className={`${m.cls} font-bold shrink-0`}>{m.mark}</span>
                              <span className="text-on-surface-variant">
                                <Tip tip={sm?.tip ?? ""}>
                                  <span style={sg.status === "fired" ? { color: HEAT } : undefined} className={sg.status === "fired" ? "" : "text-on-surface"}>{sm?.label ?? sg.id}</span>
                                </Tip>{" "}
                                <span className="text-on-surface-variant/70">{sg.detail}</span>
                              </span>
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="text-[11.5px] text-on-surface-variant/60 bg-surface-container/30 rounded-lg px-3 py-2 leading-relaxed">
                        {h.strength.signal === "na"
                          ? "피벗 없음 — 판정 불가 (약세 트랙은 매수일 기준으로 계속 감시)"
                          : `확장 전 — 대기 · ${h.strength.gate_detail}. 피벗 위 5% 이상 올라야 강세 신호를 켭니다.`}
                      </p>
                    )}
                  </div>
                )}

                {/* 약세 규칙 (전체 나열) */}
                {h.rules.length > 0 && (
                  <div className="pt-3 border-t border-outline-variant/10">
                    <div className="text-[10px] font-bold tracking-wider text-on-surface-variant/50 mb-2 uppercase flex items-baseline gap-1.5">
                      약세 규칙
                      <span className="ml-auto font-semibold normal-case tracking-normal text-on-surface-variant/70">
                        통과 {rt.pass}{rt.violation > 0 ? ` · 위반 ${rt.violation}` : ""}{rt.watch > 0 ? ` · 관찰 ${rt.watch}` : ""}
                      </span>
                    </div>
                    <ul className="text-[11px] space-y-1.5">
                      {h.rules.map((r) => {
                        const sm = STATUS_MARK[r.status] ?? STATUS_MARK.na;
                        return (
                          <li key={r.id} className="flex gap-1.5 leading-relaxed">
                            <span className={`${sm.cls} font-bold shrink-0 w-3 text-center`}>{sm.mark}</span>
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
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
