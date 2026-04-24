/**
 * 매도 트리거 자동 모니터 — 공통 타입
 */

export type Tone = "good" | "warn" | "bad" | "neutral";

/** 단일 트리거 정의 (configs.ts에서 종목별로 사용) */
export interface TriggerDef {
  /** 메트릭 ID (UI에서 key) */
  id: string;
  /** 사용자에게 표시될 라벨 — `{year}` 같은 토큰 치환 가능 */
  label: string;
  /** 어떤 collector 결과에서 값을 가져올지 (path notation, 예: "valuation.per") */
  source: string;
  /** 임계 조건 (gte=이상, lte=이하) */
  threshold: { gte?: number; lte?: number };
  /** 사용자에게 표시될 임계 설명 */
  threshold_label: string;
  /** 표시 단위 (예: "%", "배", "일") */
  suffix?: string;
  /** 임계에 근접하면 warn 톤 (gte의 경우 80%, lte의 경우 120%로 자동 계산되며, 이 값으로 override 가능) */
  warn_threshold?: number;
  /** 표시 자릿수 */
  precision?: number;
}

/** 종목별 모니터 설정 */
export interface MonitorConfig {
  code: string;
  name: string;
  corp_code: string;
  triggers: TriggerDef[];
  /** 특수관계자 매입 비율 추적 시 거래 상대방 회사명 */
  related_party_partner?: string;
  /** 모회사·외부 법인 공시 추적 시 corp_code (예: SNT홀딩스 EB 발행 추적) */
  external_corp_code?: string;
  external_corp_keywords?: string[];
  /** 5% 대량보유 변동 추적 시 인물·법인 키워드 */
  major_holder_keywords?: string[];
  /** 임원·주요주주 거래 추적 시 인물 키워드 */
  insider_keywords?: string[];
  /** 뉴스 RSS 키워드 */
  news_keywords?: string[];
}

/** 메트릭 평가 결과 (monitor JSON에 저장됨) */
export interface MetricResult {
  id: string;
  label: string;
  value: number | string | null;
  /** UI 표시용 문자열 (예: "8.20배") */
  display: string;
  /** 임계 설명 */
  threshold: string;
  /** 임계 돌파 여부 */
  hit: boolean;
  tone: Tone;
  /** 보조 설명 (예: 출처 공시 접수번호) */
  detail?: string;
}

/** 알림 항목 */
export interface MonitorAlert {
  severity: "info" | "warn" | "bad";
  type: string;
  title: string;
  message: string;
}

/** 뉴스 매칭 항목 */
export interface NewsHit {
  keyword: string;
  date: string;
  title: string;
  url: string;
}

/** 출처 항목 */
export interface MonitorSource {
  label: string;
  ref: string;
}

/** monitor/{code}.json 전체 스키마 */
export interface MonitorData {
  code: string;
  name: string;
  last_checked: string;
  metrics: MetricResult[];
  alerts: MonitorAlert[];
  news_hits: NewsHit[];
  sources: MonitorSource[];
}

/** Collector 통합 결과 (트리거 평가에 사용됨) */
export interface CollectorBundle {
  valuation: {
    source: string;
    price: number | null;
    per: number | null;
    peg: number | null;
    pbr: number | null;
    foreign_ratio: number | null;
  } | null;
  supply_gap: {
    last_date: string | null;
    last_title: string | null;
    days_ago: number | null;
    rcept_no: string | null;
  } | null;
  op_margin: {
    year: number | null;
    revenue: number | null;
    op_profit: number | null;
    op_margin_pct: number | null;
    rcept_no: string | null;
  } | null;
  related_party: {
    year: number | null;
    purchase: number | null;
    revenue: number | null;
    ratio_pct: number | null;
    rcept_no: string | null;
    report_nm: string | null;
  } | null;
  insider_trades: Array<{ date: string; title: string; rcept_no: string }>;
  major_holder_changes: Array<{ date: string; title: string; rcept_no: string }>;
  stock_buyback_events: Array<{ date: string; title: string; rcept_no: string; type: string }>;
  capital_issuance: Array<{ date: string; title: string; rcept_no: string }>;
  external_corp_disclosures: Array<{ date: string; title: string; rcept_no: string }>;
}
