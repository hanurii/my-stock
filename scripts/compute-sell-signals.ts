/**
 * 매도 시스템 - 매도 신호 계산 스크립트
 *
 * Phase 2: SK하이닉스(000660) 단일 종목 테스트.
 * 보유 종목별로 책 기준 매도 트리거를 평가하여 public/data/sell-signals.json 저장.
 *
 * strategy 페이지 평가 항목 (책 2·4 범주):
 * - 매수가 / 현재가 / +%
 * - 손절선 = avg × 0.92 (-8%)
 * - 익절선 1차 = avg × 1.20 (+20%), 2차 = avg × 1.25 (+25%)
 * - 추가 매수 한계 = avg × 1.05 (+5%)
 * - 매수 진입 정확도 (책 기준: 분기점·거래량+50%·신고가 임박)
 * - verdict: HOLD / WATCH / TRIM / SELL
 *
 * 8주 룰은 patience 페이지에서 다룸 (strategy 페이지에서 제외).
 *
 * 데이터 소스: 네이버 dayCandle (m.stock.naver.com) — 매수일 캔들·이평선·신고가
 * 참고: scripts/update-journal-sell-triggers.ts 의 fetchCandles() 패턴 재사용
 */
import fs from "fs";
import path from "path";

const UA_MOBILE =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15";
const REFERER_M = "https://m.stock.naver.com/";

// Phase 2: SK하이닉스 단일 종목 한정. Phase 3에서 holdings 전체로 확장.
const TARGET_CODES = ["000660"];

const CUT_LOSS_RATIO = 0.92; // -8%
const TAKE_PROFIT_1_RATIO = 1.2; // +20%
const TAKE_PROFIT_2_RATIO = 1.25; // +25%
const ADD_BUY_LIMIT_RATIO = 1.05; // +5%

// 매수 진입 정확도 책 기준 cutoff
const CHASE_INTRADAY_HIGH_CUTOFF = 0.95; // 매수가 / 일중 고점 ≥ 95% = 추격

const VOLUME_SURGE_RATIO = 1.5; // 매수일 거래량 ≥ 60일 평균 × 1.5 = 책 기준 +50% 동반

// 정밀 분기점 인식 파라미터
const BASE_MIN_DAYS = 25; // 5주 = base 최소 형성 기간
const BASE_MAX_DAYS = 240; // 약 12개월
const BASE_BREACH_TOLERANCE = 1.02; // 좌측 고점의 102%까지는 base 유지로 봄
const BASE_DEPTH_MIN = 0.05; // base 깊이 5% 미만은 너무 얕음 (모양 형성 안 됨)
const BASE_DEPTH_MAX = 0.40; // base 깊이 40% 초과는 너무 깊음 (책 기준 12~33% 정상)
const PIVOT_BUY_BAND = 0.05; // 분기점 +5% 이내 매수 = 정확한 분기점 매수

interface Transaction {
  id: number;
  date: string; // YYYY-MM-DD
  type: "매수" | "매도";
  code: string;
  name: string;
  quantity: number;
  price: number;
}

interface Holding {
  code: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  high_price?: number;
  high_price_date?: string;
  sector?: string;
}

interface JournalData {
  holdings: Holding[];
  transactions: Transaction[];
}

interface PriceInfo {
  localDate?: string;
  closePrice?: number;
  highPrice?: number;
  lowPrice?: number;
  openPrice?: number;
  accumulatedTradingVolume?: number;
}

interface ChartResp {
  priceInfos?: PriceInfo[];
}

interface BreakoutQuality {
  has_valid_base: boolean;
  base_left_high_date: string | null;
  base_left_high_price: number | null;
  base_low_price: number | null;
  base_depth_pct: number | null;
  base_days: number | null;
  pivot_price: number | null; // = base_left_high_price (저항선)
  vs_pivot_pct: number | null; // (매수가 - 분기점) / 분기점 × 100
  within_5pct_of_pivot: boolean; // 분기점 0~+5% 이내 = 정확한 분기점 매수
  no_base_reason: string | null; // base 없을 때 사유
}

