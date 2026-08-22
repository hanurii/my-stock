import { describe, it, expect } from "vitest";
import { matchTrades, type Fill } from "./scorecard";
import { computeOverall, type Trade } from "./scorecard";
import { computeScorecard, summarizeDataErrors } from "./scorecard";

const buy = (date: string, code: string, price: number, qty: number, extra: Partial<Fill> = {}): Fill =>
  ({ date, code, name: code, side: "buy", price, qty, ...extra });
const sell = (date: string, code: string, price: number, qty: number, extra: Partial<Fill> = {}): Fill =>
  ({ date, code, name: code, side: "sell", price, qty, ...extra });

describe("matchTrades", () => {
  it("단순 왕복: 매수1 매도1 → 1거래, 수익률·보유일수·win", () => {
    const { trades, open, errors } = matchTrades([
      buy("2026-01-05", "A", 100, 100),
      sell("2026-01-08", "A", 110, 100),
    ]);
    expect(errors).toEqual([]);
    expect(open).toEqual([]);
    expect(trades).toHaveLength(1);
    const t = trades[0];
    expect(t.avg_buy).toBe(100);
    expect(t.avg_sell).toBe(110);
    expect(t.gross_pct).toBe(10);
    expect(t.net_pct).toBe(10);
    expect(t.hold_days).toBe(3);
    expect(t.outcome).toBe("win");
    expect(t.month).toBe("2026-01");
    expect(t.buy_qty).toBe(100);
    expect(t.sell_qty).toBe(100);
  });

  it("수수료·세금: 순수익률이 총수익률보다 낮다", () => {
    const { trades } = matchTrades([
      buy("2026-01-05", "A", 100, 100, { fees: 100 }),
      sell("2026-01-08", "A", 110, 100, { fees: 100, tax: 200 }),
    ]);
    expect(trades[0].gross_pct).toBe(10);
    expect(trades[0].net_pct).toBe(5.94); // (10700/10100-1)*100
  });

  it("분할 매수(피라미딩): 가중평균 매수가", () => {
    const { trades } = matchTrades([
      buy("2026-01-05", "A", 100, 100),
      buy("2026-01-06", "A", 120, 100),
      sell("2026-01-10", "A", 130, 200),
    ]);
    expect(trades).toHaveLength(1);
    expect(trades[0].avg_buy).toBe(110);
    expect(trades[0].gross_pct).toBe(18.18);
    expect(trades[0].buy_qty).toBe(200);
  });

  it("분할 익절: 가중평균 매도가·마지막 매도일 기준 보유일수", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 200),
      sell("2026-01-05", "A", 120, 100),
      sell("2026-01-11", "A", 140, 100),
    ]);
    expect(trades).toHaveLength(1);
    expect(trades[0].avg_sell).toBe(130);
    expect(trades[0].gross_pct).toBe(30);
    expect(trades[0].close_date).toBe("2026-01-11");
    expect(trades[0].hold_days).toBe(10);
    expect(trades[0].sell_qty).toBe(200);
  });

  it("재진입 분리: 청산 후 재매수 → 2개 독립 거래", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 100),
      sell("2026-01-02", "A", 110, 100),
      buy("2026-01-05", "A", 200, 100),
      sell("2026-01-06", "A", 180, 100),
    ]);
    expect(trades).toHaveLength(2);
    expect(trades[0].outcome).toBe("win");
    expect(trades[1].outcome).toBe("loss");
    expect(trades[1].gross_pct).toBe(-10);
  });

  it("미청산: 매수만 있으면 open에만, 통계 제외", () => {
    const { trades, open } = matchTrades([buy("2026-01-01", "A", 100, 100)]);
    expect(trades).toEqual([]);
    expect(open).toHaveLength(1);
    expect(open[0]).toMatchObject({ code: "A", qty: 100, avg_buy: 100, open_date: "2026-01-01" });
  });

  it("엣지: 보유수량 초과 매도 → errors, 해당 종목 제외", () => {
    const { trades, errors } = matchTrades([
      buy("2026-01-01", "A", 100, 100),
      sell("2026-01-02", "A", 110, 150),
    ]);
    expect(trades).toEqual([]);
    expect(errors.length).toBe(1);
    expect(errors[0]).toContain("A");
  });

  it("손절 규율: 계획 손절폭 초과 손실 → stop_violation true", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 100, { stop: 95 }), // 계획 -5%
      sell("2026-01-02", "A", 90, 100),               // 실제 -10%
    ]);
    expect(trades[0].outcome).toBe("loss");
    expect(trades[0].stop_violation).toBe(true);
  });

  it("손절 규율: 손절가 있어도 수익이면 위반 아님", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 100, { stop: 95 }),
      sell("2026-01-02", "A", 110, 100),
    ]);
    expect(trades[0].stop_violation).toBe(false);
  });

  it("본전(net 0) 거래는 손실로 분류", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 100, 100),
      sell("2026-01-02", "A", 100, 100),
    ]);
    expect(trades[0].net_pct).toBe(0);
    expect(trades[0].outcome).toBe("loss");
  });

  it("데이터 오류 종목은 앞선 정상 왕복거래까지 전부 제외", () => {
    const { trades, errors } = matchTrades([
      buy("2026-01-01", "A", 100, 100),
      sell("2026-01-02", "A", 110, 100), // 정상 왕복거래
      buy("2026-01-05", "A", 100, 100),
      sell("2026-01-06", "A", 110, 150), // 보유수량 초과 매도(오류)
    ]);
    expect(trades.filter((t) => t.code === "A")).toEqual([]);
    expect(errors.length).toBe(1);
  });
});

