"""피벗 근접 알림 — 대상 고르기와 문구 만들기.

배경: 사용자는 지금 «진입임박» 종목만 자동매수를 예약한다. «예의주시» 종목이
피벗에 다가오는 순간을 알면 그때 예약을 걸 수 있다. 그래서 알림은 매수를
대신하지 않고 «예약을 걸 시점»만 알린다.

밴드는 피벗 아래 2% — 0% 는 포함하지 않는다(이미 닿았으면 예약이 의미 없다).
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import pivot_alert


def _row(code, name, pivot, price, pattern="VCP", status="forming"):
    return {"code": code, "name": name, "pivot_price": pivot,
            "price": price, "pattern": pattern, "status": status}


def test_gap_is_negative_below_pivot():
    """피벗 «아래»는 음수 — 사용자 요청 표기(26-09-17)."""
    g = pivot_alert.signed_gap(16840.0, 17091.0)
    assert abs(g - (-1.4686)) < 0.01


def test_gap_is_positive_above_pivot():
    g = pivot_alert.signed_gap(17500.0, 17091.0)
    assert g > 0


def test_select_band_is_asymmetric():
    """사용자 확정(26-09-17): 아래는 −2%, 넘은 쪽은 +30%.

    아래를 좁게 두는 건 «예약을 걸 자리»가 좁기 때문이고, 위를 넓게 두는 건
    이미 넘어 달리는 종목을 놓치지 않으려는 것이다.
    """
    rows = [_row("A", "가", 100.0, 99.0),       # −1.0% — 든다
            _row("B", "나", 100.0, 125.0)]      # +25.0% — 든다
    got = pivot_alert.select_near_pivot(rows, below_pct=2.0, above_pct=30.0)
    assert {r["code"] for r in got} == {"A", "B"}


def test_select_excludes_too_far_below():
    rows = [_row("C", "다", 100.0, 97.9)]       # −2.1%
    assert pivot_alert.select_near_pivot(rows, below_pct=2.0, above_pct=30.0) == []


def test_select_excludes_too_far_above():
    rows = [_row("D", "라", 100.0, 130.1)]      # +30.1%
    assert pivot_alert.select_near_pivot(rows, below_pct=2.0, above_pct=30.0) == []


def test_select_includes_both_edges():
    rows = [_row("E", "마", 100.0, 98.0),       # 정확히 −2.0%
            _row("F", "바", 100.0, 130.0)]      # 정확히 +30.0%
    assert len(pivot_alert.select_near_pivot(rows, below_pct=2.0, above_pct=30.0)) == 2


def test_select_sorts_by_distance_from_pivot():
    rows = [_row("A", "가", 100.0, 98.2),       # −1.8%
            _row("B", "나", 100.0, 100.5),      # +0.5%
            _row("C", "다", 100.0, 99.0)]       # −1.0%
    got = pivot_alert.select_near_pivot(rows, below_pct=2.0, above_pct=30.0)
    assert [r["code"] for r in got] == ["B", "C", "A"]


def test_select_skips_rows_without_price_or_pivot():
    rows = [_row("A", "가", None, 99.0), _row("B", "나", 100.0, None),
            _row("C", "다", 0.0, 99.0)]
    assert pivot_alert.select_near_pivot(rows, below_pct=2.0, above_pct=30.0) == []


def test_dedup_keeps_nearest_pivot_per_code():
    """한 종목이 두 패턴에 잡히면 피벗이 둘이다(삼성E&A: VCP 51,100 · 3C 51,801).

    먼저 닿는 쪽이 예약을 걸 자리이므로 «가까운» 피벗만 남긴다.
    """
    rows = [_row("028050", "삼성E&A", 51801.0, 50000.0, pattern="3C"),
            _row("028050", "삼성E&A", 51100.0, 50000.0, pattern="VCP")]
    got = pivot_alert.dedup_by_code(rows)
    assert len(got) == 1
    assert got[0]["pivot_price"] == 51100.0
    assert got[0]["pattern"] == "VCP"


def test_message_shape_follows_user_format():
    """사용자 확정 형식(26-09-17): 부호 있는 %% 가 «맨 앞» · 이름 · 현재가 · 패턴·상태 · (피벗).

    종목코드는 넣지 않는다.
    """
    rows = [_row("086670", "비엠티", 17091.0, 16840.0, status="forming")]
    msg = pivot_alert.format_message(rows, now="2026-09-17 09:32", session="정규장")
    line = _stock_lines(msg)[0]
    assert "086670" not in line              # 종목코드 제외
    assert line.lstrip().startswith("-1.47%")  # 퍼센트가 맨 앞
    assert "비엠티" in line
    assert "16,840" in line
    assert "예의주시" in line
    assert line.rstrip().endswith("(17,091)")  # 피벗은 맨 뒤 괄호


def test_message_marks_above_pivot_with_plus():
    rows = [_row("003690", "코리안리", 15469.0, 15498.0, status="breakout")]
    line = _stock_lines(pivot_alert.format_message(rows, now="x", session="정규장"))[0]
    assert line.lstrip().startswith("+0.19%")
    assert line.rstrip().endswith("(15,469)")


def _stock_lines(msg: str) -> list[str]:
    """머리말·칸이름·빈 줄을 뺀 종목 줄만."""
    return [l for l in msg.splitlines()[1:] if l and not l.startswith("[")]


def _sections(msg: str) -> dict[str, list[str]]:
    """[머리말] 별로 종목 이름을 모아 준다."""
    out: dict[str, list[str]] = {}
    cur = None
    for line in msg.splitlines()[1:]:
        if not line:
            continue
        if line.startswith("["):
            cur = line.strip()
            out[cur] = []
        elif cur:
            out[cur].append(line.split()[1])
    return out


def test_message_splits_into_near_and_crossed():
    """−2 ~ +0 은 [피벗 근접], 넘은 것은 전부 [피벗 돌파] (사용자 결정 26-09-17)."""
    rows = [_row("A", "아래", 100.0, 99.0),       # −1.00%
            _row("B", "딱피벗", 100.0, 100.0),    # +0.00% — 근접에 든다
            _row("C", "조금넘음", 100.0, 100.5),  # +0.50%
            _row("D", "많이넘음", 100.0, 108.0)]  # +8.00%
    s = _sections(pivot_alert.format_message(rows, now="x", session="정규장"))
    assert s["[피벗 근접]"] == ["딱피벗", "아래"]
    assert s["[피벗 돌파]"] == ["조금넘음", "많이넘음"]


def test_message_omits_an_empty_section():
    rows = [_row("A", "아래", 100.0, 99.0)]
    s = _sections(pivot_alert.format_message(rows, now="x", session="정규장"))
    assert list(s) == ["[피벗 근접]"]

    rows = [_row("B", "넘음", 100.0, 101.0)]
    s = _sections(pivot_alert.format_message(rows, now="x", session="정규장"))
    assert list(s) == ["[피벗 돌파]"]


def test_message_sorts_each_section_by_closeness_to_pivot():
    rows = [_row("A", "셋", 100.0, 98.2),        # −1.80%
            _row("B", "하나", 100.0, 99.9),      # −0.10%
            _row("C", "둘", 100.0, 99.0),        # −1.00%
            _row("D", "넘둘", 100.0, 110.0),     # +10.00%
            _row("E", "넘하나", 100.0, 104.0)]   # +4.00%
    s = _sections(pivot_alert.format_message(rows, now="x", session="정규장"))
    assert s["[피벗 근접]"] == ["하나", "둘", "셋"]
    assert s["[피벗 돌파]"] == ["넘하나", "넘둘"]


def test_message_when_nothing_qualifies_is_empty():
    """조용할 때는 «아무것도 보내지 않는다» — 1분마다 빈 알림이 오면 안 본다."""
    assert pivot_alert.format_message([], now="2026-09-17 09:32", session="정규장") == ""


def test_message_marks_pre_market_session():
    rows = [_row("086670", "비엠티", 17091.0, 16840.0)]
    msg = pivot_alert.format_message(rows, now="2026-09-17 08:10", session="장 전")
    assert "장 전" in msg


def _raw(**kw):
    base = {"code": "A", "name": "가", "status": "forming",
            "pivot_price": 100.0, "pct_to_pivot": 5.0, "vcp_detected": False,
            "pattern_detected": False, "num_contractions": None,
            "flag_length_days": None, "flag_depth_pct": None}
    base.update(kw)
    return base


# ── 페이지(sepaPatterns.ts classify)와 같은 티어 분류 ───────────

def test_tier_detected_statuses_map_straight_through():
    for st, want in (("breakout", "breakout"), ("actionable", "actionable"),
                     ("forming", "watch")):
        r = _raw(status=st, vcp_detected=True, num_contractions=3)
        assert pivot_alert.classify(r, "vcp") == want


def test_tier_undetected_but_near_pivot_is_watch():
    """페이지의 «넷째 경로» — 검출 안 됐어도 피벗 12% 안 + 구조 성립이면 예의주시."""
    r = _raw(vcp_detected=False, num_contractions=2, pct_to_pivot=11.0)
    assert pivot_alert.classify(r, "vcp") == "watch"


def test_tier_undetected_far_from_pivot_is_hidden():
    r = _raw(vcp_detected=False, num_contractions=2, pct_to_pivot=12.1)
    assert pivot_alert.classify(r, "vcp") is None


def test_tier_undetected_above_pivot_is_hidden():
    """pct_to_pivot 이 음수면 이미 피벗 위 — 페이지도 안 띄운다."""
    r = _raw(vcp_detected=False, num_contractions=2, pct_to_pivot=-0.5)
    assert pivot_alert.classify(r, "vcp") is None


def test_tier_failed_status_is_hidden_on_fourth_path():
    r = _raw(status="failed", vcp_detected=False, num_contractions=2, pct_to_pivot=3.0)
    assert pivot_alert.classify(r, "vcp") is None


def test_structure_ok_vcp_needs_two_contractions():
    assert pivot_alert.classify(_raw(num_contractions=2), "vcp") == "watch"
    assert pivot_alert.classify(_raw(num_contractions=1), "vcp") is None
    assert pivot_alert.classify(_raw(num_contractions=None), "vcp") is None


def test_structure_ok_powerplay_needs_flag_length_and_depth():
    ok = _raw(flag_length_days=12, flag_depth_pct=15.0)
    assert pivot_alert.classify(ok, "powerplay") == "watch"
    assert pivot_alert.classify(_raw(flag_length_days=12, flag_depth_pct=0), "powerplay") is None
    assert pivot_alert.classify(_raw(flag_length_days=0, flag_depth_pct=15.0), "powerplay") is None


def test_structure_ok_3c_needs_only_a_pivot():
    assert pivot_alert.classify(_raw(), "3c") == "watch"
    assert pivot_alert.classify(_raw(pivot_price=None), "3c") is None


# ── 감시 대상 제한 (사용자 결정 26-09-17) ─────────────────────

def test_monitor_tiers_cover_every_source_file():
    """빠뜨린 파일이 없어야 한다 — 없으면 조용히 감시에서 사라진다."""
    assert set(pivot_alert.MONITOR_TIERS) == set(pivot_alert.SOURCES)


def test_monitor_vcp_takes_all_three_tiers():
    allow = pivot_alert.MONITOR_TIERS["sepa-vcp-candidates.json"]
    assert allow == {"breakout", "actionable", "watch"}


def test_monitor_3c_takes_only_actionable():
    allow = pivot_alert.MONITOR_TIERS["sepa-3c-candidates.json"]
    assert allow == {"actionable"}


def test_monitor_powerplay_trend_takes_all_but_all_universe_is_dropped():
    assert pivot_alert.MONITOR_TIERS["sepa-power-play-candidates.json"] == {
        "breakout", "actionable", "watch"}
    assert pivot_alert.MONITOR_TIERS["sepa-power-play-all-candidates.json"] == set()


def test_monitored_is_page_classification_plus_the_tier_filter():
    """감시 판정은 «페이지 분류»를 깎지 않고 그 «위에» 얹는다.

    깎아 버리면 페이지와 어긋난 것인지 일부러 뺀 것인지 구분이 안 된다.
    """
    raw = {"code": "A", "status": "forming", "pivot_price": 100.0,
           "pct_to_pivot": 5.0, "vcp_detected": True}
    assert pivot_alert.classify(raw, "vcp") == "watch"          # 페이지엔 뜬다
    assert pivot_alert.is_monitored(raw, "sepa-vcp-candidates.json", "vcp")
    assert not pivot_alert.is_monitored(raw, "sepa-3c-candidates.json", "3c")


def test_telegram_request_targets_the_bot_and_chat():
    url, body = pivot_alert.build_telegram_request("123:ABC", "555", "안녕")
    assert url == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert body["chat_id"] == "555"
    assert body["text"] == "안녕"


def test_telegram_request_disables_link_preview():
    """종목명이 링크로 잡혀 미리보기가 붙으면 알림이 길어진다."""
    _, body = pivot_alert.build_telegram_request("t", "c", "x")
    assert body.get("disable_web_page_preview") is True


def test_telegram_needs_both_token_and_chat_id():
    import pytest
    with pytest.raises(RuntimeError, match="TELEGRAM"):
        pivot_alert.build_telegram_request("", "555", "안녕")
    with pytest.raises(RuntimeError, match="TELEGRAM"):
        pivot_alert.build_telegram_request("123:ABC", "", "안녕")
