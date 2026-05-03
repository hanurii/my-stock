import type { MegacapStock } from "@/lib/megacap";
import { marketLabel, formatMarketCap } from "@/lib/megacap";

interface Props {
  stocks: MegacapStock[];
}

interface ReturnMachine {
  stock: MegacapStock;
  dividendPct: number;
  buybackPct: number;
  totalYield: number;
}

// 진짜 애플식 환원 머신 식별:
//  - 배당수익률 ≥ 2% (배당주)
//  - 자사주매입 ≥ 4% (자사주매입도 활발)
//  - 합산 환원율 ≤ 30% (이상치/특별배당 제외)
function isReturnMachine(s: MegacapStock): ReturnMachine | null {
  const dy = s.metrics.dividendYield;
  const sr = s.shareholder_return;
  const mc = s.metrics.marketCap;
  if (dy == null || dy < 0.02) return null;
  if (!sr || !mc || mc <= 0) return null;
  const buybackPct = (sr.buybacks_ttm / mc) * 100;
  if (buybackPct < 4) return null;
  if (sr.yield_pct > 30) return null; // 데이터 이상치 컷
  return {
    stock: s,
    dividendPct: dy * 100,
    buybackPct,
    totalYield: sr.yield_pct,
  };
}

function signalColorOf(label: MegacapStock["signal"]["label"]): string {
  if (label === "강한 매수") return "#10b981";
  if (label === "매수 검토") return "#fbbf24";
  if (label === "관찰") return "#94a3b8";
  return "#475569";
}

export function ReturnMachineCards({ stocks }: Props) {
  const machines = stocks
    .map((s) => isReturnMachine(s))
    .filter((m): m is ReturnMachine => m !== null)
    .sort((a, b) => b.totalYield - a.totalYield)
    .slice(0, 10);

  if (machines.length === 0) {
    return (
      <div className="text-on-surface-variant/60 text-sm py-6 text-center">
        조건 충족 종목이 없습니다.
      </div>
    );
  }

  return (
    <div>
      <div className="text-xs text-on-surface-variant/70 mb-3 leading-relaxed">
        조건: <span className="font-medium text-on-surface">배당수익률 ≥ 2%</span> + <span className="font-medium text-on-surface">자사주매입 ≥ 4%</span> = 총 환원율 ≥ 6%.
        2016 Q1 애플(배당 2.1% + 자사주매입 6~8%)과 같은 패턴.
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {machines.map((m, i) => {
          const s = m.stock;
          const sigColor = signalColorOf(s.signal.label);
          return (
            <div
              key={s.ticker}
              className="bg-surface-container-low rounded-xl ghost-border overflow-hidden"
              style={{ borderLeft: "3px solid #34d399" }}
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs font-mono text-on-surface-variant/50">
                      #{i + 1}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-on-surface">{s.name_kr}</div>
                      <div className="text-[11px] font-mono text-on-surface-variant/60">
                        {s.ticker} · {marketLabel(s.market)}
                      </div>
                    </div>
                  </div>
                  {s.signal.label && (
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-medium shrink-0"
                      style={{
                        backgroundColor: `${sigColor}20`,
                        color: sigColor,
                        border: `1px solid ${sigColor}40`,
                      }}
                    >
                      {s.signal.label}
                    </span>
                  )}
                </div>

                <div className="bg-surface-container/30 rounded-lg p-3 mt-3">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="text-[9px] uppercase tracking-wider text-on-surface-variant/60">
                        배당
                      </div>
                      <div className="text-sm font-mono font-bold text-amber-400 mt-0.5">
                        {m.dividendPct.toFixed(1)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] uppercase tracking-wider text-on-surface-variant/60">
                        자사주매입
                      </div>
                      <div className="text-sm font-mono font-bold text-blue-400 mt-0.5">
                        {m.buybackPct.toFixed(1)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] uppercase tracking-wider text-on-surface-variant/60">
                        총 환원
                      </div>
                      <div className="text-sm font-mono font-bold text-emerald-400 mt-0.5">
                        {m.totalYield.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-3 text-[11px]">
                  <span className="text-on-surface-variant/70">
                    시총 {formatMarketCap(s.metrics.marketCap, s.currency)}
                  </span>
                  <span className="text-on-surface-variant/70">
                    점수 <span className="font-mono font-bold text-on-surface">{s.scores.total.toFixed(1)}</span>
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-on-surface-variant/50 mt-3 leading-relaxed">
        💡 이 종목들은 4단계 점수가 낮을 수 있지만(보험·은행·정유 등 본업 마진이 메가캡 평균보다 낮음), 사용자님이 의도하신 "애플처럼 사고 싶다"의 직접적 후보입니다. 분할매수 시그널과 환율 점수를 함께 보고 판단하세요.
      </p>
    </div>
  );
}