interface EntryQuality {
  entry_date: string;
  entry_close: number | null;
  entry_high: number | null;
  entry_low: number | null;
  entry_volume: number | null;
  vs_close_pct: number | null;
  vs_high_ratio: number | null;
  avg_volume_60d: number | null;
  volume_ratio: number | null;
  prior_high_52w: number | null;
  prior_high_52w_date: string | null;
  vs_prior_high_ratio: number | null;
  checks: {
    chased_intraday_high: boolean;
    volume_surge_50pct: boolean;
    near_breakout: boolean; // 단순 근사 (직전 52주 신고가 95%+)
  };
  breakout: BreakoutQuality;
  grade: {
    label: "정확한 진입" | "부분 통과" | "잘못된 진입";
    book_checks_passed: number; // 0~3
    book_checks_total: number; // 3
  };
}

interface StrategyEval {
  cut_loss_price: number;
  take_profit_1_price: number;
  take_profit_2_price: number;
  add_buy_limit_price: number;
  can_add_buy: boolean;
  rule_checks: {
    cut_loss_hit: boolean;
    take_profit_1_hit: boolean;
    take_profit_2_hit: boolean;
    add_buy_blocked: boolean;
  };
  entry_quality: EntryQuality | null;
}

interface Verdict {
  verdict: "HOLD" | "BAD_ENTRY" | "WATCH" | "TRIM" | "SELL";
  reasons: string[];
}

interface HoldingResult {
  code: string;
  name: string;
  sector?: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  profit_pct: number;
  eval_amount: number;
  position_start_date: string | null;
  holding_days: number;
  holding_weeks: number;
  high_price?: number;
  high_price_date?: string;
  ma50: number | null;
  ma200: number | null;
  strategy: StrategyEval;
  strategy_verdict: Verdict;
}

interface SellSignalsOutput {
  generated_at: string;
  target_codes: string[];
  holdings: HoldingResult[];
}

async function fetchCandles(
  code: string,
  count: number = 220,
): Promise<PriceInfo[]> {
  const url = `https://api.stock.naver.com/chart/domestic/item/${code}?periodType=dayCandle&count=${count}`;
  const res = await fetch(url, {
    headers: { "User-Agent": UA_MOBILE, Referer: REFERER_M },
  });
  if (!res.ok) throw new Error(`네이버 캔들 실패 (${code}): ${res.status}`);
  const json = (await res.json()) as ChartResp;
  return (json.priceInfos ?? []).filter(
    (p) => p.localDate && p.closePrice != null,
  );
}

function todayKstISO(): string {
  // KST = UTC+9. Node 환경의 timezone에 의존하지 않도록 명시 변환.
  const now = new Date(Date.now() + 9 * 3600 * 1000);
  return now.toISOString().slice(0, 10);
}

function daysBetween(isoFrom: string, isoTo: string): number {
  const a = new Date(isoFrom + "T00:00:00Z").getTime();
  const b = new Date(isoTo + "T00:00:00Z").getTime();
  return Math.floor((b - a) / 86400000);
}

/**
 * 현재 보유 포지션의 시작일 산출.
 *
 * 정의: transactions를 날짜별 net delta로 묶어 누적 잔량을 계산하고,
 *   누적이 0인 상태에서 net 매수가 발생한 가장 최근 날짜.
 *
 * 같은 날 스캘핑 매수·매도 페어(net=0)는 잔량에 영향 없음. 따라서
 *   부분매도 → 전량매도 → 재매수 흐름에서 재매수 날짜가 정확히 잡힘.
 */
function computeCurrentPositionStartDate(
  transactions: Transaction[],
  code: string,
): string | null {
  const txs = transactions.filter((t) => t.code === code);
  const dailyNet = new Map<string, number>();
  for (const t of txs) {
    const delta = t.type === "매수" ? t.quantity : -t.quantity;
    dailyNet.set(t.date, (dailyNet.get(t.date) ?? 0) + delta);
  }
  const dates = Array.from(dailyNet.keys()).sort();
  let cum = 0;
  let firstBuyDate: string | null = null;
  for (const date of dates) {
    const net = dailyNet.get(date)!;
    if (cum === 0 && net > 0) firstBuyDate = date;
    cum += net;
    if (cum <= 0) {
      cum = 0;
      firstBuyDate = null;
    }
  }
  return firstBuyDate;
}

