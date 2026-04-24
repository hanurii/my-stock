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
];
