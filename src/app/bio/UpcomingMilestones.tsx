import React from "react";

export interface Milestone {
  company_code: string;
  company_name: string;
  pipeline: string;
  nct_id?: string;
  date_start: string;
  date_label: string;
  event: string;
  location?: string;
  session?: string;
  content: string;
  importance?: "high" | "medium" | "low";
  source?: { label: string; url: string };
}

export function UpcomingMilestones({ milestones }: { milestones: Milestone[] }) {
  if (!milestones || milestones.length === 0) return null;

  const sorted = [...milestones].sort((a, b) =>
    a.date_start.localeCompare(b.date_start),
  );

  return (
    <section
      className="mb-8 rounded-2xl overflow-hidden"
      style={{
        background:
          "linear-gradient(155deg, rgba(233,193,118,0.08) 0%, rgba(233,193,118,0.03) 50%, transparent 100%)",
        boxShadow:
          "0 0 0 1px rgba(233,193,118,0.18), 0 8px 24px -16px rgba(233,193,118,0.25)",
      }}
    >
      <div
        className="h-1 w-full"
        style={{
          background: "linear-gradient(90deg, #e9c176 0%, rgba(233,193,118,0.25) 100%)",
        }}
      />
      <div className="p-5 sm:p-6">
        <div className="flex items-center gap-2 mb-4">
          <span
            className="material-symbols-outlined text-base"
            style={{ color: "#e9c176" }}
          >
            event_upcoming
          </span>
          <h3 className="text-sm font-serif font-medium text-on-surface">
            다가오는 마일스톤
          </h3>
          <span className="text-[10px] uppercase tracking-[0.18em] text-on-surface-variant/40">
            Upcoming Milestones
          </span>
          <span className="ml-auto text-xs text-on-surface-variant/50">
            {sorted.length}건
          </span>
        </div>
        <div className="space-y-3">
          {sorted.map((m, i) => (
            <MilestoneCard key={`${m.company_code}-${m.date_start}-${i}`} milestone={m} />
          ))}
        </div>
      </div>
    </section>
  );
}

function MilestoneCard({ milestone: m }: { milestone: Milestone }) {
  const accent =
    m.importance === "high"
      ? "#e9c176"
      : m.importance === "low"
      ? "#bcc7de"
      : "#95d3ba";

  return (
    <div
      className="rounded-lg p-4"
      style={{
        backgroundColor: "rgba(255,255,255,0.02)",
        border: `1px solid ${accent}25`,
      }}
    >
      <div className="flex flex-col sm:flex-row gap-3">
        <div
          className="shrink-0 rounded-md px-3 py-2 text-center self-start"
          style={{
            backgroundColor: `${accent}15`,
            border: `1px solid ${accent}30`,
            minWidth: 120,
          }}
        >
          <p
            className="text-[11px] font-mono font-medium leading-tight"
            style={{ color: accent }}
          >
            {m.date_label}
          </p>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap mb-1">
            <span className="text-sm font-medium text-on-surface">
              {m.event}
            </span>
            {m.location && (
              <span className="text-xs text-on-surface-variant/60">
                · {m.location}
              </span>
            )}
          </div>
          <p className="text-xs text-on-surface-variant/70 mb-1.5">
            <span className="font-medium" style={{ color: accent }}>
              {m.company_name}
            </span>
            <span className="mx-1.5 text-on-surface-variant/30">·</span>
            <span>{m.pipeline}</span>
            {m.session && (
              <>
                <span className="mx-1.5 text-on-surface-variant/30">·</span>
                <span>{m.session}</span>
              </>
            )}
          </p>
          <p className="text-xs text-on-surface-variant leading-relaxed">
            {m.content}
          </p>
          {m.source && (
            <a
              href={m.source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] text-on-surface-variant/50 hover:text-primary mt-2 transition-colors"
            >
              <span className="material-symbols-outlined" style={{ fontSize: "12px" }}>
                link
              </span>
              {m.source.label}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
