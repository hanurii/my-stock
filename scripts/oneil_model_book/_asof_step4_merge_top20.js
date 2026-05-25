// Step 4: 4축 점-시점 합산 (C·A·N제외·S·L) → top 20 잠정 추출
// 후보 = 점-시점 C 게이트 통과 종목 (ranking 페이지 정의와 동일)
// 합산 = C + A + S + L (4축, 원본 점수 단순 합)
//   - C: 점-시점 (Step 2 산출)
//   - A: 점-시점 (Step 2 산출)
//   - S: 오늘 기준 (can-slim-s-candidates.json, 정밀도 절충)
//   - L: 점-시점 (Step 1 산출, KOSPI 시총 상위 300 모집단)
//
// 출력: research/oneil-model-book/_asof_2025-11-25_top20.json

const fs = require('fs');
const path = require('path');

const ROOT = 'C:/Users/hanul/playground/my-stock';

const lmar = require(path.join(ROOT, 'research/oneil-model-book/_asof_2025-11-25_l_marcap.json'));
const ca = require(path.join(ROOT, 'research/oneil-model-book/_asof_2025-11-25_c_a.json'));
const sData = require(path.join(ROOT, 'public/data/can-slim-s-candidates.json'));

// lookup 구축
const lByCode = Object.fromEntries(lmar.rows.map((r) => [r.code, r]));
const caByCode = Object.fromEntries(ca.rows.map((r) => [r.code, r]));
const sByCode = Object.fromEntries(sData.candidates.map((c) => [c.code, c]));

// 후보 = 점-시점 C 게이트 통과 + L 점수 산출 가능
const cands = ca.rows.filter((r) => r.c_passes_gate);
console.log(`점-시점 C 게이트 통과: ${cands.length}`);

const rows = [];
for (const cr of cands) {
  const l = lByCode[cr.code];
  const s = sByCode[cr.code];
  if (!l) continue;  // 가격 캐시 없으면 제외

  const cScore = cr.c_score || 0;
  const aScore = cr.a_score || 0;
  const lScore = l.l_score || 0;
  const sScore = s?.s_score || 0;

  const total4 = cScore + aScore + sScore + lScore;
  rows.push({
    code: cr.code,
    name: cr.name,
    market: cr.market,
    market_cap_eok: l.market_cap_eok,
    close_asof: l.close_asof,
    pct_from_52w_high: l.pct_from_52w_high,
    return_1y_pct: l.return_1y_pct,
    c_score: cScore,
    c_tier: cr.c_tier,
    c_latest_quarter: cr.c_latest_quarter,
    c_yoy: cr.c_yoy_pct,
    c_sales_yoy: cr.c_sales_yoy_pct,
    a_score: aScore,
    a_track: cr.a_track,
    a_grade: cr.a_grade,
    a_latest_annual: cr.a_latest_annual,
    s_score: sScore,
    s_basis_today: s ? true : false,  // 오늘 기준 메타
    l_score: lScore,
    total_4axis: total4,
  });
}

rows.sort((a, b) => b.total_4axis - a.total_4axis);

const top20 = rows.slice(0, 20);
console.log(`\nTop 20 (4축 C+A+S+L 합산):`);
console.log('순  code   name              시장  시총(억)   C     A    S    L   합산  신고대비%  1Y%');
console.log('─'.repeat(110));
for (let i = 0; i < top20.length; i++) {
  const r = top20[i];
  console.log(
    `${(i + 1).toString().padStart(2)} ${r.code} ${(r.name||'').padEnd(18)} ${r.market.padEnd(6)} ${(r.market_cap_eok||0).toLocaleString().padStart(9)} ${r.c_score.toFixed(0).padStart(4)} ${r.a_score.toString().padStart(4)} ${r.s_score.toString().padStart(4)} ${r.l_score.toString().padStart(4)} ${r.total_4axis.toFixed(0).padStart(5)} ${(r.pct_from_52w_high+'%').padStart(8)} ${(r.return_1y_pct+'%').padStart(7)}`,
  );
}

const outPath = path.join(ROOT, 'research/oneil-model-book/_asof_2025-11-25_top20.json');
fs.writeFileSync(outPath, JSON.stringify({
  asof: '2025-11-25',
  c_gate_passers: cands.length,
  top20,
  all_rows: rows,
}, null, 2));
console.log(`\n저장: ${outPath}`);