// 지표 테스트용 최소 Trade 생성기 (basis별 pct와 보유일수만 의미 있음)
function mkTrade(net: number, days: number, month: string, code = "X"): Trade {
  return {
    code, name: code, open_date: `${month}-01`, close_date: `${month}-05`,
    avg_buy: 100, avg_sell: 100 * (1 + net / 100),
    gross_pct: net, net_pct: net, hold_days: days,
    gross_won: net, net_won: net,
    outcome: net > 0 ? "win" : "loss", month,
    buy_qty: 1, sell_qty: 1,
  };
}

describe("computeOverall", () => {
  it("승률·평균수익·평균손실·손익비·조정후·기대수익·유지일수", () => {
    const trades = [
      mkTrade(10, 5, "2026-01"),
      mkTrade(20, 10, "2026-01"),
      mkTrade(-5, 8, "2026-01"),
    ];
    const o = computeOverall(trades, "net");
    expect(o.trade_count).toBe(3);
    expect(o.win_count).toBe(2);
    expect(o.loss_count).toBe(1);
    expect(o.win_rate).toBe(66.67);
    expect(o.avg_win).toBe(15);
    expect(o.avg_loss).toBe(5); // 양수 크기
    expect(o.payoff_ratio).toBe(3); // 15/5
    expect(o.adj_payoff_ratio).toBe(6); // (15*2/3)/(5*1/3)
    expect(o.expectancy).toBe(8.33); // 2/3*15 - 1/3*5
    expect(o.max_win?.pct).toBe(20);
    expect(o.max_loss?.pct).toBe(5);
    expect(o.win_days).toBe(8); // round((5+10)/2)=8
    expect(o.loss_days).toBe(8);
  });

  it("거래 0건 → 모든 지표 null, 카운트 0", () => {
    const o = computeOverall([], "net");
    expect(o).toMatchObject({ win_rate: null, avg_win: null, avg_loss: null, payoff_ratio: null, trade_count: 0 });
  });

  it("수익거래만 있으면 avg_loss·payoff null, 손실거래만 있으면 avg_win·payoff null", () => {
    expect(computeOverall([mkTrade(10, 3, "2026-01")], "net").payoff_ratio).toBe(null);
    expect(computeOverall([mkTrade(-10, 3, "2026-01")], "net").payoff_ratio).toBe(null);
  });
});

import { computeMonthly } from "./scorecard";

describe("computeMonthly", () => {
  it("월별 행 + 평균행(월평균, 총거래=합계), 수익거래 0인 달은 null", () => {
    const trades = [
      mkTrade(10, 3, "2026-01", "A"),
      mkTrade(-4, 10, "2026-01", "B"),
      mkTrade(-5, 8, "2026-02", "C"), // 2월엔 수익거래 없음
    ];
    const m = computeMonthly(trades, "net");
    expect(m.rows).toHaveLength(2);

    const jan = m.rows[0];
    expect(jan.month).toBe("2026-01");
    expect(jan.avg_win).toBe(10);
    expect(jan.avg_loss).toBe(4);
    expect(jan.win_rate).toBe(50);
    expect(jan.trades).toBe(2);
    expect(jan.max_win).toBe(10);
    expect(jan.max_loss).toBe(4);
    expect(jan.win_days).toBe(3);
    expect(jan.loss_days).toBe(10);

    const feb = m.rows[1];
    expect(feb.avg_win).toBe(null);
    expect(feb.avg_loss).toBe(5);
    expect(feb.win_rate).toBe(0);
    expect(feb.max_win).toBe(null);
    expect(feb.win_days).toBe(null);
    expect(feb.loss_days).toBe(8);

    const avg = m.average;
    expect(avg.month).toBe("평균");
    expect(avg.trades).toBe(3); // 합계
    expect(avg.avg_win).toBe(10); // null 달 제외 → [10] 평균
    expect(avg.avg_loss).toBe(4.5); // [4,5] 평균
    expect(avg.win_rate).toBe(25); // [50,0] 평균
    expect(avg.max_loss).toBe(4.5);
    expect(avg.win_days).toBe(3); // [3] 평균
    expect(avg.loss_days).toBe(9); // [10,8] 평균
  });
});