function mean(arr: number[]): number {
  return arr.reduce((s, v) => s + v, 0) / arr.length;
}

/**
 * 매수 시점 이전 데이터에서 적절한 base(모양)와 분기점(pivot)을 자동 인식.
 *
 * 책 기준 base 정의:
 * - 좌측 고점(left side high) 이후 매수일까지 일정 기간 횡보·조정
 * - 좌측 고점은 매수일에서 5주(25일) 이상 이전
 * - 좌측 고점 이후 매수일까지 그 고점이 깨지지 않음 (저항선 유지, 2% 여유)
 * - base 깊이 = (좌측고점 - 최저점) / 좌측고점, 5%~40% 범위 (책 12~33% 정상)
 * - 분기점 = 좌측 고점 (저항선 돌파 = 본격 상승 시작)
 *
 * 가장 entry_idx에 가까운(즉 가장 최근) 유효 base를 선택.
 */
function findBase(candles: PriceInfo[], entryIdx: number): BreakoutQuality {
  const empty: BreakoutQuality = {
    has_valid_base: false,
    base_left_high_date: null,
    base_left_high_price: null,
    base_low_price: null,
    base_depth_pct: null,
    base_days: null,
    pivot_price: null,
    vs_pivot_pct: null,
    within_5pct_of_pivot: false,
    no_base_reason: null,
  };

  if (entryIdx < BASE_MIN_DAYS) {
    return { ...empty, no_base_reason: "캔들 이력 부족 (5주 미만)" };
  }

  const oldestIdx = Math.max(0, entryIdx - BASE_MAX_DAYS);

  // i = entryIdx - 25부터 거꾸로 (가장 최근 base를 우선)
  for (let i = entryIdx - BASE_MIN_DAYS; i >= oldestIdx; i--) {
    const leftHigh = candles[i].highPrice;
    if (!leftHigh || leftHigh <= 0) continue;

    // i+1 ~ entryIdx-1 사이에서 leftHigh의 102% 초과 high가 나오면 base 깨짐
    let breached = false;
    let periodLow = Infinity;
    for (let j = i + 1; j < entryIdx; j++) {
      const h = candles[j].highPrice ?? 0;
      const l = candles[j].lowPrice ?? Infinity;
      if (h > leftHigh * BASE_BREACH_TOLERANCE) {
        breached = true;
        break;
      }
      if (l < periodLow) periodLow = l;
    }
    if (breached || periodLow === Infinity) continue;

    const depth = (leftHigh - periodLow) / leftHigh;
    if (depth < BASE_DEPTH_MIN || depth > BASE_DEPTH_MAX) continue;

    const leftHighDateRaw = candles[i].localDate ?? null;
    return {
      has_valid_base: true,
      base_left_high_date: leftHighDateRaw
        ? `${leftHighDateRaw.slice(0, 4)}-${leftHighDateRaw.slice(4, 6)}-${leftHighDateRaw.slice(6, 8)}`
        : null,
      base_left_high_price: leftHigh,
      base_low_price: periodLow,
      base_depth_pct: parseFloat((depth * 100).toFixed(2)),
      base_days: entryIdx - i,
      pivot_price: leftHigh,
      vs_pivot_pct: null, // 호출자에서 채움
      within_5pct_of_pivot: false, // 호출자에서 채움
      no_base_reason: null,
    };
  }

  // base 없음 사유 추정
  const recentMax = Math.max(
    ...candles
      .slice(Math.max(0, entryIdx - BASE_MIN_DAYS), entryIdx)
      .map((c) => c.highPrice ?? 0),
  );
  const olderMax = Math.max(
    ...candles
      .slice(oldestIdx, Math.max(0, entryIdx - BASE_MIN_DAYS))
      .map((c) => c.highPrice ?? 0),
  );
  let reason: string;
  if (recentMax > olderMax * BASE_BREACH_TOLERANCE) {
    reason = "최근 5주 내 신고가 갱신 — 횡보·조정 없는 모멘텀 추격";
  } else {
    reason = "유효한 모양 형성 안 됨 (깊이 5~40% 또는 5주+ 조건 미달)";
  }
  return { ...empty, no_base_reason: reason };
}

