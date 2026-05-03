/**
 * 메가캡 우량주 모니터 — 유니버스 후보 풀
 *
 * Yahoo Finance 티커 기준. 시장별 시총 상위 자동 선정의 1차 후보.
 * 분기별 1회 수동 갱신 권장. 새 메가캡 등장 시 추가, 합병/상폐 시 제거.
 */

export interface UniverseCandidate {
  ticker: string;        // Yahoo Finance 티커
  name_kr: string;       // 한국어 표시명
  market: "US" | "KR" | "JP" | "CN" | "EU" | "OTHER";
  currency: "USD" | "KRW" | "JPY" | "CNY" | "HKD" | "EUR" | "TWD" | "INR" | "GBP";
  sector?: string;       // 대분류 섹터
}

// ── 시장별 쿼터 (총 100개) ──
export const MARKET_QUOTAS: Record<UniverseCandidate["market"], number> = {
  US: 50,
  KR: 15,
  JP: 15,
  CN: 10,
  EU: 5,
  OTHER: 5,
};

// ── 미국 메가캡 후보 (시총 큰 기업 위주) ──
const US: UniverseCandidate[] = [
  { ticker: "AAPL", name_kr: "애플", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "MSFT", name_kr: "마이크로소프트", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "GOOGL", name_kr: "알파벳(A)", market: "US", currency: "USD", sector: "Communication" },
  { ticker: "AMZN", name_kr: "아마존", market: "US", currency: "USD", sector: "Consumer Discretionary" },
  { ticker: "NVDA", name_kr: "엔비디아", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "META", name_kr: "메타", market: "US", currency: "USD", sector: "Communication" },
  { ticker: "BRK-B", name_kr: "버크셔해서웨이(B)", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "V", name_kr: "비자", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "MA", name_kr: "마스터카드", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "JPM", name_kr: "JP모건", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "JNJ", name_kr: "존슨앤드존슨", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "WMT", name_kr: "월마트", market: "US", currency: "USD", sector: "Consumer Staples" },
  { ticker: "PG", name_kr: "P&G", market: "US", currency: "USD", sector: "Consumer Staples" },
  { ticker: "UNH", name_kr: "유나이티드헬스", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "HD", name_kr: "홈디포", market: "US", currency: "USD", sector: "Consumer Discretionary" },
  { ticker: "KO", name_kr: "코카콜라", market: "US", currency: "USD", sector: "Consumer Staples" },
  { ticker: "PEP", name_kr: "펩시코", market: "US", currency: "USD", sector: "Consumer Staples" },
  { ticker: "COST", name_kr: "코스트코", market: "US", currency: "USD", sector: "Consumer Staples" },
  { ticker: "AVGO", name_kr: "브로드컴", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "XOM", name_kr: "엑손모빌", market: "US", currency: "USD", sector: "Energy" },
  { ticker: "ORCL", name_kr: "오라클", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "MCD", name_kr: "맥도날드", market: "US", currency: "USD", sector: "Consumer Discretionary" },
  { ticker: "MRK", name_kr: "머크", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "BAC", name_kr: "뱅크오브아메리카", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "ABBV", name_kr: "애브비", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "NKE", name_kr: "나이키", market: "US", currency: "USD", sector: "Consumer Discretionary" },
  { ticker: "CRM", name_kr: "세일즈포스", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "ACN", name_kr: "액센추어", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "CSCO", name_kr: "시스코", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "PFE", name_kr: "화이자", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "INTC", name_kr: "인텔", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "WFC", name_kr: "웰스파고", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "NFLX", name_kr: "넷플릭스", market: "US", currency: "USD", sector: "Communication" },
  { ticker: "AMD", name_kr: "AMD", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "TXN", name_kr: "텍사스인스트루먼트", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "IBM", name_kr: "IBM", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "MS", name_kr: "모건스탠리", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "CMCSA", name_kr: "컴캐스트", market: "US", currency: "USD", sector: "Communication" },
  { ticker: "ADBE", name_kr: "어도비", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "GS", name_kr: "골드만삭스", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "RTX", name_kr: "RTX", market: "US", currency: "USD", sector: "Industrials" },
  { ticker: "GE", name_kr: "GE에어로스페이스", market: "US", currency: "USD", sector: "Industrials" },
  { ticker: "AMGN", name_kr: "암젠", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "BMY", name_kr: "BMS", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "BA", name_kr: "보잉", market: "US", currency: "USD", sector: "Industrials" },
  { ticker: "CAT", name_kr: "캐터필러", market: "US", currency: "USD", sector: "Industrials" },
  { ticker: "AXP", name_kr: "아메리칸익스프레스", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "BLK", name_kr: "블랙록", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "SCHW", name_kr: "찰스슈왑", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "CVX", name_kr: "셰브론", market: "US", currency: "USD", sector: "Energy" },
  { ticker: "LIN", name_kr: "린데", market: "US", currency: "USD", sector: "Materials" },
  { ticker: "NOW", name_kr: "서비스나우", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "DHR", name_kr: "다나허", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "BKNG", name_kr: "부킹홀딩스", market: "US", currency: "USD", sector: "Consumer Discretionary" },
  { ticker: "ELV", name_kr: "엘리번스헬스", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "SBUX", name_kr: "스타벅스", market: "US", currency: "USD", sector: "Consumer Discretionary" },
  { ticker: "MDT", name_kr: "메드트로닉", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "ISRG", name_kr: "인튜이티브서지컬", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "INTU", name_kr: "인튜이트", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "AMT", name_kr: "아메리칸타워", market: "US", currency: "USD", sector: "Real Estate" },
  { ticker: "GILD", name_kr: "길리어드", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "MMC", name_kr: "마쉬앤맥레넌", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "ZTS", name_kr: "조에티스", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "VRTX", name_kr: "버텍스", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "REGN", name_kr: "리제네론", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "LRCX", name_kr: "램리서치", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "ADI", name_kr: "아날로그디바이스", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "KLAC", name_kr: "KLA", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "EQIX", name_kr: "에퀴닉스", market: "US", currency: "USD", sector: "Real Estate" },
  { ticker: "ANET", name_kr: "아리스타네트웍스", market: "US", currency: "USD", sector: "Technology" },
  { ticker: "ADP", name_kr: "ADP", market: "US", currency: "USD", sector: "Industrials" },
  { ticker: "TJX", name_kr: "TJX", market: "US", currency: "USD", sector: "Consumer Discretionary" },
  { ticker: "PGR", name_kr: "프로그레시브", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "ICE", name_kr: "인터컨티넨탈익스체인지", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "MO", name_kr: "알트리아", market: "US", currency: "USD", sector: "Consumer Staples" },
  { ticker: "MCO", name_kr: "무디스", market: "US", currency: "USD", sector: "Financials" },
  { ticker: "BDX", name_kr: "벡톤디킨슨", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "MMM", name_kr: "3M", market: "US", currency: "USD", sector: "Industrials" },
  { ticker: "SYK", name_kr: "스트라이커", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "LLY", name_kr: "일라이릴리", market: "US", currency: "USD", sector: "Healthcare" },
  { ticker: "TSLA", name_kr: "테슬라", market: "US", currency: "USD", sector: "Consumer Discretionary" },
  { ticker: "PLTR", name_kr: "팔란티어", market: "US", currency: "USD", sector: "Technology" },
];

