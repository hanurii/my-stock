"use client";

import { Fragment, useMemo, useState } from "react";

export interface ShareholderDetail {
  item: string;
  basis: string;
  score: number;
}

export interface ShareholderMetrics {
  treasury_cancellation_years: number;
  consecutive_dividend_years: number;
  dilutive_event_count: number;
  has_data: boolean;
}

export interface SCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  pct_from_52w_high: number | null;
  c_grade: string | null;
  c_score: number | null;
  s_score: number;
  shareholder_score: number;
  debt_score: number;
  is_financial: boolean;
  debt_ratio: number | null;
  debt_basis: string;
  shareholder_metrics: ShareholderMetrics;
  shareholder_details: ShareholderDetail[];
  badges: string[];
}

type SortKey = "s_score" | "market_cap" | "debt_ratio" | "shareholder_score";

interface Props {
  candidates: SCandidate[];
}

function fmtCap(eok: number): string {
  if (!eok) return "—";
  if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`;
  return `${eok.toLocaleString()}억`;
}

function fmtPct(n: number | null, digits = 1): string {
  if (n === null || n === undefined) return "—";
  return `${n.toFixed(digits)}%`;
}

function debtColor(n: number | null, isFinancial: boolean): string {
  if (isFinancial) return "var(--on-surface-variant)";
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n <= 50) return "#10b981";
  if (n <= 100) return "#34d399";
  if (n <= 150) return "#a8b5d0";
  if (n <= 200) return "#e9c176";
  return "#ffb4ab";
}

function scoreColor(score: number): string {
  if (score >= 50) return "#10b981";
  if (score >= 40) return "#34d399";
  if (score >= 30) return "#a8b5d0";
  if (score >= 20) return "#e9c176";
  return "#ffb4ab";
}

function badgeStyle(badge: string): { bg: string; color: string } {
  if (badge === "소각") return { bg: "#10b98120", color: "#10b981" };
  if (badge === "배당") return { bg: "#e9c17620", color: "#e9c176" };
  if (badge === "희석주의") return { bg: "#ffb4ab20", color: "#ffb4ab" };
  if (badge === "금융기관") return { bg: "#a8b5d020", color: "#a8b5d0" };
  if (badge === "주주환원 데이터 없음")
    return { bg: "var(--surface-container)", color: "var(--on-surface-variant)" };
  return { bg: "var(--surface-container)", color: "var(--on-surface-variant)" };
}

export function SupplyDemandTable({ candidates }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("s_score");
  const [sortDesc, setSortDesc] = useState(true);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const sorted = useMemo(() => {
    return [...candidates].sort((a, b) => {
      let av: number | null = 0;
      let bv: number | null = 0;
      if (sortKey === "s_score") {
        av = a.s_score;
        bv = b.s_score;
      } else if (sortKey === "market_cap") {
        av = a.market_cap_eok;
        bv = b.market_cap_eok;
      } else if (sortKey === "debt_ratio") {
        av = a.debt_ratio;
        bv = b.debt_ratio;
      } else if (sortKey === "shareholder_score") {
        av = a.shareholder_score;
        bv = b.shareholder_score;
      }
      const an = av ?? -Infinity;
      const bn = bv ?? -Infinity;
      return sortDesc ? bn - an : an - bn;
    });
  }, [candidates, sortKey, sortDesc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc(!sortDesc);
    else {
      setSortKey(key);
      setSortDesc(true);
    }
  };

  const arrow = (key: SortKey) =>
    sortKey === key ? (sortDesc ? "↓" : "↑") : "";

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-on-surface-variant/70 border-b border-on-surface/10">
            <th className="text-left py-2 px-2 font-medium">#</th>
            <th className="text-left py-2 px-2 font-medium">종목</th>
            <th
              className="text-right py-2 px-2 font-medium cursor-pointer hover:text-on-surface-variant"
              onClick={() => toggleSort("s_score")}
            >
              S 점수 {arrow("s_score")}
            </th>
            <th
              className="text-right py-2 px-2 font-medium cursor-pointer hover:text-on-surface-variant"
              onClick={() => toggleSort("shareholder_score")}
            >
              주주가치 {arrow("shareholder_score")}
            </th>
            <th className="text-right py-2 px-2 font-medium">부채 점수</th>
            <th
              className="text-right py-2 px-2 font-medium cursor-pointer hover:text-on-surface-variant"
              onClick={() => toggleSort("debt_ratio")}
            >
              부채비율 {arrow("debt_ratio")}
            </th>
            <th
              className="text-right py-2 px-2 font-medium cursor-pointer hover:text-on-surface-variant"
              onClick={() => toggleSort("market_cap")}
            >
              시총 {arrow("market_cap")}
            </th>
            <th className="text-center py-2 px-2 font-medium">C 등급</th>
            <th className="text-left py-2 px-2 font-medium">라벨</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c, idx) => {
            const isExpanded = expandedCode === c.code;
            return (
              <Fragment key={c.code}>
                <tr
                  className="border-b border-on-surface/5 hover:bg-surface-container/30 cursor-pointer transition-colors"
                  onClick={() => setExpandedCode(isExpanded ? null : c.code)}
                >
                  <td className="py-2.5 px-2 text-on-surface-variant/50 text-xs">
                    {idx + 1}
                  </td>
                  <td className="py-2.5 px-2">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-xs text-on-surface-variant/50">
                        {isExpanded ? "expand_less" : "expand_more"}
                      </span>
                      <div>
                        <div className="font-medium text-on-surface">
                          {c.name}
                        </div>
                        <div className="text-[10px] text-on-surface-variant/50">
                          {c.code} · {c.market}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="text-right py-2.5 px-2">
                    <span
                      className="font-mono font-bold"
                      style={{ color: scoreColor(c.s_score) }}
                    >
                      {c.s_score}
                    </span>
                    <span className="text-[10px] text-on-surface-variant/40 ml-0.5">
                      /60
                    </span>
                  </td>
                  <td className="text-right py-2.5 px-2 font-mono text-on-surface-variant">
                    {c.shareholder_score}
                    <span className="text-[10px] text-on-surface-variant/40 ml-0.5">
                      /50
                    </span>
                  </td>
                  <td className="text-right py-2.5 px-2 font-mono text-on-surface-variant">
                    {c.debt_score}
                    <span className="text-[10px] text-on-surface-variant/40 ml-0.5">
                      /10
                    </span>
                  </td>
                  <td className="text-right py-2.5 px-2">
                    <span style={{ color: debtColor(c.debt_ratio, c.is_financial) }}>
                      {fmtPct(c.debt_ratio)}
                    </span>
                  </td>
                  <td className="text-right py-2.5 px-2 text-on-surface-variant">
                    {fmtCap(c.market_cap_eok)}
                  </td>
                  <td className="text-center py-2.5 px-2 text-on-surface-variant/70 text-xs">
                    {c.c_grade ?? "—"}
                  </td>
                  <td className="py-2.5 px-2">
                    <div className="flex flex-wrap gap-1">
                      {c.badges.length === 0 ? (
                        <span className="text-on-surface-variant/40 text-xs">
                          —
                        </span>
                      ) : (
                        c.badges.map((b) => {
                          const s = badgeStyle(b);
                          return (
                            <span
                              key={b}
                              className="text-[10px] px-1.5 py-0.5 rounded"
                              style={{ backgroundColor: s.bg, color: s.color }}
                            >
                              {b}
                            </span>
                          );
                        })
                      )}
                    </div>
                  </td>
                </tr>
                {isExpanded && (
                  <tr className="bg-surface-container-low/30 border-b border-on-surface/10">
                    <td colSpan={9} className="p-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div>
                          <h4 className="font-medium text-on-surface mb-2.5">
                            주주가치 점수 내역
                            <span className="text-on-surface-variant/50 text-[10px] ml-2">
                              기본 25점에서 가감
                            </span>
                          </h4>
                          <div className="space-y-1.5">
                            {c.shareholder_details.map((d, i) => (
                              <div
                                key={i}
                                className="flex justify-between items-center gap-2"
                              >
                                <div>
                                  <span className="text-on-surface">
                                    {d.item}
                                  </span>
                                  <span className="text-on-surface-variant/60 ml-2">
                                    {d.basis}
                                  </span>
                                </div>
                                <span
                                  className="font-mono shrink-0"
                                  style={{
                                    color:
                                      d.score > 0
                                        ? "#10b981"
                                        : d.score < 0
                                          ? "#ffb4ab"
                                          : "var(--on-surface-variant)",
                                  }}
                                >
                                  {d.score > 0 ? `+${d.score}` : d.score}
                                </span>
                              </div>
                            ))}
                            <div className="pt-1.5 mt-1.5 border-t border-on-surface/10 flex justify-between items-center">
                              <span className="text-on-surface">최종</span>
                              <span className="font-mono font-bold text-on-surface">
                                {c.shareholder_score} / 50
                              </span>
                            </div>
                          </div>
                        </div>
                        <div>
                          <h4 className="font-medium text-on-surface mb-2.5">
                            부채비율 · 기타
                          </h4>
                          <div className="space-y-1.5 text-on-surface-variant/80">
                            <div className="flex justify-between">
                              <span>부채비율 기준</span>
                              <span className="text-on-surface">
                                {c.debt_basis}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>부채 점수</span>
                              <span className="font-mono text-on-surface">
                                {c.debt_score} / 10
                              </span>
                            </div>
                            <div className="pt-2 mt-2 border-t border-on-surface/10 space-y-1">
                              <div className="flex justify-between">
                                <span>자사주 소각 연도</span>
                                <span className="font-mono text-on-surface">
                                  {c.shareholder_metrics.treasury_cancellation_years}년
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span>연속 배당 연도</span>
                                <span className="font-mono text-on-surface">
                                  {c.shareholder_metrics.consecutive_dividend_years}년
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span>희석 이벤트 (5년)</span>
                                <span className="font-mono text-on-surface">
                                  {c.shareholder_metrics.dilutive_event_count}건
                                </span>
                              </div>
                            </div>
                            <div className="pt-2 mt-2 border-t border-on-surface/10 space-y-1">
                              <div className="flex justify-between">
                                <span>현재가</span>
                                <span className="font-mono text-on-surface">
                                  {c.current_price.toLocaleString()}원
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span>52주 신고가 대비</span>
                                <span className="font-mono text-on-surface">
                                  {c.pct_from_52w_high !== null
                                    ? `${c.pct_from_52w_high.toFixed(2)}%`
                                    : "—"}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span>C 점수 / 등급</span>
                                <span className="font-mono text-on-surface">
                                  {c.c_score ?? "—"} ({c.c_grade ?? "—"})
                                </span>
                              </div>
                            </div>
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
