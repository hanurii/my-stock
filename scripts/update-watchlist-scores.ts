/**
 * 워치리스트 & 오일전문가 포트폴리오 시세 자동 업데이트 스크립트
 *
 * - 국내 종목: DART 확정 실적 (PER/PBR) + 네이버 금융 (가격/배당/시총/외인)
 * - 해외 종목: Yahoo Finance v10 quoteSummary (crumb/cookie 인증)
 * - 동일 종목은 한 번만 조회하여 양쪽에 재활용
 * - 점수 변화 시 previous_score/previous_rank/grade_change_reason 자동 갱신
 *
 * 사용법: npx tsx scripts/update-watchlist-scores.ts
 */
import fs from "fs";
import path from "path";
import {
  scoreDomestic,
  scoreOverseas,
  scoreGrowth,
  scoreGrowthScreen,
  getGrade,
  type DomesticStockInput,
  type OverseasStockInput,
  type GrowthStockInput,
  type GrowthScreenInput,
  type ScoredResult,
} from "../src/lib/scoring";
import { loadShareholderReturnMap, invalidateShareholderCache } from "./load-shareholder-returns";

// ── 설정 ──

const NAVER_API = "https://m.stock.naver.com/api/stock";
const DART_API = "https://opendart.fss.or.kr/api";
const DART_API_KEY = process.env.DART_API_KEY || "";
const YAHOO_SUMMARY = "https://query2.finance.yahoo.com/v10/finance/quoteSummary";
const YAHOO_CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb";
const YAHOO_COOKIE_URL = "https://fc.yahoo.com/curveball";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
const REQUEST_DELAY_MS = 1000;

// ── 타입 ──

interface MarketData {
  price?: number;
  per: number | null;
  pbr: number;
  dividend_yield: number;
  market_cap?: number | null;         // 시가총액 (억원)
  foreign_ownership?: number | null;  // 외국인 보유비중 (%)
  prev_year_op_margin?: number | null; // 전년 영업이익률 (finance/annual에서 추출)
}

interface StockBase {
  code: string;
  name: string;
  per: number | null;
  pbr: number;
  dividend_yield: number;
  scored_at: string;
  current_price_at_scoring?: number;
  previous_score?: number;
  previous_rank?: number;
  grade_change_reason?: string;
  [key: string]: unknown;
}

// Yahoo 심볼 매핑 (코드 → Yahoo 심볼)
const YAHOO_SYMBOL_MAP: Record<string, string> = {
  "PBR.A": "PBR-A",
  "LGEN": "LGEN.L",
  "AV.": "AV.L",
};

// ── 유틸 ──

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const fmt = (n: number | null | undefined): string =>
  n == null ? "—" : n.toLocaleString();

const diff = (a: number | null, b: number | null): string => {
  if (a == null || b == null) return "—";
  const d = b - a;
  const sign = d >= 0 ? "+" : "";
  return `${sign}${d.toFixed(2)}`;
};

function parseNumber(value: string | undefined): number | null {
  if (!value) return null;
  const cleaned = value.replace(/[^0-9.\-]/g, "");
  const num = parseFloat(cleaned);
  return isNaN(num) ? null : num;
}

// ── 네이버 금융 API (국내) ──

async function fetchFromNaver(code: string): Promise<MarketData | null> {
  try {
    // basic API에서 오늘 종가 조회
    const basicRes = await fetch(`${NAVER_API}/${code}/basic`, {
      headers: { "User-Agent": UA },
    });
    const basicJson = basicRes.ok ? await basicRes.json() : null;
    const todayClose = basicJson?.closePrice
      ? parseNumber(String(basicJson.closePrice))
      : null;

    // integration API에서 PER/PBR/배당수익률 조회
    const url = `${NAVER_API}/${code}/integration`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;

    const json = await res.json();
    const infos: { key: string; value: string }[] = json.totalInfos || [];
    const get = (key: string) => infos.find((i) => i.key === key)?.value;

    // 오늘 종가 우선, 없으면 전일 종가
    const finalPrice = todayClose || parseNumber(get("전일"));
    if (!finalPrice) return null;

    let per = parseNumber(get("PER"));
    let pbr = parseNumber(get("PBR"));
    const dividendYield = parseNumber(get("배당수익률"));

    // PER/PBR이 N/A인 경우 finance/annual에서 직접 계산 + 전년 영업이익률 추출
    let prevYearOpMargin: number | null = null;
    if (per == null || pbr == null || pbr === 0) {
      const fallback = await fetchFundamentalsFromNaver(code, finalPrice);
      if (fallback) {
        if (per == null && fallback.per != null) per = fallback.per;
        if ((pbr == null || pbr === 0) && fallback.pbr > 0) pbr = fallback.pbr;
        if (fallback.prev_year_op_margin != null) prevYearOpMargin = fallback.prev_year_op_margin;
      }
    }

    // 시가총액: "73조 7,046억" → 억원 단위로 파싱
    const marketCapStr = get("시총");
    let marketCap: number | null = null;
    if (marketCapStr) {
      let total = 0;
      const joMatch = marketCapStr.match(/([\d,]+)조/);
      const eokMatch = marketCapStr.match(/([\d,]+)억/);
      if (joMatch) total += parseFloat(joMatch[1].replace(/,/g, "")) * 10000;
      if (eokMatch) total += parseFloat(eokMatch[1].replace(/,/g, ""));
      if (total > 0) marketCap = Math.round(total);
    }

    // 외국인 보유비중: "49.89%" → 49.89
    const foreignOwnership = parseNumber(get("외인소진율"));

    return { price: finalPrice, per, pbr: pbr ?? 0, dividend_yield: dividendYield ?? 0, market_cap: marketCap, foreign_ownership: foreignOwnership, prev_year_op_margin: prevYearOpMargin };
  } catch {
    return null;
  }
}

