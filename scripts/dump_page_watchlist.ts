// 페이지(/stocks/sepa)가 «실제로» 표에 띄우는 종목 집합을 그대로 뽑는다.
//
// 왜 있나: 같은 분류 규칙을 pivot_alert.py 가 파이썬으로 옮겨 적었다. 두 벌을
// 손으로 맞춘 규칙은 갈라진다. 이 각본은 «페이지 코드 자체»를 불러 돌리므로
// 옮겨 적은 쪽이 틀리면 집합이 어긋나 드러난다.
//
// 쓰기: npx tsx scripts/dump_page_watchlist.ts > <출력.json>
//   출력은 {"파일이름": {"종목코드": "티어"}} 꼴.

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { PATTERNS, buildSection, type RawCandidate } from "../src/app/stocks/sepa/sepaPatterns";

const DATA = join(import.meta.dirname, "..", "public", "data");

function readJson<T>(name: string): T | null {
  try {
    return JSON.parse(readFileSync(join(DATA, name), "utf-8")) as T;
  } catch {
    return null;
  }
}

const exclusionFile = readJson<{ exclusions?: { code: string }[] }>("sepa-exclusions.json");
const excludeCodes = new Set((exclusionFile?.exclusions ?? []).map((e) => e.code));

const out: Record<string, Record<string, string>> = {};
for (const config of Object.values(PATTERNS)) {
  const data = readJson<{ candidates?: RawCandidate[] }>(config.file);
  const { rows } = buildSection(data?.candidates ?? [], config, undefined, excludeCodes);
  out[config.file] = Object.fromEntries(rows.map((r) => [r.code, r.tier]));
}

process.stdout.write(JSON.stringify(out, null, 1));
