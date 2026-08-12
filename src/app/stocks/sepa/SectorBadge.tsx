// 주도 섹터 배지(①~⑧ = 8대 주도 섹터, ⑨백화점 = 주도주 랠리 동행 소비주) — 표시 전용(정렬·점수 무관여).
// ExportBadge(🚢) 형제. 데이터: public/data/sepa-leading-sectors.json (tag_leading_sectors.py 산출) — 파일 없으면 배지 없이 렌더.

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

const CIRCLED = "①②③④⑤⑥⑦⑧⑨";

// confidence low = 연한 배지 + "?" — 큐레이션 확인 전 경계 종목임을 표시.
const BADGE_STYLE = {
  normal: { color: "#c4b5fd", bg: "rgba(139,92,246,0.16)" },
  low: { color: "rgba(196,181,253,0.65)", bg: "rgba(139,92,246,0.10)" },
};

export function SectorBadge({ tag }: { tag?: SectorTag }) {
  if (!tag) return null;
  const low = tag.confidence === "low";
  const s = low ? BADGE_STYLE.low : BADGE_STYLE.normal;
  const num = tag.rank >= 1 && tag.rank <= 9 ? CIRCLED[tag.rank - 1] : String(tag.rank);
  // rank 9(백화점)는 주도 섹터 순위가 아니라 동행 소비주 표시 — 툴팁 문구 구분.
  const title = tag.rank === 9
    ? `${tag.label} — 주도 섹터 랠리 동행 표시`
    : `주도 섹터 ${tag.rank}위 — ${tag.label}${low ? " · 분류 확신 낮음(확인 필요)" : ""}`;
  return (
    <span
      title={title}
      className="inline-flex items-center gap-0.5 rounded px-1 py-px text-[10px] leading-none align-middle whitespace-nowrap"
      style={{ backgroundColor: s.bg, color: s.color }}
    >
      {num}{tag.short}
      {low && <span className="opacity-70">?</span>}
    </span>
  );
}
