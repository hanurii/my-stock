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


def test_default_band_matches_the_user_decision():
    """아래 −3% · 위 +30% (26-09-18 −2 에서 −3 으로 넓힘).

    계기: 케이씨가 −2.80% 로 0.8%p 모자라 안 떴다. −2% 가 실제로 써 보니 좁았다.
    """
    assert pivot_alert.DEFAULT_BELOW_PCT == 3.0
    assert pivot_alert.DEFAULT_ABOVE_PCT == 30.0


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


# ── 장중 거래량 폭발 (사용자 결정 26-09-20) ───────────────────

def test_volume_measured_only_during_regular_session():
    """09:00 전에는 안 재도 된다 — 통합(UN) 조회가 거래량을 안 준다.

    정규장에는 «꼭» 재야 한다(사용자 결정). 정규장 밖에서 재면 분자에
    애프터마켓이 섞여 분모(정규장 일봉)와 기준이 갈린다 — 26-09-20 실측:
    삼성전자 KIS acml_vol 이 캐시 09-18 거래량의 1.163배(다른 다섯은 1.000).
    """
    assert pivot_alert.should_measure_volume(_at(9, 0))
    assert pivot_alert.should_measure_volume(_at(13, 0))
    assert pivot_alert.should_measure_volume(_at(15, 30))
    assert not pivot_alert.should_measure_volume(_at(8, 59))
    assert not pivot_alert.should_measure_volume(_at(15, 31))
    assert not pivot_alert.should_measure_volume(_at(18, 0))


def test_volume_multiple_projects_to_a_full_day():
    """09:30 에 하루치의 20.8%가 나온다 — 누적을 그 비율로 나눠 하루로 환산한다.

    환산을 안 하면 이른 시각에는 모든 종목이 「거래량 없음」으로 보인다.
    """
    m = pivot_alert.volume_multiple(acml_vol=2080, day_frac=0.208, avg_vol=10000)
    assert abs(m - 1.0) < 1e-9          # 2080/0.208 = 10,000 = 평균과 같다
    m2 = pivot_alert.volume_multiple(acml_vol=8320, day_frac=0.208, avg_vol=10000)
    assert abs(m2 - 4.0) < 1e-9


def test_volume_multiple_is_none_when_inputs_missing():
    assert pivot_alert.volume_multiple(None, 0.2, 10000) is None
    assert pivot_alert.volume_multiple(1000, 0.2, 0) is None
    assert pivot_alert.volume_multiple(1000, 0, 10000) is None


def test_average_volume_excludes_today():
    """분모는 «지난» N일이다. 오늘을 넣으면 오늘 폭발이 분모를 키워 배수를 눌러 버린다."""
    series = {"dates": ["d1", "d2", "d3", "d4"], "volumes": [100, 200, 300, 9999]}
    assert pivot_alert.avg_recent_volume(series, window=3, today="d4") == 200.0


def test_average_volume_needs_enough_days():
    series = {"dates": ["d1", "d2"], "volumes": [100, 200]}
    assert pivot_alert.avg_recent_volume(series, window=20, today="d2") is None


def test_line_shows_volume_multiple_when_measured():
    r = _row("A", "가", 100.0, 99.0)
    r["vol_mult"] = 4.2
    line = pivot_alert.format_message([r], now="x", session="정규장(KRX)").splitlines()[2]
    assert "거래량 4.2배" in line


def test_premarket_denominator_uses_same_time_of_day():
    """프리마켓은 «같은 시각까지의» 프리마켓 누적과 견준다.

    정규장 20일 평균을 분모로 쓰면 늘 0.0X 배가 나온다 — 프리마켓 거래량이
    정규장 하루의 1~10% 수준이기 때문이다(26-09-21 실측).
    """
    hist = {"20260916": {"0810": 100, "0830": 300, "0840": 400},
            "20260917": {"0810": 200, "0830": 500, "0840": 600},
            "20260918": {"0810": 300, "0830": 700, "0840": 800}}
    assert pivot_alert.premarket_baseline(hist, "0830") == 500.0     # 중앙 300/500/700
    assert pivot_alert.premarket_baseline(hist, "0810") == 200.0


def test_premarket_denominator_uses_last_bar_at_or_before_now():
    """그 시각 정각 봉이 없으면 «그 이전 마지막» 누적을 쓴다(누적이라 단조)."""
    hist = {"20260918": {"0810": 300, "0830": 700}}
    assert pivot_alert.premarket_baseline(hist, "0829") == 300.0
    assert pivot_alert.premarket_baseline(hist, "0805") is None      # 그 전엔 자료 없음


def test_premarket_denominator_skips_days_with_no_trading():
    """휴일은 빈 칸으로 기록된다 — 세면 분모가 눌린다."""
    hist = {"20260918": {"0830": 700}, "20260919": {}, "20260920": {}}
    assert pivot_alert.premarket_baseline(hist, "0830") == 700.0


def test_line_marks_stocks_with_no_nxt_trade():
    """NXT 에서 체결이 없으면 «전일 종가»가 실시간 값처럼 보인다 — 맨 앞에 (전).

    26-09-21 08:2x 실측: 감시 57종목 중 31종목이 프리마켓 체결 없음.
    절반 이상이 전일 종가였는데 그게 드러나지 않았다.
    """
    r = _row("A", "가", 100.0, 99.0)
    r["no_trade"] = True
    line = pivot_alert.format_message([r], now="x", session="장 전(NXT 통합)").splitlines()[2]
    assert line.startswith("(전) ")


