"use client";

import { Fragment, useMemo, useState } from "react";

export interface AScoredCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  a_score: number;
  a_score_tier: string;
  a_score_breakdown: {
    eps_consecutive: number;
    eps_growth: number;
    profitability?: number;  // ROE·마진 max — 최신 스키마
    roe: number;              // ROE 단독 점수 (호환 + 비교용)
    margin?: number;          // 마진 단독 점수
    deceleration: number;
    non_cyclical: number;
  };
  a_score_notes: Record<string, string>;
  three_year_avg_growth: number | null;
  latest_roe: number | null;
  pretax_margin: number | null;
  three_year_growths: number[];
  annual_eps: [string, number][];
  annual_roe: [string, number][];
  cyclical: boolean;
  induty_code: string | null;
  consecutive_3y_increase: boolean;
  five_year_with_crisis_waiver: boolean;
  deceleration_gate_pass: boolean;
  main_track_pass: boolean;
  main_track_via_margin?: boolean;
  badges: string[];
  ttm_eps?: number | null;
  ttm_period?: string | null;
  evaluation_basis?: string | null;
  criteria_c_summary: {
    yoy_pct: number | null;
    latest_quarter: string | null;
    sales_yoy_pct: number | null;
  };
}

interface Props {
  candidates: AScoredCandidate[];
}

type MarketFilter = "ALL" | "KOSPI" | "KOSDAQ";

