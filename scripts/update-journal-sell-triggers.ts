/**
 * 매매일지 매도 트리거 가격 갱신 스크립트
 *
 * 동작:
 * - public/data/journal.json holdings 각 종목에 대해
 *   2020-01-01 이후 일중 최고가(highPrice) max 를 산출
 * - sell_trigger_price = round(high_price * 0.9) 계산해 holdings 에 저장
 * - 데이터 소스: 네이버 차트 API (monthCandle 110 + dayCandle 110 병합)
 *
 * GitHub Actions update-watchlist.yml 에서 매일 06:30 / 17:00 KST 자동 실행.
 */
import fs from "fs";
import path from "path";

const UA_MOBILE =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15";
const REFERER_M = "https://m.stock.naver.com/";
const SINCE = "20200101";
const TRIGGER_RATIO = 0.9;

interface PriceInfo {
  localDate?: string;
  closePrice?: number;
  highPrice?: number;
}

interface ChartResp {
  priceInfos?: PriceInfo[];
}

interface Holding {
  code: string;
  name: string;
  high_price?: number;
  high_price_date?: string;
  sell_trigger_price?: number;
  [k: string]: unknown;
}

interface JournalData {
  holdings: Holding[];
  [k: string]: unknown;
}

function bizdateToISO(d: string): string {
  return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
}

async function fetchCandles(
  code: string,
  periodType: "dayCandle" | "monthCandle",
): Promise<PriceInfo[]> {
  const url = `https://api.stock.naver.com/chart/domestic/item/${code}?periodType=${periodType}&count=110`;
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": UA_MOBILE, Referer: REFERER_M },
    });
    if (!res.ok) return [];
    const json = (await res.json()) as ChartResp;
    return json.priceInfos ?? [];
  } catch {
    return [];
  }
}

async function computeHigh(
  code: string,
): Promise<{ high: number; date: string } | null> {
  const [day, month] = await Promise.all([
    fetchCandles(code, "dayCandle"),
    fetchCandles(code, "monthCandle"),
  ]);
  const merged = [...day, ...month].filter(
    (p) => p.localDate && p.localDate >= SINCE && p.highPrice != null,
  );
  if (merged.length === 0) return null;
  let best = merged[0];
  for (const p of merged) {
    if ((p.highPrice ?? 0) > (best.highPrice ?? 0)) best = p;
  }
  return { high: best.highPrice!, date: bizdateToISO(best.localDate!) };
}

async function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function main() {
  const filePath = path.join(process.cwd(), "public", "data", "journal.json");
  const raw = fs.readFileSync(filePath, "utf-8");
  const data = JSON.parse(raw) as JournalData;

  if (!Array.isArray(data.holdings) || data.holdings.length === 0) {
    console.log("[journal-sell-triggers] holdings 없음 — 종료");
    return;
  }

  console.log(
    `[journal-sell-triggers] ${data.holdings.length} 종목 처리 시작 (2020-01-01 이후 highPrice max 기준)`,
  );

  let updated = 0;
  for (const h of data.holdings) {
    const result = await computeHigh(h.code);
    if (result) {
      const trigger = Math.round(result.high * TRIGGER_RATIO);
      const changed =
        h.high_price !== result.high ||
        h.high_price_date !== result.date ||
        h.sell_trigger_price !== trigger;
      h.high_price = result.high;
      h.high_price_date = result.date;
      h.sell_trigger_price = trigger;
      if (changed) updated += 1;
      console.log(
        `  ${h.code} ${h.name}: high=${result.high.toLocaleString()} (${result.date}) → trigger=${trigger.toLocaleString()}${changed ? " *" : ""}`,
      );
    } else {
      console.warn(`  ${h.code} ${h.name}: 차트 데이터 조회 실패 — 스킵`);
    }
    await sleep(1000);
  }

  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n");
  console.log(
    `[journal-sell-triggers] 완료 — ${updated} 종목 변경, journal.json 저장`,
  );
}

main().catch((e) => {
  console.error("[journal-sell-triggers] 실패:", e);
  process.exit(1);
});
