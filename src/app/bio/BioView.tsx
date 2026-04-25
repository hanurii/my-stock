"use client";

import React from "react";

// ── 타입 ──

interface PipelineQuality {
  patent_matched_count: number;
  patent_search_keywords: string[];
  pubmed_count: number;
  high_if_papers: number;
  total_citations: number;
  notable_journals: string[];
  conference_level: string | null;
  has_results_posted: boolean;
  bigpharma_deal: { tier: string; terminated: boolean };
  contract_structure: string | null;
  milestone_ratio: number | null;
  ceo_background: string;
  phase1_cleared: boolean;
}

interface ClinicalAssessmentDetail {
  signal: "good" | "warn" | "bad";
  text: string;
}

interface ClinicalAssessment {
  verdict: "good" | "caution" | "danger";
  design: string;
  sample_size: string;
  primary_endpoint: string;
  p_value: string;
  details: ClinicalAssessmentDetail[];
  conclusion: string;
  sources: string[];
}

interface Pipeline {
  nct_id: string;
  company: { code: string; name: string; market: string; market_cap: number };
  trial_name: string;
  indication: string;
  disease_category: string;
  phase: string;
  status: string;
  start_date: string;
  est_completion: string;
  tech_summary_en: string;
  competing_phase3_count: number;
  quality: PipelineQuality;
  clinical_assessment?: ClinicalAssessment;
}

interface Milestone {
  date: string;
  event: string;
  location?: string;
  session?: string;
  content: string;
  importance?: "high" | "medium" | "low";
  source?: { label: string; url: string };
}

interface Briefing {
  tech_kr: string;
  market_briefing: string;
  upcoming_milestones?: Milestone[];
}

interface QualityCheck {
  signal: "good" | "bad" | "warn";
  detail: string;
}

interface ResearchData {
  company: string;
  quality_checks: Record<string, QualityCheck>;
}

interface BioViewProps {
  pipelines: Pipeline[];
  briefings: Record<string, Briefing>;
  research: Record<string, ResearchData>;
}

// ── 유틸 ──