def test_line_has_no_marker_when_the_stock_traded():
    r = _row("A", "가", 100.0, 99.0)
    r["no_trade"] = False
    line = pivot_alert.format_message([r], now="x", session="장 전(NXT 통합)").splitlines()[2]
    assert not line.startswith("(전)")


def test_line_omits_volume_when_not_measured():
    line = pivot_alert.format_message([_row("A", "가", 100.0, 99.0)],
                                      now="x", session="장 전(NXT 통합)").splitlines()[2]
    assert "거래량" not in line


# ── 폴링 간격 (사용자 결정 26-09-18) ──────────────────────────

def test_regular_session_polls_fast():
    """정규장 09:00~15:30 내내 빠른 주기 (사용자 결정 26-09-18, 09:30 에서 넓힘)."""
    for h, m in ((9, 0), (9, 30), (12, 0), (15, 29), (15, 30)):
        assert pivot_alert.poll_interval(_at(h, m), base=60, fast=15) == 15


def test_outside_regular_session_uses_base_interval():
    """장 전(NXT)·장후·애프터마켓은 기본 주기 — 거래가 얇아 15초가 아깝다."""
    assert pivot_alert.poll_interval(_at(8, 59), base=60, fast=15) == 60
    assert pivot_alert.poll_interval(_at(15, 31), base=60, fast=15) == 60
    assert pivot_alert.poll_interval(_at(19, 0), base=60, fast=15) == 60


def test_fast_interval_never_exceeds_base():
    """빠른 간격이 기본보다 크면 뜻이 없다 — 작은 쪽을 쓴다."""
    assert pivot_alert.poll_interval(_at(9, 10), base=10, fast=15) == 10


def test_sleep_subtracts_the_time_the_poll_took():
    """간격은 «주기»다. 조회가 7초 걸렸으면 15초 주기는 8초를 쉬어야 한다."""
    assert pivot_alert.sleep_seconds(interval=15, elapsed=7.0) == 8.0
    assert pivot_alert.sleep_seconds(interval=15, elapsed=0.0) == 15.0


def test_sleep_is_never_negative():
    """조회가 간격보다 오래 걸리면 쉬지 않고 바로 다음 바퀴로."""
    assert pivot_alert.sleep_seconds(interval=15, elapsed=22.0) == 0.0


# ── 시세 계열 고르기 (사용자 결정 26-09-18) ───────────────────

def _at(h, m):
    from datetime import datetime
    return datetime(2026, 9, 18, h, m, tzinfo=pivot_alert.KST)


def test_regular_session_uses_krx_quote():
    """정규장에는 피벗과 «같은 계열»인 KRX(J)로 잰다 — 피벗이 정규장 일봉에서 나왔다."""
    assert pivot_alert.quote_market_div(_at(9, 0)) == "J"
    assert pivot_alert.quote_market_div(_at(12, 0)) == "J"
    assert pivot_alert.quote_market_div(_at(15, 30)) == "J"


def test_premarket_uses_nxt_only_quote():
    """프리마켓은 NXT «단독»(NX)으로 받는다 — 체결 유무를 갈라야 하기 때문이다.

    UN 은 체결이 없으면 «전일 종가»로 덮어 주므로 「안 움직인 것」과
    「거래가 없는 것」이 구분되지 않는다(26-09-21 실측: 감시 57 중 31종목 무체결).
    """
    assert pivot_alert.quote_market_div(_at(8, 0)) == "NX"
    assert pivot_alert.quote_market_div(_at(8, 59)) == "NX"


def test_after_hours_uses_integrated_quote():
    """장 마감 뒤에는 J 가 15:30 에 멈춘다 — 통합(UN)을 쓴다.

    26-09-18 16:10 실측: 케이씨 J 41,300(=당일 정규장 종가) vs UN 41,000(MTS 와 일치).
    """
    assert pivot_alert.quote_market_div(_at(15, 31)) == "UN"
    assert pivot_alert.quote_market_div(_at(16, 10)) == "UN"
    assert pivot_alert.quote_market_div(_at(19, 55)) == "UN"


def test_message_names_the_quote_series():
    """어느 계열로 잰 값인지 문구에 남긴다 — 두 계열이 갈릴 때 구분이 안 되면 위험하다."""
    rows = [_row("A", "가", 100.0, 99.0)]
    head = pivot_alert.format_message(rows, now="x", session="장 전(NXT 통합)").splitlines()[0]
    assert "NXT 통합" in head


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


def test_monitor_powerplay_trend_takes_all_tiers():
    assert pivot_alert.MONITOR_TIERS["sepa-power-play-candidates.json"] == {
        "breakout", "actionable", "watch"}


def test_monitor_powerplay_all_universe_takes_only_actionable():
    """전수는 트렌드 관문을 못 넘은 종목이라 예의주시까지 받으면 100여 종목이 밀려든다.

    피벗에 바짝 붙은 «진입임박»만 받는다(사용자 결정 26-09-18 — 3C 와 같은 기준).
    계기: 디아이(003160)가 추천 리스트에는 진입임박으로 올랐는데 전수 파일이
    통째로 빠져 있어 알림에 «안» 떴다.
    """
    assert pivot_alert.MONITOR_TIERS["sepa-power-play-all-candidates.json"] == {"actionable"}


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
