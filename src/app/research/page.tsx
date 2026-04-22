import Link from "next/link";
import {
  loadResearchIndex,
  STATUS_LABEL,
  STATUS_COLOR,
  TONE_COLOR,
  type ResearchStatus,
} from "@/lib/research";

const STATUS_ORDER: ResearchStatus[] = ["holding", "interested", "watching"];

export default async function ResearchIndexPage() {
  const entries = await loadResearchIndex();

  const grouped: Record<ResearchStatus, typeof entries> = {
    holding: [],
    interested: [],
    watching: [],
  };
  for (const entry of entries) {
    (grouped[entry.status] ?? grouped.watching).push(entry);
  }

  return (
    <div className="space-y-12">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Stock Deep Research
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          종목 심층 분석
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          보유 종목과 매수 검토 종목에 대한 주주가치·공시 기반 비판적 검증.
        </p>
      </section>

      {/* Empty state */}
      {entries.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <span className="material-symbols-outlined text-5xl text-primary-dim/30 mb-4">
            lab_research
          </span>
          <p className="text-on-surface-variant text-sm">
            아직 분석 데이터가 준비되지 않았습니다.
          </p>
        </div>
      )}

      {/* Grouped sections */}
      {STATUS_ORDER.map((status) => {
        const items = grouped[status];
        if (items.length === 0) return null;

        return (
          <section key={status}>
            <div className="flex items-center gap-3 mb-5">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: STATUS_COLOR[status] }}
              />
              <h3 className="text-lg font-serif text-on-surface">
                {STATUS_LABEL[status]}
              </h3>
              <span className="text-xs text-on-surface-variant/50">
                {items.length}건
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {items.map((entry) => (
                <Link
                  key={entry.code}
                  href={`/research/${entry.code}`}
                  className="group bg-surface-container-low rounded-xl ghost-border p-5 hover:bg-surface-container/80 transition-colors block"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <h4 className="text-lg font-medium text-on-surface group-hover:text-primary transition-colors">
                        {entry.name}
                      </h4>
                      <p className="text-xs text-on-surface-variant mt-0.5">
                        {entry.market} · {entry.code} · {entry.sector}
                      </p>
                    </div>
                    <span
                      className="text-[11px] px-2 py-0.5 rounded shrink-0"
                      style={{
                        backgroundColor: `${TONE_COLOR[entry.verdict_tone]}20`,
                        color: TONE_COLOR[entry.verdict_tone],
                      }}
                    >
                      {entry.verdict}
                    </span>
                  </div>

                  <p className="text-sm text-on-surface-variant leading-relaxed mt-3">
                    {entry.thesis}
                  </p>

                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-on-surface-variant/10">
                    <span className="text-[11px] text-on-surface-variant/50">
                      업데이트 {entry.updated_at}
                    </span>
                    <span className="text-xs text-primary/70 group-hover:text-primary flex items-center gap-1">
                      상세 보기
                      <span className="material-symbols-outlined text-sm">
                        arrow_forward
                      </span>
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
