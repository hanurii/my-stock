import fs from "fs";
import path from "path";
import { Collapsible } from "@/components/Collapsible";
import { SectorPieChart } from "@/components/SectorPieChart";
import { formatUSD } from "@/lib/format";

// ── 타입 ──

interface Holding {
  rank: number;
  name: string;
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
  const d = new Date(dateStr + "T00:00:00");
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

function formatShares(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return n.toLocaleString();
}

// ── 변화 테이블 ──

function ChangeSection({ title, icon, color, entries }: {
  title: string;
  icon: string;
  color: string;
  entries: ChangeEntry[];
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
        {entries.map((e) => (
          <div key={e.cusip} className="flex items-center justify-between py-2 px-3 rounded-lg bg-surface-container/30">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-on-surface">{e.name}</span>
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
        ))}
      </div>
    </div>
  );
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

      {/* Investment Signals */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-primary text-xl mt-0.5">psychology</span>
          <div className="space-y-2">
            <h3 className="text-base font-serif text-on-surface">투자 시그널</h3>
            <div className="space-y-1.5 text-sm text-on-surface-variant leading-relaxed">
              <p>
                <strong className="text-on-surface">집중도:</strong> Top 5 종목이 포트폴리오의{" "}
                <span className="font-mono text-primary">{concentration.top5_pct}%</span>를 차지합니다.
                {concentration.top5_pct > 70 && " 매우 집중된 포트폴리오입니다."}
                {concentration.top5_pct <= 70 && concentration.top5_pct > 50 && " 상당히 집중된 포트폴리오입니다."}
              </p>
              {hasChanges && (
                <p>
                  <strong className="text-on-surface">변화:</strong>{" "}
                  {changes.new_buys.length > 0 && <span className="text-tertiary">{changes.new_buys.length}개 신규 매수</span>}
                  {changes.new_buys.length > 0 && changes.exits.length > 0 && ", "}
                  {changes.exits.length > 0 && <span className="text-error">{changes.exits.length}개 전량 매도</span>}
                  {(changes.new_buys.length > 0 || changes.exits.length > 0) && changes.increased.length > 0 && ", "}
                  {changes.increased.length > 0 && <span className="text-info">{changes.increased.length}개 비중 확대</span>}
                  {(changes.new_buys.length > 0 || changes.exits.length > 0 || changes.increased.length > 0) && changes.decreased.length > 0 && ", "}
                  {changes.decreased.length > 0 && <span className="text-on-surface-variant">{changes.decreased.length}개 비중 축소</span>}
                </p>
              )}
              <p>
                <strong className="text-on-surface">1위:</strong>{" "}
                {holdings[0]?.ticker || holdings[0]?.name} ({holdings[0]?.weight_pct}%) —{" "}
                {holdings[0]?.weight_pct > 25
                  ? "단일 종목 비중이 매우 높습니다."
                  : "포트폴리오의 핵심 종목입니다."}
              </p>
            </div>
          </div>
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
            <ChangeSection title="신규 매수" icon="add_circle" color="#95d3ba" entries={changes.new_buys} />
            <ChangeSection title="비중 확대" icon="trending_up" color="#6ea8fe" entries={changes.increased} />
            <ChangeSection title="비중 축소" icon="trending_down" color="#fb923c" entries={changes.decreased} />
            <ChangeSection title="전량 매도" icon="remove_circle" color="#ffb4ab" entries={changes.exits} />
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
                      <span className="md:hidden text-xs text-on-surface-variant ml-1.5">{h.ticker}</span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">{h.ticker || "—"}</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface-variant hidden md:table-cell">{formatShares(h.shares)}</td>
                    <td className="text-right px-3 py-2.5 font-mono text-on-surface">{formatUSD(h.value)}</td>
                    <td className="text-right px-3 py-2.5 font-mono font-bold text-primary">{h.weight_pct}%</td>
                    <td className="px-3 py-2.5 text-on-surface-variant hidden lg:table-cell">{h.sector || "—"}</td>
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
          <SectorPieChart sectors={sectors} totalValue={latest.total_value} />
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
