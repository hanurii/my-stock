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
  /** hit 시 톤을 강제로 지정 (긍정 시그널 — 예: GS 자사주 취득결정 공시는 hit이지만 'good') */
  tone_on_hit?: Tone;
  /** miss(hit=false, value 존재) 시 톤을 강제로 지정.
   *  default는 "good" — 매도 트리거가 발동 안 했으면 안전 신호.
   *  단, 긍정 시그널 트리거(예: GS buyback_acquisition)는 miss=현 상태이므로 "neutral" 사용. */
  tone_on_miss?: Tone;
  /** true이면 metric 카드는 표시하되 alerts에는 추가하지 않음.
   *  추출 정확도가 미검증인 V2 지표(KB금융 NIM·NPL·ROE 본문 파싱)에 사용. */
  silent_alert?: boolean;
}

/** 모니터 목적 — 매도 트리거 vs 매수(진입) 트리거 분기.
 *  알림 문구·all_clear 메시지·뉴스 알림 라벨이 purpose에 따라 변함. 기본 "exit". */
export type MonitorPurpose = "exit" | "entry";

/** 종목별 모니터 설정 */
export interface MonitorConfig {
  code: string;
  name: string;
  corp_code: string;
  /** 모니터 목적 (기본 "exit"). entry-configs.ts 항목은 "entry"로 명시. */
  purpose?: MonitorPurpose;
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
  /** 우선주 모니터링 시 보통주 종목코드 — pref_discount collector 활성화 트리거 */
  common_stock_code?: string;
  /** 자사 corp_code DART 공시 키워드 매칭 그룹 (PF 손실·자본 규제 후퇴 등 정성 신호 감지) */
  disclosure_keyword_groups?: Array<{
    /** group key — source path에서 사용 (snake_case 권장) */
    name: string;
    /** UI 라벨 */
    label: string;
    /** report_nm 부분 일치 키워드 */
    keywords: string[];
  }>;
  /** ClinicalTrials.gov sponsor 검색용 키워드 (바이오 종목 임상 단계 변경 감지) */
  clinical_sponsor_keywords?: string[];
  /** 자회사(은행 등) 별도 corp_code — NIM·NPL 본문 파싱 + 5% 대량보유 변동 추적용 */
  bank_corp_code?: string;
  /** 정규식 추출 정확도 1회성 검증 — 특정 보고서 기간(target_period)이 잡히면
   *  metric 값들을 기대값과 비교해 alert에 결과 표시. silent_alert 해제 판단용.
   *  KB금융 NIM·NPL·ROE 본문 파싱이 1Q26 IR 발표값과 일치하는지 자동 점검.
   */
  verification?: {
    /** 검증 트리거 기간 (예: "2026-Q1"). bundle.quarterly_net_income.period와 일치 시에만 비교 실행 */
    target_period: string;
    /** 사용자에게 노출되는 검증 라벨 (예: "1Q26 정규식 정확도") */
    label: string;
    /** 허용 오차 (%p) — 모든 metric의 절대값 차이가 이 이하면 통과 */
    tolerance_pp: number;
    /** metric id → 기대값 (%) */
    expected: Record<string, number>;
    /** 검증 통과 시 안내에 포함할 metric id 목록 (configs.ts에서 silent_alert 제거 대상) */
    unlock_silent_metric_ids: string[];
  };
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
    dividend_yield: number | null;
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
  /** 자사주 매입 프로그램 종합 상태 — 취득결정·취득결과보고·소각결정 3종 공시를
   *  통합 추적. 가장 최근 활동일 기준 경과일 + 단계별 상태(active/cooldown/post_cooldown/abandoned).
   */
  buyback_program_status: {
    last_date: string | null;
    last_title: string | null;
    /** 마지막 공시 종류: "acquire" (취득결정), "result" (취득결과보고), "cancel" (소각결정) */
    last_kind: "acquire" | "result" | "cancel" | null;
    days_ago: number | null;
    /** active=취득 진행 중 / cooldown=완료 직후 정상 / post_cooldown=후속 발표 지연 / abandoned=프로그램 사실상 중단 */
    status: "active" | "cooldown" | "post_cooldown" | "abandoned" | null;
    rcept_no: string | null;
    /** 추적 기간 동안의 단계별 누적 건수 — 운영 모니터링용 */
    acquire_count: number;
    result_count: number;
    cancel_count: number;
  } | null;
  /** 자사 corp_code DART 공시 키워드 매칭 결과 (그룹별 dictionary).
   *  source path 예: `disclosure_keyword_hits.groups.pf_loss.hits.count` (gte 1로 매도 신호).
   */
  disclosure_keyword_hits: {
    period_days: number;
    groups: Record<
      string,
      {
        label: string;
        keywords: string[];
        hits: Array<{
          date: string;
          title: string;
          rcept_no: string;
          matched: string[];
        }>;
      }
    >;
  } | null;
  /** 보통주-우선주 디스카운트율 (우선주 모니터링용, 네이버 종가 기반) */
  pref_discount: {
    common_code: string;
    pref_code: string;
    common_price: number | null;
    pref_price: number | null;
    discount_pct: number | null;
    as_of: string | null;
  } | null;
  /** 별도 재무제표 기준 분기 순이익 (지주사 자체 이익 추적용) */
  separate_quarterly_income: {
    year: number | null;
    period: string | null;
    net_income: number | null;
    net_income_billion: number | null;
    rcept_no: string | null;
  } | null;
  /** 자체 corp 채무보증결정 공시 (자회사 보증 누적 추적) */
  debt_guarantee_events: Array<{ date: string; title: string; rcept_no: string }>;
  /** 원유 시세 (Brent 기반 — 두바이유 직접 시리즈는 무료 일별 API 부재로 Brent로 근사.
   *  정유사 마진은 두바이유와 강한 연동 — Brent 70달러 이하 추세는 정유 매크로 약화 신호.
   */
  crude_oil_price: {
    /** 시세 출처 (Yahoo Finance "BZ=F") */
    source: string;
    /** 사용 심볼 */
    symbol: string;
    /** 가장 최근 종가 (USD/배럴) */
    latest_close: number | null;
    latest_date: string | null;
    /** 최근 7거래일 평균 (단기 노이즈 필터) */
    avg_7d: number | null;
    /** 최근 7거래일 종가 시퀀스 (가장 오래된 → 최신) */
    series: Array<{ date: string; close: number }>;
  } | null;
  /** 금융사(은행지주) 분기 NIM. DART 분기·사업보고서 본문 정규식 추출.
   *  source path 예: `net_interest_margin.group_nim_pct` (lte 1.7로 매도 신호).
   */
  net_interest_margin: {
    /** 그룹(연결) NIM (%) */
    group_nim_pct: number | null;
    /** 은행 단독 NIM (%) — bank_corp_code의 보고서 본문에서 추출 */
    bank_nim_pct: number | null;
    period: string | null;
    rcept_no: string | null;
    /** 추출에 사용된 본문 컨텍스트 (디버깅·정규식 보강용) */
    source_text: string | null;
  } | null;
  /** 금융사 NPL 비율·연체율·CCR (대손충당금전입비율). 본문 정규식 추출.
   *  source path 예: `npl_ratio.npl_ratio_pct` (gte 0.5로 매도 신호).
   */
  npl_ratio: {
    npl_ratio_pct: number | null;
    delinquency_pct: number | null;
    ccr_pct: number | null;
    period: string | null;
    rcept_no: string | null;
    source_text: string | null;
  } | null;
  /** 분기 ROE (연환산). 분기 순이익 × 4 / 자기자본.
   *  source path 예: `roe.annualized_roe_pct` (lte 10으로 매도 신호).
   */
  roe: {
    annualized_roe_pct: number | null;
    quarterly_net_income_million: number | null;
    total_equity_million: number | null;
    period: string | null;
    rcept_no: string | null;
  } | null;
  /** 자회사(은행) 단독 공시 (5% 대량보유 변동 등). bank_corp_code 사용. */
  bank_corp_disclosures: Array<{ date: string; title: string; rcept_no: string }>;
  /** ClinicalTrials.gov 임상 파이프라인 status 추적 (바이오 종목 임상 단계 변경 감지).
   *  source path 예: `clinical_pipeline.recent_changes_30d.count` (gte 1로 매도 신호).
   *  캐시 파일(`.cache/clinical-pipeline-{code}.json`)과 비교해 status 변경분만 감지.
   */
  clinical_pipeline: {
    sponsor_keywords: string[];
    trials: Array<{
      nct_id: string;
      title: string;
      indication: string;
      phase: string;
      status: string;
      last_update_date: string;
    }>;
    count: number;
    recent_changes_30d: {
      count: number;
      changes: Array<{
        nct_id: string;
        title: string;
        from_status: string;
        to_status: string;
        date: string;
      }>;
    };
  } | null;
}

/** PeerPbrPremium 결과 (export 편의) */
export type PeerPbrPremiumResult = NonNullable<CollectorBundle["peer_pbr_premium"]>;
export type DividendTrendResult = NonNullable<CollectorBundle["dividend_trend"]>;
export type ForeignNetBuyTrendResult = NonNullable<CollectorBundle["foreign_net_buy"]>;
export type QuarterlyNetIncomeResult = NonNullable<CollectorBundle["quarterly_net_income"]>;
export type BuybackProgramStatusResult = NonNullable<CollectorBundle["buyback_program_status"]>;
export type DisclosureKeywordHitsResult = NonNullable<CollectorBundle["disclosure_keyword_hits"]>;
export type PrefDiscountResult = NonNullable<CollectorBundle["pref_discount"]>;
export type SeparateQuarterlyIncomeResult = NonNullable<CollectorBundle["separate_quarterly_income"]>;
export type CrudeOilPriceResult = NonNullable<CollectorBundle["crude_oil_price"]>;
