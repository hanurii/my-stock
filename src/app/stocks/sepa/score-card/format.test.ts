import { describe, it, expect } from "vitest";
import { fmtPct, fmtLossPct, fmtSignedPct, fmtNum, fmtRatio, plColor, fmtSignedWon, PROFIT_COLOR, LOSS_COLOR } from "./format";

describe("format helpers", () => {
  it("fmtPct: 2자리 % / null은 -", () => {
    expect(fmtPct(4.88)).toBe("4.88%");
    expect(fmtPct(0)).toBe("0.00%");
    expect(fmtPct(null)).toBe("-");
  });
  it("fmtLossPct: 양수 크기를 -X% 로 / null은 -", () => {
    expect(fmtLossPct(5.62)).toBe("-5.62%");
    expect(fmtLossPct(null)).toBe("-");
  });
  it("fmtSignedPct: 부호 붙임 / null은 -", () => {
    expect(fmtSignedPct(7.56)).toBe("+7.56%");
    expect(fmtSignedPct(-5.62)).toBe("-5.62%");
    expect(fmtSignedPct(0)).toBe("+0.00%");
    expect(fmtSignedPct(null)).toBe("-");
  });
  it("fmtNum / fmtRatio", () => {
    expect(fmtNum(3)).toBe("3");
    expect(fmtNum(0)).toBe("0");
    expect(fmtNum(null)).toBe("-");
    expect(fmtRatio(2.28)).toBe("2.28");
    expect(fmtRatio(null)).toBe("-");
  });
  it("plColor: >0 수익색, <=0 손실색, null은 상속", () => {
    expect(plColor(5)).toBe(PROFIT_COLOR);
    expect(plColor(-5)).toBe(LOSS_COLOR);
    expect(plColor(0)).toBe(LOSS_COLOR);
    expect(plColor(null)).toBe("inherit");
  });
  it("fmtSignedWon: 부호+천단위+원 / null은 -", () => {
    expect(fmtSignedWon(154)).toBe("+154원");
    expect(fmtSignedWon(-533186)).toBe("-533,186원");
    expect(fmtSignedWon(0)).toBe("+0원");
    expect(fmtSignedWon(null)).toBe("-");
  });
});
