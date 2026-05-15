import fs from "fs/promises";
import path from "path";
import Link from "next/link";
import { BearMarketBanner } from "./BearMarketBanner";
import type { SellSignalsOutput } from "./types";

async function getData(): Promise<SellSignalsOutput | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "sell-signals.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

interface PageInfo {
  slug: string;
  title: string;
  subtitle: string;
  desc: string;
  icon: string;
  enabled: boolean;
  bookCategories: string;
}

const PAGES: PageInfo[] = [
  {
    slug: "strategy",
    title: "핵심 매수·매도 전략",
    subtitle: "Strategy",
    desc: "손절 -7~8%, 익절 +20~25%, 8주 룰 예외, 추가 매수 +5% 한계. 종목별 진행률·룰 체크.",
    icon: "rule",
    enabled: true,
    bookCategories: "책 2·3·4 범주",
  },
  {
    slug: "peak",
    title: "고점 판단 시스템",
    subtitle: "Peak Detection",
    desc: "최후의 정점 11신호, 약세 징후, 지지선 붕괴, 분기 EPS 2분기 둔화. 50일·200일선 괴리율·거래량 z-score.",
    icon: "trending_up",
    enabled: false,
    bookCategories: "책 5·6·7·10 범주",
  },
  {
    slug: "patience",
    title: "인내심 갖고 보유",
    subtitle: "Patience",
    desc: "80% 종목 모양 돌파 후 되돌림, 10주선 두 번 견디기, +15%·+20% 본전 보호, 시장 추세 -10%+ 컨텍스트.",
    icon: "self_improvement",
    enabled: false,
    bookCategories: "책 8·9 범주",
  },
  {
    slug: "lessons",
    title: "오닐의 중요한 이야기",
    subtitle: "Lessons",
    desc: "매도 철학·심리, 두 가지 대전제, 매도 후 학습. 인용·격언 모음.",
    icon: "menu_book",
    enabled: false,
    bookCategories: "책 1·11 범주",
  },
];

function verdictBadgeStyle(v: string): { bg: string; fg: string; label: string } {
  switch (v) {
    case "SELL":
      return { bg: "#ffb4ab", fg: "#3a0f0a", label: "매도" };
    case "TRIM":
      return { bg: "#e8a25b", fg: "#3a1f0a", label: "비중 축소" };
    case "WATCH":
      return { bg: "#e8c875", fg: "#3a2e0a", label: "관찰" };
    case "BAD_ENTRY":
      return { bg: "#b09bce", fg: "#1f1535", label: "잘못 매수" };
    default:
      return { bg: "#95d3ba", fg: "#0f3a2a", label: "보유" };
  }
}

export default async function SellIndexPage() {
  const data = await getData();

  return (
    <div className="space-y-8">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          매도 시스템
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          오닐 책 매도 원칙 기반 보유 종목 매도 타이밍 판단. CAN SLIM 7원칙(매수) 보조 시스템.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5 leading-relaxed">
          &ldquo;제대로 사는 방법뿐만 아니라 제대로 파는 방법도 배워야 한다.&rdquo; — 윌리엄 오닐
        </p>
      </header>

      <BearMarketBanner />

      {/* 4개 페이지 카드 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-[#ffb4ab]">
            grid_view
          </span>
          4개 평가 페이지
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {PAGES.map((p) => {
            const passedVerdicts =
              p.slug === "strategy" && data
                ? data.holdings.reduce(
                    (acc, h) => {
                      acc[h.strategy_verdict.verdict] =
                        (acc[h.strategy_verdict.verdict] ?? 0) + 1;
                      return acc;
                    },
                    {} as Record<string, number>,
                  )
                : null;

            const content = (
              <>
                <div className="flex items-baseline gap-3 mb-2">
                  <span className="material-symbols-outlined text-2xl text-[#ffb4ab]">
                    {p.icon}
                  </span>
                  <div>
                    <p className="text-base font-medium text-on-surface">
                      {p.title}
                    </p>
                    <p className="text-[11px] text-on-surface-variant/60">
                      {p.subtitle} · {p.bookCategories}
                    </p>
                  </div>
                </div>
                <p className="text-xs text-on-surface-variant/80 leading-relaxed mb-3">
                  {p.desc}
                </p>
                {passedVerdicts && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {(
                      ["HOLD", "BAD_ENTRY", "WATCH", "TRIM", "SELL"] as const
                    ).map((v) => {
                      const count = passedVerdicts[v] ?? 0;
                      if (count === 0) return null;
                      const s = verdictBadgeStyle(v);
                      return (
                        <span
                          key={v}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium"
                          style={{ backgroundColor: s.bg, color: s.fg }}
                        >
                          {s.label} {count}
                        </span>
                      );
                    })}
                  </div>
                )}
                {p.enabled ? (
                  <p className="text-xs text-[#ffb4ab]/80 mt-2 flex items-center gap-1">
                    상세 보기
                    <span className="material-symbols-outlined text-sm">
                      arrow_forward
                    </span>
                  </p>
                ) : (
                  <p className="text-xs text-on-surface-variant/40 mt-2">
                    향후 추가 예정
                  </p>
                )}
              </>
            );

            return p.enabled ? (
              <Link
                key={p.slug}
                href={`/stocks/canslim/sell/${p.slug}`}
                className="block bg-surface-container-low rounded-xl ghost-border p-5 hover:bg-surface-container/50 transition-all"
              >
                {content}
              </Link>
            ) : (
              <div
                key={p.slug}
                className="bg-surface-container-low rounded-xl ghost-border p-5 opacity-60"
              >
                {content}
              </div>
            );
          })}
        </div>
      </section>

      {/* 보유 종목 verdict 요약 (strategy 페이지 기준) */}
      {data && data.holdings.length > 0 && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-4">
          <h3 className="text-sm font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-base text-primary">
              list_alt
            </span>
            보유 종목 한 줄 요약 — 핵심 전략 페이지 판정
          </h3>
          <div className="space-y-1.5 text-xs">
            {data.holdings.map((h) => {
              const s = verdictBadgeStyle(h.strategy_verdict.verdict);
              return (
                <div
                  key={h.code}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5 border-b border-on-surface/5 last:border-0"
                >
                  <span
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold w-[72px] justify-center"
                    style={{ backgroundColor: s.bg, color: s.fg }}
                  >
                    {s.label}
                  </span>
                  <span className="text-on-surface font-medium min-w-[100px]">
                    {h.name}
                  </span>
                  <span className="text-on-surface-variant/60">
                    {h.profit_pct >= 0 ? "+" : ""}
                    {h.profit_pct.toFixed(2)}%
                  </span>
                  <span className="text-on-surface-variant/60">
                    보유 {h.holding_weeks.toFixed(1)}주
                  </span>
                  <span className="text-on-surface-variant/70 flex-1 text-[11px]">
                    {h.strategy_verdict.reasons[0]}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="text-[10px] text-on-surface-variant/50 mt-3">
            생성일 {data.generated_at.slice(0, 19).replace("T", " ")} · 대상{" "}
            {data.holdings.length}종목
          </p>
        </section>
      )}
    </div>
  );
}
