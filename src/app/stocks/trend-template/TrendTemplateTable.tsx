"use client";

import { useMemo, useState } from "react";

export interface TrendTemplateRow {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  rs: number | null;
  return_window_pct: number | null;
  sma200_rising_5m: boolean;
  high_52w: number | null;
  pct_from_52w_high: number | null;
  c_score: number | null;
  c_score_tier: string | null;
  c_gate_pass: boolean;
  eps_yoy_pct: number | null;
  sales_yoy_pct: number | null;
  eps_accel_3q: boolean;
  sales_accel_3q: boolean;
  never_sell: boolean;
  eps_accel_quality: string | null;
  latest_quarter: string | null;
  evaluated_for_code33: boolean;
  code33_pass: boolean;
  net_margin_pct: number | null;
  net_margin_accel_3q: boolean;
  listed_shares: number | null;
}

type SortKey =
  | "code33"
  | "c_score"
  | "rs"
  | "market_cap"
  | "eps_yoy"
  | "sales_yoy"
  | "net_margin"
  | "from_high";
type MarketFilter = "ALL" | "KOSPI" | "KOSDAQ";
type TierFilter = "ALL" | "강력" | "좋음" | "중립" | "약함" | "미평가";

const TIER_META: Record<string, { color: string; bg: string; mark: string }> = {
  강력: { color: "#10b981", bg: "rgba(16,185,129,0.18)", mark: "🅐" },
  좋음: { color: "#34d399", bg: "rgba(52,211,153,0.15)", mark: "🅑" },
  중립: { color: "#e9c176", bg: "rgba(233,193,118,0.15)", mark: "🅒" },
  약함: { color: "#ffb4ab", bg: "rgba(255,180,171,0.15)", mark: "🅓" },
};