async function fetchFundamentalsFromNaver(
  code: string,
  price: number,
): Promise<{ per: number | null; pbr: number; prev_year_op_margin?: number | null } | null> {
  try {
    const url = `${NAVER_API}/${code}/finance/annual`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;

    const json = await res.json();
    const periods = json.financeInfo?.trTitleList as
      | { key: string; isConsensus: string }[]
      | undefined;
    const rows = json.financeInfo?.rowList as
      | { title: string; columns: Record<string, { value: string }> }[]
      | undefined;
    if (!periods || !rows) return null;

    const confirmedAll = [...periods].filter((p) => p.isConsensus === "N");
    const confirmed = confirmedAll[confirmedAll.length - 1];
    if (!confirmed) return null;

    const getValue = (title: string, periodKey: string): number | null => {
      const row = rows.find((r) => r.title === title);
      return parseNumber(row?.columns[periodKey]?.value);
    };

    const eps = getValue("EPS", confirmed.key);
    const bps = getValue("BPS", confirmed.key);
    const per = eps && eps > 0 ? parseFloat((price / eps).toFixed(2)) : null;
    const pbr = bps && bps > 0 ? parseFloat((price / bps).toFixed(2)) : 0;

    // 전년 영업이익률도 함께 추출 (별도 API 호출 불필요)
    let prevYearOpMargin: number | null = null;
    if (confirmedAll.length >= 2) {
      const prevYear = confirmedAll[confirmedAll.length - 2];
      prevYearOpMargin = getValue("영업이익률", prevYear.key);
    }

    if (per != null || pbr > 0) {
      console.log(
        `   📈 finance/annual fallback (${confirmed.key}): EPS ${fmt(eps)} BPS ${fmt(bps)} → PER ${fmt(per)} PBR ${pbr}`,
      );
    }
    return { per, pbr, prev_year_op_margin: prevYearOpMargin };
  } catch {
    return null;
  }
}

// ── DART 확정 실적 (국내 PER/PBR) ──

import { loadCorpCodeMap } from "./fetch-shareholder-returns";

let corpCodeMap: Map<string, string> | null = null;

async function ensureCorpCodeMap(): Promise<Map<string, string>> {
  if (!corpCodeMap) {
    corpCodeMap = await loadCorpCodeMap();
  }
  return corpCodeMap;
}

interface DartFundamentals {
  per: number | null;
  pbr: number;
  eps: number | null;
  bps: number;
  dividend_yield: number;   // DART 확정 배당수익률 (현재가 기준)
  dps: number;              // 주당배당금
  period: string;           // "FY2025" 등
}

/**
 * DART 확정 실적에서 EPS/BPS/배당 조회하여 PER/PBR 계산.
 * 최신 사업보고서부터 역순 탐색.
 */
async function fetchFundamentalsFromDart(
  stockCode: string,
  price: number,
  isPreferred: boolean = false,
): Promise<DartFundamentals | null> {
  if (!DART_API_KEY) return null;

  const map = await ensureCorpCodeMap();
  // 우선주(코드 끝 5)는 보통주 코드로 매핑 (같은 corp_code)
  const lookupCode = isPreferred ? stockCode.slice(0, 5) + "0" : stockCode;
  const corpCode = map.get(lookupCode);
  if (!corpCode) return null;

  // 최신 사업보고서부터 역순 탐색
  const currentYear = new Date().getFullYear();
  const periods = [
    { year: currentYear - 1, code: "11011", label: `FY${currentYear - 1}`, quarters: 4 },
    { year: currentYear - 2, code: "11011", label: `FY${currentYear - 2}`, quarters: 4 },
  ];

  for (const p of periods) {
    try {
      // 연결재무제표(CFS) 우선, 없으면 별도재무제표(OFS)
      let items: { account_nm: string; thstrm_amount: string; sj_div: string }[] = [];
      let fsDiv = "CFS";

      for (const fs of ["CFS", "OFS"] as const) {
        const url = `${DART_API}/fnlttSinglAcntAll.json?crtfc_key=${DART_API_KEY}&corp_code=${corpCode}&bsns_year=${p.year}&reprt_code=${p.code}&fs_div=${fs}`;
        const res = await fetch(url);
        if (!res.ok) continue;
        const data = await res.json();
        if (data.status === "000") {
          items = data.list;
          fsDiv = fs;
          break;
        }
        await sleep(300);
      }
      if (items.length === 0) continue;

      // EPS 탐색 (다양한 항목명 대응)
      // "이익" 또는 "손익" 매칭 (DART 항목명이 종목마다 다름)
      const hasEarnings = (nm: string) => nm.includes("이익") || nm.includes("손익");
      const epsSearches = isPreferred
        ? [
            (i: { account_nm: string }) => i.account_nm.includes("우선주") && i.account_nm.includes("주당") && hasEarnings(i.account_nm),
            (i: { account_nm: string }) => i.account_nm.includes("보통주") && i.account_nm.includes("기본") && hasEarnings(i.account_nm) && !i.account_nm.includes("희석"),
            (i: { account_nm: string }) => /기본.*주당/.test(i.account_nm) && hasEarnings(i.account_nm) && !i.account_nm.includes("희석"),
            (i: { account_nm: string }) => /기본.*주당/.test(i.account_nm) && hasEarnings(i.account_nm),
          ]
        : [
            (i: { account_nm: string }) => i.account_nm.includes("보통주") && i.account_nm.includes("기본") && hasEarnings(i.account_nm) && !i.account_nm.includes("희석"),
            (i: { account_nm: string }) => /기본.*주당/.test(i.account_nm) && hasEarnings(i.account_nm) && !i.account_nm.includes("희석"),
            (i: { account_nm: string }) => /기본.*주당/.test(i.account_nm) && hasEarnings(i.account_nm),
          ];

      let epsItem;
      for (const search of epsSearches) {
        epsItem = items.find(search);
        if (epsItem) break;
      }
      if (!epsItem) continue;

      const eps = parseNumber(epsItem.thstrm_amount);
      if (!eps || eps <= 0) continue;

      // BPS: 자본총계 / 발행주식총수 (stockTotqySttus API)
      const equityItem = items.find((i) =>
        i.account_nm.replace(/\s/g, "") === "자본총계" && i.sj_div === "BS",
      );
      const equity = parseNumber(equityItem?.thstrm_amount);

      let bps = 0;
      if (equity && equity > 0) {
        try {
          await sleep(300);
          const sharesUrl = `${DART_API}/stockTotqySttus.json?crtfc_key=${DART_API_KEY}&corp_code=${corpCode}&bsns_year=${p.year}&reprt_code=${p.code}`;
          const sharesRes = await fetch(sharesUrl);
          const sharesData = await sharesRes.json();
          if (sharesData.list) {
            // 보통주 + 우선주 발행주식총수 합산
            const totalRow = sharesData.list.find((r: { se: string }) => r.se === "합계");
            if (totalRow) {
              const totalShares = parseNumber(totalRow.istc_totqy);
              if (totalShares && totalShares > 0) {
                bps = Math.round(equity / totalShares);
              }
            }
          }
        } catch { /* 발행주식수 조회 실패 시 BPS = 0 */ }
      }

      const per = parseFloat((price / eps).toFixed(2));
      const pbr = bps > 0 ? parseFloat((price / bps).toFixed(2)) : 0;

      // 배당 정보 조회 (alotMatter)
      let dps = 0;
      let dividendYield = 0;
      try {
        await sleep(300);
        const divUrl = `${DART_API}/alotMatter.json?crtfc_key=${DART_API_KEY}&corp_code=${corpCode}&bsns_year=${p.year}&reprt_code=11011`;
        const divRes = await fetch(divUrl);
        const divData = await divRes.json();
        if (divData.list) {
          const stockKind = isPreferred ? "우선주" : "보통주";
          const dpsItem = divData.list.find((i: { se: string; stock_knd: string }) =>
            i.se === "주당 현금배당금(원)" && i.stock_knd === stockKind,
          );
          if (dpsItem) {
            dps = parseNumber(dpsItem.thstrm) || 0;
            dividendYield = price > 0 ? parseFloat((dps / price * 100).toFixed(2)) : 0;
          }
        }
      } catch { /* 배당 조회 실패 시 무시 */ }

      console.log(`   📋 DART 확정(${p.label}, ${fsDiv}): EPS ${fmt(eps)} BPS ${fmt(bps)} → PER ${per} PBR ${pbr} | 배당 ${fmt(dps)}원 (${dividendYield}%)`);

      return { per, pbr, eps, bps, dividend_yield: dividendYield, dps, period: p.label };
    } catch {
      continue;
    }
  }

  return null;
}

