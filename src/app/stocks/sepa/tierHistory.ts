// SEPA 티어 추이 계산 (순수). 히스토리 스냅샷 → 종목별 최근 티어 시퀀스 문자열.
import {
  classifyCandidate,
  PATTERNS,
  type PatternConfig,
  type RawCandidate,
  type Tier,
} from "./sepaPatterns";

export type PatternKey = keyof typeof PATTERNS;

export interface TierHistory {
  dates: string[];
  byDate: Record<string, Partial<Record<PatternKey, RawCandidate[]>>>;
}

const TIER_DOT: Record<Tier, string> = {
  breakout: "🔴",
  actionable: "🟢",
  watch: "🟡",
};

// 티어 시퀀스(오래된→최신) → 표시 문자열. null(숨김/미노출)은 점 생략.
// 신규(직전 날짜 null + 최신 non-null, 직전 날짜가 존재할 때) → 앞에 🆕.
export function renderTrend(seq: (Tier | null)[]): string {
  const dots = seq
    .filter((t): t is Tier => t != null)
    .map((t) => TIER_DOT[t])
    .join("");
  const last = seq[seq.length - 1];
  const prev = seq.length >= 2 ? seq[seq.length - 2] : undefined;
  const isNew = last != null && prev === null;
  return (isNew ? "🆕" : "") + dots;
}

export function computeTrendByCode(
  history: TierHistory,
  patternKey: PatternKey,
  config: PatternConfig
): Record<string, string> {
  const dates = history.dates ?? [];
  const tierPerDate: Record<string, Record<string, Tier | null>> = {};
  const allCodes = new Set<string>();
  for (const d of dates) {
    const recs = history.byDate?.[d]?.[patternKey] ?? [];
    const m: Record<string, Tier | null> = {};
    for (const raw of recs) {
      m[raw.code] = classifyCandidate(raw, config);
      allCodes.add(raw.code);
    }
    tierPerDate[d] = m;
  }
  const out: Record<string, string> = {};
  for (const code of allCodes) {
    const seq = dates.map((d) => tierPerDate[d]?.[code] ?? null);
    out[code] = renderTrend(seq);
  }
  return out;
}
