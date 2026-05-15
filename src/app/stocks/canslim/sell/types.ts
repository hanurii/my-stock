// 매도 시스템 공통 타입 (scripts/compute-sell-signals.ts 출력과 1:1 매핑)

export interface Verdict {
  verdict: "HOLD" | "BAD_ENTRY" | "WATCH" | "TRIM" | "SELL";
  reasons: string[];
}

export interface BreakoutQuality {
  has_valid_base: boolean;
  base_left_high_date: string | null;
  base_left_high_price: number | null;
  base_low_price: number | null;
  base_depth_pct: number | null;
  base_days: number | null;
  pivot_price: number | null;
  vs_pivot_pct: number | null;
  within_5pct_of_pivot: boolean;
  no_base_reason: string | null;
}

export interface EntryQuality {
  entry_date: string;
  entry_close: number | null;
  entry_high: number | null;
  entry_low: number | null;
  entry_volume: number | null;
  vs_close_pct: number | null;
  vs_high_ratio: number | null;
  avg_volume_60d: number | null;
  volume_ratio: number | null;
  prior_high_52w: number | null;
  prior_high_52w_date: string | null;
  vs_prior_high_ratio: number | null;
  checks: {
    chased_intraday_high: boolean;
    volume_surge_50pct: boolean;
    near_breakout: boolean;
  };
  breakout: BreakoutQuality;
  grade: {
    label: "정확한 진입" | "부분 통과" | "잘못된 진입";
    book_checks_passed: number;
    book_checks_total: number;
  };
}

export interface StrategyEval {
  cut_loss_price: number;
  take_profit_1_price: number;
  take_profit_2_price: number;
  add_buy_limit_price: number;
  can_add_buy: boolean;
  rule_checks: {
    cut_loss_hit: boolean;
    take_profit_1_hit: boolean;
    take_profit_2_hit: boolean;
    add_buy_blocked: boolean;
  };
  entry_quality: EntryQuality | null;
}

export interface SellHoldingResult {
  code: string;
  name: string;
  sector?: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  profit_pct: number;
  eval_amount: number;
  position_start_date: string | null;
  holding_days: number;
  holding_weeks: number;
  high_price?: number;
  high_price_date?: string;
  ma50: number | null;
  ma200: number | null;
  strategy: StrategyEval;
  strategy_verdict: Verdict;
}

export interface SellSignalsOutput {
  generated_at: string;
  target_codes: string[];
  holdings: SellHoldingResult[];
}
