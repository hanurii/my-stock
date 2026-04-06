"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import Link from "next/link";

interface DateNavProps {
  dates: string[];
  activeDate: string;
  fadeFrom?: string; // CSS variable name, e.g. "surface" or "surface-container-low"
}

export function DateNav({
  dates,
  activeDate,
  fadeFrom = "surface",
}: DateNavProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLAnchorElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 4);
  }, []);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ inline: "center", block: "nearest" });
    // delay check so layout settles after scrollIntoView
    requestAnimationFrame(updateScrollState);
  }, [activeDate, updateScrollState]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener("scroll", updateScrollState, { passive: true });
    window.addEventListener("resize", updateScrollState);
    return () => {
      el.removeEventListener("scroll", updateScrollState);
      window.removeEventListener("resize", updateScrollState);
    };
  }, [updateScrollState]);

  const gradientFrom = `var(--color-${fadeFrom})`;

  return (
    <div className="relative min-w-0 flex-1">
      {canScrollLeft && (
        <div
          className="absolute left-0 top-0 bottom-0 w-8 z-10 pointer-events-none rounded-l-lg"
          style={{
            background: `linear-gradient(to right, ${gradientFrom}, transparent)`,
          }}
        />
      )}
      {canScrollRight && (
        <div
          className="absolute right-0 top-0 bottom-0 w-8 z-10 pointer-events-none rounded-r-lg"
          style={{
            background: `linear-gradient(to left, ${gradientFrom}, transparent)`,
          }}
        />
      )}

      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto scrollbar-hide"
      >
        {dates.map((d, i) => (
          <Link
            key={d}
            ref={d === activeDate ? activeRef : undefined}
            href={i === 0 ? "/" : `/report/${d}`}
            className={`px-3 py-1.5 rounded-lg text-sm transition-all whitespace-nowrap shrink-0 ${
              d === activeDate
                ? "gold-shimmer text-on-primary font-bold"
                : "bg-surface-container-high text-on-surface-variant hover:text-primary hover:bg-surface-container-highest"
            }`}
          >
            {d}
          </Link>
        ))}
      </div>
    </div>
  );
}
