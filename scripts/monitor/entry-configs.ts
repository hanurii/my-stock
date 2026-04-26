/**
 * 매수 트리거 자동 모니터 — 종목별 설정
 *
 * monitor-entry.ts가 ENTRY_CONFIGS를 순회하며 collector 호출 →
 * public/data/research/monitor_entry/{code}.json 저장.
 *
 * ## 설계 원칙 (2026-04-26 사용자 요청 반영)
 * 가격 절대치 트리거 → 의사결정 핵심이 아님. 대신 두 카테고리로 명확화:
 *
 *   ❌ 매수 보류 신호 (tone_on_hit: "bad")
 *      - 신규 CB/BW/유증 (희석 시작)
 *      - 분기 영업적자 (펀더멘털 훼손)
 *      - 분기 OPM 큰 폭 후퇴 (수익성 약화)
 *      → 한 건이라도 hit 시 진입 보류
 *
 *   ✅ 매수 시그널 (tone_on_hit: "good")
 *      - 분기 OPM 임계 유지 (펀더멘털 견조)
 *      - PER 본격 저평가 도달 (valuation 매력)
 *      - 자사주 매입·소각 결정 (주주환원 강화)
 *      - 신규 대형 수주 / 오버행 해소 공시
 *      → 다수 hit 시 분할 진입 검토
 *
 * news_keywords는 호재 명시 phrase만 (feedback_monitor_news_keywords 정책 매수 버전).
 */
import type { MonitorConfig } from "./types";

