export type RegimePoint = { date: string; index: number; ma20: number | null; up: boolean | null };

export type MarketRegime = {
  generated_at: string;
  current: { date: string; index: number; ma20: number | null; uptrend: boolean | null };
  series: RegimePoint[];
};

/** series 에서 하락구간(up===false)이 연속된 구간을 [{x1,x2}] 로 묶는다(음영용). */
export function downtrendSegments(series: RegimePoint[]): { x1: string; x2: string }[] {
  const segs: { x1: string; x2: string }[] = [];
  let start: string | null = null;
  let prev: string | null = null;
  for (const p of series) {
    if (p.up === false) {
      if (start === null) start = p.date;
      prev = p.date;
    } else if (start !== null && prev !== null) {
      segs.push({ x1: start, x2: prev });
      start = null;
      prev = null;
    }
  }
  if (start !== null && prev !== null) segs.push({ x1: start, x2: prev });
  return segs;
}
