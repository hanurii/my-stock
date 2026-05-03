"use client";

import { useState, useMemo } from "react";
import type { MegacapStock } from "@/lib/megacap";
import { marketLabel } from "@/lib/megacap";

// 2016년 1분기 애플 점수 (역사적 사실 — 정적 상수)
// scripts/fetch-megacap-monitor.ts:computeScore() 로직을 당시 메트릭에 적용한 결과
// 자본 운용력 14.4점 = FCF Yield 7 (만점) + 총 주주환원율 5 (8.2% 추정 → 5점) + EPS 성장 1.4 + 매출 성장 1.0
const BENCHMARK = {
  total: 88.9,
  pillars: {
    quality: 40,
    moat: 18,
    capital: 14.4,
    valuation: 16.5,
  },
  signal: { label: "매수 검토", triggers_met: 2, max: 3 },
  metrics: [
    { label: "자기자본이익률(ROE)", value: "46%" },
    { label: "영업이익률", value: "30.5%" },
    { label: "순이익률", value: "22.8%" },
    { label: "잉여현금수익률", value: "12%" },
    { label: "총 주주환원율", value: "약 8.2% (배당 2% + 자사주매입 6%)" },
    { label: "주가수익비율(PER)", value: "10.5" },
    { label: "52주 고점대비 하락률", value: "-25%" },
  ],
  triggers: [
    { met: false, label: "예상 PER이 현재 PER보다 15%↑ 낮음" },
    { met: true, label: "52주 고점 대비 -20% 이상 하락" },
    { met: true, label: "잉여현금수익률 ≥ 5%" },
  ],
  context: {
    period: "2016년 1분기",
    avg_buy_price: "$25 (분할 후 환산)",
    current_price: "$280 (2026-05)",
    return: "약 11배 (10년 9개월)",
    note: "버크셔 첫 매입은 2016 Q1 / 980만주 / 약 10억 달러. 매입 시점 시장은 'iPhone 판매 둔화'로 PER 10배 수준까지 빠진 구간이었음. 자사주매입 + 배당으로 연 8~10% 주주환원을 하던 '환원 머신'이었으며, 이후 2017-2018년 추가 매수로 포트의 30~50%까지 확대.",
  },
};

interface Props {
  stocks: MegacapStock[];
}

