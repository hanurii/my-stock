import { describe, it, expect } from "vitest";
import { computePositionSizing, fmtKRW } from "./positionSizing";

describe("computePositionSizing", () => {
  it("기준 예시: 1.5억 · 5종목", () => {
    const r = computePositionSizing(150_000_000, 5);
    expect(r.valid).toBe(true);
    expect(r.positionAmount).toBe(30_000_000);
    expect(r.positionWeightPct).toBe(20);
    expect(r.stopLowPct).toBe(6.25);
    expect(r.stopHighPct).toBe(10);
    expect(r.lossAtLow).toBe(1_875_000);
    expect(r.lossAtHigh).toBe(3_000_000);
    expect(r.riskAtLowPct).toBeCloseTo(1.25, 6);
    expect(r.riskAtHighPct).toBeCloseTo(2.0, 6);
    expect(r.warnings).toEqual([]);
  });

  it("N=4: 비중 25%, 경고 없음, 손절 5~10%", () => {
    const r = computePositionSizing(100_000_000, 4);
    expect(r.positionWeightPct).toBe(25);
    expect(r.stopLowPct).toBe(5);
    expect(r.stopHighPct).toBe(10);
    expect(r.riskAtLowPct).toBeCloseTo(1.25, 6);
    expect(r.riskAtHighPct).toBeCloseTo(2.5, 6);
    expect(r.warnings).toEqual([]);
  });

  it("N=2: 비중 50% → '>25% 권장 초과' 경고", () => {
    const r = computePositionSizing(100_000_000, 2);
    expect(r.positionWeightPct).toBe(50);
    expect(r.stopLowPct).toBe(2.5);
    expect(r.stopHighPct).toBe(5);
    expect(r.warnings.some((w) => w.includes("25%"))).toBe(true);
    expect(r.warnings.some((w) => w.includes("50%"))).toBe(false);
  });

  it("N=1: 비중 100% → '50% 초과' 경고", () => {
    const r = computePositionSizing(100_000_000, 1);
    expect(r.positionWeightPct).toBe(100);
    expect(r.warnings.some((w) => w.includes("50%"))).toBe(true);
  });

  it("N=15: '>12개' + '보수적'(10% 손절도 위험<1.25%) 경고, 손절 10% 캡", () => {
    const r = computePositionSizing(150_000_000, 15);
    expect(r.stopLowPct).toBe(10);
    expect(r.stopHighPct).toBe(10);
    expect(r.riskAtHighPct).toBeLessThan(1.25);
    expect(r.warnings.some((w) => w.includes("12개"))).toBe(true);
    expect(r.warnings.some((w) => w.includes("보수적"))).toBe(true);
  });

  it("유효성: capital 0 / numStocks 0 → valid false", () => {
    expect(computePositionSizing(0, 5).valid).toBe(false);
    expect(computePositionSizing(150_000_000, 0).valid).toBe(false);
    expect(computePositionSizing(-1, 5).valid).toBe(false);
  });

  it("소수 종목 수는 내림(floor)", () => {
    const r = computePositionSizing(150_000_000, 5.9);
    expect(r.positionWeightPct).toBe(20); // floor(5.9)=5
  });
});

describe("fmtKRW", () => {
  it("억·만원 단위", () => {
    expect(fmtKRW(150_000_000)).toBe("1억 5,000만원");
    expect(fmtKRW(30_000_000)).toBe("3,000만원");
    expect(fmtKRW(1_875_000)).toBe("187.5만원");
    expect(fmtKRW(100_000_000)).toBe("1억원");
    expect(fmtKRW(0)).toBe("0원");
    expect(fmtKRW(5_000)).toBe("5,000원");
  });
});
