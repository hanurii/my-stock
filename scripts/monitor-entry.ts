/**
 * 매수 트리거 자동 모니터 — 메인 entry
 *
 * entry-configs.ts의 종목별 설정(매수 검토 종목)을 순회하며 collector 호출 →
 * public/data/research/monitor_entry/{code}.json 저장.
 *
 * processStock·collector 인프라는 monitor-research.ts와 100% 공유.
 * MonitorConfig.purpose="entry" 설정으로 알림 메시지만 매수 문맥으로 분기됨.
 *
 * 실행:
 *   npx tsx scripts/monitor-entry.ts        — 전체
 *   npx tsx scripts/monitor-entry.ts 088130 — 단일 종목
 */
import fs from "fs";
import path from "path";
import { ENTRY_CONFIGS } from "./monitor/entry-configs";
import { processStock } from "./monitor-research";

async function main() {
  const targetCode = process.argv[2];
  const targets = targetCode
    ? ENTRY_CONFIGS.filter((c) => c.code === targetCode)
    : ENTRY_CONFIGS;
  if (targets.length === 0) {
    console.error(`❌ 종목 ${targetCode} 설정 없음 — entry-configs.ts 확인`);
    process.exit(1);
  }
  const outDir = path.resolve("public/data/research/monitor_entry");
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