function fmtCap(eok: number): string {
  if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`;
  return `${eok.toLocaleString()}억`;
}

function tierColor(tier: string): string {
  if (tier.startsWith("정통")) return "#10b981";
  if (tier.startsWith("근접")) return "#34d399";
  if (tier.startsWith("약식")) return "#e9c176";
  return "#ffb4ab";
}

function scoreBarColor(score: number): string {
  if (score >= 80) return "#10b981";
  if (score >= 60) return "#34d399";
  if (score >= 40) return "#e9c176";
  return "#ffb4ab";
}

export function AScoredTable({ candidates }: Props) {
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL");
  const [tierFilter, setTierFilter] = useState<string>("ALL");
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let arr = candidates;
    if (marketFilter !== "ALL") arr = arr.filter((c) => c.market === marketFilter);
    if (tierFilter !== "ALL") {
      arr = arr.filter((c) => {
        if (tierFilter === "정통") return c.a_score >= 80;
        if (tierFilter === "근접") return c.a_score >= 60 && c.a_score < 80;
        if (tierFilter === "약식") return c.a_score >= 40 && c.a_score < 60;
        return c.a_score < 40;
      });
    }
    return arr;
  }, [candidates, marketFilter, tierFilter]);

  const counts = useMemo(() => ({
    정통: candidates.filter((c) => c.a_score >= 80).length,
    근접: candidates.filter((c) => c.a_score >= 60 && c.a_score < 80).length,
    약식: candidates.filter((c) => c.a_score >= 40 && c.a_score < 60).length,
    미달: candidates.filter((c) => c.a_score < 40).length,
  }), [candidates]);

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
        <div className="flex gap-1 rounded-md bg-surface-container-low p-1">
          {["ALL", "정통", "근접", "약식", "미달"].map((t) => (
            <button
              key={t}
              onClick={() => setTierFilter(t)}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                tierFilter === t
                  ? "bg-primary/15 text-primary"
                  : "text-on-surface-variant/70 hover:bg-surface-container/50"
              }`}
            >
              {t === "ALL" ? `전체 (${candidates.length})` : `${t} (${counts[t as keyof typeof counts]})`}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-on-surface-variant/60 ml-auto">
          5개 컷오프 각 20점 (3년 연속 증가 / 3Y 평균 EPS / 수익성 ROE·마진 max / 둔화 게이트 / 비경기민감) · 100점, 내림차순 정렬
        </span>
      </div>

      <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-container/40 text-xs">
              <tr className="text-left">
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">종목</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">A 점수</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden sm:table-cell">분류</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden md:table-cell">기준 분기</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden md:table-cell">ROE</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden md:table-cell">3Y avg EPS</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">세전 마진</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">시총</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-on-surface-variant/60 text-sm">
                    조건에 맞는 종목이 없습니다.
                  </td>
                </tr>
              )}
              {filtered.map((c) => {
                const isOpen = expandedCode === c.code;
                const tColor = tierColor(c.a_score_tier);
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
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-on-surface">{c.name}</span>
                            {c.main_track_pass && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-600/20 text-emerald-300 font-bold">메인 통과</span>
                            )}
                            {c.main_track_via_margin && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 font-bold">🥇 마진 우위</span>
                            )}
                          </div>
                          <span className="text-[11px] text-on-surface-variant/60">
                            {c.code} · {c.market}
                            {c.cyclical && " · 경기민감"}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-base" style={{ color: scoreBarColor(c.a_score) }}>
                            {c.a_score}
                          </span>
                          <span className="text-[10px] text-on-surface-variant/60">/100</span>
                        </div>
                        <div className="w-20 h-1.5 mt-1 bg-surface-container rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${c.a_score}%`,
                              backgroundColor: scoreBarColor(c.a_score),
                            }}
                          />
                        </div>
                      </td>
                      <td className="px-3 py-2.5 hidden sm:table-cell text-xs" style={{ color: tColor }}>
                        {c.a_score_tier}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                        <span className="font-mono text-on-surface-variant">{c.evaluation_basis ?? "—"}</span>
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                        {c.latest_roe !== null ? `${c.latest_roe.toFixed(1)}%` : "—"}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                        {c.three_year_avg_growth !== null
                          ? `${c.three_year_avg_growth > 0 ? "+" : ""}${c.three_year_avg_growth.toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="px-3 py-2.5 hidden lg:table-cell text-xs">
                        {c.pretax_margin !== null ? `${c.pretax_margin.toFixed(1)}%` : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-on-surface-variant text-xs hidden lg:table-cell">
                        {fmtCap(c.market_cap_eok)}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-surface-container/10 border-t border-on-surface/5">
                        <td colSpan={8} className="px-3 py-4 text-xs text-on-surface-variant">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                            <div>
                              <p className="font-medium text-on-surface mb-2">A 점수 항목별 ({c.a_score}/100)</p>
                              <ul className="space-y-1.5">
                                {(() => {
                                  const b = c.a_score_breakdown;
                                  const profScore = b.profitability ?? b.roe ?? 0;
                                  const profNote = c.a_score_notes["수익성"] ?? c.a_score_notes["ROE"] ?? "—";
                                  const items = [
                                    { key: "eps_consecutive", label: "3년 연속 EPS 증가", score: b.eps_consecutive, note: c.a_score_notes["연속_증가"] },
                                    { key: "eps_growth", label: "3년 평균 EPS 성장률", score: b.eps_growth, note: c.a_score_notes["성장률"] },
                                    { key: "profitability", label: "수익성 (ROE·마진)", score: profScore, note: profNote },
                                    { key: "deceleration", label: "둔화 게이트", score: b.deceleration, note: c.a_score_notes["둔화_게이트"] },
                                    { key: "non_cyclical", label: "비경기민감주", score: b.non_cyclical, note: c.a_score_notes["비사이클"] },
                                  ];
                                  return items.map((item) => (
                                    <li key={item.key} className="flex items-baseline gap-2 leading-relaxed">
                                      <span className="text-on-surface-variant w-32 shrink-0">{item.label}</span>
                                      <span className="font-mono font-medium" style={{ color: scoreBarColor(item.score * 5) }}>
                                        {item.score}/20
                                      </span>
                                      <span className="text-on-surface-variant/60">— {item.note}</span>
                                    </li>
                                  ));
                                })()}
                              </ul>
                            </div>
                            <div>
                              <p className="font-medium text-on-surface mb-2">3년 EPS 증가율 추이</p>
                              {c.three_year_growths.length > 0 ? (
                                <p className="font-mono">
                                  {c.three_year_growths.map((g, i) => (
                                    <span key={i}>
                                      <span style={{ color: g >= 25 ? "#10b981" : g > 0 ? "#a8b5d0" : "#ffb4ab" }}>
                                        {g > 0 ? "+" : ""}{g.toFixed(1)}%
                                      </span>
                                      {i < c.three_year_growths.length - 1 && <span className="text-on-surface-variant/40 mx-1">→</span>}
                                    </span>
                                  ))}
                                </p>
                              ) : (
                                <p className="text-on-surface-variant/60">데이터 부족</p>
                              )}
                              {c.annual_eps.length > 0 && (
                                <div className="mt-2">
                                  <p className="text-on-surface-variant/60 mb-1">
                                    연간 EPS · 평가 기준: <span className="text-on-surface-variant">{c.evaluation_basis ?? "—"}</span>
                                  </p>
                                  <ul className="space-y-0.5 font-mono text-[11px]">
                                    {c.annual_eps.slice(-6).map(([k, v]) => {
                                      const isTTM = k.startsWith("TTM_");
                                      const label = isTTM ? `TTM (${k.slice(4)})` : k.slice(0, 4);
                                      return (
                                        <li key={k} className={isTTM ? "border-t border-on-surface/10 pt-0.5 mt-0.5" : ""}>
                                          <span className="text-on-surface-variant/60 w-24 inline-block">{label}</span>
                                          <span className={v > 0 ? "text-on-surface" : "text-red-400"}>
                                            {v.toLocaleString()}원
                                          </span>
                                          {isTTM && <span className="text-emerald-400 ml-2 text-[10px]">잠정 포함 가능</span>}
                                        </li>
                                      );
                                    })}
                                  </ul>
                                </div>
                              )}
                              {c.badges.length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-1">
                                  {c.badges.map((b) => (
                                    <span key={b} className="text-[10px] px-1.5 py-0.5 rounded bg-on-surface/10 text-on-surface-variant">
                                      {b}
                                    </span>
                                  ))}
                                </div>
                              )}
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
