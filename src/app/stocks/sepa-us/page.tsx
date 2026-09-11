import fs from "fs/promises";
import path from "path";

/**
 * 미국 전용 SEPA 후보 페이지.
 *
 * 읽는 자료는 «검출기 세 파일»뿐이다. 1단계 산출(sepa-us-trend-candidates.json, 8.8MB)은
 * 읽지 않는다 — 머리에 쓸 수(평가·통과·입력 수)가 검출기 파일 머리에 이미 다 들어 있고,
 * 8.8MB 에는 평가한 3천여 건이 전부 들어 있어 매 요청마다 파싱하면 낭비다.
 *
 * 한국 페이지(src/app/stocks/sepa/**)의 구조를 본떴으나 컴포넌트를 빌려 쓰지는 않는다.
 * 이유 둘: (1) 한국 표는 원화 정수 표기·KOSPI/KOSDAQ 배지라 미국 값에 맞지 않고,
 * (2) 한국 용어표의 「피벗대비 = (현재가−피벗)/피벗 · 음수=아래」는 산출 코드
 * (vcp.py:304 `(pivot - last_close) / pivot`)와 부호가 반대다. 빌려 쓰면 그 오표기를
 * 미국 쪽에 그대로 옮기게 된다. 한국 쪽은 이 작업에서 고치지 않는다.
 */

const DETECTORS = [
  { file: "sepa-us-vcp-candidates.json", label: "VCP (변동성 수축 패턴)" },
  { file: "sepa-us-power-play-candidates.json", label: "파워 플레이 (하이 타이트 플래그)" },
  { file: "sepa-us-3c-candidates.json", label: "3C (컵 완성 치트)" },
] as const;

interface UsCandidate {
  code: string;
  name: string;
  market: string;
  current_price: number | null;
  pivot_price: number | null;
  pct_to_pivot: number | null;
  rs: number | null;
  turnover_eok: number | null;
  status: string;
  [key: string]: unknown;
}

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
  candidates: UsCandidate[];
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
  data: UsDetectorFile | null;
  error: string | null;
}

async function readDetector(file: string, label: string): Promise<Loaded> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", file);
    const parsed = JSON.parse(await fs.readFile(filePath, "utf-8")) as UsDetectorFile;
    const missing = REQUIRED_KEYS.filter((k) => parsed[k] === undefined || parsed[k] === null);
    if (missing.length > 0) throw new Error(`머리 항목이 없습니다: ${missing.join(", ")}`);
    if (!Array.isArray(parsed.candidates)) throw new Error("candidates 배열이 없습니다");
    return { file, label, data: parsed, error: null };
  } catch (e) {
    return { file, label, data: null, error: e instanceof Error ? e.message : String(e) };
  }
}

function fmtPrice(n: number | null): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "—";
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// pct_to_pivot = (피벗 − 현재가) / 피벗 × 100 — 양수면 피벗 «아래»(그만큼 올라야 닿는다).
function fmtToPivot(n: number | null): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "—";
  if (n >= 0) return `${n.toFixed(2)}% 아래`;
  return `${Math.abs(n).toFixed(2)}% 위`;
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

function isDetected(c: UsCandidate, key: string): boolean {
  return c[key] === true;
}

function sortByPivot(rows: UsCandidate[]): UsCandidate[] {
  return [...rows].sort((a, b) => {
    const ap = a.pct_to_pivot == null ? Infinity : Math.abs(a.pct_to_pivot);
    const bp = b.pct_to_pivot == null ? Infinity : Math.abs(b.pct_to_pivot);
    if (ap !== bp) return ap - bp;
    return (b.rs ?? -1) - (a.rs ?? -1);
  });
}

