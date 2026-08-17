// 실적 발표 임박 배지(📅) + 주간 요약 — 표시 전용(정렬·점수 무관여). SectorBadge·ExportBadge 형제.
// 데이터: public/data/sepa-earnings-calendar.json — 파일 없으면 배지·요약 없이 렌더.
// 발표는 쿠션 없는 이진 이벤트 — 배지·요약 모두 "발표 전 신규 매수 주의" 경고 목적.

export interface EarningsEntry {
  name?: string | null;
  status: "confirmed" | "estimated";
  expected: string; // 대표 예상일 YYYY-MM-DD
  window?: [string, string]; // 불확실 구간
  d_day: number; // asof 기준 expected까지 남은 달력일(거래일 아님). 지났으면 음수
  basis: string; // 근거 요약(툴팁용)
  last_report?: { date: string; title: string } | null;
}
export type EarningsMap = Record<string, EarningsEntry>;

export interface EarningsCalendarFile {
  asof?: string;
  generated_at?: string;
  byCode?: EarningsMap;
}

const BADGE_WINDOW_DAYS = 14; // 배지 노출 구간(오늘~2주)
const SUMMARY_WINDOW_DAYS = 7; // 주간 요약 노출 구간(오늘~1주)

// 확정 D-2 이내 = 강조(돌파와 같은 붉은 톤) · 확정 = 금색 · 추정 = 연한 회색
const BADGE_STYLE = {
  imminent: { color: "#ffb4ab", bg: "rgba(255,180,171,0.15)" },
  confirmed: { color: "#e9c176", bg: "rgba(233,193,118,0.14)" },
  estimated: { color: "#a8b5d0", bg: "rgba(168,181,208,0.12)" },
};

const WEEKDAY_KO = ["일", "월", "화", "수", "목", "금", "토"];

function fmtMD(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${Number(m)}/${Number(d)}`;
}
function fmtMDWeekday(iso: string): string {
  return `${fmtMD(iso)}(${WEEKDAY_KO[new Date(`${iso}T00:00:00`).getDay()]})`;
}

function tooltip(e: EarningsEntry): string {
  const when =
    e.status === "confirmed"
      ? `실적 발표 확정 ${fmtMDWeekday(e.expected)}`
      : `실적 발표 추정 ${e.window ? `${fmtMD(e.window[0])}~${fmtMD(e.window[1])}` : `~${fmtMD(e.expected)}`}(과거 발표 패턴)`;
  return `${when} — ${e.basis} — 발표 전 신규 매수 주의`;
}

export function EarningsBadge({ entry }: { entry?: EarningsEntry }) {
  if (!entry || entry.d_day < 0 || entry.d_day > BADGE_WINDOW_DAYS) return null;
  const confirmed = entry.status === "confirmed";
  const s = confirmed
    ? entry.d_day <= 2
      ? BADGE_STYLE.imminent
      : BADGE_STYLE.confirmed
    : BADGE_STYLE.estimated;
  return (
    <span
      title={tooltip(entry)}
      className="inline-flex items-center gap-0.5 rounded px-1 py-px text-[10px] leading-none align-middle whitespace-nowrap"
      style={{ backgroundColor: s.bg, color: s.color }}
    >
      {confirmed ? `📅D-${entry.d_day}` : `📅~${fmtMD(entry.expected)}`}
    </span>
  );
}

export function EarningsWeekSummary({ byCode }: { byCode?: EarningsMap }) {
  const entries = Object.entries(byCode ?? {})
    .filter(([, e]) => e.d_day >= 0 && e.d_day <= SUMMARY_WINDOW_DAYS)
    .sort((a, b) => a[1].d_day - b[1].d_day || (a[1].name ?? "").localeCompare(b[1].name ?? "", "ko"));
  if (entries.length === 0) return null;
  return (
    <section className="bg-surface-container-low rounded-xl ghost-border p-4">
      <h3 className="text-sm font-serif font-bold text-on-surface mb-2">
        📅 이번 주 실적 발표 예정
        <span className="text-[11px] font-normal text-on-surface-variant/60 ml-2">
          발표 전 신규 매수 주의 — 쿠션 없는 이진 이벤트
        </span>
      </h3>
      <ul className="space-y-1 text-[11px] text-on-surface-variant leading-relaxed">
        {entries.map(([code, e]) => {
          const confirmed = e.status === "confirmed";
          return (
            <li key={code}>
              <span className="tabular-nums font-medium text-on-surface">
                {fmtMDWeekday(e.expected)}
                {confirmed ? "" : "쯤"}
              </span>
              {" · "}
              <strong className="text-on-surface">{e.name ?? code}</strong>
              {" — "}
              <span style={{ color: confirmed ? BADGE_STYLE.confirmed.color : BADGE_STYLE.estimated.color }}>
                {confirmed ? "확정" : "추정(과거 패턴)"}
              </span>
              <span className="text-on-surface-variant/60"> · {e.basis}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