// ── 한국 메가캡 후보 (KOSPI 시총 상위) ──
const KR: UniverseCandidate[] = [
  { ticker: "005930.KS", name_kr: "삼성전자", market: "KR", currency: "KRW", sector: "Technology" },
  { ticker: "000660.KS", name_kr: "SK하이닉스", market: "KR", currency: "KRW", sector: "Technology" },
  { ticker: "373220.KS", name_kr: "LG에너지솔루션", market: "KR", currency: "KRW", sector: "Industrials" },
  { ticker: "207940.KS", name_kr: "삼성바이오로직스", market: "KR", currency: "KRW", sector: "Healthcare" },
  { ticker: "005380.KS", name_kr: "현대차", market: "KR", currency: "KRW", sector: "Consumer Discretionary" },
  { ticker: "005935.KS", name_kr: "삼성전자우", market: "KR", currency: "KRW", sector: "Technology" },
  { ticker: "000270.KS", name_kr: "기아", market: "KR", currency: "KRW", sector: "Consumer Discretionary" },
  { ticker: "035420.KS", name_kr: "NAVER", market: "KR", currency: "KRW", sector: "Communication" },
  { ticker: "035720.KS", name_kr: "카카오", market: "KR", currency: "KRW", sector: "Communication" },
  { ticker: "105560.KS", name_kr: "KB금융", market: "KR", currency: "KRW", sector: "Financials" },
  { ticker: "055550.KS", name_kr: "신한지주", market: "KR", currency: "KRW", sector: "Financials" },
  { ticker: "028260.KS", name_kr: "삼성물산", market: "KR", currency: "KRW", sector: "Industrials" },
  { ticker: "068270.KS", name_kr: "셀트리온", market: "KR", currency: "KRW", sector: "Healthcare" },
  { ticker: "051910.KS", name_kr: "LG화학", market: "KR", currency: "KRW", sector: "Materials" },
  { ticker: "006400.KS", name_kr: "삼성SDI", market: "KR", currency: "KRW", sector: "Industrials" },
  { ticker: "012330.KS", name_kr: "현대모비스", market: "KR", currency: "KRW", sector: "Consumer Discretionary" },
  { ticker: "015760.KS", name_kr: "한국전력", market: "KR", currency: "KRW", sector: "Utilities" },
  { ticker: "086790.KS", name_kr: "하나금융지주", market: "KR", currency: "KRW", sector: "Financials" },
  { ticker: "003670.KS", name_kr: "포스코퓨처엠", market: "KR", currency: "KRW", sector: "Materials" },
  { ticker: "096770.KS", name_kr: "SK이노베이션", market: "KR", currency: "KRW", sector: "Energy" },
  { ticker: "009150.KS", name_kr: "삼성전기", market: "KR", currency: "KRW", sector: "Technology" },
  { ticker: "010130.KS", name_kr: "고려아연", market: "KR", currency: "KRW", sector: "Materials" },
  { ticker: "066570.KS", name_kr: "LG전자", market: "KR", currency: "KRW", sector: "Consumer Discretionary" },
  { ticker: "017670.KS", name_kr: "SK텔레콤", market: "KR", currency: "KRW", sector: "Communication" },
  { ticker: "030200.KS", name_kr: "KT", market: "KR", currency: "KRW", sector: "Communication" },
];

