"use client";

import { useState } from "react";

// ── 타입 ──

interface ScoreDetail {
  item: string;
  basis: string;
  score: number;
  max: number;
  cat: number;
}

interface TrackACandidate {
  code: string;
  name: string;
  market: string;
  score: number;
  grade: string;
  cat1: number;
  cat2: number;
  cat3: number;
  details: ScoreDetail[];
  data_confidence: string;
  market_cap: number;
  current_price: number;
  highest_phase: string;
  pipeline_count: number;
  has_bigpharma_deal: boolean;
}

interface PipelineMilestones {
  patent: boolean;
  publication: boolean;
  preclinical: boolean;
  phase1: boolean;
  phase2: boolean;
  phase3: boolean | "in_progress";
  nda: boolean;
  approved: boolean;
}

interface Pipeline {
  name: string;
  indication: string;
  phase: string;
  phase_status: string;
  start_date: string;
  est_completion: string;
  milestones: PipelineMilestones;
  external_validation: string[];
  filter_met: number;
  tech_summary: string;
  tech_detail: string;
  market_impact: string;
  global_exclusivity: {
    competing_trials: number;
    patent_scope: string;
    uniqueness: string;
  };
}

interface TrackBCandidate {
  code: string;
  name: string;
  market: string;
  score: number;
  grade: string;
  cat1: number;
  cat2: number;
  cat3: number;
  details: ScoreDetail[];
  data_confidence: string;
  market_cap: number;
  current_price: number;
  pipelines: Pipeline[];
}

interface BioTabsProps {
  trackA: TrackACandidate[];
  trackB: TrackBCandidate[];
}

// ── 유틸 ──

