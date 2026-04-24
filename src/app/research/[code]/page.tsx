import Link from "next/link";
import { notFound } from "next/navigation";
import fs from "fs/promises";
import path from "path";
import {
  loadResearchDetail,
  STATUS_LABEL,
  STATUS_COLOR,
  TONE_COLOR,
  TONE_ICON,
  type Tone,
} from "@/lib/research";

interface MetricResult {
  id: string;
  label: string;
  value: number | string | null;
  display: string;
  threshold: string;
  hit: boolean;
  tone: Tone;
  detail?: string;
}

interface MonitorData {
  code: string;
  name: string;
  last_checked: string;
  metrics: MetricResult[];
  alerts: Array<{
    severity: "info" | "warn" | "bad";
    type: string;
    title: string;
    message: string;
  }>;
  news_hits: Array<{
    keyword: string;
    date: string;
    title: string;
    url: string;
    severity?: "info" | "warn" | "bad";
    signals?: string[];
  }>;
  sources: Array<{ label: string; ref: string }>;
}

async function loadMonitor(code: string): Promise<MonitorData | null> {
  try {
    const raw = await fs.readFile(
      path.join(process.cwd(), "public", "data", "research", "monitor", `${code}.json`),
      "utf-8",
    );
    return JSON.parse(raw) as MonitorData;
  } catch {
    return null;
  }
}

const SEVERITY_COLOR: Record<MonitorData["alerts"][number]["severity"], string> = {
  info: TONE_COLOR.neutral,
  warn: TONE_COLOR.warn,
  bad: TONE_COLOR.bad,
};
const SEVERITY_ICON: Record<MonitorData["alerts"][number]["severity"], string> = {
  info: "check_circle",
  warn: "warning",
  bad: "cancel",
};

function MonitorMetric({ metric }: { metric: MetricResult }) {
  const color = TONE_COLOR[metric.tone];
  const emphasized = metric.tone === "bad" || metric.tone === "warn";
  return (
    <div
      className="rounded-xl p-4 backdrop-blur-sm"
      style={{
        backgroundColor: emphasized ? `${color}15` : "rgba(255,255,255,0.02)",
        border: `1px solid ${emphasized ? `${color}40` : "rgba(255,255,255,0.06)"}`,
      }}
    >
      <p className="text-[10px] uppercase tracking-[0.18em] text-on-surface-variant/60 mb-2 line-clamp-1">
        {metric.label}
      </p>
      <p className="text-2xl font-serif font-bold leading-none" style={{ color }}>
        {metric.display}
      </p>
      <p className="text-[10px] text-on-surface-variant/50 mt-2 line-clamp-1">
        임계 {metric.threshold}
      </p>
    </div>
  );
}

const METRIC_GRID_COLS: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-2 sm:grid-cols-3",
  4: "grid-cols-2 sm:grid-cols-4",
  5: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-5",
  6: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-6",
};

