"""Environment-driven configuration for the Kiki complete-trip demo backend.

Two services run from this one codebase, told apart only by env vars:
  * mock  — every flag below false/default (the reliable demo + rehearsal path)
  * real  — SABRE_FLIGHTS_LIVE + PAYPAL_LIVE true, with real credentials, so the
            two sponsor touchpoints (flight search, payment) make genuine calls
            while everything else keeps serving the mock trip.

Real credentials come from the environment (Render env vars / a local .env that
is gitignored). They are never committed.
"""
import os


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# Serve JSON fixtures from backend/mocks/ instead of calling real Sabre.
MOCK_MODE: bool = _bool_env("MOCK_MODE", True)

# Artificial latency added to every endpoint so voice rehearsals match
# real API timing. Set to 0 for tests / local iteration.
MOCK_DELAY_SECONDS: float = float(os.getenv("MOCK_DELAY_SECONDS", "1.5"))

# Return a polished fake payment confirmation instead of charging anything.
PAYMENT_MOCK: bool = _bool_env("PAYMENT_MOCK", True)

# --------------------------------------------------------------------------
# Real-integration feature flags — narrow on purpose. Only the two sponsor
# touchpoints go live; hotels/cars/activities/status stay mock even when these
# are true, so nothing 501s.
# --------------------------------------------------------------------------

# When true, /flights/search calls real Sabre Flight Shop v1 (live itineraries).
SABRE_FLIGHTS_LIVE: bool = _bool_env("SABRE_FLIGHTS_LIVE", False)

# When true, /hotel/adjust attaches a real Sabre hotel insight (via MCP-Skills search-hotels).
SABRE_HOTELS_LIVE: bool = _bool_env("SABRE_HOTELS_LIVE", False)

# When true, the /payment/paypal/* endpoints are enabled (real sandbox PayPal).
PAYPAL_LIVE: bool = _bool_env("PAYPAL_LIVE", False)

# --- Sabre (CERT / test environment) ---
# Two ways to auth, in priority order:
#   1. SABRE_ACCESS_TOKEN — paste a ready-made bearer token from Sabre's "Get
#      Token" tool. Simplest, but it expires (regenerate when it does).
#   2. SABRE_CLIENT_ID + SABRE_CLIENT_SECRET — the app auto-fetches + refreshes
#      tokens itself. Sturdier for a long session.
SABRE_ACCESS_TOKEN: str = os.getenv("SABRE_ACCESS_TOKEN", "").strip()
SABRE_CLIENT_ID: str = os.getenv("SABRE_CLIENT_ID", "")
SABRE_CLIENT_SECRET: str = os.getenv("SABRE_CLIENT_SECRET", "")
# Two hosts: the "havail" host serves the fare/seasonality REST APIs; the
# "platform" host serves Flight Shop v1 (real itineraries). Both accept the
# same token.
SABRE_BASE_URL: str = os.getenv("SABRE_BASE_URL", "https://api-crt.cert.havail.sabre.com").rstrip("/")
SABRE_SHOP_BASE_URL: str = os.getenv("SABRE_SHOP_BASE_URL", "https://api.cert.platform.sabre.com").rstrip("/")
# Pseudo-city code — required in Flight Shop's processingOptions. The hackathon
# token is provisioned for this PCC.
SABRE_PCC: str = os.getenv("SABRE_PCC", "S5OM")
# Sabre MCP-Skills endpoint (hotels are only reachable here, not via plain REST).
SABRE_MCP_URL: str = os.getenv("SABRE_MCP_URL", "https://mcp2.cert.sabre.com/mcp").rstrip("/")

# --- PayPal (sandbox) ---
PAYPAL_CLIENT_ID: str = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET: str = os.getenv("PAYPAL_SECRET", "")
PAYPAL_BASE_URL: str = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").rstrip("/")
PAYPAL_CURRENCY: str = os.getenv("PAYPAL_CURRENCY", "USD")


# --- Vocal Bridge (voice-token minting for the UI's /token route) ---
# The VB API key must stay server-side; the UI calls our /token, we call VB.
# Canonical env var is VB_API_KEY (VOCAL_BRIDGE_API_KEY kept as a fallback).
VB_API_KEY: str = os.getenv("VB_API_KEY", "") or os.getenv("VOCAL_BRIDGE_API_KEY", "")
# Account-level VB keys require the agent id; default to the Maui "KiKi" agent.
VB_AGENT_ID: str = os.getenv("VB_AGENT_ID", "98d6dd19-790c-40af-aeaf-28f53bc64ce4")
VB_TOKEN_URL: str = os.getenv("VB_TOKEN_URL", "https://vocalbridgeai.com/api/v1/token")


def mode() -> dict:
    """Self-describing status for /health, so each deployed URL says what it is."""
    any_live = SABRE_FLIGHTS_LIVE or SABRE_HOTELS_LIVE or PAYPAL_LIVE
    return {
        "mode": "real" if any_live else "mock",
        "sabre_flights": "live" if SABRE_FLIGHTS_LIVE else "mock",
        "sabre_hotels": "live" if SABRE_HOTELS_LIVE else "mock",
        "paypal": "live" if PAYPAL_LIVE else "mock",
    }
