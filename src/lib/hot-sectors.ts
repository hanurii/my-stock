export type HotClassification =
  | "real_hot"
  | "real_hot_warning"
  | "emerging"
  | "short_burst"
  | "cooling"
  | "in_progress"
  | "fake_hot"
  | "neutral";

// 가속도 페이즈 — 6M/60D/20D 월간 환산 수익률을 비교해 추세 단계 분류.
// 1~6개월 보유 전략에서 "초기 진입"에 적합한 시점을 찾는 보조 지표.
export type MomentumPhase =
  | "early_accel"      // ⭐ 가장 좋은 진입: 가속 중 + 6M < 50% (아직 안 오른 초기 단계)
  | "accelerating"     // 🚀 가속 중이지만 이미 6M ≥ 50% (후발 진입)
  | "early_recovery"   // 🌅 6M은 음수지만 60D 양수 (반등 시작)
  | "decelerating"     // 📉 60D/월 < 6M/월 (감속, 정점 근처)
  | "weakening"        // 🔻 6M·60D 모두 음수 (약세 지속)
  | "stable";          // ➖ 데이터 부족/판단 보류

// 월간 환산 수익률 (가속도 비교용 보조 데이터)
export interface MonthlyRates {
  m6: number | null;     // 6M 수익률 / 6
  m60: number | null;    // 60D 수익률 / 3
  m20: number | null;    // 20D 수익률 (≈ 1개월)
  w5: number | null;     // 5D 수익률 (≈ 1주, 참고)
}

export function classifyMomentumPhase(
  perf_5d: number | null,
  perf_20d: number | null,
  perf_60d: number | null,
  perf_6m: number | null,
): MomentumPhase {
  if (perf_6m == null || perf_60d == null) return "stable";
  const m6 = perf_6m / 6;
  const m60 = perf_60d / 3;
  const m20 = perf_20d ?? 0;

  // 약세 지속
  if (perf_6m < 0 && perf_60d < 0) return "weakening";
  // 회복 시작 (6M 음수지만 60D 양수)
  if (perf_6m < 0 && perf_60d > 0) return "early_recovery";

  // 가속 판정: 60D/월 > 6M/월 + 20D/월 > 60D/월
  const accelerating = m60 > m6 && m20 > m60;
  const decelerating = m60 < m6;

  if (accelerating && perf_6m < 50) return "early_accel";
  if (accelerating) return "accelerating";
  if (decelerating) return "decelerating";
  return "stable";
}

export function momentumPhaseLabel(p: MomentumPhase): string {
  return {
    early_accel: "⭐ 초기 가속",
    accelerating: "🚀 가속 중",
    early_recovery: "🌅 회복 시작",
    decelerating: "📉 감속/성숙",
    weakening: "🔻 약세 지속",
    stable: "➖ 유지",
  }[p];
}

export function momentumPhaseColor(p: MomentumPhase): string {
  return {
    early_accel: "text-tertiary",
    accelerating: "text-primary",
    early_recovery: "text-tertiary/80",
    decelerating: "text-on-surface-variant",
    weakening: "text-error",
    stable: "text-on-surface-variant",
  }[p];
}

export function momentumPhaseDescription(p: MomentumPhase): string {
  return {
    early_accel:
      "월간 가속도가 빨라지는 중 + 6개월 누적이 아직 50% 미만 — 1~6개월 보유 전략에 가장 적합한 진입 단계",
    accelerating:
      "월간 가속도는 빨라지나 이미 6개월 누적 50% 이상 — 후발 진입 위험 동반",
    early_recovery:
      "6개월 수익률은 음수지만 최근 60일 양수 전환 — 약세에서 반등 초기",
    decelerating:
      "최근 60일 월평균이 6개월 평균보다 낮음 — 모멘텀 감속, 정점 근처 가능성",
    weakening: "6개월·60일 모두 음수 — 추세적 약세 지속",
    stable: "뚜렷한 가속/감속 신호 없음",
  }[p];
}

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
  news_mention_5d_total: number;
  news_mention_7d_series: number[];   // 최근 7일 카운트 (오늘부터 역순: [today, -1d, -2d, ...])

  // 점수
  real_hot_score: number;
  short_momentum_score: number;
  score_breakdown: ScoreBreakdown;
  fake_hot_signals: string[];
  classification: HotClassification;

  // 가속도 페이즈 (1~6개월 보유 전략용 진입 단계 판정)
  momentum_phase: MomentumPhase;
  monthly_rates: MonthlyRates;
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
