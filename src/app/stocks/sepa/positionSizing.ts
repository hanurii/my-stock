// 미너비니 리스크 규칙 기반 포지션 크기·손절 계산 (순수 로직, 프레임워크 비의존).
// 핵심: 계좌 위험(%) = 포지션 비중(%) × 손절 라인(%). 균등 분할(1/N) 가정.

export const ACCOUNT_RISK_MIN = 1.25;  // 한 매매 최소 권장 위험(총자본 %)
export const ACCOUNT_RISK_MAX = 2.5;   // 한 매매 최대 권장 위험(총자본 %)
export const MAX_STOP_PCT = 10;        // 최대 손절(%)
export const MAX_POSITION_PCT = 50;    // 한 종목 최대 비중(%)
export const BEST_POSITION_PCT = 25;   // 최고 종목 권장 상한(%)
export const MAX_STOCKS = 12;          // 최대 종목 수

export interface PositionSizing {
  valid: boolean;
  positionAmount: number;     // 포지션당 분배금액(원)
  positionWeightPct: number;  // 포지션 비중(%) = 100/N
  stopLowPct: number;         // 손절 하한(%) — 위험 1.25%용
  stopHighPct: number;        // 손절 상한(%) — 위험 2.5%용(보통 10% 캡)
  lossAtLow: number;          // 손절 하한에서 1종목 손실액(원)
  lossAtHigh: number;         // 손절 상한에서 1종목 손실액(원)
  riskAtLowPct: number;       // 손절 하한에서 계좌 위험(%)
  riskAtHighPct: number;      // 손절 상한에서 계좌 위험(%)
  warnings: string[];
}

export function computePositionSizing(capital: number, numStocks: number): PositionSizing {
  const n = Math.floor(numStocks);
  if (!(capital > 0) || !(n >= 1)) {
    return {
      valid: false, positionAmount: 0, positionWeightPct: 0,
      stopLowPct: 0, stopHighPct: 0, lossAtLow: 0, lossAtHigh: 0,
      riskAtLowPct: 0, riskAtHighPct: 0, warnings: [],
    };
  }

  const positionWeightPct = 100 / n;
  const positionAmount = capital / n;
  const stopLowPct = Math.min(MAX_STOP_PCT, ACCOUNT_RISK_MIN * n);
  const stopHighPct = Math.min(MAX_STOP_PCT, ACCOUNT_RISK_MAX * n);
  const lossAtLow = (positionAmount * stopLowPct) / 100;
  const lossAtHigh = (positionAmount * stopHighPct) / 100;
  const riskAtLowPct = (positionWeightPct * stopLowPct) / 100;
  const riskAtHighPct = (positionWeightPct * stopHighPct) / 100;

  const warnings: string[] = [];
  if (positionWeightPct > MAX_POSITION_PCT) {
    warnings.push("한 종목 비중이 50%를 초과합니다 — 분산 부족(미너비니 최대 50%).");
  } else if (positionWeightPct > BEST_POSITION_PCT) {
    warnings.push("포지션 비중이 25%를 초과합니다 — 최고 종목도 20~25% 권장.");
  }
  if (n > MAX_STOCKS) {
    warnings.push("종목 수가 12개를 초과합니다 — 미너비니 권장 10~12개.");
  }
  if (riskAtHighPct < ACCOUNT_RISK_MIN) {
    warnings.push("비중이 작아 10% 손절에도 계좌 위험이 1.25% 미만입니다(보수적 — 위험 여력 있음).");
  }

  return {
    valid: true, positionAmount, positionWeightPct,
    stopLowPct, stopHighPct, lossAtLow, lossAtHigh,
    riskAtLowPct, riskAtHighPct, warnings,
  };
}

// 원화를 억·만원 단위로 읽기 쉽게. 1만원 미만은 원 단위.
export function fmtKRW(n: number): string {
  if (!(n > 0)) return "0원";
  if (n < 1e4) return `${Math.round(n).toLocaleString()}원`;
  const eok = Math.floor(n / 1e8);
  const man = Math.round(((n - eok * 1e8) / 1e4) * 10) / 10;
  const parts: string[] = [];
  if (eok > 0) parts.push(`${eok.toLocaleString()}억`);
  if (man > 0) parts.push(`${man.toLocaleString()}만`);
  return `${parts.join(" ")}원`;
}
