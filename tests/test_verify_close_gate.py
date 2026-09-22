"""캐시 종가 관문 — 배선 밖의 자(거래소 기준가)로 재는 검사의 순수 로직.

배경 (2026-09-14~22 실사고):
  애프터마켓 개장으로 종가가 둘이 됐다(정규장 / 통합). 어느 출처가 어느 쪽을
  주는지 26-09-16 에 거꾸로 적었고, 그 믿음으로 넣은 고침이 09-14~09-21 캐시
  종가의 60~66% 를 어긋나게 했다. 틀린 줄 몰랐던 까닭은 «고른 두 출처끼리만»
  맞대 봤기 때문이다 — 둘 다 틀렸을 경우를 그 비교는 못 가른다.

그래서 이 관문의 자는 채우기 사슬(pdata·FDR) 밖에 있다:
  기준가(D) = 종가(D) − prdy_vrss(D) 이고 기준가는 정의상 전일 정규장 종가다.
  연쇄가 깨지면 «판정하지 않는다» — 자가 안 선 판은 결과를 읽지 않는다.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import verify_close_gate as g


# ── 한 쌍 가르기 ─────────────────────────────────────────────

def test_exact_match_is_match():
    assert g.classify_pair(10000.0, 10000.0) == "match"


def test_rounding_noise_stays_match():
    """수정주가 복원은 소수 둘째 자리에서 끊는다 — 그 잔차를 어긋남으로 세지 않는다."""
    assert g.classify_pair(10001.0, 10000.0) == "match"      # 0.01%


def test_aftermarket_sized_gap_is_diverge():
    """실측 중앙 0.7~0.9% — 통합 종가가 섞이면 이 크기로 어긋난다."""
    assert g.classify_pair(10080.0, 10000.0) == "diverge"    # 0.80%


def test_split_sized_gap_is_corp_action_not_diverge():
    """액면분할은 «종가가 틀린» 게 아니라 «기준이 다른» 것이다 — 따로 센다."""
    assert g.classify_pair(2000.0, 10000.0) == "corp_action"


def test_zero_reference_is_unknown_not_match():
    """자가 0 이면 비율을 못 낸다. 못 내는 것을 «맞음»으로 세지 않는다."""
    assert g.classify_pair(10000.0, 0.0) == "unknown"


# ── 세기 ─────────────────────────────────────────────────────

def test_corp_action_is_excluded_from_denominator():
    """기업행위를 분모에 넣으면 분할 많은 날 관문이 저절로 시끄러워진다."""
    t = g.tally([(10000.0, 10000.0), (10000.0, 10000.0), (2000.0, 10000.0)])
    assert t["n"] == 2 and t["corp_action"] == 1 and t["rate"] == 0.0


def test_diverge_rate_counts_only_real_divergence():
    t = g.tally([(10080.0, 10000.0)] + [(10000.0, 10000.0)] * 3)
    assert t["diverge"] == 1 and t["n"] == 4 and t["rate"] == 25.0


def test_empty_pairs_do_not_divide_by_zero():
    assert g.tally([])["rate"] == 0.0


# ── 양성 대조: 자가 서는가 ───────────────────────────────────

def test_chain_holds_when_base_equals_previous_close():
    c = g.chain_ok([1000.0, 1100.0, 1050.0], [990.0, 1000.0, 1100.0])
    assert c["n"] == 2 and c["bad"] == 0


def test_chain_breaks_when_base_disagrees():
    c = g.chain_ok([1000.0, 1100.0], [990.0, 1080.0])
    assert c["bad"] == 1


# ── 판정 ─────────────────────────────────────────────────────

def test_broken_chain_yields_inconclusive_not_pass():
    """자가 안 섰으면 「통과」도 「실패」도 아니다 — 못 가림이다."""
    _msg, code = g.verdict({"n": 100, "diverge": 0, "rate": 0.0}, {"n": 50, "bad": 3})
    assert code == 2


def test_no_pairs_yields_inconclusive():
    _msg, code = g.verdict({"n": 0, "diverge": 0, "rate": 0.0}, {"n": 50, "bad": 0})
    assert code == 2


def test_clean_cache_passes():
    _msg, code = g.verdict({"n": 200, "diverge": 0, "rate": 0.0}, {"n": 50, "bad": 0})
    assert code == 0


def test_contaminated_cache_fails():
    """09-14~09-21 실측(60~66%)이 이 관문을 지나갔어야 «안» 된다."""
    _msg, code = g.verdict({"n": 200, "diverge": 126, "rate": 63.0}, {"n": 50, "bad": 0})
    assert code == 1


def test_threshold_edge_just_below_passes():
    _msg, code = g.verdict({"n": 200, "diverge": 10, "rate": 5.0}, {"n": 50, "bad": 0})
    assert code == 0


# ── 문턱을 결과 보고 고치지 못하게 ───────────────────────────

def test_thresholds_are_the_preregistered_ones():
    """사전 등록한 수다. 바꾸려면 이 시험을 «먼저» 고쳐야 한다 — 그러면 눈에 띈다."""
    assert (g.DIVERGE_PCT, g.CORP_ACTION_PCT, g.FAIL_ABOVE_RATE) == (0.2, 5.0, 5.0)


# ── 표본 고르기 ──────────────────────────────────────────────

def test_sample_is_reproducible_within_a_day():
    codes = [f"{i:06d}" for i in range(500)]
    assert g.pick_sample(codes, 40, "20260922") == g.pick_sample(codes, 40, "20260922")


def test_sample_moves_across_days():
    """한 표본에 고정하면 그 밖은 영원히 안 쓸린다."""
    codes = [f"{i:06d}" for i in range(500)]
    assert g.pick_sample(codes, 40, "20260922") != g.pick_sample(codes, 40, "20260923")


def test_sample_never_exceeds_the_pool():
    assert len(g.pick_sample(["000001", "000002"], 40, "20260922")) == 2
