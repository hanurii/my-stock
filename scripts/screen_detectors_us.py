# scripts/screen_detectors_us.py
"""미국 SEPA 2단계 — 검출기 셋(VCP · 파워플레이 · 3C). --kind 로 갈린다.

입력: public/data/sepa-us-trend-candidates.json (1단계 screen_trend_template_us.py 산출)
출력: public/data/sepa-us-{vcp,power-play,3c}-candidates.json

검출기 코드와 값은 한국과 «같은 모듈»을 그대로 쓴다 — 27.4년 백테스트가 그 값으로
돌았다. params 를 넘기지 않는다(None 이면 각 모듈의 DEFAULT_PARAMS 가 쓰인다).
넘기는 순간 verify_frozen_params.py 가 얼린 값을 우회하게 된다.

한국 대응물(하네스 정본)과의 관계
  vcp        <- scripts/screen_vcp.py
  power-play <- scripts/screen_power_play.py  (--universe trend 기본값만)
  3c         <- scripts/screen_3c.py

한국판과 «다른» 자리 넷 — 되돌리기 전에 까닭을 읽어라
  1) gate_near: 대상 술어가 `all_pass` «만»이다. 한국 정본은
     `all_pass or gate_near`(screen_vcp.py:44)인데 미국판은 «일부러» 좁다 —
     27.4년 하네스가 `GATE_NEAR_ALLOW = set()` 로 돌았다
     (backtest_volatility_pilot_us.py:237). 오늘은 1단계가 gate_near 키를 아예
     안 내서 결과가 같지만, 관문 완화가 들어오는 날 넓은 술어를 쓰면 27.4년이
     «본 적 없는» 종목이 조용히 들어온다. 갈래별 수는 그래도 둘 다 찍는다.
  2) asof 자르기: 미국 1단계는 --asof 를 받는다. 2단계가 뼈대 전체(310봉)를 그냥
     읽으면 1단계가 «못 본» 봉을 2단계가 본다 = 룩어헤드다. 그래서 1단계 산출의
     asof 로 계열을 자른다. 자르는 규칙은 screen_trend_template._truncate_to_asof
     하나를 «가져다» 쓴다(베끼면 자가 둘이 된다).
  3) IPO 트랙이 «없다». 한국에는 있다(find-ipo). ⛔ 여기에 더하지 마라.
     🔴 까닭은 「자료가 없어서」가 «아니다» — evaluate_ipo_track 이 요구하는
     closes·ipo_rs 는 둘 다 우리 뼈대로 «계산된다»(뼈대 4,648 중 20~199봉이
     349종목 있다). 진짜 까닭은 **27.4년 하네스가 ipo_track 을 한 번도 «안 돌렸다»**는
     것이다 — backtest_volatility_pilot_us.py 는 vcp·cheat·power_play 셋만 import 한다.
     ⇒ 미국에서 IPO 트랙이 돈을 버는지 «잰 적이 없다». 근거 없는 후보를 실전 화면에
     올리지 않는다(사용자 결정 2026-09-11). 재고 싶으면 «먼저» 하네스로 재라.
  4) 「진입」의 자가 «둘»이라 갈라 적는다. 모듈의 `entry_ready` 는
     detected ∧ status ∈ {breakout, actionable}(vcp.py:340) 인데, 27.4년 하네스가
     «진입»으로 «센» 것은 detected ∧ status ∈ ENTRY_STATUSES ∧ pivot_price 다
     (backtest_volatility_pilot_us.py:236·288) — breakout 이 «빠진다».
     사용자 진입이 「장 시작 전 피벗 가격 예약」이라 이미 피벗 위면 예약이 안
     걸리거나 추격이 된다. 그래서 `entry_ready_count`(하네스 정의)와
     `already_breakout_count` 를 따로 싣는다. 모듈 필드는 «고치지 않는다».
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import cheat, power_play, us_matrix, vcp  # noqa: E402
# asof 자르기 규칙 정본. 베끼지 않고 가져다 쓴다.
from screen_trend_template import _truncate_to_asof  # noqa: E402
# 🔴 27.4년 하네스에서 «읽어» 온다. 베껴 적으면 자가 둘이 되고(규약 ⑦), 하네스가
#    바뀌는 날 조용히 갈라진다. 최상위에 부수효과가 없어 import 가 안전하다(실측 0.96s).
#    ⛔ 하네스를 «고치지» 않는다 — 읽기만 한다.
import backtest_volatility_pilot_us as _harness  # noqa: E402

# 진입으로 «셀» 상태. 하네스 :236 `ENTRY_STATUSES = {"actionable"}`.
HARNESS_ENTRY_STATUSES = frozenset(_harness.ENTRY_STATUSES)
# 관문 임박 허용 집합. 하네스 :237 `GATE_NEAR_ALLOW: set = set()` (:565 기본값 "off").
HARNESS_GATE_NEAR_ALLOW = frozenset(_harness.GATE_NEAR_ALLOW)

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-us-trend-candidates.json"
OUT = {k: ROOT / "public" / "data" / f"sepa-us-{k}-candidates.json"
       for k in ("vcp", "power-play", "3c")}

STATUS_ORDER = {"breakout": 0, "actionable": 1, "forming": 2, "failed": 3}

# Step 1 에서 «코드를 직접 읽어» 확인한 이름이다(2026-09-11):
#   vcp.evaluate_vcp(series, params=None)                scripts/canslim_lib/vcp.py:224
#   power_play.evaluate_power_play(series, params=None)  scripts/canslim_lib/power_play.py:72
#   cheat.evaluate_cheat(series, params=None)            scripts/canslim_lib/cheat.py:87
# ⛔ ipo_track 은 여기 «없다» — import 조차 하지 않는다(위 머리글 3) 참고).
EVALS = {
    "vcp": (vcp.evaluate_vcp, vcp.DEFAULT_PARAMS, "vcp_detected", "VCP"),
    "power-play": (power_play.evaluate_power_play, power_play.DEFAULT_PARAMS,
                   "pattern_detected", "파워플레이"),
    "3c": (cheat.evaluate_cheat, cheat.DEFAULT_PARAMS, "pattern_detected", "3C"),
}

KINDS = sorted(set(OUT))


def _rel(p: Path) -> str:
    """보기 좋은 경로. 저장소 «밖»이면 절대 경로 그대로 — relative_to 는 터진다.

    (시험이 tmp 경로를 쓰면 여기서 터졌다. 찍는 줄이 각본을 죽이면 안 된다.)
    """
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _write_json(path: Path, payload: dict) -> None:
    """임시 파일에 쓰고 옮긴다 — 제자리 덮어쓰기는 여는 순간 원본을 자른다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    os.replace(tmp, path)


