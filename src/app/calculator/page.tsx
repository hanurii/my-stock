import fs from "fs";
import path from "path";
import { Collapsible } from "@/components/Collapsible";

interface QuarterlyData {
  quarter: string;
  eps: number;
  revenue: number;
  operating_income: number;
  net_income: number;
  op_margin: number;
}

interface YearlyData {
  year: number;
  eps: number;
  dps: number;
  bps: number;
  payout_ratio: number;
  per: number;
  pbr: number;
  revenue: number;
  operating_income: number;
  net_income: number;
  op_margin: number;
}

interface StockData {
  code: string;
  name: string;
  is_preferred: boolean;
  current_price: number;
  quarterly?: QuarterlyData[];
  latest: {
    eps: number;
    per: number | null;
    bps: number;
    pbr: number | null;
    dps: number;
    dividend_yield: number | null;
    payout_ratio: number | null;
    basis_year: number;
  };
  history: YearlyData[];
}

interface CalculatorData {
  generated_at: string;
  source: string;
  stocks: StockData[];
}

const DATA_DIR = path.join(process.cwd(), "public", "data");
const CALCULATOR_PATH = path.join(DATA_DIR, "calculator.json");
const ARCHIVE_PATH = path.join(DATA_DIR, "calculator-archive.json");

/**
 * 과거 재무 데이터(history)를 병합한다.
 * 같은 연도가 있으면 최신(incoming) 데이터를 우선한다.
 */
function mergeHistory(existing: YearlyData[], incoming: YearlyData[]): YearlyData[] {
  const map = new Map<number, YearlyData>();
  for (const h of existing) map.set(h.year, h);
  for (const h of incoming) map.set(h.year, h); // 최신 우선
  return Array.from(map.values()).sort((a, b) => a.year - b.year);
}

/**
 * 최신 calculator.json과 아카이브를 병합하여 반환한다.
 * 병합 결과는 아카이브에 자동 저장된다.
 */
function getCalculatorData(): CalculatorData | null {
  try {
    const raw = fs.readFileSync(CALCULATOR_PATH, "utf-8");
    const latest = JSON.parse(raw) as CalculatorData;

    // 아카이브 로드
    let archive: CalculatorData | null = null;
    try {
      const archiveRaw = fs.readFileSync(ARCHIVE_PATH, "utf-8");
      archive = JSON.parse(archiveRaw) as CalculatorData;
    } catch {
      // 아카이브 없음 — 첫 실행
    }

    if (archive) {
      // 아카이브의 각 종목 히스토리를 최신 데이터와 병합
      for (const stock of latest.stocks) {
        const archived = archive.stocks.find((s) => s.code === stock.code);
        if (archived) {
          stock.history = mergeHistory(archived.history, stock.history);
        }
      }

      // 아카이브에만 있고 최신에 없는 종목도 보존
      for (const archived of archive.stocks) {
        if (!latest.stocks.find((s) => s.code === archived.code)) {
          latest.stocks.push(archived);
        }
      }
    }

    // 병합 결과를 아카이브로 저장
    try {
      fs.writeFileSync(ARCHIVE_PATH, JSON.stringify(latest, null, 2), "utf-8");
    } catch {
      // 빌드 환경 등에서 쓰기 실패 시 무시
    }

    return latest;
  } catch {
    // calculator.json이 없으면 아카이브에서라도 로드
    try {
      const archiveRaw = fs.readFileSync(ARCHIVE_PATH, "utf-8");
      return JSON.parse(archiveRaw) as CalculatorData;
    } catch {
      return null;
    }
  }
}

