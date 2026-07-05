export const PROFIT_COLOR = "#95d3ba";
export const LOSS_COLOR = "#ffb4ab";

export function fmtPct(n: number | null): string {
  return n == null ? "-" : `${n.toFixed(2)}%`;
}
export function fmtLossPct(n: number | null): string {
  return n == null ? "-" : `-${n.toFixed(2)}%`;
}
export function fmtSignedPct(n: number | null): string {
  return n == null ? "-" : `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}
export function fmtNum(n: number | null): string {
  return n == null ? "-" : String(n);
}
export function fmtRatio(n: number | null): string {
  return n == null ? "-" : n.toFixed(2);
}
export function plColor(n: number | null): string {
  if (n == null) return "inherit";
  return n > 0 ? PROFIT_COLOR : LOSS_COLOR;
}
