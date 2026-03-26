"use client";

import type { Indicator } from "@/lib/data";
import React, { useState } from "react";

interface IndicatorTableProps {
  title: string;
  indicators: Indicator[];
}

function CommentCell({ comment }: { comment: string }) {
  const [open, setOpen] = useState(false);
  const buttonRef = React.useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  const handleOpen = () => {
    if (!open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setPos({
        top: rect.top,
        left: Math.max(8, rect.left - 192),
      });
    }
    setOpen((v) => !v);
  };

  return (
    <td className="px-3 py-3 text-xs text-on-surface-variant/60 leading-snug max-w-[240px]">
      <span className="hidden min-[1475px]:inline">{comment}</span>
      <span className="min-[1475px]:hidden">
        <button
          ref={buttonRef}
          type="button"
          onClick={handleOpen}
          className="p-1 rounded hover:bg-surface-container-high/50 transition-colors"
          aria-label="코멘트 보기"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-4 h-4 text-on-surface-variant/50"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 0-2 0 1 1 0 0 0 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
              clipRule="evenodd"
            />
          </svg>
        </button>
        {open && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <div
              className="fixed z-50 w-48 p-3 rounded-lg bg-surface-container-high text-on-surface text-xs leading-relaxed shadow-lg ghost-border"
              style={{ top: pos.top, left: pos.left }}
            >
              {comment}
            </div>
          </>
        )}
      </span>
    </td>
  );
}

export function IndicatorTable({ title, indicators }: IndicatorTableProps) {
  return (
    <div className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border overflow-hidden">
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
                {ind.change > 0 ? "+" : ""}{ind.change_unit === "%p" ? `${ind.change.toFixed(2)}%p` : `${ind.change.toFixed(2)}%`}
              </td>
              <td className={`px-3 py-3 text-right font-mono text-sm whitespace-nowrap ${weeklyColor}`}>
                {ind.weekly_change > 0 ? "+" : ""}{ind.change_unit === "%p" ? `${ind.weekly_change.toFixed(2)}%p` : `${ind.weekly_change.toFixed(1)}%`}
              </td>
              <td className="px-3 py-3 text-xs text-on-surface-variant whitespace-nowrap hidden md:table-cell">
                {ind.trend}
              </td>
              <CommentCell comment={ind.comment} />
            </tr>
          );
        })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
