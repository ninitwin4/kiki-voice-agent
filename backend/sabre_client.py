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
    """Sabre OAuth2 client_credentials, with Sabre's double-base64 Basic-auth quirk."""
    global _token
    if _token and _token[1] - 60 > time.monotonic():
        return _token[0]
    if not (config.SABRE_CLIENT_ID and config.SABRE_CLIENT_SECRET):
        raise RuntimeError("Sabre credentials missing — set SABRE_CLIENT_ID / SABRE_CLIENT_SECRET.")

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


def _hhmm(iso_dt: str) -> str:
    """'2026-08-03T08:15:00' -> '08:15'."""
    try:
        return iso_dt.split("T", 1)[1][:5]
    except (IndexError, AttributeError):
        return ""


def _segments(od_option: dict) -> list[dict]:
    seg = od_option.get("FlightSegment", [])
    return seg if isinstance(seg, list) else [seg]


def _leg(seg: dict) -> dict:
    carrier = (seg.get("MarketingAirline") or {}).get("Code", "")
    return {
        "carrier_code": carrier,
        "carrier": _CARRIERS.get(carrier, carrier),
        "flight_no": f"{carrier} {seg.get('FlightNumber', '')}".strip(),
        "depart_time": _hhmm(seg.get("DepartureDateTime", "")),
        "arrive_time": _hhmm(seg.get("ArrivalDateTime", "")),
    }


def _map_itinerary(priced: dict, tier: str, travelers: int, recommended: bool) -> dict:
    """Map one Sabre PricedItinerary into our FlightOption shape (best-effort)."""
    ods = (
        priced.get("AirItinerary", {})
        .get("OriginDestinationOptions", {})
        .get("OriginDestinationOption", [])
    )
    ods = ods if isinstance(ods, list) else [ods]
    out_segs = _segments(ods[0]) if ods else []
    ret_segs = _segments(ods[1]) if len(ods) > 1 else []

    first_out = _leg(out_segs[0]) if out_segs else {}
    last_out = _leg(out_segs[-1]) if out_segs else {}
    first_ret = _leg(ret_segs[0]) if ret_segs else {}
    last_ret = _leg(ret_segs[-1]) if ret_segs else {}
    stops = max(len(out_segs) - 1, 0)

    fare = (
        priced.get("AirItineraryPricingInfo", {})
        .get("ItinTotalFare", {})
        .get("TotalFare", {})
    )
    total_price = round(float(fare.get("Amount", 0) or 0), 2)
    price_pp = round(total_price / travelers, 2) if travelers else total_price

    conn = "Nonstop" if stops == 0 else f"{stops}-stop"
    tradeoff = f"{conn} on {first_out.get('carrier', 'this carrier')}, about ${price_pp:.0f} per person."
    if recommended:
        tradeoff += " Best price of the three."

    return {
        "flight_id": (first_out.get("flight_no", f"OPT{tier}") or f"OPT{tier}").replace(" ", ""),
        "tier": tier,
        "carrier": first_out.get("carrier", ""),
        "flight_no": first_out.get("flight_no", ""),
        "depart_time": first_out.get("depart_time", ""),
        "arrive_time": last_out.get("arrive_time", ""),
        "stops": stops,
        "price_pp": price_pp,
        "total_price": total_price,
        "recommended": recommended,
        "return_flight_no": first_ret.get("flight_no", ""),
        "return_depart_time": first_ret.get("depart_time", ""),
        "return_arrive_time": last_ret.get("arrive_time", ""),
        "tradeoff": tradeoff,
    }


def get_trip_status() -> dict:
    """TODO: fetch the PNR via Sabre Get Reservation and map it to the trip shape."""
    raise NotImplementedError("Sabre Get Reservation is not integrated yet — set MOCK_MODE=true.")


def search_flights(
    origin: str, destination: str, depart_date: str, return_date: str, travelers: int
) -> dict:
    """Call Sabre air shopping (InstaFlights) for a round trip and map to FlightSearchOut."""
    token = _get_token()
    resp = httpx.get(
        f"{config.SABRE_BASE_URL}/v1/shop/flights",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "origin": origin,
            "destination": destination,
            "departuredate": depart_date,
            "returndate": return_date,
            "limit": 3,
            "sortby": "totalfare",
            "order": "asc",
            "pointofsalecountry": "US",
            "passengercount": travelers,
        },
        timeout=30,
    )
    resp.raise_for_status()
    priced = resp.json().get("PricedItineraries", [])[:3]

    tiers = ["A", "B", "C"]
    options = [
        _map_itinerary(it, tiers[i], travelers, recommended=(i == 0))
        for i, it in enumerate(priced)
    ]
    return {
        "request": {
            "origin": origin,
            "destination": destination,
            "month": "",  # real search is date-driven, not month-keyed
            "dates": f"{depart_date} → {return_date}",
            "travelers": travelers,
            "season": "",
            "source": "Sabre InstaFlights (live)",
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
