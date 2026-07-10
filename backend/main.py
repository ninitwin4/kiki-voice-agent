"""Kiki — voice-agent travel demo backend (project: complete-trip).

Simulates trip-disruption recovery for traveler Mary (SFO→AUS tonight for her
sister's wedding) with Sabre-shaped mock data. All state lives in a single
in-memory TRIP object; POST /demo/reset restores the initial fixture so the
demo can be rehearsed repeatedly.
"""
import asyncio
import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config, sabre_client

MOCKS_DIR = Path(__file__).parent / "mocks"

_INITIAL_TRIP: dict = json.loads((MOCKS_DIR / "trip.json").read_text())
_FLIGHT_SEARCH: dict = json.loads((MOCKS_DIR / "flight_search.json").read_text())

# The single shared demo state. Endpoints mutate it in place so
# /trip/status reflects the demo's progress.
TRIP: dict = copy.deepcopy(_INITIAL_TRIP)


# --------------------------------------------------------------------------
# Pydantic models (kept explicit so the OpenAPI spec is clean enough to hand
# straight to a voice platform's tool config)
# --------------------------------------------------------------------------

class Traveler(BaseModel):
    name: str
    email: str
    loyalty: str


class TripFlightSegment(BaseModel):
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    status: str
    cancellation_reason: str | None = None


class TripFlight(BaseModel):
    record_locator: str
    cabin: str
    fare_paid: float
    rebooked_fare: float | None = None
    status: str
    segments: list[TripFlightSegment]


class TripHotel(BaseModel):
    name: str
    confirmation_number: str
    check_in: str
    nights: int
    late_checkin: bool
    guaranteed_until: str
    status: str
    note: str | None = None


class TripTransport(BaseModel):
    provider: str
    confirmation_number: str
    pickup_location: str
    pickup_time: str
    status: str
    note: str | None = None


class TripDining(BaseModel):
    venue: str
    event: str
    party_size: int
    time: str
    status: str
    note: str | None = None


class PaymentRecord(BaseModel):
    confirmation_code: str
    amount: float
    currency: str
    method: str
    status: str
    processed_at: str


class TripStatusOut(BaseModel):
    trip_id: str
    traveler: Traveler
    purpose: str
    flight: TripFlight
    hotel: TripHotel
    transport: TripTransport
    dining: TripDining
    payments: list[PaymentRecord]


class Fare(BaseModel):
    amount: float
    currency: str


class SearchSegment(BaseModel):
    carrier: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration: str
    aircraft: str


class Itinerary(BaseModel):
    flight_id: str
    recommended: bool
    reason: str
    cabin: str
    seats_remaining: int
    totalFare: Fare
    segments: list[SearchSegment]


class SearchRequestEcho(BaseModel):
    origin: str
    destination: str
    date: str
    source: str


class FlightSearchOut(BaseModel):
    request: SearchRequestEcho
    itineraries: list[Itinerary]


class RebookIn(BaseModel):
    flight_id: str = Field(..., description="flight_id from /flights/search, e.g. 'AA1885'")


class RebookOut(BaseModel):
    confirmed: bool
    message: str
    record_locator: str
    price_difference: float
    currency: str
    flight: TripFlight


class HotelAdjustIn(BaseModel):
    late_checkin: bool = True
    expected_arrival: str | None = Field(None, description="Expected arrival at the hotel, e.g. '22:30'")


class HotelAdjustOut(BaseModel):
    confirmed: bool
    message: str
    hotel: TripHotel


class DiningMoveIn(BaseModel):
    new_time: str = Field(..., description="New reservation time, e.g. '22:00'")


class DiningMoveOut(BaseModel):
    confirmed: bool
    message: str
    dining: TripDining


class TransportUpdateIn(BaseModel):
    new_pickup_time: str = Field(..., description="New pickup time at AUS arrivals, e.g. '21:45'")
    flight_number: str | None = Field(None, description="Flight the pickup should track, e.g. 'AA 1885'")


class TransportUpdateOut(BaseModel):
    confirmed: bool
    message: str
    transport: TripTransport


class PaymentIn(BaseModel):
    amount: float = Field(..., description="Amount to charge, e.g. the rebooking price difference")
    currency: str = "USD"


class PaymentOut(BaseModel):
    confirmed: bool
    confirmation_code: str
    amount: float
    currency: str
    method: str
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
    description="Trip-disruption recovery demo backend with Sabre-shaped mock data.",
    version="0.1.0",
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


# --------------------------------------------------------------------------
# Endpoints — each docstring is one line so it can be reused verbatim as the
# voice-agent tool description.
# --------------------------------------------------------------------------

@app.post("/trip/status", response_model=TripStatusOut)
async def trip_status() -> dict:
    """Get Mary's full trip itinerary with the current status of the flight, hotel, airport pickup, and rehearsal dinner."""
    if not config.MOCK_MODE:
        return sabre_client.get_trip_status()
    return TRIP


@app.post("/flights/search", response_model=FlightSearchOut)
async def flights_search() -> dict:
    """Search for alternative SFO to AUS flights tonight and return priced itineraries with a recommended option."""
    if not config.MOCK_MODE:
        return sabre_client.search_flights(origin="SFO", destination="AUS")
    return _FLIGHT_SEARCH


