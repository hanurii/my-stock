"""KIS 시세 조회의 토큰 만료전-무효화(HTTP 500) 복구 검증.
캐시 토큰이 만료 전 서버측 무효화되면 KIS가 500을 준다 — 봇이 쓰는 fetch_quote_with_volume 이
토큰을 한 번 강제 재발급하고 재시도해야 한다(무한 재발급은 금지)."""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib import kis_api


class _FakeResp:
    def __init__(self, payload):
        self._p = payload
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return json.dumps(self._p).encode("utf-8")


def _no_sleep(monkeypatch):
    monkeypatch.setattr(kis_api, "_throttle", lambda: None)
    monkeypatch.setattr(kis_api.time, "sleep", lambda *_: None)


def test_fetch_quote_reissues_token_on_http_500(monkeypatch):
    # OLD 토큰이면 KIS가 500(만료 전 무효화), NEW 토큰이면 정상 → 재발급 후 성공해야 한다.
    _no_sleep(monkeypatch)
    calls = {"issue": 0}
    def fake_issue():
        calls["issue"] += 1
        return "NEWTOKEN"
    monkeypatch.setattr(kis_api, "_issue_token", fake_issue)

    def fake_urlopen(req, timeout=8):
        auth = req.get_header("Authorization") or ""
        if "OLDTOKEN" in auth:
            raise kis_api._urlreq.HTTPError(req.full_url, 500, "server error", {}, None)
        return _FakeResp({"rt_cd": "0", "output": {"stck_prpr": "70000", "acml_vol": "12345"}})
    monkeypatch.setattr(kis_api._urlreq, "urlopen", fake_urlopen)

    out = kis_api.fetch_quote_with_volume("005930", token="OLDTOKEN")
    assert out == {"current": 70000.0, "acml_vol": 12345.0}
    assert calls["issue"] == 1   # 토큰 딱 한 번만 재발급


def test_fetch_quote_gives_up_if_still_500_after_reissue(monkeypatch):
    # 재발급해도 계속 500이면 무한 재발급하지 않고 None (재발급은 1회 한도).
    _no_sleep(monkeypatch)
    calls = {"issue": 0}
    def fake_issue():
        calls["issue"] += 1
        return "NEWTOKEN"
    monkeypatch.setattr(kis_api, "_issue_token", fake_issue)
    monkeypatch.setattr(kis_api._urlreq, "urlopen",
                        lambda req, timeout=8: (_ for _ in ()).throw(
                            kis_api._urlreq.HTTPError(req.full_url, 500, "err", {}, None)))
    out = kis_api.fetch_quote_with_volume("005930", token="OLDTOKEN")
    assert out is None
    assert calls["issue"] == 1   # 딱 1회만
