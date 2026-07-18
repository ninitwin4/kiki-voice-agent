"""Kiki — voice-agent travel demo backend (project: complete-trip).

Plans a 5-person Maui group trip (2 couples + 1 child) SFO⇄OGG with
Sabre-shaped mock data. The demo plans the first week of November, Kiki checks
the weather and finds it's Maui's rainy season, then rebooks to the first week
of August (dry) — and that date change cascades across flights, hotel,
transport, and activities so /trip/status re-flows the whole trip.

All state lives in a single in-memory TRIP object. Month-specific pricing
lives in mocks/catalog.json + mocks/flight_search.json, so November and
August can't drift apart. POST /demo/reset restores the initial
November-planning state so the demo can be rehearsed repeatedly.
"""
import asyncio
import copy
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config, paypal_client, sabre_client, vb_client

MOCKS_DIR = Path(__file__).parent / "mocks"

_TRIP_HEADER: dict = json.loads((MOCKS_DIR / "trip.json").read_text())
_CATALOG: dict = json.loads((MOCKS_DIR / "catalog.json").read_text())
_FLIGHTS: dict = json.loads((MOCKS_DIR / "flight_search.json").read_text())

MONTHS = tuple(_CATALOG.keys())  # ("november", "august")


# --------------------------------------------------------------------------
# Trip assembly — every vendor is priced from the catalog for the trip's
# current month, so a month change re-prices everything consistently.
# --------------------------------------------------------------------------

VEHICLE_SEATS = 7  # the minivan; a bigger party needs a note about a second van

# Bounds for /trip/configure, so the demo can flex without going off a cliff.
NIGHTS_MIN, NIGHTS_MAX = 1, 14
TRAVELERS_MIN, TRAVELERS_MAX = 1, 9
ROOMS_MIN, ROOMS_MAX = 1, 6


def _options(month: str) -> list[dict]:
    return _FLIGHTS[month]["options"]


def _recommended(month: str) -> dict:
    return next(o for o in _options(month) if o["recommended"])


def _nights(trip: dict) -> int:
    return trip["nights"]


def _travelers(trip: dict) -> int:
    return trip["party"]["total"]


def _rooms(trip: dict) -> int:
    return trip["party"]["rooms"]


def _end_date(start: str, nights: int) -> str:
    y, m, d = (int(x) for x in start.split("-"))
    return (date(y, m, d) + timedelta(days=nights)).isoformat()


def _priced_option(option: dict, travelers: int) -> dict:
    """A flight search option with total_price recomputed for the party size."""
    priced = dict(option)
    priced["total_price"] = round(option["price_pp"] * travelers, 2)
    return priced


def _flight_entry(option: dict, status: str, travelers: int, locator: str | None = None) -> dict:
    """Shape a search option into the trip's `flights` block, priced for the party."""
    entry = {k: option[k] for k in (
        "flight_id", "tier", "carrier", "flight_no", "depart_time", "arrive_time",
        "stops", "price_pp", "return_flight_no",
        "return_depart_time", "return_arrive_time", "tradeoff",
    )}
    entry["total_price"] = round(option["price_pp"] * travelers, 2)
    entry["status"] = status
    entry["record_locator"] = locator
    return entry


