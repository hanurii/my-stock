import { getGrade, type ScoreDetail } from "@/lib/scoring";

export function RankChange({ currentRank, previousRank }: { currentRank: number; previousRank?: number }) {
  if (previousRank == null) return null;
  const diff = previousRank - currentRank;
  if (diff > 0) return <span className="text-[11px] text-emerald-400 font-mono">{"\u25B2"}{diff}</span>;
  if (diff < 0) return <span className="text-[11px] text-red-400 font-mono">{"\u25BC"}{Math.abs(diff)}</span>;
  return null;
}

export function GradeChangeBadge({ grade, score, previousScore, compact }: {
  grade: string;
  score: number;
  previousScore?: number;
  compact?: boolean;
}) {
  if (previousScore == null || score === previousScore) return null;
  const prevGrade = getGrade(previousScore);
  const gradeChanged = prevGrade !== grade;
  const isUpgrade = score > previousScore;
  const color = isUpgrade ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400";
  const scoreDiff = score - previousScore;
  const sign = scoreDiff > 0 ? "+" : "";

  if (compact) {
    return (
      <span className={`text-[10px] px-1 py-0.5 rounded ${color}`}>
        {gradeChanged ? `${prevGrade}\u2192${grade}` : `${sign}${scoreDiff}`}
      </span>
    );
  }

  return null;
}

export function ScoreChangeComment({ score, previousScore, grade, details, previousDetails }: {
  score: number;
  previousScore?: number;
  grade: string;
  details: ScoreDetail[];
  previousDetails?: ScoreDetail[];
}) {
  if (previousScore == null || score === previousScore) return null;

  const isUpgrade = score > previousScore;
  const scoreDiff = score - previousScore;
  const scoreSign = scoreDiff > 0 ? "+" : "";
  const prevGrade = getGrade(previousScore);
  const gradeChanged = prevGrade !== grade;

  // 항목별 변동 비교
  const changedItems: { item: string; prevScore: number; currScore: number; diff: number }[] = [];
  if (previousDetails && previousDetails.length > 0) {
    details.forEach((curr) => {
      const prev = previousDetails.find((p) => p.item === curr.item);
      if (prev && prev.score !== curr.score) {
        changedItems.push({ item: curr.item, prevScore: prev.score, currScore: curr.score, diff: curr.score - prev.score });
      }
    });
  }

  return (
    <div className={`flex items-start gap-2 px-3 py-2 rounded-lg mb-3 ${isUpgrade ? "bg-emerald-500/5" : "bg-red-500/5"}`}>
      <span className="material-symbols-outlined text-sm mt-0.5 shrink-0" style={{ color: isUpgrade ? "#6eedb5" : "#ffb4ab" }}>
        {isUpgrade ? "trending_up" : "trending_down"}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          {gradeChanged
            ? <span className="text-xs font-bold" style={{ color: isUpgrade ? "#6eedb5" : "#ffb4ab" }}>{prevGrade}{"\u2192"}{grade}</span>
            : <span className="text-xs font-bold" style={{ color: isUpgrade ? "#6eedb5" : "#ffb4ab" }}>{scoreSign}{scoreDiff}점</span>
          }
          <span className="text-xs text-on-surface-variant/50">({previousScore}{"\u2192"}{score}점)</span>
          {changedItems.length > 0 && (
            <>
              <span className="text-xs text-on-surface-variant/30">|</span>
              {changedItems.map((c) => {
                const sign = c.diff > 0 ? "+" : "";
                const clr = c.diff > 0 ? "text-emerald-400" : "text-red-400";
                return (
                  <span key={c.item} className="text-xs text-on-surface-variant">
                    {c.item}{" "}
                    <span className="font-mono text-on-surface-variant/60">{c.prevScore}</span>
                    {"\u2192"}
                    <span className="font-mono text-on-surface-variant/60">{c.currScore}</span>
                    <span className={`font-mono font-bold ml-0.5 ${clr}`}>({sign}{c.diff})</span>
                  </span>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
