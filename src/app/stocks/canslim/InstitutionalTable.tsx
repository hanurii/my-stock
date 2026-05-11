"use client";

import { Fragment, useState } from "react";

interface ReporterHistory {
  rcept_dt: string;
  stkrt: number;
  stkrt_irds: number;
}

export interface IReporter {
  name: string;
  category: "korean_am" | "global_am" | "pension" | "other";
  current_stkrt: number;
  peak_stkrt: number;
  first_rcept_dt: string;
  last_rcept_dt: string;
  filings: number;
  is_active: boolean;
  is_strict_new_1y: boolean;
  is_recent_buyer_90d: boolean;
  is_returning_after_gap: boolean;
  is_new_or_increasing_1y: boolean;
  is_exit_1y: boolean;
  stkrt_history: ReporterHistory[];
}

interface MajorstockSummary {
  korean_am_count: number;
  global_am_count: number;
  pension_count: number;
  new_or_increasing_1y: Array<{ name: string; category: string; label: string; first_rcept_dt: string; current_stkrt: number }>;
  strict_new_count: number;
  recent_buyer_count: number;
  returning_count: number;
  exits_1y: Array<{ name: string; category: string; peak_stkrt: number; current_stkrt: number; last_rcept_dt: string }>;
  total_stkrt_change_1y_pct: number;
  any_institutional: boolean;
}

interface OrgFlow {
  days_covered: number;
  first_date: string | null;
  last_date: string | null;
  cum_60d: number;
  cum_prev_60d: number;
  trend_60d: "up" | "flat" | "down";
  trend_qoq: "improving" | "flat" | "deteriorating";
  is_outflow: boolean;
  is_consistently_declining: boolean;
  is_sharp_drop_qoq: boolean;
}

export interface ICandidate {
  code: string;
  name: string;
  corp_code?: string;
  via_parent?: string | null;
  passes_i: boolean;
  exclusion_reasons: string[];
  warning_signals: string[];
  fetch_error?: string;
  i_analysis?: {
    majorstock: {
      reporters: IReporter[];
      summary: MajorstockSummary;
    };
    org_flow: OrgFlow & { daily?: Array<{ date: string; close: number; org_net: number; fgn_net: number }> };
  };
}

interface Props {
  candidates: ICandidate[];
}

