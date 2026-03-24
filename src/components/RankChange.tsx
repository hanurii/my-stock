import { getGrade } from "@/lib/scoring";

export function RankChange({ currentRank, previousRank }: { currentRank: number; previousRank?: number }) {
  if (previousRank == null) return null;
  const diff = previousRank - currentRank;
  if (diff > 0) return <span className="text-[11px] text-emerald-400 font-mono">{"\u25B2"}{diff}</span>;
  if (diff < 0) return <span className="text-[11px] text-red-400 font-mono">{"\u25BC"}{Math.abs(diff)}</span>;
  return null;
}

export function GradeChangeBadge({ grade, score, previousScore, gradeChangeReason, compact }: {
  grade: string;
  score: number;
  previousScore?: number;
  gradeChangeReason?: string;
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

  return (
    <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg mb-3 ${color}`}>
      {gradeChanged
        ? <span className="font-bold">{prevGrade}{"\u2192"}{grade}</span>
        : <span className="font-bold">{sign}{scoreDiff}점</span>
      }
      <span className="text-on-surface-variant/60">({previousScore}{"\u2192"}{score}점)</span>
      {gradeChangeReason && <span className="text-on-surface-variant/80">{gradeChangeReason}</span>}
    </div>
  );
}
