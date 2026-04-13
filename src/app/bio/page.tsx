import fs from "fs/promises";
import path from "path";
import { BioTabs } from "./BioTabs";

// ── 데이터 로드 ──

async function getData() {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "bio-watchlist.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

// ── 페이지 ──

export default async function BioPage() {
  const data = await getData();
  const hasData = data?.track_a?.candidates?.length > 0 || data?.track_b?.candidates?.length > 0;

  return (
    <div className="max-w-6xl mx-auto">
      <header className="mb-8">
        <h2 className="text-2xl font-bold font-serif text-primary tracking-tight">
          기대 바이오주
        </h2>
        <p className="text-xs text-on-surface-variant mt-2">
          한국 상장 바이오주 중 투자 매력이 높은 기업을 7대 기준으로 선별합니다.
        </p>
        {data?.scanned_at && (
          <p className="text-xs text-on-surface-variant/50 mt-1">
            스캔일: {data.scanned_at} · 전체 {data.total_scanned?.toLocaleString()}종목
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
        <BioTabs
          trackA={data.track_a.candidates}
          trackB={data.track_b.candidates}
        />
      )}
    </div>
  );
}