export const ENTRY_CONFIGS: MonitorConfig[] = [
  // ───── 동아엘텍 (088130) — interested ─────
  // research/088130.json: 모회사 자본구조 깨끗 + OLED 8.6세대 사이클.
  // 핵심 보류 신호: 통화선물 청산손실 3회차 누적, 자회사 CB/EB Put 부담.
  // 핵심 진입 신호: 모회사 본체 신규 희석 0건 유지 + OPM 견조.
  {
    code: "088130",
    name: "동아엘텍",
    corp_code: "00489243",
    purpose: "entry",
    triggers: [
      // ❌ 매수 보류
      {
        id: "no_capital_issuance",
        label: "❌ 신규 자본조달 공시 (CB/BW/유증, 90일)",
        source: "capital_issuance.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
        tone_on_hit: "bad",
        tone_on_miss: "good",
      },
      {
        id: "op_margin_collapse",
        label: "❌ 분기 영업이익률 후퇴",
        source: "op_margin.op_margin_pct",
        threshold: { lte: 12 },
        threshold_label: "12% 이하",
        suffix: "%",
        precision: 1,
        warn_threshold: 14,
        tone_on_hit: "bad",
        tone_on_miss: "good",
      },
      // ✅ 매수 시그널
      {
        id: "op_margin_strong",
        label: "✅ 분기 영업이익률 견조",
        source: "op_margin.op_margin_pct",
        threshold: { gte: 18 },
        threshold_label: "18% 이상",
        suffix: "%",
        precision: 1,
        warn_threshold: 16,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "per_value_zone",
        label: "✅ PER 본격 저평가",
        source: "valuation.per",
        threshold: { lte: 3.5 },
        threshold_label: "3.5배 이하",
        suffix: "배",
        precision: 2,
        warn_threshold: 4.0,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "buyback_action",
        label: "✅ 자사주 매입·소각 신규 (90일)",
        source: "stock_buyback_events.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "selik_overhang_release",
        label: "✅ 선익시스템 CB/EB 만기전 매입·말소",
        source: "external_corp_disclosures.count",
        threshold: { gte: 1 },
        threshold_label: "공시 1건+",
        suffix: "건",
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
    ],
    external_corp_code: "00136218", // 선익시스템
    external_corp_keywords: [
      "사채권 만기 전 취득",
      "사채권만기전취득",
      "전환사채권",
      "교환사채권",
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
  // research/265560.json: 현대차 7년 1,985억 수주 + CB 잔액 0원.
  // 핵심 보류 신호: 단일고객 의존 72.6% / 대형 계약 해지 패턴 (2024 KG·2025 포스코인터).
  // 핵심 진입 신호: OPM 견조 + 신규 글로벌 OEM 수주 + 자사주 소각(처분 아닌).
  {
    code: "265560",
    name: "영화테크",
    corp_code: "00659976",
    purpose: "entry",
    triggers: [
      // ❌ 매수 보류
      {
        id: "no_capital_issuance",
        label: "❌ 신규 자본조달 공시 (CB/BW/유증, 90일)",
        source: "capital_issuance.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
        tone_on_hit: "bad",
        tone_on_miss: "good",
      },
      {
        id: "op_margin_collapse",
        label: "❌ 분기 영업이익률 후퇴",
        source: "op_margin.op_margin_pct",
        threshold: { lte: 10 },
        threshold_label: "10% 이하",
        suffix: "%",
        precision: 1,
        warn_threshold: 12,
        tone_on_hit: "bad",
        tone_on_miss: "good",
      },
      // ✅ 매수 시그널
      {
        id: "op_margin_strong",
        label: "✅ 분기 영업이익률 견조",
        source: "op_margin.op_margin_pct",
        threshold: { gte: 16 },
        threshold_label: "16% 이상",
        suffix: "%",
        precision: 1,
        warn_threshold: 14,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "per_value_zone",
        label: "✅ PER 저평가",
        source: "valuation.per",
        threshold: { lte: 5.0 },
        threshold_label: "5.0배 이하",
        suffix: "배",
        precision: 2,
        warn_threshold: 5.5,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "new_supply_contract",
        label: "✅ 신규 단일판매·공급계약",
        source: "supply_gap.days_ago",
        threshold: { lte: 7 },
        threshold_label: "최근 7일 내 신규",
        suffix: "일 전",
        warn_threshold: 30,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "buyback_action",
        label: "✅ 자사주 매입·소각 신규 (90일)",
        source: "stock_buyback_events.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
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
  // research/046940.json: 5년간 희석 0건 + PER 2.03 + GTX-B 수주.
  // 핵심 보류 신호: 사업보고서 정정 노이즈 + 건설업 OPM 변동성 (2024 0.93% → 2025 17.85%).
  // 핵심 진입 신호: 정정본 발표 후 펀더멘털 재확인 + OPM 지속.
  {
    code: "046940",
    name: "우원개발",
    corp_code: "00363246",
    purpose: "entry",
    triggers: [
      // ❌ 매수 보류
      {
        id: "no_capital_issuance",
        label: "❌ 신규 자본조달 공시 (CB/BW/유증, 90일)",
        source: "capital_issuance.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
        tone_on_hit: "bad",
        tone_on_miss: "good",
      },
      {
        id: "op_margin_collapse",
        label: "❌ 분기 영업이익률 급락 (일회성 검증)",
        source: "op_margin.op_margin_pct",
        threshold: { lte: 5 },
        threshold_label: "5% 이하 (2024 0.93% 회귀)",
        suffix: "%",
        precision: 1,
        warn_threshold: 8,
        tone_on_hit: "bad",
        tone_on_miss: "good",
      },
      // ✅ 매수 시그널
      {
        id: "op_margin_sustained",
        label: "✅ 분기 영업이익률 지속",
        source: "op_margin.op_margin_pct",
        threshold: { gte: 12 },
        threshold_label: "12% 이상",
        suffix: "%",
        precision: 1,
        warn_threshold: 10,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "per_value_zone",
        label: "✅ PER 추가 저평가",
        source: "valuation.per",
        threshold: { lte: 1.8 },
        threshold_label: "1.8배 이하 (현 2.03배)",
        suffix: "배",
        precision: 2,
        warn_threshold: 2.0,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "new_supply_contract",
        label: "✅ 신규 SOC 수주 공시",
        source: "supply_gap.days_ago",
        threshold: { lte: 7 },
        threshold_label: "최근 7일 내 신규",
        suffix: "일 전",
        warn_threshold: 30,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "correction_disclosure",
        label: "✅ 사업보고서 정정 공시 (노이즈 해소)",
        source: "disclosure_keyword_hits.groups.correction.hits.count",
        threshold: { gte: 1 },
        threshold_label: "정정본 1건+",
        suffix: "건",
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
  // research/099410.json: 조선 슈퍼사이클 + CB/BW/EB 0건 + OPM 22%.
  // 핵심 보류 신호: 2021 관리종목 이력 종목이라 분기 적자 1회만으로도 즉각 보류.
  // 핵심 진입 신호: OPM 견조 지속 + 자사주 매입·소각 정책 도입 (현재 0).
  {
    code: "099410",
    name: "동방선기",
    corp_code: "00526678",
    purpose: "entry",
    triggers: [
      // ❌ 매수 보류
      {
        id: "no_capital_issuance",
        label: "❌ 신규 자본조달 공시 (CB/BW/유증, 90일)",
        source: "capital_issuance.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
        tone_on_hit: "bad",
        tone_on_miss: "good",
      },
      {
        id: "op_margin_collapse",
        label: "❌ 분기 영업이익률 급락 (관리종목 이력)",
        source: "op_margin.op_margin_pct",
        threshold: { lte: 12 },
        threshold_label: "12% 이하",
        suffix: "%",
        precision: 1,
        warn_threshold: 15,
        tone_on_hit: "bad",
        tone_on_miss: "good",
      },
      // ✅ 매수 시그널
      {
        id: "op_margin_strong",
        label: "✅ 분기 영업이익률 견조",
        source: "op_margin.op_margin_pct",
        threshold: { gte: 18 },
        threshold_label: "18% 이상",
        suffix: "%",
        precision: 1,
        warn_threshold: 16,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "per_value_zone",
        label: "✅ PER 저평가",
        source: "valuation.per",
        threshold: { lte: 8.0 },
        threshold_label: "8.0배 이하 (현 9.67배)",
        suffix: "배",
        precision: 2,
        warn_threshold: 9.0,
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "buyback_action",
        label: "✅ 자사주 매입·소각 신규 (주주환원 정책 도입)",
        source: "stock_buyback_events.count",
        threshold: { gte: 1 },
        threshold_label: "1건 이상",
        suffix: "건",
        tone_on_hit: "good",
        tone_on_miss: "neutral",
      },
      {
        id: "new_supply_contract",
        label: "✅ 신규 단일판매·공급계약",
        source: "supply_gap.days_ago",
        threshold: { lte: 7 },
        threshold_label: "최근 7일 내 신규",
        suffix: "일 전",
        warn_threshold: 30,
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
