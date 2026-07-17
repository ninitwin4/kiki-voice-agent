"""PayPal (sandbox) client for the hackathon "real" version.

Standard server-side Orders v2 flow: create an order, the buyer approves it via
the PayPal button in the itinerary UI, then capture it. Enabled only when
PAYPAL_LIVE is true; credentials come from config (env vars).
"""
import time

import httpx

from . import config

# Cached OAuth token: (access_token, expires_at_monotonic).
_token: tuple[str, float] | None = None


def _require_creds() -> None:
    if not (config.PAYPAL_CLIENT_ID and config.PAYPAL_SECRET):
        raise RuntimeError("PayPal credentials missing — set PAYPAL_CLIENT_ID / PAYPAL_SECRET.")


def get_access_token() -> str:
    global _token
    if _token and _token[1] - 60 > time.monotonic():
        return _token[0]
    _require_creds()
    resp = httpx.post(
        f"{config.PAYPAL_BASE_URL}/v1/oauth2/token",
        auth=(config.PAYPAL_CLIENT_ID, config.PAYPAL_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials"},
        timeout=20,
    )
    resp.raise_for_status()
    body = resp.json()
    _token = (body["access_token"], time.monotonic() + float(body.get("expires_in", 3000)))
    return _token[0]


def create_order(amount: float, currency: str) -> dict:
    """Create a PayPal order for `amount`; returns {order_id, status, approve_url}."""
    token = get_access_token()
    resp = httpx.post(
        f"{config.PAYPAL_BASE_URL}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
                    "description": "Kiki — Maui group trip",
                }
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    approve_url = next(
        (l["href"] for l in body.get("links", []) if l.get("rel") == "approve"), None
    )
    return {"order_id": body["id"], "status": body.get("status"), "approve_url": approve_url}


def capture_order(order_id: str) -> dict:
    """Capture an approved PayPal order; returns the capture summary."""
    token = get_access_token()
    resp = httpx.post(
        f"{config.PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    capture = (
        body.get("purchase_units", [{}])[0]
        .get("payments", {})
        .get("captures", [{}])[0]
    )
    amount = capture.get("amount", {})
    return {
        "order_id": body.get("id", order_id),
        "status": body.get("status"),
        "capture_id": capture.get("id"),
        "amount": float(amount.get("value", 0) or 0),
        "currency": amount.get("currency_code", config.PAYPAL_CURRENCY),
        "payer_email": (body.get("payer", {}) or {}).get("email_address"),
    }
