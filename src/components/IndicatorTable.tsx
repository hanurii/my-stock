import type { Indicator } from "@/lib/data";

interface IndicatorTableProps {
  title: string;
  indicators: Indicator[];
}

export function IndicatorTable({ title, indicators }: IndicatorTableProps) {
  return (
    <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
      <h4 className="text-base font-serif text-on-surface mb-5 tracking-tight">
        {title}
      </h4>
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-base">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-on-surface-variant/50">
              <th className="text-left px-4 pb-3 font-normal">지표</th>
              <th className="text-right px-3 pb-3 font-normal">현재값</th>
              <th className="text-right px-3 pb-3 font-normal">전일비</th>
              <th className="text-right px-3 pb-3 font-normal">주간</th>
              <th className="text-left px-3 pb-3 font-normal hidden md:table-cell">추세</th>
              <th className="text-left px-3 pb-3 font-normal">코멘트</th>
            </tr>
          </thead>
          <tbody className="space-y-1">
        {indicators.map((ind) => {
          if (ind.error) {
            return (
              <tr key={ind.name}>
                <td className="px-4 py-3 text-on-surface-variant" colSpan={6}>{ind.name} — 데이터 없음</td>
              </tr>
            );
          }

          const changeColor =
            ind.change > 0 ? "text-error" : ind.change < 0 ? "text-[#6ea8fe]" : "text-on-surface-variant";
          const weeklyColor =
            ind.weekly_change > 0 ? "text-error" : ind.weekly_change < 0 ? "text-[#6ea8fe]" : "text-on-surface-variant";

          return (
            <tr
              key={ind.name}
              className="hover:bg-surface-container-high/30 transition-colors"
            >
              <td className="px-4 py-3 font-medium text-on-surface whitespace-nowrap">
                {ind.name}
              </td>
              <td className="px-3 py-3 text-right font-mono text-on-surface whitespace-nowrap">
                {ind.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </td>
              <td className={`px-3 py-3 text-right font-mono text-sm whitespace-nowrap ${changeColor}`}>
                {ind.change > 0 ? "+" : ""}{ind.change.toFixed(2)}%
              </td>
              <td className={`px-3 py-3 text-right font-mono text-sm whitespace-nowrap ${weeklyColor}`}>
                {ind.weekly_change > 0 ? "+" : ""}{ind.weekly_change.toFixed(1)}%
              </td>
              <td className="px-3 py-3 text-xs text-on-surface-variant whitespace-nowrap hidden md:table-cell">
                {ind.trend}
              </td>
              <td className="px-3 py-3 text-xs text-on-surface-variant/60 leading-snug max-w-[240px]">
                {ind.comment}
              </td>
            </tr>
          );
        })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
