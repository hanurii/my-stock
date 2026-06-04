import fs from "fs/promises";
import path from "path";
import { RankingTable } from "../canslim/ranking/RankingTable";
import {
  PRINCIPLES,
  type Principle,
  type RankingCandidate,
} from "../canslim/ranking/types";
import { passesCGate } from "../canslim/lib/cFilter";
import type { CanslimCandidate } from "../canslim/CanslimTable";
import type { NCandidate } from "../canslim/NewHighsTable";

interface CanslimData {
  generated_at: string;
  candidates: CanslimCandidate[];
}

interface NData {
  generated_at: string;
  candidates: NCandidate[];
}

interface ACandidate {
  code: string;
  score: number;
  track: string;
  track_label: string;
  grade: string;
}

interface AData {
  generated_at: string;
  candidates: ACandidate[];
}

interface LCandidateRaw {
  code: string;
  rs_score: number;
}

interface LData {
  generated_at: string;
  candidates: LCandidateRaw[];
}

interface SCandidateRaw {
  code: string;
  s_score: number;
}

interface SDataFile {
  generated_at: string;
  candidates: SCandidateRaw[];
}

interface TrendCriterion {
  pass: boolean;
}

interface TrendCandidateRaw {
  code: string;
  rs: number | null;
  all_pass: boolean;
  criteria?: Record<string, TrendCriterion>;
}

interface TrendDataFile {
  generated_at: string;
  candidates: TrendCandidateRaw[];
}

interface CScoredDetail {
  yoy_pct: number | null;
  sales_yoy_pct: number | null;
}

interface CScoredCandidate {
  code: string;
  c_score: number | null;
  c_detailed: CScoredDetail;
}

interface CScoredData {
  generated_at: string;
  candidates: CScoredCandidate[];
}