// ── 일본 메가캡 후보 ──
const JP: UniverseCandidate[] = [
  { ticker: "7203.T", name_kr: "토요타", market: "JP", currency: "JPY", sector: "Consumer Discretionary" },
  { ticker: "6758.T", name_kr: "소니", market: "JP", currency: "JPY", sector: "Technology" },
  { ticker: "6861.T", name_kr: "키엔스", market: "JP", currency: "JPY", sector: "Industrials" },
  { ticker: "8306.T", name_kr: "미쓰비시UFJ", market: "JP", currency: "JPY", sector: "Financials" },
  { ticker: "9984.T", name_kr: "소프트뱅크그룹", market: "JP", currency: "JPY", sector: "Communication" },
  { ticker: "9983.T", name_kr: "패스트리테일링", market: "JP", currency: "JPY", sector: "Consumer Discretionary" },
  { ticker: "8035.T", name_kr: "도쿄일렉트론", market: "JP", currency: "JPY", sector: "Technology" },
  { ticker: "7974.T", name_kr: "닌텐도", market: "JP", currency: "JPY", sector: "Communication" },
  { ticker: "4063.T", name_kr: "신에츠화학", market: "JP", currency: "JPY", sector: "Materials" },
  { ticker: "6098.T", name_kr: "리쿠르트", market: "JP", currency: "JPY", sector: "Industrials" },
  { ticker: "6501.T", name_kr: "히타치", market: "JP", currency: "JPY", sector: "Industrials" },
  { ticker: "8316.T", name_kr: "미쓰이스미토모금융", market: "JP", currency: "JPY", sector: "Financials" },
  { ticker: "8058.T", name_kr: "미쓰비시상사", market: "JP", currency: "JPY", sector: "Industrials" },
  { ticker: "7267.T", name_kr: "혼다", market: "JP", currency: "JPY", sector: "Consumer Discretionary" },
  { ticker: "8001.T", name_kr: "이토추상사", market: "JP", currency: "JPY", sector: "Industrials" },
  { ticker: "8031.T", name_kr: "미쓰이물산", market: "JP", currency: "JPY", sector: "Industrials" },
  { ticker: "9433.T", name_kr: "KDDI", market: "JP", currency: "JPY", sector: "Communication" },
  { ticker: "4502.T", name_kr: "다케다제약", market: "JP", currency: "JPY", sector: "Healthcare" },
  { ticker: "6902.T", name_kr: "덴소", market: "JP", currency: "JPY", sector: "Consumer Discretionary" },
  { ticker: "8411.T", name_kr: "미즈호금융", market: "JP", currency: "JPY", sector: "Financials" },
  { ticker: "7011.T", name_kr: "미쓰비시중공업", market: "JP", currency: "JPY", sector: "Industrials" },
  { ticker: "7741.T", name_kr: "호야", market: "JP", currency: "JPY", sector: "Healthcare" },
  { ticker: "4661.T", name_kr: "오리엔탈랜드", market: "JP", currency: "JPY", sector: "Consumer Discretionary" },
  { ticker: "9432.T", name_kr: "NTT", market: "JP", currency: "JPY", sector: "Communication" },
  { ticker: "6594.T", name_kr: "니덱", market: "JP", currency: "JPY", sector: "Industrials" },
];

