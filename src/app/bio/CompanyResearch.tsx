"use client";

// ── 타입 ──

interface QualityCheck {
  signal: "good" | "bad" | "warn";
  detail: string;
}

interface TimelineEvent {
  date: string;
  event: string;
  source: string;
}

interface CompanyResearchData {
  company: string;
  market: string;
  updated_at: string;
  title: string;
  summary: string;
  timeline: TimelineEvent[];
  quality_checks: Record<string, QualityCheck>;
  warnings: string[];
  conclusion: string;
}

interface CompanyResearchProps {
  research: Record<string, CompanyResearchData>;
}

// ── 시그널 스타일 ──

const SIGNAL_STYLE: Record<string, { icon: string; color: string }> = {
  good: { icon: "✓", color: "#95d3ba" },
  bad: { icon: "✕", color: "#ffb4ab" },
  warn: { icon: "!", color: "#e9c176" },
  na: { icon: "—", color: "#8e8e8e" },
};

const CHECK_LABELS: Record<string, string> = {
  patent: "특허",
  paper: "논문",
  conference: "학회 발표",
  clinical_data: "임상 데이터",
  bigpharma: "빅파마 계약",
  contract: "계약 구조",
  management: "경영진",
};

// ── 컴포넌트 ──

export function CompanyResearch({ research }: CompanyResearchProps) {
  const entries = Object.entries(research);
  if (entries.length === 0) return null;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-bold font-serif text-primary flex items-center gap-2">
        기업 심층 분석
        <span className="text-xs font-normal text-on-surface-variant">({entries.length}건)</span>
      </h3>

      {entries.map(([code, data]) => (
        <ResearchCard key={code} code={code} data={data} />
      ))}
    </div>
  );
}

function ResearchCard({ code, data }: { code: string; data: CompanyResearchData }) {
  return (
    <div className="bg-surface-container-low rounded-xl ghost-border p-4 sm:p-5">
      {/* 헤더 */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: "#e9c17620", color: "#e9c176" }}>
            심층 분석
          </span>
          <span className="text-xs text-on-surface-variant/50">{data.market} · {code}</span>
          <span className="text-xs text-on-surface-variant/50">업데이트: {data.updated_at}</span>
        </div>
        <h4 className="text-base font-bold text-on-surface mb-1">{data.company}</h4>
        <p className="text-sm text-on-surface-variant">{data.title}</p>
      </div>

      {/* 요약 */}
      <div className="bg-surface-container/30 rounded-lg p-3 mb-4">
        <p className="text-sm text-on-surface leading-relaxed">{data.summary}</p>
      </div>

      {/* 경고 */}
      {data.warnings.length > 0 && (
        <div className="rounded-lg p-3 mb-4 border" style={{ borderColor: "#ffb4ab30", backgroundColor: "#ffb4ab08" }}>
          <p className="text-xs font-bold mb-2" style={{ color: "#ffb4ab" }}>주의사항</p>
          <ul className="space-y-1">
            {data.warnings.map((w, i) => (
              <li key={i} className="text-xs flex items-start gap-1.5" style={{ color: "#ffb4ab" }}>
                <span className="shrink-0 mt-0.5">✕</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 질적 검증 */}
      <div className="mb-4">
        <p className="text-xs font-medium text-on-surface-variant mb-2">시동위키 7대 기준 검증</p>
        <div className="space-y-1.5">
          {Object.entries(data.quality_checks).map(([key, check]) => {
            const style = SIGNAL_STYLE[check.signal];
            const label = CHECK_LABELS[key] || key;
            return (
              <div key={key} className="flex items-start gap-2 text-xs">
                <span className="shrink-0 w-[64px] text-on-surface-variant/60">{label}</span>
                <span className="shrink-0" style={{ color: style.color }}>{style.icon}</span>
                <span style={{ color: check.signal === "bad" ? "#ffb4ab" : check.signal === "warn" ? "#e9c176" : undefined }}>
                  {check.detail}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 타임라인 (접이식) */}
      <details className="mb-3 group">
        <summary className="cursor-pointer text-xs text-on-surface-variant/60 hover:text-on-surface-variant flex items-center gap-1">
          <span className="material-symbols-outlined text-sm group-open:rotate-90 transition-transform">chevron_right</span>
          주요 경과 ({data.timeline.length}건)
        </summary>
        <div className="mt-3 space-y-2">
          {data.timeline.map((evt, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="shrink-0 text-on-surface-variant/50 font-mono w-[76px]">{evt.date}</span>
              <span className="text-on-surface-variant">{evt.event}</span>
              <span className="shrink-0 text-on-surface-variant/30">({evt.source})</span>
            </div>
          ))}
        </div>
      </details>

      {/* 결론 */}
      <div className="pt-3 border-t border-on-surface-variant/10">
        <p className="text-xs font-medium text-on-surface-variant mb-1">종합 판단</p>
        <p className="text-sm text-on-surface leading-relaxed">{data.conclusion}</p>
      </div>
    </div>
  );
}
