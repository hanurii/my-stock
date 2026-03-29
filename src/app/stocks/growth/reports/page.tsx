import fs from "fs";
import path from "path";
import Link from "next/link";
import { getGradeColor } from "@/lib/scoring";

// ── 타입 ──

interface NewsItem {
  title: string;
  link: string;
  source: string;
  date: string;
}

interface DartDisclosure {
  title: string;
  link: string;
  date: string;
  type: string;
}

interface StockReport {
  code: string;
  name: string;
  sector: string;
  score: number;
  grade: string;
  cat1: number;
  cat2: number;
  cat3: number;
  highlights: string;
  catalyst: string;
  strengths: string[];
  weaknesses: string[];
  shareholder_summary: {
    cancellation_years: number;
    dividend_history: { year: number; dps: number | null }[];
    dilutive_count: number;
    dilutive_types: Record<string, number>;
  };
  news: NewsItem[];
  disclosures: DartDisclosure[];
  risk_flags: string[];
}

interface ReportData {
  generated_at: string;
  description: string;
  stocks: StockReport[];
}

// ── 데이터 로드 ──

function getReportData(): ReportData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "stock-reports.json");
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as ReportData;
  } catch {
    return null;
  }
}

// ── 컴포넌트 ──

function TagList({ items, color }: { items: string[]; color: string }) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item, i) => (
        <span
          key={i}
          className="text-xs px-2 py-0.5 rounded"
          style={{ backgroundColor: `${color}15`, color }}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function Section({ icon, title, children }: { icon: string; title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <span className="material-symbols-outlined text-on-surface-variant text-sm">{icon}</span>
        <h5 className="text-sm font-medium text-on-surface-variant">{title}</h5>
      </div>
      {children}
    </div>
  );
}

function StockReportCard({ stock }: { stock: StockReport }) {
  const color = getGradeColor(stock.grade);
  const sh = stock.shareholder_summary;

  return (
    <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
      <div className="p-5 sm:p-6 space-y-5">
        {/* 헤더 */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-lg font-medium text-on-surface">{stock.name}</h3>
              <span
                className="text-xs px-2 py-0.5 rounded font-bold"
                style={{ backgroundColor: `${color}20`, color }}
              >
                {stock.grade}
              </span>
              {stock.risk_flags.length > 0 && (
                <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: "#ffb4ab20", color: "#ffb4ab" }}>
                  {stock.risk_flags.length}개 리스크
                </span>
              )}
            </div>
            <p className="text-sm text-on-surface-variant mt-0.5">
              {stock.code} · {stock.sector}
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-serif font-bold" style={{ color }}>{stock.score}</p>
            <p className="text-xs text-on-surface-variant">/100점</p>
          </div>
        </div>

        {/* 하이라이트 */}
        {stock.highlights && (
          <p className="text-sm text-on-surface-variant leading-relaxed">{stock.highlights}</p>
        )}

        {/* 카테고리 점수 바 */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: "성장성", score: stock.cat1, max: 35 },
            { label: "밸류에이션", score: stock.cat2, max: 30 },
            { label: "경쟁력/시그널", score: stock.cat3, max: 35 },
          ].map(({ label, score, max }) => {
            const pct = max > 0 ? (score / max) * 100 : 0;
            return (
              <div key={label} className="text-center">
                <p className="text-xs text-on-surface-variant mb-1">{label}</p>
                <div className="h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: pct >= 70 ? "#95d3ba" : pct >= 50 ? "#e9c176" : "#ffb4ab",
                    }}
                  />
                </div>
                <p className="text-xs font-mono text-on-surface mt-0.5">{score}/{max}</p>
              </div>
            );
          })}
        </div>

        {/* 강점 / 약점 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Section icon="thumb_up" title="강점">
            <TagList items={stock.strengths} color="#95d3ba" />
          </Section>
          <Section icon="thumb_down" title="약점">
            <TagList items={stock.weaknesses} color="#e9c176" />
          </Section>
        </div>

        {/* 리스크 플래그 */}
        {stock.risk_flags.length > 0 && (
          <Section icon="warning" title="리스크 플래그">
            <TagList items={stock.risk_flags} color="#ffb4ab" />
          </Section>
        )}

        {/* 주주환원 */}
        <Section icon="volunteer_activism" title="주주환원 현황">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="bg-surface-container/30 rounded-lg p-2">
              <p className="text-xs text-on-surface-variant">자사주 소각</p>
              <p className="text-sm font-mono text-on-surface mt-0.5"
                style={{ color: sh.cancellation_years > 0 ? "#95d3ba" : undefined }}>
                {sh.cancellation_years > 0 ? `${sh.cancellation_years}년 실적` : "없음"}
              </p>
            </div>
            <div className="bg-surface-container/30 rounded-lg p-2">
              <p className="text-xs text-on-surface-variant">배당 이력</p>
              <p className="text-sm font-mono text-on-surface mt-0.5"
                style={{ color: sh.dividend_history.some((d) => d.dps && d.dps > 0) ? "#e9c176" : undefined }}>
                {sh.dividend_history.filter((d) => d.dps && d.dps > 0).length > 0
                  ? sh.dividend_history.filter((d) => d.dps && d.dps > 0).map((d) => `${d.year}:${d.dps}원`).join(" · ")
                  : "없음"}
              </p>
            </div>
            <div className="bg-surface-container/30 rounded-lg p-2">
              <p className="text-xs text-on-surface-variant">희석 이벤트</p>
              <p className="text-sm font-mono text-on-surface mt-0.5"
                style={{ color: sh.dilutive_count > 0 ? "#ffb4ab" : undefined }}>
                {sh.dilutive_count > 0
                  ? `${sh.dilutive_count}건`
                  : "없음"}
              </p>
            </div>
          </div>
        </Section>

        {/* DART 공시 */}
        {stock.disclosures.length > 0 && (
          <Section icon="description" title="DART 최근 공시">
            <div className="space-y-1">
              {stock.disclosures.map((d, i) => (
                <a
                  key={i}
                  href={d.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-2 text-sm text-on-surface-variant hover:text-primary transition-colors"
                >
                  <span className="text-xs text-on-surface-variant/50 shrink-0 mt-0.5">{d.date}</span>
                  <span className="line-clamp-1">{d.title}</span>
                </a>
              ))}
            </div>
          </Section>
        )}

        {/* 뉴스 */}
        {stock.news.length > 0 && (
          <Section icon="newspaper" title="최근 뉴스">
            <div className="space-y-1">
              {stock.news.map((n, i) => (
                <a
                  key={i}
                  href={n.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-2 text-sm text-on-surface-variant hover:text-primary transition-colors"
                >
                  <span className="text-xs text-on-surface-variant/50 shrink-0 mt-0.5">[{n.source}]</span>
                  <span className="line-clamp-1">{n.title}</span>
                </a>
              ))}
            </div>
          </Section>
        )}

        {/* 촉매 */}
        {stock.catalyst && (
          <Section icon="bolt" title="촉매/모멘텀">
            <p className="text-sm text-on-surface-variant">{stock.catalyst}</p>
          </Section>
        )}
      </div>
    </div>
  );
}

