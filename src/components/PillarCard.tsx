"use client";

import { useState } from "react";

export interface PillarMetric {
  label: string;       // 지표명 + 만점 기준 (예: "ROE ≥20%")
  plain: string;       // 쉬운 풀이
}

interface Props {
  title: string;        // 한국어 (예: "사업 실력")
  subtitle?: string;    // 영문 보조 (예: "Quality")
  points: number;       // 예: 40
  question: string;     // 예: "회사가 진짜로 돈을 잘 버는가?"
  color: string;        // 좌측 보더 컬러
  metrics: PillarMetric[];
  analogy: string;      // 식당 비유
}

export function PillarCard({ title, subtitle, points, question, color, metrics, analogy }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="bg-surface-container/30 rounded-lg ghost-border overflow-hidden transition-all"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left flex items-center gap-3 px-4 py-3 hover:bg-surface-container/50 transition-colors group"
      >
        <span
          className="material-symbols-outlined text-primary-dim/60 text-base transition-transform duration-200"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          chevron_right
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className="font-bold text-on-surface text-sm">{title}</span>
            {subtitle && (
              <span className="text-[10px] font-mono uppercase tracking-wider text-on-surface-variant/50">
                {subtitle}
              </span>
            )}
            <span className="text-xs font-mono" style={{ color }}>
              ({points}점)
            </span>
            <span className="text-xs text-on-surface-variant">— {question}</span>
          </div>
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 text-xs space-y-2.5 border-t border-on-surface-variant/10">
          <div className="space-y-1.5 mt-3">
            {metrics.map((m, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <span className="material-symbols-outlined text-primary-dim/70 text-sm mt-0.5 shrink-0">
                  query_stats
                </span>
                <div className="flex-1">
                  <span className="font-medium text-on-surface">{m.label}</span>
                  <span className="text-on-surface-variant"> — {m.plain}</span>
                </div>
              </div>
            ))}
          </div>
          <div
            className="rounded-md p-3 mt-3 text-on-surface-variant leading-relaxed"
            style={{ backgroundColor: `${color}10`, borderLeft: `2px solid ${color}40` }}
          >
            <span className="text-on-surface font-medium">▸ 식당 비유:</span> {analogy}
          </div>
        </div>
      )}
    </div>
  );
}
