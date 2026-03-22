import fs from "fs";
import path from "path";

export interface Indicator {
  name: string;
  value: number;
  change: number;
  weekly_change: number;
  trend: string;
  comment: string;
  timeseries?: { 날짜: string; 종가: number }[];
  error?: boolean;
}

export interface ReportData {
  meta: { date: string; weekday: string; generated_at: string };
  briefing: string;
  scenario: { 코드: string; 시나리오: string; 해석: string; 대응: string };
  indicators: {
    korea: Indicator[];
    us: Indicator[];
    fx: Indicator[];
    bonds: Indicator[];
    commodities: Indicator[];
  };
  spread: { 금리차: number; 상태: string; "10년물": number; "3개월물": number };
  causal_chain: string;
  investment_direction: string;
  news: { 제목: string; 링크: string; 출처: string; 날짜: string }[];
  cpi_gdp: {
    us_cpi: { 날짜?: string; 전년동월대비?: number; 판단?: string };
    us_gdp: { 날짜?: string; 성장률?: number; 판단?: string };
    kr_cpi: { 날짜?: string; 전년동월대비?: number; 판단?: string };
    kr_gdp: { 날짜?: string; 성장률?: number; 판단?: string };
    matrix_us: { 위치: string; 해석: string; 사분면?: number };
    matrix_kr: { 위치: string; 해석: string; 사분면?: number };
  };
  divergence: string;
  historical: {
    name: string;
    current: number;
    unit: string;
    all_high: number;
    all_low: number;
    percentile: number;
    judgment: string;
    periods: Record<string, { 시작값: number; 최고: number; 최저: number; 변동률: number }>;
  }[];
  asset_recommendation: string;
  longterm_charts: {
    name: string;
    unit: string;
    start_year: string;
    end_year: string;
    timeseries: { 날짜: string; 종가: number }[];
  }[];
}

const DATA_DIR = path.join(process.cwd(), "public", "data");

/**
 * 특정 날짜의 리포트를 가져온다.
 * date가 없으면 가장 최신 리포트를 반환한다.
 */
export function getReportData(date?: string): ReportData | null {
  try {
    if (date) {
      const filePath = path.join(DATA_DIR, `${date}.json`);
      const raw = fs.readFileSync(filePath, "utf-8");
      return JSON.parse(raw) as ReportData;
    }

    // 날짜 미지정: 가장 최신 파일
    const dates = getReportDates();
    if (dates.length === 0) return null;
    const latest = dates[0]; // 내림차순 정렬됨
    const filePath = path.join(DATA_DIR, `${latest}.json`);
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as ReportData;
  } catch {
    return null;
  }
}

/**
 * 저장된 모든 리포트 날짜 목록을 반환한다. (최신순)
 */
export function getReportDates(): string[] {
  try {
    const files = fs.readdirSync(DATA_DIR);
    return files
      .filter((f) => f.endsWith(".json") && f !== "latest.json" && f !== "calculator.json" && f !== "calculator-archive.json" && /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
      .map((f) => f.replace(".json", ""))
      .sort((a, b) => b.localeCompare(a)); // 최신순
  } catch {
    return [];
  }
}
