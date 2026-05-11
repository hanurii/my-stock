"use client";

import { useMemo, useState } from "react";

interface Holding {
  code: string;
  name: string;
  sector: string | null;
  current_stkrt: number;
  first_rcept_dt: string;
  last_rcept_dt: string;
  stkrt_irds_recent: number;
  filings: number;
}

export interface Manager {
  manager_name: string;
  manager_name_normalized: string;
  category: "korean_am" | "global_am" | "pension";
  grade_1y: string;
  grade_3y: string;
  total_holdings: number;
  new_entries_1y_count: number;
  holdings: Holding[];
}

interface Props {
  managers: Manager[];
  universeSize: number;
  fundSnapshot: string | null;
}

const GROUP_ORDER: Array<{ key: string; title: string; description: string; matcher: (m: Manager) => boolean }> = [
  {
    key: "a+",
    title: "🥇 a+ 등급 (한국 Top 3)",
    description: "fundguide 1년 수익률 상위 1~3위",
    matcher: (m) => m.category === "korean_am" && m.grade_1y === "a+",
  },
  {
    key: "a",
    title: "🥈 a 등급 (한국 4~7위)",
    description: "fundguide 1년 수익률 4~7위",
    matcher: (m) => m.category === "korean_am" && m.grade_1y === "a",
  },
  {
    key: "a-",
    title: "🥉 a- 등급 (한국 8~10위)",
    description: "fundguide 1년 수익률 8~10위",
    matcher: (m) => m.category === "korean_am" && m.grade_1y === "a-",
  },
  {
    key: "unrated_kr",
    title: "🇰🇷 unrated 한국 운용사",
    description: "fundguide Top 10 미포함 — 등급 없음",
    matcher: (m) => m.category === "korean_am" && (m.grade_1y === "unrated" || !["a+", "a", "a-"].includes(m.grade_1y)),
  },
  {
    key: "global",
    title: "🌐 글로벌 운용사 (unrated)",
    description: "fundguide 미수록 — 한국 시장 비교 등급 불가, 단 5%+ 보유는 강한 시그널",
    matcher: (m) => m.category === "global_am",
  },
  {
    key: "pension",
    title: "💼 연기금",
    description: "국민연금 등 — 한국 최대 기관 투자자",
    matcher: (m) => m.category === "pension",
  },
];

function gradeBadgeColor(grade: string): string {
  switch (grade) {
    case "a+":
      return "#e9c176";
    case "a":
      return "#95d3ba";
    case "a-":
      return "#a8b5d0";
    default:
      return "var(--on-surface-variant)";
  }
}

function isNewEntry(h: Holding, oneYearAgoISO: string): boolean {
  return h.first_rcept_dt >= oneYearAgoISO;
}

export function ManagerPortfolios({ managers, universeSize, fundSnapshot }: Props) {
  const [expandedManager, setExpandedManager] = useState<Set<string>>(new Set());

  const oneYearAgoISO = useMemo(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 1);
    return d.toISOString().slice(0, 10);
  }, []);

  const grouped = useMemo(() => {
    return GROUP_ORDER.map((g) => ({
      ...g,
      items: managers.filter(g.matcher).sort((a, b) => b.total_holdings - a.total_holdings),
    }));
  }, [managers]);

  const toggle = (name: string) => {
    setExpandedManager((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <div className="space-y-8">
      <div className="text-[11px] text-on-surface-variant/60 flex flex-wrap gap-x-4 gap-y-1">
        <span>모집단 종목: {universeSize}</span>
        <span>매핑 운용사·연기금: {managers.length}</span>
        {fundSnapshot && <span>등급 스냅샷: {fundSnapshot}</span>}
      </div>

      {grouped.map((group) => (
        <section key={group.key}>
          <div className="flex items-baseline justify-between mb-2">
            <h3 className="text-base font-serif font-bold text-on-surface">
              {group.title} <span className="text-xs font-normal text-on-surface-variant/60">({group.items.length})</span>
            </h3>
            <p className="text-[11px] text-on-surface-variant/50">{group.description}</p>
          </div>
          {group.items.length === 0 ? (
            <p className="text-xs text-on-surface-variant/50 ghost-border rounded-lg p-3">
              모집단 종목에서 해당 카테고리 운용사 없음
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {group.items.map((m) => {
                const isExpanded = expandedManager.has(m.manager_name);
                const visibleHoldings = isExpanded ? m.holdings : m.holdings.slice(0, 5);
                const remaining = m.holdings.length - visibleHoldings.length;
                return (
                  <div
                    key={m.manager_name}
                    className="rounded-xl ghost-border p-4 bg-surface-container/30"
                  >
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="min-w-0">
                        <h4 className="text-sm font-medium text-on-surface truncate" title={m.manager_name}>
                          {m.manager_name}
                        </h4>
                        <div className="flex items-center gap-2 text-[10px] text-on-surface-variant/60 mt-0.5">
                          <span>{m.total_holdings}종목 보유</span>
                          {m.new_entries_1y_count > 0 && (
                            <>
                              <span>·</span>
                              <span className="text-primary">🆕 신규 {m.new_entries_1y_count}건</span>
                            </>
                          )}
                        </div>
                      </div>
                      {(m.grade_1y && m.grade_1y !== "unrated") && (
                        <span
                          className="text-[11px] font-mono px-2 py-0.5 rounded font-medium flex-shrink-0"
                          style={{
                            backgroundColor: `${gradeBadgeColor(m.grade_1y)}20`,
                            color: gradeBadgeColor(m.grade_1y),
                          }}
                        >
                          1y {m.grade_1y}
                        </span>
                      )}
                    </div>
                    <div className="space-y-1.5">
                      {visibleHoldings.map((h) => {
                        const isNew = isNewEntry(h, oneYearAgoISO);
                        return (
                          <div
                            key={h.code}
                            className="flex items-center gap-2 px-2 py-1 rounded bg-surface-container/40 text-[11px]"
                          >
                            <span className="font-mono text-[10px] text-on-surface-variant/50 w-12">{h.code}</span>
                            <span className="flex-1 truncate text-on-surface" title={h.name}>
                              {h.name}
                            </span>
                            {h.sector && (
                              <span className="text-[10px] text-on-surface-variant/50 truncate max-w-[80px]" title={h.sector}>
                                {h.sector}
                              </span>
                            )}
                            <span className="font-mono text-on-surface-variant font-medium">
                              {h.current_stkrt.toFixed(2)}%
                            </span>
                            {isNew && (
                              <span className="text-[9px] px-1 py-0.5 rounded bg-primary/10 text-primary flex-shrink-0">
                                🆕
                              </span>
                            )}
                          </div>
                        );
                      })}
                      {remaining > 0 && (
                        <button
                          onClick={() => toggle(m.manager_name)}
                          className="text-[11px] text-on-surface-variant/70 hover:text-on-surface px-2 py-1"
                        >
                          + {remaining}개 더 보기
                        </button>
                      )}
                      {isExpanded && m.holdings.length > 5 && (
                        <button
                          onClick={() => toggle(m.manager_name)}
                          className="text-[11px] text-on-surface-variant/70 hover:text-on-surface px-2 py-1"
                        >
                          접기
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
