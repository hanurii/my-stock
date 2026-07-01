// SEPA 패턴 대시보드 순수 로직: 티어 분류·정렬·섹션 빌드·패턴 레지스트리.
// 프레임워크 비의존(서버/클라이언트 양쪽에서 import 가능, vitest로 단위 테스트).

export const WATCH_PCT = 12;

export type Tier = "breakout" | "actionable" | "watch";
export type PatternStatus = "breakout" | "actionable" | "forming" | "failed";

export interface RawCandidate {
  code: string;
  name: string;
  market: string;
  current_price: number;
  rs: number | null;
  status?: string;
  pivot_price?: number | null;
  pct_to_pivot?: number | null;
  [k: string]: unknown;
}

export interface ClassifiedRow {
  code: string;
  name: string;
  market: string;
  current_price: number;
  rs: number | null;
  status: string;
  pivot_price: number | null;
  pct_to_pivot: number | null;
  tier: Tier;
  raw: RawCandidate;
}

export interface PatternColumn {
  key: string;
  label: string;
  // pct=부호 있는 증감(+/−) · depth/tight=크기(부호 없는 양수 %) · price/int/ratio/days
  kind: "pct" | "depth" | "price" | "int" | "ratio" | "days" | "tight";
}

export interface PatternConfig {
  id: string;
  label: string;
  file: string;
  detectField: string;
  structureOk: (raw: RawCandidate) => boolean;
  columns: PatternColumn[];
}

export interface SectionResult {
  rows: ClassifiedRow[];
  counts: { breakout: number; actionable: number; watch: number };
}

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

// 티어 분류. 입력은 정규화된 원시값(detected·structureOk 는 호출자가 패턴별로 계산해 전달).
export function classify(
  c: { detected: boolean; status: string; pivot_price: number | null; pct_to_pivot: number | null; structureOk: boolean },
  watchPct: number = WATCH_PCT
): Tier | null {
  if (c.detected && c.status === "breakout") return "breakout";
  if (c.detected && c.status === "actionable") return "actionable";
  if (c.detected && c.status === "forming") return "watch";
  const nearPivot =
    c.pivot_price != null &&
    c.pct_to_pivot != null &&
    c.pct_to_pivot >= 0 &&
    c.pct_to_pivot <= watchPct;
  if (c.status !== "failed" && nearPivot && c.structureOk) return "watch";
  return null;
}

const TIER_ORDER: Record<Tier, number> = { breakout: 0, actionable: 1, watch: 2 };

// 정렬: 티어(🔴→🟢→🟡) → abs(pct_to_pivot) 오름차순 → rs 내림차순. in-place.
export function sortRows(rows: ClassifiedRow[]): void {
  rows.sort((a, b) => {
    const t = TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
    if (t !== 0) return t;
    const ap = a.pct_to_pivot == null ? Infinity : Math.abs(a.pct_to_pivot);
    const bp = b.pct_to_pivot == null ? Infinity : Math.abs(b.pct_to_pivot);
    if (ap !== bp) return ap - bp;
    return (b.rs ?? -1) - (a.rs ?? -1);
  });
}

// 레코드 1건 → 티어(숨김이면 null). buildSection·tierHistory 공유(DRY).
export function classifyCandidate(
  raw: RawCandidate,
  config: PatternConfig,
  watchPct: number = WATCH_PCT
): Tier | null {
  const detected = Boolean(raw[config.detectField]);
  const structureOk = config.structureOk(raw);
  return classify(
    {
      detected,
      status: String(raw.status ?? ""),
      pivot_price: num(raw.pivot_price),
      pct_to_pivot: num(raw.pct_to_pivot),
      structureOk,
    },
    watchPct
  );
}

