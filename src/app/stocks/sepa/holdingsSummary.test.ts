import { describe, it, expect } from "vitest";
import { accumTally, ruleTally, strengthTally } from "./holdingsSummary";
import type { HoldingRule } from "./SepaHoldingsSection";

describe("accumTally", () => {
  it("counts met accumulation + ok mvp out of 6", () => {
    const acc = { window: "15일 완료", elapsed: 15, signals: [
      { id: "a", status: "met", detail: "" },
      { id: "b", status: "met", detail: "" },
      { id: "c", status: "unmet", detail: "" }] };
    const mvp = { status: "yes", m: { ok: true, detail: "" },
      v: { ok: true, detail: "" }, p: { ok: true, detail: "" } };
    expect(accumTally(acc as never, mvp as never)).toEqual({ met: 5, total: 6, complete: true });
  });
  it("marks incomplete when elapsed < 15", () => {
    expect(accumTally({ window: "", elapsed: 2, signals: [] } as never, undefined).complete).toBe(false);
  });
});

describe("ruleTally", () => {
  it("tallies by status", () => {
    const rules = [
      { id: "1", status: "pass", detail: "" }, { id: "2", status: "violation", detail: "" },
      { id: "3", status: "watch", detail: "" }, { id: "4", status: "pending", detail: "" },
      { id: "5", status: "na", detail: "" }];
    // weakEntry 는 26-08-22 추가 — kind 가 없는 규칙만 있으면 false
    expect(ruleTally(rules as never)).toEqual({ pass: 1, violation: 1, watch: 1, pending: 2, weakEntry: false });
  });
});

describe("strengthTally", () => {
  it("returns null when not extended", () => {
    expect(strengthTally({ signal: "not_extended", extended: false,
      gate_detail: "", count: 0, signals: [] })).toBeNull();
  });
  it("returns fired/total when extended", () => {
    expect(strengthTally({ signal: "sell_into_strength", extended: true, gate_detail: "",
      count: 2, signals: [{}, {}, {}, {}] as never })).toEqual({ fired: 2, total: 4 });
  });
});

// ── 돌파 품질(①)은 약세 규칙 집계에서 뺀다 (26-08-22) ──────────────────────
// low_volume_breakout 은 매수 순간 확정돼 이후 안 바뀌는 값이라 매도 신호가 아니다.
// 실측: 실거래 63건 중 43건(68%)에 상시 점등해 "위반 1건"이 배경 소음이 돼 있었다.
describe("ruleTally — 매수 품질 분리", () => {
  const exit = (id: string, status: HoldingRule["status"]): HoldingRule =>
    ({ id, status, detail: "", kind: "exit" });
  const entry = (status: HoldingRule["status"]): HoldingRule =>
    ({ id: "low_volume_breakout", status, detail: "", kind: "entry_quality" });

  it("돌파 품질 위반은 약세 위반으로 세지 않는다", () => {
    const t = ruleTally([entry("violation"), exit("close_below_ma", "pass"),
                         exit("weak_days_dominant", "pass")]);
    expect(t.violation).toBe(0);
    expect(t.pass).toBe(2);
  });

  it("움직이는 규칙 위반은 그대로 센다", () => {
    const t = ruleTally([entry("violation"), exit("close_below_ma", "violation"),
                         exit("weak_days_dominant", "pass")]);
    expect(t.violation).toBe(1);
  });

  it("kind 가 없는 옛 데이터는 종전대로 센다(하위 호환)", () => {
    const legacy: HoldingRule[] = [
      { id: "low_volume_breakout", status: "violation", detail: "" },
      { id: "close_below_ma", status: "violation", detail: "" },
    ];
    expect(ruleTally(legacy).violation).toBe(2);
  });

  it("돌파 품질이 위반인지 따로 알려준다", () => {
    expect(ruleTally([entry("violation")]).weakEntry).toBe(true);
    expect(ruleTally([entry("pass")]).weakEntry).toBe(false);
    expect(ruleTally([exit("close_below_ma", "pass")]).weakEntry).toBe(false);
  });
});
