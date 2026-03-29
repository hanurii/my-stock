"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/stocks/watchlist", label: "저평가 배당주", icon: "paid" },
  { href: "/stocks/growth", label: "저평가 성장주", icon: "trending_up" },
  { href: "/stocks/oil-expert", label: "오일전문가 포트폴리오", icon: "local_fire_department" },
  { href: "/stocks/berkshire", label: "버핏 포트폴리오", icon: "account_balance" },
];

export default function StocksLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="space-y-8">
      {/* Tab Navigation */}
      <div className="flex gap-1 bg-surface-container-low rounded-xl p-1.5 ghost-border">
        {tabs.map((tab) => {
          const isActive = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex items-center gap-2.5 px-5 py-3 rounded-lg text-sm font-medium transition-all duration-300 flex-1 justify-center ${
                isActive
                  ? "bg-primary/15 text-primary shadow-sm"
                  : "text-on-surface-variant/60 hover:text-on-surface-variant hover:bg-surface-container/50"
              }`}
            >
              <span className="material-symbols-outlined text-lg">{tab.icon}</span>
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden text-xs">{tab.label}</span>
            </Link>
          );
        })}
      </div>

      {children}
    </div>
  );
}
