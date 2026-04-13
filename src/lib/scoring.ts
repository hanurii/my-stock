// ─────────────────────────────────────────────
// 저평가 우량주 자동 채점 엔진
// 국내 배당주: accelerated-long-term-investing.md 11.2절
// 해외 배당주: accelerated-long-term-investing.md 11.2.1절
// 국내 성장주: GARP(Growth At a Reasonable Price) 전략
// ─────────────────────────────────────────────

// ── 공통 타입 ──

export type GrowthPotential = "very_high" | "high" | "moderate" | "low";
export type ManagementQuality = "excellent" | "professional" | "poor";
export type DividendCutHistory = "none" | "restored" | "cut";
export type ProfitStatus = "sustained" | "turning" | "deficit";

export interface ScoreDetail {
  item: string;
  basis: string;
  score: number;
  max: number;
  cat: number;
}

export interface ScoredResult {
  cat1: number;
  cat2: number;
  cat3: number;
  score: number;
  grade: string;
  details: ScoreDetail[];
  shareholderBadges?: ShareholderBadges;
}

// ── 주주환원 보정 ──

export interface ShareholderReturnData {
  treasury_cancellation_years: number;  // 소각 실적이 있는 연도 수
  consecutive_dividend_years: number;   // 최근 연속 배당 연도 수
  dilutive_event_count: number;         // 희석성 이벤트 건수 (5년)
}

export interface ShareholderBadges {
  cancellation: boolean;  // 소각 배지 (녹색)
  dividend: boolean;      // 배당 배지 (황색)
  dilution: boolean;      // 희석주의 배지 (적색)
}

// ── 국내 종목 입력 ──

export interface DomesticStockInput {
  code: string;
  name: string;
  sector: string;
  highlights: string;
  estimated?: boolean;
  scored_at: string;
  catalyst?: string;
  a_grade_price?: number;
  current_price_at_scoring?: number;
  tier?: string;
  // Cat1
  per: number | null;
  pbr: number;
  profit_sustainable: boolean;
  single_listed: boolean;
  // Cat2
  dividend_yield: number;
  quarterly_dividend: boolean;
  dividend_increase_years: number | null; // null = 들쑥날쑥
  buyback_consecutive_years: number;      // 0 = 안함
  buyback_ratio: number;                  // 연간 소각 비율 %
  treasury_stock_ratio: number | null;    // null = 없음(보유 안 함)
  // Cat3
  growth_potential: GrowthPotential;
  management_quality: ManagementQuality;
  global_brand: boolean;
  // 이전 채점 비교
  previous_score?: number;
  previous_rank?: number;
  previous_details?: ScoreDetail[];
  grade_change_reason?: string;
}

// ── 해외 종목 입력 ──

export interface OverseasStockInput {
  code: string;
  name: string;
  sector: string;
  country: string;
  highlights: string;
  estimated?: boolean;
  scored_at: string;
  // Cat1
  per: number | null;
  pbr: number;
  profit_sustainable: boolean;
  // Cat2
  dividend_yield: number;
  dividend_increase_years: number | null; // null = 들쑥날쑥
  payout_ratio: number | null;           // null = 적자
  buyback_consecutive_years: number;
  buyback_ratio: number;
  dividend_cut_history: DividendCutHistory;
  // Cat3
  growth_potential: GrowthPotential;
  management_quality: ManagementQuality;
  global_brand: boolean;
  // 이전 채점 비교
  previous_score?: number;
  previous_rank?: number;
  previous_details?: ScoreDetail[];
  grade_change_reason?: string;
}

// ── 등급 산출 ──

export function getGrade(score: number): string {
  if (score > 80) return "A";
  if (score >= 70) return "B";
  if (score >= 50) return "C";
  return "D";
}

export function getGradeColor(grade: string): string {
  const colors: Record<string, string> = {
    A: "#95d3ba", B: "#6ea8fe", C: "#e9c176", D: "#ffb4ab",
  };
  return colors[grade] || "#909097";
}

export function getGradeLabel(grade: string): string {
  const labels: Record<string, string> = {
    A: "강력 매수", B: "매수 검토", C: "워치리스트", D: "투자 부적합",
  };
  return labels[grade] || "";
}

// ── 국내 채점 ──

export function scoreDomestic(input: DomesticStockInput): ScoredResult {
  const details: ScoreDetail[] = [];

  // ── Cat1: 저평가/이익창출력 (만점 35) ──

  // PER: <5: 20, <8: 15, <10: 10, ≥10: 5
  let perScore: number;
  let perBasis: string;
  if (input.per == null) {
    perScore = 0;
    perBasis = "적자 (PER 산출 불가)";
  } else if (input.per < 5) {
    perScore = 20;
    perBasis = `${input.per}배 (<5)`;
  } else if (input.per < 8) {
    perScore = 15;
    perBasis = `${input.per}배 (<8)`;
  } else if (input.per < 10) {
    perScore = 10;
    perBasis = `${input.per}배 (<10)`;
  } else {
    perScore = 5;
    perBasis = `${input.per}배 (≥10)`;
  }
  details.push({ item: "PER", basis: perBasis, score: perScore, max: 20, cat: 1 });

  // PBR: <0.3: 5, <0.6: 4, <1.0: 3, ≥1.0: 0
  let pbrScore: number;
  if (input.pbr < 0.3) pbrScore = 5;
  else if (input.pbr < 0.6) pbrScore = 4;
  else if (input.pbr < 1.0) pbrScore = 3;
  else pbrScore = 0;
  details.push({ item: "PBR", basis: `${input.pbr}배 (${pbrScore > 0 ? "<" + (pbrScore === 5 ? "0.3" : pbrScore === 4 ? "0.6" : "1.0") : "≥1.0"})`, score: pbrScore, max: 5, cat: 1 });

  // 이익 지속가능성
  const profitScore = input.profit_sustainable ? 5 : 0;
  details.push({ item: "이익 지속가능성", basis: input.profit_sustainable ? "대체로 지속가능" : "불안정한 이익창출력", score: profitScore, max: 5, cat: 1 });

  // 중복상장
  const listingScore = input.single_listed ? 5 : 0;
  details.push({ item: "중복상장 여부", basis: input.single_listed ? "단독상장" : "중복상장", score: listingScore, max: 5, cat: 1 });

  const cat1 = perScore + pbrScore + profitScore + listingScore;

  // ── Cat2: 주주환원 의지 (만점 40) ──

  // 배당수익률: >7%: 10, >5%: 7, >3%: 5, ≤3%: 2
  let divYieldScore: number;
  if (input.dividend_yield > 7) divYieldScore = 10;
  else if (input.dividend_yield > 5) divYieldScore = 7;
  else if (input.dividend_yield > 3) divYieldScore = 5;
  else divYieldScore = 2;
  details.push({ item: "배당수익률", basis: `${input.dividend_yield}% (${divYieldScore >= 7 ? ">" + (divYieldScore === 10 ? "7%" : "5%") : divYieldScore === 5 ? ">3%" : "≤3%"})`, score: divYieldScore, max: 10, cat: 2 });

  // 분기배당
  const quarterlyScore = input.quarterly_dividend ? 5 : 0;
  details.push({ item: "분기배당", basis: input.quarterly_dividend ? "실시" : "미실시", score: quarterlyScore, max: 5, cat: 2 });

  // 배당 연속 인상: 10년+: 5, 5년+: 4, 3년+: 3, 없음: 0
  let divIncreaseScore: number;
  let divIncreaseBasis: string;
  if (input.dividend_increase_years == null) {
    divIncreaseScore = 0;
    divIncreaseBasis = "배당 들쑥날쑥";
  } else if (input.dividend_increase_years >= 10) {
    divIncreaseScore = 5;
    divIncreaseBasis = `${input.dividend_increase_years}년 이상`;
  } else if (input.dividend_increase_years >= 5) {
    divIncreaseScore = 4;
    divIncreaseBasis = `${input.dividend_increase_years}년 (5년 이상)`;
  } else if (input.dividend_increase_years >= 3) {
    divIncreaseScore = 3;
    divIncreaseBasis = `${input.dividend_increase_years}년 (3년 이상)`;
  } else {
    divIncreaseScore = 0;
    divIncreaseBasis = `${input.dividend_increase_years}년 (해당없음)`;
  }
  details.push({ item: "배당 연속 인상", basis: divIncreaseBasis, score: divIncreaseScore, max: 5, cat: 2 });

  // 자사주 소각: 5년연속: 7, 3년연속: 5, 작년만: 3, 안함: 0
  let buybackScore: number;
  let buybackBasis: string;
  if (input.buyback_consecutive_years >= 5) {
    buybackScore = 7;
    buybackBasis = `${input.buyback_consecutive_years}년 연속 소각`;
  } else if (input.buyback_consecutive_years >= 3) {
    buybackScore = 5;
    buybackBasis = `${input.buyback_consecutive_years}년 연속 소각`;
  } else if (input.buyback_consecutive_years >= 1) {
    buybackScore = 3;
    buybackBasis = `${input.buyback_consecutive_years}년 소각`;
  } else {
    buybackScore = 0;
    buybackBasis = "소각 안 함";
  }
  details.push({ item: "자사주 소각", basis: buybackBasis, score: buybackScore, max: 7, cat: 2 });

  // 소각 비율: >2%: 8, >1.5%: 5, >0.5%: 3, ≤0.5%: 0
  let burnRatioScore: number;
  if (input.buyback_consecutive_years === 0) {
    burnRatioScore = 0;
  } else if (input.buyback_ratio > 2) {
    burnRatioScore = 8;
  } else if (input.buyback_ratio > 1.5) {
    burnRatioScore = 5;
  } else if (input.buyback_ratio > 0.5) {
    burnRatioScore = 3;
  } else {
    burnRatioScore = 0;
  }
  details.push({ item: "소각 비율", basis: input.buyback_consecutive_years > 0 ? `${input.buyback_ratio}%` : "해당없음", score: burnRatioScore, max: 8, cat: 2 });

  // 자사주 보유: 없음(0%): 5, <2%: 4, <5%: 2, ≥5%: 0
  let treasuryScore: number;
  let treasuryBasis: string;
  if (input.treasury_stock_ratio == null || input.treasury_stock_ratio === 0) {
    treasuryScore = 5;
    treasuryBasis = "없음";
  } else if (input.treasury_stock_ratio < 2) {
    treasuryScore = 4;
    treasuryBasis = `${input.treasury_stock_ratio}% (<2%)`;
  } else if (input.treasury_stock_ratio < 5) {
    treasuryScore = 2;
    treasuryBasis = `${input.treasury_stock_ratio}% (<5%)`;
  } else {
    treasuryScore = 0;
    treasuryBasis = `${input.treasury_stock_ratio}% (≥5%)`;
  }
  details.push({ item: "자사주 보유", basis: treasuryBasis, score: treasuryScore, max: 5, cat: 2 });

  const cat2 = divYieldScore + quarterlyScore + divIncreaseScore + buybackScore + burnRatioScore + treasuryScore;

  // ── Cat3: 미래 성장/경쟁력 (만점 25) ──

  // 미래 성장 잠재력: 매우높다: 10, 높다: 7, 보통: 5, 낮다: 3
  const growthMap: Record<GrowthPotential, { score: number; label: string }> = {
    very_high: { score: 10, label: "매우 높다" },
    high: { score: 7, label: "높다" },
    moderate: { score: 5, label: "보통" },
    low: { score: 3, label: "낮다" },
  };
  const growth = growthMap[input.growth_potential];
  details.push({ item: "미래 성장 잠재력", basis: growth.label, score: growth.score, max: 10, cat: 3 });

  // 기업 경영: 우수: 10, 전문: 5, 저조: 0
  const mgmtMap: Record<ManagementQuality, { score: number; label: string }> = {
    excellent: { score: 10, label: "우수한 경영자" },
    professional: { score: 5, label: "전문경영자" },
    poor: { score: 0, label: "저조한 실적" },
  };
  const mgmt = mgmtMap[input.management_quality];
  details.push({ item: "기업 경영", basis: mgmt.label, score: mgmt.score, max: 10, cat: 3 });

  // 세계적 브랜드
  const brandScore = input.global_brand ? 5 : 0;
  details.push({ item: "세계적 브랜드", basis: input.global_brand ? "있다" : "없다", score: brandScore, max: 5, cat: 3 });

  const cat3 = growth.score + mgmt.score + brandScore;

  const score = cat1 + cat2 + cat3;
  return { cat1, cat2, cat3, score, grade: getGrade(score), details };
}

