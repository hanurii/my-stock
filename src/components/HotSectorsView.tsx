"use client";

import { useState, useMemo } from "react";
import type { HotSectorsData, KoreanSector, KoreanTheme } from "@/lib/hot-sectors";
import { HotSectorTabBar } from "./HotSectorTabBar";
import { HotSectorCard } from "./HotSectorCard";
import { GlobalSectorTable } from "./GlobalSectorTable";
import { SectorRotationChart } from "./SectorRotationChart";

type SortKey = "score" | "perf_60d" | "perf_20d" | "alignment";

const SORT_OPTIONS: Array<{ key: SortKey; label: string }> = [
  { key: "score", label: "RealHot 점수" },
  { key: "perf_60d", label: "60일 수익률" },
  { key: "perf_20d", label: "20일 수익률" },
  { key: "alignment", label: "3주체 일치" },
];

function sortSectors<T extends KoreanSector | KoreanTheme>(items: T[], key: SortKey): T[] {
  return [...items].sort((a, b) => {
    if (key === "score") return b.real_hot_score - a.real_hot_score;
    if (key === "perf_60d") return (b.perf_60d ?? -999) - (a.perf_60d ?? -999);
    if (key === "perf_20d") return (b.perf_20d ?? -999) - (a.perf_20d ?? -999);
    return b.three_investor_alignment_60d - a.three_investor_alignment_60d;
  });
}

// 안정 후보 — 5조건 모두 충족 (가장 엄격)
function isStableCandidate(s: KoreanSector | KoreanTheme): boolean {
  return (
    s.classification === "real_hot" &&
    (s.perf_60d ?? 0) < 100 &&
    s.three_investor_alignment_60d === 3 &&
    (s.volume_sustain_ratio ?? 0) >= 1.3 &&
    s.fake_hot_signals.length === 0
  );
}

// 검토 가능 — 한 단계 완화 (4조건 + warning 분류 허용)
function isReviewable(s: KoreanSector | KoreanTheme): boolean {
  return (
    (s.classification === "real_hot" || s.classification === "real_hot_warning") &&
    (s.perf_60d ?? 0) < 150 &&
    s.three_investor_alignment_60d >= 2 &&
    (s.volume_sustain_ratio ?? 0) >= 1.0 &&
    s.fake_hot_signals.length <= 1
  );
}

function hasETF<T extends KoreanSector | KoreanTheme>(s: T): boolean {
  return s.etf_options.length > 0;
}

type FilterMode = "all" | "safe" | "reviewable";

const FILTER_OPTIONS: Array<{ key: FilterMode; label: string; tooltip: string }> = [
  { key: "all", label: "전체", tooltip: "모든 섹터/테마 표시" },
  {
    key: "safe",
    label: "🛡️ 안정 후보만",
    tooltip:
      "5조건 모두: 🔥 진짜 핫 + 60D<100% + 3주체 모두 매수 + 거래대금 ≥1.3× + 가짜 시그널 0개",
  },
  {
    key: "reviewable",
    label: "🟡 검토 가능",
    tooltip:
      "한 단계 완화: 🔥/⚠️ + 60D<150% + 3주체 ≥2/3 + 거래대금 ≥1.0× + 가짜 시그널 ≤1개",
  },
];

