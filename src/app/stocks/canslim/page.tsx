import fs from "fs/promises";
import path from "path";
import Link from "next/link";
import { type CanslimCandidate } from "./CanslimTable";
import { type AnnualCandidate, type TurnaroundCandidate, type NewListingCandidate } from "./AnnualEarningsTable";

interface MarketStatus {
  kospi_trend_verdict: string;
  passed: boolean;
  value: string;
  detail: string;
  kospi_close: number | null;
}

interface CanslimData {
  generated_at: string;
  scanned_count: number;
  evaluated_count: number;
  market_status: MarketStatus;
  candidates: CanslimCandidate[];
}

interface CanslimAData {
  generated_at: string;
  c_input_count: number;
  a_passed_count: number;
  turnaround_count: number;
  preliminary_turnaround_count?: number;
  new_listing_count?: number;
  candidates: AnnualCandidate[];
  turnaround_candidates: TurnaroundCandidate[];
  new_listing_candidates?: NewListingCandidate[];
}

async function getData(): Promise<CanslimData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

async function getAData(): Promise<CanslimAData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-a-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

const USER_C_THRESHOLD = 25;

export default async function CanslimIndexPage() {
  const [data, aData] = await Promise.all([getData(), getAData()]);

  // C 통과 종목 수 계산
  const cMainCount = data
    ? data.candidates.filter((c) => {
        const cr = c.criteria.C;
        if (cr.yoy_pct === null || cr.yoy_pct === undefined) return false;
        if (cr.yoy_pct < USER_C_THRESHOLD) return false;
        const salesAccompany = (cr.sales_yoy_pct !== null && cr.sales_yoy_pct >= 25) || cr.sales_accel_3q;
        if (!salesAccompany) return false;
        const accelerating = cr.eps_accel_3q || ((cr.accel_delta_pp ?? 0) > 0);
        if (!accelerating) return false;
        if (cr.consecutive_decline_quarters >= 2) return false;
        if (cr.severe_decel) return false;
        return true;
      }).length
    : 0;

  const marketGo = data?.market_status.passed ?? false;
  const marketColor = marketGo ? "#95d3ba" : "#ffb4ab";

  const aMainCount = aData?.a_passed_count ?? 0;
  const aTurnaroundCount = aData?.turnaround_count ?? 0;
  const aPrelimCount = aData?.preliminary_turnaround_count ?? 0;
  const aNewListingCount = aData?.new_listing_count ?? 0;

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 7원칙(C·A·N·S·L·I·M)을 한국 시장에 적용한 종목 발굴 시스템.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          각 원칙은 독립 페이지에서 평가하며 cascading filter 구조: 다음 글자는 이전 글자 통과 종목의 부분집합.
        </p>
      </header>

      {/* 시장 추세 미니배너 (M 미리보기) */}
      {data && (
        <section
          className="rounded-xl ghost-border p-4 flex items-center gap-3"
          style={{ backgroundColor: `${marketColor}10` }}
        >
          <span className="material-symbols-outlined text-2xl" style={{ color: marketColor }}>
            {marketGo ? "trending_up" : "trending_down"}
          </span>
          <div className="flex-1">
            <p className="text-sm font-medium text-on-surface">
              시장 추세(M): <span style={{ color: marketColor }}>{data.market_status.value}</span>
            </p>
            <p className="text-xs text-on-surface-variant/70 mt-0.5">{data.market_status.detail}</p>
          </div>
        </section>
      )}

      {/* C·A 카드 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">check_circle</span>
          구현된 원칙
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* C 카드 */}
          <Link
            href="/stocks/canslim/c"
            className="block bg-surface-container-low rounded-xl ghost-border p-5 hover:bg-surface-container/50 transition-all group"
          >
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-3xl font-serif font-bold text-primary">C</span>
              <span className="text-sm text-on-surface-variant">Current Quarterly Earnings</span>
            </div>
            <p className="text-base font-medium text-on-surface mb-1">현재 분기 EPS</p>
            <p className="text-xs text-on-surface-variant/80 leading-relaxed mb-3">
              분기 EPS YoY +25% 이상 + 매출 동반 + 가속 + 경고 없음 (O&apos;Neil 원전 강화)
            </p>
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-bold text-primary">{cMainCount}</span>
              <span className="text-xs text-on-surface-variant/60">통과 종목</span>
            </div>
            <p className="text-xs text-primary/80 mt-3 group-hover:text-primary flex items-center gap-1">
              상세 보기
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </p>
          </Link>

          {/* A 카드 */}
          <Link
            href="/stocks/canslim/a"
            className="block bg-surface-container-low rounded-xl ghost-border p-5 hover:bg-surface-container/50 transition-all group"
          >
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-3xl font-serif font-bold text-primary">A</span>
              <span className="text-sm text-on-surface-variant">Annual Earnings Increases</span>
            </div>
            <p className="text-base font-medium text-on-surface mb-1">연간 EPS</p>
            <p className="text-xs text-on-surface-variant/80 leading-relaxed mb-3">
              3년 연속 EPS 증가 + 평균 +25%↑ + ROE ≥ 12% (한국 보정) + 비경기민감 + 턴어라운드·신규상장 트랙
            </p>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-on-surface-variant/80 text-xs">메인 <strong className="text-primary text-base">{aMainCount}</strong></span>
              <span className="text-on-surface-variant/80 text-xs">턴어라운드 <strong className="text-tertiary text-base">{aTurnaroundCount}</strong></span>
              {aPrelimCount > 0 && (
                <span className="text-on-surface-variant/80 text-xs">예비 <strong className="text-amber-400 text-base">{aPrelimCount}</strong></span>
              )}
              {aNewListingCount > 0 && (
                <span className="text-on-surface-variant/80 text-xs">신규상장 <strong className="text-blue-300 text-base">{aNewListingCount}</strong></span>
              )}
            </div>
            <p className="text-xs text-primary/80 mt-3 group-hover:text-primary flex items-center gap-1">
              상세 보기
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </p>
          </Link>
        </div>
      </section>

      {/* N·S·L·I·M 자리표시자 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-on-surface-variant">timeline</span>
          나머지 5원칙 — 향후 추가 예정
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
          {[
            { letter: "N", name: "New Highs", body: "52주 신고가 근접 + 베이스 돌파" },
            { letter: "S", name: "Supply & Demand", body: "거래량 급증 + 유통주식 수급" },
            { letter: "L", name: "Leader", body: "상대강도(RS) 상위 20%" },
            { letter: "I", name: "Institutional", body: "외인+기관 매집 + 분기 증가 추세" },
            { letter: "M", name: "Market Direction", body: "지수 200일선 위 + 50일선이 위로" },
          ].map((l) => (
            <div key={l.letter} className="bg-surface-container-low rounded-lg ghost-border p-3 opacity-60">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-2xl font-serif font-bold text-on-surface-variant">{l.letter}</span>
                <span className="text-[11px] text-on-surface-variant/70">{l.name}</span>
              </div>
              <p className="text-on-surface-variant/80 leading-relaxed">{l.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