// ── 해외 채점 ──

export function scoreOverseas(input: OverseasStockInput): ScoredResult {
  const details: ScoreDetail[] = [];

  // ── Cat1: 저평가/이익창출력 (만점 30) ──

  // PER: <8: 20, <12: 15, <18: 10, ≥18: 5
  let perScore: number;
  let perBasis: string;
  if (input.per == null) {
    perScore = 0;
    perBasis = "적자 (PER 산출 불가)";
  } else if (input.per < 8) {
    perScore = 20;
    perBasis = `${input.per}배 (<8)`;
  } else if (input.per < 12) {
    perScore = 15;
    perBasis = `${input.per}배 (<12)`;
  } else if (input.per < 18) {
    perScore = 10;
    perBasis = `${input.per}배 (<18)`;
  } else {
    perScore = 5;
    perBasis = `${input.per}배 (≥18)`;
  }
  details.push({ item: "PER", basis: perBasis, score: perScore, max: 20, cat: 1 });

  // PBR: <0.8: 5, <1.5: 4, <3.0: 3, ≥3.0: 0
  let pbrScore: number;
  if (input.pbr < 0.8) pbrScore = 5;
  else if (input.pbr < 1.5) pbrScore = 4;
  else if (input.pbr < 3.0) pbrScore = 3;
  else pbrScore = 0;
  details.push({ item: "PBR", basis: `${input.pbr}배 (${pbrScore > 0 ? "<" + (pbrScore === 5 ? "0.8" : pbrScore === 4 ? "1.5" : "3.0") : "≥3.0"})`, score: pbrScore, max: 5, cat: 1 });

  // 이익 지속가능성
  const profitScore = input.profit_sustainable ? 5 : 0;
  details.push({ item: "이익 지속가능성", basis: input.profit_sustainable ? "대체로 지속가능" : "불안정한 이익창출력", score: profitScore, max: 5, cat: 1 });

  const cat1 = perScore + pbrScore + profitScore;

  // ── Cat2: 주주환원 의지 (만점 45) ──

  // 배당수익률: >7%: 10, >5%: 7, >3%: 5, ≤3%: 2
  let divYieldScore: number;
  if (input.dividend_yield > 7) divYieldScore = 10;
  else if (input.dividend_yield > 5) divYieldScore = 7;
  else if (input.dividend_yield > 3) divYieldScore = 5;
  else divYieldScore = 2;
  details.push({ item: "배당수익률", basis: `${input.dividend_yield}%`, score: divYieldScore, max: 10, cat: 2 });

  // 배당 연속 인상: 50년+: 10, 25년+: 8, 10년+: 6, 5년+: 4, 3년+: 2, 없음: 0
  let divIncreaseScore: number;
  let divIncreaseBasis: string;
  if (input.dividend_increase_years == null) {
    divIncreaseScore = 0;
    divIncreaseBasis = "배당 들쑥날쑥";
  } else if (input.dividend_increase_years >= 50) {
    divIncreaseScore = 10;
    divIncreaseBasis = `${input.dividend_increase_years}년 (Dividend King)`;
  } else if (input.dividend_increase_years >= 25) {
    divIncreaseScore = 8;
    divIncreaseBasis = `${input.dividend_increase_years}년 (Dividend Aristocrat)`;
  } else if (input.dividend_increase_years >= 10) {
    divIncreaseScore = 6;
    divIncreaseBasis = `${input.dividend_increase_years}년 (10년 이상)`;
  } else if (input.dividend_increase_years >= 5) {
    divIncreaseScore = 4;
    divIncreaseBasis = `${input.dividend_increase_years}년 (5년 이상)`;
  } else if (input.dividend_increase_years >= 3) {
    divIncreaseScore = 2;
    divIncreaseBasis = `${input.dividend_increase_years}년 (3년 이상)`;
  } else {
    divIncreaseScore = 0;
    divIncreaseBasis = `${input.dividend_increase_years}년 (해당없음)`;
  }
  details.push({ item: "배당 연속 인상", basis: divIncreaseBasis, score: divIncreaseScore, max: 10, cat: 2 });

  // Payout Ratio: <60%: 5, <80%: 3, ≥80% 또는 적자: 0
  let payoutScore: number;
  let payoutBasis: string;
  if (input.payout_ratio == null) {
    payoutScore = 0;
    payoutBasis = "적자";
  } else if (input.payout_ratio < 60) {
    payoutScore = 5;
    payoutBasis = `${input.payout_ratio}% (<60%)`;
  } else if (input.payout_ratio < 80) {
    payoutScore = 3;
    payoutBasis = `${input.payout_ratio}% (<80%)`;
  } else {
    payoutScore = 0;
    payoutBasis = `${input.payout_ratio}% (≥80%)`;
  }
  details.push({ item: "Payout Ratio", basis: payoutBasis, score: payoutScore, max: 5, cat: 2 });

  // 자사주 소각: 5년연속: 7, 3년연속: 5, 작년만: 3, 안함: 0
  let buybackScore: number;
  let buybackBasis: string;
  if (input.buyback_consecutive_years >= 5) {
    buybackScore = 7;
    buybackBasis = `${input.buyback_consecutive_years}년+ 연속 소각`;
  } else if (input.buyback_consecutive_years >= 3) {
    buybackScore = 5;
    buybackBasis = `${input.buyback_consecutive_years}년 연속 소각`;
  } else if (input.buyback_consecutive_years >= 1) {
    buybackScore = 3;
    buybackBasis = `${input.buyback_consecutive_years}년 소각`;
  } else {
    buybackScore = 0;
    buybackBasis = "소각 안 함";
  }
  details.push({ item: "자사주 소각", basis: buybackBasis, score: buybackScore, max: 7, cat: 2 });

  // 소각 비율: >2%: 8, >1.5%: 5, >0.5%: 3, ≤0.5%: 0
  let burnRatioScore: number;
  if (input.buyback_consecutive_years === 0) {
    burnRatioScore = 0;
  } else if (input.buyback_ratio > 2) {
    burnRatioScore = 8;
  } else if (input.buyback_ratio > 1.5) {
    burnRatioScore = 5;
  } else if (input.buyback_ratio > 0.5) {
    burnRatioScore = 3;
  } else {
    burnRatioScore = 0;
  }
  details.push({ item: "소각 비율", basis: input.buyback_consecutive_years > 0 ? `${input.buyback_ratio}%` : "해당없음", score: burnRatioScore, max: 8, cat: 2 });

  // 배당 삭감 이력: 없음: 5, 복원: 2, 삭감/중단: 0
  const cutMap: Record<DividendCutHistory, { score: number; label: string }> = {
    none: { score: 5, label: "5년 내 삭감 없음" },
    restored: { score: 2, label: "삭감 후 복원" },
    cut: { score: 0, label: "삭감 또는 중단" },
  };
  const cut = cutMap[input.dividend_cut_history];
  details.push({ item: "배당 삭감 이력", basis: cut.label, score: cut.score, max: 5, cat: 2 });

  const cat2 = divYieldScore + divIncreaseScore + payoutScore + buybackScore + burnRatioScore + cut.score;

  // ── Cat3: 미래 성장/경쟁력 (만점 25) ──

  const growthMap: Record<GrowthPotential, { score: number; label: string }> = {
    very_high: { score: 10, label: "매우 높다" },
    high: { score: 7, label: "높다" },
    moderate: { score: 5, label: "보통" },
    low: { score: 3, label: "낮다" },
  };
  const growth = growthMap[input.growth_potential];
  details.push({ item: "미래 성장 잠재력", basis: growth.label, score: growth.score, max: 10, cat: 3 });

  const mgmtMap: Record<ManagementQuality, { score: number; label: string }> = {
    excellent: { score: 10, label: "우수한 경영 실적" },
    professional: { score: 5, label: "보통" },
    poor: { score: 0, label: "저조한 경영 실적" },
  };
  const mgmt = mgmtMap[input.management_quality];
  details.push({ item: "기업 경영", basis: mgmt.label, score: mgmt.score, max: 10, cat: 3 });

  const brandScore = input.global_brand ? 5 : 0;
  details.push({ item: "세계적 브랜드", basis: input.global_brand ? "있다" : "없다", score: brandScore, max: 5, cat: 3 });

  const cat3 = growth.score + mgmt.score + brandScore;

  const score = cat1 + cat2 + cat3;
  return { cat1, cat2, cat3, score, grade: getGrade(score), details };
}

