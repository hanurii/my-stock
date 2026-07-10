import { fmtPrice } from "./sepaPatterns";

export interface BuyRec {
  code: string;
  name: string;
  market: string;
  current_price: number | null;
  rs: number | null;
  status: string | null;
  pivot_price: number | null;
  pct_to_pivot: number | null;
  entry_ready: boolean;
  superperf_score: number;
  score_reasons: string[];
  prior_adv_pct: number | null;
  dist_52wh: number | null;
  pattern: string;
  entry_tier: "ready" | "near" | "far";
}

export interface BuyRecFile {
  generated_at?: string;
  asof?: string;
  min_score?: number;
  count?: number;
  candidates?: BuyRec[];
}

function scoreMeta(s: number): { color: string; bg: string; label: string } {
  if (s >= 5) return { color: "#10b981", bg: "rgba(16,185,129,0.16)", label: "강력" };
  if (s >= 4) return { color: "#34d399", bg: "rgba(52,211,153,0.15)", label: "높음" };
  return { color: "#e9c176", bg: "rgba(233,193,118,0.15)", label: "관심" };
}

const ENTRY_META: Record<BuyRec["entry_tier"], { dot: string; label: string; color: string; bg: string }> = {
  ready: { dot: "🟢", label: "진입권", color: "#34d399", bg: "rgba(52,211,153,0.15)" },
  near: { dot: "🟡", label: "곧", color: "#e9c176", bg: "rgba(233,193,118,0.15)" },
  far: { dot: "", label: "멀음", color: "#a8b5d0", bg: "rgba(168,181,208,0.10)" },
};

function rsColor(n: number | null): string {
  if (n === null || n === undefined) return "var(--on-surface-variant)";
  if (n >= 90) return "#10b981";
  if (n >= 80) return "#34d399";
  if (n >= 70) return "#e9c176";
  return "#ffb4ab";
}

function fmtAdv(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return `${n > 0 ? "+" : ""}${Math.round(n)}%`;
}

export function BuyRecommendationSection({ data }: { data: BuyRecFile | null }) {
  if (!data) {
    return (
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">trophy</span>
          매수 추천 리스트 (초수익 잠재력 순)
        </h3>
        <p className="text-sm text-on-surface-variant/60 bg-surface-container-low rounded-xl ghost-border p-4">
          데이터가 아직 생성되지 않았습니다. (산출 파일 <code className="text-xs">sepa-buy-recommendations.json</code> 없음 —{" "}
          <code className="text-xs">find-buy-recommendations</code> 스킬 실행)
        </p>
      </section>
    );
  }

  const rows = data.candidates ?? [];

  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-1 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">trophy</span>
        매수 추천 리스트 (초수익 잠재력 순)
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">{rows.length}종목</span>
      </h3>
      <p className="text-xs text-on-surface-variant/70 leading-relaxed mb-3">
        검출된 후보 중 <strong className="text-on-surface">초수익 잠재력</strong>(직전 상승폭·RS·RS선 신고가·RS선 선행 —
        방법충실 돌파 백테스트로 검증, <strong className="text-on-surface">4점↑ = 6개월 내 더블 도달률 36%</strong> vs 0~1점 15%)이
        높은 순. 매수 타이밍(<span style={{ color: "#34d399" }}>진입권</span>/<span style={{ color: "#e9c176" }}>곧</span>/멀음)은
        배지로 표시만 하고 정렬엔 반영하지 않습니다(점수 순수 랭킹). <strong className="text-on-surface">점수(잠재력)와 매수 타이밍은 별개</strong> —
        점수 높아도 피벗을 이미 지났으면 지금 매수는 아닙니다.
      </p>

      {rows.length === 0 ? (
        <p className="text-center text-on-surface-variant/60 py-6 text-sm bg-surface-container-low rounded-xl ghost-border">
          현재 초수익 잠재력 후보 없음(점수 {data.min_score ?? 3}점 이상).
        </p>
      ) : (
        <div className="overflow-x-auto bg-surface-container-low rounded-xl ghost-border">
          <table className="w-full text-xs">
            <thead className="bg-surface-container/40">
              <tr>
                <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">#</th>
                <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">초수익</th>
                <th className="px-2 py-2 text-left text-[11px] font-medium text-on-surface-variant/80 sticky left-0 bg-surface-container/40">종목</th>
                <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">시장</th>
                <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">패턴</th>
                <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">RS</th>
                <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80" title="최근 6개월 최저점 대비 상승폭">직전상승</th>
                <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80">현재가</th>
                <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">매수</th>
                <th className="px-2 py-2 text-left text-[11px] font-medium text-on-surface-variant/80">근거</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const sm = scoreMeta(r.superperf_score);
                const em = ENTRY_META[r.entry_tier];
                return (
                  <tr key={r.code} className="border-t border-outline-variant/10 hover:bg-surface-container-high/50 transition-colors">
                    <td className="px-2 py-2 text-center text-on-surface-variant/50 font-mono">{i + 1}</td>
                    <td className="px-2 py-2 text-center whitespace-nowrap">
                      <span className="text-[11px] px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: sm.bg, color: sm.color }}>
                        {r.superperf_score}점 {sm.label}
                      </span>
                    </td>
                    <td className="px-2 py-2 sticky left-0 bg-surface-container-low">
                      <div className="flex flex-col">
                        <span className="text-on-surface font-medium leading-tight">{r.name}</span>
                        <span className="text-[10px] text-on-surface-variant/50 font-mono">{r.code}</span>
                      </div>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${r.market === "KOSPI" ? "bg-blue-500/15 text-blue-300" : "bg-purple-500/15 text-purple-300"}`}>
                        {r.market}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-center text-on-surface-variant/80 whitespace-nowrap">{r.pattern}</td>
                    <td className="px-2 py-2 text-right font-bold" style={{ color: rsColor(r.rs) }}>{r.rs ?? "—"}</td>
                    <td className="px-2 py-2 text-right font-medium" style={{ color: "#34d399" }}>{fmtAdv(r.prior_adv_pct)}</td>
                    <td className="px-2 py-2 text-right text-on-surface-variant">{fmtPrice(r.current_price)}</td>
                    <td className="px-2 py-2 text-center whitespace-nowrap">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ backgroundColor: em.bg, color: em.color }}>
                        {em.dot} {em.label}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-left text-[10px] text-on-surface-variant/70">{r.score_reasons.join(" · ")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