function computeEntryQuality(
  avgPrice: number,
  entryDate: string,
  candles: PriceInfo[],
): EntryQuality | null {
  const yyyymmdd = entryDate.replace(/-/g, "");
  const idx = candles.findIndex((c) => c.localDate === yyyymmdd);
  if (idx < 0) {
    return {
      entry_date: entryDate,
      entry_close: null,
      entry_high: null,
      entry_low: null,
      entry_volume: null,
      vs_close_pct: null,
      vs_high_ratio: null,
      avg_volume_60d: null,
      volume_ratio: null,
      prior_high_52w: null,
      prior_high_52w_date: null,
      vs_prior_high_ratio: null,
      checks: {
        chased_intraday_high: false,
        volume_surge_50pct: false,
        near_breakout: false,
      },
      breakout: {
        has_valid_base: false,
        base_left_high_date: null,
        base_left_high_price: null,
        base_low_price: null,
        base_depth_pct: null,
        base_days: null,
        pivot_price: null,
        vs_pivot_pct: null,
        within_5pct_of_pivot: false,
        no_base_reason: "매수일 캔들 데이터 없음",
      },
      grade: {
        label: "잘못된 진입",
        book_checks_passed: 0,
        book_checks_total: 3,
      },
    };
  }
  const entry = candles[idx];
  const entryClose = entry.closePrice ?? null;
  const entryHigh = entry.highPrice ?? null;
  const entryLow = entry.lowPrice ?? null;
  const entryVol = entry.accumulatedTradingVolume ?? null;

  const vsClosePct =
    entryClose != null && entryClose > 0
      ? ((avgPrice - entryClose) / entryClose) * 100
      : null;
  const vsHighRatio =
    entryHigh != null && entryHigh > 0 ? avgPrice / entryHigh : null;

  // 매수 직전 60일 평균 거래량
  const priorWindow = candles.slice(Math.max(0, idx - 60), idx);
  const priorVols = priorWindow
    .map((c) => c.accumulatedTradingVolume ?? 0)
    .filter((v) => v > 0);
  const avgVol60 = priorVols.length > 0 ? mean(priorVols) : null;
  const volRatio =
    entryVol != null && avgVol60 != null && avgVol60 > 0
      ? entryVol / avgVol60
      : null;

  // 매수 직전 52주 신고가 (240 영업일 ≈ 1년)
  const priorYear = candles.slice(Math.max(0, idx - 240), idx);
  let priorHigh = 0;
  let priorHighDate: string | null = null;
  for (const c of priorYear) {
    if ((c.highPrice ?? 0) > priorHigh) {
      priorHigh = c.highPrice!;
      priorHighDate = c.localDate ?? null;
    }
  }
  const priorHigh52w = priorHigh > 0 ? priorHigh : null;
  const vsPriorHighRatio = priorHigh52w ? avgPrice / priorHigh52w : null;

  // 정밀 분기점 인식
  const breakoutBase = findBase(candles, idx);
  let withinPivot = false;
  let vsPivotPct: number | null = null;
  if (breakoutBase.has_valid_base && breakoutBase.pivot_price) {
    vsPivotPct = ((avgPrice - breakoutBase.pivot_price) / breakoutBase.pivot_price) * 100;
    withinPivot = vsPivotPct >= 0 && vsPivotPct <= PIVOT_BUY_BAND * 100;
  }
  const breakout: BreakoutQuality = {
    ...breakoutBase,
    vs_pivot_pct: vsPivotPct != null ? parseFloat(vsPivotPct.toFixed(2)) : null,
    within_5pct_of_pivot: withinPivot,
  };

  // 책 기준 3 cutoff 진입 등급
  const chased =
    vsHighRatio != null && vsHighRatio >= CHASE_INTRADAY_HIGH_CUTOFF;
  const volSurge = volRatio != null && volRatio >= VOLUME_SURGE_RATIO;
  const exactPivot = withinPivot;

  const checks3 = [exactPivot, volSurge, !chased];
  const passed = checks3.filter(Boolean).length;
  let label: "정확한 진입" | "부분 통과" | "잘못된 진입";
  if (exactPivot && passed === 3) {
    label = "정확한 진입";
  } else if (exactPivot) {
    label = "부분 통과"; // 분기점 매수했으나 거래량 또는 추격 1개 미충족
  } else {
    label = "잘못된 진입"; // 분기점 매수 자체가 아님
  }

  return {
    entry_date: entryDate,
    entry_close: entryClose,
    entry_high: entryHigh,
    entry_low: entryLow,
    entry_volume: entryVol,
    vs_close_pct: vsClosePct != null ? parseFloat(vsClosePct.toFixed(2)) : null,
    vs_high_ratio:
      vsHighRatio != null ? parseFloat(vsHighRatio.toFixed(4)) : null,
    avg_volume_60d: avgVol60 != null ? Math.round(avgVol60) : null,
    volume_ratio: volRatio != null ? parseFloat(volRatio.toFixed(2)) : null,
    prior_high_52w: priorHigh52w,
    prior_high_52w_date: priorHighDate
      ? `${priorHighDate.slice(0, 4)}-${priorHighDate.slice(4, 6)}-${priorHighDate.slice(6, 8)}`
      : null,
    vs_prior_high_ratio:
      vsPriorHighRatio != null
        ? parseFloat(vsPriorHighRatio.toFixed(4))
        : null,
    checks: {
      chased_intraday_high: chased,
      volume_surge_50pct: volSurge,
      near_breakout:
        vsPriorHighRatio != null && vsPriorHighRatio >= 0.95,
    },
    breakout,
    grade: { label, book_checks_passed: passed, book_checks_total: 3 },
  };
}

