import { describe, it, expect } from "vitest";
import {
  classify,
  sortRows,
  buildSection,
  fmtCell,
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

  it("파워플레이 structureOk: 깃발 길이>0 AND 눌림>0 (눌림 0% 퇴화 깃발 제외)", () => {
    const cands: RawCandidate[] = [
      { code: "P", name: "p", market: "KOSDAQ", current_price: 1, rs: 88, status: "forming", pivot_price: 100, pct_to_pivot: 6, pattern_detected: false, flag_length_days: 8, flag_depth_pct: 5 },
      { code: "Q-len0", name: "q", market: "KOSDAQ", current_price: 1, rs: 88, status: "forming", pivot_price: 100, pct_to_pivot: 6, pattern_detected: false, flag_length_days: 0, flag_depth_pct: 5 },
      // 신고가 부근 퇴화: 눌림 0% + 피벗=현재가(pct 0) → 제외돼야 함
      { code: "R-depth0", name: "r", market: "KOSDAQ", current_price: 1, rs: 88, status: "forming", pivot_price: 100, pct_to_pivot: 0, pattern_detected: false, flag_length_days: 44, flag_depth_pct: 0 },
    ];
    const r = buildSection(cands, PATTERNS.powerplayTrend);
    expect(r.rows.map((x) => x.code)).toEqual(["P"]);
  });

  it("excludeCodes: 상장폐지 예정 등 제외 종목은 통과 종목이어도 숨김·카운트 제외", () => {
    const cands: RawCandidate[] = [
      { code: "A", name: "a", market: "KOSPI", current_price: 1, rs: 90, status: "breakout", pivot_price: 100, pct_to_pivot: -5, vcp_detected: true, num_contractions: 3 },
      { code: "057050", name: "현대홈쇼핑", market: "KOSPI", current_price: 1, rs: 89, status: "breakout", pivot_price: 100, pct_to_pivot: -3, vcp_detected: true, num_contractions: 3 },
    ];
    const r = buildSection(cands, PATTERNS.vcp, WATCH_PCT, new Set(["057050"]));
    expect(r.rows.map((x) => x.code)).toEqual(["A"]);
    expect(r.counts).toEqual({ breakout: 1, actionable: 0, watch: 0 });
  });

  it("excludeCodes 미지정 시 아무것도 제외하지 않음", () => {
    const cands: RawCandidate[] = [
      { code: "057050", name: "현대홈쇼핑", market: "KOSPI", current_price: 1, rs: 89, status: "breakout", pivot_price: 100, pct_to_pivot: -3, vcp_detected: true, num_contractions: 3 },
    ];
    expect(buildSection(cands, PATTERNS.vcp).rows.map((x) => x.code)).toEqual(["057050"]);
  });
});

describe("fmtCell", () => {
  it("pct=부호 있는 증감(+ 상승)", () => {
    expect(fmtCell(26.36, "pct")).toBe("+26.4%");
    expect(fmtCell(-5, "pct")).toBe("-5.0%");
  });
  it("depth/tight=크기(+ 부호 없이)", () => {
    expect(fmtCell(26.36, "depth")).toBe("26.4%");
    expect(fmtCell(10.96, "tight")).toBe("11.0%");
  });
  it("null → —", () => {
    expect(fmtCell(null, "depth")).toBe("—");
    expect(fmtCell(undefined, "pct")).toBe("—");
  });
  it("ratio/int/days/price", () => {
    expect(fmtCell(0.634, "ratio")).toBe("0.63");
    expect(fmtCell(5, "int")).toBe("5");
    expect(fmtCell(53, "days")).toBe("53일");
    expect(fmtCell(29500, "price")).toBe("29,500");
  });
});

describe("PATTERNS 컬럼 kind — 깊이는 부호 없는 depth", () => {
  it("VCP 베이스깊이·파워플레이 깃발깊이 = depth, 깃대상승 = pct", () => {
    const vcpDepth = PATTERNS.vcp.columns.find((c) => c.key === "base_depth_pct");
    const ppFlagDepth = PATTERNS.powerplayTrend.columns.find((c) => c.key === "flag_depth_pct");
    const ppPoleGain = PATTERNS.powerplayTrend.columns.find((c) => c.key === "flagpole_gain_pct");
    expect(vcpDepth?.kind).toBe("depth");
    expect(ppFlagDepth?.kind).toBe("depth");
    expect(ppPoleGain?.kind).toBe("pct");
  });
});
