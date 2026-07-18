"""Minimal Sabre MCP-Skills client (Streamable HTTP / JSON-RPC).

Hotels aren't reachable via plain Sabre REST on this account — only through the
MCP-Skills server (mcp2.cert.sabre.com). This is a thin port of the transport
proven in the team's sabre-api-testing harness: initialize → notifications/
initialized → tools/call, with the required `Conversation-Id` header and SSE
response parsing. Used only when SABRE_HOTELS_LIVE is on.
"""
import json
import uuid

import httpx

from . import config

PROTOCOL_VERSION = "2025-06-18"


def _parse(resp: httpx.Response) -> dict:
    """MCP replies as either JSON or an SSE stream — handle both, return the JSON-RPC message."""
    if "event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                try:
                    return json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
        return {}
    try:
        return resp.json()
    except ValueError:
        return {}


def call_tool(name: str, arguments: dict, timeout: float = 60.0) -> dict:
    """Run one MCP-Skills business tool and return its parsed structured payload."""
    token = config.SABRE_ACCESS_TOKEN or ""
    if not token:
        raise RuntimeError("SABRE_ACCESS_TOKEN required for Sabre MCP calls (pre-issued token).")

    url = config.SABRE_MCP_URL
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Conversation-Id": str(uuid.uuid4()),  # required on every business call
    }

    init = httpx.post(url, headers=headers, timeout=30, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                   "clientInfo": {"name": "kiki-backend", "version": "0.2"}},
    })
    init.raise_for_status()
    session_id = init.headers.get("mcp-session-id")  # optional; gateway is stateless
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    httpx.post(url, headers=headers, timeout=30,
               json={"jsonrpc": "2.0", "method": "notifications/initialized"})

    resp = httpx.post(url, headers=headers, timeout=timeout, json={
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    })
    resp.raise_for_status()
    msg = _parse(resp)
    if msg.get("error"):
        raise RuntimeError(f"MCP tools/call({name}) error: {msg['error']}")
    content = (msg.get("result") or {}).get("content") or []
    text = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        return {}


def search_hotels(destination: str, check_in: str, check_out: str,
                  adults: int = 2, max_results: int = 8) -> list[dict]:
    """Real Sabre hotel search near an airport → [{name, code, city}]. Empty on any failure."""
    try:
        payload = call_tool("search-hotels", {
            "referencePoint": {"type": "Airport", "value": destination},
            "radiusInMiles": 25,
            "checkInDate": check_in,
            "checkOutDate": check_out,
            "numberOfAdults": adults,
            "pos": {"source": {"pseudoCityCode": config.SABRE_PCC}},
            "maxResults": max_results,
        })
    except Exception:
        return []
    hotels = payload.get("hotels", []) if isinstance(payload, dict) else []
    out = []
    for h in hotels:
        info = h.get("hotel", {})
        name = info.get("hotelName")
        if name:
            out.append({
                "name": name,
                "code": info.get("hotelCode"),
                "city": (info.get("address") or {}).get("cityName"),
            })
    return out
