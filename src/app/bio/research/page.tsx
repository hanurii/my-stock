import fs from "fs/promises";
import path from "path";
import { CompanyResearch } from "../CompanyResearch";

async function loadJSON(filename: string) {
  try {
    const filePath = path.join(process.cwd(), "public", "data", filename);
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export default async function ResearchPage() {
  const research = (await loadJSON("bio-research.json")) || {};

  return (
    <div className="max-w-6xl mx-auto">
      <header className="mb-8">
        <h2 className="text-2xl font-bold font-serif text-primary tracking-tight">
          기업 심층 분석
        </h2>
        <p className="text-xs text-on-surface-variant mt-2">
          시동위키 7대 기준으로 한국 바이오 기업의 기술력을 질적으로 검증합니다.
        </p>
      </header>

      {Object.keys(research).length > 0 ? (
        <CompanyResearch research={research} />
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <span className="material-symbols-outlined text-5xl text-primary-dim/30 mb-4">
            lab_research
          </span>
          <p className="text-on-surface-variant text-sm">
            아직 심층 분석 데이터가 준비되지 않았습니다.
          </p>
        </div>
      )}
    </div>
  );
}
