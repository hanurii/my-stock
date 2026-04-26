"use client";

import { useState, useMemo } from "react";
import type { SectorCumPoint } from "@/lib/foreign-flow";

interface Props {
  cum20d: SectorCumPoint[];
  cum60d: SectorCumPoint[];
}

type Window = "20d" | "60d";

function formatBillion(v: number): string {
  const sign = v >= 0 ? "+" : "−";
  const abs = Math.abs(v);
  if (abs >= 10000) return `${sign}${(abs / 10000).toFixed(2)}조`;
  if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(1)}천억`;
  return `${sign}${Math.round(abs)}억`;
}

export function ForeignFlowSectorBars({ cum20d, cum60d }: Props) {
  const [win, setWin] = useState<Window>("20d");

  const data = win === "20d" ? cum20d : cum60d;

  const { buyTop, sellTop, maxAbs } = useMemo(() => {
    const sorted = [...data].sort((a, b) => b.net_buy_billion - a.net_buy_billion);
    const buy = sorted.filter((s) => s.net_buy_billion > 0).slice(0, 10);
    const sell = sorted
      .filter((s) => s.net_buy_billion < 0)
      .sort((a, b) => a.net_buy_billion - b.net_buy_billion)
      .slice(0, 10);
    const max = Math.max(
      ...buy.map((s) => Math.abs(s.net_buy_billion)),
      ...sell.map((s) => Math.abs(s.net_buy_billion)),
      1,
    );
    return { buyTop: buy, sellTop: sell, maxAbs: max };
  }, [data]);

  return (
    <div>
      <div className="flex items-center justify-end gap-1 rounded-md bg-surface-container-low p-1 mb-5 w-fit ml-auto">
        {([
          ["20d", "최근 20일"],
          ["60d", "최근 60일"],
        ] as Array<[Window, string]>).map(([w, label]) => (
          <button
            key={w}
            onClick={() => setWin(w)}
            className={`px-3 py-1.5 text-xs rounded transition-colors ${
              win === w
                ? "bg-primary text-on-primary font-semibold"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {data.length === 0 ? (
        <div className="text-on-surface-variant text-sm py-12 text-center">
          업종별 데이터가 아직 없습니다.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <SectorBarList
            title="매수 우위 TOP 10"
            color="#e9c176"
            items={buyTop}
            maxAbs={maxAbs}
          />
          <SectorBarList
            title="매도 우위 TOP 10"
            color="#ffb4ab"
            items={sellTop}
            maxAbs={maxAbs}
          />
        </div>
      )}
    </div>
  );
}

function SectorBarList({
  title,
  color,
  items,
  maxAbs,
}: {
  title: string;
  color: string;
  items: SectorCumPoint[];
  maxAbs: number;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
        <h4 className="text-xs uppercase tracking-[0.18em] text-on-surface-variant">
          {title}
        </h4>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-on-surface-variant">해당 구간 데이터 없음</p>
      ) : (
        <ul className="space-y-2">
          {items.map((s) => {
            const ratio = Math.min(100, (Math.abs(s.net_buy_billion) / maxAbs) * 100);
            return (
              <li key={s.sector} className="text-sm">
                <div className="flex items-baseline justify-between mb-1 gap-3">
                  <span className="text-on-surface truncate" title={s.sector}>
                    {s.sector}
                  </span>
                  <span
                    className="font-mono text-xs whitespace-nowrap"
                    style={{ color }}
                  >
                    {formatBillion(s.net_buy_billion)}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-surface-container-low overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${ratio}%`, background: color, opacity: 0.85 }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
