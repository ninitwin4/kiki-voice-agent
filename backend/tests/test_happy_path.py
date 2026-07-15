"""Maui group-trip demo.

Two paths matter:
  * happy path  — plan August → book all 4 vendors → pay
  * rebook path — August → October cascades every vendor's dates and prices
"""
import pytest

AUG_FLIGHT_IDS = {"AA289", "AA1412", "AA674"}
OCT_FLIGHT_IDS = {"AA293", "AA1428", "AA682"}


def test_full_demo_happy_path_august(client):
    # 1. Initial state: planning August, nothing booked, over budget.
    trip = client.post("/trip/status").json()
    assert trip["status"] == "PLANNING"
    assert trip["month"] == "august"
    assert trip["dates"]["start"] == "2026-08-03"
    assert trip["party"]["total"] == 5
    assert trip["party"]["rooms"] == 2
    assert trip["flights"]["status"] == "NOT_BOOKED"
    assert trip["hotel"]["status"] == "NOT_BOOKED"
    assert trip["transport"]["status"] == "NOT_BOOKED"
    assert trip["activities"]["status"] == "NOT_BOOKED"
    assert trip["payments"] == []
    # The constraint that drives the demo: August blows the budget.
    assert trip["totals"]["within_budget"] is False
    assert trip["totals"]["over_budget_by"] > 0

    # 2. Search: three options, exactly one recommended, each with a tradeoff.
    search = client.post("/flights/search", json={"month": "august"}).json()
    assert search["request"]["destination"] == "OGG"
    assert search["request"]["travelers"] == 5
    assert len(search["options"]) == 3
    assert {o["flight_id"] for o in search["options"]} == AUG_FLIGHT_IDS
    assert all(o["tradeoff"] for o in search["options"])
    assert all(o["total_price"] == pytest.approx(o["price_pp"] * 5) for o in search["options"])
    recommended = [o for o in search["options"] if o["recommended"]]
    assert len(recommended) == 1
    best = recommended[0]
    assert best["flight_id"] == "AA289"
    assert best["stops"] == 0

    # 3. Book the recommended flight for all 5.
    booked = client.post("/flights/book", json={"flight_id": best["flight_id"]})
    assert booked.status_code == 200
    body = booked.json()
    assert body["confirmed"] is True
    assert body["record_locator"].startswith("PNR-")
    assert body["flights"]["status"] == "BOOKED"
    assert body["flights"]["total_price"] == pytest.approx(3910.0)
    assert body["totals"]["flights_quoted"] is False

    # 4. Hotel — two rooms for the August week.
    hotel = client.post("/hotel/adjust").json()
    assert hotel["confirmed"] is True
    assert hotel["hotel"]["status"] == "BOOKED"
    assert hotel["hotel"]["rooms"] == 2
    assert hotel["hotel"]["check_in"] == "2026-08-03"
    assert hotel["hotel"]["check_out"] == "2026-08-10"
    assert hotel["hotel"]["total"] == pytest.approx(685.0 * 2 * 7)

    # 5. Transport — minivan + child car seat at OGG.
    transport = client.post("/transport/update").json()
    assert transport["confirmed"] is True
    assert transport["transport"]["status"] == "BOOKED"
    assert transport["transport"]["car_seat"] is True
    assert transport["transport"]["pickup_location"].startswith("OGG")
    assert transport["transport"]["pickup_date"] == "2026-08-03"

    # 6. Activities — surf lesson + Molokini snorkel, both booked.
    activities = client.post("/activities/book").json()
    assert activities["confirmed"] is True
    assert activities["activities"]["status"] == "BOOKED"
    assert {a["activity_id"] for a in activities["activities"]["items"]} == {"surf", "snorkel"}
    assert all(a["status"] == "BOOKED" for a in activities["activities"]["items"])
    assert all(a["participants"] == 5 for a in activities["activities"]["items"])
    surf = next(a for a in activities["activities"]["items"] if a["activity_id"] == "surf")
    assert surf["kid_friendly"] is True
    assert surf["date"].startswith("2026-08")

    # 7. Pay the trip total (no amount → charges the running total).
    expected_total = client.post("/trip/status").json()["totals"]["trip_total"]
    payment = client.post("/payment/confirm", json={}).json()
    assert payment["confirmed"] is True
    assert payment["confirmation_code"].startswith("PAY-")
    assert payment["amount"] == pytest.approx(expected_total)

    # 8. Final: everything booked and the payment is on the trip.
    trip = client.post("/trip/status").json()
    assert trip["status"] == "BOOKED"
    assert trip["flights"]["status"] == "BOOKED"
    assert trip["hotel"]["status"] == "BOOKED"
    assert trip["transport"]["status"] == "BOOKED"
    assert trip["activities"]["status"] == "BOOKED"
    assert len(trip["payments"]) == 1
    assert trip["payments"][0]["status"] == "PAID"


