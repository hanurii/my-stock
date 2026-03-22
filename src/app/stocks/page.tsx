import fs from "fs";
import path from "path";
import { Collapsible } from "@/components/Collapsible";

interface StockEntry {
  code: string;
  name: string;
  sector: string;
  score: number;
  grade: string;
  tier?: string;
  cat1: number;
  cat2: number;
  cat3: number;
  highlights: string;
  a_grade_price?: number;
  current_price_at_scoring?: number;
  catalyst?: string;
}

interface WatchlistData {
  generated_at: string;
  framework: {
    category1: { name: string; max_score: number; key_metrics: string[] };
    category2: { name: string; max_score: number; key_metrics: string[] };
    category3: { name: string; max_score: number; key_metrics: string[] };
  };
  grades: Record<string, { min: number; label: string; color: string }>;
  stocks: StockEntry[];
  excluded: { name: string; score: number; reason: string }[];
  market_insight: string;
}

function getWatchlistData(): WatchlistData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "watchlist.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as WatchlistData;
  } catch {
    return null;
  }
}

function getGradeColor(grade: string): string {
  const colors: Record<string, string> = {
    A: "#95d3ba", B: "#6ea8fe", C: "#e9c176", D: "#ffb4ab",
  };
  return colors[grade] || "#909097";
}

function getTierLabel(tier?: string): string | null {
  const labels: Record<string, string> = {
    tier1: "때를 기다리는 종목",
    tier2: "변화를 감시하는 종목",
    tier3: "장기 모니터링",
  };
  return tier ? labels[tier] || null : null;
}

