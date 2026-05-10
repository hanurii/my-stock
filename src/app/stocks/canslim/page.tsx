import fs from "fs/promises";
import path from "path";
import { CanslimTable, type CanslimCandidate } from "./CanslimTable";

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

async function getData(): Promise<CanslimData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

const USER_C_THRESHOLD = 23;

export default async function CanslimPage() {
  const data = await getData();

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

  const main = data.candidates.filter(
    (c) => c.criteria.C.yoy_pct !== null && c.criteria.C.yoy_pct !== undefined && c.criteria.C.yoy_pct >= USER_C_THRESHOLD,
  );
  const turnaround = data.candidates.filter((c) => c.criteria.C.is_turnaround);

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
          분기 EPS YoY <strong className="text-on-surface-variant">+{USER_C_THRESHOLD}% 미만</strong> 종목은 노출 제외 (사용자 컷오프). 흑자전환 종목은 별도 섹션.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일: {data.generated_at} · 평가 {data.evaluated_count.toLocaleString()}종목 · 메인 노출 {main.length} · 흑자전환 {turnaround.length}
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

      {/* 메인 테이블 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">trending_up</span>
          분기 EPS YoY +{USER_C_THRESHOLD}% 이상 ({main.length}종목)
        </h3>
        <CanslimTable candidates={main} mode="main" />
      </section>

      {/* 흑자전환 섹션 */}
      {turnaround.length > 0 && (
        <section>
          <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary">flash_on</span>
            흑자전환 종목 ({turnaround.length})
          </h3>
          <p className="text-xs text-on-surface-variant/60 mb-3">
            전년 같은 분기에 적자였다 올해 흑자로 돌아온 종목. YoY % 비교는 불가하지만 강력한 신호.
          </p>
          <CanslimTable candidates={turnaround} mode="turnaround" />
        </section>
      )}

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

      {/* A·N·S·L·I·M 진행 상황 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-on-surface-variant">timeline</span>
          나머지 6원칙 — 향후 추가 예정
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          {[
            { letter: "A", name: "Annual Earnings", body: "연간 순이익 3년 이상 +25% 성장 + ROE" },
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