function evaluateStrategy(
  h: Holding,
  entryQuality: EntryQuality | null,
): StrategyEval {
  const cutLoss = Math.round(h.avg_price * CUT_LOSS_RATIO);
  const tp1 = Math.round(h.avg_price * TAKE_PROFIT_1_RATIO);
  const tp2 = Math.round(h.avg_price * TAKE_PROFIT_2_RATIO);
  const addLimit = Math.round(h.avg_price * ADD_BUY_LIMIT_RATIO);

  const canAddBuy = h.current_price <= addLimit;

  return {
    cut_loss_price: cutLoss,
    take_profit_1_price: tp1,
    take_profit_2_price: tp2,
    add_buy_limit_price: addLimit,
    can_add_buy: canAddBuy,
    rule_checks: {
      cut_loss_hit: h.current_price <= cutLoss,
      take_profit_1_hit: h.current_price >= tp1,
      take_profit_2_hit: h.current_price >= tp2,
      add_buy_blocked: !canAddBuy,
    },
    entry_quality: entryQuality,
  };
}

function determineStrategyVerdict(
  profitPct: number,
  s: StrategyEval,
): Verdict {
  const reasons: string[] = [];
  let verdict: Verdict["verdict"] = "HOLD";

  // 1순위: 손절 (책 2범주)
  if (s.rule_checks.cut_loss_hit) {
    verdict = "SELL";
    reasons.push(
      `매수가 대비 ${profitPct.toFixed(1)}% — 책 기준 -7~8% 손절선 도달, 무조건 손절`,
    );
    return { verdict, reasons };
  }

  // 2순위: 익절
  if (s.rule_checks.take_profit_2_hit) {
    verdict = "TRIM";
    reasons.push(
      `+${profitPct.toFixed(1)}% 익절선 2차(+25%) 도달 — 분할 매도 권장 (강력 종목 여부는 인내 보유 페이지 참조)`,
    );
  } else if (s.rule_checks.take_profit_1_hit) {
    verdict = "TRIM";
    reasons.push(
      `+${profitPct.toFixed(1)}% 익절선 1차(+20%) 진입 — 분할 매도 검토 (강력 종목 여부는 인내 보유 페이지 참조)`,
    );
  }

  // 3순위: 손절선 접근 (WATCH)
  if (verdict === "HOLD" && profitPct <= -5) {
    verdict = "WATCH";
    reasons.push(
      `매수가 대비 ${profitPct.toFixed(1)}% — 손절선 -8% 접근 중, 추세 깨졌으면 미리 손절 가능`,
    );
  }

  // 4순위: 잘못된 진입 (BAD_ENTRY) — HOLD 상태인 종목에 한정
  //   진입이 책 기준에 안 맞고(분기점 매수 아님) 손익이 -5%~+20% 사이라면
  //   "지금 매도 아깝지만 매도 종목에 가까움" 분류
  const eq = s.entry_quality;
  if (
    verdict === "HOLD" &&
    eq &&
    eq.grade.label === "잘못된 진입" &&
    profitPct > -5 &&
    profitPct < 20
  ) {
    verdict = "BAD_ENTRY";
    const reason = eq.breakout.no_base_reason
      ? `진입 시점에 적절한 모양(base)이 없었음 — ${eq.breakout.no_base_reason}`
      : eq.breakout.pivot_price && eq.breakout.vs_pivot_pct != null
        ? `분기점 ${eq.breakout.pivot_price.toLocaleString()}원 대비 ${eq.breakout.vs_pivot_pct >= 0 ? "+" : ""}${eq.breakout.vs_pivot_pct.toFixed(1)}% 매수 — 책 기준 ±5% 이내 위반`
        : "정확한 분기점 매수가 아님";
    reasons.push(`잘못 매수한 종목 (${reason})`);
    reasons.push(
      "권장 액션: 본전 회복 시 즉시 매도 또는 손절선 도달까지 대기. 닻 내림 효과 주의 — '지금 이 가격에 새로 산다면 살 것인가?'로 재평가.",
    );
  }

  // 진입 정확도 경고 (verdict와 무관하게 항상 reason 추가)
  if (eq && eq.checks.chased_intraday_high && verdict !== "BAD_ENTRY") {
    reasons.push(
      `매수 진입이 일중 고점 ${((eq.vs_high_ratio ?? 0) * 100).toFixed(1)}% — 추격 매수 경고`,
    );
  }

  // 추가매수 게이트 (책 4범주, 보조 안내)
  if (s.rule_checks.add_buy_blocked && profitPct < 20 && verdict === "HOLD") {
    reasons.push(`현재가가 매수가 +5% 이상 — 추가 매수 금지 (책 기준)`);
  }

  // 보유 인내 기본
  if (verdict === "HOLD" && reasons.length === 0) {
    reasons.push(
      `매수가 대비 ${profitPct >= 0 ? "+" : ""}${profitPct.toFixed(1)}% — 손절·익절선 사이, 정확한 진입 + 인내 보유`,
    );
  }

  return { verdict, reasons };
}