function CandidateTable({ rows }: { rows: UsCandidate[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-on-surface-variant/60 py-3">해당 종목 없음.</p>;
  }
  return (
    <div className="overflow-x-auto bg-surface-container-low rounded-xl ghost-border">
      <table className="w-full text-xs">
        <thead className="bg-surface-container/40">
          <tr>
            <th className="px-2 py-2 text-left text-[11px] font-medium text-on-surface-variant/80">종목</th>
            <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">시장</th>
            <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">상태</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">현재가</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">피벗</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">피벗까지</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">RS</th>
            <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">
              50일 거래대금
              <span className="block font-normal text-on-surface-variant/50">억원 상당</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.code} className="border-t border-outline-variant/10 hover:bg-surface-container-high/50 transition-colors">
              <td className="px-2 py-2">
                <span className="text-on-surface font-medium">{r.code}</span>
                <span className="block text-[10px] text-on-surface-variant/60">{r.name}</span>
              </td>
              <td className="px-2 py-2 text-center">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-500/15 text-slate-300">{r.market}</span>
              </td>
              <td className="px-2 py-2 text-center text-on-surface-variant">{r.status}</td>
              <td className="px-2 py-2 text-right text-on-surface-variant">{fmtPrice(r.current_price)}</td>
              <td className="px-2 py-2 text-right text-on-surface-variant">{fmtPrice(r.pivot_price)}</td>
              <td className="px-2 py-2 text-right text-on-surface-variant">{fmtToPivot(r.pct_to_pivot)}</td>
              <td className="px-2 py-2 text-right font-bold" style={{ color: rsColor(r.rs) }}>{r.rs ?? "—"}</td>
              <td className="px-2 py-2 text-right text-on-surface-variant">{fmtEok(r.turnover_eok)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CountMismatch({ what, shown, header }: { what: string; shown: number; header: number }) {
  if (shown === header) return null;
  return (
    <p
      className="text-[11px] rounded px-2 py-1 my-1"
      style={{ backgroundColor: "rgba(255,180,171,0.18)", color: "#ffb4ab" }}
    >
      같은 것을 가리키는 수가 둘입니다 — {what}: 표에 고른 {shown}건 vs 파일 머리 {header}건.
      파일을 다시 만들기 전에는 아래 표를 믿지 마십시오.
    </p>
  );
}

function DetectorSection({ loaded }: { loaded: Loaded }) {
  const d = loaded.data;
  if (!d) return null;
  const entry = sortByPivot(
    d.candidates.filter(
      (c) => isDetected(c, d.detected_key) && c.status === "actionable" && c.pivot_price != null,
    ),
  );
  const breakout = sortByPivot(
    d.candidates.filter((c) => isDetected(c, d.detected_key) && c.status === "breakout"),
  );
  const rest = d.detected_count - entry.length - breakout.length;
  const notDetected = d.input_n - d.detected_count;

  return (
    <section className="space-y-3">
      <h3 className="text-lg font-serif font-bold text-on-surface">
        {loaded.label}
        <span className="text-xs font-normal text-on-surface-variant/60 ml-2">
          검출 {d.detected_count} · 진입 {d.entry_ready_count} · 이미 돌파 {d.already_breakout_count}
        </span>
      </h3>

      <div className="bg-surface-container-low rounded-xl ghost-border p-3 space-y-1">
        <p className="text-[11px] text-on-surface-variant/80 leading-relaxed">
          <strong className="text-on-surface">진입 정의</strong> — {d.entry_definition}
        </p>
        <p className="text-[11px] text-on-surface-variant/80 leading-relaxed">
          <strong className="text-on-surface">이미 돌파</strong> — {d.already_breakout_note}
        </p>
        <p className="text-[11px] text-on-surface-variant/60 leading-relaxed">
          <strong>모듈 자</strong>(참고, 주문을 거는 수가 아님) {d.module_entry_ready_count} — {d.module_entry_ready_note}
        </p>
      </div>

      <div>
        <p className="text-sm font-medium text-on-surface mb-1">
          진입 — 장 시작 전 피벗 예약을 거는 대상 · {d.entry_ready_count}건
        </p>
        <CountMismatch what={`${loaded.label} 진입`} shown={entry.length} header={d.entry_ready_count} />
        <CandidateTable rows={entry} />
      </div>

      <div>
        <p className="text-sm font-medium text-on-surface mb-1">
          이미 돌파 — 진입이 아니다(정보) · {d.already_breakout_count}건
        </p>
        <CountMismatch
          what={`${loaded.label} 이미 돌파`}
          shown={breakout.length}
          header={d.already_breakout_count}
        />
        <CandidateTable rows={breakout} />
      </div>

      <p className="text-[11px] text-on-surface-variant/55">
        표에 없는 것: 검출됐으나 진입도 이미 돌파도 아닌 {rest}건 · 2단계 입력 중 이 패턴이 검출되지 않은{" "}
        {notDetected}건 (2단계 입력 {d.input_n}건 = 검출 {d.detected_count} + 미검출 {notDetected}).
      </p>
    </section>
  );
}

function LoadFailure({ loads }: { loads: Loaded[] }) {
  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold" style={{ color: "#ffb4ab" }}>
          미국 SEPA 후보 — 자료를 읽지 못했습니다
        </h2>
        <p className="text-sm text-on-surface-variant mt-2">
          검출기 파일 셋 중 하나라도 못 읽으면 이 페이지는 아무 수도 보이지 않습니다. 반쪽짜리 화면이
          「오늘은 후보가 없다」로 읽히는 것을 막기 위해서입니다.
          <code className="text-xs ml-1">/sepa-us</code> 를 다시 돌린 뒤 새로고침하십시오.
        </p>
      </header>
      <ul className="space-y-2">
        {loads.map((l) => (
          <li
            key={l.file}
            className="rounded-xl p-3 text-sm ghost-border"
            style={{ backgroundColor: l.error ? "rgba(255,180,171,0.12)" : "rgba(255,255,255,0.03)" }}
          >
            <code className="text-xs text-on-surface">public/data/{l.file}</code>
            <span className="block mt-1" style={{ color: l.error ? "#ffb4ab" : "#34d399" }}>
              {l.error ? `읽기 실패 — ${l.error}` : "정상"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default async function SepaUsPage() {
  const loads = await Promise.all(DETECTORS.map((d) => readDetector(d.file, d.label)));
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

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">미국 SEPA 후보</h2>
        <p className="text-base text-on-surface-variant mt-2">
          미너비니 SEPA — 1단계 트렌드 템플릿을 통과한 미국 종목에서 VCP · 파워 플레이 · 3C 를 찾은 결과.
          장 시작 전 피벗 예약을 걸 대상만 「진입」으로 따로 뽑았습니다.
        </p>
      </header>

      {/* ① 이 수를 믿어도 되나 — 맨 위 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 space-y-3">
        <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
          <div>
            <p className="text-[11px] text-on-surface-variant/60">기준일 (asof)</p>
            <p className="text-2xl font-bold text-on-surface leading-tight">{head.asof}</p>
          </div>
          <div>
            <p className="text-[11px] text-on-surface-variant/60">읽은 시세 파일 (price_source)</p>
            <p className="text-2xl font-bold leading-tight" style={{ color: tailAttached ? "#34d399" : "#e9c176" }}>
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
            <p className="text-lg font-bold text-on-surface leading-tight">{head.price_asof}</p>
          </div>
          <div>
            <p className="text-[11px] text-on-surface-variant/60">산출 시각 (generated_at)</p>
            <p className="text-lg font-bold text-on-surface leading-tight">{head.generated_at}</p>
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
              위에 크게 적은 머리 수는 {DETECTORS[0].label} 파일 것입니다. 파일별 값은 각 파일을 직접 보십시오.
            </p>
          </div>
        )}

        <div className="border-t border-outline-variant/10 pt-3">
          <p className="text-[11px] font-bold text-on-surface-variant/60 mb-1.5">분모 사슬</p>
          <p className="text-base text-on-surface">
            평가 {head.stage1_evaluated_n.toLocaleString()}
            <span className="text-on-surface-variant/50 mx-2">→</span>
            8관문 통과 {head.stage1_all_pass_n.toLocaleString()}
            <span className="text-on-surface-variant/50 mx-2">→</span>
            2단계 입력 {head.input_n.toLocaleString()}
          </p>
          <p className="text-[11px] text-on-surface-variant/70 mt-1">
            2단계에서 빠진 것 — 시세 없음 {head.no_series_n} · 마지막 봉이 낡음 {head.stale_bar_n} · 평가 오류{" "}
            {head.eval_error_n}
          </p>
        </div>
      </section>

      {/* ② 검출기 셋 — 진입과 이미 돌파를 갈라서 */}
      {loads.map((l) => (
        <DetectorSection key={l.file} loaded={l} />
      ))}

      {/* 표 읽는 법 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 text-xs space-y-2">
        <h3 className="text-sm font-serif font-bold text-on-surface">표 읽는 법</h3>
        <ul className="space-y-1 text-on-surface-variant">
          <li>
            <strong className="text-on-surface">피벗</strong> — 돌파 기준가. 장 시작 전 이 가격에 자동매수를
            예약합니다.
          </li>
          <li>
            <strong className="text-on-surface">피벗까지</strong> — (피벗 − 현재가) ÷ 피벗. 「아래」면 그만큼 올라야
            피벗에 닿고, 「위」면 이미 피벗을 넘었다는 뜻입니다.
          </li>
          <li>
            <strong className="text-on-surface">RS</strong> — 상대강도 순위(1~99). 1단계 합격선은 80입니다.
          </li>
          <li>
            <strong className="text-on-surface">50일 거래대금</strong> — 하루 거래대금 50일 평균을
            <strong className="text-on-surface"> 원화로 환산한 「억원 상당」</strong>입니다. 달러가 아닙니다.
          </li>
        </ul>
        <p className="text-on-surface-variant/55 pt-2 border-t border-outline-variant/15">
          읽는 자료는 검출기 파일 셋뿐입니다(VCP · 파워 플레이 · 3C). 페이지는 읽기 전용이며 아무것도 쓰지 않습니다.
        </p>
      </section>
    </div>
  );
}
