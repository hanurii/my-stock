import type { EpsAccelQuality } from "../lib/epsAccel";

export type Principle = "C" | "A" | "N" | "S" | "L" | "I" | "M";

export const PRINCIPLES: Principle[] = ["C", "A", "N", "S", "L", "I", "M"];

export const PRINCIPLE_LABELS: Record<Principle, string> = {
  C: "Current",
  A: "Annual",
  N: "New",
  S: "Supply",
  L: "Leader",
  I: "Institutional",
  M: "Market",
};

// 원칙별 원본 만점. null = 아직 점수 체계 미확정.
// L: RS 점수 1~99 백분위 그대로 사용 (모집단 외 종목도 추정치 부여, 데이터 부족은 0).
// S: 주주가치 50 (기본 25 + 자사주 소각/연속 배당 가점, 희석 감점) + 부채비율 10 (금융업 5점 고정).
export const PRINCIPLE_MAX: Record<Principle, number | null> = {
  C: 100,
  A: 50,
  N: 30,
  S: 60,
  L: 99,
  I: null,
  M: null,
};

// 현재 시점에서 산정 가능한 만점 합 (null 제외)
export const TOTAL_MAX = PRINCIPLES.reduce(
  (sum, p) => sum + (PRINCIPLE_MAX[p] ?? 0),
  0,
);

export interface RankingCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  pct_from_52w_high: number | null;
  c_eps_accel_quality?: EpsAccelQuality | null;
  c_never_sell?: boolean;
  a_track_label?: string;
  a_grade?: string;
  scores: Record<Principle, number | null>;
  total: number;
}

export interface RankingData {
  generated_at: string | null;
  candidates: RankingCandidate[];
}
