import fs from "fs/promises";
import path from "path";
import { getGradeColor, type ScoreChangeEntry } from "@/lib/scoring";
import { Collapsible } from "@/components/Collapsible";
import { RankChange, GradeChangeBadge, ScoreChangeComment } from "@/components/RankChange";
import { getStockTrend, type RankHistory } from "@/lib/rank-history";
import { RankTrendSparkline } from "@/components/RankTrendSparkline";


// ── 타입 ──

interface ScoreDetail {
  item: string;
  basis: string;
  score: number;
  max: number;
  cat: number;
}

interface Candidate {
  code: string;
  name: string;
  market: string;
  score: number;
  grade: string;
  cat1: number;
  cat2: number;
  cat3: number;
  details: ScoreDetail[];
  market_cap: number;
  per: number | null;
  pbr: number;
  dividend_yield: number;
  foreign_ownership: number;
  current_price: number;
  revenue_latest: number;
  revenue_prev: number;
  op_profit_latest: number;
  op_profit_prev: number;
  op_margin: number;
  op_margin_prev: number | null;
  profit_years: number;
  eps_current: number | null;
  eps_consensus: number | null;
  shareholderBadges?: { cancellation: boolean; dividend: boolean; dilution: boolean };
  previous_score?: number;
  previous_rank?: number;
  previous_details?: ScoreDetail[];
  score_history?: ScoreChangeEntry[];
  is_top10: boolean;
}

interface ScreenData {
  scanned_at: string;
  base_rate: number;
  total_scanned: number;
  filter_passed: number;
  scored_count: number;
  candidates: Candidate[];
  excluded: { code: string; name: string; reason: string }[];
}

// ── 데이터 로드 ──

async function getData(): Promise<ScreenData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "growth-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

// ── 포맷 ──