@app.post("/flights/rebook", response_model=RebookOut)
async def flights_rebook(body: RebookIn) -> dict:
    """Rebook Mary onto the chosen alternative flight by flight_id and return the confirmation and price difference."""
    if not config.MOCK_MODE:
        return sabre_client.rebook_flight(flight_id=body.flight_id)

    itinerary = next(
        (i for i in _FLIGHT_SEARCH["itineraries"] if i["flight_id"] == body.flight_id),
        None,
    )
    if itinerary is None:
        valid = [i["flight_id"] for i in _FLIGHT_SEARCH["itineraries"]]
        raise HTTPException(status_code=404, detail=f"Unknown flight_id '{body.flight_id}'. Valid options: {valid}")

    price_difference = round(itinerary["totalFare"]["amount"] - TRIP["flight"]["fare_paid"], 2)
    TRIP["flight"]["segments"] = [
        {
            "flight_number": seg["flight_number"],
            "origin": seg["origin"],
            "destination": seg["destination"],
            "departure_time": seg["departure_time"],
            "arrival_time": seg["arrival_time"],
            "status": "CONFIRMED",
            "cancellation_reason": None,
        }
        for seg in itinerary["segments"]
    ]
    TRIP["flight"]["status"] = "CONFIRMED"
    TRIP["flight"]["cabin"] = itinerary["cabin"]
    TRIP["flight"]["rebooked_fare"] = itinerary["totalFare"]["amount"]

    first, last = itinerary["segments"][0], itinerary["segments"][-1]
    return {
        "confirmed": True,
        "message": (
            f"Rebooked on {first['flight_number']}, departing SFO at {first['departure_time']} "
            f"and arriving AUS at {last['arrival_time']}."
        ),
        "record_locator": TRIP["flight"]["record_locator"],
        "price_difference": price_difference,
        "currency": itinerary["totalFare"]["currency"],
        "flight": TRIP["flight"],
    }


@app.post("/hotel/adjust", response_model=HotelAdjustOut)
async def hotel_adjust(body: HotelAdjustIn | None = None) -> dict:
    """Flag a late check-in on Mary's hotel reservation so the room is held past the release time."""
    if not config.MOCK_MODE:
        return sabre_client.adjust_hotel(
            late_checkin=body.late_checkin if body else True,
            expected_arrival=body.expected_arrival if body else None,
        )

    late_checkin = body.late_checkin if body else True
    expected = (body.expected_arrival if body else None) or "late tonight"
    TRIP["hotel"]["late_checkin"] = late_checkin
    TRIP["hotel"]["status"] = "CONFIRMED" if late_checkin else "AT_RISK"
    TRIP["hotel"]["note"] = (
        f"Late arrival on file — room held all night (expected arrival {expected})"
        if late_checkin
        else TRIP["hotel"]["note"]
    )
    return {
        "confirmed": True,
        "message": f"{TRIP['hotel']['name']} will hold the room for a late check-in (expected arrival {expected}).",
        "hotel": TRIP["hotel"],
    }


@app.post("/dining/move", response_model=DiningMoveOut)
async def dining_move(body: DiningMoveIn) -> dict:
    """Move the rehearsal-dinner reservation to a new time and return the updated reservation."""
    if not config.MOCK_MODE:
        return sabre_client.move_dining(new_time=body.new_time)

    TRIP["dining"]["time"] = body.new_time
    TRIP["dining"]["status"] = "CONFIRMED"
    TRIP["dining"]["note"] = f"Moved to {body.new_time} for Mary's late arrival"
    return {
        "confirmed": True,
        "message": (
            f"Rehearsal dinner at {TRIP['dining']['venue']} moved to {body.new_time} "
            f"for a party of {TRIP['dining']['party_size']}."
        ),
        "dining": TRIP["dining"],
    }


@app.post("/transport/update", response_model=TransportUpdateOut)
async def transport_update(body: TransportUpdateIn) -> dict:
    """Re-time Mary's airport pickup to match the new flight arrival and return the confirmation."""
    if not config.MOCK_MODE:
        return sabre_client.update_transport(
            new_pickup_time=body.new_pickup_time, flight_number=body.flight_number
        )

    TRIP["transport"]["pickup_time"] = body.new_pickup_time
    TRIP["transport"]["status"] = "CONFIRMED"
    tracked = body.flight_number or TRIP["flight"]["segments"][-1]["flight_number"]
    TRIP["transport"]["note"] = f"Pickup re-timed to {body.new_pickup_time}, tracking {tracked}"
    return {
        "confirmed": True,
        "message": (
            f"{TRIP['transport']['provider']} pickup moved to {body.new_pickup_time} "
            f"at {TRIP['transport']['pickup_location']}."
        ),
        "transport": TRIP["transport"],
    }


@app.post("/payment/confirm", response_model=PaymentOut)
async def payment_confirm(body: PaymentIn) -> dict:
    """Charge the traveler's card on file for the given amount and return a payment confirmation code."""
    if not config.PAYMENT_MOCK:
        raise NotImplementedError(
            "Real payment processing is not integrated yet — set PAYMENT_MOCK=true."
        )

    record = {
        "confirmation_code": f"PAY-{uuid.uuid4().hex[:8].upper()}",
        "amount": round(body.amount, 2),
        "currency": body.currency,
        "method": "Visa ending 4242 (card on file)",
        "status": "PAID",
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    TRIP["payments"].append(record)
    return {
        "confirmed": True,
        "confirmation_code": record["confirmation_code"],
        "amount": record["amount"],
        "currency": record["currency"],
        "method": record["method"],
        "message": f"Payment of {record['amount']:.2f} {record['currency']} approved. Confirmation {record['confirmation_code']}.",
    }


@app.post("/demo/reset", response_model=ResetOut)
async def demo_reset() -> dict:
    """Reset the demo to its initial state, with Mary's original flight cancelled and everything else at risk."""
    TRIP.clear()
    TRIP.update(copy.deepcopy(_INITIAL_TRIP))
    return {"reset": True, "message": "Trip restored to initial state: AA 2418 is CANCELLED again."}


@app.get("/health")
async def health() -> dict:
    """Liveness check (also useful as the Render health-check path)."""
    return {"status": "ok", "mock_mode": config.MOCK_MODE}
