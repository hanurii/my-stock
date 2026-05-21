import fs from "fs/promises";
import path from "path";
import { SupplyDemandTable, type SCandidate } from "../SupplyDemandTable";

interface SData {
  generated_at: string;
  schema_version: string;
  c_universe_count: number;
  c_passed_count: number;
  scored_count: number;
  shareholder_covered: number;
  debt_covered: number;
  financial_count: number;
  scoring: {
    shareholder_max: number;
    shareholder_base: number;
    debt_max: number;
    financial_debt_score: number;
    total_max: number;
  };
  candidates: SCandidate[];
}

async function getData(): Promise<SData | null> {
  try {
    const filePath = path.join(
      process.cwd(),
      "public",
      "data",
      "can-slim-s-candidates.json",
    );
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export default async function CanslimSPage() {
  const data = await getData();

  if (!data || data.candidates.length === 0) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            CAN SLIM 발굴 — S: 수요와 공급
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">
            데이터가 아직 생성되지 않았습니다.
          </p>
        </header>
      </div>
    );
  }

  const { scoring } = data;
  const srPct = (data.shareholder_covered / data.scored_count) * 100;
  const debtPct = (data.debt_covered / data.scored_count) * 100;

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — S: 수요와 공급
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 네 번째 글자 &lsquo;S&rsquo; — 주주환원과 부채비율로
          수급 체질을 60점 만점으로 채점.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          입력 모집단:{" "}
          <strong className="text-on-surface-variant">C 통과 종목 전체</strong>{" "}
          · 컷오프 / 통과·미통과 이분법 없음. 모든 종목이 점수와 함께 노출.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일 {data.generated_at} · C 스캔 universe{" "}
          {data.c_universe_count.toLocaleString()}종목 · C 통과 (passesCGate){" "}
          {data.c_passed_count}종목 · S 채점{" "}
          <strong className="text-on-surface-variant">{data.scored_count}개</strong>
        </p>
      </header>

      {/* 점수 체계 안내 */}
      <section className="bg-surface-container-low/50 rounded-xl ghost-border p-5">
        <h3 className="text-sm font-medium text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base">tune</span>
          점수 체계 — 총 {scoring.total_max}점
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 text-xs text-on-surface-variant/80">
          <div>
            <p className="text-on-surface-variant mb-2">
              주주가치 ({scoring.shareholder_max}점) · 기본{" "}
              {scoring.shareholder_base}점에서 가감
            </p>
            <ul className="space-y-1 list-disc list-inside">
              <li>
                자사주 소각: 1년 <strong>+5</strong> · 2년 <strong>+10</strong> ·
                3년+ <strong>+15</strong>
              </li>
              <li>
                연속 배당: 1년 <strong>+2</strong> · 2~3년 <strong>+5</strong> ·
                4년+ <strong>+10</strong>
              </li>
              <li>
                지분 희석 (5년): 건당 <strong>−5</strong>
              </li>
              <li>최종 0~50 clamp · shareholder-returns.json 미보유 시 기본 25점</li>
            </ul>
          </div>
          <div>
            <p className="text-on-surface-variant mb-2">
              부채비율 ({scoring.debt_max}점)
            </p>
            <ul className="space-y-1 list-disc list-inside">
              <li>
                ≤ 50% <strong>10점</strong> · ≤ 100% <strong>7점</strong> · ≤ 150%{" "}
                <strong>4점</strong> · ≤ 200% <strong>2점</strong> · &gt; 200%{" "}
                <strong>0점</strong>
              </li>
              <li>
                금융업 (KSIC 64·65·66){" "}
                <strong>{scoring.financial_debt_score}점 고정</strong> — 고객
                예수금 구조상 일반 점수표 미적용
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-4 pt-3 border-t border-on-surface/10 grid grid-cols-3 gap-3 text-[11px] text-on-surface-variant/70">
          <div>
            주주환원 데이터:{" "}
            <strong className="text-on-surface-variant">
              {data.shareholder_covered}
            </strong>{" "}
            / {data.scored_count} ({srPct.toFixed(1)}%)
          </div>
          <div>
            부채비율 데이터:{" "}
            <strong className="text-on-surface-variant">{data.debt_covered}</strong>{" "}
            / {data.scored_count} ({debtPct.toFixed(1)}%)
          </div>
          <div>
            금융업:{" "}
            <strong className="text-on-surface-variant">
              {data.financial_count}
            </strong>{" "}
            종목 (5점 고정)
          </div>
        </div>
      </section>

      {/* 메인 테이블 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">
            trending_up
          </span>
          전 종목 S 점수 ({data.scored_count})
        </h3>
        <p className="text-xs text-on-surface-variant/60 mb-3">
          기본 정렬: S 점수 내림차순. 컬럼 헤더 클릭으로 정렬 변경. 행 클릭으로
          세부 점수 펼치기.
        </p>
        <SupplyDemandTable candidates={data.candidates} />
      </section>

      {/* S 원칙 학습 섹션 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">menu_book</span>
          &lsquo;S&rsquo; 원칙 — 8가지 핵심 (William O&apos;Neil)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            {
              title: "1. 발행 주식수 — 작을수록 가볍다",
              body: "보통주 50억주는 공급이 많아 움직임이 둔하고, 500만주는 가벼워 의미 있는 매수만 들어와도 상승. 동일 조건이면 발행수 적은 쪽이 더 나은 수익률 — 단 자본금·유동성이 작아 상승만큼 급락도 빠르다.",
            },
            {
              title: "2. 유통 물량 / 경영진 지분",
              body: "노련한 투자자는 발행수보다 유통 물량(전체 - 대주주·임원 보유)에 주목. 경영진이 자기 회사 주식을 많이 보유하면 애착의 반증 — 대기업 1~3%, 중소기업은 그 이상이 긍정 신호. O'Neil: “경영진이 많은 주식을 보유한 기업은 자기 회사 주식에 애착을 가지고 있다는 반증이다.”",
            },
            {
              title: "3. 주식 분할 — 과도하면 천장 신호",
              body: "1대2·2대3은 적정, 1대3·1대5는 공급 급증 위험. 노련한 프로는 분할 호재에 시장이 고무됐을 때 오히려 매도하고, 공매도 표적은 기관이 이미 대규모로 보유 + 급등 후 하락 시작 종목. O'Neil: “두세 차례의 주식 분할은 천장을 쳤다는 징후” (분할 다음해 본격 상승 확률은 18% 채 안 됨).",
            },
            {
              title: "4. 자사주 매수 — 강력한 긍정 신호",
              body: "CAN SLIM 충족 기업이 장내에서 지속적으로 자기 주식을 사들이면 (1) 유통 주식 감소 (2) 가까운 매출·순이익 증가 예상 — 두 가지를 동시에 시사. O'Neil: “자사주 10%만 매수해도 무척 큰 것이다” — 특히 중소형 성장주가 그럴 경우 더욱 긍정적.",
            },
            {
              title: "5. 부채 비율 — 낮을수록 좋다",
              body: "부채 많은 기업의 EPS는 금리 상승 시 급격히 쪼그라든다. 차입의 제1원칙은 '감당할 수 없는 금액은 빌리지 않는 것'. 최근 2~3년 부채 상환한 기업은 이자비용 감소만으로 EPS 증가. 전환사채(CB)는 보통주 전환 시 EPS 희석 주의. O'Neil: “부채비율은 낮을수록 더 안전하고 더 나은 기업이다.”",
            },
            {
              title: "6. 거래량 — 수요·공급의 최고 척도",
              body: "매일의 거래량이 수요·공급 가늠 최고 도구. 하락 중 거래량이 마르면 매도 압력 소진, 상승 중 거래량 증가는 기관 매수 반영. 피벗 돌파 시 거래량은 평균 대비 +40~50% 이상(종종 +100%) 동반되어야 한다.",
            },
            {
              title: "7. 차트 모양 — 매주 관찰",
              body: "주가가 새 모양을 만들기 시작해 완성될 때까지 매주 관찰. 주간 등락폭, 거래량 증감, 종가가 고가/저가 어디에 근접한지를 점검해 '에너지 축적의 올바른 모양' 인지 '결함이 많은 속기 쉬운 모양' 인지 구분.",
            },
            {
              title: "8. 종합 — 자사주 + 경영진 지분 우선",
              body: "기업 규모와 무관하게 CAN SLIM 7원칙 모두 충족이 기본. 단 소형주는 변동성이 크고 시장 관심이 대형주↔소형주 사이를 오간다. 결론적으로 장내 자사주 매수 + 경영진 지분 보유가 큰 기업의 주식일수록 더 좋다.",
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
