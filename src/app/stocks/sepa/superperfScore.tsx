// 초수익 잠재력 점수 표시 — 매수 추천·보유 점검 공용.

export interface SuperperfFactors {
  score: number;
  rs: number | null;
  prior_adv_pct: number | null;
  rs_nh_days: number | null;
  rs_leads: number | null;
  dist_52wh?: number | null;
}

// 점수 색: 4+ 초록 · 2~3 금색 · 0~1 회색
export function scoreStyle(s: number): { color: string; bg: string } {
  if (s >= 4) return { color: "#10b981", bg: "rgba(16,185,129,0.16)" };
  if (s >= 2) return { color: "#e9c176", bg: "rgba(233,193,118,0.14)" };
  return { color: "#a8b5d0", bg: "rgba(168,181,208,0.12)" };
}

// 상세 점수 내역 — 4개 요인의 획득/만점(✓ 획득·– 미획득)
export function SuperperfBreakdown({ sp, title }: { sp: SuperperfFactors; title?: string }) {
  const priorEarned = sp.prior_adv_pct == null ? 0 : sp.prior_adv_pct >= 100 ? 2 : sp.prior_adv_pct >= 50 ? 1 : 0;
  const rsEarned = sp.rs == null ? 0 : sp.rs >= 90 ? 2 : sp.rs >= 80 ? 1 : 0;
  const nhEarned = sp.rs_nh_days != null && sp.rs_nh_days <= 10 ? 1 : 0;
  const leadEarned = sp.rs_leads != null && sp.rs_leads > 0 ? 1 : 0;
  const factors: { name: string; value: string; earned: number; max: number }[] = [
    { name: "직전 상승폭", value: sp.prior_adv_pct == null ? "—" : `${sp.prior_adv_pct > 0 ? "+" : ""}${Math.round(sp.prior_adv_pct)}%`, earned: priorEarned, max: 2 },
    { name: "RS 상대강도", value: sp.rs != null ? String(sp.rs) : "—", earned: rsEarned, max: 2 },
    { name: "RS선 신고가", value: sp.rs_nh_days == null ? "—" : sp.rs_nh_days === 0 ? "오늘 (0일 전)" : `${sp.rs_nh_days}일 전`, earned: nhEarned, max: 1 },
    { name: "RS선 선행", value: sp.rs_leads == null ? "—" : sp.rs_leads > 0 ? `주가보다 ${sp.rs_leads}일 먼저` : "뒤처짐 (주가가 먼저)", earned: leadEarned, max: 1 },
  ];
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-[10px] font-bold tracking-wider text-on-surface-variant/50 uppercase">{title ?? "초수익 잠재력"}</span>
        <span className="text-xs font-bold tabular-nums text-on-surface">{sp.score} / 6점</span>
      </div>
      <div className="flex flex-col gap-1">
        {factors.map((f) => {
          const on = f.earned > 0;
          return (
            <div key={f.name} className={`flex items-center gap-2.5 text-[11.5px] ${on ? "" : "opacity-60"}`}>
              <span className="w-3 text-center" style={{ color: on ? "#34d399" : "var(--on-surface-variant)" }}>{on ? "✓" : "–"}</span>
              <span className="w-24 text-on-surface whitespace-nowrap">{f.name}</span>
              <span className="tabular-nums font-semibold w-11 text-right" style={{ color: on ? "#34d399" : "var(--on-surface-variant)" }}>{f.earned} / {f.max}</span>
              <span className="tabular-nums text-on-surface-variant/70 whitespace-nowrap">{f.value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
