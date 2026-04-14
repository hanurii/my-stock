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
}

interface Briefing {
  tech_kr: string;
  market_briefing: string;
}

interface BioViewProps {
  pipelines: Pipeline[];
  briefings: Record<string, Briefing>;
}

// ── 유틸 ──

function fmtNum(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}조`;
  return `${n.toLocaleString()}억`;
}

const phaseLabel: Record<string, string> = { PHASE3: "3상", PHASE2: "2상" };
const statusLabel: Record<string, string> = {
  RECRUITING: "모집 중",
  ACTIVE_NOT_RECRUITING: "진행 중 (모집 완료)",
  NOT_YET_RECRUITING: "모집 예정",
  ENROLLING_BY_INVITATION: "초청만 참여 가능",
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
  const isPhase2 = pl.phase === "PHASE2";
  const isPhase3 = pl.phase === "PHASE3";

  // 특허 (기술별 키워드 매칭)
  const patentSignal: Signal = q.patent_matched_count > 0 ? "good" : "bad";
  const patentDetail = q.patent_matched_count > 0
    ? `관련 특허 ${q.patent_matched_count}건`
    : "관련 특허 없음";

  // 논문 (프로세스 바에서는 존재 여부만, 상세는 세부 검증에서)
  const paperExistSignal: Signal = q.pubmed_count > 0 ? "good" : "bad";
  const paperExistDetail = q.pubmed_count > 0 ? `논문 ${q.pubmed_count}편` : "논문 없음";

  // 학회
  // 학회: 저명학회 구두=별2, 일반 구두=별1, 포스터/기타=뱃지없음, 없음=경고
  const confSignal: Signal = q.conference_level === "oral_top4" ? "star2"
    : q.conference_level === "poster_top4" || q.conference_level === "other_intl" ? "none"
    : "bad";
  const confDetail = q.conference_level === "oral_top4" ? "ASCO/ASH/AACR/ESMO 구두 발표"
    : q.conference_level === "poster_top4" ? "포스터 발표"
    : q.conference_level === "other_intl" ? "기타 학회 발표"
    : "발표 없음";

  // 1상
  const p1Signal: Signal = "none"; // 2상/3상이면 반드시 통과
  const p1Detail = "안전성 통과";

  // 2상
  let p2Signal: Signal;
  let p2Detail: string;
  if (isPhase3) {
    // 3상 진행 중 → 2상은 이미 완료된 상태
    p2Signal = q.has_results_posted ? "good" : "bad";
    p2Detail = q.has_results_posted ? "2상 완료, 결과 공개됨" : "2상 완료, 결과 미공개 — 의심";
  } else {
    // 2상 진행 중 → 현재 단계
    p2Signal = "none";
    p2Detail = "진행 중";
  }

  // 3상
  const p3Signal: Signal = "none";
  const p3Detail = isPhase3 ? "진행 중" : "";

  // 빅파마
  const pharmaSignal: Signal = q.bigpharma_deal.terminated ? "bad"
    : q.bigpharma_deal.tier === "top20" ? "star"
    : q.bigpharma_deal.tier === "global" ? "good"
    : "none";
  const pharmaDetail = q.bigpharma_deal.terminated ? "계약 파기 이력"
    : q.bigpharma_deal.tier === "top20" ? "Top20 빅파마 계약"
    : q.bigpharma_deal.tier === "global" ? "글로벌 빅파마 계약"
    : "빅파마 계약 없음";

  // 경영진 (프로세스 바 밖, 상시 체크)
  // → 세부 검증에서만 표시

  return [
    { label: "특허", reached: q.patent_matched_count > 0, current: false, signal: patentSignal, detail: patentDetail },
    { label: "논문", reached: q.pubmed_count > 0, current: false, signal: paperExistSignal, detail: paperExistDetail },
    { label: "학회발표", reached: q.conference_level != null, current: false, signal: confSignal, detail: confDetail },
    { label: "1상", reached: true, current: false, signal: p1Signal, detail: p1Detail },
    { label: "2상", reached: true, current: isPhase2, signal: p2Signal, detail: p2Detail },
    { label: "3상", reached: isPhase3, current: isPhase3, signal: p3Signal, detail: p3Detail },
    { label: "허가", reached: false, current: false, signal: "none", detail: "" },
  ];
}

// ── 대시보드 카드 ──

function DashboardCards({ groups }: { groups: [string, Pipeline[]][] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {groups.map(([category, pls]) => {
        const phase3 = pls.filter(p => p.phase === "PHASE3").length;
        const phase2 = pls.filter(p => p.phase === "PHASE2").length;

        // 주요 기업 (중복 제거, 최대 3개)
        const companies = [...new Set(pls.map(p => p.company.name))];
        const companyText = companies.length <= 3
          ? companies.join(", ")
          : `${companies.slice(0, 3).join(", ")} 외 ${companies.length - 3}`;

        // 질적 지표 집계
        const withPatent = pls.filter(p => p.quality.patent_matched_count > 0).length;
        const withJournal = pls.filter(p => p.quality.notable_journals?.length > 0).length;
        const withConf = pls.filter(p => p.quality.conference_level === "oral_top4").length;
        const withBigpharma = pls.filter(p => p.quality.bigpharma_deal.tier === "top20" || p.quality.bigpharma_deal.tier === "global").length;

        return (
          <a
            key={category}
            href={`#cat-${category}`}
            className="bg-surface-container-low rounded-xl ghost-border p-3 hover:bg-surface-container transition-colors cursor-pointer block"
          >
            <div className="flex items-baseline justify-between mb-2">
              <h4 className="text-sm font-bold text-on-surface">{category}</h4>
              <span className="text-xs text-on-surface-variant">{pls.length}건</span>
            </div>

            {/* 단계 비율 */}
            <div className="flex gap-2 mb-2 text-xs">
              {phase3 > 0 && <span style={{ color: "#95d3ba" }}>3상 {phase3}</span>}
              {phase2 > 0 && <span style={{ color: "#6ea8fe" }}>2상 {phase2}</span>}
            </div>

            {/* 기업 */}
            <p className="text-xs text-on-surface-variant/60 mb-2 truncate">{companyText}</p>

            {/* 질적 지표 */}
            <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-on-surface-variant/50">
              {withConf > 0 && <span style={{ color: "#e9c176" }}>★★ 학회 {withConf}</span>}
              {withBigpharma > 0 && <span style={{ color: "#e9c176" }}>빅파마 {withBigpharma}</span>}
              {withPatent > 0 && <span>특허 {withPatent}</span>}
              {withJournal > 0 && <span>저널 {withJournal}</span>}
            </div>
          </a>
        );
      })}
    </div>
  );
}

