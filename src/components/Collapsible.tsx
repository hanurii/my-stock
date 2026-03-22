"use client";

import { useState } from "react";

export function Collapsible({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left group"
      >
        <span
          className="material-symbols-outlined text-primary-dim/60 text-base transition-transform duration-200"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          chevron_right
        </span>
        <h4 className="text-lg font-serif text-on-surface group-hover:text-primary transition-colors">
          {title}
        </h4>
      </button>
      {open && <div className="mt-4">{children}</div>}
    </div>
  );
}
