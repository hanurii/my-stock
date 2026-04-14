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
  const pipelines = data?.pipelines || [];
  const bigpharmaDeals = data?.bigpharma_deals || [];

  const hasData = pipelines.length > 0 || bigpharmaDeals.length > 0;

  return (
    <div className="max-w-6xl mx-auto">
      <header className="mb-8">
        <h2 className="text-2xl font-bold font-serif text-primary tracking-tight">
          기대 바이오주
        </h2>
        <p className="text-xs text-on-surface-variant mt-2">
          한국 상장 바이오주 중 임상 2상/3상이 진행 중인 기술을 질적으로 검증합니다.
        </p>
        {data?.scanned_at && (
          <p className="text-xs text-on-surface-variant/50 mt-1">
            스캔일: {data.scanned_at} · 전체 {data.total_scanned?.toLocaleString()}종목 스캔 · 2상/3상 {pipelines.length}건 · 빅파마 딜 {bigpharmaDeals.length}건
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
        <BioPageTabs
          pipelines={pipelines}
          briefings={briefings}
          bigpharmaDeals={bigpharmaDeals}
        />
      )}
    </div>
  );
}
