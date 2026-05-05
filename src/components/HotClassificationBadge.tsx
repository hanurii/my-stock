import {
  classificationLabel,
  classificationColor,
  type HotClassification,
} from "@/lib/hot-sectors";

const BG_BY_CLASS: Record<HotClassification, string> = {
  real_hot: "bg-primary/15 border-primary/40",
  real_hot_warning: "bg-primary/10 border-primary/30 border-dashed",
  emerging: "bg-tertiary/15 border-tertiary/40",
  short_burst: "bg-error/10 border-error/30",
  cooling: "bg-secondary/10 border-secondary/30",
  in_progress: "bg-tertiary/8 border-tertiary/25",
  fake_hot: "bg-error/8 border-error/30 border-dashed",
  neutral: "bg-on-surface-variant/8 border-on-surface-variant/20",
};

export function HotClassificationBadge({
  classification,
  compact = false,
}: {
  classification: HotClassification;
  compact?: boolean;
}) {
  const label = classificationLabel(classification);
  const color = classificationColor(classification);
  const bg = BG_BY_CLASS[classification];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${color} ${bg} ${
        compact ? "text-[10px] py-0.5" : ""
      }`}
    >
      {label}
    </span>
  );
}
