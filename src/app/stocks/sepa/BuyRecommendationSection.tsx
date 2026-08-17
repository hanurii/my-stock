"use client";

import { useState, Fragment } from "react";
import { fmtPrice } from "./sepaPatterns";
import { ExportBadge, type ExportTagMap } from "./ExportBadge";
import { SectorBadge, type SectorTagMap } from "./SectorBadge";
import { EarningsBadge, type EarningsMap } from "./EarningsBadge";

export interface BuyRec {
  code: string;
  name: string;
  market: string;
  current_price: number | null;
  rs: number | null;
  status: string | null;
  pivot_price: number | null;
  pct_to_pivot: number | null;
  entry_ready?: boolean;
  superperf_score: number;
  score_reasons: string[];
  prior_adv_pct: number | null;
  dist_52wh: number | null;
  rs_nh_days: number | null;
  rs_leads: number | null;
  pattern: string;
  gate_near?: boolean;
  gate_near_reasons?: string[];
  adv_50d_eok?: number | null;
  position_pct_of_adv?: number | null;
  one_day_exit?: boolean | null;
  liquidity?: string | null;
  /** 최근 20일 평균 거래대금(억원) — 청산 부담 N/M의 분모 */
  adv_20d_eok?: number | null;
  /** N: 기준 슬롯(position_krw) 매수 시 청산 부담률(%, ADV20 대비) */
  burden_pct?: number | null;
  /** M: 분할매도 가능성이 시작되는 금액(원) = ADV20 × 5% */
  split_risk_krw?: number | null;
  demand_watch?: { reason?: string; added?: string | null } | null;
}

export interface BuyRecFile {
  generated_at?: string;
  asof?: string;
  min_score?: number;
  position_krw?: number;
  count?: number;
  candidates?: BuyRec[];
}

// 매수 상태 = 패턴 리스트와 동일(돌파/진입임박/예의주시)
const STATUS_META: Record<string, { dot: string; label: string; color: string; bg: string }> = {
  breakout: { dot: "🔴", label: "돌파", color: "#ffb4ab", bg: "rgba(255,180,171,0.15)" },
  actionable: { dot: "🟢", label: "진입임박", color: "#34d399", bg: "rgba(52,211,153,0.15)" },
  forming: { dot: "🟡", label: "예의주시", color: "#e9c176", bg: "rgba(233,193,118,0.15)" },
};

