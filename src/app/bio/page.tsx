import fs from "fs/promises";
import path from "path";

// ── 타입 ──

interface BioCandidate {
  code: string;
  name: string;
  market: string;
  score: number;
  grade: string;
  market_cap: number;
  current_price: number;
}

interface BioData {
  updated_at: string;
  total_scanned: number;
  candidates: BioCandidate[];
}

// ── 데이터 로드 ──

async function getData(): Promise<BioData | null> {
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

  if (!data || data.candidates.length === 0) {
    return (
      <div className="max-w-6xl mx-auto">
        <header className="mb-10">
          <h2 className="text-2xl font-bold font-serif text-primary tracking-tight">
            기대 바이오주
          </h2>
          <p className="text-xs text-on-surface-variant mt-2">
            한국 상장 바이오주 중 투자 매력이 높은 기업을 선별합니다.
          </p>
        </header>

        <div className="flex flex-col items-center justify-center py-20 text-center">
          <span className="material-symbols-outlined text-5xl text-primary-dim/30 mb-4">
            biotech
          </span>
          <p className="text-on-surface-variant text-sm">
            아직 바이오주 데이터가 준비되지 않았습니다.
          </p>
          <p className="text-on-surface-variant/60 text-xs mt-1">
            선별 기준 확정 후 데이터가 채워집니다.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <header className="mb-10">
        <h2 className="text-2xl font-bold font-serif text-primary tracking-tight">
          기대 바이오주
        </h2>
        <p className="text-xs text-on-surface-variant mt-2">
          {data.updated_at} 기준 · 총 {data.total_scanned}개 스캔 · {data.candidates.length}개 선별
        </p>
      </header>

      {/* 후속 구현: 스코어링 기준에 따른 종목 카드 및 테이블 */}
    </div>
  );
}
