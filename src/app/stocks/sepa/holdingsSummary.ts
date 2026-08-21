// 보유 점검 카드 요약(점수판) 순수 계산 — SepaHoldingsSection에서 사용
import type { Accumulation, Mvp, HoldingRule, Strength } from "./SepaHoldingsSection";

export function accumTally(acc?: Accumulation, mvp?: Mvp): { met: number; total: number; complete: boolean } {
  let met = 0;
  for (const s of acc?.signals ?? []) if (s.status === "met") met++;
  if (mvp) for (const k of ["m", "v", "p"] as const) if (mvp[k]?.ok === true) met++;
  return { met, total: 6, complete: (acc?.elapsed ?? 0) >= 15 };
}

/** 약세 규칙 집계. **매수 품질(kind="entry_quality")은 위반에서 제외**한다.
 *
 * ①저거래량 돌파는 '돌파일 거래량'이라 매수 순간 확정되고 이후 안 바뀐다. 매일 다시 봐도
 * 답이 같으니 매도 신호가 아니라 매수 품질이다. 실측(26-08-22): 실거래 왕복 63건 중
 * 43건(68%)에 상시 점등해 "위반 1건"이 배경 소음이 돼 있었고, 조기청산 20건 중 19건이
 * 이것 때문에 🟠였는데 그중 53%가 이후 +20%에 도달했다.
 * kind 가 없는 옛 산출물은 종전대로 센다(하위 호환).
 */
export function ruleTally(rules: HoldingRule[]): {
  pass: number; violation: number; watch: number; pending: number; weakEntry: boolean;
} {
  const t = { pass: 0, violation: 0, watch: 0, pending: 0, weakEntry: false };
  for (const r of rules) {
    if (r.kind === "entry_quality") {
      t.weakEntry = r.status === "violation";
      continue;
    }
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
