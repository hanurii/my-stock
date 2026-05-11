"use client";

import { Fragment, useMemo, useState } from "react";

export interface NSource {
  title: string;
  url: string;
}

export interface NCommentary {
  new_product: string | null;
  new_management: string | null;
  new_high_reason: string | null;
  sources: NSource[];
  researched_at: string;
}

export interface NCandidate {
  code: string;
  name: string;
  market: string;
  a_score: number;
  a_score_tier: string;
  current_price: number;
  current_date: string;
  high_52w: number;
  high_52w_date: string;
  pct_from_52w_high: number;
  n_commentary: NCommentary;
}

type SortKey = "pct_from_52w_high" | "a_score";

interface Props {
  candidates: NCandidate[];
}

function fmtPrice(n: number): string {
  return n.toLocaleString();
}

function pctColor(pct: number): string {
  if (pct >= 0) return "#10b981";
  if (pct >= -2) return "#34d399";
  if (pct >= -5) return "#a8b5d0";
  return "#ffb4ab";
}

function pctLabel(pct: number): string {
  if (pct === 0) return "당일 신고가";
  if (pct >= -1) return "신고가 근접";
  if (pct >= -3) return "신고가권";
  if (pct >= -5) return "근접권";
  return "미달";
}

function scoreColor(score: number): string {
  if (score >= 95) return "#10b981";
  if (score >= 85) return "#34d399";
  return "#a8b5d0";
}

export function NewHighsTable({ candidates }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("pct_from_52w_high");
  const [sortDesc, setSortDesc] = useState(true);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const sorted = useMemo(() => {
    return [...candidates].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
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
            <th
              className="text-right py-2.5 px-3 font-normal cursor-pointer hover:text-on-surface"
              onClick={() => toggleSort("a_score")}
            >
              A 점수 {sortArrow("a_score")}
            </th>
            <th className="text-right py-2.5 px-3 font-normal">현재가</th>
            <th className="text-right py-2.5 px-3 font-normal">52주 신고가 (도달일)</th>
            <th
              className="text-right py-2.5 px-3 font-normal cursor-pointer hover:text-on-surface"
              onClick={() => toggleSort("pct_from_52w_high")}
            >
              신고가 대비 {sortArrow("pct_from_52w_high")}
            </th>
            <th className="w-8" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => {
            const pct = c.pct_from_52w_high;
            const isExpanded = expandedCode === c.code;
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
                    </div>
                  </td>
                  <td className="text-right py-3 px-3">
                    <span
                      className="font-bold"
                      style={{ color: scoreColor(c.a_score) }}
                    >
                      {c.a_score}
                    </span>
                  </td>
                  <td className="text-right py-3 px-3 text-on-surface-variant">
                    {fmtPrice(c.current_price)}
                  </td>
                  <td className="text-right py-3 px-3 text-on-surface-variant/80 text-xs">
                    {fmtPrice(c.high_52w)} <span className="text-on-surface-variant/40">({c.high_52w_date})</span>
                  </td>
                  <td className="text-right py-3 px-3">
                    <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ backgroundColor: `${pctColor(pct)}20` }}>
                      <span className="font-bold text-xs" style={{ color: pctColor(pct) }}>
                        {pct === 0 ? "0%" : `${pct.toFixed(2)}%`}
                      </span>
                      <span className="text-[10px]" style={{ color: pctColor(pct) }}>
                        {pctLabel(pct)}
                      </span>
                    </div>
                  </td>
                  <td className="text-right py-3 pl-1 pr-2 text-on-surface-variant/40">
                    <span className="material-symbols-outlined text-base">
                      {isExpanded ? "expand_less" : "expand_more"}
                    </span>
                  </td>
                </tr>
                {isExpanded && (
                  <tr className="bg-surface-container/30 border-b border-on-surface/5">
                    <td colSpan={6} className="p-5">
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
  const { new_product, new_management, new_high_reason, sources, researched_at } = candidate.n_commentary;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <CommentaryCard
          icon="rocket_launch"
          title="신제품"
          body={new_product}
          accent="#95d3ba"
        />
        <CommentaryCard
          icon="groups"
          title="신경영"
          body={new_management}
          accent="#e9c176"
        />
        <CommentaryCard
          icon="trending_up"
          title="신고가 이유"
          body={new_high_reason}
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
          <p className="text-[10px] text-on-surface-variant/40 mt-2">
            조사일 {researched_at}
          </p>
        </div>
      )}
    </div>
  );
}

function CommentaryCard({
  icon,
  title,
  body,
  accent,
}: {
  icon: string;
  title: string;
  body: string | null;
  accent: string;
}) {
  const isEmpty = !body;
  return (
    <div
      className={`rounded-lg p-3 ${
        isEmpty
          ? "bg-on-surface/[0.03] border border-on-surface/5"
          : "bg-surface-container/40"
      }`}
    >
      <div className="flex items-center gap-1.5 mb-2">
        <span
          className="material-symbols-outlined text-base"
          style={{ color: isEmpty ? "var(--on-surface-variant)" : accent }}
        >
          {icon}
        </span>
        <span
          className="text-xs font-medium"
          style={{ color: isEmpty ? "var(--on-surface-variant)" : "var(--on-surface)" }}
        >
          {title}
        </span>
      </div>
      <p
        className={`text-xs leading-relaxed ${
          isEmpty ? "text-on-surface-variant/40 italic" : "text-on-surface-variant"
        }`}
      >
        {isEmpty ? "확인된 카탈리스트 없음" : body}
      </p>
    </div>
  );
}
