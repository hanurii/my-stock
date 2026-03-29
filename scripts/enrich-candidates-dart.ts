/**
 * 성장주 스크리닝 후보 — DART 확정 실적 데이터로 보강
 *
 * growth-candidates.json의 30개 후보에 대해
 * DART fnlttSinglAcntAll API로 확정 재무제표를 수집하고
 * 점수를 재계산한다.
 *
 * 사용법: npx tsx scripts/enrich-candidates-dart.ts
 */
import fs from "fs";
import path from "path";
import { loadCorpCodeMap } from "./fetch-shareholder-returns";
import { scoreGrowthScreen, type GrowthScreenInput } from "../src/lib/scoring";

// ── 설정 ──

const DART_API = "https://opendart.fss.or.kr/api";
const DART_API_KEY = process.env.DART_API_KEY ?? "";
const DATA_DIR = path.resolve("public/data");
const CANDIDATES_FILE = path.join(DATA_DIR, "growth-candidates.json");
const REQUEST_DELAY_MS = 500;
const CURRENT_YEAR = new Date().getFullYear();
const YEARS = [CURRENT_YEAR - 1, CURRENT_YEAR - 2, CURRENT_YEAR - 3]; // 최근 3년

// ── 유틸 ──

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

function parseAmount(s: string | undefined | null): number {
  if (!s || s === "-" || s === "") return 0;
  return Number(s.replace(/,/g, "")) || 0;
}

// ── DART API ──

interface DartFinItem {
  sj_div: string;       // IS(손익계산서), BS(재무상태표)
  account_nm: string;   // 계정명
  thstrm_amount: string; // 당기금액
  frmtrm_amount: string; // 전기금액
  bfefrmtrm_amount: string; // 전전기금액
}

async function dartGet(endpoint: string, params: Record<string, string>): Promise<DartFinItem[] | null> {
  const url = new URL(`${DART_API}/${endpoint}.json`);
  url.searchParams.set("crtfc_key", DART_API_KEY);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);

  const res = await fetch(url.toString());
  if (!res.ok) return null;
  const json = await res.json() as { status: string; list?: DartFinItem[] };
  if (json.status === "000" && json.list) return json.list;
  return null;
}

// ── 재무제표에서 데이터 추출 ──

interface YearlyFinancials {
  revenue: number;
  op_profit: number;
  net_income: number;
  eps: number;
  total_equity: number;
  total_debt: number;
}

function extractFinancials(items: DartFinItem[]): { current: YearlyFinancials; prev: YearlyFinancials; prevPrev: YearlyFinancials } {
  const extract = (field: "thstrm_amount" | "frmtrm_amount" | "bfefrmtrm_amount"): YearlyFinancials => {
    let revenue = 0, opProfit = 0, netIncome = 0, eps = 0, totalEquity = 0, totalDebt = 0;

    for (const item of items) {
      const name = item.account_nm?.trim() || "";
      const val = parseAmount(item[field]);

      // 손익계산서: IS 또는 CIS(포괄손익계산서) — 회사마다 다름
      if (item.sj_div === "IS" || item.sj_div === "CIS") {
        // 매출액
        if ((name === "매출액" || name === "수익(매출액)" || name === "영업수익" || name === "수익") && revenue === 0) {
          revenue = val;
        }
        // 영업이익
        if (name === "영업이익" || name === "영업이익(손실)") {
          opProfit = val;
        }
        // 당기순이익 (지배주주)
        if ((name.includes("당기순이익") || name.includes("당기순손익")) && name.includes("지배")) {
          netIncome = val;
        }
        // 당기순이익 (전체 — 폴백)
        if ((name === "당기순이익" || name === "당기순이익(손실)") && netIncome === 0) {
          netIncome = val;
        }
        // EPS
        if ((name.includes("기본주당") && (name.includes("이익") || name.includes("손익"))) && eps === 0) {
          eps = val;
        }
      }

      if (item.sj_div === "BS") {
        if (name === "자본총계" && totalEquity === 0) totalEquity = val;
        if (name === "부채총계" && totalDebt === 0) totalDebt = val;
      }
    }

    return { revenue, op_profit: opProfit, net_income: netIncome, eps, total_equity: totalEquity, total_debt: totalDebt };
  };

  return {
    current: extract("thstrm_amount"),
    prev: extract("frmtrm_amount"),
    prevPrev: extract("bfefrmtrm_amount"),
  };
}

