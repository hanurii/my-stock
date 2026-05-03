import { Metadata } from "next";

export const metadata: Metadata = {
  title: "감정 다스리기 | My Stock",
  description: "투자 심리와 행동 편향을 통제하는 방법",
};

interface Bias {
  icon: string;
  name: string;
  english: string;
  description: string;
  example: string;
  countermeasure: string;
}

interface Trigger {
  scenario: string;
  emotion: string;
  trap: string;
  rule: string;
}

interface Checklist {
  title: string;
  items: string[];
}

interface Quote {
  text: string;
  author: string;
  context: string;
}

const biases: Bias[] = [
  {
    icon: "trending_down",
    name: "손실 회피",
    english: "Loss Aversion",
    description:
      "같은 크기의 이익보다 손실의 고통을 약 2배 강하게 느낌. 카너먼·트버스키 전망이론의 핵심.",
    example:
      "10% 수익 종목은 빨리 팔아 차익을 확정하고, 20% 손실 종목은 '본전만 오면 팔겠다'며 끝까지 들고 감.",
    countermeasure:
      "매수 시점에 손절선과 익절선을 동시에 명문화. 가격이 아닌 '가설 깨짐' 기준으로 매도 판단.",
  },
  {
    icon: "swap_vert",
    name: "처분 효과",
    english: "Disposition Effect",
    description:
      "이익 종목은 너무 일찍 팔고, 손실 종목은 너무 오래 보유하는 경향. 손실 회피의 매매적 발현.",
    example:
      "수익 5%에서 익절하고, -30% 종목은 '언젠간 오르겠지' 하며 5년째 보유.",
    countermeasure:
      "포지션마다 투자 가설을 기록하고, 매도는 가설 검증 결과로 결정. 이익/손실 절대값은 무시.",
  },
  {
    icon: "fact_check",
    name: "확증 편향",
    english: "Confirmation Bias",
    description:
      "내 판단을 뒷받침하는 정보만 수집하고, 반대 정보는 무시·왜곡함.",
    example:
      "매수한 종목의 호재 뉴스만 검색하고, 부정적 리포트는 '편향된 분석'이라며 무시.",
    countermeasure:
      "매수 전 일부러 그 종목의 비판적 리포트·공매도 보고서를 1개 이상 찾아 읽기. 반대 의견 노트 작성.",
  },
  {
    icon: "groups",
    name: "군중 심리",
    english: "Herd Behavior",
    description:
      "다수가 사면 안전하다고 느끼고, 다수가 팔면 위험하다고 느끼는 본능적 동조.",
    example:
      "유튜브·커뮤니티에서 추천 폭증한 테마주에 추격 매수 → 곧 고점에서 물림.",
    countermeasure:
      "공포·탐욕 지수와 반대로 행동. 군중이 환호할 때 비중 축소, 패닉할 때 분할 매수.",
  },
  {
    icon: "anchor",
    name: "닻 내림 효과",
    english: "Anchoring",
    description:
      "처음 본 숫자(매수가, 52주 고점 등)에 비합리적으로 집착함.",
    example:
      "10만원에 산 주식이 7만원으로 하락. 펀더멘털이 무너졌는데도 '10만원만 회복하면 팔겠다'.",
    countermeasure:
      "매수가는 의사결정에 무관함을 인식. '지금 이 가격에 새로 산다면 살 것인가?'로 재평가.",
  },
  {
    icon: "bolt",
    name: "FOMO",
    english: "Fear of Missing Out",
    description:
      "남들이 돈 버는 걸 못 견뎌 충동 매수하는 심리. 강세장 후반에 가장 강함.",
    example:
      "이미 200% 오른 종목을 '나만 못 탔다'며 고점에 추격 매수.",
    countermeasure:
      "신규 진입 종목은 24~72시간 대기 룰. 그 사이에 펀더멘털 점검 + 밸류에이션 확인. 결심이 흔들리면 진입 X.",
  },
  {
    icon: "verified",
    name: "자기 과신",
    english: "Overconfidence",
    description:
      "최근 몇 번의 성공이 본인 실력 때문이라 착각하고, 운의 비중을 과소평가함.",
    example:
      "강세장에서 5연승 → 본인이 시장을 읽었다고 믿고 비중·레버리지 확대 → 한 번에 다 잃음.",
    countermeasure:
      "매매일지에 매수 사유와 결과를 기록하고, 분기별로 적중률 점검. 운과 실력을 분리해서 평가.",
  },
  {
    icon: "history_toggle_off",
    name: "매몰비용 오류",
    english: "Sunk Cost Fallacy",
    description:
      "이미 투입한 시간·돈·연구가 아까워 손절 못 하는 심리.",
    example:
      "1년간 분석한 종목인데 펀더멘털이 무너졌어도 '여기서 팔면 그동안 노력이 헛수고'라며 보유.",
    countermeasure:
      "과거 비용은 의사결정에 무관함을 인식. '오늘 신규 자금이 있다면 이 종목을 살 것인가?'로 재평가.",
  },
  {
    icon: "psychology_alt",
    name: "통제 환상",
    english: "Illusion of Control",
    description:
      "시장의 무작위성을 본인이 통제할 수 있다고 착각함. 잦은 매매의 원인.",
    example:
      "차트를 한 시간씩 들여다보면 다음 움직임을 예측할 수 있다고 믿음 → 단타 남발 → 거래비용·세금만 누적.",
    countermeasure:
      "예측 불가능을 인정. 통제 가능한 것(분산, 비중, 매매 규율)에만 집중. 시장 타이밍 시도 금지.",
  },
  {
    icon: "newspaper",
    name: "최신성 편향",
    english: "Recency Bias",
    description:
      "최근 일어난 사건이 미래에도 계속될 거라고 과대평가하는 경향.",
    example:
      "지난 3개월 강세장이 영원할 것 같아 현금 비중 0%로 운용 → 폭락기 대응 불가.",
    countermeasure:
      "10년 이상의 장기 데이터·사이클로 사고. 시장은 평균 회귀한다는 사실 기억.",
  },
];

