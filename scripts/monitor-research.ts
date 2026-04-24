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
    const s = Number.isInteger(value) ? String(value) : value.toFixed(precision);
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
    newsHits,
  ] = await Promise.all([
    Promise.resolve(sourceSet.has("valuation") ? col.collectValuation(config.code) : null),
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
      ? col.collectBuybackCancellationGap(config.corp_code, 365)
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
  };

  // 메트릭 평가
  const metrics: MetricResult[] = config.triggers.map((trig) => {
    const value = resolveSource(trig.source, bundle);
    const hit = evaluateThreshold(value, trig.threshold);
    const warn = !hit && evaluateWarn(value, trig);
    const tone: Tone =
      hit ? "bad" : warn ? "warn" : value == null ? "neutral" : "good";
    // label 동적 치환 — 예: "대명ENG 매입 비율 ({year})"
    let label = trig.label;
    if (trig.id === "related_party" && related_party?.year) {
      label = `${config.related_party_partner ?? "특수관계자"} 매입 (${related_party.year})`;
    }
    if (trig.id === "op_margin" && op_margin?.year) {
      label = `분기 영업이익률 (${op_margin.year})`;
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
  for (const m of metrics) {
    if (m.hit) {
      alerts.push({
        severity: "bad",
        type: m.id,
        title: `${m.label} ${m.threshold}`,
        message: `현재 ${m.display} — 매도 트리거 도달`,
      });
    } else if (m.tone === "warn") {
      alerts.push({
        severity: "warn",
        type: m.id,
        title: `${m.label} 임계 근접`,
        message: `현재 ${m.display} (임계 ${m.threshold})`,
      });
    } else if (m.value == null) {
      alerts.push({
        severity: "warn",
        type: `${m.id}_missing`,
        title: `${m.label} 데이터 미수집`,
        message: "DART/시세 조회 실패 — 다음 실행에서 재시도",
      });
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
