"use client";

import { useState } from "react";

interface GlossaryItem {
  term: string;          // 한국어 (영문)
  definition: string;    // 풀이 한 줄
  example?: string;      // 구체 사례
}

const ITEMS: GlossaryItem[] = [
  {
    term: "주가수익비율 (PER, Price-to-Earnings Ratio)",
    definition: "지금 주가가 1주당 연간 순이익의 몇 배인지. 낮을수록 싸다는 뜻.",
    example: "PER 10 = 현재 이익 그대로 가면 10년이면 본전. PER 30 = 30년 본전.",
  },
  {
    term: "현재 PER (Trailing PER)",
    definition: "최근 12개월 실제 이익을 기준으로 계산한 PER. 확정된 과거 실적이라 신뢰도 높음.",
  },
  {
    term: "예상 PER (Forward PER)",
    definition: "향후 12개월 예상 이익으로 계산한 PER. 실적 개선이 예상되면 현재 PER보다 낮게 나옴.",
    example: "현재 PER 30 → 예상 PER 20이면, 시장이 '내년 이익이 50% 늘 것'으로 보고 있다는 뜻.",
  },
  {
    term: "자기자본이익률 (ROE, Return on Equity)",
    definition: "주주가 맡긴 돈 100원으로 1년에 얼마 버는지. 높을수록 자본 효율이 좋음.",
    example: "ROE 20% = 내 돈 1억 맡기면 연 2,000만원 벌어주는 회사.",
  },
  {
    term: "주당순이익 (EPS, Earnings Per Share)",
    definition: "회사 전체 순이익을 발행 주식수로 나눈 1주당 이익. 매년 늘어나면 좋은 회사.",
    example: "작년 EPS 1,000원 → 올해 1,150원이면 EPS 성장률 15%.",
  },
  {
    term: "잉여현금흐름 (FCF, Free Cash Flow)",
    definition: "영업으로 번 현금에서 시설투자 등 필수 지출을 뺀 진짜 자유롭게 쓸 수 있는 돈.",
    example: "이 돈으로 배당·자사주매입·신규투자·부채상환 가능. 회계 이익보다 더 정직한 지표.",
  },
  {
    term: "잉여현금수익률 (FCF Yield)",
    definition: "잉여현금흐름을 시가총액으로 나눈 비율. 회사 통째로 사면 매년 받는 현금 수익률.",
    example: "시총 10조 회사가 연 FCF 7,000억이면 FCF Yield 7% — 부동산 월세보다 좋은 수준.",
  },
  {
    term: "주가순자산비율 (PBR, Price-to-Book Ratio)",
    definition: "주가가 1주당 장부상 순자산의 몇 배인지. 1.0이면 장부가와 같은 가격.",
    example: "PBR 0.8 = 회사 청산해도 받을 자산보다 싸게 거래되는 중. PBR 5 = 자산보다 5배 비쌈.",
  },
  {
    term: "기업가치/EBITDA (EV/EBITDA)",
    definition: "회사를 통째로 인수할 가격(부채 포함)을 영업현금으로 나눈 값. 본전 회수 연수와 비슷.",
    example: "EV/EBITDA 10 = 영업현금으로 10년이면 인수금 회수 가능 — 적정 수준.",
  },
  {
    term: "영업이익률",
    definition: "매출 1,000원 중 본업으로 남는 이익 비율. 높을수록 해자가 강한 회사.",
    example: "영업이익률 25% = 1만원 음식 팔아 본업으로 2,500원 남기는 가게.",
  },
  {
    term: "순이익률",
    definition: "매출 1,000원 중 세금·이자 다 빼고 진짜 통장에 남는 비율.",
  },
  {
    term: "부채비율 (Debt-to-Equity)",
    definition: "회사 빚이 자기자본의 몇 %인지. 100% 이하면 빚이 자기 돈보다 적은 안전 구간.",
    example: "부채비율 50% = 자기자본 10억, 빚 5억. 빚 부담이 적은 안정적 재무.",
  },
  {
    term: "환율 점수 (FX Score)",
    definition: "원화 가치가 5년 평균보다 어디 있는지에 따른 외화 종목 가산/감점. ±20점 범위.",
    example: "원화 강세 = 외화 매수 유리(+10~+20점), 원화 약세 = 환차손 위험(-10~-20점).",
  },
  {
    term: "5년 평균 대비 편차 (Z-Score)",
    definition: "현재 값이 5년 평균에서 표준편차의 몇 배 떨어져 있는지를 나타내는 통계 지표.",
    example: "편차 +1.5σ = '5년에 한 번 있을까 말까 한 높은 수준'. -1.5σ = '드물게 낮은 수준'.",
  },
  {
    term: "표준편차 (σ, Sigma)",
    definition: "데이터가 평균에서 평균적으로 얼마나 흩어져 있는지의 단위. 통계학 기본 척도.",
  },
  {
    term: "고점대비 하락률 (Drawdown)",
    definition: "최근 신고가에서 현재까지 얼마나 떨어졌는지. -20% 이상이면 일시적 우려로 빠진 구간.",
    example: "52주 신고가 100 → 현재 75 = 드로다운 -25%.",
  },
  {
    term: "5년 위치 (5y Percentile)",
    definition: "최근 5년 가격 범위 중 현재 가격이 차지하는 백분위. 0% = 5년 최저, 100% = 5년 최고.",
    example: "5년 위치 30% = 5년 동안 본 가격 중 하위 30% — 비교적 싼 구간.",
  },
  {
    term: "분할매수 트리거",
    definition: "분할매수에 들어가도 좋은 신호 3가지(예상 PER 개선 / 고점 -20% / 잉여현금수익률 5%+) 중 충족 개수.",
    example: "3개 모두 충족 = 강한 매수 / 2개 = 매수 검토 / 1개 = 관찰.",
  },
  {
    term: "버핏 후보",
    definition: "4단계 평가 점수(사업 실력+해자+자본+가격) 합산이 70점 이상인 우량 기업.",
  },
  {
    term: "종합 점수",
    definition: "종목 점수(0~100) + 환율 점수(-20~+20)로 환율까지 고려한 최종 매수 우선순위 점수.",
  },
];