const triggers: Trigger[] = [
  {
    scenario: "보유 종목이 하루에 -10% 폭락",
    emotion: "공포 · 패닉 · 즉시 매도 충동",
    trap: "최저가에 던지고 다음 날 반등하는 패턴.",
    rule: "당일 매도 금지 룰. 24시간 후 재평가. 펀더멘털이 깨졌는지(가설 검증), 단순 시장 조정인지 분리.",
  },
  {
    scenario: "관심 종목이 단숨에 +30% 급등",
    emotion: "FOMO · 추격 매수 충동",
    trap: "고점에 진입해 곧바로 조정 받음.",
    rule: "급등 직후 신규 진입 금지. 최소 1주일 관망 후 조정 시 분할 진입.",
  },
  {
    scenario: "친구·커뮤니티가 큰 수익 자랑",
    emotion: "조급함 · 비교 · 본인 전략 의심",
    trap: "검증 없이 따라 사거나, 본인의 안정형 포트폴리오를 갑자기 공격적으로 변경.",
    rule: "타인 수익은 표본 1개일 뿐. 본인 매매일지로만 성과 평가. 전략 변경은 분기 단위로만.",
  },
  {
    scenario: "큰 호재 뉴스 발표 (실적·계약·승인)",
    emotion: "흥분 · 추가 매수 충동",
    trap: "이미 가격에 반영된 뉴스에 추격 매수 → 차익실현 매물에 물림.",
    rule: "호재 발표 당일 매수 금지. 다음 날 거래량·수급 확인 후 판단.",
  },
  {
    scenario: "장기 보유 종목이 횡보만 1년째",
    emotion: "지루함 · 갈아타고 싶은 충동",
    trap: "지루함을 이유로 매도 → 매도 직후 급등.",
    rule: "지루함은 매도 사유가 아님. 가설이 유지되면 보유. 따분함을 못 견디면 그건 종목 문제가 아니라 비중 문제.",
  },
  {
    scenario: "전체 시장이 폭락 (코스피 -5%)",
    emotion: "공황 · 전량 청산 충동",
    trap: "바닥에서 던지고 회복기를 놓침. 통계상 최악의 5일을 놓치면 장기 수익률 절반 이상 사라짐.",
    rule: "지수 폭락은 매수 기회 점검 신호. 사전 작성한 '폭락 시 매수 종목 리스트'를 꺼내 검토.",
  },
];

