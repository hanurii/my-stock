import fs from "fs/promises";
import path from "path";
import { BioPageTabs } from "./BioPageTabs";

// ── 데이터 로드 ──

async function loadJSON(filename: string) {
  try {
    const filePath = path.join(process.cwd(), "public", "data", filename);
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

// ── 페이지 ──

export default async function BioPage() {
  const data = await loadJSON("bio-watchlist.json");
  const briefings = (await loadJSON("bio-briefings.json")) || {};
  const research = (await loadJSON("bio-research.json")) || {};
  const pipelines = data?.pipelines || [];
  const bigpharmaDeals = data?.bigpharma_deals || [];

  const hasData = pipelines.length > 0 || bigpharmaDeals.length > 0;

  return (
    <div className="max-w-6xl mx-auto">
      <header className="mb-8">
        <h2 className="text-2xl font-bold font-serif text-primary tracking-tight">
          바이오주 모니터링
        </h2>
        <p className="text-xs text-on-surface-variant mt-2">
          관심 바이오 기업의 임상 파이프라인을 추적합니다.
        </p>
        {data?.scanned_at && (
          <p className="text-xs text-on-surface-variant/50 mt-1">
            스캔일: {data.scanned_at} · {data.total_scanned?.toLocaleString()}개 기업 · 파이프라인 {pipelines.length}건 · 빅파마 딜 {bigpharmaDeals.length}건
          </p>
        )}
      </header>

      {!hasData ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <span className="material-symbols-outlined text-5xl text-primary-dim/30 mb-4">
            biotech
          </span>
          <p className="text-on-surface-variant text-sm">
            아직 바이오주 데이터가 준비되지 않았습니다.
          </p>
          <p className="text-on-surface-variant/60 text-xs mt-1">
            npx tsx scripts/screen-bio.ts 실행 후 데이터가 채워집니다.
          </p>
        </div>
      ) : (
        <>
          <BioPageTabs
            pipelines={pipelines}
            briefings={briefings}
            bigpharmaDeals={bigpharmaDeals}
            research={research}
          />
        </>
      )}
    </div>
  );
}
