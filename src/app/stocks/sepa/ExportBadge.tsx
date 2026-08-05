// 수출 주도 품목 배지 — 표시 전용(정렬·점수 무관여).
// 데이터: public/data/sepa-export-tags.json (tag_export_leaders.py 산출) — 파일 없으면 배지 없이 렌더.

export interface ExportTag {
  name?: string | null;
  category: string;
  label: string;
  tier: "direct" | "indirect";
  basis: string;
}
export type ExportTagMap = Record<string, ExportTag>;

export interface ExportTagsFile {
  asof?: string;
  config_asof?: string;
  tags?: ExportTagMap;
}

// direct = 진한 배지 · indirect(밸류체인) = 연한 배지 — 색은 기존 인라인 hex 팔레트 관례.
const BADGE_STYLE: Record<ExportTag["tier"], { color: string; bg: string }> = {
  direct: { color: "#7dd3fc", bg: "rgba(56,189,248,0.16)" },
  indirect: { color: "rgba(125,211,252,0.65)", bg: "rgba(56,189,248,0.10)" },
};

export function ExportBadge({ tag }: { tag?: ExportTag }) {
  if (!tag) return null;
  const direct = tag.tier === "direct";
  // 설정파일은 사용자 직접 관리 — tier 오타가 페이지 전체를 깨지 않게 폴백.
  const s = BADGE_STYLE[tag.tier] ?? BADGE_STYLE.indirect;
  return (
    <span
      title={`수출 주도 품목(${tag.label}${direct ? "" : " · 간접/밸류체인"}) — ${tag.basis}`}
      className="inline-flex items-center gap-0.5 rounded px-1 py-px text-[10px] leading-none align-middle whitespace-nowrap"
      style={{ backgroundColor: s.bg, color: s.color }}
    >
      🚢 {tag.label}
      {!direct && <span className="opacity-70">·간접</span>}
    </span>
  );
}
