import type { EntryQuality, SellHoldingResult, Verdict } from "./types";

const VERDICT_STYLE: Record<
  Verdict["verdict"],
  { label: string; bg: string; fg: string; icon: string }
> = {
  HOLD: {
    label: "보유",
    bg: "#95d3ba",
    fg: "#0f3a2a",
    icon: "trending_flat",
  },
  BAD_ENTRY: {
    label: "잘못 매수",
    bg: "#b09bce",
    fg: "#1f1535",
    icon: "warning",
  },
  WATCH: {
    label: "관찰",
    bg: "#e8c875",
    fg: "#3a2e0a",
    icon: "visibility",
  },
  TRIM: {
    label: "비중 축소",
    bg: "#e8a25b",
    fg: "#3a1f0a",
    icon: "remove_circle",
  },
  SELL: {
    label: "매도",
    bg: "#ffb4ab",
    fg: "#3a0f0a",
    icon: "arrow_downward",
  },
};

function formatKrw(n: number): string {
  return n.toLocaleString("ko-KR");
}

function profitColor(pct: number): string {
  if (pct >= 5) return "#95d3ba";
  if (pct >= 0) return "#cfe8d0";
  if (pct >= -5) return "#e8c875";
  return "#ffb4ab";
}

interface ProgressBarProps {
  cutLoss: number;
  avg: number;
  tp1: number;
  tp2: number;
  current: number;
}

/**
 * 손절선 ~ 매수가 ~ 익절1 ~ 익절2 진행률 바.
 * 라벨 겹침 방지: 외곽 stop(손절선/익절2차)은 바 위, 안쪽 stop(매수가/익절1차)은 바 아래에 배치.
 */
