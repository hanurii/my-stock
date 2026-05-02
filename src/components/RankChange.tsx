import { getGrade, type ScoreDetail, type ScoreChangeEntry } from "@/lib/scoring";

export function RankChange({ currentRank, previousRank }: { currentRank: number; previousRank?: number }) {
  if (previousRank == null) return null;
  const diff = previousRank - currentRank;
  if (diff > 0) return <span className="text-[11px] text-emerald-400 font-mono">{"▲"}{diff}</span>;
  if (diff < 0) return <span className="text-[11px] text-red-400 font-mono">{"▼"}{Math.abs(diff)}</span>;
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
        {gradeChanged ? `${prevGrade}→${grade}` : `${sign}${scoreDiff}`}
      </span>
    );
  }

  return null;
}

interface ChangedItem {
  item: string;
  prevScore: number;
  currScore: number;
  diff: number;
}

function ChangeRow({
  fromScore,
  toScore,
  changedItems,
  timestamp,
  dim,
}: {
  fromScore: number;
  toScore: number;
  changedItems: ChangedItem[];
  timestamp?: string;
  dim?: boolean;
}) {
  const isUpgrade = toScore > fromScore;
  const scoreDiff = toScore - fromScore;
  const scoreSign = scoreDiff > 0 ? "+" : "";
  const prevGrade = getGrade(fromScore);
  const newGrade = getGrade(toScore);
  const gradeChanged = prevGrade !== newGrade;
  const headerColor = isUpgrade ? "#6eedb5" : "#ffb4ab";

  return (
    <div className={`flex items-start gap-2 ${dim ? "opacity-70" : ""}`}>
      <span className="material-symbols-outlined text-sm mt-0.5 shrink-0" style={{ color: headerColor }}>
        {isUpgrade ? "trending_up" : "trending_down"}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          {gradeChanged
            ? <span className="text-xs font-bold" style={{ color: headerColor }}>{prevGrade}{"→"}{newGrade}</span>
            : <span className="text-xs font-bold" style={{ color: headerColor }}>{scoreSign}{scoreDiff}점</span>
          }
          <span className="text-xs text-on-surface-variant/50">({fromScore}{"→"}{toScore}점)</span>
          {timestamp && (
            <span className="text-[10px] text-on-surface-variant/40 font-mono">{timestamp}</span>
          )}
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
                    {"→"}
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

export function ScoreChangeComment({ score, previousScore, grade, details, previousDetails, scoreHistory }: {
  score: number;
  previousScore?: number;
  grade: string;
  details: ScoreDetail[];
  previousDetails?: ScoreDetail[];
  scoreHistory?: ScoreChangeEntry[];
}) {
  void grade; // grade는 latest.to에서 파생되므로 외부 prop은 미사용
  // score_history 우선 사용 (최근 2건). 없으면 previous_details 비교로 fallback (백워드 호환).
  const hasHistory = Array.isArray(scoreHistory) && scoreHistory.length > 0;

  if (!hasHistory) {
    if (previousScore == null || score === previousScore) return null;
    const changedItems: ChangedItem[] = [];
    if (previousDetails && previousDetails.length > 0) {
      details.forEach((curr) => {
        const prev = previousDetails.find((p) => p.item === curr.item);
        if (prev && prev.score !== curr.score) {
          changedItems.push({ item: curr.item, prevScore: prev.score, currScore: curr.score, diff: curr.score - prev.score });
        }
      });
    }
    const isUpgrade = score > previousScore;
    return (
      <div className={`px-3 py-2 rounded-lg mb-3 ${isUpgrade ? "bg-emerald-500/5" : "bg-red-500/5"}`}>
        <ChangeRow fromScore={previousScore} toScore={score} changedItems={changedItems} />
      </div>
    );
  }

  const history = scoreHistory!;
  const latest = history[0];
  const prior = history[1]; // 최대 2건만 저장됨
  const latestUp = latest.to > latest.from;

  return (
    <div className={`px-3 py-2 rounded-lg mb-3 space-y-1 ${latestUp ? "bg-emerald-500/5" : "bg-red-500/5"}`}>
      <ChangeRow
        fromScore={latest.from}
        toScore={latest.to}
        timestamp={latest.at}
        changedItems={latest.details_diff.map((d) => ({ item: d.item, prevScore: d.from, currScore: d.to, diff: d.diff }))}
      />
      {prior && (
        <ChangeRow
          fromScore={prior.from}
          toScore={prior.to}
          timestamp={prior.at}
          changedItems={prior.details_diff.map((d) => ({ item: d.item, prevScore: d.from, currScore: d.to, diff: d.diff }))}
          dim
        />
      )}
    </div>
  );
}