export default function CalculatorPage() {
  const data = getCalculatorData();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
        <p className="text-on-surface-variant text-base">calculator.json이 아직 생성되지 않았습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Financial Statements
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          재무제표 계산기
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          {data.generated_at} 기준 · DART 공시 데이터 기반
        </p>
        <p className="text-sm text-on-surface-variant/60 mt-1">
          실적 발표 직후 최신 EPS로 PER을 계산합니다. 증권사 반영 전에 먼저 확인하세요.
        </p>
      </section>

      {/* 목차 */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <h3 className="text-base font-serif text-on-surface mb-4">목차</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {data.stocks.map((stock) => (
            <a
              key={stock.code}
              href={`#stock-${stock.code}`}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-container-high/50 transition-colors group"
            >
              <span className="text-primary-dim/40 group-hover:text-primary transition-colors text-sm">→</span>
              <span className="text-base text-on-surface group-hover:text-primary transition-colors">
                {stock.name}
              </span>
              {stock.is_preferred && (
                <span className="text-[10px] text-primary/50">우선주</span>
              )}
            </a>
          ))}
        </div>
      </section>

      {/* Stock Cards */}
      {data.stocks.map((stock) => {
        const sortedHistory = [...stock.history]
          .filter((h) => h.eps || h.dps || h.bps)
          .sort((a, b) => b.year - a.year);

        return (
          <section
            key={stock.code}
            id={`stock-${stock.code}`}
            className="bg-surface-container-low rounded-xl ghost-border overflow-hidden scroll-mt-8"
          >
            {/* ── Stock Header ── */}
            <div className="p-5 sm:p-8 flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="text-2xl font-serif text-on-surface tracking-tight">{stock.name}</h3>
                  {stock.is_preferred && (
                    <span className="text-xs uppercase tracking-wider bg-primary/10 text-primary px-2.5 py-1 rounded">
                      우선주
                    </span>
                  )}
                </div>
                <p className="text-base text-on-surface-variant mt-1.5">{stock.code}</p>
              </div>
              <div className="sm:text-right">
                <p className="text-xs text-on-surface-variant/50 mb-1">현재 종가</p>
                <p className="text-3xl sm:text-4xl font-serif text-primary tracking-tight">
                  {stock.current_price.toLocaleString()}
                  <span className="text-lg text-on-surface-variant ml-1">원</span>
                </p>
              </div>
            </div>

            {/* ── Latest Metrics ── */}
            <div className="px-5 sm:px-8 pb-5 sm:pb-8">
              <div className="flex items-center gap-2 mb-5">
                <h4 className="text-lg font-serif text-primary">최신 지표</h4>
                <span className="text-sm text-on-surface-variant">
                  — {stock.latest.basis_year}년 사업보고서 기준
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
                {[
                  { label: "EPS", value: stock.latest.eps, unit: "원", desc: "주당순이익" },
                  { label: "PER", value: stock.latest.per, unit: "배", desc: "현재 주가 ÷ EPS" },
                  { label: "BPS", value: stock.latest.bps, unit: "원", desc: "주당순자산" },
                  { label: "PBR", value: stock.latest.pbr, unit: "배", desc: "현재 주가 ÷ BPS" },
                  { label: "배당수익률", value: stock.latest.dividend_yield, unit: "%", desc: "배당금 ÷ 현재 주가" },
                  { label: "주당배당금", value: stock.latest.dps, unit: "원", desc: "확정 배당" },
                ].map((m) => (
                  <div key={m.label} className="bg-surface-container rounded-xl p-3 sm:p-5 ghost-border">
                    <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-2">{m.label}</p>
                    <p className="text-xl sm:text-2xl font-mono text-on-surface leading-tight break-all">
                      {m.value != null ? m.value.toLocaleString() : "—"}
                      <span className="text-sm text-on-surface-variant ml-1">{m.unit}</span>
                    </p>
                    <p className="text-xs text-on-surface-variant/40 mt-2">{m.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* ── 연도별 전체 추이 (접기/펼치기) ── */}
            {sortedHistory.length > 0 && (
              <div className="px-5 sm:px-8 pb-5 sm:pb-8">
                <Collapsible title="연도별 전체 추이">
                  <div className="overflow-x-auto">
                    <table className="w-full text-base">
                      <thead>
                        <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                          <th className="text-left px-4 pb-3 font-normal">연도</th>
                          <th className="text-right px-4 pb-3 font-normal">매출</th>
                          <th className="text-right px-4 pb-3 font-normal">영업이익</th>
                          <th className="text-right px-4 pb-3 font-normal">영업이익률</th>
                          <th className="text-right px-4 pb-3 font-normal">EPS</th>
                          <th className="text-right px-4 pb-3 font-normal">PER</th>
                          <th className="text-right px-4 pb-3 font-normal">PBR</th>
                          <th className="text-right px-4 pb-3 font-normal">배당금</th>
                          <th className="text-right px-4 pb-3 font-normal">배당성향</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sortedHistory.map((h, i) => (
                          <tr
                            key={h.year}
                            className={`transition-colors ${
                              i === 0 ? "bg-primary/5 hover:bg-primary/10" : "hover:bg-surface-container/30"
                            }`}
                          >
                            <td className={`px-4 py-3 font-medium ${i === 0 ? "text-primary" : "text-on-surface"}`}>
                              {h.year}
                              {i === 0 && <span className="text-xs text-primary/60 ml-2">최신</span>}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.revenue ? `${(h.revenue / 1e8).toLocaleString(undefined, { maximumFractionDigits: 0 })}억` : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.operating_income ? `${(h.operating_income / 1e8).toLocaleString(undefined, { maximumFractionDigits: 0 })}억` : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.op_margin ? `${h.op_margin}%` : "—"}
                            </td>
                            <td className={`px-4 py-3 text-right font-mono ${h.eps > 0 ? "text-on-surface" : h.eps < 0 ? "text-[#ffb4ab]" : "text-on-surface-variant/40"}`}>
                              {h.eps ? h.eps.toLocaleString() : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.per ? `${h.per}배` : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.pbr ? `${h.pbr}배` : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface">
                              {h.dps ? h.dps.toLocaleString() : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                              {h.payout_ratio ? `${h.payout_ratio}%` : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Collapsible>
              </div>
            )}
          </section>
        );
      })}

      {/* Guide */}
      <section className="bg-surface-container-low rounded-xl p-8 ghost-border">
        <h3 className="text-lg font-serif text-on-surface mb-5">사용 가이드</h3>
        <div className="space-y-4 text-base text-on-surface-variant leading-relaxed">
          <p>
            <strong className="text-on-surface">최신 PER</strong> — 현재 주가를 가장 최근 공시된 EPS로 나눈 값입니다.
            실적 발표 직후 증권사보다 먼저 확인할 수 있습니다.
            PER이 낮을수록 이익 대비 주가가 저평가된 것입니다.
          </p>
          <p>
            <strong className="text-on-surface">배당수익률</strong> — 확정된 주당배당금을 현재 주가로 나눈 값입니다.
            은행 이자와 비교하여 투자 매력도를 판단할 수 있습니다.
          </p>
          <p>
            <strong className="text-on-surface">연도별 추이</strong> — 10년간 EPS와 배당금의 추세를 보면
            기업의 성장성과 주주환원 의지를 파악할 수 있습니다.
            EPS와 배당금이 꾸준히 늘어나는 기업이 좋은 기업입니다.
          </p>
        </div>
      </section>

      {/* BPS 가이드 */}
      <section className="bg-surface-container-low rounded-xl p-8 ghost-border">
        <h3 className="text-lg font-serif text-on-surface mb-5">BPS(주당 순자산가치) 가이드</h3>
        <div className="space-y-6 text-base text-on-surface-variant leading-relaxed">
          <p>
            주식 투자에서 <strong className="text-on-surface">BPS(Book-value Per Share)</strong>는{" "}
            <strong className="text-primary">&apos;주당 순자산가치&apos;</strong>를 의미합니다.
            기업의 재무 건전성과 내재 가치를 판단할 때 아주 중요한 지표 중 하나입니다.
          </p>
          <p>
            쉽게 요약하자면, <strong className="text-on-surface">&quot;오늘 당장 회사가 문을 닫고 모든 자산을 팔아 빚을 갚은 뒤,
            남은 돈을 주주들에게 나눠준다면 주당 얼마씩 돌아가는가?&quot;</strong>를 나타내는 수치입니다.
          </p>

          {/* 1. 계산 방법 */}
          <div>
            <h4 className="text-base font-bold text-on-surface mb-3">1. BPS 계산 방법</h4>
            <p className="mb-3">
              BPS는 기업의 <strong className="text-on-surface">순자산(자기자본)</strong>을 발행 주식 총수로 나누어 산출합니다.
            </p>
            <div className="bg-surface-container rounded-xl p-5 ghost-border text-center font-mono text-lg text-primary mb-3">
              BPS = 순자산(총자산 − 총부채) ÷ 발행 주식 총수
            </div>
            <ul className="space-y-1.5 pl-4">
              <li className="flex items-start gap-2">
                <span className="text-primary mt-0.5">·</span>
                <span><strong className="text-on-surface">순자산:</strong> 자본금, 자본잉여금, 이익잉여금 등을 모두 합친 금액입니다.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary mt-0.5">·</span>
                <span><strong className="text-on-surface">의미:</strong> BPS가 높을수록 기업의 수익성이나 재무 구조가 탄탄하여 &apos;알짜배기&apos; 기업일 가능성이 높습니다.</span>
              </li>
            </ul>
          </div>

          {/* 2. 활용법 */}
          <div>
            <h4 className="text-base font-bold text-on-surface mb-3">2. BPS를 어떻게 활용하나요?</h4>

            <div className="space-y-4">
              <div>
                <p className="font-semibold text-on-surface mb-1.5">① 주가와의 비교</p>
                <ul className="space-y-1.5 pl-4">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">·</span>
                    <span><strong className="text-on-surface">현재 주가 &gt; BPS:</strong> 시장에서 기업의 미래 성장성을 높게 평가하여 자산 가치보다 더 비싸게 거래되고 있다는 뜻입니다.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">·</span>
                    <span><strong className="text-on-surface">현재 주가 &lt; BPS:</strong> 기업이 가진 실제 자산 가치보다 주가가 낮게 형성된 상태로, 흔히 &apos;저평가&apos; 되었다고 판단합니다.</span>
                  </li>
                </ul>
              </div>

              <div>
                <p className="font-semibold text-on-surface mb-1.5">② PBR(주가순자산비율)과의 관계</p>
                <ul className="space-y-1.5 pl-4">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">·</span>
                    <span>BPS는 PBR 지표를 구하는 기초가 됩니다. PBR은 현재 주가를 BPS로 나눈 값입니다.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">·</span>
                    <span><strong className="text-on-surface">PBR이 1배 미만</strong>이라면, 주가가 주당 순자산가치에도 못 미친다는 의미이므로 청산 가치보다 낮게 거래되고 있다고 봅니다.</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* 3. 유의할 점 */}
          <div>
            <h4 className="text-base font-bold text-on-surface mb-3">3. 투자 시 유의할 점</h4>
            <p className="mb-3">
              BPS가 높거나 주가보다 크다고 해서 무조건 좋은 주식은 아닙니다.
            </p>
            <ul className="space-y-1.5 pl-4">
              <li className="flex items-start gap-2">
                <span className="text-primary mt-0.5">·</span>
                <span><strong className="text-on-surface">업종별 특성:</strong> 제조나 금융업처럼 실물 자산이나 자본이 중요한 업종은 BPS가 중요하지만, 소프트웨어나 서비스업 같은 고성장주는 무형 자산의 가치가 커서 BPS가 상대적으로 낮게 나타날 수 있습니다.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary mt-0.5">·</span>
                <span><strong className="text-on-surface">자산의 질:</strong> 장부상 순자산이 많더라도 실제 현금화하기 어려운 노후 설비나 악성 재고가 포함되어 있을 수 있으므로 재무제표를 함께 살피는 것이 좋습니다.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