// ── 메인 컴포넌트 ──

export function BioView({ pipelines, briefings }: BioViewProps) {
  const groups = new Map<string, Pipeline[]>();
  for (const pl of pipelines) {
    const cat = pl.disease_category;
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat)!.push(pl);
  }
  const sortedGroups = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);

  return (
    <div className="space-y-8">
      {/* 대시보드 카드 */}
      <DashboardCards groups={sortedGroups} />

      {/* 병명별 상세 */}
      {sortedGroups.map(([category, pls]) => (
        <div key={category} id={`cat-${category}`}>
          <h3 className="text-lg font-bold font-serif text-primary mb-4 flex items-center gap-2">
            {category}
            <span className="text-xs font-normal text-on-surface-variant">({pls.length}건)</span>
          </h3>
          <div className="space-y-4">
            {pls.map((pl) => (
              <PipelineCard key={pl.nct_id} pipeline={pl} briefing={briefings[pl.nct_id]} />
            ))}
          </div>
        </div>
      ))}
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
        </p>
      </div>

      {/* 프로세스 바 */}
      <ProcessBar steps={steps} />

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
        <div className="mt-3 space-y-2">
          {/* 프로세스 단계별 상세 + 논문 관련 필드 그룹화 */}
          {steps.map((step) => (
            step.detail && <React.Fragment key={step.label}>
              <DetailRow label={step.label} signal={step.signal} detail={step.detail} />
              {step.label === "논문" && (
                <div className="ml-[60px] space-y-1.5 py-1">
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
                </div>
              )}
            </React.Fragment>
          ))}

          {/* 경영진 (프로세스 바 밖의 항목) */}
          <DetailRow label="경영진"
            signal={q.ceo_background === "scientist" ? "good" : q.ceo_background === "cto_scientist" ? "good" : "bad"}
            detail={q.ceo_background === "scientist" ? "박사/연구원 출신 CEO"
              : q.ceo_background === "cto_scientist" ? "기술자 CTO 보유"
              : q.ceo_background === "professional" ? "경영 전문가(금융/경영) — 기술자 부재"
              : "경영진 기술 전문성 확인 불가"} />

          {/* 계약 구조 */}
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

          {/* 메타 정보 */}
          <div className="flex flex-wrap gap-3 text-xs text-on-surface-variant/50 pt-2 mt-1 border-t border-on-surface-variant/10">
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
  // domestic 또는 none — 비활성화 칭호
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded text-on-surface-variant/30 border border-on-surface-variant/10">
      빅파마 계약 없음
    </span>
  );
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
