import os
from types import SimpleNamespace

import pytest


class _FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload
        self.request = SimpleNamespace(url="fake://trademe")

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.auth = None

    def get(self, url, timeout=None):
        return self.routes[("GET", url)]()

    def post(self, url, json=None, timeout=None):
        return self.routes[("POST", url)](json)


def _set_dummy_creds(monkeypatch):
    monkeypatch.setenv("CONSUMER_KEY", "x")
    monkeypatch.setenv("CONSUMER_SECRET", "y")
    monkeypatch.setenv("ACCESS_TOKEN", "a")
    monkeypatch.setenv("ACCESS_TOKEN_SECRET", "b")


def test_trademe_api_init_requires_creds(monkeypatch):
    from retail_os.trademe.api import TradeMeAPI

    for k in ["CONSUMER_KEY", "CONSUMER_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET"]:
        monkeypatch.delenv(k, raising=False)
    
    # Preventing TradeMeAPI from re-reading .env
    monkeypatch.setattr("retail_os.trademe.api.load_dotenv", lambda *args, **kwargs: None)

    with pytest.raises(ValueError):
        TradeMeAPI()


def test_trademe_get_account_summary_success(monkeypatch):
    _set_dummy_creds(monkeypatch)

    import retail_os.trademe.api as mod

    def mk():
        # Minimal stable-shaped response used by get_account_summary()
        return _FakeResponse(
            200,
            {
                "MemberId": 123,
                "Nickname": "tester",
                "Email": "tester@example.com",
                "AccountBalance": 12.34,
                "PayNowBalance": 3.21,
                "UniquePositive": 10,
                "UniqueNegative": 0,
                "FeedbackCount": 10,
                "TotalItemsSold": 99,
            },
        )

    fake = _FakeSession({("GET", f"{mod.PROD_URL}/MyTradeMe/Summary.json"): lambda: mk()})
    monkeypatch.setattr(mod.requests, "Session", lambda: fake)

    api = mod.TradeMeAPI()
    out = api.get_account_summary()
    assert isinstance(out, dict)
    assert out.get("account_balance") == 12.34


def test_trademe_update_price_failure(monkeypatch):
    _set_dummy_creds(monkeypatch)

    import retail_os.trademe.api as mod

    def update(_payload):
        return _FakeResponse(200, {"Success": False, "Description": "Cannot update"})

    fake = _FakeSession({("POST", f"{mod.PROD_URL}/Selling/Update.json"): lambda p=None: update(p)})
    monkeypatch.setattr(mod.requests, "Session", lambda: fake)

    api = mod.TradeMeAPI()
    with pytest.raises(Exception):
        api.update_price("123", 9.99)