const buyChecklist: Checklist = {
  title: "매수 전 체크리스트",
  items: [
    "이 종목이 왜 좋은지 3줄로 설명할 수 있는가? (투자 가설)",
    "지난 5년·10년 ROE·영업이익률 추이를 확인했는가?",
    "현재 PER·PBR이 동종업계·과거 평균 대비 합리적인가?",
    "부채비율·이자보상배율은 안전한가?",
    "이 종목의 비판적 리포트·리스크 요인 1개 이상 읽었는가?",
    "포트폴리오 내 비중이 상한선(예: 10%)을 넘지 않는가?",
    "같은 섹터 비중이 25%를 넘지 않는가?",
    "분할 매수 계획(횟수·간격·금액)을 정했는가?",
    "손절·익절 트리거를 명문화했는가?",
    "주변 추천이 아니라 본인 분석 기반인가?",
    "최근 3일 내 급등 직후 추격 매수가 아닌가?",
    "매수 후 1년간 못 팔아도 괜찮은 종목인가?",
  ],
};

const sellChecklist: Checklist = {
  title: "매도 전 체크리스트",
  items: [
    "매수 시점의 가설이 깨졌는가? (펀더멘털 훼손)",
    "단순히 가격이 빠져서 매도하려는 건 아닌가?",
    "지금 신규 자금이 있다면 이 종목을 살 것인가? (NO면 매도, YES면 보유)",
    "더 매력적인 대체 종목이 있는가? (기회비용)",
    "비중이 과도해져 리밸런싱이 필요한가?",
    "밸류에이션이 본인 기준 과열 구간에 도달했는가?",
    "감정(공포·지루함·복수심)이 매도 동기인가?",
    "매도 결정을 24시간 후에도 동일하게 내릴 수 있는가?",
  ],
};

const dailyRoutine = [
  {
    when: "장 시작 전",
    actions: [
      "매크로 지표 확인 (환율·금리·유가, 미국 시장 마감)",
      "보유 종목 공시·뉴스 점검 (가설 영향 여부)",
      "오늘 매매 계획 확인 (분할 진행도, 트리거 가격)",
    ],
  },
  {
    when: "장중",
    actions: [
      "시세창 1시간에 1회만 확인",
      "충동 매매 신호 감지 시 24시간 대기 룰 적용",
      "뉴스 헤드라인은 보되, 커뮤니티·종목토론방은 차단",
    ],
  },
  {
    when: "장 마감 후",
    actions: [
      "매매일지 기록: 오늘 매매 사유, 당시 감정, 결과 가설",
      "관심 종목 종가·거래량 점검",
      "내일의 트리거·계획 미리 작성",
    ],
  },
  {
    when: "주간 (일요일)",
    actions: [
      "포트폴리오 비중·섹터 분산 점검",
      "보유 종목별 가설 유효성 재확인",
      "이번 주 충동 매매 / 룰 위반 사례 복기",
    ],
  },
  {
    when: "월간",
    actions: [
      "수익률을 코스피·벤치마크와 비교 (절대값 아닌 상대값)",
      "매매일지 기반으로 본인 행동 패턴 분석",
      "다음 달 매크로 이벤트 캘린더 작성 (FOMC, 실적시즌 등)",
    ],
  },
  {
    when: "분기",
    actions: [
      "전체 종목 가설 전면 재검토",
      "실적 시즌 결과로 가설 검증/수정",
      "전략 변경(섹터 비중·신규 진입 룰) 검토",
    ],
  },
];

