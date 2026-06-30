"use client";

import { useMemo, useState } from "react";
import {
  type ClassifiedRow,
  type PatternColumn,
  type Tier,
  fmtPct,
  fmtPrice,
  fmtCell,
} from "./sepaPatterns";

const TIER_META: Record<Tier, { label: string; color: string; bg: string; dot: string }> = {
  breakout: { label: "돌파", color: "#ffb4ab", bg: "rgba(255,180,171,0.15)", dot: "🔴" },
  actionable: { label: "진입임박", color: "#34d399", bg: "rgba(52,211,153,0.15)", dot: "🟢" },
  watch: { label: "예의주시", color: "#e9c176", bg: "rgba(233,193,118,0.15)", dot: "🟡" },
};

const TIER_ORDER: Record<Tier, number> = { breakout: 0, actionable: 1, watch: 2 };

function rsColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= 90) return "#10b981";
  if (n >= 80) return "#34d399";
  if (n >= 70) return "#e9c176";
  return "#ffb4ab";
}

// 피벗 대비: 0 에 가까울수록 진입 적기. 음수(이미 위)·양수(아래) 모두 |값| 작을수록 좋음.
function pivotColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  const a = Math.abs(n);
  if (a <= 3) return "#10b981";
  if (a <= 8) return "#34d399";
  if (a <= 12) return "#e9c176";
  return "#a8b5d0";
}

type SortKey = "tier" | "rs" | "pivot" | "from_pivot";

interface SortHeaderProps {
  k: SortKey;
  label: string;
  activeSortKey: SortKey;
  sortDesc: boolean;
  onToggle: (key: SortKey) => void;
}

function SortHeader({ k, label, activeSortKey, sortDesc, onToggle }: SortHeaderProps) {
  return (
    <th
      onClick={() => onToggle(k)}
      className="px-2 py-2 cursor-pointer hover:bg-surface-container-high transition-colors text-right text-[11px] font-medium text-on-surface-variant/80"
    >
      <span className="inline-flex items-center gap-0.5 justify-end">
        {label}
        {activeSortKey === k && (
          <span className="material-symbols-outlined text-[14px] leading-none">
            {sortDesc ? "arrow_drop_down" : "arrow_drop_up"}
          </span>
        )}
      </span>
    </th>
  );
}

interface Props {
  rows: ClassifiedRow[];
  columns: PatternColumn[];
}

export function SepaPatternTable({ rows, columns }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("tier");
  const [sortDesc, setSortDesc] = useState(false);

  const sorted = useMemo(() => {
    const out = [...rows];
    out.sort((a, b) => {
      const get = (r: ClassifiedRow): number => {
        switch (sortKey) {
          case "tier":
            return TIER_ORDER[r.tier];
          case "rs":
            return r.rs ?? -1;
          case "pivot":
            return r.pivot_price ?? -1;
          case "from_pivot":
            return r.pct_to_pivot == null ? Infinity : Math.abs(r.pct_to_pivot);
        }
      };
      const av = get(a);
      const bv = get(b);
      const primary = av === bv ? 0 : (sortDesc ? bv - av : av - bv);
      if (primary !== 0) return primary;
      // 보조: 티어 → 피벗 근접 → RS
      if (TIER_ORDER[a.tier] !== TIER_ORDER[b.tier]) return TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
      const ap = a.pct_to_pivot == null ? Infinity : Math.abs(a.pct_to_pivot);
      const bp = b.pct_to_pivot == null ? Infinity : Math.abs(b.pct_to_pivot);
      if (ap !== bp) return ap - bp;
      return (b.rs ?? -1) - (a.rs ?? -1);
    });
    return out;
  }, [rows, sortKey, sortDesc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc(!sortDesc);
    else {
      setSortKey(key);
      setSortDesc(key === "rs" || key === "pivot"); // RS·피벗은 큰 값 먼저, 티어·피벗거리는 작은 값 먼저
    }
  };

  if (rows.length === 0) {
    return (
      <p className="text-center text-on-surface-variant/60 py-6 text-sm">
        현재 해당 종목 없음.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto bg-surface-container-low rounded-xl ghost-border">
      <table className="w-full text-xs">
        <thead className="bg-surface-container/40">
          <tr>
            <th className="px-2 py-2 text-left text-[11px] font-medium text-on-surface-variant/80 sticky left-0 bg-surface-container/40">
              종목
            </th>
            <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">시장</th>
            <SortHeader k="tier" label="상태" activeSortKey={sortKey} sortDesc={sortDesc} onToggle={toggleSort} />
            <SortHeader k="rs" label="RS" activeSortKey={sortKey} sortDesc={sortDesc} onToggle={toggleSort} />
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">현재가</th>
            <SortHeader k="pivot" label="피벗" activeSortKey={sortKey} sortDesc={sortDesc} onToggle={toggleSort} />
            <SortHeader k="from_pivot" label="피벗대비" activeSortKey={sortKey} sortDesc={sortDesc} onToggle={toggleSort} />
            {columns.map((c) => (
              <th key={c.key} className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const meta = TIER_META[r.tier];
            return (
              <tr key={r.code} className="border-t border-outline-variant/10 hover:bg-surface-container-high/50 transition-colors">
                <td className="px-2 py-2 sticky left-0 bg-surface-container-low">
                  <div className="flex flex-col">
                    <span className="text-on-surface font-medium leading-tight">{r.name}</span>
                    <span className="text-[10px] text-on-surface-variant/50 font-mono">{r.code}</span>
                  </div>
                </td>
                <td className="px-2 py-2 text-center">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${r.market === "KOSPI" ? "bg-blue-500/15 text-blue-300" : "bg-purple-500/15 text-purple-300"}`}>
                    {r.market}
                  </span>
                </td>
                <td className="px-2 py-2 text-center">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ backgroundColor: meta.bg, color: meta.color }}>
                    {meta.dot} {meta.label}
                  </span>
                </td>
                <td className="px-2 py-2 text-right font-bold" style={{ color: rsColor(r.rs) }}>
                  {r.rs ?? "—"}
                </td>
                <td className="px-2 py-2 text-right text-on-surface-variant">{fmtPrice(r.current_price)}</td>
                <td className="px-2 py-2 text-right text-on-surface-variant">{fmtPrice(r.pivot_price)}</td>
                <td className="px-2 py-2 text-right" style={{ color: pivotColor(r.pct_to_pivot) }}>
                  {fmtPct(r.pct_to_pivot, 1)}
                </td>
                {columns.map((c) => (
                  <td key={c.key} className="px-2 py-2 text-right text-on-surface-variant">
                    {fmtCell(r.raw[c.key], c.kind)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