export function GlossarySection() {
  const [open, setOpen] = useState(false);

  return (
    <section className="bg-surface-container-low rounded-xl ghost-border overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-6 hover:bg-surface-container/30 transition-colors text-left"
      >
        <span className="material-symbols-outlined text-primary text-xl">menu_book</span>
        <h3 className="text-xl font-serif text-on-surface tracking-tight flex-1">용어 해설집</h3>
        <span className="text-xs text-on-surface-variant/60">{ITEMS.length}개 용어</span>
        <span
          className="material-symbols-outlined text-primary-dim/60 text-base transition-transform duration-200"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          chevron_right
        </span>
      </button>
      {open && (
        <div className="px-6 pb-6 -mt-2">
          <p className="text-xs text-on-surface-variant/60 mb-4">
            이 페이지에서 쓰이는 용어를 가나다 순이 아닌 등장 빈도순으로 정리했습니다. 모르는 용어가 있으면 여기서 빠르게 찾아보세요.
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            {ITEMS.map((item, i) => (
              <div key={i} className="bg-surface-container/30 rounded-lg p-4 ghost-border">
                <div className="text-sm font-bold text-on-surface mb-1.5">{item.term}</div>
                <div className="text-xs text-on-surface-variant leading-relaxed mb-1.5">
                  {item.definition}
                </div>
                {item.example && (
                  <div className="text-[11px] text-on-surface-variant/70 leading-relaxed pt-1.5 border-t border-on-surface-variant/10">
                    <span className="text-primary-dim/80">▸ 예:</span> {item.example}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
