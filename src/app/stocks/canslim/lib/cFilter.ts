import type { CCriterion } from "../CanslimTable";

export const USER_C_THRESHOLD = 25;

export function passesCGate(cr: CCriterion): boolean {
  if (cr.yoy_pct === null || cr.yoy_pct === undefined) return false;
  if (cr.yoy_pct < USER_C_THRESHOLD) return false;

  const salesAccompany = (cr.sales_yoy_pct !== null && cr.sales_yoy_pct >= 25) || cr.sales_accel_3q;
  if (!salesAccompany) return false;

  const q = cr.eps_accel_quality;
  const qualityAccel = q === "mild" || q === "strong" || q === "explosive";
  const accelerating = cr.eps_accel_3q || qualityAccel;
  if (!accelerating) return false;

  if (cr.consecutive_decline_quarters >= 2) return false;
  if (cr.severe_decel) return false;
  return true;
}
