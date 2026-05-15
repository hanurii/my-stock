import fs from "fs/promises";
import path from "path";
import { HoldingCard } from "../HoldingCard";
import { BearMarketBanner } from "../BearMarketBanner";
import type { SellSignalsOutput } from "../types";

async function getData(): Promise<SellSignalsOutput | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "sell-signals.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export default async function SellStrategyPage() {
  const data = await getData();

  if (!data || data.holdings.length === 0) {
    return (
      <div className="space-y-6">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            매도 시스템 — 핵심 매수·매도 전략
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">
            데이터가 아직 생성되지 않았습니다. <code className="text-xs">scripts/compute-sell-signals.ts</code> 실행 필요.
          </p>
        </header>
      </div>
    );
  }

  // verdict 분포 집계
  const verdictCounts = data.holdings.reduce(
    (acc, h) => {
      acc[h.strategy_verdict.verdict] = (acc[h.strategy_verdict.verdict] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="space-y-8">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          매도 시스템 — 핵심 매수·매도 전략
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          오닐 책 기준 손절 -7~8%, 익절 +20~25%, 8주 룰 예외, 추가 매수 +5% 한계.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5 leading-relaxed">
          &ldquo;정확한 시세 분기점에서 매수했고, 매수 지점에서 5% 이상 오른 다음에는 추가 매수를 하지 않았다면, 정상적인 조정이 닥쳐도 그냥 지켜볼 수 있다.&rdquo;
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일: {data.generated_at.slice(0, 19).replace("T", " ")} · 대상 {data.holdings.length}종목
        </p>
      </header>

      <BearMarketBanner />

      {/* 핵심 3룰 + 진입 정확도 요약 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">
            rule
          </span>
          전략 3룰 + 매수 진입 정확도 — 책 기준
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs mb-3">
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <p className="text-on-surface-variant/60 mb-0.5">손실 차단</p>
            <p className="text-on-surface font-medium">매수가 -7~8%</p>
            <p className="text-on-surface-variant/70 text-[11px] mt-0.5">
              무조건 손절. 추세 깨졌으면 -4~5%도 가능
            </p>
          </div>
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <p className="text-on-surface-variant/60 mb-0.5">이익 실현</p>
            <p className="text-on-surface font-medium">매수가 +20~25%</p>
            <p className="text-on-surface-variant/70 text-[11px] mt-0.5">
              분할 매도 검토 (강력 종목 8주 예외는 인내 보유 페이지)
            </p>
          </div>
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <p className="text-on-surface-variant/60 mb-0.5">추가 매수 한계</p>
            <p className="text-on-surface font-medium">매수가 +5%</p>
            <p className="text-on-surface-variant/70 text-[11px] mt-0.5">
              초과 시 추가 매수 금지 (+2.5%에서 첫 추가)
            </p>
          </div>
        </div>
        <div className="bg-surface-container/30 rounded-lg p-2.5 text-[11px] text-on-surface-variant/80 leading-relaxed">
          <p className="font-medium text-on-surface-variant mb-1">매수 진입 정확도 (책 인용)</p>
          정확한 시세 분기점에서 매수 + 매수일 거래량은 60일 평균 대비 +50% 이상 + 일중 고점 추격 금지. &ldquo;정확하게 사면 매도 문제 대부분이 해결된다.&rdquo;
        </div>
      </section>

      {/* verdict 분포 */}
      <section className="flex flex-wrap items-center gap-3 text-xs">
        <span className="text-on-surface-variant/60">판정 분포:</span>
        {(["HOLD", "BAD_ENTRY", "WATCH", "TRIM", "SELL"] as const).map((v) => {
          const count = verdictCounts[v] ?? 0;
          const labels = {
            HOLD: { ko: "보유", color: "#95d3ba" },
            BAD_ENTRY: { ko: "잘못 매수", color: "#b09bce" },
            WATCH: { ko: "관찰", color: "#e8c875" },
            TRIM: { ko: "비중 축소", color: "#e8a25b" },
            SELL: { ko: "매도", color: "#ffb4ab" },
          };
          return (
            <span
              key={v}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full"
              style={{
                backgroundColor: `${labels[v].color}20`,
                color: labels[v].color,
              }}
            >
              <span className="font-medium">{labels[v].ko}</span>
              <strong>{count}</strong>
            </span>
          );
        })}
      </section>

      {/* 보유 종목 카드 그리드 */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data.holdings.map((h) => (
          <HoldingCard key={h.code} h={h} />
        ))}
      </section>
    </div>
  );
}