const quotes: Quote[] = [
  {
    text: "투자는 90%가 심리, 10%가 분석이다.",
    author: "앙드레 코스톨라니",
    context: "유럽 전설적 투기자. 시장의 본질이 인간 군중 심리임을 강조.",
  },
  {
    text: "남들이 욕심낼 때 두려워하고, 남들이 두려워할 때 욕심내라.",
    author: "워런 버핏",
    context: "역발상 투자의 정수. 군중 심리의 반대편에 서는 것이 알파의 원천.",
  },
  {
    text: "주식 시장은 인내심 없는 자에게서 인내심 있는 자에게로 부를 옮기는 도구다.",
    author: "워런 버핏",
    context: "장기 투자의 본질. 단타·잦은 매매가 결국 패배 게임인 이유.",
  },
  {
    text: "시장은 단기적으로는 투표 기계, 장기적으로는 저울이다.",
    author: "벤저민 그레이엄",
    context: "단기 가격은 군중의 인기 투표지만, 장기 가격은 가치를 따라간다는 의미.",
  },
  {
    text: "Mr. Market은 매일 당신에게 가격을 제시한다. 그가 우울할 땐 헐값에 사주고, 흥분할 땐 비싸게 팔아주면 된다.",
    author: "벤저민 그레이엄",
    context: "시장을 변덕스러운 동업자에 비유. 시장 가격에 끌려다니지 않는 마음가짐.",
  },
  {
    text: "투자자의 가장 큰 적은 자기 자신이다.",
    author: "벤저민 그레이엄",
    context: "외부 시장보다 내부 감정과 편향이 더 큰 위험 요인이라는 통찰.",
  },
  {
    text: "주식이 빠지는 게 두려우면 시장에 들어오지 마라. 변동성은 가격의 본질이다.",
    author: "피터 린치",
    context: "변동성을 위험이 아닌 자연 현상으로 받아들여야 한다는 조언.",
  },
  {
    text: "기다리는 자에게 모든 것이 온다. 다만 인내심을 가지고 노력하는 자에게만.",
    author: "찰리 멍거",
    context: "좋은 기회는 자주 오지 않으며, 그것을 알아보고 행동할 준비된 자만 잡을 수 있다.",
  },
  {
    text: "투자에서 가장 위험한 네 단어는 '이번엔 다르다'이다.",
    author: "존 템플턴",
    context: "버블 후반에 항상 등장하는 합리화. 시장은 늘 비슷한 패턴으로 회귀.",
  },
  {
    text: "투자의 비밀은 행동하지 않는 것이다.",
    author: "찰리 멍거",
    context: "잦은 매매가 가장 큰 적. 좋은 기업을 사서 가만히 두는 것이 최고의 전략.",
  },
];

