"use client";

import { Fragment, useMemo, useState } from "react";

export interface CCriterion {
  pass: boolean;
  value: string;
  detail: string;
  yoy_pct: number | null;
  latest_quarter: string | null;
  latest_eps: number | null;
  prev_yoy_pct: number | null;
  accel_delta_pp: number | null;
  sales_yoy_pct: number | null;
  sales_yoy_history: [string, number][];
  sales_accel_3q: boolean;
  eps_yoy_history: [string, number][];
  eps_accel_3q: boolean;
  never_sell: boolean;
  eps_new_high: boolean;
  consecutive_decline_quarters: number;
  severe_decel: boolean;
  is_turnaround: boolean;
  dilution_flag: boolean | null;
  latest_is_preliminary?: boolean;
  preliminary_rcept_no?: string | null;
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
  criteria: {
    C: CCriterion;
  };
}

type SortKey = "yoy_pct" | "accel_delta_pp" | "sales_yoy_pct" | "latest_eps" | "market_cap";
type MarketFilter = "ALL" | "KOSPI" | "KOSDAQ";

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
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("yoy_pct");
  const [sortDesc, setSortDesc] = useState(true);
  const [salesAccompanyOnly, setSalesAccompanyOnly] = useState(false);
  const [salesAccel3qOnly, setSalesAccel3qOnly] = useState(false);
  const [newHighOnly, setNewHighOnly] = useState(false);
  const [accelOnly, setAccelOnly] = useState(false);
  const [noWarningOnly, setNoWarningOnly] = useState(false);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let arr = candidates;
    if (marketFilter !== "ALL") arr = arr.filter((c) => c.market === marketFilter);
    if (salesAccompanyOnly) {
      arr = arr.filter((c) => c.criteria.C.sales_yoy_pct !== null && c.criteria.C.sales_yoy_pct >= 25);
    }
    if (salesAccel3qOnly) {
      arr = arr.filter((c) => c.criteria.C.sales_accel_3q);
    }
    if (newHighOnly) arr = arr.filter((c) => c.criteria.C.eps_new_high);
    if (accelOnly) {
      arr = arr.filter((c) => c.criteria.C.accel_delta_pp !== null && c.criteria.C.accel_delta_pp > 0);
    }
    if (noWarningOnly) {
      arr = arr.filter((c) => {
        const cr = c.criteria.C;
        return cr.consecutive_decline_quarters < 2 && !cr.severe_decel && !cr.dilution_flag;
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
  }, [candidates, marketFilter, salesAccompanyOnly, salesAccel3qOnly, newHighOnly, accelOnly, noWarningOnly, sortKey, sortDesc]);

  const SortHeader = ({ k, label }: { k: SortKey; label: string }) => (
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
        <FilterToggle on={noWarningOnly} onChange={setNoWarningOnly} label="경고 없음" />
      </div>

      {/* 테이블 */}
      <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-container/40 text-xs">
              <tr className="text-left">
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70">종목</th>
                <th className="px-3 py-2.5 font-medium">
                  <SortHeader k="yoy_pct" label="분기 EPS YoY" />
                </th>
                <th className="px-3 py-2.5 font-medium">
                  <SortHeader k="latest_eps" label="최근 EPS" />
                </th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden sm:table-cell">분기</th>
                <th className="px-3 py-2.5 font-medium hidden md:table-cell">
                  <SortHeader k="accel_delta_pp" label="가속" />
                </th>
                <th className="px-3 py-2.5 font-medium hidden md:table-cell">
                  <SortHeader k="sales_yoy_pct" label="매출 YoY" />
                </th>
                <th className="px-3 py-2.5 font-medium text-on-surface-variant/70 hidden lg:table-cell">신호</th>
                <th className="px-3 py-2.5 font-medium hidden lg:table-cell">
                  <SortHeader k="market_cap" label="시총" />
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-on-surface-variant/60 text-sm">
                    조건에 맞는 종목이 없습니다.
                  </td>
                </tr>
              )}
              {filtered.map((c) => {
                const cr = c.criteria.C;
                const isOpen = expandedCode === c.code;
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
                      <td className="px-3 py-2.5 font-medium" style={{ color: pctColor(cr.yoy_pct) }}>
                        <div className="flex items-center gap-1.5">
                          <span className={cr.yoy_pct !== null && cr.yoy_pct >= 100 ? "font-bold" : ""}>
                            {fmtPct(cr.yoy_pct)}
                          </span>
                          {cr.is_turnaround && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-tertiary/15 text-tertiary font-medium">흑자전환</span>
                          )}
                          {cr.latest_is_preliminary && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 font-medium" title="잠정실적 기반 (분기보고서 미공시)">잠정</span>
                          )}
                          {cr.never_sell && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-600/20 text-emerald-300 font-bold" title="최근 3분기 매출+순이익 모두 가속 - O'Neil 원전: 절대 매도 금지 종목">⛔ 절대 매도 금지</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-on-surface-variant">
                        {cr.latest_eps !== null ? `${Math.round(cr.latest_eps).toLocaleString()}원` : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-on-surface-variant/70 hidden sm:table-cell text-xs">
                        {cr.latest_quarter ?? "—"}
                      </td>
                      <td
                        className="px-3 py-2.5 hidden md:table-cell text-xs"
                        style={{ color: deltaColor(cr.accel_delta_pp) }}
                      >
                        {cr.accel_delta_pp !== null
                          ? `${cr.accel_delta_pp > 0 ? "+" : ""}${cr.accel_delta_pp.toFixed(1)}%p`
                          : "—"}
                      </td>
                      <td
                        className="px-3 py-2.5 hidden md:table-cell text-xs"
                        style={{ color: pctColor(cr.sales_yoy_pct) }}
                      >
                        {fmtPct(cr.sales_yoy_pct)}
                      </td>
                      <td className="px-3 py-2.5 hidden lg:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {cr.eps_new_high && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/15 text-primary">12M 신고점</span>
                          )}
                          {cr.accel_delta_pp !== null && cr.accel_delta_pp > 0 && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400">가속</span>
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
                          {cr.sales_accel_3q && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400">매출 3분기 가속</span>
                          )}
                        </div>
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
                        <td colSpan={8} className="px-3 py-4 text-xs text-on-surface-variant">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                            <div>
                              <p className="font-medium text-on-surface mb-2 flex items-center gap-2">
                                <span className="material-symbols-outlined text-sm text-primary">show_chart</span>
                                EPS 분기별 YoY 추세
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
                              <p className="font-medium text-on-surface mb-2 flex items-center gap-2">
                                <span className="material-symbols-outlined text-sm text-primary">payments</span>
                                매출 분기별 YoY 추세
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
                                  최근 3분기 매출과 EPS가 모두 가속 중. O&apos;Neil 원전: &quot;3분기 동안 매출액과 순이익 증가율이 가속화되고 있다면 절대 초조해하거나 서둘러 매도할 필요가 없다. 꿋꿋이 포지션을 지키면 된다.&quot;
                                </p>
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
      </div>
    </div>
  );
}

function readSortValue(c: CanslimCandidate, k: SortKey): number | null {
  const cr = c.criteria.C;
  if (k === "yoy_pct") return cr.yoy_pct;
  if (k === "accel_delta_pp") return cr.accel_delta_pp;
  if (k === "sales_yoy_pct") return cr.sales_yoy_pct;
  if (k === "latest_eps") return cr.latest_eps;
  if (k === "market_cap") return c.market_cap_eok;
  return null;
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
