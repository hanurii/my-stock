import fs from "fs/promises";
import path from "path";
import { type CanslimCandidate } from "../CanslimTable";
import { CanslimAScoreTable, type CanslimACandidate } from "../CanslimAScoreTable";

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

interface TrackCounts {
  orthodox: number;
  turnaround_orthodox: number;
  turnaround_preliminary: number;
  new_listing: number;
  unclassified: number;
}

interface CanslimAData {
  generated_at: string;
  schema_version: number;
  c_input_count: number;
  track_counts: TrackCounts;
  candidates: CanslimACandidate[];
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

export default async function CanslimAPage() {
  const [data, aData] = await Promise.all([getData(), getAData()]);

  // C 통과 종목 수 (표시용)
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

  const tc = aData?.track_counts;

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — A: 연간 EPS
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 두 번째 글자 &lsquo;A&rsquo; — 최근 실적이 일시적이지 않다는 점을 연간 EPS·ROE로 입증.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5 leading-relaxed">
          <strong className="text-on-surface-variant">3트랙 × 50점 만점 점수 체계 (v2).</strong>{" "}
          모든 C 통과 종목을 트랙 (정통 A · 턴어라운드 · 신규상장) 으로 분류 후 점수 부여.
          탈락/통과 없음, 점수가 곧 가치.
          {" "}<strong className="text-on-surface-variant">정통 A</strong>: EPS 지속성 10 + 성장 강도 25 + 수익성 (ROE) 15.
          {" "}<strong className="text-on-surface-variant">턴어라운드</strong>: 회복 5 + 분기 급증 25 + TTM 5 + 수익성 15.
          {" "}<strong className="text-on-surface-variant">신규상장</strong>: 분기 EPS 25 + 분기 매출 5 + 수익성 15 + 안정성 5.
          {" "}마진은 점수에서 제외, 5단계 라벨로 별도 노출. 경기민감은 정보 라벨만, 점수 영향 없음.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          입력 모집단: <strong className="text-on-surface-variant">C 통과 종목 {cMainCount}개</strong> ·
          {aData && tc
            ? ` 생성일 ${aData.generated_at} · 총 ${aData.candidates.length}종목 (정통 A ${tc.orthodox} · 턴어라운드 ${tc.turnaround_orthodox} · 예비 ${tc.turnaround_preliminary} · 신규상장 ${tc.new_listing} · 분류불가 ${tc.unclassified} → 0점)`
            : " A 데이터 미생성 (`python scripts/screen_canslim_a.py` 실행 필요)"}
        </p>
      </header>

      {/* A 본문 */}
      <section>
        {aData ? (
          <CanslimAScoreTable candidates={aData.candidates} />
        ) : (
          <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-center text-sm text-on-surface-variant/70">
            A 스크리닝 데이터가 아직 생성되지 않았습니다.
            <br />
            <span className="text-[11px] text-on-surface-variant/50 mt-1 block">
              <code className="px-1.5 py-0.5 bg-surface-container/50 rounded">python scripts/screen_canslim_a.py</code> 실행 후 새로고침하세요.
            </span>
          </div>
        )}
      </section>

      {/* A 원칙 학습 섹션 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">menu_book</span>
          &lsquo;A&rsquo; 원칙 — 핵심 개념 (William O&apos;Neil + 한국형 보정)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            {
              title: "1. 연간 EPS — A 의 핵심",
              body: "최근 3년 연속 EPS 매년 증가 + 권장 +25%↑. 정통 A 트랙 점수의 절반 (25점) 을 차지. 한 해 dip 면 부분 점수.",
            },
            {
              title: "2. ROE — 수익성",
              body: "한국형 만점 12% · 글로벌 만점 17% · 부분 점수 8~12% · 그 미만 부분 점수. 점수 척도가 세 트랙 공통.",
            },
            {
              title: "3. 세전 마진율 — 라벨만",
              body: "(법인세비용차감전이익 / 매출액) × 100. 점수에 들어가지 않고 5단계 라벨로만 노출 (매우높음 ≥20% · 높음 15~20% · 중간 10~15% · 낮음 5~10% · 매우낮음).",
            },
            {
              title: "4. 턴어라운드 트랙",
              body: "적자→흑자 V자 회복. 정통: 연 +5%↑ + 2분기 +50%↑ + TTM 90%↑. 예비: +3%↑ / +30%↑ / 80%↑. 분기 급증 강도 25점이 핵심.",
            },
            {
              title: "5. 신규상장 트랙",
              body: "상장 < 3년 (연 데이터 4년 미달). 분기 EPS·매출 2분기 연속 +25%↑ 입장 조건. 분기 EPS 강도 25점이 핵심.",
            },
            {
              title: "6. 경기민감주 — 페널티 없음",
              body: "철강·화학·제지·고무·기계 (KSIC 24·20·17·22·29). 한국 시장에선 짧은 구간 매력적일 수 있어 점수 페널티 없음. ⚠️ 정보 라벨만 표시.",
            },
            {
              title: "7. 등급 컷오프 (세 트랙 공통)",
              body: "40↑ 최상 · 30~39 상 · 20~29 중 · <20 하. 모든 트랙 50점 만점이라 트랙 구분 없이 동일 등급 적용.",
            },
            {
              title: "8. 정렬",
              body: "점수 내림차순. 동점 시 수익성 점수 (15점 공통 척도) → 종목 코드 사전순. 트랙 우선 정렬 없음 — 점수가 곧 가치.",
            },
          ].map((c) => (
            <div key={c.title} className="bg-surface-container/50 rounded-lg p-3">
              <p className="font-medium text-on-surface mb-1">{c.title}</p>
              <p className="text-on-surface-variant leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
