"""Stub adapter for the real Sabre (and payment) APIs.

Each function mirrors one mock-mode endpoint in main.py and must return the
exact same JSON shape as its backend/mocks/ counterpart, so flipping
MOCK_MODE=false is the only change needed to go live. Until implemented,
every call raises NotImplementedError, which main.py maps to HTTP 501.
"""


def get_trip_status() -> dict:
    """TODO: fetch the PNR via Sabre Get Reservation and map it to the trip.json shape."""
    raise NotImplementedError("Sabre Get Reservation is not integrated yet — set MOCK_MODE=true.")


def search_flights(origin: str, destination: str) -> dict:
    """TODO: call Sabre Bargain Finder Max and map itineraries to the flight_search.json shape."""
    raise NotImplementedError("Sabre Bargain Finder Max is not integrated yet — set MOCK_MODE=true.")


def rebook_flight(flight_id: str) -> dict:
    """TODO: exchange the ticket via Sabre (cancel segment + book selected itinerary), return RebookOut shape."""
    raise NotImplementedError("Sabre rebooking is not integrated yet — set MOCK_MODE=true.")


def adjust_hotel(late_checkin: bool, expected_arrival: str | None) -> dict:
    """TODO: update the hotel booking via Sabre Content Services for Lodging, return HotelAdjustOut shape."""
    raise NotImplementedError("Sabre hotel modification is not integrated yet — set MOCK_MODE=true.")


def move_dining(new_time: str) -> dict:
    """TODO: integrate a restaurant-reservation provider (dining is not a Sabre product), return DiningMoveOut shape."""
    raise NotImplementedError("Dining-reservation integration is not implemented yet — set MOCK_MODE=true.")


def update_transport(new_pickup_time: str, flight_number: str | None) -> dict:
    """TODO: re-time the ground transport booking with the provider, return TransportUpdateOut shape."""
    raise NotImplementedError("Ground-transport integration is not implemented yet — set MOCK_MODE=true.")


def confirm_payment(amount: float, currency: str) -> dict:
    """TODO: charge via the real payment provider (e.g. PayPal), return PaymentOut shape."""
    raise NotImplementedError("Real payment processing is not integrated yet — set PAYMENT_MOCK=true.")
