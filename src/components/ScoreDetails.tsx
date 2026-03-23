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

interface ScoreStyle {
  color: string;
  glow?: string;       // text-shadow
  barGradient?: string; // 바 그라데이션
}

function getScoreStyle(pct: number): ScoreStyle {
  if (pct >= 90) return {
    color: "#e0f7ff",
    glow: "0 0 12px rgba(180, 235, 255, 0.8), 0 0 4px rgba(255, 255, 255, 0.6)",
    barGradient: "linear-gradient(90deg, #88e0f7, #d4f5ff, #88e0f7)",
  };
  if (pct >= 70) return {
    color: "#6eedb5",
    glow: "0 0 10px rgba(110, 237, 181, 0.6), 0 0 3px rgba(149, 211, 186, 0.4)",
    barGradient: "linear-gradient(90deg, #4dcea0, #95d3ba, #4dcea0)",
  };
  if (pct >= 50) return {
    color: "#f0d060",
    barGradient: "linear-gradient(90deg, #d4a640, #f0d060, #d4a640)",
  };
  if (pct >= 30) return {
    color: "#b0b0bc",
    barGradient: "linear-gradient(90deg, #8e8e9a, #c8c8d0, #8e8e9a)",
  };
  return {
    color: "#6b5030",
    barGradient: "linear-gradient(90deg, #5a4020, #8b6f47, #5a4020)",
  };
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
                  <span
                    className="text-base font-mono font-bold"
                    style={{ color: getScoreStyle(catPct).color, textShadow: getScoreStyle(catPct).glow }}
                  >
                    {catTotal}/{catMax}
                  </span>
                </div>
                <div className="space-y-2">
                  {items.map((d) => {
                    const pct = d.max > 0 ? (d.score / d.max) * 100 : 0;
                    const style = getScoreStyle(pct);

                    return (
                      <div key={d.item} className="flex items-center gap-4 py-2 px-4 rounded-lg bg-surface-container/30">
                        {/* 좌: 항목명 */}
                        <span className="text-sm text-on-surface font-medium w-28 shrink-0">
                          {d.item}
                        </span>

                        {/* 중: 근거 */}
                        <span className="text-sm text-on-surface-variant/60 flex-1">
                          {d.basis}
                        </span>

                        {/* 우: 그래프 + 점수 */}
                        <div className="flex items-center gap-3 shrink-0">
                          <div className="w-24 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{ width: `${pct}%`, background: style.barGradient || style.color }}
                            />
                          </div>
                          <span
                            className="text-sm font-mono font-bold w-14 text-right"
                            style={{ color: style.color, textShadow: style.glow }}
                          >
                            {d.score}/{d.max}
                          </span>
                        </div>
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
