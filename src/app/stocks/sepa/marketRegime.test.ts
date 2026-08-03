import { describe, it, expect } from "vitest";
import { downtrendSegments, regimeStreak, type RegimePoint } from "./marketRegime";

const pt = (date: string, up: boolean | null): RegimePoint => ({ date, index: 100, ma20: 100, up });

describe("downtrendSegments", () => {
  it("단일 하락구간을 묶는다", () => {
    const s = [pt("d0", true), pt("d1", false), pt("d2", false), pt("d3", true)];
    expect(downtrendSegments(s)).toEqual([{ x1: "d1", x2: "d2" }]);
  });
  it("복수 하락구간을 각각 묶는다", () => {
    const s = [pt("d0", false), pt("d1", true), pt("d2", false)];
    expect(downtrendSegments(s)).toEqual([{ x1: "d0", x2: "d0" }, { x1: "d2", x2: "d2" }]);
  });
  it("끝까지 하락이면 마지막 구간을 닫는다", () => {
    const s = [pt("d0", true), pt("d1", false), pt("d2", false)];
    expect(downtrendSegments(s)).toEqual([{ x1: "d1", x2: "d2" }]);
  });
  it("전부 상승이면 빈 배열", () => {
    expect(downtrendSegments([pt("d0", true), pt("d1", true)])).toEqual([]);
  });
  it("up===null 은 하락으로 치지 않는다", () => {
    const s = [pt("d0", null), pt("d1", false)];
    expect(downtrendSegments(s)).toEqual([{ x1: "d1", x2: "d1" }]);
  });
});

describe("regimeStreak", () => {
  it("끝에서 같은 국면이 이어진 일수를 센다", () => {
    const s = [pt("d0", false), pt("d1", true), pt("d2", true), pt("d3", true)];
    expect(regimeStreak(s)).toBe(3);
  });
  it("하락 스트릭도 센다", () => {
    const s = [pt("d0", true), pt("d1", false), pt("d2", false)];
    expect(regimeStreak(s)).toBe(2);
  });
  it("마지막이 null 이면 0", () => {
    expect(regimeStreak([pt("d0", true), pt("d1", null)])).toBe(0);
  });
  it("빈 배열은 0", () => {
    expect(regimeStreak([])).toBe(0);
  });
  it("전 구간 같은 국면이면 전체 길이", () => {
    expect(regimeStreak([pt("d0", true), pt("d1", true)])).toBe(2);
  });
  it("null 에서 스트릭이 끊긴다", () => {
    const s = [pt("d0", true), pt("d1", null), pt("d2", true), pt("d3", true)];
    expect(regimeStreak(s)).toBe(2);
  });
});