function PriceProgressBar({
  cutLoss,
  avg,
  tp1,
  tp2,
  current,
}: ProgressBarProps) {
  const min = cutLoss;
  const max = tp2;
  const range = max - min;
  const clamp = (v: number) => Math.max(min, Math.min(max, v));
  const pct = (v: number) => ((clamp(v) - min) / range) * 100;

  const currentPct = pct(current);
  const avgPct = pct(avg);
  const tp1Pct = pct(tp1);

  // 안쪽 라벨이 양 끝에 닿지 않도록 정렬 보정
  function innerLabelStyle(posPct: number): React.CSSProperties {
    if (posPct < 12) return { left: "0%", transform: "translateX(0)" };
    if (posPct > 88) return { right: "0%", left: "auto", transform: "translateX(0)" };
    return { left: `${posPct}%`, transform: "translateX(-50%)" };
  }
  function innerLabelAlign(posPct: number): string {
    if (posPct < 12) return "text-left";
    if (posPct > 88) return "text-right";
    return "text-center";
  }

  return (
    <div className="space-y-1.5">
      {/* 상단 외곽 라벨: 손절선 / 익절 2차 */}
      <div className="flex justify-between items-start text-[10px]">
        <div className="text-left">
          <p className="font-medium" style={{ color: "#ffb4ab" }}>
            손절선 <span className="text-on-surface-variant/50">-8%</span>
          </p>
          <p className="text-on-surface-variant/70">{formatKrw(cutLoss)}원</p>
        </div>
        <div className="text-right">
          <p className="font-medium" style={{ color: "#95d3ba" }}>
            <span className="text-on-surface-variant/50">+25%</span> 익절 2차
          </p>
          <p className="text-on-surface-variant/70">{formatKrw(tp2)}원</p>
        </div>
      </div>

      {/* 진행률 바 */}
      <div className="relative h-3 w-full">
        {/* 색상 영역 (손절~매수가 빨강, 매수가~익절1 무난, 익절1~익절2 초록) */}
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-1 rounded-full overflow-hidden">
          <div
            className="absolute inset-y-0 bg-[#ffb4ab]/30"
            style={{ left: "0%", width: `${avgPct}%` }}
          />
          <div
            className="absolute inset-y-0 bg-on-surface/10"
            style={{ left: `${avgPct}%`, width: `${tp1Pct - avgPct}%` }}
          />
          <div
            className="absolute inset-y-0 bg-[#95d3ba]/30"
            style={{ left: `${tp1Pct}%`, right: "0%" }}
          />
        </div>

        {/* 4개 stop 수직선 */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-px h-3"
          style={{ left: 0, backgroundColor: "#ffb4ab" }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-px h-3"
          style={{ left: `${avgPct}%`, backgroundColor: "#a8b5d0" }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-px h-3"
          style={{ left: `${tp1Pct}%`, backgroundColor: "#e8a25b" }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-px h-3"
          style={{ right: 0, backgroundColor: "#95d3ba" }}
        />

        {/* 현재가 마커 */}
        <div
          className="absolute top-1/2 w-3 h-3 rounded-full border-2 border-surface bg-on-surface shadow z-10"
          style={{
            left: `${currentPct}%`,
            transform: "translate(-50%, -50%)",
          }}
          title={`현재가 ${formatKrw(current)}원`}
        />
      </div>

      {/* 하단 안쪽 라벨: 매수가 / 익절 1차 (각 stop의 정확한 위치) */}
      <div className="relative h-9">
        <div
          className={`absolute top-0 text-[10px] whitespace-nowrap ${innerLabelAlign(avgPct)}`}
          style={innerLabelStyle(avgPct)}
        >
          <p className="font-medium" style={{ color: "#a8b5d0" }}>
            매수가
          </p>
          <p className="text-on-surface-variant/70">{formatKrw(avg)}원</p>
        </div>
        <div
          className={`absolute top-0 text-[10px] whitespace-nowrap ${innerLabelAlign(tp1Pct)}`}
          style={innerLabelStyle(tp1Pct)}
        >
          <p className="font-medium" style={{ color: "#e8a25b" }}>
            <span className="text-on-surface-variant/50">+20%</span> 익절 1차
          </p>
          <p className="text-on-surface-variant/70">{formatKrw(tp1)}원</p>
        </div>
      </div>

      {/* 현재가 표기 (마커 아래) */}
      <div className="relative h-5">
        <span
          className={`absolute top-0 text-[11px] font-bold text-on-surface whitespace-nowrap ${innerLabelAlign(currentPct)}`}
          style={innerLabelStyle(currentPct)}
        >
          현재가 {formatKrw(current)}원
        </span>
      </div>
    </div>
  );
}

interface RuleCheckProps {
  label: string;
  hit: boolean;
  hitLabel?: string;
  passLabel?: string;
  tone?: "good" | "bad" | "info";
}

function RuleCheck({
  label,
  hit,
  hitLabel = "도달",
  passLabel = "정상",
  tone = "info",
}: RuleCheckProps) {
  const color = hit
    ? tone === "bad"
      ? "#ffb4ab"
      : tone === "good"
        ? "#95d3ba"
        : "#e8c875"
    : "#7a8b87";
  return (
    <div className="flex items-center gap-1.5">
      <span
        className="material-symbols-outlined text-base"
        style={{ color }}
      >
        {hit ? "check_circle" : "radio_button_unchecked"}
      </span>
      <span className="text-on-surface-variant">{label}</span>
      <span className="text-on-surface-variant/60 text-[11px]">
        — {hit ? hitLabel : passLabel}
      </span>
    </div>
  );
}

function GradeBadge({ grade }: { grade: EntryQuality["grade"] }) {
  const color =
    grade.label === "정확한 진입"
      ? "#95d3ba"
      : grade.label === "부분 통과"
        ? "#e8c875"
        : "#b09bce";
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold"
      style={{ backgroundColor: `${color}30`, color }}
    >
      {grade.label} ({grade.book_checks_passed}/{grade.book_checks_total})
    </span>
  );
}

interface CutoffCardProps {
  passed: boolean;
  title: string;
  primary: string;
  secondary?: string;
  note?: string;
}

function CutoffCard({ passed, title, primary, secondary, note }: CutoffCardProps) {
  const color = passed ? "#95d3ba" : "#b09bce";
  return (
    <div
      className="rounded-lg p-3 border"
      style={{
        backgroundColor: `${color}10`,
        borderColor: `${color}30`,
      }}
    >
      <div className="flex items-center gap-1.5 mb-2">
        <span
          className="material-symbols-outlined text-base"
          style={{ color }}
        >
          {passed ? "check_circle" : "cancel"}
        </span>
        <p className="text-[11px] font-medium text-on-surface-variant">
          {title}
        </p>
      </div>
      <p className="text-sm font-bold" style={{ color }}>
        {primary}
      </p>
      {secondary && (
        <p className="text-[11px] text-on-surface-variant/70 mt-0.5">
          {secondary}
        </p>
      )}
      {note && (
        <p className="text-[10px] text-on-surface-variant/50 mt-1.5 leading-relaxed">
          {note}
        </p>
      )}
    </div>
  );
}

function EntryQualitySection({ eq }: { eq: EntryQuality }) {
  const b = eq.breakout;
  const vsHighPct =
    eq.vs_high_ratio != null ? eq.vs_high_ratio * 100 : null;

  // 카드 1: 정확한 분기점 매수
  let pivotCard: CutoffCardProps;
  if (b.has_valid_base && b.pivot_price != null && b.vs_pivot_pct != null) {
    const sign = b.vs_pivot_pct >= 0 ? "+" : "";
    pivotCard = {
      passed: b.within_5pct_of_pivot,
      title: "정확한 분기점 매수",
      primary: `분기점 대비 ${sign}${b.vs_pivot_pct.toFixed(2)}%`,
      secondary: `분기점 ${formatKrw(b.pivot_price)}원 (${b.base_left_high_date ?? "-"})`,
      note: b.within_5pct_of_pivot
        ? `모양 깊이 ${b.base_depth_pct?.toFixed(1)}% · ${((b.base_days ?? 0) / 5).toFixed(1)}주 형성 — 책 기준 ±5% 이내 충족`
        : `모양은 있으나 분기점 +5% 초과 — 책 기준 위반`,
    };
  } else {
    pivotCard = {
      passed: false,
      title: "정확한 분기점 매수",
      primary: "유효한 모양 없음",
      secondary: b.no_base_reason ?? "매수 직전 base 형성 안 됨",
      note: "책 기준: 좌측 고점 + 5주+ 형성 + 깊이 5~40% + 분기점 +5% 이내 매수",
    };
  }

  // 카드 2: 거래량 동반
  const volCard: CutoffCardProps = {
    passed: eq.checks.volume_surge_50pct,
    title: "거래량 동반",
    primary:
      eq.volume_ratio != null
        ? `60일 평균 × ${eq.volume_ratio.toFixed(2)}배`
        : "데이터 없음",
    secondary:
      eq.entry_volume != null && eq.avg_volume_60d != null
        ? `매수일 ${eq.entry_volume.toLocaleString()}주 / 평균 ${eq.avg_volume_60d.toLocaleString()}주`
        : undefined,
    note: eq.checks.volume_surge_50pct
      ? "책 기준 60일 평균 +50% (1.5배) 이상 충족"
      : "책 기준 60일 평균 +50% 미달",
  };

  // 카드 3: 일중 고점 추격 회피 (NOT chased가 통과)
  const chaseCard: CutoffCardProps = {
    passed: !eq.checks.chased_intraday_high,
    title: "일중 고점 추격 회피",
    primary: vsHighPct != null ? `일중 고점의 ${vsHighPct.toFixed(1)}%` : "데이터 없음",
    secondary:
      eq.entry_high != null && eq.entry_low != null
        ? `일중 ${formatKrw(eq.entry_low)}~${formatKrw(eq.entry_high)}원`
        : undefined,
    note: eq.checks.chased_intraday_high
      ? "책 기준 위반 — 일중 고점 95% 이상 매수는 추격"
      : "책 기준 < 95% 만족",
  };

  return (
    <div className="bg-surface-container/30 rounded-lg p-3 space-y-3 text-xs">
      {/* 헤더 */}
      <div className="flex items-baseline justify-between gap-2">
        <div className="flex items-center gap-2">
          <p className="text-on-surface-variant/80 font-medium">
            매수 진입 정확도
          </p>
          <GradeBadge grade={eq.grade} />
        </div>
        <p className="text-[10px] text-on-surface-variant/50">
          진입일 {eq.entry_date}
        </p>
      </div>

      {/* 3 cutoff 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <CutoffCard {...pivotCard} />
        <CutoffCard {...volCard} />
        <CutoffCard {...chaseCard} />
      </div>

      {/* 보조 — 매수일 캔들 raw + 직전 52주 신고가 */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-on-surface-variant/60 pt-1 border-t border-on-surface/5">
        {eq.entry_close != null && (
          <span>
            매수일 종가{" "}
            <span className="text-on-surface-variant/80">
              {formatKrw(eq.entry_close)}원
            </span>
            {eq.vs_close_pct != null && (
              <span className="text-on-surface-variant/50 ml-1">
                (매수가 {eq.vs_close_pct >= 0 ? "+" : ""}
                {eq.vs_close_pct.toFixed(2)}%)
              </span>
            )}
          </span>
        )}
        {eq.prior_high_52w && eq.prior_high_52w_date && (
          <span>
            직전 52주 신고가{" "}
            <span className="text-on-surface-variant/80">
              {formatKrw(eq.prior_high_52w)}원
            </span>
            <span className="text-on-surface-variant/50 ml-1">
              ({eq.prior_high_52w_date.slice(0, 4)}-
              {eq.prior_high_52w_date.slice(4, 6)}-
              {eq.prior_high_52w_date.slice(6, 8)})
            </span>
          </span>
        )}
      </div>
    </div>
  );
}

export function HoldingCard({ h }: { h: SellHoldingResult }) {
  const v = VERDICT_STYLE[h.strategy_verdict.verdict];
  const profitPct = h.profit_pct;
  const profitC = profitColor(profitPct);

  return (
    <article className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
      {/* 헤더 */}
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-serif font-bold text-on-surface">
            {h.name}
            <span className="text-xs font-sans font-normal text-on-surface-variant/60 ml-2">
              {h.code}
            </span>
          </h3>
          {h.sector && (
            <p className="text-xs text-on-surface-variant/60 mt-0.5">
              {h.sector}
            </p>
          )}
        </div>
        <span
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold"
          style={{ backgroundColor: v.bg, color: v.fg }}
        >
          <span className="material-symbols-outlined text-sm">{v.icon}</span>
          {v.label}
        </span>
      </header>

      {/* 손익 한 줄 */}
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-on-surface-variant/60 text-xs mb-0.5">매수가</p>
          <p className="text-on-surface font-medium">
            {formatKrw(h.avg_price)}원
          </p>
        </div>
        <div>
          <p className="text-on-surface-variant/60 text-xs mb-0.5">현재가</p>
          <p className="text-on-surface font-medium">
            {formatKrw(h.current_price)}원
          </p>
        </div>
        <div>
          <p className="text-on-surface-variant/60 text-xs mb-0.5">손익률</p>
          <p className="font-bold" style={{ color: profitC }}>
            {profitPct >= 0 ? "+" : ""}
            {profitPct.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* 손절·익절 가격 명시 */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="bg-[#ffb4ab]/10 rounded-lg p-2.5 border border-[#ffb4ab]/20">
          <p className="text-[#ffb4ab]/80 mb-0.5">손절선 -8%</p>
          <p className="text-on-surface font-medium">
            {formatKrw(h.strategy.cut_loss_price)}원
          </p>
        </div>
        <div className="bg-[#e8a25b]/10 rounded-lg p-2.5 border border-[#e8a25b]/20">
          <p className="text-[#e8a25b]/80 mb-0.5">익절 1차 +20%</p>
          <p className="text-on-surface font-medium">
            {formatKrw(h.strategy.take_profit_1_price)}원
          </p>
        </div>
        <div className="bg-[#95d3ba]/10 rounded-lg p-2.5 border border-[#95d3ba]/20">
          <p className="text-[#95d3ba]/80 mb-0.5">익절 2차 +25%</p>
          <p className="text-on-surface font-medium">
            {formatKrw(h.strategy.take_profit_2_price)}원
          </p>
        </div>
      </div>

      {/* 진행률 바: 손절선 ~ 매수가 ~ 익절선 (외곽 위·안쪽 아래 분산 배치) */}
      <div>
        <PriceProgressBar
          cutLoss={h.strategy.cut_loss_price}
          avg={h.avg_price}
          tp1={h.strategy.take_profit_1_price}
          tp2={h.strategy.take_profit_2_price}
          current={h.current_price}
        />
      </div>

      {/* 보유 기간 + 평가액 + 추가매수 한계 */}
      <div className="grid grid-cols-3 gap-3 text-xs">
        <div className="bg-surface-container/50 rounded-lg p-2.5">
          <p className="text-on-surface-variant/60 mb-0.5">포지션 시작</p>
          <p className="text-on-surface font-medium">
            {h.position_start_date ?? "-"}
          </p>
          <p className="text-on-surface-variant/60 text-[11px] mt-0.5">
            보유 {h.holding_weeks.toFixed(1)}주 ({h.holding_days}일)
          </p>
        </div>
        <div className="bg-surface-container/50 rounded-lg p-2.5">
          <p className="text-on-surface-variant/60 mb-0.5">평가액</p>
          <p className="text-on-surface font-medium">
            {formatKrw(h.eval_amount)}원
          </p>
          <p className="text-on-surface-variant/60 text-[11px] mt-0.5">
            {h.quantity}주 보유
          </p>
        </div>
        <div className="bg-surface-container/50 rounded-lg p-2.5">
          <p className="text-on-surface-variant/60 mb-0.5">
            추가매수 한계 +5%
          </p>
          <p className="text-on-surface font-medium">
            {formatKrw(h.strategy.add_buy_limit_price)}원
          </p>
          <p
            className="text-[11px] mt-0.5"
            style={{
              color: h.strategy.can_add_buy ? "#95d3ba" : "#ffb4ab",
            }}
          >
            {h.strategy.can_add_buy ? "추가 가능" : "추격 금지"}
          </p>
        </div>
      </div>

      {/* 룰 체크리스트 (8주 룰 제외) */}
      <div className="bg-surface-container/30 rounded-lg p-3 space-y-1.5 text-xs">
        <p className="text-on-surface-variant/80 font-medium mb-1.5">
          매도 룰 체크
        </p>
        <RuleCheck
          label="매수가 -8% 손절선"
          hit={h.strategy.rule_checks.cut_loss_hit}
          hitLabel="도달 — 즉시 손절"
          passLabel="여유"
          tone="bad"
        />
        <RuleCheck
          label="매수가 +20% 익절선 1차"
          hit={h.strategy.rule_checks.take_profit_1_hit}
          hitLabel="도달 — 분할 매도 검토"
          passLabel="미도달"
          tone="info"
        />
        <RuleCheck
          label="매수가 +25% 익절선 2차"
          hit={h.strategy.rule_checks.take_profit_2_hit}
          hitLabel="도달 — 분할 매도 권장"
          passLabel="미도달"
          tone="info"
        />
      </div>

      {/* 매수 진입 정확도 */}
      {h.strategy.entry_quality && (
        <EntryQualitySection eq={h.strategy.entry_quality} />
      )}

      {/* verdict 사유 */}
      <div className="border-l-2 pl-3" style={{ borderColor: v.bg }}>
        <p className="text-xs text-on-surface-variant/80 font-medium mb-1">
          판정 사유
        </p>
        <ul className="text-xs text-on-surface-variant space-y-0.5">
          {h.strategy_verdict.reasons.map((r, i) => (
            <li key={i} className="leading-relaxed">
              · {r}
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}
