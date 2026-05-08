"use client";

import { useState } from "react";

export function Collapsible({
  title,
  children,
  defaultOpen = false,
  size = "h4",
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  size?: "h3" | "h4";
}) {
  const [open, setOpen] = useState(defaultOpen);

  const isH3 = size === "h3";
  const titleClass = isH3
    ? "text-2xl font-serif text-on-surface tracking-tight group-hover:text-primary transition-colors"
    : "text-lg font-serif text-on-surface group-hover:text-primary transition-colors";
  const iconClass = isH3
    ? "material-symbols-outlined text-primary-dim/60 text-xl transition-transform duration-200"
    : "material-symbols-outlined text-primary-dim/60 text-base transition-transform duration-200";

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left group"
      >
        <span
          className={iconClass}
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          chevron_right
        </span>
        {isH3 ? (
          <h3 className={titleClass}>{title}</h3>
        ) : (
          <h4 className={titleClass}>{title}</h4>
        )}
      </button>
      {open && <div className="mt-4">{children}</div>}
    </div>
  );
}
