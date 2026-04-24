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
  // 주의: '최대주주 지분 변동'은 일반 5% 대주주(BlackRock 등) 공시까지 포함되어 false-positive 잦음.
  // SK스퀘어 보유분 직접 추적은 hyslrSttus API 분기 갱신만 가능 → 분기보고서 시즌에만 의미.
  // 1차 버전은 정량 트리거 2개 + 뉴스 키워드만 운영.
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
    ],
    news_keywords: [
      "삼성 HBM3E 엔비디아 공급",
      "DRAM 가격 하락",
      "엔비디아 Capex 감소",
    ],
  },
];