function fmtCap(eok: number): string {
  if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`;
  return `${eok.toLocaleString()}억`;
}

function fmtShare(n: number | null): string {
  if (n === null || n === undefined) return "—";
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)}억주`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}만주`;
  return `${n.toLocaleString()}주`;
}

function fmtPct(n: number | null, digits = 1): string {
  if (n === null || n === undefined) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

function pctColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= 100) return "#10b981";
  if (n >= 40) return "#34d399";
  if (n >= 25) return "#6ea8fe";
  if (n > 0) return "#a8b5d0";
  return "#ffb4ab";
}

function rsColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= 90) return "#10b981";
  if (n >= 80) return "#34d399";
  if (n >= 70) return "#e9c176";
  return "#ffb4ab";
}

function scoreColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= 80) return "#10b981";
  if (n >= 70) return "#34d399";
  if (n >= 50) return "#e9c176";
  return "#ffb4ab";
}

function fromHighColor(n: number | null): string {
  // 신고가 대비 갭. 0 에 가까울수록(신고가 근접) 좋음. 모두 음수 또는 0.
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= -3) return "#10b981";   // 신고가 코앞 또는 신고가
  if (n >= -10) return "#34d399";  // 신고가 근접
  if (n >= -20) return "#e9c176";  // 약간 떨어짐
  return "#a8b5d0";                // 멀어짐
}

interface Props {
  rows: TrendTemplateRow[];
}

export function TrendTemplateTable({ rows }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("code33");
  const [sortDesc, setSortDesc] = useState(true);
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL");
  const [tierFilter, setTierFilter] = useState<TierFilter>("ALL");
  const [onlyCode33, setOnlyCode33] = useState(false);
  const [onlyGate, setOnlyGate] = useState(false);
  const [only5m, setOnly5m] = useState(false);
  const [rsMin, setRsMin] = useState<number>(0);
  const [cMin, setCMin] = useState<number>(0);
  const [excludeNegSales, setExcludeNegSales] = useState(false);

  const applyStrongPreset = () => {
    setRsMin(88);
    setCMin(70);
    setExcludeNegSales(true);
  };
  const resetFilters = () => {
    setMarketFilter("ALL");
    setTierFilter("ALL");
    setOnlyCode33(false);
    setOnlyGate(false);
    setOnly5m(false);
    setRsMin(0);
    setCMin(0);
    setExcludeNegSales(false);
  };

  const filtered = useMemo(() => {
    let out = rows;
    if (marketFilter !== "ALL") out = out.filter((r) => r.market === marketFilter);
    if (tierFilter !== "ALL") {
      out = out.filter((r) =>
        tierFilter === "미평가" ? r.c_score_tier === null : r.c_score_tier === tierFilter
      );
    }
    if (onlyCode33) out = out.filter((r) => r.code33_pass);
    if (onlyGate) out = out.filter((r) => r.c_gate_pass);
    if (only5m) out = out.filter((r) => r.sma200_rising_5m);
    if (rsMin > 0) out = out.filter((r) => (r.rs ?? -1) >= rsMin);
    if (cMin > 0) out = out.filter((r) => (r.c_score ?? -1) >= cMin);
    if (excludeNegSales) out = out.filter((r) => (r.sales_yoy_pct ?? -1) >= 0);

    const sorted = [...out].sort((a, b) => {
      const get = (r: TrendTemplateRow): number => {
        switch (sortKey) {
          case "code33":
            return r.code33_pass ? 1 : 0;
          case "c_score":
            return r.c_score ?? -1;
          case "rs":
            return r.rs ?? -1;
          case "market_cap":
            return r.market_cap_eok;
          case "eps_yoy":
            return r.eps_yoy_pct ?? -1e9;
          case "sales_yoy":
            return r.sales_yoy_pct ?? -1e9;
          case "net_margin":
            return r.net_margin_pct ?? -1e9;
          case "from_high":
            // 0 에 가까울수록(=신고가 근접) 좋음. 내림차순일 때 -2% 가 -20% 보다 위.
            return r.pct_from_52w_high ?? -1e9;
        }
      };
      const av = get(a);
      const bv = get(b);
      const primary = sortDesc ? bv - av : av - bv;
      if (primary !== 0) return primary;
      // 보조 정렬: 코드33 우선 → C 점수 → RS
      if (sortKey !== "code33") {
        const c33 = (b.code33_pass ? 1 : 0) - (a.code33_pass ? 1 : 0);
        if (c33 !== 0) return c33;
      }
      const cs = (b.c_score ?? -1) - (a.c_score ?? -1);
      if (cs !== 0) return cs;
      return (b.rs ?? -1) - (a.rs ?? -1);
    });
    return sorted;
  }, [rows, sortKey, sortDesc, marketFilter, tierFilter, onlyCode33, onlyGate, only5m, rsMin, cMin, excludeNegSales]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc(!sortDesc);
    else {
      setSortKey(key);
      setSortDesc(true);
    }
  };

  const SortHeader = ({ k, label, align = "right" }: { k: SortKey; label: string; align?: "left" | "right" | "center" }) => (
    <th
      onClick={() => toggleSort(k)}
      className={`px-2 py-2 cursor-pointer hover:bg-surface-container-high transition-colors text-${align} text-[11px] font-medium text-on-surface-variant/80`}
    >
      <span className="inline-flex items-center gap-0.5">
        {label}
        {sortKey === k && (
          <span className="material-symbols-outlined text-[14px] leading-none">
            {sortDesc ? "arrow_drop_down" : "arrow_drop_up"}
          </span>
        )}
      </span>
    </th>
  );

  return (
    <div className="space-y-3">
      {/* 프리셋 */}
      <div className="flex flex-wrap gap-2 text-xs items-center">
        <span className="text-on-surface-variant/70">프리셋:</span>
        <button
          onClick={applyStrongPreset}
          className="px-2.5 py-1 rounded ghost-border bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 transition-colors"
          title="RS≥88 AND C점수≥70 AND 매출 YoY≥0 적용"
        >
          ⚡ 최강 후보 (RS≥88 · C≥70 · 매출+)
        </button>
        <button
          onClick={resetFilters}
          className="px-2.5 py-1 rounded ghost-border bg-surface-container-low text-on-surface-variant hover:bg-surface-container-high transition-colors"
        >
          ↺ 필터 초기화
        </button>
        <span className="ml-auto text-on-surface-variant/60 self-center">
          <strong className="text-on-surface">{filtered.length}</strong> / {rows.length} 종목 표시
        </span>
      </div>

      {/* 필터 — 카테고리·토글 */}
      <div className="flex flex-wrap gap-2 text-xs">
        <select
          value={marketFilter}
          onChange={(e) => setMarketFilter(e.target.value as MarketFilter)}
          className="bg-surface-container-low ghost-border rounded px-2 py-1 text-on-surface"
        >
          <option value="ALL">전체 시장</option>
          <option value="KOSPI">KOSPI</option>
          <option value="KOSDAQ">KOSDAQ</option>
        </select>
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value as TierFilter)}
          className="bg-surface-container-low ghost-border rounded px-2 py-1 text-on-surface"
        >
          <option value="ALL">전체 등급</option>
          <option value="강력">🅐 강력</option>
          <option value="좋음">🅑 좋음</option>
          <option value="중립">🅒 중립</option>
          <option value="약함">🅓 약함</option>
          <option value="미평가">미평가</option>
        </select>
        <button
          onClick={() => setOnlyCode33(!onlyCode33)}
          className={`px-2 py-1 rounded ghost-border ${onlyCode33 ? "bg-primary/20 text-primary" : "bg-surface-container-low text-on-surface-variant"}`}
        >
          ★ 코드 33 만
        </button>
        <button
          onClick={() => setOnlyGate(!onlyGate)}
          className={`px-2 py-1 rounded ghost-border ${onlyGate ? "bg-emerald-500/20 text-emerald-300" : "bg-surface-container-low text-on-surface-variant"}`}
        >
          C 게이트 통과만
        </button>
        <button
          onClick={() => setOnly5m(!only5m)}
          className={`px-2 py-1 rounded ghost-border ${only5m ? "bg-sky-500/20 text-sky-300" : "bg-surface-container-low text-on-surface-variant"}`}
        >
          200MA 5M↑ 만
        </button>
        <button
          onClick={() => setExcludeNegSales(!excludeNegSales)}
          className={`px-2 py-1 rounded ghost-border ${excludeNegSales ? "bg-rose-500/20 text-rose-300" : "bg-surface-container-low text-on-surface-variant"}`}
        >
          매출 YoY 음수 제외
        </button>
      </div>

      {/* 필터 — 수치 컷오프 */}
      <div className="flex flex-wrap gap-3 text-xs items-center bg-surface-container-low/60 rounded px-3 py-2 ghost-border">
        <label className="flex items-center gap-1.5 text-on-surface-variant">
          <span>RS ≥</span>
          <input
            type="number"
            min={0}
            max={99}
            step={1}
            value={rsMin}
            onChange={(e) => setRsMin(Math.max(0, Math.min(99, Number(e.target.value) || 0)))}
            className="w-14 bg-surface-container rounded px-1.5 py-0.5 text-on-surface text-right"
          />
        </label>
        <label className="flex items-center gap-1.5 text-on-surface-variant">
          <span>C 점수 ≥</span>
          <input
            type="number"
            min={0}
            max={120}
            step={5}
            value={cMin}
            onChange={(e) => setCMin(Math.max(0, Math.min(120, Number(e.target.value) || 0)))}
            className="w-14 bg-surface-container rounded px-1.5 py-0.5 text-on-surface text-right"
          />
        </label>
        <span className="text-on-surface-variant/50 text-[11px]">
          (0 = 컷오프 없음)
        </span>
      </div>

      {/* 표 */}
      <div className="overflow-x-auto bg-surface-container-low rounded-xl ghost-border">
        <table className="w-full text-xs">
          <thead className="bg-surface-container/40">
            <tr>
              <th className="px-2 py-2 text-left text-[11px] font-medium text-on-surface-variant/80 sticky left-0 bg-surface-container/40">
                종목
              </th>
              <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">시장</th>
              <SortHeader k="market_cap" label="시총" />
              <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">유통주식수</th>
              <th
                onClick={() => toggleSort("from_high")}
                title="C 게이트 통과 종목은 KIS 통합시세(KRX+NXT) 기준, 그 외는 KRX 정규장 종가 기준."
                className="px-2 py-2 cursor-pointer hover:bg-surface-container-high transition-colors text-right text-[11px] font-medium text-on-surface-variant/80"
              >
                <span className="inline-flex items-center gap-0.5">
                  신고가 대비
                  {sortKey === "from_high" && (
                    <span className="material-symbols-outlined text-[14px] leading-none">
                      {sortDesc ? "arrow_drop_down" : "arrow_drop_up"}
                    </span>
                  )}
                </span>
              </th>
              <SortHeader k="rs" label="RS" />
              <SortHeader k="c_score" label="C 점수" />
              <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">등급/게이트</th>
              <SortHeader k="eps_yoy" label="EPS YoY" />
              <SortHeader k="sales_yoy" label="매출 YoY" />
              <SortHeader k="net_margin" label="순이익률" />
              <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">가속/배지</th>
              <SortHeader k="code33" label="코드33" align="center" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const tier = r.c_score_tier;
              const tierMeta = tier ? TIER_META[tier] : null;
              return (
                <tr
                  key={r.code}
                  className={`border-t border-outline-variant/10 hover:bg-surface-container-high/50 transition-colors ${r.code33_pass ? "bg-amber-500/[0.04]" : ""}`}
                >
                  {/* 종목 */}
                  <td className="px-2 py-2 sticky left-0 bg-surface-container-low">
                    <div className="flex flex-col">
                      <span className="text-on-surface font-medium leading-tight">{r.name}</span>
                      <span className="text-[10px] text-on-surface-variant/50 font-mono">{r.code}</span>
                    </div>
                  </td>
                  {/* 시장 */}
                  <td className="px-2 py-2 text-center">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${r.market === "KOSPI" ? "bg-blue-500/15 text-blue-300" : "bg-purple-500/15 text-purple-300"}`}>
                      {r.market}
                    </span>
                  </td>
                  {/* 시총 */}
                  <td className="px-2 py-2 text-right text-on-surface-variant">{fmtCap(r.market_cap_eok)}</td>
                  {/* 유통주식수 */}
                  <td className="px-2 py-2 text-right text-on-surface-variant/70 text-[11px]">{fmtShare(r.listed_shares)}</td>
                  {/* 신고가 대비 */}
                  <td className="px-2 py-2 text-right" style={{ color: fromHighColor(r.pct_from_52w_high) }} title={r.high_52w ? `52주 신고가: ${r.high_52w.toLocaleString()}원` : ""}>
                    {r.pct_from_52w_high !== null ? `${r.pct_from_52w_high >= -0.05 ? "★ " : ""}${r.pct_from_52w_high.toFixed(1)}%` : "—"}
                  </td>
                  {/* RS */}
                  <td className="px-2 py-2 text-right font-bold" style={{ color: rsColor(r.rs) }}>
                    {r.rs ?? "—"}
                  </td>
                  {/* C 점수 */}
                  <td className="px-2 py-2 text-right font-bold" style={{ color: scoreColor(r.c_score) }}>
                    {r.c_score !== null ? r.c_score.toFixed(1) : "—"}
                  </td>
                  {/* 등급/게이트 */}
                  <td className="px-2 py-2 text-center">
                    <div className="inline-flex flex-col items-center gap-0.5">
                      {tierMeta ? (
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                          style={{ backgroundColor: tierMeta.bg, color: tierMeta.color }}
                          title={tier ?? ""}
                        >
                          {tierMeta.mark} {tier}
                        </span>
                      ) : (
                        <span className="text-[10px] text-on-surface-variant/40">미평가</span>
                      )}
                      {r.c_gate_pass && (
                        <span className="text-[9px] text-emerald-400">게이트✓</span>
                      )}
                    </div>
                  </td>
                  {/* EPS YoY */}
                  <td className="px-2 py-2 text-right" style={{ color: pctColor(r.eps_yoy_pct) }}>
                    {fmtPct(r.eps_yoy_pct, 0)}
                    {r.eps_accel_3q && <span className="text-[9px] text-emerald-400 ml-0.5">✓</span>}
                  </td>
                  {/* 매출 YoY */}
                  <td className="px-2 py-2 text-right" style={{ color: pctColor(r.sales_yoy_pct) }}>
                    {fmtPct(r.sales_yoy_pct, 0)}
                    {r.sales_accel_3q && <span className="text-[9px] text-emerald-400 ml-0.5">✓</span>}
                  </td>
                  {/* 순이익률 */}
                  <td className="px-2 py-2 text-right" style={{ color: pctColor(r.net_margin_pct) }}>
                    {fmtPct(r.net_margin_pct, 2)}
                    {r.net_margin_accel_3q && <span className="text-[9px] text-emerald-400 ml-0.5">✓</span>}
                  </td>
                  {/* 배지 */}
                  <td className="px-2 py-2 text-center text-[10px]">
                    <div className="inline-flex flex-wrap gap-0.5 justify-center">
                      {r.never_sell && <span title="EPS+매출 3분기 가속" className="text-emerald-300">⛔</span>}
                      {r.sma200_rising_5m && <span title="200MA 5개월 상승 우수" className="text-sky-300">★5M↑</span>}
                      {r.eps_accel_quality === "explosive" && <span title="폭발 가속" style={{ color: "#ff7a7a" }}>🔥</span>}
                      {r.eps_accel_quality === "strong" && <span title="강력 가속">▲▲</span>}
                      {r.eps_accel_quality === "mild" && <span title="완만 가속">▲</span>}
                    </div>
                  </td>
                  {/* 코드33 */}
                  <td className="px-2 py-2 text-center">
                    {r.code33_pass ? (
                      <span
                        className="inline-block text-[11px] px-1.5 py-0.5 rounded font-bold"
                        style={{ backgroundColor: "rgba(233,193,118,0.2)", color: "#e9c176" }}
                        title="EPS·매출·순이익률 3분기 모두 가속"
                      >
                        ★ 통과
                      </span>
                    ) : r.evaluated_for_code33 ? (
                      <span className="text-[10px] text-on-surface-variant/40">미통과</span>
                    ) : (
                      <span className="text-[10px] text-on-surface-variant/30">평가외</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && (
        <p className="text-center text-on-surface-variant/60 py-6 text-sm">
          조건에 맞는 종목이 없습니다.
        </p>
      )}
    </div>
  );
}