function fmtNum(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}조`;
  return `${n.toLocaleString()}억`;
}

const gradeColors: Record<string, string> = {
  A: "#95d3ba", B: "#6ea8fe", C: "#e9c176", D: "#ffb4ab",
};

const phaseLabels: Record<string, string> = {
  approved: "허가/출시", phase3: "3상", phase2: "2상", phase1: "1상", preclinical: "전임상", none: "-",
};

// ── 컴포넌트 ──

export function BioTabs({ trackA, trackB }: BioTabsProps) {
  const [tab, setTab] = useState<"a" | "b">("a");

  return (
    <div>
      {/* 탭 헤더 */}
      <div className="flex gap-1 mb-6 bg-surface-container-low rounded-lg p-1">
        <button
          onClick={() => setTab("a")}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
            tab === "a" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container"
          }`}
        >
          <span className="material-symbols-outlined text-base align-middle mr-1">verified</span>
          안정형 ({trackA.length})
        </button>
        <button
          onClick={() => setTab("b")}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
            tab === "b" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container"
          }`}
        >
          <span className="material-symbols-outlined text-base align-middle mr-1">rocket_launch</span>
          유망형 ({trackB.length})
        </button>
      </div>

      {tab === "a" ? <TrackAView candidates={trackA} /> : <TrackBView candidates={trackB} />}
    </div>
  );
}

// ── A 트랙: 종목 카드 ──

function TrackAView({ candidates }: { candidates: TrackACandidate[] }) {
  return (
    <div className="space-y-4">
      {candidates.map((stock, i) => {
        const color = gradeColors[stock.grade] || "#909097";
        return (
          <div key={stock.code} className="bg-surface-container-low rounded-xl ghost-border p-4 sm:p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className="text-xl font-serif font-bold w-8" style={{ color }}>{i + 1}</span>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-base font-medium text-on-surface">{stock.name}</h4>
                    <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>{stock.grade}</span>
                    <span className="text-xs text-on-surface-variant/50">{stock.market}</span>
                    {stock.has_bigpharma_deal && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#95d3ba20", color: "#95d3ba" }}>빅파마</span>
                    )}
                    {stock.data_confidence === "low" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#ffb4ab20", color: "#ffb4ab" }}>데이터 부족</span>
                    )}
                  </div>
                  <p className="text-sm text-on-surface-variant">{stock.code} · 시총 {fmtNum(stock.market_cap)}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-serif font-bold" style={{ color }}>{stock.score}</p>
                <p className="text-xs text-on-surface-variant">/100점</p>
              </div>
            </div>

            {/* 핵심 지표 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
              {[
                { label: "임상 단계", value: phaseLabels[stock.highest_phase] || "-" },
                { label: "파이프라인", value: `${stock.pipeline_count}개` },
                { label: "시총", value: fmtNum(stock.market_cap) },
                { label: "현재가", value: `${stock.current_price.toLocaleString()}원` },
              ].map(({ label, value }) => (
                <div key={label} className="bg-surface-container/30 rounded-lg p-2 text-center">
                  <p className="text-xs text-on-surface-variant">{label}</p>
                  <p className="text-sm font-mono text-on-surface mt-0.5">{value}</p>
                </div>
              ))}
            </div>

            {/* 카테고리 점수 바 */}
            <div className="grid grid-cols-3 gap-2 mb-3">
              {[
                { label: "기술 검증", score: stock.cat1, max: 35 },
                { label: "임상/사업", score: stock.cat2, max: 45 },
                { label: "경영/재무", score: stock.cat3, max: 20 },
              ].map(({ label, score, max }) => {
                const pct = max > 0 ? (score / max) * 100 : 0;
                return (
                  <div key={label} className="text-center">
                    <p className="text-xs text-on-surface-variant mb-1">{label}</p>
                    <div className="h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{
                        width: `${pct}%`,
                        backgroundColor: pct >= 70 ? "#95d3ba" : pct >= 50 ? "#e9c176" : "#ffb4ab",
                      }} />
                    </div>
                    <p className="text-xs font-mono text-on-surface mt-0.5">{score}/{max}</p>
                  </div>
                );
              })}
            </div>

            {/* 세부 채점 (접을 수 있음) */}
            <Details summary="세부 채점">
              <div className="space-y-1 mt-2">
                {stock.details.map((d) => (
                  <div key={d.item} className="flex items-center justify-between text-sm py-1">
                    <span className="text-on-surface-variant">{d.item}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-on-surface-variant/60">{d.basis}</span>
                      <span className="font-mono text-on-surface" style={{ color: d.score < 0 ? "#ffb4ab" : undefined }}>
                        {d.max > 0 ? `${d.score}/${d.max}` : d.score > 0 ? `+${d.score}` : `${d.score}`}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Details>
          </div>
        );
      })}
    </div>
  );
}

// ── B 트랙: 프로세스 흐름도 ──

const MILESTONES = [
  { key: "patent", label: "특허", icon: "license" },
  { key: "publication", label: "논문", icon: "article" },
  { key: "preclinical", label: "전임상", icon: "science" },
  { key: "phase1", label: "1상", icon: "clinical_notes" },
  { key: "phase2", label: "2상", icon: "monitor_heart" },
  { key: "phase3", label: "3상", icon: "vaccines" },
  { key: "nda", label: "허가신청", icon: "assignment_turned_in" },
  { key: "approved", label: "승인", icon: "verified" },
] as const;

function TrackBView({ candidates }: { candidates: TrackBCandidate[] }) {
  if (candidates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <span className="material-symbols-outlined text-5xl text-primary-dim/30 mb-4">rocket_launch</span>
        <p className="text-on-surface-variant text-sm">B 트랙 조건을 충족하는 파이프라인이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {candidates.map((company) => {
        const color = gradeColors[company.grade] || "#909097";
        return (
          <div key={company.code} className="space-y-4">
            {company.pipelines.map((pl, pi) => (
              <div key={pi} className="bg-surface-container-low rounded-xl ghost-border p-4 sm:p-6">
                {/* 기업 + 점수 헤더 */}
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-base font-medium text-on-surface">{company.name}</h4>
                      <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>{company.grade}</span>
                      <span className="text-xs text-on-surface-variant/50">{company.market}</span>
                    </div>
                    <p className="text-sm text-on-surface-variant">{company.code} · 시총 {fmtNum(company.market_cap)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-serif font-bold" style={{ color }}>{company.score}</p>
                    <p className="text-xs text-on-surface-variant">/100점</p>
                  </div>
                </div>

                {/* 파이프라인 제목 + 적응증 */}
                <div className="mb-4">
                  <h5 className="text-sm font-bold text-primary mb-1">{pl.name.length > 80 ? pl.name.slice(0, 80) + "..." : pl.name}</h5>
                  <p className="text-xs text-on-surface-variant">적응증: {pl.indication || "-"}</p>
                  {pl.est_completion && <p className="text-xs text-on-surface-variant/60 mt-0.5">예상 완료: {pl.est_completion}</p>}
                </div>

                {/* 프로세스 흐름도 */}
                <div className="mb-4 overflow-x-auto">
                  <div className="flex items-center gap-0 min-w-[600px]">
                    {MILESTONES.map((ms, mi) => {
                      const val = pl.milestones[ms.key as keyof PipelineMilestones];
                      const done = val === true;
                      const inProgress = val === "in_progress";
                      const bg = done ? "#95d3ba" : inProgress ? "#e9c176" : "transparent";
                      const border = done ? "#95d3ba" : inProgress ? "#e9c176" : "rgba(255,255,255,0.1)";
                      const textColor = done || inProgress ? "#1a1a1a" : "rgba(255,255,255,0.3)";

                      return (
                        <div key={ms.key} className="flex items-center">
                          <div className="flex flex-col items-center" style={{ minWidth: 64 }}>
                            <div
                              className="w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all"
                              style={{ backgroundColor: bg, borderColor: border }}
                            >
                              <span className="material-symbols-outlined text-base" style={{ color: textColor }}>
                                {done ? "check" : inProgress ? "pending" : ms.icon}
                              </span>
                            </div>
                            <span className={`text-[10px] mt-1 ${done || inProgress ? "text-on-surface" : "text-on-surface-variant/30"}`}>
                              {ms.label}
                            </span>
                          </div>
                          {mi < MILESTONES.length - 1 && (
                            <div className="w-4 h-0.5 -mt-3" style={{ backgroundColor: done ? "#95d3ba" : "rgba(255,255,255,0.08)" }} />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* 외부 검증 배지 */}
                {pl.external_validation.length > 0 && (
                  <div className="flex gap-2 mb-4">
                    {pl.external_validation.includes("bigpharma_lo") && (
                      <span className="text-xs px-2 py-1 rounded-full" style={{ backgroundColor: "#95d3ba20", color: "#95d3ba" }}>
                        <span className="material-symbols-outlined text-xs align-middle mr-0.5">handshake</span>
                        빅파마 L/O
                      </span>
                    )}
                    {pl.external_validation.includes("asco_oral") && (
                      <span className="text-xs px-2 py-1 rounded-full" style={{ backgroundColor: "#6ea8fe20", color: "#6ea8fe" }}>
                        <span className="material-symbols-outlined text-xs align-middle mr-0.5">podium</span>
                        학회 구두 발표
                      </span>
                    )}
                  </div>
                )}

                {/* 기술 상세 */}
                {pl.tech_summary && (
                  <Details summary="기술 소개">
                    <p className="text-sm text-on-surface-variant mt-2 leading-relaxed">{pl.tech_summary}</p>
                    {pl.tech_detail && (
                      <p className="text-xs text-on-surface-variant/60 mt-2 leading-relaxed">{pl.tech_detail.slice(0, 500)}{pl.tech_detail.length > 500 ? "..." : ""}</p>
                    )}
                  </Details>
                )}

                {/* 시장 파급력 + 독점성 */}
                {(pl.market_impact || pl.global_exclusivity.competing_trials > 0) && (
                  <Details summary="시장 파급력 / 독점성">
                    <div className="mt-2 space-y-2">
                      {pl.market_impact && <p className="text-sm text-on-surface-variant">{pl.market_impact}</p>}
                      {pl.global_exclusivity.competing_trials > 0 && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-on-surface-variant/60">동일 적응증 3상 경쟁:</span>
                          <span className="text-sm font-mono text-on-surface">{pl.global_exclusivity.competing_trials}개</span>
                        </div>
                      )}
                      {pl.global_exclusivity.uniqueness && (
                        <p className="text-xs text-on-surface-variant/60">{pl.global_exclusivity.uniqueness}</p>
                      )}
                    </div>
                  </Details>
                )}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

// ── 간이 Details 컴포넌트 (HTML details/summary) ──

function Details({ summary, children }: { summary: string; children: React.ReactNode }) {
  return (
    <details className="mt-3 group">
      <summary className="cursor-pointer text-xs text-on-surface-variant/60 hover:text-on-surface-variant flex items-center gap-1">
        <span className="material-symbols-outlined text-sm group-open:rotate-90 transition-transform">chevron_right</span>
        {summary}
      </summary>
      {children}
    </details>
  );
}
