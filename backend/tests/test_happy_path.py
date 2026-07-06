"""Full demo happy path: status → search → rebook → hotel → dining →
transport → payment → status shows all green."""
import pytest


def test_full_demo_happy_path(client):
    # 1. Initial status: flight cancelled, everything else at risk.
    trip = client.post("/trip/status").json()
    assert trip["flight"]["status"] == "CANCELLED"
    assert trip["flight"]["segments"][0]["status"] == "CANCELLED"
    assert trip["hotel"]["status"] == "AT_RISK"
    assert trip["dining"]["status"] == "AT_RISK"
    assert trip["payments"] == []

    # 2. Search: three alternatives, exactly one recommended.
    search = client.post("/flights/search").json()
    assert len(search["itineraries"]) == 3
    recommended = [i for i in search["itineraries"] if i["recommended"]]
    assert len(recommended) == 1
    best = recommended[0]
    assert best["flight_id"] == "AA1885"

    # 3. Rebook onto the recommended flight.
    rebook = client.post("/flights/rebook", json={"flight_id": best["flight_id"]})
    assert rebook.status_code == 200
    body = rebook.json()
    assert body["confirmed"] is True
    assert body["price_difference"] == pytest.approx(209.40 - 164.20)
    assert body["flight"]["status"] == "CONFIRMED"

    # 4. Hotel late check-in.
    hotel = client.post("/hotel/adjust", json={"expected_arrival": "22:30"}).json()
    assert hotel["confirmed"] is True
    assert hotel["hotel"]["late_checkin"] is True
    assert hotel["hotel"]["status"] == "CONFIRMED"

    # 5. Move the rehearsal dinner.
    dining = client.post("/dining/move", json={"new_time": "22:00"}).json()
    assert dining["confirmed"] is True
    assert dining["dining"]["time"] == "22:00"

    # 6. Re-time the airport pickup.
    transport = client.post(
        "/transport/update",
        json={"new_pickup_time": "21:45", "flight_number": "AA 1885"},
    ).json()
    assert transport["confirmed"] is True
    assert transport["transport"]["pickup_time"] == "21:45"

    # 7. Pay the fare difference.
    payment = client.post("/payment/confirm", json={"amount": 45.20}).json()
    assert payment["confirmed"] is True
    assert payment["confirmation_code"].startswith("PAY-")

    # 8. Final status: everything green and the payment is on the trip.
    trip = client.post("/trip/status").json()
    assert trip["flight"]["status"] == "CONFIRMED"
    assert all(seg["status"] == "CONFIRMED" for seg in trip["flight"]["segments"])
    assert trip["hotel"]["status"] == "CONFIRMED"
    assert trip["dining"]["status"] == "CONFIRMED"
    assert trip["transport"]["status"] == "CONFIRMED"
    assert len(trip["payments"]) == 1
    assert trip["payments"][0]["status"] == "PAID"


def test_reset_restores_initial_state(client):
    client.post("/flights/rebook", json={"flight_id": "AA1885"})
    client.post("/hotel/adjust", json={})
    client.post("/payment/confirm", json={"amount": 45.20})

    reset = client.post("/demo/reset").json()
    assert reset["reset"] is True

    trip = client.post("/trip/status").json()
    assert trip["flight"]["status"] == "CANCELLED"
    assert trip["hotel"]["late_checkin"] is False
    assert trip["payments"] == []


def test_rebook_unknown_flight_id_is_404(client):
    resp = client.post("/flights/rebook", json={"flight_id": "UA123"})
    assert resp.status_code == 404
    assert "AA1885" in resp.json()["detail"]