async function main() {
  const journalPath = path.join(process.cwd(), "public", "data", "journal.json");
  const journal = JSON.parse(fs.readFileSync(journalPath, "utf-8")) as JournalData;

  const targets = journal.holdings.filter((h) => TARGET_CODES.includes(h.code));
  if (targets.length === 0) {
    console.error("대상 종목이 holdings에 없음:", TARGET_CODES);
    process.exit(1);
  }

  const today = todayKstISO();
  console.log(`[compute-sell-signals] 기준일 ${today}, 대상 ${targets.length}종목\n`);

  const results: HoldingResult[] = [];

  for (const h of targets) {
    console.log(`[${h.code} ${h.name}] 처리 시작`);

    // 1) 네이버 캔들
    const candles = await fetchCandles(h.code, 220);
    if (candles.length === 0) {
      console.warn(`  캔들 데이터 없음 — 스킵`);
      continue;
    }
    candles.sort((a, b) =>
      (a.localDate ?? "").localeCompare(b.localDate ?? ""),
    );
    const closes = candles
      .map((c) => c.closePrice ?? 0)
      .filter((v) => v > 0);
    const ma50 = closes.length >= 50 ? mean(closes.slice(-50)) : null;
    const ma200 = closes.length >= 200 ? mean(closes.slice(-200)) : null;

    // 2) 현재 포지션 시작일 + 보유 주차
    const positionStart = computeCurrentPositionStartDate(
      journal.transactions,
      h.code,
    );
    const holdingDays = positionStart ? daysBetween(positionStart, today) : 0;
    const holdingWeeks = holdingDays / 7;

    // 3) 매수 진입 정확도 (책 기준: 분기점·거래량+50%·신고가 임박)
    const entryQuality = positionStart
      ? computeEntryQuality(h.avg_price, positionStart, candles)
      : null;

    // 4) 손익률 + strategy 평가
    const profitPct = ((h.current_price - h.avg_price) / h.avg_price) * 100;
    const strategy = evaluateStrategy(h, entryQuality);
    const strategyVerdict = determineStrategyVerdict(profitPct, strategy);

    const result: HoldingResult = {
      code: h.code,
      name: h.name,
      sector: h.sector,
      quantity: h.quantity,
      avg_price: h.avg_price,
      current_price: h.current_price,
      profit_pct: parseFloat(profitPct.toFixed(2)),
      eval_amount: h.current_price * h.quantity,
      position_start_date: positionStart,
      holding_days: holdingDays,
      holding_weeks: parseFloat(holdingWeeks.toFixed(2)),
      high_price: h.high_price,
      high_price_date: h.high_price_date,
      ma50: ma50 != null ? Math.round(ma50) : null,
      ma200: ma200 != null ? Math.round(ma200) : null,
      strategy,
      strategy_verdict: strategyVerdict,
    };

    results.push(result);

    console.log(
      `  매수가 ${h.avg_price.toLocaleString()} / 현재가 ${h.current_price.toLocaleString()} (${profitPct >= 0 ? "+" : ""}${profitPct.toFixed(2)}%)`,
    );
    console.log(
      `  포지션 시작 ${positionStart ?? "-"} (${holdingDays}일 = ${holdingWeeks.toFixed(2)}주)`,
    );
    console.log(
      `  손절 ${strategy.cut_loss_price.toLocaleString()} / 익절1 ${strategy.take_profit_1_price.toLocaleString()} / 익절2 ${strategy.take_profit_2_price.toLocaleString()}`,
    );
    if (entryQuality && entryQuality.entry_close != null) {
      console.log(
        `  매수 진입: 종가 ${entryQuality.entry_close.toLocaleString()} 대비 ${entryQuality.vs_close_pct != null && entryQuality.vs_close_pct >= 0 ? "+" : ""}${entryQuality.vs_close_pct?.toFixed(2)}% / 일중 고점 ${((entryQuality.vs_high_ratio ?? 0) * 100).toFixed(1)}% / 거래량 ${entryQuality.volume_ratio?.toFixed(2)}배`,
      );
      const b = entryQuality.breakout;
      if (b.has_valid_base && b.pivot_price) {
        console.log(
          `  분기점 인식: ✓ 좌측 고점 ${b.pivot_price.toLocaleString()}원 (${b.base_left_high_date}, ${b.base_days}일 base, 깊이 ${b.base_depth_pct}%) / 매수가 vs 분기점 ${(entryQuality.breakout.vs_pivot_pct ?? 0) >= 0 ? "+" : ""}${entryQuality.breakout.vs_pivot_pct}% / ±5% 이내 ${b.within_5pct_of_pivot ? "✓" : "✗"}`,
        );
      } else {
        console.log(`  분기점 인식: ✗ ${b.no_base_reason}`);
      }
      console.log(
        `  진입 등급: ${entryQuality.grade.label} (${entryQuality.grade.book_checks_passed}/${entryQuality.grade.book_checks_total} 통과)`,
      );
    }
    console.log(
      `  50일선 ${ma50 != null ? Math.round(ma50).toLocaleString() : "-"} / 200일선 ${ma200 != null ? Math.round(ma200).toLocaleString() : "-"}`,
    );
    console.log(
      `  verdict: ${strategyVerdict.verdict} — ${strategyVerdict.reasons.join("; ")}`,
    );
  }

  const output: SellSignalsOutput = {
    generated_at: new Date().toISOString(),
    target_codes: TARGET_CODES,
    holdings: results,
  };

  const outputPath = path.join(
    process.cwd(),
    "public",
    "data",
    "sell-signals.json",
  );
  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2) + "\n");
  console.log(`\n[완료] ${outputPath}`);
}

main().catch((e) => {
  console.error("[compute-sell-signals] 실패:", e);
  process.exit(1);
});
