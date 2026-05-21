export type EpsAccelQuality = "none" | "mild" | "strong" | "explosive";

export const EPS_ACCEL_QUALITY_META: Record<
  EpsAccelQuality,
  { label: string; color: string; bg: string; weight: string; icon: string }
> = {
  none: { label: "—", color: "var(--on-surface-variant)", bg: "transparent", weight: "", icon: "" },
  mild: {
    label: "가속",
    color: "#6ee7b7",
    bg: "rgba(110,231,183,0.12)",
    weight: "",
    icon: "▲",
  },
  strong: {
    label: "강력 가속",
    color: "#34d399",
    bg: "rgba(52,211,153,0.15)",
    weight: "font-semibold",
    icon: "▲▲",
  },
  explosive: {
    label: "폭발 가속",
    color: "#10b981",
    bg: "rgba(16,185,129,0.20)",
    weight: "font-bold",
    icon: "🔥",
  },
};
