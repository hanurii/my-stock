import fs from "fs/promises";
import path from "path";
import {
  scoreDomestic,
  scoreOverseas,
  getGradeColor,
  getGradeLabel,
  DOMESTIC_FRAMEWORK,
  OVERSEAS_FRAMEWORK,
  type DomesticStockInput,
  type OverseasStockInput,
  type ScoredResult,
} from "@/lib/scoring";
import { formatScoredAt } from "@/lib/format";
import { DomesticScoringCriteria, OverseasScoringCriteria } from "@/components/ScoringCriteria";
import { ScoreDetails } from "@/components/ScoreDetails";
import { Collapsible } from "@/components/Collapsible";
import { RankChange, ScoreChangeComment } from "@/components/RankChange";
import { SectorPieChart } from "@/components/SectorPieChart";
import { getStockTrend, type RankHistory } from "@/lib/rank-history";
import { RankTrendSparkline } from "@/components/RankTrendSparkline";


type ScoredDomestic = DomesticStockInput & ScoredResult;
type ScoredOverseas = OverseasStockInput & ScoredResult;

interface OilExpertData {
  owner: string;
  domestic: DomesticStockInput[];
  overseas: OverseasStockInput[];
  insights: { portfolio_strategy: string };
}

async function getData(): Promise<{ domestic: ScoredDomestic[]; overseas: ScoredOverseas[]; insights: OilExpertData["insights"] } | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "oil-expert-watchlist.json");
    const raw = await fs.readFile(filePath, "utf-8");
    const data = JSON.parse(raw) as OilExpertData;

    const domestic: ScoredDomestic[] = data.domestic
      .map((s) => ({ ...s, ...scoreDomestic(s) }))
      .sort((a, b) => b.score - a.score);

    const overseas: ScoredOverseas[] = data.overseas
      .map((s) => ({ ...s, ...scoreOverseas(s) }))
      .sort((a, b) => b.score - a.score);

    return { domestic, overseas, insights: data.insights };
  } catch {
    return null;
  }
}

type AnyScored = (ScoredDomestic | ScoredOverseas) & { country?: string };

