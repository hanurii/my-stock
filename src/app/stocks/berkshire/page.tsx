import fs from "fs";
import path from "path";
import { Collapsible } from "@/components/Collapsible";
import { SectorPieChart } from "@/components/SectorPieChart";
import { formatUSD } from "@/lib/format";

// ── 타입 ──

interface Holding {
  rank: number;
  name: string;
  name_kr: string | null;
  ticker: string | null;
  cusip: string;
  title_of_class: string;
  value: number;
  shares: number;
  weight_pct: number;
  sector: string | null;
}

interface ChangeEntry {
  name: string;
  ticker: string | null;
  cusip: string;
  current_shares: number;
  previous_shares: number;
  current_value: number;
  change_pct: number;
  current_weight_pct: number;
}

interface CashDataPoint {
  period: string;
  cash: number;
  cash_equivalents: number;
  total_assets: number;
  cash_ratio_pct: number;
}

interface Berkshire13FData {
  generated_at: string;
  latest: {
    accession_number: string;
    filing_date: string;
    report_period: string;
    total_value: number;
    total_positions: number;
    holdings: Holding[];
    changes: {
      new_buys: ChangeEntry[];
      increased: ChangeEntry[];
      decreased: ChangeEntry[];
      exits: ChangeEntry[];
    };
    sectors: { sector: string; value: number; weight_pct: number; count: number }[];
    concentration: { top5_pct: number; top10_pct: number };
  };
  cash_trend: CashDataPoint[];
  history: {
    accession_number: string;
    filing_date: string;
    report_period: string;
    total_value: number;
    total_positions: number;
    top5: { name: string; ticker: string | null; weight_pct: number }[];
  }[];
}

// ── 데이터 로드 ──

function getData(): Berkshire13FData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "berkshire-13f.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as Berkshire13FData;
  } catch {
    return null;
  }
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00Z");
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

function displayName(name: string, nameKr: string | null): string {
  return nameKr ? `${name} (${nameKr})` : name;
}

const SECTOR_KR: Record<string, string> = {
  Financials: "금융",
  Technology: "기술",
  "Consumer Staples": "필수소비재",
  Energy: "에너지",
  Communication: "커뮤니케이션",
  Healthcare: "헬스케어",
  "Consumer Discretionary": "임의소비재",
  Materials: "소재",
  Industrials: "산업재",
  "Real Estate": "부동산",
  ETF: "ETF",
};

function sectorKr(sector: string): string {
  return SECTOR_KR[sector] ? `${sector} (${SECTOR_KR[sector]})` : sector;
}

function formatShares(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return n.toLocaleString();
}

// ── 변화 테이블 ──