// ── 프레임워크 정의 ──

export const DOMESTIC_FRAMEWORK = {
  category1: { name: "저평가/이익창출력", max_score: 35, key_metrics: ["PER", "PBR", "이익지속성", "중복상장"] },
  category2: { name: "주주환원 의지", max_score: 40, key_metrics: ["배당수익률", "분기배당", "배당연속인상", "자사주소각", "소각비율", "자사주보유"] },
  category3: { name: "미래성장/경쟁력", max_score: 25, key_metrics: ["성장잠재력", "경영품질", "브랜드"] },
};

export const OVERSEAS_FRAMEWORK = {
  category1: { name: "저평가/이익창출력", max_score: 30, key_metrics: ["PER", "PBR", "이익지속성"] },
  category2: { name: "주주환원 의지", max_score: 45, key_metrics: ["배당수익률", "배당연속인상", "Payout Ratio", "자사주소각", "소각비율", "배당삭감이력"] },
  category3: { name: "미래성장/경쟁력", max_score: 25, key_metrics: ["성장잠재력", "경영품질", "브랜드"] },
};

export const GROWTH_FRAMEWORK = {
  category1: { name: "성장성", max_score: 35, key_metrics: ["매출성장률", "영업이익성장률", "분기YoY", "성장가속도", "R&D·투자비율"] },
  category2: { name: "합리적 밸류에이션", max_score: 30, key_metrics: ["PEG", "PSR", "PER", "흑자지속성"] },
  category3: { name: "경쟁력/저평가시그널", max_score: 35, key_metrics: ["부채비율", "영업이익률", "이익률개선", "글로벌확장성", "종합경쟁력", "시가총액", "외국인비중"] },
};

export const GRADES = {
  A: { min: 80, label: "강력 매수", color: "#95d3ba" },
  B: { min: 70, label: "매수 검토", color: "#6ea8fe" },
  C: { min: 50, label: "워치리스트", color: "#e9c176" },
  D: { min: 0, label: "투자 부적합", color: "#ffb4ab" },
};

// ── 성장주 입력 ──

export interface GrowthStockInput {
  code: string;
  name: string;
  sector: string;
  highlights: string;
  estimated?: boolean;
  scored_at: string;
  catalyst?: string;
  a_grade_price?: number;
  current_price_at_scoring?: number;
  tier?: string;
  // Cat1: 성장성
  revenue_growth_3y: number;         // 매출 성장률 3년 CAGR (%)
  op_profit_growth_3y: number;       // 영업이익 성장률 3년 CAGR (%)
  recent_qtr_op_growth: number;      // 최근 분기 YoY 영업이익 성장률 (%)
  rnd_investment_ratio: number;      // R&D·설비투자/매출 비율 (%)
  // Cat2: 합리적 밸류에이션
  peg: number | null;                // PEG ratio (null = 산출 불가)
  psr: number;                       // PSR (시총/매출)
  per: number | null;                // PER (null = 적자)
  profit_status: ProfitStatus;       // 흑자 지속성
  // Cat3: 경쟁력/재무건전성
  debt_ratio: number;                // 부채비율 (%)
  op_margin: number;                 // 영업이익률 (%)
  prev_year_op_margin: number | null; // 전년 영업이익률 (%, null = 데이터 없음)
  global_revenue_ratio: number;      // 해외매출 비중 (%)
  competitive_edge: number;          // 종합 경쟁력 (0~8, 주관 — 보수적 채점)
  market_cap: number | null;         // 시가총액 (억원, null = 미확인)
  foreign_ownership: number | null;  // 외국인 보유비중 (%, null = 미확인)
  // 이전 채점 비교
  previous_score?: number;
  previous_rank?: number;
  previous_details?: ScoreDetail[];
  grade_change_reason?: string;
}

// ── 금리 환경 감점 ──

export function getInterestRatePenalty(baseRate: number): { penalty: number; label: string } {
  if (baseRate <= 1.5) return { penalty: 0, label: "초저금리 — 성장주 최적 환경" };
  if (baseRate <= 2.0) return { penalty: 3, label: "저금리" };
  if (baseRate <= 2.5) return { penalty: 5, label: "보통" };
  if (baseRate <= 3.0) return { penalty: 10, label: "고금리 — 성장주 주의" };
  if (baseRate <= 3.5) return { penalty: 13, label: "고금리 — 성장주 위험" };
  return { penalty: 15, label: "초고금리 — 성장주 극도로 불리" };
}

// ── 성장주 채점 ──

