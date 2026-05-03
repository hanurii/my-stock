import { combinedScore, currencyToFXScore, marketLabel, formatMarketCap } from "@/lib/megacap";
import { getMegacapData, getMegacapFXData } from "@/lib/megacap-data";
import { FXSignalBar } from "@/components/FXSignalBar";
import { MegacapTable } from "@/components/MegacapTable";
import { PillarCard } from "@/components/PillarCard";
import { GlossarySection } from "@/components/GlossarySection";

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
          5년 평균 환율 대비 현재 위치 · 원화 강세(녹색) = 외화 종목 매수 유리 · 원화 약세(주황) = 환차손 위험
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
            종목 점수 + 환율 점수 종합 상위 {buyTriggered.length}개. 분할매수 검토용.
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
                      {" + 환율 "}
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
          행을 클릭하면 4단계 평가 점수 분해 + 핵심 지표 + 5년 가격 위치 + 분할매수 트리거 상세를 펼칩니다.
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
            <h4 className="text-base font-bold text-on-surface mb-1">버핏의 4단계 기업 평가 (총 100점)</h4>
            <p className="text-xs text-on-surface-variant/70 mb-3">
              "식당 한 곳을 통째로 인수한다면 무엇을 보겠는가?" — 워런 버핏이 60년간 기업을 평가해온 4가지 기둥(pillar)을 점수화한 것입니다. 카드를 클릭하면 풀어쓴 설명을 펼칩니다.
            </p>
            <div className="space-y-2">
              <PillarCard
                title="사업 실력"
                subtitle="Quality"
                points={40}
                question="회사가 진짜로 돈을 잘 버는가?"
                color="#6ea8fe"
                metrics={[
                  { label: "자기자본이익률(ROE) ≥20% (15점)", plain: "내 돈 100만원으로 1년에 20만원 이상 벌면 만점 — 자본 활용 능력" },
                  { label: "영업이익률 ≥25% (10점)", plain: "매출 1,000원 중 본업으로 250원 이상 남기면 만점 — 본업의 수익 밀도" },
                  { label: "순이익률 ≥20% (10점)", plain: "매출 1,000원 중 세금·이자까지 다 빼고 200원 이상 진짜 남으면 만점 — 최종 통장 잔고" },
                  { label: "부채비율 ≤50% (5점)", plain: "빚이 자기자본의 절반 이하면 만점 — 재무 안전성" },
                ]}
                analogy="자기 돈 1억으로 식당을 차렸는데 연 2,000만원 순수익을 내고, 빚이 5,000만원 이하인 가게. 본업이 탄탄하고 빚 부담도 없는 안정적인 기업입니다."
              />
              <PillarCard
                title="경제적 해자"
                subtitle="Moat"
                points={20}
                question="다른 회사가 쉽게 따라잡을 수 없는가?"
                color="#c084fc"
                metrics={[
                  { label: "영업이익률 절대치 ≥15% (10점)", plain: "마진이 두 자릿수면 '쉽게 카피되지 않는 비밀'이 있다는 증거" },
                  { label: "EV/EBITDA ≤ 20 (5점)", plain: "회사를 통째로 사면 영업현금으로 본전 뽑는데 20년 이하면 적정 가격" },
                  { label: "주가순자산비율(PBR) 적정성 (5점)", plain: "장부상 자산 대비 주가가 너무 비싸지 않은가" },
                ]}
                analogy="옆집은 마진 5% 남기는데 우리 가게는 25% 남긴다면 → 따라하기 어려운 비밀 레시피·브랜드·입지가 있다는 뜻. 워런 버핏은 이걸 '해자(moat)'라고 부릅니다 — 성을 둘러싼 물길처럼 경쟁자가 못 들어오게 막는 진입장벽."
              />
              <PillarCard
                title="자본 운용력"
                subtitle="Capital"
                points={20}
                question="번 돈을 잘 굴려서 성장하고 있는가?"
                color="#34d399"
                metrics={[
                  { label: "잉여현금수익률 ≥6% (10점)", plain: "시가총액 대비 매년 통장에 진짜 들어오는 현금이 6% 이상" },
                  { label: "주당순이익 성장률 ≥15% (5점)", plain: "1주당 이익이 매년 15% 이상 성장 (작년 1,000원 → 올해 1,150원)" },
                  { label: "매출 성장률 ≥10% (5점)", plain: "회사 자체가 매년 10% 이상 커지고 있는가" },
                ]}
                analogy="식당 인수가가 5억인데 매년 진짜 통장에 3,000만원 쌓이면 6% (월세 받는 셈). 좋은 기업은 번 돈으로 자사주 매입·재투자해서 주당순이익과 매출이 꾸준히 늘어납니다."
              />
              <PillarCard
                title="가격 매력"
                subtitle="Valuation"
                points={20}
                question="지금 사기에 가격이 적당한가?"
                color="#fbbf24"
                metrics={[
                  { label: "주가수익비율(PER) ≤10 (10점)", plain: "현재 이익으로 본전 뽑는데 10년 이하면 만점 — 싸게 사는 셈" },
                  { label: "잉여현금수익률 ≥6% (5점)", plain: "자본 운용력과 같은 지표지만, 가격 관점에서 한 번 더 평가" },
                  { label: "52주 신고가 대비 −30% 이상 하락 (5점)", plain: "최근 1년 신고가 대비 30% 이상 빠졌으면 만점 — 버핏의 '두려울 때 사라'" },
                ]}
                analogy="작년 50억에 거래되던 식당이 갑자기 35억 매물로 나오면 → 같은 가게를 30% 싸게 사는 셈입니다. 좋은 회사라도 비싸게 사면 안 좋은 투자가 되기에, 가격 매력을 따로 점수화합니다."
              />
            </div>
          </div>

          <div>
            <h4 className="text-base font-bold text-on-surface mb-2">상관관계 흐름도</h4>
            <pre className="bg-surface-container/30 rounded-lg p-4 text-[11px] text-on-surface-variant whitespace-pre overflow-x-auto leading-relaxed">
{`[원화 강세 (5년 평균보다 충분히 낮음)] ────────┐
                                              ↓
[종목 점수 ≥ 70 (버핏 후보)] + [환율 점수 +10~+20]
                                              ↓
                          [종합 점수 80~120]
                                              ↓
                  [분할매수 트리거 2~3개 충족 확인]
                      ├─ 향후 12개월 예상 PER이 현재보다 15%↑ 낮음 (실적 개선)
                      ├─ 52주 신고가 대비 -20% 이상 (일시적 우려로 저평가)
                      └─ 잉여현금수익률 > 5% (시총 대비 현금 창출력 입증)
                                              ↓
                          [🟢 분할매수 적기]

[원화 약세] → 외화 종목 [환율 -10~-20] → 종합점수 하락
           → 한국 종목 (환율 영향 0)에 우선 배분 권장
`}
            </pre>
          </div>

          <div>
            <h4 className="text-base font-bold text-on-surface mb-2">분할매수 트리거 (3개 중 2개 이상이면 시그널 점등)</h4>
            <ul className="text-xs text-on-surface-variant space-y-1 ml-3 list-disc">
              <li><strong>향후 12개월 예상 PER &lt; 현재 PER × 0.85</strong>: 시장 전망상 향후 1년간 1주당 이익이 빠르게 개선될 것으로 컨센서스 형성</li>
              <li><strong>52주 신고가 대비 -20% 이상 하락</strong>: 일시적 우려로 우량주가 저평가된 구간 (버핏 애플 매입 시 패턴)</li>
              <li><strong>잉여현금수익률 ≥ 5%</strong>: 시가총액 대비 매년 통장에 들어오는 진짜 현금이 5% 이상 — 자사주매입·배당·재투자 여력 확보</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Glossary */}
      <GlossarySection />

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
              5년 평균 환율 대비 편차, 버핏 4단계 기업 평가, 분할매수 트리거 모두 자동 산정 결과이며,
              일부 신흥국 종목은 영업현금·잉여현금 데이터가 누락되어 점수가 낮게 나올 수 있습니다.
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