/**
 * 네이버 finance/annual에서 전년 영업이익률을 조회
 * 확정 실적 기간 중 마지막에서 두 번째(= 전년) 영업이익률을 반환
 */
async function fetchPrevYearOpMargin(code: string): Promise<number | null> {
  try {
    const url = `${NAVER_API}/${code}/finance/annual`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;

    const json = await res.json();
    const periods = json.financeInfo?.trTitleList as
      | { key: string; isConsensus: string }[]
      | undefined;
    const rows = json.financeInfo?.rowList as
      | { title: string; columns: Record<string, { value: string }> }[]
      | undefined;
    if (!periods || !rows) return null;

    // 확정 실적만 필터 (컨센서스 제외)
    const confirmed = periods.filter((p) => p.isConsensus === "N");
    if (confirmed.length < 2) return null;

    // 마지막에서 두 번째 = 전년
    const prevYear = confirmed[confirmed.length - 2];

    // "영업이익률" 행 찾기
    const opMarginRow = rows.find((r) => r.title === "영업이익률");
    if (!opMarginRow) return null;

    const value = parseNumber(opMarginRow.columns[prevYear.key]?.value);
    if (value != null) {
      console.log(`   📊 전년 영업이익률 (${prevYear.key}): ${value}%`);
    }
    return value;
  } catch {
    return null;
  }
}

// ── 성장주 스크리닝 실적 조회 (공시월용) ──

interface ScreenFundamentals {
  revenue_latest: number;
  revenue_prev: number;
  op_profit_latest: number;
  op_profit_prev: number;
  op_margin: number;
  op_margin_prev: number | null;
  profit_years: number;
  eps_current: number | null;
  eps_consensus: number | null;
}

function parseNumStr(s: string | undefined | null): number {
  if (!s || s === "-" || s === "") return 0;
  const m = s.replace(/,/g, "").match(/-?[\d.]+/);
  return m ? Number(m[0]) || 0 : 0;
}

/**
 * 네이버 finance/annual에서 실적 데이터를 조회 (성장주 스크리닝 후보용)
 * screen-growth-full.ts의 fetchPhase2()와 동일한 로직
 */
async function fetchScreenFundamentals(code: string): Promise<ScreenFundamentals | null> {
  try {
    const url = `${NAVER_API}/${code}/finance/annual`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;
    const json = await res.json();

    const periods = json.financeInfo?.trTitleList as { key: string; isConsensus: string }[] | undefined;
    const rows = json.financeInfo?.rowList as { title: string; columns: Record<string, { value: string }> }[] | undefined;
    if (!periods || !rows) return null;

    const confirmed = periods.filter((p: { isConsensus: string }) => p.isConsensus === "N");
    const latest = confirmed[confirmed.length - 1];
    const prev = confirmed[confirmed.length - 2];
    if (!latest) return null;

    const consensus = periods.find((p: { isConsensus: string }) => p.isConsensus === "Y");

    const getValue = (title: string, periodKey: string): number => {
      const row = rows.find((r: { title: string }) => r.title === title);
      return parseNumStr(row?.columns[periodKey]?.value);
    };

    const revLatest = getValue("매출액", latest.key);
    const revPrev = prev ? getValue("매출액", prev.key) : 0;
    const opLatest = getValue("영업이익", latest.key);
    const opPrev = prev ? getValue("영업이익", prev.key) : 0;
    const opMargin = getValue("영업이익률", latest.key);
    const opMarginPrev = prev ? getValue("영업이익률", prev.key) : null;

    const epsRow = rows.find((r: { title: string }) => r.title === "EPS");
    const epsCurrent = epsRow ? parseNumStr(epsRow.columns[latest.key]?.value) : null;
    const epsConsensus = consensus && epsRow ? parseNumStr(epsRow.columns[consensus.key]?.value) : null;

    let profitYears = 0;
    for (let i = confirmed.length - 1; i >= 0; i--) {
      const op = getValue("영업이익", confirmed[i].key);
      if (op > 0) profitYears++;
      else break;
    }

    return {
      revenue_latest: revLatest,
      revenue_prev: revPrev,
      op_profit_latest: opLatest,
      op_profit_prev: opPrev,
      op_margin: opMargin || 0,
      op_margin_prev: opMarginPrev,
      profit_years: profitYears,
      eps_current: epsCurrent && epsCurrent > 0 ? epsCurrent : null,
      eps_consensus: epsConsensus && epsConsensus > 0 ? epsConsensus : null,
    };
  } catch {
    return null;
  }
}

