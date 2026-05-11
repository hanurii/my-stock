import fs from "fs/promises";
import path from "path";
import { CanslimTable, type CanslimCandidate } from "./CanslimTable";
import { AnnualEarningsTable, TurnaroundTable, NewListingTable, type AnnualCandidate, type TurnaroundCandidate, type NewListingCandidate } from "./AnnualEarningsTable";
import { AScoredTable, type AScoredCandidate } from "./AScoredTable";

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

export default async function CanslimPage() {
  const [data, aData] = await Promise.all([getData(), getAData()]);

  if (!data || data.candidates.length === 0) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            CAN SLIM 발굴 — C: 현재 분기 EPS
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">데이터가 아직 생성되지 않았습니다.</p>
        </header>
      </div>
    );
  }

  // 평가된 universe 내 시총 순위 부여
  const rankByCode = new Map<string, number>();
  [...data.candidates]
    .sort((a, b) => b.market_cap_eok - a.market_cap_eok)
    .forEach((c, idx) => rankByCode.set(c.code, idx + 1));

  const main = data.candidates.filter((c) => {
    const cr = c.criteria.C;
    if (cr.yoy_pct === null || cr.yoy_pct === undefined) return false;
    if (cr.yoy_pct < USER_C_THRESHOLD) return false;
    // 매출 동반 검증: 매출 +25% 이상 OR 매출 3분기 가속 둘 중 하나라도 없으면 제외
    const salesAccompany = (cr.sales_yoy_pct !== null && cr.sales_yoy_pct >= 25) || cr.sales_accel_3q;
    if (!salesAccompany) return false;
    // O'Neil 원전 가속화 게이트: EPS 가속 (3분기 단조 증가) 또는 직전 분기 대비 가속 둘 중 하나 필수
    const accelerating = cr.eps_accel_3q || ((cr.accel_delta_pp ?? 0) > 0);
    if (!accelerating) return false;
    // O'Neil 원전 경고 자동 제외: 2분기 연속 EPS 감소 / 증가율 2/3 둔화
    if (cr.consecutive_decline_quarters >= 2) return false;
    if (cr.severe_decel) return false;
    return true;
  });

  const marketGo = data.market_status.passed;
  const marketColor = marketGo ? "#95d3ba" : "#ffb4ab";

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — C: 현재 분기 EPS
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 첫 글자 &lsquo;C&rsquo; — 분기 주당순이익이 전년 동기 대비 얼마나 크게 늘었는가.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          노출 조건: 분기 EPS YoY <strong className="text-on-surface-variant">+{USER_C_THRESHOLD}% 이상</strong> AND <strong className="text-on-surface-variant">매출 동반</strong>(분기 매출 +25% OR 3분기 매출 가속). 흑자전환은 절댓값 분모 공식으로 함께 평가.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일: {data.generated_at} · 평가 {data.evaluated_count.toLocaleString()}종목 · 노출 {main.length}종목
        </p>
      </header>

      {/* 시장 추세 미니배너 (M 원칙 미리보기) */}
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

      {/* 참고 임계값 가이드 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">straighten</span>
          분기 EPS YoY 참고선
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <p className="text-on-surface-variant/60 mb-0.5">사용자 컷오프</p>
            <p className="text-on-surface font-medium">+{USER_C_THRESHOLD}% 이상</p>
          </div>
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <p className="text-on-surface-variant/60 mb-0.5">권장 (O&apos;Neil)</p>
            <p className="text-on-surface font-medium">+25~30%</p>
          </div>
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <p className="text-on-surface-variant/60 mb-0.5">우수</p>
            <p className="text-on-surface font-medium">+40~100%</p>
          </div>
          <div className="bg-surface-container/50 rounded-lg p-2.5">
            <p className="text-on-surface-variant/60 mb-0.5">최고</p>
            <p className="text-on-surface font-medium">+100% 이상</p>
          </div>
        </div>
      </section>

      {/* 필터 설명 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 text-xs space-y-2">
        <h3 className="text-sm font-serif font-bold text-on-surface flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-base text-primary">filter_alt</span>
          필터 설명
        </h3>
        <p className="text-on-surface-variant"><strong className="text-on-surface">매출 +25% 이상</strong>: 이번 분기 매출 YoY ≥ 25% 종목 (이미 페이지 노출 조건의 일부, 토글로 좁히기 가능).</p>
        <p className="text-on-surface-variant"><strong className="text-on-surface">매출 3분기 가속</strong>: 최근 3분기 매출 YoY 성장률이 단조 증가 (이미 페이지 노출 조건의 일부).</p>
        <p className="text-on-surface-variant"><strong className="text-on-surface">EPS 가속 중</strong>: 이번 분기 EPS YoY 성장률이 직전 분기 EPS YoY 성장률보다 큰 종목 (O&apos;Neil 원전 #3 가장 중요).</p>
        <p className="text-on-surface-variant"><strong className="text-on-surface">12M EPS 신고점</strong>: 최근 12개월 4개 분기 EPS가 그 이전 모든 분기의 신고점에 근접·돌파.</p>
        <p className="text-on-surface-variant"><strong className="text-on-surface">경고 없음</strong>: 2분기 연속 EPS 감소·심각 둔화·증자 희석 이력 없음.</p>
        <p className="text-emerald-300"><strong>⛔ 절대 매도 금지</strong>: 매출+EPS 모두 최근 3분기 가속 — O&apos;Neil 원전 #4 (배지로 자동 부여, 필터 X).</p>
      </section>

      {/* 메인 테이블 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">trending_up</span>
          분기 EPS YoY +{USER_C_THRESHOLD}% 이상 ({main.length}종목)
        </h3>
        <CanslimTable
          candidates={main.map((c) => ({ ...c, market_cap_rank: rankByCode.get(c.code) }))}
        />
      </section>

      {/* C 원칙 학습 섹션 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">menu_book</span>
          &lsquo;C&rsquo; 원칙 — 7가지 핵심 (William O&apos;Neil)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            { title: "1. 비교 기준", body: "반드시 전년 동기 대비. 직전 분기 비교는 계절성 왜곡. 4분기는 작년 4분기와 비교." },
            { title: "2. 최소 매수 컷오프", body: "절대 하한 +18~20% (이하는 매수 금지). 권장 +25~30%. 대세 상승기엔 +40~500%, 최고 종목 +100~500%." },
            { title: "3. 가속화 (가장 중요)", body: "증가율 절대 폭보다 직전 분기 대비 더 커지는가가 핵심. 15%→40~50% 가속이면 어닝 서프라이즈. 12개월 매분기 EPS 신고점에 근접하면 최고." },
            { title: "4. 매출액 동반", body: "EPS 폭증해도 매출 +25%↑ 또는 3분기 연속 가속해야 의미. 매출+순이익 모두 가속 중이면 특별 관리." },
            { title: "5. 미래 실적·컨센", body: "향후 1~2분기 예상치를 1년 전 같은 분기와 비교. 애널리스트 예상치 상향 횟수, 컨센 상회 빈도 확인." },
            { title: "6. 경고·위험", body: "강세장 막바지엔 +100%여도 천정 가능. 2분기 연속 EPS 감소는 심각. 증가율 2/3 둔화(100%→30%)도 심각. 증자 희석 이력 필수 확인." },
            { title: "7. 동종업계 검증", body: "같은 업종에서 눈길 끄는 기업이 단 하나도 없으면 투자 판단 자체가 틀렸을 가능성." },
          ].map((c) => (
            <div key={c.title} className="bg-surface-container/50 rounded-lg p-3">
              <p className="font-medium text-on-surface mb-1">{c.title}</p>
              <p className="text-on-surface-variant leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* A 원칙 — 활성 섹션 (C 통과 종목의 부분집합) */}
      <section>
        <header className="mb-4">
          <h3 className="text-xl sm:text-2xl font-serif font-bold text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">stacked_bar_chart</span>
            CAN SLIM 발굴 — A: 연간 EPS
          </h3>
          <p className="text-sm text-on-surface-variant mt-2">
            윌리엄 오닐의 두 번째 글자 &lsquo;A&rsquo; — 최근 실적이 일시적이지 않다는 점을 연간 EPS·ROE로 입증.
          </p>
          <p className="text-xs text-on-surface-variant/60 mt-1.5">
            메인 트랙 (모두 충족, AND): ① 최근 3년 연속 EPS 증가 ② 3년 평균 +25% 이상 ③ <strong className="text-on-surface-variant">ROE ≥ 12% (한국 보정, O&apos;Neil 원전 17%)</strong> ④ 직전 분기 EPS YoY ≥ 3년 평균/3 (둔화 게이트) ⑤ 비경기민감 (KSIC 24·20·17·22·29 제외). ROE ≥ 17% 시 <span className="px-1 py-0.5 rounded bg-emerald-500/15 text-emerald-300">글로벌 ROE</span> 배지, ≥ 25% 시 <span className="px-1 py-0.5 rounded bg-emerald-600/20 text-emerald-300 font-bold">탁월 ROE</span>.
          </p>
          <p className="text-xs text-on-surface-variant/50 mt-1">
            입력 모집단: <strong className="text-on-surface-variant">C 통과 종목 {main.length}개</strong>의 부분집합 ·
            {aData
              ? ` 생성일 ${aData.generated_at} · 평가 ${aData.c_input_count}종목 · 메인 ${aData.a_passed_count} + 턴어라운드 ${aData.turnaround_count}${
                  aData.preliminary_turnaround_count ? ` + 예비 ${aData.preliminary_turnaround_count}` : ""
                }`
              : " A 데이터 미생성 (`python scripts/screen_canslim_a.py` 실행 필요)"}
          </p>
        </header>

        {aData ? (
          <div className="space-y-6">
            {aData.scored_candidates && aData.scored_candidates.length > 0 && (
              <div>
                <h4 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
                  <span className="material-symbols-outlined text-base text-primary">leaderboard</span>
                  A 충족도 점수 ({aData.scored_candidates.length}종목, 100점 만점)
                  <span className="text-xs text-on-surface-variant/60 font-normal ml-2">
                    · 한국 시장(사이클 종목 주도) 보정 — O'Neil 원전에 얼마나 가까운지 정량화
                  </span>
                </h4>
                <AScoredTable candidates={aData.scored_candidates} />
              </div>
            )}
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
          &lsquo;A&rsquo; 원칙 — 11가지 핵심 (William O&apos;Neil)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            { title: "1. 연간 EPS 증가율 (핵심)", body: "최근 3년 연속 EPS 매년 증가 + 권장 25~50%↑. 5년 연속이면 최고. 위기 한 해 둔화는 다음해 회복 시 OK. 통과율 전체의 20% 미만." },
            { title: "2. 성장 둔화 경고", body: "직전 3년 30%+ 성장이 최근 분기 10~15%로 떨어지면 성장주 생명 다함. 분기 EPS가 연간 평균의 1/3 이하면 탈락 신호." },
            { title: "3. ROE", body: "최소 17% (경영진 우수성). 탁월한 성장주는 25~50%." },
            { title: "4. 주당현금흐름 (CPS)", body: "CPS = 영업CF / 발행주식. 일부 우수 성장주는 CPS가 EPS보다 20%↑ (가점)." },
            { title: "5. 안정성 지수", body: "20~25 미만 이상적, 30 초과 경기민감주. 분기 EPS 추세선 편차로 1~99 점수화 (낮을수록 안정)." },
            { title: "6. 경기민감주 회피", body: "철강·화학·제지·고무·기계 (KSIC 24·20·17·22·29). 강세장 막바지 반짝." },
            { title: "7. 턴어라운드 (별도 트랙)", body: "연 EPS 5~10%↑ + 분기 EPS 2분기 연속 급증 + TTM 사상 최고치 근접. (이번 범위 제외)" },
            { title: "8. 신규 상장 (별도 트랙)", body: "상장 <3년: 최근 5~6분기 EPS 큰 폭 + 매출 동반. (이번 범위 제외)" },
            { title: "9. PER 사용 원칙", body: "PER 자체로 매수/매도 판단 금지. 낮다고 매수 X, 높다고 외면 X. 좋은 주식은 비싸다." },
            { title: "10. 목표주가 산정", body: "목표가 = (2년 후 EPS 예상치) × (매수 지점 PER) × 2 (강세장 절정엔 ×2.25). 신흥 단계 PER 20 → 확장 종료 PER 45 (≈125% 확장)." },
            { title: "11. 핵심 결론", body: "지난 3년 눈에 띄는 EPS 증가율 + 최근 강력한 실적 호전 — 두 축에 어긋나면 관심 갖지 마라." },
          ].map((c) => (
            <div key={c.title} className="bg-surface-container/50 rounded-lg p-3">
              <p className="font-medium text-on-surface mb-1">{c.title}</p>
              <p className="text-on-surface-variant leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* N·S·L·I·M 자리표시자 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-on-surface-variant">timeline</span>
          나머지 5원칙 — 향후 추가 예정
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
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
