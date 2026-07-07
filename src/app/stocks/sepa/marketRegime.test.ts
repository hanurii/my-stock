import { describe, it, expect } from "vitest";
import { downtrendSegments, type RegimePoint } from "./marketRegime";

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
