import type { PeakEval, PeakSignal, SellHoldingResult, Verdict } from "./types";

const VERDICT_STYLE: Record<
  Verdict["verdict"],
  { label: string; bg: string; fg: string; icon: string }
> = {
  HOLD: { label: "보유", bg: "#95d3ba", fg: "#0f3a2a", icon: "trending_flat" },
  BAD_ENTRY: { label: "잘못 매수", bg: "#b09bce", fg: "#1f1535", icon: "warning" },
  WATCH: { label: "관찰", bg: "#e8c875", fg: "#3a2e0a", icon: "visibility" },
  TRIM: { label: "비중 축소", bg: "#e8a25b", fg: "#3a1f0a", icon: "remove_circle" },
  SELL: { label: "매도", bg: "#ffb4ab", fg: "#3a0f0a", icon: "arrow_downward" },
};

const SEVERITY_STYLE: Record<
  PeakSignal["severity"],
  { label: string; color: string }
> = {
  strong: { label: "강", color: "#ffb4ab" },
  medium: { label: "중", color: "#e8a25b" },
  weak: { label: "약", color: "#e8c875" },
};

const CATEGORY_ICON: Record<string, string> = {
  "최후의 정점": "mode_heat",
  "약세 징후": "trending_down",
  "지지선 붕괴": "bar_chart",
  thesis: "policy",
};

function formatKrw(n: number): string {
  return n.toLocaleString("ko-KR");
}

function MetricBox({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-surface-container/50 rounded-lg p-2.5">
      <p className="text-on-surface-variant/60 text-[10px] mb-0.5">{label}</p>
      <p className="text-on-surface font-medium" style={color ? { color } : undefined}>
        {value}
      </p>
      {sub && <p className="text-on-surface-variant/60 text-[10px] mt-0.5">{sub}</p>}
    </div>
  );
}

function SignalRow({ signal }: { signal: PeakSignal }) {
  const s = SEVERITY_STYLE[signal.severity];
  const icon = CATEGORY_ICON[signal.book_category] ?? "circle";
  return (
    <div
      className="rounded-lg p-2.5 border flex items-start gap-2"
      style={{
        backgroundColor: `${s.color}10`,
        borderColor: `${s.color}30`,
      }}
    >
      <span
        className="material-symbols-outlined text-base mt-0.5"
        style={{ color: s.color }}
      >
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-1.5 flex-wrap">
          <span className="text-xs font-medium text-on-surface">{signal.label}</span>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded-full"
            style={{
              backgroundColor: `${s.color}30`,
              color: s.color,
            }}
          >
            {s.label}
          </span>
          <span className="text-[10px] text-on-surface-variant/60">
            {signal.book_category}
          </span>
        </div>
        <p className="text-[11px] text-on-surface-variant/80 mt-0.5 leading-relaxed">
          {signal.detail}
        </p>
      </div>
    </div>
  );
}

