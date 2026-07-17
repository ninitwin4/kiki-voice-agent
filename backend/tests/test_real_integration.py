"""Smoke tests for the real Sabre + PayPal integration.

These skip automatically unless credentials are present in the environment, so
the normal mock test run (and CI without secrets) stays green. Run them with a
real .env loaded to verify live calls before a demo.
"""
import os

import pytest
from fastapi.testclient import TestClient

HAS_SABRE = bool(os.getenv("SABRE_CLIENT_ID") and os.getenv("SABRE_CLIENT_SECRET"))
HAS_PAYPAL = bool(os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_SECRET"))


def _client(**env) -> TestClient:
    for k, v in env.items():
        os.environ[k] = v
    os.environ["MOCK_DELAY_SECONDS"] = "0"
    import importlib
    from backend import config as config_mod
    importlib.reload(config_mod)
    from backend import main as main_mod
    importlib.reload(main_mod)
    return TestClient(main_mod.app)


def test_health_reports_mode_flags():
    c = _client(SABRE_FLIGHTS_LIVE="false", PAYPAL_LIVE="false")
    body = c.get("/health").json()
    assert body["mode"] == "mock"
    assert body["sabre"] == "mock"
    assert body["paypal"] == "mock"


def test_paypal_endpoints_404_when_disabled():
    c = _client(PAYPAL_LIVE="false")
    assert c.get("/payment/paypal/config").status_code == 404


@pytest.mark.skipif(not HAS_SABRE, reason="Sabre credentials not set")
def test_real_sabre_flight_search_maps_to_our_shape():
    c = _client(SABRE_FLIGHTS_LIVE="true")
    resp = c.post("/flights/search", json={"month": "august"})
    assert resp.status_code == 200
    body = resp.json()
    assert "Sabre" in body["request"]["source"]
    assert len(body["options"]) >= 1
    for o in body["options"]:
        assert o["carrier"] and o["flight_no"]
        assert o["total_price"] > 0
        assert o["tradeoff"]


@pytest.mark.skipif(not HAS_PAYPAL, reason="PayPal credentials not set")
def test_real_paypal_create_order():
    c = _client(PAYPAL_LIVE="true")
    cfg = c.get("/payment/paypal/config").json()
    assert cfg["client_id"]
    created = c.post("/payment/paypal/create-order", json={"amount": 10.00}).json()
    assert created["order_id"]
    assert created["amount"] == 10.00
    # Capture needs buyer approval first, so we only assert the order was created.
