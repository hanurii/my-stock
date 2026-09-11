"""미국 SEPA 1단계 — 8관문 + RS 80.

★ 뺀 것과 까닭 (설계 문서 §"미국 결과로 재구성"의 실체):
  - 국면 자동 필터: 60·112 — 미국 등가중 20MA 로 MDD −36.2 → −55.4% 악화
  - DART 실적: 자료원 교체(Sharadar)
  - 외국인 지분율: 미국에 대응물 없음
★ 검출기·관문의 수는 하나도 바꾸지 않는다. verify_frozen_params.py 로 검산한다.

사용 예:
  # 전체 스캔 + JSON 저장 (기본)
  python scripts/screen_trend_template_us.py

  # 과거 시점 기준 (룩어헤드 방지) — 뼈대가 가진 310봉 안에서만 가능
  python scripts/screen_trend_template_us.py --asof 2026-06-30

관문 판정(evaluate_trend_template)과 RS 계산(_compute_rs_for_all)은 한 줄도
바꾸지 않는다 — 27.4년 백테스트가 그 수로 돌았다. 여기서 바꾼 자리는 셋뿐이다:
시세 출처(us_matrix) · 유니버스(us_loader) · 산출 경로.

★ 관문 «순서»도 하네스와 같게 둔다(backtest_volatility_pilot_us.py:347-371):
    200봉 확인 ∧ 마지막 봉 = 기준일 → is_halted(거래정지) → 유동성 → RS → 8관문
  순서를 바꾸면 수가 아니라 **분모**가 달라진다.

🔴 여기가 한국판과 **일부러 다른 한 자리**다 — 되돌리지 마라(사용자 결정 2026-09-11).
  한국은 RS 를 **전 시장**으로 잰다(`minervini_filter.py:19-20`: 저유동을 풀에서 빼면
  전 종목 RS 가 왜곡된다). 미국판은 **거른 뒤** 잰다. 까닭 셋:
   ① 27.4년의 수가 그 규약에서 나왔다 — 하네스가 `stD`(다 거른 뒤)로
      `_compute_rs_for_all` 을 부른다(`backtest_volatility_pilot_us.py:347-371`).
      전 시장으로 재면 백테스트가 **본 적 없는** 19종목이 후보로 올라온다(실측).
   ② 한국 규약은 「더 낫다」는 **설계 주장**이지 검정된 것이 아니다.
   ③ 한국 근거의 **크기**가 미국에 없다 — 그 주석이 든 수는 「저유동이 시장의 ~57%」인데
      미국 실측은 457/3,918 = **11.7%**(다섯 배 차이). 게다가 한국 결과를 미국 판단의
      근거로 쓰지 않는다(사용자 결정 2026-09-09).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Windows cp949 콘솔에서 한글 안전 출력
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import us_matrix  # noqa: E402
# 거래정지 관문. 한국 정지 «플래그» 자료원은 미국에 없지만 is_halted 는 거래량으로
# **계산**한다 — 뼈대에 volumes 가 있으므로 그대로 쓸 수 있다.
# 판정 일수(HALT_ZERO_VOL_DAYS=5)는 «가져다» 쓴다. days 를 넘기지 않는다 —
# 하네스도 안 넘긴다(backtest_volatility_pilot_us.py:357).
from canslim_lib import liveness  # noqa: E402
from canslim_lib.minervini_filter import (  # noqa: E402
    MIN_TURNOVER_EOK_DEFAULT, avg_turnover_eok)
from canslim_lib.trend_template import (  # noqa: E402
    compute_gate_margin,
    evaluate_trend_template,
    TT_LOW_MIN_PCT,
    TT_HIGH_MAX_PCT,
    TT_SMA200_RISING_LOOKBACK_DAYS,
    TT_SMA200_RISING_PREFERRED_DAYS,
)
import us_loader  # noqa: E402
# RS 계산·asof 자르기·「몇 봉부터 평가하나」는 한국판에서 **가져다** 쓴다.
# 베껴 적으면 값이 갈라질 수 있고, 갈라지는 순간 27.4년과 다른 수가 된다.
from screen_trend_template import (  # noqa: E402
    _compute_rs_for_all,
    _truncate_to_asof,
    MIN_CLOSES_FOR_TT,
    MIN_RS_COMPARISON_POOL,
)

UTC = timezone.utc
OUTPUT_PATH = ROOT / "public" / "data" / "sepa-us-trend-candidates.json"

# RS 합격선 80. 27.4년 하네스가 돌던 값이다
# (backtest_volatility_pilot_us.py:55 `RS_MIN = 80`).
# 한국판 기본값 TT_RS_MIN_DEFAULT(70)가 **아니다** — 미국은 80 으로 돌았다.
RS_MIN = 80

# 유니버스 판. us_loader.load_tickers 의 기본판과 같다
# (Domestic Common Stock · NASDAQ/NYSE/NYSEMKT · SPAC 제외).
US_VARIANT = "base"


# ──────────────────────────────────────────────────
# 거래대금 — 단위를 옮기는 자리
# ──────────────────────────────────────────────────

def avg_turnover_eok_us(series: dict | None, asof: str | None) -> float | None:
    """미국 시세의 50일 평균 거래대금(억원 상당). 판정 불가면 None.

    minervini_filter.avg_turnover_eok 는 close×volume 을 1e8 로 나눈다 —
    미국 자료에 대면 그 값은 **억 달러**다. 하네스가 5.0 과 견주는 자는
    **억원 상당**이다(us_loader.py:30 `turnover_eok = USD × USD_KRW ÷ 1e8`).
    그래서 USD_KRW 를 곱한다. 평균은 선형이라 곱을 나중에 해도 값이 같다.

    창(50일)·최소 표본(20일)은 minervini_filter 의 얼린 값을 그대로 쓴다.
    """
    v = avg_turnover_eok(series, asof=asof)
    return None if v is None else v * us_loader.USD_KRW


# ──────────────────────────────────────────────────
# 유니버스 · 수집
# ──────────────────────────────────────────────────

def sharadar_snapshot_date(meta: dict) -> str:
    """Sharadar 메타를 «얼린» 날. 자료에서 «유도»한다 — 손으로 적지 않는다.

    손으로 적으면 뼈대를 다시 만드는 날 같은 것을 가리키는 자가 둘이 되고,
    그 둘은 언젠가 갈라진다. 살아 있는 종목의 lastpricedate 는 전부 수령일과
    같으므로 메타 전체의 최댓값이 곧 수령일이다
    (실측 2026-09-09: 4,053종목이 같은 값을 들고, 그보다 뒤인 종목은 0).
    """
    return max((m["lastpricedate"] for m in meta.values()), default="")


def is_listed_on(m: dict, asof: str, snapshot: str) -> bool:
    """「이 종목이 기준일에 상장돼 있었나」. 얼린 날짜를 «상한»으로 쓰지 않는다.

    🔴 하네스의 술어(`us_loader.build_all` 의
    `firstpricedate <= d <= lastpricedate`)를 글자 그대로 옮기면 «첫 갱신»에
    유니버스가 0 이 된다. 하네스는 자료 수령일 «이하»의 날만 스캔해서 그 술어가
    맞았지만, 이 도구는 수령일 «뒤»를 산다 — 꼬리를 붙이는 목적이 바로 기준일을
    수령일 뒤로 옮기는 것이다. 얼린 표에서 살아 있는 종목의 lastpricedate 는
    「그날 상폐」가 아니라 「스냅샷 때 거래 중이었다」는 뜻이라 상한이 아니다.

        진짜 상장폐지  = lastpricedate <  스냅샷   -> 그 날짜가 상한이다
        아직 살아 있음 = lastpricedate == 스냅샷   -> 상한 없음
        하한은 그대로  = firstpricedate <= asof

    🔴 그래서 «스냅샷 뒤»에 난 상장폐지는 이 술어로 못 잡는다 — 얼린 표에
    안 실렸기 때문이다. 다만 «전부» 놓치지는 않는다: 관문 «앞»에 이미
    `collect_one` 의 `stale`(마지막 봉 != 기준일)과 `liveness.is_halted`
    (최근 5거래일 거래량 0)가 있어, 거래가 끊긴 종목은 거기서 떨어진다.
    그 둘은 «거래가 있었나»를 보고 이 술어는 «상장 명부에 있나»를 본다 —
    다른 자다. 그러니 「is_halted 가 있으니 됐다」로 읽지 마라. 상장폐지 뒤에도
    장외에서 거래가 이어지는 종목은 둘 다 못 거른다.
    """
    if m["firstpricedate"] > asof:
        return False
    if m["lastpricedate"] >= snapshot:      # 스냅샷 때 살아 있었다 — 상한 없음
        return True
    return asof <= m["lastpricedate"]       # 스냅샷 «전»에 이미 끊긴 것


def universe_collapse_reason(n_universe: int, n_ceiling: int,
                             min_ratio: float = 0.5) -> str | None:
    """유니버스가 무너졌으면 사유 글, 멀쩡하면 None.

    왜 있나: 「후보 0」이 조용히 «정상 종료»로 나오는 것이 1번 결함의 «본체»였다.
    통과 0 은 약세장일 수 있지만 유니버스 0 은 약세장이 아니라 고장이다.

    자(분모)는 «날짜 술어를 걸기 «전»» 모집단이다 — 메타에 있고 뼈대에 시세도
    있는 종목 수. 날짜 술어가 고장 나면 분자만 줄고 분모는 그대로라 비가
    떨어진다. 분모를 「술어를 통과한 것」으로 잡으면 항등식이 되어 이 관문이
    «질 수가 없다».

    문턱 0.5 — 실측 2026-09-09 에 4,053/4,648 = 87.2% 이고, 메타가 얼려 있어
    상폐가 더 늘지 않으므로(스냅샷 뒤 상폐는 표에 안 실린다) 이 비가 절반 밑으로
    내려가는 길은 날짜 술어 고장 말고는 없다. 과거 기준일(`--asof`)로 내려가면
    그 뒤 신규 상장분이 빠지는데, 뼈대가 310봉(약 1.2년)뿐이라 그 폭이 한 자릿수
    퍼센트다.
    """
    if n_ceiling <= 0:
        return ("뼈대에 메타와 겹치는 종목이 «하나도» 없다 — 시세 파일이나 "
                "유니버스 표가 어긋났다")
    if n_universe == 0:
        return ("유니버스가 0종목이다 — 약세장이 아니라 «고장»이다 "
                "(모집단 %d종목 중 0). 기준일이 Sharadar 스냅샷보다 뒤인데 "
                "상장 판정이 얼린 날짜를 상한으로 쓰고 있지 않은지 봐라"
                % n_ceiling)
    ratio = n_universe / n_ceiling
    if ratio < min_ratio:
        return ("유니버스가 모집단의 %.1f%% 로 쪼그라들었다 (%d / %d). "
                "문턱 %.0f%% 미만 — 정상적인 상장·상폐로는 이만큼 안 줄어든다"
                % (ratio * 100, n_universe, n_ceiling, min_ratio * 100))
    return None


def build_universe(base: dict, asof: str) -> tuple[list[dict], int, int, str]:
    """(그날 상장 중이고 뼈대에 시세가 있는 종목, 메타 전체 수, 모집단, 스냅샷일).

    모집단 = 메타에 있고 뼈대에 시세도 있는 종목 수. 「날짜 술어를 걸기 «전»」의
    수라서 `universe_collapse_reason` 의 분모로 쓸 수 있다(항등식이 아니다).
    상장 여부 판정은 `is_listed_on` 이 정본이다 — 왜 하네스 술어를 글자
    그대로 못 쓰는지도 거기 적혀 있다.
    """
    meta = us_loader.load_tickers(US_VARIANT)
    snapshot = sharadar_snapshot_date(meta)
    series = base.get("series") or {}
    n_ceiling = 0
    out: list[dict] = []
    for code, m in meta.items():
        if code not in series:
            continue
        n_ceiling += 1
        if not is_listed_on(m, asof, snapshot):
            continue
        out.append({"code": code, "name": m["name"], "market": m["exchange"]})
    out.sort(key=lambda s: s["code"])
    return out, len(meta), n_ceiling, snapshot


def resolve_trading_day(base: dict, asof: str) -> tuple[str, bool]:
    """기준일을 **실제 거래일**로 내린다. (거래일, 요청값과 달라졌나).

    하네스는 REF 시계열의 달력에서 스캔일을 고르므로 기준일이 «언제나» 거래일이다
    (us_loader.py:211-212 로 달력을 만들고 backtest_volatility_pilot_us.py:332-334
    에서 고른다). 이걸 안 하면 --asof 에 주말을 넣었을 때 아래 「마지막 봉 = 기준일」
    관문이 **전 종목을 떨어뜨려** 조용히 후보 0 이 된다.
    """
    cal = ((base.get("series") or {}).get(us_loader.REF) or {}).get("dates") or []
    eligible = [d for d in cal if d <= asof]
    if not eligible:
        return asof, False
    return eligible[-1], eligible[-1] != asof


def collect_one(stock: dict, asof: str | None) -> dict:
    """단일 종목 시세 수집 + asof 자르기. 한국 `_collect_one` 과 같은 모양.

    `reason_code` 로 탈락 사유를 «코드»로도 남긴다 — 분모를 셀 때 글자를 맞춰
    세면 문구를 고치는 순간 조용히 0 이 된다.
    """
    code = stock["code"]
    base_row = {
        "code": code, "name": stock["name"], "market": stock["market"],
        # 미국 자료에는 시총 대응물을 안 받아 왔다(us_loader 가 cap_eok=None).
        # 키를 지우면 한국 산출을 읽는 자리가 KeyError 로 죽으므로 None 으로 둔다.
        "market_cap_eok": None,
    }
    s = us_matrix.get_series(code)
    if not s or not s.get("closes"):
        return {**base_row, "ok": False, "reason_code": "no_series",
                "reason": "시세 없음 (뼈대에 종목 없음)",
                "closes": None, "dates": None, "series": None}

    closes, dates = _truncate_to_asof(
        list(s["closes"]), list(s["dates"]), asof)

    if len(closes) < MIN_CLOSES_FOR_TT:
        return {**base_row, "ok": False, "reason_code": "short",
                "reason": f"데이터 부족 (보유 일수 {len(closes)} < {MIN_CLOSES_FOR_TT})",
                "closes": closes, "dates": dates, "series": s}

    # 하네스 :355 의 `t["dates"][-1] != D` — 그날 «안 거래된» 종목은 버린다.
    # ★ 오늘 자료로는 0건이다. 그래도 넣는 까닭: 꼬리(us_seam)가 한 번이라도 돌면
    #   「표가 빈 종목은 실패가 아니다」(us_seam.py fetch_tail)라 그 종목엔 «옛 뼈대»가
    #   남고(attach), **종목마다 마지막 날이 다른** 파일이 «정상적으로» 생긴다.
    #   그때 이 관문이 없으면 하네스가 버리는 종목이 8관문에도 RS 비교풀에도 들어간다.
    if not dates or dates[-1] != asof:
        return {**base_row, "ok": False, "reason_code": "stale",
                "reason": f"마지막 봉 {dates[-1] if dates else '없음'} != 기준일 {asof}",
                "closes": closes, "dates": dates, "series": s}

    return {**base_row, "ok": True, "reason_code": None, "reason": None,
            "closes": closes, "dates": dates, "series": s,
            "last_date": dates[-1] if dates else None,
            "last_close": closes[-1]}


# ──────────────────────────────────────────────────
# 메인 흐름
# ──────────────────────────────────────────────────

def run_full_scan(args: argparse.Namespace) -> None:
    rs_min = args.rs_min

    print("미국 트렌드 템플레이트 스크리너 "
          f"(RS 합격선: {rs_min}, 거래대금 하한: {args.min_turnover_eok:g}억 상당)")

    # ── 1단계: 자료 적재.
    # 🔴 load_base 가 아니라 load_latest 다 — 꼬리가 붙은 합본이 있으면 그것을 읽는다.
    #    2026-09-11 검토: tail.json 을 «읽는» 자리가 저장소에 «0개»여서 자료를
    #    갱신해도 결과가 안 바뀌었다. 예외도 경고도 없는 조용한 실패였다.
    t0 = time.time()
    try:
        base, src = us_matrix.load_latest()
    except FileNotFoundError:
        print(f"[멈춤] 시세 파일이 없다: {us_matrix.BASE_PATH}")
        print("       /update-data-us 로 먼저 만들어라.")
        sys.exit(1)
    base_asof = base.get("asof") or ""
    n_series = len(base.get("series") or {})
    # «어느 파일을 읽었나»를 반드시 찍는다. 안 보이면 위 병을 또 놓친다.
    kind = "합본(뼈대+꼬리)" if src == us_matrix.TAIL_PATH else "뼈대만 (꼬리 아직 없음)"
    print()
    print(f"[자료] {src.name} — {kind}")
    print(f"       {n_series}종목 · 자료 최신일 {base_asof} "
          f"({time.time() - t0:.1f}s)")

    asof_req = args.asof or base_asof
    asof, moved = resolve_trading_day(base, asof_req)
    if args.asof:
        print(f"       --asof {args.asof} 적용 "
              f"(뼈대는 {us_matrix.TRIM_BARS}봉만 들고 있다)")
    if moved:
        print(f"       기준일을 «거래일»로 내림: {asof_req} -> {asof}")

    # ── 2단계: 유니버스
    universe, meta_n, ceiling_n, snapshot = build_universe(base, asof)
    print(f"\n[유니버스] variant={US_VARIANT}")
    print(f"  Sharadar 메타 전체(상폐 이력 포함): {meta_n}종목")
    print(f"  Sharadar 스냅샷 날짜(메타에서 «유도»): {snapshot}")
    print(f"  메타에 있고 뼈대에 시세도 있음(모집단): {ceiling_n}종목")
    print(f"  -> {asof} 상장 중: {len(universe)}종목")
    if asof > snapshot:
        print(f"  (기준일이 스냅샷보다 뒤다 — 스냅샷 뒤에 «새로» 난 상장폐지는 "
              f"얼린 표에 없어 이 판정으로 못 잡는다. 거래가 끊긴 종목은 "
              f"아래 stale·거래정지 관문이 잡는다)")
    # 「후보 0」이 조용히 정상 종료로 나오는 것이 막아야 할 바로 그 모양이다.
    collapse = universe_collapse_reason(len(universe), ceiling_n)
    if collapse:
        print(f"\n[멈춤] {collapse}")
        print("       뒤 단계를 돌리지 않는다 — 「통과 0」으로 조용히 끝내면 "
              "고장이 약세장으로 읽힌다.")
        sys.exit(1)

    # ── 3단계: 시세 수집 (뼈대가 이미 메모리에 있어 병렬이 필요 없다)
    raw_results = [collect_one(s, asof) for s in universe]
    # 사유를 «코드»로 센다 — 글자로 세면 문구를 고치는 순간 조용히 0 이 된다.
    n_short = sum(1 for r in raw_results if r.get("reason_code") == "short")
    n_stale = sum(1 for r in raw_results if r.get("reason_code") == "stale")
    n_noser = sum(1 for r in raw_results if r.get("reason_code") == "no_series")
    n_200plus = len(raw_results) - n_short - n_noser      # stale 을 «포함»한 수
    ok_count = sum(1 for r in raw_results if r["ok"])
    full_bars = sum(1 for r in raw_results
                    if r["ok"] and len(r["closes"]) >= us_matrix.TRIM_BARS)
    assert n_200plus - n_stale == ok_count, "분모 셈이 어긋난다"
    print()
    print(f"[분모] 200봉 이상 확보: {n_200plus}종목 "
          f"(200봉 미만 {n_short} · 시세 없음 {n_noser} 뺀 뒤)")
    print(f"  마지막 봉 != 기준일({asof}) 이라 제외: {n_stale}종목 -> {ok_count}종목")
    print(f"  그중 {us_matrix.TRIM_BARS}봉을 꽉 채운 것: {full_bars}종목")

    # ── 3.5단계: 거래정지 관문 — 하네스 순서를 지킨다(200봉 → 정지 → 유동성).
    # 유동성 **앞**이자 RS **앞**이다. 뒤로 옮기면 정지 종목이 RS 비교풀에 남는다.
    kept, halted = [], []
    for r in raw_results:
        if r["ok"] and liveness.is_halted(r["series"], asof=asof):
            halted.append(r)
            continue
        kept.append(r)
    raw_results = kept
    n_skip_halt = len(halted)
    ok_after_halt = sum(1 for r in raw_results if r["ok"])
    print(f"  거래정지 제외: {n_skip_halt}종목 "
          f"(최근 {liveness.HALT_ZERO_VOL_DAYS}거래일 거래량이 모두 0) "
          f"-> {ok_after_halt}종목")

    # ── 3.6단계: 유동성 관문 — 하네스 순서상 RS **앞**이다.
    kept, liq_dropped = [], []
    for r in raw_results:
        if not r["ok"]:
            kept.append(r)
            continue
        tv = avg_turnover_eok_us(r["series"], asof)
        r["turnover_eok"] = None if tv is None else round(tv, 2)
        if tv is None or tv < args.min_turnover_eok:
            liq_dropped.append(r)
            continue
        kept.append(r)
    raw_results = kept
    eval_n = sum(1 for r in raw_results if r["ok"])
    print(f"  저유동성 제외: {len(liq_dropped)}종목 "
          f"(50일 평균 거래대금 < {args.min_turnover_eok:g}억 상당) "
          f"-> 평가 대상 {eval_n}종목 = 8관문 판정의 분모")

    # ── 4단계: RS — 정지·유동성을 **다 거른 뒤**의 생존자로만 잰다.
    #   여기가 한국판과 «일부러» 다른 자리다. 까닭은 머리말 참조.
    #   ⛔ 순서를 위로 올리면(전 시장으로 재면) 오늘 자료에서 통과가 302 -> 321 로
    #      늘고, 그 19종목은 27.4년이 «본 적 없는» 종목이다.
    print(f"\n[RS] 점수 1-99 계산 중... (비교풀 최소 {args.rs_pool_min})")
    rs_map = _compute_rs_for_all(raw_results, min_pool=args.rs_pool_min)
    rs_n = sum(1 for v in rs_map.values() if v["rs"] is not None)
    # 🚨 「RS 비교풀 크기」라는 말에 자가 «셋»이다. 뭉쳐 쓰면 규약 ⑦에 걸린다.
    rs_input_n = eval_n                                  # ㉠ 계산에 «넣은» 종목 수
    pool_252 = max((v.get("rs_universe_n") or 0)         # ㉢ 제일 큰 «단일 창» 비교풀
                   for v in rs_map.values()) if rs_map else 0
    print(f"  RS 계산에 넣은 종목(모집단): {rs_input_n}종목")
    print(f"  RS 가 «산출된» 종목: {rs_n}종목 "
          f"(나머지는 비교 표본 < {args.rs_pool_min} 이라 RS=None -> 조건⑧ 자동 탈락)")
    print(f"  제일 큰 단일-창 비교풀(52주 252거래일): {pool_252}종목")

    # ── 5단계: 8조건 평가
    print("\n[관문] 8가지 조건 평가 중...")
    candidates: list[dict] = []
    failed_stocks: list[dict] = []
    pass_count = 0

    for r in raw_results:
        if not r["ok"]:
            failed_stocks.append({
                "code": r["code"], "name": r["name"], "market": r["market"],
                "market_cap_eok": r["market_cap_eok"], "reason": r["reason"],
            })
            continue
        rs_entry = rs_map.get(r["code"], {})
        rs_val = rs_entry.get("rs")
        result = evaluate_trend_template(r["closes"], rs=rs_val, rs_min=rs_min)
        candidates.append({
            "code": r["code"],
            "name": r["name"],
            "market": r["market"],
            "market_cap_eok": r["market_cap_eok"],
            "current_price": r["last_close"],
            "last_date": r["last_date"],
            "turnover_eok": r.get("turnover_eok"),
            "rs": rs_val,
            "rs_basis": rs_entry.get("rs_basis"),
            "rs_window_days": rs_entry.get("win"),
            "rs_universe_n": rs_entry.get("rs_universe_n"),
            "return_window_pct": rs_entry.get("ret_pct"),
            "rs_note": rs_entry.get("rs_note"),
            "passed_count": result["passed_count"],
            "all_pass": result["pass"],
            "gate_margin": compute_gate_margin(
                result, r["last_close"], rs_val, rs_min),
            "criteria": result["criteria"],
            "extras": result["extras"],
        })
        if result["pass"]:
            pass_count += 1

    candidates.sort(key=lambda c: (-1 if c["all_pass"] else 0,
                                   -(c["rs"] or -1),
                                   -(c["passed_count"] or 0)))

    print(f"\n[결과] 8개 모두 통과: {pass_count}종목 / 평가 {eval_n}종목")

    # ── 6단계: 저장
    output = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        # asof = **자료 날짜**. 실행 시각을 쓰면 날짜가 하루 밀린다(한국판과 같은 까닭).
        "asof": asof,
        "market": "US",
        "variant": US_VARIANT,
        "universe_meta_n": meta_n,
        # 상장 판정의 «상한»이 아니라 「스냅샷 때 살아 있었나」의 자다.
        # 손으로 안 적고 메타에서 유도한다(sharadar_snapshot_date).
        "sharadar_snapshot_date": snapshot,
        "universe_ceiling_n": ceiling_n,         # 날짜 술어 «전» 모집단
        "scanned_count": len(universe),
        "source_file": src.name,                # 뼈대만인가 합본인가
        "asof_requested": asof_req,             # 내려가기 «전» 요청값
        # 분모가 여럿이다. 하나로 뭉치면 안 되므로 단계마다 따로 적는다.
        "bars_ok_count": n_200plus,             # 200봉 이상 (stale 포함)
        "stale_bar_excluded": n_stale,          # 마지막 봉 != 기준일
        "evaluated_count": ok_count,            # 200봉 이상 ∧ 마지막 봉 = 기준일
        "full_bars_count": full_bars,
        "trim_bars": us_matrix.TRIM_BARS,
        "halted_excluded": n_skip_halt,         # 거래정지 (유동성 앞)
        "halt_zero_vol_days": liveness.HALT_ZERO_VOL_DAYS,
        "low_turnover_excluded": len(liq_dropped),
        "gate_denominator": eval_n,             # 8관문 판정의 분모
        "all_pass_count": pass_count,
        # 🚨 「RS 비교풀 크기」에 자가 셋이다 — 셋 다 따로 적는다(규약 ⑦).
        "rs_input_n": rs_input_n,               # ㉠ RS 계산에 넣은 종목 수
        "rs_universe_n": rs_n,                  # ㉡ RS 가 «산출된» 종목 수
                                                #    (한국판 최상위 키와 같은 뜻)
        "rs_pool_252": pool_252,                # ㉢ 제일 큰 단일-창 비교풀
        "rs_pool_scope": "정지·유동성 제외 뒤 생존자 (27.4년 하네스 규약·2026-09-11 결정)",
        "rs_min": rs_min,
        "min_closes_for_tt": MIN_CLOSES_FOR_TT,
        "min_turnover_eok": args.min_turnover_eok,
        "usd_krw": us_loader.USD_KRW,
        "thresholds": {
            "low_min_pct": TT_LOW_MIN_PCT,
            "high_max_pct": TT_HIGH_MAX_PCT,
            "sma200_rising_lookback_days": TT_SMA200_RISING_LOOKBACK_DAYS,
            "sma200_rising_preferred_days": TT_SMA200_RISING_PREFERRED_DAYS,
        },
        "candidates": candidates,
        "failed_stocks": failed_stocks,
    }

    # 제자리 덮어쓰기 금지 — 여는 순간 잘린다. 임시 파일에 다 쓰고 옮긴다.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT_PATH.with_name(OUTPUT_PATH.name + ".tmp")
    tmp.write_text(json.dumps(output, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    tmp.replace(OUTPUT_PATH)
    print(f"\n[저장] {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"  (총 {len(candidates)}종목 기록, 8개 통과 {pass_count}종목)")

    print("\n[8개 통과 상위 20]")
    top = [c for c in candidates if c["all_pass"]][:20]
    if not top:
        print("  (없음)")
    for c in top:
        name = (c["name"] or "")[:28]
        print(f"  {c['code']:<6s} {name:<28s} ({c['market']})"
              f" 종가 {c['current_price']:>9,.2f}"
              f" RS {c['rs']:>2}"
              f" 거래대금 {c['turnover_eok']:>9,.0f}억")


def main():
    parser = argparse.ArgumentParser(
        description="미국 Minervini 트렌드 템플레이트 스크리너 (8관문 + RS 80)")
    parser.add_argument("--asof", default=None,
                        help="기준 날짜 YYYY-MM-DD (default: 뼈대의 자료 최신일). "
                             "룩어헤드 방지용 과거 평가에 쓴다.")
    parser.add_argument("--rs-min", type=int, default=RS_MIN,
                        help=f"RS 합격선 1-99 (default: {RS_MIN} — 27.4년 하네스 값)")
    parser.add_argument("--rs-pool-min", type=int, default=MIN_RS_COMPARISON_POOL,
                        help="RS 백분위 비교 모집단 최소 개수 "
                             f"(default: {MIN_RS_COMPARISON_POOL})")
    parser.add_argument("--min-turnover-eok", type=float,
                        default=MIN_TURNOVER_EOK_DEFAULT,
                        help="저유동성 기준: 50일 평균 거래대금 하한(억원 상당, "
                             f"기본 {MIN_TURNOVER_EOK_DEFAULT:g})")
    args = parser.parse_args()
    run_full_scan(args)


if __name__ == "__main__":
    main()
