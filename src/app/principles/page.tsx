import { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "나의 투자 원칙 | My Stock",
  description: "박탈감 회피를 1차 동기로 두는 절충형 인덱스+액티브 투자 헌장 (2026-05-09 v2)",
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
      "어떤 종목을 사느냐보다 자산을 어디에 얼마나 배분하느냐가 장기 수익률을 결정한다. 비중은 한 번 정하면 분기 단위로만 바꾼다. 박탈감 회피(1차 동기) + 손실회피(2차 모티프) + 통제감을 모두 균형 있게 충족하기 위해 50/25/25 구조로 설계됨.",
    principles: [
      {
        number: "1.1",
        rule: "코스피200 ETF 50% + 배당 25% + 알파 25%",
        why: "박탈감 1차 동기 → 시장 베타 추종이 우선 = 코스피200 ETF 50% 코어. 매도 충동 억제 앵커 + 손실회피 2차 모티프 + 매일 천천히 우상향 자산군 = 배당 25%. 종목 선택 능력에 대한 자기 자백을 인정하되 격리 결박 = 알파(저평가 성장주) 25%.",
        how: "배당 25% 안 구성: 한국 고배당 ETF 15% + 우량 배당주 2~3종목 10%. 알파 25% 안 구성: 기둥(개별 종목 4~5개) + 위성(사이클 수혜 ETF 1~2개). 목표 시점 2027/Q1, 분기당 7%p 분할 매도로 현재 51% 성장주를 25%로 이행.",
      },
      {
        number: "1.2",
        rule: "비상금 6개월치 1,500만 원 분리 (CMA/MMF, 주식 계좌 외)",
        why: "약세장 + 큰 지출이 동시에 오면 헌장 전체가 무너진다. 손실 구간에서 강제 매도해야 하기 때문. 자녀·차량·주택 대출 등 1년 내 약 2,500만 원 추가 지출 가능성. 단일 실패점 차단.",
        how: "월 250만 원 × 6개월 = 1,500만 원을 CMA/MMF/파킹통장으로 분리. 현재 51% 성장주 → 25% 이행과 함께 진행. 한 분기에 500만 원씩 3분기 분할로 매도, 펀더멘털 약한 종목부터 정리.",
      },
      {
        number: "1.3",
        rule: "알파 영역 종목당 상한 6%, 하한 1% (전체 자산 대비)",
        why: "한 종목이 크게 오르면 비중이 자연스럽게 커진다. 상한 없으면 단일 종목이 알파 영역의 60%를 먹어버리는 표류 패턴이 4~5개월 동안 검증됨. \"이 종목은 진짜 좋다\"는 본능을 룰로 결박해야 함.",
        how: "분기말 6% 초과 시 절삭, 1% 미만 자투리 종목 정리. 6% 상한이면 단일 종목 -50% 시 전체 자산 -3% 충격으로 제한.",
      },
      {
        number: "1.4",
        rule: "단일 섹터 비중 25% 이하",
        why: "섹터 사이클은 같이 움직인다. 반도체 한 섹터에 25%가 묶이면 사이클 전환기에 포트폴리오 전체가 흔들림. 코스피200 ETF에는 이미 반도체 25~35%가 자동 포함되어 있다는 점도 고려.",
        how: "메가캡·성장주 스크리닝·바이오 워치리스트 점검 시 섹터 합산 비중 항상 확인. 코스피200 ETF의 반도체 노출까지 합산해서 계산.",
      },
      {
        number: "1.5",
        rule: "기둥 + 위성 모델 — 알파 5~7개로 분산 + 통제감 균형",
        why: "분산형(10개+)은 분석 시간 부담 + 단일 종목 영향력 약함. 집중형(2~3개)은 \"내가 안 산 종목\"이 오를 때 박탈감 발작. 본인 1차 동기(박탈감 회피)를 알파 영역 안에서도 일관되게 적용한 구조.",
        how: "기둥(개별 종목 4~5개) — 본인이 깊게 분석하고 확신 있는 종목. 위성(사이클 수혜 ETF 1~2개) — 본인이 좋게 본 종목들이 여럿 들어 있는 ETF, 분석 부담 없음 + 박탈감 차단.",
      },
    ],
  },
  {
    id: "buying",
    number: "II",
    title: "매수 규율",
    subtitle: "Buying Discipline",
    icon: "shopping_cart_checkout",
    intro:
      "매수 버튼을 누르는 순간이 가장 위험하다. 사전에 만든 룰이 그 순간의 충동을 우회한다. 자동화 + 체크리스트 + 24시간 쿨다운으로 의지에 의존하지 않는 결박을 구축한다.",
    principles: [
      {
        number: "2.1",
        rule: "코어 ETF는 매월 정해진 일자 자동 적립식 매수",
        why: "\"한 달 중 가장 낮은 가격에 사면 합리적\"이라는 직관은 시장 타이밍 함정. 사전 예측 불가능. 매월 같은 날 자동 매수가 통계적으로 더 나은 결과(Vanguard/Schwab 다수 연구). 호가창 노출 시간도 줄어 충동 매매 트리거 차단.",
        how: "증권사 적립식 자동 매수 설정. 매수 시점은 한 번 정한 후 변경 금지. 거시 위기 발동 시 자동 적립 일시 중단(매수 룰 2.5 적용).",
      },
      {
        number: "2.2",
        rule: "신규 알파 매수 전 체크리스트 3가지 필수",
        why: "감으로 매수하면 (d) 자백한 \"근거 없는 자신감\" 패턴이 그대로 작동. 사전 약속이 사후 후회를 줄인다.",
        how: "매수 전 다음 셋 모두 종이/문서에 기록. ① DART 확정 공시 기반 회사 실적 점수 ② 진입 기준(monitor_entry/entry-configs.ts 활용) ③ 손절 라인. 셋 중 하나라도 비면 매수 보류.",
      },
      {
        number: "2.3",
        rule: "큰 의사결정 24시간 쿨다운",
        why: "박탈감 절정 + 유튜버 시그널 + 외인 매도 등 본인 의지가 가장 약한 순간이 매매를 가장 충동적으로 결정하는 순간이다. 24시간 후엔 흥분이 가라앉고 합리적 판단 가능. \"지금 안 사면 영원히 못 산다\"는 느낌은 99% 거짓.",
        how: "신규 매수 / 임의 매도 / 유튜버 시그널 매매 / 비중 조정 모두 결정 시점부터 24시간 지연. 스마트폰 스톱워치로 시간 측정 동안 분석만, 매매 X. 자동 트리거(트레일링 스탑·거시 위기 객관 트리거·분기 리밸런싱 정해진 일정)는 즉시 실행 예외.",
      },
      {
        number: "2.4",
        rule: "2단계 매매 분리 — my-stock에서 결정, 증권사 앱에서 실행",
        why: "주식창 보다 즉각 매매하는 \"무지성 매매\" 차단. 결정과 실행을 분리하면 결정 단계에서 체크리스트와 24시간 쿨다운이 강제 적용된다.",
        how: "1단계(결정): my-stock 프로젝트에서 매수 의사결정 폼 작성 + 24시간 타이머 시작. 2단계(실행): 24시간 통과한 종목만 증권사 앱에서 매매. 충동 매수 시 my-stock 켜고 폼 작성 자체가 5분 정도 시간을 끔.",
      },
      {
        number: "2.5",
        rule: "거시 위기 발동 시 신규 매수 일시 중단",
        why: "거시 위기 트리거(매도 룰 3.6)가 발동되어 보유 자산 전량 매도 상태에서 자동 적립까지 계속되면 일관성 무너짐.",
        how: "거시 위기 트리거 발동 시 자동 적립식 매수 일시 중단. 재매수 트리거 충족 시 자동 적립 재개.",
      },
      {
        number: "2.6",
        rule: "FOMO 매수 차단 — 시장 주간 +5% 폭등 시 그 주 신규 매수 금지",
        why: "박탈감 1차 동기로 인한 발작 매수 차단. 통계적으로 폭등 직후 1~2주는 횡보·조정 가능성이 더 높음. 폭등 마지막 날 매수가 통계적으로 가장 나쁜 진입 시점.",
        how: "시장 주간 +5% 이상 폭등 + 본인 계좌 정체 감지 시 그 주 신규 매수 금지. 분석은 가능, 매수는 다음 주 월요일 이후.",
      },
    ],
  },
  {
    id: "selling",
    number: "III",
    title: "매도 규율",
    subtitle: "Selling Discipline",
    icon: "logout",
    intro:
      "매도 룰은 매수 룰보다 더 정밀해야 한다. 매수는 안 하면 그만이지만, 매도는 보유 중인 자산을 만지는 행위라 감정 강도가 더 높다. 자동 트리거 + 단계별 분할 + 명확한 재매수 트리거로 자산 보호.",
    principles: [
      {
        number: "3.1",
        rule: "두 단계 손절·익절 룰",
        why: "매수 직후 변동성에 손절당하는 함정과 +50% 후 익절을 너무 일찍 하는 함정을 모두 피하기 위한 단계 분리.",
        how: "(a) 매수 ~ +10% 도달 전: 매수가 -10% 시 매도 (전통 손절). (b) +10% ~ +50% 도달 전: 도달 최고점 -10% 시 매도 (트레일링 스탑). 펀더멘털 무훼손 + 외인 매도 -5% 시 자동 보유 룰 적용 가능. (c) +50% 이후: 도달 최고점 -10% 시 매도. 펀더멘털 무관 즉시.",
      },
      {
        number: "3.2",
        rule: "매도 후 재매수 분할 + 백스톱",
        why: "손절 후 V자 반등하면 영원히 못 돌아오는 함정. 재매수 트리거를 매도 시점에 미리 정해두지 않으면 충동 결정이 됨.",
        how: "매도 시점에 다음을 캘린더·증권 앱 알림에 등록. 매도가 -10%(1/3) / -20%(1/3) / -30%(1/3) 분할 매수. 마지막 1/3 백스톱: 다음 셋 중 가장 먼저 발생 — (가) 매도가 -30% 도달 (나) 매도가 -20% 도달 후 저점 +10% 반등 (다) 매도가 -20% 도달 후 3개월 경과.",
      },
      {
        number: "3.3",
        rule: "코어 코스피200 ETF 매도 금지",
        why: "코어는 박탈감 안전판이다. 코어를 흔들면 안전판이 무너진다. 단순 사이클 다운으로 -25% 빠져도 V자 반등 가능성이 있어 보유가 답.",
        how: "분기 리밸런싱(50% 비중 유지)을 위한 매도 외에는 매도 금지. 핫 섹터 진입은 알파 영역 25% 안에서만. 다음 두 예외만 매도 가능 — (a) 슈퍼사이클(코스피·반도체 12개월 +50% 또는 반도체 ETF 코스피 대비 +30%p 아웃퍼폼) + 사이클 다운 신호(코스피 -10% + 반도체 60일 이평 하향 + 외인 5거래일 순매도) 동시 충족. (b) 거시 위기 트리거 발동(룰 3.6).",
      },
      {
        number: "3.4",
        rule: "배당주 매도 금지",
        why: "배당주는 매도 충동 억제 앵커 역할. \"팔지 않고 오래 보게 되는 명분\"이 본인 평온의 진짜 트리거 중 하나. 자주 매매하면 그 효과 사라짐.",
        how: "분기 리밸런싱 외 매도 금지. 예외: 펀더멘털 훼손(분기 영업이익 YoY -40% 이상 또는 배당 컷 발표). 거시 위기 트리거 발동 시 함께 매도.",
      },
      {
        number: "3.5",
        rule: "외인 매도 자동 보유 룰 (펀더멘털 무훼손 시)",
        why: "이상적 자기(시나리오 답변에서 침착)와 실시간 행동(외인 매도 보면 흔들림)이 어긋남을 본인 자백. 의지가 아니라 룰로 결박해야 함.",
        how: "매수 시점에 \"이런 일이 일어나면 내 가설이 깨진 것\"이라는 펀더멘털 훼손 기준 미리 정의(예: 분기 영업이익 YoY -20% 이하 + 컨센 미달). 그 기준이 발동 안 한 상태에서 외인 순매도 + 가격 -5% 빠지면 다시 분석하지 않고 그냥 보유.",
      },
      {
        number: "3.6",
        rule: "거시 위기 트리거 발동 시 보유 자산 100% 매도",
        why: "사용자 거시 공포 본능을 룰로 흡수하되, 단순 \"감\"이 아니라 객관적 트리거로 결박. 이란-미국 전쟁 사례 데이터 검증 — \"5거래일 연속 보도\" 트리거는 03-09 발동 시점에 이미 -18% 손실 후. 빠른 트리거 추가 필요.",
        how: "다음 둘 중 어느 하나 충족 시 발동. **(빠른 트리거)** 셋 모두 충족 — ① 단일거래일 코스피 -5% 이상 폭락(종가 또는 시초가 갭) ② 매일경제/한국경제 1면 위기 사유 보도 ③ Claude에게 거시 상황 보고 후 동의. **(객관 트리거)** 둘 다 충족 — ① 코스피 전고점 -10% 도달 ② 다음 셋 중 하나: 전쟁 발발 / 한국 분기 GDP -2% 또는 미국 두 분기 연속 마이너스 / 환율 1,500원 돌파. 발동 후: 매도 자금 50% CMA/MMF, 50% 단기채 ETF 분산. 재매수 트리거(저점 +10% / 외인 5거래일 연속 순매수 / 거시 사유 해소) 충족 시 1/3씩 분할 재매수.",
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
          "출처를 좁혀야 노이즈를 줄일 수 있다. 두 곳은 한국 경제 보도의 표준이고, 같은 사실을 두 곳에서 교차 확인 가능. 거시 위기 트리거의 보도 조건도 이 두 곳 기준.",
        how:
          "리포트·매크로 분석에서 인용 시 항상 출처 명시. 다른 매체 정보는 두 곳에서 확인된 후에만 보조 인용.",
      },
      {
        number: "4.3",
        rule: "확정 데이터 우선, 추정치는 보조 지표로만",
        why:
          "DART 확정 공시 > 잠정실적 > 증권사 컨센. 위 단계로 갈수록 신뢰도가 떨어진다. 알파 영역 신규 매수 시 점수 계산은 확정 공시 기반이 필수.",
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
      {
        number: "4.5",
        rule: "거시 위기 판단은 Claude 동의를 필수 검증 단계로",
        why:
          "단일 유튜버 편향, 단일 신문 편향을 제3의 분석으로 검증. 가짜 패닉 보도와 단일 유튜버의 자극적 보도가 트리거를 오발동시키는 것 차단.",
        how:
          "거시 위기 빠른 트리거(룰 3.6) 발동 직전, Claude에게 다음 보고서 형식으로 상황 보고: 코스피·환율·금리 (3년 평균 대비), 미국·중국·한국 GDP 흐름, 진행 중인 전쟁·지정학 충돌, 매경/한경 1면 헤드라인 5거래일치, 신뢰 유튜버 발언 요약. Claude가 \"거시 위기 아닙니다\"로 답하면 트리거 미발동.",
      },
      {
        number: "4.6",
        rule: "잠정실적 분석은 3가지 모두 확인 (YoY 단일 비교 금지)",
        why:
          "매출·이익이 YoY로 좋아 보여도 컨센 미스이거나, 일회성 이익이 끼었거나, 분기 추세가 꺾이는 중일 수 있다.",
        how:
          "① 컨센서스 비교 ② 분기 추세 ③ 일회성 영업외 분리 — 세 가지 모두 통과해야 \"실적 호조\"로 분류.",
      },
    ],
  },
  {
    id: "psychology",
    number: "V",
    title: "심리 통제",
    subtitle: "Emotional Discipline",
    icon: "self_improvement",
    intro:
      "1차 동기 = 박탈감 회피. 2차 모티프 = 손실회피. 두 동기는 양립 불가. 박탈감 발작이 가장 위험한 순간이며, 그 순간을 결박하는 룰들이 헌장의 핵심.",
    principles: [
      {
        number: "5.1",
        rule: "박탈감이 1차 동기, 손실회피는 2차 (자기진단 거꾸로 함정 회피)",
        why:
          "처음 메모리는 \"잃지 않는 투자가 1번\"이었지만, 8주 진단으로 본인의 진짜 1차 동기가 박탈감 회피임이 두 시나리오 답변에서 확인됨. 시장 +30%·본인 +8%가 본인 -18% 평가손보다 더 견디기 힘들다고 답변. 본인 한 단어: \"박탈감.\"",
        how:
          "헌장의 모든 룰을 \"박탈감 발작 시점에서도 작동하는가\"로 점검. 손실회피와 충돌하면 박탈감 회피가 1차로 적용. 단, 영구 손실 회피(아래 정의 명확화 섹션)는 손실회피의 본질이라 절대 양보 X.",
      },
      {
        number: "5.2",
        rule: "남과 비교해서 내린 결정은 모두 무효",
        why:
          "남이 번 돈은 표본 1개. 그 사람의 매수 시점·비중·진입 가격·매도 계획을 모르면 결과만 보고 따라 사는 건 도박.",
        how:
          "친구·커뮤니티·유튜버 수익 자랑을 보면 매주 일요일 자동 리포트(YTD 누적 수익 + 누적 배당 + 코스피 대비 상대 성과)를 다시 본다. 전략 변경은 분기 단위로만.",
      },
      {
        number: "5.3",
        rule: "유튜버 시그널 매매는 24시간 쿨다운 통과 후에만",
        why:
          "신뢰 유튜버가 점심·오후 시그널을 발신하면 본인 의지가 가장 약하다고 자백. 의지로는 못 막는다 — \"신뢰하는 사람\"의 말이라.",
        how:
          "유튜버가 \"지금 다 파셔야 한다\" 같은 강한 시그널 발신 시 24시간 후 매매 결정. 24시간 후에도 그 시그널이 합리적이면 매매. 보통 흥분이 가라앉고 다른 정보가 들어와 검증되어 매매 보류로 결정되는 경우가 많음.",
      },
      {
        number: "5.4",
        rule: "매도 후 \"못 잡은 종목\" 후회 금지",
        why:
          "원칙을 지킨 결과 못 잡은 것은 실패가 아니라 성공이다. 그 종목을 잡았다면 다음 사이클 정점에서 비슷한 종목을 또 추격했을 것.",
        how:
          "급등 종목을 보고 배가 아플 때 이 페이지를 다시 펼친다. 본인이 못 잡은 게 아니라 안 잡은 것임을 확인.",
      },
      {
        number: "5.5",
        rule: "와이프 응대 한 줄 답변 미리 준비",
        why:
          "\"왜 우리는 +X%야?\" 같은 와이프 질문 자체는 24시간 쿨다운으로 풀리지 않음. 정서적 압박은 즉각 응대해야 함.",
        how:
          "표준 답변: \"코스피 ETF 절반 들고 있어서 시장은 따라가. 더 사면 천장이라 위험해. 우리 룰대로 가는 게 맞아.\" 와이프께 헌장 룰북·주간 리포트는 같이 보여주되, 의사결정 참여는 안 부담.",
      },
      {
        number: "5.6",
        rule: "충동이 강할 때 거래 금지",
        why:
          "공포·흥분·복수심 — 강한 감정은 모두 동일하게 판단을 망친다.",
        how:
          "감정 강도 7/10 이상이면 그날은 거래 X. 매매일지에 감정 상태 기록 후 다음 날 재검토. 24시간 쿨다운 룰의 일반 케이스.",
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
      "원칙은 매일의 작은 운영 규율로 실현된다. 자동화·정기 점검·외부 결박이 의지에 기대지 않는 헌장의 뼈대.",
    principles: [
      {
        number: "6.1",
        rule: "매주 일요일 자동 리포트 5섹션",
        why:
          "박탈감의 변형(\"내 종목이 일하는 느낌이 없다\")을 분기배당이 아니라 주간 리포트로 채운다. 누적·상대 성과가 단기 변동을 노이즈로 처리하는 효과.",
        how:
          "5섹션: ① 주간 변동 ② YTD 누적 수익 ③ YTD 누적 배당 ④ 펀더멘털 진척(주요 보유 종목 매출·영업이익 YoY) ⑤ 코스피 대비 상대 성과. my-stock에서 자동 생성.",
      },
      {
        number: "6.2",
        rule: "분기 자기검증 — 알파 vs 코스피 ETF 비교",
        why:
          "본인 종목 선택 능력이 진짜 시장 평균보다 나은지 객관적 데이터로 확인. (d) 자백 결박. 계속 못 이긴다는 게 데이터로 드러나면 비중을 강제로 줄여 손해 키우는 걸 막기 위함.",
        how:
          "매 분기말 알파 영역 누적 수익률 vs 같은 기간 코스피200 ETF 비교 기록. 4분기(1년) 연속으로 코스피 ETF보다 -5%p 이상 지면 알파 비중을 자동 -5%p 축소. 의지가 아니라 룰로.",
      },
      {
        number: "6.3",
        rule: "분기 리밸런싱 — 종목당 6% 초과 절삭, 1% 미만 정리",
        why:
          "한 종목이 크게 오르면 비중이 자연스럽게 커지므로 분기마다 점검해 6% 상한 유지.",
        how:
          "분기말 1회 리밸런싱. 6% 초과 종목은 6%로 절삭(차익실현), 1% 미만 자투리 종목은 정리. 코어 ETF는 50% 비중 유지를 위한 리밸런싱만.",
      },
      {
        number: "6.4",
        rule: "매매일지 반영 시 모든 보유 종목 현재가도 당일 시세로 갱신",
        why:
          "한 종목만 갱신하면 포트폴리오 평가액이 부정확해지고, 비중·수익률 통계도 왜곡된다.",
        how:
          "매수·매도 기록할 때 보유 종목 전체를 같은 날짜 시세로 일괄 갱신. /journal 페이지 사용.",
      },
      {
        number: "6.5",
        rule: "응답·UI 모두 한국어 우선",
        why:
          "트리밍, 워치리스트 같은 영어 표현이 익숙하지 않으면 직관적 의사결정에 방해가 된다.",
        how:
          "비중 축소, 관심 종목, 매수 검토 등 한국어 표현으로 통일. 영어 약어는 PER·ROE처럼 보편화된 것만 허용.",
      },
      {
        number: "6.6",
        rule: "리포트에 지표 간 상관관계 흐름도 항상 포함",
        why:
          "지표를 따로 보면 노이즈, 묶어서 보면 패턴. 학습 효과를 위해 흐름도가 필수.",
        how:
          "거시 리포트·종목 분석 모두 핵심 지표 간 인과관계를 ASCII 흐름도로 표현.",
      },
    ],
  },
];

// 보류 항목 (재검토 트리거 정의)
const heldItems = [
  {
    title: "사이클 정점 매수 타이밍",
    decision: "단순 분기 분할 매수 유지 (슈퍼사이클 종료 신호까지)",
    why: "옵션 B(밸류에이션 트리거)는 슈퍼사이클 진입 종목에 못 올라타는 박탈감이 더 큰 고통이라는 본인 판단. 본인 1차 동기와 일관된 선택.",
    triggers: [
      "반도체 ETF가 60일 이동평균선 하향 돌파 + 외인 5거래일 연속 순매도",
      "글로벌 메모리 반도체 현물가(DRAM/NAND) 분기 단위 하락 시작",
      "코스피 지수 전고점 대비 -15% 도달",
    ],
    next: "위 셋 중 하나 발동 시 옵션 B(밸류에이션 트리거) 또는 C(시간 연장)로 전환 검토.",
  },
  {
    title: "한국 시장 100% 노출",
    decision: "한국 100% 유지 (코리아 디스카운트 개선 모멘텀에 베팅)",
    why: "정부의 코리아 디스카운트 개선 정책 + 한국 시장 슈퍼사이클 모멘텀. 정치 변수 의존성은 객관 트리거로 결박.",
    triggers: [
      "한국 시장 지지부진 — 코스피 6개월간 ±5% 박스권 횡보",
      "달러 환율 저렴 — 원달러 환율 1,200원 이하",
      "정치 변수 변화 — 코리아 디스카운트 개선 정책 후퇴 또는 정권 교체",
    ],
    next: "위 셋 중 둘 충족 시 미국 시장 진입 검토 시작. 진입 규모: 코어 50% 안에서 미국 S&P500 ETF 10~20%p, 배당 25% 안에서 미국 배당 ETF 5~10%p, 알파 25% 안에서 미국 저평가 성장주 5~10%p. 6~12개월 분할 진입.",
  },
];

// 거부 항목
const rejectedItems = [
  {
    title: "와이프 공동 의사결정 참여",
    why: "와이프 일희일비 성격으로 주식 의사결정 참여 시 가정 갈등 트리거. 와이프가 사용자에게 투자를 일임하기로 협의 완료.",
    alternative: "정보 공유는 OK. 주간 리포트와 헌장 룰북은 같이 보기 — 와이프가 \"우리 자산이 잘 운용되고 있다\"는 안심을 얻을 수 있는 수준. 의사결정 참여는 부담시키지 않음. 와이프 결박 자리는 디지털 결박 도구(자동 매수·캘린더 알림·24시간 쿨다운·매수 전 체크리스트 강제)가 대체.",
  },
];

const reminders = [
  {
    text: "박탈감 회피가 1차 동기, 손실회피는 2차다.",
    context: "시장이 폭등하는데 내 계좌만 정체되는 고통이 평가손 자체보다 더 견디기 힘들다는 자기진단. 처음에는 손실회피를 1차로 잘못 인식했었음.",
  },
  {
    text: "변동성이 두려워 안전마진 있는 종목조차 못 사면 그건 투자가 아니라 회피다.",
    context: "잃지 않는 투자 = 영구 손실 회피이지, 일시적 변동성 회피가 아님.",
  },
  {
    text: "원칙을 지킨 결과 못 잡은 것은 실패가 아니라 성공이다.",
    context: "급등 종목을 못 잡았다고 배가 아플 때.",
  },
  {
    text: "\"지금 안 사면 영원히 못 산다\"는 99% 거짓이다. 시장은 항상 다시 기회를 준다.",
    context: "FOMO 발작 + 유튜버 시그널 + 시장 폭등 시.",
  },
  {
    text: "코어와 배당주는 매도 안 한다. 박탈감 안전판이기 때문이다.",
    context: "코스피 -25% 사이클 다운 시. 단순 사이클 다운은 V자 반등 가능성, 거시 위기와 다르다.",
  },
  {
    text: "유튜버가 \"지금 다 파세요\"라고 하면 24시간 후에 결정한다.",
    context: "신뢰하는 사람의 말이라 의지로 못 막는다 — 룰로 막는다.",
  },
];

export default function PrinciplesPage() {
  return (
    <div className="space-y-14">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Investing Constitution v2 · 2026-05-09
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          나의 투자 원칙
        </h2>
        <p className="text-base text-on-surface-variant mt-2 leading-relaxed">
          박탈감 회피를 1차 동기로 두는 절충형 인덱스+액티브 한국 시장 투자자의 운영 헌장.
        </p>
      </section>

      {/* 한 페이지 요약 (와이프 공유용) */}
      <section className="bg-gradient-to-br from-primary/10 via-surface-container-low to-surface-container rounded-xl p-6 sm:p-8 ghost-border">
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/70 mb-3">
          One-Page Summary · 와이프와 함께 보는 페이지
        </p>
        <h3 className="text-lg font-serif text-primary mb-4 tracking-tight">
          한 문장 요약
        </h3>
        <p className="text-base text-on-surface leading-relaxed mb-6 font-serif">
          코스피200 ETF 절반(50%) + 한국 고배당 ETF·우량 배당주(25%) + 직접 분석한 저평가 성장주(25%).
          <br />
          시장과 함께 가는 걸 1순위로 두고, 거시 위기 발동 시 전량 매도하는 절충형 인덱스+액티브 투자자.
        </p>
        <h3 className="text-lg font-serif text-primary mb-4 tracking-tight">
          핵심 룰 6가지 (와이프가 안심하는 안전성 위주)
        </h3>
        <ul className="text-sm text-on-surface-variant space-y-2.5 leading-relaxed">
          <li>· <span className="text-primary/90">비상금 6개월치 1,500만 원 분리</span> (CMA/MMF, 주식 계좌 외) — 약세장 + 큰 지출 동시에 와도 강제 매도 X</li>
          <li>· <span className="text-primary/90">코스피200 ETF 절반(50%)</span>은 매월 정해진 일자 자동 적립식 매수, 매도 금지</li>
          <li>· <span className="text-primary/90">큰 의사결정은 24시간 쿨다운</span> — 충동 매매 차단</li>
          <li>· <span className="text-primary/90">거시 위기 발동 시 전량 매도</span> — 명확한 트리거(단일일 -5% + 거시 사유 OR 코스피 -10% + 객관 사유)</li>
          <li>· <span className="text-primary/90">매주 일요일 자동 리포트</span>로 평가액·배당 누적 확인 (와이프와 함께 보기)</li>
          <li>· <span className="text-primary/90">전략 변경은 분기 단위로만</span> — 매주 결정 바꾸지 않음</li>
        </ul>
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

      {/* 1차 동기 재진단 */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <div className="flex items-baseline gap-2 mb-3">
          <span className="material-symbols-outlined text-primary/70 text-xl">psychology</span>
          <h3 className="text-lg font-serif text-primary tracking-tight">
            1차 동기 재진단 (2026-05-09 v2)
          </h3>
        </div>
        <p className="text-sm text-on-surface-variant mb-5 leading-relaxed">
          처음 메모리에는 "잃지 않는 투자가 1차 동기"로 박혀 있었으나, 심층 진단으로 본인의 진짜 1차 동기가
          <span className="text-primary/90"> 박탈감 회피 = "시장과 함께 가고 싶다"</span>임이 확인됨. 사고실험에서
          시장 +30%·본인 +8%·손실 0이 본인 -18% 평가손보다 더 견디기 힘들다고 본인 입으로 답변. 본인 한 단어 자가진단: <span className="text-primary/90">"박탈감"</span>.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
            <p className="text-[10px] uppercase tracking-[0.15em] text-primary/90 mb-2 font-medium">
              1차 동기 · Primary
            </p>
            <h4 className="text-base font-serif text-on-surface mb-2">박탈감 회피</h4>
            <p className="text-xs text-on-surface-variant/85 leading-relaxed">
              시장이 폭등하는데 내 계좌만 정체되는 고통 &gt; 손실 자체. \"원래 성향도 모든 사람들과 같이 하고 싶고 같이 가고 싶은 마음이 큽니다.\" → 코스피200 ETF 50%로 시장 베타 추종 우선.
            </p>
          </div>
          <div className="bg-tertiary/5 border border-tertiary/20 rounded-lg p-4">
            <p className="text-[10px] uppercase tracking-[0.15em] text-tertiary/90 mb-2 font-medium">
              2차 모티프 · Secondary
            </p>
            <h4 className="text-base font-serif text-on-surface mb-2">손실회피</h4>
            <p className="text-xs text-on-surface-variant/85 leading-relaxed">
              평가손 자체보다 거시 흐름으로 원금이 깨질 것 같은 느낌이 더 큰 트리거. 시나리오 -18% 평가손에서는 침착하게 펀더멘털 점검 후 대응. → 거시 위기 트리거 + 비상금 분리 + 코어/배당 매도 금지로 결박.
            </p>
          </div>
        </div>
        <p className="text-xs text-on-surface-variant/70 mt-5 leading-relaxed">
          → 두 동기는 <span className="text-error/80">양립 불가</span>. 한쪽을 풀려고 비중을 옮기면 다른 쪽이 도진다. 헌장은 "박탈감을 1차로 두되, 영구 손실은 절대 양보 X" 구조.
        </p>
      </section>

      {/* Why */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <h3 className="text-lg font-serif text-primary mb-4 tracking-tight">
          왜 원칙인가
        </h3>
        <div className="space-y-3 text-sm text-on-surface-variant leading-relaxed">
          <p>
            시장은 매일 새로운 이야기를 들고 온다. 슈퍼사이클·AI 혁명·금리 인하·전쟁 — 어떤 이야기든
            "이번엔 다르다"는 메시지를 담고 있다. 그 이야기에 매번 휘둘리면 일관된 성과는 불가능하다.
          </p>
          <p>
            원칙은 시장의 이야기보다 느리게 바뀐다. 그래서 단기적으로는 답답해 보이지만,
            장기적으로는 <span className="text-primary/90">감정에 휘둘리지 않는 유일한 방법</span>이다.
          </p>
          <p>
            이 페이지는 자기 자신과의 약속을 누적해 명문화한 것이다. 새로운 원칙이 추가될 수는 있지만,
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
        </section>
      ))}

      {/* 보류 항목 */}
      <section>
        <div className="flex items-baseline gap-3 mb-2">
          <span className="text-[11px] font-mono text-primary-dim/60 tracking-wider">VII.</span>
          <h3 className="text-2xl font-serif text-on-surface tracking-tight">
            보류 항목 (재검토 트리거)
          </h3>
          <span className="material-symbols-outlined text-primary/60 text-xl">schedule</span>
        </div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/50 mb-3">Held Items</p>
        <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
          현재는 결정 보류. 객관적 트리거 발동 시 재검토. 감으로 판단하지 않도록 트리거를 명문화.
        </p>
        <div className="space-y-4">
          {heldItems.map((item) => (
            <article key={item.title} className="bg-surface-container-low rounded-xl p-6 ghost-border">
              <h4 className="text-base font-serif text-on-surface mb-2 tracking-tight">{item.title}</h4>
              <p className="text-xs text-on-surface-variant mb-3">
                <span className="text-primary/80 font-medium">현재 결정 · </span>
                {item.decision}
              </p>
              <p className="text-xs text-on-surface-variant/85 mb-3 leading-relaxed">
                <span className="text-primary-dim/80 font-medium">왜 · </span>
                {item.why}
              </p>
              <div className="bg-surface-container/50 rounded-lg p-4 mb-3">
                <p className="text-[11px] uppercase tracking-wider text-primary-dim/70 mb-2">재검토 트리거</p>
                <ul className="text-xs text-on-surface-variant space-y-1.5 leading-relaxed">
                  {item.triggers.map((t, i) => (
                    <li key={i}>· {t}</li>
                  ))}
                </ul>
              </div>
              <p className="text-xs text-on-surface-variant/85 leading-relaxed">
                <span className="text-tertiary/90 font-medium">발동 후 · </span>
                {item.next}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* 거부 항목 */}
      <section>
        <div className="flex items-baseline gap-3 mb-2">
          <span className="text-[11px] font-mono text-primary-dim/60 tracking-wider">VIII.</span>
          <h3 className="text-2xl font-serif text-on-surface tracking-tight">
            거부 항목 (의도적 불채택)
          </h3>
          <span className="material-symbols-outlined text-primary/60 text-xl">block</span>
        </div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/50 mb-3">Rejected Items</p>
        <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
          제안되었으나 본인 환경·합리적 사유로 채택하지 않은 항목. 사유와 대안 결박을 명문화.
        </p>
        <div className="space-y-4">
          {rejectedItems.map((item) => (
            <article key={item.title} className="bg-surface-container-low rounded-xl p-6 ghost-border">
              <h4 className="text-base font-serif text-on-surface mb-3 tracking-tight">{item.title}</h4>
              <p className="text-xs text-on-surface-variant/85 mb-3 leading-relaxed">
                <span className="text-error/80 font-medium">왜 거부 · </span>
                {item.why}
              </p>
              <p className="text-xs text-on-surface-variant/85 leading-relaxed">
                <span className="text-tertiary/90 font-medium">대체 결박 · </span>
                {item.alternative}
              </p>
            </article>
          ))}
        </div>
      </section>

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
              이 헌장은 Claude와의 반복 대화로 누적된 것이다.
              새로운 원칙이 필요하면 매매일지에 먼저 기록하고, 분기 회고에서 정식 원칙으로 승격한다.
            </p>
            <p>
              원칙을 깨야 할 상황이 생기면 그 자리에서 즉흥적으로 깨지 말고,
              <span className="text-primary/90"> 24시간 대기 + 매매일지에 사유 기록 + 분기 회고에서 명문화</span> 절차를 거친다.
            </p>
            <p className="text-xs text-on-surface-variant/60">
              헌장의 본질은 결국 <span className="text-primary/80">박탈감 발작 시점에서도 작동하는 룰</span>을 만드는 것이다.
              의지가 약한 순간을 위해 자동화·체크리스트·24시간 쿨다운으로 결박한다.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
