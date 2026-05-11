"use client";

import { useMemo, useState } from "react";

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

  const sorted = useMemo(() => {
    return [...candidates].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      return sortDesc ? bv - av : av - bv;
    });
  }, [candidates, sortKey, sortDesc]);

  return (
    <div>
      {/* 정렬 토글 */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="text-xs text-on-surface-variant/60">정렬:</span>
        <div className="flex gap-1 rounded-md bg-surface-container-low p-1">
          {([
            { key: "pct_from_52w_high" as SortKey, label: "신고가 대비" },
            { key: "a_score" as SortKey, label: "A 점수" },
          ]).map((opt) => (
            <button
              key={opt.key}
              onClick={() => {
                if (sortKey === opt.key) setSortDesc(!sortDesc);
                else { setSortKey(opt.key); setSortDesc(true); }
              }}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                sortKey === opt.key
                  ? "bg-primary/15 text-primary"
                  : "text-on-surface-variant/70 hover:bg-surface-container/50"
              }`}
            >
              {opt.label} {sortKey === opt.key ? (sortDesc ? "↓" : "↑") : ""}
            </button>
          ))}
        </div>
      </div>

      {/* 카드 리스트 */}
      <div className="space-y-4">
        {sorted.map((c) => {
          const pct = c.pct_from_52w_high;
          const npd = c.n_commentary.new_product;
          const nmg = c.n_commentary.new_management;
          const nhr = c.n_commentary.new_high_reason;

          return (
            <div
              key={c.code}
              className="bg-surface-container-low rounded-xl ghost-border p-5"
            >
              {/* 헤더: 종목명 + A점수 + 가격 정보 */}
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2 mb-4 pb-4 border-b border-on-surface/5">
                <div className="flex items-baseline gap-2">
                  <h4 className="text-lg font-serif font-bold text-on-surface">{c.name}</h4>
                  <span className="text-xs text-on-surface-variant/60 font-mono">{c.code}</span>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] text-on-surface-variant/60">A</span>
                  <span
                    className="text-sm font-bold"
                    style={{ color: scoreColor(c.a_score) }}
                  >
                    {c.a_score}
                  </span>
                </div>

                <div className="flex-1" />

                <div className="flex items-baseline gap-3 text-sm">
                  <span className="text-on-surface-variant/80">
                    {fmtPrice(c.current_price)}원
                  </span>
                  <span className="text-[11px] text-on-surface-variant/50">/</span>
                  <span className="text-on-surface-variant/60 text-xs">
                    52주高 {fmtPrice(c.high_52w)} <span className="text-on-surface-variant/40">({c.high_52w_date})</span>
                  </span>
                </div>

                <div
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded"
                  style={{ backgroundColor: `${pctColor(pct)}20` }}
                >
                  <span
                    className="text-sm font-bold"
                    style={{ color: pctColor(pct) }}
                  >
                    {pct === 0 ? "0%" : `${pct.toFixed(2)}%`}
                  </span>
                  <span className="text-[10px]" style={{ color: pctColor(pct) }}>
                    {pctLabel(pct)}
                  </span>
                </div>
              </div>

              {/* 3개 코멘트 카드 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <CommentaryCard
                  icon="rocket_launch"
                  title="신제품"
                  body={npd}
                  accent="#95d3ba"
                />
                <CommentaryCard
                  icon="groups"
                  title="신경영"
                  body={nmg}
                  accent="#e9c176"
                />
                <CommentaryCard
                  icon="trending_up"
                  title="신고가 이유"
                  body={nhr}
                  accent="#a8b5d0"
                />
              </div>

              {/* 출처 */}
              {c.n_commentary.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-on-surface/5">
                  <p className="text-[11px] text-on-surface-variant/60 mb-1.5">출처</p>
                  <div className="flex flex-wrap gap-x-3 gap-y-1.5">
                    {c.n_commentary.sources.map((s, i) => (
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
                    조사일 {c.n_commentary.researched_at}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
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
