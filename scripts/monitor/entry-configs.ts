/**
 * 매수 트리거 자동 모니터 — 종목별 설정
 *
 * monitor-entry.ts가 ENTRY_CONFIGS를 순회하며 collector 호출 →
 * public/data/research/monitor_entry/{code}.json 저장.
 *
 * 트리거 정의·임계값은 각 종목 research/{code}.json execution_plan.steps[*].trigger와 일치시킨다.
 *
 * tone_on_hit: "good" — 진입 조건 충족 시 매수 시그널(녹색).
 * tone_on_miss: "neutral" — 미충족 시 관망(회색). 일반 매도 트리거의 기본 "good"과 다름.
 *
 * news_keywords는 호재 명시 phrase만 (feedback_monitor_news_keywords 정책 준수).
 */
import type { MonitorConfig } from "./types";

export const ENTRY_CONFIGS: MonitorConfig[] = [
  // ───── 동아엘텍 (088130) — interested ─────
  // research/088130.json execution_plan 3단계 트리거 자동화:
  // 1차: 가격 -10% 조정 (현 11,250원 → 10,125원 부근)
  // 2차: 선익시스템(corp_code 00136218) CB·EB Put Option 행사 공시 (2026.06.21~)
  // 3차: 분기 OPM ≥ 18% 유지
  {
    code: "088130",
    name: "동아엘텍",
    corp_code: "00489243",
    purpose: "entry",
    triggers: [
      {
        id: "entry_drawdown_10pct",
        label: "진입 가격 (현 11,250원 -10%)",
        source: "valuation.price",
        threshold: { lte: 10125 },
        threshold_label: "10,125원 이하",
        suffix: "원",
        precision: 0,
        warn_threshold: 10688, // -5% (현 -5%~-10% 구간 warn)
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "selik_cb_put_disclosure",
        label: "선익시스템 CB/EB 매매·말소 공시 (90일)",
        source: "external_corp_disclosures.count",
        threshold: { gte: 1 },
        threshold_label: "공시 1건+",
        suffix: "건",
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "q1_op_margin_18",
        label: "분기 영업이익률",
        source: "op_margin.op_margin_pct",
        threshold: { gte: 18 },
        threshold_label: "18% 이상 유지",
        suffix: "%",
        precision: 1,
        warn_threshold: 16,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
    ],
    // 선익시스템 corp_code: 00136218 (코스닥 171090)
    external_corp_code: "00136218",
    external_corp_keywords: [
      "전환사채권",
      "교환사채권",
      "사채권 만기 전 취득",
      "사채권만기전취득",
    ],
    news_keywords: [
      "동아엘텍 OLED 수주",
      "선익시스템 OLED 수주",
      "동아엘텍 자사주 소각",
      "동아엘텍 실적 호조",
      "OLED 8.6세대 양산",
    ],
  },

  // ───── 영화테크 (265560) — interested ─────
  // research/265560.json execution_plan 3단계:
  // 1차: 가격 -7% (현 10,200원 → 9,486원)
  // 2차: 1Q OPM ≥ 16% + 신규 수주 공시
  // 3차: (단일 고객 다변화는 자동화 불가, 신규 수주만 추적)
  {
    code: "265560",
    name: "영화테크",
    corp_code: "00659976",
    purpose: "entry",
    triggers: [
      {
        id: "entry_drawdown_7pct",
        label: "진입 가격 (현 10,200원 -7%)",
        source: "valuation.price",
        threshold: { lte: 9486 },
        threshold_label: "9,486원 이하",
        suffix: "원",
        precision: 0,
        warn_threshold: 9690, // -5%
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "q1_op_margin_16",
        label: "분기 영업이익률",
        source: "op_margin.op_margin_pct",
        threshold: { gte: 16 },
        threshold_label: "16% 이상 유지",
        suffix: "%",
        precision: 1,
        warn_threshold: 14,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "new_supply_contract",
        label: "신규 단일판매·공급계약",
        source: "supply_gap.days_ago",
        threshold: { lte: 7 }, // 최근 7일 내 신규 수주
        threshold_label: "최근 7일 내 신규 공시",
        suffix: "일 전",
        warn_threshold: 30,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
    ],
    news_keywords: [
      "영화테크 현대차 수주",
      "영화테크 PCDU 양산",
      "영화테크 신규 수주",
      "영화테크 실적 호조",
      "현대차 PCDU 공급",
    ],
  },

  // ───── 우원개발 (046940) — interested ─────
  // research/046940.json execution_plan 3단계:
  // 1차: 가격 -10% (현 5,400원 → 4,860원)
  // 2차: 사업보고서 정정본 발표 (한국거래소 정정요구 진행 중)
  // 3차: 1Q OPM ≥ 12% + 신규 SOC 수주
  {
    code: "046940",
    name: "우원개발",
    corp_code: "00400485",
    purpose: "entry",
    triggers: [
      {
        id: "entry_drawdown_10pct",
        label: "진입 가격 (현 5,400원 -10%)",
        source: "valuation.price",
        threshold: { lte: 4860 },
        threshold_label: "4,860원 이하",
        suffix: "원",
        precision: 0,
        warn_threshold: 5130, // -5%
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "correction_disclosure",
        label: "사업보고서 정정 공시 (90일)",
        source: "disclosure_keyword_hits.groups.correction.hits.count",
        threshold: { gte: 1 },
        threshold_label: "정정본 1건+",
        suffix: "건",
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "q1_op_margin_12",
        label: "분기 영업이익률",
        source: "op_margin.op_margin_pct",
        threshold: { gte: 12 },
        threshold_label: "12% 이상 유지",
        suffix: "%",
        precision: 1,
        warn_threshold: 10,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "new_supply_contract",
        label: "신규 단일판매·공급계약 (SOC 수주)",
        source: "supply_gap.days_ago",
        threshold: { lte: 7 },
        threshold_label: "최근 7일 내 신규 공시",
        suffix: "일 전",
        warn_threshold: 30,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
    ],
    disclosure_keyword_groups: [
      {
        name: "correction",
        label: "사업보고서 정정",
        keywords: ["사업보고서 [기재정정]", "사업보고서[기재정정]", "기재정정"],
      },
    ],
    news_keywords: [
      "우원개발 GTX",
      "우원개발 신규 수주",
      "우원개발 SOC",
      "우원개발 실적 호조",
    ],
  },

  // ───── 동방선기 (099410) — interested ─────
  // research/099410.json execution_plan 3단계:
  // 1차: 가격 -10% (현 5,490원 → 4,941원)
  // 2차: 1Q OPM ≥ 18% 유지
  // 3차: 자사주 매입·소각 결정 공시 (주주환원 정책 도입)
  {
    code: "099410",
    name: "동방선기",
    corp_code: "00526678",
    purpose: "entry",
    triggers: [
      {
        id: "entry_drawdown_10pct",
        label: "진입 가격 (현 5,490원 -10%)",
        source: "valuation.price",
        threshold: { lte: 4941 },
        threshold_label: "4,941원 이하",
        suffix: "원",
        precision: 0,
        warn_threshold: 5216, // -5%
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "q1_op_margin_18",
        label: "분기 영업이익률",
        source: "op_margin.op_margin_pct",
        threshold: { gte: 18 },
        threshold_label: "18% 이상 유지",
        suffix: "%",
        precision: 1,
        warn_threshold: 16,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "buyback_announcement",
        label: "자사주 매입·소각 공시 (90일)",
        source: "stock_buyback_events.count",
        threshold: { gte: 1 },
        threshold_label: "공시 1건+",
        suffix: "건",
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
    ],
    news_keywords: [
      "동방선기 신규 수주",
      "동방선기 자사주",
      "동방선기 실적 호조",
      "조선 슈퍼사이클",
    ],
  },
];
