import fs from "fs/promises";
import path from "path";
import { Collapsible } from "@/components/Collapsible";
import { ScoreDetails } from "@/components/ScoreDetails";
import { RankChange, GradeChangeBadge, ScoreChangeComment } from "@/components/RankChange";
import {
  scoreGrowth,
  getGradeColor,
  getGradeLabel,
  getInterestRatePenalty,
  GROWTH_FRAMEWORK,
  type GrowthStockInput,
  type ScoredResult,
  type ShareholderReturnData,
} from "@/lib/scoring";
import { GrowthScoringCriteria } from "@/components/ScoringCriteria";
import { formatScoredAt } from "@/lib/format";


type GrowthStock = GrowthStockInput;

interface GrowthWatchlistData {
  stocks: GrowthStock[];
  excluded: { name: string; reason: string }[];
  tiers: Record<string, { label: string; desc: string }>;
  market_insight: string;
  base_rate: number;
}

type ScoredStock = GrowthStock & ScoredResult;

// ── 주주환원 데이터 변환 ──

// 나쁜 희석: 기존 주주 지분을 일방적으로 희석시키는 행위
const DILUTIVE_TYPES = new Set([
  "전환권행사", "신주인수권행사", "유상증자(제3자배정)",
  "주식매수선택권행사", "상환권행사",
]);
// 합리적 희석 (감점 제외): 유상증자(일반공모), 유상증자(주주우선공모), 유상증자(주주배정)

interface RawShareholderStock {
  code: string;
  treasury_stock: { year: number; cancelled: number }[];
  dividends: { year: number; dps: number | null }[];
  capital_changes: { year: number; type: string }[];
}

async function loadShareholderReturns(): Promise<Map<string, ShareholderReturnData>> {
  const map = new Map<string, ShareholderReturnData>();
  try {
    const filePath = path.join(process.cwd(), "public", "data", "shareholder-returns.json");
    const raw = JSON.parse(await fs.readFile(filePath, "utf-8")) as { stocks: RawShareholderStock[] };

    const currentYear = new Date().getFullYear();
    for (const s of raw.stocks) {
      const cancellationYears = s.treasury_stock.filter((t) => t.cancelled > 0).length;

      // 연속 배당 연도 수 (현재 연도 제외, 최근부터 역순)
      const validDivs = s.dividends
        .filter((d) => d.year < currentYear)
        .sort((a, b) => b.year - a.year);
      let consecutiveDivYears = 0;
      for (const d of validDivs) {
        if (d.dps !== null && d.dps > 0) consecutiveDivYears++;
        else break;
      }

      const dilutiveCount = s.capital_changes.filter((c) => DILUTIVE_TYPES.has(c.type)).length;

      map.set(s.code, {
        treasury_cancellation_years: cancellationYears,
        consecutive_dividend_years: consecutiveDivYears,
        dilutive_event_count: dilutiveCount,
      });
    }
  } catch {
    // shareholder-returns.json 없으면 빈 맵 반환
  }
  return map;
}

async function getGrowthData(): Promise<{
  stocks: ScoredStock[];
  excluded: GrowthWatchlistData["excluded"];
  tiers: GrowthWatchlistData["tiers"];
  market_insight: string;
  base_rate: number;
} | null> {
  try {
    const filePath = path.join(
      process.cwd(),
      "public",
      "data",
      "growth-watchlist.json",
    );
    const raw = await fs.readFile(filePath, "utf-8");
    const data = JSON.parse(raw) as GrowthWatchlistData;

    // 주주환원 데이터 로드
    const shReturnMap = await loadShareholderReturns();

    const baseRate = data.base_rate ?? 2.75;
    const stocks: ScoredStock[] = data.stocks
      .map((s) => ({ ...s, ...scoreGrowth(s, baseRate, shReturnMap.get(s.code)) }))
      .sort((a, b) => {
        const gradeOrder: Record<string, number> = { A: 0, B: 1, C: 2, D: 3 };
        const gDiff = (gradeOrder[a.grade] ?? 9) - (gradeOrder[b.grade] ?? 9);
        return gDiff !== 0 ? gDiff : b.score - a.score;
      });

    return {
      stocks,
      excluded: data.excluded,
      tiers: data.tiers,
      market_insight: data.market_insight,
      base_rate: baseRate,
    };
  } catch {
    return null;
  }
}

