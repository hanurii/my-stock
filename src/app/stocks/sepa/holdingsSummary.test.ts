import { describe, it, expect } from "vitest";
import { accumTally, ruleTally, strengthTally } from "./holdingsSummary";

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
    expect(ruleTally(rules as never)).toEqual({ pass: 1, violation: 1, watch: 1, pending: 2 });
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
