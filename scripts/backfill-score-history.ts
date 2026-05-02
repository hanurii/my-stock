/**
 * 점수 변경 히스토리 백필 (1회용 도구)
 *
 * 기존 git 이력을 walk해서 각 종목의 점수 변경을 score_history에 누적한다.
 * 최근 2건만 유지 (스크립트 본 로직과 동일).
 *
 * 사용법: npx tsx scripts/backfill-score-history.ts [--write]
 *   --write 없으면 dry-run (변경 없이 리포트만 출력)
 */
import { execSync } from "child_process";
import fs from "fs";

const TARGETS: { file: string; sections: string[] }[] = [
  { file: "public/data/watchlist.json", sections: ["stocks"] },
  { file: "public/data/growth-watchlist.json", sections: ["stocks"] },
  { file: "public/data/oil-expert-watchlist.json", sections: ["domestic", "overseas"] },
];

const SCORE_HISTORY_LIMIT = 2;

interface ScoreDetail { item: string; score: number; max?: number; cat?: number; basis?: string }
interface Stock {
  code: string;
  name: string;
  scored_at?: string;
  previous_score?: number;
  details?: ScoreDetail[];
  previous_details?: ScoreDetail[];
  grade_change_reason?: string;
  score_history?: ScoreChangeEntry[];
  [k: string]: unknown;
}
interface ScoreDetailDiff { item: string; from: number; to: number; diff: number }
interface ScoreChangeEntry {
  at: string;
  from: number;
  to: number;
  reason: string;
  details_diff: ScoreDetailDiff[];
}

function totalScore(details?: ScoreDetail[]): number | null {
  if (!Array.isArray(details) || details.length === 0) return null;
  return details.reduce((s, d) => s + (d.score ?? 0), 0);
}

function diffDetails(before?: ScoreDetail[], after?: ScoreDetail[]): ScoreDetailDiff[] {
  if (!before || !after) return [];
  const diffs: ScoreDetailDiff[] = [];
  for (let i = 0; i < before.length; i++) {
    const b = before[i];
    const a = after.find((x) => x.item === b.item);
    if (a && b.score !== a.score) {
      diffs.push({ item: a.item, from: b.score, to: a.score, diff: a.score - b.score });
    }
  }
  return diffs;
}

function buildReasonText(diffs: ScoreDetailDiff[]): string {
  return diffs.map((d) => `${d.item} ${d.from}→${d.to}점(${d.diff > 0 ? "+" : ""}${d.diff})`).join(", ");
}

function pushHistory(stock: Stock, entry: ScoreChangeEntry) {
  const hist = (stock.score_history ?? []).filter((e) => e.at !== entry.at);
  stock.score_history = [entry, ...hist]
    .sort((a, b) => (a.at < b.at ? 1 : -1)) // 최신이 앞
    .slice(0, SCORE_HISTORY_LIMIT);
}

function loadCommitFile(sha: string, file: string): unknown | null {
  try {
    const buf = execSync(`git show ${sha}:${file}`, { stdio: ["ignore", "pipe", "ignore"] });
    return JSON.parse(buf.toString());
  } catch {
    return null;
  }
}

function getStocksFromData(data: unknown, sections: string[]): Stock[] {
  if (!data || typeof data !== "object") return [];
  const out: Stock[] = [];
  for (const sec of sections) {
    const arr = (data as Record<string, unknown>)[sec];
    if (Array.isArray(arr)) out.push(...(arr as Stock[]));
  }
  return out;
}

const dryRun = !process.argv.includes("--write");

console.log(`📚 score_history 백필 ${dryRun ? "(dry-run)" : "(write)"}`);
console.log("═".repeat(70));

for (const { file, sections } of TARGETS) {
  console.log(`\n📂 ${file}`);
  console.log("─".repeat(70));

  if (!fs.existsSync(file)) {
    console.log("  ⚠️ 파일 없음, 스킵");
    continue;
  }

  // git log 신규→오래된 순서, 최근 50개 정도면 충분
  const log = execSync(`git log --oneline -80 -- ${file}`, { stdio: ["ignore", "pipe", "ignore"] })
    .toString()
    .trim()
    .split("\n");
  const shas = log.map((l) => l.split(" ")[0]).reverse(); // 오래된 → 최신

  // 종목별 history accumulator
  const codeMap = new Map<string, Stock>();
  let prevSnapshot: Map<string, Stock> = new Map();

  for (const sha of shas) {
    const data = loadCommitFile(sha, file);
    if (!data) continue;
    const stocks = getStocksFromData(data, sections);
    const curSnapshot = new Map<string, Stock>();
    for (const s of stocks) curSnapshot.set(s.code, s);

    if (prevSnapshot.size > 0) {
      for (const [code, cur] of curSnapshot) {
        const prev = prevSnapshot.get(code);
        if (!prev) continue;
        const curTotal = totalScore(cur.details);
        const prevTotal = totalScore(prev.details);
        if (curTotal == null || prevTotal == null) continue;
        if (curTotal === prevTotal) continue;
        // 점수가 달라진 종목 — score_history entry 합성
        const diffs = diffDetails(prev.details, cur.details);
        if (diffs.length === 0) continue; // 점수 동일하지 않은데 diff 없으면 노이즈, 스킵
        const at = cur.scored_at ?? sha;
        const reason = cur.grade_change_reason && cur.grade_change_reason.length > 0
          ? cur.grade_change_reason
          : buildReasonText(diffs);
        const entry: ScoreChangeEntry = {
          at,
          from: prevTotal,
          to: curTotal,
          reason,
          details_diff: diffs,
        };
        let acc = codeMap.get(code);
        if (!acc) {
          acc = { code, name: cur.name, score_history: [] };
          codeMap.set(code, acc);
        }
        pushHistory(acc, entry);
      }
    }

    prevSnapshot = curSnapshot;
  }

  // 현재 파일에 적용
  const liveData = JSON.parse(fs.readFileSync(file, "utf-8"));
  const liveStocks = getStocksFromData(liveData, sections);
  let updated = 0;
  for (const s of liveStocks) {
    const acc = codeMap.get(s.code);
    if (!acc || !acc.score_history || acc.score_history.length === 0) continue;
    // 기존 score_history와 병합 (같은 at은 dedupe, 최대 2건)
    const existing = s.score_history ?? [];
    const merged = [...existing, ...acc.score_history];
    const seen = new Set<string>();
    const dedup: ScoreChangeEntry[] = [];
    merged
      .sort((a, b) => (a.at < b.at ? 1 : -1))
      .forEach((e) => {
        if (!seen.has(e.at)) {
          seen.add(e.at);
          dedup.push(e);
        }
      });
    s.score_history = dedup.slice(0, SCORE_HISTORY_LIMIT);
    s.grade_change_reason = s.score_history[0].reason;
    updated++;
    if (updated <= 8) {
      const last = s.score_history[0];
      console.log(`  ✅ ${s.code} ${s.name}: [${last.at}] ${last.from}→${last.to}점 | ${last.reason}${s.score_history[1] ? ` (+ 직전 ${s.score_history[1].from}→${s.score_history[1].to})` : ""}`);
    }
  }

  console.log(`  …총 ${updated}개 종목에 score_history 백필`);

  if (!dryRun && updated > 0) {
    fs.writeFileSync(file, JSON.stringify(liveData, null, 2) + "\n", "utf-8");
    console.log(`  💾 저장 완료`);
  }
}

console.log("\n" + (dryRun ? "💡 --write 옵션을 추가해 실제 저장하세요." : "✨ 백필 완료"));