describe("computeScorecard", () => {
  const params = { rr_target: 2, stop_loss_pct_default: -4, generated_at: "2026-07-05", strategy: "minervini" };

  it("net/gross 2뷰·open_positions·RBA·진단을 조립", () => {
    const sc = computeScorecard([
      buy("2026-01-01", "A", 100, 100, { stop: 90 }),
      sell("2026-01-10", "A", 130, 100), // 승 +30, 9일
      buy("2026-02-01", "B", 100, 100, { stop: 95 }), // 계획 -5%
      sell("2026-02-05", "B", 90, 100),  // 손 -10%, 위반, 4일
      buy("2026-03-01", "C", 100, 100),  // 미청산
    ], params);

    expect(sc.overall.net.trade_count).toBe(2);
    expect(sc.overall.gross.trade_count).toBe(2);
    expect(sc.monthly.net.rows).toHaveLength(2);
    expect(sc.open_positions).toHaveLength(1);
    expect(sc.open_positions[0].code).toBe("C");

    // RBA: 평균수익 30 → 권장 15, 기본 손절 4% < 15 → ok
    expect(sc.rba.avg_win_net).toBe(30);
    expect(sc.rba.recommended_max_stop_pct).toBe(15);
    expect(sc.rba.current_default_stop_pct).toBe(4);
    expect(sc.rba.status).toBe("ok");

    // 진단: 손절 위반 1건
    expect(sc.diagnostics.stop_violations).toBe(1);
    expect(sc.diagnostics.warnings.some((w) => w.includes("손절 규율 위반"))).toBe(true);

    expect(sc.generated_at).toBe("2026-07-05");
    expect(sc.strategy).toBe("minervini");
  });

  it("거래 0건이면 RBA status unknown", () => {
    const sc = computeScorecard([buy("2026-03-01", "C", 100, 100)], params);
    expect(sc.overall.net.trade_count).toBe(0);
    expect(sc.rba.status).toBe("unknown");
    expect(sc.rba.recommended_max_stop_pct).toBe(null);
  });

  it("기본 손절이 권장보다 넓으면 too_wide 경고", () => {
    // 평균수익 6 → 권장 3, 기본 손절 4 > 3 → too_wide
    const sc = computeScorecard([
      buy("2026-01-01", "A", 100, 100),
      sell("2026-01-05", "A", 106, 100),
    ], params);
    expect(sc.rba.status).toBe("too_wide");
    expect(sc.diagnostics.warnings.some((w) => w.includes("권장"))).toBe(true);
  });
});

describe("원 손익(net_won/gross_won/total_won)", () => {
  it("완결 거래의 net_won/gross_won", () => {
    const { trades } = matchTrades([
      buy("2026-07-01", "T", 100, 10, { fees: 10 }),
      sell("2026-07-02", "T", 120, 10, { fees: 12, tax: 24 }),
    ]);
    expect(trades[0].gross_won).toBe(200); // (120-100)*10
    expect(trades[0].net_won).toBe(154);   // (1200-36) - (1000+10)
  });
  it("손실 거래는 net_won < 0", () => {
    const { trades } = matchTrades([
      buy("2026-07-01", "L", 100, 10, { fees: 10 }),
      sell("2026-07-02", "L", 90, 10, { fees: 9, tax: 18 }),
    ]);
    expect(trades[0].gross_won).toBe(-100);
    expect(trades[0].net_won).toBe(-137); // (900-27) - (1000+10)
  });
  it("computeOverall.total_won: basis별 합계", () => {
    const { trades } = matchTrades([
      buy("2026-07-01", "T", 100, 10, { fees: 10 }),
      sell("2026-07-02", "T", 120, 10, { fees: 12, tax: 24 }),
      buy("2026-07-01", "L", 100, 10, { fees: 10 }),
      sell("2026-07-02", "L", 90, 10, { fees: 9, tax: 18 }),
    ]);
    expect(computeOverall(trades, "net").total_won).toBe(17);   // 154 - 137
    expect(computeOverall(trades, "gross").total_won).toBe(100); // 200 - 100
  });
  it("거래 0건이면 total_won === 0", () => {
    expect(computeOverall([], "net").total_won).toBe(0);
  });
});