export function BuffettBenchmarkCard({ stocks }: Props) {
  const [showClosest, setShowClosest] = useState(true);

  const closest = useMemo(() => {
    return [...stocks]
      .map((s) => ({ stock: s, delta: s.scores.total - BENCHMARK.total }))
      .sort((a, b) => Math.abs(a.delta) - Math.abs(b.delta))
      .slice(0, 5);
  }, [stocks]);

  return (
    <section className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
      {/* 황금색 강조 배너 */}
      <div
        className="px-6 py-5"
        style={{
          background:
            "linear-gradient(135deg, rgba(251, 191, 36, 0.12) 0%, rgba(251, 191, 36, 0.04) 100%)",
          borderBottom: "1px solid rgba(251, 191, 36, 0.2)",
        }}
      >
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">🍎</span>
          <div className="flex-1">
            <div className="text-[10px] uppercase tracking-[0.2em] text-amber-400/80">
              Historical Benchmark
            </div>
            <h3 className="text-lg sm:text-xl font-serif text-on-surface tracking-tight">
              버핏이 매입한 시점의 애플 — {BENCHMARK.context.period}
            </h3>
          </div>
        </div>
        <p className="text-xs text-on-surface-variant/80 leading-relaxed">
          이 점수는 사용자님의 점수 체계에 2016 Q1 애플의 실제 메트릭을 적용한 결과입니다. 현재 메가캡 100종목 중 이 점수에 가까운 종목은 분할매수 검토 시 1차 후보가 됩니다.
        </p>
      </div>

      <div className="p-6 space-y-5">
        {/* 점수 + 시그널 */}
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-on-surface-variant/60 mb-1">
              종목 점수
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-mono font-bold text-amber-400">{BENCHMARK.total}</span>
              <span className="text-sm text-on-surface-variant">/ 100</span>
            </div>
          </div>
          <div className="h-12 w-px bg-on-surface-variant/20" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-on-surface-variant/60 mb-1">
              시그널
            </div>
            <span
              className="inline-block px-3 py-1 rounded-md text-xs font-medium"
              style={{
                backgroundColor: "rgba(251, 191, 36, 0.15)",
                color: "#fbbf24",
                border: "1px solid rgba(251, 191, 36, 0.4)",
              }}
            >
              {BENCHMARK.signal.label} (트리거 {BENCHMARK.signal.triggers_met}/{BENCHMARK.signal.max})
            </span>
          </div>
          <div className="h-12 w-px bg-on-surface-variant/20" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-on-surface-variant/60 mb-1">
              매입 후 수익률
            </div>
            <div className="text-base font-bold text-emerald-400">{BENCHMARK.context.return}</div>
            <div className="text-[10px] text-on-surface-variant/60">
              {BENCHMARK.context.avg_buy_price} → {BENCHMARK.context.current_price}
            </div>
          </div>
        </div>

        {/* 4-Pillar 분해 */}
        <div>
          <h4 className="text-xs uppercase tracking-wider text-on-surface-variant/60 mb-2">
            4단계 점수 분해
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <PillarBar label="사업 실력" value={BENCHMARK.pillars.quality} max={40} color="#6ea8fe" />
            <PillarBar label="경제적 해자" value={BENCHMARK.pillars.moat} max={20} color="#c084fc" />
            <PillarBar label="자본 운용력" value={BENCHMARK.pillars.capital} max={20} color="#34d399" />
            <PillarBar label="가격 매력" value={BENCHMARK.pillars.valuation} max={20} color="#fbbf24" />
          </div>
        </div>

        {/* 핵심 메트릭 + 트리거 */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <h4 className="text-xs uppercase tracking-wider text-on-surface-variant/60 mb-2">
              당시 핵심 메트릭
            </h4>
            <div className="bg-surface-container/30 rounded-lg p-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
              {BENCHMARK.metrics.map((m, i) => (
                <div key={i} className="flex justify-between">
                  <span className="text-on-surface-variant">{m.label}</span>
                  <span className="font-mono font-medium text-on-surface">{m.value}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-xs uppercase tracking-wider text-on-surface-variant/60 mb-2">
              분할매수 트리거 ({BENCHMARK.signal.triggers_met}/{BENCHMARK.signal.max})
            </h4>
            <div className="bg-surface-container/30 rounded-lg p-3 text-xs space-y-1.5">
              {BENCHMARK.triggers.map((t, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span
                    className="material-symbols-outlined text-base mt-0.5 shrink-0"
                    style={{ color: t.met ? "#34d399" : "#475569" }}
                  >
                    {t.met ? "check_circle" : "radio_button_unchecked"}
                  </span>
                  <span className={t.met ? "text-on-surface" : "text-on-surface-variant/50"}>
                    {t.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 맥락 설명 */}
        <div className="bg-surface-container/20 rounded-lg p-3 text-xs text-on-surface-variant leading-relaxed">
          <span className="text-amber-400/90 font-medium">▸ 매입 맥락:</span> {BENCHMARK.context.note}
        </div>

        {/* 현재 가장 가까운 종목 Top 5 */}
        <div>
          <button
            onClick={() => setShowClosest(!showClosest)}
            className="w-full flex items-center gap-2 text-left mb-3 group"
          >
            <span
              className="material-symbols-outlined text-primary-dim/60 text-base transition-transform duration-200"
              style={{ transform: showClosest ? "rotate(90deg)" : "rotate(0deg)" }}
            >
              chevron_right
            </span>
            <h4 className="text-sm font-bold text-on-surface group-hover:text-primary transition-colors">
              현재 100종목 중 점수가 가장 비슷한 Top 5
            </h4>
            <span className="ml-auto text-[10px] text-on-surface-variant/40">
              점수 차이 작은 순
            </span>
          </button>
          {showClosest && (
            <div className="space-y-1.5">
              {closest.map((entry, i) => {
                const s = entry.stock;
                return (
                  <div
                    key={s.ticker}
                    className="flex items-center justify-between bg-surface-container/30 rounded-lg px-4 py-2.5 ghost-border"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <span className="text-sm font-mono text-on-surface-variant/50 w-6">
                        {i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-on-surface text-sm truncate">
                          {s.name_kr}
                        </div>
                        <div className="text-[11px] font-mono text-on-surface-variant/60">
                          {s.ticker} · {marketLabel(s.market)}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-sm font-mono font-bold text-on-surface">
                          {s.scores.total.toFixed(1)}점
                        </div>
                        <div className="text-[10px] text-on-surface-variant/60">
                          애플 대비 {entry.delta >= 0 ? "+" : ""}{entry.delta.toFixed(1)}점
                        </div>
                      </div>
                      {s.signal.label && (
                        <span
                          className="px-2 py-0.5 rounded text-[10px] font-medium hidden sm:inline-block"
                          style={{
                            backgroundColor:
                              s.signal.label === "강한 매수"
                                ? "rgba(16, 185, 129, 0.15)"
                                : s.signal.label === "매수 검토"
                                  ? "rgba(251, 191, 36, 0.15)"
                                  : "rgba(148, 163, 184, 0.15)",
                            color:
                              s.signal.label === "강한 매수"
                                ? "#10b981"
                                : s.signal.label === "매수 검토"
                                  ? "#fbbf24"
                                  : "#94a3b8",
                          }}
                        >
                          {s.signal.label}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
              <p className="text-[10px] text-on-surface-variant/50 mt-2 leading-relaxed">
                ⚠️ 점수가 비슷하다고 같은 종류의 기업은 아닙니다. 산업·해자·성장 단계가 다를 수 있으니 펼침 영역에서 4단계 분해와 핵심 지표를 함께 확인하세요.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function PillarBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = (value / max) * 100;
  return (
    <div className="bg-surface-container/30 rounded-lg p-2.5">
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-on-surface-variant">{label}</span>
        <span className="font-mono font-bold" style={{ color }}>
          {value}/{max}
        </span>
      </div>
      <div className="h-1.5 bg-surface-container rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}
