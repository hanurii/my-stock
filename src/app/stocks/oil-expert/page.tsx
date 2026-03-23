import fs from "fs";
import path from "path";

interface StockEntry {
  code: string;
  name: string;
  sector: string;
  country?: string;
  per: number | null;
  pbr: number;
  dividend_yield: number;
  score: number;
  grade: string;
  cat1: number;
  cat2: number;
  cat3: number;
  highlights: string;
  estimated?: boolean;
}

interface Framework {
  category1: { name: string; max_score: number; key_metrics: string[] };
  category2: { name: string; max_score: number; key_metrics: string[] };
  category3: { name: string; max_score: number; key_metrics: string[] };
}

interface MarketSection {
  framework: Framework;
  grades: Record<string, { min: number; label: string; color: string }>;
  stocks: StockEntry[];
}

interface OilExpertData {
  generated_at: string;
  owner: string;
  domestic: MarketSection;
  overseas: MarketSection;
  insights: {
    domestic_summary: string;
    overseas_summary: string;
    portfolio_strategy: string;
  };
}

function getData(): OilExpertData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "oil-expert-watchlist.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as OilExpertData;
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

function StockTable({ stocks, framework, market }: { stocks: StockEntry[]; framework: Framework; market: "domestic" | "overseas" }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
            <th className="text-center px-3 pb-3 font-normal w-10">#</th>
            <th className="text-left px-3 pb-3 font-normal">종목</th>
            {market === "overseas" && <th className="text-left px-3 pb-3 font-normal hidden md:table-cell">국가</th>}
            <th className="text-left px-3 pb-3 font-normal">섹터</th>
            <th className="text-center px-3 pb-3 font-normal">등급</th>
            <th className="text-right px-3 pb-3 font-normal">점수</th>
            <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">PER</th>
            <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">PBR</th>
            <th className="text-right px-3 pb-3 font-normal hidden md:table-cell">배당률</th>
            <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">{framework.category1.name.split("/")[0]}</th>
            <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">주주환원</th>
            <th className="text-right px-3 pb-3 font-normal hidden lg:table-cell">성장</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock, i) => {
            const color = getGradeColor(stock.grade);
            return (
              <tr key={stock.code} className={`hover:bg-surface-container/30 transition-colors ${i === 0 ? "bg-primary/5" : ""}`}>
                <td className="text-center px-3 py-2.5 font-mono" style={{ color }}>{i + 1}</td>
                <td className="px-3 py-2.5 font-medium text-on-surface">
                  {stock.name}
                  {stock.estimated && <span className="text-[10px] text-on-surface-variant/40 ml-1">~</span>}
                </td>
                {market === "overseas" && <td className="px-3 py-2.5 text-on-surface-variant hidden md:table-cell">{stock.country}</td>}
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
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StockCards({ stocks, framework }: { stocks: StockEntry[]; framework: Framework }) {
  return (
    <div className="space-y-4">
      {stocks.map((stock, rank) => {
        const color = getGradeColor(stock.grade);
        const cat1Pct = (stock.cat1 / framework.category1.max_score) * 100;
        const cat2Pct = (stock.cat2 / framework.category2.max_score) * 100;
        const cat3Pct = (stock.cat3 / framework.category3.max_score) * 100;

        return (
          <div key={stock.code} className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  <span className="text-2xl font-serif font-bold w-8" style={{ color }}>{rank + 1}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-lg font-medium text-on-surface">{stock.name}</h4>
                      <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>{stock.grade}</span>
                      {stock.estimated && <span className="text-xs text-on-surface-variant/40">추정치</span>}
                    </div>
                    <p className="text-sm text-on-surface-variant">
                      {stock.code} · {stock.sector}
                      {stock.country && <span> · {stock.country}</span>}
                    </p>
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
                  { label: framework.category1.name.split("/")[0], score: stock.cat1, max: framework.category1.max_score, pct: cat1Pct },
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

              {/* Key Metrics */}
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

              {/* Highlights */}
              <p className="text-sm text-on-surface-variant leading-relaxed">{stock.highlights}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function GradeDistribution({ stocks }: { stocks: StockEntry[] }) {
  const gradeGroups: Record<string, StockEntry[]> = { A: [], B: [], C: [], D: [] };
  stocks.forEach((s) => {
    if (gradeGroups[s.grade]) gradeGroups[s.grade].push(s);
  });

  const labels: Record<string, string> = { A: "강력 매수", B: "매수 검토", C: "워치리스트", D: "투자 부적합" };

  return (
    <div className="grid grid-cols-4 gap-4">
      {(["A", "B", "C", "D"] as const).map((grade) => {
        const count = gradeGroups[grade].length;
        const color = getGradeColor(grade);
        return (
          <div key={grade} className="text-center p-4 rounded-xl ghost-border bg-surface-container/30">
            <p className="text-3xl font-serif font-bold" style={{ color }}>{grade}</p>
            <p className="text-2xl font-mono text-on-surface mt-1">{count}<span className="text-sm text-on-surface-variant">개</span></p>
            <p className="text-xs text-on-surface-variant mt-1">{labels[grade]}</p>
          </div>
        );
      })}
    </div>
  );
}

function SectorBreakdown({ stocks }: { stocks: StockEntry[] }) {
  const sectorMap = new Map<string, StockEntry[]>();
  stocks.forEach((s) => {
    const sector = s.sector.replace("(우)", "");
    const existing = sectorMap.get(sector) || [];
    existing.push(s);
    sectorMap.set(sector, existing);
  });

  const sectors = Array.from(sectorMap.entries()).sort((a, b) => b[1].length - a[1].length);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {sectors.map(([sector, sectorStocks]) => {
        const avgScore = Math.round(sectorStocks.reduce((sum, s) => sum + s.score, 0) / sectorStocks.length);
        const color = getGradeColor(avgScore >= 80 ? "A" : avgScore >= 70 ? "B" : avgScore >= 50 ? "C" : "D");
        return (
          <div key={sector} className="bg-surface-container/30 rounded-lg p-3 ghost-border">
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-on-surface">{sector}</span>
              <span className="text-xs font-mono" style={{ color }}>{avgScore}점</span>
            </div>
            <p className="text-xs text-on-surface-variant">
              {sectorStocks.map(s => s.name).join(", ")}
            </p>
          </div>
        );
      })}
    </div>
  );
}

export default function OilExpertPage() {
  const data = getData();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
      </div>
    );
  }

  const { domestic, overseas, insights } = data;
  const allStocksCount = domestic.stocks.length + overseas.stocks.length;

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Oil Expert Portfolio
        </p>
        <h2 className="text-4xl font-serif font-bold text-on-surface tracking-tight">
          오일전문가 포트폴리오
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          {data.generated_at} 기준 · 국내 {domestic.stocks.length}종목 + 해외 {overseas.stocks.length}종목 = 총 {allStocksCount}종목
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
          <p className="text-sm text-on-surface-variant ml-9">{domestic.stocks.length}종목 · {insights.domestic_summary}</p>
        </div>

        {/* Domestic Scoring Framework */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            { key: "category1", icon: "analytics" },
            { key: "category2", icon: "volunteer_activism" },
            { key: "category3", icon: "trending_up" },
          ].map(({ key, icon }) => {
            const cat = domestic.framework[key as keyof Framework];
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

        {/* Domestic Grade Distribution */}
        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <h3 className="text-base font-serif text-on-surface mb-4">등급 분포 — 국내</h3>
          <GradeDistribution stocks={domestic.stocks} />
        </div>

        {/* Domestic Sector Breakdown */}
        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <h3 className="text-base font-serif text-on-surface mb-4">섹터별 분포</h3>
          <SectorBreakdown stocks={domestic.stocks} />
        </div>

        {/* Domestic Full Table */}
        <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
          <div className="p-6 pb-3">
            <h3 className="text-base font-serif text-on-surface">국내 전체 종목</h3>
          </div>
          <StockTable stocks={domestic.stocks} framework={domestic.framework} market="domestic" />
        </div>

        {/* Domestic B Grade Cards */}
        {domestic.stocks.filter(s => s.grade === "A" || s.grade === "B").length > 0 && (
          <div>
            <h4 className="text-lg font-serif text-on-surface mb-4">
              A/B 등급 — 매수 검토 대상
            </h4>
            <StockCards
              stocks={domestic.stocks.filter(s => s.grade === "A" || s.grade === "B")}
              framework={domestic.framework}
            />
          </div>
        )}

        {/* Domestic C Grade Cards */}
        {domestic.stocks.filter(s => s.grade === "C").length > 0 && (
          <div>
            <h4 className="text-lg font-serif text-on-surface mb-4">
              C등급 — 워치리스트 ({domestic.stocks.filter(s => s.grade === "C").length}개)
            </h4>
            <StockCards
              stocks={domestic.stocks.filter(s => s.grade === "C")}
              framework={domestic.framework}
            />
          </div>
        )}
      </section>

      {/* ────────────── 해외 종목 ────────────── */}
      <section className="space-y-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="material-symbols-outlined text-primary">public</span>
            <h3 className="text-2xl font-serif text-on-surface tracking-tight">해외 종목</h3>
          </div>
          <p className="text-sm text-on-surface-variant ml-9">{overseas.stocks.length}종목 · {insights.overseas_summary}</p>
        </div>

        {/* Overseas Scoring Framework */}
        <div className="bg-surface-container-low rounded-xl p-5 ghost-border">
          <div className="flex items-start gap-3 mb-4">
            <span className="material-symbols-outlined text-primary/60 text-lg mt-0.5">info</span>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              해외 전용 점수표 적용: PER/PBR 구간 상향, 분기배당 제거(미국 기본), Payout Ratio 건전성 + 배당 삭감 이력 신규 추가.
              국내 점수와 절대값 비교 불가 — 등급과 상대 순위로 비교.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { key: "category1", icon: "analytics" },
              { key: "category2", icon: "volunteer_activism" },
              { key: "category3", icon: "trending_up" },
            ].map(({ key, icon }) => {
              const cat = overseas.framework[key as keyof Framework];
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

        {/* Overseas Grade Distribution */}
        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <h3 className="text-base font-serif text-on-surface mb-4">등급 분포 — 해외</h3>
          <GradeDistribution stocks={overseas.stocks} />
        </div>

        {/* Overseas Full Table */}
        <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
          <div className="p-6 pb-3">
            <h3 className="text-base font-serif text-on-surface">해외 전체 종목</h3>
          </div>
          <StockTable stocks={overseas.stocks} framework={overseas.framework} market="overseas" />
        </div>

        {/* Overseas B Grade Cards */}
        {overseas.stocks.filter(s => s.grade === "A" || s.grade === "B").length > 0 && (
          <div>
            <h4 className="text-lg font-serif text-on-surface mb-4">
              A/B 등급 — 매수 검토 대상
            </h4>
            <StockCards
              stocks={overseas.stocks.filter(s => s.grade === "A" || s.grade === "B")}
              framework={overseas.framework}
            />
          </div>
        )}

        {/* Overseas C Grade Cards */}
        {overseas.stocks.filter(s => s.grade === "C").length > 0 && (
          <div>
            <h4 className="text-lg font-serif text-on-surface mb-4">
              C등급 — 워치리스트 ({overseas.stocks.filter(s => s.grade === "C").length}개)
            </h4>
            <StockCards
              stocks={overseas.stocks.filter(s => s.grade === "C")}
              framework={overseas.framework}
            />
          </div>
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
                ...domestic.stocks.map(s => ({ ...s, market: "국내" as const })),
                ...overseas.stocks.map(s => ({ ...s, market: "해외" as const })),
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
            <p>국내 종목은 국내 점수표, 해외 종목은 해외 전용 점수표로 각각 채점되었습니다.</p>
            <p>오일전문가가 이 종목들을 매수한 시점에는 대부분 더 높은 등급이었을 것입니다. 주가가 오르면서 점수가 내려간 것이므로, 현재 점수가 낮아도 보유 중인 것은 합리적입니다.</p>
            <p><strong className="text-on-surface">~</strong> 표시 종목은 일부 데이터가 추정치입니다.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