// ── Yahoo Finance API (해외) ──

let yahooCookie: string | null = null;
let yahooCrumb: string | null = null;

async function initYahooAuth(): Promise<boolean> {
  try {
    // Step 1: Get cookie
    const cookieRes = await fetch(YAHOO_COOKIE_URL, {
      headers: { "User-Agent": UA },
      redirect: "manual",
    });
    const setCookie = cookieRes.headers.get("set-cookie");
    if (setCookie) {
      yahooCookie = setCookie.split(";")[0];
    }

    // Step 2: Get crumb
    const crumbRes = await fetch(YAHOO_CRUMB_URL, {
      headers: {
        "User-Agent": UA,
        ...(yahooCookie ? { Cookie: yahooCookie } : {}),
      },
    });
    yahooCrumb = await crumbRes.text();

    return !!yahooCookie && !!yahooCrumb;
  } catch {
    return false;
  }
}

function getYahooSymbol(code: string): string {
  return YAHOO_SYMBOL_MAP[code] || code;
}

async function fetchFromYahoo(code: string, existingPbr: number): Promise<MarketData | null> {
  if (!yahooCookie || !yahooCrumb) return null;

  try {
    const symbol = getYahooSymbol(code);
    const url = `${YAHOO_SUMMARY}/${symbol}?modules=summaryDetail,defaultKeyStatistics,price&crumb=${yahooCrumb}`;
    const res = await fetch(url, {
      headers: { "User-Agent": UA, Cookie: yahooCookie },
    });
    if (!res.ok) return null;

    const json = await res.json();
    const r = json.quoteSummary?.result?.[0];
    if (!r) return null;

    const price = r.price?.regularMarketPrice?.raw;
    const pe = r.summaryDetail?.trailingPE?.raw ?? null;
    let pb = r.defaultKeyStatistics?.priceToBook?.raw ?? 0;
    const divYield = r.summaryDetail?.dividendYield?.raw ?? 0;

    // 영국 주식 PBR 단위 문제 (펜스/파운드 → 100배 이상이면 기존값 유지)
    if (pb > 100) pb = existingPbr;

    return {
      price,
      per: pe != null ? parseFloat(pe.toFixed(2)) : null,
      pbr: pb > 0 ? parseFloat(pb.toFixed(2)) : 0,
      dividend_yield: divYield > 0 ? parseFloat((divYield * 100).toFixed(2)) : 0,
    };
  } catch {
    return null;
  }
}

// ── 채점 & 순위 ──

type ScoreFn = (stocks: StockBase[]) => ScoredAll;

interface ScoredAll {
  scores: number[];
  ranks: number[];
  grades: string[];
  details: ScoredResult["details"][];
}

function scoreAllDomestic(stocks: StockBase[]): ScoredAll {
  const results = stocks.map((s) => scoreDomestic(s as unknown as DomesticStockInput));
  return buildRanks(results);
}

function scoreAllOverseas(stocks: StockBase[]): ScoredAll {
  const results = stocks.map((s) => scoreOverseas(s as unknown as OverseasStockInput));
  return buildRanks(results);
}

// ── 누락 종목 주주환원 데이터 자동 수집 ──

const SH_RETURNS_PATH = path.join(process.cwd(), "public", "data", "shareholder-returns.json");

async function ensureShareholderData(stocks: { code: string; name: string }[]): Promise<void> {
  // 기존 데이터 로드
  let existing: { generated_at: string; description: string; stocks: { code: string }[] };
  try {
    existing = JSON.parse(fs.readFileSync(SH_RETURNS_PATH, "utf-8"));
  } catch {
    existing = { generated_at: "", description: "", stocks: [] };
  }

  const existingCodes = new Set(existing.stocks.map((s) => s.code));
  const missing = stocks.filter((s) => /^\d{6}$/.test(s.code) && !existingCodes.has(s.code));

  if (missing.length === 0) return;

  const dartKey = process.env.DART_API_KEY ?? "";
  if (!dartKey) {
    console.warn(`  ⚠ 주주환원 데이터 누락 ${missing.length}개 종목 — DART_API_KEY 미설정으로 건너뜀`);
    missing.forEach((s) => console.warn(`    · ${s.name}(${s.code})`));
    return;
  }

  console.log(`\n📦 주주환원 데이터 누락 ${missing.length}개 종목 자동 수집`);

  // 기존 캐시된 corpCodeMap 재사용
  const { fetchStockShareholderData } = await import("./fetch-shareholder-returns");
  const corpMap = await ensureCorpCodeMap();

  for (const stock of missing) {
    const corpCode = corpMap.get(stock.code);
    if (!corpCode) {
      console.warn(`  ⚠ ${stock.name}(${stock.code}) — corp_code 매핑 실패, 건너뜀`);
      continue;
    }
    console.log(`  + ${stock.name}(${stock.code}) → corp_code: ${corpCode}`);
    try {
      const data = await fetchStockShareholderData(corpCode, stock.code, stock.name);
      existing.stocks.push(data as typeof existing.stocks[number]);
    } catch (e) {
      console.warn(`  ⚠ ${stock.name} 수집 실패:`, e);
    }
  }

  existing.generated_at = new Date(Date.now() + 9 * 3600_000).toISOString().split("T")[0];
  fs.writeFileSync(SH_RETURNS_PATH, JSON.stringify(existing, null, 2), "utf-8");
  invalidateShareholderCache(); // 새 데이터 반영을 위해 캐시 무효화
  console.log(`  ✓ shareholder-returns.json 업데이트 완료\n`);
}