function fmtShares(n: number): string {
  if (n === 0) return "0";
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "+";
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(1)}K`;
  return `${sign}${abs}`;
}

function categoryBadge(cat: string): { label: string; color: string } {
  switch (cat) {
    case "korean_am":
      return { label: "🇰🇷 운용", color: "#a8b5d0" };
    case "global_am":
      return { label: "🌐 운용", color: "#95d3ba" };
    case "pension":
      return { label: "💼 연기금", color: "#e9c176" };
    default:
      return { label: "기타", color: "var(--on-surface-variant)" };
  }
}

function newLabel(reporter: IReporter): string | null {
  if (reporter.is_strict_new_1y) return "🆕 신규";
  if (reporter.is_returning_after_gap) return "🔄 재등장";
  if (reporter.is_recent_buyer_90d) return "➕ 추가매수";
  return null;
}

function trendQoqLabel(t: string): { text: string; color: string } {
  if (t === "improving") return { text: "↑ 개선", color: "#95d3ba" };
  if (t === "deteriorating") return { text: "↓ 악화", color: "#ffb4ab" };
  return { text: "→ 보합", color: "var(--on-surface-variant)" };
}

export function InstitutionalTable({ candidates }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (code: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  if (candidates.length === 0) {
    return <p className="text-sm text-on-surface-variant">표시할 종목이 없습니다.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl ghost-border">
      <table className="w-full text-xs">
        <thead className="bg-surface-container/40 text-on-surface-variant/80">
          <tr>
            <th className="text-left px-3 py-2.5 font-medium">종목</th>
            <th className="text-right px-2 py-2.5 font-medium" title="현재 5% 이상 보유 운용사·연기금 수">
              5%+ 기관
            </th>
            <th className="text-right px-2 py-2.5 font-medium" title="strict 신규 + 추가매수 + 재등장 합계">
              신규 시그널
            </th>
            <th className="text-right px-2 py-2.5 font-medium">1년 지분 변동</th>
            <th className="text-right px-2 py-2.5 font-medium">60일 기관 매매</th>
            <th className="text-center px-2 py-2.5 font-medium">분기 추세</th>
            <th className="text-left px-3 py-2.5 font-medium">상태</th>
            <th className="w-8" aria-hidden></th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => {
            const isExpanded = expanded.has(c.code);
            const analysis = c.i_analysis;
            const s = analysis?.majorstock.summary;
            const o = analysis?.org_flow;
            const totalInst = s ? s.korean_am_count + s.global_am_count + s.pension_count : 0;
            const newSig = s ? s.strict_new_count + s.recent_buyer_count + s.returning_count : 0;
            const grayed = !c.passes_i;
            const rowClass = grayed ? "opacity-55" : "";
            const qoq = o ? trendQoqLabel(o.trend_qoq) : { text: "—", color: "var(--on-surface-variant)" };

            return (
              <Fragment key={c.code}>
                <tr
                  className={`border-t border-on-surface/5 hover:bg-surface-container/30 cursor-pointer transition-colors ${rowClass}`}
                  onClick={() => toggle(c.code)}
                >
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-shrink-0">
                        {grayed ? (
                          <span className="material-symbols-outlined text-base text-on-surface-variant/40">
                            visibility_off
                          </span>
                        ) : (
                          <span className="material-symbols-outlined text-base text-primary">
                            radio_button_checked
                          </span>
                        )}
                      </div>
                      <div>
                        <div className="font-medium text-on-surface">{c.name}</div>
                        <div className="text-[10px] text-on-surface-variant/60">{c.code}</div>
                      </div>
                    </div>
                  </td>
                  <td className="text-right px-2 py-3 text-on-surface-variant">
                    {analysis ? (
                      <span className="font-mono">
                        {totalInst}
                        {s && (
                          <span className="text-[10px] text-on-surface-variant/60 ml-1">
                            ({s.korean_am_count}/{s.global_am_count}/{s.pension_count})
                          </span>
                        )}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="text-right px-2 py-3 font-mono">
                    {analysis ? (
                      <span className={newSig === 0 ? "text-on-surface-variant/50" : "text-on-surface"}>
                        {newSig}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td
                    className="text-right px-2 py-3 font-mono"
                    style={{
                      color:
                        s === undefined
                          ? "var(--on-surface-variant)"
                          : s.total_stkrt_change_1y_pct > 0
                          ? "#95d3ba"
                          : s.total_stkrt_change_1y_pct < 0
                          ? "#ffb4ab"
                          : "var(--on-surface-variant)",
                    }}
                  >
                    {s ? `${s.total_stkrt_change_1y_pct >= 0 ? "+" : ""}${s.total_stkrt_change_1y_pct.toFixed(2)}%p` : "—"}
                  </td>
                  <td
                    className="text-right px-2 py-3 font-mono"
                    style={{
                      color:
                        o === undefined
                          ? "var(--on-surface-variant)"
                          : o.cum_60d > 0
                          ? "#95d3ba"
                          : o.cum_60d < 0
                          ? "#ffb4ab"
                          : "var(--on-surface-variant)",
                    }}
                  >
                    {o ? fmtShares(o.cum_60d) : "—"}
                  </td>
                  <td className="text-center px-2 py-3" style={{ color: qoq.color }}>
                    {qoq.text}
                  </td>
                  <td className="px-3 py-3">
                    {grayed ? (
                      <div className="space-y-1">
                        <span className="inline-block text-[10px] px-1.5 py-0.5 rounded bg-on-surface/5 text-on-surface-variant/80">
                          회색 처리
                        </span>
                        <div className="text-[10px] text-on-surface-variant/70 max-w-xs leading-tight">
                          {c.exclusion_reasons.slice(0, 2).join("; ")}
                        </div>
                      </div>
                    ) : c.warning_signals.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {c.warning_signals.slice(0, 2).map((w, i) => (
                          <span
                            key={i}
                            className="inline-block text-[10px] px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-300/90"
                            title={w}
                          >
                            ⚠ {w.length > 24 ? w.slice(0, 24) + "…" : w}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-[10px] text-on-surface-variant/50">—</span>
                    )}
                  </td>
                  <td className="px-1 text-on-surface-variant/60">
                    <span className="material-symbols-outlined text-base">
                      {isExpanded ? "expand_less" : "expand_more"}
                    </span>
                  </td>
                </tr>
                {isExpanded && analysis && (
                  <tr className={`border-t border-on-surface/5 bg-surface-container/15 ${rowClass}`}>
                    <td colSpan={8} className="px-4 py-4">
                      <div className="space-y-4">
                        {c.exclusion_reasons.length > 0 && (
                          <div className="rounded-lg p-3 bg-on-surface/5">
                            <p className="text-[11px] font-medium text-on-surface-variant mb-1">제외 사유</p>
                            <ul className="space-y-1 text-[11px] text-on-surface-variant/80">
                              {c.exclusion_reasons.map((r, i) => (
                                <li key={i}>• {r}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {c.warning_signals.length > 0 && (
                          <div className="rounded-lg p-3 bg-amber-400/5">
                            <p className="text-[11px] font-medium text-amber-300/90 mb-1">경고 시그널</p>
                            <ul className="space-y-1 text-[11px] text-on-surface-variant/80">
                              {c.warning_signals.map((w, i) => (
                                <li key={i}>• {w}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div>
                          <p className="text-[11px] font-medium text-on-surface-variant mb-2">
                            5%+ 보고자 ({analysis.majorstock.reporters.filter((r) => r.is_active).length})
                          </p>
                          <div className="space-y-1.5">
                            {analysis.majorstock.reporters.filter((r) => r.is_active).map((r) => {
                              const badge = categoryBadge(r.category);
                              const nl = newLabel(r);
                              return (
                                <div
                                  key={r.name}
                                  className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface-container/40 text-[11px]"
                                >
                                  <span className="font-mono text-[10px]" style={{ color: badge.color }}>
                                    {badge.label}
                                  </span>
                                  <span className="flex-1 truncate text-on-surface">{r.name}</span>
                                  <span className="font-mono text-on-surface-variant">
                                    {r.current_stkrt.toFixed(2)}%
                                  </span>
                                  <span className="text-[10px] text-on-surface-variant/60">
                                    {r.first_rcept_dt}
                                  </span>
                                  {nl && (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                                      {nl}
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                            {analysis.majorstock.reporters.filter((r) => r.is_active).length === 0 && (
                              <p className="text-[11px] text-on-surface-variant/60">
                                현재 5% 이상 보유 중인 운용사·연기금 없음
                              </p>
                            )}
                          </div>
                        </div>

                        {analysis.majorstock.summary.exits_1y.length > 0 && (
                          <div>
                            <p className="text-[11px] font-medium text-on-surface-variant mb-2">
                              1년 내 5% 이탈 ({analysis.majorstock.summary.exits_1y.length})
                            </p>
                            <div className="space-y-1">
                              {analysis.majorstock.summary.exits_1y.map((e) => (
                                <div
                                  key={e.name}
                                  className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface-container/40 text-[11px]"
                                >
                                  <span className="font-mono text-[10px] text-on-surface-variant/60">
                                    {categoryBadge(e.category).label}
                                  </span>
                                  <span className="flex-1 truncate text-on-surface-variant">{e.name}</span>
                                  <span className="font-mono text-on-surface-variant/70">
                                    {e.peak_stkrt.toFixed(2)}% → 미만
                                  </span>
                                  <span className="text-[10px] text-on-surface-variant/60">{e.last_rcept_dt}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                          <div>
                            <p className="text-on-surface-variant/60 mb-0.5">60일 누적</p>
                            <p
                              className="font-mono font-medium"
                              style={{
                                color:
                                  o!.cum_60d > 0 ? "#95d3ba" : o!.cum_60d < 0 ? "#ffb4ab" : "var(--on-surface)",
                              }}
                            >
                              {fmtShares(o!.cum_60d)}주
                            </p>
                          </div>
                          <div>
                            <p className="text-on-surface-variant/60 mb-0.5">직전 60일</p>
                            <p className="font-mono">{fmtShares(o!.cum_prev_60d)}주</p>
                          </div>
                          <div>
                            <p className="text-on-surface-variant/60 mb-0.5">분기 추세</p>
                            <p style={{ color: trendQoqLabel(o!.trend_qoq).color }}>
                              {trendQoqLabel(o!.trend_qoq).text}
                            </p>
                          </div>
                          <div>
                            <p className="text-on-surface-variant/60 mb-0.5">수집 기간</p>
                            <p className="text-on-surface-variant/80 text-[10px]">
                              {o!.first_date} ~ {o!.last_date}
                            </p>
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
