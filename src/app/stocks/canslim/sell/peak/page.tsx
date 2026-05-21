import fs from "fs/promises";
import path from "path";
import { PeakCard } from "../PeakCard";
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

export default async function SellPeakPage() {
  const data = await getData();

  if (!data || data.holdings.length === 0) {
    return (
      <div className="space-y-6">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            매도 시스템 — 고점 판단
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">
            데이터가 아직 생성되지 않았습니다. <code className="text-xs">scripts/compute-sell-signals.ts</code> 실행 필요.
          </p>
        </header>
      </div>
    );
  }

  const verdictCounts = data.holdings.reduce(
    (acc, h) => {
      acc[h.peak_verdict.verdict] = (acc[h.peak_verdict.verdict] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="space-y-8">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          매도 시스템 — 고점 판단
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          책 기준 최후의 정점 신호 + 약세 징후 + 지지선 붕괴 + thesis 알람 통합 평가.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5 leading-relaxed">
          &ldquo;주가가 200일 이동평균선보다 70~100%, 혹은 그 이상 높이 올라가면 파는 게 좋다.&rdquo; — 책 5범주
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일: {data.generated_at.slice(0, 19).replace("T", " ")} · 대상 {data.holdings.length}종목
        </p>
      </header>

      <BearMarketBanner />

      {/* 평가 신호 카테고리 안내 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">
            radar
          </span>
          평가 신호 — 4 카테고리
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <div className="flex items-center gap-1 mb-1">
              <span className="material-symbols-outlined text-sm" style={{ color: "#ffb4ab" }}>
                mode_heat
              </span>
              <p className="text-on-surface font-medium">최후의 정점</p>
            </div>
            <p className="text-on-surface-variant/70 text-[11px] leading-relaxed">
              200일선 +70%+ 괴리, 신고가 -8%+, distribution day 누적
            </p>
          </div>
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <div className="flex items-center gap-1 mb-1">
              <span className="material-symbols-outlined text-sm" style={{ color: "#e8c875" }}>
                trending_down
              </span>
              <p className="text-on-surface font-medium">약세 징후</p>
            </div>
            <p className="text-on-surface-variant/70 text-[11px] leading-relaxed">
              거래량 적은 신고가, 연속 하락일 증가
            </p>
          </div>
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <div className="flex items-center gap-1 mb-1">
              <span className="material-symbols-outlined text-sm" style={{ color: "#ffb4ab" }}>
                bar_chart
              </span>
              <p className="text-on-surface font-medium">지지선 붕괴</p>
            </div>
            <p className="text-on-surface-variant/70 text-[11px] leading-relaxed">
              50일선 이탈, 200일선 이탈 + 우하향 반전
            </p>
          </div>
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <div className="flex items-center gap-1 mb-1">
              <span className="material-symbols-outlined text-sm" style={{ color: "#e8a25b" }}>
                policy
              </span>
              <p className="text-on-surface font-medium">thesis 알람</p>
            </div>
            <p className="text-on-surface-variant/70 text-[11px] leading-relaxed">
              종목별 research/monitor 시그널 (PER, 지배구조 등)
            </p>
          </div>
        </div>
        <p className="text-[10px] text-on-surface-variant/50 mt-3">
          판정 룰: 강 신호 2건+ → 매도 / 강 1건 → 비중 축소 / 중·약 누적 → 관찰
        </p>
      </section>

      {/* verdict 분포 */}
      <section className="flex flex-wrap items-center gap-3 text-xs">
        <span className="text-on-surface-variant/60">판정 분포:</span>
        {(["HOLD", "WATCH", "TRIM", "SELL"] as const).map((v) => {
          const count = verdictCounts[v] ?? 0;
          const labels = {
            HOLD: { ko: "보유", color: "#95d3ba" },
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

      {/* 보유 종목 카드 */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data.holdings.map((h) => (
          <PeakCard key={h.code} h={h} />
        ))}
      </section>
    </div>
  );
}