// 유동성(청산 용이성) = 기준 포지션 ÷ 하루 평균 거래대금(50일). 낮을수록 빠져나오기 쉬움.
const LIQ_META: Record<string, { dot: string; label: string; color: string; bg: string }> = {
  ok: { dot: "🟢", label: "여유", color: "#34d399", bg: "rgba(52,211,153,0.15)" },
  caution: { dot: "🟡", label: "주의", color: "#e9c176", bg: "rgba(233,193,118,0.15)" },
  danger: { dot: "🔴", label: "위험", color: "#ffb4ab", bg: "rgba(255,180,171,0.15)" },
};
function fmtManwon(n?: number): string {
  return n == null ? "1,000만원" : `${Math.round(n / 10000).toLocaleString()}만원`;
}
// (구 데이터 폴백용) 안전 매수 한도 = 하루 평균 거래대금(50일) × 5%.
const SAFE_ADV_RATIO = 0.05;
function safeLimitEok(advEok?: number | null): number | null {
  return advEok == null ? null : advEok * SAFE_ADV_RATIO;
}
function fmtLimitEok(limitEok: number | null): string {
  if (limitEok == null) return "—";
  if (limitEok >= 1) return `~${limitEok.toFixed(1).replace(/\.0$/, "")}억`;
  // 1억 미만은 100만원 단위 반올림 (0.895억 → ~9,000만)
  return `~${(Math.round(limitEok * 100) * 100).toLocaleString()}만`;
}
// 청산 부담 색: N(burden_pct) 기준 — 실제 손절 34건 슬리피지 실측 앵커
// 🟢 5% 미만(비용 사실상 0) · 🟡 5~30%(분할 매도 가능성) · 🔴 30% 이상(실측 사고 구간)
function burdenMeta(pct: number): { dot: string; color: string; bg: string } {
  if (pct < 5) return { dot: "🟢", color: "#34d399", bg: "rgba(52,211,153,0.15)" };
  if (pct < 30) return { dot: "🟡", color: "#e9c176", bg: "rgba(233,193,118,0.15)" };
  return { dot: "🔴", color: "#ffb4ab", bg: "rgba(255,180,171,0.15)" };
}
// M(분할매도 가능성 시작 금액, 원) 표시: 1억 이상 "N.N억"(끝 .0 제거) · 미만은 10만 단위 반올림 "3,730만"
function fmtSplitRisk(krw: number): string {
  if (krw >= 100_000_000) return `${(krw / 100_000_000).toFixed(1).replace(/\.0$/, "")}억`;
  return `${(Math.round(krw / 100_000) * 10).toLocaleString()}만`;
}
// 초수익 점수 색: 4+ 초록 · 2~3 금색(동일) · 0~1 회색
function scoreStyle(s: number): { color: string; bg: string } {
  if (s >= 4) return { color: "#10b981", bg: "rgba(16,185,129,0.16)" };
  if (s >= 2) return { color: "#e9c176", bg: "rgba(233,193,118,0.14)" };
  return { color: "#a8b5d0", bg: "rgba(168,181,208,0.12)" };
}
// 피벗 대비: 0에 가까울수록 진입 적기(|값| 작을수록 좋음)
function pivotColor(n: number | null): string {
  if (n == null) return "var(--on-surface-variant)";
  const a = Math.abs(n);
  if (a <= 3) return "#10b981";
  if (a <= 8) return "#34d399";
  if (a <= 12) return "#e9c176";
  return "#a8b5d0";
}
function scoreText(s: number): string {
  return s === 6 ? "6점 만점" : `${s}점`;
}
function rsColor(n: number | null): string {
  if (n == null) return "var(--on-surface-variant)";
  if (n >= 90) return "#10b981";
  if (n >= 80) return "#34d399";
  if (n >= 70) return "#e9c176";
  return "#ffb4ab";
}
function fmtAdv(n: number | null): string {
  return n == null ? "—" : `${n > 0 ? "+" : ""}${Math.round(n)}%`;
}
function fmtFromPivot(n: number | null): string {
  // 데이터(pct_to_pivot)=(피벗−현재)/피벗. 표시는 부호 반전: 음수=피벗 아래, 양수=피벗 위.
  if (n == null) return "—";
  const v = -n;
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

const COLS = 12;

function Detail({ r, slotLabel }: { r: BuyRec; slotLabel: string }) {
  // 각 요인이 획득한 점수(만점 대비) — 어디서 점수를 받았는지 한눈에.
  const priorEarned = r.prior_adv_pct == null ? 0 : r.prior_adv_pct >= 100 ? 2 : r.prior_adv_pct >= 50 ? 1 : 0;
  const rsEarned = r.rs == null ? 0 : r.rs >= 90 ? 2 : r.rs >= 80 ? 1 : 0;
  const nhEarned = r.rs_nh_days != null && r.rs_nh_days <= 10 ? 1 : 0;
  const leadEarned = r.rs_leads != null && r.rs_leads > 0 ? 1 : 0;
  const factors: { name: string; value: string; earned: number; max: number }[] = [
    { name: "직전 상승폭", value: fmtAdv(r.prior_adv_pct), earned: priorEarned, max: 2 },
    { name: "RS 상대강도", value: r.rs != null ? String(r.rs) : "—", earned: rsEarned, max: 2 },
    { name: "RS선 신고가", value: r.rs_nh_days == null ? "—" : r.rs_nh_days === 0 ? "오늘 (0일 전)" : `${r.rs_nh_days}일 전`, earned: nhEarned, max: 1 },
    { name: "RS선 선행", value: r.rs_leads == null ? "—" : r.rs_leads > 0 ? `주가보다 ${r.rs_leads}일 먼저` : "뒤처짐 (주가가 먼저)", earned: leadEarned, max: 1 },
  ];
  const hasBurden = r.burden_pct != null && r.split_risk_krw != null;
  const liquidityRows: [string, string][] = hasBurden
    ? [
        ["최근 20일 평균 거래대금", r.adv_20d_eok != null ? `${r.adv_20d_eok}억` : "—"],
        ["참고: 50일 평균", r.adv_50d_eok != null ? `${r.adv_50d_eok}억` : "—"],
        [`${slotLabel} 매수 시 부담`, `${r.burden_pct!.toFixed(1)}%`],
        ["분할매도 가능성 시작", `약 ${fmtSplitRisk(r.split_risk_krw!)}부터`],
      ]
    : [
        ["하루 평균 거래대금(50일)", r.adv_50d_eok != null ? `${r.adv_50d_eok}억` : "—"],
        ["안전 매수 한도(거래대금 5%)", fmtLimitEok(safeLimitEok(r.adv_50d_eok))],
        ["포지션 비중(유동성)", r.position_pct_of_adv != null ? `하루 거래대금의 ${r.position_pct_of_adv}%` : "—"],
        ["하루 청산", r.one_day_exit == null ? "—" : r.one_day_exit ? "가능" : "불가 (며칠 분할 필요)"],
      ];
  const extra: [string, string][] = [
    ["52주 고가 대비", r.dist_52wh != null ? `${r.dist_52wh}%` : "—"],
    ["현재가", fmtPrice(r.current_price)],
    ["피벗(매수 기준선)", fmtPrice(r.pivot_price)],
    ["피벗 대비", fmtFromPivot(r.pct_to_pivot)],
    ...liquidityRows,
  ];
  return (
    <div className="space-y-3">
      {/* 점수 내역 — 어느 요인에서 몇 점 */}
      <div>
        <div className="flex items-baseline justify-between mb-1.5">
          <span className="text-[10px] font-bold tracking-wider text-on-surface-variant/50 uppercase">초수익 잠재력</span>
          <span className="text-xs font-bold tabular-nums text-on-surface">{r.superperf_score} / 6점</span>
        </div>
        <div className="flex flex-col gap-1">
          {factors.map((f) => {
            const on = f.earned > 0;
            return (
              <div key={f.name} className={`flex items-center gap-2.5 text-[11.5px] ${on ? "" : "opacity-60"}`}>
                <span className="w-3 text-center" style={{ color: on ? "#34d399" : "var(--on-surface-variant)" }}>{on ? "✓" : "–"}</span>
                <span className="w-24 text-on-surface whitespace-nowrap">{f.name}</span>
                <span className="tabular-nums font-semibold w-11 text-right" style={{ color: on ? "#34d399" : "var(--on-surface-variant)" }}>{f.earned} / {f.max}</span>
                <span className="tabular-nums text-on-surface-variant/70 whitespace-nowrap">{f.value}</span>
              </div>
            );
          })}
        </div>
      </div>
      {/* 세부값 */}
      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1.5 border-t border-outline-variant/10 pt-2">
        {extra.map(([k, v]) => (
          <div key={k} className="flex flex-col">
            <dt className="text-[10px] text-on-surface-variant/50">{k}</dt>
            <dd className="text-xs text-on-surface font-medium tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function BuyRecommendationSection({ data, exportTags, sectorTags, earnings }: { data: BuyRecFile | null; exportTags?: ExportTagMap; sectorTags?: SectorTagMap; earnings?: EarningsMap }) {
  const [open, setOpen] = useState<string | null>(null);

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
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">trophy</span>
        매수 추천 리스트 (초수익 잠재력 순)
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">{rows.length}종목</span>
      </h3>

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
                <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80" title="피벗 = 매수 기준선(이 가격 돌파가 매수 신호)">피벗</th>
                <th className="px-2 py-2 text-right text-[11px] font-medium text-on-surface-variant/80" title="현재가와 피벗(매수 기준선) 차이. 0에 가까울수록 진입 적기 · 양수=피벗 위">피벗대비</th>
                <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80" title={`N / M — N: 기준 슬롯(${fmtManwon(data.position_krw)}) 매수 시 청산 부담률(최근 20일 평균 거래대금 대비) · M: 분할매도 가능성이 시작되는 금액(거래대금의 5%). 막지 않는 정보 표시.`}>청산 부담</th>
                <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80">매수</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const sm = STATUS_META[r.status ?? ""] ?? { dot: "", label: r.status ?? "—", color: "#a8b5d0", bg: "rgba(168,181,208,0.10)" };
                const lm = r.liquidity != null ? LIQ_META[r.liquidity] ?? null : null;
                const burden =
                  r.burden_pct != null && r.split_risk_krw != null
                    ? { n: r.burden_pct.toFixed(1), m: fmtSplitRisk(r.split_risk_krw), ...burdenMeta(r.burden_pct) }
                    : null;
                const ss = scoreStyle(r.superperf_score);
                const isOpen = open === r.code;
                const dimmed = r.demand_watch != null; // 기관 수요 유보 — 순위 제외·딤드(모니터링용으로 남김)
                return (
                  <Fragment key={r.code}>
                    <tr
                      onClick={() => setOpen(isOpen ? null : r.code)}
                      className={`border-t border-outline-variant/10 hover:bg-surface-container-high/50 transition-colors cursor-pointer ${dimmed ? "opacity-40 hover:opacity-70" : ""}`}
                    >
                      <td className="px-2 py-2 text-center text-on-surface-variant/50 font-mono">{dimmed ? "—" : i + 1}</td>
                      <td className="px-2 py-2 text-center whitespace-nowrap">
                        <span className="text-[11px] px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: ss.bg, color: ss.color }}>
                          {scoreText(r.superperf_score)}
                        </span>
                      </td>
                      <td className="px-2 py-2 sticky left-0 bg-surface-container-low">
                        <div className="flex flex-col">
                          <span className="text-on-surface font-medium leading-tight">
                            {r.name} <SectorBadge tag={sectorTags?.[r.code]} /> <ExportBadge tag={exportTags?.[r.code]} />{" "}
                            <EarningsBadge entry={earnings?.[r.code]} />
                            {r.gate_near === true && (
                              <span
                                title={`관문 임박 — 트렌드 8조건 중 ${r.gate_near_reasons?.join(" · ") || "이평선 근접(①⑤)"}만 미달(52주고가 -25% 이내 등 나머지 통과). 이평선 바로 밑 코일이 돌파 전날 빠지지 않게 편입`}
                                className="inline-flex items-center rounded px-1 py-px text-[10px] leading-none align-middle whitespace-nowrap ml-0.5"
                                style={{ backgroundColor: "rgba(168,181,208,0.14)", color: "#a8b5d0" }}
                              >
                                ⏳관문임박
                              </span>
                            )}
                            {dimmed && (
                              <span
                                title={`기관 수요 유보(${r.demand_watch?.added ?? ""}) — ${r.demand_watch?.reason ?? ""}`}
                                className="inline-flex items-center rounded px-1 py-px text-[10px] leading-none align-middle whitespace-nowrap ml-0.5"
                                style={{ backgroundColor: "rgba(168,181,208,0.14)", color: "#a8b5d0" }}
                              >
                                🚫 기관수요 유보
                              </span>
                            )}
                          </span>
                          <span className="text-[10px] text-on-surface-variant/50 font-mono">
                            {r.code}
                            {r.gate_near === true && (r.gate_near_reasons?.length ?? 0) > 0 && (
                              <span className="font-sans" style={{ color: "#a8b5d0" }}>
                                {" · "}⏳ {r.gate_near_reasons!.join(" · ")}
                              </span>
                            )}
                          </span>
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
                      <td className="px-2 py-2 text-right tabular-nums text-on-surface">{fmtPrice(r.current_price)}</td>
                      <td className="px-2 py-2 text-right tabular-nums text-on-surface-variant/80">{fmtPrice(r.pivot_price)}</td>
                      <td className="px-2 py-2 text-right tabular-nums" style={{ color: pivotColor(r.pct_to_pivot) }}>{fmtFromPivot(r.pct_to_pivot)}</td>
                      <td className="px-2 py-2 text-center whitespace-nowrap">
                        {burden != null ? (
                          <span
                            className="text-[10px] px-1.5 py-0.5 rounded font-medium tabular-nums"
                            style={{ backgroundColor: burden.bg, color: burden.color }}
                            title={`${fmtManwon(data.position_krw)} 매수 시 부담 ${burden.n}%(최근 20일 평균 거래대금 ${r.adv_20d_eok ?? "—"}억 기준) — 분할매도 가능성은 약 ${burden.m}부터`}
                          >
                            {burden.dot} {burden.n}% / {burden.m}
                          </span>
                        ) : lm == null ? (
                          <span className="text-on-surface-variant/50">—</span>
                        ) : (
                          <span
                            className="text-[10px] px-1.5 py-0.5 rounded font-medium tabular-nums"
                            style={{ backgroundColor: lm.bg, color: lm.color }}
                            title={r.adv_50d_eok != null ? `하루 평균 거래대금 ${r.adv_50d_eok}억의 5% — 기준 포지션은 거래대금의 ${r.position_pct_of_adv ?? "—"}%` : undefined}
                          >
                            {lm.dot} {r.adv_50d_eok != null ? fmtLimitEok(safeLimitEok(r.adv_50d_eok)) : lm.label}
                          </span>
                        )}
                      </td>
                      <td className="px-2 py-2 text-center whitespace-nowrap">
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ backgroundColor: sm.bg, color: sm.color }}>
                          {sm.dot} {sm.label}
                        </span>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-surface-container/25">
                        <td colSpan={COLS} className="px-4 py-3 border-t border-outline-variant/10">
                          <Detail r={r} slotLabel={fmtManwon(data.position_krw)} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 채점 기준 — 리스트 하단 */}
      <div className="mt-3 text-[11px] text-on-surface-variant/70 leading-relaxed bg-surface-container/20 rounded-lg px-3 py-2.5">
        <p className="font-semibold text-on-surface">초수익 잠재력 점수 (6점 만점)</p>
        <p className="mb-2 text-on-surface-variant/55">방법충실 돌파 백테스트로 검증 — 4점↑ = 6개월 내 더블 도달률 36% vs 0~1점 15%</p>
        <ul className="space-y-1 tabular-nums">
          <li>· <strong className="text-on-surface">직전 상승폭</strong> : 100%+ = 2점 · 50~100% = 1점</li>
          <li>· <strong className="text-on-surface">RS 상대강도</strong> : 90+ = 2점 · 80~89 = 1점</li>
          <li>· <strong className="text-on-surface">RS선 신고가</strong> : 최근 10거래일 내 신고가 = 1점</li>
          <li>· <strong className="text-on-surface">RS선 선행</strong> : RS선이 주가보다 먼저 신고가 = 1점</li>
        </ul>
        <p className="mt-2 pt-2 border-t border-outline-variant/10">
          <strong className="text-on-surface">청산 부담 (N / M)</strong> : N = 기준 슬롯 {fmtManwon(data.position_krw)}{" "}
          매수 시 청산 부담률(최근 20일 평균 거래대금 대비) — 🟢 5% 미만 = 시장가 즉시 청산(실측 슬리피지 사실상 0) ·
          🟡 5~30% = 분할 매도 가능성 · 🔴 30% 이상 = 여러 날 각오(실측 사고 구간). M = 분할매도 가능성이 시작되는
          금액(거래대금의 5% 경계) — 이 금액까지는 🟢. 경계는 실제 손절 34건의 슬리피지 실측이 앵커.
        </p>
        <p className="mt-1.5">
          <strong className="text-on-surface">🚫 기관수요 유보</strong> : 셋업은 점등하지만 돌파일 거래량 등 기관 매집
          증거가 없어 매수 유보한 종목(<code className="text-[10px]">sepa-demand-watchlist.json</code> 직접 관리) —
          순위에서 빼고 흐리게 표시만. 기관 수요가 붙으면 목록에서 제거해 복귀.
        </p>
      </div>
    </section>
  );
}
