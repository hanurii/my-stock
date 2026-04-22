import fs from "fs/promises";
import path from "path";

export type ResearchStatus = "holding" | "interested" | "watching";
export type Tone = "good" | "warn" | "bad" | "neutral";

export interface ResearchIndexEntry {
  code: string;
  name: string;
  sector: string;
  market: string;
  status: ResearchStatus;
  verdict: string;
  verdict_tone: Tone;
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
  verdict: { label: string; tone: Tone; summary?: string };
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