async function fetchDartFinancials(corpCode: string): Promise<{ current: YearlyFinancials; prev: YearlyFinancials; prevPrev: YearlyFinancials } | null> {
  // 최근 연도부터 시도 (사업보고서가 아직 안 나온 연도가 있을 수 있음)
  for (const year of YEARS) {
    // CFS(연결) 우선, OFS(별도) 폴백
    for (const fsDiv of ["CFS", "OFS"]) {
      const items = await dartGet("fnlttSinglAcntAll", {
        corp_code: corpCode,
        bsns_year: String(year),
        reprt_code: "11011",
        fs_div: fsDiv,
      });
      await sleep(REQUEST_DELAY_MS);

      if (!items || items.length === 0) continue;

      const result = extractFinancials(items);
      // 매출이 있어야 유효한 데이터
      if (result.current.revenue > 0) {
        return result;
      }
    }
  }
  return null;
}

// ── 메인 ──

async function main() {
  if (!DART_API_KEY) {
    console.error("❌ DART_API_KEY 환경변수가 설정되지 않았습니다.");
    process.exit(1);
  }

  console.log("📊 DART 확정 실적으로 후보군 보강 시작\n");

  // 후보 로드
  const data = JSON.parse(fs.readFileSync(CANDIDATES_FILE, "utf-8"));
  const candidates = data.candidates as (GrowthScreenInput & { score: number; grade: string; details: unknown[]; is_top10: boolean })[];
  console.log(`  후보: ${candidates.length}개\n`);

  // corp_code 매핑
  const corpMap = await loadCorpCodeMap();

  let enriched = 0;
  let failed = 0;

  for (let i = 0; i < candidates.length; i++) {
    const c = candidates[i];
    const corpCode = corpMap.get(c.code);
    if (!corpCode) {
      console.warn(`  ⚠ ${c.name}(${c.code}) — corp_code 매핑 실패`);
      failed++;
      continue;
    }

    console.log(`  [${i + 1}/${candidates.length}] ${c.name}(${c.code})`);
    const fin = await fetchDartFinancials(corpCode);
    if (!fin) {
      console.warn(`    → DART 데이터 없음, 네이버 데이터 유지`);
      failed++;
      continue;
    }

    // 이전 값 백업 (비교용)
    const prevScore = c.score;

    // DART 데이터로 교체
    c.revenue_latest = fin.current.revenue;
    c.revenue_prev = fin.prev.revenue;
    c.op_profit_latest = fin.current.op_profit;
    c.op_profit_prev = fin.prev.op_profit;
    c.op_margin = fin.current.revenue > 0
      ? parseFloat(((fin.current.op_profit / fin.current.revenue) * 100).toFixed(2))
      : 0;
    c.op_margin_prev = fin.prev.revenue > 0
      ? parseFloat(((fin.prev.op_profit / fin.prev.revenue) * 100).toFixed(2))
      : null;
    if (fin.current.eps > 0) c.eps_current = fin.current.eps;
    // eps_consensus는 네이버 데이터 유지 (DART에 없음)

    // 흑자 연수 재계산
    let profitYears = 0;
    if (fin.current.op_profit > 0) profitYears++;
    if (fin.prev.op_profit > 0) profitYears++;
    if (fin.prevPrev.op_profit > 0) profitYears++;
    c.profit_years = profitYears;

    // 점수 재계산
    const result = scoreGrowthScreen(c, data.base_rate);
    c.score = result.score;
    c.grade = result.grade;
    c.details = result.details;

    const diff = c.score - prevScore;
    console.log(`    → DART 반영: ${prevScore}→${c.score}점 (${diff > 0 ? "+" : ""}${diff}) [${c.grade}]`);
    enriched++;
  }

  // 재정렬
  const gradeOrder: Record<string, number> = { A: 0, B: 1, C: 2, D: 3 };
  candidates.sort((a, b) => {
    const gd = (gradeOrder[a.grade] ?? 9) - (gradeOrder[b.grade] ?? 9);
    return gd !== 0 ? gd : b.score - a.score;
  });

  // Top 10 재지정
  candidates.forEach((c, i) => { c.is_top10 = i < 10; });

  // 저장
  fs.writeFileSync(CANDIDATES_FILE, JSON.stringify(data, null, 2), "utf-8");

  console.log(`\n✅ 완료: ${enriched}개 DART 반영, ${failed}개 실패`);
  console.log("\n🏆 Top 10 (DART 확정 기준):");
  candidates.slice(0, 10).forEach((c, i) => {
    console.log(`  ${(i + 1).toString().padStart(2)}. [${c.grade}] ${c.name.padEnd(14)} ${String(c.score).padStart(3)}점`);
  });
}

main().catch((e) => {
  console.error("❌ 실행 오류:", e);
  process.exit(1);
});
