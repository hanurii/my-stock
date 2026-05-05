import { classificationLabel, type RotationSnapshot, type HotClassification } from "@/lib/hot-sectors";

export function SectorRotationChart({
  snapshots,
  transitions,
}: {
  snapshots: RotationSnapshot[];
  transitions: Array<{
    from_name: string;
    to_name: string;
    flow_direction: "cooling" | "heating";
    score_delta: number;
  }>;
}) {
  if (snapshots.length === 0) {
    return (
      <div className="text-on-surface-variant text-sm">
        로테이션 스냅샷이 아직 누적되지 않았습니다 (첫 실행). 시간이 지나며 자동으로 채워집니다.
      </div>
    );
  }

  // 모든 스냅샷에 등장하는 섹터 union
  const sectorNames = Array.from(
    new Set(snapshots.flatMap((s) => s.sectors.map((x) => x.name))),
  );

  function scoreFor(snapshot: RotationSnapshot, name: string): number | null {
    const found = snapshot.sectors.find((s) => s.name === name);
    return found ? found.real_hot_score : null;
  }

  function classFor(snapshot: RotationSnapshot, name: string): HotClassification | null {
    const found = snapshot.sectors.find((s) => s.name === name);
    return found ? found.classification : null;
  }

  function colorByScore(score: number | null): string {
    if (score == null) return "text-on-surface-variant/50";
    if (score >= 75) return "text-primary";
    if (score >= 60) return "text-tertiary";
    if (score >= 40) return "text-on-surface";
    return "text-error";
  }

  // 점수 변화 큰 순으로 정렬 (current vs 첫 스냅샷)
  const oldestSnap = snapshots[0];
  const newestSnap = snapshots[snapshots.length - 1];
  const sortedNames = [...sectorNames].sort((a, b) => {
    const aDelta = (scoreFor(newestSnap, a) ?? 0) - (scoreFor(oldestSnap, a) ?? 0);
    const bDelta = (scoreFor(newestSnap, b) ?? 0) - (scoreFor(oldestSnap, b) ?? 0);
    return bDelta - aDelta;
  });

  const labelForSnap: Record<RotationSnapshot["label"], string> = {
    "6m_ago": "6개월 전",
    "3m_ago": "3개월 전",
    "1m_ago": "1개월 전",
    current: "현재",
  };

  return (
    <div className="space-y-6">
      {/* Transitions */}
      {transitions.length > 0 ? (
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
          <p className="text-[11px] uppercase tracking-[0.16em] text-primary/90 mb-2">
            최근 1개월 자금 이동 시그널
          </p>
          <ul className="space-y-1">
            {transitions.slice(0, 4).map((t, i) => (
              <li key={i} className="text-sm text-on-surface flex items-center gap-2">
                <span className="text-error">{t.from_name}</span>
                <span className="text-on-surface-variant">→</span>
                <span className="text-primary">{t.to_name}</span>
                <span className="text-[11px] text-on-surface-variant ml-auto">
                  점수 차 +{Math.round(t.score_delta)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Snapshot table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-[10px] uppercase tracking-[0.16em] text-on-surface-variant/80 border-b border-outline-variant/20">
              <th className="text-left py-2 pr-3">섹터</th>
              {snapshots.map((s) => (
                <th key={s.label} className="text-right py-2 px-2 whitespace-nowrap">
                  {labelForSnap[s.label]}
                  <div className="text-[9px] font-normal text-on-surface-variant/60">
                    {s.date}
                  </div>
                </th>
              ))}
              <th className="text-right py-2 px-2">변화</th>
            </tr>
          </thead>
          <tbody>
            {sortedNames.map((name) => {
              const oldScore = scoreFor(oldestSnap, name);
              const newScore = scoreFor(newestSnap, name);
              const delta = newScore != null && oldScore != null ? newScore - oldScore : null;
              const newCls = classFor(newestSnap, name);
              return (
                <tr key={name} className="border-b border-outline-variant/10">
                  <td className="py-2 pr-3 text-on-surface">
                    {name}
                    {newCls ? (
                      <span className="text-[10px] text-on-surface-variant/70 ml-2">
                        {classificationLabel(newCls)}
                      </span>
                    ) : null}
                  </td>
                  {snapshots.map((snap) => {
                    const sc = scoreFor(snap, name);
                    return (
                      <td
                        key={snap.label}
                        className={`text-right px-2 font-medium ${colorByScore(sc)}`}
                      >
                        {sc ?? "—"}
                      </td>
                    );
                  })}
                  <td
                    className={`text-right px-2 font-medium ${
                      delta == null
                        ? "text-on-surface-variant"
                        : delta > 5
                          ? "text-primary"
                          : delta < -5
                            ? "text-error"
                            : "text-on-surface-variant"
                    }`}
                  >
                    {delta == null ? "—" : delta > 0 ? `+${delta}` : `${delta}`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