export function scoreGrowth(input: GrowthStockInput, baseRate: number, shReturn?: ShareholderReturnData): ScoredResult {
  const details: ScoreDetail[] = [];

  // ── Cat1: 성장성 (만점 35) ──

  // 매출 성장률 3년 CAGR: >20%: 8, >12%: 6, >5%: 3, ≤5%: 1
  let revGrowthScore: number;
  if (input.revenue_growth_3y > 20) revGrowthScore = 8;
  else if (input.revenue_growth_3y > 12) revGrowthScore = 6;
  else if (input.revenue_growth_3y > 5) revGrowthScore = 3;
  else revGrowthScore = 1;
  details.push({ item: "매출 성장률 (3Y CAGR)", basis: `${input.revenue_growth_3y}%`, score: revGrowthScore, max: 8, cat: 1 });

  // 영업이익 성장률 3년 CAGR: >25%: 8, >15%: 6, >5%: 3, ≤5%: 1
  let opGrowthScore: number;
  if (input.op_profit_growth_3y > 25) opGrowthScore = 8;
  else if (input.op_profit_growth_3y > 15) opGrowthScore = 6;
  else if (input.op_profit_growth_3y > 5) opGrowthScore = 3;
  else opGrowthScore = 1;
  details.push({ item: "영업이익 성장률 (3Y CAGR)", basis: `${input.op_profit_growth_3y}%`, score: opGrowthScore, max: 8, cat: 1 });

  // 최근 분기 YoY 영업이익 성장률: >30%: 7, >15%: 5, >0%: 3, ≤0%: 0
  let qtrGrowthScore: number;
  if (input.recent_qtr_op_growth > 30) qtrGrowthScore = 7;
  else if (input.recent_qtr_op_growth > 15) qtrGrowthScore = 5;
  else if (input.recent_qtr_op_growth > 0) qtrGrowthScore = 3;
  else qtrGrowthScore = 0;
  details.push({ item: "최근 분기 YoY 영업이익", basis: `${input.recent_qtr_op_growth}%`, score: qtrGrowthScore, max: 7, cat: 1 });

  // 성장 가속도: 최근 분기 성장 > 3년 평균 → 지금 순풍이 불고 있다
  let accelScore: number;
  let accelBasis: string;
  if (input.recent_qtr_op_growth > 0 && input.op_profit_growth_3y > 0
      && input.recent_qtr_op_growth > input.op_profit_growth_3y * 2) {
    accelScore = 5;
    accelBasis = `분기 ${input.recent_qtr_op_growth}% > 3Y ${input.op_profit_growth_3y}%×2 (강한 가속)`;
  } else if (input.recent_qtr_op_growth > 0
      && input.recent_qtr_op_growth > input.op_profit_growth_3y) {
    accelScore = 3;
    accelBasis = `분기 ${input.recent_qtr_op_growth}% > 3Y ${input.op_profit_growth_3y}% (가속 중)`;
  } else {
    accelScore = 0;
    accelBasis = `분기 ${input.recent_qtr_op_growth}% ≤ 3Y ${input.op_profit_growth_3y}% (둔화·정체)`;
  }
  details.push({ item: "성장 가속도", basis: accelBasis, score: accelScore, max: 5, cat: 1 });

  // R&D·설비투자/매출 비율: >10%: 7, >5%: 5, >2%: 3, ≤2%: 1
  let rndScore: number;
  if (input.rnd_investment_ratio > 10) rndScore = 7;
  else if (input.rnd_investment_ratio > 5) rndScore = 5;
  else if (input.rnd_investment_ratio > 2) rndScore = 3;
  else rndScore = 1;
  details.push({ item: "R&D·설비투자/매출", basis: `${input.rnd_investment_ratio}%`, score: rndScore, max: 7, cat: 1 });

  const cat1 = revGrowthScore + opGrowthScore + qtrGrowthScore + accelScore + rndScore;

  // ── Cat2: 합리적 밸류에이션 (만점 30) ──

  // PEG: <0.5: 10, <1.0: 8, <1.5: 5, <2.0: 2, ≥2.0: 0, 적자(null): -5 감점
  let pegScore: number;
  let pegBasis: string;
  if (input.peg == null) {
    pegScore = input.profit_status === "deficit" ? -5 : 0;
    pegBasis = input.profit_status === "deficit" ? "산출 불가 (적자 — 감점)" : "산출 불가 (이익성장률 음수 또는 데이터 부족)";
  } else if (input.peg < 0.5) {
    pegScore = 10;
    pegBasis = `${input.peg} (<0.5)`;
  } else if (input.peg < 1.0) {
    pegScore = 8;
    pegBasis = `${input.peg} (<1.0)`;
  } else if (input.peg < 1.5) {
    pegScore = 5;
    pegBasis = `${input.peg} (<1.5)`;
  } else if (input.peg < 2.0) {
    pegScore = 2;
    pegBasis = `${input.peg} (<2.0)`;
  } else {
    pegScore = 0;
    pegBasis = `${input.peg} (≥2.0)`;
  }
  details.push({ item: "PEG", basis: pegBasis, score: pegScore, max: 10, cat: 2 });

  // PSR: <0.5: 10, <1: 8, <3: 6, <5: 3, <10: 1, ≥10: 0
  // PSR이 낮다 = 매출은 나오는데 시장이 아직 주목 안 함 → "저평가 발굴" 핵심 지표
  let psrScore: number;
  if (input.psr < 0.5) psrScore = 10;
  else if (input.psr < 1) psrScore = 8;
  else if (input.psr < 3) psrScore = 6;
  else if (input.psr < 5) psrScore = 3;
  else if (input.psr < 10) psrScore = 1;
  else psrScore = 0;
  details.push({ item: "PSR", basis: `${input.psr}배`, score: psrScore, max: 10, cat: 2 });

  // PER: <15: 5, <25: 3, <40: 1, ≥40: 0, 적자(null/음수): -5 감점
  let perScore: number;
  let perBasis: string;
  if (input.per == null || input.per < 0) {
    perScore = -5;
    perBasis = "적자 (PER 마이너스 — 감점)";
  } else if (input.per < 15) {
    perScore = 5;
    perBasis = `${input.per}배 (<15)`;
  } else if (input.per < 25) {
    perScore = 3;
    perBasis = `${input.per}배 (<25)`;
  } else if (input.per < 40) {
    perScore = 1;
    perBasis = `${input.per}배 (<40)`;
  } else {
    perScore = 0;
    perBasis = `${input.per}배 (≥40)`;
  }
  details.push({ item: "PER", basis: perBasis, score: perScore, max: 5, cat: 2 });

  // 흑자 지속성: 흑자 지속: 5, 흑자 전환 임박: 3, 적자 지속: -5 감점
  const profitStatusMap: Record<ProfitStatus, { score: number; label: string }> = {
    sustained: { score: 5, label: "흑자 지속" },
    turning: { score: 3, label: "흑자 전환 임박" },
    deficit: { score: -5, label: "적자 지속 (감점)" },
  };
  const profitResult = profitStatusMap[input.profit_status];
  details.push({ item: "흑자 지속성", basis: profitResult.label, score: profitResult.score, max: 5, cat: 2 });

  const cat2 = pegScore + psrScore + perScore + profitResult.score;

  // ── Cat3: 경쟁력/재무건전성 (만점 35) ──

  // 부채비율: <50%: 6, <100%: 4, <200%: 2, ≥200%: 0
  let debtScore: number;
  if (input.debt_ratio < 50) debtScore = 6;
  else if (input.debt_ratio < 100) debtScore = 4;
  else if (input.debt_ratio < 200) debtScore = 2;
  else debtScore = 0;
  details.push({ item: "부채비율", basis: `${input.debt_ratio}%`, score: debtScore, max: 6, cat: 3 });

  // 영업이익률: >15%: 5, >8%: 4, >3%: 2, ≤3%: 0
  let marginScore: number;
  if (input.op_margin > 15) marginScore = 5;
  else if (input.op_margin > 8) marginScore = 4;
  else if (input.op_margin > 3) marginScore = 2;
  else marginScore = 0;
  details.push({ item: "영업이익률", basis: `${input.op_margin}%`, score: marginScore, max: 5, cat: 3 });

  // 영업이익률 개선 추세: 전년 대비 개선폭
  let marginTrendScore: number;
  let marginTrendBasis: string;
  if (input.prev_year_op_margin == null) {
    marginTrendScore = 0;
    marginTrendBasis = "전년 데이터 없음";
  } else {
    const improvement = input.op_margin - input.prev_year_op_margin;
    if (improvement > 5) {
      marginTrendScore = 5;
      marginTrendBasis = `${input.prev_year_op_margin}% → ${input.op_margin}% (+${improvement.toFixed(1)}%p, 대폭 개선)`;
    } else if (improvement > 2) {
      marginTrendScore = 3;
      marginTrendBasis = `${input.prev_year_op_margin}% → ${input.op_margin}% (+${improvement.toFixed(1)}%p, 개선)`;
    } else if (improvement > 0) {
      marginTrendScore = 1;
      marginTrendBasis = `${input.prev_year_op_margin}% → ${input.op_margin}% (+${improvement.toFixed(1)}%p, 소폭 개선)`;
    } else {
      marginTrendScore = 0;
      marginTrendBasis = `${input.prev_year_op_margin}% → ${input.op_margin}% (${improvement.toFixed(1)}%p, 악화)`;
    }
  }
  details.push({ item: "영업이익률 개선", basis: marginTrendBasis, score: marginTrendScore, max: 5, cat: 3 });

  // 글로벌 확장성: 해외매출 >30%: 3, >10%: 2, ≤10%: 0
  let globalScore: number;
  if (input.global_revenue_ratio > 30) globalScore = 3;
  else if (input.global_revenue_ratio > 10) globalScore = 2;
  else globalScore = 0;
  details.push({ item: "글로벌 확장성", basis: `해외매출 ${input.global_revenue_ratio}%`, score: globalScore, max: 3, cat: 3 });

  // 종합 경쟁력 (주관, 보수적 채점): 0~8
  const edgeScore = Math.min(8, Math.max(0, input.competitive_edge));
  let edgeBasis: string;
  if (edgeScore >= 7) edgeBasis = "뚜렷한 경쟁 우위";
  else if (edgeScore >= 4) edgeBasis = "보통 수준의 경쟁력";
  else edgeBasis = "경쟁 우위 불명확";
  details.push({ item: "종합 경쟁력", basis: edgeBasis, score: edgeScore, max: 8, cat: 3 });

  // 시가총액 (발견 가능성): 소형주일수록 아직 시장이 모를 확률 높음
  let capScore: number;
  let capBasis: string;
  if (input.market_cap == null) {
    capScore = 0;
    capBasis = "미확인";
  } else if (input.market_cap < 3000) {
    capScore = 4;
    capBasis = `${input.market_cap.toLocaleString()}억 (소형주 — 발굴 기회)`;
  } else if (input.market_cap < 7000) {
    capScore = 3;
    capBasis = `${input.market_cap.toLocaleString()}억 (중소형주)`;
  } else if (input.market_cap < 20000) {
    capScore = 2;
    capBasis = `${input.market_cap.toLocaleString()}억 (중형주)`;
  } else if (input.market_cap < 100000) {
    capScore = 1;
    capBasis = `${input.market_cap.toLocaleString()}억 (대형주)`;
  } else {
    capScore = 0;
    capBasis = `${input.market_cap.toLocaleString()}억 (초대형주)`;
  }
  details.push({ item: "시가총액", basis: capBasis, score: capScore, max: 4, cat: 3 });

  // 외국인 보유비중 (시장 관심도): 낮을수록 아직 시장이 주목 안 한 종목
  let foreignScore: number;
  let foreignBasis: string;
  if (input.foreign_ownership == null) {
    foreignScore = 0;
    foreignBasis = "미확인";
  } else if (input.foreign_ownership < 5) {
    foreignScore = 4;
    foreignBasis = `${input.foreign_ownership}% (시장 미주목)`;
  } else if (input.foreign_ownership < 10) {
    foreignScore = 3;
    foreignBasis = `${input.foreign_ownership}% (관심 초기)`;
  } else if (input.foreign_ownership < 20) {
    foreignScore = 2;
    foreignBasis = `${input.foreign_ownership}% (보통)`;
  } else if (input.foreign_ownership < 30) {
    foreignScore = 1;
    foreignBasis = `${input.foreign_ownership}% (관심 높음)`;
  } else {
    foreignScore = 0;
    foreignBasis = `${input.foreign_ownership}% (이미 널리 알려짐)`;
  }
  details.push({ item: "외국인 보유비중", basis: foreignBasis, score: foreignScore, max: 4, cat: 3 });

  const cat3 = debtScore + marginScore + marginTrendScore + globalScore + edgeScore + capScore + foreignScore;

  // ── 금리 환경 감점 ──

  const rateResult = getInterestRatePenalty(baseRate);
  if (rateResult.penalty > 0) {
    details.push({ item: "금리 환경 감점", basis: `기준금리 ${baseRate}% — ${rateResult.label}`, score: -rateResult.penalty, max: 0, cat: 0 });
  }

  // ── Cat4: 주주환원 보정 ──

  let shReturnAdj = 0;
  let shareholderBadges: ShareholderBadges | undefined;

  if (shReturn) {
    // 자사주 소각 가점
    let cancelScore: number;
    let cancelBasis: string;
    if (shReturn.treasury_cancellation_years >= 3) {
      cancelScore = 3;
      cancelBasis = `${shReturn.treasury_cancellation_years}년 소각 실적`;
    } else if (shReturn.treasury_cancellation_years === 2) {
      cancelScore = 2;
      cancelBasis = "2년 소각 실적";
    } else if (shReturn.treasury_cancellation_years === 1) {
      cancelScore = 1;
      cancelBasis = "1년 소각 실적";
    } else {
      cancelScore = 0;
      cancelBasis = "소각 실적 없음";
    }
    details.push({ item: "자사주 소각", basis: cancelBasis, score: cancelScore, max: 3, cat: 4 });

    // 배당 연속성 가점
    let divScore: number;
    let divBasis: string;
    if (shReturn.consecutive_dividend_years >= 4) {
      divScore = 2;
      divBasis = `${shReturn.consecutive_dividend_years}년 연속 배당`;
    } else if (shReturn.consecutive_dividend_years >= 2) {
      divScore = 1;
      divBasis = `${shReturn.consecutive_dividend_years}년 연속 배당`;
    } else {
      divScore = 0;
      divBasis = shReturn.consecutive_dividend_years === 1 ? "1년 배당 (불규칙)" : "배당 없음";
    }
    details.push({ item: "배당 연속성", basis: divBasis, score: divScore, max: 2, cat: 4 });

    // 지분 희석 감점: 1건당 -5점
    const dc = shReturn.dilutive_event_count;
    const dilutionScore = dc * -5;
    const dilutionBasis = dc > 0 ? `희석 이벤트 ${dc}건 × -5점` : "희석 이력 없음";
    details.push({ item: "지분 희석", basis: dilutionBasis, score: dilutionScore, max: 0, cat: 4 });

    shReturnAdj = cancelScore + divScore + dilutionScore;

    shareholderBadges = {
      cancellation: shReturn.treasury_cancellation_years >= 2,
      dividend: shReturn.consecutive_dividend_years >= 3,
      dilution: dc >= 3,
    };
  }

  const score = Math.max(0, cat1 + cat2 + cat3 + shReturnAdj - rateResult.penalty);

  // 지분 희석 등급 상한 (Grade Cap)
  let grade = getGrade(score);
  let gradeCap: string | undefined;
  if (shReturn) {
    const dc = shReturn.dilutive_event_count;
    if (dc >= 10) {
      gradeCap = "D";
    } else if (dc >= 5) {
      gradeCap = "C";
    } else if (dc >= 3) {
      gradeCap = "B";
    }
    if (gradeCap) {
      const gradeOrder = ["A", "B", "C", "D"];
      const currentIdx = gradeOrder.indexOf(grade);
      const capIdx = gradeOrder.indexOf(gradeCap);
      if (currentIdx < capIdx) {
        grade = gradeCap;
        details.push({ item: "희석 등급 상한", basis: `희석 ${dc}건 → 최대 ${gradeCap}등급`, score: 0, max: 0, cat: 4 });
      }
    }
  }

  // 역성장 등급 상한
  if (input.op_profit_growth_3y < 0) {
    const growthCap = "D";
    const gradeOrder = ["A", "B", "C", "D"];
    const currentIdx = gradeOrder.indexOf(grade);
    const capIdx = gradeOrder.indexOf(growthCap);
    if (currentIdx < capIdx) {
      grade = growthCap;
      details.push({ item: "역성장 등급 상한", basis: `영업이익 3Y CAGR ${input.op_profit_growth_3y}% → ${growthCap}등급 고정`, score: 0, max: 0, cat: 1 });
    }
  }

  return { cat1, cat2, cat3, score, grade, details, shareholderBadges };
}

