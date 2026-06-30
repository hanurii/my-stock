import { describe, it, expect } from "vitest";
import {
  classify,
  sortRows,
  buildSection,
  PATTERNS,
  WATCH_PCT,
  type ClassifiedRow,
  type RawCandidate,
} from "./sepaPatterns";

const base = { detected: true, structureOk: true, pivot_price: 100, pct_to_pivot: 5 };

describe("classify", () => {
  it("WATCH_PCT 상수는 12", () => {
    expect(WATCH_PCT).toBe(12);
  });
  it("detected + breakout → 🔴 breakout", () => {
    expect(classify({ ...base, status: "breakout", pct_to_pivot: -8 })).toBe("breakout");
  });
  it("detected + actionable → 🟢 actionable", () => {
    expect(classify({ ...base, status: "actionable" })).toBe("actionable");
  });
  it("detected + forming → 🟡 watch (피벗 거리 무관)", () => {
    expect(classify({ ...base, status: "forming", pct_to_pivot: 50 })).toBe("watch");
  });
  it("미검출 + forming + 피벗 0~12% 근접 + 구조 → 🟡 watch", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: 8 })).toBe("watch");
  });
  it("경계: pct_to_pivot 정확히 12 → 포함(watch)", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: 12 })).toBe("watch");
  });
  it("경계: pct_to_pivot 12.01 → 숨김(null)", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: 12.01 })).toBeNull();
  });
  it("경계: pct_to_pivot 0 → 포함, 음수(미검출) → 숨김", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: 0 })).toBe("watch");
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: 100, pct_to_pivot: -0.01 })).toBeNull();
  });
  it("미검출 + 근접하지만 구조 미형성 → 숨김", () => {
    expect(classify({ detected: false, structureOk: false, status: "forming", pivot_price: 100, pct_to_pivot: 5 })).toBeNull();
  });
  it("failed → 숨김", () => {
    expect(classify({ ...base, status: "failed" })).toBeNull();
    expect(classify({ detected: false, structureOk: true, status: "failed", pivot_price: 100, pct_to_pivot: 3 })).toBeNull();
  });
  it("피벗 없음 + 미검출 → 숨김", () => {
    expect(classify({ detected: false, structureOk: true, status: "forming", pivot_price: null, pct_to_pivot: null })).toBeNull();
  });
  it("미검출 breakout(피벗 위, pct 음수) → 근접 아님 → 숨김", () => {
    expect(classify({ detected: false, structureOk: true, status: "breakout", pivot_price: 100, pct_to_pivot: -8 })).toBeNull();
  });
});

function row(over: Partial<ClassifiedRow>): ClassifiedRow {
  return {
    code: "0", name: "n", market: "KOSPI", current_price: 1, rs: 50,
    status: "forming", pivot_price: 100, pct_to_pivot: 5, tier: "watch",
    raw: {} as RawCandidate, ...over,
  };
}

describe("sortRows", () => {
  it("티어 우선(🔴→🟢→🟡), 동률은 피벗 거리(절댓값) 가까운 순, 그다음 RS 내림차순", () => {
    const rows = [
      row({ code: "watchFar", tier: "watch", pct_to_pivot: 10, rs: 90 }),
      row({ code: "breakoutA", tier: "breakout", pct_to_pivot: -20, rs: 50 }),
      row({ code: "breakoutB", tier: "breakout", pct_to_pivot: -2, rs: 50 }),
      row({ code: "actionable", tier: "actionable", pct_to_pivot: 1, rs: 70 }),
      row({ code: "watchNearLowRs", tier: "watch", pct_to_pivot: 3, rs: 40 }),
      row({ code: "watchNearHighRs", tier: "watch", pct_to_pivot: 3, rs: 95 }),
    ];
    sortRows(rows);
    expect(rows.map((r) => r.code)).toEqual([
      "breakoutB",       // 🔴 abs 2
      "breakoutA",       // 🔴 abs 20
      "actionable",      // 🟢
      "watchNearHighRs", // 🟡 abs 3, rs 95
      "watchNearLowRs",  // 🟡 abs 3, rs 40
      "watchFar",        // 🟡 abs 10
    ]);
  });
});

describe("buildSection", () => {
  it("null 후보 → 빈 결과", () => {
    const r = buildSection(null, PATTERNS.vcp);
    expect(r.rows).toEqual([]);
    expect(r.counts).toEqual({ breakout: 0, actionable: 0, watch: 0 });
  });

  it("VCP: detectField·structureOk 적용, 숨김 제외, 카운트", () => {
    const cands: RawCandidate[] = [
      { code: "A", name: "a", market: "KOSPI", current_price: 1, rs: 90, status: "breakout", pivot_price: 100, pct_to_pivot: -5, vcp_detected: true, num_contractions: 3 },
      { code: "B", name: "b", market: "KOSDAQ", current_price: 1, rs: 80, status: "actionable", pivot_price: 100, pct_to_pivot: 2, vcp_detected: true, num_contractions: 2 },
      { code: "C", name: "c", market: "KOSPI", current_price: 1, rs: 70, status: "forming", pivot_price: 100, pct_to_pivot: 7, vcp_detected: false, num_contractions: 2 },
      { code: "D-hidden", name: "d", market: "KOSPI", current_price: 1, rs: 60, status: "forming", pivot_price: 100, pct_to_pivot: 7, vcp_detected: false, num_contractions: 1 }, // 구조 미형성(수축<2) → 숨김
      { code: "E-hidden", name: "e", market: "KOSPI", current_price: 1, rs: 60, status: "failed", pivot_price: 100, pct_to_pivot: 1, vcp_detected: false, num_contractions: 3 },
    ];
    const r = buildSection(cands, PATTERNS.vcp);
    expect(r.rows.map((x) => x.code)).toEqual(["A", "B", "C"]);
    expect(r.counts).toEqual({ breakout: 1, actionable: 1, watch: 1 });
    expect(r.rows[0].tier).toBe("breakout");
  });

  it("파워플레이: flag_length_days>0 이 structureOk", () => {
    const cands: RawCandidate[] = [
      { code: "P", name: "p", market: "KOSDAQ", current_price: 1, rs: 88, status: "forming", pivot_price: 100, pct_to_pivot: 6, pattern_detected: false, flag_length_days: 8 },
      { code: "Q-hidden", name: "q", market: "KOSDAQ", current_price: 1, rs: 88, status: "forming", pivot_price: 100, pct_to_pivot: 6, pattern_detected: false, flag_length_days: 0 },
    ];
    const r = buildSection(cands, PATTERNS.powerplayTrend);
    expect(r.rows.map((x) => x.code)).toEqual(["P"]);
  });
});
