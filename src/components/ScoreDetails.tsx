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

export function ScoreDetails({ details }: { details: ScoreDetail[] }) {
  const [open, setOpen] = useState(false);

  if (!details || details.length === 0) return null;

  // 카테고리별 그룹핑
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
        <div className="mt-4 space-y-5">
          {[1, 2, 3].map((catNum) => {
            const items = grouped[catNum];
            if (!items) return null;
            const catTotal = items.reduce((s, d) => s + d.score, 0);
            const catMax = items.reduce((s, d) => s + d.max, 0);

            return (
              <div key={catNum}>
                <div className="flex items-center justify-between mb-2">
                  <h5 className="text-sm font-medium text-on-surface">
                    카테고리 {catNum}: {catNames[catNum]}
                  </h5>
                  <span className="text-sm font-mono text-primary">
                    {catTotal}/{catMax}
                  </span>
                </div>
                <div className="space-y-1">
                  {items.map((d) => {
                    const pct = d.max > 0 ? (d.score / d.max) * 100 : 0;
                    return (
                      <div key={d.item} className="flex items-center gap-3 py-1.5 px-3 rounded-lg bg-surface-container/30">
                        <span className="text-sm text-on-surface w-28 shrink-0">{d.item}</span>
                        <div className="flex-1">
                          <div className="w-full h-1 bg-surface-container-highest rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{
                                width: `${pct}%`,
                                backgroundColor: pct >= 80 ? "#95d3ba" : pct >= 50 ? "#e9c176" : "#ffb4ab",
                              }}
                            />
                          </div>
                        </div>
                        <span className="text-xs font-mono text-on-surface-variant w-12 text-right">
                          {d.score}/{d.max}
                        </span>
                        <span className="text-xs text-on-surface-variant/50 w-36 text-right hidden md:block">
                          {d.basis}
                        </span>
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
