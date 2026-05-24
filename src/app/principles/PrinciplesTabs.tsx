"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/principles", label: "투자 원칙", icon: "balance" },
  { href: "/principles/musings", label: "고민 한 스푼", icon: "psychology" },
  { href: "/principles/discipline", label: "감정 다스리기", icon: "self_improvement" },
];

export function PrinciplesTabs() {
  const pathname = usePathname();

  return (
    <div className="flex gap-1 bg-surface-container-low rounded-xl p-1.5 ghost-border overflow-x-auto scrollbar-hide">
      {tabs.map((tab) => {
        const isActive = pathname === tab.href;

        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`relative flex items-center gap-2.5 px-5 py-3 rounded-lg text-sm font-medium transition-all duration-300 sm:flex-1 flex-shrink-0 justify-center whitespace-nowrap ${
              isActive
                ? "bg-primary/15 text-primary shadow-sm"
                : "text-on-surface-variant/60 hover:text-on-surface-variant hover:bg-surface-container/50"
            }`}
          >
            <span className="material-symbols-outlined text-lg">{tab.icon}</span>
            <span>{tab.label}</span>
          </Link>
        );
      })}
    </div>
  );
}
