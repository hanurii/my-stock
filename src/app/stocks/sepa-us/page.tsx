import fs from "fs/promises";
import path from "path";
import Link from "next/link";
import {
  PATTERNS,
  sortRows,
  fmtCell,
  fmtPct,
  type ClassifiedRow,
  type PatternColumn,
  type RawCandidate,
  type Tier,
} from "../sepa/sepaPatterns";

/**
 * 미국 전용 SEPA 후보 페이지.
 *
 * 읽는 자료는 «검출기 세 파일»뿐이다. 1단계 산출(sepa-us-trend-candidates.json, 8.8MB)은
 * 읽지 않는다 — 머리에 쓸 수(평가·통과·입력 수)가 검출기 파일 머리에 이미 다 들어 있다.
 *
 * 한국 `sepa/sepaPatterns.ts` 에서 «순수 로직만» 가져다 쓴다(정렬·칸 정의·칸 서식).
 * 한국 파일은 고치지 않는다. 표 그리는 컴포넌트(SepaPatternTable)는 가져다 쓰지 않는다 —
 * 원화 정수 표기·KOSPI/KOSDAQ 배지·한국 전용 배지 props 가 미국에 안 맞고, 맞추려면 그쪽을
 * 고쳐야 하기 때문이다.
 *
 * ⚠️ 「피벗대비」는 «자가 둘»이다.
 *    자료 축: pct_to_pivot = (피벗 − 현재가)/피벗  → 양수 = 피벗 «아래»
 *    표시 축: (현재가 − 피벗)/피벗 = −자료축        → 음수 = 피벗 «아래»  (한국 규약)
 *    뒤집는 곳은 `toDisplayPct()` «한 군데»뿐이다. 정렬·색은 |값| 이라 축과 무관하다.
 */

const DETECTORS = [
  {
    file: "sepa-us-vcp-candidates.json",
    label: "VCP (변동성 수축 패턴)",
    columns: PATTERNS.vcp.columns as readonly PatternColumn[],
  },
  {
    file: "sepa-us-power-play-candidates.json",
    label: "파워 플레이 (하이 타이트 플래그)",
    columns: PATTERNS.powerplayTrend.columns as readonly PatternColumn[],
  },
  {
    file: "sepa-us-3c-candidates.json",
    label: "3C (컵 완성 치트)",
    columns: PATTERNS.threeC.columns as readonly PatternColumn[],
  },
] as const;

// 한국 SepaPatternTable 의 TIER_META 와 같은 낱말·같은 색.
const TIER_META: Record<Tier, { label: string; color: string; bg: string; dot: string }> = {
  breakout: { label: "돌파", color: "#ffb4ab", bg: "rgba(255,180,171,0.15)", dot: "🔴" },
  actionable: { label: "진입임박", color: "#34d399", bg: "rgba(52,211,153,0.15)", dot: "🟢" },
  watch: { label: "예의주시", color: "#e9c176", bg: "rgba(233,193,118,0.15)", dot: "🟡" },
};

// 검출된 종목의 status → 티어. 검출 안 된 종목은 이 페이지에 올리지 않는다.
// (한국 classify 는 피벗 12% 안의 «미검출» 종목도 예의주시로 올리지만, 그 문턱은 한국 값이라
//  미국에서 잰 적이 없다. 그래서 「검출된 것」으로 한정한다 — 그래야 검출 N 과 행 수가 맞는다.)
const STATUS_TO_TIER: Record<string, Tier> = {
  breakout: "breakout",
  actionable: "actionable",
  forming: "watch",
};

interface UsDetectorFile {
  generated_at: string;
  asof: string;
  price_source: string;
  price_asof: string;
  stage1_evaluated_n: number;
  stage1_all_pass_n: number;
  input_n: number;
  no_series_n: number;
  stale_bar_n: number;
  eval_error_n: number;
  detected_key: string;
  detected_count: number;
  entry_definition: string;
  entry_ready_count: number;
  already_breakout_count: number;
  already_breakout_note: string;
  module_entry_ready_count: number;
  module_entry_ready_note: string;
  candidates: RawCandidate[];
}

