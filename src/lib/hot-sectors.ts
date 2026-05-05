export type HotClassification =
  | "real_hot"
  | "real_hot_warning"
  | "emerging"
  | "short_burst"
  | "cooling"
  | "in_progress"
  | "fake_hot"
  | "neutral";

export interface ETFOption {
  code: string;
  name: string;
  note?: string;
}

export interface ScoreBreakdown {
  trend_consistency: number;
  three_investor: number;
  sustained_volume: number;
  return_60d_pct: number;
  news_decoupling: number;
}

export interface SectorMetrics {
  // 가격 수익률 (%)
  perf_5d: number | null;
  perf_20d: number | null;
  perf_60d: number | null;
  perf_3m: number | null;
  perf_6m: number | null;

  // 3주체 60D 누적 (억원)
  foreign_60d_billion: number | null;
  organ_60d_billion: number | null;
  individual_60d_billion: number | null;
  // 단기 보조 (5D 누적)
  foreign_5d_billion: number | null;
  organ_5d_billion: number | null;
  individual_5d_billion: number | null;
  three_investor_alignment_60d: 0 | 1 | 2 | 3;

  // 거래대금 (억원)
  volume_recent_60d_billion: number | null;
  volume_prev_60d_billion: number | null;
  volume_sustain_ratio: number | null;
  volume_5d_spike_ratio: number | null;

  // 뉴스
  news_mention_change_5d: number | null;
  news_mention_today: number;

  // 점수
  real_hot_score: number;
  short_momentum_score: number;
  score_breakdown: ScoreBreakdown;
  fake_hot_signals: string[];
  classification: HotClassification;
}

export interface KoreanSector extends SectorMetrics {
  wics_name: string;
  gics_mapped: string;
  stock_count: number;
  etf_options: ETFOption[];
  top_stocks: Array<{
    code: string;
    name: string;
    perf_5d: number | null;
    perf_60d: number | null;
  }>;
}

export interface KoreanTheme extends SectorMetrics {
  theme_name: string;
  stock_codes: string[];
  news_keywords: string[];
  stock_count: number;
  etf_options: ETFOption[];
  representative_stocks: Array<{
    code: string;
    name: string;
    perf_5d: number | null;
    perf_60d: number | null;
  }>;
  in_watchlist: string[];
}

export interface GlobalSector {
  ticker: string;
  gics_name: string;
  gics_name_kr: string;
  perf_5d: number | null;
  perf_20d: number | null;
  perf_60d: number | null;
  perf_3m: number | null;
  perf_6m: number | null;
  perf_ytd: number | null;
}

export interface RotationSnapshot {
  label: "6m_ago" | "3m_ago" | "1m_ago" | "current";
  date: string;
  sectors: Array<{
    name: string;
    real_hot_score: number;
    classification: HotClassification;
  }>;
}

export interface HotSectorsData {
  meta: {
    last_updated: string;
    source: string;
    backfill_days: number;
    failed_count: number;
    last_error?: string;
  };
  korea_sectors: { sectors: KoreanSector[] };
  korea_themes: { themes: KoreanTheme[] };
  global_sectors: {
    sectors: GlobalSector[];
    spy_perf: {
      perf_5d: number | null;
      perf_20d: number | null;
      perf_60d: number | null;
      perf_3m: number | null;
      perf_6m: number | null;
      perf_ytd: number | null;
    };
  };
  rotation: {
    snapshots: RotationSnapshot[];
    transitions: Array<{
      from_name: string;
      to_name: string;
      flow_direction: "cooling" | "heating";
      score_delta: number;
    }>;
  };
}

// ── 분류 라벨 한글 ──
export function classificationLabel(c: HotClassification): string {
  return {
    real_hot: "🔥 진짜 핫",
    real_hot_warning: "⚠️ 진짜이나 일부 우려",
    emerging: "🚀 신규 부상",
    short_burst: "⚡ 단기 가속",
    cooling: "❄️ 식어가는 중",
    in_progress: "🟡 진행 중",
    fake_hot: "❌ 가짜 핫 (뉴스 스파이크)",
    neutral: "🔘 중립",
  }[c];
}

export function classificationColor(c: HotClassification): string {
  return {
    real_hot: "text-primary",
    real_hot_warning: "text-primary/80",
    emerging: "text-tertiary",
    short_burst: "text-error",
    cooling: "text-secondary",
    in_progress: "text-tertiary/80",
    fake_hot: "text-error",
    neutral: "text-on-surface-variant",
  }[c];
}

export function classificationDescription(c: HotClassification): string {
  return {
    real_hot: "60일+ 추세 + 3주체 매집 + 거래대금 지속. 안정 진입 후보.",
    real_hot_warning: "추세는 강하나 일부 경고 신호 동반.",
    emerging: "단기 모멘텀 강함. 60일 추세는 약하지만 빠른 진입 기회 (단기 리스크).",
    short_burst: "단기만 강함. 외인은 빠지는 중. 막차 위험.",
    cooling: "지난 분기/반기 강세였으나 최근 약화. 보유 중이면 갈아탈 시점 고려.",
    in_progress: "추세 형성 중. 추가 확인 필요.",
    fake_hot: "단발성 뉴스 스파이크. 매수 금지 권고.",
    neutral: "특별한 시그널 없음.",
  }[c];
}

// ── 포맷터 ──
export function formatBillion(v: number | null): string {
  if (v == null) return "—";
  const sign = v >= 0 ? "+" : "−";
  const abs = Math.abs(v);
  if (abs >= 10000) return `${sign}${(abs / 10000).toFixed(2)}조`;
  if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(1)}천억`;
  return `${sign}${Math.round(abs)}억`;
}

export function formatPct(v: number | null, digits: number = 1): string {
  if (v == null) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

export function formatRatio(v: number | null, digits: number = 2): string {
  if (v == null) return "—";
  return `${v.toFixed(digits)}×`;
}