// ── 손절 규율 판정 축 (26-08-21) ────────────────────────────────────────────
// 손절선(stop)은 '가격'으로 적히므로 비교 대상도 가격 기준 총수익률이어야 한다.
// 순수익률(수수료·세금 반영)과 비교하면 손절선을 지킨 거래도 왕복 비용만큼 위반으로 찍힌다.
describe("stop_violation 판정 축", () => {
  it("가격은 손절선 안인데 비용 때문에 순수익률만 넘은 경우 → 위반 아님", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 1000, 100, { stop: 950, fees: 1000 }), // 계획 -5%
      sell("2026-01-02", "A", 952, 100, { fees: 300 }),             // 가격 -4.8%
    ]);
    const t = trades[0];
    expect(t.gross_pct).toBe(-4.8);
    expect(t.net_pct).toBe(-6.04);
    expect(t.outcome).toBe("loss");
    expect(t.stop_violation).toBe(false);
  });

  it("가격 자체가 손절선을 넘겼으면 비용과 무관하게 위반", () => {
    const { trades } = matchTrades([
      buy("2026-01-01", "A", 1000, 100, { stop: 950, fees: 1000 }),
      sell("2026-01-02", "A", 900, 100, { fees: 300 }),             // 가격 -10%
    ]);
    expect(trades[0].gross_pct).toBe(-10);
    expect(trades[0].stop_violation).toBe(true);
  });

  it("손절가 없이 기본 손절폭으로 판정할 때도 가격 기준", () => {
    const { trades } = matchTrades(
      [
        buy("2026-01-01", "A", 1000, 100, { fees: 1000 }),
        sell("2026-01-02", "A", 952, 100, { fees: 300 }),
      ],
      -5,
    );
    expect(trades[0].stop_violation).toBe(false);
  });
});

// ── 같은 날 매수·매도: 배열 순서가 곧 장중 순서 (26-08-21) ──────────────────
// 체결 레코드에 시각이 없어 matchTrades 는 (날짜, 배열 인덱스)로만 정렬한다.
// 따라서 같은 날 안의 기록 순서는 데이터이며, 임의 재정렬은 집계를 조용히 망가뜨린다.
describe("같은 날 매수·매도 순서", () => {
  it("당일 매수→당일 매도(단타)는 보유일 0의 정상 왕복거래", () => {
    const { trades, open, errors } = matchTrades([
      buy("2026-01-05", "A", 100, 100),
      sell("2026-01-05", "A", 105, 100),
    ]);
    expect(errors).toEqual([]);
    expect(open).toEqual([]);
    expect(trades).toHaveLength(1);
    expect(trades[0].hold_days).toBe(0);
    expect(trades[0].gross_pct).toBe(5);
  });

  it("전량 청산 후 같은 날 재진입 → 왕복거래 1건 + 미청산 1건(합쳐지지 않는다)", () => {
    const { trades, open, errors } = matchTrades([
      buy("2026-01-05", "A", 100, 100),
      sell("2026-01-08", "A", 110, 100),
      buy("2026-01-08", "A", 112, 50),
    ]);
    expect(errors).toEqual([]);
    expect(trades).toHaveLength(1);
    expect(trades[0].close_date).toBe("2026-01-08");
    expect(open).toHaveLength(1);
    expect(open[0].qty).toBe(50);
    expect(open[0].open_date).toBe("2026-01-08");
  });

  it("당일 매수분을 이틀에 나눠 팔아도 오류가 아니다", () => {
    const { trades, errors } = matchTrades([
      buy("2026-01-05", "A", 100, 120),
      sell("2026-01-05", "A", 105, 70),
      sell("2026-01-06", "A", 108, 50),
    ]);
    expect(errors).toEqual([]);
    expect(trades).toHaveLength(1);
    expect(trades[0].sell_qty).toBe(120);
  });
});

// ── 데이터 오류 요약(화면 경고 배너용) (26-08-21) ───────────────────────────
describe("summarizeDataErrors", () => {
  it("오류가 없으면 null", () => {
    expect(summarizeDataErrors([])).toBeNull();
  });

  it("건수·영향 종목코드(첫 등장 순, 중복 제거)·원문을 담는다", () => {
    const s = summarizeDataErrors([
      "009150: 매도 수량이 보유수량 초과 (2026-07-01)",
      "086670: 매도 수량이 보유수량 초과 (2026-07-01)",
      "009150: 매도 수량이 보유수량 초과 (2026-07-02)",
    ]);
    expect(s).not.toBeNull();
    expect(s!.count).toBe(3);
    expect(s!.codes).toEqual(["009150", "086670"]);
    expect(s!.lines).toHaveLength(3);
  });

  it("코드를 못 읽는 형식이어도 건수는 세고 원문을 보존한다", () => {
    const s = summarizeDataErrors(["알 수 없는 오류"]);
    expect(s!.count).toBe(1);
    expect(s!.codes).toEqual([]);
    expect(s!.lines).toEqual(["알 수 없는 오류"]);
  });
});