// 머리에 하나라도 없으면 「읽었다」고 할 수 없다. 조용히 0 으로 떨어지는 것을 막는다.
const REQUIRED_KEYS: (keyof UsDetectorFile)[] = [
  "generated_at", "asof", "price_source", "price_asof",
  "stage1_evaluated_n", "stage1_all_pass_n", "input_n",
  "no_series_n", "stale_bar_n", "eval_error_n",
  "detected_key", "detected_count",
  "entry_definition", "entry_ready_count",
  "already_breakout_count", "already_breakout_note",
  "module_entry_ready_count", "module_entry_ready_note",
];

interface Loaded {
  file: string;
  label: string;
  columns: readonly PatternColumn[];
  data: UsDetectorFile | null;
  error: string | null;
}

async function readDetector(
  file: string,
  label: string,
  columns: readonly PatternColumn[],
): Promise<Loaded> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", file);
    const parsed = JSON.parse(await fs.readFile(filePath, "utf-8")) as UsDetectorFile;
    const missing = REQUIRED_KEYS.filter((k) => parsed[k] === undefined || parsed[k] === null);
    if (missing.length > 0) throw new Error(`머리 항목이 없습니다: ${missing.join(", ")}`);
    if (!Array.isArray(parsed.candidates)) throw new Error("candidates 배열이 없습니다");
    return { file, label, columns, data: parsed, error: null };
  } catch (e) {
    return { file, label, columns, data: null, error: e instanceof Error ? e.message : String(e) };
  }
}

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

// 🔴 부호를 뒤집는 «유일한» 자리. 자료 축 → 표시 축(한국 규약: 음수 = 피벗 아래).
function toDisplayPct(rawPctToPivot: number | null): number | null {
  return rawPctToPivot === null ? null : -rawPctToPivot;
}

function fmtUsdPrice(n: number | null): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "—";
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtEok(n: number | null): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "—";
  return n.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
}

function rsColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= 90) return "#10b981";
  if (n >= 80) return "#34d399";
  if (n >= 70) return "#e9c176";
  return "#ffb4ab";
}

// 0 에 가까울수록 진입 적기. |값| 만 쓰므로 «자료 축이든 표시 축이든 같은 답»이다 — 인자는 자료 축.
function pivotColor(rawPctToPivot: number | null): string {
  if (rawPctToPivot === null || rawPctToPivot === undefined) return "var(--on-surface-variant)";
  const a = Math.abs(rawPctToPivot);
  if (a <= 3) return "#10b981";
  if (a <= 8) return "#34d399";
  if (a <= 12) return "#e9c176";
  return "#a8b5d0";
}

interface TierCounts {
  breakout: number;
  actionable: number;
  watch: number;
  failed: number;
}

function buildUsRows(d: UsDetectorFile): { rows: ClassifiedRow[]; counts: TierCounts } {
  const rows: ClassifiedRow[] = [];
  let failed = 0;
  for (const raw of d.candidates) {
    if (raw[d.detected_key] !== true) continue; // 검출 안 된 종목은 안 올린다
    const status = String(raw.status ?? "");
    if (status === "failed") {
      failed += 1; // 한국과 같이 표에는 안 올리고 수만 적는다
      continue;
    }
    const tier = STATUS_TO_TIER[status];
    if (!tier) continue;
    rows.push({
      code: raw.code,
      name: raw.name,
      market: raw.market,
      current_price: raw.current_price,
      rs: raw.rs ?? null,
      status,
      pivot_price: num(raw.pivot_price),
      pct_to_pivot: num(raw.pct_to_pivot), // 자료 축 그대로 보관 — 뒤집기는 그릴 때 한 번
      tier,
      raw,
    });
  }
  sortRows(rows); // 한국과 같은 정렬: 돌파 → 진입임박 → 예의주시 → |피벗거리| → RS
  return {
    rows,
    counts: {
      breakout: rows.filter((r) => r.tier === "breakout").length,
      actionable: rows.filter((r) => r.tier === "actionable").length,
      watch: rows.filter((r) => r.tier === "watch").length,
      failed,
    },
  };
}

