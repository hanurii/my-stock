"""미너비니 VCP(변동성 수축 패턴) 평가 부품 (순수 함수).

개념(VCP·피벗·수축·거래량 마름)=마크 미너비니. 구체 수치·계산규칙=이 프로젝트의
공학적 번역(원전 아님). 정의·근거: docs/superpowers/specs/2026-06-29-find-vcp-design.md
"""
from __future__ import annotations

DEFAULT_PARAMS: dict = {
    "lookback_days": 120,
    "zigzag_pct": 8.0,
    "min_base_days": 10,
    "contraction_tol": 1.15,
    "max_final_depth": 10.0,
    "breakout_vol_mult": 1.4,
    "near_pivot_pct": 5.0,
    "base_vol_cap": 50,
    "zigzag_k": 4.0,
    "zigzag_k2": 2.5,   # 2-pass retry k: 선행급등이 변동성 부풀리면 재시도
    "dry_max": 0.82,    # 우측 거래량 마름 기준 (MA50 대비 최댓값 허용; 켐트로스 dry_min=0.816)
}


def zigzag(values: list[float], pct: float) -> list[tuple[int, float, str]]:
    """퍼센트-역행 ZigZag. 교대 피벗 (index, price, kind) 리스트.

    시작점은 첫 확정 레그 방향에 따라 high/low 로 포함되고, 끝에는 진행 중인
    마지막 극점을 닫는 피벗으로 추가한다.
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [(0, values[0], "high")]
    thr = pct / 100.0
    pivots: list[tuple[int, float, str]] = []
    ext_idx, ext_val = 0, values[0]
    direction = 0  # 0 미정, 1 상승레그(ext=고점후보), -1 하락레그(ext=저점후보)
    for i in range(1, n):
        v = values[i]
        if direction == 0:
            if v >= ext_val * (1 + thr):
                pivots.append((0, values[0], "low"))
                direction, ext_idx, ext_val = 1, i, v
            elif v <= ext_val * (1 - thr):
                pivots.append((0, values[0], "high"))
                direction, ext_idx, ext_val = -1, i, v
            elif v > ext_val:
                ext_idx, ext_val = i, v
        elif direction == 1:
            if v > ext_val:
                ext_idx, ext_val = i, v
            elif v <= ext_val * (1 - thr):
                pivots.append((ext_idx, ext_val, "high"))
                direction, ext_idx, ext_val = -1, i, v
        else:  # direction == -1
            if v < ext_val:
                ext_idx, ext_val = i, v
            elif v >= ext_val * (1 + thr):
                pivots.append((ext_idx, ext_val, "low"))
                direction, ext_idx, ext_val = 1, i, v
    closing = "high" if direction == 1 else "low"
    pivots.append((ext_idx, ext_val, closing))
    return pivots


def volume_ma(volumes: list[float], window: int = 50) -> list[float]:
    """Trailing moving average of volumes. Handles partial windows."""
    out: list[float] = []
    for i in range(len(volumes)):
        seg = volumes[max(0, i - window + 1):i + 1]
        out.append(sum(seg) / len(seg) if seg else 0.0)
    return out


def adaptive_zigzag(values: list[float], k: float = 4.0) -> list[tuple[int, float, str]]:
    """베이스 변동성(평균 일간 절대등락%)에 비례한 임계로 zigzag 실행. 하한 없음."""
    n = len(values)
    if n < 2:
        return zigzag(values, 8.0)
    rets = [abs(values[i] / values[i - 1] - 1) * 100.0 for i in range(1, n) if values[i - 1]]
    vol = (sum(rets) / len(rets)) if rets else 0.0
    thr = k * vol if vol > 0 else 8.0
    return zigzag(values, thr)


def find_contractions(pivots: list[tuple[int, float, str]]) -> list[float]:
    """인접한 (고점 → 바로 다음 저점) 쌍의 되돌림 깊이%를 시간순으로."""
    depths: list[float] = []
    for a, b in zip(pivots, pivots[1:]):
        if a[2] == "high" and b[2] == "low":
            high, low = a[1], b[1]
            if high > 0:
                depths.append((high - low) / high * 100.0)
    return depths


def find_contraction_chain(swings: list[tuple[int, float, str]], tol: float = 1.15) -> dict | None:
    """끝쪽의 수렴하는 (고→저) 수축 연쇄. base_start=첫 수축 고점, pivot=마지막 수축 고점.

    last_lo_idx: 마지막 수축 저점의 closes 인덱스 (피벗 산출에 사용).
    """
    pairs = []  # (hi_idx, hi_price, lo_idx, lo_price, depth%)
    for a, b in zip(swings, swings[1:]):
        if a[2] == "high" and b[2] == "low" and a[1] > 0:
            pairs.append((a[0], a[1], b[0], b[1], (a[1] - b[1]) / a[1] * 100.0))
    if not pairs:
        return None
    chain = [pairs[-1]]
    for prev in reversed(pairs[:-1]):
        # 시간순으로 깊이가 얕아지는(수렴) 동안만 연쇄에 포함: later <= prev*tol
        if chain[0][4] <= prev[4] * tol:
            chain.insert(0, prev)
        else:
            break
    return {
        "base_start": chain[0][0],
        "pivot": round(chain[-1][1], 2),
        "last_lo_idx": chain[-1][2],   # 마지막 수축 저점 인덱스 (참고용; 피벗은 chain["pivot"] 사용)
        "depths": [round(c[4], 2) for c in chain],
        "count": len(chain),
    }


def _is_breakout(closes, opens, vols, ma50, pivot, p) -> bool:
    """마지막 바가 돌파인가: 첫돌파+양봉+거래량터짐+근접(시가 기준).

    근접 판단을 시가(open)로 하는 이유: 갭업 돌파(전일 피벗 아래→당일 갭업)에서
    종가는 피벗에서 멀리 떨어지더라도 시가는 피벗 근처에서 출발하기 때문.
    """
    i = len(closes) - 1
    if pivot is None or i < 1:
        return False
    if not (closes[i] > pivot and closes[i - 1] <= pivot):   # 첫돌파
        return False
    if not (closes[i] > opens[i]):                            # 양봉
        return False
    m = ma50[i] if i < len(ma50) else None
    if not (m and vols[i] >= m * p["breakout_vol_mult"]):     # 거래량 터짐
        return False
    if (opens[i] - pivot) / pivot * 100.0 > p["near_pivot_pct"]:  # 피벗 근접(시가 기준)
        return False
    return True


def _mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def evaluate_vcp(series: dict, params: dict | None = None) -> dict:
    """VCP 종합 판정.

    series 키: dates, closes, highs, lows, opens, volumes.
    반환 dict 키: vcp_detected, num_contractions, contractions,
    base_length_days, base_depth_pct, pivot_price, pct_to_pivot,
    volume_dryup_ratio, tightness_pct, status, swings, reason, entry_ready.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    lb = p["lookback_days"]
    closes = (series.get("closes") or [])[-lb:]
    highs = (series.get("highs") or [])[-lb:]
    lows = (series.get("lows") or [])[-lb:]
    vols = (series.get("volumes") or [])[-lb:]
    opens = (series.get("opens") or [])[-lb:]
    dates = (series.get("dates") or [])[-lb:]

    base: dict = {
        "vcp_detected": False, "num_contractions": 0, "contractions": [],
        "base_length_days": 0, "base_depth_pct": None, "pivot_price": None,
        "pct_to_pivot": None, "volume_dryup_ratio": None, "tightness_pct": None,
        "status": "forming", "swings": [], "reason": None, "entry_ready": False,
    }
    if len(closes) < p["min_base_days"]:
        base["reason"] = "no_data" if not closes else "base_too_short"
        return base

    swings = adaptive_zigzag(closes, p["zigzag_k"])
    chain = find_contraction_chain(swings, p["contraction_tol"])

    # 2-pass: 선행급등이 전구간 변동성을 부풀려 임계가 너무 높을 때, 낮은 k로 재시도.
    # 이미 chain_cnt >= 2이면 재시도 불필요(2차 다올처럼 고변동성이지만 잘 잡히는 경우 보호).
    if (chain is None or chain["count"] < 2) and p.get("zigzag_k2"):
        swings2 = adaptive_zigzag(closes, p["zigzag_k2"])
        chain2 = find_contraction_chain(swings2, p["contraction_tol"])
        if chain2 is not None and (chain is None or chain2["count"] > chain["count"]):
            swings, chain = swings2, chain2

    base["swings"] = [{"date": dates[i] if i < len(dates) else None, "price": round(pr, 2), "kind": k}
                      for i, pr, k in swings]
    if not chain:
        base["reason"] = "no_contraction_chain"
        return base

    bs = chain["base_start"]; depths = chain["depths"]; T = chain["count"]

    # 피벗 = 횡보 천장(저항선): 베이스 구간에서 '돌파 바(마지막 봉)'를 제외한 종가 최고치.
    #  - 평가당 1회만 산출하는 '안정 레벨'이다(바마다 갱신하는 러닝맥스 아님). 러닝맥스를 쓰면
    #    closes[-2]<=pivot 이 항상 참이 되어 첫돌파 가드(_is_breakout)가 무효화된다(과거 회귀).
    #  - 베이스 전체(base_start~돌파 직전)의 천장을 쓰므로 '계단식 VCP'에서 우측 회복이
    #    마지막 수축 고점을 이미 넘었어도, 진짜 저항선(베이스 최고가) 최초 돌파를 정확히 잡는다.
    #  - 종가 기준(고가 아님): 장중 스파이크 고가(예: 한솔케미칼 ~309500)를 천장으로 오인하지 않도록.
    n = len(closes)
    ceiling_seg = closes[bs:n - 1]
    pivot = round(max(ceiling_seg), 2) if ceiling_seg else chain["pivot"]

    base["num_contractions"] = T
    base["contractions"] = depths
    base["base_length_days"] = len(closes) - bs
    bl = lows[bs:]; bv = vols[bs:]
    ma50 = volume_ma(vols, 50)
    base_ma50 = ma50[bs:]
    last_close = closes[-1]

    base["pivot_price"] = pivot
    if pivot:
        base["pct_to_pivot"] = round((pivot - last_close) / pivot * 100.0, 2)
    base["volume_dryup_ratio"] = (round((_mean(vols[-5:]) or 0.0) / ma50[-1], 3) if ma50 and ma50[-1] else None)
    tight = _mean([(highs[i] - lows[i]) / closes[i] * 100.0 for i in range(len(closes))[-10:] if closes[i]])
    base["tightness_pct"] = round(tight, 2) if tight is not None else None

    cond_count = 2 <= T <= 6
    cond_mono = all(depths[i] <= depths[i - 1] * p["contraction_tol"] for i in range(1, T)) if T >= 2 else False
    # 순(net) 수축 가드: 마지막 수축이 첫 수축보다 '실제로' 얕아야 한다(변동성 수축의 본질).
    # cond_mono는 단계마다 tol(1.15) 만큼 깊어지는 것을 허용하므로 [11.8,13.4,13.2,14.2]처럼
    # 평탄/확장하는 가짜 수축(예: 기가비스)을 통과시킨다 → 순수축 조건으로 정밀도를 높인다.
    cond_converge = depths[-1] < depths[0] if T >= 2 else False
    third = max(1, len(bv) // 3)
    right_ratios = [bv[i] / base_ma50[i] for i in range(len(bv))[-third:] if i < len(base_ma50) and base_ma50[i]]
    dry_min = min(right_ratios) if right_ratios else 9.9
    cond_dry = dry_min <= p["dry_max"]
    base["vcp_detected"] = bool(cond_count and cond_mono and cond_converge and cond_dry)
    if base["vcp_detected"]:
        base["base_depth_pct"] = round(max(depths), 2)
    else:
        base["reason"] = ("contraction_count_not_2_6" if not cond_count
                          else "not_monotone_contraction" if not cond_mono
                          else "contraction_not_converging" if not cond_converge
                          else "volume_not_drying")

    base_low = min(bl) if bl else last_close
    mono_violated = T >= 2 and depths[-1] > depths[-2] * p["contraction_tol"]
    if _is_breakout(closes, opens, vols, ma50, pivot, p):
        base["status"] = "breakout"
    elif mono_violated or last_close < base_low:
        base["status"] = "failed"
    elif (base["pct_to_pivot"] is not None and 0 <= base["pct_to_pivot"] <= p["near_pivot_pct"]
          and (base["volume_dryup_ratio"] if base["volume_dryup_ratio"] is not None else 9.9) <= 1.0):
        base["status"] = "actionable"
    else:
        base["status"] = "forming"
    base["entry_ready"] = bool(base["vcp_detected"] and base["status"] in ("breakout", "actionable"))
    return base
