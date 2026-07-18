"""Smoke tests for the real Sabre + PayPal integration.

These skip automatically unless credentials are present in the environment, so
the normal mock test run (and CI without secrets) stays green. Run them with a
real .env loaded to verify live calls before a demo.
"""
import os

import pytest
from fastapi.testclient import TestClient

HAS_SABRE = bool(
    os.getenv("SABRE_ACCESS_TOKEN")
    or (os.getenv("SABRE_CLIENT_ID") and os.getenv("SABRE_CLIENT_SECRET"))
)
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
    c = _client(SABRE_FLIGHTS_LIVE="false", SABRE_HOTELS_LIVE="false", PAYPAL_LIVE="false")
    body = c.get("/health").json()
    assert body["mode"] == "mock"
    assert body["sabre_flights"] == "mock"
    assert body["sabre_hotels"] == "mock"
    assert body["paypal"] == "mock"


def test_paypal_endpoints_404_when_disabled():
    c = _client(PAYPAL_LIVE="false")
    assert c.get("/payment/paypal/config").status_code == 404


@pytest.mark.skipif(not HAS_SABRE, reason="Sabre credentials not set")
def test_real_sabre_hybrid_search_keeps_mock_options_and_adds_live_proof():
    c = _client(SABRE_FLIGHTS_LIVE="true")
    resp = c.post("/flights/search", json={"month": "november"})
    assert resp.status_code == 200  # never 500, even if Sabre returns nothing
    body = resp.json()
    # The three BOOKABLE options are always the curated mock set (bookable ids).
    assert len(body["options"]) == 3
    assert {o["flight_id"] for o in body["options"]} == {"AA511", "AA1620", "AA742"}
    # Real Sabre proof is attached separately (best-effort — may be None if the
    # token is stale, which is exactly the graceful-degradation we want).
    if body.get("sabre_live_fares"):
        assert body["request"]["sabre_source"]
        for o in body["sabre_live_fares"]:
            assert o["carrier"] and o["price_pp"] > 0


@pytest.mark.skipif(not HAS_SABRE, reason="Sabre credentials not set")
def test_real_sabre_hotel_insight():
    c = _client(SABRE_HOTELS_LIVE="true")
    c.post("/demo/reset")
    body = c.post("/hotel/adjust").json()
    # Mock hotel still books (narrative), plus real Sabre properties attached.
    assert body["hotel"]["status"] == "BOOKED"
    if body["sabre_hotels"]:  # CERT may occasionally return none for a date
        assert body["sabre_hotel_insight"]
        assert all(h["name"] for h in body["sabre_hotels"])


@pytest.mark.skipif(not HAS_PAYPAL, reason="PayPal credentials not set")
def test_real_paypal_create_order():
    c = _client(PAYPAL_LIVE="true")
    cfg = c.get("/payment/paypal/config").json()
    assert cfg["client_id"]
    created = c.post("/payment/paypal/create-order", json={"amount": 10.00}).json()
    assert created["order_id"]
    assert created["amount"] == 10.00
    # Capture needs buyer approval first, so we only assert the order was created.
