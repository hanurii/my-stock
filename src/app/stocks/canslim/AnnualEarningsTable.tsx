"use client";

import { Fragment, useMemo, useState } from "react";

export interface ACriterion {
  main_track_pass: boolean;
  annual_eps: [string, number][];
  annual_roe: [string, number][];
  annual_cps: [string, number][];
  three_year_growths: number[];
  three_year_avg_growth: number | null;
  five_year_consecutive_increase: boolean;
  consecutive_3y_increase: boolean;
  latest_roe: number | null;
  latest_cps: number | null;
  latest_eps: number | null;
  latest_cps_eps_ratio: number | null;
  latest_quarter_yoy: number | null;
  deceleration_gate_pass: boolean;
  deceleration_gate_threshold: number | null;
  induty_code: string | null;
  cyclical: boolean;
  earnings_stability_score: number | null;
  earnings_stability_detail: string;
  badges: string[];
  fail_reasons: string[];
}

export interface AnnualCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  criteria_a: ACriterion;
  criteria_c_summary: {
    yoy_pct: number | null;
    latest_quarter: string | null;
    sales_yoy_pct: number | null;
  };
}

type SortKey = "three_year_avg_growth" | "latest_roe" | "earnings_stability_score" | "market_cap";
type MarketFilter = "ALL" | "KOSPI" | "KOSDAQ";

interface Props {
  candidates: AnnualCandidate[];
}

