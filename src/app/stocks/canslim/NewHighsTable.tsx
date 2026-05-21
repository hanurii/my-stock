"use client";

import { Fragment, useMemo, useState } from "react";

export interface NSource {
  title: string;
  url: string;
}

export interface NAxisScore {
  value: number;
  rationale: string;
}

export interface NCommentary {
  core_product: string;
  scores: {
    competitive_advantage: NAxisScore;
    revenue_contribution: NAxisScore;
    sector_impact: NAxisScore;
  };
  total_score: number;
  tier: "A" | "B" | "C" | "D";
  sources: NSource[];
  researched_at: string;
}

export interface NCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  c_score: number | null;
  c_score_tier: string | null;
  n_commentary: NCommentary | null;
}

type SortKey = "total_score" | "competitive_advantage" | "revenue_contribution" | "sector_impact" | "c_score";

interface Props {
  candidates: NCandidate[];
}

const TIER_META: Record<"A" | "B" | "C" | "D", { label: string; mark: string; color: string }> = {
  A: { label: "강력 신제품", mark: "🅐", color: "#10b981" },
  B: { label: "검증 신제품", mark: "🅑", color: "#34d399" },
  C: { label: "부분 신제품", mark: "🅒", color: "#e9c176" },
  D: { label: "약함", mark: "🅓", color: "#ffb4ab" },
};

function fmtPrice(n: number): string {
  return n.toLocaleString();
}