// ── 메인 ──

export default function GrowthReportsPage() {
  const data = getReportData();

  return (
    <div className="space-y-10">
      {/* 헤더 */}
      <header>
        <div className="flex items-center gap-3 mb-2">
          <Link
            href="/stocks/growth"
            className="text-on-surface-variant hover:text-primary transition-colors"
          >
            <span className="material-symbols-outlined text-xl">arrow_back</span>
          </Link>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            종목 리서치 리포트
          </h1>
        </div>
        <p className="text-sm text-on-surface-variant">
          {data ? `${data.generated_at} 기준 · 상위 ${data.stocks.length}개 저평가 성장주` : "데이터 없음"}
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          채점 데이터 + DART 공시 + 뉴스를 종합한 리서치 자료입니다. 최종 투자 판단은 추가 조사 후 직접 하세요.
        </p>
      </header>

      {!data || data.stocks.length === 0 ? (
        <div className="bg-surface-container-low rounded-xl p-8 text-center ghost-border">
          <p className="text-on-surface-variant">
            리서치 리포트가 아직 생성되지 않았습니다.
          </p>
          <p className="text-sm text-on-surface-variant/50 mt-2">
            npx tsx scripts/collect-stock-reports.ts 를 실행하세요.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {data.stocks.map((stock) => (
            <StockReportCard key={stock.code} stock={stock} />
          ))}
        </div>
      )}
    </div>
  );
}
