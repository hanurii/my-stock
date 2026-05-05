"use client";

import { useMemo, useState } from "react";

interface TopHolding {
  code?: string;
  name: string;
  weight_pct: number;
}

interface ETF {
  code: string;
  name: string;
  manager: string;
  geography: string;
  tracking_index: string | null;
  listed_date: string | null;
  expense_ratio_pct: number | null;
  aum_krw: number | null;
  trading_volume_30d_krw: number | null;
  ytd_return_pct: number | null;
  top_holdings: TopHolding[];
  metrics_updated_at: string | null;
  notes?: string;
}

interface Sector {
  key: string;
  label: string;
  aliases: string[];
  description: string;
  etf_codes: string[];
}

interface Props {
  sectors: Sector[];
  etfs: Record<string, ETF>;
}

interface ETFScore {
  total: number;
  grade: "A" | "B" | "C" | "D" | "—";
  parts: {
    expense: number | null;
    aum: number | null;
    volume: number | null;
    age: number | null;
    diversity: number | null;
  };
  data_completeness: number;
}

function formatMoney(amount: number | null): string {
  if (amount == null) return "—";
  if (amount >= 1e12) return `${(amount / 1e12).toFixed(1)}조`;
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(0)}억`;
  if (amount >= 1e4) return `${Math.round(amount / 1e4)}만`;
  return amount.toLocaleString();
}

function ageInYears(listed_date: string | null): number | null {
  if (!listed_date) return null;
  const start = new Date(listed_date);
  const now = new Date();
  return (now.getTime() - start.getTime()) / (365.25 * 24 * 3600 * 1000);
}

function clamp(x: number, lo = 0, hi = 100): number {
  return Math.max(lo, Math.min(hi, x));
}

function computeScore(etf: ETF): ETFScore {
  // 운용보수: 0.05% 만점, 0.5% 0점
  const expense =
    etf.expense_ratio_pct != null
      ? clamp(((0.5 - etf.expense_ratio_pct) / (0.5 - 0.05)) * 100)
      : null;

  // 펀드 규모: 1조 만점, 100억 0점 (로그 스케일)
  const aum =
    etf.aum_krw != null
      ? clamp(
          ((Math.log10(etf.aum_krw) - Math.log10(1e10)) /
            (Math.log10(1e12) - Math.log10(1e10))) *
            100,
        )
      : null;

  // 거래대금: 일 10억 만점, 1억 0점 (로그 스케일)
  const dailyVolume =
    etf.trading_volume_30d_krw != null
      ? etf.trading_volume_30d_krw / 30
      : null;
  const volume =
    dailyVolume != null
      ? clamp(
          ((Math.log10(dailyVolume) - Math.log10(1e8)) /
            (Math.log10(1e9) - Math.log10(1e8))) *
            100,
        )
      : null;

  // 상장기간: 5년 만점, 0년 0점
  const years = ageInYears(etf.listed_date);
  const age = years != null ? clamp((years / 5) * 100) : null;

  // 종목 분산: 상위 3종목 비중 합 30% 이하 만점, 80% 0점
  let diversity: number | null = null;
  if (etf.top_holdings.length > 0) {
    const top3 = [...etf.top_holdings]
      .sort((a, b) => b.weight_pct - a.weight_pct)
      .slice(0, 3)
      .reduce((s, h) => s + h.weight_pct, 0);
    diversity = clamp(((80 - top3) / (80 - 30)) * 100);
  }

  const parts = { expense, aum, volume, age, diversity };
  const present = Object.values(parts).filter((v) => v != null) as number[];
  const completeness = present.length / 5;
  const total =
    present.length > 0
      ? present.reduce((s, v) => s + v, 0) / present.length
      : 0;

  let grade: ETFScore["grade"] = "—";
  if (completeness >= 0.4) {
    if (total >= 80) grade = "A";
    else if (total >= 65) grade = "B";
    else if (total >= 50) grade = "C";
    else grade = "D";
  }

  return { total, grade, parts, data_completeness: completeness };
}

const GRADE_COLOR: Record<string, string> = {
  A: "#95d3ba",
  B: "#6ea8fe",
  C: "#d4b483",
  D: "#ffb4ab",
  "—": "#9ca3af",
};

export function ETFFinder({ sectors, etfs }: Props) {
  const [selectedKey, setSelectedKey] = useState<string>(
    sectors.find((s) => s.etf_codes.length > 0)?.key || sectors[0]?.key || "",
  );
  const [query, setQuery] = useState<string>("");

  // 검색: 별칭/이름 매칭
  const matchedSector = useMemo(() => {
    if (!query.trim()) return null;
    const q = query.trim().toLowerCase();
    return (
      sectors.find((s) =>
        [s.label, s.key, ...s.aliases].some((a) =>
          a.toLowerCase().includes(q),
        ),
      ) || null
    );
  }, [query, sectors]);

  const activeSector =
    matchedSector || sectors.find((s) => s.key === selectedKey) || null;

  const sectorETFs: Array<ETF & { score: ETFScore }> = useMemo(() => {
    if (!activeSector) return [];
    return activeSector.etf_codes
      .map((code) => etfs[code])
      .filter((e): e is ETF => !!e)
      .map((e) => ({ ...e, score: computeScore(e) }))
      .sort((a, b) => b.score.total - a.score.total);
  }, [activeSector, etfs]);

  return (
    <div className="space-y-6">
      {/* 검색 */}
      <div>
        <label className="block text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">
          섹터 검색
        </label>
        <div className="relative">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/40 text-xl">
            search
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="예: 반도체, HBM, 2차전지, 바이오, 방산..."
            className="w-full bg-surface-container-low ghost-border rounded-xl pl-12 pr-4 py-3 text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
          />
        </div>
        {query.trim() && !matchedSector && (
          <p className="text-xs text-on-surface-variant/60 mt-2">
            매칭되는 섹터 없음. 아래 목록에서 직접 선택하거나 etf-data.json에 섹터 추가.
          </p>
        )}
      </div>

      {/* 섹터 선택 카드 */}
      <div>
        <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-3">
          섹터 ({sectors.length}개)
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
          {sectors.map((s) => {
            const isActive = activeSector?.key === s.key;
            const hasETFs = s.etf_codes.length > 0;
            return (
              <button
                key={s.key}
                onClick={() => {
                  setSelectedKey(s.key);
                  setQuery("");
                }}
                className={`p-3 rounded-xl ghost-border text-left transition-all ${
                  isActive
                    ? "bg-primary/15 border-primary/50"
                    : "bg-surface-container-low hover:bg-surface-container/60"
                }`}
              >
                <div className="flex items-baseline justify-between gap-2 mb-0.5">
                  <p
                    className={`text-sm font-medium ${
                      isActive ? "text-primary" : "text-on-surface"
                    }`}
                  >
                    {s.label}
                  </p>
                  <span
                    className="text-xs font-mono"
                    style={{
                      color: hasETFs ? "#95d3ba" : "#9ca3af",
                    }}
                  >
                    {s.etf_codes.length}
                  </span>
                </div>
                <p className="text-[10px] text-on-surface-variant/50 leading-tight">
                  {s.aliases.slice(0, 3).join(" · ")}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* 활성 섹터 정보 */}
      {activeSector && (
        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <div className="flex items-baseline justify-between gap-3 mb-2 flex-wrap">
            <h3 className="text-xl font-serif text-on-surface">
              {activeSector.label}
            </h3>
            <p className="text-xs text-on-surface-variant/50 font-mono">
              {sectorETFs.length}개 ETF
            </p>
          </div>
          <p className="text-sm text-on-surface-variant mb-3">
            {activeSector.description}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {activeSector.aliases.map((a) => (
              <span
                key={a}
                className="text-[10px] px-2 py-0.5 rounded-full bg-surface-container/50 text-on-surface-variant/60"
              >
                #{a}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ETF 리스트 */}
      {activeSector && sectorETFs.length === 0 && (
        <div className="bg-surface-container-low rounded-xl p-10 ghost-border text-center">
          <span className="material-symbols-outlined text-primary-dim/30 text-4xl mb-3 block">
            inventory_2
          </span>
          <p className="text-on-surface-variant">
            아직 등록된 ETF가 없습니다.
          </p>
          <p className="text-xs text-on-surface-variant/50 mt-2">
            etf-data.json의 sectors[].etf_codes에 코드를 추가하고 etfs 객체에 메타데이터 입력.
          </p>
        </div>
      )}

      {sectorETFs.length > 0 && (
        <div className="space-y-3">
          {sectorETFs.map((etf, idx) => {
            const gradeColor = GRADE_COLOR[etf.score.grade];
            const hasMetrics =
              etf.expense_ratio_pct != null ||
              etf.aum_krw != null ||
              etf.trading_volume_30d_krw != null;
            return (
              <div
                key={etf.code}
                className="bg-surface-container-low rounded-xl ghost-border p-5 sm:p-6"
              >
                {/* 헤더 */}
                <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
                  <div className="flex items-start gap-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center font-mono font-bold text-sm shrink-0"
                      style={{
                        backgroundColor: `${gradeColor}20`,
                        color: gradeColor,
                      }}
                    >
                      {idx + 1}
                    </div>
                    <div>
                      <div className="flex items-baseline gap-2 flex-wrap">
                        <h4 className="text-lg font-medium text-on-surface">
                          {etf.name}
                        </h4>
                        <span className="text-xs text-on-surface-variant/50 font-mono">
                          {etf.code}
                        </span>
                      </div>
                      <p className="text-xs text-on-surface-variant/60 mt-0.5">
                        {etf.manager} · {etf.geography}
                        {etf.tracking_index ? ` · ${etf.tracking_index} 추종` : ""}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold"
                      style={{
                        backgroundColor: `${gradeColor}20`,
                        color: gradeColor,
                      }}
                    >
                      {etf.score.grade !== "—" && (
                        <span className="font-mono text-base">
                          {etf.score.grade}
                        </span>
                      )}
                      <span>
                        {etf.score.grade === "—"
                          ? "데이터 부족"
                          : `${Math.round(etf.score.total)}점`}
                      </span>
                    </div>
                    <p className="text-[10px] text-on-surface-variant/40 mt-1 font-mono">
                      완성도 {Math.round(etf.score.data_completeness * 100)}%
                    </p>
                  </div>
                </div>

                {/* 메트릭 그리드 */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
                  <Metric
                    label="운용보수"
                    value={
                      etf.expense_ratio_pct != null
                        ? `${etf.expense_ratio_pct.toFixed(2)}%`
                        : null
                    }
                    score={etf.score.parts.expense}
                  />
                  <Metric
                    label="펀드 규모"
                    value={etf.aum_krw != null ? formatMoney(etf.aum_krw) : null}
                    score={etf.score.parts.aum}
                  />
                  <Metric
                    label="30일 거래대금"
                    value={
                      etf.trading_volume_30d_krw != null
                        ? formatMoney(etf.trading_volume_30d_krw)
                        : null
                    }
                    score={etf.score.parts.volume}
                  />
                  <Metric
                    label="상장기간"
                    value={(() => {
                      const y = ageInYears(etf.listed_date);
                      return y != null ? `${y.toFixed(1)}년` : null;
                    })()}
                    score={etf.score.parts.age}
                  />
                  <ReturnMetric
                    label="올해 수익률"
                    value={etf.ytd_return_pct}
                  />
                </div>

                {/* 상위 종목 */}
                {etf.top_holdings.length > 0 && (
                  <div className="mb-4">
                    <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-2">
                      상위 종목 (분산 점수 {etf.score.parts.diversity != null ? `${Math.round(etf.score.parts.diversity)}점` : "—"})
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {[...etf.top_holdings]
                        .sort((a, b) => b.weight_pct - a.weight_pct)
                        .slice(0, 10)
                        .map((h) => (
                          <span
                            key={h.code || h.name}
                            className="text-xs px-2 py-1 rounded-md bg-surface-container/40 text-on-surface-variant"
                          >
                            {h.name}{" "}
                            <span className="text-on-surface-variant/50 font-mono">
                              {h.weight_pct.toFixed(1)}%
                            </span>
                          </span>
                        ))}
                    </div>
                  </div>
                )}

                {/* 노트 */}
                {etf.notes && (
                  <p className="text-xs text-on-surface-variant/60 leading-relaxed mt-3 pt-3 border-t border-outline-variant/10">
                    {etf.notes}
                  </p>
                )}

                {/* 데이터 미갱신 경고 */}
                {!hasMetrics && (
                  <div
                    className="mt-3 p-3 rounded-lg text-xs"
                    style={{ backgroundColor: "#d4b48312", color: "#d4b483" }}
                  >
                    <span className="material-symbols-outlined text-sm align-middle mr-1">
                      info
                    </span>
                    수치 데이터 미갱신. 정확한 평가를 위해 운용보수·펀드 규모·거래대금 입력 필요.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ReturnMetric({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {
  const color =
    value == null
      ? "#9ca3af"
      : value >= 0
        ? "#95d3ba"
        : "#ffb4ab";
  return (
    <div className="bg-surface-container/30 rounded-lg p-3">
      <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
        {label}
      </p>
      <p
        className="text-base font-mono font-bold"
        style={{ color: value == null ? "#9ca3af" : color }}
      >
        {value == null ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`}
      </p>
      <p className="text-[10px] text-on-surface-variant/40 mt-1">
        연초 대비 등락
      </p>
    </div>
  );
}

function Metric({
  label,
  value,
  score,
}: {
  label: string;
  value: string | null;
  score: number | null;
}) {
  const color =
    score == null
      ? "#9ca3af"
      : score >= 80
        ? "#95d3ba"
        : score >= 50
          ? "#d4b483"
          : "#ffb4ab";

  return (
    <div className="bg-surface-container/30 rounded-lg p-3">
      <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">
        {label}
      </p>
      <p
        className="text-base font-mono font-bold"
        style={{ color: value ? color : "#9ca3af" }}
      >
        {value ?? "—"}
      </p>
      {score != null && (
        <div className="mt-1.5 h-1 bg-surface-container/50 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{
              width: `${score}%`,
              backgroundColor: color,
            }}
          />
        </div>
      )}
    </div>
  );
}
