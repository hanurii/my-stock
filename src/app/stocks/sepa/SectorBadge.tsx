// 8대 주도 섹터 배지 — 표시 전용(정렬·점수 무관여). ExportBadge(🚢) 형제.
// 데이터: public/data/sepa-leading-sectors.json (tag_leading_sectors.py 산출) — 파일 없으면 배지 없이 렌더.

export interface SectorTag {
  name?: string | null;
  rank: number;
  label: string;
  short: string;
  confidence?: string;
}
export type SectorTagMap = Record<string, SectorTag>;

export interface SectorTagsFile {
  asof?: string;
  config_asof?: string;
  tags?: SectorTagMap;
  unclassified?: { code: string; name?: string | null }[];
}

const CIRCLED = "①②③④⑤⑥⑦⑧";

// confidence low = 연한 배지 + "?" — 큐레이션 확인 전 경계 종목임을 표시.
const BADGE_STYLE = {
  normal: { color: "#c4b5fd", bg: "rgba(139,92,246,0.16)" },
  low: { color: "rgba(196,181,253,0.65)", bg: "rgba(139,92,246,0.10)" },
};

export function SectorBadge({ tag }: { tag?: SectorTag }) {
  if (!tag) return null;
  const low = tag.confidence === "low";
  const s = low ? BADGE_STYLE.low : BADGE_STYLE.normal;
  const num = tag.rank >= 1 && tag.rank <= 8 ? CIRCLED[tag.rank - 1] : String(tag.rank);
  return (
    <span
      title={`주도 섹터 ${tag.rank}위 — ${tag.label}${low ? " · 분류 확신 낮음(확인 필요)" : ""}`}
      className="inline-flex items-center gap-0.5 rounded px-1 py-px text-[10px] leading-none align-middle whitespace-nowrap"
      style={{ backgroundColor: s.bg, color: s.color }}
    >
      {num}{tag.short}
      {low && <span className="opacity-70">?</span>}
    </span>
  );
}
