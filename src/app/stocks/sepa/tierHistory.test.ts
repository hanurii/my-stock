import { describe, it, expect } from "vitest";
import { renderTrend, computeTrendByCode, type TierHistory } from "./tierHistory";
import { PATTERNS, type RawCandidate } from "./sepaPatterns";

describe("renderTrend", () => {
  it("어제→오늘 티어 점", () => {
    expect(renderTrend(["actionable", "breakout"])).toBe("🟢🔴");
    expect(renderTrend(["actionable", "actionable"])).toBe("🟢🟢");
    expect(renderTrend(["actionable", "watch"])).toBe("🟢🟡");
  });
  it("신규(직전 없음+오늘 있음) → 🆕 접두", () => {
    expect(renderTrend([null, "breakout"])).toBe("🆕🔴");
    expect(renderTrend([null, null, "breakout"])).toBe("🆕🔴");
  });
  it("단일 날짜는 🆕 없음", () => {
    expect(renderTrend(["breakout"])).toBe("🔴");
  });
  it("3일치", () => {
    expect(renderTrend(["watch", "actionable", "breakout"])).toBe("🟡🟢🔴");
  });
  it("모두 없음 → 빈 문자열", () => {
    expect(renderTrend([null, null])).toBe("");
  });
});

describe("computeTrendByCode", () => {
  // 최소 필드만 갖춘 VCP 레코드
  const rec = (code: string, over: Partial<RawCandidate>): RawCandidate => ({
    code, name: code, market: "KOSPI", current_price: 1, rs: 90,
    status: "forming", pivot_price: 100, pct_to_pivot: 5,
    vcp_detected: true, num_contractions: 2, ...over,
  });
  const history: TierHistory = {
    dates: ["2026-06-30", "2026-07-01"],
    byDate: {
      "2026-06-30": {
        vcp: [
          rec("A", { status: "actionable", pct_to_pivot: 2 }),   // 어제 🟢
          rec("B", { status: "actionable", pct_to_pivot: 2 }),   // 어제 🟢
        ],
      },
      "2026-07-01": {
        vcp: [
          rec("A", { status: "breakout", pct_to_pivot: -5 }),    // 오늘 🔴
          rec("B", { status: "forming", pct_to_pivot: 6 }),      // 오늘 🟡
          rec("C", { status: "breakout", pct_to_pivot: -3 }),    // 오늘 🔴 (신규)
        ],
      },
    },
  };
  it("종목별 추이 문자열 (신규 🆕 포함)", () => {
    const t = computeTrendByCode(history, "vcp", PATTERNS.vcp);
    expect(t["A"]).toBe("🟢🔴");   // 진입임박 → 돌파
    expect(t["B"]).toBe("🟢🟡");   // 진입임박 → 예의주시
    expect(t["C"]).toBe("🆕🔴");   // 어제 없음 → 오늘 돌파
  });
});
