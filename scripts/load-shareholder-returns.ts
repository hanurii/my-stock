/**
 * 주주환원 데이터 로드 유틸
 *
 * shareholder-returns.json을 읽어 ShareholderReturnData 맵으로 변환.
 * screen-growth-full, enrich-candidates-dart, update-watchlist-scores에서 공용.
 */
import fs from "fs";
import path from "path";
import type { ShareholderReturnData } from "../src/lib/scoring";

const DILUTIVE_TYPES = new Set([
  "전환권행사", "신주인수권행사", "유상증자(제3자배정)",
  "주식매수선택권행사", "상환권행사",
]);

export function loadShareholderReturnMap(): Map<string, ShareholderReturnData> {
  const map = new Map<string, ShareholderReturnData>();
  try {
    const filePath = path.join(process.cwd(), "public", "data", "shareholder-returns.json");
    const raw = JSON.parse(fs.readFileSync(filePath, "utf-8")) as {
      stocks: { code: string; treasury_stock: { cancelled: number }[]; dividends: { year: number; dps: number | null }[]; capital_changes: { year: number; type: string }[] }[];
    };
    const currentYear = new Date().getFullYear();
    const cutoffYear = currentYear - 5; // 최근 5년만 카운트
    for (const s of raw.stocks) {
      const cancellationYears = s.treasury_stock.filter((t) => t.cancelled > 0).length;
      const validDivs = s.dividends.filter((d) => d.year < currentYear).sort((a, b) => b.year - a.year);
      let consecutiveDivYears = 0;
      for (const d of validDivs) {
        if (d.dps !== null && d.dps > 0) consecutiveDivYears++;
        else break;
      }
      const dilutiveCount = s.capital_changes.filter((c) => DILUTIVE_TYPES.has(c.type) && c.year >= cutoffYear).length;
      map.set(s.code, { treasury_cancellation_years: cancellationYears, consecutive_dividend_years: consecutiveDivYears, dilutive_event_count: dilutiveCount });
    }
  } catch { /* shareholder-returns.json 없으면 빈 맵 */ }
  return map;
}
