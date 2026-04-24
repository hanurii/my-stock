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
        // 사용자 trigger 원문은 '1% 초과'였으나 SK에코플랜트(EPC, M16·M18 메모리 공장 건설사)
        // 정상 거래만으로 2025년 약 4.84조(5.575%) 발생. 임계 7%로 상향해 EPC 정상 거래는 통과,
        // SK이노/SK㈜ 운영비 급증·신규 우회 거래 등 +1.3%p 이상 변동 시에만 신호.
        // 추후 '전년 대비 증가율' 메트릭 보강 예정.
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
        id: "sk_square_disposal",
        label: "SK스퀘어 처분·매각 공시 (90일)",
        source: "external_corp_disclosures.count",
        threshold: { gte: 1 },
        threshold_label: "처분 공시 1건+",
        suffix: "건",
      },
    ],
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
];