function fmtNum(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}조`;
  return `${n.toLocaleString()}억`;
}

const phaseLabel: Record<string, string> = { PHASE3: "3상", PHASE2: "2상", PHASE1: "1상", "N/A": "전임상" };
const statusLabel: Record<string, string> = {
  RECRUITING: "모집 중",
  ACTIVE_NOT_RECRUITING: "진행 중 (모집 완료)",
  NOT_YET_RECRUITING: "모집 예정",
  ENROLLING_BY_INVITATION: "초청만 참여 가능",
  COMPLETED: "완료",
  TERMINATED: "종료",
  WITHDRAWN: "철회",
};

// ── 프로세스 단계 정의 ──

type Signal = "good" | "star" | "star2" | "bad" | "none";

interface StepResult {
  label: string;
  reached: boolean;   // 이 단계를 통과/진행 중인지
  current: boolean;    // 현재 진행 중인 단계인지
  signal: Signal;      // 질적 시그널
  detail: string;      // 시그널 사유
}

function buildSteps(pl: Pipeline): StepResult[] {
  const q = pl.quality;
  const isPhase1 = pl.phase === "PHASE1";
  const isPhase2 = pl.phase === "PHASE2";
  const isPhase3 = pl.phase === "PHASE3";
  const isCompleted = pl.status === "COMPLETED";
  const isTerminated = pl.status === "TERMINATED" || pl.status === "WITHDRAWN";

  // 특허 (기술별 키워드 매칭)
  const patentSignal: Signal = q.patent_matched_count > 0 ? "good" : "bad";
  const patentDetail = q.patent_matched_count > 0
    ? `관련 특허 ${q.patent_matched_count}건`
    : "관련 특허 없음";

  // 논문 (프로세스 바에서는 존재 여부만, 상세는 세부 검증에서)
  const paperExistSignal: Signal = q.pubmed_count > 0 ? "good" : "bad";
  const paperExistDetail = q.pubmed_count > 0 ? `논문 ${q.pubmed_count}편` : "논문 없음";

  // 학회: 저명학회 구두=별2, 포스터/기타=뱃지없음, 없음=경고
  const confSignal: Signal = q.conference_level === "oral_top4" ? "star2"
    : q.conference_level === "poster_top4" || q.conference_level === "other_intl" ? "none"
    : "bad";
  const confDetail = q.conference_level === "oral_top4" ? "ASCO/ASH/AACR/ESMO 구두 발표"
    : q.conference_level === "poster_top4" ? "포스터 발표"
    : q.conference_level === "other_intl" ? "기타 학회 발표"
    : "발표 없음";

  // 1상
  const p1Reached = isPhase1 || isPhase2 || isPhase3;
  const p1Current = isPhase1 && !isCompleted && !isTerminated;
  const p1Signal: Signal = isPhase1 && isTerminated ? "bad" : "none";
  const p1Detail = isPhase1 && isCompleted ? "1상 완료"
    : isPhase1 && isTerminated ? "종료/철회"
    : p1Reached && !isPhase1 ? "안전성 통과"
    : "진행 중";

  // 2상
  const p2Reached = isPhase2 || isPhase3;
  const p2Current = isPhase2 && !isCompleted && !isTerminated;
  let p2Signal: Signal;
  let p2Detail: string;
  if (isPhase3) {
    p2Signal = q.has_results_posted ? "good" : "bad";
    p2Detail = q.has_results_posted ? "2상 완료, 결과 공개됨" : "2상 완료, 결과 미공개";
  } else if (isPhase2 && isCompleted) {
    p2Signal = q.has_results_posted ? "good" : "none";
    p2Detail = q.has_results_posted ? "2상 완료, 결과 공개됨" : "2상 완료";
  } else if (isPhase2 && isTerminated) {
    p2Signal = "bad";
    p2Detail = "종료/철회";
  } else if (isPhase2) {
    p2Signal = "none";
    p2Detail = "진행 중";
  } else {
    p2Signal = "none";
    p2Detail = "";
  }

  // 3상
  const p3Current = isPhase3 && !isCompleted && !isTerminated;
  let p3Signal: Signal = "none";
  let p3Detail = "";
  if (isPhase3 && isCompleted) { p3Signal = "good"; p3Detail = "3상 완료"; }
  else if (isPhase3 && isTerminated) { p3Signal = "bad"; p3Detail = "종료/철회"; }
  else if (isPhase3) { p3Detail = "진행 중"; }

  // 빅파마
  const pharmaSignal: Signal = q.bigpharma_deal.terminated ? "bad"
    : q.bigpharma_deal.tier === "top20" ? "star"
    : q.bigpharma_deal.tier === "global" ? "good"
    : "none";
  const pharmaDetail = q.bigpharma_deal.terminated ? "계약 파기 이력"
    : q.bigpharma_deal.tier === "top20" ? "Top20 빅파마 계약"
    : q.bigpharma_deal.tier === "global" ? "글로벌 빅파마 계약"
    : "빅파마 계약 없음";

  return [
    { label: "특허", reached: q.patent_matched_count > 0, current: false, signal: patentSignal, detail: patentDetail },
    { label: "논문", reached: q.pubmed_count > 0, current: false, signal: paperExistSignal, detail: paperExistDetail },
    { label: "학회발표", reached: q.conference_level != null, current: false, signal: confSignal, detail: confDetail },
    { label: "1상", reached: p1Reached, current: p1Current, signal: p1Signal, detail: p1Detail },
    { label: "2상", reached: p2Reached, current: p2Current, signal: p2Signal, detail: p2Detail },
    { label: "3상", reached: isPhase3, current: p3Current, signal: p3Signal, detail: p3Detail },
    { label: "허가", reached: false, current: false, signal: "none", detail: "" },
  ];
}

// ── 빅파마 관심도 점수 (파이프라인 정렬용) ──

const PHARMA_TIER_SCORE: Record<string, number> = { top20: 3, global: 2, domestic: 1, none: 0 };

function bigpharmaScore(pl: Pipeline): number {
  const q = pl.quality;
  let score = PHARMA_TIER_SCORE[q.bigpharma_deal.tier] || 0;
  if (q.bigpharma_deal.terminated) score -= 1;
  return score;
}

// ── research good 갯수 ──

function countGood(r?: ResearchData): number {
  if (!r?.quality_checks) return 0;
  return Object.values(r.quality_checks).filter(c => c.signal === "good").length;
}

// ── 메인 컴포넌트 ──

export function BioView({ pipelines, briefings, research }: BioViewProps) {
  // 기업별 그룹핑
  const groups = new Map<string, Pipeline[]>();
  for (const pl of pipelines) {
    const key = pl.company.code;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(pl);
  }

  // 기업별 정렬: research의 good 갯수 내림차순
  const sortedGroups = [...groups.entries()].sort((a, b) => {
    const aGood = countGood(research[a[0]]);
    const bGood = countGood(research[b[0]]);
    return bGood - aGood;
  });

  // 각 기업 내 파이프라인 정렬: 빅파마 관심도 내림차순
  for (const [, pls] of sortedGroups) {
    pls.sort((a, b) => bigpharmaScore(b) - bigpharmaScore(a));
  }

  return (
    <div className="space-y-8">
      {/* 기업별 상세 */}
      {sortedGroups.map(([companyCode, pls]) => {
        const company = pls[0].company;
        const r = research[companyCode];
        const goodCnt = countGood(r);
        const totalChecks = r?.quality_checks ? Object.keys(r.quality_checks).length : 0;

        return (
          <div key={companyCode} id={`company-${companyCode}`}>
            <h3 className="text-lg font-bold font-serif text-primary mb-1 flex items-center gap-2">
              {company.name}
              <span className="text-xs font-normal text-on-surface-variant">
                {company.market} · {companyCode} · 시총 {fmtNum(company.market_cap)}
              </span>
              {totalChecks > 0 && (
                <span className="text-xs px-2 py-0.5 rounded font-bold" style={{
                  backgroundColor: goodCnt >= 5 ? "#95d3ba20" : goodCnt >= 3 ? "#e9c17620" : "#ffb4ab20",
                  color: goodCnt >= 5 ? "#95d3ba" : goodCnt >= 3 ? "#e9c176" : "#ffb4ab",
                }}>
                  7대 기준 ✓ {goodCnt}/{totalChecks}
                </span>
              )}
            </h3>
            {/* 빅파마 / 계약 요약 */}
            {r?.quality_checks?.bigpharma && (
              <div className="mt-2 mb-1 flex items-start gap-2 text-xs">
                <span className="shrink-0 font-medium" style={{ color: "#e9c176" }}>빅파마</span>
                <span className="text-on-surface-variant">{r.quality_checks.bigpharma.detail}</span>
              </div>
            )}
            {r?.quality_checks?.contract && (
              <div className="mb-1 flex items-start gap-2 text-xs">
                <span className="shrink-0 font-medium text-on-surface-variant/60">계약</span>
                <span className="text-on-surface-variant">{r.quality_checks.contract.detail}</span>
              </div>
            )}
            <p className="text-xs text-on-surface-variant/50 mb-4 mt-2">{pls.length}건의 파이프라인</p>
            <div className="space-y-4">
              {pls.map((pl) => (
                <PipelineCard key={pl.nct_id} pipeline={pl} briefing={briefings[pl.nct_id]} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── 파이프라인 카드 ──

function PipelineCard({ pipeline: pl, briefing }: { pipeline: Pipeline; briefing?: Briefing }) {
  const q = pl.quality;
  const steps = buildSteps(pl);

  return (
    <div className="bg-surface-container-low rounded-xl ghost-border p-4 sm:p-5">
      {/* 헤더 */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="text-xs px-2 py-0.5 rounded font-bold" style={{
            backgroundColor: pl.phase === "PHASE3" ? "#95d3ba20" : "#6ea8fe20",
            color: pl.phase === "PHASE3" ? "#95d3ba" : "#6ea8fe",
          }}>{phaseLabel[pl.phase] || pl.phase}</span>
          <span className="text-xs text-on-surface-variant/50">{statusLabel[pl.status] || pl.status.replace(/_/g, " ")}</span>
          <BigPharmaBadge deal={q.bigpharma_deal} />
        </div>
        <h4 className="text-sm font-medium text-on-surface leading-snug mb-1">
          {briefing?.tech_kr || pl.trial_name}
        </h4>
        <p className="text-xs text-on-surface-variant">
          {pl.company.name} · {pl.company.market} · 시총 {fmtNum(pl.company.market_cap)}
          {q.bigpharma_deal.terminated && (
            <span className="ml-1" style={{ color: "#ffb4ab", fontSize: "10px" }}>과거 빅파마 계약 파기 이력</span>
          )}
          {q.bigpharma_deal.tier !== "top20" && q.bigpharma_deal.tier !== "global" && (
            <span className="ml-1 text-on-surface-variant/30" style={{ fontSize: "10px" }}>· 빅파마 계약 없음</span>
          )}
        </p>
      </div>

      {/* 프로세스 바 */}
      <ProcessBar steps={steps} />

      {/* 다가오는 마일스톤 */}
      {briefing?.upcoming_milestones && briefing.upcoming_milestones.length > 0 && (
        <div className="space-y-2 mt-4">
          {briefing.upcoming_milestones.map((m, i) => (
            <UpcomingMilestoneBox key={i} milestone={m} />
          ))}
        </div>
      )}

      {/* AI 시장 브리핑 */}
      {briefing?.market_briefing && (
        <div className="bg-primary/5 rounded-lg p-3 mt-4 border border-primary/10">
          <p className="text-xs font-medium text-primary mb-1">시장 분석</p>
          <p className="text-sm text-on-surface leading-relaxed">{briefing.market_briefing}</p>
        </div>
      )}

      {/* 세부 질적 검증 (접이식, 기본 접힘) */}
      <details className="mt-3 group">
        <summary className="cursor-pointer text-xs text-on-surface-variant/60 hover:text-on-surface-variant flex items-center gap-1">
          <span className="material-symbols-outlined text-sm group-open:rotate-90 transition-transform">chevron_right</span>
          기술 질적 검증 상세
        </summary>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Box 1: 특허 */}
          <DetailBox title="특허">
            <DetailRow label="특허" signal={steps.find(s => s.label === "특허")!.signal} detail={steps.find(s => s.label === "특허")!.detail} />
            {q.patent_search_keywords?.length > 0 && (
              <p className="text-[10px] text-on-surface-variant/40 mt-1">키워드: {q.patent_search_keywords.join(", ")}</p>
            )}
          </DetailBox>

          {/* Box 2: 논문 · 학회 */}
          <DetailBox title="논문 · 학회">
            <DetailRow label="논문" signal={steps.find(s => s.label === "논문")!.signal} detail={steps.find(s => s.label === "논문")!.detail} />
            <DetailRow label="인용수"
              signal={q.total_citations >= 300 ? "good" : q.total_citations > 0 ? "none" : "bad"}
              detail={q.total_citations > 0
                ? `피인용 ${q.total_citations.toLocaleString()}회 (${q.total_citations >= 1000 ? "매우높음" : q.total_citations >= 300 ? "높음" : q.total_citations >= 50 ? "중간" : "낮음"})`
                : "인용 실적 없음"} />
            <DetailRow label="저명 저널"
              signal={q.notable_journals?.length > 0 ? "star" : "bad"}
              detail={q.notable_journals?.length > 0
                ? `게재 (${q.notable_journals.join(", ")})`
                : "저명 저널 게재 없음"} />
            <DetailRow label="학회발표" signal={steps.find(s => s.label === "학회발표")!.signal} detail={steps.find(s => s.label === "학회발표")!.detail} />
          </DetailBox>

          {/* Box 3: 임상 진행 */}
          <DetailBox title="임상 진행">
            {steps.filter(s => ["1상", "2상", "3상"].includes(s.label)).map(step => (
              step.detail && <DetailRow key={step.label} label={step.label} signal={step.signal} detail={step.detail} />
            ))}
          </DetailBox>

          {/* Box 4: 경영 · 계약 */}
          <DetailBox title="경영 · 계약">
            <DetailRow label="경영진"
              signal={q.ceo_background === "scientist" ? "good" : q.ceo_background === "cto_scientist" ? "good" : "bad"}
              detail={q.ceo_background === "scientist" ? "박사/연구원 출신 CEO"
                : q.ceo_background === "cto_scientist" ? "기술자 CTO 보유"
                : q.ceo_background === "professional" ? "경영 전문가(금융/경영) — 기술자 부재"
                : "경영진 기술 전문성 확인 불가"} />
            {q.contract_structure && (
              <DetailRow label="계약 구조"
                signal={q.contract_structure === "no_return" ? "good" : q.contract_structure === "returnable" ? "bad" : "none"}
                detail={q.contract_structure === "no_return" ? "반환의무 없음"
                  : q.contract_structure === "returnable" ? "반환의무 있음 — 기술 가치 의문"
                  : "불명"} />
            )}
            {q.milestone_ratio != null && q.milestone_ratio > 50 && (
              <DetailRow label="마일스톤" signal="bad"
                detail={`마일스톤 비중 ${q.milestone_ratio}% — 확정 수령 아님`} />
            )}
          </DetailBox>

          {/* Box 5: 임상 데이터 평가 (있을 때만) */}
          {pl.clinical_assessment && (
            <AssessmentBox assessment={pl.clinical_assessment} />
          )}

          {/* 메타 정보 */}
          <div className="sm:col-span-2 flex flex-wrap gap-3 text-xs text-on-surface-variant/50 pt-2 mt-1 border-t border-on-surface-variant/10">
            <span>NCT: {pl.nct_id}</span>
            <span>적응증: {pl.indication}</span>
            {pl.competing_phase3_count > 0 && <span>3상 경쟁: {pl.competing_phase3_count}개</span>}
            {pl.est_completion && <span>예상 완료: {pl.est_completion}</span>}
            {pl.start_date && <span>시작: {pl.start_date}</span>}
          </div>
        </div>
      </details>
    </div>
  );
}

// ── 프로세스 바 ──

// ── 빅파마 칭호 뱃지 ──

function BigPharmaBadge({ deal }: { deal: { tier: string; terminated: boolean } }) {
  // 계약 파기는 회사명 옆에 별도 표시하므로 여기서는 현재 상태만
  if (deal.tier === "top20") {
    return (
      <span className="text-[10px] px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: "#e9c17630", color: "#e9c176" }}>
        ★ Top20 빅파마
      </span>
    );
  }
  if (deal.tier === "global") {
    return (
      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#95d3ba20", color: "#95d3ba" }}>
        글로벌 빅파마
      </span>
    );
  }
  // domestic 또는 none — 회사명 옆에 표시하므로 여기선 생략
  return null;
}

const SIGNAL_COLORS: Record<Signal, string> = {
  star2: "#e9c176",
  star: "#e9c176",
  good: "#95d3ba",
  bad: "#ffb4ab",
  none: "",
};

const SIGNAL_ICON: Record<Signal, string> = {
  star2: "★★",
  star: "★",
  good: "✓",
  bad: "✕",
  none: "",
};

function ProcessBar({ steps }: { steps: StepResult[] }) {
  return (
    <div className="overflow-x-auto">
      <div className="flex items-start gap-0 min-w-[560px]">
        {steps.map((step, i) => {
          const reached = step.reached;
          const current = step.current;
          const hasSignal = step.signal !== "none";

          // 원 색상: bad 시그널이면 빨간 테두리
          const isBad = step.signal === "bad";
          const circleBg = current ? "#6ea8fe" : reached ? "#95d3ba" : isBad ? "transparent" : "transparent";
          const circleBorder = current ? "#6ea8fe" : reached ? "#95d3ba" : isBad ? "#ffb4ab" : "rgba(255,255,255,0.12)";
          const iconColor = reached || current ? "#1a1a1a" : isBad ? "#ffb4ab" : "rgba(255,255,255,0.2)";

          // 연결선
          const lineDone = reached && i < steps.length - 1 && steps[i + 1].reached;

          return (
            <div key={step.label} className="flex items-start">
              <div className="flex flex-col items-center" style={{ minWidth: 68 }}>
                {/* 원 */}
                <div className="relative">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center border-2"
                    style={{ backgroundColor: circleBg, borderColor: circleBorder }}
                  >
                    {current ? (
                      <span className="material-symbols-outlined text-sm" style={{ color: iconColor }}>pending</span>
                    ) : reached ? (
                      <span className="material-symbols-outlined text-sm" style={{ color: iconColor }}>check</span>
                    ) : isBad ? (
                      <span className="text-sm font-bold" style={{ color: iconColor }}>✕</span>
                    ) : (
                      <span className="text-[10px]" style={{ color: iconColor }}>{i + 1}</span>
                    )}
                  </div>
                  {/* 시그널 뱃지 */}
                  {hasSignal && (
                    <span
                      className="absolute -top-1.5 -right-1.5 text-xs font-bold w-4 h-4 flex items-center justify-center rounded-full"
                      style={{
                        color: SIGNAL_COLORS[step.signal],
                        backgroundColor: `${SIGNAL_COLORS[step.signal]}18`,
                        fontSize: "10px",
                      }}
                    >
                      {SIGNAL_ICON[step.signal]}
                    </span>
                  )}
                </div>
                {/* 라벨 */}
                <span className={`text-[10px] mt-1 ${reached || current ? "text-on-surface" : "text-on-surface-variant/30"}`}>
                  {step.label}
                </span>
                {/* 시그널 사유 (짧게) */}
                {hasSignal && (
                  <span className="text-[9px] mt-0.5 max-w-[64px] text-center leading-tight" style={{ color: SIGNAL_COLORS[step.signal] }}>
                    {step.detail.length > 12 ? step.detail.slice(0, 12) + "…" : step.detail}
                  </span>
                )}
              </div>
              {/* 연결선 */}
              {i < steps.length - 1 && (
                <div className="w-3 h-0.5 mt-4" style={{
                  backgroundColor: lineDone ? "#95d3ba" : "rgba(255,255,255,0.08)",
                }} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 다가오는 마일스톤 박스 ──

function UpcomingMilestoneBox({ milestone: m }: { milestone: Milestone }) {
  const accent = m.importance === "high" ? "#e9c176" : m.importance === "low" ? "#bcc7de" : "#95d3ba";
  return (
    <div
      className="rounded-lg p-3 sm:p-4"
      style={{
        background: `linear-gradient(155deg, ${accent}15 0%, ${accent}05 60%, transparent 100%)`,
        border: `1px solid ${accent}30`,
        boxShadow: `0 0 0 1px ${accent}10`,
      }}
    >
      <div className="flex items-start gap-2.5">
        <span className="material-symbols-outlined text-base shrink-0 mt-0.5" style={{ color: accent }}>
          event
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap mb-1">
            <span className="text-[10px] uppercase tracking-[0.18em] font-medium" style={{ color: accent }}>
              다가오는 마일스톤
            </span>
            <span className="text-[11px] font-mono" style={{ color: accent }}>{m.date}</span>
          </div>
          <p className="text-sm font-medium text-on-surface leading-snug">
            {m.event}
            {m.location && <span className="text-on-surface-variant/70 font-normal"> · {m.location}</span>}
          </p>
          {m.session && (
            <p className="text-[11px] mt-0.5" style={{ color: accent }}>{m.session}</p>
          )}
          <p className="text-xs text-on-surface-variant leading-relaxed mt-1.5">{m.content}</p>
          {m.source && (
            <a
              href={m.source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] text-on-surface-variant/50 hover:text-primary mt-2 transition-colors"
            >
              <span className="material-symbols-outlined" style={{ fontSize: "12px" }}>link</span>
              {m.source.label}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// ── 상세 검증 박스 ──

function DetailBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-on-surface-variant/10 px-3 py-2.5 space-y-1.5">
      <span className="text-[10px] text-on-surface-variant/40 font-medium">{title}</span>
      {children}
    </div>
  );
}

// ── 임상 데이터 평가 박스 ──

const VERDICT_STYLE: Record<string, { icon: string; label: string; color: string }> = {
  good: { icon: "✅", label: "긍정", color: "#95d3ba" },
  caution: { icon: "⚠️", label: "경계", color: "#c4a882" },
  danger: { icon: "🚨", label: "위험", color: "#ffb4ab" },
};

function AssessmentBox({ assessment: a }: { assessment: ClinicalAssessment }) {
  const v = VERDICT_STYLE[a.verdict] || VERDICT_STYLE.caution;
  return (
    <div className="sm:col-span-2 rounded-lg border border-on-surface-variant/10 px-3 py-2.5 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-on-surface-variant/40 font-medium">임상 데이터 평가</span>
        <span className="text-[10px] font-bold" style={{ color: v.color }}>{v.icon} {v.label}</span>
      </div>

      {/* 설계 요약 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        <div><span className="text-on-surface-variant/50">설계</span><p className="text-on-surface-variant mt-0.5">{a.design}</p></div>
        <div><span className="text-on-surface-variant/50">샘플</span><p className="text-on-surface-variant mt-0.5">{a.sample_size}</p></div>
        <div><span className="text-on-surface-variant/50">1차 변수</span><p className="text-on-surface-variant mt-0.5">{a.primary_endpoint}</p></div>
        <div><span className="text-on-surface-variant/50">p-value</span><p className="text-on-surface-variant mt-0.5 font-mono">{a.p_value}</p></div>
      </div>

      {/* 상세 판단 */}
      <div className="space-y-1">
        {a.details.map((d, i) => (
          <div key={i} className="flex items-start gap-1.5 text-xs">
            <span className="shrink-0 mt-0.5" style={{ color: d.signal === "good" ? "#95d3ba" : d.signal === "warn" ? "#c4a882" : "#ffb4ab" }}>
              {d.signal === "good" ? "✓" : d.signal === "warn" ? "!" : "✕"}
            </span>
            <span style={{ color: d.signal === "bad" ? "#ffb4ab" : d.signal === "warn" ? "#c4a882" : undefined }}>{d.text}</span>
          </div>
        ))}
      </div>

      {/* 결론 */}
      <p className="text-xs text-on-surface-variant/60 leading-relaxed pt-1 border-t border-on-surface-variant/10">{a.conclusion}</p>

      {/* 출처 */}
      {a.sources.length > 0 && (
        <div className="flex flex-wrap gap-2 text-[10px] text-on-surface-variant/40">
          {a.sources.map((src, i) => (
            <a key={i} href={src} target="_blank" rel="noopener noreferrer" className="hover:text-on-surface-variant underline">
              출처 {i + 1}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ── 상세 검증 행 ──

function DetailRow({ label, signal, detail }: { label: string; signal: Signal; detail: string }) {
  const icon = SIGNAL_ICON[signal] || "—";
  const color = SIGNAL_COLORS[signal] || "rgba(255,255,255,0.3)";

  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="shrink-0 w-[52px] text-on-surface-variant/60">{label}</span>
      <span className="shrink-0" style={{ color }}>{icon}</span>
      <span style={{ color: signal === "bad" ? "#ffb4ab" : signal === "star" || signal === "star2" ? "#e9c176" : undefined }}>
        {detail}
      </span>
    </div>
  );
}
