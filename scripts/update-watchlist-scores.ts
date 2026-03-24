/**
 * 워치리스트 시세 자동 업데이트 스크립트
 *
 * 네이버 금융 API에서 현재가·PER·PBR·배당수익률을 직접 가져와
 * watchlist.json을 업데이트한다.
 *
 * - 네이버 금융이 실적 발표를 반영하므로 EPS/BPS 변경도 자동 반영
 * - 점수 변화 시 previous_score/previous_rank/grade_change_reason도 자동 갱신
 * - 수동 업데이트 불필요 (완전 자동)
 *
 * 사용법: npx tsx scripts/update-watchlist-scores.ts
 */
import fs from "fs";
import path from "path";
import {
  scoreDomestic,
  getGrade,
  type DomesticStockInput,
} from "../src/lib/scoring";

// ── 설정 ──

const NAVER_API = "https://m.stock.naver.com/api/stock";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
const REQUEST_DELAY_MS = 1000;

// ── 타입 ──

interface Stock extends DomesticStockInput {
  current_price_at_scoring?: number;
  previous_score?: number;
  previous_rank?: number;
  grade_change_reason?: string;
  [key: string]: unknown;
}

interface NaverData {
  price: number;
  per: number | null;
  pbr: number;
  dividend_yield: number;
}

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

// ── 네이버 금융 API ──

function parseNumber(value: string | undefined): number | null {
  if (!value) return null;
  const cleaned = value.replace(/[^0-9.\-]/g, "");
  const num = parseFloat(cleaned);
  return isNaN(num) ? null : num;
}

async function fetchFromNaver(code: string): Promise<NaverData | null> {
  try {
    const url = `${NAVER_API}/${code}/integration`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;

    const json = await res.json();
    const infos: { key: string; value: string }[] = json.totalInfos || [];

    const get = (key: string) => infos.find((i) => i.key === key)?.value;

    const price = json.closePrice
      ? parseNumber(json.closePrice)
      : parseNumber(get("전일"));

    // 장중이면 현재가 사용
    const currentPrice = json.currentPrice
      ? parseNumber(json.currentPrice)
      : null;

    const finalPrice = currentPrice || price;
    if (!finalPrice) return null;

    let per = parseNumber(get("PER"));
    let pbr = parseNumber(get("PBR"));
    const dividendYield = parseNumber(get("배당수익률"));

    // integration에서 PER/PBR이 N/A인 경우 finance/annual에서 직접 계산
    if (per == null || pbr == null || pbr === 0) {
      const fallback = await fetchFundamentalsFromNaver(code, finalPrice);
      if (fallback) {
        if (per == null && fallback.per != null) per = fallback.per;
        if ((pbr == null || pbr === 0) && fallback.pbr > 0) pbr = fallback.pbr;
      }
    }

    return {
      price: finalPrice,
      per,
      pbr: pbr ?? 0,
      dividend_yield: dividendYield ?? 0,
    };
  } catch {
    return null;
  }
}

/**
 * integration에서 PER/PBR이 N/A일 때
 * finance/annual의 최신 확정 EPS/BPS로 직접 계산
 */
async function fetchFundamentalsFromNaver(
  code: string,
  price: number,
): Promise<{ per: number | null; pbr: number } | null> {
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

    // 최신 확정(isConsensus=N) 기간 찾기
    const confirmed = [...periods]
      .filter((p) => p.isConsensus === "N")
      .pop();
    if (!confirmed) return null;

    const getValue = (title: string): number | null => {
      const row = rows.find((r) => r.title === title);
      return parseNumber(row?.columns[confirmed.key]?.value);
    };

    const eps = getValue("EPS");
    const bps = getValue("BPS");

    const per = eps && eps > 0 ? parseFloat((price / eps).toFixed(2)) : null;
    const pbr = bps && bps > 0 ? parseFloat((price / bps).toFixed(2)) : 0;

    if (per != null || pbr > 0) {
      console.log(
        `   📈 finance/annual fallback (${confirmed.key}): EPS ${fmt(eps)} BPS ${fmt(bps)} → PER ${fmt(per)} PBR ${pbr}`,
      );
    }

    return { per, pbr };
  } catch {
    return null;
  }
}

// ── 채점 & 순위 ──

function scoreAll(stocks: Stock[]): { scores: number[]; ranks: number[]; grades: string[] } {
  const results = stocks.map((s) => scoreDomestic(s));
  const scores = results.map((r) => r.score);
  const grades = results.map((r) => r.grade);

  // 점수 내림차순으로 순위 계산
  const indexed = scores.map((score, i) => ({ score, i }));
  indexed.sort((a, b) => b.score - a.score);
  const ranks = new Array<number>(stocks.length);
  indexed.forEach((item, rank) => {
    ranks[item.i] = rank + 1;
  });

  return { scores, ranks, grades };
}