export default function DisciplinePage() {
  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Emotional Discipline
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          감정 다스리기
        </h2>
        <p className="text-base text-on-surface-variant mt-2 leading-relaxed">
          투자의 90%는 심리다. 좋은 분석을 무력화시키는 건 시장이 아니라 본인의 감정과 편향이다.
        </p>
      </section>

      {/* Why */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <h3 className="text-lg font-serif text-primary mb-4 tracking-tight">
          왜 감정 통제인가
        </h3>
        <div className="space-y-3 text-sm text-on-surface-variant leading-relaxed">
          <p>
            아무리 좋은 매수 기준과 스코어링 체계를 갖춰도, 매매 순간의 감정 한 번이 1년 분석을 무너뜨린다.
            폭락장에 패닉셀하고, 급등주에 FOMO로 추격 매수하고, 손실 종목을 매몰비용 때문에 못 던지는 것 — 모두 감정 통제 실패다.
          </p>
          <p>
            기관·외인이 룰 기반 시스템 매매를 하는 진짜 이유는 정보 우위가 아니라 <span className="text-primary/90">감정을 시스템으로 차단</span>하기 때문이다.
            개인 투자자는 그 시스템을 본인이 만들어 본인에게 강제해야 한다.
          </p>
          <p>
            이 페이지는 그 시스템의 <span className="text-primary/90">참고 매뉴얼</span>이다. 충동이 올 때마다 다시 펼쳐 본다.
          </p>
        </div>
      </section>

      {/* Cognitive Biases */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface tracking-tight mb-2">
          1. 인지 편향 10선
        </h3>
        <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
          인간 뇌는 진화적으로 시장에 부적합하게 설계되어 있다. 편향의 이름을 알아야 자기 행동을 메타 인지할 수 있다.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {biases.map((b) => (
            <article
              key={b.name}
              className="bg-surface-container-low rounded-xl p-6 ghost-border"
            >
              <div className="flex items-start gap-3 mb-3">
                <span className="material-symbols-outlined text-primary/80 text-2xl shrink-0 mt-0.5">
                  {b.icon}
                </span>
                <div>
                  <h4 className="text-base font-serif text-on-surface tracking-tight">
                    {b.name}
                  </h4>
                  <p className="text-[11px] uppercase tracking-[0.15em] text-primary-dim/60">
                    {b.english}
                  </p>
                </div>
              </div>
              <p className="text-sm text-on-surface-variant leading-relaxed mb-3">
                {b.description}
              </p>
              <div className="space-y-2 text-xs text-on-surface-variant/80 leading-relaxed">
                <p>
                  <span className="text-primary-dim/80 font-medium">예 · </span>
                  {b.example}
                </p>
                <p>
                  <span className="text-tertiary/90 font-medium">대응 · </span>
                  {b.countermeasure}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Emotional Triggers */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface tracking-tight mb-2">
          2. 감정 유발 상황과 대응 룰
        </h3>
        <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
          감정을 통제하는 가장 효과적인 방법은 <span className="text-primary/90">사전에 만든 규칙</span>으로 그 순간을 우회하는 것이다.
        </p>
        <div className="space-y-4">
          {triggers.map((t) => (
            <article
              key={t.scenario}
              className="bg-surface-container-low rounded-xl p-6 ghost-border"
            >
              <div className="flex flex-col md:flex-row md:items-start md:gap-6">
                <div className="md:w-1/3 mb-3 md:mb-0">
                  <p className="text-[10px] uppercase tracking-[0.15em] text-primary-dim/60 mb-1">
                    상황
                  </p>
                  <h4 className="text-base font-serif text-on-surface tracking-tight leading-snug">
                    {t.scenario}
                  </h4>
                </div>
                <div className="md:flex-1 space-y-3 text-sm leading-relaxed">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.15em] text-error/70 mb-0.5">
                      감정
                    </p>
                    <p className="text-on-surface-variant">{t.emotion}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.15em] text-error/70 mb-0.5">
                      함정
                    </p>
                    <p className="text-on-surface-variant">{t.trap}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.15em] text-tertiary/80 mb-0.5">
                      사전 룰
                    </p>
                    <p className="text-on-surface">{t.rule}</p>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Mr. Market */}
      <section className="bg-gradient-to-br from-surface-container-low to-surface-container rounded-xl p-6 sm:p-8 ghost-border">
        <div className="flex items-start gap-3 mb-4">
          <span className="material-symbols-outlined text-primary text-3xl">
            theater_comedy
          </span>
          <div>
            <h3 className="text-xl font-serif text-on-surface tracking-tight">
              3. Mr. Market 마음가짐
            </h3>
            <p className="text-[11px] uppercase tracking-[0.15em] text-primary-dim/60 mt-1">
              Benjamin Graham&apos;s Allegory
            </p>
          </div>
        </div>
        <div className="space-y-3 text-sm text-on-surface-variant leading-relaxed">
          <p>
            벤저민 그레이엄은 시장을 <span className="text-primary/90">조울증을 앓는 동업자 &apos;Mr. Market&apos;</span>에 비유했다.
            그는 매일 당신에게 와서 자기 지분을 사거나 팔겠다며 가격을 제시한다.
          </p>
          <p>
            기분이 좋은 날엔 터무니없이 <span className="text-tertiary/90">비싼 값</span>을 부르고, 우울한 날엔 <span className="text-tertiary/90">헐값</span>을 부른다.
            그의 가격은 회사의 진짜 가치와 무관하다 — 그저 그날의 기분일 뿐이다.
          </p>
          <p>
            <span className="text-primary/90">올바른 자세</span>는 그의 가격을 참고하되 끌려다니지 않는 것이다.
            그가 환호할 때 비싸게 팔아주고, 절망할 때 헐값에 사준다. 그의 변덕에 동조해 같이 흥분하거나 패닉하면, 동업자가 아니라 그의 환자가 된다.
          </p>
          <p className="text-on-surface italic pl-4 border-l-2 border-primary/40 mt-5">
            &quot;시장 가격은 당신에게 봉사하기 위해 존재하는 것이지, 당신을 안내하기 위해 존재하는 것이 아니다.&quot;
            <span className="block text-xs text-primary-dim/70 mt-2 not-italic">— Benjamin Graham, The Intelligent Investor</span>
          </p>
        </div>
      </section>

      {/* Daily Routine */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface tracking-tight mb-2">
          4. 감정 통제 루틴
        </h3>
        <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
          충동을 의지로 막기는 어렵다. 매일·매주 반복되는 <span className="text-primary/90">루틴</span>이 충동의 자리를 미리 차지하게 한다.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {dailyRoutine.map((r) => (
            <article
              key={r.when}
              className="bg-surface-container-low rounded-xl p-5 ghost-border"
            >
              <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
                {r.when}
              </p>
              <ul className="space-y-2 text-sm text-on-surface-variant leading-relaxed">
                {r.actions.map((a, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-primary/60 mt-1.5 shrink-0">·</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      {/* Checklists */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface tracking-tight mb-2">
          5. 매수·매도 체크리스트
        </h3>
        <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
          매매 버튼을 누르기 전 통과해야 하는 관문. 충동 매매를 차단하는 가장 단순하고 강력한 도구.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <article className="bg-surface-container-low rounded-xl p-6 ghost-border">
            <div className="flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-tertiary/90 text-xl">
                shopping_cart_checkout
              </span>
              <h4 className="text-base font-serif text-on-surface tracking-tight">
                {buyChecklist.title}
              </h4>
            </div>
            <ul className="space-y-2.5 text-sm text-on-surface-variant leading-relaxed">
              {buyChecklist.items.map((item, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <span className="text-[10px] font-mono text-primary-dim/60 shrink-0 mt-1 w-4">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </article>

          <article className="bg-surface-container-low rounded-xl p-6 ghost-border">
            <div className="flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-error/80 text-xl">
                logout
              </span>
              <h4 className="text-base font-serif text-on-surface tracking-tight">
                {sellChecklist.title}
              </h4>
            </div>
            <ul className="space-y-2.5 text-sm text-on-surface-variant leading-relaxed">
              {sellChecklist.items.map((item, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <span className="text-[10px] font-mono text-primary-dim/60 shrink-0 mt-1 w-4">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </article>
        </div>
      </section>

      {/* Quotes */}
      <section>
        <h3 className="text-2xl font-serif text-on-surface tracking-tight mb-2">
          6. 흔들릴 때 펼쳐 보는 문장들
        </h3>
        <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
          시장이 격렬할 때, 본인이 흔들릴 때 다시 읽는다.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quotes.map((q, i) => (
            <article
              key={i}
              className="bg-surface-container-low rounded-xl p-6 ghost-border"
            >
              <span className="material-symbols-outlined text-primary/30 text-2xl mb-2 block">
                format_quote
              </span>
              <p className="text-sm text-on-surface leading-relaxed font-serif italic mb-3">
                {q.text}
              </p>
              <p className="text-xs text-primary tracking-wide mb-1">— {q.author}</p>
              <p className="text-[11px] text-on-surface-variant/70 leading-relaxed">
                {q.context}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Footer note */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-primary/70 text-2xl shrink-0">
            self_improvement
          </span>
          <div className="space-y-2 text-sm text-on-surface-variant leading-relaxed">
            <p>
              감정 통제는 한 번에 완성되지 않는다. <span className="text-primary/90">매매일지</span>를 통해 본인의 패턴을 인식하고,
              한 번의 실수를 다음 한 번의 룰로 만들어 가는 누적 과정이다.
            </p>
            <p>
              완벽한 통제를 목표로 하지 말고, 감정에 휘둘려 내린 결정의 횟수를 분기마다 줄여 나가는 것을 목표로 한다.
              잃지 않는 투자의 본질은 결국 <span className="text-primary/90">잃게 만드는 행동을 줄이는 것</span>이다.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
