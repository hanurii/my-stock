import fs from "fs/promises";
import path from "path";
import Link from "next/link";
import { ManagerPortfolios, type Manager } from "./ManagerPortfolios";

interface ManagerData {
  generated_at: string;
  universe_size: number;
  fund_rankings_snapshot: string | null;
  manager_count: number;
  managers: Manager[];
}

interface FundRanking {
  manager: string;
  rank: number;
  return_pct: number;
  grade: string;
}

interface FundRankingsData {
  snapshot_date: string | null;
  rankings: {
    "1year"?: {
      computed?: {
        avg_return_pct?: number;
        managers?: FundRanking[];
      };
    };
    quarterly?: Record<string, Array<{ rank: number; manager: string; return_pct: number }>>;
  };
}

async function getManagerData(): Promise<ManagerData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "manager-portfolios.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

async function getFundRankings(): Promise<FundRankingsData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "fund-rankings.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export default async function CanslimIManagersPage() {
  const [data, fundRankings] = await Promise.all([getManagerData(), getFundRankings()]);

  if (!data) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            CAN SLIM — I: 운용사 관점
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">데이터가 아직 생성되지 않았습니다.</p>
        </header>
      </div>
    );
  }

  const topManagers = fundRankings?.rankings["1year"]?.computed?.managers || [];

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM — I: 운용사 관점
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          한국 주식에 5% 이상 베팅한 운용사·연기금이 어떤 종목에 집중하고 있는지 — 등급별 분류.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          모집단: <strong className="text-on-surface-variant">워치리스트 + L 통과 종목</strong>의 DART 5%룰 보고자 역인덱스.
          한국 운용사 등급은 fundguide.net 1년 수익률 Top 10 상대평가 (a+/a/a-).
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일 {data.generated_at} · 모집단 {data.universe_size}종목 · 매핑 운용사·연기금{" "}
          <strong className="text-on-surface-variant">{data.manager_count}개</strong>
        </p>
        <div className="mt-3">
          <Link
            href="/stocks/canslim/i"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg ghost-border text-xs text-on-surface-variant hover:bg-surface-container/50 transition-all"
          >
            <span className="material-symbols-outlined text-base">arrow_back</span>
            종목 관점으로 돌아가기
          </Link>
        </div>
      </header>

      {/* fundguide Top 10 1년 수익률 */}
      {topManagers.length > 0 && (
        <section className="bg-surface-container-low/50 rounded-xl ghost-border p-5">
          <h3 className="text-sm font-medium text-on-surface mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-base">leaderboard</span>
            fundguide 한국 국내주식형 1년 수익률 Top 10
            {fundRankings?.snapshot_date && (
              <span className="text-[10px] text-on-surface-variant/60 font-normal">
                ({fundRankings.snapshot_date} 스냅샷)
              </span>
            )}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
            {topManagers.map((m) => (
              <div
                key={m.manager}
                className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface-container/30"
              >
                <span className="font-mono text-[10px] w-6 text-on-surface-variant/60">#{m.rank}</span>
                <span
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded font-medium"
                  style={{
                    backgroundColor:
                      m.grade === "a+"
                        ? "#e9c17620"
                        : m.grade === "a"
                        ? "#95d3ba20"
                        : "#a8b5d020",
                    color: m.grade === "a+" ? "#e9c176" : m.grade === "a" ? "#95d3ba" : "#a8b5d0",
                  }}
                >
                  {m.grade}
                </span>
                <span className="flex-1 truncate text-on-surface">{m.manager}</span>
                <span className="font-mono text-on-surface-variant font-medium">
                  +{m.return_pct.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-on-surface-variant/50 mt-3">
            상대평가 (Top 10 한정, b/c 등급 없음): rank 1-3 = a+, 4-7 = a, 8-10 = a-. 등급은 모집단 워치리스트·L 통과 종목에 5%+ 보유한 운용사에만 매핑됨.
          </p>
        </section>
      )}

      {/* 운용사 카드 그리드 */}
      <section>
        <ManagerPortfolios
          managers={data.managers}
          universeSize={data.universe_size}
          fundSnapshot={data.fund_rankings_snapshot}
        />
      </section>

      <section className="bg-surface-container-low rounded-xl ghost-border p-5 text-xs text-on-surface-variant/80 space-y-2">
        <h3 className="text-sm font-medium text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-base">info</span>
          데이터 출처 + 한계
        </h3>
        <ul className="space-y-1 list-disc list-inside">
          <li>
            <strong>DART 5%룰 (대량보유보고)</strong>: 자본시장법상 의무 공시. 종목 보유 5% 이상 + 1%p 이상 변동 시 5일 내 보고.
          </li>
          <li>
            <strong>fundguide.net</strong> 1년 수익률 Top 10: 사용자가 분기마다 수동 입력. b/c 등급 없음 (Top 10 한정).
          </li>
          <li>
            글로벌 운용사 (BlackRock·Capital·Norges·Macquarie·Nomura 등) 는 fundguide 미수록 → <strong>unrated 글로벌</strong> 라벨. 단 5%+ 보유는 그 자체로 강한 시그널.
          </li>
          <li>
            모집단 외 종목 (KOSPI200+KOSDAQ150 전수) 보유는 잡히지 않음. 모집단 확장은 별도 작업.
          </li>
        </ul>
      </section>
    </div>
  );
}