function buildChangeReason(
  stock: Stock,
  prev: { per: number | null; pbr: number; div: number },
  next: { per: number | null; pbr: number; div: number },
): string {
  const parts: string[] = [];

  if (prev.per != null && next.per != null && prev.per !== next.per) {
    parts.push(`PER ${prev.per}→${next.per}`);
  }
  if (prev.pbr !== next.pbr) {
    parts.push(`PBR ${prev.pbr}→${next.pbr}`);
  }
  if (prev.div !== next.div) {
    parts.push(`배당 ${prev.div}%→${next.div}%`);
  }

  return parts.join(", ");
}

// ── 메인 ──

async function main() {
  const filePath = path.join(process.cwd(), "public", "data", "watchlist.json");
  const raw = fs.readFileSync(filePath, "utf-8");
  const data = JSON.parse(raw);
  const stocks = data.stocks as Stock[];
  const today = new Date().toISOString().split("T")[0];

  console.log(`📊 워치리스트 시세 업데이트 (${today})`);
  console.log("─".repeat(65));

  // Step 1: 업데이트 전 현재 점수/순위 계산
  const before = scoreAll(stocks);

  // Step 2: 시세 업데이트
  let updated = 0;
  let skipped = 0;
  const prevMarketData: { per: number | null; pbr: number; div: number }[] = [];

  for (let i = 0; i < stocks.length; i++) {
    const stock = stocks[i];
    prevMarketData.push({ per: stock.per, pbr: stock.pbr, div: stock.dividend_yield });

    const result = await fetchFromNaver(stock.code);

    if (!result) {
      console.log(`\n❌ ${stock.name} (${stock.code}): 시세 조회 실패 — 건너뜀`);
      skipped++;
      await sleep(REQUEST_DELAY_MS);
      continue;
    }

    // 네이버에서 N/A인 항목은 기존 값 유지
    const newPer = result.per ?? stock.per;
    const newPbr = result.pbr > 0 ? result.pbr : stock.pbr;
    const newDiv = result.dividend_yield;

    const prev = prevMarketData[i];

    stock.per = newPer;
    stock.pbr = newPbr;
    stock.dividend_yield = newDiv;
    stock.current_price_at_scoring = result.price;
    stock.scored_at = today;

    // fundamentals 필드가 남아있으면 제거 (더 이상 필요 없음)
    if ("fundamentals" in stock) {
      delete stock.fundamentals;
    }

    const kept: string[] = [];
    if (result.per == null) kept.push("PER");
    if (result.pbr === 0) kept.push("PBR");

    console.log(
      `\n✅ ${stock.name} (${stock.code}) ${fmt(stock.current_price_at_scoring)}원` +
        (kept.length > 0 ? ` ⚠️ ${kept.join("/")} 기존값 유지` : ""),
    );
    console.log(
      `   PER ${fmt(prev.per)} → ${fmt(newPer)} (${diff(prev.per, newPer)})` +
        ` | PBR ${prev.pbr} → ${newPbr} (${diff(prev.pbr, newPbr)})` +
        ` | 배당률 ${prev.div}% → ${newDiv}% (${diff(prev.div, newDiv)})`,
    );

    updated++;
    await sleep(REQUEST_DELAY_MS);
  }

  // Step 3: 업데이트 후 점수/순위 계산 & 변화 반영
  const after = scoreAll(stocks);

  let gradeChanges = 0;
  let scoreChanges = 0;
  let rankChanges = 0;

  for (let i = 0; i < stocks.length; i++) {
    const stock = stocks[i];

    // previous_score, previous_rank 저장
    stock.previous_score = before.scores[i];
    stock.previous_rank = before.ranks[i];

    // 점수/등급 변화 감지
    const oldGrade = before.grades[i];
    const newGrade = after.grades[i];
    const scoreChanged = before.scores[i] !== after.scores[i];

    if (scoreChanged) {
      const reason = buildChangeReason(
        stock,
        prevMarketData[i],
        { per: stock.per, pbr: stock.pbr, div: stock.dividend_yield },
      );
      stock.grade_change_reason = reason;
      scoreChanges++;

      if (oldGrade !== newGrade) {
        gradeChanges++;
        console.log(
          `\n🔄 ${stock.name}: ${oldGrade}(${before.scores[i]}점) → ${newGrade}(${after.scores[i]}점) | ${reason}`,
        );
      } else {
        console.log(
          `\n📝 ${stock.name}: ${before.scores[i]}점 → ${after.scores[i]}점 | ${reason}`,
        );
      }
    } else {
      delete stock.grade_change_reason;
    }

    if (before.ranks[i] !== after.ranks[i]) {
      rankChanges++;
    }
  }

  // 저장
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", "utf-8");

  console.log("\n" + "─".repeat(65));
  console.log(
    `💾 완료: ${updated}개 업데이트, ${skipped}개 실패` +
      (scoreChanges > 0 ? `, ${scoreChanges}개 점수 변화` : "") +
      (gradeChanges > 0 ? ` (등급 변화 ${gradeChanges}개)` : "") +
      (rankChanges > 0 ? `, ${rankChanges}개 순위 변동` : ""),
  );

  if (skipped > 0) {
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error("스크립트 실행 실패:", err);
  process.exitCode = 1;
});
