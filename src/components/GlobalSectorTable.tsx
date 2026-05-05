import { formatPct, type GlobalSector } from "@/lib/hot-sectors";

export function GlobalSectorTable({
  sectors,
  spy,
}: {
  sectors: GlobalSector[];
  spy: {
    perf_5d: number | null;
    perf_20d: number | null;
    perf_60d: number | null;
    perf_3m: number | null;
    perf_6m: number | null;
    perf_ytd: number | null;
  };
}) {
  function cellClass(v: number | null): string {
    if (v == null) return "text-on-surface-variant";
    if (v > 0) return "text-primary";
    if (v < 0) return "text-error";
    return "text-on-surface-variant";
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-[10px] uppercase tracking-[0.16em] text-on-surface-variant/80 border-b border-outline-variant/20">
            <th className="text-left py-2 pr-3">섹터 (티커)</th>
            <th className="text-right py-2 px-2">5D</th>
            <th className="text-right py-2 px-2">20D</th>
            <th className="text-right py-2 px-2">60D</th>
            <th className="text-right py-2 px-2">3M</th>
            <th className="text-right py-2 px-2">6M</th>
            <th className="text-right py-2 px-2">YTD</th>
          </tr>
        </thead>
        <tbody>
          {/* SPY benchmark row */}
          <tr className="border-b border-outline-variant/15 bg-surface-container-low/40">
            <td className="py-2 pr-3 text-tertiary font-medium">
              S&P 500 (SPY) <span className="text-[10px] text-on-surface-variant/70">— 벤치마크</span>
            </td>
            <td className={`text-right px-2 ${cellClass(spy.perf_5d)}`}>{formatPct(spy.perf_5d)}</td>
            <td className={`text-right px-2 ${cellClass(spy.perf_20d)}`}>{formatPct(spy.perf_20d)}</td>
            <td className={`text-right px-2 ${cellClass(spy.perf_60d)}`}>{formatPct(spy.perf_60d)}</td>
            <td className={`text-right px-2 ${cellClass(spy.perf_3m)}`}>{formatPct(spy.perf_3m)}</td>
            <td className={`text-right px-2 ${cellClass(spy.perf_6m)}`}>{formatPct(spy.perf_6m)}</td>
            <td className={`text-right px-2 ${cellClass(spy.perf_ytd)}`}>{formatPct(spy.perf_ytd)}</td>
          </tr>
          {sectors
            .slice()
            .sort((a, b) => (b.perf_60d ?? -999) - (a.perf_60d ?? -999))
            .map((s) => (
              <tr key={s.ticker} className="border-b border-outline-variant/10">
                <td className="py-2 pr-3 text-on-surface">
                  <span className="font-mono text-primary/80 mr-2">{s.ticker}</span>
                  {s.gics_name_kr}
                </td>
                <td className={`text-right px-2 ${cellClass(s.perf_5d)}`}>{formatPct(s.perf_5d)}</td>
                <td className={`text-right px-2 ${cellClass(s.perf_20d)}`}>{formatPct(s.perf_20d)}</td>
                <td className={`text-right px-2 font-medium ${cellClass(s.perf_60d)}`}>{formatPct(s.perf_60d)}</td>
                <td className={`text-right px-2 ${cellClass(s.perf_3m)}`}>{formatPct(s.perf_3m)}</td>
                <td className={`text-right px-2 ${cellClass(s.perf_6m)}`}>{formatPct(s.perf_6m)}</td>
                <td className={`text-right px-2 ${cellClass(s.perf_ytd)}`}>{formatPct(s.perf_ytd)}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