def test_rebook_august_to_october_cascades_every_vendor(client):
    # Book the whole trip in August first.
    client.post("/flights/book", json={"flight_id": "AA289"})
    client.post("/hotel/adjust")
    client.post("/transport/update")
    client.post("/activities/book")

    before = client.post("/trip/status").json()
    assert before["month"] == "august"
    assert before["totals"]["within_budget"] is False
    august_total = before["totals"]["trip_total"]

    # The constraint surfaces → move the whole trip to October.
    rebook = client.post("/trip/rebook", json={"month": "october"})
    assert rebook.status_code == 200
    body = rebook.json()
    assert body["confirmed"] is True
    assert body["previous_month"] == "august"
    assert body["month"] == "october"
    assert body["savings"] > 0

    # The cascade: every vendor moved to October dates AND October prices,
    # and everything that was booked stays booked.
    assert body["dates"]["start"] == "2026-10-05"
    assert body["dates"]["end"] == "2026-10-12"

    assert body["flights"]["status"] == "BOOKED"
    assert body["flights"]["flight_id"] == "AA293"  # same tier A, October equivalent
    assert body["flights"]["tier"] == "A"
    assert body["flights"]["total_price"] == pytest.approx(2980.0)

    assert body["hotel"]["status"] == "BOOKED"
    assert body["hotel"]["check_in"] == "2026-10-05"
    assert body["hotel"]["check_out"] == "2026-10-12"
    assert body["hotel"]["total"] == pytest.approx(512.0 * 2 * 7)

    assert body["transport"]["status"] == "BOOKED"
    assert body["transport"]["pickup_date"] == "2026-10-05"
    assert body["transport"]["dropoff_date"] == "2026-10-12"
    assert body["transport"]["car_seat"] is True

    assert body["activities"]["status"] == "BOOKED"
    for item in body["activities"]["items"]:
        assert item["status"] == "BOOKED"
        assert item["date"].startswith("2026-10")

    # October lands inside budget — the whole point of the move.
    assert body["totals"]["within_budget"] is True
    assert body["totals"]["trip_total"] < august_total
    assert body["totals"]["over_budget_by"] == 0

    # /trip/status re-flows the entire trip on the new dates.
    after = client.post("/trip/status").json()
    assert after["month"] == "october"
    assert after["dates"]["season"] == "shoulder"
    assert after["flights"]["flight_id"] == "AA293"
    assert after["hotel"]["check_in"] == "2026-10-05"
    assert after["totals"]["trip_total"] == pytest.approx(body["totals"]["trip_total"])


def test_august_and_october_return_real_and_different_data(client):
    august = client.post("/flights/search", json={"month": "august"}).json()
    october = client.post("/flights/search", json={"month": "october"}).json()

    aug_ids = {o["flight_id"] for o in august["options"]}
    oct_ids = {o["flight_id"] for o in october["options"]}
    assert aug_ids == AUG_FLIGHT_IDS
    assert oct_ids == OCT_FLIGHT_IDS
    assert aug_ids.isdisjoint(oct_ids)  # genuinely different flight numbers

    # Shoulder season is cheaper on every tier — this is what sells the rebook.
    aug_by_tier = {o["tier"]: o for o in august["options"]}
    oct_by_tier = {o["tier"]: o for o in october["options"]}
    for tier in ("A", "B", "C"):
        assert oct_by_tier[tier]["price_pp"] < aug_by_tier[tier]["price_pp"]
        assert oct_by_tier[tier]["depart_time"] != aug_by_tier[tier]["depart_time"]


def test_option_shapes_cover_the_three_intended_tradeoffs(client):
    for month in ("august", "october"):
        options = client.post("/flights/search", json={"month": month}).json()["options"]
        by_tier = {o["tier"]: o for o in options}

        # A: nonstop, pricier, and the recommended one.
        assert by_tier["A"]["stops"] == 0
        assert by_tier["A"]["recommended"] is True
        assert by_tier["A"]["price_pp"] > by_tier["B"]["price_pp"]

        # B: one-stop, cheapest.
        assert by_tier["B"]["stops"] == 1
        assert by_tier["B"]["price_pp"] == min(o["price_pp"] for o in options)

        # C: nonstop but an early return — the option the group rejects.
        assert by_tier["C"]["stops"] == 0
        assert by_tier["C"]["return_depart_time"] < "07:00"


def test_search_defaults_to_the_trips_current_month(client):
    assert client.post("/flights/search", json={}).json()["request"]["month"] == "august"
    client.post("/trip/rebook", json={"month": "october"})
    assert client.post("/flights/search", json={}).json()["request"]["month"] == "october"


def test_book_single_activity_marks_partial(client):
    body = client.post("/activities/book", json={"activity": "surf"}).json()
    assert body["activities"]["status"] == "PARTIAL"
    surf = next(a for a in body["activities"]["items"] if a["activity_id"] == "surf")
    snorkel = next(a for a in body["activities"]["items"] if a["activity_id"] == "snorkel")
    assert surf["status"] == "BOOKED"
    assert snorkel["status"] == "NOT_BOOKED"


def test_reset_restores_initial_august_planning_state(client):
    client.post("/flights/book", json={"flight_id": "AA289"})
    client.post("/hotel/adjust")
    client.post("/trip/rebook", json={"month": "october"})
    client.post("/payment/confirm", json={})

    reset = client.post("/demo/reset").json()
    assert reset["reset"] is True

    trip = client.post("/trip/status").json()
    assert trip["status"] == "PLANNING"
    assert trip["month"] == "august"
    assert trip["dates"]["start"] == "2026-08-03"
    assert trip["flights"]["status"] == "NOT_BOOKED"
    assert trip["hotel"]["status"] == "NOT_BOOKED"
    assert trip["transport"]["status"] == "NOT_BOOKED"
    assert trip["activities"]["status"] == "NOT_BOOKED"
    assert trip["payments"] == []
    assert trip["totals"]["within_budget"] is False


def test_book_unknown_flight_id_is_404(client):
    resp = client.post("/flights/book", json={"flight_id": "UA999"})
    assert resp.status_code == 404
    assert "AA289" in resp.json()["detail"]


def test_rebook_unknown_month_is_404(client):
    resp = client.post("/trip/rebook", json={"month": "december"})
    assert resp.status_code == 404
    assert "august" in resp.json()["detail"]


def test_rebook_to_the_same_month_is_400(client):
    resp = client.post("/trip/rebook", json={"month": "august"})
    assert resp.status_code == 400
