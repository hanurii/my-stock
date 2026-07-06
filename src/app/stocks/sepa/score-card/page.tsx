import fs from "fs/promises";
import path from "path";
import type { Scorecard } from "@/lib/scorecard";
import { ScorecardView } from "./ScorecardView";
import { SepaHoldingsSection, type HoldingsFeedbackFile } from "../SepaHoldingsSection";

async function readJson<T>(filename: string): Promise<T | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", filename);
    return JSON.parse(await fs.readFile(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

export default async function ScorecardPage() {
  const data = await readJson<Scorecard>("scorecard.json");
  const holdings = await readJson<HoldingsFeedbackFile>("sepa-holdings-feedback.json");
  return (
    <div className="space-y-10">
      {data ? (
        <ScorecardView data={data} />
      ) : (
        <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-sm text-on-surface-variant/70">
          정산표 데이터가 없습니다. <code className="text-xs">npm run scorecard</code> 실행 후 생성됩니다.
        </div>
      )}
      <SepaHoldingsSection data={holdings} />
    </div>
  );
}
