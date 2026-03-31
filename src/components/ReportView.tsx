import { IndicatorTable } from "@/components/IndicatorTable";
import { ChartsSection } from "@/components/ChartsSection";
import { MarkdownText } from "@/components/MarkdownText";
import type { ReportData } from "@/lib/data";

// ── 마크다운 테이블 파싱 (investment_direction, asset_recommendation 공용) ──

function MarkdownTable({ tableLines, keyPrefix }: { tableLines: string[]; keyPrefix: string }) {
  const dataRows = tableLines.filter((l) => !l.match(/^\|[\s-|]+$/));
  if (dataRows.length < 1) return null;

  const headerCells = dataRows[0].split("|").filter((c) => c.trim());
  const bodyRows = dataRows.slice(1);

  return (
    <div className="rounded-xl overflow-x-auto ghost-border my-4">
      <table className="text-base">
        <thead>
          <tr>
            {headerCells.map((cell, ci) => (
              <th key={`${keyPrefix}-h-${ci}`} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-on-surface-variant/50 font-normal bg-surface-container/50 whitespace-nowrap">
                {cell.trim()}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, ri) => {
            const cells = row.split("|").filter((c) => c.trim());
            return (
              <tr key={`${keyPrefix}-r-${ri}`} className="hover:bg-surface-container-high/30 transition-colors">
                {cells.map((cell, ci) => (
                  <td key={ci} className="px-4 py-3 text-base text-on-surface-variant leading-relaxed whitespace-nowrap">
                    <MarkdownText>{cell.trim()}</MarkdownText>
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function ReportView({ report }: { report: ReportData }) {
  const {
    meta, briefing, scenario, indicators, spread,
    causal_chain, investment_direction, news,
    cpi_gdp, divergence, historical, asset_recommendation,
  } = report;

  const isDraft = !briefing || briefing.trim() === "";

  return (
    <div className="space-y-12">
      {/* ── Hero Header ── */}
      <section>
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
            Daily Macro Report
          </p>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
            거시경제 데일리 리포트
          </h2>
          <p className="text-base text-on-surface-variant mt-2">
            {meta.generated_at} ({meta.weekday}) 기준
          </p>
        </div>
        {isDraft && (
          <div className="mt-4 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
            <p className="text-sm text-amber-400 flex items-center gap-2">
              <span className="material-symbols-outlined text-base">hourglass_top</span>
              분석 대기 중 — 데이터는 수집되었으나 AI 분석이 아직 완료되지 않았습니다.
            </p>
          </div>
        )}
      </section>

      {/* ── Briefing ── */}
      {isDraft ? (
        <section className="glass-card rounded-xl p-5 sm:p-8 ghost-border overflow-hidden opacity-50">
          <div className="flex items-center gap-3 mb-4">
            <span className="material-symbols-outlined text-on-surface-variant text-2xl">hourglass_top</span>
            <h3 className="text-xl font-serif text-on-surface-variant tracking-tight">
              오늘의 거시경제 브리핑
            </h3>
          </div>
          <p className="text-base text-on-surface-variant italic">분석 섹션 생성 대기 중...</p>
        </section>
      ) : (
        <section className="glass-card rounded-xl p-5 sm:p-8 ghost-border overflow-hidden">
          <div className="flex items-center gap-3 mb-6">
            <span className="material-symbols-outlined text-primary text-2xl">auto_awesome</span>
            <h3 className="text-xl font-serif text-on-surface tracking-tight">
              오늘의 거시경제 브리핑
            </h3>
          </div>
          <div className="space-y-4">
            {briefing.split("\n").map((line, i) => {
              if (line.startsWith("## ") || line.startsWith("### ") || !line.trim()) return null;
              return (
                <p key={i} className="text-base text-on-surface-variant leading-[1.8]">
                  <MarkdownText>{line}</MarkdownText>
                </p>
              );
            })}
          </div>
        </section>
      )}

      {/* ── Indicator Dashboard ── */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
          핵심 지표 대시보드
        </h3>
        <p className="text-sm text-on-surface-variant mb-6">
          전일 대비 변동과 주간 추세. 빨간색은 상승, 파란색은 하락.
        </p>

        <div className="grid gap-5">
          <div className="grid grid-cols-1 gap-5">
            <IndicatorTable title="한국 시장" indicators={indicators.korea} />
            <IndicatorTable title="미국 시장" indicators={indicators.us} />
          </div>
          <div className="grid grid-cols-1 gap-5">
            <IndicatorTable title="환율" indicators={indicators.fx} />
            <IndicatorTable title="채권 금리" indicators={indicators.bonds} />
          </div>

          {/* 장단기 금리차 */}
          {spread && !("error" in spread) && (
            <div className="bg-surface-container-low rounded-xl p-5 ghost-border flex flex-wrap items-center gap-6">
              <span className="text-base text-on-surface-variant">장단기 금리차</span>
              <span className={`text-xl font-mono font-bold ${spread.금리차 < 0 ? "text-error" : "text-tertiary"}`}>
                {spread.금리차}%
              </span>
              <span className="text-sm text-on-surface-variant">
                {spread.상태} · 10년물 {spread["10년물"]}% | 3개월물 {spread["3개월물"]}%
              </span>
            </div>
          )}

          <IndicatorTable title="원자재 & 변동성" indicators={indicators.commodities} />
        </div>
      </section>

      {/* ── Causal Chain ── */}
      <section className="bg-surface-container-low rounded-xl p-5 sm:p-8 ghost-border">
        <h3 className="text-xl font-serif text-on-surface mb-5 tracking-tight">
          오늘의 인과관계 분석
        </h3>
        <div className="space-y-6">
          {causal_chain.split("\n\n").map((block, bi) => {
            const lines = block.split("\n").filter((l) => l.trim());
            if (lines.length === 0) return null;

            // 제목 추출 (**제목**)
            const titleLine = lines.find((l) => l.startsWith("**") && l.endsWith("**"));
            const contentLines = lines.filter(
              (l) => l !== titleLine && !l.trim().startsWith("```")
            );

            if (!titleLine && contentLines.length === 0) return null;

            return (
              <div key={bi} className="bg-surface-container-lowest rounded-xl p-5">
                {titleLine && (
                  <h4 className="text-base font-bold text-primary mb-3 font-serif">
                    {titleLine.replace(/\*\*/g, "")}
                  </h4>
                )}
                <div className="space-y-1.5">
                  {contentLines.map((line, li) => {
                    const trimmed = line.trim();
                    if (trimmed.startsWith("→")) {
                      return (
                        <div key={li} className="flex items-start gap-2 pl-2">
                          <span className="text-primary text-sm mt-0.5">→</span>
                          <span className="text-base text-on-surface-variant leading-relaxed">
                            {trimmed.slice(1).trim()}
                          </span>
                        </div>
                      );
                    }
                    return (
                      <p key={li} className="text-base text-on-surface leading-relaxed">
                        {trimmed}
                      </p>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Investment Direction ── */}
      <section className="bg-surface-container-low rounded-xl p-5 sm:p-8 ghost-border">
        <h3 className="text-xl font-serif text-on-surface mb-5 tracking-tight">
          이번 주 투자 방향
        </h3>
        <div className="space-y-3">
          {(() => {
            const lines = investment_direction.split("\n");
            const elements: React.ReactNode[] = [];
            let i = 0;
            let isSubTopic = false; // 3) 이후 하위 주제 여부

            while (i < lines.length) {
              const line = lines[i];

              // 제목 (**제목**)
              if (line.startsWith("**") && line.endsWith("**")) {
                const title = line.replace(/\*\*/g, "");
                // 번호로 시작하는 대주제 (1), 2), 3) 등)
                const isMainHeading = /^\d+\)/.test(title);
                if (isMainHeading) {
                  isSubTopic = /^3\)/.test(title);
                  elements.push(
                    <h4 key={i} className="text-lg font-bold text-primary mt-8 mb-3 first:mt-0 font-serif">
                      {title}
                    </h4>
                  );
                } else if (isSubTopic) {
                  // 3) 하위 주제: 더 작은 크기 + 다른 색상
                  elements.push(
                    <h5 key={i} className="text-base font-semibold text-on-surface mt-6 mb-2 font-serif">
                      {title}
                    </h5>
                  );
                } else {
                  elements.push(
                    <h4 key={i} className="text-lg font-bold text-primary mt-8 mb-3 first:mt-0 font-serif">
                      {title}
                    </h4>
                  );
                }
                i++;
                continue;
              }

              // 마크다운 테이블 (| 로 시작하는 연속된 행)
              if (line.startsWith("|")) {
                const tableLines: string[] = [];
                while (i < lines.length && lines[i].startsWith("|")) {
                  tableLines.push(lines[i]);
                  i++;
                }
                elements.push(<MarkdownTable key={`table-${i}`} tableLines={tableLines} keyPrefix={`inv-${i}`} />);
                continue;
              }

              // 리스트 항목
              if (line.startsWith("- ")) {
                elements.push(
                  <p key={i} className="text-base text-on-surface-variant pl-4 border-l-2 border-primary/20 leading-[1.8]">
                    <MarkdownText>{line.slice(2)}</MarkdownText>
                  </p>
                );
                i++;
                continue;
              }

              // 빈 줄 무시
              if (!line.trim()) {
                i++;
                continue;
              }

              // 일반 텍스트
              elements.push(
                <p key={i} className="text-base text-on-surface-variant leading-[1.8]">
                  {line}
                </p>
              );
              i++;
            }

            return elements;
          })()}
        </div>
      </section>

      {/* ── CPI / GDP Matrix ── */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
          성장-물가 매트릭스
        </h3>
        <p className="text-sm text-on-surface-variant mb-6">
          CPI(물가)와 GDP(성장률)로 현재 경제의 위치를 판단합니다.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
          <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
            <h4 className="text-xs uppercase tracking-[0.15em] text-primary-dim/60 mb-4">Consumer Price Index</h4>
            <div className="space-y-4">
              {[
                { flag: "🇺🇸", label: "미국", d: cpi_gdp.us_cpi },
                { flag: "🇰🇷", label: "한국", d: cpi_gdp.kr_cpi },
              ].map(({ flag, label, d }) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-base text-on-surface">{flag} {label}</span>
                  <div className="text-right">
                    <span className="text-lg font-mono text-on-surface">
                      {d?.전년동월대비 != null ? `${d.전년동월대비 > 0 ? "+" : ""}${d.전년동월대비}%` : "—"}
                    </span>
                    <p className="text-xs text-on-surface-variant mt-0.5">{d?.날짜}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface-container-low rounded-xl p-6 ghost-border">
            <h4 className="text-xs uppercase tracking-[0.15em] text-primary-dim/60 mb-4">GDP Growth Rate</h4>
            <div className="space-y-4">
              {[
                { flag: "🇺🇸", label: "미국", d: cpi_gdp.us_gdp },
                { flag: "🇰🇷", label: "한국", d: cpi_gdp.kr_gdp },
              ].map(({ flag, label, d }) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-base text-on-surface">{flag} {label}</span>
                  <div className="text-right">
                    <span className="text-lg font-mono text-on-surface">
                      {d?.성장률 != null ? `${d.성장률 > 0 ? "+" : ""}${d.성장률}%` : "—"}
                    </span>
                    <p className="text-xs text-on-surface-variant mt-0.5">{d?.날짜}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-surface-container rounded-xl p-5 ghost-border">
            <p className="text-sm tracking-[0.1em] text-primary-dim/60 mb-2">📍 미국</p>
            <p className="text-xl font-serif text-primary">{cpi_gdp.matrix_us?.위치}</p>
            <p className="text-base text-on-surface-variant mt-2 leading-relaxed">{cpi_gdp.matrix_us?.해석}</p>
          </div>
          <div className="bg-surface-container rounded-xl p-5 ghost-border">
            <p className="text-sm tracking-[0.1em] text-primary-dim/60 mb-2">📍 한국</p>
            <p className="text-xl font-serif text-primary">{cpi_gdp.matrix_kr?.위치}</p>
            <p className="text-base text-on-surface-variant mt-2 leading-relaxed">{cpi_gdp.matrix_kr?.해석}</p>
          </div>
        </div>
      </section>

      {/* ── Asset Recommendation ── */}
      {asset_recommendation && asset_recommendation.trim() && (
        <section className="bg-surface-container-low rounded-xl p-5 sm:p-8 ghost-border">
          <h3 className="text-xl font-serif text-on-surface mb-5 tracking-tight">
            현재 환경에서의 자산별 판단
          </h3>
          <div className="space-y-3">
            {(() => {
              const lines = asset_recommendation.split("\n");
              const elements: React.ReactNode[] = [];
              let i = 0;

              while (i < lines.length) {
                const line = lines[i];

                // 마크다운 테이블
                if (line.startsWith("|")) {
                  const tableLines: string[] = [];
                  while (i < lines.length && lines[i].startsWith("|")) {
                    tableLines.push(lines[i]);
                    i++;
                  }
                  elements.push(<MarkdownTable key={`table-${i}`} tableLines={tableLines} keyPrefix={`asset-${i}`} />);
                  continue;
                }

                // blockquote
                if (line.startsWith(">")) {
                  elements.push(
                    <p key={i} className="text-base text-on-surface-variant pl-4 border-l-2 border-primary/20 leading-[1.8]">
                      <MarkdownText>{line.slice(1).trim()}</MarkdownText>
                    </p>
                  );
                  i++;
                  continue;
                }

                // details/summary (접힌 메뉴) 스킵
                if (line.startsWith("<details") || line.startsWith("</details") || line.startsWith("<summary") || line.startsWith("</summary")) {
                  i++;
                  continue;
                }

                // 소제목
                if (line.startsWith("###")) {
                  elements.push(
                    <h4 key={i} className="text-lg font-bold text-primary mt-6 mb-3 font-serif">
                      {line.replace(/^#+\s*/, "")}
                    </h4>
                  );
                  i++;
                  continue;
                }

                if (!line.trim()) { i++; continue; }

                elements.push(
                  <p key={i} className="text-base text-on-surface-variant leading-[1.8]">
                    <MarkdownText>{line}</MarkdownText>
                  </p>
                );
                i++;
              }
              return elements;
            })()}
          </div>
        </section>
      )}

      {/* ── Divergence Warning ── */}
      {divergence && divergence.trim() && (
        <section className="bg-surface-container-low rounded-xl p-5 sm:p-8 ghost-border border-l-2 border-primary">
          <div className="flex items-center gap-3 mb-4">
            <span className="material-symbols-outlined text-primary">warning</span>
            <h3 className="text-lg font-serif text-primary tracking-tight">괴리 감지</h3>
          </div>
          <div className="text-base text-on-surface-variant leading-[1.8] space-y-2">
            {divergence.replace(/### ⚠️ 괴리 감지\n*/g, "").replace(/> /g, "").split("\n").map((line, i) =>
              line.trim() ? <p key={i}><MarkdownText>{line}</MarkdownText></p> : null
            )}
          </div>
        </section>
      )}

      {/* ── Historical Position ── */}
      {historical && historical.length > 0 && (
        <section>
          <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
            역사적 위치 분석
          </h3>
          <p className="text-sm text-on-surface-variant mb-6">
            현재값이 역사적으로 어디에 위치하는지 파악합니다.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {historical.map((h) => {
              const barWidth = Math.max(0, Math.min(100, h.percentile));

              // 이모지로 색상 결정 (유니코드 코드포인트 기준)
              const judgment = h.judgment || "";
              const firstChar = judgment.codePointAt(0);
              let dotColor = "#909097"; // 기본 회색
              if (firstChar === 0x1F534) dotColor = "#ffb4ab";      // 🔴
              else if (firstChar === 0x1F7E1) dotColor = "#e9c176"; // 🟡
              else if (firstChar === 0x1F7E2) dotColor = "#95d3ba"; // 🟢
              else if (firstChar === 0x1F535) dotColor = "#6ea8fe"; // 🔵
              // ⚪ (0x26AA) = 기본 회색 유지

              // 선행 이모지 제거 (정확한 유니코드 코드포인트)
              const judgmentText = judgment.replace(/^(\u{1F534}|\u{1F7E1}|\u{1F7E2}|\u{1F535}|\u{26AA})\s*/u, "");

              return (
                <div key={h.name} className="bg-surface-container-low rounded-xl p-5 ghost-border">
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="text-base font-medium text-on-surface">{h.name}</h4>
                    <span className="text-sm font-mono text-primary">
                      {h.current.toLocaleString()} {h.unit}
                    </span>
                  </div>
                  <div className="mb-3">
                    <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${barWidth}%`, backgroundColor: dotColor }} />
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="text-[10px] text-on-surface-variant">{h.all_low.toLocaleString()}</span>
                      <span className="text-[10px]" style={{ color: dotColor }}>{h.percentile.toFixed(0)}%</span>
                      <span className="text-[10px] text-on-surface-variant">{h.all_high.toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="mt-0.5 shrink-0 w-2 h-2 rounded-full" style={{ backgroundColor: dotColor }} />
                    <p className="text-xs leading-relaxed" style={{ color: dotColor }}>
                      {judgmentText}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ── News ── */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface mb-2 tracking-tight">
          주요 경제 뉴스
        </h3>
        <p className="text-sm text-on-surface-variant mb-6">매일경제 · 한국경제</p>
        <div className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
          {news.map((article, i) => (
            <a
              key={i}
              href={article.링크}
              target="_blank"
              rel="noopener noreferrer"
              className={`flex items-start gap-4 px-6 py-4 hover:bg-surface-container/50 transition-colors group ${
                i % 2 === 1 ? "bg-surface-container/20" : ""
              }`}
            >
              <span className="text-primary-dim/40 text-sm font-mono mt-0.5 shrink-0">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="flex-1">
                <p className="text-base text-on-surface group-hover:text-primary transition-colors leading-snug">
                  {article.제목}
                </p>
                <p className="text-xs text-on-surface-variant/50 mt-1.5">{article.출처}</p>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant/30 group-hover:text-primary/50 transition-colors text-base mt-0.5">
                open_in_new
              </span>
            </a>
          ))}
        </div>
      </section>

      {/* ── Charts ── */}
      <ChartsSection report={report} />
    </div>
  );
}