function fmtCap(eok: number): string {
  if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`;
  return `${eok.toLocaleString()}억`;
}

function fmtPct(n: number | null): string {
  if (n === null || n === undefined) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function growthColor(n: number | null): string {
  if (n === null) return "var(--on-surface-variant)";
  if (n >= 50) return "#10b981";
  if (n >= 25) return "#34d399";
  if (n > 0) return "#a8b5d0";
  return "#ffb4ab";
}

function roeColor(n: number | null): string {
  if (n === null) return "var(--on-surface-variant)";
  if (n >= 25) return "#10b981";
  if (n >= 17) return "#34d399";
  if (n >= 10) return "#a8b5d0";
  return "#ffb4ab";
}

function stabilityColor(n: number | null): string {
  if (n === null) return "var(--on-surface-variant)";
  // 한국 보정: <30 우수 / 30~40 보통 / >40 부족
  if (n < 30) return "#10b981";
  if (n <= 40) return "#a8b5d0";
  return "#ffb4ab";
}

function badgeStyle(label: string): string {
  if (label === "탁월 ROE") return "bg-emerald-600/20 text-emerald-300 font-bold";
  if (label === "글로벌 ROE") return "bg-emerald-500/15 text-emerald-300";
  if (label === "5년 연속 성장") return "bg-emerald-500/15 text-emerald-300";
  if (label === "현금창출력 우수") return "bg-cyan-500/15 text-cyan-300";
  if (label === "안정성 우수") return "bg-primary/15 text-primary";
  if (label === "안정성 보통") return "bg-on-surface/10 text-on-surface-variant";
  if (label === "안정성 부족") return "bg-amber-500/15 text-amber-400";
  if (label === "사상 최고치") return "bg-tertiary/15 text-tertiary font-medium";
  return "bg-on-surface/10 text-on-surface-variant";
}

export function AnnualEarningsTable({ candidates }: Props) {
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("three_year_avg_growth");
  const [sortDesc, setSortDesc] = useState(true);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let arr = candidates;
    if (marketFilter !== "ALL") arr = arr.filter((c) => c.market === marketFilter);
    return [...arr].sort((a, b) => {
      const av = readSortValue(a, sortKey);
      const bv = readSortValue(b, sortKey);
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return sortDesc ? bv - av : av - bv;
    });
  }, [candidates, marketFilter, sortKey, sortDesc]);

  const SortHeader = ({ k, label }: { k: SortKey; label: string }) => (
    <button
      onClick={() => {
        if (sortKey === k) setSortDesc(!sortDesc);
        else {
          setSortKey(k);
          setSortDesc(true);
        }
      }}
      className={`text-left flex items-center gap-1 ${
        sortKey === k ? "text-primary" : "text-on-surface-variant/70 hover:text-on-surface-variant"
      }`}
    >
      {label}
      {sortKey === k && (
        <span className="material-symbols-outlined text-sm">
          {sortDesc ? "arrow_downward" : "arrow_upward"}
        </span>
      )}
    </button>
  );

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <div className="flex gap-1 rounded-md bg-surface-container-low p-1">
          {(["ALL", "KOSPI", "KOSDAQ"] as MarketFilter[]).map((m) => (
            <button
              key={m}
              onClick={() => setMarketFilter(m)}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                marketFilter === m
                  ? "bg-primary/15 text-primary"
                  : "text-on-surface-variant/70 hover:bg-surface-container/50"
              }`}
            >
              {m === "ALL" ? "전체" : m}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-container/40 text-xs">
              <tr className="text-left">
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">종목</th>
                <th className="px-3 py-2.5 font-medium">
                  <SortHeader k="three_year_avg_growth" label="3년 평균 EPS 증가" />
                </th>
                <th className="px-3 py-2.5 font-medium hidden sm:table-cell">
                  <SortHeader k="latest_roe" label="ROE" />
                </th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden md:table-cell">3년 EPS 추이</th>
                <th className="px-3 py-2.5 font-medium hidden lg:table-cell">
                  <SortHeader k="earnings_stability_score" label="안정성 지수" />
                </th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">배지</th>
                <th className="px-3 py-2.5 font-medium hidden lg:table-cell">
                  <SortHeader k="market_cap" label="시총" />
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-on-surface-variant/60 text-sm">
                    A 메인 트랙을 통과한 종목이 없습니다.
                    <br />
                    <span className="text-[11px] text-on-surface-variant/50">
                      (A는 3년 연속 EPS 증가 + 평균 ≥25% + ROE ≥17% + 둔화 게이트 + 비경기민감 5중 AND 조건)
                    </span>
                  </td>
                </tr>
              )}
              {filtered.map((c) => {
                const a = c.criteria_a;
                const isOpen = expandedCode === c.code;
                return (
                  <Fragment key={c.code}>
                    <tr
                      onClick={() => setExpandedCode(isOpen ? null : c.code)}
                      className={`border-t border-on-surface/5 cursor-pointer hover:bg-surface-container/30 ${
                        isOpen ? "bg-surface-container/20" : ""
                      }`}
                    >
                      <td className="px-3 py-2.5">
                        <div className="flex flex-col">
                          <span className="font-medium text-on-surface">{c.name}</span>
                          <span className="text-[11px] text-on-surface-variant/60">
                            {c.code} · {c.market}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 font-medium" style={{ color: growthColor(a.three_year_avg_growth) }}>
                        {fmtPct(a.three_year_avg_growth)}
                      </td>
                      <td
                        className="px-3 py-2.5 hidden sm:table-cell font-medium"
                        style={{ color: roeColor(a.latest_roe) }}
                      >
                        {a.latest_roe !== null ? `${a.latest_roe.toFixed(1)}%` : "—"}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                        {a.three_year_growths.length > 0 ? (
                          <span className="font-mono text-on-surface-variant">
                            {a.three_year_growths.map((g, i) => (
                              <span key={i}>
                                <span style={{ color: growthColor(g) }}>{fmtPct(g)}</span>
                                {i < a.three_year_growths.length - 1 && <span className="text-on-surface-variant/40 mx-1">→</span>}
                              </span>
                            ))}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td
                        className="px-3 py-2.5 hidden lg:table-cell text-xs"
                        style={{ color: stabilityColor(a.earnings_stability_score) }}
                      >
                        {a.earnings_stability_score !== null ? a.earnings_stability_score : "—"}
                      </td>
                      <td className="px-3 py-2.5 hidden lg:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {a.badges.map((b) => (
                            <span key={b} className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${badgeStyle(b)}`}>
                              {b}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-on-surface-variant text-xs hidden lg:table-cell">
                        {fmtCap(c.market_cap_eok)}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-surface-container/10 border-t border-on-surface/5">
                        <td colSpan={7} className="px-3 py-4 text-xs text-on-surface-variant">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                            <div>
                              <p className="font-medium text-on-surface mb-2 flex items-center gap-2">
                                <span className="material-symbols-outlined text-sm text-primary">show_chart</span>
                                연간 EPS 추이
                              </p>
                              {a.annual_eps.length > 0 ? (
                                <ul className="space-y-1">
                                  {a.annual_eps.map(([k, v]) => (
                                    <li key={k} className="flex items-baseline gap-3 leading-relaxed">
                                      <span className="text-on-surface-variant/60 font-mono text-[11px] w-14">{k.slice(0, 4)}</span>
                                      <span className="font-medium text-on-surface">{v.toLocaleString()}원</span>
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p>연간 EPS 데이터 없음.</p>
                              )}
                            </div>
                            <div>
                              <p className="font-medium text-on-surface mb-2 flex items-center gap-2">
                                <span className="material-symbols-outlined text-sm text-primary">percent</span>
                                ROE 추이
                              </p>
                              {a.annual_roe.length > 0 ? (
                                <ul className="space-y-1">
                                  {a.annual_roe.map(([k, v]) => (
                                    <li key={k} className="flex items-baseline gap-3 leading-relaxed">
                                      <span className="text-on-surface-variant/60 font-mono text-[11px] w-14">{k.slice(0, 4)}</span>
                                      <span className="font-medium" style={{ color: roeColor(v) }}>{v.toFixed(1)}%</span>
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p>ROE 데이터 없음.</p>
                              )}
                            </div>
                            <div className="md:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2 text-[11px]">
                              <div className="bg-surface-container/40 rounded-md p-2.5">
                                <p className="text-on-surface-variant/60 mb-0.5">직전 분기 EPS YoY</p>
                                <p className="font-medium text-on-surface" style={{ color: growthColor(a.latest_quarter_yoy) }}>
                                  {fmtPct(a.latest_quarter_yoy)}
                                </p>
                                <p className="text-on-surface-variant/50 mt-0.5">
                                  둔화 게이트: ≥{a.deceleration_gate_threshold !== null ? `${a.deceleration_gate_threshold.toFixed(1)}%` : "—"}
                                  {" "}
                                  {a.deceleration_gate_pass ? "✓" : "✗"}
                                </p>
                              </div>
                              <div className="bg-surface-container/40 rounded-md p-2.5">
                                <p className="text-on-surface-variant/60 mb-0.5">CPS / EPS 비율</p>
                                <p className="font-medium text-on-surface">
                                  {a.latest_cps_eps_ratio !== null ? `${a.latest_cps_eps_ratio.toFixed(2)}x` : "미수집"}
                                </p>
                                <p className="text-on-surface-variant/50 mt-0.5">≥1.20 시 가점 배지</p>
                              </div>
                              <div className="bg-surface-container/40 rounded-md p-2.5">
                                <p className="text-on-surface-variant/60 mb-0.5">안정성 지수</p>
                                <p className="font-medium" style={{ color: stabilityColor(a.earnings_stability_score) }}>
                                  {a.earnings_stability_score !== null ? a.earnings_stability_score : "평가 불가"}
                                </p>
                                <p className="text-on-surface-variant/50 mt-0.5">{a.earnings_stability_detail || "—"}</p>
                              </div>
                              <div className="bg-surface-container/40 rounded-md p-2.5">
                                <p className="text-on-surface-variant/60 mb-0.5">산업 코드 (KSIC)</p>
                                <p className="font-medium text-on-surface">{a.induty_code ?? "—"}</p>
                                <p className="text-on-surface-variant/50 mt-0.5">
                                  {a.cyclical ? "경기민감주 (제외)" : "비경기민감"}
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
      </div>
    </div>
  );
}

function readSortValue(c: AnnualCandidate, k: SortKey): number | null {
  const a = c.criteria_a;
  if (k === "three_year_avg_growth") return a.three_year_avg_growth;
  if (k === "latest_roe") return a.latest_roe;
  if (k === "earnings_stability_score") return a.earnings_stability_score === null ? null : -a.earnings_stability_score;
  if (k === "market_cap") return c.market_cap_eok;
  return null;
}

// ────────────────────────────────────────────────────────
// 턴어라운드 트랙 — 별도 컴포넌트 (메인 트랙 미충족 V자 회복주)
// ────────────────────────────────────────────────────────

export interface TurnaroundCriterion {
  turnaround_pass: boolean;
  preliminary_turnaround_pass: boolean;
  annual_eps: [string, number][];
  annual_roe: [string, number][];
  latest_annual_yoy: number | null;
  two_quarter_surge: boolean;
  two_quarter_surge_detail: string;
  preliminary_two_quarter_surge: boolean;
  ttm_high_ratio: number | null;
  is_all_time_high: boolean;
  latest_quarter_yoy: number | null;
  induty_code: string | null;
  cyclical: boolean;
  earnings_stability_score: number | null;
  earnings_stability_detail: string;
  latest_roe: number | null;
  badges: string[];
  fail_reasons: string[];
}

export interface TurnaroundCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  criteria_turnaround: TurnaroundCriterion;
  is_preliminary?: boolean;
  criteria_c_summary: {
    yoy_pct: number | null;
    latest_quarter: string | null;
    sales_yoy_pct: number | null;
  };
}

interface TurnaroundProps {
  candidates: TurnaroundCandidate[];
}

export function TurnaroundTable({ candidates }: TurnaroundProps) {
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const sorted = useMemo(() => {
    return [...candidates].sort((a, b) => {
      // 정통 턴어라운드 우선, 예비는 그 아래
      const aPrelim = a.is_preliminary ? 1 : 0;
      const bPrelim = b.is_preliminary ? 1 : 0;
      if (aPrelim !== bPrelim) return aPrelim - bPrelim;
      const av = a.criteria_turnaround.latest_annual_yoy ?? -Infinity;
      const bv = b.criteria_turnaround.latest_annual_yoy ?? -Infinity;
      return bv - av;
    });
  }, [candidates]);

  return (
    <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-surface-container/40 text-xs">
            <tr className="text-left">
              <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">종목</th>
              <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">직전 1년 EPS YoY</th>
              <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden sm:table-cell">2분기 급증</th>
              <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden md:table-cell">TTM / 사상 최고</th>
              <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden md:table-cell">ROE</th>
              <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">배지</th>
              <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">시총</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-on-surface-variant/60 text-sm">
                  턴어라운드 후보가 없습니다.
                </td>
              </tr>
            )}
            {sorted.map((c) => {
              const t = c.criteria_turnaround;
              const isOpen = expandedCode === c.code;
              return (
                <Fragment key={c.code}>
                  <tr
                    onClick={() => setExpandedCode(isOpen ? null : c.code)}
                    className={`border-t border-on-surface/5 cursor-pointer hover:bg-surface-container/30 ${
                      isOpen ? "bg-surface-container/20" : ""
                    }`}
                  >
                    <td className="px-3 py-2.5">
                      <div className="flex flex-col">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-on-surface">{c.name}</span>
                          {c.is_preliminary && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 font-medium" title="정통 턴어라운드 한두 항목 약간 미달 — 다음 분기 잡힐 가능성">
                              예비
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] text-on-surface-variant/60">
                          {c.code} · {c.market}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 font-medium" style={{ color: growthColor(t.latest_annual_yoy) }}>
                      {t.latest_annual_yoy === 999.99 ? "흑자전환" : fmtPct(t.latest_annual_yoy)}
                    </td>
                    <td className="px-3 py-2.5 hidden sm:table-cell text-xs text-on-surface-variant">
                      {t.two_quarter_surge_detail || "—"}
                    </td>
                    <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                      {t.is_all_time_high ? (
                        <span className="text-tertiary font-medium">사상 최고</span>
                      ) : t.ttm_high_ratio !== null ? (
                        <span className="text-on-surface-variant">{(t.ttm_high_ratio * 100).toFixed(0)}%</span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-2.5 hidden md:table-cell text-xs font-medium" style={{ color: roeColor(t.latest_roe) }}>
                      {t.latest_roe !== null ? `${t.latest_roe.toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-3 py-2.5 hidden lg:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {t.badges.map((b) => (
                          <span key={b} className={`text-[10px] px-1.5 py-0.5 rounded ${badgeStyle(b)}`}>
                            {b}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-on-surface-variant text-xs hidden lg:table-cell">
                      {fmtCap(c.market_cap_eok)}
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="bg-surface-container/10 border-t border-on-surface/5">
                      <td colSpan={7} className="px-3 py-4 text-xs text-on-surface-variant">
                        {c.is_preliminary && (
                          <PreliminaryReasonPanel t={t} />
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                          <div>
                            <p className="font-medium text-on-surface mb-2 flex items-center gap-2">
                              <span className="material-symbols-outlined text-sm text-primary">show_chart</span>
                              연간 EPS 추이
                            </p>
                            {t.annual_eps.length > 0 ? (
                              <ul className="space-y-1">
                                {t.annual_eps.map(([k, v]) => (
                                  <li key={k} className="flex items-baseline gap-3 leading-relaxed">
                                    <span className="text-on-surface-variant/60 font-mono text-[11px] w-14">{k.slice(0, 4)}</span>
                                    <span className="font-medium" style={{ color: v < 0 ? "#ffb4ab" : "var(--on-surface)" }}>
                                      {v.toLocaleString()}원
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p>연간 EPS 데이터 없음.</p>
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-on-surface mb-2 flex items-center gap-2">
                              <span className="material-symbols-outlined text-sm text-primary">percent</span>
                              ROE 추이
                            </p>
                            {t.annual_roe.length > 0 ? (
                              <ul className="space-y-1">
                                {t.annual_roe.map(([k, v]) => (
                                  <li key={k} className="flex items-baseline gap-3 leading-relaxed">
                                    <span className="text-on-surface-variant/60 font-mono text-[11px] w-14">{k.slice(0, 4)}</span>
                                    <span className="font-medium" style={{ color: roeColor(v) }}>{v.toFixed(1)}%</span>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p>ROE 데이터 없음.</p>
                            )}
                          </div>
                          <div className="md:col-span-2 grid grid-cols-2 sm:grid-cols-3 gap-3 mt-2 text-[11px]">
                            <div className="bg-surface-container/40 rounded-md p-2.5">
                              <p className="text-on-surface-variant/60 mb-0.5">직전 분기 EPS YoY</p>
                              <p className="font-medium" style={{ color: growthColor(t.latest_quarter_yoy) }}>
                                {fmtPct(t.latest_quarter_yoy)}
                              </p>
                            </div>
                            <div className="bg-surface-container/40 rounded-md p-2.5">
                              <p className="text-on-surface-variant/60 mb-0.5">안정성 지수</p>
                              <p className="font-medium" style={{ color: stabilityColor(t.earnings_stability_score) }}>
                                {t.earnings_stability_score !== null ? t.earnings_stability_score : "평가 불가"}
                              </p>
                              <p className="text-on-surface-variant/50 mt-0.5">{t.earnings_stability_detail || "—"}</p>
                            </div>
                            <div className="bg-surface-container/40 rounded-md p-2.5">
                              <p className="text-on-surface-variant/60 mb-0.5">산업 코드 (KSIC)</p>
                              <p className="font-medium text-on-surface">{t.induty_code ?? "—"}</p>
                              <p className="text-on-surface-variant/50 mt-0.5">{t.cyclical ? "경기민감" : "비경기민감"}</p>
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
    </div>
  );
}

// ────────────────────────────────────────────────────────
// 예비 사유 / 정통 승격 조건 패널 — is_preliminary 일 때만 표시
// ────────────────────────────────────────────────────────

const TURNAROUND_STRICT = {
  ANNUAL_YOY: 5.0,
  QUARTERLY_YOY: 50.0,
  TTM_RATIO: 0.90,
};

const TURNAROUND_PRELIM = {
  ANNUAL_YOY: 0.0,
  QUARTERLY_YOY: 30.0,
  TTM_RATIO: 0.80,
};

interface ConditionStatus {
  label: string;
  current: string;
  strict_pass: boolean;
  prelim_pass: boolean;
  strict_threshold: string;
  upgrade_hint: string;
}

function buildConditionStatus(t: TurnaroundCriterion): ConditionStatus[] {
  const yoy = t.latest_annual_yoy;
  const yoyStr = yoy === 999.99 ? "흑자전환" : yoy !== null ? `${yoy >= 0 ? "+" : ""}${yoy.toFixed(1)}%` : "N/A";
  const recoveryStrict = yoy !== null && (yoy === 999.99 || yoy >= TURNAROUND_STRICT.ANNUAL_YOY);
  const recoveryPrelim = yoy !== null && (yoy === 999.99 || yoy >= TURNAROUND_PRELIM.ANNUAL_YOY);

  const surgeStrict = t.two_quarter_surge;
  const surgePrelim = t.preliminary_two_quarter_surge;
  const surgeDetail = t.two_quarter_surge_detail || "데이터 부족";

  const ttmRatio = t.ttm_high_ratio;
  const ttmStr = t.is_all_time_high
    ? "사상 최고치"
    : ttmRatio !== null
    ? `${(ttmRatio * 100).toFixed(0)}%`
    : "N/A";
  const highStrict = t.is_all_time_high || (ttmRatio !== null && ttmRatio >= TURNAROUND_STRICT.TTM_RATIO);
  const highPrelim = t.is_all_time_high || (ttmRatio !== null && ttmRatio >= TURNAROUND_PRELIM.TTM_RATIO);

  return [
    {
      label: "직전 1년 EPS YoY",
      current: yoyStr,
      strict_pass: recoveryStrict,
      prelim_pass: recoveryPrelim,
      strict_threshold: `≥ +${TURNAROUND_STRICT.ANNUAL_YOY}%`,
      upgrade_hint:
        recoveryStrict
          ? "이미 정통 통과"
          : yoy !== null
          ? `다음 분기 연 EPS YoY 가 +${TURNAROUND_STRICT.ANNUAL_YOY}% 이상으로 회복되면 정통`
          : "데이터 보강 필요",
    },
    {
      label: "분기 EPS 2분기 연속 급증",
      current: surgeDetail,
      strict_pass: surgeStrict,
      prelim_pass: surgePrelim,
      strict_threshold: `2분기 연속 ≥ +${TURNAROUND_STRICT.QUARTERLY_YOY}%`,
      upgrade_hint:
        surgeStrict
          ? "이미 정통 통과"
          : `다음 분기 EPS YoY 가 +${TURNAROUND_STRICT.QUARTERLY_YOY}% 이상이면 정통 승격`,
    },
    {
      label: "TTM 사상 최고치",
      current: ttmStr,
      strict_pass: highStrict,
      prelim_pass: highPrelim,
      strict_threshold: `≥ ${(TURNAROUND_STRICT.TTM_RATIO * 100).toFixed(0)}% 또는 신고가`,
      upgrade_hint:
        highStrict
          ? "이미 정통 통과"
          : ttmRatio !== null
          ? `TTM EPS 가 사상 최고치의 ${(TURNAROUND_STRICT.TTM_RATIO * 100).toFixed(0)}% 이상까지 회복하면 정통 (현재 ${(ttmRatio * 100).toFixed(0)}%)`
          : "데이터 보강 필요",
    },
  ];
}

function PreliminaryReasonPanel({ t }: { t: TurnaroundCriterion }) {
  const conditions = buildConditionStatus(t);
  const reasons = conditions.filter((c) => !c.strict_pass && c.prelim_pass);

  return (
    <div className="mb-4 p-3 rounded-lg bg-amber-500/8 border border-amber-500/20">
      <p className="font-medium text-amber-300 mb-2 flex items-center gap-2">
        <span className="material-symbols-outlined text-sm">info</span>
        예비 사유 — 정통 승격까지 남은 조건
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {conditions.map((cond) => {
          const isReason = !cond.strict_pass && cond.prelim_pass;
          const stateColor = cond.strict_pass
            ? "text-emerald-300"
            : cond.prelim_pass
            ? "text-amber-400"
            : "text-on-surface-variant/70";
          const stateIcon = cond.strict_pass ? "check_circle" : cond.prelim_pass ? "warning" : "cancel";
          const stateText = cond.strict_pass ? "정통 통과" : cond.prelim_pass ? "예비만 통과" : "미통과";
          const bgClass = isReason
            ? "bg-amber-500/10 border-amber-500/30"
            : "bg-surface-container/40 border-on-surface/5";
          return (
            <div
              key={cond.label}
              className={`rounded-md p-2.5 border ${bgClass}`}
            >
              <div className="flex items-center gap-1 mb-1">
                <span className={`material-symbols-outlined text-sm ${stateColor}`}>{stateIcon}</span>
                <span className={`text-[10px] font-medium ${stateColor}`}>{stateText}</span>
              </div>
              <p className="text-on-surface-variant/70 text-[11px] mb-0.5">{cond.label}</p>
              <p className="font-medium text-on-surface mb-1">{cond.current}</p>
              <p className="text-on-surface-variant/60 text-[10px]">정통 기준: {cond.strict_threshold}</p>
              {isReason && (
                <p className="text-amber-300/90 text-[10px] mt-1.5 leading-relaxed">
                  → {cond.upgrade_hint}
                </p>
              )}
            </div>
          );
        })}
      </div>
      {reasons.length === 0 && (
        <p className="text-on-surface-variant/60 text-[11px] mt-2">
          모든 조건이 정통 기준 충족 — 데이터 갱신 필요 (다음 스크리닝에서 정통 트랙으로 이동 예정).
        </p>
      )}
    </div>
  );
}
