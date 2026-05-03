import type { MegacapFXRate } from "@/lib/megacap";

interface Props {
  rates: MegacapFXRate[];
}

function colorForScore(score: number): string {
  if (score >= 20) return "#10b981";    // 진한 초록
  if (score >= 10) return "#34d399";    // 초록
  if (score === 0) return "#94a3b8";   // 회색
  if (score >= -10) return "#fb923c";   // 주황
  return "#ef4444";                     // 빨강
}

function flagFor(currency: string): string {
  return ({
    USD: "🇺🇸",
    JPY: "🇯🇵",
    CNY: "🇨🇳",
    HKD: "🇭🇰",
    EUR: "🇪🇺",
    TWD: "🇹🇼",
    GBP: "🇬🇧",
    INR: "🇮🇳",
  } as Record<string, string>)[currency] ?? "🌐";
}

export function FXSignalBar({ rates }: Props) {
  if (rates.length === 0) {
    return (
      <div className="text-on-surface-variant text-sm py-6 text-center">
        환율 데이터가 아직 없습니다.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
      {rates.map((r) => {
        const color = colorForScore(r.fx_score);
        return (
          <div
            key={r.currency}
            className="bg-surface-container/30 rounded-lg p-3 ghost-border"
            style={{ borderLeft: `3px solid ${color}` }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-on-surface-variant">
                {flagFor(r.currency)} {r.currency}
              </span>
              <span
                className="text-xs font-bold font-mono"
                style={{ color }}
              >
                {r.fx_score >= 0 ? "+" : ""}{r.fx_score}
              </span>
            </div>
            <div className="text-sm font-mono text-on-surface mb-0.5">
              {r.current.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}
            </div>
            <div className="text-[10px] text-on-surface-variant/70">
              5년평균比 {r.pct_from_avg >= 0 ? "+" : ""}{r.pct_from_avg.toFixed(1)}%
              <span className="text-on-surface-variant/40"> · 편차 {r.z_score >= 0 ? "+" : ""}{r.z_score}σ</span>
            </div>
            <div className="text-[10px] text-on-surface-variant/70 mt-0.5">
              {r.fx_label.replace(" (외화 매수 최적)", "").replace(" (외화 매수 비추)", "")}
            </div>
          </div>
        );
      })}
    </div>
  );
}
