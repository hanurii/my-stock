"use client";

import { useState } from "react";

interface ScoreDetail {
  item: string;
  basis: string;
  score: number;
  max: number;
  cat: number;
}

const catNames: Record<number, string> = {
  1: "저평가/이익창출력",
  2: "주주환원 의지",
  3: "미래 성장/경쟁력",
};

function getScoreColor(pct: number): string {
  if (pct >= 80) return "#95d3ba";
  if (pct >= 50) return "#e9c176";
  return "#ffb4ab";
}

export function ScoreDetails({ details }: { details: ScoreDetail[] }) {
  const [open, setOpen] = useState(false);

  if (!details || details.length === 0) return null;

  const grouped: Record<number, ScoreDetail[]> = {};
  details.forEach((d) => {
    if (!grouped[d.cat]) grouped[d.cat] = [];
    grouped[d.cat].push(d);
  });

  return (
    <div className="mt-4">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm text-primary-dim/60 hover:text-primary transition-colors group"
      >
        <span
          className="material-symbols-outlined text-sm transition-transform duration-200"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          chevron_right
        </span>
        <span className="group-hover:text-primary">세부 채점 보기</span>
      </button>

      {open && (
        <div className="mt-4 space-y-6">
          {[1, 2, 3].map((catNum) => {
            const items = grouped[catNum];
            if (!items) return null;
            const catTotal = items.reduce((s, d) => s + d.score, 0);
            const catMax = items.reduce((s, d) => s + d.max, 0);
            const catPct = catMax > 0 ? (catTotal / catMax) * 100 : 0;

            return (
              <div key={catNum}>
                <div className="flex items-center justify-between mb-3">
                  <h5 className="text-sm font-medium text-on-surface">
                    {catNames[catNum]}
                  </h5>
                  <span className="text-base font-mono font-bold" style={{ color: getScoreColor(catPct) }}>
                    {catTotal}/{catMax}
                  </span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {items.map((d) => {
                    const pct = d.max > 0 ? (d.score / d.max) * 100 : 0;
                    const color = getScoreColor(pct);

                    return (
                      <div key={d.item} className="bg-surface-container/40 rounded-xl p-4">
                        <p className="text-xs text-on-surface-variant/60 mb-2">{d.item}</p>
                        <div className="flex items-end justify-between mb-2">
                          <span className="text-2xl font-mono font-bold leading-none" style={{ color }}>
                            {d.score}
                          </span>
                          <span className="text-xs text-on-surface-variant/40">/{d.max}</span>
                        </div>
                        <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden mb-2">
                          <div
                            className="h-full rounded-full transition-all duration-300"
                            style={{ width: `${pct}%`, backgroundColor: color }}
                          />
                        </div>
                        <p className="text-[11px] text-on-surface-variant/50 leading-snug">{d.basis}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
