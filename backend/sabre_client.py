"""Adapter for the real Sabre APIs.

For the hackathon "real" version only `search_flights` is implemented — it calls
Sabre air shopping (InstaFlights) and maps the result into the exact
`FlightSearchOut` shape the mock returns, so the rest of the app, the Vocal
Bridge tool, and the itinerary UI keep working unchanged. The other functions
stay stubbed (never called while only SABRE_FLIGHTS_LIVE is on).

Credentials come from config (env vars); nothing is hard-coded.
"""
import base64
import time

import httpx

from . import config

# Common carrier code → name, so options read naturally when spoken. Anything
# not listed falls back to the raw code.
_CARRIERS = {
    "AA": "American Airlines", "UA": "United", "DL": "Delta", "AS": "Alaska",
    "HA": "Hawaiian", "WN": "Southwest", "B6": "JetBlue", "NK": "Spirit",
    "F9": "Frontier", "G4": "Allegiant",
}

# Cached OAuth token: (access_token, expires_at_monotonic).
_token: tuple[str, float] | None = None


def _get_token() -> str:
    """Return a Sabre bearer token.

    Prefers a pasted SABRE_ACCESS_TOKEN (simplest — just one value to provide);
    otherwise does the OAuth2 client_credentials exchange with client id/secret,
    using Sabre's double-base64 Basic-auth quirk, and caches the result.
    """
    if config.SABRE_ACCESS_TOKEN:
        return config.SABRE_ACCESS_TOKEN

    global _token
    if _token and _token[1] - 60 > time.monotonic():
        return _token[0]
    if not (config.SABRE_CLIENT_ID and config.SABRE_CLIENT_SECRET):
        raise RuntimeError(
            "Sabre credentials missing — set SABRE_ACCESS_TOKEN, or "
            "SABRE_CLIENT_ID / SABRE_CLIENT_SECRET."
        )

    enc_id = base64.b64encode(config.SABRE_CLIENT_ID.encode()).decode()
    enc_secret = base64.b64encode(config.SABRE_CLIENT_SECRET.encode()).decode()
    cred = base64.b64encode(f"{enc_id}:{enc_secret}".encode()).decode()

    resp = httpx.post(
        f"{config.SABRE_BASE_URL}/v2/auth/token",
        headers={
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=20,
    )
    resp.raise_for_status()
    body = resp.json()
    _token = (body["access_token"], time.monotonic() + float(body.get("expires_in", 600)))
    return _token[0]


def get_trip_status() -> dict:
    """TODO: fetch the PNR via Sabre Get Reservation and map it to the trip shape."""
    raise NotImplementedError("Sabre Get Reservation is not integrated yet — set MOCK_MODE=true.")


_SEASON_RANK = {"low": 0, "medium": 1, "high": 2}


def _seasonality_insight(destination: str) -> str | None:
    """Real Sabre Travel Seasonality → a spoken insight comparing the trip's two
    candidate windows (early August vs early October) using live demand ratings.

    Sabre returns weekly Low/Medium/High demand for the destination. We pull the
    rating for the first week of each month and, if August is busier, say so —
    real Sabre data backing the "move to October" story. Best-effort: any shape
    mismatch or error yields None so it never breaks the flight search.
    """
    try:
        token = _get_token()
        resp = httpx.get(
            f"{config.SABRE_BASE_URL}/v1/historical/flights/{destination}/seasonality",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        weeks = resp.json().get("Seasonality", [])

        def rating_for(month: int) -> str | None:
            in_month = [w for w in weeks if w.get("WeekStartDate", "")[5:7] == f"{month:02d}"]
            early = [w for w in in_month if int((w.get("WeekStartDate", "0000-00-00") + "")[8:10] or 99) <= 10]
            pick = (early or in_month)
            return pick[0].get("SeasonalityIndicator") if pick else None

        aug, oct_ = rating_for(8), rating_for(10)
        if aug and oct_:
            tail = ""
            if _SEASON_RANK.get(aug.lower(), 1) > _SEASON_RANK.get(oct_.lower(), 1):
                tail = " — so October is the cheaper window."
            return (
                f"Live Sabre demand data rates the first week of August as {aug} "
                f"and early October as {oct_} for {destination}{tail}"
            )
        if aug or oct_:
            m, r = ("August", aug) if aug else ("October", oct_)
            return f"Live Sabre demand data rates early {m} as {r} season for {destination}."
        return None
    except Exception:
        return None


def search_flights(
    origin: str, destination: str, depart_date: str, return_date: str, travelers: int
) -> dict:
    """Real Sabre fare check for the route, mapped into FlightSearchOut.

    Sabre CERT can't return full itineraries for this account (InstaFlights cache
    is empty, BFM isn't provisioned), but the "cheapest fares to a destination"
    API returns real airlines + prices. We map those into our option shape and
    attach a live Travel Seasonality insight. A Sabre 404 means "no fares found"
    (not a missing endpoint), so we degrade to an empty option list, not an error.
    """
    token = _get_token()
    resp = httpx.get(
        f"{config.SABRE_BASE_URL}/v1/shop/flights/cheapest/fares/{destination}",
        headers={"Authorization": f"Bearer {token}"},
        params={"origin": origin, "pointofsalecountry": "US"},
        timeout=30,
    )
    if resp.status_code == 404:  # Sabre 404 = "no fares found", not a missing endpoint
        fares = []
    else:
        resp.raise_for_status()
        fares = resp.json().get("FareInfo", [])
    fares = sorted(fares, key=lambda f: f.get("LowestFare", {}).get("Fare", 1e9))[:3]

    tiers = ["A", "B", "C"]
    options = []
    for i, f in enumerate(fares):
        low = f.get("LowestFare", {})
        fare = round(float(low.get("Fare", 0) or 0), 2)
        codes = low.get("AirlineCodes") or []
        code = codes[0] if codes else "SB"
        carrier = _CARRIERS.get(code, code)
        from_loc = f.get("OriginLocation", origin)
        options.append({
            "flight_id": f"{code}{i}",
            "tier": tiers[i],
            "carrier": carrier,
            "flight_no": "",  # cheapest-fares gives fares + airline, not flight numbers
            "depart_time": "",
            "arrive_time": "",
            "stops": 0,
            "price_pp": fare,
            "total_price": round(fare * travelers, 2),
            "recommended": i == 0,
            "return_flight_no": "",
            "return_depart_time": "",
            "return_arrive_time": "",
            "tradeoff": (
                f"Live Sabre fare: {carrier} into {destination} from {from_loc}, "
                f"about ${fare:.0f} per person."
            ),
        })

    return {
        "request": {
            "origin": origin,
            "destination": destination,
            "month": "",
            "dates": f"{depart_date} → {return_date}",
            "travelers": travelers,
            "season": "",
            "source": "Sabre cheapest-fares (live)",
            "sabre_insight": _seasonality_insight(destination),
        },
        "options": options,
    }


def book_flight(flight_id: str) -> dict:
    """TODO: book the selected itinerary for the group via Sabre, return the FlightBookOut shape."""
    raise NotImplementedError("Sabre booking is not integrated yet — set MOCK_MODE=true.")


def adjust_hotel(month: str) -> dict:
    """TODO: book 2 rooms via Sabre Content Services for Lodging, return the HotelBookOut shape."""
    raise NotImplementedError("Sabre hotel booking is not integrated yet — set MOCK_MODE=true.")


def update_transport(month: str) -> dict:
    """TODO: book the minivan + child car seat with the ground-transport provider, return the TransportBookOut shape."""
    raise NotImplementedError("Ground-transport integration is not implemented yet — set MOCK_MODE=true.")


def book_activities(activity: str | None, month: str) -> dict:
    """TODO: book the surf lesson / Molokini tour with the activities provider (not a Sabre product), return the ActivitiesBookOut shape."""
    raise NotImplementedError("Activities integration is not implemented yet — set MOCK_MODE=true.")


def configure_trip(nights: int | None, travelers: int | None, rooms: int | None) -> dict:
    """TODO: re-quote every vendor for the new party size / length via Sabre, return the TripConfigureOut shape."""
    raise NotImplementedError("Sabre re-quoting is not integrated yet — set MOCK_MODE=true.")


def rebook_trip(month: str) -> dict:
    """TODO: exchange the ticket and move every vendor booking to the new month's dates, return the TripRebookOut shape."""
    raise NotImplementedError("Sabre exchanges are not integrated yet — set MOCK_MODE=true.")


def confirm_payment(amount: float, currency: str) -> dict:
    """TODO: charge via the real payment provider (e.g. PayPal), return the PaymentOut shape."""
    raise NotImplementedError("Real payment processing is not integrated yet — set PAYMENT_MOCK=true.")