// ── 중국 메가캡 후보 (본토 A주 + 홍콩 H주) ──
const CN: UniverseCandidate[] = [
  { ticker: "0700.HK", name_kr: "텐센트", market: "CN", currency: "HKD", sector: "Communication" },
  { ticker: "9988.HK", name_kr: "알리바바(HK)", market: "CN", currency: "HKD", sector: "Consumer Discretionary" },
  { ticker: "1810.HK", name_kr: "샤오미", market: "CN", currency: "HKD", sector: "Technology" },
  { ticker: "9618.HK", name_kr: "JD닷컴", market: "CN", currency: "HKD", sector: "Consumer Discretionary" },
  { ticker: "3690.HK", name_kr: "메이투안", market: "CN", currency: "HKD", sector: "Consumer Discretionary" },
  { ticker: "0941.HK", name_kr: "차이나모바일", market: "CN", currency: "HKD", sector: "Communication" },
  { ticker: "1398.HK", name_kr: "공상은행", market: "CN", currency: "HKD", sector: "Financials" },
  { ticker: "0939.HK", name_kr: "건설은행", market: "CN", currency: "HKD", sector: "Financials" },
  { ticker: "2318.HK", name_kr: "핑안보험(HK)", market: "CN", currency: "HKD", sector: "Financials" },
  { ticker: "600519.SS", name_kr: "귀주모태", market: "CN", currency: "CNY", sector: "Consumer Staples" },
  { ticker: "601318.SS", name_kr: "핑안보험(A)", market: "CN", currency: "CNY", sector: "Financials" },
  { ticker: "600036.SS", name_kr: "초상은행", market: "CN", currency: "CNY", sector: "Financials" },
  { ticker: "000333.SZ", name_kr: "메이디그룹", market: "CN", currency: "CNY", sector: "Consumer Discretionary" },
  { ticker: "000858.SZ", name_kr: "오량액", market: "CN", currency: "CNY", sector: "Consumer Staples" },
  { ticker: "002594.SZ", name_kr: "BYD", market: "CN", currency: "CNY", sector: "Consumer Discretionary" },
  { ticker: "300750.SZ", name_kr: "CATL", market: "CN", currency: "CNY", sector: "Industrials" },
  { ticker: "600276.SS", name_kr: "장쑤헝루이의약", market: "CN", currency: "CNY", sector: "Healthcare" },
  { ticker: "600900.SS", name_kr: "양쯔강전력", market: "CN", currency: "CNY", sector: "Utilities" },
  { ticker: "002475.SZ", name_kr: "리쉰정밀", market: "CN", currency: "CNY", sector: "Technology" },
  { ticker: "601888.SS", name_kr: "중국국제여행", market: "CN", currency: "CNY", sector: "Consumer Discretionary" },
];

