"use client";

import { Fragment, useMemo, useState } from "react";

export interface SCriterion {
  shares_outstanding: number | null;
  insider_pct: number | null;
  float_ratio_estimated: number | null;
  buyback_3y: Array<{ date: string; report_nm: string; rcept_no: string }>;
  buyback_count_3y: number;
  buyback_large_label: boolean;
  treasury_stock_pct_estimated: number | null;
  debt_ratio_current: number | null;
  debt_ratio_quarterly: [string, number][];
  debt_ratio_annual: [string, number][];
  debt_reduction: {
    applies: boolean;
    annual_delta: number | null;
    quarterly_delta: number | null;
    annual_label: boolean;
    quarterly_label: boolean;
  };
  debt_reduction_annual_label: boolean;
  debt_reduction_quarterly_label: boolean;
  debt_reduction_label: boolean;
  splits_5y: Array<{ date: string; report_nm: string; rcept_no: string }>;
  splits_5y_count: number;
  split_warning_label: boolean;
  split_exclude: boolean;
  debt_ratio_excessive: boolean;
  pass_s: boolean;
  fail_reasons: string[];
}

export interface SCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  a_score: number | null;
  pct_from_52w_high: number | null;
  criteria: { S: SCriterion };
}

type SortKey = "market_cap" | "debt_ratio" | "insider_pct" | "a_score";

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

function fmtPrice(n: number): string {
  return n.toLocaleString();
}

function debtColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n <= 50) return "#10b981";
  if (n <= 100) return "#34d399";
  if (n <= 150) return "#a8b5d0";
  return "#ffb4ab";
}

function debtDeltaArrow(annual: [string, number][], qtr: [string, number][]): { arrow: string; color: string; detail: string } {
  // 가장 긴 시계열의 가장 오래된 vs 최근 비교
  const series = annual.length >= 2 ? annual : qtr.length >= 2 ? qtr : [];
  if (series.length < 2) return { arrow: "", color: "var(--on-surface-variant)", detail: "" };
  const first = series[0][1];
  const last = series[series.length - 1][1];
  const delta = last - first;
  if (Math.abs(delta) < 1) return { arrow: "→", color: "var(--on-surface-variant)", detail: `±${Math.abs(delta).toFixed(1)}%p` };
  if (delta < 0) return { arrow: "↓", color: "#10b981", detail: `${delta.toFixed(1)}%p` };
  return { arrow: "↑", color: "#ffb4ab", detail: `+${delta.toFixed(1)}%p` };
}

function fmtQuarterLabel(key: string): string {
  if (key.length !== 6) return key;
  const yr = key.slice(2, 4);
  const mo = key.slice(4, 6);
  const qMap: Record<string, string> = { "03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4" };
  return `${yr}${qMap[mo] ?? `·${mo}`}`;
}

function fmtAnnualLabel(key: string): string {
  if (key.length >= 4) return key.slice(0, 4);
  return key;
}

// delta = oldest - latest. 양수 = 감소(좋음), 음수 = 증가(나쁨).
function fmtDelta(delta: number | null): { text: string; color: string; arrow: string } | null {
  if (delta === null || delta === undefined) return null;
  if (delta > 0) return { text: `${delta.toFixed(1)}%p 감소`, color: "#10b981", arrow: "↓" };
  if (delta < 0) return { text: `${Math.abs(delta).toFixed(1)}%p 증가`, color: "#ffb4ab", arrow: "↑" };
  return { text: "변화 없음", color: "var(--on-surface-variant)", arrow: "→" };
}

