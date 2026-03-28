import fs from "fs";
import path from "path";
import { Collapsible } from "@/components/Collapsible";
import { ScoreDetails } from "@/components/ScoreDetails";
import { RankChange, GradeChangeBadge, ScoreChangeComment } from "@/components/RankChange";
import {
  scoreDomestic,
  getGradeColor,
  getGradeLabel,
  DOMESTIC_FRAMEWORK,
  type DomesticStockInput,
  type ScoredResult,
} from "@/lib/scoring";
import { DomesticScoringCriteria } from "@/components/ScoringCriteria";
import { formatScoredAt } from "@/lib/format";

interface WatchlistStock extends DomesticStockInput {
  tier?: string;
  catalyst?: string;
  a_grade_price?: number;
  current_price_at_scoring?: number;
}

interface WatchlistData {
  stocks: WatchlistStock[];
  excluded: { name: string; reason: string }[];
  tiers: Record<string, { label: string; desc: string }>;
  market_insight: string;
}

type ScoredStock = WatchlistStock & ScoredResult;

function getWatchlistData(): { stocks: ScoredStock[]; excluded: WatchlistData["excluded"]; tiers: WatchlistData["tiers"]; market_insight: string } | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "watchlist.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    const data = JSON.parse(raw) as WatchlistData;

    const stocks: ScoredStock[] = data.stocks
      .map((s) => ({ ...s, ...scoreDomestic(s) }))
      .sort((a, b) => b.score - a.score);

    return { stocks, excluded: data.excluded, tiers: data.tiers, market_insight: data.market_insight };
  } catch {
    return null;
  }
}

function getTierLabel(tier?: string): string | null {
  const labels: Record<string, string> = {
    tier1: "때를 기다리는 종목",
    tier2: "변화를 감시하는 종목",
    tier3: "장기 모니터링",
  };
  return tier ? labels[tier] || null : null;
}

// ── 공통 StockCard 컴포넌트 (A/B/C 등급 공용) ──

