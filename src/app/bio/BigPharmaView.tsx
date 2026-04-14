"use client";

import React from "react";

// ── 타입 ──

interface BigPharmaDeal {
  id: string;
  company: { code: string; name: string; market: string; market_cap: number };
  bigpharma: { name: string; tier: string };
  deal: {
    type: string;
    title: string;
    rcept_no: string;
    disclosure_date: string;
    total_amount: string | null;
    contract_details: string | null;
    returnable: boolean | null;
    terminated: boolean;
    honest_disclosure: string;
  };
  technology: {
    name: string | null;
    indication: string | null;
    disease_category: string;
    nct_id: string | null;
    phase: string | null;
  };
  quality: {
    patent_matched_count: number;
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
    patent_search_keywords: string[];
  };
  news_summary: string | null;
}

interface BigPharmaViewProps {
  deals: BigPharmaDeal[];
}

// ── 유틸 ──

function fmtCap(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}조`;
  return `${n.toLocaleString()}억`;
}

// ── 메인 뷰 ──

export function BigPharmaView({ deals }: BigPharmaViewProps) {
  if (deals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <span className="material-symbols-outlined text-5xl text-primary-dim/30 mb-4">handshake</span>
        <p className="text-on-surface-variant text-sm">빅파마 딜 데이터가 아직 없습니다.</p>
        <p className="text-on-surface-variant/60 text-xs mt-1">스크리닝 실행 후 데이터가 채워집니다.</p>
      </div>
    );
  }

  // 빅파마별 그룹화
  const grouped = new Map<string, BigPharmaDeal[]>();
  for (const d of deals) {
    const key = d.bigpharma.name;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(d);
  }
  // 딜 수 내림차순 정렬
  const sortedGroups = [...grouped.entries()].sort((a, b) => b[1].length - a[1].length);

  return (
    <div className="space-y-8">
      {sortedGroups.map(([pharmaName, groupDeals]) => (
        <section key={pharmaName}>
          <h3 className="text-lg font-serif font-bold text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">apartment</span>
            {pharmaName}
            <span className="text-xs font-normal text-on-surface-variant">({groupDeals.length}건)</span>
          </h3>
          <div className="space-y-4">
            {groupDeals.map(deal => <DealCard key={deal.id} deal={deal} />)}
          </div>
        </section>
      ))}
    </div>
  );
}

// ── 딜 카드 ──

function DealCard({ deal }: { deal: BigPharmaDeal }) {
  const d = deal.deal;
  const t = deal.technology;
  const q = deal.quality;

  return (
    <div className="bg-surface-container-low rounded-xl ghost-border p-4 sm:p-5">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: "#e9c17630", color: "#e9c176" }}>
              {deal.bigpharma.name}
            </span>
            <h4 className="text-base font-medium text-on-surface">{deal.company.name}</h4>
            <span className="text-xs text-on-surface-variant/50">{deal.company.market}</span>
            <DealTypeBadge type={d.type} />
            {d.terminated && (
              <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#ffb4ab20", color: "#ffb4ab" }}>해지됨</span>
            )}
          </div>
          <p className="text-sm text-on-surface-variant">{deal.company.code} · 시총 {fmtCap(deal.company.market_cap)}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-on-surface-variant/50">{d.disclosure_date?.replace(/(\d{4})(\d{2})(\d{2})/, "$1.$2.$3")}</p>
        </div>
      </div>

      {/* 공시 제목 */}
      <p className="text-xs text-on-surface-variant mb-3 bg-surface-container/30 rounded-lg p-2">
        {d.title}
      </p>

      {/* 계약 요약 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <InfoCell label="계약 금액" value={d.total_amount || "미공개"} />
        <InfoCell label="기술명" value={t.name || "미확인"} />
        <InfoCell label="적응증" value={t.indication || "미확인"} />
        <InfoCell label="임상 단계" value={t.phase ? t.phase.replace("PHASE", "") + "상" : "임상 전"} />
      </div>

      {/* 계약 건전성 인디케이터 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        <HealthIndicator
          label="반환의무"
          status={d.returnable === false ? "good" : d.returnable === true ? "bad" : "unknown"}
          text={d.returnable === false ? "없음" : d.returnable === true ? "있음" : "미확인"}
        />
        <HealthIndicator
          label="해지이력"
          status={d.terminated ? "bad" : "good"}
          text={d.terminated ? "있음" : "없음"}
        />
        <HealthIndicator
          label="공시성실성"
          status={d.honest_disclosure === "honest" ? "good" : d.honest_disclosure === "hype" ? "bad" : "unknown"}
          text={d.honest_disclosure === "honest" ? "정직" : d.honest_disclosure === "hype" ? "과대포장" : "미확인"}
        />
        <HealthIndicator
          label="CEO 전문성"
          status={q.ceo_background === "scientist" || q.ceo_background === "cto_scientist" ? "good" : q.ceo_background === "professional" ? "neutral" : "unknown"}
          text={q.ceo_background === "scientist" ? "박사/연구원" : q.ceo_background === "cto_scientist" ? "CTO 기술자" : q.ceo_background === "professional" ? "경영전문" : "미확인"}
        />
      </div>

      {/* 질적 검증 요약 */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-3">
        <MiniStat label="특허" value={q.patent_matched_count > 0 ? `${q.patent_matched_count}건` : "-"} good={q.patent_matched_count > 0} />
        <MiniStat label="논문" value={q.pubmed_count > 0 ? `${q.pubmed_count}편` : "-"} good={q.pubmed_count > 0} />
        <MiniStat label="인용수" value={q.total_citations > 0 ? q.total_citations.toLocaleString() : "-"} good={q.total_citations > 0} />
        <MiniStat label="학회" value={q.conference_level === "oral_top4" ? "구두발표" : q.conference_level === "poster_top4" ? "포스터" : "-"} good={q.conference_level === "oral_top4"} />
        <MiniStat label="IF≥10" value={q.high_if_papers > 0 ? `${q.high_if_papers}편` : "-"} good={q.high_if_papers > 0} />
        <MiniStat label="결과공개" value={q.has_results_posted ? "O" : "X"} good={q.has_results_posted} />
      </div>

      {/* 계약 세부 (접이식) */}
      {d.contract_details && (
        <details className="mt-3 group">
          <summary className="cursor-pointer text-xs text-on-surface-variant/60 hover:text-on-surface-variant flex items-center gap-1">
            <span className="material-symbols-outlined text-sm group-open:rotate-90 transition-transform">chevron_right</span>
            계약 세부사항
          </summary>
          <p className="text-xs text-on-surface-variant mt-2 leading-relaxed bg-surface-container/20 rounded-lg p-3">
            {d.contract_details}
          </p>
        </details>
      )}
    </div>
  );
}

// ── 서브 컴포넌트 ──

function DealTypeBadge({ type }: { type: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    "기술이전": { bg: "#6ea8fe20", text: "#6ea8fe" },
    "공동개발": { bg: "#95d3ba20", text: "#95d3ba" },
    "투자": { bg: "#e9c17620", text: "#e9c176" },
  };
  const c = colors[type] || { bg: "rgba(255,255,255,0.05)", text: "#909097" };
  return <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: c.bg, color: c.text }}>{type}</span>;
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-container/30 rounded-lg p-2 text-center">
      <p className="text-xs text-on-surface-variant">{label}</p>
      <p className="text-sm font-mono text-on-surface mt-0.5 truncate">{value}</p>
    </div>
  );
}

function HealthIndicator({ label, status, text }: { label: string; status: "good" | "bad" | "neutral" | "unknown"; text: string }) {
  const colors = {
    good: { bg: "#95d3ba15", border: "#95d3ba40", text: "#95d3ba", icon: "check_circle" },
    bad: { bg: "#ffb4ab15", border: "#ffb4ab40", text: "#ffb4ab", icon: "cancel" },
    neutral: { bg: "rgba(255,255,255,0.03)", border: "rgba(255,255,255,0.08)", text: "#e9c176", icon: "info" },
    unknown: { bg: "rgba(255,255,255,0.03)", border: "rgba(255,255,255,0.08)", text: "#909097", icon: "help" },
  };
  const c = colors[status];

  return (
    <div className="rounded-lg p-2 text-center border" style={{ backgroundColor: c.bg, borderColor: c.border }}>
      <span className="material-symbols-outlined text-sm" style={{ color: c.text }}>{c.icon}</span>
      <p className="text-[10px] text-on-surface-variant mt-0.5">{label}</p>
      <p className="text-xs font-medium mt-0.5" style={{ color: c.text }}>{text}</p>
    </div>
  );
}

function MiniStat({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className="text-center">
      <p className="text-[10px] text-on-surface-variant">{label}</p>
      <p className={`text-xs font-mono mt-0.5 ${good ? "text-on-surface" : "text-on-surface-variant/40"}`}>{value}</p>
    </div>
  );
}
