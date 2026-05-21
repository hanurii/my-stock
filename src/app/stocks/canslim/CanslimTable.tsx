"use client";

import { Fragment, useMemo, useState } from "react";
import { EPS_ACCEL_QUALITY_META, type EpsAccelQuality } from "./lib/epsAccel";
export { EPS_ACCEL_QUALITY_META } from "./lib/epsAccel";
export type { EpsAccelQuality } from "./lib/epsAccel";

export interface CCriterion {
  pass: boolean;
  value: string;
  detail: string;
  yoy_pct: number | null;
  latest_quarter: string | null;
  latest_eps: number | null;
  prev_yoy_pct: number | null;
  accel_delta_pp: number | null;
  eps_accel_quality?: EpsAccelQuality;
  sales_yoy_pct: number | null;
  sales_yoy_history: [string, number][];
  sales_accel_3q: boolean;
  eps_yoy_history: [string, number][];
  eps_accel_3q: boolean;
  never_sell: boolean;
  eps_new_high: boolean;
  consecutive_decline_quarters: number;
  severe_decel: boolean;
  dilution_flag: boolean | null;
  latest_is_preliminary?: boolean;
  preliminary_rcept_no?: string | null;
}

export type CScoreTier = "강력" | "좋음" | "중립" | "약함";

export interface CScoreBreakdown {
  yoy: number;
  accel: number;
  sales: number;
}

export interface CScoreNotes {
  yoy: string;
  accel: string;
  sales: string;
}

export interface CanslimCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  market_cap_rank?: number;
  per: number | null;
  pbr: number | null;
  current_price: number;
  pct_from_52w_high: number | null;
  criteria: {
    C: CCriterion;
  };
  c_score?: number;
  c_score_tier?: CScoreTier;
  c_score_breakdown?: CScoreBreakdown;
  c_score_notes?: CScoreNotes;
  management_quality?: string | null;
}

type SortKey =
  | "c_score"
  | "yoy_pct"
  | "accel_delta_pp"
  | "sales_yoy_pct"
  | "latest_eps"
  | "market_cap"
  | "pct_from_52w_high";
type MarketFilter = "ALL" | "KOSPI" | "KOSDAQ";
type TierFilter = "ALL" | CScoreTier;

const TIER_META: Record<CScoreTier, { color: string; bg: string; mark: string }> = {
  강력: { color: "#10b981", bg: "rgba(16,185,129,0.18)", mark: "🅐" },
  좋음: { color: "#34d399", bg: "rgba(52,211,153,0.15)", mark: "🅑" },
  중립: { color: "#e9c176", bg: "rgba(233,193,118,0.15)", mark: "🅒" },
  약함: { color: "#ffb4ab", bg: "rgba(255,180,171,0.15)", mark: "🅓" },
};

function tierOf(score: number | undefined): CScoreTier | null {
  if (score === undefined || score === null) return null;
  if (score >= 80) return "강력";
  if (score >= 70) return "좋음";
  if (score >= 50) return "중립";
  return "약함";
}

function scoreColor(score: number | undefined): string {
  if (score === undefined || score === null) return "var(--on-surface-variant)";
  if (score >= 80) return "#10b981";
  if (score >= 70) return "#34d399";
  if (score >= 50) return "#e9c176";
  return "#ffb4ab";
}

interface Props {
  candidates: CanslimCandidate[];
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

function pctColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= 100) return "#10b981";
  if (n >= 40) return "#34d399";
  if (n >= 25) return "#6ea8fe";
  if (n > 0) return "#a8b5d0";
  return "#ffb4ab";
}

function deltaColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n > 0) return "#10b981";
  if (n < 0) return "#ffb4ab";
  return "var(--on-surface-variant)";
}