function ShareholderBadges({ badges }: { badges?: ScoredResult["shareholderBadges"] }) {
  if (!badges) return null;
  return (
    <>
      {badges.cancellation && (
        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#95d3ba20", color: "#95d3ba" }}>소각</span>
      )}
      {badges.dividend && (
        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#e9c17620", color: "#e9c176" }}>배당</span>
      )}
      {badges.dilution && (
        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#ffb4ab20", color: "#ffb4ab" }}>희석주의</span>
      )}
    </>
  );
}

function getTierLabel(tier?: string): string | null {
  const labels: Record<string, string> = {
    tier1: "때를 기다리는 종목",
    tier2: "변화를 감시하는 종목",
    tier3: "장기 모니터링",
  };
  return tier ? labels[tier] || null : null;
}

export default async function GrowthPage() {
  const data = await getGrowthData();
  const framework = GROWTH_FRAMEWORK;

  if (!data || data.stocks.length === 0) {
    return (
      <div className="space-y-14">
        {/* Header */}
        <section>
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
            Undervalued Growth Stocks
          </p>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
            저평가 성장주
          </h2>
          <p className="text-base text-on-surface-variant mt-2">
            성장주 전용 스코어링 시스템 (준비 중)
          </p>
        </section>

        {/* Empty State */}
        <section className="bg-surface-container-low rounded-xl p-12 ghost-border text-center">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant/30 mb-4">
            trending_up
          </span>
          <h3 className="text-xl font-serif text-on-surface mb-3">
            아직 등록된 종목이 없습니다
          </h3>
          <p className="text-sm text-on-surface-variant leading-relaxed max-w-md mx-auto">
            저평가 성장주 스코어링 체계를 준비 중입니다. 배당주와는 다른
            기준으로 저평가 성장주를 발굴할 예정입니다.
          </p>
        </section>
      </div>
    );
  }

  const { stocks, excluded, base_rate } = data;
  const rateInfo = getInterestRatePenalty(base_rate);

  // 등급별 분류 (한 번만 계산)
  const gradeGroups: Record<string, ScoredStock[]> = {
    A: [],
    B: [],
    C: [],
    D: [],
  };
  const visibleStocks: ScoredStock[] = [];
  for (const s of stocks) {
    if (gradeGroups[s.grade]) gradeGroups[s.grade].push(s);
    if (s.score >= 45) visibleStocks.push(s);
  }
  const hiddenCount = stocks.length - visibleStocks.length;
  const abStocks = [...gradeGroups.A, ...gradeGroups.B];
  const cStocks = gradeGroups.C;
  const dStocks = gradeGroups.D;

  const calculatedAt = formatScoredAt(
    stocks.reduce((latest, s) => (s.scored_at > latest ? s.scored_at : latest), stocks[0]?.scored_at ?? "")
  );

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Undervalued Growth Stocks
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          저평가 성장주
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          GARP 스코어링 · 성장성 35 + 밸류에이션 30 + 경쟁력/시그널 35 ± 주주환원 보정 − 금리 감점
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1.5">
          점수 갱신: {calculatedAt}
        </p>

        {/* 금리 환경 배너 */}
        <div className={`mt-4 flex items-center gap-3 rounded-xl p-4 ghost-border ${rateInfo.penalty >= 10 ? "bg-[#ffb4ab]/10" : rateInfo.penalty >= 5 ? "bg-[#e9c176]/10" : "bg-[#95d3ba]/10"}`}>
          <span className="material-symbols-outlined text-lg" style={{ color: rateInfo.penalty >= 10 ? "#ffb4ab" : rateInfo.penalty >= 5 ? "#e9c176" : "#95d3ba" }}>
            {rateInfo.penalty >= 10 ? "warning" : rateInfo.penalty >= 5 ? "info" : "check_circle"}
          </span>
          <div>
            <p className="text-sm text-on-surface">
              한국은행 기준금리 <span className="font-mono font-bold">{base_rate}%</span>
              {rateInfo.penalty > 0 && <span className="text-on-surface-variant"> · 전 종목 <span className="font-mono font-bold" style={{ color: "#ffb4ab" }}>−{rateInfo.penalty}점</span> 감점</span>}
            </p>
            <p className="text-xs text-on-surface-variant/60 mt-0.5">{rateInfo.label}</p>
          </div>
        </div>
      </section>

      {/* Scoring Framework */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {[
          { key: "category1" as const, icon: "trending_up" },
          { key: "category2" as const, icon: "query_stats" },
          { key: "category3" as const, icon: "shield" },
        ].map(({ key, icon }) => {
          const cat = framework[key];
          return (
            <div
              key={key}
              className="bg-surface-container-low rounded-xl p-5 ghost-border"
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="material-symbols-outlined text-primary text-lg">
                  {icon}
                </span>
                <h4 className="text-sm font-serif text-on-surface">
                  {cat.name}
                </h4>
              </div>
              <p className="text-2xl font-serif text-primary mb-2">
                {cat.max_score}
                <span className="text-sm text-on-surface-variant">점</span>
              </p>
              <div className="flex flex-wrap gap-1.5">
                {cat.key_metrics.map((m: string) => (
                  <span
                    key={m}
                    className="text-xs bg-surface-container-high px-2 py-0.5 rounded text-on-surface-variant"
                  >
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
        <GrowthScoringCriteria />
      </section>

      {/* Grade Distribution */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <h3 className="text-base font-serif text-on-surface mb-4">등급 분포</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {(["A", "B", "C", "D"] as const).map((grade) => {
            const count = gradeGroups[grade].length;
            const color = getGradeColor(grade);
            return (
              <div
                key={grade}
                className="text-center p-4 rounded-xl ghost-border bg-surface-container/30"
              >
                <p className="text-3xl font-serif font-bold" style={{ color }}>
                  {grade}
                </p>
                <p className="text-2xl font-mono text-on-surface mt-1">
                  {count}
                  <span className="text-sm text-on-surface-variant">개</span>
                </p>
                <p className="text-xs text-on-surface-variant mt-1">
                  {getGradeLabel(grade)}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Quick Summary Table */}
      <section className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
        <div className="p-6 pb-3">
          <h3 className="text-base font-serif text-on-surface">
            전체 종목 한눈에 보기
          </h3>
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
                <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">
                  PEG
                </th>
                <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">
                  PSR
                </th>
                <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">
                  매출↑
                </th>
                <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">
                  시총
                </th>
                <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">
                  외인
                </th>
                <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">
                  성장성
                </th>
                <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">
                  밸류에이션
                </th>
                <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">
                  시그널
                </th>
                <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">
                  채점일
                </th>
              </tr>
            </thead>
            <tbody>
              {visibleStocks.map((stock, i) => {
                const color = getGradeColor(stock.grade);
                const rank = i + 1;
                return (
                  <tr
                    key={stock.code}
                    className={`hover:bg-surface-container/30 transition-colors ${rank === 1 ? "bg-primary/5" : ""}`}
                  >
                    <td
                      className="text-center px-3 py-2.5 font-mono"
                      style={{ color }}
                    >
                      {rank}
                    </td>
                    <td className="px-3 py-2.5 font-medium text-on-surface">
                      <span className="inline-flex items-center gap-1.5 flex-wrap">
                        {stock.name}
                        {stock.estimated && (
                          <span className="text-[10px] text-on-surface-variant/40">
                            ~
                          </span>
                        )}
                        <RankChange
                          currentRank={rank}
                          previousRank={stock.previous_rank}
                        />
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-on-surface-variant">
                      {stock.sector}
                    </td>
                    <td className="text-center px-3 py-2.5">
                      <span
                        className="text-xs px-2 py-0.5 rounded font-bold"
                        style={{
                          backgroundColor: `${color}20`,
                          color,
                        }}
                      >
                        {stock.grade}
                      </span>
                    </td>
                    <td
                      className="text-right px-3 py-2.5 font-mono font-bold"
                      style={{ color }}
                    >
                      {stock.score}
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">
                      {stock.peg != null ? `${stock.peg}` : "—"}
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">
                      {stock.psr}x
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">
                      {stock.revenue_growth_3y}%
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">
                      {stock.market_cap != null ? (stock.market_cap >= 10000 ? `${(stock.market_cap / 10000).toFixed(1)}조` : `${stock.market_cap.toLocaleString()}억`) : "—"}
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">
                      {stock.foreign_ownership != null ? `${stock.foreign_ownership}%` : "—"}
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden lg:table-cell">
                      {stock.cat1}/{framework.category1.max_score}
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden lg:table-cell">
                      {stock.cat2}/{framework.category2.max_score}
                    </td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden lg:table-cell">
                      {stock.cat3}/{framework.category3.max_score}
                    </td>
                    <td className="text-right px-3 py-2.5 text-xs text-on-surface-variant/50 hidden lg:table-cell">
                      {formatScoredAt(stock.scored_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Stock Rankings */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
          종목 순위
        </h3>
        <p className="text-sm text-on-surface-variant mb-6">
          점수 높은 순 · 자동 계산
        </p>

        {/* A/B 등급 */}
        <div className="space-y-4">
          {abStocks
            .map((stock, rank) => {
              const color = getGradeColor(stock.grade);
              const tierLabel = getTierLabel(stock.tier);
              const cat1Pct =
                (stock.cat1 / framework.category1.max_score) * 100;
              const cat2Pct =
                (stock.cat2 / framework.category2.max_score) * 100;
              const cat3Pct =
                (stock.cat3 / framework.category3.max_score) * 100;

              return (
                <div
                  key={stock.code}
                  className="bg-surface-container-low rounded-xl ghost-border overflow-hidden"
                >
                  <div className="p-4 sm:p-6">
                    <ScoreChangeComment score={stock.score} previousScore={stock.previous_score} grade={stock.grade} details={stock.details} previousDetails={stock.previous_details} />
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-4">
                        <div className="text-center w-8">
                          <span
                            className="text-2xl font-serif font-bold"
                            style={{ color }}
                          >
                            {rank + 1}
                          </span>
                          <RankChange
                            currentRank={rank + 1}
                            previousRank={stock.previous_rank}
                          />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="text-base sm:text-lg font-medium text-on-surface">
                              {stock.name}
                            </h4>
                            <span
                              className="text-xs px-2 py-0.5 rounded font-bold"
                              style={{
                                backgroundColor: `${color}20`,
                                color,
                              }}
                            >
                              {stock.grade}
                            </span>
                            <ShareholderBadges badges={stock.shareholderBadges} />
                            {stock.estimated && (
                              <span className="text-xs text-on-surface-variant/40">
                                추정치
                              </span>
                            )}
                            {tierLabel && (
                              <span className="text-xs text-on-surface-variant/50">
                                {tierLabel}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-on-surface-variant">
                            {stock.code} · {stock.sector}
                            <span className="text-xs text-on-surface-variant/40 ml-2">
                              {formatScoredAt(stock.scored_at)} 채점
                            </span>
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p
                          className="text-2xl sm:text-3xl font-serif font-bold"
                          style={{ color }}
                        >
                          {stock.score}
                        </p>
                        <p className="text-xs text-on-surface-variant">
                          /100점
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-4">
                      {[
                        {
                          label: "성장성",
                          score: stock.cat1,
                          max: framework.category1.max_score,
                          pct: cat1Pct,
                        },
                        {
                          label: "밸류에이션",
                          score: stock.cat2,
                          max: framework.category2.max_score,
                          pct: cat2Pct,
                        },
                        {
                          label: "경쟁력/시그널",
                          score: stock.cat3,
                          max: framework.category3.max_score,
                          pct: cat3Pct,
                        },
                      ].map((cat) => (
                        <div
                          key={cat.label}
                          className="bg-surface-container/50 rounded-lg p-2 sm:p-3"
                        >
                          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-1.5 gap-0.5">
                            <span className="text-[10px] sm:text-xs text-on-surface-variant">
                              {cat.label}
                            </span>
                            <span className="text-xs sm:text-sm font-mono text-on-surface">
                              {cat.score}/{cat.max}
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{
                                width: `${cat.pct}%`,
                                backgroundColor: color,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3 text-sm">
                      <span className="text-on-surface-variant">
                        PEG{" "}
                        <span className="font-mono text-on-surface">
                          {stock.peg != null ? stock.peg : "—"}
                        </span>
                      </span>
                      <span className="text-on-surface-variant">
                        PSR{" "}
                        <span className="font-mono text-on-surface">
                          {stock.psr}x
                        </span>
                      </span>
                      <span className="text-on-surface-variant">
                        PER{" "}
                        <span className="font-mono text-on-surface">
                          {stock.per != null ? `${stock.per}x` : "적자"}
                        </span>
                      </span>
                      <span className="text-on-surface-variant">
                        매출↑{" "}
                        <span className="font-mono text-on-surface">
                          {stock.revenue_growth_3y}%
                        </span>
                      </span>
                      <span className="text-on-surface-variant">
                        영업이익↑{" "}
                        <span className="font-mono text-on-surface">
                          {stock.op_profit_growth_3y}%
                        </span>
                      </span>
                      {stock.market_cap != null && (
                        <span className="text-on-surface-variant">
                          시총{" "}
                          <span className="font-mono text-on-surface">
                            {stock.market_cap >= 10000 ? `${(stock.market_cap / 10000).toFixed(1)}조` : `${stock.market_cap.toLocaleString()}억`}
                          </span>
                        </span>
                      )}
                      {stock.foreign_ownership != null && (
                        <span className="text-on-surface-variant">
                          외인{" "}
                          <span className="font-mono text-on-surface">
                            {stock.foreign_ownership}%
                          </span>
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-on-surface-variant leading-relaxed">
                      {stock.highlights}
                    </p>

                    {stock.catalyst && (
                      <div className="mt-3 flex items-start gap-2">
                        <span className="material-symbols-outlined text-primary text-sm mt-0.5">
                          bolt
                        </span>
                        <p className="text-sm text-primary/80">
                          {stock.catalyst}
                        </p>
                      </div>
                    )}

                    {stock.a_grade_price && (
                      <div className="mt-3 flex items-center gap-2">
                        <span className="material-symbols-outlined text-[#95d3ba] text-sm">
                          flag
                        </span>
                        <p className="text-sm text-[#95d3ba]">
                          A등급 예상 진입가:{" "}
                          {stock.a_grade_price.toLocaleString()}원
                          {stock.current_price_at_scoring && (
                            <span className="text-on-surface-variant/50 ml-1">
                              (분석 당시{" "}
                              {stock.current_price_at_scoring.toLocaleString()}원
                              대비 -
                              {Math.round(
                                (1 -
                                  stock.a_grade_price /
                                    stock.current_price_at_scoring) *
                                  100,
                              )}
                              %)
                            </span>
                          )}
                        </p>
                      </div>
                    )}

                    <ScoreDetails details={stock.details} />
                  </div>
                </div>
              );
            })}
        </div>

        {/* C 등급 */}
        {cStocks.length > 0 && (
          <div className="mt-6">
            <Collapsible
              title={`C등급 — 워치리스트 (${cStocks.length}개)`}
            >
              <div className="space-y-4">
                {cStocks
                  .map((stock) => {
                    const color = getGradeColor(stock.grade);
                    const tierLabel = getTierLabel(stock.tier);
                    const globalRank = stocks.indexOf(stock) + 1;
                    const cat1Pct =
                      (stock.cat1 / framework.category1.max_score) * 100;
                    const cat2Pct =
                      (stock.cat2 / framework.category2.max_score) * 100;
                    const cat3Pct =
                      (stock.cat3 / framework.category3.max_score) * 100;

                    return (
                      <div
                        key={stock.code}
                        className="bg-surface-container-low rounded-xl ghost-border overflow-hidden"
                      >
                        <div className="p-6">
                          <ScoreChangeComment score={stock.score} previousScore={stock.previous_score} grade={stock.grade} details={stock.details} previousDetails={stock.previous_details} />
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-4">
                              <div className="text-center w-8">
                                <span
                                  className="text-2xl font-serif font-bold"
                                  style={{ color }}
                                >
                                  {globalRank}
                                </span>
                                <RankChange
                                  currentRank={globalRank}
                                  previousRank={stock.previous_rank}
                                />
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <h4 className="text-lg font-medium text-on-surface">
                                    {stock.name}
                                  </h4>
                                  <span
                                    className="text-xs px-2 py-0.5 rounded font-bold"
                                    style={{
                                      backgroundColor: `${color}20`,
                                      color,
                                    }}
                                  >
                                    {stock.grade}
                                  </span>
                                  <ShareholderBadges badges={stock.shareholderBadges} />
                                  {stock.estimated && (
                                    <span className="text-xs text-on-surface-variant/40">
                                      추정치
                                    </span>
                                  )}
                                  {tierLabel && (
                                    <span className="text-xs text-on-surface-variant/50">
                                      {tierLabel}
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-on-surface-variant">
                                  {stock.code} · {stock.sector}
                                  <span className="text-xs text-on-surface-variant/40 ml-2">
                                    {formatScoredAt(stock.scored_at)} 채점
                                  </span>
                                </p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p
                                className="text-2xl sm:text-3xl font-serif font-bold"
                                style={{ color }}
                              >
                                {stock.score}
                              </p>
                              <p className="text-xs text-on-surface-variant">
                                /100점
                              </p>
                            </div>
                          </div>
                          <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-4">
                            {[
                              {
                                label: framework.category1.name.split("/")[0],
                                score: stock.cat1,
                                max: framework.category1.max_score,
                                pct: cat1Pct,
                              },
                              {
                                label: "밸류에이션",
                                score: stock.cat2,
                                max: framework.category2.max_score,
                                pct: cat2Pct,
                              },
                              {
                                label: "경쟁력/시그널",
                                score: stock.cat3,
                                max: framework.category3.max_score,
                                pct: cat3Pct,
                              },
                            ].map((cat) => (
                              <div
                                key={cat.label}
                                className="bg-surface-container/50 rounded-lg p-3"
                              >
                                <div className="flex justify-between items-center mb-1.5">
                                  <span className="text-xs text-on-surface-variant">
                                    {cat.label}
                                  </span>
                                  <span className="text-sm font-mono text-on-surface">
                                    {cat.score}/{cat.max}
                                  </span>
                                </div>
                                <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                                  <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{
                                      width: `${cat.pct}%`,
                                      backgroundColor: color,
                                    }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                          <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3 text-sm">
                            <span className="text-on-surface-variant">
                              PEG{" "}
                              <span className="font-mono text-on-surface">
                                {stock.peg != null ? stock.peg : "—"}
                              </span>
                            </span>
                            <span className="text-on-surface-variant">
                              PSR{" "}
                              <span className="font-mono text-on-surface">
                                {stock.psr}x
                              </span>
                            </span>
                            <span className="text-on-surface-variant">
                              PER{" "}
                              <span className="font-mono text-on-surface">
                                {stock.per != null ? `${stock.per}x` : "적자"}
                              </span>
                            </span>
                            <span className="text-on-surface-variant">
                              매출↑{" "}
                              <span className="font-mono text-on-surface">
                                {stock.revenue_growth_3y}%
                              </span>
                            </span>
                            {stock.market_cap != null && (
                              <span className="text-on-surface-variant">
                                시총{" "}
                                <span className="font-mono text-on-surface">
                                  {stock.market_cap >= 10000 ? `${(stock.market_cap / 10000).toFixed(1)}조` : `${stock.market_cap.toLocaleString()}억`}
                                </span>
                              </span>
                            )}
                            {stock.foreign_ownership != null && (
                              <span className="text-on-surface-variant">
                                외인{" "}
                                <span className="font-mono text-on-surface">
                                  {stock.foreign_ownership}%
                                </span>
                              </span>
                            )}
                          </div>

                          <p className="text-sm text-on-surface-variant leading-relaxed">
                            {stock.highlights}
                          </p>
                          {stock.catalyst && (
                            <div className="mt-3 flex items-start gap-2">
                              <span className="material-symbols-outlined text-primary text-sm mt-0.5">
                                bolt
                              </span>
                              <p className="text-sm text-primary/80">
                                {stock.catalyst}
                              </p>
                            </div>
                          )}
                          <ScoreDetails details={stock.details} />
                        </div>
                      </div>
                    );
                  })}
              </div>
            </Collapsible>
          </div>
        )}

        {/* D 등급 */}
        {dStocks.length > 0 && (
          <div className="mt-6">
            <Collapsible
              title={`D등급 — 투자 부적합 (${dStocks.length}개)`}
            >
              <div className="space-y-4">
                {dStocks
                  .map((stock) => {
                    const color = getGradeColor(stock.grade);
                    const globalRank = stocks.indexOf(stock) + 1;

                    return (
                      <div
                        key={stock.code}
                        className="bg-surface-container-low rounded-xl ghost-border overflow-hidden"
                      >
                        <div className="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                          <div className="flex items-center gap-4">
                            <span
                              className="text-xl font-serif font-bold w-8 shrink-0"
                              style={{ color }}
                            >
                              {globalRank}
                            </span>
                            <div>
                              <h4 className="text-base font-medium text-on-surface inline-flex items-center gap-1.5 flex-wrap">
                                {stock.name}
                                <ShareholderBadges badges={stock.shareholderBadges} />
                                <RankChange
                                  currentRank={globalRank}
                                  previousRank={stock.previous_rank}
                                />
                                <GradeChangeBadge
                                  grade={stock.grade}
                                  score={stock.score}
                                  previousScore={stock.previous_score}
                                  compact
                                />
                              </h4>
                              <p className="text-sm text-on-surface-variant">
                                {stock.code} · {stock.sector}
                                <span className="text-xs text-on-surface-variant/40 ml-2">
                                  {formatScoredAt(stock.scored_at)}
                                </span>
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-4 ml-12 sm:ml-0">
                            <p className="text-sm text-on-surface-variant/60 max-w-sm sm:text-right">
                              {stock.highlights}
                            </p>
                            <p
                              className="text-2xl font-serif font-bold shrink-0"
                              style={{ color }}
                            >
                              {stock.score}
                            </p>
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
      {excluded.length > 0 && (
        <section>
          <Collapsible title="제외 종목 (밸류 트랩 또는 펀더멘탈 약화)">
            <div className="space-y-2">
              {excluded.map((stock) => (
                <div
                  key={stock.name}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-4 p-4 bg-surface-container/30 rounded-lg"
                >
                  <span className="text-base text-on-surface shrink-0">
                    {stock.name}
                  </span>
                  <p className="text-sm text-on-surface-variant/60 sm:text-right">
                    {stock.reason}
                  </p>
                </div>
              ))}
            </div>
          </Collapsible>
        </section>
      )}

      {/* Guide */}
      <section className="bg-surface-container-low rounded-xl p-8 ghost-border">
        <h3 className="text-lg font-serif text-on-surface mb-5">
          점수 시스템 해석
        </h3>
        <div className="space-y-4 text-base text-on-surface-variant leading-relaxed">
          <p>
            <strong className="text-on-surface">핵심 공식:</strong> 저평가
            성장주 = 높은 성장률 + 성장 가속 + 낮은 PEG/PSR + 경쟁우위 + 소형주(시장 미주목) + 낮은 외국인비중.
            반면 적자(PER 마이너스) + 고부채 + 성장 둔화 = 고평가 함정 (감점·회피).
          </p>
          <p>
            <strong className="text-on-surface">
              금리가 높으면 성장주가 불리합니다.
            </strong>{" "}
            고금리 환경에서는 전 종목에 감점이 적용되어 매수 등급 진입이
            어려워집니다. 금리 인하 사이클에서 성장주 매수 기회가 열립니다.
          </p>
          <p>
            <strong className="text-on-surface">분기별 재점검:</strong> 실적
            시즌마다 매출 성장률, EPS, PEG 변화를 반영하여 점수를 갱신합니다.
            기준금리 변동 시에도 전체 점수가 재산출됩니다.
          </p>
        </div>
      </section>
    </div>
  );
}
