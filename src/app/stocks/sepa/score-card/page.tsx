import fs from "fs/promises";
import path from "path";
import type { Scorecard } from "@/lib/scorecard";
import { ScorecardView } from "./ScorecardView";

async function readScorecard(): Promise<Scorecard | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "scorecard.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8")) as Scorecard;
  } catch {
    return null;
  }
}

export default async function ScorecardPage() {
  const data = await readScorecard();
  if (!data) {
    return (
      <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-sm text-on-surface-variant/70">
        정산표 데이터가 없습니다. <code className="text-xs">npm run scorecard</code> 실행 후 생성됩니다.
      </div>
    );
  }
  return <ScorecardView data={data} />;
}