def _apply_month(trip: dict, month: str) -> None:
    """Re-assemble the trip for `month`, pricing every vendor from the catalog's
    base rates times the trip's current size (nights, travelers, rooms).

    This is the single re-pricing path: a month change (/trip/rebook) and a size
    change (/trip/configure) both run through here, so nothing can drift. Booked
    statuses and confirmation numbers survive, and a booked flight carries its
    tier (A/B/C) across to the equivalent option in the new month.
    """
    entry = _CATALOG[month]
    nights = trip.get("nights") or entry["dates"]["nights"]
    travelers = _travelers(trip)
    rooms = _rooms(trip)
    start = entry["dates"]["start"]
    end = _end_date(start, nights)

    trip["month"] = month
    trip["nights"] = nights
    trip["dates"] = {
        "start": start, "end": end, "nights": nights,
        "label": entry["label"], "season": entry["season"],
    }

    prev_hotel = trip.get("hotel") or {}
    hotel = copy.deepcopy(entry["hotel"])
    hotel["rooms"] = rooms
    hotel["nights"] = nights
    hotel["check_in"] = start
    hotel["check_out"] = end
    hotel["total"] = round(hotel["nightly_rate"] * rooms * nights, 2)
    hotel["status"] = prev_hotel.get("status", "NOT_BOOKED")
    hotel["confirmation_number"] = prev_hotel.get("confirmation_number")
    trip["hotel"] = hotel

    prev_transport = trip.get("transport") or {}
    transport = copy.deepcopy(entry["transport"])
    transport["days"] = nights
    transport["pickup_date"] = start
    transport["dropoff_date"] = end
    transport["total"] = round(
        (transport["daily_rate"] + transport["car_seat_fee_per_day"]) * nights, 2
    )
    if travelers > VEHICLE_SEATS:
        transport["note"] = (
            f"{transport['note']} Party of {travelers} exceeds one minivan "
            f"({VEHICLE_SEATS} seats) — a second vehicle may be needed."
        )
    transport["status"] = prev_transport.get("status", "NOT_BOOKED")
    transport["confirmation_number"] = prev_transport.get("confirmation_number")
    trip["transport"] = transport

    prev_activities = trip.get("activities") or {}
    prev_by_id = {a["activity_id"]: a for a in prev_activities.get("items", [])}
    items = []
    for template in entry["activities"]:
        item = copy.deepcopy(template)
        item["participants"] = travelers
        item["total"] = round(item["price_pp"] * travelers, 2)
        prev = prev_by_id.get(item["activity_id"], {})
        item["status"] = prev.get("status", "NOT_BOOKED")
        item["confirmation_number"] = prev.get("confirmation_number")
        items.append(item)
    trip["activities"] = {
        "status": prev_activities.get("status", "NOT_BOOKED"),
        "items": items,
    }

    prev_flights = trip.get("flights") or {}
    if prev_flights.get("status") == "BOOKED":
        same_tier = next(o for o in _options(month) if o["tier"] == prev_flights["tier"])
        trip["flights"] = _flight_entry(
            same_tier, "BOOKED", travelers, prev_flights.get("record_locator")
        )
    else:
        trip["flights"] = {"status": "NOT_BOOKED", "tier": None, "flight_id": None}


def _build_initial_trip() -> dict:
    trip = copy.deepcopy(_TRIP_HEADER)
    trip.setdefault("nights", _CATALOG[trip["month"]]["dates"]["nights"])
    _apply_month(trip, trip["month"])
    return trip


def _flights_amount(trip: dict) -> float:
    """Booked fare if a flight is booked, otherwise the recommended option's
    quote for the current party — so /trip/status shows a realistic total
    before anything is booked."""
    if trip["flights"].get("status") == "BOOKED":
        return trip["flights"]["total_price"]
    return round(_recommended(trip["month"])["price_pp"] * _travelers(trip), 2)


def _totals(trip: dict) -> dict:
    flights = _flights_amount(trip)
    hotel = trip["hotel"]["total"]
    transport = trip["transport"]["total"]
    activities = round(sum(a["total"] for a in trip["activities"]["items"]), 2)
    trip_total = round(flights + hotel + transport + activities, 2)
    budget = trip["budget"]["amount"]
    return {
        "currency": trip["budget"]["currency"],
        "flights": flights,
        "hotel": hotel,
        "transport": transport,
        "activities": activities,
        "trip_total": trip_total,
        "budget": budget,
        "over_budget_by": round(max(trip_total - budget, 0.0), 2),
        "within_budget": trip_total <= budget,
        "flights_quoted": trip["flights"].get("status") != "BOOKED",
    }


def _validate_month(month: str) -> str:
    key = (month or "").strip().lower()
    if key not in _CATALOG:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown month '{month}'. Valid options: {list(MONTHS)}",
        )
    return key


