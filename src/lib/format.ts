/**
 * "2026-03-28" → "2026.03.28"
 * "2026-03-28T06:30" → "2026.03.28 오전"
 * "2026-03-28T17:00" → "2026.03.28 오후"
 */
export function formatScoredAt(dateStr: string): string {
  const hasTime = dateStr.includes("T");
  const datePart = hasTime ? dateStr.split("T")[0] : dateStr;
  const d = new Date(datePart + "T00:00:00");
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const base = `${y}.${m}.${day}`;
  if (!hasTime) return base;
  const hour = parseInt(dateStr.split("T")[1].split(":")[0], 10);
  return `${base} ${hour < 12 ? "오전" : "오후"}`;
}

/**
 * 달러 금액 포맷 (e.g. $62.0B, $350M, $1,234)
 */
export function formatUSD(amount: number): string {
  if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
  if (amount >= 1e6) return `$${(amount / 1e6).toFixed(0)}M`;
  return `$${amount.toLocaleString()}`;
}