function fmtCap(eok: number): string {
  if (!eok) return "—";
  if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`;
  return `${eok.toLocaleString()}억`;
}

function axisColor(value: number, max: number): string {
  const ratio = value / max;
  if (ratio >= 0.85) return "#10b981";
  if (ratio >= 0.6) return "#34d399";
  if (ratio >= 0.4) return "#a8b5d0";
  if (ratio >= 0.2) return "#e9c176";
  return "#ffb4ab";
}

export function NewHighsTable({ candidates }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("total_score");
  const [sortDesc, setSortDesc] = useState(true);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const sorted = useMemo(() => {
    return [...candidates].sort((a, b) => {
      const get = (c: NCandidate): number | null => {
        if (sortKey === "c_score") return c.c_score;
        const nc = c.n_commentary;
        if (!nc) return null;
        if (sortKey === "total_score") return nc.total_score;
        if (sortKey === "competitive_advantage") return nc.scores.competitive_advantage.value;
        if (sortKey === "revenue_contribution") return nc.scores.revenue_contribution.value;
        if (sortKey === "sector_impact") return nc.scores.sector_impact.value;
        return null;
      };
      const av = get(a);
      const bv = get(b);
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return sortDesc ? bv - av : av - bv;
    });
  }, [candidates, sortKey, sortDesc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDesc(!sortDesc);
    else { setSortKey(key); setSortDesc(true); }
  }

  function sortArrow(key: SortKey): string {
    if (sortKey !== key) return "";
    return sortDesc ? "↓" : "↑";
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-[11px] text-on-surface-variant/70 border-b border-on-surface/10">
            <th className="text-left py-2.5 pr-3 font-normal">종목명</th>
            <th className="text-left py-2.5 px-3 font-normal">핵심 신제품</th>
            <th
              className="text-right py-2.5 px-2 font-normal cursor-pointer hover:text-on-surface whitespace-nowrap"
              onClick={() => toggleSort("competitive_advantage")}
              title="경쟁 우위 (15점)"
            >
              경쟁 {sortArrow("competitive_advantage")}
            </th>
            <th
              className="text-right py-2.5 px-2 font-normal cursor-pointer hover:text-on-surface whitespace-nowrap"
              onClick={() => toggleSort("revenue_contribution")}
              title="현재 매출 기여 (10점)"
            >
              매출 {sortArrow("revenue_contribution")}
            </th>
            <th
              className="text-right py-2.5 px-2 font-normal cursor-pointer hover:text-on-surface whitespace-nowrap"
              onClick={() => toggleSort("sector_impact")}
              title="섹터·시장 임팩트 (5점)"
            >
              섹터 {sortArrow("sector_impact")}
            </th>
            <th
              className="text-right py-2.5 px-3 font-normal cursor-pointer hover:text-on-surface whitespace-nowrap"
              onClick={() => toggleSort("total_score")}
            >
              N 점수 {sortArrow("total_score")}
            </th>
            <th
              className="text-right py-2.5 px-3 font-normal cursor-pointer hover:text-on-surface whitespace-nowrap"
              onClick={() => toggleSort("c_score")}
              title="C 점수"
            >
              C {sortArrow("c_score")}
            </th>
            <th className="text-right py-2.5 px-3 font-normal whitespace-nowrap">시총</th>
            <th className="w-8" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => {
            const nc = c.n_commentary;
            const isExpanded = expandedCode === c.code;
            const tier = nc ? TIER_META[nc.tier] : null;
            return (
              <Fragment key={c.code}>
                <tr
                  className={`border-b border-on-surface/5 cursor-pointer transition-colors ${
                    isExpanded ? "bg-surface-container/40" : "hover:bg-surface-container/30"
                  }`}
                  onClick={() => setExpandedCode(isExpanded ? null : c.code)}
                >
                  <td className="py-3 pr-3">
                    <div className="flex items-baseline gap-2">
                      <span className="font-medium text-on-surface">{c.name}</span>
                      <span className="text-[11px] text-on-surface-variant/50 font-mono">{c.code}</span>
                      <span className="text-[10px] text-on-surface-variant/40">{c.market}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-xs text-on-surface-variant max-w-[260px]">
                    {nc ? (
                      <span className="line-clamp-2">{nc.core_product}</span>
                    ) : (
                      <span className="text-on-surface-variant/40 italic">미조사</span>
                    )}
                  </td>
                  <td className="text-right py-3 px-2 text-xs">
                    {nc ? (
                      <span style={{ color: axisColor(nc.scores.competitive_advantage.value, 15) }}>
                        {nc.scores.competitive_advantage.value}
                        <span className="text-on-surface-variant/40">/15</span>
                      </span>
                    ) : "—"}
                  </td>
                  <td className="text-right py-3 px-2 text-xs">
                    {nc ? (
                      <span style={{ color: axisColor(nc.scores.revenue_contribution.value, 10) }}>
                        {nc.scores.revenue_contribution.value}
                        <span className="text-on-surface-variant/40">/10</span>
                      </span>
                    ) : "—"}
                  </td>
                  <td className="text-right py-3 px-2 text-xs">
                    {nc ? (
                      <span style={{ color: axisColor(nc.scores.sector_impact.value, 5) }}>
                        {nc.scores.sector_impact.value}
                        <span className="text-on-surface-variant/40">/5</span>
                      </span>
                    ) : "—"}
                  </td>
                  <td className="text-right py-3 px-3">
                    {nc && tier ? (
                      <div
                        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded"
                        style={{ backgroundColor: `${tier.color}20` }}
                      >
                        <span className="text-xs" style={{ color: tier.color }}>{tier.mark}</span>
                        <span className="font-bold text-xs" style={{ color: tier.color }}>
                          {nc.total_score}
                          <span className="text-on-surface-variant/40 font-normal">/30</span>
                        </span>
                      </div>
                    ) : (
                      <span className="text-on-surface-variant/40 text-xs">—</span>
                    )}
                  </td>
                  <td className="text-right py-3 px-3 text-xs text-on-surface-variant">
                    {c.c_score !== null ? c.c_score.toFixed(0) : "—"}
                  </td>
                  <td className="text-right py-3 px-3 text-xs text-on-surface-variant/70 whitespace-nowrap">
                    {fmtCap(c.market_cap_eok)}
                  </td>
                  <td className="text-right py-3 pl-1 pr-2 text-on-surface-variant/40">
                    <span className="material-symbols-outlined text-base">
                      {isExpanded ? "expand_less" : "expand_more"}
                    </span>
                  </td>
                </tr>
                {isExpanded && (
                  <tr className="bg-surface-container/30 border-b border-on-surface/5">
                    <td colSpan={9} className="p-5">
                      <ExpandedDetail candidate={c} />
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

function ExpandedDetail({ candidate }: { candidate: NCandidate }) {
  const nc = candidate.n_commentary;
  if (!nc) {
    return (
      <p className="text-xs text-on-surface-variant/60 italic">
        이 종목은 아직 N 점수 조사가 완료되지 않았습니다.
      </p>
    );
  }
  const { scores, sources, researched_at, core_product } = nc;
  return (
    <div className="space-y-4">
      <div>
        <p className="text-[11px] text-on-surface-variant/60 mb-1">핵심 신제품</p>
        <p className="text-sm text-on-surface font-medium">{core_product}</p>
        <p className="text-[11px] text-on-surface-variant/60 mt-2">
          현재가 <span className="text-on-surface-variant">{fmtPrice(candidate.current_price)}</span>원
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <AxisCard
          title="① 경쟁 우위"
          value={scores.competitive_advantage.value}
          max={15}
          rationale={scores.competitive_advantage.rationale}
          accent="#95d3ba"
        />
        <AxisCard
          title="② 현재 매출 기여"
          value={scores.revenue_contribution.value}
          max={10}
          rationale={scores.revenue_contribution.rationale}
          accent="#e9c176"
        />
        <AxisCard
          title="③ 섹터·시장 임팩트"
          value={scores.sector_impact.value}
          max={5}
          rationale={scores.sector_impact.rationale}
          accent="#a8b5d0"
        />
      </div>
      {sources.length > 0 && (
        <div className="pt-3 border-t border-on-surface/5">
          <p className="text-[11px] text-on-surface-variant/60 mb-1.5">출처</p>
          <div className="flex flex-wrap gap-x-3 gap-y-1.5">
            {sources.map((s, i) => (
              <a
                key={i}
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-primary/80 hover:text-primary inline-flex items-center gap-0.5"
              >
                <span className="material-symbols-outlined text-[14px]">link</span>
                {s.title}
              </a>
            ))}
          </div>
        </div>
      )}
      {researched_at && (
        <p className="text-[10px] text-on-surface-variant/40">조사일 {researched_at}</p>
      )}
    </div>
  );
}

function AxisCard({
  title,
  value,
  max,
  rationale,
  accent,
}: {
  title: string;
  value: number;
  max: number;
  rationale: string;
  accent: string;
}) {
  const color = axisColor(value, max);
  return (
    <div className="bg-surface-container/40 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-on-surface">{title}</span>
        <span className="text-xs font-bold" style={{ color }}>
          {value}<span className="text-on-surface-variant/40 font-normal">/{max}</span>
        </span>
      </div>
      <div className="h-1 bg-on-surface/10 rounded-full overflow-hidden mb-2">
        <div
          className="h-full rounded-full"
          style={{ width: `${(value / max) * 100}%`, backgroundColor: accent }}
        />
      </div>
      <p className="text-xs text-on-surface-variant leading-relaxed">{rationale}</p>
    </div>
  );
}
