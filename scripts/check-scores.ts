import { scoreDomestic } from "../src/lib/scoring";
import fs from "fs";

const raw = JSON.parse(fs.readFileSync("public/data/oil-expert-watchlist.json", "utf-8"));

const origScores: Record<string, number> = {
  "하나금융지주": 75, "기아": 69, "현대차2우B": 69, "우리금융지주": 67,
  "한국타이어": 66, "DB손해보험": 63, "금호석유우": 58, "빙그레": 50,
  "기업은행": 49, "삼성화재우": 47, "LX인터내셔널": 43, "금호석유": 43,
  "대상": 40, "세아제강": 39, "농심": 37, "오뚜기": 34
};

interface Scored {
  name: string;
  cat1: number;
  cat2: number;
  cat3: number;
  score: number;
  grade: string;
  details: { item: string; basis: string; score: number; max: number; cat: number }[];
}

const stocks: Scored[] = raw.domestic
  .map((s: any) => ({ name: s.name, ...scoreDomestic(s) }))
  .sort((a: Scored, b: Scored) => b.score - a.score);

console.log("=== 오일전문가 국내 16종목 자동 채점 결과 ===\n");
console.log("순위  종목            Cat1/35  Cat2/40  Cat3/25  총점  등급  원본  차이");
console.log("─".repeat(80));

for (let i = 0; i < stocks.length; i++) {
  const s = stocks[i];
  const orig = origScores[s.name] ?? 0;
  const diff = s.score - orig;
  const diffStr = diff > 0 ? "+" + diff : diff === 0 ? " =" : "" + diff;
  console.log(
    `${String(i + 1).padStart(2)}    ${s.name.padEnd(14)}  ${String(s.cat1).padStart(4)}/35   ${String(s.cat2).padStart(4)}/40   ${String(s.cat3).padStart(4)}/25   ${String(s.score).padStart(3)}    ${s.grade}    ${String(orig).padStart(3)}   ${diffStr}`
  );
}

const diffs = stocks.filter(s => s.score !== (origScores[s.name] ?? 0));
if (diffs.length > 0) {
  console.log("\n=== 원본과 차이나는 종목 세부 분석 ===\n");
  for (const s of diffs) {
    const orig = origScores[s.name] ?? 0;
    console.log(`■ ${s.name}: 자동계산 ${s.score}점 vs 원본 ${orig}점 (${s.score - orig > 0 ? "+" : ""}${s.score - orig})`);
    for (const d of s.details) {
      console.log(`  ${d.item.padEnd(14)} ${String(d.score).padStart(2)}/${String(d.max).padStart(2)}  ${d.basis}`);
    }
    console.log("");
  }
} else {
  console.log("\n✓ 모든 종목이 원본과 일치합니다.");
}