function DebtTimeline({
  series,
  type,
  delta,
}: {
  series: [string, number][];
  type: "quarterly" | "annual";
  delta: number | null;
}) {
  if (series.length === 0) return null;
  const fmt = type === "quarterly" ? fmtQuarterLabel : fmtAnnualLabel;
  const label = type === "quarterly" ? `분기 (${series.length}분기)` : `연간 (${series.length}년)`;
  const deltaInfo = fmtDelta(delta);
  return (
    <div className="mb-3 last:mb-0">
      <div className="flex items-baseline justify-between mb-1.5 gap-2">
        <span className="text-[10px] text-on-surface-variant/60">{label}</span>
        {deltaInfo && (
          <span className="text-[11px]" style={{ color: deltaInfo.color }}>
            {deltaInfo.arrow} {deltaInfo.text}
          </span>
        )}
      </div>
      <div className="flex items-center gap-1 flex-wrap">
        {series.map(([k, v], i) => {
          const isLatest = i === series.length - 1;
          return (
            <Fragment key={k}>
              <div
                className={`px-2 py-1 rounded text-center min-w-[58px] ${
                  isLatest
                    ? "bg-surface-container ring-1 ring-on-surface/20"
                    : "bg-surface-container-low/60"
                }`}
              >
                <div className="text-[9px] text-on-surface-variant/60 leading-tight">{fmt(k)}</div>
                <div className="text-xs font-medium" style={{ color: debtColor(v) }}>
                  {v.toFixed(1)}%
                </div>
              </div>
              {!isLatest && <span className="text-on-surface-variant/30 text-xs">→</span>}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}

export function SupplyDemandTable({ candidates }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("market_cap");
  const [sortDesc, setSortDesc] = useState(true);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const sorted = useMemo(() => {
    return [...candidates].sort((a, b) => {
      let av: number | null = 0;
      let bv: number | null = 0;
      if (sortKey === "market_cap") { av = a.market_cap_eok; bv = b.market_cap_eok; }
      else if (sortKey === "debt_ratio") { av = a.criteria.S.debt_ratio_current; bv = b.criteria.S.debt_ratio_current; }
      else if (sortKey === "insider_pct") { av = a.criteria.S.insider_pct; bv = b.criteria.S.insider_pct; }
      else if (sortKey === "a_score") { av = a.a_score; bv = b.a_score; }
      const an = av ?? -Infinity;
      const bn = bv ?? -Infinity;
      return sortDesc ? bn - an : an - bn;
    });
  }, [candidates, sortKey, sortDesc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc(!sortDesc);
    else { setSortKey(key); setSortDesc(true); }
  };

  const arrow = (key: SortKey) => sortKey === key ? (sortDesc ? "↓" : "↑") : "";

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-on-surface-variant/70 border-b border-on-surface/10">
            <th className="text-left py-2 px-2 font-medium">종목</th>
            <th className="text-right py-2 px-2 font-medium cursor-pointer hover:text-on-surface-variant" onClick={() => toggleSort("market_cap")}>
              시총 {arrow("market_cap")}
            </th>
            <th className="text-right py-2 px-2 font-medium cursor-pointer hover:text-on-surface-variant" onClick={() => toggleSort("debt_ratio")}>
              부채비율 {arrow("debt_ratio")}
            </th>
            <th className="text-right py-2 px-2 font-medium cursor-pointer hover:text-on-surface-variant" onClick={() => toggleSort("insider_pct")}>
              경영진 지분 {arrow("insider_pct")}
            </th>
            <th className="text-right py-2 px-2 font-medium">유통물량</th>
            <th className="text-right py-2 px-2 font-medium">자사주 %</th>
            <th className="text-center py-2 px-2 font-medium">분할 횟수</th>
            <th className="text-center py-2 px-2 font-medium">자사주 매입</th>
            <th className="text-left py-2 px-2 font-medium">라벨</th>
            <th className="text-right py-2 px-2 font-medium cursor-pointer hover:text-on-surface-variant" onClick={() => toggleSort("a_score")}>
              A 점수 {arrow("a_score")}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => {
            const s = c.criteria.S;
            const arrowInfo = debtDeltaArrow(s.debt_ratio_annual, s.debt_ratio_quarterly);
            const labels: { text: string; color: string }[] = [];
            if (s.buyback_large_label) labels.push({ text: "자사주 매우 큰 매입", color: "#10b981" });
            if (s.debt_reduction_annual_label) labels.push({ text: "연간 부채 크게 감소", color: "#34d399" });
            if (s.debt_reduction_quarterly_label) labels.push({ text: "분기 부채 크게 감소", color: "#6ea8fe" });
            if (s.split_warning_label) labels.push({ text: "주식 분할 주의", color: "#fbbf24" });
            const isExpanded = expandedCode === c.code;

            return (
              <Fragment key={c.code}>
                <tr
                  className="border-b border-on-surface/5 hover:bg-surface-container/30 cursor-pointer transition-colors"
                  onClick={() => setExpandedCode(isExpanded ? null : c.code)}
                >
                  <td className="py-2.5 px-2">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-xs text-on-surface-variant/50">
                        {isExpanded ? "expand_less" : "expand_more"}
                      </span>
                      <div>
                        <div className="font-medium text-on-surface">{c.name}</div>
                        <div className="text-[10px] text-on-surface-variant/50">{c.code} · {c.market}</div>
                      </div>
                    </div>
                  </td>
                  <td className="text-right py-2.5 px-2 text-on-surface-variant">{fmtCap(c.market_cap_eok)}</td>
                  <td className="text-right py-2.5 px-2">
                    <span style={{ color: debtColor(s.debt_ratio_current) }}>
                      {fmtPct(s.debt_ratio_current)}
                    </span>
                    {arrowInfo.arrow && (
                      <span className="ml-1 text-[10px]" style={{ color: arrowInfo.color }}>
                        {arrowInfo.arrow} {arrowInfo.detail}
                      </span>
                    )}
                  </td>
                  <td className="text-right py-2.5 px-2 text-on-surface-variant">
                    {fmtPct(s.insider_pct)}
                  </td>
                  <td className="text-right py-2.5 px-2 text-on-surface-variant">
                    {fmtPct(s.float_ratio_estimated)}
                  </td>
                  <td className="text-right py-2.5 px-2 text-on-surface-variant">
                    {fmtPct(s.treasury_stock_pct_estimated, 2)}
                  </td>
                  <td className="text-center py-2.5 px-2 text-on-surface-variant">
                    {s.splits_5y_count > 0 ? `${s.splits_5y_count}회` : "—"}
                  </td>
                  <td className="text-center py-2.5 px-2 text-on-surface-variant">
                    {s.buyback_count_3y > 0 ? `${s.buyback_count_3y}건` : "—"}
                  </td>
                  <td className="py-2.5 px-2">
                    <div className="flex flex-wrap gap-1">
                      {labels.length === 0 ? (
                        <span className="text-on-surface-variant/40 text-xs">—</span>
                      ) : labels.map((l) => (
                        <span
                          key={l.text}
                          className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{ backgroundColor: `${l.color}20`, color: l.color }}
                        >
                          {l.text}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="text-right py-2.5 px-2 text-on-surface-variant">
                    {c.a_score ?? "—"}
                  </td>
                </tr>
                {isExpanded && (
                  <tr className="bg-surface-container-low/30 border-b border-on-surface/10">
                    <td colSpan={10} className="p-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div>
                          <h4 className="font-medium text-on-surface mb-2.5">
                            부채비율 추세 <span className="text-on-surface-variant/50 text-[10px] ml-1">과거 → 현재</span>
                          </h4>
                          <DebtTimeline series={s.debt_ratio_quarterly} type="quarterly" delta={s.debt_reduction.quarterly_delta} />
                          <DebtTimeline series={s.debt_ratio_annual} type="annual" delta={s.debt_reduction.annual_delta} />
                          {s.debt_ratio_quarterly.length === 0 && s.debt_ratio_annual.length === 0 && (
                            <div className="text-on-surface-variant/50 text-xs">—</div>
                          )}
                        </div>
                        <div>
                          <h4 className="font-medium text-on-surface mb-2">발행주식수 · 가격</h4>
                          <div className="text-on-surface-variant/80 space-y-1">
                            <div>발행주식수: {s.shares_outstanding?.toLocaleString() ?? "—"}주</div>
                            <div>현재가: {fmtPrice(c.current_price)}원</div>
                            <div>52주 신고가 대비: {c.pct_from_52w_high !== null ? `${c.pct_from_52w_high.toFixed(2)}%` : "—"}</div>
                          </div>
                        </div>
                        {s.buyback_3y.length > 0 && (
                          <div className="md:col-span-2">
                            <h4 className="font-medium text-on-surface mb-2">최근 3년 자사주 매입 결정 공시 ({s.buyback_3y.length}건)</h4>
                            <div className="space-y-1">
                              {s.buyback_3y.slice(0, 6).map((b, i) => (
                                <div key={i} className="text-on-surface-variant/80">
                                  <span className="text-on-surface-variant/60">{b.date}</span>
                                  {" · "}
                                  <a
                                    href={`https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${b.rcept_no}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="hover:text-primary"
                                  >
                                    {b.report_nm}
                                  </a>
                                </div>
                              ))}
                              {s.buyback_3y.length > 6 && (
                                <div className="text-on-surface-variant/50 text-[10px]">… 외 {s.buyback_3y.length - 6}건</div>
                              )}
                            </div>
                          </div>
                        )}
                        {s.splits_5y.length > 0 && (
                          <div className="md:col-span-2">
                            <h4 className="font-medium text-on-surface mb-2">최근 5년 주식분할 결정 ({s.splits_5y.length}회)</h4>
                            <div className="space-y-1">
                              {s.splits_5y.map((sp, i) => (
                                <div key={i} className="text-on-surface-variant/80">
                                  <span className="text-on-surface-variant/60">{sp.date}</span>
                                  {" · "}
                                  <a
                                    href={`https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${sp.rcept_no}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="hover:text-primary"
                                  >
                                    {sp.report_nm}
                                  </a>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
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

export function ExcludedSection({ excluded }: { excluded: Array<{ code: string; name: string; reasons: string[] }> }) {
  if (excluded.length === 0) return null;
  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-on-surface-variant">filter_alt_off</span>
        제외 종목 ({excluded.length})
      </h3>
      <div className="bg-surface-container-low/50 rounded-xl ghost-border p-4 space-y-2 text-sm">
        {excluded.map((e) => (
          <div key={e.code} className="flex items-baseline gap-2">
            <span className="text-on-surface font-medium">{e.name}</span>
            <span className="text-[10px] text-on-surface-variant/50">{e.code}</span>
            <span className="text-on-surface-variant/80 text-xs">— {e.reasons.join("; ")}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