// ── 성장주 스크리닝 (자동 매매용) ──

export interface GrowthScreenInput {
  code: string;
  name: string;
  market: string;              // KOSPI | KOSDAQ
  // 시세
  per: number | null;
  pbr: number;
  market_cap: number;          // 억원
  foreign_ownership: number;
  dividend_yield: number;
  current_price: number;
  // 연간 실적
  revenue_latest: number;      // 최근 연도 매출
  revenue_prev: number;        // 전년 매출
  op_profit_latest: number;    // 최근 연도 영업이익
  op_profit_prev: number;      // 전년 영업이익
  op_margin: number;           // 영업이익률 (%)
  op_margin_prev: number | null; // 전년 영업이익률 (%)
  profit_years: number;        // 연속 흑자 연수
  // 컨센서스
  eps_current: number | null;  // 최근 확정 EPS
  eps_consensus: number | null; // 컨센서스 EPS (미래)
}

export function scoreGrowthScreen(input: GrowthScreenInput, baseRate: number, shReturn?: ShareholderReturnData): ScoredResult {
  const details: ScoreDetail[] = [];

  // ── Cat1: 성장 모멘텀 (만점 45) ──

  // 컨센서스 EPS 성장률 (15점)
  let consensusScore: number;
  let consensusBasis: string;
  if (input.eps_current && input.eps_current > 0 && input.eps_consensus && input.eps_consensus > 0) {
    const epsGrowth = ((input.eps_consensus - input.eps_current) / input.eps_current) * 100;
    if (epsGrowth > 30) consensusScore = 15;
    else if (epsGrowth > 15) consensusScore = 10;
    else if (epsGrowth > 5) consensusScore = 6;
    else consensusScore = 0;
    consensusBasis = `EPS ${input.eps_current.toLocaleString()}→${input.eps_consensus.toLocaleString()} (${epsGrowth > 0 ? "+" : ""}${epsGrowth.toFixed(1)}%)`;
  } else {
    consensusScore = 0;
    consensusBasis = "컨센서스 없음";
  }
  details.push({ item: "컨센서스 EPS 성장률", basis: consensusBasis, score: consensusScore, max: 15, cat: 1 });

  // 영업이익 성장률 YoY (12점)
  let opGrowthScore: number;
  let opGrowthPct = 0;
  if (input.op_profit_prev > 0 && input.op_profit_latest > 0) {
    opGrowthPct = ((input.op_profit_latest - input.op_profit_prev) / input.op_profit_prev) * 100;
  } else if (input.op_profit_prev <= 0 && input.op_profit_latest > 0) {
    opGrowthPct = 100; // 적자 → 흑자 전환
  } else {
    opGrowthPct = -100;
  }
  if (opGrowthPct > 50) opGrowthScore = 12;
  else if (opGrowthPct > 30) opGrowthScore = 9;
  else if (opGrowthPct > 15) opGrowthScore = 6;
  else if (opGrowthPct > 0) opGrowthScore = 3;
  else opGrowthScore = 0;
  details.push({ item: "영업이익 성장률 YoY", basis: `${opGrowthPct > 0 ? "+" : ""}${opGrowthPct.toFixed(1)}%`, score: opGrowthScore, max: 12, cat: 1 });

  // 매출 성장률 YoY (8점)
  let revGrowthScore: number;
  let revGrowthPct = 0;
  if (input.revenue_prev > 0) {
    revGrowthPct = ((input.revenue_latest - input.revenue_prev) / input.revenue_prev) * 100;
  }
  if (revGrowthPct > 30) revGrowthScore = 8;
  else if (revGrowthPct > 15) revGrowthScore = 6;
  else if (revGrowthPct > 5) revGrowthScore = 3;
  else revGrowthScore = 1;
  details.push({ item: "매출 성장률 YoY", basis: `${revGrowthPct > 0 ? "+" : ""}${revGrowthPct.toFixed(1)}%`, score: revGrowthScore, max: 8, cat: 1 });

  // 영업이익률 개선 (10점)
  let marginImpScore: number;
  let marginImpBasis: string;
  if (input.op_margin_prev != null) {
    const diff = input.op_margin - input.op_margin_prev;
    if (diff > 5) marginImpScore = 10;
    else if (diff > 2) marginImpScore = 7;
    else if (diff > 0) marginImpScore = 3;
    else marginImpScore = 0;
    marginImpBasis = `${input.op_margin_prev.toFixed(1)}%→${input.op_margin.toFixed(1)}% (${diff > 0 ? "+" : ""}${diff.toFixed(1)}%p)`;
  } else {
    marginImpScore = 0;
    marginImpBasis = "전년 데이터 없음";
  }
  details.push({ item: "영업이익률 개선", basis: marginImpBasis, score: marginImpScore, max: 10, cat: 1 });

  const cat1 = consensusScore + opGrowthScore + revGrowthScore + marginImpScore;

  // ── Cat2: 성장 대비 밸류에이션 (만점 35) ──

  // Forward PER (15점)
  let fwdPerScore: number;
  let fwdPerBasis: string;
  if (input.eps_consensus && input.eps_consensus > 0 && input.current_price > 0) {
    const fwdPer = input.current_price / input.eps_consensus;
    if (fwdPer < 8) fwdPerScore = 15;
    else if (fwdPer < 12) fwdPerScore = 11;
    else if (fwdPer < 20) fwdPerScore = 7;
    else if (fwdPer < 30) fwdPerScore = 3;
    else fwdPerScore = 0;
    fwdPerBasis = `${fwdPer.toFixed(1)}배`;
  } else {
    fwdPerScore = 0;
    fwdPerBasis = "산출 불가 (컨센서스 없음)";
  }
  details.push({ item: "Forward PER", basis: fwdPerBasis, score: fwdPerScore, max: 15, cat: 2 });

  // PER (10점)
  let perScore: number;
  if (input.per == null || input.per <= 0) perScore = 0;
  else if (input.per < 10) perScore = 10;
  else if (input.per < 15) perScore = 8;
  else if (input.per < 25) perScore = 5;
  else if (input.per < 40) perScore = 2;
  else perScore = 0;
  details.push({ item: "PER", basis: input.per != null ? `${input.per.toFixed(1)}배` : "적자", score: perScore, max: 10, cat: 2 });

  // PEG (10점) — PER ÷ EPS 성장률 (Forward PER과 동일한 EPS 기준)
  let pegScore: number;
  let pegBasis: string;
  const epsGrowthPct = input.eps_current && input.eps_current > 0 && input.eps_consensus && input.eps_consensus > 0
    ? ((input.eps_consensus - input.eps_current) / input.eps_current) * 100
    : null;
  if (input.per && input.per > 0 && epsGrowthPct && epsGrowthPct > 0) {
    const peg = input.per / epsGrowthPct;
    if (peg < 0.5) pegScore = 10;
    else if (peg < 1.0) pegScore = 7;
    else if (peg < 1.5) pegScore = 4;
    else if (peg < 2.0) pegScore = 1;
    else pegScore = 0;
    pegBasis = `${peg.toFixed(2)} (PER ${input.per.toFixed(1)} ÷ EPS성장률 ${epsGrowthPct.toFixed(0)}%)`;
  } else {
    pegScore = 0;
    pegBasis = epsGrowthPct != null && epsGrowthPct <= 0 ? "EPS 역성장" : "산출 불가 (컨센서스 없음)";
  }
  details.push({ item: "PEG", basis: pegBasis, score: pegScore, max: 10, cat: 2 });

  const cat2 = fwdPerScore + perScore + pegScore;

  // ── Cat3: 안전장치 (만점 20) ──

  // 흑자 지속 연수 (10점)
  let profitScore: number;
  if (input.profit_years >= 3) profitScore = 10;
  else if (input.profit_years === 2) profitScore = 7;
  else if (input.profit_years === 1) profitScore = 3;
  else profitScore = 0;
  details.push({ item: "흑자 지속", basis: `${input.profit_years}년 연속`, score: profitScore, max: 10, cat: 3 });

  // 영업이익률 수준 (10점)
  let marginScore: number;
  if (input.op_margin > 15) marginScore = 10;
  else if (input.op_margin > 8) marginScore = 7;
  else if (input.op_margin > 3) marginScore = 4;
  else marginScore = 0;
  details.push({ item: "영업이익률", basis: `${input.op_margin.toFixed(1)}%`, score: marginScore, max: 10, cat: 3 });

  const cat3 = profitScore + marginScore;

  // ── Cat4: 주주환원 보정 ──

  let shReturnAdj = 0;
  let shareholderBadges: ShareholderBadges | undefined;

  if (shReturn) {
    // 자사주 소각 가점
    let cancelScore: number;
    let cancelBasis: string;
    if (shReturn.treasury_cancellation_years >= 3) {
      cancelScore = 3;
      cancelBasis = `${shReturn.treasury_cancellation_years}년 소각 실적`;
    } else if (shReturn.treasury_cancellation_years === 2) {
      cancelScore = 2;
      cancelBasis = "2년 소각 실적";
    } else if (shReturn.treasury_cancellation_years === 1) {
      cancelScore = 1;
      cancelBasis = "1년 소각 실적";
    } else {
      cancelScore = 0;
      cancelBasis = "소각 실적 없음";
    }
    details.push({ item: "자사주 소각", basis: cancelBasis, score: cancelScore, max: 3, cat: 4 });

    // 배당 연속성 가점
    let divScore: number;
    let divBasis: string;
    if (shReturn.consecutive_dividend_years >= 4) {
      divScore = 2;
      divBasis = `${shReturn.consecutive_dividend_years}년 연속 배당`;
    } else if (shReturn.consecutive_dividend_years >= 2) {
      divScore = 1;
      divBasis = `${shReturn.consecutive_dividend_years}년 연속 배당`;
    } else {
      divScore = 0;
      divBasis = shReturn.consecutive_dividend_years === 1 ? "1년 배당 (불규칙)" : "배당 없음";
    }
    details.push({ item: "배당 연속성", basis: divBasis, score: divScore, max: 2, cat: 4 });

    // 지분 희석 감점: 1건당 -5점
    const dc = shReturn.dilutive_event_count;
    const dilutionScore = dc * -5;
    const dilutionBasis = dc > 0 ? `희석 이벤트 ${dc}건 × -5점` : "희석 이력 없음";
    details.push({ item: "지분 희석", basis: dilutionBasis, score: dilutionScore, max: 0, cat: 4 });

    shReturnAdj = cancelScore + divScore + dilutionScore;

    shareholderBadges = {
      cancellation: shReturn.treasury_cancellation_years >= 2,
      dividend: shReturn.consecutive_dividend_years >= 3,
      dilution: dc >= 3,
    };
  }

  // ── 금리 감점 ──
  const rateResult = getInterestRatePenalty(baseRate);
  if (rateResult.penalty > 0) {
    details.push({ item: "금리 환경 감점", basis: `기준금리 ${baseRate}% — ${rateResult.label}`, score: -rateResult.penalty, max: 0, cat: 0 });
  }

  const score = Math.max(0, cat1 + cat2 + cat3 + shReturnAdj - rateResult.penalty);

  // 지분 희석 등급 상한 (Grade Cap)
  let grade = getGrade(score);
  let gradeCap: string | undefined;
  if (shReturn) {
    const dc = shReturn.dilutive_event_count;
    if (dc >= 10) {
      gradeCap = "D";
    } else if (dc >= 5) {
      gradeCap = "C";
    } else if (dc >= 3) {
      gradeCap = "B";
    }
    if (gradeCap) {
      const gradeOrder = ["A", "B", "C", "D"];
      const currentIdx = gradeOrder.indexOf(grade);
      const capIdx = gradeOrder.indexOf(gradeCap);
      if (currentIdx < capIdx) {
        grade = gradeCap;
        details.push({ item: "희석 등급 상한", basis: `희석 ${dc}건 → 최대 ${gradeCap}등급`, score: 0, max: 0, cat: 4 });
      }
    }
  }

  // 역성장 등급 상한
  if (opGrowthPct < 0) {
    const gradeOrder = ["A", "B", "C", "D"];
    const currentIdx = gradeOrder.indexOf(grade);
    const capIdx = gradeOrder.indexOf("D");
    if (currentIdx < capIdx) {
      grade = "D";
      details.push({ item: "역성장 등급 상한", basis: `영업이익 YoY ${opGrowthPct.toFixed(1)}% → D등급 고정`, score: 0, max: 0, cat: 1 });
    }
  }

  return { cat1, cat2, cat3, score, grade, details, shareholderBadges };
}

