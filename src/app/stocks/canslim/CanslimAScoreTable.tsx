"use client";

import { Fragment, useMemo, useState } from "react";

export interface CanslimACandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  evaluation_basis: string;
  ttm_eps: number | null;
  ttm_period: string | null;
  criteria_c_summary: {
    yoy_pct: number | null;
    latest_quarter: string | null;
    sales_yoy_pct: number | null;
  };
  track: "orthodox" | "turnaround" | "new_listing" | "unclassified";
  track_label: string;
  score: number;
  grade: "최상" | "상" | "중" | "하";
  axis_breakdown: Record<string, number>;
  axis_notes: Record<string, string>;
  is_preliminary: boolean;
  badges: string[];
  fail_reasons?: string[];
  margin_label: string;
  is_cyclical: boolean;
  raw: {
    annual_eps: [string, number][];
    annual_roe: [string, number][];
    three_year_growths: number[];
    three_year_avg_growth: number | null;
    latest_annual_yoy: number | null;
    latest_roe: number | null;
    latest_quarter_yoy: number | null;
    pretax_margin: number | null;
    ttm_high_ratio: number | null;
    is_all_time_high: boolean;
    induty_code: string | null;
  };
}

interface Props {
  candidates: CanslimACandidate[];
}

type MarketFilter = "ALL" | "KOSPI" | "KOSDAQ";
type TrackFilter = "ALL" | "orthodox" | "turnaround_orthodox" | "turnaround_preliminary" | "new_listing" | "unclassified";
type GradeFilter = "ALL" | "최상" | "상" | "중" | "하";

const TRACK_LABEL: Record<TrackFilter, string> = {
  ALL: "전체",
  orthodox: "정통 A",
  turnaround_orthodox: "턴어라운드",
  turnaround_preliminary: "예비 턴어라운드",
  new_listing: "신규상장",
  unclassified: "분류 불가",
};

const AXIS_LABELS: Record<string, { label: string; max: number }> = {
  // 정통 A
  eps_consistency: { label: "EPS 지속성", max: 10 },
  eps_growth: { label: "EPS 성장 강도", max: 25 },
  profitability: { label: "수익성 (ROE)", max: 15 },
  // 턴어라운드
  recovery_strength: { label: "회복 강도", max: 5 },
  quarterly_surge: { label: "분기 급증 강도", max: 25 },
  ttm_recovery: { label: "TTM 회복도", max: 5 },
  // 신규상장
  quarterly_eps_strength: { label: "분기 EPS 강도", max: 25 },
  quarterly_sales_strength: { label: "분기 매출 강도", max: 5 },
  stability: { label: "안정성", max: 5 },
};

const AXIS_ORDER: Record<string, string[]> = {
  orthodox: ["eps_consistency", "eps_growth", "profitability"],
  turnaround: ["recovery_strength", "quarterly_surge", "ttm_recovery", "profitability"],
  new_listing: ["quarterly_eps_strength", "quarterly_sales_strength", "profitability", "stability"],
  unclassified: [],
};