function makeScoreAllGrowth(baseRate: number): ScoreFn {
  const shReturnMap = loadShareholderReturnMap();
  return (stocks: StockBase[]) => {
    const results = stocks.map((s) => scoreGrowth(s as unknown as GrowthStockInput, baseRate, shReturnMap.get(s.code)));
    return buildRanks(results, true);
  };
}

function buildRanks(results: ScoredResult[], sortByGradeThenScore = false): ScoredAll {
  const scores = results.map((r) => r.score);
  const grades = results.map((r) => r.grade);
  const details = results.map((r) => r.details);
  const indexed = scores.map((score, i) => ({ score, grade: grades[i], i }));
  if (sortByGradeThenScore) {
    const gradeOrder: Record<string, number> = { A: 0, B: 1, C: 2, D: 3 };
    indexed.sort((a, b) => {
      const gDiff = (gradeOrder[a.grade] ?? 9) - (gradeOrder[b.grade] ?? 9);
      return gDiff !== 0 ? gDiff : b.score - a.score;
    });
  } else {
    indexed.sort((a, b) => b.score - a.score);
  }
  const ranks = new Array<number>(scores.length);
  indexed.forEach((item, rank) => { ranks[item.i] = rank + 1; });
  return { scores, ranks, grades, details };
}

/**
 * 업데이트 전후 채점 세부 항목을 비교하여
 * 실제 점수가 변한 항목만 사유로 반환
 */
function buildChangeReason(
  beforeDetails: ScoredResult["details"],
  afterDetails: ScoredResult["details"],
): string {
  const parts: string[] = [];
  for (let i = 0; i < beforeDetails.length; i++) {
    const b = beforeDetails[i];
    const a = afterDetails[i];
    if (b && a && b.score !== a.score) {
      const diff = a.score - b.score;
      const sign = diff > 0 ? "+" : "";
      parts.push(`${a.item} ${b.score}→${a.score}점(${sign}${diff})`);
    }
  }
  return parts.join(", ");
}

// ── 공통 업데이트 로직 ──

interface UpdateResult {
  updated: number;
  skipped: number;
  scoreChanges: number;
  gradeChanges: number;
  rankChanges: number;
}

async function updateStocks(
  stocks: StockBase[],
  fetchFn: (code: string, stock: StockBase) => Promise<MarketData | null>,
  scoreFn: ScoreFn,
  today: string,
  scoredAt: string,
  naverCache: Map<string, MarketData>,
  useDart: boolean = false,
  dartCache?: Map<string, DartFundamentals>,
): Promise<UpdateResult> {
  // Step 1: 업데이트 전 점수/순위 + 이미 오늘 업데이트된 종목 기록
  const before = scoreFn(stocks);
  const alreadyUpdatedToday = stocks.map(
    (s) => s.scored_at.startsWith(today) && s.previous_score != null,
  );

  // Step 2: 시세 업데이트
  let updated = 0;
  let skipped = 0;
  const prevMarketData: { per: number | null; pbr: number; div: number }[] = [];

  for (let i = 0; i < stocks.length; i++) {
    const stock = stocks[i];
    prevMarketData.push({ per: stock.per, pbr: stock.pbr, div: stock.dividend_yield });

    // 캐시 확인 (워치리스트에서 이미 조회한 국내 종목)
    let result = naverCache.get(stock.code) || null;
    if (!result) {
      result = await fetchFn(stock.code, stock);
      if (result) naverCache.set(stock.code, result);
      await sleep(REQUEST_DELAY_MS);
    } else {
      console.log(`   ♻️ 캐시 재활용`);
    }

    if (!result) {
      console.log(`\n❌ ${stock.name} (${stock.code}): 시세 조회 실패 — 건너뜀`);
      skipped++;
      continue;
    }

    // 네이버에서 가격/시총/외인/전년영업이익률 적용
    if (result.price) stock.current_price_at_scoring = result.price;
    if (result.market_cap != null) stock.market_cap = result.market_cap;
    if (result.foreign_ownership != null) stock.foreign_ownership = result.foreign_ownership;
    if (result.prev_year_op_margin != null) stock.prev_year_op_margin = result.prev_year_op_margin;
    stock.scored_at = scoredAt;

    // DART 확정 실적으로 PER/PBR/배당 결정
    let newPer: number | null;
    let newPbr: number;
    let newDiv: number;
    let dataSource = "네이버";

    if (useDart && result.price && result.price > 0) {
      const isPreferred = stock.code.endsWith("5") || stock.code.endsWith("7") || stock.code.endsWith("9");
      // DART 캐시 확인
      let dart = dartCache?.get(stock.code) ?? null;
      if (!dart) {
        await sleep(300);
        dart = await fetchFundamentalsFromDart(stock.code, result.price, isPreferred);
        if (dart && dartCache) dartCache.set(stock.code, dart);
      } else {
        // 캐시된 DART 데이터를 현재 가격으로 PER/PBR 재계산
        if (dart.eps && dart.eps > 0) dart.per = parseFloat((result.price / dart.eps).toFixed(2));
        if (dart.bps > 0) dart.pbr = parseFloat((result.price / dart.bps).toFixed(2));
        if (dart.dps > 0) dart.dividend_yield = parseFloat((dart.dps / result.price * 100).toFixed(2));
      }

      if (dart && dart.per != null) {
        newPer = dart.per;
        newPbr = dart.pbr > 0 ? dart.pbr : (result.pbr > 0 ? result.pbr : stock.pbr);
        newDiv = dart.dividend_yield > 0 ? dart.dividend_yield : result.dividend_yield;
        dataSource = `DART 확정(${dart.period})`;
      } else {
        // DART 실패 → 이전 값 유지
        newPer = stock.per;
        newPbr = stock.pbr;
        newDiv = result.dividend_yield;
        dataSource = "⚠️ DART 실패 — 이전값 유지";
      }
    } else {
      // 해외 종목 등 DART 미사용
      newPer = result.per ?? stock.per;
      newPbr = result.pbr > 0 ? result.pbr : stock.pbr;
      newDiv = result.dividend_yield;
    }

    stock.per = newPer;
    stock.pbr = newPbr;
    stock.dividend_yield = newDiv;

    // estimated 플래그 자동 제거
    if (newPer != null && newPbr > 0) {
      if (stock.estimated) {
        delete stock.estimated;
      }
    }

    if ("fundamentals" in stock) delete stock.fundamentals;

    const priceStr = result.price ? `${fmt(result.price)}` : "";
    console.log(
      `\n✅ ${stock.name} (${stock.code}) ${priceStr} [${dataSource}]`,
    );
    console.log(
      `   PER ${fmt(prevMarketData[i].per)} → ${fmt(newPer)} (${diff(prevMarketData[i].per, newPer)})` +
        ` | PBR ${prevMarketData[i].pbr} → ${newPbr} (${diff(prevMarketData[i].pbr, newPbr)})` +
        ` | 배당률 ${prevMarketData[i].div}% → ${newDiv}% (${diff(prevMarketData[i].div, newDiv)})`,
    );

    updated++;
  }

  // Step 3: 변화 반영
  const after = scoreFn(stocks);
  let gradeChanges = 0;
  let scoreChanges = 0;
  let rankChanges = 0;

  for (let i = 0; i < stocks.length; i++) {
    const stock = stocks[i];

    // 같은 날 중복 실행 시 previous_score/previous_rank를 덮어쓰지 않음
    // (Step 2 전에 scored_at이 이미 오늘이었는지 기준)
    if (!alreadyUpdatedToday[i]) {
      stock.previous_score = before.scores[i];
      stock.previous_rank = before.ranks[i];
    }

    const oldGrade = stock.previous_score != null ? getGrade(stock.previous_score) : before.grades[i];
    const newGrade = after.grades[i];
    const prevScore = stock.previous_score ?? before.scores[i];
    const scoreChanged = prevScore !== after.scores[i];

    if (scoreChanged) {
      const reason = buildChangeReason(
        before.details[i],
        after.details[i],
      );
      stock.grade_change_reason = reason;
      scoreChanges++;

      if (oldGrade !== newGrade) {
        gradeChanges++;
        console.log(`\n🔄 ${stock.name}: ${oldGrade}(${prevScore}점) → ${newGrade}(${after.scores[i]}점) | ${reason}`);
      } else {
        console.log(`\n📝 ${stock.name}: ${prevScore}점 → ${after.scores[i]}점 | ${reason}`);
      }
    } else if (!alreadyUpdatedToday[i]) {
      delete stock.grade_change_reason;
    }

    // 현재 세부 점수 항상 저장 (UI 표시용 + 다음 실행 비교 기준)
    stock.details = after.details[i];
    if (!alreadyUpdatedToday[i]) {
      stock.previous_details = before.details[i];
    }

    const prevRank = stock.previous_rank ?? before.ranks[i];
    if (prevRank !== after.ranks[i]) rankChanges++;
  }

  return { updated, skipped, scoreChanges, gradeChanges, rankChanges };
}