// ─────────────────────────────────────────────
// 바이오주 채점 엔진
// 7대 기준: 특허/논문/학회/임상/빅파마계약/계약구조/경영진
// ─────────────────────────────────────────────

export type ConferenceLevel = "oral_top4" | "poster_top4" | "other_intl" | "none";
export type HighestPhase = "approved" | "phase3" | "phase2" | "phase1" | "preclinical" | "none";
export type LicenseOutTier = "top20" | "global" | "domestic" | "none";
export type TerminationHistory = "none" | "re_contracted" | "terminated";
export type ContractStructure = "no_return" | "unknown" | "returnable";
export type CeoBackground = "scientist" | "cto_scientist" | "professional" | "unknown";
export type ExitSignal = "none" | "minor" | "major";
export type DisclosureHonesty = "honest" | "hype" | "unknown";
export type FundQuality = "longterm_bio" | "mixed" | "shortterm_speculative" | "unknown";

export interface BioStockInput {
  code: string;
  name: string;
  market: string;
  // Cat1: 기술 검증 (25점)
  patent_domestic: number;  // 참고용 — 채점 미반영
  patent_pct: number;       // 참고용 — 채점 미반영
  pubmed_count: number;
  high_if_papers: number;
  total_citations: number;
  conference_level: ConferenceLevel | null;
  // Cat2: 임상/사업 (52점)
  highest_phase: HighestPhase;
  pipeline_count: number;
  results_transparency: number;
  license_out_tier: LicenseOutTier;
  termination_history: TerminationHistory;
  contract_structure: ContractStructure | null;
  milestone_ratio: number | null;         // 마일스톤 비중 0-100% (수동)
  disclosure_honesty: DisclosureHonesty | null;  // 공시 성실성 (수동)
  // Cat3: 경영/재무 (23점)
  ceo_background: CeoBackground;
  dilution_3yr_pct: number;
  exit_signal: ExitSignal;
  cash_runway_years: number | null;
  fund_quality: FundQuality | null;       // 투자 자금 질 (반자동)
  // 임상 과대포장 감지
  withdrawn_terminated_count: number;     // 중단/철회 임상 수 (자동)
  successful_completion_count: number;    // 완료+결과공개 임상 수 (자동)
  clinical_hype: boolean | null;          // 임상 과대포장 플래그 (수동)
  // 메타
  market_cap: number;
  current_price: number;
}

