// Step 1: 점-시점(2025-11-25) L 점수 + 신고가 대비 + 시총 + 1년 수익률 universe 전체 계산
// 출력: research/oneil-model-book/_asof_2025-11-25_l_marcap.json
//
// 점-시점 안전장치:
//  - 종가 배열은 date 기준 idx_asof 이하만 사용
//  - 시총 = close[idx_asof] × shares (현재 주식수로 근사, 분할·증자 무시)
//  - L 점수 정의: KOSPI 시총 상위 300종 모집단 + 추가종목으로 1년 수익률 백분위(1~99)
//    fetch_l_rs.py 의 정의 그대로 포팅 (점-시점 시총 기준)

const fs = require('fs');
const path = require('path');

const ROOT = 'C:/Users/hanul/playground/my-stock';
const ASOF = '2025-11-25';

const prices = require(path.join(ROOT, 'research/oneil-model-book/cycles/c2024-12/_universe_prices_5y.json'));
const shares = require(path.join(ROOT, 'research/oneil-model-book/_universe_shares.json'));
const market = require(path.join(ROOT, 'research/oneil-model-book/_universe_market.json'));
const candidates = require(path.join(ROOT, 'public/data/can-slim-candidates.json'));

// 종목명·시장 lookup
const meta = {};
for (const c of candidates.candidates) {
  meta[c.code] = { name: c.name, market: c.market };
}

// universe = prices 캐시에 들어있는 모든 종목
const universe = Object.keys(prices);
console.log(`Universe size: ${universe.length}`);

// 점-시점 계산
const rows = [];
const TRADING_DAYS = 252;
let missing = 0;

for (const code of universe) {
  const px = prices[code];
  if (!px || !px.d || !px.c || px.d.length < 252) { missing++; continue; }
  const ds = px.d;
  const cs = px.c;

  // idx_asof: ds[i] <= ASOF 최대 i
  let idx = -1;
  for (let i = ds.length - 1; i >= 0; i--) {
    if (ds[i] <= ASOF) { idx = i; break; }
  }
  if (idx < 252) { missing++; continue; }

  const close_asof = cs[idx];
  if (!close_asof || close_asof <= 0) { missing++; continue; }

  // 1년 전 종가 (= idx - 252)
  const close_1y_ago = cs[idx - 252];
  if (!close_1y_ago || close_1y_ago <= 0) { missing++; continue; }
  const return_1y_pct = (close_asof / close_1y_ago - 1) * 100;

  // 52주(252일) 신고가 대비
  const window = cs.slice(Math.max(0, idx - 251), idx + 1);
  const high52 = Math.max(...window);
  const pct_from_high = (close_asof / high52 - 1) * 100;

  // 점-시점 시총 (억): close × shares / 1e8
  const sh = shares[code];
  const market_cap_eok = sh && sh > 0 ? Math.round((close_asof * sh) / 1e8) : null;

  rows.push({
    code,
    name: meta[code]?.name || '?',
    market: meta[code]?.market || market[code] || '?',
    close_asof,
    return_1y_pct: +return_1y_pct.toFixed(2),
    high_52w: high52,
    pct_from_52w_high: +pct_from_high.toFixed(2),
    market_cap_eok,
    idx_asof: idx,
    date_asof: ds[idx],
  });
}

console.log(`유효 종목: ${rows.length}, 미달: ${missing}`);

// L 점수 계산: KOSPI 시총 상위 300 모집단 (점-시점 시총 기준)
const kospi_sorted_by_mcap = rows
  .filter((r) => r.market === 'KOSPI' && r.market_cap_eok)
  .sort((a, b) => b.market_cap_eok - a.market_cap_eok);
const universe_codes = new Set(kospi_sorted_by_mcap.slice(0, 300).map((r) => r.code));

// 모집단 1년 수익률 정렬 → 백분위
const pop = rows.filter((r) => universe_codes.has(r.code))
  .sort((a, b) => a.return_1y_pct - b.return_1y_pct);
const n = pop.length;
console.log(`KOSPI 시총 상위 300 모집단(점-시점): ${n}개`);

const rs_by_code = {};
for (let i = 0; i < n; i++) {
  const rs = Math.round(1 + 98 * i / (n - 1));
  rs_by_code[pop[i].code] = rs;
}

// 모집단 외 종목도 같은 분포에 매핑 (백분위 estimation)
for (const r of rows) {
  if (rs_by_code[r.code] !== undefined) continue;
  const target = r.return_1y_pct;
  let lower = 0;
  for (const pr of pop) if (pr.return_1y_pct < target) lower++;
  const rs = Math.round(1 + 98 * lower / (n - 1));
  rs_by_code[r.code] = Math.max(1, Math.min(99, rs));
}

// 결과 출력
const out = rows.map((r) => ({
  ...r,
  l_score: rs_by_code[r.code] ?? 0,
  in_kospi_top300: universe_codes.has(r.code),
}));

const outPath = path.join(ROOT, 'research/oneil-model-book/_asof_2025-11-25_l_marcap.json');
fs.writeFileSync(outPath, JSON.stringify({
  asof: ASOF,
  universe_size: out.length,
  kospi_top300_size: n,
  rows: out,
}, null, 2));
console.log(`저장: ${outPath} (${out.length} rows)`);

// 점검: 상위 L 5개, 상위 시총 5개
const top_l = out.filter(r=>r.in_kospi_top300).sort((a,b)=>b.l_score-a.l_score).slice(0,10);
console.log('\nL 점수 상위 10 (모집단 내):');
for (const r of top_l) {
  console.log(`  ${r.code} ${r.name.padEnd(20)} L=${r.l_score} 1Y=${r.return_1y_pct}% 신고가대비=${r.pct_from_52w_high}% 시총=${r.market_cap_eok.toLocaleString()}억`);
}
