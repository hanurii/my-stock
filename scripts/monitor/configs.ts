/**
 * 매도 트리거 자동 모니터 — 종목별 설정
 *
 * 신규 종목 추가 시 이 파일에 엔트리만 추가하면 monitor-research.ts가 자동 처리.
 * 트리거 정의·임계값·뉴스 키워드는 각 종목 research/{code}.json의 exit_timing과 일치시킨다.
 */
import type { MonitorConfig } from "./types";

export const CONFIGS: MonitorConfig[] = [
  // ───── 아바코 (083930) ─────
  {
    code: "083930",
    name: "아바코",
    corp_code: "00442145",
    triggers: [
      {
        id: "per",
        label: "PER",
        source: "valuation.per",
        threshold: { gte: 15 },
        threshold_label: "15배 돌파",
        suffix: "배",
        precision: 2,
        warn_threshold: 12,
      },
      {
        id: "peg",
        label: "PEG",
        source: "valuation.peg",
        threshold: { gte: 0.7 },
        threshold_label: "0.7 돌파",
        precision: 2,
        warn_threshold: 0.6,
      },
      {
        id: "supply_gap",
        label: "수주 공백",
        source: "supply_gap.days_ago",
        threshold: { gte: 90 },
        threshold_label: "90일 경과",
        suffix: "일",
      },
      {
        id: "related_party",
        label: "대명ENG 매입 비율",
        source: "related_party.ratio_pct",
        threshold: { gte: 10 },
        threshold_label: "매출의 10% 초과",
        suffix: "%",
        precision: 2,
        warn_threshold: 8,
      },
    ],
    related_party_partner: "대명ENG",
    // 아바코는 affiliate_transactions collector를 사용하지 않음(관계사 1개만 추적)
    // → YoY 메트릭 추가는 SK하이닉스부터 적용
    news_keywords: [
      "중국 디스플레이 장비 수출 규제",
      "중국 OLED 보조금",
      "BOE 8.6세대 투자 축소",
    ],
  },

  // ───── SK하이닉스 (000660) ─────
  // 정량: PBR + 영업이익률 + 계열사 거래 비율
  // 공시 감지: SK스퀘어(corp_code 01596425) 처분·매각 공시
  // 뉴스: 삼성 HBM 점유율 추격 / DRAM 가격 / 엔비디아 Capex
  {
    code: "000660",
    name: "SK하이닉스",
    corp_code: "00164779",
    triggers: [
      {
        id: "pbr",
        label: "PBR",
        source: "valuation.pbr",
        threshold: { gte: 8 },
        threshold_label: "8배 돌파",
        suffix: "배",
        precision: 2,
        warn_threshold: 7.5,
      },
      {
        id: "op_margin",
        label: "분기 영업이익률",
        source: "op_margin.op_margin_pct",
        threshold: { lte: 30 },
        threshold_label: "30% 이하",
        suffix: "%",
        precision: 1,
        warn_threshold: 40,
      },
      {
        // 사용자 trigger 원문 '1% 초과'는 SK이노/SK㈜ 운영비(0.07~0.4%)만 본 것.
        // SK에코플랜트(EPC, M16·M18 메모리 공장 건설) 정상 거래로 5.6% 수준은 일상.
        // 절대값은 정보 표시용(임계 7%), 실제 매도 신호는 YoY 증가율로 포착.
        id: "affiliate_ratio",
        label: "계열사 거래 매출 비율 (1년)",
        source: "affiliate_transactions.ratio_pct",
        threshold: { gte: 7 },
        threshold_label: "매출의 7% 초과",
        suffix: "%",
        precision: 3,
        warn_threshold: 6,
      },
      {
        // 사용자 원문 '급격히 확대' 의도에 가장 가까운 메트릭 — 전년 동기 대비 변화
        id: "affiliate_yoy_pp",
        label: "계열사 거래 비율 YoY 변화",
        source: "affiliate_transactions.yoy_change_pp",
        threshold: { gte: 2 },
        threshold_label: "+2%p 이상 급증",
        suffix: "%p",
        precision: 2,
        warn_threshold: 1,
      },
      {
        id: "sk_square_disposal",
        label: "SK스퀘어 처분·매각 공시 (90일)",
        source: "external_corp_disclosures.count",
        threshold: { gte: 1 },
        threshold_label: "처분 공시 1건+",
        suffix: "건",
      },
      {
        // hyslrSttus 기반 SK스퀘어 보유 비율 — 분기보고서 갱신 시에만 변화 감지 가능.
        // 공시 감지와 병용하여 2중 안전망.
        id: "sk_square_ratio",
        label: "SK스퀘어 보유 비율",
        source: "major_shareholder.end_ratio",
        threshold: { lte: 19 },
        threshold_label: "19% 이하로 감소",
        suffix: "%",
        precision: 2,
        warn_threshold: 19.5,
      },
      {
        id: "sk_square_change_pp",
        label: "SK스퀘어 기초→기말 변화",
        source: "major_shareholder.change_pp",
        threshold: { lte: -0.1 },
        threshold_label: "-0.1%p 이상 감소",
        suffix: "%p",
        precision: 2,
        warn_threshold: -0.01,
      },
    ],
    major_shareholder_name: "SK스퀘어",
    external_corp_code: "01596425", // SK스퀘어
    // SK스퀘어가 보유한 SK하이닉스 매각 시 발생하는 공시만 정확히 잡기 위함:
    // - "타법인주식 및 출자증권의 처분결정" (SK스퀘어가 SK하이닉스 주식을 처분하는 결정)
    // - 자회사 자사주 처분 공시는 false-positive이므로 제외
    external_corp_keywords: [
      "타법인주식 및 출자증권의 처분",
      "타법인주식및출자증권의처분",
      "타법인 주식 및 출자증권 처분",
    ],
    news_keywords: [
      "삼성 HBM3E 엔비디아 점유율",
      "삼성 HBM4 엔비디아 공급",
      "DRAM 고정거래가 하락",
      "엔비디아 Capex 가이던스",
      "SK스퀘어 SK하이닉스 블록딜",
    ],
  },

  // ───── 삼성전자 (005930) ─────
  // research/005930.json exit_timing 6개 트리거 자동화:
  // 1. PER ≥ 35배
  // 2. 자사주 소각 공시 공백 (2026.03.31 2차 소각 이후 후속 발표 부재 감지 — 180일 임계)
  // 3. 삼성생명(00126256) 타법인주식 처분 공시 (보험업법 개정 등으로 매도 시)
  // 4. 이재용 회장 지분 변동 (hyslrSttus 기준, 분기보고서 갱신 시 감지)
  // 5. 뉴스: 파운드리 분사·매각, HBM4 엔비디아 공급 성공/실패
  {
    code: "005930",
    name: "삼성전자",
    corp_code: "00126380",
    triggers: [
      {
        id: "per",
        label: "PER",
        source: "valuation.per",
        threshold: { gte: 35 },
        threshold_label: "35배 돌파",
        suffix: "배",
        precision: 2,
        warn_threshold: 33,
      },
      {
        id: "buyback_gap",
        label: "자사주 소각 공시 공백",
        source: "buyback_cancellation_gap.days_ago",
        threshold: { gte: 180 },
        threshold_label: "180일 경과",
        suffix: "일",
        warn_threshold: 120,
      },
      {
        id: "samsung_life_disposal",
        label: "삼성생명 처분 공시 (90일)",
        source: "external_corp_disclosures.count",
        threshold: { gte: 1 },
        threshold_label: "처분 공시 1건+",
        suffix: "건",
      },
      {
        id: "lee_jae_yong_ratio",
        label: "이재용 지분 비율",
        source: "major_shareholder.end_ratio",
        threshold: { lte: 1.4 },
        threshold_label: "1.4% 이하로 감소",
        suffix: "%",
        precision: 2,
        warn_threshold: 1.55,
      },
      {
        id: "lee_jae_yong_change_pp",
        label: "이재용 기초→기말 변화",
        source: "major_shareholder.change_pp",
        threshold: { lte: -0.1 },
        threshold_label: "-0.1%p 이상 감소",
        suffix: "%p",
        precision: 2,
        warn_threshold: -0.01,
      },
      {
        // 실시간 일가 매도 감지 (최대주주등소유주식변동신고서 본문 파싱)
        id: "family_sell_count",
        label: "일가 매도 공시 (90일)",
        source: "insider_family_trades.trades.count",
        threshold: { gte: 1 },
        threshold_label: "매도 건수 1건+",
        suffix: "건",
      },
      {
        id: "family_sell_shares",
        label: "일가 누적 매도 주식수 (90일)",
        source: "insider_family_trades.total_shares_sold",
        threshold: { gte: 5000000 },
        threshold_label: "500만주 이상",
        suffix: "주",
        warn_threshold: 1000000,
      },
    ],
    external_corp_code: "00126256", // 삼성생명
    family_member_names: ["홍라희", "이재용", "이부진", "이서현", "이건희"],
    external_corp_keywords: [
      "타법인주식 및 출자증권의 처분",
      "타법인주식및출자증권의처분",
      "타법인 주식 및 출자증권 처분",
    ],
    major_shareholder_name: "이재용",
    news_keywords: [
      "삼성전자 파운드리 분사",
      "삼성전자 파운드리 매각",
      "삼성 HBM4 엔비디아 공급",
      "삼성 HBM4 엔비디아 계약",
      "삼성전자 자사주 소각",
      "삼성 일가 블록딜",
      "삼성생명 삼성전자 지분 매각",
    ],
  },

  // ───── SNT에너지 (100840) ─────
  // research/100840.json exit_timing 5개 중 4개 자동화:
  // 1. 영업이익률 ≤ 10% (구조적 개선 반전)
  // 2. 수주 공시 공백 ≥ 180일 (6개월, 중동 수주 감소)
  // 3. SNT홀딩스 특수관계인 지분 ≤ 50% (경영권 마지노선)
  // 4. SNT홀딩스(00225159) EB 신규 발행 공시 (외부법인 추적)
  // 5. 뉴스: 방산·원전·중동 프로젝트
  // (주가 +50% 급등 + 외국인 변화는 평단 참조 복잡 — 생략)
  {
    code: "100840",
    name: "SNT에너지",
    corp_code: "00648721",
    triggers: [
      {
        id: "op_margin",
        label: "분기 영업이익률",
        source: "op_margin.op_margin_pct",
        threshold: { lte: 10 },
        threshold_label: "10% 이하",
        suffix: "%",
        precision: 1,
        warn_threshold: 12,
      },
      {
        id: "supply_gap",
        label: "수주 공백",
        source: "supply_gap.days_ago",
        threshold: { gte: 180 },
        threshold_label: "180일 경과",
        suffix: "일",
        warn_threshold: 120,
      },
      {
        id: "snt_holdings_ratio",
        label: "SNT홀딩스 지분 비율",
        source: "major_shareholder.end_ratio",
        threshold: { lte: 50 },
        threshold_label: "50% 이하로 감소",
        suffix: "%",
        precision: 2,
        warn_threshold: 51,
      },
      {
        id: "snt_holdings_eb",
        label: "SNT홀딩스 EB 발행 공시 (90일)",
        source: "external_corp_disclosures.count",
        threshold: { gte: 1 },
        threshold_label: "EB 발행 공시 1건+",
        suffix: "건",
      },
    ],
    major_shareholder_name: "SNT홀딩스",
    external_corp_code: "00225159", // SNT홀딩스 (구 SNT모터스)
    external_corp_keywords: [
      "교환사채권발행결정",
      "교환사채",
      "주요사항보고서(교환사채권",
    ],
    news_keywords: [
      "SNT에너지 중동 수주",
      "SNT에너지 원전 플랜트",
      "SNT홀딩스 교환사채",
      "SNT홀딩스 EB",
      "SNT에너지 방산 수주",
    ],
  },

  // ───── 비에이치아이 (083650) ─────
  // research/083650.json exit_timing 6개 중 5개 자동화:
  // 1. 영업이익률 한자릿수 초반 후퇴 (≤ 7%, warn ≤ 10%)
  // 2. 수주 공시 공백 ≥ 90일 (3개월)
  // 3. 박은미 최대주주 지분 감소 (hyslrSttus)
  // 4. 우종인·박은미 매도 (insider_family_trades)
  // 5. 비에이치아이건설(01081622) 관련 공시 (외부법인 추적)
  // + 뉴스: 원전/발전 수주, 주식담보제공, 자금대여
  {
    code: "083650",
    name: "비에이치아이",
    corp_code: "00409788",
    triggers: [
      {
        id: "op_margin",
        label: "분기 영업이익률",
        source: "op_margin.op_margin_pct",
        threshold: { lte: 7 },
        threshold_label: "7% 이하",
        suffix: "%",
        precision: 1,
        warn_threshold: 10,
      },
      {
        id: "supply_gap",
        label: "수주 공백",
        source: "supply_gap.days_ago",
        threshold: { gte: 90 },
        threshold_label: "90일 경과",
        suffix: "일",
        warn_threshold: 60,
      },
      {
        id: "park_eun_mi_ratio",
        label: "박은미 지분 비율",
        source: "major_shareholder.end_ratio",
        threshold: { lte: 15 },
        threshold_label: "15% 이하로 감소",
        suffix: "%",
        precision: 2,
        warn_threshold: 16,
      },
      {
        id: "owner_sell_count",
        label: "오너 일가 매도 공시 (90일)",
        source: "insider_family_trades.trades.count",
        threshold: { gte: 1 },
        threshold_label: "매도 건수 1건+",
        suffix: "건",
      },
      {
        id: "owner_sell_shares",
        label: "오너 일가 누적 매도",
        source: "insider_family_trades.total_shares_sold",
        threshold: { gte: 500000 },
        threshold_label: "50만주 이상",
        suffix: "주",
        warn_threshold: 100000,
      },
      {
        id: "bhi_construction_disclosure",
        label: "비에이치아이건설 공시 (90일)",
        source: "external_corp_disclosures.count",
        threshold: { gte: 1 },
        threshold_label: "공시 1건+",
        suffix: "건",
      },
    ],
    major_shareholder_name: "박은미",
    family_member_names: ["우종인", "박은미", "이가현", "차미림"],
    external_corp_code: "01081622", // 비에이치아이건설 (비상장, 오너 가족회사)
    // 비상장사라 정기 감사보고서가 매년 3~4월 나옴 — 이건 매도 트리거 아님.
    // 매도 신호로 유의미한 공시만 필터: 주요사항보고서(자금대여·타법인출자·채무보증 등)
    external_corp_keywords: [
      "주요사항보고서",
      "금전대여",
      "자금대여",
      "타법인주식",
      "채무보증",
      "자산양수도",
      "자금지원",
    ],
    news_keywords: [
      "비에이치아이 원전 수주",
      "비에이치아이 HRSG",
      "우종인 주식담보",
      "비에이치아이건설 자금",
      "비에이치아이 블록딜",
      "비에이치아이 금전대여",
    ],
  },

  // ───── 하나금융지주 (086790) ─────
  // research/086790.json exit_timing 6개 트리거 자동화:
  // 1. PBR 1.0 돌파 + 4대 금융지주 평균 대비 프리미엄 (peer_pbr_premium)
  // 2. 분기배당 동결 (dividend_trend QoQ ≤ 0%) + 자사주 취득결정 후 90일 후속 부재
  // 3. 외국인 지분율 65% 이하 + 최근 20거래일 외국인 순매도 전환
  // 4. 분기 적자 전환 (quarterly_net_income ≤ 0)
  // 5. 자본 규제·주주환원 후퇴 — 뉴스 키워드
  // 6. 함영주 회장 사법 리스크 — 뉴스 키워드
  {
    code: "086790",
    name: "하나금융지주",
    corp_code: "00547583",
    triggers: [
      {
        id: "pbr",
        label: "PBR",
        source: "valuation.pbr",
        threshold: { gte: 1.0 },
        threshold_label: "1.0 돌파",
        suffix: "배",
        precision: 2,
        warn_threshold: 0.95,
      },
      {
        id: "pbr_premium_pp",
        label: "4대 지주 평균 대비 PBR 프리미엄",
        source: "peer_pbr_premium.premium_pp",
        threshold: { gte: 0.10 },
        threshold_label: "+0.10pp 이상",
        suffix: "pp",
        precision: 3,
        warn_threshold: 0.05,
      },
      {
        id: "foreign_ratio",
        label: "외국인 지분율",
        source: "valuation.foreign_ratio",
        threshold: { lte: 65 },
        threshold_label: "65% 이하",
        suffix: "%",
        precision: 2,
        warn_threshold: 66.5,
      },
      {
        id: "foreign_net_buy_4w",
        label: "최근 20거래일 외국인 순매수",
        source: "foreign_net_buy.cumulative_20d_shares",
        threshold: { lte: 0 },
        threshold_label: "순매도 전환",
        suffix: "주",
      },
      {
        id: "dividend_qoq_change",
        label: "분기배당 QoQ 변화율",
        source: "dividend_trend.qoq_change_pct",
        threshold: { lte: 0 },
        threshold_label: "동결 또는 감소",
        suffix: "%",
        precision: 1,
        warn_threshold: 1,
      },
      {
        // 자사주 매입 프로그램 종합 상태 — 취득결정·취득결과·소각결정 3종 통합 추적
        // days_ago는 마지막 활동(어떤 종류든) 기준 경과일이라 단순 '취득결정 90일'보다 정밀.
        // 매입은 보통 2~3개월 진행되므로 취득결과보고서가 그 후 30~60일 내 정상 후속.
        // → 마지막 활동 후 180일+면 프로그램 사실상 중단(abandoned)으로 매도 신호.
        id: "buyback_program_status",
        label: "자사주 프로그램 마지막 활동 후 경과일",
        source: "buyback_program_status.days_ago",
        threshold: { gte: 180 },
        threshold_label: "180일+ (프로그램 중단)",
        suffix: "일",
        warn_threshold: 90,
      },
      {
        id: "quarterly_net_income",
        label: "최근 분기 순이익",
        source: "quarterly_net_income.net_income_billion",
        threshold: { lte: 0 },
        threshold_label: "분기 적자 전환",
        suffix: "억",
        precision: 0,
        warn_threshold: 5000,
      },
      {
        // PF 손실·충당금 등 자사 직접 공시 — 뉴스보다 한 단계 더 강한 신호
        id: "pf_loss_disclosure",
        label: "PF 손실·충당금 공시 (90일)",
        source: "disclosure_keyword_hits.groups.pf_loss.hits.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
      },
      {
        // 주주환원 정책 변경·축소 등 자사 직접 공시
        id: "shareholder_policy_disclosure",
        label: "주주환원 정책 변경 공시 (90일)",
        source: "disclosure_keyword_hits.groups.policy_change.hits.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
      },
    ],
    peer_codes: ["105560", "055550", "316140"], // KB금융, 신한지주, 우리금융지주
    disclosure_keyword_groups: [
      {
        // 은행지주 PF 손실: report_nm에 노출되는 키워드 — 손상차손은 자율 공시이거나
        // 분기보고서 본문에서만 잡히므로 여기서는 주요사항보고서 수준 키워드만.
        name: "pf_loss",
        label: "PF 손실·충당금",
        keywords: [
          "충당금 적립",
          "대규모 손실",
          "손상차손 인식",
          "부동산 PF",
          "프로젝트금융",
        ],
      },
      {
        // 주주환원 정책 변경/철회: 단순 결정 공시는 긍정·부정 모두 가능하지만
        // 키워드 자체로 변경 사실은 잡힘 → 사용자가 매뉴얼 검토.
        name: "policy_change",
        label: "주주환원 정책 변경",
        keywords: [
          "주주환원 정책 변경",
          "배당정책 변경",
          "기업가치 제고 계획 변경",
          "기업가치 제고계획 변경",
          "자기주식취득 철회",
          "자기주식취득결정 취소",
        ],
      },
    ],
    news_keywords: [
      "하나금융 분기배당",
      "하나금융 자사주",
      "하나금융 주주환원",
      "금융당국 자본규제",
      "은행 주주환원 후퇴",
      "함영주 회장",
      "하나은행 사법",
    ],
  },

  // ───── KB금융지주 (105560) ─────
  // research/105560.json exit_timing 6개 자동화 매핑:
  // 1. PBR 1.1 돌파 + 4대 금융지주 평균 대비 프리미엄 (peer_pbr_premium)
  // 2. 그룹 NIM 1.7% / 은행 NIM 1.6% 이탈 — V2 net_interest_margin (본문 정규식 추출)
  // 3. NPL 0.5% / CCR 0.20% 진입 — V2 npl_ratio (본문 정규식 추출)
  // 4. 자사주 소각 정책 중단 (365일 후속 부재) + 분기배당 동결·삭감 (QoQ ≤ 0%)
  // 5. 분기 ROE 10% 미만 — V2 roe (자기자본+분기순이익 표준필드 → 연환산)
  // 6. 국민연금 지분 처분 — bank_corp_disclosures (KB국민은행 5% 변동 보고) + 뉴스 키워드
  {
    code: "105560",
    name: "KB금융",
    corp_code: "00688996",      // KB금융지주 (DART) — 첫 dry-run에서 회사명 일치 검증
    bank_corp_code: "00103403", // KB국민은행 (자회사 NIM 보강·5% 변동 추적) — 첫 dry-run 검증
    triggers: [
      // 1차 metric 7개 (하나금융 패턴 차용)
      {
        id: "pbr",
        label: "PBR",
        source: "valuation.pbr",
        threshold: { gte: 1.1 },
        threshold_label: "1.1배 돌파",
        suffix: "배",
        precision: 2,
        warn_threshold: 1.05,
      },
      {
        // 임계 0.20pp — KB는 4대 금융지주 1등주로 자연스러운 +0.15~0.25pp 프리미엄을 가진다.
        // 첫 dry-run(2026-04-25) +0.247pp는 정상 상태. +0.20 돌파는 "1등 프리미엄도 과도한 구간"
        // (=PBR 1배 돌파 가까이) 신호로 사용.
        id: "pbr_premium_pp",
        label: "4대 지주 평균 대비 PBR 프리미엄",
        source: "peer_pbr_premium.premium_pp",
        threshold: { gte: 0.20 },
        threshold_label: "+0.20pp 이상",
        suffix: "pp",
        precision: 3,
        warn_threshold: 0.15,
      },
      {
        id: "foreign_ratio",
        label: "외국인 지분율",
        source: "valuation.foreign_ratio",
        threshold: { lte: 70 },
        threshold_label: "70% 이하",
        suffix: "%",
        precision: 2,
        warn_threshold: 72,
      },
      {
        id: "foreign_net_buy_4w",
        label: "최근 20거래일 외국인 순매수",
        source: "foreign_net_buy.cumulative_20d_shares",
        threshold: { lte: 0 },
        threshold_label: "순매도 전환",
        suffix: "주",
      },
      {
        id: "dividend_qoq_change",
        label: "분기배당 QoQ 변화율",
        source: "dividend_trend.qoq_change_pct",
        threshold: { lte: 0 },
        threshold_label: "동결 또는 감소",
        suffix: "%",
        precision: 1,
      },
      {
        id: "buyback_cancellation_gap",
        label: "자사주 소각결정 후 경과일",
        source: "buyback_cancellation_gap.days_ago",
        threshold: { gte: 365 },
        threshold_label: "365일 후속 부재",
        suffix: "일",
        warn_threshold: 270,
      },
      {
        id: "quarterly_net_income",
        label: "최근 분기 순이익",
        source: "quarterly_net_income.net_income_billion",
        threshold: { lte: 13000 },
        threshold_label: "1.3조 이하 (Q1’26 1.89조 대비 -30%)",
        suffix: "억",
        precision: 0,
        warn_threshold: 15000,
      },
      // V2 metric 3개 (금융사 특화 지표 — 신규 collector)
      // silent_alert: 본문 정규식 추출의 정확도 검증 전이므로 metric만 표시.
      //
      // 활성화 검증 체크포인트 (2026-05 중순 1Q26 분기보고서 제출 후):
      //   1. monitor JSON의 group_nim ≈ 1.99% (KB IR 보도자료 1.99% 일치)
      //   2. monitor JSON의 npl_ratio ≈ 0.34% (1Q26 잠정 0.34% 일치)
      //   3. monitor JSON의 quarterly_roe ≈ 13.94% (1Q26 IR 13.94% 일치)
      //   3개 모두 ±0.1%p 이내 일치 시 silent_alert 제거하여 alert 활성화.
      {
        id: "group_nim",
        label: "그룹 NIM",
        source: "net_interest_margin.group_nim_pct",
        threshold: { lte: 1.7 },
        threshold_label: "1.7% 이하",
        suffix: "%",
        precision: 2,
        warn_threshold: 1.85,
        silent_alert: true,
      },
      {
        id: "npl_ratio",
        label: "NPL 비율",
        source: "npl_ratio.npl_ratio_pct",
        threshold: { gte: 0.5 },
        threshold_label: "0.5% 돌파",
        suffix: "%",
        precision: 2,
        warn_threshold: 0.45,
        silent_alert: true,
      },
      {
        id: "quarterly_roe",
        label: "ROE (사업보고서 기준 연환산)",
        source: "roe.annualized_roe_pct",
        threshold: { lte: 10 },
        threshold_label: "10% 이하",
        suffix: "%",
        precision: 2,
        warn_threshold: 12,
        silent_alert: true,
      },
      // bank_corp_disclosures는 metric화하지 않고 sources/news 영역에만 노출
      // (단순 카운트로 매도 신호 단정 불가 — 보고사유 분류 필요. 후속 plan에서 별도 metric화)
    ],
    peer_codes: ["055550", "086790", "316140"], // 신한지주·하나금융·우리금융 (KB 자기 제외)
    // major_shareholder_name 미설정 — KB는 1대주주 부재 분산구조 (국민연금 5%대)
    news_keywords: [
      "KB금융 자사주 소각",
      "KB금융 분기배당",
      "KB금융 NIM 압축",
      "KB금융 부동산 PF 부실",
      "KB금융 충당금 적립",
      "국민연금 KB금융 지분 매각",
      "한국은행 기준금리 인하",
    ],
  },

  // ───── 현대차2우B (005387) ─────
  // research/005387.json exit_timing 6개 중 5개 자동화:
  // 1. 부분익절 ① — 가격 320,000 돌파 + PER 9배 (price + per 트리거)
  // 2. 부분익절 ③ — 보통주-우선주 괴리율 30% 이하 (pref_discount, 신규 collector)
  // 3. 전량매도 ① — 자사주 소각 공시 1년 부재 (buyback_cancellation_gap, 보통주 005380 corp_code 기준)
  // 4. 전량매도 ② — 분기 영업이익률 4% 미만 (op_margin)
  // 5. 뉴스: 트럼프 관세·우선주 차별·지배구조 개편
  // (부분익절 ② DPS 추가 감소는 분기배당 도입 첫해라 baseline 부족 — 2027년 봄 결산 후 dividend_trend 트리거 추가 검토)
  // (전량매도 ③ 지배구조 개편 시 우선주 차별은 정성 판단 영역 — 뉴스 키워드만 추적)
  {
    code: "005387",
    name: "현대차2우B",
    corp_code: "00164742",        // 현대자동차 (보통주 발행회사 corp_code)
    common_stock_code: "005380",  // 보통주 종목코드 (괴리율 collector용)
    triggers: [
      {
        id: "price",
        label: "우선주 종가",
        source: "valuation.price",
        threshold: { gte: 320000 },
        threshold_label: "320,000원 돌파",
        suffix: "원",
        warn_threshold: 290000,
      },
      {
        id: "per",
        label: "PER",
        source: "valuation.per",
        threshold: { gte: 9 },
        threshold_label: "9배 돌파",
        suffix: "배",
        precision: 2,
        warn_threshold: 8,
      },
      {
        id: "pref_discount",
        label: "보통주 대비 디스카운트",
        source: "pref_discount.discount_pct",
        threshold: { lte: 30 },
        threshold_label: "30% 이하로 축소",
        suffix: "%",
        precision: 1,
        warn_threshold: 35,
      },
      {
        id: "buyback_gap",
        label: "자사주 소각 공시 공백",
        source: "buyback_cancellation_gap.days_ago",
        threshold: { gte: 365 },
        threshold_label: "365일 경과",
        suffix: "일",
        warn_threshold: 270,
      },
      {
        id: "op_margin",
        label: "분기 영업이익률",
        source: "op_margin.op_margin_pct",
        threshold: { lte: 4 },
        threshold_label: "4% 미만",
        suffix: "%",
        precision: 1,
        warn_threshold: 7,
      },
    ],
    news_keywords: [
      "트럼프 자동차 관세",
      "현대차 미국 관세",
      "현대차 멕시코 공장",
      "현대모비스 분할",
      "현대차 지배구조 개편",
      "현대차 우선주 차별",
      "현대차 자사주 소각",
    ],
  },

  // ───── GS (078930) ─────
  // research/078930.json exit_timing 6개 중 5개 자동화 + 자사주 취득 긍정 신호:
  // 1. PER ≥ 10배 (지주사 디스카운트 정상화)
  // 2. 배당수익률 ≤ 3.5% (밸류업 가이던스 4%대 이탈 신호)
  // 3. 주가 85,000원+ (52주 고점 83,000 돌파 익절 영역)
  // 4. 별도 분기 순이익 적자 전환 (지주사 자체 배당 여력 압박, separate_quarterly_income)
  // 5. 자회사 채무보증결정 공시 (debt_guarantee_events, 90일) — v1은 카운트 감지, v2에서 자본 5% 정밀 계산
  // 6. 자사주 취득결정 공시 (긍정 시그널 — PBR 0.49 디스카운트 해소 기대, tone_on_hit="good")
  // 7. 두바이유 70달러 이하 (Brent 7일 평균 대용 — 두바이유 직접 무료 일별 API 부재로 Brent ±2달러 swing 근사)
  // 정제마진 5달러는 무료 API 부재 — 뉴스 키워드만 (싱가포르 복합정제마진·GS칼텍스 정제마진·크랙 스프레드)
  {
    code: "078930",
    name: "GS",
    corp_code: "00500254",
    triggers: [
      {
        id: "per",
        label: "PER",
        source: "valuation.per",
        threshold: { gte: 10 },
        threshold_label: "10배 돌파",
        suffix: "배",
        precision: 2,
        warn_threshold: 9.5,
      },
      {
        id: "dividend_yield",
        label: "배당수익률",
        source: "valuation.dividend_yield",
        threshold: { lte: 3.5 },
        threshold_label: "3.5% 이하",
        suffix: "%",
        precision: 2,
        warn_threshold: 3.7,
      },
      {
        id: "price_high",
        label: "주가",
        source: "valuation.price",
        threshold: { gte: 85000 },
        threshold_label: "85,000원+ 돌파",
        suffix: "원",
        precision: 0,
        warn_threshold: 82000,
      },
      {
        id: "separate_net_loss",
        label: "별도 분기 순이익",
        source: "separate_quarterly_income.net_income_billion",
        threshold: { lte: 0 },
        threshold_label: "적자 전환",
        suffix: "억",
        precision: 0,
        warn_threshold: 500,
      },
      {
        id: "debt_guarantee_count",
        label: "자회사 채무보증결정 공시 (90일)",
        source: "debt_guarantee_events.count",
        threshold: { gte: 1 },
        threshold_label: "공시 1건+",
        suffix: "건",
      },
      {
        // 긍정 시그널 트리거 — hit이면 "good"(매수 보강), miss이면 "neutral"(현 상태 유지, 약점 미해소).
        // 다른 매도 트리거는 miss=good(안전)이지만 이건 정책 부재가 GS의 약점이므로 의미가 다름.
        id: "buyback_acquisition",
        label: "자사주 취득결정 공시 (90일·긍정)",
        source: "stock_buyback_events.count",
        threshold: { gte: 1 },
        threshold_label: "공시 1건+ (재평가 신호)",
        suffix: "건",
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "oil_price_brent",
        label: "Brent 7일 평균 (두바이유 대용)",
        source: "crude_oil_price.avg_7d",
        threshold: { lte: 70 },
        threshold_label: "70달러 이하 (정유 매크로 약화)",
        suffix: "$",
        precision: 2,
        warn_threshold: 78,
      },
    ],
    news_keywords: [
      "두바이유 70달러",
      "두바이유 하락",
      "정제마진 하락",
      "싱가포르 복합정제마진",
      "GS칼텍스 정제마진",
      "GS칼텍스 적자",
      "크랙 스프레드 하락",
      "이란 미국 합의",
      "중동 긴장 완화",
      "GS 자사주 매입",
      "GS 자사주 소각",
      "GS 배당성향",
    ],
  },

  // ───── 디앤디파마텍 (347850) ─────
  // research/347850.json exit_timing 3개 트리거 자동화 + 자본구조·밸류에이션 보강:
  // 1. 48주 1차 평가변수 미달 — DART 공시 부재라 뉴스 RSS + ClinicalTrials.gov status 변경으로 간접 감지
  // 2. 안전성 중대 이상반응 — 동일 (뉴스 RSS만)
  // 3. ORALINK 라이선스 축소·반환 — 디앤디 자체 capital_issuance 공시 + Pfizer/Metsera 뉴스
  // + 자본구조: PBR 50배(극고평가), CEO 지분 10%(경영권), 신규 자본조달, 분기 영업이익률(적자 폭 악화)
  // (Metsera는 미국 법인 — DART corp_code 부재로 external_corp_disclosures 미적용)
  {
    code: "347850",
    name: "디앤디파마텍",
    corp_code: "01376715",
    triggers: [
      {
        id: "pbr",
        label: "PBR (극고평가)",
        source: "valuation.pbr",
        threshold: { gte: 50 },
        threshold_label: "50배 돌파",
        suffix: "배",
        precision: 2,
        warn_threshold: 45,
      },
      {
        id: "ceo_founder_ratio",
        label: "이슬기 CEO 지분 비율",
        source: "major_shareholder.end_ratio",
        threshold: { lte: 10 },
        threshold_label: "10% 이하로 감소",
        suffix: "%",
        precision: 2,
        warn_threshold: 11,
      },
      {
        id: "capital_issuance",
        label: "신규 자본조달 (CB/BW/EB/유증) 90일",
        source: "capital_issuance.count",
        threshold: { gte: 1 },
        threshold_label: "발행 공시 1건+",
        suffix: "건",
      },
      {
        // 매출 0에 가까운 적자 바이오라 op_margin_pct는 항상 -수백% 수준.
        // 매도 신호보다 '정보 표시'에 가까움 → tone_on_miss: neutral로 항시 정보용.
        // 매출이 정말 크게 줄어 -2000% 아래로 가면 그때만 bad.
        id: "op_margin",
        label: "분기 영업이익률 (정보용)",
        source: "op_margin.op_margin_pct",
        threshold: { lte: -2000 },
        threshold_label: "-2000% 이하 악화 (이례적)",
        suffix: "%",
        precision: 1,
        warn_threshold: -1500,
        tone_on_miss: "neutral",
      },
      {
        id: "clinical_status_change",
        label: "임상 단계 status 변경 (30일)",
        source: "clinical_pipeline.recent_changes_30d.count",
        threshold: { gte: 1 },
        threshold_label: "status 변경 1건+",
        suffix: "건",
      },
    ],
    major_shareholder_name: "이슬기",
    clinical_sponsor_keywords: ["D&D Pharmatech", "Neuraly"],
    news_keywords: [
      "디앤디파마텍 DD01 48주",       // 핵심 카탈리스트 (2026.05~06)
      "디앤디파마텍 DD01 임상",
      "디앤디파마텍 FDA",
      "디앤디파마텍 Pfizer",
      "디앤디파마텍 라이선스",
      "ORALINK 라이선스",
      "Metsera Pfizer 통합",
    ],
  },
];
