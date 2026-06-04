import fs from "fs/promises";
import path from "path";
import { RankingTable } from "./RankingTable";
import {
  PRINCIPLES,
  PRINCIPLE_LABELS,
  PRINCIPLE_MAX,
  TOTAL_MAX,
  type Principle,
  type RankingCandidate,
} from "./types";
import { passesCGate } from "../lib/cFilter";
import type { CanslimCandidate } from "../CanslimTable";
import type { NCandidate } from "../NewHighsTable";

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
  value: unknown;
  detail: string;
}

interface TrendCandidateRaw {
  code: string;
  criteria?: Record<string, TrendCriterion>;
}

interface TrendDataFile {
  generated_at: string;
  candidates: TrendCandidateRaw[];
}

async function getData(): Promise<CanslimData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

async function getNData(): Promise<NData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-n-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

async function getAData(): Promise<AData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-a-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

async function getLData(): Promise<LData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-l-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

async function getSData(): Promise<SDataFile | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-s-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

async function getTrendData(): Promise<TrendDataFile | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "trend-template-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

function emptyScores(): Record<Principle, number | null> {
  return PRINCIPLES.reduce(
    (acc, p) => {
      acc[p] = null;
      return acc;
    },
    {} as Record<Principle, number | null>,
  );
}

export default async function CanslimRankingPage() {
  const [data, nData, aData, lData, sData, trendData] = await Promise.all([
    getData(),
    getNData(),
    getAData(),
    getLData(),
    getSData(),
    getTrendData(),
  ]);

  // N 점수 lookup (code → 원본 30점 만점 점수)
  const nScoreByCode = new Map<string, number>();
  for (const nc of nData?.candidates ?? []) {
    if (nc.n_commentary) {
      nScoreByCode.set(nc.code, nc.n_commentary.total_score);
    }
  }

  // A 점수 lookup (code → 원본 50점 만점 점수 + 트랙·등급 메타)
  const aByCode = new Map<string, ACandidate>();
  for (const ac of aData?.candidates ?? []) {
    aByCode.set(ac.code, ac);
  }

  // L 점수 lookup (code → RS 0~99, 데이터 부족은 0)
  const lScoreByCode = new Map<string, number>();
  for (const lc of lData?.candidates ?? []) {
    lScoreByCode.set(lc.code, lc.rs_score);
  }

  // S 점수 lookup (code → 60점 만점, 정규화 없음)
  const sScoreByCode = new Map<string, number>();
  for (const sc of sData?.candidates ?? []) {
    sScoreByCode.set(sc.code, sc.s_score);
  }

  // 트렌드 #1 (현주가 > 150MA AND > 200MA) lookup. 트렌드 평가 데이터가 있는 종목만 판정 가능.
  const trend1ByCode = new Map<string, boolean>();
  for (const tc of trendData?.candidates ?? []) {
    const c1 = tc.criteria?.["1"];
    if (c1) trend1ByCode.set(tc.code, c1.pass);
  }

  // 각 letter screener 의 데이터 생성일 (사용자 표시용)
  const generatedAt: Record<Principle, string | null> = {
    C: data?.generated_at ?? null,
    A: aData?.generated_at ?? null,
    N: nData?.generated_at ?? null,
    S: sData?.generated_at ?? null,
    L: lData?.generated_at ?? null,
    I: null,
    M: data?.generated_at ?? null,  // M은 풀스캔 시 KOSPI 추세 판정
  };

  // ── 컷오프 기준: C ≥ 70 AND RS ≥ 88 AND 트렌드 #1 AND 총점 ≥ 250 ─────
  // 사용자 정의: 네 조건을 모두 만족해야 ranking 페이지 노출.
  // 트렌드 #1: 현주가 > 150MA AND > 200MA — 차트가 죽은 종목 자동 제외.
  // 총점 ≥ 250: 어느 한 원칙이 강해도 다른 원칙 평균 이하면 종합 약함 → 제외.
  const C_SCORE_CUTOFF = 70;
  const RS_CUTOFF = 88;
  const TOTAL_CUTOFF = 250;

  const gatePassed = (data?.candidates ?? []).filter((c) => passesCGate(c.criteria.C));

  const allRows: RankingCandidate[] = gatePassed.map((c) => {
    const scores = emptyScores();
    scores.C = typeof c.c_score === "number" ? c.c_score : null;
    const nScore = nScoreByCode.get(c.code);
    scores.N = typeof nScore === "number" ? nScore : null;
    const a = aByCode.get(c.code);
    scores.A = a ? a.score : null;
    const lScore = lScoreByCode.get(c.code);
    scores.L = typeof lScore === "number" ? lScore : null;
    const sScore = sScoreByCode.get(c.code);
    scores.S = typeof sScore === "number" ? sScore : null;
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

  const candidates: RankingCandidate[] = allRows.filter((r) => {
    if ((r.scores.C ?? 0) < C_SCORE_CUTOFF) return false;
    if ((r.scores.L ?? 0) < RS_CUTOFF) return false;
    // 트렌드 #1 — 데이터 없으면 통과 처리(보수적). 데이터 있고 미통과면 제외.
    const t1 = trend1ByCode.get(r.code);
    if (t1 === false) return false;
    if (r.total < TOTAL_CUTOFF) return false;
    return true;
  });
  const cutoffRemoved = allRows.length - candidates.length;

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 종합 랭킹
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          각 원칙(C·A·N·S·L·I·M)별 원본 점수를 합산해 내림차순으로 표시.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5 leading-relaxed">
          현재 산정 만점: <strong className="text-on-surface-variant">{TOTAL_MAX}점</strong>{" "}
          (C 100 + A 50 + N 30 + S 60 + L 99 · I/M 미산정). 컬럼 헤더 클릭으로 원칙별 정렬 가능.
        </p>
        {data?.generated_at && (
          <p className="text-[11px] text-on-surface-variant/50 mt-1">
            생성일: {data.generated_at} · 노출 {candidates.length}종목 (C 게이트 + 컷오프 통과)
          </p>
        )}
      </header>

      {/* 컷오프 안내 */}
      <section className="rounded-xl bg-amber-500/[0.07] border border-amber-500/30 p-4">
        <p className="text-xs font-medium flex items-center gap-1.5 mb-1.5" style={{ color: "#e9c176" }}>
          <span className="material-symbols-outlined text-sm">filter_alt</span>
          컷오프 기준 적용 중
        </p>
        <p className="text-xs text-on-surface-variant leading-relaxed">
          <strong className="text-on-surface">C 점수 ≥ {C_SCORE_CUTOFF}</strong> AND{" "}
          <strong className="text-on-surface">RS ≥ {RS_CUTOFF}</strong> AND{" "}
          <strong className="text-on-surface">트렌드 #1 통과</strong> (현주가 &gt; 150MA AND &gt; 200MA) AND{" "}
          <strong className="text-on-surface">총점 ≥ {TOTAL_CUTOFF}</strong> — 네 조건을 모두 만족하지 못한 종목은 자동 제외됩니다.
        </p>
        <p className="text-[10px] text-on-surface-variant/60 mt-1.5 tabular-nums">
          C 게이트 통과 {allRows.length}종목 → 컷오프 통과 {candidates.length}종목 (제외 {cutoffRemoved}종목)
        </p>
      </section>

      <section className="rounded-xl ghost-border bg-surface-container-low/50 p-4">
        <p className="text-xs font-medium text-on-surface-variant mb-2 flex items-center gap-1.5">
          <span className="material-symbols-outlined text-sm text-primary">info</span>
          원칙별 점수 기준
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 text-[11px]">
          {PRINCIPLES.map((p) => {
            const max = PRINCIPLE_MAX[p];
            const gen = generatedAt[p];
            return (
              <div
                key={p}
                className="flex flex-col bg-surface-container/40 rounded-md px-2 py-1.5 leading-tight"
              >
                <span className="font-serif font-bold text-primary text-sm">{p}</span>
                <span className="text-on-surface-variant/70">{PRINCIPLE_LABELS[p]}</span>
                <span className="text-on-surface-variant/50 text-[10px] mt-0.5">
                  {max !== null ? `${max}점 만점` : "미산정"}
                </span>
                <span
                  className="text-on-surface-variant/40 text-[9px] mt-0.5 tabular-nums"
                  title="이 원칙 점수의 데이터 기준 일자"
                >
                  {gen ?? "—"}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-[10px] text-on-surface-variant/50 mt-2 leading-relaxed">
          * 원칙마다 만점이 다릅니다 (C 100 · A 50 · N 30 · S 60 · L 99). 정규화 없이 원본 점수 그대로 합산합니다. 점수가 산정되지 않은 원칙은 &mdash;로 표시.
        </p>
      </section>

      <RankingTable candidates={candidates} />
    </div>
  );
}
