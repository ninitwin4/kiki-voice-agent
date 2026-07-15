"""Stub adapter for the real Sabre (and payment) APIs.

Each function mirrors one mock-mode endpoint in main.py and must return the
exact same JSON shape as its backend/mocks/ counterpart, so flipping
MOCK_MODE=false is the only change needed to go live. Until implemented,
every call raises NotImplementedError, which main.py maps to HTTP 501.
"""


def get_trip_status() -> dict:
    """TODO: fetch the PNR via Sabre Get Reservation and map it to the trip shape."""
    raise NotImplementedError("Sabre Get Reservation is not integrated yet — set MOCK_MODE=true.")


def search_flights(origin: str, destination: str, month: str) -> dict:
    """TODO: call Sabre Bargain Finder Max for SFO⇄OGG on the month's dates, map to the flight_search shape."""
    raise NotImplementedError("Sabre Bargain Finder Max is not integrated yet — set MOCK_MODE=true.")


def book_flight(flight_id: str) -> dict:
    """TODO: book the selected itinerary for 5 travelers via Sabre, return the FlightBookOut shape."""
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


def rebook_trip(month: str) -> dict:
    """TODO: exchange the ticket and move every vendor booking to the new month's dates, return the TripRebookOut shape."""
    raise NotImplementedError("Sabre exchanges are not integrated yet — set MOCK_MODE=true.")


def confirm_payment(amount: float, currency: str) -> dict:
    """TODO: charge via the real payment provider (e.g. PayPal), return the PaymentOut shape."""
    raise NotImplementedError("Real payment processing is not integrated yet — set PAYMENT_MOCK=true.")
