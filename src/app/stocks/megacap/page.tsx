import { combinedScore, currencyToFXScore, marketLabel, formatMarketCap } from "@/lib/megacap";
import { getMegacapData, getMegacapFXData } from "@/lib/megacap-data";
import { FXSignalBar } from "@/components/FXSignalBar";
import { MegacapTable } from "@/components/MegacapTable";

export const dynamic = "force-static";
export const revalidate = false;

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00Z");
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

export default async function MegacapPage() {
  const [data, fxData] = await Promise.all([getMegacapData(), getMegacapFXData()]);

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
        <p className="text-on-surface-variant">
          메가캡 데이터를 먼저 수집해주세요.
          <br />
          <code className="text-xs">npx tsx scripts/fetch-megacap-monitor.ts</code>
        </p>
      </div>
    );
  }

  const buyTriggered = data.stocks
    .filter((s) => s.signal.label === "강한 매수" || s.signal.label === "매수 검토")
    .sort((a, b) => combinedScore(b, fxData) - combinedScore(a, fxData))
    .slice(0, 12);

  return (
    <div className="space-y-12">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Mega-cap Quality Stocks Monitor
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          메가캡 우량주 모니터
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          글로벌 메가캡 {data.total_selected}종목 · 버핏 후보 {data.buffett_candidates_count}개 · 매수 시그널 {data.signal_count}개
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1.5">
          기준일: {formatDate(data.generated_at)} ·{" "}
          {Object.entries(data.market_breakdown).map(([m, n]) => `${m} ${n}`).join(" / ")}
        </p>
      </section>

      {/* FX Signal Bar */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <span className="material-symbols-outlined text-primary text-xl">currency_exchange</span>
          <h3 className="text-xl font-serif text-on-surface tracking-tight">통화별 환율 시그널</h3>
        </div>
        <p className="text-sm text-on-surface-variant mb-4">
          5년 평균 환율 대비 z-score · 원화 강세(녹색) = 외화 종목 매수 유리 · 원화 약세(주황) = 환차손 위험
        </p>
        {fxData ? (
          <FXSignalBar rates={fxData.rates} />
        ) : (
          <div className="text-on-surface-variant/60 text-sm py-6 text-center">
            환율 데이터 수집 중. <code className="text-xs">npx tsx scripts/fetch-megacap-fx.ts</code>
          </div>
        )}
      </section>

      {/* Buy Signal Cards */}
      {buyTriggered.length > 0 && (
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="material-symbols-outlined text-tertiary text-xl">notifications_active</span>
            <h3 className="text-xl font-serif text-on-surface tracking-tight">지금 매수 시그널이 켜진 종목</h3>
          </div>
          <p className="text-sm text-on-surface-variant mb-4">
            종목 점수 + FX 점수 종합 상위 {buyTriggered.length}개. 분할매수 검토용.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {buyTriggered.map((s) => {
              const fxScore = currencyToFXScore(s.currency, fxData);
              const combined = s.scores.total + fxScore;
              const sigColor = s.signal.label === "강한 매수" ? "#10b981" : "#fbbf24";
              return (
                <div
                  key={s.ticker}
                  className="bg-surface-container-low rounded-xl p-4 ghost-border"
                  style={{ borderLeft: `3px solid ${sigColor}` }}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="text-sm font-medium text-on-surface">{s.name_kr}</div>
                      <div className="text-[11px] font-mono text-on-surface-variant/60">
                        {s.ticker} · {marketLabel(s.market)}
                      </div>
                    </div>
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-medium"
                      style={{ backgroundColor: `${sigColor}20`, color: sigColor, border: `1px solid ${sigColor}40` }}
                    >
                      {s.signal.label}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
                    <Stat label="시총" value={formatMarketCap(s.metrics.marketCap, s.currency)} />
                    <Stat label="PER" value={s.metrics.trailingPE != null ? s.metrics.trailingPE.toFixed(1) : "—"} />
                    <Stat label="배당" value={s.metrics.dividendYield != null ? `${(s.metrics.dividendYield * 100).toFixed(1)}%` : "—"} />
                  </div>
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-on-surface-variant/10">
                    <div className="text-[10px] text-on-surface-variant">
                      종목 <span className="font-mono font-bold text-on-surface">{s.scores.total.toFixed(0)}</span>
                      {" + FX "}
                      <span className="font-mono font-bold" style={{ color: fxScore > 0 ? "#34d399" : fxScore < 0 ? "#fb923c" : "#94a3b8" }}>
                        {fxScore >= 0 ? "+" : ""}{fxScore}
                      </span>
                    </div>
                    <div className="text-base font-mono font-bold text-primary">
                      = {combined.toFixed(0)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Full Table */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <span className="material-symbols-outlined text-primary text-xl">table_view</span>
          <h3 className="text-xl font-serif text-on-surface tracking-tight">전체 메가캡 100종목</h3>
        </div>
        <p className="text-sm text-on-surface-variant mb-4">
          행을 클릭하면 4-Pillar 점수 분해 + 핵심 지표 + 5년 가격 위치 + 분할매수 트리거 상세를 펼칩니다.
        </p>
        <MegacapTable stocks={data.stocks} fxData={fxData} />
      </section>

      {/* Methodology + 상관관계 흐름도 */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <div className="flex items-center gap-3 mb-4">
          <span className="material-symbols-outlined text-primary text-xl">school</span>
          <h3 className="text-xl font-serif text-on-surface tracking-tight">점수 산정 기준</h3>
        </div>

        <div className="space-y-4 text-sm">
          <div>
            <h4 className="text-base font-bold text-on-surface mb-2">버핏 4-Pillar 스코어카드 (100점)</h4>
            <div className="grid sm:grid-cols-2 gap-3 text-xs">
              <div className="bg-surface-container/30 rounded-lg p-3">
                <div className="font-bold text-on-surface mb-1">Quality (40점) — 사업 본질의 우수성</div>
                <ul className="text-on-surface-variant space-y-0.5 ml-3 list-disc">
                  <li>ROE: ≥20% 만점, 15% 75%pt, 10% 50%pt</li>
                  <li>영업이익률, 순이익률 (각 10점)</li>
                  <li>부채/자본: ≤50% 만점</li>
                </ul>
              </div>
              <div className="bg-surface-container/30 rounded-lg p-3">
                <div className="font-bold text-on-surface mb-1">Moat (20점) — 해자(경쟁우위)</div>
                <ul className="text-on-surface-variant space-y-0.5 ml-3 list-disc">
                  <li>영업이익률 절대치 ≥15% (해자 증명)</li>
                  <li>EV/EBITDA ≤ 20</li>
                  <li>P/B 적정성</li>
                </ul>
              </div>
              <div className="bg-surface-container/30 rounded-lg p-3">
                <div className="font-bold text-on-surface mb-1">Capital (20점) — 자본 효율 + 성장</div>
                <ul className="text-on-surface-variant space-y-0.5 ml-3 list-disc">
                  <li>FCF Yield (FCF/시총)</li>
                  <li>EPS 성장률, 매출 성장률</li>
                </ul>
              </div>
              <div className="bg-surface-container/30 rounded-lg p-3">
                <div className="font-bold text-on-surface mb-1">Valuation (20점) — 가격 매력</div>
                <ul className="text-on-surface-variant space-y-0.5 ml-3 list-disc">
                  <li>Trailing PER 절대 수준</li>
                  <li>FCF Yield (밸류 관점)</li>
                  <li>52주 고점 대비 드로다운</li>
                </ul>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-base font-bold text-on-surface mb-2">상관관계 흐름도</h4>
            <pre className="bg-surface-container/30 rounded-lg p-4 text-[11px] text-on-surface-variant whitespace-pre overflow-x-auto leading-relaxed">
{`[원화 강세 (z<-0.5)] ───────────┐
                                ↓
[종목 점수 ≥ 70 (버핏 후보)] + [FX 점수 +10~+20]
                                ↓
                    [종합 점수 80~120]
                                ↓
            [분할매수 트리거 2~3개 충족 확인]
                ├─ Forward PER < Trailing × 0.85 (실적 개선)
                ├─ 52w 고점 대비 -20% 이상 (일시적 우려)
                └─ FCF Yield > 5% (현금 생성력 입증)
                                ↓
                    [🟢 분할매수 적기]

[원화 약세 (z>0.5)] → 외화 종목 [FX -10~-20] → 종합점수 하락
                  → 한국 종목 (FX 영향 0)에 우선 배분 권장
`}
            </pre>
          </div>

          <div>
            <h4 className="text-base font-bold text-on-surface mb-2">분할매수 트리거 (3개 중 2개 이상)</h4>
            <ul className="text-xs text-on-surface-variant space-y-1 ml-3 list-disc">
              <li><strong>Forward PER &lt; Trailing × 0.85</strong>: 향후 12개월 EPS가 빠르게 개선될 것으로 컨센서스 형성</li>
              <li><strong>52주 고점 대비 -20% 이상</strong>: 일시적 우려로 우량주가 저평가된 구간 (버핏 애플 매입 시 패턴)</li>
              <li><strong>FCF Yield ≥ 5%</strong>: 시총 대비 잉여현금흐름이 충분 — 자사주매입·배당·재투자 여력 확보</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="bg-surface-container-low rounded-xl p-6 ghost-border">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-on-surface-variant/50 text-lg mt-0.5">info</span>
          <div className="space-y-2 text-sm text-on-surface-variant leading-relaxed">
            <p>
              <strong className="text-on-surface">데이터 출처:</strong> Yahoo Finance · 매 영업일 17:30 KST 자동 갱신.
              유니버스는 시장별 시총 상위 자동 선정 (US 50 / KR 15 / JP 15 / CN 10 / EU 5 / 기타 5).
            </p>
            <p>
              5년 평균 환율 대비 z-score, 4-Pillar 스코어카드, 분할매수 트리거 모두 자동 산정 결과이며,
              일부 신흥국 종목은 EBITDA·FCF 데이터가 누락되어 점수가 낮게 나올 수 있습니다.
            </p>
            <p className="text-xs text-on-surface-variant/60">
              본 페이지는 학습·기록용이며 투자 조언이 아닙니다. 실제 매수 전 재무제표 확정 공시 및 사업보고서를 직접 확인하세요.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-on-surface-variant/60">{label}</div>
      <div className="font-mono text-on-surface mt-0.5">{value}</div>
    </div>
  );
}
