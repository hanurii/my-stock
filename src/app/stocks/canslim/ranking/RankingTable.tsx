"use client";

import { useMemo, useState } from "react";
import {
  PRINCIPLES,
  PRINCIPLE_LABELS,
  PRINCIPLE_MAX,
  TOTAL_MAX,
  type Principle,
  type RankingCandidate,
} from "./types";
import { EPS_ACCEL_QUALITY_META, type EpsAccelQuality } from "../lib/epsAccel";

type SortKey = "total" | "market_cap" | "pct_from_52w_high" | Principle;
type MarketFilter = "ALL" | "KOSPI" | "KOSDAQ";

interface Props {
  candidates: RankingCandidate[];
}

function fmtCap(eok: number): string {
  if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`;
  return `${eok.toLocaleString()}억`;
}

function fmtFrom52wHigh(n: number | null): string {
  if (n === null || n === undefined) return "—";
  if (n === 0) return "신고점";
  return `${n.toFixed(1)}%`;
}

function from52wHighColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n === 0) return "#10b981";
  if (n >= -5) return "#34d399";
  if (n >= -15) return "#a8b5d0";
  return "#ffb4ab";
}

function ratioColor(value: number | null, max: number | null): string {
  if (value === null || value === undefined || max === null || max <= 0) {
    return "var(--on-surface-variant)";
  }
  const pct = (value / max) * 100;
  if (pct >= 80) return "#10b981";
  if (pct >= 60) return "#34d399";
  if (pct >= 40) return "#e9c176";
  if (pct >= 20) return "#a8b5d0";
  return "#ffb4ab";
}

export function RankingTable({ candidates }: Props) {
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("total");
  const [sortDesc, setSortDesc] = useState(true);

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

  const sortHeaderProps = { sortKey, sortDesc, setSortKey, setSortDesc };

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
        <span className="text-[11px] text-on-surface-variant/60 ml-2">
          총 {filtered.length}종목
        </span>
      </div>

      <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-container/40 text-xs">
              <tr className="text-left">
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 sticky left-0 bg-surface-container/40 z-10">
                  종목
                </th>
                <th className="px-3 py-2.5 font-medium text-right">
                  <SortHeader k="total" label="합산" {...sortHeaderProps} align="right" />
                </th>
                {PRINCIPLES.map((p) => (
                  <th key={p} className="px-2 py-2.5 font-medium text-center">
                    <SortHeader
                      k={p}
                      label={p}
                      sublabel={PRINCIPLE_LABELS[p]}
                      {...sortHeaderProps}
                      align="center"
                    />
                  </th>
                ))}
                <th
                  className="px-3 py-2.5 font-medium hidden md:table-cell text-right"
                  title="C 게이트 통과 종목은 KIS 통합시세(KRX+NXT) 기준, 그 외는 KRX 정규장 종가 기준."
                >
                  <SortHeader
                    k="pct_from_52w_high"
                    label="신고점 대비"
                    {...sortHeaderProps}
                    align="right"
                  />
                </th>
                <th className="px-3 py-2.5 font-medium hidden sm:table-cell text-right">
                  <SortHeader k="market_cap" label="시총" {...sortHeaderProps} align="right" />
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={4 + PRINCIPLES.length} className="px-3 py-16 text-center">
                    <div className="flex flex-col items-center gap-2 text-on-surface-variant/60">
                      <span className="material-symbols-outlined text-3xl text-on-surface-variant/40">
                        leaderboard
                      </span>
                      <p className="text-sm">아직 표시할 종목이 없습니다.</p>
                      <p className="text-xs text-on-surface-variant/50 leading-relaxed max-w-md">
                        각 원칙별 페이지(C·A·N·S·L·I·M)에서 100점 만점 점수 산정이 완료되면,
                        <br />
                        이 페이지에서 합산 점수 내림차순으로 종목이 정렬되어 표시됩니다.
                      </p>
                    </div>
                  </td>
                </tr>
              )}
              {filtered.map((c, idx) => (
                <tr
                  key={c.code}
                  className="border-t border-on-surface/5 hover:bg-surface-container/30 transition-colors"
                >
                  <td className="px-3 py-2.5 sticky left-0 bg-surface-container-low/80 backdrop-blur-sm z-10">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-on-surface-variant/50 font-mono w-5 text-right">
                        {idx + 1}
                      </span>
                      <div className="flex flex-col">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-medium text-on-surface">{c.name}</span>
                          {c.c_never_sell && (
                            <span
                              className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-600/20 text-emerald-300 font-bold whitespace-nowrap"
                              title="최근 3분기 매출+순이익 모두 가속 - O'Neil 책 기준: 절대 매도 금지 종목"
                            >
                              ⛔ 절대 매도 금지
                            </span>
                          )}
                          <AccelQualityChip quality={c.c_eps_accel_quality} />
                        </div>
                        <span className="text-[11px] text-on-surface-variant/60">
                          {c.code} · {c.market}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <div className="flex flex-col items-end leading-tight">
                      <span
                        className="font-bold text-base font-mono"
                        style={{ color: ratioColor(c.total, TOTAL_MAX) }}
                      >
                        {c.total}
                      </span>
                      <span className="text-[10px] text-on-surface-variant/50">/ {TOTAL_MAX}</span>
                    </div>
                  </td>
                  {PRINCIPLES.map((p) => {
                    const s = c.scores[p];
                    return (
                      <td key={p} className="px-2 py-2.5 text-center">
                        <ScoreCell value={s} max={PRINCIPLE_MAX[p]} />
                      </td>
                    );
                  })}
                  <td
                    className="px-3 py-2.5 text-right hidden md:table-cell text-xs font-mono tabular-nums"
                    style={{ color: from52wHighColor(c.pct_from_52w_high) }}
                  >
                    {fmtFrom52wHigh(c.pct_from_52w_high)}
                  </td>
                  <td className="px-3 py-2.5 text-right hidden sm:table-cell text-xs text-on-surface-variant">
                    {fmtCap(c.market_cap_eok)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ScoreCell({ value, max }: { value: number | null; max: number | null }) {
  if (value === null || value === undefined || max === null) {
    return <span className="text-on-surface-variant/40 font-mono text-xs">—</span>;
  }
  const color = ratioColor(value, max);
  const fillPct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="inline-flex flex-col items-center leading-tight min-w-[2.5rem]">
      <span className="font-mono font-medium text-sm tabular-nums" style={{ color }}>
        {value}
        <span className="text-on-surface-variant/40 text-[10px] font-normal">/{max}</span>
      </span>
      <span
        className="block h-1 w-9 rounded-full mt-0.5"
        style={{
          background: `linear-gradient(to right, ${color} ${fillPct}%, var(--surface-container, rgba(255,255,255,0.06)) ${fillPct}%)`,
        }}
        aria-hidden
      />
    </div>
  );
}

function readSortValue(c: RankingCandidate, k: SortKey): number | null {
  if (k === "total") return c.total;
  if (k === "market_cap") return c.market_cap_eok;
  if (k === "pct_from_52w_high") return c.pct_from_52w_high;
  return c.scores[k];
}

function AccelQualityChip({ quality }: { quality?: EpsAccelQuality | null }) {
  if (!quality || quality === "none") return null;
  const meta = EPS_ACCEL_QUALITY_META[quality];
  return (
    <span
      className={`text-[10px] px-1.5 py-0.5 rounded inline-flex items-center gap-0.5 whitespace-nowrap ${meta.weight}`}
      style={{ backgroundColor: meta.bg, color: meta.color }}
      title="O'Neil 책 기준 #3: EPS 증가율의 직전 분기 대비 가속 폭"
    >
      <span>{meta.icon}</span>
      <span>{meta.label}</span>
    </span>
  );
}

function SortHeader({
  k,
  label,
  sublabel,
  sortKey,
  sortDesc,
  setSortKey,
  setSortDesc,
  align,
}: {
  k: SortKey;
  label: string;
  sublabel?: string;
  sortKey: SortKey;
  sortDesc: boolean;
  setSortKey: (k: SortKey) => void;
  setSortDesc: (d: boolean) => void;
  align?: "left" | "right" | "center";
}) {
  const justify =
    align === "right" ? "justify-end" : align === "center" ? "justify-center" : "justify-start";
  return (
    <button
      onClick={() => {
        if (sortKey === k) setSortDesc(!sortDesc);
        else {
          setSortKey(k);
          setSortDesc(true);
        }
      }}
      className={`flex w-full items-center gap-0.5 ${justify} ${
        sortKey === k ? "text-primary" : "text-on-surface-variant/70 hover:text-on-surface-variant"
      }`}
    >
      <span className="flex flex-col leading-tight">
        <span className={sublabel ? "font-serif font-bold" : ""}>{label}</span>
        {sublabel && (
          <span className="text-[9px] font-normal text-on-surface-variant/50">{sublabel}</span>
        )}
      </span>
      {sortKey === k && (
        <span className="material-symbols-outlined text-sm">
          {sortDesc ? "arrow_downward" : "arrow_upward"}
        </span>
      )}
    </button>
  );
}
