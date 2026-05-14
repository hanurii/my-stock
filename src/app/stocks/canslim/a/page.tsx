import fs from "fs/promises";
import path from "path";
import { type CanslimCandidate } from "../CanslimTable";
import { AnnualEarningsTable, TurnaroundTable, NewListingTable, type AnnualCandidate, type TurnaroundCandidate, type NewListingCandidate } from "../AnnualEarningsTable";
import { AScoredTable, type AScoredCandidate } from "../AScoredTable";

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
  scored_candidates?: AScoredCandidate[];
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

  // C 통과 종목 수 계산 (A는 C 통과의 부분집합 — 표시용)
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

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — A: 연간 EPS
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 두 번째 글자 &lsquo;A&rsquo; — 최근 실적이 일시적이지 않다는 점을 연간 EPS·ROE로 입증.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          메인 트랙 (모두 충족, AND): ① 최근 3년 연속 EPS 증가 ② 3년 평균 +25% 이상 ③ <strong className="text-on-surface-variant">ROE ≥ 12%</strong> <em className="text-on-surface-variant/80">또는</em> <strong className="text-on-surface-variant">세전 마진율 ≥ 15% (ROE ≥ 8% 바닥선)</strong> ④ 직전 분기 EPS YoY ≥ 3년 평균/3 (둔화 게이트) ⑤ 비경기민감 (KSIC 24·20·17·22·29 제외).
          {" "}ROE ≥ 17% <span className="px-1 py-0.5 rounded bg-emerald-500/15 text-emerald-300">글로벌 ROE</span> · ≥ 25% <span className="px-1 py-0.5 rounded bg-emerald-600/20 text-emerald-300 font-bold">탁월 ROE</span>.
          {" "}마진 ≥ 15% <span className="px-1 py-0.5 rounded bg-amber-500/15 text-amber-300">🥇 우수 마진</span> · ≥ 20% <span className="px-1 py-0.5 rounded bg-amber-600/20 text-amber-200 font-bold">🏆 탁월 마진</span>.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          입력 모집단: <strong className="text-on-surface-variant">C 통과 종목 {cMainCount}개</strong>의 부분집합 ·
          {aData
            ? ` 생성일 ${aData.generated_at} · 평가 ${aData.c_input_count}종목 · 메인 ${aData.a_passed_count} + 턴어라운드 ${aData.turnaround_count}${
                aData.preliminary_turnaround_count ? ` + 예비 ${aData.preliminary_turnaround_count}` : ""
              }${
                aData.new_listing_count ? ` + 신규상장 ${aData.new_listing_count}` : ""
              }`
            : " A 데이터 미생성 (`python scripts/screen_canslim_a.py` 실행 필요)"}
        </p>
      </header>

      {/* A 본문 */}
      <section>
        {aData ? (
          <div className="space-y-6">
            <div>
              <h4 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
                <span className="material-symbols-outlined text-base text-emerald-300">check_circle</span>
                메인 트랙 ({aData.candidates.length}종목)
              </h4>
              <AnnualEarningsTable candidates={aData.candidates} />
            </div>
            <div>
              <h4 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
                <span className="material-symbols-outlined text-base text-tertiary">change_circle</span>
                턴어라운드 트랙 ({aData.turnaround_candidates.length}종목
                {aData.preliminary_turnaround_count ? ` — 정통 ${aData.turnaround_count} + ` : ""}
                {aData.preliminary_turnaround_count ? <span className="text-amber-400">예비 {aData.preliminary_turnaround_count}</span> : null}
                {aData.preliminary_turnaround_count ? ")" : ")"}
                <span className="text-xs text-on-surface-variant/60 font-normal ml-2">
                  · 정통: 연 EPS +5%↑ + 분기 2분기 +50%↑ + TTM 사상 최고치 90%↑ · 예비: +0%/+30%/80%
                </span>
              </h4>
              <TurnaroundTable candidates={aData.turnaround_candidates} />
            </div>
            {aData.new_listing_candidates && aData.new_listing_candidates.length > 0 && (
              <div>
                <h4 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
                  <span className="material-symbols-outlined text-base text-blue-300">new_releases</span>
                  신규 상장 트랙 ({aData.new_listing_candidates.length}종목)
                  <span className="text-xs text-on-surface-variant/60 font-normal ml-2">
                    · 상장 &lt;3년 (연 데이터 부족) + 분기 EPS·매출 모두 +25%↑ 지속 + 비경기민감
                  </span>
                </h4>
                <NewListingTable candidates={aData.new_listing_candidates} />
              </div>
            )}
            {aData.scored_candidates && aData.scored_candidates.length > 0 && (
              <div>
                <h4 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
                  <span className="material-symbols-outlined text-base text-primary">leaderboard</span>
                  A 충족도 점수 ({aData.scored_candidates.length}종목, 100점 만점)
                  <span className="text-xs text-on-surface-variant/60 font-normal ml-2">
                    · 한국 시장(사이클 종목 주도) 보정 — O&apos;Neil 책 기준에 얼마나 가까운지 정량화
                  </span>
                </h4>
                <AScoredTable candidates={aData.scored_candidates} />
              </div>
            )}
          </div>
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
          &lsquo;A&rsquo; 원칙 — 12가지 핵심 (William O&apos;Neil)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            { title: "1. 연간 EPS 증가율 (핵심)", body: "최근 3년 연속 EPS 매년 증가 + 권장 25~50%↑. 5년 연속이면 최고. 위기 한 해 둔화는 다음해 회복 시 OK. 통과율 전체의 20% 미만." },
            { title: "2. 성장 둔화 경고", body: "직전 3년 30%+ 성장이 최근 분기 10~15%로 떨어지면 성장주 생명 다함. 분기 EPS가 연간 평균의 1/3 이하면 탈락 신호." },
            { title: "3. ROE", body: "최소 17% (경영진 우수성). 탁월한 성장주는 25~50%. ROE가 너무 낮으면 #12 세전 순이익 마진율로 대체 평가." },
            { title: "4. 주당현금흐름 (CPS)", body: "CPS = 영업CF / 발행주식. 일부 우수 성장주는 CPS가 EPS보다 20%↑ (가점)." },
            { title: "5. 안정성 지수", body: "20~25 미만 이상적, 30 초과 경기민감주. 분기 EPS 추세선 편차로 1~99 점수화 (낮을수록 안정)." },
            { title: "6. 경기민감주 회피", body: "철강·화학·제지·고무·기계 (KSIC 24·20·17·22·29). 강세장 막바지 반짝." },
            { title: "7. 턴어라운드 (별도 트랙)", body: "연 EPS 5~10%↑ + 분기 EPS 2분기 연속 급증 + TTM 사상 최고치 근접. 마진 ≥ 15% 시 TTM 게이트 면제 (회복 초기 종목 구제)." },
            { title: "8. 신규 상장 (별도 트랙)", body: "상장 <3년: 최근 5~6분기 EPS 큰 폭 + 매출 동반 (별도 트랙으로 구현)." },
            { title: "9. PER 사용 원칙", body: "PER 자체로 매수/매도 판단 금지. 낮다고 매수 X, 높다고 외면 X. 좋은 주식은 비싸다." },
            { title: "10. 목표주가 산정", body: "목표가 = (2년 후 EPS 예상치) × (매수 지점 PER) × 2 (강세장 절정엔 ×2.25). 신흥 단계 PER 20 → 확장 종료 PER 45 (≈125% 확장)." },
            { title: "11. 핵심 결론", body: "지난 3년 눈에 띄는 EPS 증가율 + 최근 강력한 실적 호전 — 두 축에 어긋나면 관심 갖지 마라." },
            {
              title: "12. 세전 순이익 마진율 — ROE 대안 게이트",
              body:
                "수식: (법인세비용차감전순이익 ÷ 매출액) × 100. DART 사업보고서(연간 IS) 직접 조회. " +
                "ROE 12% 미달이어도 마진 ≥ 15% AND ROE ≥ 8% 바닥선 충족 시 메인 트랙 통과 인정 (책의 'ROE 낮을 시 마진 대안' 정신). " +
                "근거: ROE는 부채·자기자본 구조로 왜곡될 수 있지만, 마진은 비즈니스 본연의 가격결정력·해자(moat)를 직접 보여줌. " +
                "한국 KOSPI 분포: ≥20% 상위 5%(탁월), ≥15% 상위 10%(우수), ≥10% 상위 25%(양호).",
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
