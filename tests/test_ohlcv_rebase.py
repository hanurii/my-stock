"""FDR 보충일에 기준가가 바뀐 종목(액면분할·주식병합·감자)의 과거 시세 환산.

배경 (2026-07-31 실사고):
  수정주가 복원(_apply_adjustment)은 pdata 로 만든 시계열에만 돌고,
  --fill-fdr 로 덧붙이는 최신일은 그 체인 밖에 있다. 그래서 그날 기준가가
  바뀐 종목은 "옛 기준 과거 + 새 기준 하루"가 되어 가짜 점프가 생겼다.
    금호전기  캐시 894 ← 실제 4,470  → 재개일 +360% 로 표시
    GMI벤처   캐시 481 ← 실제 2,405  → +380%
    남영비비안 캐시 7,800 ← 실제 3,905 → -35%
  이 가짜 급등이 위로 터지면 200일선·52주 신고가·RS 가 전부 틀어져
  "하루에 +360% 오른 초강세주"로 후보에 오를 수 있다.

판별자: FDR 을 캐시 최신일 '포함' 으로 받아오므로 겹치는 하루가 생긴다.
  그 겹침 바의 종가 ÷ 캐시 종가 = 기준가 변경 비율.
  정상 종목은 정확히 1.0, 기준가가 바뀐 종목만 5.0 / 0.5 처럼 튄다.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib import ohlcv_matrix


def _series(closes):
    """종가 리스트로 최소 시계열 구성 (고·저·시가는 종가와 같은 배수)."""
    n = len(closes)
    return {
        "dates": [f"2026-07-{i + 20:02d}" for i in range(n)],
        "timestamps": [0] * n,
        "closes": list(closes),
        "opens": list(closes),
        "highs": [c * 1.02 for c in closes],
        "lows": [c * 0.98 for c in closes],
        "volumes": [1000] * n,
    }


def test_rebase_ratio_detects_stock_merge():
    # 금호전기: 캐시 894(옛 기준) vs FDR 4,470(5:1 병합 후) → 5.0
    assert ohlcv_matrix.detect_rebase_ratio(894.0, 4470.0) == 5.0


def test_rebase_ratio_detects_stock_split():
    # 남영비비안: 캐시 7,800 vs FDR 3,905(1:2 분할 후) → 0.5 근방
    r = ohlcv_matrix.detect_rebase_ratio(7800.0, 3905.0)
    assert r is not None and abs(r - 0.5) < 0.01


def test_rebase_ratio_none_for_normal_stock():
    # 정상 종목은 pdata 복원 종가와 FDR 수정주가가 일치 → 환산 불필요
    assert ohlcv_matrix.detect_rebase_ratio(207000.0, 207000.0) is None


def test_rebase_ratio_ignores_rounding_noise():
    # 반올림 수준(0.1%)의 차이는 기업행위가 아니다
    assert ohlcv_matrix.detect_rebase_ratio(3000.0, 3002.0) is None


def test_rebase_ratio_rejects_absurd_ratio():
    # 데이터 오류로 보이는 극단 비율은 환산하지 않는다(과거를 망치지 않기 위해)
    assert ohlcv_matrix.detect_rebase_ratio(1.0, 100000.0) is None


def test_rebase_ratio_handles_missing_price():
    assert ohlcv_matrix.detect_rebase_ratio(0.0, 4470.0) is None
    assert ohlcv_matrix.detect_rebase_ratio(894.0, None) is None


def test_rebase_history_scales_all_price_fields():
    s = _series([100.0, 110.0, 120.0])
    ohlcv_matrix.rebase_history(s, 5.0)
    assert s["closes"] == [500.0, 550.0, 600.0]
    assert s["opens"] == [500.0, 550.0, 600.0]
    assert abs(s["highs"][0] - 510.0) < 0.01
    assert abs(s["lows"][0] - 490.0) < 0.01


def test_rebase_history_leaves_volume_alone():
    # 거래량은 상대 비교용이라 환산 대상이 아니다(주식 수 변화는 별개 이슈)
    s = _series([100.0, 110.0])
    ohlcv_matrix.rebase_history(s, 5.0)
    assert s["volumes"] == [1000, 1000]


def test_rebase_history_upto_leaves_newest_bar_alone():
    """사후 복구: 이미 새 기준으로 붙은 마지막 바는 건드리지 않는다."""
    s = _series([894.0, 894.0, 4115.0])   # 앞 2일 옛 기준, 마지막은 새 기준
    ohlcv_matrix.rebase_history(s, 5.0, upto=2)
    assert s["closes"] == [4470.0, 4470.0, 4115.0]


def test_merge_gap_disappears_after_rebase():
    """실사고 재현: 옛 기준 과거에 새 기준 하루를 붙이면 +400% 가짜 점프.

    환산 후에는 실제 등락(4,470 → 4,115 = -7.9%)만 남아야 한다.
    """
    s = _series([894.0, 894.0, 894.0])          # 정지 중 동결(옛 기준)
    fdr_overlap_close = 4470.0                   # FDR 이 준 같은 날 종가(새 기준)
    ratio = ohlcv_matrix.detect_rebase_ratio(s["closes"][-1], fdr_overlap_close)
    assert ratio == 5.0
    ohlcv_matrix.rebase_history(s, ratio)

    s["closes"].append(4115.0)                   # 재개일 종가(새 기준)
    jump = (s["closes"][-1] - s["closes"][-2]) / s["closes"][-2] * 100
    assert -10 < jump < 0, f"환산 후에도 가짜 점프가 남음: {jump:+.1f}%"