async function readJson<T>(file: string): Promise<T | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", file);
    return JSON.parse(await fs.readFile(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

function emptyScores(): Record<Principle, number | null> {
  return PRINCIPLES.reduce((acc, p) => {
    acc[p] = null;
    return acc;
  }, {} as Record<Principle, number | null>);
}

// ─── 컷오프 상수 (ranking 페이지와 동일) ─────────
const C_SCORE_CUTOFF = 70;
const RS_CUTOFF = 88;
const TOTAL_CUTOFF = 250;

export default async function HeroProfilePage() {
  const [data, nData, aData, lData, sData, trendData, cScoredData] = await Promise.all([
    readJson<CanslimData>("can-slim-candidates.json"),
    readJson<NData>("can-slim-n-candidates.json"),
    readJson<AData>("can-slim-a-candidates.json"),
    readJson<LData>("can-slim-l-candidates.json"),
    readJson<SDataFile>("can-slim-s-candidates.json"),
    readJson<TrendDataFile>("trend-template-candidates.json"),
    readJson<CScoredData>("trend-template-c-scored.json"),
  ]);

  const nScoreByCode = new Map<string, number>();
  for (const nc of nData?.candidates ?? []) {
    if (nc.n_commentary) nScoreByCode.set(nc.code, nc.n_commentary.total_score);
  }
  const aByCode = new Map<string, ACandidate>();
  for (const ac of aData?.candidates ?? []) aByCode.set(ac.code, ac);
  const lScoreByCode = new Map<string, number>();
  for (const lc of lData?.candidates ?? []) lScoreByCode.set(lc.code, lc.rs_score);
  const sScoreByCode = new Map<string, number>();
  for (const sc of sData?.candidates ?? []) sScoreByCode.set(sc.code, sc.s_score);

  const trendByCode = new Map<string, TrendCandidateRaw>();
  for (const tc of trendData?.candidates ?? []) trendByCode.set(tc.code, tc);
  const cscoredByCode = new Map<string, CScoredCandidate>();
  for (const c of cScoredData?.candidates ?? []) cscoredByCode.set(c.code, c);

  // ─── ranking 페이지의 컷오프 동일 적용 ─────
  const allRows: RankingCandidate[] = (data?.candidates ?? [])
    .filter((c) => passesCGate(c.criteria.C))
    .map((c) => {
      const scores = emptyScores();
      scores.C = typeof c.c_score === "number" ? c.c_score : null;
      scores.N = nScoreByCode.get(c.code) ?? null;
      const a = aByCode.get(c.code);
      scores.A = a ? a.score : null;
      scores.L = lScoreByCode.get(c.code) ?? null;
      scores.S = sScoreByCode.get(c.code) ?? null;
      const total = PRINCIPLES.reduce((sum, p) => sum + (scores[p] ?? 0), 0);
      return {
        code: c.code,
        name: c.name,
        market: c.market,
        market_cap_eok: c.market_cap_eok,
        pct_from_52w_high: c.pct_from_52w_high,
        c_eps_accel_quality: c.criteria.C.eps_accel_quality ?? null,
        c_never_sell: c.criteria.C.never_sell,
        a_track_label: a?.track_label,
        a_grade: a?.grade,
        scores,
        total,
      };
    });

  const rankingPassed = allRows.filter((r) => {
    if ((r.scores.C ?? 0) < C_SCORE_CUTOFF) return false;
    if ((r.scores.L ?? 0) < RS_CUTOFF) return false;
    const t1 = trendByCode.get(r.code)?.criteria?.["1"]?.pass;
    if (t1 === false) return false;
    if (r.total < TOTAL_CUTOFF) return false;
    return true;
  });
  const rankingCodes = new Set(rankingPassed.map((r) => r.code));

  // ─── 트렌드 페이지 "최강 후보" 동일 조건 ─────
  // 트렌드 8 통과 + RS ≥ 88 + C ≥ 70 + 매출 YoY ≥ 0
  const trendStrongCodes = new Set<string>();
  for (const t of trendData?.candidates ?? []) {
    if (!t.all_pass) continue;
    const rs = t.rs;
    if (rs === null || rs === undefined || rs < 88) continue;
    const c = cscoredByCode.get(t.code);
    if (!c) continue;
    const cscore = c.c_score;
    const syoy = c.c_detailed?.sales_yoy_pct;
    if (cscore === null || cscore === undefined || cscore < 70) continue;
    if (syoy === null || syoy === undefined || syoy < 0) continue;
    trendStrongCodes.add(t.code);
  }

  // ─── 교집합 ─────
  const heroCodes = new Set([...rankingCodes].filter((c) => trendStrongCodes.has(c)));
  const heroes = rankingPassed
    .filter((r) => heroCodes.has(r.code))
    .sort((a, b) => b.total - a.total);

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          Hero Profile — 황금 후보
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          CAN SLIM 종합 ranking 컷오프와 트렌드 템플레이트 최강 후보 필터를 모두 통과한 종목.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5 leading-relaxed">
          <strong className="text-on-surface-variant">두 필터 모두 통과해야 노출.</strong>{" "}
          펀더멘털·상대강도·차트 추세·매출 동반·종합 점수가 모두 강한 종목만 추려집니다.
        </p>
      </header>

      {/* 조건 안내 */}
      <section className="rounded-xl bg-amber-500/[0.07] border border-amber-500/30 p-4">
        <p className="text-xs font-medium flex items-center gap-1.5 mb-2" style={{ color: "#e9c176" }}>
          <span className="material-symbols-outlined text-sm">verified</span>
          교집합 통과 기준 (두 필터 모두 만족)
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="bg-surface-container/40 rounded-lg p-3">
            <p className="font-medium text-on-surface mb-1.5 flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">leaderboard</span>
              ranking 페이지 컷오프
            </p>
            <ul className="text-on-surface-variant space-y-0.5 list-disc ml-4">
              <li>C 게이트 통과 (5조건)</li>
              <li>C 점수 ≥ {C_SCORE_CUTOFF}</li>
              <li>RS ≥ {RS_CUTOFF}</li>
              <li>트렌드 #1 (현주가 &gt; 150MA AND &gt; 200MA)</li>
              <li>총점 ≥ {TOTAL_CUTOFF}</li>
            </ul>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-3">
            <p className="font-medium text-on-surface mb-1.5 flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">trending_up</span>
              트렌드 페이지 최강 후보
            </p>
            <ul className="text-on-surface-variant space-y-0.5 list-disc ml-4">
              <li>트렌드 8조건 전부 통과</li>
              <li>RS ≥ 88</li>
              <li>C 점수 ≥ 70</li>
              <li>매출 YoY ≥ 0</li>
            </ul>
          </div>
        </div>
        <p className="text-[10px] text-on-surface-variant/55 mt-3 pt-2 border-t border-amber-500/15">
          <span className="material-symbols-outlined text-[12px] align-middle mr-0.5">info</span>
          C 게이트 통과 종목은 <strong className="text-on-surface-variant">KIS 통합시세 (KRX 정규장 + NXT 애프터 종가)</strong> 기준이고, 그 외 종목은 KRX 정규장 종가 기준입니다.
        </p>
      </section>

      {/* 카운트 카드 */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-surface-container-low rounded-lg p-4 ghost-border">
          <p className="text-[11px] text-on-surface-variant/70 mb-1">ranking 페이지 통과</p>
          <p className="text-2xl font-serif font-bold text-on-surface">{rankingPassed.length}</p>
        </div>
        <div className="bg-surface-container-low rounded-lg p-4 ghost-border">
          <p className="text-[11px] text-on-surface-variant/70 mb-1">트렌드 최강 후보</p>
          <p className="text-2xl font-serif font-bold text-on-surface">{trendStrongCodes.size}</p>
        </div>
        <div className="bg-amber-500/[0.07] rounded-lg p-4 border border-amber-500/30">
          <p className="text-[11px] mb-1" style={{ color: "#e9c176" }}>
            ★ 황금 후보 (교집합)
          </p>
          <p className="text-2xl font-serif font-bold" style={{ color: "#e9c176" }}>
            {heroes.length}
          </p>
        </div>
      </section>

      {/* 표 — RankingTable 재사용 */}
      {heroes.length > 0 ? (
        <RankingTable candidates={heroes} />
      ) : (
        <p className="text-center text-on-surface-variant/60 py-8 text-sm">
          현재 두 필터를 모두 통과하는 종목이 없습니다.
        </p>
      )}
    </div>
  );
}
