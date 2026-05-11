"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface Principle {
  letter: string;
  name: string;
  href: string;
  enabled: boolean;
}

const principles: Principle[] = [
  { letter: "C", name: "Current Quarterly", href: "/stocks/canslim/c", enabled: true },
  { letter: "A", name: "Annual Earnings", href: "/stocks/canslim/a", enabled: true },
  { letter: "N", name: "New Highs", href: "/stocks/canslim/n", enabled: false },
  { letter: "S", name: "Supply & Demand", href: "/stocks/canslim/s", enabled: false },
  { letter: "L", name: "Leader (RS)", href: "/stocks/canslim/l", enabled: false },
  { letter: "I", name: "Institutional", href: "/stocks/canslim/i", enabled: false },
  { letter: "M", name: "Market Direction", href: "/stocks/canslim/m", enabled: false },
];

export function CanslimNav() {
  const pathname = usePathname();
  const isHome = pathname === "/stocks/canslim";

  return (
    <nav className="sticky top-0 z-30 flex gap-1 bg-surface-container-low/90 backdrop-blur-md rounded-xl p-1.5 ghost-border overflow-x-auto scrollbar-hide shadow-sm">
      <Link
        href="/stocks/canslim"
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all flex-shrink-0 ${
          isHome
            ? "bg-primary/15 text-primary"
            : "text-on-surface-variant/70 hover:text-on-surface-variant hover:bg-surface-container/50"
        }`}
        title="CAN SLIM 인덱스"
      >
        <span className="material-symbols-outlined text-base">home</span>
        <span className="hidden sm:inline">개요</span>
      </Link>
      <span className="w-px bg-on-surface/10 my-1.5 mx-0.5" aria-hidden />
      {principles.map((p) => {
        const isActive = pathname.startsWith(p.href);
        if (p.enabled) {
          return (
            <Link
              key={p.letter}
              href={p.href}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-all flex-shrink-0 ${
                isActive
                  ? "bg-primary/15 text-primary font-bold"
                  : "text-on-surface-variant/70 hover:text-on-surface-variant hover:bg-surface-container/50"
              }`}
              title={p.name}
            >
              <span className={`text-base font-serif ${isActive ? "font-bold" : "font-medium"}`}>{p.letter}</span>
              <span className="hidden md:inline text-[11px] text-on-surface-variant/60">{p.name}</span>
            </Link>
          );
        }
        return (
          <span
            key={p.letter}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs flex-shrink-0 opacity-40 cursor-not-allowed"
            title={`${p.name} — 향후 추가 예정`}
          >
            <span className="text-base font-serif text-on-surface-variant/60">{p.letter}</span>
            <span className="hidden md:inline text-[11px] text-on-surface-variant/40">{p.name}</span>
          </span>
        );
      })}
    </nav>
  );
}