function CandidateTable({ rows, columns }: { rows: ClassifiedRow[]; columns: readonly PatternColumn[] }) {
  if (rows.length === 0) {
    return <p className="text-center text-on-surface-variant/60 py-6 text-sm">현재 해당 종목 없음.</p>;
  }
  return (
    <div className="overflow-x-auto bg-surface-container-low rounded-xl ghost-border">
      <table className="w-full text-xs">
        <thead className="bg-surface-container/40">
          <tr>
            <th className="px-2 py-2 text-left text-[11px] font-medium text-on-surface-variant/80 sticky left-0 bg-surface-container/40">
              종목
            </th>
            <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">시장</th>
            <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">상태</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">RS</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">현재가</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">피벗</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">피벗대비</th>
            {columns.map((c) => (
              <th key={c.key} className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">
                {c.label}
              </th>
            ))}
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">
              거래대금
              <span className="block font-normal text-on-surface-variant/50">억원 상당</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const meta = TIER_META[r.tier];
            return (
              <tr
                key={r.code}
                className="border-t border-outline-variant/10 hover:bg-surface-container-high/50 transition-colors"
              >
                <td className="px-2 py-2 sticky left-0 bg-surface-container-low">
                  <div className="flex flex-col">
                    <span className="text-on-surface font-medium leading-tight">{r.name}</span>
                    <span className="text-[10px] text-on-surface-variant/50 font-mono">{r.code}</span>
                  </div>
                </td>
                <td className="px-2 py-2 text-center">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-500/15 text-slate-300">
                    {r.market}
                  </span>
                </td>
                <td className="px-2 py-2 text-center">
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded font-medium whitespace-nowrap"
                    style={{ backgroundColor: meta.bg, color: meta.color }}
                  >
                    {meta.dot} {meta.label}
                  </span>
                </td>
                <td className="px-2 py-2 text-right font-bold" style={{ color: rsColor(r.rs) }}>
                  {r.rs ?? "—"}
                </td>
                <td className="px-2 py-2 text-right text-on-surface-variant">{fmtUsdPrice(r.current_price)}</td>
                <td className="px-2 py-2 text-right text-on-surface-variant">{fmtUsdPrice(r.pivot_price)}</td>
                <td className="px-2 py-2 text-right" style={{ color: pivotColor(r.pct_to_pivot) }}>
                  {/* 자료 축 → 표시 축 뒤집기는 toDisplayPct() 한 군데. 음수 = 피벗 아래. */}
                  {fmtPct(toDisplayPct(r.pct_to_pivot), 1)}
                </td>
                {columns.map((c) => (
                  <td key={c.key} className="px-2 py-2 text-right text-on-surface-variant">
                    {fmtCell(r.raw[c.key], c.kind)}
                  </td>
                ))}
                <td className="px-2 py-2 text-right text-on-surface-variant">
                  {fmtEok(num(r.raw.turnover_eok))}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CountMismatch({ what, shown, header }: { what: string; shown: number; header: number }) {
  if (shown === header) return null;
  return (
    <p
      className="text-[11px] rounded px-2 py-1 mb-1"
      style={{ backgroundColor: "rgba(255,180,171,0.18)", color: "#ffb4ab" }}
    >
      같은 것을 가리키는 수가 둘입니다 — {what}: 표에서 센 {shown}건 vs 파일 머리 {header}건. 파일을 다시 만들기
      전에는 아래 표를 믿지 마십시오.
    </p>
  );
}

function DetectorSection({ loaded }: { loaded: Loaded }) {
  const d = loaded.data;
  if (!d) return null;
  const { rows, counts } = buildUsRows(d);
  const shownTotal = counts.breakout + counts.actionable + counts.watch;
  const notDetected = d.input_n - d.detected_count;

  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">pattern</span>
        {loaded.label}
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">
          🔴 {counts.breakout} · 🟢 {counts.actionable} · 🟡 {counts.watch}
        </span>
      </h3>

      <div className="bg-surface-container-low rounded-xl ghost-border p-4 mb-3 space-y-1.5">
        <p className="text-[11px] leading-relaxed" style={{ color: "#34d399" }}>
          <strong>주문을 거는 대상은 🟢 진입임박 {d.entry_ready_count}종목뿐입니다.</strong>{" "}
          <span className="text-on-surface-variant/80">🔴 돌파 {d.already_breakout_count}종목은 이미 피벗 위입니다.</span>
        </p>
        <p className="text-[11px] text-on-surface-variant/80 leading-relaxed">
          <strong className="text-on-surface">🟢 진입임박(= 진입)</strong> — {d.entry_definition}
        </p>
        <p className="text-[11px] text-on-surface-variant/80 leading-relaxed">
          <strong className="text-on-surface">🔴 돌파(= 이미 돌파)</strong> — {d.already_breakout_note}
        </p>
        <p className="text-[11px] text-on-surface-variant/60 leading-relaxed pt-1.5 border-t border-outline-variant/10">
          <strong>모듈 자</strong> {d.module_entry_ready_count} — {d.module_entry_ready_note}
        </p>
      </div>

      <CountMismatch what={`${loaded.label} 진입임박`} shown={counts.actionable} header={d.entry_ready_count} />
      <CountMismatch what={`${loaded.label} 돌파`} shown={counts.breakout} header={d.already_breakout_count} />
      <CountMismatch what={`${loaded.label} 검출`} shown={shownTotal + counts.failed} header={d.detected_count} />

      <CandidateTable rows={rows} columns={loaded.columns} />

      <p className="text-[11px] text-on-surface-variant/55 mt-2 leading-relaxed">
        검출 {d.detected_count} = 🔴 돌파 {counts.breakout} + 🟢 진입임박 {counts.actionable} + 🟡 예의주시{" "}
        {counts.watch} + 실패 {counts.failed}(한국과 같이 표에 안 올림) · 이 패턴이 검출되지 않은 {notDetected}종목도
        표에 없습니다 (2단계 입력 {d.input_n} = 검출 {d.detected_count} + 미검출 {notDetected}).
      </p>
    </section>
  );
}

function LoadFailure({ loads }: { loads: Loaded[] }) {
  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold" style={{ color: "#ffb4ab" }}>
          미국 SEPA 후보 — 자료를 읽지 못했습니다
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          검출기 파일 셋 중 하나라도 못 읽으면 이 페이지는 아무 수도 보이지 않습니다. 반쪽짜리 화면이 「오늘은 후보가
          없다」로 읽히는 것을 막기 위해서입니다. <code className="text-xs">/sepa-us</code> 를 다시 돌린 뒤
          새로고침하십시오.
        </p>
      </header>
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">rule</span>
          검출기 파일 셋
        </h3>
        <ul className="space-y-1.5">
          {loads.map((l) => (
            <li key={l.file} className="text-xs">
              <code className="text-[11px] text-on-surface">public/data/{l.file}</code>
              <span className="block mt-0.5" style={{ color: l.error ? "#ffb4ab" : "#34d399" }}>
                {l.error ? `읽기 실패 — ${l.error}` : "정상"}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default async function SepaUsPage() {
  const loads = await Promise.all(DETECTORS.map((d) => readDetector(d.file, d.label, d.columns)));
  if (loads.some((l) => l.error !== null)) return <LoadFailure loads={loads} />;

  const files = loads.map((l) => l.data as UsDetectorFile);
  const head = files[0];

  const asofs = Array.from(new Set(files.map((f) => f.asof)));
  const priceSources = Array.from(new Set(files.map((f) => f.price_source)));
  const priceAsofs = Array.from(new Set(files.map((f) => f.price_asof)));
  const evaluated = Array.from(new Set(files.map((f) => f.stage1_evaluated_n)));
  const allPass = Array.from(new Set(files.map((f) => f.stage1_all_pass_n)));
  const inputs = Array.from(new Set(files.map((f) => f.input_n)));

  const disagreements: string[] = [];
  if (asofs.length > 1) disagreements.push(`기준일이 서로 다릅니다 — ${asofs.join(" · ")}`);
  if (priceSources.length > 1) disagreements.push(`읽은 시세 파일이 서로 다릅니다 — ${priceSources.join(" · ")}`);
  if (priceAsofs.length > 1) disagreements.push(`시세 기준일이 서로 다릅니다 — ${priceAsofs.join(" · ")}`);
  if (evaluated.length > 1) disagreements.push(`평가 수가 서로 다릅니다 — ${evaluated.join(" · ")}`);
  if (allPass.length > 1) disagreements.push(`8관문 통과 수가 서로 다릅니다 — ${allPass.join(" · ")}`);
  if (inputs.length > 1) disagreements.push(`2단계 입력 수가 서로 다릅니다 — ${inputs.join(" · ")}`);

  const tailAttached = head.price_source.includes("tail");
  const totalEntry = files.reduce((s, f) => s + f.entry_ready_count, 0);
  const totalBreakout = files.reduce((s, f) => s + f.already_breakout_count, 0);

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">미국 SEPA 셋업</h2>
        <p className="text-base text-on-surface-variant mt-2">
          미너비니 SEPA — 트렌드 템플릿 1단계를 통과한 미국 종목에 대해 VCP·파워 플레이·3C 의 돌파·진입임박·예의주시를
          한눈에.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          기준일: {head.asof} · 2단계 입력 {head.input_n.toLocaleString()}종목 / 평가{" "}
          {head.stage1_evaluated_n.toLocaleString()} · 🟢 진입 {totalEntry} · 🔴 이미 돌파 {totalBreakout}
        </p>
        <p className="text-xs mt-2">
          <Link
            href="/stocks/sepa-us/method"
            className="text-primary hover:underline inline-flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm">menu_book</span>
            우리 방법 — 무엇을 · 언제 · 얼마나 사고 언제 파는가
          </Link>
        </p>
      </header>

      {/* 자료 상태 — 이 수를 믿어도 되나 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 space-y-3">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">fact_check</span>
          자료 상태 — 이 수를 믿어도 되나
        </h3>

        <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
          <div>
            <p className="text-[11px] text-on-surface-variant/60">기준일 (asof)</p>
            <p className="text-2xl font-serif font-bold text-on-surface leading-tight">{head.asof}</p>
          </div>
          <div>
            <p className="text-[11px] text-on-surface-variant/60">읽은 시세 파일 (price_source)</p>
            <p
              className="text-2xl font-serif font-bold leading-tight"
              style={{ color: tailAttached ? "#34d399" : "#e9c176" }}
            >
              {head.price_source}
            </p>
            <p className="text-[11px] text-on-surface-variant/70">
              {tailAttached
                ? "꼬리(최근 일봉)가 붙은 시세입니다."
                : "뼈대만 읽었습니다 — 꼬리(최근 일봉)가 아직 안 붙었습니다."}
            </p>
          </div>
          <div>
            <p className="text-[11px] text-on-surface-variant/60">시세 기준일 (price_asof)</p>
            <p className="text-lg font-serif font-bold text-on-surface leading-tight">{head.price_asof}</p>
          </div>
          <div>
            <p className="text-[11px] text-on-surface-variant/60">산출 시각 (generated_at)</p>
            <p className="text-lg font-serif font-bold text-on-surface leading-tight">{head.generated_at}</p>
          </div>
        </div>

        {disagreements.length > 0 && (
          <div className="rounded-lg p-3" style={{ backgroundColor: "rgba(255,180,171,0.18)" }}>
            <p className="text-sm font-bold" style={{ color: "#ffb4ab" }}>
              세 파일의 머리가 어긋납니다 — 한쪽만 갱신된 상태입니다.
            </p>
            <ul className="text-xs mt-1 space-y-0.5" style={{ color: "#ffb4ab" }}>
              {disagreements.map((m) => (
                <li key={m}>· {m}</li>
              ))}
            </ul>
            <p className="text-[11px] text-on-surface-variant/70 mt-1">
              위에 크게 적은 수는 {DETECTORS[0].label} 파일 것입니다. 파일별 값은 각 파일을 직접 보십시오.
            </p>
          </div>
        )}

        <div className="border-t border-outline-variant/10 pt-3">
          <p className="text-[11px] font-bold text-on-surface-variant/60 mb-1.5">
            분모 사슬 <span className="font-normal text-on-surface-variant/50">· 모든 수는 산출 파일에서 읽습니다</span>
          </p>
          <p className="text-base text-on-surface">
            평가 {head.stage1_evaluated_n.toLocaleString()}
            <span className="text-on-surface-variant/50 mx-2">→</span>
            8관문 통과 {head.stage1_all_pass_n.toLocaleString()}
            <span className="text-on-surface-variant/50 mx-2">→</span>
            2단계 입력 {head.input_n.toLocaleString()}
          </p>
          <p className="text-[11px] text-on-surface-variant/70 mt-1 leading-relaxed">
            2단계에서 빠진 것 — 시세 없음 {head.no_series_n} · 마지막 봉이 낡음 {head.stale_bar_n} · 평가 오류{" "}
            {head.eval_error_n}
          </p>
        </div>
      </section>

      {/* 검출기 셋 */}
      {loads.map((l) => (
        <DetectorSection key={l.file} loaded={l} />
      ))}

      {/* 용어·지표 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 text-xs space-y-4">
        <h3 className="text-sm font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">help_outline</span>
          상태·지표
        </h3>

        <div>
          <p className="text-[11px] font-bold text-on-surface-variant/60 mb-1.5">
            🚦 상태 배지{" "}
            <span className="font-normal text-on-surface-variant/50">· 승격 순서: 예의주시 → 진입임박 → 돌파</span>
          </p>
          <ul className="space-y-1 text-on-surface-variant">
            <li>
              <strong style={{ color: "#34d399" }}>🟢 진입임박</strong> —{" "}
              <strong className="text-on-surface">이것만 실제 주문 대상입니다.</strong> 패턴 확정 + 피벗 코앞. 장
              시작 전 피벗 가격에 자동매수를 예약합니다. 27.4년 백테스트가 「진입」으로 센 것도 이것뿐입니다.
            </li>
            <li>
              <strong style={{ color: "#ffb4ab" }}>🔴 돌파</strong> — 이미 피벗 위입니다. 예약이 안 걸리거나 추격이
              되므로 <strong className="text-on-surface">주문 대상이 아닙니다.</strong> 정보로만 둡니다.
            </li>
            <li>
              <strong style={{ color: "#e9c176" }}>🟡 예의주시</strong> — 패턴이 형성 중(forming). 관심종목이지 매수는
              아닙니다.
            </li>
            <li className="text-on-surface-variant/60">
              실패(failed)와 이 패턴이 검출되지 않은 종목은 표에 올리지 않고, 몇 종목인지만 각 패턴 아래에 적습니다.
              「추이」 칸은 <code className="text-[11px]">sepa-tier-history.json</code> 에서 오는데 미국에는 그 파일이
              없어 칸 자체를 만들지 않았습니다.
            </li>
          </ul>
        </div>

        <div className="border-t border-outline-variant/10 pt-3">
          <p className="text-[11px] font-bold text-on-surface-variant/60 mb-1.5">📊 주요 지표</p>
          <dl className="space-y-1.5 text-on-surface-variant">
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">피벗</dt>
              <dd className="flex-1">최소저항선(돌파 기준가). 장 시작 전 이 가격에 예약을 겁니다.</dd>
            </div>
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">피벗대비</dt>
              <dd className="flex-1">
                (현재가−피벗)/피벗 · <strong className="text-on-surface">음수=아래, 양수=위</strong> ·{" "}
                <strong className="text-on-surface">0에 가까울수록 진입 적기</strong>.
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">RS</dt>
              <dd className="flex-1">상대강도 순위(1~99). 1단계 합격선은 80입니다.</dd>
            </div>
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">코일</dt>
              <dd className="flex-1">
                돌파 직전 좁고 조용하게 응축되는 최종 수축 구간.
                <span className="block text-on-surface-variant/80 mt-0.5">
                  ├ <strong className="text-on-surface/90">코일길이</strong> : 그 구간 일수 — 짧을수록 좋음(통상 3~5일)
                </span>
                <span className="block text-on-surface-variant/80">
                  └ <strong className="text-on-surface/90">코일마름</strong> : 코일 거래량 ÷ 50일 평균 — 낮을수록 좋음
                </span>
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">타이트</dt>
              <dd className="flex-1">최근 ~10일 일중 변동폭((고−저)/종가) 평균(%) — 작을수록 변동성 압축.</dd>
            </div>
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">베이스깊이</dt>
              <dd className="flex-1">고점 대비 최대 조정폭(%).</dd>
            </div>
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">깃대·깃발</dt>
              <dd className="flex-1">
                깃대상승·깃대일수 = 폭등 구간의 상승폭과 일수 · 깃발깊이 = 그 뒤 횡보의 조정폭(%).
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">거래대금</dt>
              <dd className="flex-1">
                하루 거래대금의 50일 평균을 <strong className="text-on-surface">원화로 환산한 「억원 상당」</strong>
                입니다 — 달러가 아닙니다.
              </dd>
            </div>
          </dl>
        </div>

        <p className="text-on-surface-variant/55 pt-2 border-t border-outline-variant/15">
          칸 이름·자릿수·단위는 한국 페이지 정의(<code className="text-[11px]">sepa/sepaPatterns.ts</code>)를 그대로
          가져다 씁니다. 검출기 코드와 값도 한국과 같은 모듈입니다. 읽는 자료는 검출기 파일 셋뿐이며 페이지는 읽기
          전용입니다.
        </p>
      </section>
    </div>
  );
}
