import { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "나의 투자 원칙 | My Stock",
  description: "잃지 않는 투자를 위한 개인 투자 헌법",
};

interface Principle {
  number: string;
  rule: string;
  why: string;
  how: string;
}

interface PrincipleSection {
  id: string;
  number: string;
  title: string;
  subtitle: string;
  icon: string;
  intro: string;
  principles: Principle[];
}

const sections: PrincipleSection[] = [
  {
    id: "allocation",
    number: "I",
    title: "자산 배분",
    subtitle: "Asset Allocation",
    icon: "donut_large",
    intro:
      "어떤 종목을 사느냐보다 자산을 어디에 얼마나 배분하느냐가 장기 수익률을 결정한다. 비중은 한 번 정하면 분기 단위로만 바꾼다.",
    principles: [
      {
        number: "1.1",
        rule: "배당주 80% · 성장주 20%",
        why: "잃지 않는 투자의 기반은 안정적인 현금 흐름. 배당이 매년 들어오면 시장이 빠져도 버틸 수 있고, 추가 매수 자금이 자동으로 생긴다.",
        how: "성장주는 비중이 20%를 넘으면 즉시 리밸런싱. 강세장에서 성장주가 빨리 오를수록 비중이 깨지므로, 분기마다 비중 점검 필수.",
      },
      {
        number: "1.2",
        rule: "한 종목 최대 비중은 자산의 10% 이하",
        why: "단일 종목 리스크. 기업은 망하지만 분산 포트폴리오는 망하지 않는다.",
        how: "비중이 10%에 근접하면 추가 매수 중단. 평가익으로 비중이 부풀면 일부 차익실현으로 비중 회복.",
      },
      {
        number: "1.3",
        rule: "단일 섹터 비중은 25% 이하",
        why: "섹터 사이클은 같이 움직인다. 반도체 한 섹터에 25%가 묶이면 사이클 전환기에 포트폴리오 전체가 흔들림.",
        how: "메가캡·성장주 스크리닝·바이오 워치리스트 점검 시 섹터 합산 비중 항상 확인.",
      },
      {
        number: "1.4",
        rule: "자산 규모에 맞는 종목 수 — 현재 단계는 8~15종목",
        why:
          "Markowitz 분산 효과는 15~20종목이면 비체계적 위험의 90% 이상이 제거된다. 그 이상 늘리면 모니터링은 어려워지고 결국 지수와 비슷해진다. 반대로 5종목 이하는 한 종목 충격이 포트폴리오 전체를 흔든다. 자산 규모가 커질수록 한 종목당 절대 금액이 커져서 분산이 강제된다.",
        how:
          "현재 자산(약 1.7억)에서는 8~15종목이 적정 범위. 한 종목 10% 상한을 지키면 자연스럽게 최소 10종목이 되고, 깊이 있게 분석·모니터링 가능한 한도가 15종목 정도. 자산이 3억 이상으로 늘어나면 12~20종목으로 확장, 10억 이상이면 ETF 활용도 검토.",
      },
    ],
  },
  {
    id: "selection",
    number: "II",
    title: "종목 선정",
    subtitle: "Stock Selection",
    icon: "checklist_rtl",
    intro:
      "지수 추종이 아니라 종목 선택으로 알파를 추구한다. 단, 선정 기준은 감이 아니라 명문화된 점수 체계로 한다.",
    principles: [
      {
        number: "2.1",
        rule: "잃지 않는 투자가 1번 규칙",
        why:
          '벤저민 그레이엄·워런 버핏의 1번 규칙: "돈을 잃지 마라." 2번 규칙: "1번 규칙을 잊지 마라." 못 잡은 종목보다 잃은 종목이 더 아프다.',
        how:
          "매수 결정의 첫 질문은 '얼마 벌 수 있나'가 아니라 '최악의 경우 얼마 잃나'. 안전마진이 없으면 진입 X.",
      },
      {
        number: "2.2",
        rule: "메가캡은 버핏 4단계 평가 70점 이상이 베이스라인",
        why:
          "사업 실력(40) + 경제적 해자(20) + 자본 운용력(20) + 가격 매력(20) = 100점. 70점은 4가지 기둥이 모두 합격선이라는 의미.",
        how: (
          "/stocks/megacap 페이지에서 점수 내림차순으로 확인. " +
          "70점 미달은 회사가 좋아도 가격이 비싸거나, 가격이 싸도 회사가 약하다는 뜻 — 둘 중 하나라도 부족하면 패스."
        ),
      },
      {
        number: "2.3",
        rule: "점수 계산은 반드시 DART 확정 공시 데이터 기반",
        why:
          "증권사 컨센서스·추정치는 지연되거나 편향될 수 있다. DART 확정 공시는 회사가 법적 책임을 지고 제출한 숫자.",
        how:
          "공시 전 컨센만 보고 매수 금지. 분기 실적은 잠정실적이라도 공시 발표 후 판단. 데이터 출처를 항상 명시.",
      },
      {
        number: "2.4",
        rule: "바이오주는 시동위키 7가지 기준 통과 종목만",
        why:
          "바이오는 일반 재무지표가 잘 통하지 않는다. 임상 단계·파이프라인·파트너십·현금 소진율 등 별도 기준이 필요.",
        how:
          "/bio/research 페이지의 7대 기준 체크. 임상 결과 분석 시 OS(전체 생존율) 우선, 美 파트너 주가 선확인, 회사 PR 비판 검증, 상업화 관점 필수.",
      },
      {
        number: "2.5",
        rule: "잠정실적 분석은 3가지 모두 확인 (YoY 단일 비교 금지)",
        why:
          "매출·이익이 YoY로 좋아 보여도 컨센 미스이거나, 일회성 이익이 끼었거나, 분기 추세가 꺾이는 중일 수 있다.",
        how:
          "① 컨센서스 비교 ② 분기 추세 ③ 일회성 영업외 분리 — 세 가지 모두 통과해야 '실적 호조'로 분류.",
      },
    ],
  },
  {
    id: "trading",
    number: "III",
    title: "매매 규율",
    subtitle: "Trading Discipline",
    icon: "rule",
    intro:
      "매수 버튼을 누르는 순간이 가장 위험하다. 사전에 만든 룰이 그 순간의 충동을 우회한다.",
    principles: [
      {
        number: "3.1",
        rule: "신고가 갱신 종목 추격 매수 금지",
        why:
          "버핏의 안전마진 원칙. 52주 신고가는 정의상 가격 매력이 0인 구간. 추격은 사이클 정점에서 물리는 가장 흔한 패턴.",
        how:
          "메가캡 점수에서 가격 매력 점수가 0점인 종목은 자동으로 매수 후보에서 제외. 강한 모멘텀에 끌리면 24~72시간 대기 룰.",
      },
      {
        number: "3.2",
        rule: "사이클 정점 진입 회피 (반도체·소재 등)",
        why:
          "사이클 종목은 호황 정점에서 forward PER이 5배까지 떨어지는 함정이 있다. 시장이 1년 후 EPS 폭증을 미리 반영했을 뿐, 사이클이 꺾이면 EPS도 반토막 → forward PER도 다시 15~20배로 회귀. 한국 반도체 2018년 -47%, 2022년 -56% 드로다운이 패턴.",
        how:
          "사이클 종목은 신고가 부근에서 안 산다. 만약 들어간다면 자산의 3% 이하 비중 + 분할매수 + 1년 단위 보유 각오.",
      },
      {
        number: "3.3",
        rule: "분할 매수 트리거 2/3 이상 충족 시에만 진입",
        why:
          "한 번에 몰빵은 타이밍 한 번에 모든 게 결정됨. 트리거 기반 분할은 가설이 검증되는 만큼만 자금이 들어감.",
        how:
          "트리거: ① 향후 12M 예상 PER < 현재 PER × 0.85 ② 52주 신고가 대비 -20% 이상 하락 ③ 잉여현금수익률 ≥ 5%. 2개 이상 충족 시 분할 매수 시작.",
      },
      {
        number: "3.4",
        rule: "호재 발표 당일 매수 금지",
        why:
          "이미 가격에 반영된 뉴스에 추격하면 차익실현 매물에 물린다. 호재가 진짜라면 다음 날에도 매수 가능.",
        how:
          "발표 다음 날 거래량·수급(외인·기관) 확인 후 판단. 호재 후 거래량 급증 + 수급 이탈 = 매수 금지 신호.",
      },
      {
        number: "3.5",
        rule: "Forward PER 매력만으로 매수 결정 X",
        why:
          "Forward PER은 시장 컨센서스의 미래 EPS 추정치 / 현재 가격. 사이클 정점에서는 추정치 자체가 비현실적으로 낙관적이다. Trailing PER도 함께 봐야 함정을 피한다.",
        how:
          "Forward PER ≤ 7배라도, Trailing PER이 30배 이상이면 사이클 정점 신호로 간주. 두 PER의 갭이 너무 크면 보수적으로 판단.",
      },
    ],
  },
  {
    id: "verification",
    number: "IV",
    title: "정보·검증",
    subtitle: "Information & Verification",
    icon: "verified_user",
    intro:
      "분석의 90%는 데이터의 신뢰성에서 결정된다. 출처가 모호한 숫자는 안 쓰는 것만 못하다.",
    principles: [
      {
        number: "4.1",
        rule: "모든 데이터는 실제 조회+검증 (추론·환각 금지)",
        why:
          "리포트에 검증되지 않은 숫자가 한 번 들어가면 그 위에 쌓이는 모든 판단이 흔들린다.",
        how:
          "리포트 작성 시 모든 지표는 실제 API/소스에서 조회한 값으로만 표기. 점수 변동 사유는 실제 변경한 필드를 grade_change_reason에 명시.",
      },
      {
        number: "4.2",
        rule: "경제 뉴스는 매일경제·한국경제 두 곳에서만",
        why:
          "출처를 좁혀야 노이즈를 줄일 수 있다. 두 곳은 한국 경제 보도의 표준이고, 같은 사실을 두 곳에서 교차 확인 가능.",
        how:
          "리포트·매크로 분석에서 인용 시 항상 출처 명시. 다른 매체 정보는 두 곳에서 확인된 후에만 보조 인용.",
      },
      {
        number: "4.3",
        rule: "확정 데이터 우선, 추정치는 보조 지표로만",
        why:
          "DART 확정 공시 > 잠정실적 > 증권사 컨센. 위 단계로 갈수록 신뢰도가 떨어진다.",
        how:
          "점수·등급 계산은 항상 가장 신뢰할 수 있는 단계의 데이터로. 컨센만 보고 매수 결정 X.",
      },
      {
        number: "4.4",
        rule: "단위는 사용자에게 친숙한 형태로 (채권 금리는 %p)",
        why:
          "bp(베이시스 포인트)는 글로벌 표준이지만 직관성이 떨어진다. %p가 즉시 이해된다.",
        how:
          "채권 금리·스프레드 변동은 항상 %p 단위. 0.25%p 인상 같은 식으로 표기.",
      },
    ],
  },
  {
    id: "psychology",
    number: "V",
    title: "심리 통제",
    subtitle: "Emotional Discipline",
    icon: "self_improvement",
    intro: (
      "감정에 휘둘려 내린 결정 한 번이 1년 분석을 무너뜨린다. " +
      "자세한 매뉴얼은 /discipline 페이지 참조."
    ),
    principles: [
      {
        number: "5.1",
        rule: "남과 비교해서 내린 결정은 모두 무효",
        why:
          "남이 번 돈은 표본 1개. 그 사람의 매수 시점·비중·진입 가격·매도 계획을 모르면 결과만 보고 따라 사는 건 도박.",
        how:
          "친구·커뮤니티 수익 자랑을 보면 매매일지를 펼쳐 본인 성과만 본다. 전략 변경은 분기 단위로만.",
      },
      {
        number: "5.2",
        rule: "FOMO 매수 금지 (24~72시간 대기 룰)",
        why:
          "이미 200% 오른 종목을 '나만 못 탔다'며 추격 매수하는 건 가장 흔한 손실 패턴. 강세장 후반에 가장 강함.",
        how:
          "신규 진입 종목은 무조건 24~72시간 대기. 그 사이에 펀더멘털 점검 + 밸류에이션 확인. 결심이 흔들리면 진입 X.",
      },
      {
        number: "5.3",
        rule: "못 잡은 종목 후회 금지",
        why:
          "원칙을 지킨 결과 못 잡은 것은 실패가 아니라 성공이다. 그 종목을 잡았다면 다음 사이클 정점에서 비슷한 종목을 또 추격했을 것.",
        how:
          "급등 종목을 보고 배가 아플 때 이 페이지를 다시 펼친다. 본인이 못 잡은 게 아니라 안 잡은 것임을 확인.",
      },
      {
        number: "5.4",
        rule: "충동이 강할 때 거래 금지",
        why:
          "공포·흥분·복수심 — 강한 감정은 모두 동일하게 판단을 망친다. 강도가 높을수록 결정의 질은 낮아진다.",
        how:
          "감정 강도 7/10 이상이면 그날은 거래 X. 매매일지에 감정 상태 기록 후 다음 날 재검토.",
      },
    ],
  },
  {
    id: "operations",
    number: "VI",
    title: "운영 규율",
    subtitle: "Operations",
    icon: "settings",
    intro:
      "원칙은 매일의 작은 운영 규율로 실현된다. 자잘해 보이지만 누적되면 큰 차이를 만든다.",
    principles: [
      {
        number: "6.1",
        rule: "매매일지 반영 시 모든 보유 종목 현재가도 당일 시세로 갱신",
        why:
          "한 종목만 갱신하면 포트폴리오 평가액이 부정확해지고, 비중·수익률 통계도 왜곡된다.",
        how:
          "매수·매도 기록할 때 보유 종목 전체를 같은 날짜 시세로 일괄 갱신. /journal 페이지 사용.",
      },
      {
        number: "6.2",
        rule: "응답·UI 모두 한국어 우선",
        why:
          "트리밍, 워치리스트 같은 영어 표현이 익숙하지 않으면 직관적 의사결정에 방해가 된다.",
        how:
          "비중 축소, 관심 종목, 매수 검토 등 한국어 표현으로 통일. 영어 약어는 PER·ROE처럼 보편화된 것만 허용.",
      },
      {
        number: "6.3",
        rule: "리포트에 지표 간 상관관계 흐름도 항상 포함",
        why:
          "지표를 따로 보면 노이즈, 묶어서 보면 패턴. 학습 효과를 위해 흐름도가 필수.",
        how:
          "거시 리포트·종목 분석 모두 핵심 지표 간 인과관계를 ASCII 흐름도로 표현.",
      },
    ],
  },
];

