import fs from "fs/promises";
import path from "path";

export type ResearchStatus = "holding" | "interested" | "watching";
export type Tone = "good" | "warn" | "bad" | "neutral";
export type VerdictLevel =
  | "buy"
  | "scaled_buy"
  | "hold"
  | "watch_exit"
  | "scaled_sell"
  | "full_exit";

export interface ResearchIndexEntry {
  code: string;
  name: string;
  sector: string;
  market: string;
  status: ResearchStatus;
  verdict_level: VerdictLevel;
  verdict_comment?: string;
  thesis: string;
  updated_at: string;
}

export interface ResearchDetail {
  code: string;
  name: string;
  sector: string;
  market: string;
  status: ResearchStatus;
  updated_at: string;
  thesis: string;
  verdict: { level: VerdictLevel; comment?: string; summary?: string };
  entry_timing?: {
    label: string;
    tone: Tone;
    headline: string;
    reasons: { tone: Tone; text: string }[];
  };
  investment_thesis?: {
    label: string;
    tone: Tone;
    headline: string;
    reasons: { tone: Tone; text: string }[];
  };
  exit_timing?: {
    label: string;
    tone: Tone;
    headline: string;
    reasons: { tone: Tone; text: string }[];
  };
  snapshot?: {
    current_price?: number;
    market_cap_billion?: number;
    per?: number;
    pbr?: number;
    dividend_yield?: number;
    foreign_ratio?: number;
    treasury_ratio?: number;
    price_as_of?: string;
  };
  scoring_refs?: {
    framework: string;
    score: number;
    rank?: number;
    grade?: string;
    applicable: boolean;
    note?: string;
  }[];
  dilution_checklist?: { item: string; signal: Tone; detail: string }[];
  bond_overhang?: {
    title: string;
    subtitle?: string;
    columns: string[];
    rows: { cells: string[]; tone?: Tone }[];
    footnote?: string;
  };
  holding_capacity?: {
    title: string;
    total_shares: number;
    current_snt_holdings: number;
    snt_holdings_ratio: number;
    foundation_shares?: number;
    foundation_ratio?: number;
    total_related_ratio?: number;
    control_floor_pct: number;
    control_floor_shares: number;
    remaining_cushion_shares: number;
    sold_past_10m_shares?: number;
    interpretation: string;
  };
  timeline?: { date: string; event: string; source?: string }[];
  critical_points?: { tone: Tone; title: string; body: string }[];
  execution_plan?: {
    strategy: string;
    target_slot: string;
    steps: { phase: string; size_pct: number; trigger: string; reason: string }[];
    stop_condition?: string;
    core_principle?: string;
  };
  sources?: { label: string; ref: string }[];
}

const RESEARCH_DIR = path.join(process.cwd(), "public", "data", "research");

export async function loadResearchIndex(): Promise<ResearchIndexEntry[]> {
  try {
    const raw = await fs.readFile(path.join(RESEARCH_DIR, "index.json"), "utf-8");
    const data = JSON.parse(raw) as { entries: ResearchIndexEntry[] };
    return data.entries ?? [];
  } catch {
    return [];
  }
}

export async function loadResearchDetail(code: string): Promise<ResearchDetail | null> {
  try {
    const raw = await fs.readFile(path.join(RESEARCH_DIR, `${code}.json`), "utf-8");
    return JSON.parse(raw) as ResearchDetail;
  } catch {
    return null;
  }
}

export const STATUS_LABEL: Record<ResearchStatus, string> = {
  holding: "보유 중",
  interested: "매수 검토",
  watching: "관심 종목",
};

export const STATUS_COLOR: Record<ResearchStatus, string> = {
  holding: "#95d3ba",
  interested: "#e9c176",
  watching: "#bcc7de",
};

export const TONE_COLOR: Record<Tone, string> = {
  good: "#95d3ba",
  warn: "#e9c176",
  bad: "#ffb4ab",
  neutral: "#bcc7de",
};

export const TONE_ICON: Record<Tone, string> = {
  good: "check_circle",
  warn: "warning",
  bad: "cancel",
  neutral: "info",
};

export const VERDICT_ORDER: VerdictLevel[] = [
  "buy",
  "scaled_buy",
  "hold",
  "watch_exit",
  "scaled_sell",
  "full_exit",
];

export const VERDICT_LABEL: Record<VerdictLevel, string> = {
  buy: "매수 추천",
  scaled_buy: "분할 매수 추천",
  hold: "보유 유지",
  watch_exit: "매도 모니터링 필요",
  scaled_sell: "분할 매도 추천",
  full_exit: "전량 매도 추천",
};

export const VERDICT_COLOR: Record<VerdictLevel, string> = {
  buy: "#7ab8ff",
  scaled_buy: "#9fd2e8",
  hold: "#95d3ba",
  watch_exit: "#e9c176",
  scaled_sell: "#e9a36f",
  full_exit: "#d97a78",
};

export const VERDICT_DESCRIPTION: Record<VerdictLevel, string> = {
  buy: "진입 시그널 강함, 적극 매수",
  scaled_buy: "조건 충족, 분할 진입 권장",
  hold: "현 비중 유지, 특이 변동 없음",
  watch_exit: "트리거 임박, 매도 준비",
  scaled_sell: "비중 축소, 분할 차익실현",
  full_exit: "시그널 깨짐, 청산 권장",
};

export function formatVerdict(level: VerdictLevel, comment?: string): string {
  const base = VERDICT_LABEL[level];
  return comment ? `${base} (${comment})` : base;
}