function printSummary(label: string, r: UpdateResult) {
  console.log(
    `💾 ${label}: ${r.updated}개 업데이트, ${r.skipped}개 실패` +
      (r.scoreChanges > 0 ? `, ${r.scoreChanges}개 점수 변화` : "") +
      (r.gradeChanges > 0 ? ` (등급 변화 ${r.gradeChanges}개)` : "") +
      (r.rankChanges > 0 ? `, ${r.rankChanges}개 순위 변동` : ""),
  );
}

// ── 메인 ──

async function main() {
  const kstNow = new Date(Date.now() + 9 * 3600_000);
  const today = kstNow.toISOString().split("T")[0];
  const hh = String(kstNow.getUTCHours()).padStart(2, "0");
  const mm = String(kstNow.getUTCMinutes()).padStart(2, "0");
  const scoredAt = `${today}T${hh}:${mm}`;
  const naverCache = new Map<string, MarketData>();
  const dartCache = new Map<string, DartFundamentals>();

  // DART corp_code 매핑 사전 로드
  if (DART_API_KEY) {
    console.log("📡 DART corp_code 매핑 로드...");
    await ensureCorpCodeMap();
  } else {
    console.log("⚠️ DART_API_KEY 미설정 — 네이버 TTM 사용");
  }

  // ─── 1. 워치리스트 (국내) ───
  const watchlistPath = path.join(process.cwd(), "public", "data", "watchlist.json");
  const watchlistData = JSON.parse(fs.readFileSync(watchlistPath, "utf-8"));

  console.log(`\n📊 [워치리스트] 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  const watchlistResult = await updateStocks(
    watchlistData.stocks as StockBase[],
    async (code) => fetchFromNaver(code),
    scoreAllDomestic,
    today,
    scoredAt,
    naverCache,
    !!DART_API_KEY,
    dartCache,
  );

  fs.writeFileSync(watchlistPath, JSON.stringify(watchlistData, null, 2) + "\n", "utf-8");
  console.log("\n" + "─".repeat(65));
  printSummary("워치리스트", watchlistResult);

  // ─── 2. 저평가 성장주 (국내) ───
  const growthPath = path.join(process.cwd(), "public", "data", "growth-watchlist.json");
  const growthData = JSON.parse(fs.readFileSync(growthPath, "utf-8"));

  if ((growthData.stocks as StockBase[]).length > 0) {
    console.log(`\n\n📊 [저평가 성장주] 시세 업데이트 (${today})`);
    console.log("─".repeat(65));

    // 누락 종목 주주환원 데이터 자동 수집
    await ensureShareholderData(growthData.stocks as { code: string; name: string }[]);

    const baseRate = growthData.base_rate ?? 2.75;

    // 전년 영업이익률은 updateStocks() 내 finance/annual 폴백에서 자동 추출

    const growthResult = await updateStocks(
      growthData.stocks as StockBase[],
      async (code) => fetchFromNaver(code),
      makeScoreAllGrowth(baseRate),
      today,
      scoredAt,
      naverCache,
      !!DART_API_KEY,
      dartCache,
    );

    console.log("\n" + "─".repeat(65));
    printSummary("저평가 성장주", growthResult);
  } else {
    console.log(`\n\n📊 [저평가 성장주] 종목 없음 — 건너뜀`);
  }

  fs.writeFileSync(growthPath, JSON.stringify(growthData, null, 2) + "\n", "utf-8");

  // ─── 3. 오일전문가 포트폴리오 ───
  const oilPath = path.join(process.cwd(), "public", "data", "oil-expert-watchlist.json");
  const oilData = JSON.parse(fs.readFileSync(oilPath, "utf-8"));

  // 2-1. 국내 종목
  console.log(`\n\n📊 [오일전문가 - 국내] 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  const oilDomesticResult = await updateStocks(
    oilData.domestic as StockBase[],
    async (code) => fetchFromNaver(code),
    scoreAllDomestic,
    today,
    scoredAt,
    naverCache,
    !!DART_API_KEY,
    dartCache,
  );

  console.log("\n" + "─".repeat(65));
  printSummary("오일전문가 국내", oilDomesticResult);

  // 2-2. 해외 종목
  console.log(`\n\n📊 [오일전문가 - 해외] 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  const yahooOk = await initYahooAuth();
  if (!yahooOk) {
    console.log("⚠️ Yahoo Finance 인증 실패 — 해외 종목 건너뜀");
  } else {
    const oilOverseasResult = await updateStocks(
      oilData.overseas as StockBase[],
      async (code, stock) => fetchFromYahoo(code, stock.pbr),
      scoreAllOverseas,
      today,
      scoredAt,
      new Map(), // 해외는 별도 캐시 (네이버 캐시와 분리)
    );

    console.log("\n" + "─".repeat(65));
    printSummary("오일전문가 해외", oilOverseasResult);
  }

  fs.writeFileSync(oilPath, JSON.stringify(oilData, null, 2) + "\n", "utf-8");

  // ─── 4. 성장주 스크리닝 종가 갱신 ───
  const screenPath = path.join(process.cwd(), "public", "data", "growth-candidates.json");
  try {
    const screenData = JSON.parse(fs.readFileSync(screenPath, "utf-8"));
    const candidates = screenData.candidates as (GrowthScreenInput & { score: number; grade: string; cat1: number; cat2: number; cat3: number; details: unknown[]; is_top10: boolean; previous_score?: number; previous_rank?: number; previous_details?: unknown[]; fundamentals_updated_at?: string })[];

    if (candidates.length > 0) {
      // 공시월 판별 (3월=사업보고서, 5월=1Q, 8월=반기, 11월=3Q)
      const DISCLOSURE_MONTHS = [3, 5, 8, 11];
      const currentMonth = new Date().getMonth() + 1;
      const isDisclosureMonth = DISCLOSURE_MONTHS.includes(currentMonth);

      const modeLabel = isDisclosureMonth ? "종가 + 실적 갱신" : "종가 기준 밸류에이션 갱신";
      console.log(`\n\n📊 [성장주 스크리닝] ${modeLabel} (${today})`);
      if (isDisclosureMonth) console.log(`  📋 공시월(${currentMonth}월) — 실적 데이터도 갱신합니다`);
      console.log("─".repeat(65));

      let screenUpdated = 0;
      let fundamentalsUpdated = 0;
      let fundamentalsSkipped = 0;
      const baseRate = screenData.base_rate ?? 2.75;

      // 당일 중복 실행 시 previous 덮어쓰기 방지
      const screenAlreadyUpdatedToday = screenData.scanned_at === today
        && candidates.some((c) => c.previous_score != null);

      // 업데이트 전 점수·순위 스냅샷
      const gradeOrderBefore: Record<string, number> = { A: 0, B: 1, C: 2, D: 3 };
      const beforeScores = candidates.map((c) => c.score);
      const beforeDetails = candidates.map((c) => c.details);
      const sortedBefore = candidates
        .map((c, i) => ({ i, grade: c.grade, score: c.score }))
        .sort((a, b) => {
          const gd = (gradeOrderBefore[a.grade] ?? 9) - (gradeOrderBefore[b.grade] ?? 9);
          return gd !== 0 ? gd : b.score - a.score;
        });
      const beforeRanks = new Array<number>(candidates.length);
      sortedBefore.forEach((entry, rank) => { beforeRanks[entry.i] = rank + 1; });

      // 누락 종목 주주환원 데이터 자동 수집 + 로드
      await ensureShareholderData(candidates as { code: string; name: string }[]);
      const screenShReturnMap = loadShareholderReturnMap();

      for (let ci = 0; ci < candidates.length; ci++) {
        const c = candidates[ci];
        // 네이버에서 오늘 종가만 조회 (캐시 활용)
        let market = naverCache.get(c.code) || null;
        if (!market) {
          market = await fetchFromNaver(c.code);
          if (market) naverCache.set(c.code, market);
          await sleep(REQUEST_DELAY_MS);
        }

        if (!market?.price) continue;

        const prevPrice = c.current_price;

        // 종가 기반 밸류에이션 갱신
        c.current_price = market.price;
        if (market.market_cap != null) c.market_cap = market.market_cap;
        if (market.foreign_ownership != null) c.foreign_ownership = market.foreign_ownership;
        c.dividend_yield = market.dividend_yield;
        c.pbr = market.pbr;

        // 공시월: 실적 데이터 갱신 (이번 달 이미 갱신된 종목은 스킵)
        if (isDisclosureMonth) {
          const alreadyUpdatedThisMonth = c.fundamentals_updated_at
            && c.fundamentals_updated_at.startsWith(today.slice(0, 7)); // YYYY-MM 비교

          if (alreadyUpdatedThisMonth) {
            fundamentalsSkipped++;
          } else {
            const fundamentals = await fetchScreenFundamentals(c.code);
            if (fundamentals) {
              c.revenue_latest = fundamentals.revenue_latest;
              c.revenue_prev = fundamentals.revenue_prev;
              c.op_profit_latest = fundamentals.op_profit_latest;
              c.op_profit_prev = fundamentals.op_profit_prev;
              c.op_margin = fundamentals.op_margin;
              c.op_margin_prev = fundamentals.op_margin_prev;
              c.profit_years = fundamentals.profit_years;
              c.eps_current = fundamentals.eps_current;
              c.eps_consensus = fundamentals.eps_consensus;
              c.fundamentals_updated_at = today;
              fundamentalsUpdated++;
              console.log(`  📋 ${c.name}: 실적 갱신 (매출 ${fundamentals.revenue_latest?.toLocaleString()}억, 영업이익 ${fundamentals.op_profit_latest?.toLocaleString()}억, EPS ${fundamentals.eps_current?.toLocaleString()})`);
            }
            await sleep(REQUEST_DELAY_MS);
          }
        }

        // PER 재계산 (실적 갱신 후 최신 EPS 기반)
        if (c.eps_current && c.eps_current > 0) {
          c.per = parseFloat((market.price / c.eps_current).toFixed(2));
        }

        // 점수 재계산 (주주환원 보정 포함)
        const result = scoreGrowthScreen(c, baseRate, screenShReturnMap.get(c.code));
        c.score = result.score;
        c.grade = result.grade;
        c.cat1 = result.cat1;
        c.cat2 = result.cat2;
        c.cat3 = result.cat3;
        c.details = result.details;

        // 이전 점수·순위·세부 저장 (당일 중복 실행 시 보호)
        if (!screenAlreadyUpdatedToday) {
          c.previous_score = beforeScores[ci];
          c.previous_rank = beforeRanks[ci];
          c.previous_details = beforeDetails[ci];
        }

        const diff = c.score - beforeScores[ci];
        if (diff !== 0) {
          console.log(`  ${c.name}: ${prevPrice?.toLocaleString()}→${market.price.toLocaleString()}원 | ${beforeScores[ci]}→${c.score}점 (${diff > 0 ? "+" : ""}${diff})`);
        }
        screenUpdated++;
      }

      // 재정렬 + Top 10 재지정
      const gradeOrder: Record<string, number> = { A: 0, B: 1, C: 2, D: 3 };
      candidates.sort((a, b) => {
        const gd = (gradeOrder[a.grade] ?? 9) - (gradeOrder[b.grade] ?? 9);
        return gd !== 0 ? gd : b.score - a.score;
      });
      candidates.forEach((c, i) => { c.is_top10 = i < 10; });

      screenData.scanned_at = today;
      fs.writeFileSync(screenPath, JSON.stringify(screenData, null, 2), "utf-8");
      console.log(`\n💾 성장주 스크리닝: ${screenUpdated}개 종가 갱신`);
      if (isDisclosureMonth) {
        console.log(`  📋 실적 갱신: ${fundamentalsUpdated}개 완료, ${fundamentalsSkipped}개 스킵 (이미 갱신됨)`);
      }
    }
  } catch {
    // growth-candidates.json 없으면 건너뜀
  }

  // ─── 5. 매매일지 보유 종목 ───
  const journalPath = path.join(process.cwd(), "public", "data", "journal.json");
  const journalData = JSON.parse(fs.readFileSync(journalPath, "utf-8"));

  console.log(`\n\n📊 [매매일지] 보유 종목 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  const holdings = journalData.holdings as {
    code: string; name: string;
    quantity: number; avg_price: number;
    current_price: number; eval_amount: number;
    profit_amount: number; profit_pct: number;
    [key: string]: unknown;
  }[];

  let journalUpdated = 0;
  let journalSkipped = 0;

  for (const h of holdings) {
    // 네이버 캐시 재활용 또는 신규 조회
    let cached = naverCache.get(h.code);
    if (!cached) {
      const result = await fetchFromNaver(h.code);
      if (result) {
        naverCache.set(h.code, result);
        cached = result;
      }
      await sleep(REQUEST_DELAY_MS);
    }

    if (!cached?.price) {
      console.log(`\n❌ ${h.name} (${h.code}): 시세 조회 실패 — 건너뜀`);
      journalSkipped++;
      continue;
    }

    const prevPrice = h.current_price;
    const newPrice = cached.price;

    h.current_price = newPrice;
    h.eval_amount = newPrice * h.quantity;
    h.profit_amount = h.eval_amount - h.avg_price * h.quantity;
    h.profit_pct = parseFloat(((h.profit_amount / (h.avg_price * h.quantity)) * 100).toFixed(1));

    const priceDiff = newPrice - prevPrice;
    const sign = priceDiff >= 0 ? "+" : "";
    console.log(
      `\n✅ ${h.name} (${h.code}) ${fmt(prevPrice)}원 → ${fmt(newPrice)}원 (${sign}${fmt(priceDiff)})` +
        `\n   평가금액 ${fmt(h.eval_amount)}원 | 수익 ${fmt(h.profit_amount)}원 (${h.profit_pct}%)`,
    );

    journalUpdated++;
  }

  // 요약 갱신
  if (journalUpdated > 0) {
    const totalEval = holdings.reduce((s, h) => s + h.eval_amount, 0);
    const totalInvested = holdings.reduce((s, h) => s + h.avg_price * h.quantity, 0);
    const holdingsProfit = totalEval - totalInvested;

    journalData.summary.total_current_value = totalEval;
    journalData.summary.total_assets = totalEval + journalData.summary.cash;

    // 순수익 = 매매차익 + 보유평가손익 - 비용
    const netProfit = journalData.summary.gross_profit + holdingsProfit - journalData.summary.total_cost;
    journalData.summary.net_profit = netProfit;
    journalData.summary.net_profit_pct = parseFloat(
      ((netProfit / journalData.summary.total_invested) * 100).toFixed(1),
    );

    console.log(
      `\n📊 포트폴리오 요약: 평가액 ${fmt(totalEval)}원 | 총자산 ${fmt(journalData.summary.total_assets)}원 | 순수익률 ${journalData.summary.net_profit_pct}%`,
    );
  }

  fs.writeFileSync(journalPath, JSON.stringify(journalData, null, 2) + "\n", "utf-8");

  console.log("\n" + "─".repeat(65));
  console.log(`💾 매매일지: ${journalUpdated}개 업데이트, ${journalSkipped}개 실패`);

  console.log("\n" + "═".repeat(65));
  console.log("✨ 전체 업데이트 완료");

  const totalSkipped = watchlistResult.skipped + oilDomesticResult.skipped + journalSkipped;
  if (totalSkipped > 0) process.exitCode = 1;
}

main().catch((err) => {
  console.error("스크립트 실행 실패:", err);
  process.exitCode = 1;
});