function fmtCap(eok: number): string {
  if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`;
  return `${eok.toLocaleString()}억`;
}

function scoreColor(score: number): string {
  if (score >= 40) return "#10b981";
  if (score >= 30) return "#34d399";
  if (score >= 20) return "#e9c176";
  return "#ffb4ab";
}

function trackColor(track: CanslimACandidate["track"], isPrelim: boolean): string {
  if (track === "orthodox") return "#10b981";
  if (track === "turnaround") return isPrelim ? "#fbbf24" : "#a78bfa";
  if (track === "new_listing") return "#60a5fa";
  return "#6b7280"; // unclassified
}

function marginColor(label: string): string {
  switch (label) {
    case "매우높음": return "#10b981";
    case "높음": return "#34d399";
    case "중간": return "#a8b5d0";
    case "낮음": return "#e9c176";
    case "매우낮음": return "#ffb4ab";
    default: return "#6b7280";
  }
}

export function CanslimAScoreTable({ candidates }: Props) {
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL");
  const [trackFilter, setTrackFilter] = useState<TrackFilter>("ALL");
  const [gradeFilter, setGradeFilter] = useState<GradeFilter>("ALL");
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let arr = candidates;
    if (marketFilter !== "ALL") arr = arr.filter((c) => c.market === marketFilter);
    if (trackFilter !== "ALL") {
      arr = arr.filter((c) => {
        if (trackFilter === "orthodox") return c.track === "orthodox";
        if (trackFilter === "turnaround_orthodox") return c.track === "turnaround" && !c.is_preliminary;
        if (trackFilter === "turnaround_preliminary") return c.track === "turnaround" && c.is_preliminary;
        if (trackFilter === "new_listing") return c.track === "new_listing";
        if (trackFilter === "unclassified") return c.track === "unclassified";
        return true;
      });
    }
    if (gradeFilter !== "ALL") arr = arr.filter((c) => c.grade === gradeFilter);
    return arr;
  }, [candidates, marketFilter, trackFilter, gradeFilter]);

  const trackCounts = useMemo(() => ({
    orthodox: candidates.filter((c) => c.track === "orthodox").length,
    turnaround_orthodox: candidates.filter((c) => c.track === "turnaround" && !c.is_preliminary).length,
    turnaround_preliminary: candidates.filter((c) => c.track === "turnaround" && c.is_preliminary).length,
    new_listing: candidates.filter((c) => c.track === "new_listing").length,
    unclassified: candidates.filter((c) => c.track === "unclassified").length,
  }), [candidates]);

  const gradeCounts = useMemo(() => ({
    최상: candidates.filter((c) => c.grade === "최상").length,
    상: candidates.filter((c) => c.grade === "상").length,
    중: candidates.filter((c) => c.grade === "중").length,
    하: candidates.filter((c) => c.grade === "하").length,
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
          {(["ALL", "orthodox", "turnaround_orthodox", "turnaround_preliminary", "new_listing", "unclassified"] as TrackFilter[]).map((t) => (
            <button
              key={t}
              onClick={() => setTrackFilter(t)}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                trackFilter === t
                  ? "bg-primary/15 text-primary"
                  : "text-on-surface-variant/70 hover:bg-surface-container/50"
              }`}
            >
              {t === "ALL"
                ? `전체 (${candidates.length})`
                : `${TRACK_LABEL[t]} (${trackCounts[t as keyof typeof trackCounts]})`}
            </button>
          ))}
        </div>
        <div className="flex gap-1 rounded-md bg-surface-container-low p-1">
          {(["ALL", "최상", "상", "중", "하"] as GradeFilter[]).map((g) => (
            <button
              key={g}
              onClick={() => setGradeFilter(g)}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                gradeFilter === g
                  ? "bg-primary/15 text-primary"
                  : "text-on-surface-variant/70 hover:bg-surface-container/50"
              }`}
            >
              {g === "ALL" ? "전체 등급" : `${g} (${gradeCounts[g as keyof typeof gradeCounts]})`}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-on-surface-variant/60 ml-auto">
          3트랙 × 50점 만점 · 점수 내림차순 · 동점 시 수익성→코드순
        </span>
      </div>

      <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-container/40 text-xs">
              <tr className="text-left">
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">종목</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">A 점수</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden sm:table-cell">트랙</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden md:table-cell">ROE</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden md:table-cell">마진</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">3Y avg EPS</th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">시총</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-on-surface-variant/60 text-sm">
                    조건에 맞는 종목이 없습니다.
                  </td>
                </tr>
              )}
              {filtered.map((c) => {
                const isOpen = expandedCode === c.code;
                const tColor = trackColor(c.track, c.is_preliminary);
                const trackDisplayLabel = c.track === "turnaround" && c.is_preliminary
                  ? "🟡 예비 턴어라운드"
                  : c.track === "turnaround"
                    ? "🔄 턴어라운드"
                    : c.track === "new_listing"
                      ? "🆕 신규상장"
                      : c.track === "unclassified"
                        ? "— 분류 불가"
                        : "정통 A";
                const axisKeys = AXIS_ORDER[c.track] ?? Object.keys(c.axis_breakdown);
                const margin = c.raw.pretax_margin;
                const roe = c.raw.latest_roe;
                const avg = c.raw.three_year_avg_growth;
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
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-on-surface">{c.name}</span>
                            {c.badges.slice(0, 3).map((b) => (
                              <span
                                key={b}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-on-surface/10 text-on-surface-variant"
                              >
                                {b}
                              </span>
                            ))}
                          </div>
                          <span className="text-[11px] text-on-surface-variant/60">
                            {c.code} · {c.market}
                            {c.is_cyclical && <span className="text-amber-400/80"> · ⚠️ 경기민감</span>}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-base" style={{ color: scoreColor(c.score) }}>
                            {c.score}
                          </span>
                          <span className="text-[10px] text-on-surface-variant/60">/50</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-bold" style={{ color: scoreColor(c.score), backgroundColor: `${scoreColor(c.score)}1a` }}>
                            {c.grade}
                          </span>
                        </div>
                        <div className="w-24 h-1.5 mt-1 bg-surface-container rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${(c.score / 50) * 100}%`,
                              backgroundColor: scoreColor(c.score),
                            }}
                          />
                        </div>
                      </td>
                      <td className="px-3 py-2.5 hidden sm:table-cell text-xs" style={{ color: tColor }}>
                        {trackDisplayLabel}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                        {roe !== null ? `${roe.toFixed(1)}%` : "—"}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                        {margin !== null ? (
                          <span>
                            {margin.toFixed(1)}%{" "}
                            <span className="text-[10px]" style={{ color: marginColor(c.margin_label) }}>
                              ({c.margin_label})
                            </span>
                          </span>
                        ) : (
                          <span className="text-on-surface-variant/50">데이터 없음</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 hidden lg:table-cell text-xs">
                        {avg !== null
                          ? `${avg > 0 ? "+" : ""}${avg.toFixed(1)}%`
                          : "—"}
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
                              <p className="font-medium text-on-surface mb-2">
                                {c.track === "unclassified" ? (
                                  <>분류 불가 사유 (0점)</>
                                ) : (
                                  <>축별 점수 ({c.score}/50, {c.track_label}{c.is_preliminary ? " · 예비" : ""})</>
                                )}
                              </p>
                              {c.track === "unclassified" ? (
                                <ul className="space-y-1.5">
                                  {(c.fail_reasons ?? []).map((r, i) => (
                                    <li key={i} className="text-on-surface-variant/80 leading-relaxed">
                                      <span className="text-amber-400/80">▸</span> {r}
                                    </li>
                                  ))}
                                  {(!c.fail_reasons || c.fail_reasons.length === 0) && (
                                    <li className="text-on-surface-variant/60">상세 사유 없음</li>
                                  )}
                                </ul>
                              ) : (
                                <ul className="space-y-1.5">
                                  {axisKeys.map((k) => {
                                    const score = c.axis_breakdown[k] ?? 0;
                                    const meta = AXIS_LABELS[k] ?? { label: k, max: 0 };
                                    const note = c.axis_notes[k] ?? "—";
                                    const pct = meta.max > 0 ? (score / meta.max) * 100 : 0;
                                    return (
                                      <li key={k} className="flex items-baseline gap-2 leading-relaxed">
                                        <span className="text-on-surface-variant w-32 shrink-0">{meta.label}</span>
                                        <span
                                          className="font-mono font-medium"
                                          style={{ color: scoreColor(pct * 0.4) }}
                                        >
                                          {score}/{meta.max}
                                        </span>
                                        <span className="text-on-surface-variant/60">— {note}</span>
                                      </li>
                                    );
                                  })}
                                </ul>
                              )}
                              <p className="mt-3 text-[11px] text-on-surface-variant/60">
                                기준: <span className="font-mono">{c.evaluation_basis}</span>
                              </p>
                            </div>
                            <div>
                              <p className="font-medium text-on-surface mb-2">연간 EPS 추이</p>
                              {c.raw.annual_eps.length > 0 ? (
                                <ul className="space-y-0.5 font-mono text-[11px]">
                                  {c.raw.annual_eps.slice(-6).map(([k, v]) => {
                                    const isTTM = k.startsWith("TTM_");
                                    const label = isTTM ? `TTM (${k.slice(4)})` : k.slice(0, 4);
                                    return (
                                      <li key={k} className={isTTM ? "border-t border-on-surface/10 pt-0.5 mt-0.5" : ""}>
                                        <span className="text-on-surface-variant/60 w-24 inline-block">{label}</span>
                                        <span className={v > 0 ? "text-on-surface" : "text-red-400"}>
                                          {v.toLocaleString()}원
                                        </span>
                                      </li>
                                    );
                                  })}
                                </ul>
                              ) : (
                                <p className="text-on-surface-variant/60">데이터 부족</p>
                              )}
                              {c.raw.three_year_growths.length > 0 && (
                                <div className="mt-2">
                                  <p className="text-on-surface-variant/60 mb-1">3년 EPS 증가율 추이</p>
                                  <p className="font-mono">
                                    {c.raw.three_year_growths.map((g, i) => (
                                      <span key={i}>
                                        <span style={{ color: g >= 25 ? "#10b981" : g > 0 ? "#a8b5d0" : "#ffb4ab" }}>
                                          {g > 0 ? "+" : ""}{g.toFixed(1)}%
                                        </span>
                                        {i < c.raw.three_year_growths.length - 1 && (
                                          <span className="text-on-surface-variant/40 mx-1">→</span>
                                        )}
                                      </span>
                                    ))}
                                  </p>
                                </div>
                              )}
                              {c.badges.length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-1">
                                  {c.badges.map((b) => (
                                    <span
                                      key={b}
                                      className="text-[10px] px-1.5 py-0.5 rounded bg-on-surface/10 text-on-surface-variant"
                                    >
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