export function CanslimTable({ candidates }: Props) {
  const hasScores = useMemo(() => candidates.some((c) => c.c_score !== undefined), [candidates]);
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL");
  const [tierFilter, setTierFilter] = useState<TierFilter>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>(hasScores ? "c_score" : "yoy_pct");
  const [sortDesc, setSortDesc] = useState(true);
  const [salesAccompanyOnly, setSalesAccompanyOnly] = useState(false);
  const [salesAccel3qOnly, setSalesAccel3qOnly] = useState(false);
  const [newHighOnly, setNewHighOnly] = useState(false);
  const [accelOnly, setAccelOnly] = useState(false);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const tierCounts = useMemo(() => {
    const counts: Record<CScoreTier, number> = { 강력: 0, 좋음: 0, 중립: 0, 약함: 0 };
    for (const c of candidates) {
      const t = c.c_score_tier ?? tierOf(c.c_score);
      if (t) counts[t]++;
    }
    return counts;
  }, [candidates]);

  const filtered = useMemo(() => {
    let arr = candidates;
    if (marketFilter !== "ALL") arr = arr.filter((c) => c.market === marketFilter);
    if (tierFilter !== "ALL") {
      arr = arr.filter((c) => (c.c_score_tier ?? tierOf(c.c_score)) === tierFilter);
    }
    if (salesAccompanyOnly) {
      arr = arr.filter((c) => c.criteria.C.sales_yoy_pct !== null && c.criteria.C.sales_yoy_pct >= 25);
    }
    if (salesAccel3qOnly) {
      arr = arr.filter((c) => c.criteria.C.sales_accel_3q);
    }
    if (newHighOnly) arr = arr.filter((c) => c.criteria.C.eps_new_high);
    if (accelOnly) {
      arr = arr.filter((c) => {
        const q = c.criteria.C.eps_accel_quality;
        return q === "mild" || q === "strong" || q === "explosive";
      });
    }
    return [...arr].sort((a, b) => {
      const av = readSortValue(a, sortKey);
      const bv = readSortValue(b, sortKey);
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return sortDesc ? bv - av : av - bv;
    });
  }, [candidates, marketFilter, tierFilter, salesAccompanyOnly, salesAccel3qOnly, newHighOnly, accelOnly, sortKey, sortDesc]);

  const sortHeaderProps = { sortKey, sortDesc, setSortKey, setSortDesc };

  return (
    <div>
      {/* 필터 */}
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

        <FilterToggle on={salesAccompanyOnly} onChange={setSalesAccompanyOnly} label="매출 +25% 이상" />
        <FilterToggle on={salesAccel3qOnly} onChange={setSalesAccel3qOnly} label="매출 3분기 가속" />
        <FilterToggle on={newHighOnly} onChange={setNewHighOnly} label="12M EPS 신고점" />
        <FilterToggle on={accelOnly} onChange={setAccelOnly} label="EPS 가속 중" />
      </div>

      {hasScores && (
        <div className="flex flex-wrap items-center gap-1 mb-3 rounded-md bg-surface-container-low p-1 w-fit">
          {(["ALL", "강력", "좋음", "중립", "약함"] as TierFilter[]).map((t) => {
            const count = t === "ALL" ? candidates.length : tierCounts[t as CScoreTier];
            const meta = t === "ALL" ? null : TIER_META[t as CScoreTier];
            return (
              <button
                key={t}
                onClick={() => setTierFilter(t)}
                className={`px-3 py-1.5 rounded text-xs transition-all flex items-center gap-1.5 ${
                  tierFilter === t
                    ? "bg-primary/15 text-primary"
                    : "text-on-surface-variant/70 hover:bg-surface-container/50"
                }`}
              >
                {meta && <span style={{ color: meta.color }}>{meta.mark}</span>}
                <span>{t === "ALL" ? "전체" : t}</span>
                <span className="text-[10px] text-on-surface-variant/50">({count})</span>
              </button>
            );
          })}
        </div>
      )}

      {/* 테이블 */}
      <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-container/40 text-xs">
              <tr className="text-left">
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">종목</th>
                {hasScores && (
                  <th className="px-3 py-2.5 font-medium">
                    <SortHeader k="c_score" label="C 점수" {...sortHeaderProps} />
                  </th>
                )}
                <th className="px-3 py-2.5 font-medium">
                  <SortHeader k="yoy_pct" label="분기 EPS YoY" {...sortHeaderProps} />
                </th>
                <th className="px-3 py-2.5 font-medium">
                  <SortHeader k="latest_eps" label="최근 EPS" {...sortHeaderProps} />
                </th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden sm:table-cell">분기</th>
                <th className="px-3 py-2.5 font-medium hidden md:table-cell">
                  <SortHeader k="accel_delta_pp" label="EPS 가속" {...sortHeaderProps} />
                </th>
                <th className="px-3 py-2.5 font-medium hidden md:table-cell">
                  <SortHeader k="sales_yoy_pct" label="매출 가속" {...sortHeaderProps} />
                </th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">신호</th>
                <th className="px-3 py-2.5 font-medium hidden lg:table-cell">
                  <SortHeader k="pct_from_52w_high" label="신고점 대비" {...sortHeaderProps} />
                </th>
                <th className="px-3 py-2.5 font-medium hidden lg:table-cell">
                  <SortHeader k="market_cap" label="시총" {...sortHeaderProps} />
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9 + (hasScores ? 1 : 0)} className="px-3 py-8 text-center text-on-surface-variant/60 text-sm">
                    조건에 맞는 종목이 없습니다.
                  </td>
                </tr>
              )}
              {filtered.map((c) => {
                const cr = c.criteria.C;
                const isOpen = expandedCode === c.code;
                const tier = c.c_score_tier ?? tierOf(c.c_score);
                const tierMeta = tier ? TIER_META[tier] : null;
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
                      {hasScores && (
                        <td className="px-3 py-2.5">
                          {c.c_score !== undefined ? (
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-base" style={{ color: scoreColor(c.c_score) }}>
                                {c.c_score}
                              </span>
                              <span className="text-[10px] text-on-surface-variant/60">/100</span>
                              {tier && tierMeta && (
                                <span
                                  className="text-[10px] px-1.5 py-0.5 rounded font-bold"
                                  style={{ backgroundColor: tierMeta.bg, color: tierMeta.color }}
                                  title="C 4축 합산 등급"
                                >
                                  {tierMeta.mark} {tier}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-on-surface-variant/50 text-xs">—</span>
                          )}
                        </td>
                      )}
                      <td className="px-3 py-2.5 font-medium" style={{ color: pctColor(cr.yoy_pct) }}>
                        <div className="flex items-center gap-1.5">
                          <span className={cr.yoy_pct !== null && cr.yoy_pct >= 100 ? "font-bold" : ""}>
                            {fmtPct(cr.yoy_pct)}
                          </span>
                          {cr.latest_is_preliminary && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 font-medium" title="잠정실적 기반 (분기보고서 미공시)">잠정</span>
                          )}
                          {cr.never_sell && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-600/20 text-emerald-300 font-bold" title="최근 3분기 매출+순이익 모두 가속 - O'Neil 책 기준: 절대 매도 금지 종목">⛔ 절대 매도 금지</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-on-surface-variant">
                        {cr.latest_eps !== null ? `${Math.round(cr.latest_eps).toLocaleString()}원` : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-on-surface-variant/70 hidden sm:table-cell text-xs">
                        {cr.latest_quarter ?? "—"}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                        {(() => {
                          const q: EpsAccelQuality = cr.eps_accel_quality ?? "none";
                          const meta = EPS_ACCEL_QUALITY_META[q];
                          if (q === "none") {
                            return (
                              <span className="text-on-surface-variant/60">
                                {cr.accel_delta_pp !== null
                                  ? `${cr.accel_delta_pp > 0 ? "+" : ""}${cr.accel_delta_pp.toFixed(1)}%p`
                                  : "—"}
                              </span>
                            );
                          }
                          return (
                            <div
                              className="inline-flex items-center gap-1.5 px-2 py-1 rounded"
                              style={{ backgroundColor: meta.bg }}
                              title="O'Neil 책 기준 #3: EPS 증가율의 직전 분기 대비 가속 폭"
                            >
                              <span style={{ color: meta.color }} className="text-[11px]">{meta.icon}</span>
                              <span className={meta.weight} style={{ color: meta.color }}>
                                {cr.accel_delta_pp !== null
                                  ? `${cr.accel_delta_pp > 0 ? "+" : ""}${cr.accel_delta_pp.toFixed(1)}%p`
                                  : "—"}
                              </span>
                              <span className="text-[10px]" style={{ color: meta.color, opacity: 0.85 }}>
                                {meta.label}
                              </span>
                            </div>
                          );
                        })()}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell text-xs">
                        <div className="flex flex-col gap-0.5">
                          <span style={{ color: pctColor(cr.sales_yoy_pct) }}>
                            {fmtPct(cr.sales_yoy_pct)}
                          </span>
                          {cr.sales_accel_3q && (
                            <span
                              className="inline-flex items-center gap-1 text-[10px] text-on-surface-variant/80"
                              title="최근 3분기 매출 YoY 단조 증가 또는 폭발"
                            >
                              <span style={{ color: "#a8b5d0" }}>▲</span>
                              <span>3분기 가속</span>
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 hidden lg:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {cr.eps_new_high && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/15 text-primary">12M 신고점</span>
                          )}
                          {cr.severe_decel && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400">심각 둔화</span>
                          )}
                          {cr.consecutive_decline_quarters >= 2 && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400">
                              {cr.consecutive_decline_quarters}분기 연속 감소
                            </span>
                          )}
                          {cr.dilution_flag === true && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400">희석 주의</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 hidden lg:table-cell text-xs">
                        {c.pct_from_52w_high !== null && c.pct_from_52w_high !== undefined ? (
                          <span
                            className="font-medium"
                            style={{ color: c.pct_from_52w_high >= -3 ? "#10b981" : c.pct_from_52w_high >= -15 ? "#a8b5d0" : "#ffb4ab" }}
                            title="52주 신고점 대비 현재가 비율 (음수 = 신고점 아래)"
                          >
                            {c.pct_from_52w_high > 0 ? "+" : ""}{c.pct_from_52w_high.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-on-surface-variant/50">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 hidden lg:table-cell text-xs">
                        <div className="flex flex-col leading-tight">
                          <span className="text-on-surface-variant">{fmtCap(c.market_cap_eok)}</span>
                          {c.market_cap_rank !== undefined && (
                            <span className="text-[10px] text-on-surface-variant/50">시총 {c.market_cap_rank}위</span>
                          )}
                        </div>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-surface-container/10 border-t border-on-surface/5">
                        <td colSpan={9 + (hasScores ? 1 : 0)} className="px-3 py-4 text-xs text-on-surface-variant">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                            {c.c_score_breakdown && c.c_score_notes && (
                              <div className="md:col-span-2">
                                <p className="font-medium text-on-surface mb-2 flex items-center gap-2">
                                  <span className="material-symbols-outlined text-sm text-primary">scoreboard</span>
                                  C 점수 3축 분해 ({c.c_score}/100)
                                </p>
                                <ul className="space-y-1.5">
                                  {[
                                    { key: "yoy" as const, label: "① 분기 EPS YoY 폭", max: 42 },
                                    { key: "accel" as const, label: "② EPS 가속 폭", max: 38 },
                                    { key: "sales" as const, label: "③ 매출 가속", max: 20 },
                                  ].map((axis) => {
                                    const s = c.c_score_breakdown![axis.key];
                                    const note = c.c_score_notes![axis.key];
                                    return (
                                      <li key={axis.key} className="flex items-baseline gap-2 leading-relaxed">
                                        <span className="text-on-surface-variant w-36 shrink-0">{axis.label}</span>
                                        <span className="font-mono font-medium" style={{ color: scoreColor((s / axis.max) * 100) }}>
                                          {s}/{axis.max}
                                        </span>
                                        <span className="text-on-surface-variant/60">— {note}</span>
                                      </li>
                                    );
                                  })}
                                </ul>
                              </div>
                            )}
                            <div>
                              <p className="font-medium text-on-surface mb-2 flex items-center gap-2 flex-wrap">
                                <span className="material-symbols-outlined text-sm text-primary">show_chart</span>
                                EPS 분기별 YoY 추세
                                {(() => {
                                  const q: EpsAccelQuality = cr.eps_accel_quality ?? "none";
                                  if (q === "none") return null;
                                  const meta = EPS_ACCEL_QUALITY_META[q];
                                  return (
                                    <span
                                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] ${meta.weight}`}
                                      style={{ backgroundColor: meta.bg, color: meta.color }}
                                      title={`EPS 가속 폭 ${cr.accel_delta_pp?.toFixed(1)}%p (O'Neil 책 기준 #3)`}
                                    >
                                      <span>{meta.icon}</span>
                                      <span>{meta.label}</span>
                                    </span>
                                  );
                                })()}
                              </p>
                              {cr.eps_yoy_history && cr.eps_yoy_history.length > 0 ? (
                                <ul className="space-y-1">
                                  {cr.eps_yoy_history.map(([q, v]) => (
                                    <li key={q} className="flex items-baseline gap-3 leading-relaxed">
                                      <span className="text-on-surface-variant/60 font-mono text-[11px] w-12">{q.slice(0, 4)}.{q.slice(4)}</span>
                                      <span className="font-medium" style={{ color: pctColor(v) }}>
                                        {v > 0 ? "+" : ""}{v.toFixed(1)}%
                                      </span>
                                    </li>
                                  ))}
                                  {cr.eps_accel_3q && (
                                    <li className="text-emerald-400 font-medium pt-1">→ 최근 3분기 EPS 가속 중</li>
                                  )}
                                </ul>
                              ) : (
                                <p className="leading-relaxed">{cr.detail}</p>
                              )}
                              {cr.prev_yoy_pct !== null && cr.eps_yoy_history.length === 0 && (
                                <p className="mt-2 text-on-surface-variant/70 leading-relaxed">
                                  직전 분기 YoY {fmtPct(cr.prev_yoy_pct)}
                                  <br />
                                  가속 delta:{" "}
                                  <span style={{ color: deltaColor(cr.accel_delta_pp) }}>
                                    {cr.accel_delta_pp !== null ? `${cr.accel_delta_pp > 0 ? "+" : ""}${cr.accel_delta_pp.toFixed(1)}%p` : "—"}
                                  </span>
                                </p>
                              )}
                            </div>
                            <div>
                              <p className="font-medium text-on-surface-variant/90 mb-2 flex items-center gap-2 text-[12px]">
                                <span className="material-symbols-outlined text-sm text-on-surface-variant/70">payments</span>
                                매출 분기별 YoY 추세
                                <span className="text-[10px] text-on-surface-variant/60 font-normal">(보조)</span>
                              </p>
                              {cr.sales_yoy_history && cr.sales_yoy_history.length > 0 ? (
                                <ul className="space-y-1">
                                  {cr.sales_yoy_history.map(([q, v]) => (
                                    <li key={q} className="flex items-baseline gap-3 leading-relaxed">
                                      <span className="text-on-surface-variant/60 font-mono text-[11px] w-12">{q.slice(0, 4)}.{q.slice(4)}</span>
                                      <span className="font-medium" style={{ color: pctColor(v) }}>
                                        {v > 0 ? "+" : ""}{v.toFixed(1)}%
                                      </span>
                                    </li>
                                  ))}
                                  {cr.sales_accel_3q && (
                                    <li className="text-emerald-400 font-medium pt-1">→ 최근 3분기 매출 가속 중</li>
                                  )}
                                </ul>
                              ) : (
                                <p className="text-on-surface-variant/70 leading-relaxed">분기 매출 데이터 부족 (DART 보강 미적용 또는 7분기 미만).</p>
                              )}
                            </div>
                            {cr.never_sell && (
                              <div className="md:col-span-2 mt-1 p-3 rounded-md bg-emerald-600/15 border border-emerald-600/30">
                                <p className="text-emerald-300 font-medium leading-relaxed">
                                  ⛔ <strong>절대 매도 금지 종목</strong>
                                  <br />
                                  최근 3분기 매출과 EPS가 모두 가속 중. O&apos;Neil 책 기준: &quot;3분기 동안 매출액과 순이익 증가율이 가속화되고 있다면 절대 초조해하거나 서둘러 매도할 필요가 없다. 꿋꿋이 포지션을 지키면 된다.&quot;
                                </p>
                              </div>
                            )}
                            <p className="md:col-span-2 mt-2 text-[10px] text-on-surface-variant/50 leading-relaxed">
                              * 표시된 모든 % 는 <strong>작년 같은 분기 대비(YoY)</strong> 값입니다 — 직전 분기 대비가 아님 (예: 2026.03 항목은 vs 2025.03). 분모(작년 EPS)가 ±100원 미만일 땐 100원으로 floor 처리해 폭주 억제.
                            </p>
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

function readSortValue(c: CanslimCandidate, k: SortKey): number | null {
  const cr = c.criteria.C;
  if (k === "c_score") return c.c_score ?? null;
  if (k === "yoy_pct") return cr.yoy_pct;
  if (k === "accel_delta_pp") return cr.accel_delta_pp;
  if (k === "sales_yoy_pct") return cr.sales_yoy_pct;
  if (k === "latest_eps") return cr.latest_eps;
  if (k === "market_cap") return c.market_cap_eok;
  if (k === "pct_from_52w_high") return c.pct_from_52w_high;
  return null;
}

function SortHeader({
  k,
  label,
  sortKey,
  sortDesc,
  setSortKey,
  setSortDesc,
}: {
  k: SortKey;
  label: string;
  sortKey: SortKey;
  sortDesc: boolean;
  setSortKey: (k: SortKey) => void;
  setSortDesc: (d: boolean) => void;
}) {
  return (
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
}

function FilterToggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      onClick={() => onChange(!on)}
      className={`px-3 py-1.5 rounded-md text-xs transition-all ${
        on
          ? "bg-primary/15 text-primary"
          : "bg-surface-container-low text-on-surface-variant/70 hover:bg-surface-container/50"
      }`}
    >
      {label}
    </button>
  );
}
