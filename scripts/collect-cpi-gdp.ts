/**
 * CPI/GDP 자동 수집 스크립트
 *
 * 데이터 소스:
 *   미국 CPI : FRED CPIAUCSL (St.Louis Fed) — API 키 불필요
 *   미국 GDP : FRED A191RL1Q225SBEA (분기 SAAR 성장률) — API 키 불필요
 *   한국 CPI : mods.go.kr 소비자물가지수 HTML 스크래핑 (통계청)
 *   한국 GDP : IMF WEO DataMapper API — API 키 불필요
 *             ※ 한국은행 ECOS API 키 발급 후 분기 데이터로 전환 예정
 *
 * 새 데이터가 현재 리포트보다 최신이면 public/data/ 아래 모든 리포트를 업데이트.
 * 변경 없으면 파일 수정 없이 종료.
 *
 * 실행: npx tsx scripts/collect-cpi-gdp.ts
 */
import fs from "fs";
import path from "path";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
const FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv";

// ─────────────────────────────────────────────
// 1. 미국 CPI (FRED CPIAUCSL)
// ─────────────────────────────────────────────

interface CpiData {
  날짜: string;
  전년동월대비: number;
  판단: string;
}

async function fetchUsCpi(): Promise<CpiData | null> {
  try {
    const res = await fetch(`${FRED_BASE}?id=CPIAUCSL`, {
      headers: { "User-Agent": UA },
    });
    if (!res.ok) return null;

    const lines = (await res.text()).trim().split("\n").slice(1); // skip header
    const data = lines
      .map((line) => {
        const [date, value] = line.split(",");
        return { date: date.trim(), value: parseFloat(value.trim()) };
      })
      .filter((d) => !isNaN(d.value))
      .sort((a, b) => a.date.localeCompare(b.date));

    // 최소 13개월 필요 (전년동월비 계산용)
    if (data.length < 13) return null;

    const latest = data[data.length - 1];
    const yearAgo = data[data.length - 13]; // 정확히 12개월 전
    const yoy = parseFloat((((latest.value / yearAgo.value) - 1) * 100).toFixed(2));

    return { 날짜: latest.date, 전년동월대비: yoy, 판단: getCpiJudgment(yoy) };
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────
// 2. 미국 GDP (FRED A191RL1Q225SBEA)
//    Real GDP, 전분기 대비 연율 성장률 (SAAR)
// ─────────────────────────────────────────────

interface GdpData {
  날짜: string;
  성장률: number;
  판단: string;
}

async function fetchUsGdp(): Promise<GdpData | null> {
  try {
    const res = await fetch(`${FRED_BASE}?id=A191RL1Q225SBEA`, {
      headers: { "User-Agent": UA },
    });
    if (!res.ok) return null;

    const lines = (await res.text()).trim().split("\n").slice(1);
    const data = lines
      .map((line) => {
        const [date, value] = line.split(",");
        return { date: date.trim(), value: parseFloat(value.trim()) };
      })
      .filter((d) => !isNaN(d.value))
      .sort((a, b) => a.date.localeCompare(b.date));

    if (data.length === 0) return null;

    const latest = data[data.length - 1];
    return {
      날짜: latest.date, // "YYYY-MM-01" (분기 첫 날)
      성장률: parseFloat(latest.value.toFixed(1)),
      판단: getGdpJudgment(latest.value),
    };
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────
// 3. 한국 CPI (mods.go.kr 스크래핑)
// ─────────────────────────────────────────────

async function fetchKrCpi(): Promise<CpiData | null> {
  try {
    const res = await fetch(
      "https://mods.go.kr/cpidtval.es?mid=b70201010000",
      { headers: { "User-Agent": UA } },
    );
    if (!res.ok) return null;
    const html = await res.text();

    // 테이블 전체 추출
    const tables = html.match(/<table[\s\S]*?<\/table>/gi) || [];

    for (const table of tables) {
      // "전년동월비" 행이 있는 테이블 탐색
      if (!table.includes("전년동월비") && !table.includes("전년동월")) continue;

      const rows = table.match(/<tr[\s\S]*?<\/tr>/gi) || [];

      let dateHeaders: string[] = [];
      let yoyRow: number[] = [];

      for (const row of rows) {
        const cells = (row.match(/<t[hd][^>]*>([\s\S]*?)<\/t[hd]>/gi) || [])
          .map((cell) =>
            cell
              .replace(/<[^>]+>/g, "")
              .replace(/&nbsp;/g, " ")
              .replace(/\s+/g, " ")
              .trim(),
          );

        if (cells.length === 0) continue;

        // 헤더 행: YYYY.MM 또는 'YYYY년MM월' 패턴 포함
        if (cells.some((c) => /\d{4}[.\s년]\s*\d{1,2}/.test(c))) {
          dateHeaders = cells;
          continue;
        }

        // 전년동월비 행
        if (/전년동월[비율]?/.test(cells[0])) {
          yoyRow = cells
            .slice(1)
            .map((c) => parseFloat(c.replace(/,/g, "")))
            .filter((v) => !isNaN(v));
        }
      }

      if (yoyRow.length === 0) continue;

      const latestValue = yoyRow[yoyRow.length - 1];

      // 날짜 파싱: 헤더 마지막 날짜 셀에서 추출
      let latestDate = "";
      if (dateHeaders.length > 0) {
        const lastHeader = dateHeaders[dateHeaders.length - 1];
        const m = lastHeader.match(/(\d{4})[.\s년]\s*(\d{1,2})/);
        if (m) {
          latestDate = `${m[1]}년 ${parseInt(m[2])}월`;
        }
      }

      return {
        날짜: latestDate,
        전년동월대비: parseFloat(latestValue.toFixed(1)),
        판단: getCpiJudgment(latestValue),
      };
    }

    return null;
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────
// 4. 한국 GDP (IMF WEO DataMapper API)
//    연간 실질 GDP 성장률
// ─────────────────────────────────────────────

async function fetchKrGdp(): Promise<GdpData | null> {
  try {
    const year = new Date().getFullYear();
    // 최근 3개년 요청 (최신 확정치 탐색)
    const url = `https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/KOR?periods=${year - 2},${year - 1},${year}`;
    const res = await fetch(url, { headers: { "User-Agent": UA } });
    if (!res.ok) return null;

    const json = await res.json() as {
      values?: { NGDP_RPCH?: { KOR?: Record<string, number> } };
    };

    const korData = json.values?.NGDP_RPCH?.KOR;
    if (!korData) return null;

    const years = Object.keys(korData)
      .filter((y) => korData[y] != null)
      .sort();
    if (years.length === 0) return null;

    const latestYear = years[years.length - 1];
    const value = parseFloat(korData[latestYear].toFixed(1));

    return {
      날짜: `${latestYear}년`,
      성장률: value,
      판단: getGdpJudgment(value),
    };
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────
// 판단 문구 (CPI / GDP)
// ─────────────────────────────────────────────

function getCpiJudgment(cpi: number): string {
  if (cpi < 0) return "🔵 디플레이션 — 경기 수축 위험";
  if (cpi < 1) return "🔵 물가 매우 낮음 — 경기 침체 우려";
  if (cpi < 2) return "🟢 물가 안정 — 금리 인하 여지 있음";
  if (cpi < 3) return "⚪ 물가 보통 — 중앙은행 목표 부근, 정책 여유 있음";
  if (cpi < 4) return "🟡 물가 상승 — 금리 인하 지연 우려";
  return "🔴 고물가 — 금리 인상 압박";
}

function getGdpJudgment(gdp: number): string {
  if (gdp < 0) return "🔴 마이너스 성장 — 경기 침체";
  if (gdp < 1) return "🟡 저성장 — 경기 침체 경계";
  if (gdp < 2) return "🟡 저성장 — 경기 둔화 조짐";
  if (gdp < 3) return "🟢 안정 성장";
  return "🟢 고성장 — 경기 양호";
}

// ─────────────────────────────────────────────
// 성장-물가 매트릭스 계산
//   GDP 임계값: 2%   (미만 = 저성장)
//   CPI 임계값: 3%   (이상 = 고물가)
// ─────────────────────────────────────────────

const GDP_THRESHOLD = 2.0;
const CPI_THRESHOLD = 3.0;

function calcMatrix(gdp: number, cpi: number) {
  const high = gdp >= GDP_THRESHOLD;
  const hot = cpi >= CPI_THRESHOLD;

  if (high && !hot)
    return { 위치: "고성장·저물가 (골디락스)", 해석: "최적 성장 환경. 경기 호황 속 물가 안정. 위험자산 선호 국면.", 사분면: 1 };
  if (high && hot)
    return { 위치: "고성장·고물가 (과열)", 해석: "경기 과열 구간. 중앙은행 금리 인상 압박. 채권·성장주 불리.", 사분면: 2 };
  if (!high && hot)
    return { 위치: "저성장·고물가 (스태그플레이션)", 해석: "가장 불리한 거시 환경. 정책 선택지 제한. 실물자산·단기채 유리.", 사분면: 3 };
  return { 위치: "저성장·저물가 (디플레이션 우려)", 해석: "경기 침체 우려 구간. 중앙은행 완화 정책 기대 가능.", 사분면: 4 };
}

// ─────────────────────────────────────────────
// 날짜 비교 헬퍼
// ─────────────────────────────────────────────

/** "2026년 3월" 형태를 YYYYMM 숫자로 변환 */
function parseKrDate(s: string): number {
  const m = s.match(/(\d{4})년\s*(\d{1,2})월/);
  return m ? parseInt(m[1]) * 100 + parseInt(m[2]) : 0;
}

/** "2025년" 형태를 연도 숫자로 변환 */
function parseKrYear(s: string): number {
  return parseInt(s.replace(/년.*/, "")) || 0;
}

// ─────────────────────────────────────────────
// 메인
// ─────────────────────────────────────────────

async function main() {
  const dataDir = path.join(process.cwd(), "public", "data");

  console.log("📊 CPI/GDP 자동 수집");
  console.log("─".repeat(55));

  // ── 데이터 수집 ──
  console.log("\n1️⃣  미국 CPI  (FRED CPIAUCSL)");
  const usCpi = await fetchUsCpi();
  console.log(usCpi
    ? `  ✅ ${usCpi.날짜} | YoY ${usCpi.전년동월대비}% | ${usCpi.판단}`
    : "  ❌ 수집 실패");

  console.log("\n2️⃣  미국 GDP  (FRED A191RL1Q225SBEA)");
  const usGdp = await fetchUsGdp();
  console.log(usGdp
    ? `  ✅ ${usGdp.날짜} | ${usGdp.성장률}% (SAAR) | ${usGdp.판단}`
    : "  ❌ 수집 실패");

  console.log("\n3️⃣  한국 CPI  (mods.go.kr)");
  const krCpi = await fetchKrCpi();
  console.log(krCpi
    ? `  ✅ ${krCpi.날짜} | YoY ${krCpi.전년동월대비}% | ${krCpi.판단}`
    : "  ❌ 수집 실패 — 직전 값 유지");

  console.log("\n4️⃣  한국 GDP  (IMF WEO API)");
  const krGdp = await fetchKrGdp();
  console.log(krGdp
    ? `  ✅ ${krGdp.날짜} | ${krGdp.성장률}% | ${krGdp.판단}`
    : "  ❌ 수집 실패 — 직전 값 유지");

  // ── 최신 리포트에서 기존 cpi_gdp 로드 ──
  const files = fs.readdirSync(dataDir)
    .filter((f) => /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
    .sort();

  if (files.length === 0) {
    console.error("\n❌ 리포트 파일 없음");
    process.exitCode = 1;
    return;
  }

  const prev = JSON.parse(
    fs.readFileSync(path.join(dataDir, files[files.length - 1]), "utf-8"),
  ).cpi_gdp as {
    us_cpi: CpiData;
    us_gdp: GdpData;
    kr_cpi: CpiData;
    kr_gdp: GdpData;
    matrix_us: ReturnType<typeof calcMatrix>;
    matrix_kr: ReturnType<typeof calcMatrix>;
  };

  // ── 새 데이터가 더 최신이면 교체, 아니면 직전 값 유지 ──
  const newUsCpi = usCpi && usCpi.날짜 > (prev.us_cpi?.날짜 ?? "") ? usCpi : prev.us_cpi;
  const newUsGdp = usGdp && usGdp.날짜 > (prev.us_gdp?.날짜 ?? "") ? usGdp : prev.us_gdp;

  const newKrCpi = krCpi && parseKrDate(krCpi.날짜) > parseKrDate(prev.kr_cpi?.날짜 ?? "0년 0월")
    ? krCpi
    : prev.kr_cpi;

  const newKrGdp = krGdp && parseKrYear(krGdp.날짜) >= parseKrYear(prev.kr_gdp?.날짜 ?? "0년")
    ? krGdp
    : prev.kr_gdp;

  // ── 매트릭스 재계산 ──
  const newCpiGdp = {
    us_cpi: newUsCpi,
    us_gdp: newUsGdp,
    kr_cpi: newKrCpi,
    kr_gdp: newKrGdp,
    matrix_us: calcMatrix(newUsGdp.성장률, newUsCpi.전년동월대비),
    matrix_kr: calcMatrix(newKrGdp.성장률, newKrCpi.전년동월대비),
  };

  // ── 변경 여부 확인 ──
  const prevStr = JSON.stringify({
    us_cpi: prev.us_cpi,
    us_gdp: prev.us_gdp,
    kr_cpi: prev.kr_cpi,
    kr_gdp: prev.kr_gdp,
  });
  const newStr = JSON.stringify({
    us_cpi: newCpiGdp.us_cpi,
    us_gdp: newCpiGdp.us_gdp,
    kr_cpi: newCpiGdp.kr_cpi,
    kr_gdp: newCpiGdp.kr_gdp,
  });

  if (prevStr === newStr) {
    console.log("\n✅ 데이터 변경 없음 — 업데이트 불필요");
    return;
  }

  // ── 모든 리포트 JSON 업데이트 ──
  console.log(`\n📝 ${files.length}개 리포트 cpi_gdp 업데이트 중...`);
  for (const file of files) {
    const filePath = path.join(dataDir, file);
    const report = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    report.cpi_gdp = newCpiGdp;
    fs.writeFileSync(filePath, JSON.stringify(report, null, 2) + "\n", "utf-8");
  }

  // ── 결과 요약 ──
  console.log("─".repeat(55));
  console.log("📊 업데이트 결과:");
  console.log(`  🇺🇸 CPI : ${newCpiGdp.us_cpi.날짜}  →  YoY ${newCpiGdp.us_cpi.전년동월대비}%`);
  console.log(`  🇺🇸 GDP : ${newCpiGdp.us_gdp.날짜}  →  ${newCpiGdp.us_gdp.성장률}%`);
  console.log(`  🇰🇷 CPI : ${newCpiGdp.kr_cpi.날짜}  →  YoY ${newCpiGdp.kr_cpi.전년동월대비}%`);
  console.log(`  🇰🇷 GDP : ${newCpiGdp.kr_gdp.날짜}  →  ${newCpiGdp.kr_gdp.성장률}%`);
  console.log(`  🇺🇸 Matrix : Q${newCpiGdp.matrix_us.사분면} ${newCpiGdp.matrix_us.위치}`);
  console.log(`  🇰🇷 Matrix : Q${newCpiGdp.matrix_kr.사분면} ${newCpiGdp.matrix_kr.위치}`);
}

main().catch((err) => {
  console.error("스크립트 실행 실패:", err);
  process.exitCode = 1;
});
