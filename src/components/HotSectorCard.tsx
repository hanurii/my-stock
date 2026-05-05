"use client";

import { useState } from "react";
import {
  formatBillion,
  formatPct,
  type KoreanSector,
  type KoreanTheme,
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

function InvestorCell({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number | null;
  highlight?: "turn" | null;
}) {
  const positive = value != null && value > 0;
  return (
    <div
      className={`flex flex-col items-center rounded-md border px-2 py-1.5 ${
        highlight === "turn"
          ? "border-tertiary/40 bg-tertiary/5"
          : positive
            ? "border-primary/40 bg-primary/8"
            : "border-on-surface-variant/15 bg-on-surface-variant/5"
      }`}
    >
      <span className="text-[10px] uppercase tracking-[0.16em] text-on-surface-variant/80">
        {label}
        {highlight === "turn" ? <span className="text-tertiary ml-1">⚡</span> : null}
      </span>
      <span
        className={`text-xs sm:text-sm font-medium ${
          highlight === "turn"
            ? "text-tertiary"
            : positive
              ? "text-primary"
              : "text-on-surface-variant"
        }`}
      >
        {formatBillion(value)}
      </span>
    </div>
  );
}

// 60D vs 5D 비교로 추세 변화 한 줄 코멘트 자동 생성
function trendComment(data: SectorOrTheme): { text: string; tone: "primary" | "tertiary" | "warning" | "error" | "neutral" } {
  const f60 = data.foreign_60d_billion ?? 0;
  const f5 = data.foreign_5d_billion ?? 0;
  const o60 = data.organ_60d_billion ?? 0;
  const o5 = data.organ_5d_billion ?? 0;
  const i60 = data.individual_60d_billion ?? 0;
  const p60 = data.perf_60d ?? 0;
  const p5 = data.perf_5d ?? 0;

  const fTurn = f60 < 0 && f5 > 0;
  const fContinue = f60 > 0 && f5 > 0;
  const fLeaving = f60 < 0 && f5 < 0;
  const fProfitTaking = f60 > 0 && f5 < 0;

  // 1. 외인 turn-around + 기관도 함께 매수 → 가장 강한 반전 신호
  if (fTurn && o5 > 0) {
    return {
      text: "외인 매도 → 5D 매수 전환 + 기관 동반 매수, 추세 반전 가능성",
      tone: "tertiary",
    };
  }
  // 2. 외인+기관 모두 60D/5D 지속 매수
  if (fContinue && o60 > 0 && o5 > 0) {
    return {
      text: "외인·기관 60D/5D 지속 매수, 안정 추세 유지 중",
      tone: "primary",
    };
  }
  // 3. 외인 매도 지속 + 개인이 받음 + 가격 강세 → 후반부 위험
  if (fLeaving && i60 > 0 && p60 > 10) {
    return {
      text: "외인 매도 지속, 개인이 받는 중 + 가격 강세 — 후반부 패턴 주의",
      tone: "warning",
    };
  }
  // 4. 외인 turn 단독
  if (fTurn) {
    return {
      text: "외인 60D 매도 → 5D 매수 전환, 단기 모멘텀 변화 시작",
      tone: "tertiary",
    };
  }
  // 5. 외인 차익 실현
  if (fProfitTaking) {
    return {
      text: "외인 60D 매수 누적이나 5D 매도 시작, 차익 실현 가능성",
      tone: "warning",
    };
  }
  // 6. 외인 지속 매수
  if (fContinue) {
    return { text: "외인 60D/5D 매수 지속", tone: "primary" };
  }
  // 7. 외인 매도 지속 + 가격도 약세
  if (fLeaving && p60 < 0) {
    return { text: "외인 매도 지속 + 가격 약세, 약세 추세", tone: "error" };
  }
  // 8. 외인 매도 + 가격 횡보
  if (fLeaving) {
    return { text: "외인 60D/5D 매도 지속, 추세 약화", tone: "error" };
  }
  return { text: "뚜렷한 추세 변화 신호 없음", tone: "neutral" };
}

const TONE_CLASS = {
  primary: "text-primary border-primary/30 bg-primary/8",
  tertiary: "text-tertiary border-tertiary/40 bg-tertiary/8",
  warning: "text-error/90 border-error/30 bg-error/5 border-dashed",
  error: "text-error border-error/30 bg-error/8",
  neutral: "text-on-surface-variant border-on-surface-variant/20 bg-on-surface-variant/5",
} as const;

export function HotSectorCard({ data }: { data: SectorOrTheme }) {
  const [stocksOpen, setStocksOpen] = useState(false);

  const isTheme = "theme_name" in data;
  const topStocks = isTheme
    ? (data as KoreanTheme).representative_stocks
    : (data as KoreanSector).top_stocks;
  const inWatchlist = isTheme ? (data as KoreanTheme).in_watchlist : [];

  // turn-around 표시: 60D 음수 + 5D 양수
  const turn = (v60: number | null, v5: number | null): "turn" | null =>
    v60 != null && v5 != null && v60 < 0 && v5 > 0 ? "turn" : null;

  const comment = trendComment(data);

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

      {/* 누적 순매수 — 60일 그리드 */}
      <div>
        <p className="text-[10px] uppercase tracking-[0.18em] text-on-surface-variant/70 mb-2">
          60일 누적 순매수
        </p>
        <div className="grid grid-cols-3 gap-2">
          <InvestorCell label="외국인" value={data.foreign_60d_billion} />
          <InvestorCell label="기관" value={data.organ_60d_billion} />
          <InvestorCell label="개인" value={data.individual_60d_billion} />
        </div>
      </div>

      {/* 누적 순매수 — 5일 그리드 (turn-around 시 ⚡) */}
      <div>
        <p className="text-[10px] uppercase tracking-[0.18em] text-on-surface-variant/70 mb-2">
          5일 누적 순매수 <span className="text-on-surface-variant/60 normal-case tracking-normal">(단기 변화)</span>
        </p>
        <div className="grid grid-cols-3 gap-2">
          <InvestorCell
            label="외국인"
            value={data.foreign_5d_billion}
            highlight={turn(data.foreign_60d_billion, data.foreign_5d_billion)}
          />
          <InvestorCell
            label="기관"
            value={data.organ_5d_billion}
            highlight={turn(data.organ_60d_billion, data.organ_5d_billion)}
          />
          <InvestorCell
            label="개인"
            value={data.individual_5d_billion}
            highlight={turn(data.individual_60d_billion, data.individual_5d_billion)}
          />
        </div>
        <p className="text-[10px] text-on-surface-variant/60 mt-1.5">
          ⚡ = 60D 매도였으나 5D 매수 전환 (추세 반전 가능성) · 개인 = −(외인+기관) 추정
        </p>
      </div>

      {/* 추세 변화 한 줄 코멘트 */}
      <div className={`rounded-md border px-3 py-2 text-[12px] ${TONE_CLASS[comment.tone]}`}>
        💬 {comment.text}
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