function fmtNum(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}조`;
  return `${n.toLocaleString()}억`;
}

function fmtGrowth(latest: number, prev: number): string {
  if (prev <= 0) return latest > 0 ? "흑자전환" : "-";
  const pct = ((latest - prev) / prev) * 100;
  return `${pct > 0 ? "+" : ""}${pct.toFixed(0)}%`;
}

// ── 페이지 ──

export default async function GrowthScreenPage() {
  const data = await getData();

  let rankHistory: RankHistory | null = null;
  try {
    const histPath = path.join(process.cwd(), "public", "data", "rank-history-growth-screen.json");
    rankHistory = JSON.parse(await fs.readFile(histPath, "utf-8"));
  } catch { /* */ }

  if (!data || data.candidates.length === 0) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">성장주 스크리닝</h2>
          <p className="text-sm text-on-surface-variant mt-2">데이터가 아직 생성되지 않았습니다.</p>
        </header>
      </div>
    );
  }

  const top10 = data.candidates.filter((c) => c.is_top10);
  const rest = data.candidates.filter((c) => !c.is_top10);

  return (
    <div className="space-y-10">
      {/* 헤더 */}
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          성장주 스크리닝
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          성장 모멘텀 45 + 성장 대비 밸류에이션 35 + 안전장치 20 − 금리 감점
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1.5">
          스캔일: {data.scanned_at} · 전체 {data.total_scanned.toLocaleString()}종목 → 1차 필터 {data.filter_passed.toLocaleString()}개 → 채점 {data.scored_count.toLocaleString()}개
        </p>
      </header>

      {/* Top 10 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">emoji_events</span>
          Top 10 — 자동 매매 추천 종목
        </h3>
        <div className="space-y-4">
          {top10.map((stock, i) => {
            const color = getGradeColor(stock.grade);
            const opGrowth = fmtGrowth(stock.op_profit_latest, stock.op_profit_prev);
            const revGrowth = fmtGrowth(stock.revenue_latest, stock.revenue_prev);
            const fwdPer = stock.eps_consensus && stock.eps_consensus > 0 && stock.current_price > 0
              ? (stock.current_price / stock.eps_consensus).toFixed(1) + "배"
              : "-";
            const epsGrowth = stock.eps_current && stock.eps_current > 0 && stock.eps_consensus && stock.eps_consensus > 0
              ? ((stock.eps_consensus - stock.eps_current) / stock.eps_current * 100).toFixed(0) + "%"
              : "-";

            return (
              <div key={stock.code} className="bg-surface-container-low rounded-xl ghost-border p-4 sm:p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-xl font-serif font-bold w-8 flex items-center gap-1" style={{ color }}>
                      {i + 1}
                      <RankChange currentRank={i + 1} previousRank={stock.previous_rank} />
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-base font-medium text-on-surface">{stock.name}</h4>
                        <span className="text-xs px-2 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>
                          {stock.grade}
                        </span>
                        <span className="text-xs text-on-surface-variant/50">{stock.market}</span>
                        {stock.shareholderBadges?.cancellation && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#95d3ba20", color: "#95d3ba" }}>소각</span>
                        )}
                        {stock.shareholderBadges?.dividend && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#e9c17620", color: "#e9c176" }}>배당</span>
                        )}
                        {stock.shareholderBadges?.dilution && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#ffb4ab20", color: "#ffb4ab" }}>희석주의</span>
                        )}
                      </div>
                      <p className="text-sm text-on-surface-variant">{stock.code} · 시총 {fmtNum(stock.market_cap)}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <GradeChangeBadge grade={stock.grade} score={stock.score} previousScore={stock.previous_score} compact />
                      <p className="text-2xl font-serif font-bold" style={{ color }}>{stock.score}</p>
                    </div>
                    <p className="text-xs text-on-surface-variant">/100점</p>
                  </div>
                </div>

                <ScoreChangeComment score={stock.score} previousScore={stock.previous_score} grade={stock.grade} details={stock.details} previousDetails={stock.previous_details} scoreHistory={stock.score_history} />

                {/* 핵심 지표 */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
                  {[
                    { label: "영업이익 성장", value: opGrowth },
                    { label: "매출 성장", value: revGrowth },
                    { label: "Forward PER", value: fwdPer },
                    { label: "컨센서스 EPS 성장", value: epsGrowth },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-surface-container/30 rounded-lg p-2 text-center">
                      <p className="text-xs text-on-surface-variant">{label}</p>
                      <p className="text-sm font-mono text-on-surface mt-0.5">{value}</p>
                    </div>
                  ))}
                </div>

                {/* 카테고리 점수 */}
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { label: "성장 모멘텀", score: stock.cat1, max: 45 },
                    { label: "밸류에이션", score: stock.cat2, max: 35 },
                    { label: "안전장치", score: stock.cat3, max: 20 },
                    { label: "주주환원", score: stock.details.filter((d) => d.cat === 4).reduce((s, d) => s + d.score, 0), max: 5 },
                  ].map(({ label, score, max }) => {
                    const pct = max > 0 ? (score / max) * 100 : 0;
                    return (
                      <div key={label} className="text-center">
                        <p className="text-xs text-on-surface-variant mb-1">{label}</p>
                        <div className="h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{
                            width: `${pct}%`,
                            backgroundColor: pct >= 70 ? "#95d3ba" : pct >= 50 ? "#e9c176" : "#ffb4ab",
                          }} />
                        </div>
                        <p className="text-xs font-mono text-on-surface mt-0.5">{score}/{max}</p>
                      </div>
                    );
                  })}
                </div>

                {/* 세부 채점 */}
                <Collapsible title="세부 채점">
                  <div className="space-y-1 mt-2">
                    {stock.details.map((d) => (
                      <div key={d.item} className="flex items-center justify-between text-sm py-1">
                        <span className="text-on-surface-variant">{d.item}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-on-surface-variant/60">{d.basis}</span>
                          <span className="font-mono text-on-surface" style={{
                            color: d.score < 0 ? "#ffb4ab" : undefined,
                          }}>
                            {d.max > 0 ? `${d.score}/${d.max}` : d.score > 0 ? `+${d.score}` : `${d.score}`}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </Collapsible>
              </div>
            );
          })}
        </div>
      </section>

      {/* 11~30위 테이블 */}
      {rest.length > 0 && (
        <Collapsible title={`11~${10 + rest.length}위 후보군`}>
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                  <th className="text-center px-2 pb-2 font-normal">순위</th>
                  <th className="text-left px-2 pb-2 font-normal">종목</th>
                  <th className="text-center px-2 pb-2 font-normal hidden sm:table-cell">추세</th>
                  <th className="text-center px-2 pb-2 font-normal">등급</th>
                  <th className="text-right px-2 pb-2 font-normal">점수</th>
                  <th className="text-right px-2 pb-2 font-normal hidden sm:table-cell">시총</th>
                  <th className="text-right px-2 pb-2 font-normal hidden sm:table-cell">PER</th>
                  <th className="text-right px-2 pb-2 font-normal hidden lg:table-cell">영업이익 성장</th>
                </tr>
              </thead>
              <tbody>
                {rest.map((stock, i) => {
                  const color = getGradeColor(stock.grade);
                  return (
                    <tr key={stock.code} className="border-t border-surface-container-highest/30">
                      <td className="text-center px-2 py-2 font-mono" style={{ color }}>
                        <span className="inline-flex items-center gap-1">{i + 11}<RankChange currentRank={i + 11} previousRank={stock.previous_rank} /></span>
                      </td>
                      <td className="px-2 py-2">
                        <span className="text-on-surface">{stock.name}</span>
                        <span className="text-xs text-on-surface-variant/50 ml-1.5">{stock.market}</span>
                      </td>
                      <td className="text-center px-2 py-2 hidden sm:table-cell">
                        <RankTrendSparkline trend={getStockTrend(rankHistory, stock.code)} stockName={stock.name} totalStocks={data.candidates.length} />
                      </td>
                      <td className="text-center px-2 py-2">
                        <span className="text-xs px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: `${color}20`, color }}>
                          {stock.grade}
                        </span>
                      </td>
                      <td className="text-right px-2 py-2 font-mono font-bold" style={{ color }}>
                        <span className="inline-flex items-center justify-end gap-1">
                          <GradeChangeBadge grade={stock.grade} score={stock.score} previousScore={stock.previous_score} compact />
                          {stock.score}
                        </span>
                      </td>
                      <td className="text-right px-2 py-2 font-mono text-on-surface-variant hidden sm:table-cell">{fmtNum(stock.market_cap)}</td>
                      <td className="text-right px-2 py-2 font-mono text-on-surface-variant hidden sm:table-cell">{stock.per?.toFixed(1) ?? "-"}</td>
                      <td className="text-right px-2 py-2 font-mono text-on-surface-variant hidden lg:table-cell">{fmtGrowth(stock.op_profit_latest, stock.op_profit_prev)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Collapsible>
      )}

      {/* 채점 기준 */}
      <Collapsible title="채점 기준">
        <div className="space-y-4 mt-3">
          <div className="bg-surface-container-low rounded-xl p-4 ghost-border">
            <h4 className="text-sm font-serif text-on-surface mb-2">Cat1: 성장 모멘텀 (45점)</h4>
            <div className="text-xs text-on-surface-variant space-y-1">
              <p>컨센서스 EPS 성장률 (15) · 영업이익 성장률 YoY (12) · 매출 성장률 YoY (8) · 영업이익률 개선 (10)</p>
            </div>
          </div>
          <div className="bg-surface-container-low rounded-xl p-4 ghost-border">
            <h4 className="text-sm font-serif text-on-surface mb-2">Cat2: 성장 대비 밸류에이션 (35점)</h4>
            <div className="text-xs text-on-surface-variant space-y-1">
              <p>Forward PER (15) · PER (10) · PEG (10)</p>
              <p>Forward PER = 현재가 ÷ 컨센서스 EPS. 미래 이익 대비 현재 가격이 싼지를 판단합니다.</p>
            </div>
          </div>
          <div className="bg-surface-container-low rounded-xl p-4 ghost-border">
            <h4 className="text-sm font-serif text-on-surface mb-2">Cat3: 안전장치 (20점)</h4>
            <div className="text-xs text-on-surface-variant space-y-1">
              <p>흑자 지속 연수 (10) · 영업이익률 수준 (10)</p>
            </div>
          </div>
          <div className="bg-surface-container-low rounded-xl p-4 ghost-border">
            <div className="flex items-start gap-2">
              <span className="material-symbols-outlined text-on-surface-variant text-base mt-0.5">info</span>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                코스피+코스닥 전체에서 시총 500억 이상 흑자 기업만 대상.
                외국인 비중·시총 규모·배당률·PBR은 성장과 무관하여 의도적으로 제외.
                영업이익 역성장 종목은 D등급 고정. 금리 환경 감점 적용.
              </p>
            </div>
          </div>
        </div>
      </Collapsible>
    </div>
  );
}
