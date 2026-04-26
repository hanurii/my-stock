/**
 * 매도 트리거 자동 모니터 — 메인 entry
 *
 * configs.ts의 종목별 설정을 순회하며 collector 호출 → public/data/research/monitor/{code}.json 저장.
 *
 * 실행:
 *   npx tsx scripts/monitor-research.ts        — 전체
 *   npx tsx scripts/monitor-research.ts 083930 — 단일 종목
 */
import fs from "fs";
import path from "path";
import { CONFIGS } from "./monitor/configs";
import * as col from "./monitor/collectors";
import type {
  CollectorBundle,
  MetricResult,
  MonitorAlert,
  MonitorConfig,
  MonitorData,
  MonitorSource,
  TriggerDef,
  Tone,
} from "./monitor/types";

col.loadEnv();

// ── path notation으로 bundle에서 값 추출 ──
function resolveSource(srcPath: string, bundle: CollectorBundle): unknown {
  const parts = srcPath.split(".");
  let cur: unknown = bundle;
  for (const p of parts) {
    if (cur == null) return null;
    if (p === "count" && Array.isArray(cur)) return cur.length;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur;
}

function evaluateThreshold(
  value: unknown,
  threshold: { gte?: number; lte?: number },
): boolean {
  if (typeof value !== "number" || isNaN(value)) return false;
  if (threshold.gte !== undefined && value >= threshold.gte) return true;
  if (threshold.lte !== undefined && value <= threshold.lte) return true;
  return false;
}

function evaluateWarn(value: unknown, trig: TriggerDef): boolean {
  if (typeof value !== "number" || isNaN(value)) return false;
  if (trig.warn_threshold === undefined) return false;
  if (
    trig.threshold.gte !== undefined &&
    value >= trig.warn_threshold &&
    value < trig.threshold.gte
  )
    return true;
  if (
    trig.threshold.lte !== undefined &&
    value <= trig.warn_threshold &&
    value > trig.threshold.lte
  )
    return true;
  return false;
}

function formatDisplay(value: unknown, suffix?: string, precision = 2): string {
  if (value == null) return "—";
  if (typeof value === "number") {
    // 주식수 단위는 만·억으로 자동 축약하여 한 줄에 들어가게
    if (suffix === "주" && Math.abs(value) >= 10000) {
      const abs = Math.abs(value);
      const sign = value < 0 ? "-" : "";
      if (abs >= 100_000_000) return `${sign}${(abs / 100_000_000).toFixed(1)}억주`;
      const man = Math.round(abs / 10_000);
      return `${sign}${man.toLocaleString()}만주`;
    }
    const s = Number.isInteger(value) ? value.toLocaleString() : value.toFixed(precision);
    return suffix ? `${s}${suffix}` : s;
  }
  return String(value);
}

async function processStock(config: MonitorConfig): Promise<MonitorData> {
  console.log(`📊 ${config.name}(${config.code}) 모니터 시작 — ${col.kstNow()}`);

  // 트리거가 사용하는 collector만 호출 (불필요한 API 호출 절감)
  const sourceSet = new Set(config.triggers.map((t) => t.source.split(".")[0]));

  const [
    valuation,
    supply_gap,
    op_margin,
    related_party,
    affiliate_transactions,
    major_shareholder,
    buyback_cancellation_gap,
    insider_family_trades,
    insider_trades,
    major_holder_changes,
    stock_buyback_events,
    capital_issuance,
    external_corp_disclosures,
    peer_pbr_premium,
    dividend_trend,
    foreign_net_buy,
    quarterly_net_income,
    buyback_program_status,
    pref_discount,
    separate_quarterly_income,
    debt_guarantee_events,
    disclosure_keyword_hits,
    crude_oil_price,
    clinical_pipeline,
    net_interest_margin,
    npl_ratio,
    roe,
    bank_corp_disclosures,
    newsHits,
  ] = await Promise.all([
    sourceSet.has("valuation") ? col.collectValuation(config.code) : Promise.resolve(null),
    sourceSet.has("supply_gap")
      ? col.collectSupplyContractGap(config.corp_code, 180)
      : Promise.resolve(null),
    sourceSet.has("op_margin")
      ? col.collectQuarterlyOpMargin(config.corp_code)
      : Promise.resolve(null),
    sourceSet.has("related_party") && config.related_party_partner
      ? col.collectRelatedPartyPurchase(config.corp_code, config.related_party_partner)
      : Promise.resolve(null),
    sourceSet.has("affiliate_transactions")
      ? col.collectAffiliateTransactionRatio(config.corp_code, 365)
      : Promise.resolve(null),
    sourceSet.has("major_shareholder") && config.major_shareholder_name
      ? col.collectMajorShareholderRatio(config.corp_code, config.major_shareholder_name)
      : Promise.resolve(null),
    sourceSet.has("buyback_cancellation_gap")
      ? col.collectBuybackCancellationGap(config.corp_code, 730)
      : Promise.resolve(null),
    sourceSet.has("insider_family_trades") && config.family_member_names
      ? col.collectInsiderFamilyTrades(config.corp_code, 90, config.family_member_names)
      : Promise.resolve(null),
    sourceSet.has("insider_trades")
      ? col.collectInsiderTrades(config.corp_code, 90, config.insider_keywords ?? [])
      : Promise.resolve([]),
    sourceSet.has("major_holder_changes")
      ? col.collectMajorHolderChanges(config.corp_code, 90)
      : Promise.resolve([]),
    sourceSet.has("stock_buyback_events")
      ? col.collectStockBuybackEvents(config.corp_code, 90)
      : Promise.resolve([]),
    sourceSet.has("capital_issuance")
      ? col.collectCapitalIssuance(config.corp_code, 90)
      : Promise.resolve([]),
    sourceSet.has("external_corp_disclosures") && config.external_corp_code
      ? col.collectExternalCorpDisclosures(
          config.external_corp_code,
          90,
          config.external_corp_keywords ?? [],
        )
      : Promise.resolve([]),
    Promise.resolve(
      sourceSet.has("peer_pbr_premium") && config.peer_codes && config.peer_codes.length > 0
        ? col.collectPeerPbrPremium(config.code, config.peer_codes)
        : null,
    ),
    sourceSet.has("dividend_trend")
      ? col.collectDividendTrend(config.corp_code)
      : Promise.resolve(null),
    sourceSet.has("foreign_net_buy")
      ? col.collectForeignNetBuyTrend(config.code)
      : Promise.resolve(null),
    sourceSet.has("quarterly_net_income")
      ? col.collectQuarterlyNetIncome(config.corp_code)
      : Promise.resolve(null),
    sourceSet.has("buyback_program_status")
      ? col.collectBuybackProgramStatus(config.corp_code, 730)
      : Promise.resolve(null),
    sourceSet.has("pref_discount") && config.common_stock_code
      ? col.collectPrefDiscount(config.code, config.common_stock_code)
      : Promise.resolve(null),
    sourceSet.has("separate_quarterly_income")
      ? col.collectSeparateQuarterlyIncome(config.corp_code)
      : Promise.resolve(null),
    sourceSet.has("debt_guarantee_events")
      ? col.collectDebtGuaranteeEvents(config.corp_code, 90)
      : Promise.resolve([]),
    sourceSet.has("disclosure_keyword_hits") &&
    config.disclosure_keyword_groups &&
    config.disclosure_keyword_groups.length > 0
      ? col.collectDisclosureKeywordHits(
          config.corp_code,
          90,
          config.disclosure_keyword_groups,
        )
      : Promise.resolve(null),
    sourceSet.has("crude_oil_price")
      ? col.collectCrudeOilPrice()
      : Promise.resolve(null),
    sourceSet.has("clinical_pipeline") &&
    config.clinical_sponsor_keywords &&
    config.clinical_sponsor_keywords.length > 0
      ? col.collectClinicalPipelineStatus(config.code, config.clinical_sponsor_keywords)
      : Promise.resolve(null),
    sourceSet.has("net_interest_margin")
      ? col.collectNetInterestMargin(config.corp_code, config.bank_corp_code)
      : Promise.resolve(null),
    sourceSet.has("npl_ratio")
      ? col.collectNplRatio(config.corp_code)
      : Promise.resolve(null),
    sourceSet.has("roe")
      ? col.collectRoe(config.corp_code)
      : Promise.resolve(null),
    sourceSet.has("bank_corp_disclosures") && config.bank_corp_code
      ? col.collectExternalCorpDisclosures(config.bank_corp_code, 90, [
          "주식등의대량보유",
          "주식 등의 대량보유",
          "최대주주 변경",
          "최대주주변경",
        ])
      : Promise.resolve([]),
    config.news_keywords && config.news_keywords.length > 0
      ? col.collectNewsHits(config.news_keywords, 7)
      : Promise.resolve([]),
  ]);

  const bundle: CollectorBundle = {
    valuation,
    supply_gap,
    op_margin,
    related_party,
    affiliate_transactions,
    major_shareholder,
    buyback_cancellation_gap,
    insider_family_trades,
    insider_trades,
    major_holder_changes,
    stock_buyback_events,
    capital_issuance,
    external_corp_disclosures,
    peer_pbr_premium,
    dividend_trend,
    foreign_net_buy,
    quarterly_net_income,
    buyback_program_status,
    pref_discount,
    separate_quarterly_income,
    debt_guarantee_events,
    disclosure_keyword_hits,
    crude_oil_price,
    clinical_pipeline,
    net_interest_margin,
    npl_ratio,
    roe,
    bank_corp_disclosures,
  };

  // 메트릭 평가
  const metrics: MetricResult[] = config.triggers.map((trig) => {
    const value = resolveSource(trig.source, bundle);
    const hit = evaluateThreshold(value, trig.threshold);
    const warn = !hit && evaluateWarn(value, trig);
    const tone: Tone = hit
      ? trig.tone_on_hit ?? "bad"
      : warn
        ? "warn"
        : value == null
          ? "neutral"
          : trig.tone_on_miss ?? "good";
    // label 동적 치환 — 예: "대명ENG 매입 비율 ({year})"
    let label = trig.label;
    if (trig.id === "related_party" && related_party?.year) {
      label = `${config.related_party_partner ?? "특수관계자"} 매입 (${related_party.year})`;
    }
    if (trig.id === "op_margin" && op_margin?.year) {
      label = `분기 영업이익률 (${op_margin.year})`;
    }
    // 자사주 프로그램 상태 — 마지막 공시 종류와 status 정보로 라벨 보강
    if (trig.id === "buyback_program_status" && buyback_program_status?.last_kind) {
      const kindLabel =
        buyback_program_status.last_kind === "acquire"
          ? "취득결정"
          : buyback_program_status.last_kind === "result"
            ? "취득결과"
            : "소각결정";
      const statusLabel =
        buyback_program_status.status === "active"
          ? "진행 중"
          : buyback_program_status.status === "cooldown"
            ? "후속 대기"
            : buyback_program_status.status === "post_cooldown"
              ? "후속 지연"
              : "사실상 중단";
      label = `자사주 프로그램 (마지막 ${kindLabel} · ${statusLabel})`;
    }
    return {
      id: trig.id,
      label,
      value: typeof value === "number" || typeof value === "string" ? value : null,
      display: formatDisplay(value, trig.suffix, trig.precision ?? 2),
      threshold: trig.threshold_label,
      hit,
      tone,
    };
  });

  // 알림 생성
  const alerts: MonitorAlert[] = [];
  // silent_alert 트리거는 alert에서 제외 (metric 카드는 표시됨)
  const silentIds = new Set(
    config.triggers.filter((t) => t.silent_alert).map((t) => t.id),
  );
  for (const m of metrics) {
    if (silentIds.has(m.id)) continue;
    if (m.hit) {
      // 긍정 시그널 트리거(tone="good")는 매도 알림이 아니라 재평가 신호로 표시
      const isPositive = m.tone === "good";
      alerts.push({
        severity: isPositive ? "info" : "bad",
        type: m.id,
        title: `${m.label} ${m.threshold}`,
        message: isPositive
          ? `현재 ${m.display} — 긍정 시그널 발생 (재평가 검토)`
          : `현재 ${m.display} — 매도 트리거 도달`,
      });
    } else if (m.tone === "warn") {
      alerts.push({
        severity: "warn",
        type: m.id,
        title: `${m.label} 임계 근접`,
        message: `현재 ${m.display} (임계 ${m.threshold})`,
      });
    } else if (m.value == null) {
      // foreign_net_buy 워밍업 케이스 — 누적 day count가 임계 미만이면 "history 누적 중"
      const isForeignWarmup =
        m.id === "foreign_net_buy_4w" &&
        foreign_net_buy != null &&
        foreign_net_buy.days_count > 0;
      if (isForeignWarmup) {
        alerts.push({
          severity: "info",
          type: `${m.id}_warmup`,
          title: `${m.label} 누적 중`,
          message: `현재 ${foreign_net_buy!.days_count}거래일 누적 (20일 이상 시 메트릭 평가 시작).`,
        });
      } else {
        alerts.push({
          severity: "warn",
          type: `${m.id}_missing`,
          title: `${m.label} 데이터 미수집`,
          message: "DART/시세 조회 실패 — 다음 실행에서 재시도",
        });
      }
    }
  }
  if (newsHits.length > 0) {
    const sevCount = { bad: 0, warn: 0, info: 0 };
    for (const h of newsHits) sevCount[h.severity ?? "info"]++;
    const maxSev: "info" | "warn" | "bad" =
      sevCount.bad > 0 ? "bad" : sevCount.warn > 0 ? "warn" : "info";
    const sevLabel =
      maxSev === "bad"
        ? `부정 시그널 ${sevCount.bad}건 포함`
        : maxSev === "warn"
          ? `관찰 신호 ${sevCount.warn}건 포함`
          : "중립 헤드라인";
    alerts.push({
      severity: maxSev,
      type: "news_keyword_hit",
      title: `규제·매크로 키워드 뉴스 ${newsHits.length}건 (${sevLabel})`,
      message: `최근 7일 매칭. 상세는 하단 리스트 확인.`,
    });
  }
  // 정규식 정확도 1회성 검증 — target_period 일치 시에만 발동
  if (
    config.verification &&
    quarterly_net_income?.period === config.verification.target_period
  ) {
    const v = config.verification;
    const results = Object.entries(v.expected).map(([id, expected]) => {
      const m = metrics.find((x) => x.id === id);
      const actual = typeof m?.value === "number" ? m.value : null;
      const diff = actual != null ? Math.abs(actual - expected) : null;
      const passed = diff != null && diff <= v.tolerance_pp;
      return { id, expected, actual, diff, passed };
    });
    const allPassed = results.every((r) => r.passed);
    if (allPassed) {
      alerts.push({
        severity: "info",
        type: "verification_passed",
        title: `✅ ${v.label} 검증 통과 — silent_alert 해제 가능`,
        message: `허용 오차 ${v.tolerance_pp}%p 이내 모두 일치: ${results
          .map((r) => `${r.id} ${r.actual}% (기대 ${r.expected}%)`)
          .join(" · ")}. configs.ts에서 ${v.unlock_silent_metric_ids.join(", ")} trigger의 silent_alert 줄을 제거하면 alert 활성화됩니다.`,
      });
    } else {
      const fails = results
        .filter((r) => !r.passed)
        .map(
          (r) =>
            `${r.id} 추출 ${r.actual ?? "null"}% (기대 ${r.expected}%, 차이 ${r.diff?.toFixed(2) ?? "-"}%p)`,
        )
        .join(" / ");
      alerts.push({
        severity: "warn",
        type: "verification_failed",
        title: `⚠️ ${v.label} 검증 실패 — 정규식 보강 필요`,
        message: `허용 오차 ${v.tolerance_pp}%p 초과: ${fails}`,
      });
    }
  }
  if (alerts.length === 0) {
    alerts.push({
      severity: "info",
      type: "all_clear",
      title: "모든 매도 트리거 범위 내",
      message: "현재 지표·공시·뉴스 기준 즉각 매도 사유 없음. 보유 유지.",
    });
  }

  // 출처
  const sources: MonitorSource[] = [];
  if (valuation) sources.push({ label: "PER/PEG/PBR 스코어", ref: `public/data/${valuation.source}.json` });
  if (supply_gap?.rcept_no)
    sources.push({ label: "최근 공급계약 공시", ref: `DART ${supply_gap.rcept_no}` });
  if (op_margin?.rcept_no)
    sources.push({
      label: `분기 영업이익률 (${op_margin.year})`,
      ref: `DART ${op_margin.rcept_no}`,
    });
  if (related_party?.rcept_no)
    sources.push({
      label: `${config.related_party_partner ?? "특수관계자"} 매입 비율`,
      ref: `DART ${related_party.rcept_no} (${related_party.report_nm})`,
    });
  if (affiliate_transactions && affiliate_transactions.transaction_count > 0)
    sources.push({
      label: `계열사 거래 비율 (${affiliate_transactions.period_days}일 누적, ${affiliate_transactions.transaction_count}건)`,
      ref: `DART 특수관계인내부거래·출자계열사거래 ${affiliate_transactions.rcept_nos.slice(0, 3).join(", ")}${affiliate_transactions.rcept_nos.length > 3 ? " 외" : ""}`,
    });
  if (major_shareholder?.rcept_no)
    sources.push({
      label: `${major_shareholder.shareholder_name} 보유 비율 (${major_shareholder.year})`,
      ref: `DART ${major_shareholder.rcept_no} (hyslrSttus)`,
    });
  if (buyback_cancellation_gap?.rcept_no)
    sources.push({
      label: `최근 자사주 소각 공시 (${buyback_cancellation_gap.last_date})`,
      ref: `DART ${buyback_cancellation_gap.rcept_no}`,
    });
  if (insider_family_trades && insider_family_trades.trades.length > 0) {
    // 최대 건 (절대값 기준) 을 source 라벨로 — 최신보다 임팩트 큰 건이 대표
    const biggest = insider_family_trades.trades.reduce((a, b) =>
      Math.abs(a.diff_shares) >= Math.abs(b.diff_shares) ? a : b,
    );
    sources.push({
      label: `일가 매도 ${insider_family_trades.trades.length}건 총 ${insider_family_trades.total_shares_sold.toLocaleString()}주 (최대: ${biggest.name} ${biggest.date} -${Math.abs(biggest.diff_shares).toLocaleString()}주 ${biggest.kind})`,
      ref: `DART 최대주주등소유주식변동신고서 ${biggest.rcept_no}`,
    });
  }
  if (external_corp_disclosures.length > 0)
    sources.push({
      label: `외부법인 공시 ${external_corp_disclosures.length}건`,
      ref: `DART (${config.external_corp_code})`,
    });
  if (major_holder_changes.length > 0)
    sources.push({
      label: `최대주주 지분 변동 ${major_holder_changes.length}건`,
      ref: "DART 주식등의대량보유 / 최대주주등소유주식변동",
    });
  if (capital_issuance.length > 0) {
    const recent = capital_issuance[0];
    sources.push({
      label: `자본조달 공시 ${capital_issuance.length}건 (최근: ${recent.date} ${recent.title})`,
      ref: `DART ${recent.rcept_no}`,
    });
  }
  if (peer_pbr_premium && peer_pbr_premium.peers_used.length > 0) {
    sources.push({
      label: `4대 지주 평균 PBR 비교 (${peer_pbr_premium.peers_used.length}종목)`,
      ref: `peers: ${peer_pbr_premium.peers_used.join(", ")} / avg ${peer_pbr_premium.peer_avg_pbr ?? "—"}`,
    });
  }
  if (dividend_trend?.rcept_no)
    sources.push({
      label: `분기 배당 결정 (${dividend_trend.latest_record_date ?? ""})`,
      ref: `DART ${dividend_trend.rcept_no} (alotMatter)`,
    });
  if (foreign_net_buy && foreign_net_buy.days_count > 0)
    sources.push({
      label: `외국인 순매수 누적 (${foreign_net_buy.days_count}일)`,
      ref: `네이버 dealTrendInfos / history ${foreign_net_buy.latest_date ?? ""}`,
    });
  if (quarterly_net_income?.rcept_no)
    sources.push({
      label: `최근 분기 순이익 (${quarterly_net_income.period ?? ""})`,
      ref: `DART ${quarterly_net_income.rcept_no} (fnlttSinglAcntAll)`,
    });
  if (buyback_program_status?.rcept_no) {
    const kindLabel =
      buyback_program_status.last_kind === "acquire"
        ? "취득결정"
        : buyback_program_status.last_kind === "result"
          ? "취득결과보고"
          : "소각결정";
    sources.push({
      label: `자사주 프로그램 마지막 활동 (${buyback_program_status.last_date} · ${kindLabel}) — 누적 취득 ${buyback_program_status.acquire_count} / 결과 ${buyback_program_status.result_count} / 소각 ${buyback_program_status.cancel_count}`,
      ref: `DART ${buyback_program_status.rcept_no}`,
    });
  }
  if (disclosure_keyword_hits) {
    for (const [name, group] of Object.entries(disclosure_keyword_hits.groups)) {
      if (group.hits.length === 0) continue;
      const recent = group.hits[0];
      sources.push({
        label: `${group.label} 공시 ${group.hits.length}건 (최근: ${recent.date})`,
        ref: `DART ${recent.rcept_no} — 매칭 키워드: ${recent.matched.join(", ")}`,
      });
    }
  }
  if (pref_discount && pref_discount.discount_pct != null)
    sources.push({
      label: `보통주-우선주 디스카운트 (${pref_discount.as_of ?? ""})`,
      ref: `네이버 lastClose ${pref_discount.common_code}/${pref_discount.pref_code}: ${pref_discount.common_price?.toLocaleString()}원/${pref_discount.pref_price?.toLocaleString()}원`,
    });
  if (crude_oil_price?.latest_close != null)
    sources.push({
      label: `Brent 원유 종가 ${crude_oil_price.latest_close} USD (${crude_oil_price.latest_date}, 7일 평균 ${crude_oil_price.avg_7d})`,
      ref: `Yahoo Finance ${crude_oil_price.symbol}`,
    });
  if (clinical_pipeline) {
    const recent = clinical_pipeline.recent_changes_30d.changes[0];
    const recentLabel = recent
      ? ` · 최근: ${recent.nct_id} ${recent.from_status} → ${recent.to_status} (${recent.date})`
      : "";
    sources.push({
      label: `ClinicalTrials.gov 임상 ${clinical_pipeline.count}건 (30일 status 변경 ${clinical_pipeline.recent_changes_30d.count}건${recentLabel})`,
      ref: `query.spons: ${clinical_pipeline.sponsor_keywords.join(", ")}`,
    });
  }
  if (net_interest_margin?.rcept_no) {
    const parts: string[] = [];
    if (net_interest_margin.group_nim_pct != null)
      parts.push(`그룹 ${net_interest_margin.group_nim_pct}%`);
    if (net_interest_margin.bank_nim_pct != null)
      parts.push(`은행 ${net_interest_margin.bank_nim_pct}%`);
    sources.push({
      label: `NIM (${net_interest_margin.period ?? ""}${parts.length ? ` · ${parts.join("·")}` : ""})`,
      ref: `DART ${net_interest_margin.rcept_no} (본문 정규식 추출)`,
    });
  }
  if (npl_ratio?.rcept_no) {
    const parts: string[] = [];
    if (npl_ratio.npl_ratio_pct != null) parts.push(`NPL ${npl_ratio.npl_ratio_pct}%`);
    if (npl_ratio.delinquency_pct != null) parts.push(`연체 ${npl_ratio.delinquency_pct}%`);
    if (npl_ratio.ccr_pct != null) parts.push(`CCR ${npl_ratio.ccr_pct}%`);
    sources.push({
      label: `여신 건전성 (${npl_ratio.period ?? ""}${parts.length ? ` · ${parts.join("·")}` : ""})`,
      ref: `DART ${npl_ratio.rcept_no} (본문 정규식 추출)`,
    });
  }
  if (roe?.rcept_no && roe.annualized_roe_pct != null) {
    sources.push({
      label: `분기 ROE 연환산 (${roe.period ?? ""} · ${roe.annualized_roe_pct}%)`,
      ref: `DART ${roe.rcept_no} (fnlttSinglAcntAll: 자본총계+분기순이익)`,
    });
  }
  if (bank_corp_disclosures.length > 0) {
    sources.push({
      label: `자회사(은행) 5% 변동·최대주주 공시 ${bank_corp_disclosures.length}건`,
      ref: `DART (${config.bank_corp_code})`,
    });
  }
  if (newsHits.length > 0)
    sources.push({ label: "뉴스 RSS", ref: "news.google.com/rss (7일)" });

  const data: MonitorData = {
    code: config.code,
    name: config.name,
    last_checked: col.kstNow(),
    metrics,
    alerts,
    news_hits: newsHits,
    sources,
  };
  console.log(
    `  ✅ ${config.name} 메트릭 ${metrics.length}건 / 알림 ${alerts.length}건 (${alerts.map((a) => a.severity).join(", ")})`,
  );
  return data;
}

async function main() {
  const targetCode = process.argv[2];
  const targets = targetCode
    ? CONFIGS.filter((c) => c.code === targetCode)
    : CONFIGS;
  if (targets.length === 0) {
    console.error(`❌ 종목 ${targetCode} 설정 없음 — configs.ts 확인`);
    process.exit(1);
  }
  const outDir = path.resolve("public/data/research/monitor");
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  for (const config of targets) {
    try {
      const result = await processStock(config);
      const outPath = path.join(outDir, `${config.code}.json`);
      fs.writeFileSync(outPath, JSON.stringify(result, null, 2), "utf-8");
      console.log(`  💾 저장: ${outPath}\n`);
    } catch (e) {
      console.error(`❌ ${config.name}(${config.code}) 실패:`, (e as Error).message);
    }
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
