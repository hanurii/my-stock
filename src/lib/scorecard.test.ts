import { describe, it, expect } from "vitest";
import { matchTrades, type Fill } from "./scorecard";
import { computeOverall, type Trade } from "./scorecard";

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