def _confirmation(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"


TRIP: dict = _build_initial_trip()


# --------------------------------------------------------------------------
# Pydantic models (kept explicit so the OpenAPI spec is clean enough to hand
# straight to a voice platform's tool config)
# --------------------------------------------------------------------------

class Traveler(BaseModel):
    name: str
    type: str
    age: int | None = None


class Party(BaseModel):
    adults: int
    children: int
    total: int
    rooms: int
    note: str
    travelers: list[Traveler]


class Budget(BaseModel):
    amount: float
    currency: str
    note: str


class Preferences(BaseModel):
    no_early_return: bool
    note: str


class TripDates(BaseModel):
    start: str
    end: str
    nights: int
    label: str
    season: str


class TripFlights(BaseModel):
    status: str
    tier: str | None = None
    flight_id: str | None = None
    carrier: str | None = None
    flight_no: str | None = None
    depart_time: str | None = None
    arrive_time: str | None = None
    stops: int | None = None
    price_pp: float | None = None
    total_price: float | None = None
    return_flight_no: str | None = None
    return_depart_time: str | None = None
    return_arrive_time: str | None = None
    tradeoff: str | None = None
    record_locator: str | None = None


class TripHotel(BaseModel):
    status: str
    name: str
    room_type: str
    rooms: int
    check_in: str
    check_out: str
    nightly_rate: float
    nights: int
    total: float
    note: str
    confirmation_number: str | None = None


class TripTransport(BaseModel):
    status: str
    provider: str
    vehicle: str
    pickup_location: str
    pickup_date: str
    dropoff_date: str
    car_seat: bool
    car_seat_fee_per_day: float
    daily_rate: float
    days: int
    total: float
    note: str
    confirmation_number: str | None = None


class ActivityItem(BaseModel):
    activity_id: str
    name: str
    provider: str
    kid_friendly: bool
    date: str
    time: str
    duration: str
    price_pp: float
    participants: int
    total: float
    note: str
    status: str
    confirmation_number: str | None = None


class TripActivities(BaseModel):
    status: str
    items: list[ActivityItem]


class Totals(BaseModel):
    currency: str
    flights: float
    hotel: float
    transport: float
    activities: float
    trip_total: float
    budget: float
    over_budget_by: float
    within_budget: bool
    flights_quoted: bool


class PaymentRecord(BaseModel):
    confirmation_code: str
    amount: float
    currency: str
    method: str
    status: str
    processed_at: str


class TripStatusOut(BaseModel):
    trip_id: str
    trip_name: str
    status: str
    month: str
    origin: str
    destination: str
    dates: TripDates
    party: Party
    budget: Budget
    preferences: Preferences
    constraint: str
    flights: TripFlights
    hotel: TripHotel
    transport: TripTransport
    activities: TripActivities
    totals: Totals
    payments: list[PaymentRecord]


class SearchRequestEcho(BaseModel):
    origin: str
    destination: str
    month: str
    dates: str
    travelers: int
    season: str
    source: str
    # Populated only by the real Sabre path — a live Travel Seasonality insight
    # Kiki can read aloud (e.g. cheaper months to fly into Maui). None on mock.
    sabre_insight: str | None = None
    # Where the live proof came from, e.g. "Sabre Flight Shop v1 (live)". None on mock.
    sabre_source: str | None = None


class FlightOption(BaseModel):
    flight_id: str
    tier: str
    carrier: str
    flight_no: str
    depart_time: str
    arrive_time: str
    stops: int
    price_pp: float
    total_price: float
    recommended: bool
    return_flight_no: str
    return_depart_time: str
    return_arrive_time: str
    tradeoff: str


class FlightSearchIn(BaseModel):
    month: str | None = Field(
        None, description="Which month to price, 'november' or 'august'. Defaults to the trip's current month."
    )


class FlightSearchOut(BaseModel):
    request: SearchRequestEcho
    options: list[FlightOption]
    # Real Sabre fares for the same route, shown as live proof alongside the
    # bookable options. None on mock or if the live Sabre call returns nothing.
    sabre_live_fares: list[FlightOption] | None = None


class FlightBookIn(BaseModel):
    flight_id: str = Field(..., description="flight_id from /flights/search, e.g. 'AA289'")


class FlightBookOut(BaseModel):
    confirmed: bool
    message: str
    record_locator: str
    flights: TripFlights
    totals: Totals


class SabreHotel(BaseModel):
    name: str
    code: str | None = None
    city: str | None = None


class HotelBookOut(BaseModel):
    confirmed: bool
    message: str
    hotel: TripHotel
    totals: Totals
    # Populated only by the real service (SABRE_HOTELS_LIVE) — genuine Maui
    # properties from Sabre for the trip's dates. None on mock.
    sabre_hotels: list[SabreHotel] | None = None
    sabre_hotel_insight: str | None = None


class TransportBookOut(BaseModel):
    confirmed: bool
    message: str
    transport: TripTransport
    totals: Totals


class ActivitiesBookIn(BaseModel):
    activity: str | None = Field(
        None, description="Book one experience only: 'surf' or 'snorkel'. Omit to book both."
    )


class ActivitiesBookOut(BaseModel):
    confirmed: bool
    message: str
    activities: TripActivities
    totals: Totals


class TripRebookIn(BaseModel):
    month: str = Field(..., description="Move the whole trip to this month: 'november' or 'august'.")


class TripRebookOut(BaseModel):
    confirmed: bool
    message: str
    previous_month: str
    month: str
    dates: TripDates
    savings: float
    flights: TripFlights
    hotel: TripHotel
    transport: TripTransport
    activities: TripActivities
    totals: Totals


class TripConfigureIn(BaseModel):
    nights: int | None = Field(
        None, ge=NIGHTS_MIN, le=NIGHTS_MAX,
        description=f"How many nights on Maui ({NIGHTS_MIN}-{NIGHTS_MAX}). Omit to keep the current length.",
    )
    travelers: int | None = Field(
        None, ge=TRAVELERS_MIN, le=TRAVELERS_MAX,
        description=f"Total travelers including kids ({TRAVELERS_MIN}-{TRAVELERS_MAX}). Omit to keep the current party.",
    )
    rooms: int | None = Field(
        None, ge=ROOMS_MIN, le=ROOMS_MAX,
        description=f"How many hotel rooms ({ROOMS_MIN}-{ROOMS_MAX}). Omit to keep the current number.",
    )


class TripConfigureOut(BaseModel):
    confirmed: bool
    message: str
    dates: TripDates
    party: Party
    hotel: TripHotel
    transport: TripTransport
    activities: TripActivities
    flights: TripFlights
    totals: Totals


class PaymentIn(BaseModel):
    amount: float | None = Field(
        None, description="Amount to charge. Omit to charge the trip's current total."
    )
    currency: str = "USD"


class PaymentOut(BaseModel):
    confirmed: bool
    confirmation_code: str
    amount: float
    currency: str
    method: str
    message: str


class PayPalConfigOut(BaseModel):
    client_id: str
    currency: str


class PayPalCreateIn(BaseModel):
    amount: float | None = Field(
        None, description="Amount to charge. Omit to use the trip's current total."
    )


class PayPalCreateOut(BaseModel):
    order_id: str
    status: str | None = None
    approve_url: str | None = None
    amount: float
    currency: str


class PayPalCaptureIn(BaseModel):
    order_id: str = Field(..., description="order_id returned by create-order, after buyer approval.")


class PayPalCaptureOut(BaseModel):
    confirmed: bool
    status: str | None = None
    capture_id: str | None = None
    amount: float
    currency: str
    message: str


class ResetOut(BaseModel):
    reset: bool
    message: str


# --------------------------------------------------------------------------
# App setup
# --------------------------------------------------------------------------

async def mock_latency() -> None:
    """Add artificial latency so voice rehearsals match real API timing."""
    if config.MOCK_DELAY_SECONDS > 0:
        await asyncio.sleep(config.MOCK_DELAY_SECONDS)


app = FastAPI(
    title="Kiki — complete-trip demo API",
    description="Maui group-trip planning demo backend with Sabre-shaped mock data.",
    version="0.2.0",
    dependencies=[Depends(mock_latency)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
    return JSONResponse(status_code=501, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict:
    """Self-describing health check — says whether this URL is the mock or real service."""
    return {"status": "ok", "mock_mode": config.MOCK_MODE, **config.mode()}


class VoiceTokenIn(BaseModel):
    participant_name: str | None = Field(None, description="Display name for the voice session.")


@app.post("/token")
async def voice_token(body: VoiceTokenIn | None = None) -> JSONResponse:
    """Mint a short-lived Vocal Bridge voice token for the UI (VB API key stays server-side).

    Returns Vocal Bridge's token response verbatim ({token, livekit_url, room_name,
    participant_identity, expires_in, agent_mode}). On failure returns a clear
    { "error": {code, message} } body so the UI can show a connection error.
    """
    if not config.VB_API_KEY:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "not_configured",
                               "message": "Voice token minting not configured — VB_API_KEY is unset."}},
        )
    name = (body.participant_name if body else None) or "Web User"
    try:
        return JSONResponse(status_code=200, content=vb_client.mint_token(name))
    except httpx.HTTPStatusError as exc:  # VB rejected the request (bad key / agent id)
        return JSONResponse(
            status_code=502,
            content={"error": {"code": "vb_rejected",
                               "message": f"Vocal Bridge returned HTTP {exc.response.status_code}."}},
        )
    except Exception as exc:  # network / timeout — don't 500, keep the shape clear
        return JSONResponse(
            status_code=502,
            content={"error": {"code": "vb_unreachable", "message": str(exc)}},
        )


# --------------------------------------------------------------------------
# Endpoints — each docstring is one line so it can be reused verbatim as the
# voice-agent tool description.
# --------------------------------------------------------------------------

@app.post("/trip/status", response_model=TripStatusOut)
async def trip_status() -> dict:
    """Get the group's full Maui trip plan: dates, party, flights, hotel, transport, activities, running total, and whether it fits the budget."""
    if not config.MOCK_MODE:
        return sabre_client.get_trip_status()
    return {**TRIP, "totals": _totals(TRIP)}


@app.post("/flights/search", response_model=FlightSearchOut)
async def flights_search(body: FlightSearchIn | None = None) -> dict:
    """Search SFO to Maui (OGG) flights for the group and return three priced options, each with a tradeoff to read aloud."""
    month = _validate_month(body.month) if body and body.month else TRIP["month"]
    travelers = _travelers(TRIP)
    data = _FLIGHTS[month]
    resp = {
        "request": {**data["request"], "travelers": travelers},
        # The three bookable options are ALWAYS the curated mock set — so booking
        # (mock flight_ids) can't break and the narrative stays intact.
        "options": [_priced_option(o, travelers) for o in data["options"]],
        "sabre_live_fares": None,
    }
    # Hybrid real mode: attach live Sabre fares + a seasonality insight as proof
    # Kiki reads aloud. Best-effort — a stale token or empty result just omits it,
    # never breaks the search.
    if config.SABRE_FLIGHTS_LIVE:
        try:
            dates = _CATALOG[month]["dates"]
            depart = dates["start"]
            nights = TRIP.get("nights") or dates["nights"]
            proof = sabre_client.search_flights(
                origin="SFO", destination="OGG",
                depart_date=depart, return_date=_end_date(depart, nights), travelers=travelers,
            )
            resp["request"]["sabre_insight"] = proof["request"].get("sabre_insight")
            resp["request"]["sabre_source"] = proof["request"].get("source")
            resp["sabre_live_fares"] = proof["options"] or None
        except Exception:
            pass
    return resp


@app.post("/flights/book", response_model=FlightBookOut)
async def flights_book(body: FlightBookIn) -> dict:
    """Book the group onto a chosen flight by flight_id; requires explicit verbal confirmation first."""
    if not config.MOCK_MODE:
        return sabre_client.book_flight(flight_id=body.flight_id)

    option = next((o for o in _options(TRIP["month"]) if o["flight_id"] == body.flight_id), None)
    if option is None:
        valid = [o["flight_id"] for o in _options(TRIP["month"])]
        raise HTTPException(
            status_code=404,
            detail=f"Unknown flight_id '{body.flight_id}' for {TRIP['month']}. Valid options: {valid}",
        )

    travelers = _travelers(TRIP)
    locator = _confirmation("PNR")
    TRIP["flights"] = _flight_entry(option, "BOOKED", travelers, locator)
    return {
        "confirmed": True,
        "message": (
            f"Booked all {travelers} travelers on {option['carrier']} {option['flight_no']}, "
            f"SFO {option['depart_time']} → OGG {option['arrive_time']}, returning "
            f"{option['return_flight_no']} at {option['return_depart_time']}. "
            f"Total {TRIP['flights']['total_price']:.2f} USD."
        ),
        "record_locator": locator,
        "flights": TRIP["flights"],
        "totals": _totals(TRIP),
    }


@app.post("/hotel/adjust", response_model=HotelBookOut)
async def hotel_adjust() -> dict:
    """Book the two resort rooms on Maui for the trip's current dates and return the confirmation and total."""
    if not config.MOCK_MODE:
        return sabre_client.adjust_hotel(month=TRIP["month"])

    TRIP["hotel"]["status"] = "BOOKED"
    TRIP["hotel"]["confirmation_number"] = TRIP["hotel"].get("confirmation_number") or _confirmation("HTL")
    hotel = TRIP["hotel"]

    sabre_hotels = None
    sabre_hotel_insight = None
    if config.SABRE_HOTELS_LIVE:
        found = sabre_client.hotel_search(
            TRIP["destination"], hotel["check_in"], hotel["check_out"]
        )
        if found:
            sabre_hotels = found
            names = " and ".join(h["name"] for h in found[:2])
            sabre_hotel_insight = (
                f"Sabre is showing {len(found)} real Maui propert"
                f"{'y' if len(found) == 1 else 'ies'} for these dates, including {names}."
            )

    return {
        "confirmed": True,
        "message": (
            f"Booked {hotel['rooms']} {hotel['room_type']} rooms at {hotel['name']}, "
            f"{hotel['check_in']} to {hotel['check_out']} ({hotel['nights']} nights) — "
            f"{hotel['nightly_rate']:.2f} per room per night, {hotel['total']:.2f} USD total."
        ),
        "hotel": hotel,
        "totals": _totals(TRIP),
        "sabre_hotels": sabre_hotels,
        "sabre_hotel_insight": sabre_hotel_insight,
    }


@app.post("/transport/update", response_model=TransportBookOut)
async def transport_update() -> dict:
    """Book the minivan with a child car seat at Maui airport (OGG) for the trip's current dates and return the confirmation."""
    if not config.MOCK_MODE:
        return sabre_client.update_transport(month=TRIP["month"])

    TRIP["transport"]["status"] = "BOOKED"
    TRIP["transport"]["confirmation_number"] = (
        TRIP["transport"].get("confirmation_number") or _confirmation("CAR")
    )
    transport = TRIP["transport"]
    return {
        "confirmed": True,
        "message": (
            f"Booked a {transport['vehicle']} with a child car seat from {transport['provider']}, "
            f"picking up at {transport['pickup_location']} on {transport['pickup_date']} and "
            f"returning {transport['dropoff_date']} — {transport['total']:.2f} USD total."
        ),
        "transport": transport,
        "totals": _totals(TRIP),
    }


@app.post("/activities/book", response_model=ActivitiesBookOut)
async def activities_book(body: ActivitiesBookIn | None = None) -> dict:
    """Book the group's Maui experiences — a kid-friendly beginner surfing lesson and the Molokini snorkeling tour — for the trip's current dates."""
    requested = (body.activity if body else None) or None
    if not config.MOCK_MODE:
        return sabre_client.book_activities(activity=requested, month=TRIP["month"])

    items = TRIP["activities"]["items"]
    if requested:
        key = requested.strip().lower()
        targets = [a for a in items if a["activity_id"] == key]
        if not targets:
            valid = [a["activity_id"] for a in items]
            raise HTTPException(
                status_code=404,
                detail=f"Unknown activity '{requested}'. Valid options: {valid}",
            )
    else:
        targets = items

    for item in targets:
        item["status"] = "BOOKED"
        item["confirmation_number"] = item.get("confirmation_number") or _confirmation("ACT")

    TRIP["activities"]["status"] = (
        "BOOKED" if all(a["status"] == "BOOKED" for a in items) else "PARTIAL"
    )
    booked_total = round(sum(a["total"] for a in targets), 2)
    names = " and ".join(f"{a['name']} on {a['date']} at {a['time']}" for a in targets)
    return {
        "confirmed": True,
        "message": f"Booked {names} for all {_travelers(TRIP)} — {booked_total:.2f} USD total.",
        "activities": TRIP["activities"],
        "totals": _totals(TRIP),
    }


@app.post("/trip/configure", response_model=TripConfigureOut)
async def trip_configure(body: TripConfigureIn) -> dict:
    """Change the trip's size or length — number of nights, travelers, or hotel rooms — and re-price the whole trip; use this when they want anything other than the standard 5-person, 7-night plan."""
    if not config.MOCK_MODE:
        return sabre_client.configure_trip(
            nights=body.nights, travelers=body.travelers, rooms=body.rooms
        )

    changes = []
    if body.nights is not None:
        TRIP["nights"] = body.nights
        changes.append(f"{body.nights} nights")
    if body.travelers is not None:
        party = TRIP["party"]
        party["total"] = body.travelers
        party["adults"] = max(body.travelers - party.get("children", 0), 0)
        changes.append(f"{body.travelers} travelers")
    if body.rooms is not None:
        TRIP["party"]["rooms"] = body.rooms
        changes.append(f"{body.rooms} rooms")

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="Nothing to change — provide at least one of nights, travelers, or rooms.",
        )

    _apply_month(TRIP, TRIP["month"])  # single re-pricing path; keeps month + bookings
    totals = _totals(TRIP)
    dates = TRIP["dates"]
    return {
        "confirmed": True,
        "message": (
            f"Updated to {', '.join(changes)}: {_travelers(TRIP)} travelers, "
            f"{_rooms(TRIP)} rooms, {dates['nights']} nights ({dates['start']} to {dates['end']}). "
            f"New total {totals['trip_total']:.2f} USD — "
            + (
                f"{totals['over_budget_by']:.2f} over the {totals['budget']:.2f} budget."
                if not totals["within_budget"]
                else f"within the {totals['budget']:.2f} budget."
            )
        ),
        "dates": dates,
        "party": TRIP["party"],
        "hotel": TRIP["hotel"],
        "transport": TRIP["transport"],
        "activities": TRIP["activities"],
        "flights": TRIP["flights"],
        "totals": totals,
    }


