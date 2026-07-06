// 보유 점검 카드 요약(점수판) 순수 계산 — SepaHoldingsSection에서 사용
import type { Accumulation, Mvp, HoldingRule, Strength } from "./SepaHoldingsSection";

export function accumTally(acc?: Accumulation, mvp?: Mvp): { met: number; total: number; complete: boolean } {
  let met = 0;
  for (const s of acc?.signals ?? []) if (s.status === "met") met++;
  if (mvp) for (const k of ["m", "v", "p"] as const) if (mvp[k]?.ok === true) met++;
  return { met, total: 6, complete: (acc?.elapsed ?? 0) >= 15 };
}

export function ruleTally(rules: HoldingRule[]): { pass: number; violation: number; watch: number; pending: number } {
  const t = { pass: 0, violation: 0, watch: 0, pending: 0 };
  for (const r of rules) {
    if (r.status === "pass") t.pass++;
    else if (r.status === "violation") t.violation++;
    else if (r.status === "watch") t.watch++;
    else t.pending++; // pending, na
  }
  return t;
}

export function strengthTally(s?: Strength): { fired: number; total: number } | null {
  if (!s || !s.extended) return null;
  return { fired: s.count, total: s.signals.length || 4 };
}
