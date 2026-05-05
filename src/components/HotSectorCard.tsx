"use client";

import { useState } from "react";
import {
  formatBillion,
  formatPct,
  formatRatio,
  type KoreanSector,
  type KoreanTheme,
  type ETFOption,
} from "@/lib/hot-sectors";
import { HotClassificationBadge } from "./HotClassificationBadge";

type SectorOrTheme = (KoreanSector | KoreanTheme) & {
  __title: string;
  __subtitle?: string;
};

function PerfPill({
  label,
  value,
  emphasize = false,
}: {
  label: string;
  value: number | null;
  emphasize?: boolean;
}) {
  const tone =
    value == null
      ? "text-on-surface-variant"
      : value > 0
        ? "text-primary"
        : value < 0
          ? "text-error"
          : "text-on-surface-variant";
  return (
    <div className={`flex flex-col items-center ${emphasize ? "" : "opacity-90"}`}>
      <span className="text-[9px] uppercase tracking-[0.18em] text-on-surface-variant/70">
        {label}
      </span>
      <span
        className={`font-serif tracking-tight ${tone} ${
          emphasize ? "text-base sm:text-lg" : "text-xs sm:text-sm"
        }`}
      >
        {formatPct(value)}
      </span>
    </div>
  );
}

function InvestorBox({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {
  const positive = value != null && value > 0;
  return (
    <div
      className={`flex flex-col items-center rounded-md border px-2 py-1.5 ${
        positive
          ? "border-primary/40 bg-primary/8"
          : "border-on-surface-variant/15 bg-on-surface-variant/5"
      }`}
    >
      <span className="text-[10px] uppercase tracking-[0.16em] text-on-surface-variant/80">
        {label}
      </span>
      <span
        className={`text-xs sm:text-sm font-medium ${
          positive ? "text-primary" : "text-on-surface-variant"
        }`}
      >
        {formatBillion(value)}
      </span>
    </div>
  );
}

function ETFList({ etfs }: { etfs: ETFOption[] }) {
  if (etfs.length === 0) {
    return (
      <p className="text-[11px] text-on-surface-variant/70">
        매핑된 ETF 없음 (검증 실패 또는 미등록)
      </p>
    );
  }
  return (
    <ul className="space-y-1">
      {etfs.map((e) => (
        <li
          key={e.code}
          className="flex items-center gap-2 text-[12px]"
        >
          <span className="font-mono text-primary/80">{e.code}</span>
          <span className="text-on-surface">{e.name}</span>
          {e.note ? (
            <span className="text-[10px] text-on-surface-variant/70">— {e.note}</span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export function HotSectorCard({ data }: { data: SectorOrTheme }) {
  const [stocksOpen, setStocksOpen] = useState(false);

  const isTheme = "theme_name" in data;
  const topStocks = isTheme
    ? (data as KoreanTheme).representative_stocks
    : (data as KoreanSector).top_stocks;
  const inWatchlist = isTheme ? (data as KoreanTheme).in_watchlist : [];
  const newsKeywords = isTheme ? (data as KoreanTheme).news_keywords : [];

  return (
    <article className="glass-card rounded-xl ghost-border p-4 sm:p-5 flex flex-col gap-4">
      {/* Title row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col">
          <h3 className="text-lg sm:text-xl font-serif text-on-surface tracking-tight">
            {data.__title}
          </h3>
          {data.__subtitle ? (
            <p className="text-[11px] text-on-surface-variant/80 mt-0.5">
              {data.__subtitle}
            </p>
          ) : null}
        </div>
        <HotClassificationBadge classification={data.classification} />
      </div>

      {/* Performance row: 5D, 20D, 60D, 3M, 6M */}
      <div className="grid grid-cols-5 gap-1 sm:gap-2 border-y border-outline-variant/15 py-3">
        <PerfPill label="5D" value={data.perf_5d} />
        <PerfPill label="20D" value={data.perf_20d} />
        <PerfPill label="60D" value={data.perf_60d} emphasize />
        <PerfPill label="3M" value={data.perf_3m} emphasize />
        <PerfPill label="6M" value={data.perf_6m} emphasize />
      </div>

      {/* 3-investor row: 60D 누적 */}
      <div>
        <p className="text-[10px] uppercase tracking-[0.18em] text-on-surface-variant/70 mb-2">
          3주체 60일 누적 순매수
        </p>
        <div className="grid grid-cols-3 gap-2">
          <InvestorBox label="외국인" value={data.foreign_60d_billion} />
          <InvestorBox label="기관" value={data.organ_60d_billion} />
          <InvestorBox label="개인" value={data.individual_60d_billion} />
        </div>
        <p className="text-[10px] text-on-surface-variant/60 mt-1.5">
          (개인 = −(외인+기관) 추정)
        </p>
      </div>

      {/* Sub metrics: volume, news */}
      <div className="grid grid-cols-2 gap-3 text-[12px]">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-on-surface-variant/70">
            거래대금 지속성
          </p>
          <p className="text-on-surface mt-1">
            60D / 직전60D ={" "}
            <span className="font-medium">
              {formatRatio(data.volume_sustain_ratio)}
            </span>
          </p>
          <p className="text-on-surface-variant/80 text-[11px]">
            5D 스파이크: {formatRatio(data.volume_5d_spike_ratio)}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-on-surface-variant/70">
            뉴스 멘션 5D
          </p>
          <p className="text-on-surface mt-1 font-medium">
            {data.news_mention_change_5d != null
              ? `${data.news_mention_change_5d > 0 ? "+" : ""}${data.news_mention_change_5d}%`
              : "—"}
          </p>
          {newsKeywords.length > 0 ? (
            <p className="text-on-surface-variant/70 text-[10px] truncate">
              {newsKeywords.slice(0, 3).join(" · ")}
            </p>
          ) : null}
        </div>
      </div>

      {/* Score breakdown */}
      <div className="rounded-lg border border-outline-variant/15 p-3 bg-surface-container-low/40">
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-[11px] uppercase tracking-[0.16em] text-on-surface-variant/80">
            점수
          </span>
          <span className="text-[11px] text-on-surface-variant">
            ShortMomentum {data.short_momentum_score}
          </span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-serif text-primary tracking-tight">
            {data.real_hot_score}
          </span>
          <span className="text-[10px] text-on-surface-variant/70">RealHotScore</span>
        </div>
        <div className="grid grid-cols-5 gap-1 mt-2 text-[10px] text-on-surface-variant">
          <div>추세<br/><span className="text-on-surface">{data.score_breakdown.trend_consistency}</span></div>
          <div>3주체<br/><span className="text-on-surface">{data.score_breakdown.three_investor}</span></div>
          <div>거래량<br/><span className="text-on-surface">{data.score_breakdown.sustained_volume}</span></div>
          <div>60D%<br/><span className="text-on-surface">{data.score_breakdown.return_60d_pct}</span></div>
          <div>뉴스<br/><span className="text-on-surface">{data.score_breakdown.news_decoupling}</span></div>
        </div>
        {data.fake_hot_signals.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {data.fake_hot_signals.map((s) => (
              <span
                key={s}
                className="inline-flex items-center rounded-full border border-error/30 bg-error/8 px-2 py-0.5 text-[10px] text-error"
              >
                ⚠ {s}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {/* ETF buy options */}
      <div className="rounded-lg border border-primary/25 bg-primary/5 p-3">
        <div className="flex items-center gap-1.5 mb-1.5">
          <span className="material-symbols-outlined text-primary text-base">
            shopping_cart
          </span>
          <span className="text-[11px] uppercase tracking-[0.16em] text-primary/90">
            매수 가능 ETF
          </span>
        </div>
        <ETFList etfs={data.etf_options} />
      </div>

      {/* Watchlist hits (themes only) */}
      {isTheme && inWatchlist.length > 0 ? (
        <div className="text-[11px] text-tertiary">
          ✓ 워치리스트 보유/관심 {inWatchlist.length}종목 포함:{" "}
          <span className="font-mono">{inWatchlist.join(", ")}</span>
        </div>
      ) : null}

      {/* Top stocks toggle */}
      {topStocks.length > 0 ? (
        <div>
          <button
            type="button"
            onClick={() => setStocksOpen((v) => !v)}
            className="text-[11px] text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm">
              {stocksOpen ? "expand_less" : "expand_more"}
            </span>
            대표 종목 {topStocks.length}개
          </button>
          {stocksOpen ? (
            <ul className="mt-2 space-y-1.5">
              {topStocks.map((s) => (
                <li
                  key={s.code}
                  className="flex items-center justify-between text-[12px] border-b border-outline-variant/10 pb-1.5"
                >
                  <span className="text-on-surface">
                    <span className="font-mono text-primary/70 text-[10px] mr-2">
                      {s.code}
                    </span>
                    {s.name}
                  </span>
                  <span className="flex gap-3 text-[11px]">
                    <span className="text-on-surface-variant">
                      5D <span className={s.perf_5d != null && s.perf_5d > 0 ? "text-primary" : "text-error"}>{formatPct(s.perf_5d)}</span>
                    </span>
                    <span className="text-on-surface-variant">
                      60D <span className={s.perf_60d != null && s.perf_60d > 0 ? "text-primary" : "text-error"}>{formatPct(s.perf_60d)}</span>
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