const reminders = [
  {
    text: "잃지 않는 투자가 1번. 못 잡은 종목보다 잃은 종목이 더 아프다.",
    context: "이 페이지의 모든 원칙이 결국 이 한 줄로 수렴한다.",
  },
  {
    text: "원칙을 지킨 결과 못 잡은 것은 실패가 아니라 성공이다.",
    context: "급등 종목을 못 잡았다고 배가 아플 때.",
  },
  {
    text: "10번 잘 산 결과보다 1번 큰 손실을 피한 결과가 더 크다.",
    context: "복리의 비대칭성 — 50% 손실은 100% 수익으로만 회복된다.",
  },
  {
    text: "사이클 정점에서 forward PER 5배는 시장 컨센서스의 함정이다.",
    context: "한국 반도체 2018·2022 패턴. 슈퍼사이클 모멘텀에 흔들릴 때.",
  },
];

export default function PrinciplesPage() {
  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Investing Constitution
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          나의 투자 원칙
        </h2>
        <p className="text-base text-on-surface-variant mt-2 leading-relaxed">
          흔들릴 때 다시 펼쳐 보는 한 페이지. 시장이 격렬할수록 원칙이 답이다.
        </p>
      </section>

      {/* Core One-Liner */}
      <section className="bg-gradient-to-br from-primary/10 via-surface-container-low to-surface-container rounded-xl p-8 sm:p-10 ghost-border text-center">
        <span className="material-symbols-outlined text-primary/60 text-3xl mb-3 block">
          balance
        </span>
        <p className="text-xl sm:text-2xl font-serif text-on-surface tracking-tight leading-relaxed">
          잃지 않는 투자가 1번.
          <br className="hidden sm:block" />
          <span className="text-primary/90"> 못 잡은 종목보다 잃은 종목이 더 아프다.</span>
        </p>
        <p className="text-xs text-primary-dim/70 mt-4 tracking-wider">
          THE FIRST PRINCIPLE
        </p>
      </section>

      {/* "잃지 않는 투자"의 정의 명확화 */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <div className="flex items-baseline gap-2 mb-3">
          <span className="material-symbols-outlined text-primary/70 text-xl">priority_high</span>
          <h3 className="text-lg font-serif text-primary tracking-tight">
            "잃지 않는 투자"의 정의 — 헷갈리지 말 것
          </h3>
        </div>
        <p className="text-sm text-on-surface-variant mb-5 leading-relaxed">
          버핏·멍거가 말하는 "잃지 않는 투자"는 <span className="text-primary/90">영구적 자본 손실(permanent loss of capital)</span>을 피한다는 뜻이지,
          <span className="text-error/80"> 일시적 변동성</span>을 피한다는 뜻이 아니다. 두 사람 모두 초기엔 매우 공격적이었다 —
          버핏은 1964년 American Express에 파트너십 자산의 약 40%를 투입했고, 멍거는 1973~74년 -53% 드로다운을 견뎠다.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-error/5 border border-error/20 rounded-lg p-4">
            <p className="text-[10px] uppercase tracking-[0.15em] text-error/80 mb-2 font-medium">
              피해야 할 것 · Permanent Loss
            </p>
            <h4 className="text-base font-serif text-on-surface mb-2">영구적 자본 손실</h4>
            <ul className="text-xs text-on-surface-variant/85 space-y-1.5 leading-relaxed">
              <li>· 회사 펀더멘털이 무너져 본질가치 자체가 사라짐 (엔론·리먼)</li>
              <li>· 사이클 정점에서 추격 매수 후 사이클 꺾임</li>
              <li>· 안전마진 없는 비싼 가격에 매수</li>
              <li>· 빚으로 한 종목에 몰빵 → 마진콜로 강제 청산</li>
            </ul>
          </div>
          <div className="bg-tertiary/5 border border-tertiary/20 rounded-lg p-4">
            <p className="text-[10px] uppercase tracking-[0.15em] text-tertiary/90 mb-2 font-medium">
              감수해야 할 것 · Temporary Volatility
            </p>
            <h4 className="text-base font-serif text-on-surface mb-2">일시적 변동성</h4>
            <ul className="text-xs text-on-surface-variant/85 space-y-1.5 leading-relaxed">
              <li>· 본질가치는 멀쩡한데 시장이 패닉 (2020년 3월 코로나)</li>
              <li>· 안전마진 있는 종목의 -30% 드로다운</li>
              <li>· 매크로 충격으로 인한 포트폴리오 일시 평가손</li>
              <li>· 가설이 검증되는 동안의 횡보</li>
            </ul>
          </div>
        </div>
        <p className="text-xs text-on-surface-variant/70 mt-5 leading-relaxed">
          → 변동성이 두려워 안전마진 있는 종목조차 못 사면 그건 <span className="text-primary/90">투자가 아니라 회피</span>다.
          반대로, 본질가치 무너진 종목을 "조정이겠지" 하며 들고 있으면 그건 변동성이 아니라 영구 손실의 시작이다.
          두 가지를 항상 분리해서 판단한다.
        </p>
      </section>

      {/* Why */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <h3 className="text-lg font-serif text-primary mb-4 tracking-tight">
          왜 원칙인가
        </h3>
        <div className="space-y-3 text-sm text-on-surface-variant leading-relaxed">
          <p>
            시장은 매일 새로운 이야기를 들고 온다. 슈퍼사이클·AI 혁명·금리 인하 — 어떤 이야기든
            "이번엔 다르다"는 메시지를 담고 있다. 그 이야기에 매번 휘둘리면 일관된 성과는 불가능하다.
          </p>
          <p>
            원칙은 시장의 이야기보다 느리게 바뀐다. 그래서 단기적으로는 답답해 보이지만,
            장기적으로는 <span className="text-primary/90">감정에 휘둘리지 않는 유일한 방법</span>이다.
          </p>
          <p>
            이 페이지는 그동안 누적된 자기 자신과의 약속이다. 새로운 원칙이 추가될 수는 있지만,
            기존 원칙을 즉흥적으로 깨는 일은 없어야 한다. 만약 깬다면 분기 단위 회고에서 명문화하고 깬다.
          </p>
        </div>
      </section>

      {/* Sections */}
      {sections.map((section) => (
        <section key={section.id} id={section.id}>
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-[11px] font-mono text-primary-dim/60 tracking-wider">
              {section.number}.
            </span>
            <h3 className="text-2xl font-serif text-on-surface tracking-tight">
              {section.title}
            </h3>
            <span className="material-symbols-outlined text-primary/60 text-xl">
              {section.icon}
            </span>
          </div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/50 mb-3">
            {section.subtitle}
          </p>
          <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
            {section.intro}
          </p>
          <div className="space-y-4">
            {section.principles.map((p) => (
              <article
                key={p.number}
                className="bg-surface-container-low rounded-xl p-6 ghost-border"
              >
                <div className="flex items-start gap-4">
                  <span className="text-xs font-mono text-primary-dim/70 tracking-wider shrink-0 mt-0.5">
                    {p.number}
                  </span>
                  <div className="flex-1 space-y-3">
                    <h4 className="text-base font-serif text-on-surface tracking-tight leading-snug">
                      {p.rule}
                    </h4>
                    <div className="space-y-2 text-xs text-on-surface-variant/85 leading-relaxed">
                      <p>
                        <span className="text-primary-dim/80 font-medium">왜 · </span>
                        {p.why}
                      </p>
                      <p>
                        <span className="text-tertiary/90 font-medium">실행 · </span>
                        {p.how}
                      </p>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>

          {/* 자산 배분 섹션 끝에 자산 규모별 분산 가이드 표 추가 */}
          {section.id === "allocation" && (
            <div className="mt-6 bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
              <div className="flex items-baseline gap-2 mb-4">
                <span className="material-symbols-outlined text-primary/70 text-lg">table_rows</span>
                <h4 className="text-base font-serif text-primary tracking-tight">
                  자산 규모별 분산 가이드
                </h4>
              </div>
              <p className="text-xs text-on-surface-variant/80 mb-5 leading-relaxed">
                Markowitz 분산 효과 + 모니터링 한계 + 한 종목 10% 상한을 종합한 일반론. 절대값이 아니라 참고선.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[11px] uppercase tracking-wider text-on-surface-variant/60 border-b border-outline-variant/15">
                      <th className="text-left py-2.5 pr-4 font-normal">자산 규모</th>
                      <th className="text-center py-2.5 px-3 font-normal">권장 종목 수</th>
                      <th className="text-left py-2.5 pl-4 font-normal">특성</th>
                    </tr>
                  </thead>
                  <tbody className="text-on-surface-variant">
                    <tr className="border-b border-outline-variant/10">
                      <td className="py-3 pr-4 font-mono text-xs">~1억원</td>
                      <td className="text-center py-3 px-3 font-mono">5~10</td>
                      <td className="py-3 pl-4 text-xs leading-relaxed">집중 가능. 깊이 있는 종목 선택이 분산보다 중요. 버핏·멍거 초기 단계.</td>
                    </tr>
                    <tr className="border-b border-outline-variant/10 bg-primary/5">
                      <td className="py-3 pr-4 font-mono text-xs">
                        1~3억원
                        <span className="ml-2 inline-block px-1.5 py-0.5 rounded bg-primary/20 text-primary text-[9px] uppercase tracking-wider">현재</span>
                      </td>
                      <td className="text-center py-3 px-3 font-mono font-bold text-primary">8~15</td>
                      <td className="py-3 pl-4 text-xs leading-relaxed">한 종목 10% 상한 적용 시 최소 10종목. 모니터링 가능 상한이 15. 본인은 11종목.</td>
                    </tr>
                    <tr className="border-b border-outline-variant/10">
                      <td className="py-3 pr-4 font-mono text-xs">3~10억원</td>
                      <td className="text-center py-3 px-3 font-mono">12~20</td>
                      <td className="py-3 pl-4 text-xs leading-relaxed">섹터 분산 강화 단계. 코어 8~10 + 위성 5~10 구조 검토.</td>
                    </tr>
                    <tr className="border-b border-outline-variant/10">
                      <td className="py-3 pr-4 font-mono text-xs">10~50억원</td>
                      <td className="text-center py-3 px-3 font-mono">15~25</td>
                      <td className="py-3 pl-4 text-xs leading-relaxed">한 종목 절대 금액이 커져 분산이 강제됨. ETF 일부 활용 검토.</td>
                    </tr>
                    <tr>
                      <td className="py-3 pr-4 font-mono text-xs">50억원+</td>
                      <td className="text-center py-3 px-3 font-mono">20+ 또는 ETF</td>
                      <td className="py-3 pl-4 text-xs leading-relaxed">유동성·세금·시장 영향까지 고려. 일부 ETF 편입이 합리적.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-[11px] text-on-surface-variant/60 mt-4 leading-relaxed">
                ※ 종목 수보다 더 중요한 건 <span className="text-primary/80">한 종목 10% / 한 섹터 25%</span> 상한 준수.
                10종목이라도 한 종목이 30%면 사실상 1종목 포트폴리오와 같은 위험.
              </p>
            </div>
          )}
        </section>
      ))}

      {/* Reminders */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface tracking-tight mb-2">
          흔들릴 때 다시 떠올리기
        </h3>
        <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
          시장이 격렬한 순간에 본인이 가장 자주 잊는 문장들.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reminders.map((r, i) => (
            <article
              key={i}
              className="bg-surface-container-low rounded-xl p-6 ghost-border"
            >
              <span className="material-symbols-outlined text-primary/30 text-2xl mb-2 block">
                format_quote
              </span>
              <p className="text-sm text-on-surface leading-relaxed font-serif italic mb-3">
                {r.text}
              </p>
              <p className="text-[11px] text-on-surface-variant/70 leading-relaxed">
                {r.context}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Cross-links */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <h3 className="text-lg font-serif text-primary mb-4 tracking-tight">
          함께 보는 페이지
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <Link
            href="/discipline"
            className="bg-surface-container/50 hover:bg-surface-container rounded-lg p-4 transition-colors block"
          >
            <span className="material-symbols-outlined text-primary/70 text-xl mb-1 block">
              self_improvement
            </span>
            <p className="text-on-surface font-medium mb-1">감정 다스리기</p>
            <p className="text-xs text-on-surface-variant/70 leading-relaxed">
              인지 편향·충동 통제 매뉴얼
            </p>
          </Link>
          <Link
            href="/journal"
            className="bg-surface-container/50 hover:bg-surface-container rounded-lg p-4 transition-colors block"
          >
            <span className="material-symbols-outlined text-primary/70 text-xl mb-1 block">
              history_edu
            </span>
            <p className="text-on-surface font-medium mb-1">매매일지</p>
            <p className="text-xs text-on-surface-variant/70 leading-relaxed">
              원칙 위반·복기 기록
            </p>
          </Link>
          <Link
            href="/musings"
            className="bg-surface-container/50 hover:bg-surface-container rounded-lg p-4 transition-colors block"
          >
            <span className="material-symbols-outlined text-primary/70 text-xl mb-1 block">
              psychology
            </span>
            <p className="text-on-surface font-medium mb-1">고민 한 스푼</p>
            <p className="text-xs text-on-surface-variant/70 leading-relaxed">
              매크로·전략 대화 누적
            </p>
          </Link>
        </div>
      </section>

      {/* Footer note */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-primary/70 text-2xl shrink-0">
            edit_note
          </span>
          <div className="space-y-2 text-sm text-on-surface-variant leading-relaxed">
            <p>
              이 원칙들은 한 번에 만들어진 게 아니라 매매·실수·복기 과정에서 누적된 것이다.
              새로운 원칙이 필요하면 매매일지에 먼저 기록하고, 분기 회고에서 정식 원칙으로 승격한다.
            </p>
            <p>
              원칙을 깨야 할 상황이 생기면 그 자리에서 즉흥적으로 깨지 말고,
              <span className="text-primary/90"> 24시간 대기 + 매매일지에 사유 기록 + 분기 회고에서 명문화</span> 절차를 거친다.
            </p>
            <p className="text-xs text-on-surface-variant/60">
              잃지 않는 투자의 본질은 결국 <span className="text-primary/80">잃게 만드는 행동을 줄이는 것</span>이다.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