@app.post("/trip/rebook", response_model=TripRebookOut)
async def trip_rebook(body: TripRebookIn) -> dict:
    """Move the entire trip to a different month — this re-dates and re-prices the flights, hotel, minivan, and activities together."""
    month = _validate_month(body.month)
    if not config.MOCK_MODE:
        return sabre_client.rebook_trip(month=month)

    previous_month = TRIP["month"]
    if month == previous_month:
        raise HTTPException(
            status_code=400,
            detail=f"The trip is already planned for {previous_month}.",
        )

    before = _totals(TRIP)["trip_total"]
    _apply_month(TRIP, month)
    after_totals = _totals(TRIP)
    savings = round(before - after_totals["trip_total"], 2)

    dates = TRIP["dates"]
    return {
        "confirmed": True,
        "message": (
            f"Moved the whole trip from {previous_month} to {dates['label']} "
            f"({dates['start']} to {dates['end']}). Flights, hotel, minivan, and both "
            f"activities are re-dated and re-priced — new total {after_totals['trip_total']:.2f} USD, "
            f"saving {savings:.2f}."
        ),
        "previous_month": previous_month,
        "month": month,
        "dates": dates,
        "savings": savings,
        "flights": TRIP["flights"],
        "hotel": TRIP["hotel"],
        "transport": TRIP["transport"],
        "activities": TRIP["activities"],
        "totals": after_totals,
    }