export function PeakCard({ h }: { h: SellHoldingResult }) {
  const p = h.peak;
  const v = VERDICT_STYLE[h.peak_verdict.verdict];

  const drawdownColor =
    p.drawdown_from_high_pct == null
      ? undefined
      : p.drawdown_from_high_pct <= -8
        ? "#ffb4ab"
        : p.drawdown_from_high_pct <= -5
          ? "#e8c875"
          : "#95d3ba";

  const ma200FarColor =
    p.price_vs_ma200_pct == null
      ? undefined
      : p.price_vs_ma200_pct >= 70
        ? "#ffb4ab"
        : p.price_vs_ma200_pct >= 40
          ? "#e8c875"
          : "#95d3ba";

  const ma50Color =
    p.price_vs_ma50_pct == null
      ? undefined
      : p.price_vs_ma50_pct < 0
        ? "#ffb4ab"
        : "#95d3ba";

  const ma200SlopeColor =
    p.ma200_slope_pct == null
      ? undefined
      : p.ma200_slope_pct < -1
        ? "#ffb4ab"
        : p.ma200_slope_pct < 1
          ? "#e8c875"
          : "#95d3ba";

  return (
    <article className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
      {/* 헤더 */}
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-serif font-bold text-on-surface">
            {h.name}
            <span className="text-xs font-sans font-normal text-on-surface-variant/60 ml-2">
              {h.code}
            </span>
          </h3>
          {h.sector && (
            <p className="text-xs text-on-surface-variant/60 mt-0.5">{h.sector}</p>
          )}
        </div>
        <span
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold"
          style={{ backgroundColor: v.bg, color: v.fg }}
        >
          <span className="material-symbols-outlined text-sm">{v.icon}</span>
          {v.label}
        </span>
      </header>

      {/* 현재가 + 신호 hit count */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-on-surface-variant/60 text-xs mb-0.5">현재가</p>
          <p className="text-on-surface font-medium">{formatKrw(h.current_price)}원</p>
        </div>
        <div>
          <p className="text-on-surface-variant/60 text-xs mb-0.5">신호 hit</p>
          <p className="text-on-surface font-medium">
            {p.hit_count}건
            <span className="text-on-surface-variant/60 text-[11px] ml-1">
              (강 {p.signals.filter((s) => s.severity === "strong").length} / 중{" "}
              {p.signals.filter((s) => s.severity === "medium").length} / 약{" "}
              {p.signals.filter((s) => s.severity === "weak").length})
            </span>
          </p>
        </div>
      </div>

      {/* 신고가·이평선·거래량 지표 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        <MetricBox
          label="신고가 대비"
          value={
            p.drawdown_from_high_pct != null
              ? `${p.drawdown_from_high_pct.toFixed(2)}%`
              : "-"
          }
          sub={
            p.current_high_price
              ? `${formatKrw(p.current_high_price)}원${p.current_high_date ? ` (${p.current_high_date})` : ""}`
              : undefined
          }
          color={drawdownColor}
        />
        <MetricBox
          label="200일선 괴리"
          value={
            p.price_vs_ma200_pct != null
              ? `${p.price_vs_ma200_pct >= 0 ? "+" : ""}${p.price_vs_ma200_pct.toFixed(2)}%`
              : "-"
          }
          sub={
            p.ma200_approx
              ? `200일선 ${formatKrw(p.ma200_approx)}원 (40주 평균 근사)`
              : "데이터 부족"
          }
          color={ma200FarColor}
        />
        <MetricBox
          label="50일선 위치"
          value={
            p.price_vs_ma50_pct != null
              ? `${p.price_vs_ma50_pct >= 0 ? "+" : ""}${p.price_vs_ma50_pct.toFixed(2)}%`
              : "-"
          }
          sub={p.ma50 ? `50일선 ${formatKrw(p.ma50)}원` : undefined}
          color={ma50Color}
        />
        <MetricBox
          label="200일선 기울기"
          value={
            p.ma200_slope_pct != null
              ? `${p.ma200_slope_pct >= 0 ? "+" : ""}${p.ma200_slope_pct.toFixed(2)}%`
              : "-"
          }
          sub="40주 평균 변화"
          color={ma200SlopeColor}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        <MetricBox
          label="최근 거래량"
          value={
            p.recent_volume_ratio != null
              ? `60일 평균 × ${p.recent_volume_ratio.toFixed(2)}배`
              : "-"
          }
          sub={
            p.recent_volume_avg && p.volume_avg_60d
              ? `최근 5일 평균 ${p.recent_volume_avg.toLocaleString()}주`
              : undefined
          }
        />
        <MetricBox
          label="신고가일 거래량"
          value={
            p.high_day_volume_ratio != null
              ? `60일 평균 × ${p.high_day_volume_ratio.toFixed(2)}배`
              : "-"
          }
          sub="< 80%면 '거래량 적은 신고가'"
        />
        <MetricBox
          label="매물 출회일 (최근 5일)"
          value={`${p.distribution_days_in_5d}일`}
          sub="가격 ↓ + 거래량 ↑"
        />
        <MetricBox
          label="연속 하락일"
          value={`${p.consecutive_down_days}일`}
        />
      </div>

      {/* 신호 리스트 */}
      <div className="space-y-2">
        <p className="text-xs text-on-surface-variant/80 font-medium">
          감지된 매도 신호 {p.signals.length}건
        </p>
        {p.signals.length === 0 ? (
          <p className="text-xs text-on-surface-variant/60 italic px-2.5 py-2">
            정점·약세·지지선·thesis 신호 모두 미달 — 추세 유지
          </p>
        ) : (
          <div className="space-y-1.5">
            {p.signals.map((s) => (
              <SignalRow key={s.id} signal={s} />
            ))}
          </div>
        )}
      </div>

      {/* monitor 알람 상세 (있을 경우) */}
      {p.monitor_alerts_critical.length > 0 && (
        <div className="bg-surface-container/30 rounded-lg p-2.5 text-[11px] text-on-surface-variant/80">
          <p className="font-medium mb-1">research/monitor 알람</p>
          <ul className="space-y-0.5">
            {p.monitor_alerts_critical.map((title, i) => (
              <li key={i}>· {title}</li>
            ))}
          </ul>
        </div>
      )}

      {/* verdict 사유 (첫 번째만 강조) */}
      <div className="border-l-2 pl-3" style={{ borderColor: v.bg }}>
        <p className="text-xs text-on-surface-variant/80 font-medium mb-1">
          판정 사유
        </p>
        <p className="text-xs text-on-surface-variant leading-relaxed">
          {h.peak_verdict.reasons[0] ?? "신호 없음"}
        </p>
      </div>
    </article>
  );
}