function StockCard({ stock, globalRank, framework }: {
  stock: ScoredStock;
  globalRank: number;
  framework: typeof DOMESTIC_FRAMEWORK;
}) {
  const color = getGradeColor(stock.grade);
  const tierLabel = getTierLabel(stock.tier);
  const cat1Pct = (stock.cat1 / framework.category1.max_score) * 100;
  const cat2Pct = (stock.cat2 / framework.category2.max_score) * 100;
  const cat3Pct = (stock.cat3 / framework.category3.max_score) * 100;

  return (
    <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
      <div className="p-4 sm:p-6">
        <ScoreChangeComment score={stock.score} previousScore={stock.previous_score} grade={stock.grade} details={stock.details} previousDetails={stock.previous_details} />
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="text-center w-8">
              <span className="text-2xl font-serif font-bold" style={{ color }}>{globalRank}</span>
              <RankChange currentRank={globalRank} previousRank={stock.previous_rank} />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="text-base sm:text-lg font-medium text-on-surface">{stock.name}</h4>
                <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>{stock.grade}</span>
                {stock.estimated && <span className="text-xs text-on-surface-variant/40">추정치</span>}
                {tierLabel && <span className="text-xs text-on-surface-variant/50">{tierLabel}</span>}
              </div>
              <p className="text-sm text-on-surface-variant">
                {stock.code} · {stock.sector}
                <span className="text-xs text-on-surface-variant/40 ml-2">{formatScoredAt(stock.scored_at)} 채점</span>
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-2xl sm:text-3xl font-serif font-bold" style={{ color }}>{stock.score}</p>
            <p className="text-xs text-on-surface-variant">/100점</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-4">
          {[
            { label: framework.category1.name.split("/")[0], score: stock.cat1, max: framework.category1.max_score, pct: cat1Pct },
            { label: "주주환원", score: stock.cat2, max: framework.category2.max_score, pct: cat2Pct },
            { label: "성장/경쟁력", score: stock.cat3, max: framework.category3.max_score, pct: cat3Pct },
          ].map((cat) => (
            <div key={cat.label} className="bg-surface-container/50 rounded-lg p-2 sm:p-3">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-1.5 gap-0.5">
                <span className="text-[10px] sm:text-xs text-on-surface-variant">{cat.label}</span>
                <span className="text-xs sm:text-sm font-mono text-on-surface">{cat.score}/{cat.max}</span>
              </div>
              <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${cat.pct}%`, backgroundColor: color }} />
              </div>
            </div>
          ))}
        </div>

        <div className="flex gap-4 mb-3 text-sm">
          <span className="text-on-surface-variant">
            PER <span className="font-mono text-on-surface">{stock.per != null ? `${stock.per}x` : "적자"}</span>
          </span>
          <span className="text-on-surface-variant">
            PBR <span className="font-mono text-on-surface">{stock.pbr}x</span>
          </span>
          <span className="text-on-surface-variant">
            배당 <span className="font-mono text-on-surface">{stock.dividend_yield}%</span>
          </span>
        </div>

        <p className="text-sm text-on-surface-variant leading-relaxed">{stock.highlights}</p>

        {stock.catalyst && (
          <div className="mt-3 flex items-start gap-2">
            <span className="material-symbols-outlined text-primary text-sm mt-0.5">bolt</span>
            <p className="text-sm text-primary/80">{stock.catalyst}</p>
          </div>
        )}

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

        <ScoreDetails details={stock.details} />
      </div>
    </div>
  );
}

export default function WatchlistPage() {
  const data = getWatchlistData();
  const framework = DOMESTIC_FRAMEWORK;

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
      </div>
    );
  }

  const { stocks, excluded } = data;

  // 등급별 분류 (한 번만 계산)
  const abStocks: ScoredStock[] = [];
  const cStocks: ScoredStock[] = [];
  const dStocks: ScoredStock[] = [];
  const gradeCount: Record<string, number> = { A: 0, B: 0, C: 0, D: 0 };
  const visibleStocks: ScoredStock[] = [];
  const hiddenCount = stocks.filter(s => s.score < 45).length;

  for (const s of stocks) {
    if (gradeCount[s.grade] !== undefined) gradeCount[s.grade]++;
    if (s.grade === "A" || s.grade === "B") abStocks.push(s);
    else if (s.grade === "C") cStocks.push(s);
    else dStocks.push(s);
    if (s.score >= 45) visibleStocks.push(s);
  }

  const calculatedAt = formatScoredAt(new Date().toISOString().slice(0, 10));

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Undervalued Dividend Stocks
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          저평가 배당주
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          3대 카테고리 점수 시스템 (100점 만점)
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1.5">
          점수 갱신: {calculatedAt}
        </p>
      </section>

      {/* Scoring Framework */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {[
          { key: "category1" as const, icon: "analytics" },
          { key: "category2" as const, icon: "volunteer_activism" },
          { key: "category3" as const, icon: "trending_up" },
        ].map(({ key, icon }) => {
          const cat = framework[key];
          return (
            <div key={key} className="bg-surface-container-low rounded-xl p-5 ghost-border">
              <div className="flex items-center gap-3 mb-2">
                <span className="material-symbols-outlined text-primary text-lg">{icon}</span>
                <h4 className="text-sm font-serif text-on-surface">{cat.name}</h4>
              </div>
              <p className="text-2xl font-serif text-primary mb-2">{cat.max_score}<span className="text-sm text-on-surface-variant">점</span></p>
              <div className="flex flex-wrap gap-1.5">
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

      {/* Scoring Criteria */}
      <section>
        <DomesticScoringCriteria />
      </section>

      {/* Grade Distribution */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <h3 className="text-base font-serif text-on-surface mb-4">등급 분포</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {(["A", "B", "C", "D"] as const).map((grade) => {
            const count = gradeCount[grade];
            const color = getGradeColor(grade);
            return (
              <div key={grade} className="text-center p-4 rounded-xl ghost-border bg-surface-container/30">
                <p className="text-3xl font-serif font-bold" style={{ color }}>{grade}</p>
                <p className="text-2xl font-mono text-on-surface mt-1">{count}<span className="text-sm text-on-surface-variant">개</span></p>
                <p className="text-xs text-on-surface-variant mt-1">{getGradeLabel(grade)}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Quick Summary Table */}
      <section className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="p-6 pb-3">
          <h3 className="text-base font-serif text-on-surface">전체 종목 한눈에 보기</h3>
          {hiddenCount > 0 && (
            <p className="text-xs text-on-surface-variant/40 mt-1">45점 미만 {hiddenCount}개 종목 생략</p>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                <th className="text-center px-3 pb-3 font-normal w-10">#</th>
                <th className="text-left px-3 pb-3 font-normal">종목</th>
                <th className="text-left px-3 pb-3 font-normal">섹터</th>
                <th className="text-center px-3 pb-3 font-normal">등급</th>
                <th className="text-right px-3 pb-3 font-normal">점수</th>
                <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">PER</th>
                <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">PBR</th>
                <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">배당률</th>
                <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">{framework.category1.name.split("/")[0]}</th>
                <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">주주환원</th>
                <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">성장</th>
                <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">채점일</th>
              </tr>
            </thead>
            <tbody>
              {visibleStocks.map((stock, i) => {
                const color = getGradeColor(stock.grade);
                const rank = i + 1;
                return (
                  <tr key={stock.code} className={`hover:bg-surface-container/30 transition-colors ${rank === 1 ? "bg-primary/5" : ""}`}>
                    <td className="text-center px-3 py-2.5 font-mono" style={{ color }}>{rank}</td>
                    <td className="px-3 py-2.5 font-medium text-on-surface">
                      <span className="inline-flex items-center gap-1.5 flex-wrap">
                        {stock.name}
                        {stock.estimated && <span className="text-[10px] text-on-surface-variant/40">~</span>}
                        <RankChange currentRank={rank} previousRank={stock.previous_rank} />
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-on-surface-variant">{stock.sector}</td>
                    <td className="text-center px-3 py-2.5">
                      <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>{stock.grade}</span>
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono font-bold" style={{ color }}>{stock.score}</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">
                      {stock.per != null ? `${stock.per}x` : "적자"}
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">{stock.pbr}x</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">{stock.dividend_yield}%</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden lg:table-cell">{stock.cat1}/{framework.category1.max_score}</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden lg:table-cell">{stock.cat2}/{framework.category2.max_score}</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden lg:table-cell">{stock.cat3}/{framework.category3.max_score}</td>
                    <td className="text-right px-3 py-2.5 text-xs text-on-surface-variant/50 hidden lg:table-cell">{formatScoredAt(stock.scored_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Stock Rankings */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">종목 순위</h3>
        <p className="text-sm text-on-surface-variant mb-6">점수 높은 순 · 자동 계산</p>

        {/* A/B 등급 */}
        <div className="space-y-4">
          {abStocks.map((stock) => {
            const globalRank = stocks.indexOf(stock) + 1;
            return <StockCard key={stock.code} stock={stock} globalRank={globalRank} framework={framework} />;
          })}
        </div>

        {/* C 등급 */}
        {cStocks.length > 0 && (
          <div className="mt-6">
            <Collapsible title={`C등급 — 워치리스트 (${cStocks.length}개)`}>
              <div className="space-y-4">
                {cStocks.map((stock) => {
                  const globalRank = stocks.indexOf(stock) + 1;
                  return <StockCard key={stock.code} stock={stock} globalRank={globalRank} framework={framework} />;
                })}
              </div>
            </Collapsible>
          </div>
        )}

        {/* D 등급 */}
        {dStocks.length > 0 && (
          <div className="mt-6">
            <Collapsible title={`D등급 — 투자 부적합 (${dStocks.length}개)`}>
              <div className="space-y-4">
                {dStocks.map((stock) => {
                  const color = getGradeColor(stock.grade);
                  const globalRank = stocks.indexOf(stock) + 1;

                  return (
                    <div key={stock.code} className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
                      <div className="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <div className="flex items-center gap-4">
                          <span className="text-xl font-serif font-bold w-8 shrink-0" style={{ color }}>{globalRank}</span>
                          <div>
                            <h4 className="text-base font-medium text-on-surface inline-flex items-center gap-1.5 flex-wrap">
                              {stock.name}
                              <RankChange currentRank={globalRank} previousRank={stock.previous_rank} />
                              <GradeChangeBadge grade={stock.grade} score={stock.score} previousScore={stock.previous_score} compact />
                            </h4>
                            <p className="text-sm text-on-surface-variant">
                              {stock.code} · {stock.sector}
                              <span className="text-xs text-on-surface-variant/40 ml-2">{formatScoredAt(stock.scored_at)}</span>
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 ml-12 sm:ml-0">
                          <p className="text-sm text-on-surface-variant/60 max-w-sm sm:text-right">{stock.highlights}</p>
                          <p className="text-2xl font-serif font-bold shrink-0" style={{ color }}>{stock.score}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Collapsible>
          </div>
        )}
      </section>

      {/* Excluded */}
      <section>
        <Collapsible title="제외 종목 (밸류 트랩 또는 펀더멘탈 약화)">
          <div className="space-y-2">
            {excluded.map((stock) => (
              <div key={stock.name} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-4 p-4 bg-surface-container/30 rounded-lg">
                <span className="text-base text-on-surface shrink-0">{stock.name}</span>
                <p className="text-sm text-on-surface-variant/60 sm:text-right">{stock.reason}</p>
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
            <strong className="text-on-surface">핵심 공식:</strong> 저평가 배당주 = 저PER + 저PBR + 고ROE + 주주환원 + 안전마진.
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