// ── 유럽 메가캡 후보 ──
const EU: UniverseCandidate[] = [
  { ticker: "ASML", name_kr: "ASML", market: "EU", currency: "USD", sector: "Technology" }, // ADR 달러
  { ticker: "MC.PA", name_kr: "LVMH", market: "EU", currency: "EUR", sector: "Consumer Discretionary" },
  { ticker: "NVO", name_kr: "노보노디스크", market: "EU", currency: "USD", sector: "Healthcare" },
  { ticker: "SAP", name_kr: "SAP", market: "EU", currency: "USD", sector: "Technology" },
  { ticker: "NESN.SW", name_kr: "네슬레", market: "EU", currency: "EUR", sector: "Consumer Staples" },
  { ticker: "SHEL", name_kr: "쉘", market: "EU", currency: "USD", sector: "Energy" },
  { ticker: "AZN", name_kr: "아스트라제네카", market: "EU", currency: "USD", sector: "Healthcare" },
  { ticker: "TTE", name_kr: "토탈에너지", market: "EU", currency: "USD", sector: "Energy" },
  { ticker: "RY.PA", name_kr: "에르메스", market: "EU", currency: "EUR", sector: "Consumer Discretionary" },
  { ticker: "OR.PA", name_kr: "로레알", market: "EU", currency: "EUR", sector: "Consumer Staples" },
  { ticker: "SIE.DE", name_kr: "지멘스", market: "EU", currency: "EUR", sector: "Industrials" },
  { ticker: "ULVR.L", name_kr: "유니레버", market: "EU", currency: "GBP", sector: "Consumer Staples" },
  { ticker: "ROG.SW", name_kr: "로슈", market: "EU", currency: "EUR", sector: "Healthcare" },
  { ticker: "SAN.PA", name_kr: "사노피", market: "EU", currency: "EUR", sector: "Healthcare" },
  { ticker: "NOVN.SW", name_kr: "노바티스", market: "EU", currency: "EUR", sector: "Healthcare" },
];

// ── 기타 (대만/인도/브라질) ──
const OTHER: UniverseCandidate[] = [
  { ticker: "TSM", name_kr: "TSMC(ADR)", market: "OTHER", currency: "USD", sector: "Technology" },
  { ticker: "2317.TW", name_kr: "혼하이정밀", market: "OTHER", currency: "TWD", sector: "Technology" },
  { ticker: "2454.TW", name_kr: "미디어텍", market: "OTHER", currency: "TWD", sector: "Technology" },
  { ticker: "TCS.NS", name_kr: "TCS(인도)", market: "OTHER", currency: "INR", sector: "Technology" },
  { ticker: "RELIANCE.NS", name_kr: "릴라이언스", market: "OTHER", currency: "INR", sector: "Energy" },
  { ticker: "HDFCBANK.NS", name_kr: "HDFC은행", market: "OTHER", currency: "INR", sector: "Financials" },
  { ticker: "INFY", name_kr: "인포시스(ADR)", market: "OTHER", currency: "USD", sector: "Technology" },
  { ticker: "ITUB", name_kr: "이타우은행(ADR)", market: "OTHER", currency: "USD", sector: "Financials" },
  { ticker: "VALE", name_kr: "발레(ADR)", market: "OTHER", currency: "USD", sector: "Materials" },
  { ticker: "BABA", name_kr: "알리바바(ADR)", market: "OTHER", currency: "USD", sector: "Consumer Discretionary" },
];

export const UNIVERSE_CANDIDATES: UniverseCandidate[] = [...US, ...KR, ...JP, ...CN, ...EU, ...OTHER];