export function scoreBio(input: BioStockInput): ScoredResult {
  const details: ScoreDetail[] = [];
  let cat1 = 0, cat2 = 0, cat3 = 0;

  // ── Cat1: 기술 검증 (25점) ──
  // 특허 건수는 채점에서 제외 — 양이 아닌 질(빅파마 인정)로 간접 평가

  // PubMed 논문 수 (5점)
  {
    const n = input.pubmed_count;
    const s = n >= 20 ? 5 : n >= 10 ? 3 : n >= 3 ? 1 : 0;
    cat1 += s;
    details.push({ item: "PubMed 논문 수", basis: `${n}편`, score: s, max: 5, cat: 1 });
  }

  // 고영향 저널 논문 IF≥10 (5점)
  {
    const n = input.high_if_papers;
    const s = n >= 3 ? 5 : n >= 1 ? 3 : 0;
    cat1 += s;
    details.push({ item: "고영향 저널 (IF≥10)", basis: `${n}편`, score: s, max: 5, cat: 1 });
  }

  // 논문 피인용 수 (5점)
  {
    const n = input.total_citations;
    const s = n >= 500 ? 5 : n >= 100 ? 3 : n >= 20 ? 1 : 0;
    cat1 += s;
    details.push({ item: "논문 피인용 수", basis: `총 ${n.toLocaleString()}회`, score: s, max: 5, cat: 1 });
  }

  // 주요 학회 발표 (10점) — 구두 초청 발표만 인정
  {
    const lvl = input.conference_level;
    const s = lvl === "oral_top4" ? 10 : 0;
    const labels: Record<string, string> = {
      oral_top4: "ASCO/ASH/AACR/ESMO 구두 발표",
      poster_top4: "포스터 발표 (미인정)",
      other_intl: "기타 학회 (미인정)",
      none: "발표 이력 없음",
    };
    cat1 += s;
    details.push({ item: "주요 학회 발표", basis: lvl ? labels[lvl] : "미확인", score: s, max: 10, cat: 1 });
  }

  // ── Cat2: 임상/사업 진행 (52점) ──

  // 최고 임상 단계 (15점)
  {
    const phaseScores: Record<HighestPhase, number> = {
      approved: 15, phase3: 12, phase2: 8, phase1: 4, preclinical: 1, none: 0,
    };
    const phaseLabels: Record<HighestPhase, string> = {
      approved: "허가/출시", phase3: "임상 3상", phase2: "임상 2상",
      phase1: "임상 1상", preclinical: "전임상", none: "없음",
    };
    const s = phaseScores[input.highest_phase];
    cat2 += s;
    details.push({ item: "최고 임상 단계", basis: phaseLabels[input.highest_phase], score: s, max: 15, cat: 2 });
  }

  // 임상 파이프라인 수 (5점)
  {
    const n = input.pipeline_count;
    const s = n >= 5 ? 5 : n >= 3 ? 3 : n >= 1 ? 1 : 0;
    cat2 += s;
    details.push({ item: "임상 파이프라인 수", basis: `${n}개`, score: s, max: 5, cat: 2 });
  }

  // 임상 결과 공개 투명성 (5점)
  {
    const r = input.results_transparency;
    const s = r >= 50 ? 5 : r >= 25 ? 3 : r > 0 ? 1 : 0;
    cat2 += s;
    details.push({ item: "임상 결과 투명성", basis: `결과 공개 ${r}%`, score: s, max: 5, cat: 2 });
  }

  // 빅파마 L/O 계약 (10점)
  {
    const tierScores: Record<LicenseOutTier, number> = { top20: 10, global: 6, domestic: 3, none: 0 };
    const tierLabels: Record<LicenseOutTier, string> = {
      top20: "Top 20 빅파마 계약", global: "기타 글로벌 계약", domestic: "국내 L/O", none: "없음",
    };
    const s = tierScores[input.license_out_tier];
    cat2 += s;
    details.push({ item: "빅파마 L/O 계약", basis: tierLabels[input.license_out_tier], score: s, max: 10, cat: 2 });
  }

  // 계약 파기 이력 (5점)
  {
    const histScores: Record<TerminationHistory, number> = { none: 5, re_contracted: 2, terminated: 0 };
    const histLabels: Record<TerminationHistory, string> = {
      none: "파기 이력 없음", re_contracted: "파기 후 재계약", terminated: "파기 이력 있음",
    };
    const s = histScores[input.termination_history];
    cat2 += s;
    details.push({ item: "계약 파기 이력", basis: histLabels[input.termination_history], score: s, max: 5, cat: 2 });
  }

  // 계약 반환의무 (4점)
  {
    const cs = input.contract_structure;
    const s = cs === "no_return" ? 4 : cs === "unknown" ? 2 : cs === "returnable" ? 0 : 2;
    const labels: Record<string, string> = {
      no_return: "반환의무 없음", unknown: "불명", returnable: "반환의무 있음",
    };
    cat2 += s;
    details.push({ item: "계약 반환의무", basis: cs ? labels[cs] : "미확인", score: s, max: 4, cat: 2 });
  }

  // 마일스톤 비율 (4점)
  {
    const r = input.milestone_ratio;
    const s = r == null ? 1 : r >= 70 ? 4 : r >= 40 ? 2 : r > 0 ? 1 : 0;
    cat2 += s;
    details.push({ item: "마일스톤 비율", basis: r != null ? `마일스톤 ${r}%` : "미확인", score: s, max: 4, cat: 2 });
  }

  // 공시 성실성 (4점)
  {
    const h = input.disclosure_honesty;
    const s = h === "honest" ? 4 : h === "unknown" ? 2 : h === "hype" ? 0 : 2;
    const labels: Record<string, string> = {
      honest: "정직한 공시", unknown: "불명", hype: "과대포장 의심",
    };
    cat2 += s;
    details.push({ item: "공시 성실성", basis: h ? labels[h] : "미확인", score: s, max: 4, cat: 2 });
  }

  // ── Cat3: 경영/재무 건전성 (23점) ──

  // CEO/CTO 기술자 출신 (6점)
  {
    const bgScores: Record<CeoBackground, number> = { scientist: 6, cto_scientist: 4, professional: 2, unknown: 1 };
    const bgLabels: Record<CeoBackground, string> = {
      scientist: "박사/연구원 출신 CEO", cto_scientist: "기술자 CTO 보유",
      professional: "경영 전문가", unknown: "확인 불가",
    };
    const s = bgScores[input.ceo_background];
    cat3 += s;
    details.push({ item: "CEO/CTO 기술 전문성", basis: bgLabels[input.ceo_background], score: s, max: 6, cat: 3 });
  }

  // 최근 3년 희석률 (5점)
  {
    const d = input.dilution_3yr_pct;
    const s = d === 0 ? 5 : d < 10 ? 4 : d < 20 ? 2 : d < 30 ? 1 : 0;
    cat3 += s;
    details.push({ item: "최근 3년 희석률", basis: `${d.toFixed(1)}%`, score: s, max: 5, cat: 3 });
  }

  // 엑싯 시그널 (4점)
  {
    const exitScores: Record<ExitSignal, number> = { none: 4, minor: 2, major: 0 };
    const exitLabels: Record<ExitSignal, string> = {
      none: "대표이사 매도 없음", minor: "소량 매도", major: "대량 매도",
    };
    const s = exitScores[input.exit_signal];
    cat3 += s;
    details.push({ item: "엑싯 시그널", basis: exitLabels[input.exit_signal], score: s, max: 4, cat: 3 });
  }

  // 현금 런웨이 (5점)
  {
    const y = input.cash_runway_years;
    const s = y == null ? 1 : y >= 3 ? 5 : y >= 2 ? 4 : y >= 1 ? 2 : 0;
    cat3 += s;
    details.push({ item: "현금 런웨이", basis: y != null ? `${y.toFixed(1)}년` : "미확인", score: s, max: 5, cat: 3 });
  }

  // 투자 자금 질 (3점)
  {
    const fq = input.fund_quality;
    const s = fq === "longterm_bio" ? 3 : fq === "mixed" ? 2 : fq === "shortterm_speculative" ? 0 : fq === "unknown" ? 1 : 1;
    const labels: Record<string, string> = {
      longterm_bio: "바이오 전문 장기투자", mixed: "혼합", shortterm_speculative: "단기 투기성", unknown: "불명",
    };
    cat3 += s;
    details.push({ item: "투자 자금 질", basis: fq ? labels[fq] : "미확인", score: s, max: 3, cat: 3 });
  }

  // ── 감점/보너스 ──
  let score = cat1 + cat2 + cat3;

  if (input.termination_history === "terminated" && input.license_out_tier === "none") {
    score -= 5;
    details.push({ item: "감점: 계약파기 + L/O 없음", basis: "기술 신뢰도 훼손", score: -5, max: 0, cat: 0 });
  }

  if (input.dilution_3yr_pct >= 30 && input.cash_runway_years != null && input.cash_runway_years < 1) {
    score -= 5;
    details.push({ item: "감점: 고희석 + 자금 부족", basis: `희석 ${input.dilution_3yr_pct.toFixed(1)}% & 런웨이 ${input.cash_runway_years.toFixed(1)}년`, score: -5, max: 0, cat: 0 });
  }

  // 임상 중단/철회 감점 — 중단 이력 있으면서 완료+결과공개 0건
  if (input.withdrawn_terminated_count > 0 && input.successful_completion_count === 0) {
    score -= 3;
    details.push({ item: "감점: 임상 중단/철회", basis: `중단 ${input.withdrawn_terminated_count}건, 완료 0건`, score: -3, max: 0, cat: 0 });
  }

  // 임상 과대포장 감점 (수동 플래그)
  if (input.clinical_hype === true) {
    score -= 3;
    details.push({ item: "감점: 임상 과대포장", basis: "수동 플래그", score: -3, max: 0, cat: 0 });
  }

  // 보너스: 3상 이상 + Top 20 빅파마 계약 (기술 이중 검증)
  if ((input.highest_phase === "phase3" || input.highest_phase === "approved") && input.license_out_tier === "top20") {
    const bonus = Math.min(5, 100 - score);
    if (bonus > 0) {
      score += bonus;
      details.push({ item: "보너스: 3상+ & Top20 빅파마", basis: "기술 이중 검증", score: bonus, max: 5, cat: 0 });
    }
  }

  score = Math.max(0, Math.min(100, score));
  const grade = getGrade(score);

  return { cat1, cat2, cat3, score, grade, details };
}
