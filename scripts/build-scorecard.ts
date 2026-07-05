/**
 * 미너비니 정산표 CLI (C단계)
 * public/data/scorecard-fills.json 읽기 → computeScorecard → 터미널 출력 + scorecard.json 저장
 * 실행: npx tsx scripts/build-scorecard.ts
 */
import fs from "fs";
import path from "path";
import { computeScorecard, type Fill } from "../src/lib/scorecard";

const DATA = path.join(process.cwd(), "public", "data");
const IN = path.join(DATA, "scorecard-fills.json");
const OUT = path.join(DATA, "scorecard.json");

const pct = (v: number | null) => (v == null ? "-" : `${v.toFixed(2)}%`);
const num = (v: number | null) => (v == null ? "-" : String(v));

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function main() {
  const raw = JSON.parse(fs.readFileSync(IN, "utf-8"));
  const fills: Fill[] = raw.fills ?? [];
  const sc = computeScorecard(fills, {
    rr_target: raw.rr_target ?? 2,
    stop_loss_pct_default: raw.stop_loss_pct_default ?? -4,
    generated_at: today(),
    strategy: raw.strategy ?? "minervini",
  });

  fs.writeFileSync(OUT, JSON.stringify(sc, null, 2), "utf-8");

  const o = sc.overall.net;
  console.log("\n===== 트레이딩 요약 (순수익 기준, 전체) =====");
  if (o.trade_count === 0) {
    console.log("아직 청산된 거래가 없습니다. (열린 포지션 " + sc.open_positions.length + "건)");
  } else {
    console.log(`거래수 ${o.trade_count}  승 ${o.win_count}  패 ${o.loss_count}`);
    console.log(`승률 ${pct(o.win_rate)}  평균수익 ${pct(o.avg_win)}  평균손실 ${pct(o.avg_loss)}`);
    console.log(`성공/실패 비율 ${num(o.payoff_ratio)}  조정후 ${num(o.adj_payoff_ratio)}  기대수익 ${pct(o.expectancy)}`);
    console.log(`수익유지일 ${num(o.win_days)}  손실유지일 ${num(o.loss_days)}`);
    console.log(`\nRBA 권장 최대 손절폭: ${pct(sc.rba.recommended_max_stop_pct)} (현재 기본 ${sc.rba.current_default_stop_pct}%, ${sc.rba.status})`);

    console.log("\n----- 월별 확인표 (순수익) -----");
    console.log("월\t평균수익\t평균손실\t승률\t거래\t최대수익\t최대손실\t수익일\t손실일");
    for (const r of sc.monthly.net.rows) {
      console.log(`${r.month}\t${pct(r.avg_win)}\t${pct(r.avg_loss)}\t${pct(r.win_rate)}\t${r.trades}\t${pct(r.max_win)}\t${pct(r.max_loss)}\t${num(r.win_days)}\t${num(r.loss_days)}`);
    }
    const a = sc.monthly.net.average;
    console.log(`평균\t${pct(a.avg_win)}\t${pct(a.avg_loss)}\t${pct(a.win_rate)}\t${a.trades}\t${pct(a.max_win)}\t${pct(a.max_loss)}\t${num(a.win_days)}\t${num(a.loss_days)}`);
  }

  if (sc.diagnostics.warnings.length) {
    console.log("\n⚠️ 진단:");
    for (const w of sc.diagnostics.warnings) console.log("  - " + w);
  }
  if (sc.errors.length) {
    console.log("\n❗ 데이터 오류:");
    for (const e of sc.errors) console.log("  - " + e);
  }
  console.log(`\n저장됨: ${OUT}`);
}

main();
