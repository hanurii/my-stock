"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface SellPage {
  slug: string;
  label: string;
  icon: string;
  enabled: boolean;
}

const pages: SellPage[] = [
  { slug: "strategy", label: "핵심 전략", icon: "rule", enabled: true },
  { slug: "peak", label: "고점 판단", icon: "trending_up", enabled: true },
  { slug: "patience", label: "인내 보유", icon: "self_improvement", enabled: false },
  { slug: "lessons", label: "오닐의 이야기", icon: "menu_book", enabled: false },
];

export function SellNav() {
  const pathname = usePathname();
  const root = "/stocks/canslim/sell";
  const isHome = pathname === root;

  return (
    <nav className="flex gap-1 bg-surface-container-low/70 backdrop-blur-md rounded-xl p-1.5 ghost-border overflow-x-auto scrollbar-hide">
      <Link
        href={root}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all flex-shrink-0 ${
          isHome
            ? "bg-[#ffb4ab]/15 text-[#ffb4ab]"
            : "text-on-surface-variant/70 hover:text-on-surface-variant hover:bg-surface-container/50"
        }`}
        title="매도 시스템 인덱스"
      >
        <span className="material-symbols-outlined text-base">sell</span>
        <span className="hidden sm:inline">매도 시스템</span>
      </Link>
      <span className="w-px bg-on-surface/10 my-1.5 mx-0.5" aria-hidden />
      {pages.map((p) => {
        const href = `${root}/${p.slug}`;
        const isActive = pathname === href || pathname.startsWith(href + "/");
        if (p.enabled) {
          return (
            <Link
              key={p.slug}
              href={href}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-all flex-shrink-0 ${
                isActive
                  ? "bg-[#ffb4ab]/15 text-[#ffb4ab] font-bold"
                  : "text-on-surface-variant/70 hover:text-on-surface-variant hover:bg-surface-container/50"
              }`}
              title={p.label}
            >
              <span className="material-symbols-outlined text-base">{p.icon}</span>
              <span className="hidden md:inline">{p.label}</span>
            </Link>
          );
        }
        return (
          <span
            key={p.slug}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs flex-shrink-0 opacity-40 cursor-not-allowed"
            title={`${p.label} — 향후 추가 예정`}
          >
            <span className="material-symbols-outlined text-base">{p.icon}</span>
            <span className="hidden md:inline">{p.label}</span>
          </span>
        );
      })}
    </nav>
  );
}
