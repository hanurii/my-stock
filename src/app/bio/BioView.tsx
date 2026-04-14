"use client";

import React from "react";

// ── 타입 ──

interface PipelineQuality {
  has_patent: boolean;
  patent_domestic: number;
  patent_pct: number;
  high_if_papers: number;
  total_citations: number;
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

// ── 메인 컴포넌트 ──

export function BioView({ pipelines, briefings }: BioViewProps) {
  // 병명별 그룹핑
  const groups = new Map<string, Pipeline[]>();
  for (const pl of pipelines) {
    const cat = pl.disease_category;
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat)!.push(pl);
  }
  const sortedGroups = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);

  return (
    <div className="space-y-6">
      {/* 수동 입력 가이드 */}
      <Details summary="수동 입력 가이드 (bio-manual-overrides.json)">
        <div className="space-y-3 mt-2 text-sm text-on-surface-variant">
          <p className="text-xs text-on-surface-variant/60 mb-2">아래 항목은 자동 수집이 불가하여 수동 입력이 필요합니다. DART 전자공시시스템(dart.fss.or.kr)에서 확인 후 JSON 파일에 입력하세요.</p>
          <div>
            <p className="font-medium text-on-surface">contract_structure <span className="text-xs font-normal text-on-surface-variant">&quot;no_return&quot; | &quot;returnable&quot; | &quot;unknown&quot;</span></p>
            <p>DART → 주요사항보고서 → 기술이전 계약 공시문 → &quot;반환&quot; / &quot;해지 시 원상회복&quot; 조항 확인</p>
          </div>
          <div>
            <p className="font-medium text-on-surface">milestone_ratio <span className="text-xs font-normal text-on-surface-variant">0~100 (숫자)</span></p>
            <p>동일 공시문에서 계약금·마일스톤·로열티 금액 확인 → 마일스톤이 총 계약금에서 차지하는 비중(%)을 계산하여 입력</p>
          </div>
        </div>
      </Details>

      {/* 병명별 그룹 */}
      {sortedGroups.map(([category, pls]) => (
        <div key={category}>
          <h3 className="text-lg font-bold font-serif text-primary mb-3 flex items-center gap-2">
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

  return (
    <div className="bg-surface-container-low rounded-xl ghost-border p-4 sm:p-5">
      {/* 헤더: 기술명 크게, 기업명 작게 */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs px-2 py-0.5 rounded font-bold" style={{
            backgroundColor: pl.phase === "PHASE3" ? "#95d3ba20" : "#6ea8fe20",
            color: pl.phase === "PHASE3" ? "#95d3ba" : "#6ea8fe",
          }}>{phaseLabel[pl.phase] || pl.phase}</span>
          <span className="text-xs text-on-surface-variant/50">{pl.status.replace(/_/g, " ")}</span>
        </div>
        <h4 className="text-sm font-medium text-on-surface leading-snug mb-1">
          {briefing?.tech_kr || pl.trial_name}
        </h4>
        <p className="text-xs text-on-surface-variant">
          {pl.company.name} · {pl.company.market} · 시총 {fmtNum(pl.company.market_cap)}
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-0.5">
          적응증: {pl.indication} · NCT: {pl.nct_id}
        </p>
      </div>

      {/* AI 시장 브리핑 */}
      {briefing?.market_briefing && (
        <div className="bg-primary/5 rounded-lg p-3 mb-3 border border-primary/10">
          <p className="text-xs font-medium text-primary mb-1">시장 분석</p>
          <p className="text-sm text-on-surface leading-relaxed">{briefing.market_briefing}</p>
        </div>
      )}

      {/* 질적 검증 체크리스트 */}
      <div className="mb-3">
        <p className="text-xs font-medium text-on-surface-variant mb-2">기술 질적 검증</p>
        <div className="space-y-1.5">
          <CheckItem status={q.has_patent ? "good" : "bad"}
            good={`특허 보유 (국내 ${q.patent_domestic}건, PCT ${q.patent_pct}건)`}
            bad="특허 없음 — 기술 독점 불가" />

          <CheckItem
            status={q.high_if_papers > 0 ? "good" : "bad"}
            good={`고영향 저널(IF≥10) ${q.high_if_papers}편, 피인용 ${q.total_citations.toLocaleString()}회`}
            bad="고영향 저널 논문 없음" />

          <CheckItem
            status={q.conference_level === "oral_top4" ? "star" : q.conference_level === "poster_top4" || q.conference_level === "other_intl" ? "neutral" : "bad"}
            good={q.conference_level === "oral_top4" ? "ASCO/ASH/AACR/ESMO 구두 초청 발표" : `학회 발표 이력 (${q.conference_level})`}
            bad="주요 학회 발표 이력 없음" />

          <CheckItem status="good" good="임상 1상 안전성 통과" bad="" />

          <CheckItem
            status={q.has_results_posted ? "good" : "bad"}
            good="임상 결과 데이터 공개됨"
            bad="결과 미공개 — 자신 없는 기술 의심" />

          <BigPharmaCheck deal={q.bigpharma_deal} />

          <ContractCheck structure={q.contract_structure} milestoneRatio={q.milestone_ratio} />

          <CheckItem
            status={q.ceo_background === "scientist" ? "good" : q.ceo_background === "cto_scientist" ? "good" : "bad"}
            good={q.ceo_background === "scientist" ? "박사/연구원 출신 CEO" : "기술자 CTO 보유"}
            bad={q.ceo_background === "professional" ? "경영 전문가(금융/경영) — 기술자 부재" : "경영진 기술 전문성 확인 불가"} />
        </div>
      </div>

      {/* 하단 메타 */}
      <div className="flex flex-wrap gap-3 text-xs text-on-surface-variant/60 pt-2 border-t border-on-surface-variant/10">
        {pl.competing_phase3_count > 0 && <span>3상 경쟁: {pl.competing_phase3_count}개</span>}
        {pl.est_completion && <span>예상 완료: {pl.est_completion}</span>}
        {pl.start_date && <span>시작: {pl.start_date}</span>}
      </div>
    </div>
  );
}

// ── 체크 아이템 ──

function CheckItem({ status, good, bad }: { status: "good" | "bad" | "star" | "neutral"; good: string; bad: string }) {
  if (status === "star") {
    return (
      <div className="flex items-start gap-2 text-sm">
        <span className="shrink-0 text-xs mt-0.5" style={{ color: "#e9c176" }}>★</span>
        <span className="text-on-surface font-medium" style={{ color: "#e9c176" }}>{good}</span>
      </div>
    );
  }
  if (status === "good") {
    return (
      <div className="flex items-start gap-2 text-sm">
        <span className="shrink-0 text-xs mt-0.5" style={{ color: "#95d3ba" }}>✓</span>
        <span className="text-on-surface-variant">{good}</span>
      </div>
    );
  }
  if (status === "neutral") {
    return (
      <div className="flex items-start gap-2 text-sm">
        <span className="shrink-0 text-xs mt-0.5 text-on-surface-variant/40">—</span>
        <span className="text-on-surface-variant/60">{good}</span>
      </div>
    );
  }
  // bad
  return (
    <div className="flex items-start gap-2 text-sm">
      <span className="shrink-0 text-xs mt-0.5" style={{ color: "#ffb4ab" }}>✕</span>
      <span style={{ color: "#ffb4ab" }}>{bad}</span>
    </div>
  );
}

function BigPharmaCheck({ deal }: { deal: { tier: string; terminated: boolean } }) {
  if (deal.terminated) {
    return <CheckItem status="bad" good="" bad="빅파마 계약 파기 이력 — 기술 신뢰도 훼손" />;
  }
  if (deal.tier === "top20") {
    return (
      <div className="flex items-start gap-2 text-sm">
        <span className="shrink-0 text-xs mt-0.5" style={{ color: "#e9c176" }}>★</span>
        <span className="text-on-surface font-medium" style={{ color: "#e9c176" }}>Top20 빅파마 계약, 파기 없음</span>
      </div>
    );
  }
  if (deal.tier === "global") {
    return <CheckItem status="good" good="글로벌 빅파마 계약, 파기 없음" bad="" />;
  }
  if (deal.tier === "domestic") {
    return <CheckItem status="neutral" good="국내 기술이전 계약" bad="" />;
  }
  return (
    <div className="flex items-start gap-2 text-sm">
      <span className="shrink-0 text-xs mt-0.5 text-on-surface-variant/40">—</span>
      <span className="text-on-surface-variant/60">빅파마 계약 없음</span>
    </div>
  );
}

function ContractCheck({ structure, milestoneRatio }: { structure: string | null; milestoneRatio: number | null }) {
  const items: React.ReactNode[] = [];

  if (structure === "no_return") {
    items.push(<CheckItem key="cs" status="good" good="반환의무 없음" bad="" />);
  } else if (structure === "returnable") {
    items.push(<CheckItem key="cs" status="bad" good="" bad="반환의무 있음 — 기술 가치 의문" />);
  } else {
    items.push(
      <div key="cs" className="flex items-start gap-2 text-sm">
        <span className="shrink-0 text-xs mt-0.5 text-on-surface-variant/40">—</span>
        <span className="text-on-surface-variant/60">계약 구조 불명</span>
      </div>
    );
  }

  if (milestoneRatio != null && milestoneRatio > 50) {
    items.push(
      <div key="ms" className="flex items-start gap-2 text-sm">
        <span className="shrink-0 text-xs mt-0.5" style={{ color: "#e9c176" }}>!</span>
        <span style={{ color: "#e9c176" }}>마일스톤 비중 {milestoneRatio}% — 확정 수령 아님</span>
      </div>
    );
  }

  return <>{items}</>;
}

// ── Details 컴포넌트 ──

function Details({ summary, children }: { summary: string; children: React.ReactNode }) {
  return (
    <details className="group">
      <summary className="cursor-pointer text-xs text-on-surface-variant/60 hover:text-on-surface-variant flex items-center gap-1">
        <span className="material-symbols-outlined text-sm group-open:rotate-90 transition-transform">chevron_right</span>
        {summary}
      </summary>
      {children}
    </details>
  );
}
