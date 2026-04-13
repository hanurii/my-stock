"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useCallback } from "react";

const navItems = [
  { href: "/", label: "거시경제 리포트", icon: "auto_graph" },
  { href: "/stocks", label: "저평가 우량주", icon: "stars" },
  { href: "/journal", label: "매매일지", icon: "history_edu" },
  { href: "/calculator", label: "재무제표 계산기", icon: "calculate" },
  { href: "/bio", label: "기대 바이오주", icon: "biotech" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [scrollProgress, setScrollProgress] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? Math.min(scrollTop / docHeight, 1) : 0;
      setScrollProgress(progress);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  // Prevent body scroll when sidebar is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const toggleSidebar = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 md:hidden flex items-center justify-center w-10 h-10 rounded-lg bg-surface-container-high/90 backdrop-blur-sm border border-outline-variant/20 text-primary transition-colors hover:bg-surface-container-highest"
        aria-label={isOpen ? "메뉴 닫기" : "메뉴 열기"}
      >
        <span className="material-symbols-outlined text-xl">
          {isOpen ? "close" : "menu"}
        </span>
      </button>

      {/* Overlay (mobile only) */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full w-64 flex flex-col z-40 bg-surface border-r border-outline-variant/15 transition-transform duration-300 ease-in-out md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="p-8">
          <h1 className="text-xl font-bold font-serif text-primary tracking-tight">
            My Stock
          </h1>
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mt-1">
            Private Investment Platform
          </p>
        </div>

        <nav className="flex-1 mt-4">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const fillPercent = isActive ? scrollProgress * 100 : 0;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex items-center gap-4 py-4 px-6 transition-all duration-300 overflow-hidden ${
                  isActive
                    ? "text-primary border-l-2 border-primary"
                    : "text-primary-dim/70 hover:bg-surface-container-low hover:text-primary border-l-2 border-transparent"
                }`}
              >
                {/* Fill background - flows left to right */}
                {isActive && (
                  <div
                    className="absolute inset-0 transition-all duration-100 ease-out"
                    style={{
                      background: "linear-gradient(135deg, rgba(233, 193, 118, 0.25) 0%, rgba(157, 124, 57, 0.15) 100%)",
                      clipPath: `inset(0 ${100 - fillPercent}% 0 0)`,
                    }}
                  />
                )}
                {/* Left edge glow at fill position */}
                {isActive && fillPercent > 0 && (
                  <div
                    className="absolute top-0 bottom-0 w-[2px] transition-all duration-100 ease-out"
                    style={{
                      left: `${fillPercent}%`,
                      background: "rgba(233, 193, 118, 0.6)",
                      boxShadow: "0 0 8px 2px rgba(233, 193, 118, 0.3)",
                    }}
                  />
                )}
                <span className="material-symbols-outlined text-xl relative z-10">
                  {item.icon}
                </span>
                <span className="text-sm font-medium relative z-10">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto p-6 border-t border-outline-variant/15">
          <p className="text-[10px] text-on-surface-variant leading-relaxed">
            ⚠️ 본 플랫폼은 투자 권유가 아닌
            <br />
            거시경제 학습 목적입니다.
          </p>
        </div>
      </aside>
    </>
  );
}
