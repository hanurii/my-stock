"use client";

import { useMemo, useState } from "react";

export interface LCandidate {
  code: string;
  name: string;
  market: string;
  rs_score: number | null;
  return_1y_pct: number | null;
  current_price: number | null;
  a_score: number | null;
  in_universe: boolean;
  passes_l: boolean;
  fail_reasons: string[];
}

type SortKey = "rs_score" | "return_1y_pct" | "a_score";

interface Props {
  candidates: LCandidate[];
}

function fmtPrice(n: number | null): string {
  if (n == null) return "-";
  return n.toLocaleString();
}

function rsColor(rs: number | null): string {
  if (rs == null) return "var(--on-surface-variant)";
  if (rs >= 95) return "#10b981";
  if (rs >= 90) return "#34d399";
  if (rs >= 80) return "#95d3ba";
  if (rs >= 70) return "#e9c176";
  if (rs >= 60) return "#a8b5d0";
  return "#ffb4ab";
}

function rsLabel(rs: number | null): string {
  if (rs == null) return "데이터 없음";
  if (rs >= 95) return "최강 주도주";
  if (rs >= 90) return "강한 주도주";
  if (rs >= 80) return "주도주";
  if (rs >= 70) return "회색지대";
  if (rs >= 60) return "보통";
  return "소외주";
}

function aScoreColor(score: number | null): string {
  if (score == null) return "var(--on-surface-variant)";
  if (score >= 95) return "#10b981";
  if (score >= 85) return "#34d399";
  return "#a8b5d0";
}

export function LeaderTable({ candidates }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("rs_score");
  const [sortDesc, setSortDesc] = useState(true);

  const sorted = useMemo(() => {
    return [...candidates].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortDesc ? bv - av : av - bv;
    });
  }, [candidates, sortKey, sortDesc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDesc(!sortDesc);
    else {
      setSortKey(key);
      setSortDesc(true);
    }
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
              onClick={() => toggleSort("rs_score")}
            >
              RS 점수 {sortArrow("rs_score")}
            </th>
            <th
              className="text-right py-2.5 px-3 font-normal cursor-pointer hover:text-on-surface"
              onClick={() => toggleSort("return_1y_pct")}
            >
              52주 수익률 {sortArrow("return_1y_pct")}
            </th>
            <th
              className="text-right py-2.5 px-3 font-normal cursor-pointer hover:text-on-surface"
              onClick={() => toggleSort("a_score")}
            >
              A 점수 {sortArrow("a_score")}
            </th>
            <th className="text-right py-2.5 px-3 font-normal">현재가</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => {
            const rs = c.rs_score;
            return (
              <tr
                key={c.code}
                className="border-b border-on-surface/5 hover:bg-surface-container/30"
              >
                <td className="py-3 pr-3">
                  <div className="flex items-baseline gap-2">
                    <span className="font-medium text-on-surface">{c.name}</span>
                    <span className="text-[11px] text-on-surface-variant/50 font-mono">{c.code}</span>
                    {!c.in_universe && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded bg-on-surface/[0.05] text-on-surface-variant/60"
                        title="모집단(KOSPI 시총 상위 300) 외 — RS는 분포에 끼워넣어 추정"
                      >
                        모집단 외
                      </span>
                    )}
                  </div>
                </td>
                <td className="text-right py-3 px-3">
                  <div
                    className="inline-flex flex-col items-end gap-0.5 px-2 py-1 rounded"
                    style={{ backgroundColor: `${rsColor(rs)}20` }}
                  >
                    <span className="font-bold text-base leading-none" style={{ color: rsColor(rs) }}>
                      {rs ?? "-"}
                    </span>
                    <span className="text-[10px] leading-none" style={{ color: rsColor(rs) }}>
                      {rsLabel(rs)}
                    </span>
                  </div>
                </td>
                <td className="text-right py-3 px-3 font-mono text-xs">
                  <span style={{ color: c.return_1y_pct != null && c.return_1y_pct > 0 ? "#10b981" : "var(--on-surface-variant)" }}>
                    {c.return_1y_pct != null ? `${c.return_1y_pct >= 0 ? "+" : ""}${c.return_1y_pct.toFixed(2)}%` : "-"}
                  </span>
                </td>
                <td className="text-right py-3 px-3">
                  <span className="font-bold" style={{ color: aScoreColor(c.a_score) }}>
                    {c.a_score ?? "-"}
                  </span>
                </td>
                <td className="text-right py-3 px-3 text-on-surface-variant">
                  {fmtPrice(c.current_price)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