export function buildSection(
  candidates: RawCandidate[] | null | undefined,
  config: PatternConfig,
  watchPct: number = WATCH_PCT
): SectionResult {
  const rows: ClassifiedRow[] = [];
  for (const raw of candidates ?? []) {
    const tier = classifyCandidate(raw, config, watchPct);
    if (!tier) continue;
    rows.push({
      code: raw.code,
      name: raw.name,
      market: raw.market,
      current_price: raw.current_price,
      rs: raw.rs ?? null,
      status: String(raw.status ?? ""),
      pivot_price: num(raw.pivot_price),
      pct_to_pivot: num(raw.pct_to_pivot),
      tier,
      raw,
    });
  }
  sortRows(rows);
  return {
    rows,
    counts: {
      breakout: rows.filter((r) => r.tier === "breakout").length,
      actionable: rows.filter((r) => r.tier === "actionable").length,
      watch: rows.filter((r) => r.tier === "watch").length,
    },
  };
}

// ── 포맷터 ──────────────────────────────────────────────
export function fmtPct(n: number | null, digits = 1): string {
  if (n === null || n === undefined) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

export function fmtPrice(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString();
}

export function fmtCell(value: unknown, kind: PatternColumn["kind"]): string {
  const n = num(value);
  switch (kind) {
    case "price":
      return fmtPrice(n);
    case "pct":
      return fmtPct(n, 1);                       // 부호 있는 증감(+상승/−하락)
    case "depth":
    case "tight":
      return n === null ? "—" : `${n.toFixed(1)}%`;  // 크기(깊이·타이트): + 부호 없이 표기
    case "ratio":
      return n === null ? "—" : n.toFixed(2);
    case "int":
      return n === null ? "—" : String(Math.round(n));
    case "days":
      return n === null ? "—" : `${Math.round(n)}일`;
  }
}

// ── 패턴 레지스트리 ─────────────────────────────────────
const VCP_COLUMNS: PatternColumn[] = [
  { key: "num_contractions", label: "수축", kind: "int" },
  { key: "base_depth_pct", label: "베이스깊이", kind: "depth" },
  { key: "coil_len", label: "코일길이", kind: "int" },
  { key: "coil_dry_mean", label: "코일마름", kind: "ratio" },
  { key: "tightness_pct", label: "타이트", kind: "tight" },
];

const POWERPLAY_COLUMNS: PatternColumn[] = [
  { key: "flagpole_gain_pct", label: "깃대상승", kind: "pct" },
  { key: "flagpole_days", label: "깃대일수", kind: "days" },
  { key: "flag_depth_pct", label: "깃발깊이", kind: "depth" },
  { key: "tightness_pct", label: "타이트", kind: "tight" },
];

// 파워 플레이 구조 형성: 실제 깃발(눌림 폭 > 0)이 있어야 예의주시 후보.
// 신고가 부근에서 눌림 0%(flag_depth=0 → 피벗=현재가)인 퇴화 케이스를 노이즈로 제외.
const powerPlayStructureOk = (raw: RawCandidate): boolean => {
  const len = num(raw.flag_length_days);
  const depth = num(raw.flag_depth_pct);
  return len !== null && len > 0 && depth !== null && depth > 0;
};

export const PATTERNS = {
  vcp: {
    id: "vcp",
    label: "VCP (변동성 수축)",
    file: "sepa-vcp-candidates.json",
    detectField: "vcp_detected",
    structureOk: (raw) => num(raw.num_contractions) !== null && (num(raw.num_contractions) as number) >= 2,
    columns: VCP_COLUMNS,
  },
  powerplayTrend: {
    id: "powerplay-trend",
    label: "파워 플레이 — 트렌드 통과 종목 중",
    file: "sepa-power-play-candidates.json",
    detectField: "pattern_detected",
    structureOk: powerPlayStructureOk,
    columns: POWERPLAY_COLUMNS,
  },
  powerplayAll: {
    id: "powerplay-all",
    label: "파워 플레이 — 전체 종목 중 (RS 80↑)",
    file: "sepa-power-play-all-candidates.json",
    detectField: "pattern_detected",
    structureOk: powerPlayStructureOk,
    columns: POWERPLAY_COLUMNS,
  },
  threeC: {
    id: "3c",
    label: "3C (Cup Completion Cheat)",
    file: "sepa-3c-candidates.json",
    detectField: "pattern_detected",
    structureOk: (raw) => num(raw.pivot_price) !== null,
    columns: [{ key: "tightness_pct", label: "타이트", kind: "tight" }],
  },
} satisfies Record<string, PatternConfig>;