export function HotSectorsView({ data }: { data: HotSectorsData }) {
  const [tab, setTab] = useState<"kr_sectors" | "kr_themes" | "global" | "rotation">("kr_sectors");
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [filterMode, setFilterMode] = useState<FilterMode>("all");
  const [etfOnly, setEtfOnly] = useState(false);
  const [showLearning, setShowLearning] = useState(false);

  const allSectors = data.korea_sectors.sectors;
  const allThemes = data.korea_themes.themes;

  const filteredSectors = useMemo(() => {
    let result = sortSectors(allSectors, sortKey);
    if (filterMode === "safe") result = result.filter(isStableCandidate);
    else if (filterMode === "reviewable") result = result.filter(isReviewable);
    if (etfOnly) result = result.filter(hasETF);
    return result;
  }, [allSectors, sortKey, filterMode, etfOnly]);
  const filteredThemes = useMemo(() => {
    let result = sortSectors(allThemes, sortKey);
    if (filterMode === "safe") result = result.filter(isStableCandidate);
    else if (filterMode === "reviewable") result = result.filter(isReviewable);
    if (etfOnly) result = result.filter(hasETF);
    return result;
  }, [allThemes, sortKey, filterMode, etfOnly]);

  // 안정 후보 0개 + safe 모드일 때 reviewable 모드의 후보 수
  const reviewableSectorsCount = useMemo(
    () => allSectors.filter(isReviewable).length,
    [allSectors],
  );
  const reviewableThemesCount = useMemo(
    () => allThemes.filter(isReviewable).length,
    [allThemes],
  );

  return (
    <div className="space-y-8">
      {/* Learning section */}
      <section className="glass-card rounded-xl ghost-border p-4 sm:p-5">
        <button
          type="button"
          onClick={() => setShowLearning((v) => !v)}
          className="flex items-center gap-2 text-sm text-primary hover:text-primary/80"
        >
          <span className="material-symbols-outlined text-base">
            {showLearning ? "expand_less" : "expand_more"}
          </span>
          섹터 vs 테마 / 점수 공식 / 분류 라벨 정의 보기
        </button>
        {showLearning ? (
          <div className="mt-4 space-y-4 text-[13px] text-on-surface-variant leading-relaxed">
            <div>
              <p className="font-medium text-on-surface mb-1">섹터 vs 테마</p>
              <p>
                <b>섹터</b>는 GICS·WICS 같은 표준 분류로 묶은 카테고리(반도체·금융·바이오 등). 안정적이고 변화가 느림.
                <b> 테마</b>는 섹터를 가로지르는 트렌드 묶음(HBM·로봇·방산 등). 정책·뉴스에 단기 변동성 큼.
              </p>
            </div>
            <div>
              <p className="font-medium text-on-surface mb-1">RealHotScore (0~100) — 중장기 추세 점수</p>
              <p>
                = 0.30 × 추세일관성(20D/60D/3M/6M 모두 양수) + 0.25 × 3주체 매집(외인+기관+개인 60일 모두 양수)
                + 0.20 × 거래대금 지속성(60D / 직전60D ≥ 1.3) + 0.15 × 60일 수익률 백분위 + 0.10 × 뉴스 디커플링
              </p>
            </div>
            <div>
              <p className="font-medium text-on-surface mb-1">ShortMomentumScore (0~100) — 단기 진입 타이밍 보조 점수</p>
              <p>
                = 0.5 × 5D 수익률 백분위 + 0.3 × 20D 수익률 백분위 + 0.2 × 5일 거래대금 스파이크 백분위
              </p>
              <p className="mt-1 text-on-surface-variant/80">
                각 항목은 전체 섹터/테마 풀 내 <b>백분위 순위</b>. 96이면 단기 모멘텀이 상위 4% 수준.
                RealHotScore와 조합으로 진입 성격을 가늠 — 둘 다 높으면 🔥 안정 진입, RealHot은 낮은데
                ShortMomentum만 높으면 🚀 신규 부상(빠른 진입 기회) 또는 ⚡ 단기 가속(막차 위험).
              </p>
            </div>
            <div>
              <p className="font-medium text-on-surface mb-1">분류 라벨</p>
              <ul className="list-disc list-inside space-y-1">
                <li>🔥 <b>진짜 핫</b>: 점수 ≥ 70 + 단기 모멘텀 50+ + 가짜 신호 없음. 안정 진입 후보.</li>
                <li>⚠️ <b>일부 우려</b>: 점수 강하지만 가짜 신호 1~2개 동반.</li>
                <li>🚀 <b>신규 부상</b>: 단기 모멘텀 강함 + 60D 추세 약함. 빠른 진입 기회 (단기 리스크).</li>
                <li>⚡ <b>단기 가속</b>: 단기만 강하고 외인 빠짐. 막차 위험.</li>
                <li>❄️ <b>식어가는 중</b>: 6M 강세였으나 최근 약화. 보유 중이면 갈아탈 시점.</li>
                <li>🟡 <b>진행 중</b>: 추세 형성 중.</li>
                <li>❌ <b>가짜 핫</b>: 가짜 신호 2개 이상. 매수 금지 권고.</li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-on-surface mb-1">가짜 핫 시그널 4가지</p>
              <ul className="list-disc list-inside space-y-1">
                <li><b>단기 스파이크</b>: 5D ≥ +5% AND 60D ±2% 이내 (잠시 튀고 횡보)</li>
                <li><b>개인 단독 주도</b>: 외인 60D &lt; 0 AND 개인 60D &gt; 0</li>
                <li><b>거래대금 단발성 폭증</b>: 5D 거래대금이 60D 평균 대비 3배+, 그러나 20D는 1.3배 미만</li>
                <li><b>뉴스 디커플링</b>: 뉴스 5D 멘션 +200%인데 60D 가격 변화 5% 미만</li>
              </ul>
            </div>
            <p className="text-[11px] text-on-surface-variant/70 italic">
              ⚠️ 점수·분류는 보조 정보입니다. 모든 시간 윈도우(5D/20D/60D/3M/6M)와 3주체 매집·거래대금·뉴스 데이터를
              직접 보고 판단하세요. 진짜 핫이라도 매수 후 분기별 점검 필수.
            </p>
          </div>
        ) : null}
      </section>

      {/* Tabs */}
      <HotSectorTabBar
        active={tab}
        onChange={(id) => setTab(id as typeof tab)}
        tabs={[
          { id: "kr_sectors", label: "🇰🇷 한국 핫 섹터" },
          { id: "kr_themes", label: "🔥 한국 핫 테마" },
          { id: "global", label: "🌍 글로벌 GICS" },
          { id: "rotation", label: "🔄 섹터 로테이션" },
        ]}
      />

      {/* Tab content */}
      {tab === "kr_sectors" || tab === "kr_themes" ? (
        <div>
          {/* Sort toggle */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <span className="text-[11px] uppercase tracking-[0.16em] text-on-surface-variant">
              정렬
            </span>
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setSortKey(opt.key)}
                className={`text-[12px] px-2.5 py-1 rounded-full border ${
                  sortKey === opt.key
                    ? "border-primary text-primary bg-primary/10"
                    : "border-outline-variant/30 text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Filter toggles */}
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <span className="text-[11px] uppercase tracking-[0.16em] text-on-surface-variant">
              필터
            </span>
            {FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setFilterMode(opt.key)}
                title={opt.tooltip}
                className={`text-[12px] px-2.5 py-1 rounded-full border ${
                  filterMode === opt.key
                    ? "border-primary text-primary bg-primary/15"
                    : "border-outline-variant/30 text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {opt.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setEtfOnly((v) => !v)}
              className={`text-[12px] px-2.5 py-1 rounded-full border ${
                etfOnly
                  ? "border-primary text-primary bg-primary/15"
                  : "border-outline-variant/30 text-on-surface-variant hover:text-on-surface"
              }`}
            >
              🛒 매수 가능 ETF 있음
            </button>
            <span className="text-[11px] text-on-surface-variant/70 ml-auto">
              {tab === "kr_sectors"
                ? `${filteredSectors.length} / ${allSectors.length}`
                : `${filteredThemes.length} / ${allThemes.length}`}
            </span>
          </div>

          {/* Filter explainer (when filter active) */}
          {filterMode !== "all" ? (
            <p className="text-[11px] text-primary/80 mb-4 leading-relaxed">
              {FILTER_OPTIONS.find((o) => o.key === filterMode)?.tooltip}
            </p>
          ) : null}

          {/* Cards or empty state */}
          {(tab === "kr_sectors" ? filteredSectors : filteredThemes).length === 0 ? (
            <div className="glass-card rounded-xl ghost-border p-8 text-center text-on-surface-variant text-sm space-y-3">
              <p>
                조건을 충족하는 {tab === "kr_sectors" ? "섹터" : "테마"}가 없습니다.
                {filterMode === "safe" ? (
                  <span className="block mt-1 text-on-surface-variant/80">
                    현재 시장은 외인이 빠지는 패턴이 많아 5조건 모두 충족하는 진짜 핫이 드뭅니다.
                  </span>
                ) : null}
              </p>
              {filterMode === "safe" &&
              (tab === "kr_sectors" ? reviewableSectorsCount : reviewableThemesCount) > 0 ? (
                <button
                  type="button"
                  onClick={() => setFilterMode("reviewable")}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-tertiary/40 text-tertiary bg-tertiary/10 text-[12px] hover:bg-tertiary/20"
                >
                  🟡 검토 가능 후보{" "}
                  {tab === "kr_sectors"
                    ? reviewableSectorsCount
                    : reviewableThemesCount}
                  개 보기 (한 단계 완화)
                </button>
              ) : (
                <p className="text-[11px]">
                  필터를 해제하거나 ⚠️ <code>real_hot_warning</code> / 🚀{" "}
                  <code>emerging</code> 분류도 직접 데이터 확인 후 검토하세요.
                </p>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
              {tab === "kr_sectors"
                ? filteredSectors.map((s) => (
                    <HotSectorCard
                      key={s.wics_name}
                      data={{
                        ...s,
                        __title: s.wics_name,
                        __subtitle: `${s.gics_mapped} · ${s.stock_count}종목`,
                      }}
                    />
                  ))
                : filteredThemes.map((t) => (
                    <HotSectorCard
                      key={t.theme_name}
                      data={{
                        ...t,
                        __title: t.theme_name,
                        __subtitle: `${t.stock_count}종목 · ${t.news_keywords.slice(0, 2).join(", ")}`,
                      }}
                    />
                  ))}
            </div>
          )}
        </div>
      ) : null}

      {tab === "global" ? (
        <section className="glass-card rounded-xl ghost-border p-5 sm:p-6">
          <div className="mb-4">
            <h2 className="text-xl font-serif text-on-surface tracking-tight">
              S&P 500 GICS 11개 섹터 ETF
            </h2>
            <p className="text-xs text-on-surface-variant mt-1">
              한국 섹터 결정의 매크로 백드롭 (SPY 벤치마크와 비교)
            </p>
          </div>
          <GlobalSectorTable
            sectors={data.global_sectors.sectors}
            spy={data.global_sectors.spy_perf}
          />
        </section>
      ) : null}

      {tab === "rotation" ? (
        <section className="glass-card rounded-xl ghost-border p-5 sm:p-6">
          <div className="mb-4">
            <h2 className="text-xl font-serif text-on-surface tracking-tight">
              섹터 로테이션
            </h2>
            <p className="text-xs text-on-surface-variant mt-1">
              과거 시점 점수와 비교해 식어가는 섹터·뜨는 섹터 추적 (히스토리 누적 시 풍부해짐)
            </p>
          </div>
          <SectorRotationChart
            snapshots={data.rotation.snapshots}
            transitions={data.rotation.transitions}
          />
        </section>
      ) : null}
    </div>
  );
}