@app.post("/payment/confirm", response_model=PaymentOut)
async def payment_confirm(body: PaymentIn | None = None) -> dict:
    """Charge the card on file for the trip total and return a payment confirmation code."""
    if not config.PAYMENT_MOCK:
        raise NotImplementedError(
            "Real payment processing is not integrated yet — set PAYMENT_MOCK=true."
        )

    totals = _totals(TRIP)
    amount = body.amount if body and body.amount is not None else totals["trip_total"]
    currency = body.currency if body else "USD"

    record = {
        "confirmation_code": f"PAY-{uuid.uuid4().hex[:8].upper()}",
        "amount": round(amount, 2),
        "currency": currency,
        "method": "Visa ending 4242 (card on file)",
        "status": "PAID",
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    TRIP["payments"].append(record)
    TRIP["status"] = "BOOKED"
    return {
        "confirmed": True,
        "confirmation_code": record["confirmation_code"],
        "amount": record["amount"],
        "currency": record["currency"],
        "method": record["method"],
        "message": (
            f"Payment of {record['amount']:.2f} {record['currency']} approved. "
            f"Confirmation {record['confirmation_code']}."
        ),
    }


# --------------------------------------------------------------------------
# Real PayPal (sandbox) — only enabled on the "real" service (PAYPAL_LIVE=true).
# The itinerary UI drives these via the PayPal JS SDK button:
#   config -> create-order -> (buyer approves in the button) -> capture-order.
# --------------------------------------------------------------------------

def _require_paypal() -> None:
    if not config.PAYPAL_LIVE:
        raise HTTPException(
            status_code=404,
            detail="PayPal is not enabled on this service (mock version). Use /payment/confirm.",
        )


@app.get("/payment/paypal/config", response_model=PayPalConfigOut)
async def paypal_config() -> dict:
    """Public PayPal client id + currency for the UI's PayPal JS SDK (safe to expose)."""
    _require_paypal()
    return {"client_id": config.PAYPAL_CLIENT_ID, "currency": config.PAYPAL_CURRENCY}


@app.post("/payment/paypal/create-order", response_model=PayPalCreateOut)
async def paypal_create_order(body: PayPalCreateIn | None = None) -> dict:
    """Create a PayPal sandbox order for the trip total (or a given amount) and return its order_id."""
    _require_paypal()
    amount = round(
        body.amount if body and body.amount is not None else _totals(TRIP)["trip_total"], 2
    )
    result = paypal_client.create_order(amount=amount, currency=config.PAYPAL_CURRENCY)
    return {**result, "amount": amount, "currency": config.PAYPAL_CURRENCY}


@app.post("/payment/paypal/capture-order", response_model=PayPalCaptureOut)
async def paypal_capture_order(body: PayPalCaptureIn) -> dict:
    """Capture an approved PayPal sandbox order and record the payment on the trip."""
    _require_paypal()
    cap = paypal_client.capture_order(body.order_id)
    paid = cap.get("status") == "COMPLETED"
    if paid:
        TRIP["payments"].append({
            "confirmation_code": cap.get("capture_id") or "PAYPAL",
            "amount": cap["amount"],
            "currency": cap["currency"],
            "method": f"PayPal sandbox ({cap.get('payer_email') or 'buyer'})",
            "status": "PAID",
            "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        TRIP["status"] = "BOOKED"
    return {
        "confirmed": paid,
        "status": cap.get("status"),
        "capture_id": cap.get("capture_id"),
        "amount": cap["amount"],
        "currency": cap["currency"],
        "message": (
            f"PayPal payment {cap.get('status')} — {cap['amount']:.2f} {cap['currency']}"
            + (f", capture {cap['capture_id']}." if cap.get("capture_id") else ".")
        ),
    }


@app.post("/demo/reset", response_model=ResetOut)
async def demo_reset() -> dict:
    """Reset the demo to its initial state, with the group planning the first week of November and nothing booked yet."""
    TRIP.clear()
    TRIP.update(_build_initial_trip())
    totals = _totals(TRIP)
    budget_line = (
        f"{totals['over_budget_by']:.2f} over the {totals['budget']:.2f} budget"
        if not totals["within_budget"]
        else f"within the {totals['budget']:.2f} budget"
    )
    return {
        "reset": True,
        "message": (
            f"Trip restored to planning {TRIP['dates']['label']} "
            f"({TRIP['dates']['start']} to {TRIP['dates']['end']}), nothing booked. "
            f"Quote {totals['trip_total']:.2f} USD — {budget_line}."
        ),
    }