def _load_stage1() -> dict:
    if not IN_PATH.exists():
        print(f"[멈춤] 입력 파일 없음: {_rel(IN_PATH)}")
        print("       먼저 find-trend-template-us(1단계)를 실행하라.")
        sys.exit(1)
    return json.loads(IN_PATH.read_text(encoding="utf-8"))


def _cut(series: dict, asof: str | None) -> dict:
    """계열 전체를 asof 까지 자른다.

    자를 «자리»는 dates 로 정하고(_truncate_to_asof 가 정본), 나머지 축은 같은
    길이로 맞춘다. 축마다 따로 자르면 축이 어긋난 계열이 조용히 생긴다.
    """
    dates = list(series.get("dates") or [])
    if not asof or not dates:
        return series
    _, kept = _truncate_to_asof(dates, dates, asof)
    n = len(kept)
    if n == len(dates):
        return series
    return {k: (list(v)[:n] if isinstance(v, list) else v)
            for k, v in series.items()}


def run_detector(kind: str) -> int:
    fn, defaults, detected_key, label = EVALS[kind]
    data = _load_stage1()
    asof = data.get("asof")

    # 어느 시세 파일을 읽었는지 «반드시» 찍는다. 합본(꼬리)이 있는데 뼈대를 읽는
    # 조용한 실패가 2026-09-11 에 실제로 있었다(us_matrix.load_latest 주석).
    try:
        base, src = us_matrix.load_latest()
    except FileNotFoundError:
        print(f"[멈춤] 시세 파일이 없다: {us_matrix.BASE_PATH}")
        print("       /update-data-us 로 먼저 만들어라.")
        sys.exit(1)
    src_kind = "합본(뼈대+꼬리)" if src == us_matrix.TAIL_PATH else "뼈대만 (꼬리 아직 없음)"
    data_asof = base.get("asof") or ""
    print(f"[자료] {src.name} — {src_kind} · 자료 최신일 {data_asof}")
    print(f"[입력] {IN_PATH.name} · 1단계 기준일 {asof}")
    if data_asof and asof and data_asof < asof:
        print(f"[멈춤] 시세({data_asof})가 1단계 기준일({asof})보다 «과거»다. "
              "1단계를 다시 돌리거나 /update-data-us 를 먼저 하라.")
        sys.exit(1)
    if data_asof and asof and data_asof > asof:
        print(f"       시세가 더 새롭다 — 계열을 1단계 기준일 {asof} 로 자른다(룩어헤드 방지).")

    all_cands = data.get("candidates", [])
    n_pass = sum(1 for c in all_cands if c.get("all_pass"))
    n_near = sum(1 for c in all_cands if c.get("gate_near") and not c.get("all_pass"))
    # 🔴 `all_pass` «만». 한국 정본은 `all_pass or gate_near`(screen_vcp.py:44)인데
    #    미국판은 «일부러» 좁다 — 27.4년 하네스가 `GATE_NEAR_ALLOW = set()` 로 돌았다
    #    (backtest_volatility_pilot_us.py:237 선언 · :378 쓰는 자리 · :565 기본값 "off").
    #    오늘은 1단계가 gate_near 키를 «아예 안 내서» 두 술어의 결과가 같다. 그러나
    #    1단계에 관문 완화가 들어오는 날, 넓은 술어를 쓰면 27.4년이 «본 적 없는»
    #    종목이 예외도 경고도 없이 후보로 올라온다. ⛔ 넓히지 마라.
    targets = [c for c in all_cands if c.get("all_pass")]
    print(f"[대상] 1단계 평가 {len(all_cands)}종목 중 {len(targets)}종목 "
          f"(관문 통과 {n_pass} · 관문 임박 {n_near} — 임박은 «안» 넣는다, 하네스 정의)")
    # 「하네스가 임박을 안 썼다」를 «주장»으로 두지 않고 «읽어서» 찍는다.
    if HARNESS_GATE_NEAR_ALLOW:
        print(f"[경고] 하네스 GATE_NEAR_ALLOW 가 {sorted(HARNESS_GATE_NEAR_ALLOW)} 다 — "
              "더 이상 빈 집합이 아니다. 좁은 술어의 «까닭»이 사라졌으니 "
              "여기 술어를 다시 정해야 한다.")
    if n_near:
        print(f"[경고] 1단계가 gate_near 를 {n_near}종목 냈다. 하네스는 "
              "GATE_NEAR_ALLOW=set() 로 돌았으므로 여기서는 «뺀다». "
              "넣으려면 하네스를 그 설정으로 다시 돌린 근거가 먼저 있어야 한다.")
    if n_pass != data.get("all_pass_count"):
        print(f"[경고] all_pass 세어 보니 {n_pass} 인데 파일의 all_pass_count 는 "
              f"{data.get('all_pass_count')} 다 — 같은 것을 가리키는 수가 둘이다.")

    out_cands = []
    n_no_series, n_stale, n_err = 0, 0, 0
    for c in targets:
        code = c["code"]
        s = us_matrix.get_series(code)
        note = None
        if not s or not s.get("closes"):
            r = fn({})            # «빈» 결과의 모양도 모듈이 정하게 둔다
            note = "no_series"
            n_no_series += 1
        else:
            s = _cut(s, asof)
            dates = s.get("dates") or []
            if not dates or dates[-1] != asof:
                # 1단계는 「마지막 봉 = 기준일」을 요구한다(screen_trend_template_us.py:182).
                # 여기서 어긋나면 1단계와 다른 자료를 보고 있다는 뜻이다.
                r = fn({})
                note = f"stale:{dates[-1] if dates else 'none'}"
                n_stale += 1
            else:
                try:
                    r = fn(s)
                except Exception as e:   # 한 종목 오류가 전체 런을 멈추지 않게
                    r = {**fn({}), "status": "failed",
                         "reason": f"eval_error:{type(e).__name__}"}
                    note = "eval_error"
                    n_err += 1
        row = {
            "code": code, "name": c.get("name"), "market": c.get("market"),
            "current_price": c.get("current_price"), "rs": c.get("rs"),
            "turnover_eok": c.get("turnover_eok"),
            "gate_near": bool(c.get("gate_near")),
            "gate_near_reasons": c.get("gate_near_reasons") or [],
            "gate_margin": c.get("gate_margin"),
            **r,
        }
        if note:
            row["data_note"] = note
        out_cands.append(row)

    out_cands.sort(key=lambda x: (
        0 if x.get("entry_ready") else 1,
        STATUS_ORDER.get(x.get("status"), 9),
        x.get("pct_to_pivot") if x.get("pct_to_pivot") is not None else 1e9,
    ))
    dist = {k: sum(1 for x in out_cands if x.get("status") == k)
            for k in ("breakout", "actionable", "forming", "failed")}
    n_detected = sum(1 for x in out_cands if x.get(detected_key))
    # 🔴 「진입」의 자가 «둘»이다. 갈라 적는다 — 섞으면 사용자가 못 거는 주문을 센다.
    #  ㉮ 하네스 정의(27.4년이 «진입»으로 «센» 것):
    #     detected ∧ status ∈ ENTRY_STATUSES ∧ pivot_price
    #     (backtest_volatility_pilot_us.py:236 ENTRY_STATUSES={"actionable"} · :288 판정)
    #     ⇒ breakout 은 «빠진다». 사용자 진입은 「장 시작 전 피벗 가격 예약」이라
    #        이미 피벗 «위»면 예약이 안 걸리거나 추격이 된다.
    #  ㉯ 모듈 정의: detected ∧ status ∈ {breakout, actionable} (vcp.py:340 등).
    #     한국 각본이 쓰는 자다. 레코드의 `entry_ready` 필드가 이것 — 모듈 산출이라
    #     «고치지 않는다». 대신 여기서 이름을 갈라 둘 다 찍는다.
    harness_ready = [x for x in out_cands
                     if x.get(detected_key) and x.get("status") in HARNESS_ENTRY_STATUSES
                     and x.get("pivot_price")]
    already_breakout = [x for x in out_cands
                        if x.get(detected_key) and x.get("status") == "breakout"]
    n_ready = len(harness_ready)
    n_module_ready = sum(1 for x in out_cands if x.get("entry_ready"))
    # 검산: 모듈 필드(모듈이 «스스로» 계산)와 내가 status·detected 로 «다시 편» 것이
    # 맞는가. 두 수는 «다른 자료»에서 나오므로 항등식이 아니다 — 모듈이 정의를 바꾸면
    # 여기서 어긋나고, 어긋나면 위 ㉮㉯ 설명이 낡았다는 뜻이다.
    n_recomputed = sum(1 for x in out_cands if x.get(detected_key)
                       and x.get("status") in ("breakout", "actionable"))
    if n_recomputed != n_module_ready:
        print(f"[경고] 모듈 entry_ready {n_module_ready} vs 다시 편 값 {n_recomputed} — "
              "모듈이 entry_ready 정의를 바꿨다. 위 ㉮㉯ 주석을 다시 읽어라.")
    payload = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": asof,
        "market": "US",
        "source": IN_PATH.name,
        "price_source": src.name,
        "price_asof": data_asof,
        # 분모를 «전부» 적는다 — 나중에 「몇 중 몇인가」를 못 찾는 일이 없도록.
        "stage1_evaluated_n": len(all_cands),
        "stage1_all_pass_n": n_pass,
        "stage1_gate_near_n": n_near,
        "input_n": len(targets),
        "no_series_n": n_no_series,
        "stale_bar_n": n_stale,
        "eval_error_n": n_err,
        "params": dict(defaults),   # 넘긴 것이 아니라 «쓰인» 값. 얼린 값 그대로다.
        "detected_key": detected_key,
        "detected_count": n_detected,
        # 「진입」의 자 둘을 «갈라» 싣는다. 어느 것이 하네스 정의인지 같은 줄에 적는다.
        "entry_definition": (
            "하네스 정의 — detected ∧ status ∈ "
            f"{sorted(HARNESS_ENTRY_STATUSES)} ∧ pivot_price "
            "(backtest_volatility_pilot_us.py:236·288). breakout 은 진입이 아니다."),
        "entry_ready_count": n_ready,
        "already_breakout_count": len(already_breakout),
        "already_breakout_note": (
            "이미 돌파 — 27.4년 정의로는 진입 «아님»(피벗 위라 장전 예약이 "
            "안 걸리거나 추격이 된다). 정보로 남긴다."),
        "module_entry_ready_count": n_module_ready,
        "module_entry_ready_note": (
            "모듈(vcp.py:340 등)의 entry_ready = detected ∧ status ∈ "
            "{breakout, actionable}. 한국 각본이 쓰는 자다. "
            "entry_ready_count + already_breakout_count 와 견주는 값이지 "
            "«주문을 거는» 수가 아니다."),
        "status_distribution": dist,
        "candidates": out_cands,
    }
    _write_json(OUT[kind], payload)
    print(f"[저장] {_rel(OUT[kind])}")
    print(f"[{label} 요약] 입력 {len(targets)}종목 | 검출 {n_detected}")
    print(f"          진입 {n_ready} — 하네스 정의(detected + "
          f"{sorted(HARNESS_ENTRY_STATUSES)} + 피벗 있음). 주문을 거는 대상은 이것이다.")
    print(f"          이미 돌파 {len(already_breakout)} — 27.4년 정의로는 진입 «아님»"
          "(피벗 위라 장전 예약이 안 걸리거나 추격이 된다).")
    print(f"          (참고) 모듈 entry_ready {n_module_ready} = 위 둘을 합친 자. "
          "한국 각본이 쓰는 이름이다.")
    print(f"          상태 분포: breakout {dist['breakout']} · "
          f"actionable {dist['actionable']} · forming {dist['forming']} · "
          f"failed {dist['failed']}  (검출 여부와 무관한 «전체» 레코드 수다)")
    if n_no_series or n_stale or n_err:
        print(f"          자료 문제: 시세없음 {n_no_series} · 기준일 어긋남 {n_stale} · "
              f"평가오류 {n_err}")
    if not harness_ready:
        print("  (진입 종목 없음)")
    for x in harness_ready[:30]:
        print(f"  [진입      ] {x['code']:6s} {str(x.get('name'))[:24]:24s} "
              f"RS {x.get('rs')} 피벗 {x.get('pivot_price')} -> {x.get('pct_to_pivot')}%")
    for x in already_breakout[:30]:
        print(f"  [이미돌파  ] {x['code']:6s} {str(x.get('name'))[:24]:24s} "
              f"RS {x.get('rs')} 피벗 {x.get('pivot_price')} -> {x.get('pct_to_pivot')}%"
              "   <- 진입 아님")
    return n_ready


def main() -> None:
    ap = argparse.ArgumentParser(
        description="미국 SEPA 2단계 — 검출기 셋(--kind 로 갈린다)")
    ap.add_argument("--kind", required=True, choices=KINDS)
    args = ap.parse_args()
    run_detector(args.kind)


if __name__ == "__main__":
    main()