function StockTable({ stocks, framework, showCountry, rankHistory }: {
  stocks: AnyScored[];
  framework: typeof DOMESTIC_FRAMEWORK | typeof OVERSEAS_FRAMEWORK;
  showCountry?: boolean;
  rankHistory: RankHistory | null;
}) {
  const hiddenCount = stocks.filter(s => s.score < 45).length;
  const visibleStocks = stocks.filter(s => s.score >= 45);
  return (
    <div>
      {hiddenCount > 0 && (
        <div className="px-6 pb-2">
          <p className="text-xs text-on-surface-variant/40">45점 미만 {hiddenCount}개 종목 생략</p>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
              <th className="text-center px-3 pb-3 font-normal w-10">#</th>
              <th className="text-left px-3 pb-3 font-normal">종목</th>
              <th className="text-center px-2 pb-3 font-normal hidden sm:table-cell">추세</th>
              {showCountry && <th className="text-left px-3 pb-3 font-normal hidden md:table-cell">국가</th>}
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
                  <td className="text-center px-2 py-2.5 hidden sm:table-cell">
                    <RankTrendSparkline trend={getStockTrend(rankHistory, stock.code)} stockName={stock.name} totalStocks={visibleStocks.length} />
                  </td>
                  {showCountry && <td className="px-3 py-2.5 text-on-surface-variant hidden md:table-cell">{stock.country}</td>}
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
    </div>
  );
}

function StockCards({ stocks, framework }: {
  stocks: AnyScored[];
  framework: typeof DOMESTIC_FRAMEWORK | typeof OVERSEAS_FRAMEWORK;
}) {
  return (
    <div className="space-y-4">
      {stocks.map((stock, rank) => {
        const color = getGradeColor(stock.grade);
        const cat1Pct = (stock.cat1 / framework.category1.max_score) * 100;
        const cat2Pct = (stock.cat2 / framework.category2.max_score) * 100;
        const cat3Pct = (stock.cat3 / framework.category3.max_score) * 100;

        return (
          <div key={stock.code} className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
            <div className="p-4 sm:p-6">
              <ScoreChangeComment score={stock.score} previousScore={stock.previous_score} grade={stock.grade} details={stock.details} previousDetails={stock.previous_details} scoreHistory={stock.score_history} />
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className="text-center w-8">
                    <span className="text-2xl font-serif font-bold" style={{ color }}>{rank + 1}</span>
                    <RankChange currentRank={rank + 1} previousRank={stock.previous_rank} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-base sm:text-lg font-medium text-on-surface">{stock.name}</h4>
                      <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>{stock.grade}</span>
                      {stock.estimated && <span className="text-xs text-on-surface-variant/40">추정치</span>}
                    </div>
                    <p className="text-sm text-on-surface-variant">
                      {stock.code} · {stock.sector}
                      {stock.country && <span> · {stock.country}</span>}
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

              <ScoreDetails details={stock.details} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function GradeDistribution({ stocks }: { stocks: AnyScored[] }) {
  const gradeGroups: Record<string, AnyScored[]> = { A: [], B: [], C: [], D: [] };
  stocks.forEach((s) => {
    if (gradeGroups[s.grade]) gradeGroups[s.grade].push(s);
  });

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {(["A", "B", "C", "D"] as const).map((grade) => {
        const count = gradeGroups[grade].length;
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
  );
}

function buildSectorData(stocks: AnyScored[]) {
  const sectorMap = new Map<string, { count: number; names: string[] }>();
  stocks.forEach((s) => {
    const sector = s.sector.replace("(우)", "");
    const prev = sectorMap.get(sector) || { count: 0, names: [] };
    prev.count += 1;
    prev.names.push(s.name);
    sectorMap.set(sector, prev);
  });
  const total = stocks.length;
  return Array.from(sectorMap.entries())
    .map(([sector, { count, names }]) => ({
      sector,
      value: count,
      weight_pct: total > 0 ? (count / total) * 100 : 0,
      count,
      names,
    }))
    .sort((a, b) => b.count - a.count);
}

export default async function OilExpertPage() {
  const data = await getData();

  let rankHistoryDomestic: RankHistory | null = null;
  let rankHistoryOverseas: RankHistory | null = null;
  try {
    rankHistoryDomestic = JSON.parse(await fs.readFile(path.join(process.cwd(), "public", "data", "rank-history-oil-domestic.json"), "utf-8"));
  } catch { /* */ }
  try {
    rankHistoryOverseas = JSON.parse(await fs.readFile(path.join(process.cwd(), "public", "data", "rank-history-oil-overseas.json"), "utf-8"));
  } catch { /* */ }

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
      </div>
    );
  }

  const { domestic, overseas, insights } = data;
  const allStocksCount = domestic.length + overseas.length;

  const domesticAB = domestic.filter(s => s.grade === "A" || s.grade === "B");
  const domesticC = domestic.filter(s => s.grade === "C");
  const overseasAB = overseas.filter(s => s.grade === "A" || s.grade === "B");
  const overseasC = overseas.filter(s => s.grade === "C");

  const calculatedAt = formatScoredAt(
    [...domestic, ...overseas].reduce((latest, s) => (s.scored_at > latest ? s.scored_at : latest), domestic[0]?.scored_at ?? "")
  );

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Oil Expert Portfolio
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          오일전문가 포트폴리오
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          국내 {domestic.length}종목 + 해외 {overseas.length}종목 = 총 {allStocksCount}종목
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1.5">
          점수 갱신: {calculatedAt}
        </p>
      </section>

      {/* Portfolio Strategy */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-primary text-xl mt-0.5">psychology</span>
          <div>
            <h3 className="text-base font-serif text-on-surface mb-2">포트폴리오 전략</h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">{insights.portfolio_strategy}</p>
          </div>
        </div>
      </section>

      {/* ────────────── 국내 종목 ────────────── */}
      <section className="space-y-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="material-symbols-outlined text-primary">flag</span>
            <h3 className="text-2xl font-serif text-on-surface tracking-tight">국내 종목</h3>
          </div>
          <p className="text-sm text-on-surface-variant ml-9">
            {domestic.length}종목 · 점수 갱신: {calculatedAt}
          </p>
        </div>

        {/* Domestic Scoring Framework */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            { key: "category1" as const, icon: "analytics" },
            { key: "category2" as const, icon: "volunteer_activism" },
            { key: "category3" as const, icon: "trending_up" },
          ].map(({ key, icon }) => {
            const cat = DOMESTIC_FRAMEWORK[key];
            return (
              <div key={key} className="bg-surface-container-low rounded-xl p-5 ghost-border">
                <div className="flex items-center gap-3 mb-2">
                  <span className="material-symbols-outlined text-primary text-lg">{icon}</span>
                  <h4 className="text-sm font-serif text-on-surface">{cat.name}</h4>
                </div>
                <p className="text-2xl font-serif text-primary mb-2">{cat.max_score}<span className="text-sm text-on-surface-variant">점</span></p>
                <div className="flex flex-wrap gap-1.5">
                  {cat.key_metrics.map((m: string) => (
                    <span key={m} className="text-xs bg-surface-container-high px-2 py-0.5 rounded text-on-surface-variant">{m}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <DomesticScoringCriteria />

        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <h3 className="text-base font-serif text-on-surface mb-4">등급 분포 — 국내</h3>
          <GradeDistribution stocks={domestic} />
        </div>

        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <h3 className="text-base font-serif text-on-surface mb-4">섹터별 분포</h3>
          <SectorPieChart
            sectors={buildSectorData(domestic)}
            totalValue={domestic.length}
            currency="count"
          />
        </div>

        <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
          <div className="p-6 pb-3">
            <h3 className="text-base font-serif text-on-surface">국내 전체 종목</h3>
          </div>
          <StockTable stocks={domestic} framework={DOMESTIC_FRAMEWORK} rankHistory={rankHistoryDomestic} />
        </div>

        {/* Domestic A/B Cards */}
        {domesticAB.length > 0 && (
          <div>
            <h4 className="text-lg font-serif text-on-surface mb-4">A/B 등급 — 매수 검토 대상</h4>
            <StockCards stocks={domesticAB} framework={DOMESTIC_FRAMEWORK} />
          </div>
        )}

        {/* Domestic C Cards */}
        {domesticC.length > 0 && (
          <Collapsible title={`C등급 — 워치리스트 (${domesticC.length}개)`}>
            <StockCards stocks={domesticC} framework={DOMESTIC_FRAMEWORK} />
          </Collapsible>
        )}
      </section>

      {/* ────────────── 해외 종목 ────────────── */}
      <section className="space-y-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="material-symbols-outlined text-primary">public</span>
            <h3 className="text-2xl font-serif text-on-surface tracking-tight">해외 종목</h3>
          </div>
          <p className="text-sm text-on-surface-variant ml-9">
            {overseas.length}종목 · 점수 갱신: {calculatedAt}
          </p>
        </div>

        <div className="bg-surface-container-low rounded-xl p-5 ghost-border">
          <div className="flex items-start gap-3 mb-4">
            <span className="material-symbols-outlined text-primary/60 text-lg mt-0.5">info</span>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              해외 전용 점수표 적용: PER/PBR 구간 상향, 분기배당 제거(미국 기본), Payout Ratio 건전성 + 배당 삭감 이력 신규 추가.
              국내 점수와 절대값 비교 불가 — 등급과 상대 순위로 비교.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { key: "category1" as const, icon: "analytics" },
              { key: "category2" as const, icon: "volunteer_activism" },
              { key: "category3" as const, icon: "trending_up" },
            ].map(({ key, icon }) => {
              const cat = OVERSEAS_FRAMEWORK[key];
              return (
                <div key={key} className="bg-surface-container/50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="material-symbols-outlined text-primary text-base">{icon}</span>
                    <span className="text-xs font-serif text-on-surface">{cat.name}</span>
                  </div>
                  <p className="text-xl font-serif text-primary">{cat.max_score}<span className="text-xs text-on-surface-variant">점</span></p>
                </div>
              );
            })}
          </div>
        </div>

        <OverseasScoringCriteria />

        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <h3 className="text-base font-serif text-on-surface mb-4">등급 분포 — 해외</h3>
          <GradeDistribution stocks={overseas} />
        </div>

        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <h3 className="text-base font-serif text-on-surface mb-4">섹터별 분포 — 해외</h3>
          <SectorPieChart
            sectors={buildSectorData(overseas)}
            totalValue={overseas.length}
            currency="count"
          />
        </div>

        <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
          <div className="p-6 pb-3">
            <h3 className="text-base font-serif text-on-surface">해외 전체 종목</h3>
          </div>
          <StockTable stocks={overseas} framework={OVERSEAS_FRAMEWORK} showCountry rankHistory={rankHistoryOverseas} />
        </div>

        {overseasAB.length > 0 && (
          <div>
            <h4 className="text-lg font-serif text-on-surface mb-4">A/B 등급 — 매수 검토 대상</h4>
            <StockCards stocks={overseasAB} framework={OVERSEAS_FRAMEWORK} />
          </div>
        )}

        {overseasC.length > 0 && (
          <Collapsible title={`C등급 — 워치리스트 (${overseasC.length}개)`}>
            <StockCards stocks={overseasC} framework={OVERSEAS_FRAMEWORK} />
          </Collapsible>
        )}
      </section>

      {/* ────────────── 통합 Top 5 ────────────── */}
      <section className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="p-6 pb-3">
          <h3 className="text-base font-serif text-on-surface">국내 + 해외 통합 Top 5</h3>
          <p className="text-xs text-on-surface-variant mt-1">각 시장 점수표 기준 · 등급과 상대 순위로 비교</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                <th className="text-center px-3 pb-3 font-normal w-10">#</th>
                <th className="text-left px-3 pb-3 font-normal">종목</th>
                <th className="text-center px-3 pb-3 font-normal">시장</th>
                <th className="text-center px-3 pb-3 font-normal">등급</th>
                <th className="text-right px-3 pb-3 font-normal">점수</th>
                <th className="text-left px-3 pb-3 font-normal">핵심</th>
              </tr>
            </thead>
            <tbody>
              {[
                ...domestic.map(s => ({ ...s, market: "국내" as const })),
                ...overseas.map(s => ({ ...s, market: "해외" as const })),
              ]
                .sort((a, b) => b.score - a.score)
                .slice(0, 5)
                .map((stock, i) => {
                  const color = getGradeColor(stock.grade);
                  return (
                    <tr key={`${stock.market}-${stock.code}`} className={`hover:bg-surface-container/30 transition-colors ${i === 0 ? "bg-primary/5" : ""}`}>
                      <td className="text-center px-3 py-2.5 font-mono" style={{ color }}>{i + 1}</td>
                      <td className="px-3 py-2.5 font-medium text-on-surface">{stock.name}</td>
                      <td className="text-center px-3 py-2.5">
                        <span className={`text-xs px-2 py-0.5 rounded ${stock.market === "국내" ? "bg-blue-500/10 text-blue-400" : "bg-emerald-500/10 text-emerald-400"}`}>
                          {stock.market}
                        </span>
                      </td>
                      <td className="text-center px-3 py-2.5">
                        <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>{stock.grade}</span>
                      </td>
                      <td className="text-right px-3 py-2.5 font-mono font-bold" style={{ color }}>{stock.score}</td>
                      <td className="px-3 py-2.5 text-on-surface-variant text-xs max-w-xs truncate">{stock.highlights}</td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Note */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-on-surface-variant/50 text-lg mt-0.5">warning</span>
          <div className="space-y-2 text-sm text-on-surface-variant leading-relaxed">
            <p>국내 종목은 국내 점수표, 해외 종목은 해외 전용 점수표로 각각 자동 채점되었습니다.</p>
            <p>오일전문가가 이 종목들을 매수한 시점에는 대부분 더 높은 등급이었을 것입니다. 주가가 오르면서 점수가 내려간 것이므로, 현재 점수가 낮아도 보유 중인 것은 합리적입니다.</p>
            <p><strong className="text-on-surface">~</strong> 표시 종목은 일부 데이터가 추정치입니다.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
