import { describe, it, expect } from "vitest";
import { matchTrades, type Fill } from "./scorecard";

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
