"""거래정지 사유 분류 — 2026-07-31 DART 에서 실제로 받아온 공시 제목 픽스처.

분류 규칙의 핵심은 "주권매매거래정지 (사유)" 제목의 괄호 안을 1순위로 본다는 것.
한 종목의 공시 목록에는 상반된 사건이 섞여 있어서(정지와 해제가 같이 있음),
제목 전체를 키워드로 훑으면 오분류한다 — 조사 중 CSA 코스믹에서 실제로 겪었다.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib import halt_reason


# (rcept_dt, report_nm) — DART fetch_disclosure_list 반환 형태. 최신이 앞.
NICE_INFO = [                                   # 나이스정보통신 036800
    ("20260729", "주권매매거래정지              (주식분할)"),
    ("20260714", "주식분할결정              "),
]
KOMICO = [                                      # 코미코 183300
    ("20260729", "주권매매거래정지              (주식의 병합, 분할 등 전자등록 변경, 말소)"),
    ("20260710", "[기재정정]주식분할결정              "),
]
DEXTER = [                                      # 덱스터 206560
    ("20260724", "기타시장안내              (상장적격성 실질심사 대상결정 기한 안내)"),
    ("20260717", "기타시장안내              (상장적격성 실질심사 관련 안내)"),
]
CSA_COSMIC = [                                  # CSA 코스믹 083660 — 정지 '해제'
    ("20260717", "주권매매거래정지해제              (감자 주권 변경상장)"),
    ("20260716", "감자완료              "),
    ("20260630", "주권매매거래정지              (주식의 병합, 분할 등 전자등록 변경, 말소)"),
]
SPAC = [                                        # IBKS제25호스팩 0099X0
    ("20260709", "주권매매거래정지              (SPAC 합병(예비심사청구대상))"),
    ("20260709", "주요사항보고서(회사합병결정)"),
]


def test_stock_split_is_temporary():
    r = halt_reason.classify_halt_reason(NICE_INFO)
    assert r["kind"] == "temporary"
    assert "주식분할" in r["label"]


def test_electronic_registration_change_is_temporary():
    assert halt_reason.classify_halt_reason(KOMICO)["kind"] == "temporary"


def test_spac_merger_is_temporary():
    assert halt_reason.classify_halt_reason(SPAC)["kind"] == "temporary"


def test_listing_eligibility_review_is_serious():
    r = halt_reason.classify_halt_reason(DEXTER)
    assert r["kind"] == "serious"
    assert "상장적격성" in r["label"]


def test_lifted_halt_is_not_classified_as_halted():
    """정지 '해제' 가 더 최근이면 이미 풀린 것 — 사유로 못 박지 않는다.

    조사 중 이 케이스를 '심각'으로 오분류했다(다른 공시의 키워드에 걸림).
    """
    assert halt_reason.classify_halt_reason(CSA_COSMIC)["kind"] == "unknown"


def test_no_disclosure_is_unknown():
    r = halt_reason.classify_halt_reason([])
    assert r["kind"] == "unknown"
    assert r["label"] is None


def test_unrelated_disclosure_is_unknown():
    # 억지로 분류하지 않는다
    reports = [("20260720", "분기보고서 (2026.06)"), ("20260715", "임원·주요주주특정증권등소유상황보고서")]
    assert halt_reason.classify_halt_reason(reports)["kind"] == "unknown"


def test_halt_notice_wins_over_other_keywords():
    """정지 공시의 괄호가 1순위 — 다른 공시에 '합병' 이 있어도 사유는 상장적격성."""
    reports = [
        ("20260724", "주권매매거래정지              (상장적격성 실질심사 사유 발생)"),
        ("20260720", "주요사항보고서(회사합병결정)"),
    ]
    r = halt_reason.classify_halt_reason(reports)
    assert r["kind"] == "serious"


def test_merger_decision_alone_does_not_tag_temporary():
    """일시적 쪽은 보조 경로를 두지 않는다.

    합병·분할 결정 공시는 정지와 무관하게 흔하다. 정지 공시 없이 이것만 보고
    '곧 재개' 로 태깅하면 멀쩡히 거래되는 종목까지 잘못 분류된다.
    """
    reports = [("20260720", "주요사항보고서(회사합병결정)"),
               ("20260715", "[기재정정]주식병합결정              ")]
    assert halt_reason.classify_halt_reason(reports)["kind"] == "unknown"


def test_result_carries_source_report_for_audit():
    r = halt_reason.classify_halt_reason(NICE_INFO)
    assert "주권매매거래정지" in r["report"]


# ── 캐시 무효화 ──────────────────────────────────────────────

def test_cache_reused_when_halt_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(halt_reason, "CACHE_DIR", tmp_path)
    halt_reason.write_cache("036800", "2026-07-29",
                            {"kind": "temporary", "label": "주식분할", "report": "x"})
    got = halt_reason.read_cache("036800", "2026-07-29")
    assert got and got["kind"] == "temporary"


def test_cache_invalidated_when_new_halt_starts(tmp_path, monkeypatch):
    """정지 시작일이 바뀌면 새로운 정지 — 옛 사유를 재사용하면 안 된다."""
    monkeypatch.setattr(halt_reason, "CACHE_DIR", tmp_path)
    halt_reason.write_cache("036800", "2026-07-29",
                            {"kind": "temporary", "label": "주식분할", "report": "x"})
    assert halt_reason.read_cache("036800", "2026-09-01") is None


def test_cache_miss_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(halt_reason, "CACHE_DIR", tmp_path)
    assert halt_reason.read_cache("999999", "2026-07-29") is None


def test_empty_disclosure_response_is_not_cached(tmp_path, monkeypatch):
    """조회 실패를 캐시에 굳히면 안 된다.

    '공시가 없다' 와 '조회가 실패했다' 는 구분되지 않는다. 첫 실행에서 DART 키가
    안 올라와 빈 응답이 왔는데 그걸 캐시해, 키를 고친 뒤에도 99종목이 계속
    '불명' 으로 나왔다.
    """
    monkeypatch.setattr(halt_reason, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(halt_reason, "_ensure_env", lambda: None)
    import canslim_lib.management as mgmt
    import canslim_lib.fetch as fetch_mod
    monkeypatch.setattr(fetch_mod, "resolve_corp_code", lambda c, m: ("00264945", None))
    monkeypatch.setattr(mgmt, "fetch_disclosure_list", lambda *a, **k: [])

    r = halt_reason.fetch_halt_reason("036800", {"036800": "00264945"}, "2026-07-29")
    assert r["kind"] == "unknown"
    assert not (tmp_path / "036800.json").exists(), "빈 응답이 캐시로 굳었다"


# ── 제외 목록 주석 ───────────────────────────────────────────

def _fake_series(vols, dates):
    return {"dates": dates, "volumes": vols, "closes": [100.0] * len(vols)}


def test_annotate_fills_halt_span_without_dart():
    """DART 없이도(corp_map 미전달) 정지 기간은 채워지고 kind 만 unknown."""
    dates = ["2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30", "2026-07-31"]
    series = _fake_series([500, 300, 0, 0, 0], dates)
    out = halt_reason.annotate_dropped(
        [{"code": "036800", "name": "나이스정보통신", "reason": "halted"}],
        lambda c: series, corp_map=None, verbose=False)
    assert out[0]["zero_days"] == 3
    assert out[0]["last_trade"] == "2026-07-28"
    assert out[0]["kind"] == "unknown"


def test_annotate_handles_missing_series():
    out = halt_reason.annotate_dropped(
        [{"code": "057050", "name": "현대홈쇼핑", "reason": "excluded"}],
        lambda c: None, corp_map=None, verbose=False)
    assert out[0]["zero_days"] == 0
    assert out[0]["last_trade"] is None


def test_summarize_counts_reason_and_kind_separately():
    stocks = [
        {"reason": "halted", "kind": "temporary"},
        {"reason": "halted", "kind": "serious"},
        {"reason": "halted", "kind": "unknown"},
        {"reason": "excluded", "kind": "unknown"},
    ]
    c = halt_reason.summarize(stocks)
    assert c == {"total": 4, "temporary": 1, "serious": 1, "unknown": 2, "manual": 1}
