// ─────────────────────────────────────────────
// 저평가 우량주 자동 채점 엔진
// 국내: accelerated-long-term-investing.md 11.2절
// 해외: accelerated-long-term-investing.md 11.2.1절
// ─────────────────────────────────────────────

// ── 공통 타입 ──

export type GrowthPotential = "very_high" | "high" | "moderate" | "low";
export type ManagementQuality = "excellent" | "professional" | "poor";
export type DividendCutHistory = "none" | "restored" | "cut";

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

export const GRADES = {
  A: { min: 80, label: "강력 매수", color: "#95d3ba" },
  B: { min: 70, label: "매수 검토", color: "#6ea8fe" },
  C: { min: 50, label: "워치리스트", color: "#e9c176" },
  D: { min: 0, label: "투자 부적합", color: "#ffb4ab" },
};
