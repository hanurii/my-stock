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
  /** 최대주주 보유 비율 추적 시 대상 이름 (예: "SK스퀘어") */
  major_shareholder_name?: string;
  /** 오너 일가 매도 추적 시 인물 이름 목록 (예: ["홍라희", "이재용", "이부진", "이서현"]) */
  family_member_names?: string[];
  /** 동종 그룹 평균 PBR 비교용 종목코드 목록 (예: 4대 금융지주) */
  peer_codes?: string[];
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
  /** 제목의 부정 시그널 분류 결과 */
  severity?: "info" | "warn" | "bad";
  /** 감지된 부정 키워드 목록 ("하락", "추격" 등) */
  signals?: string[];
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
  affiliate_transactions: {
    ratio_pct: number | null;
    total_million: number | null;
    revenue_million: number | null;
    transaction_count: number;
    period_days: number;
    rcept_nos: string[];
    /** 전년 동기 비율 (%) — 비교 기간은 current의 직전 period_days */
    previous_ratio_pct: number | null;
    /** 전년 동기 총 거래 (백만원) */
    previous_total_million: number | null;
    /** 전년 대비 비율 변화 (%p) */
    yoy_change_pp: number | null;
    /** 전년 대비 거래금액 증가율 (%) */
    yoy_change_pct: number | null;
  } | null;
  major_shareholder: {
    shareholder_name: string;
    year: number | null;
    start_ratio: number | null;
    end_ratio: number | null;
    change_pp: number | null;
    rcept_no: string | null;
  } | null;
  /** 가장 최근 자사주 소각(주식소각결정) 공시 이후 경과일 */
  buyback_cancellation_gap: {
    last_date: string | null;
    last_title: string | null;
    days_ago: number | null;
    rcept_no: string | null;
  } | null;
  /** 오너 일가 매도 내역 ('최대주주등소유주식변동신고서' 본문 파싱 기반) */
  insider_family_trades: {
    lookback_days: number;
    total_shares_sold: number;
    total_amount_estimate: number | null;
    trades: Array<{
      date: string;
      name: string;
      kind: string;
      prev_shares: number;
      diff_shares: number;
      post_shares: number;
      rcept_no: string;
    }>;
  } | null;
  insider_trades: Array<{ date: string; title: string; rcept_no: string }>;
  major_holder_changes: Array<{ date: string; title: string; rcept_no: string }>;
  stock_buyback_events: Array<{ date: string; title: string; rcept_no: string; type: string }>;
  capital_issuance: Array<{ date: string; title: string; rcept_no: string }>;
  external_corp_disclosures: Array<{ date: string; title: string; rcept_no: string }>;
  /** 4대 금융지주 등 동종 그룹 평균 PBR 대비 프리미엄(pp) */
  peer_pbr_premium: {
    target_pbr: number | null;
    peer_avg_pbr: number | null;
    premium_pp: number | null;
    peers_used: string[];
  } | null;
  /** 분기배당 QoQ 변화율 (DART alotMatter 기반) */
  dividend_trend: {
    latest_dps: number | null;
    prev_dps: number | null;
    qoq_change_pct: number | null;
    latest_record_date: string | null;
    rcept_no: string | null;
  } | null;
  /** 외국인 순매수 누적 추적 (네이버 dealTrendInfos 일별 누적) */
  foreign_net_buy: {
    cumulative_20d_shares: number | null;
    days_count: number;
    latest_date: string | null;
  } | null;
  /** 최근 분기 순이익 (분기 적자 전환 감지용) */
  quarterly_net_income: {
    period: string | null;
    net_income_billion: number | null;
    rcept_no: string | null;
  } | null;
  /** 가장 최근 자사주 취득결정 공시 이후 경과일 */
  buyback_acquisition_gap: {
    last_date: string | null;
    last_title: string | null;
    days_ago: number | null;
    rcept_no: string | null;
  } | null;
}

/** PeerPbrPremium 결과 (export 편의) */
export type PeerPbrPremiumResult = NonNullable<CollectorBundle["peer_pbr_premium"]>;
export type DividendTrendResult = NonNullable<CollectorBundle["dividend_trend"]>;
export type ForeignNetBuyTrendResult = NonNullable<CollectorBundle["foreign_net_buy"]>;
export type QuarterlyNetIncomeResult = NonNullable<CollectorBundle["quarterly_net_income"]>;
export type BuybackAcquisitionGapResult = NonNullable<CollectorBundle["buyback_acquisition_gap"]>;