function MonitorPanel({ data }: { data: MonitorData }) {
  const hasBad = data.alerts.some((a) => a.severity === "bad");
  const hasWarn = data.alerts.some((a) => a.severity === "warn");
  const overallTone: "good" | "warn" | "bad" = hasBad ? "bad" : hasWarn ? "warn" : "good";
  const accent = TONE_COLOR[overallTone];

  const checkedKst = new Date(data.last_checked).toLocaleString("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <section
      className="relative rounded-2xl overflow-hidden"
      style={{
        background: `linear-gradient(155deg, ${accent}12 0%, ${accent}04 50%, transparent 100%)`,
        boxShadow: `0 0 0 1px ${accent}25, 0 8px 32px -12px ${accent}30`,
      }}
    >
      <div
        className="h-1 w-full"
        style={{ background: `linear-gradient(90deg, ${accent} 0%, ${accent}40 100%)` }}
      />
      <div className="p-5 sm:p-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-xl" style={{ color: accent }}>
              radar
            </span>
            <div>
              <p className="text-sm font-serif font-medium text-on-surface">
                매도 트리거 자동 모니터링
              </p>
              <p className="text-[10px] uppercase tracking-[0.2em] text-on-surface-variant/50">
                Daily Sell-Trigger Watch
              </p>
            </div>
          </div>
          <p className="text-[10px] text-on-surface-variant/50">
            최근 확인 {checkedKst} KST
          </p>
        </div>

        {/* Metric grid (메트릭 개수에 따라 자동 적응) */}
        {data.metrics.length > 0 && (
          <div
            className={`grid ${METRIC_GRID_COLS[Math.min(data.metrics.length, 6)] ?? "grid-cols-2"} gap-2 sm:gap-3 mb-4`}
          >
            {data.metrics.map((metric) => (
              <MonitorMetric key={metric.id} metric={metric} />
            ))}
          </div>
        )}

        {/* Alerts */}
        <div className="space-y-2">
          {data.alerts.map((a, i) => {
            const color = SEVERITY_COLOR[a.severity];
            return (
              <div
                key={i}
                className="flex items-start gap-2.5 rounded-lg p-3"
                style={{
                  backgroundColor: `${color}10`,
                  border: `1px solid ${color}25`,
                }}
              >
                <span
                  className="material-symbols-outlined text-base shrink-0 mt-0.5"
                  style={{ color }}
                >
                  {SEVERITY_ICON[a.severity]}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-on-surface">{a.title}</p>
                  <p className="text-xs text-on-surface-variant mt-0.5">{a.message}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* News hits */}
        {data.news_hits.length > 0 && (
          <div className="mt-4 pt-4" style={{ borderTop: `1px solid ${accent}20` }}>
            <p className="text-[10px] uppercase tracking-[0.2em] text-on-surface-variant/60 mb-2">
              규제·매크로 키워드 매칭 (최근 7일)
            </p>
            <ul className="space-y-1.5">
              {data.news_hits.slice(0, 6).map((h, i) => {
                const sev = h.severity ?? "info";
                const dotColor = SEVERITY_COLOR[sev];
                return (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    <span
                      className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                      style={{
                        backgroundColor: dotColor,
                        boxShadow: sev !== "info" ? `0 0 6px ${dotColor}` : undefined,
                      }}
                      title={sev}
                    />
                    <span className="text-on-surface-variant/50 shrink-0 font-mono">
                      {h.date}
                    </span>
                    <a
                      href={h.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-on-surface-variant hover:text-primary leading-relaxed line-clamp-2"
                    >
                      {h.title}
                      {h.signals && h.signals.length > 0 && (
                        <span
                          className="ml-1 text-[10px] font-medium"
                          style={{ color: dotColor }}
                        >
                          [{h.signals.slice(0, 2).join("·")}]
                        </span>
                      )}
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Footer sources */}
        <p className="text-[10px] text-on-surface-variant/40 mt-4">
          자동 업데이트: GitHub Actions (평일 17:30 KST) · 출처:{" "}
          {data.sources.map((s) => s.label).join(" · ")}
        </p>
      </div>
    </section>
  );
}

export async function generateStaticParams() {
  try {
    const dir = path.join(process.cwd(), "public", "data", "research");
    const files = await fs.readdir(dir);
    return files
      .filter((f) => f.endsWith(".json") && f !== "index.json")
      .map((f) => ({ code: f.replace(".json", "") }));
  } catch {
    return [];
  }
}

function Chip({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span
      className="text-[11px] px-2 py-0.5 rounded inline-flex items-center gap-1"
      style={{ backgroundColor: `${TONE_COLOR[tone]}20`, color: TONE_COLOR[tone] }}
    >
      {children}
    </span>
  );
}

function SectionHeader({ icon, title }: { icon: string; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <span className="material-symbols-outlined text-primary text-xl">{icon}</span>
      <h3 className="text-lg font-serif text-on-surface">{title}</h3>
    </div>
  );
}

const TONE_LIGHT_LABEL: Record<Tone, string> = {
  good: "GO",
  warn: "CAUTION",
  bad: "STOP",
  neutral: "HOLD",
};

function VerdictCard({
  icon,
  caption,
  captionEn,
  label,
  tone,
  headline,
  reasons,
}: {
  icon: string;
  caption: string;
  captionEn: string;
  label: string;
  tone: Tone;
  headline: string;
  reasons: { tone: Tone; text: string }[];
}) {
  const color = TONE_COLOR[tone];
  return (
    <div
      className="relative rounded-2xl overflow-hidden border-2"
      style={{
        borderColor: `${color}55`,
        background: `linear-gradient(155deg, ${color}18 0%, ${color}06 45%, transparent 100%)`,
        boxShadow: `0 0 0 1px ${color}15, 0 8px 32px -8px ${color}30`,
      }}
    >
      {/* Top accent stripe */}
      <div
        className="h-1.5 w-full"
        style={{
          background: `linear-gradient(90deg, ${color} 0%, ${color}50 100%)`,
        }}
      />

      <div className="p-6 sm:p-7">
        {/* Caption */}
        <div className="flex items-center gap-2.5 mb-5">
          <span
            className="flex items-center justify-center w-10 h-10 rounded-full shrink-0"
            style={{
              backgroundColor: `${color}20`,
              border: `1px solid ${color}40`,
            }}
          >
            <span className="material-symbols-outlined text-xl" style={{ color }}>
              {icon}
            </span>
          </span>
          <div>
            <p className="text-sm font-serif font-medium text-on-surface">
              {caption}
            </p>
            <p className="text-[10px] uppercase tracking-[0.2em] text-on-surface-variant/50">
              {captionEn}
            </p>
          </div>
        </div>

        {/* Traffic-light status */}
        <div className="flex items-center gap-3 mb-4">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase"
            style={{
              backgroundColor: `${color}25`,
              color,
              border: `1px solid ${color}50`,
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{
                backgroundColor: color,
                boxShadow: `0 0 8px ${color}`,
              }}
            />
            {TONE_LIGHT_LABEL[tone]}
          </span>
        </div>

        {/* Big label */}
        <p
          className="text-2xl sm:text-3xl font-serif font-bold leading-tight mb-4"
          style={{ color }}
        >
          {label}
        </p>

        {/* Headline */}
        <p className="text-sm text-on-surface/90 leading-relaxed mb-5">
          {headline}
        </p>

        {/* Reasons */}
        <div
          className="space-y-2 pt-4 border-t"
          style={{ borderColor: `${color}25` }}
        >
          {reasons.map((r, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span
                className="material-symbols-outlined text-base shrink-0"
                style={{ color: TONE_COLOR[r.tone] }}
              >
                {TONE_ICON[r.tone]}
              </span>
              <span className="text-on-surface-variant leading-relaxed">
                {r.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default async function ResearchDetailPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const [data, monitor] = await Promise.all([
    loadResearchDetail(code),
    loadMonitor(code),
  ]);
  if (!data) notFound();

  return (
    <div className="space-y-10">
      {/* Back link */}
      <Link
        href="/research"
        className="inline-flex items-center gap-1 text-sm text-on-surface-variant hover:text-primary transition-colors"
      >
        <span className="material-symbols-outlined text-sm">arrow_back</span>
        심층 분석 목록
      </Link>

      {/* Monitor panel (상단 우선 노출) */}
      {monitor && <MonitorPanel data={monitor} />}

      {/* Header */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <span
            className="text-[11px] px-2 py-0.5 rounded"
            style={{
              backgroundColor: `${STATUS_COLOR[data.status]}20`,
              color: STATUS_COLOR[data.status],
            }}
          >
            {STATUS_LABEL[data.status]}
          </span>
          <span className="text-xs text-on-surface-variant/50">
            {data.market} · {data.code}
          </span>
          <span className="text-xs text-on-surface-variant/50">
            업데이트 {data.updated_at}
          </span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          {data.name}
        </h2>
        <p className="text-sm text-on-surface-variant mt-1">{data.sector}</p>
      </section>

      {/* Triple Verdict: 매수 타이밍 · 투자 가치 · 매도 타이밍 */}
      {(data.entry_timing || data.investment_thesis || data.exit_timing) && (
        <section>
          <div className="flex items-baseline gap-3 mb-5">
            <p className="text-[10px] uppercase tracking-[0.25em] text-primary-dim/60">
              Key Verdicts
            </p>
            <span className="h-px flex-1 bg-gradient-to-r from-primary/30 to-transparent" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-5">
            {data.entry_timing && (
              <VerdictCard
                icon="login"
                caption="매수 타이밍"
                captionEn="Entry Timing"
                label={data.entry_timing.label}
                tone={data.entry_timing.tone}
                headline={data.entry_timing.headline}
                reasons={data.entry_timing.reasons}
              />
            )}
            {data.investment_thesis && (
              <VerdictCard
                icon="foundation"
                caption="투자 가치"
                captionEn="Investment Thesis"
                label={data.investment_thesis.label}
                tone={data.investment_thesis.tone}
                headline={data.investment_thesis.headline}
                reasons={data.investment_thesis.reasons}
              />
            )}
            {data.exit_timing && (
              <VerdictCard
                icon="logout"
                caption="매도 타이밍"
                captionEn="Exit Timing"
                label={data.exit_timing.label}
                tone={data.exit_timing.tone}
                headline={data.exit_timing.headline}
                reasons={data.exit_timing.reasons}
              />
            )}
          </div>
        </section>
      )}

      {/* Thesis 요약 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">gavel</span>
            <span className="text-xs uppercase tracking-[0.15em] text-on-surface-variant">
              종합 판정
            </span>
          </div>
          <Chip tone={data.verdict.tone}>
            <span className="material-symbols-outlined text-sm">
              {TONE_ICON[data.verdict.tone]}
            </span>
            {data.verdict.label}
          </Chip>
        </div>
        <p className="text-base text-on-surface leading-relaxed mb-3">{data.thesis}</p>
        {data.verdict.summary && (
          <p className="text-sm text-on-surface-variant leading-relaxed">
            {data.verdict.summary}
          </p>
        )}
      </section>

      {/* Snapshot */}
      {data.snapshot && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="analytics" title="스냅샷" />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {[
              {
                label: "현재가",
                value:
                  data.snapshot.current_price != null
                    ? `${data.snapshot.current_price.toLocaleString()}원`
                    : "-",
              },
              {
                label: "시가총액",
                value:
                  data.snapshot.market_cap_billion != null
                    ? `${data.snapshot.market_cap_billion.toLocaleString()}억`
                    : "-",
              },
              {
                label: "PER",
                value:
                  data.snapshot.per != null ? `${data.snapshot.per}배` : "-",
              },
              {
                label: "PBR",
                value:
                  data.snapshot.pbr != null ? `${data.snapshot.pbr}배` : "-",
              },
              {
                label: "배당수익률",
                value:
                  data.snapshot.dividend_yield != null
                    ? `${data.snapshot.dividend_yield}%`
                    : "-",
              },
              {
                label: "외국인 지분",
                value:
                  data.snapshot.foreign_ratio != null
                    ? `${data.snapshot.foreign_ratio}%`
                    : "-",
              },
              {
                label: "자사주 비율",
                value:
                  data.snapshot.treasury_ratio != null
                    ? `${data.snapshot.treasury_ratio}%`
                    : "-",
              },
            ].map((m) => (
              <div
                key={m.label}
                className="bg-surface-container/40 rounded-lg p-3"
              >
                <p className="text-[11px] text-on-surface-variant/70 mb-1">
                  {m.label}
                </p>
                <p className="text-base font-mono text-on-surface">{m.value}</p>
              </div>
            ))}
          </div>
          {data.snapshot.price_as_of && (
            <p className="text-[11px] text-on-surface-variant/40 mt-3">
              기준일 {data.snapshot.price_as_of}
            </p>
          )}
        </section>
      )}

      {/* Scoring refs */}
      {data.scoring_refs && data.scoring_refs.length > 0 && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="scoreboard" title="스코어링 프레임워크 대조" />
          <div className="space-y-3">
            {data.scoring_refs.map((ref) => (
              <div
                key={ref.framework}
                className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-surface-container/30 rounded-lg"
              >
                <div className="flex items-center gap-3 sm:w-64 shrink-0">
                  <span className="text-sm text-on-surface">{ref.framework}</span>
                  {ref.applicable ? (
                    <Chip tone="good">적용</Chip>
                  ) : (
                    <Chip tone="bad">부적합</Chip>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-2xl font-serif text-primary">
                    {ref.score}
                    <span className="text-xs text-on-surface-variant ml-0.5">
                      /100
                    </span>
                  </span>
                  {ref.grade && (
                    <span className="text-xs px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant">
                      {ref.grade}등급
                    </span>
                  )}
                  {ref.rank != null && (
                    <span className="text-xs text-on-surface-variant">
                      {ref.rank}위
                    </span>
                  )}
                </div>
                {ref.note && (
                  <p className="text-xs text-on-surface-variant/80 leading-relaxed sm:flex-1">
                    {ref.note}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Dilution checklist */}
      {data.dilution_checklist && data.dilution_checklist.length > 0 && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="verified_user" title="주주가치 희석 점검" />
          <div className="space-y-2">
            {data.dilution_checklist.map((check, i) => (
              <div
                key={i}
                className="flex items-start gap-3 py-3 border-b border-on-surface-variant/5 last:border-0"
              >
                <span
                  className="material-symbols-outlined shrink-0 text-lg"
                  style={{ color: TONE_COLOR[check.signal] }}
                >
                  {TONE_ICON[check.signal]}
                </span>
                <div className="flex-1">
                  <p className="text-sm text-on-surface font-medium">
                    {check.item}
                  </p>
                  <p className="text-xs text-on-surface-variant leading-relaxed mt-0.5">
                    {check.detail}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Bond overhang */}
      {data.bond_overhang && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="account_tree" title={data.bond_overhang.title} />
          {data.bond_overhang.subtitle && (
            <p className="text-xs text-on-surface-variant/70 mb-4">
              {data.bond_overhang.subtitle}
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-on-surface-variant/50 uppercase tracking-wider">
                  {data.bond_overhang.columns.map((col) => (
                    <th key={col} className="text-left px-3 pb-3 font-normal whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.bond_overhang.rows.map((row, i) => (
                  <tr
                    key={i}
                    className="border-t border-on-surface-variant/5"
                    style={{
                      backgroundColor: row.tone
                        ? `${TONE_COLOR[row.tone]}08`
                        : undefined,
                    }}
                  >
                    {row.cells.map((cell, j) => (
                      <td
                        key={j}
                        className="px-3 py-3 text-on-surface whitespace-nowrap"
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.bond_overhang.footnote && (
            <p className="text-[11px] text-on-surface-variant/60 mt-4 leading-relaxed">
              {data.bond_overhang.footnote}
            </p>
          )}
        </section>
      )}

      {/* Holding capacity */}
      {data.holding_capacity && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="straighten" title={data.holding_capacity.title} />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-4">
            {[
              {
                label: "총 발행주식",
                value: `${data.holding_capacity.total_shares.toLocaleString()}주`,
              },
              {
                label: "SNT홀딩스 보유",
                value: `${data.holding_capacity.current_snt_holdings.toLocaleString()}주 (${data.holding_capacity.snt_holdings_ratio}%)`,
              },
              ...(data.holding_capacity.foundation_shares != null
                ? [
                    {
                      label: "재단 보유",
                      value: `${data.holding_capacity.foundation_shares.toLocaleString()}주 (${data.holding_capacity.foundation_ratio}%)`,
                    },
                  ]
                : []),
              ...(data.holding_capacity.total_related_ratio != null
                ? [
                    {
                      label: "특수관계인 합산",
                      value: `${data.holding_capacity.total_related_ratio}%`,
                    },
                  ]
                : []),
              {
                label: `지배 마지노선 ${data.holding_capacity.control_floor_pct}%`,
                value: `${data.holding_capacity.control_floor_shares.toLocaleString()}주`,
              },
              {
                label: "추가 매도 여력",
                value: `${data.holding_capacity.remaining_cushion_shares.toLocaleString()}주`,
              },
              ...(data.holding_capacity.sold_past_10m_shares != null
                ? [
                    {
                      label: "최근 10개월 매도",
                      value: `${data.holding_capacity.sold_past_10m_shares.toLocaleString()}주`,
                    },
                  ]
                : []),
            ].map((m) => (
              <div
                key={m.label}
                className="bg-surface-container/40 rounded-lg p-3"
              >
                <p className="text-[11px] text-on-surface-variant/70 mb-1">
                  {m.label}
                </p>
                <p className="text-sm font-mono text-on-surface">{m.value}</p>
              </div>
            ))}
          </div>
          <p className="text-sm text-on-surface-variant leading-relaxed">
            {data.holding_capacity.interpretation}
          </p>
        </section>
      )}

      {/* Critical points */}
      {data.critical_points && data.critical_points.length > 0 && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="fact_check" title="핵심 포인트" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.critical_points.map((point, i) => (
              <div
                key={i}
                className="rounded-lg p-4 border"
                style={{
                  borderColor: `${TONE_COLOR[point.tone]}30`,
                  backgroundColor: `${TONE_COLOR[point.tone]}06`,
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="material-symbols-outlined text-lg"
                    style={{ color: TONE_COLOR[point.tone] }}
                  >
                    {TONE_ICON[point.tone]}
                  </span>
                  <p
                    className="text-sm font-medium"
                    style={{ color: TONE_COLOR[point.tone] }}
                  >
                    {point.title}
                  </p>
                </div>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                  {point.body}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Timeline */}
      {data.timeline && data.timeline.length > 0 && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="timeline" title="주요 경과" />
          <div className="space-y-2">
            {data.timeline.map((evt, i) => (
              <div key={i} className="flex items-start gap-3 text-xs">
                <span className="shrink-0 text-on-surface-variant/60 font-mono w-[120px]">
                  {evt.date}
                </span>
                <span className="text-on-surface-variant flex-1 leading-relaxed">
                  {evt.event}
                </span>
                {evt.source && (
                  <span className="shrink-0 text-on-surface-variant/30">
                    ({evt.source})
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Execution plan */}
      {data.execution_plan && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="flag" title="실행 전략" />
          <p className="text-sm text-primary mb-2">{data.execution_plan.strategy}</p>
          <p className="text-xs text-on-surface-variant/70 mb-5">
            대상 슬롯: {data.execution_plan.target_slot}
          </p>

          <div className="space-y-3 mb-4">
            {data.execution_plan.steps.map((step, i) => (
              <div key={i} className="bg-surface-container/30 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-sm font-medium text-on-surface">
                    {step.phase}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-primary/15 text-primary font-mono">
                    {step.size_pct}%
                  </span>
                </div>
                <p className="text-xs text-on-surface-variant mb-1">
                  <span className="text-on-surface-variant/60">트리거:</span>{" "}
                  {step.trigger}
                </p>
                <p className="text-xs text-on-surface-variant/80 leading-relaxed">
                  {step.reason}
                </p>
              </div>
            ))}
          </div>

          {data.execution_plan.stop_condition && (
            <div
              className="rounded-lg p-3 mb-3 border"
              style={{
                borderColor: `${TONE_COLOR.bad}30`,
                backgroundColor: `${TONE_COLOR.bad}06`,
              }}
            >
              <p
                className="text-xs font-medium mb-1"
                style={{ color: TONE_COLOR.bad }}
              >
                재평가 트리거
              </p>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                {data.execution_plan.stop_condition}
              </p>
            </div>
          )}

          {data.execution_plan.core_principle && (
            <div className="rounded-lg p-3 bg-surface-container/20 border border-primary/20">
              <p className="text-xs font-medium text-primary mb-1">핵심 원칙</p>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                {data.execution_plan.core_principle}
              </p>
            </div>
          )}
        </section>
      )}

      {/* Sources */}
      {data.sources && data.sources.length > 0 && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-6">
          <SectionHeader icon="source" title="출처" />
          <ul className="space-y-1.5">
            {data.sources.map((src, i) => (
              <li key={i} className="text-xs text-on-surface-variant flex gap-2">
                <span className="text-on-surface-variant/40">·</span>
                <span>{src.label}</span>
                <span className="text-on-surface-variant/40 font-mono">
                  {src.ref}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
