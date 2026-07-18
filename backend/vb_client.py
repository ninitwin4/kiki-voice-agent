"""Vocal Bridge voice-token minting.

The UI can't hold the VB API key, so it calls our POST /token, and we mint a
short-lived LiveKit voice token from Vocal Bridge server-side. Returns VB's full
response ({token, livekit_url, room_name, participant_identity, expires_in, ...})
so the UI can read `token` and the SDK still has everything else it may want.
"""
import httpx

from . import config


def mint_token(participant_name: str = "Web User") -> dict:
    if not config.VB_API_KEY:
        raise RuntimeError("VB_API_KEY not set.")
    headers = {
        "X-API-Key": config.VB_API_KEY,
        "Content-Type": "application/json",
    }
    # Account-level keys need the agent id; agent-scoped keys ignore it.
    if config.VB_AGENT_ID:
        headers["X-Agent-Id"] = config.VB_AGENT_ID
    resp = httpx.post(
        config.VB_TOKEN_URL,
        headers=headers,
        json={"participant_name": participant_name},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()