function ChangeSection({ title, icon, color, entries, holdingsMap }: {
  title: string;
  icon: string;
  color: string;
  entries: ChangeEntry[];
  holdingsMap: Map<string, Holding>;
}) {
  if (entries.length === 0) return null;

  return (
    <div className="bg-surface-container-low rounded-xl p-5 ghost-border">
      <div className="flex items-center gap-2 mb-4">
        <span className="material-symbols-outlined text-lg" style={{ color }}>{icon}</span>
        <h4 className="text-base font-serif text-on-surface">{title}</h4>
        <span className="text-xs text-on-surface-variant ml-auto">{entries.length}개</span>
      </div>
      <div className="space-y-2">
        {entries.map((e) => {
          const h = holdingsMap.get(e.cusip);
          const nameKr = h?.name_kr ?? null;
          return (
          <div key={e.cusip} className="flex items-center justify-between py-2 px-3 rounded-lg bg-surface-container/30">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-on-surface">{displayName(e.name, nameKr)}</span>
              {e.ticker && <span className="text-xs font-mono text-on-surface-variant">{e.ticker}</span>}
            </div>
            <div className="flex items-center gap-4 text-sm">
              {e.previous_shares > 0 && e.current_shares > 0 && (
                <span className="text-on-surface-variant font-mono">
                  {formatShares(e.previous_shares)} → {formatShares(e.current_shares)}
                </span>
              )}
              {e.previous_shares > 0 && e.current_shares === 0 && (
                <span className="text-on-surface-variant font-mono">
                  {formatShares(e.previous_shares)}주
                </span>
              )}
              {e.previous_shares === 0 && (
                <span className="font-mono text-on-surface">{formatUSD(e.current_value)}</span>
              )}
              <span className="font-mono font-bold" style={{ color }}>
                {e.change_pct > 0 ? "+" : ""}{e.change_pct.toFixed(1)}%
              </span>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 시장 총평 자동 생성 ──

interface Insight {
  icon: string;
  color: string;
  title: string;
  body: string;
}

function generateInsights(
  latest: Berkshire13FData["latest"],
  history: Berkshire13FData["history"],
  cashTrend: CashDataPoint[],
): Insight[] {
  const insights: Insight[] = [];
  const { holdings, changes, sectors, concentration } = latest;

  // 1. 현금 추이 분석
  if (cashTrend.length >= 3) {
    const recent = cashTrend[0];
    const prev = cashTrend[1];
    const older = cashTrend[cashTrend.length - 1];
    const cashTrendUp = recent.cash > older.cash;
    const cashChange = prev.cash > 0 ? ((recent.cash - prev.cash) / prev.cash) * 100 : 0;

    if (Math.abs(cashChange) > 20) {
      const direction = cashChange > 0 ? "증가" : "감소";
      insights.push({
        icon: cashChange > 0 ? "savings" : "payments",
        color: cashChange > 0 ? "#95d3ba" : "#e9c176",
        title: `현금성자산 전 분기 대비 ${Math.abs(cashChange).toFixed(0)}% ${direction}`,
        body: `${formatUSD(prev.cash)} → ${formatUSD(recent.cash)}.` +
          (cashChange > 0
            ? " 주식을 매도하고 현금을 쌓고 있습니다. 시장 고평가 또는 더 좋은 기회를 기다리는 시그널입니다."
            : " 현금을 소진하며 투자에 나서고 있습니다. 매력적인 투자처를 발견했거나 시장 저평가 판단 시그널입니다."),
      });
    } else if (cashTrendUp && recent.cash_ratio_pct > 5) {
      insights.push({
        icon: "savings",
        color: "#95d3ba",
        title: `현금 비율 ${recent.cash_ratio_pct}% — 장기 평균 대비 높은 수준`,
        body: "현금을 많이 보유하고 있다는 것은 적극적으로 투자할 곳을 찾지 못하고 있다는 의미입니다.",
      });
    }
  }

  // 2. 포트폴리오 가치 추이
  if (history.length >= 2) {
    const prevValue = history[0].total_value;
    const valueChange = ((latest.total_value - prevValue) / prevValue) * 100;
    const posChange = latest.total_positions - history[0].total_positions;

    if (Math.abs(valueChange) > 3 || Math.abs(posChange) >= 3) {
      const valueDir = valueChange > 0 ? "증가" : "감소";
      insights.push({
        icon: valueChange > 0 ? "trending_up" : "trending_down",
        color: valueChange > 0 ? "#6ea8fe" : "#ffb4ab",
        title: `주식 포트폴리오 ${formatUSD(prevValue)} → ${formatUSD(latest.total_value)} (${valueChange > 0 ? "+" : ""}${valueChange.toFixed(1)}%)`,
        body: `전 분기 대비 포트폴리오 가치가 ${valueDir}했으며, 종목 수는 ${history[0].total_positions}개 → ${latest.total_positions}개로 변화했습니다.` +
          (valueChange < -5 ? " 대규모 매도가 진행 중일 수 있습니다." : ""),
      });
    }
  }

  // 3. 주요 매매 활동
  if (changes.decreased.length > 0) {
    const bigSells = changes.decreased.filter((c) => c.change_pct < -30);
    if (bigSells.length > 0) {
      const names = bigSells.map((c) => {
        const h = holdings.find((x) => x.cusip === c.cusip);
        const label = h?.name_kr || c.ticker || c.name;
        return `${label}(${c.change_pct.toFixed(0)}%)`;
      }).join(", ");
      insights.push({
        icon: "remove_circle",
        color: "#ffb4ab",
        title: "대규모 비중 축소 감지",
        body: `${names}을 30% 이상 축소했습니다. 해당 종목 또는 섹터에 대한 확신이 줄어든 시그널입니다.`,
      });
    }
  }

  if (changes.new_buys.length > 0) {
    const names = changes.new_buys.map((c) => {
      const h = holdings.find((x) => x.cusip === c.cusip);
      return h?.name_kr || c.ticker || c.name;
    }).join(", ");
    insights.push({
      icon: "add_circle",
      color: "#95d3ba",
      title: `${changes.new_buys.length}개 종목 신규 편입`,
      body: `${names}. 버핏이 새로 주목하는 기업들입니다. 해당 산업의 장기 전망에 대한 긍정적 시각으로 해석할 수 있습니다.`,
    });
  }

  if (changes.exits.length > 0) {
    const names = changes.exits.map((c) => {
      const h = holdings.find((x) => x.cusip === c.cusip);
      return h?.name_kr || c.ticker || c.name;
    }).join(", ");
    insights.push({
      icon: "cancel",
      color: "#ffb4ab",
      title: `${changes.exits.length}개 종목 전량 매도`,
      body: `${names} 포지션을 완전히 청산했습니다.`,
    });
  }

  // 4. 섹터 집중도 분석
  const topSector = sectors[0];
  if (topSector && topSector.weight_pct > 35) {
    const sectorLabel: Record<string, string> = {
      Financials: "금융주는 고금리 환경에서 수익이 좋은 섹터입니다. 이 비중이 높다는 것은 고금리가 당분간 지속될 것이라는 판단을 시사합니다.",
      Technology: "기술 섹터에 강한 확신을 보이고 있습니다.",
      Energy: "에너지 가격이 구조적으로 높은 수준을 유지할 것이라는 장기적 뷰로 읽힙니다.",
      "Consumer Staples": "경기 방어적 필수소비재에 집중하고 있어, 경기 둔화를 대비하는 포지션입니다.",
      Healthcare: "헬스케어 섹터의 장기 성장에 베팅하고 있습니다.",
    };
    insights.push({
      icon: "pie_chart",
      color: "#e9c176",
      title: `${sectorKr(topSector.sector)} ${topSector.weight_pct}% — 포트폴리오의 핵심`,
      body: sectorLabel[topSector.sector] || `${topSector.sector} 섹터에 가장 큰 비중을 두고 있습니다.`,
    });
  }

  // 5. 집중도 코멘트
  if (concentration.top5_pct > 65) {
    const top5Names = holdings.slice(0, 5).map((h) => h.name_kr || h.ticker || h.name).join(", ");
    insights.push({
      icon: "target",
      color: "#c084fc",
      title: `Top 5 집중도 ${concentration.top5_pct}%`,
      body: `${top5Names}. 확신 있는 소수 종목에 자산을 집중하는 버핏의 전형적인 스타일입니다. 확신이 줄어든 종목은 빠르게 정리하는 경향이 있습니다.`,
    });
  }

  // 6. 1위 종목 분석
  const top = holdings[0];
  if (top && history.length > 0) {
    const prevTop = history[0].top5?.[0];
    if (prevTop) {
      const prevWeight = prevTop.weight_pct;
      const weightChange = top.weight_pct - prevWeight;
      if (Math.abs(weightChange) > 2) {
        insights.push({
          icon: weightChange > 0 ? "arrow_upward" : "arrow_downward",
          color: weightChange > 0 ? "#6ea8fe" : "#fb923c",
          title: `1위 ${top.name_kr || top.ticker || top.name} 비중 ${prevWeight}% → ${top.weight_pct}%`,
          body: weightChange > 0
            ? "최대 보유 종목의 비중이 늘었습니다. 추가 매수이거나 주가 상승에 따른 자연 증가입니다."
            : "최대 보유 종목의 비중을 줄이고 있습니다. 차익 실현 또는 리스크 관리로 해석됩니다.",
        });
      }
    }
  }

  return insights;
}

// ── 페이지 ──

export default function BerkshirePage() {
  const data = getData();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
        <p className="text-on-surface-variant">13F 데이터를 먼저 수집해주세요.</p>
      </div>
    );
  }

  const { latest, history, cash_trend } = data;
  const { holdings, changes, sectors, concentration } = latest;

  const hasChanges = changes.new_buys.length + changes.increased.length + changes.decreased.length + changes.exits.length > 0;
  const holdingsMap = new Map(holdings.map((h) => [h.cusip, h]));

  // ── 시장 총평 자동 생성 ──
  const insights = generateInsights(latest, history, cash_trend);

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Berkshire Hathaway 13F Holdings
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          버크셔 해서웨이 포트폴리오
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          SEC 13F 공시 기준 · {latest.total_positions}개 포지션 · {formatUSD(latest.total_value)}
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1.5">
          공시일: {formatDate(latest.filing_date)} · 기준일: {formatDate(latest.report_period)}
        </p>
      </section>

      {/* Market Commentary */}
      <section className="bg-surface-container-low rounded-xl p-5 sm:p-8 ghost-border">
        <div className="flex items-center gap-3 mb-5">
          <span className="material-symbols-outlined text-primary text-2xl">psychology</span>
          <h3 className="text-xl font-serif text-on-surface tracking-tight">
            버핏의 포트폴리오에서 읽는 시장 시그널
          </h3>
        </div>
        <div className="space-y-4">
          {insights.map((insight, i) => (
            <div key={i} className="flex items-start gap-3">
              <span
                className="material-symbols-outlined text-lg mt-0.5 shrink-0"
                style={{ color: insight.color }}
              >
                {insight.icon}
              </span>
              <div>
                <p className="text-sm font-bold text-on-surface mb-1">{insight.title}</p>
                <p className="text-sm text-on-surface-variant leading-relaxed">{insight.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Portfolio Changes */}
      {hasChanges && (
        <section>
          <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
            포트폴리오 변화
          </h3>
          <p className="text-sm text-on-surface-variant mb-6">이전 분기 대비 변동 사항</p>
          <div className="grid gap-5">
            <ChangeSection title="신규 매수" icon="add_circle" color="#95d3ba" entries={changes.new_buys} holdingsMap={holdingsMap} />
            <ChangeSection title="비중 확대" icon="trending_up" color="#6ea8fe" entries={changes.increased} holdingsMap={holdingsMap} />
            <ChangeSection title="비중 축소" icon="trending_down" color="#fb923c" entries={changes.decreased} holdingsMap={holdingsMap} />
            <ChangeSection title="전량 매도" icon="remove_circle" color="#ffb4ab" entries={changes.exits} holdingsMap={holdingsMap} />
          </div>
        </section>
      )}

      {/* Top Holdings Table */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
          보유 종목
        </h3>
        <p className="text-sm text-on-surface-variant mb-6">{latest.total_positions}개 포지션 · 평가액 내림차순</p>

        <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                  <th className="text-center px-3 pb-3 pt-4 font-normal w-10">#</th>
                  <th className="text-left px-3 pb-3 pt-4 font-normal">종목</th>
                  <th className="text-left px-3 pb-3 pt-4 font-normal hidden md:table-cell">티커</th>
                  <th className="text-right px-3 pb-3 pt-4 font-normal hidden md:table-cell">보유주식</th>
                  <th className="text-right px-3 pb-3 pt-4 font-normal">평가금액</th>
                  <th className="text-right px-3 pb-3 pt-4 font-normal">비중</th>
                  <th className="text-left px-3 pb-3 pt-4 font-normal hidden lg:table-cell">섹터</th>
                </tr>
              </thead>
              <tbody>
                {holdings.slice(0, 20).map((h) => (
                  <tr key={h.cusip} className={`hover:bg-surface-container/30 transition-colors ${h.rank === 1 ? "bg-primary/5" : ""}`}>
                    <td className="text-center px-3 py-2.5 font-mono text-primary">{h.rank}</td>
                    <td className="px-3 py-2.5 font-medium text-on-surface">
                      {h.name}
                      {h.name_kr && <span className="text-on-surface-variant text-xs ml-1">({h.name_kr})</span>}
                      <span className="md:hidden text-xs text-on-surface-variant ml-1.5">{h.ticker}</span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">{h.ticker || "—"}</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">{formatShares(h.shares)}</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface">{formatUSD(h.value)}</td>
                    <td className="text-right px-3 py-2.5 font-mono font-bold text-primary">{h.weight_pct}%</td>
                    <td className="px-3 py-2.5 text-on-surface-variant hidden lg:table-cell">{h.sector ? sectorKr(h.sector) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {holdings.length > 20 && (
          <div className="mt-4">
            <Collapsible title={`나머지 ${holdings.length - 20}개 종목`}>
              <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <tbody>
                      {holdings.slice(20).map((h) => (
                        <tr key={h.cusip} className="hover:bg-surface-container/30 transition-colors">
                          <td className="text-center px-3 py-2 font-mono text-on-surface-variant w-10">{h.rank}</td>
                          <td className="px-3 py-2 text-on-surface">
                            {h.name}
                            {h.name_kr && <span className="text-xs text-on-surface-variant ml-1">({h.name_kr})</span>}
                            {h.ticker && <span className="text-xs text-on-surface-variant ml-1.5">{h.ticker}</span>}
                          </td>
                          <td className="text-right px-3 py-2 font-mono text-on-surface-variant hidden md:table-cell">{formatShares(h.shares)}</td>
                          <td className="text-right px-3 py-2 font-mono text-on-surface">{formatUSD(h.value)}</td>
                          <td className="text-right px-3 py-2 font-mono text-primary">{h.weight_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </Collapsible>
          </div>
        )}
      </section>

      {/* Sector Allocation */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
          섹터 배분
        </h3>
        <p className="text-sm text-on-surface-variant mb-6">포트폴리오 섹터별 비중</p>
        <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <SectorPieChart sectors={sectors.map(s => ({ ...s, sector: sectorKr(s.sector) }))} totalValue={latest.total_value} />
        </div>
      </section>

      {/* Cash Trend */}
      {cash_trend && cash_trend.length > 0 && (
        <section>
          <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
            현금성자산 추이
          </h3>
          <p className="text-sm text-on-surface-variant mb-6">
            10-Q/10-K 기준 현금 및 현금성자산 (단기 재무부채권 제외)
          </p>
          <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                    <th className="text-left px-4 pb-3 pt-4 font-normal">기준일</th>
                    <th className="text-right px-4 pb-3 pt-4 font-normal">현금성자산</th>
                    <th className="text-right px-4 pb-3 pt-4 font-normal">총자산</th>
                    <th className="text-right px-4 pb-3 pt-4 font-normal">현금 비율</th>
                    <th className="text-left px-4 pb-3 pt-4 font-normal hidden md:table-cell">추세</th>
                  </tr>
                </thead>
                <tbody>
                  {cash_trend.map((c, i) => {
                    const prevCash = cash_trend[i + 1]?.cash;
                    const isIncrease = prevCash != null && c.cash > prevCash;
                    const isDecrease = prevCash != null && c.cash < prevCash;
                    const isLatest = i === 0;

                    return (
                      <tr key={c.period} className={`hover:bg-surface-container/30 transition-colors ${isLatest ? "bg-primary/5" : ""}`}>
                        <td className={`px-4 py-3 font-mono ${isLatest ? "text-primary" : "text-on-surface-variant"}`}>
                          {formatDate(c.period)}
                        </td>
                        <td className="text-right px-4 py-3 font-mono text-on-surface font-bold">
                          {formatUSD(c.cash)}
                        </td>
                        <td className="text-right px-4 py-3 font-mono text-on-surface-variant">
                          {formatUSD(c.total_assets)}
                        </td>
                        <td className="text-right px-4 py-3 font-mono font-bold" style={{
                          color: c.cash_ratio_pct >= 6 ? "#95d3ba" : c.cash_ratio_pct >= 4 ? "#e9c176" : "#ffb4ab"
                        }}>
                          {c.cash_ratio_pct}%
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell">
                          {isIncrease && (
                            <span className="text-xs text-emerald-400 flex items-center gap-1">
                              <span className="material-symbols-outlined text-sm">trending_up</span>
                              현금 증가
                            </span>
                          )}
                          {isDecrease && (
                            <span className="text-xs text-red-400 flex items-center gap-1">
                              <span className="material-symbols-outlined text-sm">trending_down</span>
                              현금 감소
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
          <div className="mt-3 flex items-start gap-2 px-1">
            <span className="material-symbols-outlined text-on-surface-variant/40 text-sm mt-0.5">info</span>
            <p className="text-xs text-on-surface-variant/50 leading-relaxed">
              XBRL 공시 기준 현금 및 현금성자산입니다. 버크셔가 대량 보유한 단기 재무부채권(T-Bills)은
              별도 항목으로 분류되어 이 수치에 포함되지 않으므로, 실제 유동성은 이보다 훨씬 큽니다.
              주식 포트폴리오 가치가 줄면서 현금이 늘어나는 패턴은 버핏의 시장 고평가 판단 시그널입니다.
            </p>
          </div>
        </section>
      )}

      {/* Equity Portfolio Value Trend */}
      {history.length > 0 && (
        <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
          <div className="flex items-start gap-3">
            <span className="material-symbols-outlined text-primary text-xl mt-0.5">monitoring</span>
            <div className="space-y-2">
              <h3 className="text-base font-serif text-on-surface">주식 포트폴리오 가치 추이</h3>
              <div className="flex flex-wrap gap-4 mt-3">
                {[...history].reverse().map((h) => (
                  <div key={h.report_period} className="text-center">
                    <p className="text-xs text-on-surface-variant">{formatDate(h.report_period).slice(2)}</p>
                    <p className="text-sm font-mono text-on-surface">{formatUSD(h.total_value)}</p>
                    <p className="text-[10px] text-on-surface-variant/50">{h.total_positions}종목</p>
                  </div>
                ))}
                <div className="text-center">
                  <p className="text-xs text-primary">{formatDate(latest.report_period).slice(2)}</p>
                  <p className="text-sm font-mono text-primary font-bold">{formatUSD(latest.total_value)}</p>
                  <p className="text-[10px] text-primary/50">{latest.total_positions}종목</p>
                </div>
              </div>
              <p className="text-xs text-on-surface-variant/50 mt-2">
                13F 주식 포트폴리오만 반영. 현금, 채권, 비상장 투자는 미포함.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Historical Comparison */}
      {history.length > 0 && (
        <section>
          <Collapsible title="분기별 추이">
            <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                      <th className="text-left px-4 pb-3 pt-4 font-normal">기준일</th>
                      <th className="text-left px-4 pb-3 pt-4 font-normal">공시일</th>
                      <th className="text-right px-4 pb-3 pt-4 font-normal">총 평가액</th>
                      <th className="text-right px-4 pb-3 pt-4 font-normal">종목수</th>
                      <th className="text-left px-4 pb-3 pt-4 font-normal hidden md:table-cell">Top 3</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* 현재 */}
                    <tr className="bg-primary/5">
                      <td className="px-4 py-3 font-mono text-primary">{formatDate(latest.report_period)}</td>
                      <td className="px-4 py-3 text-on-surface-variant">{formatDate(latest.filing_date)}</td>
                      <td className="text-right px-4 py-3 font-mono text-on-surface font-bold">{formatUSD(latest.total_value)}</td>
                      <td className="text-right px-4 py-3 font-mono text-on-surface">{latest.total_positions}</td>
                      <td className="px-4 py-3 text-on-surface-variant hidden md:table-cell">
                        {holdings.slice(0, 3).map((h) => h.ticker || h.name).join(", ")}
                      </td>
                    </tr>
                    {/* 히스토리 */}
                    {history.map((h) => (
                      <tr key={h.accession_number} className="hover:bg-surface-container/30 transition-colors">
                        <td className="px-4 py-3 font-mono text-on-surface-variant">{formatDate(h.report_period)}</td>
                        <td className="px-4 py-3 text-on-surface-variant">{formatDate(h.filing_date)}</td>
                        <td className="text-right px-4 py-3 font-mono text-on-surface">{formatUSD(h.total_value)}</td>
                        <td className="text-right px-4 py-3 font-mono text-on-surface">{h.total_positions}</td>
                        <td className="px-4 py-3 text-on-surface-variant hidden md:table-cell">
                          {h.top5.slice(0, 3).map((t) => t.ticker || t.name).join(", ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Collapsible>
        </section>
      )}

      {/* Disclaimer */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-on-surface-variant/50 text-lg mt-0.5">info</span>
          <div className="space-y-2 text-sm text-on-surface-variant leading-relaxed">
            <p>
              <strong className="text-on-surface">13F 보고서의 한계:</strong> 분기 종료 후 최대 45일 뒤 공개되므로,
              현재 시점의 포트폴리오와 다를 수 있습니다. 미국 상장 주식/ETF만 포함되며,
              현금, 채권, 비상장 투자는 반영되지 않습니다.
            </p>
            <p>
              이 데이터는 SEC EDGAR에서 자동 수집된 것으로, 투자 조언이 아닙니다.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
