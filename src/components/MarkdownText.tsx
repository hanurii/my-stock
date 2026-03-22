"use client";

import React from "react";

/**
 * 마크다운 인라인 문법(**볼드**)을 React 요소로 변환한다.
 * 순수 텍스트에 **가 그대로 노출되는 것을 방지.
 */
export function MarkdownText({
  children,
  className = "",
}: {
  children: string;
  className?: string;
}) {
  // **볼드** 패턴을 <strong>으로 변환
  const parts = children.split(/(\*\*[^*]+\*\*)/g);

  return (
    <span className={className}>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} className="font-semibold text-on-surface">
              {part.slice(2, -2)}
            </strong>
          );
        }
        return <React.Fragment key={i}>{part}</React.Fragment>;
      })}
    </span>
  );
}