export default function StocksPage() {
  const data = getWatchlistData();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
      </div>
    );
  }

  const { framework, stocks, excluded, market_insight } = data;

  // 등급별 분류
  const gradeGroups: Record<string, StockEntry[]> = { A: [], B: [], C: [], D: [] };
  stocks.forEach((s) => {
    if (gradeGroups[s.grade]) gradeGroups[s.grade].push(s);
  });

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Undervalued Stocks
        </p>
        <h2 className="text-4xl font-serif font-bold text-on-surface tracking-tight">
          저평가 우량주
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          {data.generated_at} 기준 · 3대 카테고리 점수 시스템 (100점 만점)
        </p>
      </section>

      {/* Market Insight */}
      <section className="glass-card rounded-xl p-8 ghost-border">
        <div className="flex items-center gap-3 mb-4">
          <span className="material-symbols-outlined text-primary text-2xl">auto_awesome</span>
          <h3 className="text-xl font-serif text-on-surface">시장 판단</h3>
        </div>
        <p className="text-base text-on-surface-variant leading-relaxed">{market_insight}</p>
      </section>

      {/* Scoring Framework */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {[
          { key: "category1", icon: "analytics" },
          { key: "category2", icon: "volunteer_activism" },
          { key: "category3", icon: "trending_up" },
        ].map(({ key, icon }) => {
          const cat = framework[key as keyof typeof framework];
          return (
            <div key={key} className="bg-surface-container-low rounded-xl p-6 ghost-border">
              <div className="flex items-center gap-3 mb-3">
                <span className="material-symbols-outlined text-primary">{icon}</span>
                <h4 className="text-base font-serif text-on-surface">{cat.name}</h4>
              </div>
              <p className="text-3xl font-serif text-primary mb-2">{cat.max_score}<span className="text-base text-on-surface-variant">점</span></p>
              <div className="flex flex-wrap gap-1.5 mt-3">
                {cat.key_metrics.map((m: string) => (
                  <span key={m} className="text-xs bg-surface-container-high px-2 py-0.5 rounded text-on-surface-variant">
                    {m}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </section>

      {/* Grade Distribution */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <h3 className="text-base font-serif text-on-surface mb-4">등급 분포</h3>
        <div className="grid grid-cols-4 gap-4">
          {(["A", "B", "C", "D"] as const).map((grade) => {
            const count = gradeGroups[grade].length;
            const color = getGradeColor(grade);
            const labels: Record<string, string> = { A: "강력 매수", B: "매수 검토", C: "워치리스트", D: "투자 부적합" };
            return (
              <div key={grade} className="text-center p-4 rounded-xl ghost-border bg-surface-container/30">
                <p className="text-3xl font-serif font-bold" style={{ color }}>{grade}</p>
                <p className="text-2xl font-mono text-on-surface mt-1">{count}<span className="text-sm text-on-surface-variant">개</span></p>
                <p className="text-xs text-on-surface-variant mt-1">{labels[grade]}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Stock Rankings */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">종목 순위</h3>
        <p className="text-sm text-on-surface-variant mb-6">점수 높은 순 · 클릭하면 상세 정보</p>

        <div className="space-y-4">
          {stocks.map((stock, rank) => {
            const color = getGradeColor(stock.grade);
            const tierLabel = getTierLabel(stock.tier);
            const cat1Pct = (stock.cat1 / framework.category1.max_score) * 100;
            const cat2Pct = (stock.cat2 / framework.category2.max_score) * 100;
            const cat3Pct = (stock.cat3 / framework.category3.max_score) * 100;

            return (
              <div key={stock.code} className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <span className="text-2xl font-serif font-bold w-8" style={{ color }}>
                        {rank + 1}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-lg font-medium text-on-surface">{stock.name}</h4>
                          <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>
                            {stock.grade}
                          </span>
                          {tierLabel && (
                            <span className="text-xs text-on-surface-variant/50">{tierLabel}</span>
                          )}
                        </div>
                        <p className="text-sm text-on-surface-variant">{stock.code} · {stock.sector}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-serif font-bold" style={{ color }}>{stock.score}</p>
                      <p className="text-xs text-on-surface-variant">/100점</p>
                    </div>
                  </div>

                  {/* Category Scores */}
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    {[
                      { label: "저평가", score: stock.cat1, max: framework.category1.max_score, pct: cat1Pct },
                      { label: "주주환원", score: stock.cat2, max: framework.category2.max_score, pct: cat2Pct },
                      { label: "성장/경쟁력", score: stock.cat3, max: framework.category3.max_score, pct: cat3Pct },
                    ].map((cat) => (
                      <div key={cat.label} className="bg-surface-container/50 rounded-lg p-3">
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="text-xs text-on-surface-variant">{cat.label}</span>
                          <span className="text-sm font-mono text-on-surface">{cat.score}/{cat.max}</span>
                        </div>
                        <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${cat.pct}%`, backgroundColor: color }} />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Highlights */}
                  <p className="text-sm text-on-surface-variant leading-relaxed">{stock.highlights}</p>

                  {/* Catalyst */}
                  {stock.catalyst && (
                    <div className="mt-3 flex items-start gap-2">
                      <span className="material-symbols-outlined text-primary text-sm mt-0.5">bolt</span>
                      <p className="text-sm text-primary/80">{stock.catalyst}</p>
                    </div>
                  )}

                  {/* A등급 진입 가격 */}
                  {stock.a_grade_price && (
                    <div className="mt-3 flex items-center gap-2">
                      <span className="material-symbols-outlined text-[#95d3ba] text-sm">flag</span>
                      <p className="text-sm text-[#95d3ba]">
                        A등급 예상 진입가: {stock.a_grade_price.toLocaleString()}원
                        {stock.current_price_at_scoring && (
                          <span className="text-on-surface-variant/50 ml-1">
                            (분석 당시 {stock.current_price_at_scoring.toLocaleString()}원 대비 -{Math.round((1 - stock.a_grade_price / stock.current_price_at_scoring) * 100)}%)
                          </span>
                        )}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Excluded */}
      <section>
        <Collapsible title="제외 종목 (밸류 트랩 또는 펀더멘탈 약화)">
          <div className="space-y-2">
            {excluded.map((stock) => (
              <div key={stock.name} className="flex items-center justify-between p-4 bg-surface-container/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-[#ffb4ab]">{stock.score}점</span>
                  <span className="text-base text-on-surface">{stock.name}</span>
                </div>
                <p className="text-sm text-on-surface-variant/60 max-w-md text-right">{stock.reason}</p>
              </div>
            ))}
          </div>
        </Collapsible>
      </section>

      {/* Guide */}
      <section className="bg-surface-container-low rounded-xl p-8 ghost-border">
        <h3 className="text-lg font-serif text-on-surface mb-5">점수 시스템 해석</h3>
        <div className="space-y-4 text-base text-on-surface-variant leading-relaxed">
          <p>
            <strong className="text-on-surface">핵심 공식:</strong> 저평가 우량주 = 저PER + 저PBR + 고ROE + 주주환원 + 안전마진.
            반면 저PER + 저PBR + 저ROE + 매출감소 = 가치함정 (회피).
          </p>
          <p>
            <strong className="text-on-surface">A등급은 아무 때나 나오지 않습니다.</strong> 시장이 전반적으로 오른 상태에서는 A등급이 0개입니다.
            시장 조정(20~35% 하락) 시 B/A등급 진입 종목이 나타나므로, 워치리스트를 유지하며 기다리는 것이 전략입니다.
          </p>
          <p>
            <strong className="text-on-surface">분기별 재점검:</strong> 실적 시즌마다 EPS 업데이트, 자사주 소각 여부, 배당 변화를 반영하여 점수를 갱신합니다.
          </p>
        </div>
      </section>
    </div>
  );
}
