"""Maui group-trip demo — Ni Ni & RC, the "weather cascade".

Two paths matter:
  * happy path  — plan November → book all 4 vendors → pay
  * rebook path — November → August cascades every vendor's dates and prices
    (the demo's weather-driven move: November is rainy, August is dry)
"""
import pytest

NOV_FLIGHT_IDS = {"AA511", "AA1620", "AA742"}
AUG_FLIGHT_IDS = {"AA289", "AA1412", "AA674"}


def test_full_demo_happy_path_november(client):
    # 1. Initial state: planning November, nothing booked.
    trip = client.post("/trip/status").json()
    assert trip["status"] == "PLANNING"
    assert trip["month"] == "november"
    assert trip["dates"]["start"] == "2026-11-02"
    assert trip["dates"]["end"] == "2026-11-07"
    assert trip["dates"]["nights"] == 5
    assert trip["party"]["total"] == 5
    assert trip["party"]["rooms"] == 2
    assert trip["flights"]["status"] == "NOT_BOOKED"
    assert trip["hotel"]["status"] == "NOT_BOOKED"
    assert trip["transport"]["status"] == "NOT_BOOKED"
    assert trip["activities"]["status"] == "NOT_BOOKED"
    assert trip["payments"] == []
    # November (off-season) sits inside budget.
    assert trip["totals"]["within_budget"] is True
    assert trip["totals"]["trip_total"] == pytest.approx(2980 + 4800 + 400 + 990)

    # 2. Search: three options, exactly one recommended, each with a tradeoff.
    search = client.post("/flights/search", json={"month": "november"}).json()
    assert search["request"]["destination"] == "OGG"
    assert search["request"]["travelers"] == 5
    assert len(search["options"]) == 3
    assert {o["flight_id"] for o in search["options"]} == NOV_FLIGHT_IDS
    assert all(o["tradeoff"] for o in search["options"])
    assert all(o["total_price"] == pytest.approx(o["price_pp"] * 5) for o in search["options"])
    recommended = [o for o in search["options"] if o["recommended"]]
    assert len(recommended) == 1
    best = recommended[0]
    assert best["flight_id"] == "AA511"
    assert best["stops"] == 0

    # 3. Book the recommended flight for all 5.
    booked = client.post("/flights/book", json={"flight_id": best["flight_id"]})
    assert booked.status_code == 200
    body = booked.json()
    assert body["confirmed"] is True
    assert body["record_locator"].startswith("PNR-")
    assert body["flights"]["status"] == "BOOKED"
    assert body["flights"]["total_price"] == pytest.approx(2980.0)

    # 4. Hotel — two rooms for the November week.
    hotel = client.post("/hotel/adjust").json()
    assert hotel["confirmed"] is True
    assert hotel["hotel"]["status"] == "BOOKED"
    assert hotel["hotel"]["rooms"] == 2
    assert hotel["hotel"]["check_in"] == "2026-11-02"
    assert hotel["hotel"]["check_out"] == "2026-11-07"
    assert hotel["hotel"]["total"] == pytest.approx(480.0 * 2 * 5)

    # 5. Transport — minivan + child car seat at OGG.
    transport = client.post("/transport/update").json()
    assert transport["confirmed"] is True
    assert transport["transport"]["status"] == "BOOKED"
    assert transport["transport"]["car_seat"] is True
    assert transport["transport"]["pickup_location"].startswith("OGG")
    assert transport["transport"]["pickup_date"] == "2026-11-02"

    # 6. Activities — surf lesson + Molokini snorkel, both booked.
    activities = client.post("/activities/book").json()
    assert activities["confirmed"] is True
    assert activities["activities"]["status"] == "BOOKED"
    assert {a["activity_id"] for a in activities["activities"]["items"]} == {"surf", "snorkel"}
    assert all(a["status"] == "BOOKED" for a in activities["activities"]["items"])
    assert all(a["participants"] == 5 for a in activities["activities"]["items"])

    # 7. Pay the trip total.
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


def test_rebook_november_to_august_cascades_every_vendor(client):
    # Book the whole trip in November first.
    client.post("/flights/book", json={"flight_id": "AA511"})
    client.post("/hotel/adjust")
    client.post("/transport/update")
    client.post("/activities/book")

    before = client.post("/trip/status").json()
    assert before["month"] == "november"

    # The weather constraint surfaces → move the whole trip to August.
    rebook = client.post("/trip/rebook", json={"month": "august"})
    assert rebook.status_code == 200
    body = rebook.json()
    assert body["confirmed"] is True
    assert body["previous_month"] == "november"
    assert body["month"] == "august"

    # The cascade: every vendor moved to August dates AND August prices,
    # and everything that was booked stays booked.
    assert body["dates"]["start"] == "2026-08-05"
    assert body["dates"]["end"] == "2026-08-10"
    assert body["dates"]["nights"] == 5

    assert body["flights"]["status"] == "BOOKED"
    assert body["flights"]["flight_id"] == "AA289"  # same tier A, August equivalent
    assert body["flights"]["tier"] == "A"
    assert body["flights"]["total_price"] == pytest.approx(3600.0)

    assert body["hotel"]["status"] == "BOOKED"
    assert body["hotel"]["check_in"] == "2026-08-05"
    assert body["hotel"]["check_out"] == "2026-08-10"
    assert body["hotel"]["total"] == pytest.approx(620.0 * 2 * 5)

    assert body["transport"]["status"] == "BOOKED"
    assert body["transport"]["pickup_date"] == "2026-08-05"
    assert body["transport"]["dropoff_date"] == "2026-08-10"

    assert body["activities"]["status"] == "BOOKED"
    for item in body["activities"]["items"]:
        assert item["status"] == "BOOKED"
        assert item["date"].startswith("2026-08")

    assert body["totals"]["within_budget"] is True

    # /trip/status re-flows the entire trip on the new dates.
    after = client.post("/trip/status").json()
    assert after["month"] == "august"
    assert after["dates"]["season"] == "dry"
    assert after["flights"]["flight_id"] == "AA289"
    assert after["hotel"]["check_in"] == "2026-08-05"


def test_november_and_august_return_real_and_different_data(client):
    nov = client.post("/flights/search", json={"month": "november"}).json()
    aug = client.post("/flights/search", json={"month": "august"}).json()

    nov_ids = {o["flight_id"] for o in nov["options"]}
    aug_ids = {o["flight_id"] for o in aug["options"]}
    assert nov_ids == NOV_FLIGHT_IDS
    assert aug_ids == AUG_FLIGHT_IDS
    assert nov_ids.isdisjoint(aug_ids)  # genuinely different flight numbers

    # Off-season November is cheaper per tier than peak August.
    nov_by_tier = {o["tier"]: o for o in nov["options"]}
    aug_by_tier = {o["tier"]: o for o in aug["options"]}
    for tier in ("A", "B", "C"):
        assert nov_by_tier[tier]["price_pp"] < aug_by_tier[tier]["price_pp"]


def test_option_shapes_cover_the_three_intended_tradeoffs(client):
    for month in ("november", "august"):
        options = client.post("/flights/search", json={"month": month}).json()["options"]
        by_tier = {o["tier"]: o for o in options}
        # A: nonstop, pricier, recommended.
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
    assert client.post("/flights/search", json={}).json()["request"]["month"] == "november"
    client.post("/trip/rebook", json={"month": "august"})
    assert client.post("/flights/search", json={}).json()["request"]["month"] == "august"


def test_book_single_activity_marks_partial(client):
    body = client.post("/activities/book", json={"activity": "surf"}).json()
    assert body["activities"]["status"] == "PARTIAL"
    surf = next(a for a in body["activities"]["items"] if a["activity_id"] == "surf")
    snorkel = next(a for a in body["activities"]["items"] if a["activity_id"] == "snorkel")
    assert surf["status"] == "BOOKED"
    assert snorkel["status"] == "NOT_BOOKED"


def test_configure_fewer_nights_reprices_everything(client):
    before = client.post("/trip/status").json()
    assert before["dates"]["nights"] == 5

    cfg = client.post("/trip/configure", json={"nights": 3}).json()
    assert cfg["dates"]["nights"] == 3
    assert cfg["dates"]["start"] == "2026-11-02"
    assert cfg["dates"]["end"] == "2026-11-05"  # start + 3 nights
    assert cfg["hotel"]["total"] == pytest.approx(480.0 * 2 * 3)
    assert cfg["transport"]["total"] == pytest.approx((71.0 + 9.0) * 3)
    assert client.post("/trip/status").json()["dates"]["nights"] == 3


def test_configure_party_size_reprices_per_person_costs(client):
    cfg = client.post("/trip/configure", json={"travelers": 3, "rooms": 2}).json()
    assert cfg["party"]["total"] == 3
    search = client.post("/flights/search").json()
    rec = next(o for o in search["options"] if o["recommended"])
    assert rec["total_price"] == pytest.approx(rec["price_pp"] * 3)
    assert search["request"]["travelers"] == 3
    surf = next(a for a in cfg["activities"]["items"] if a["activity_id"] == "surf")
    assert surf["participants"] == 3
    assert cfg["hotel"]["total"] == pytest.approx(480.0 * 2 * 5)  # rooms/nights unchanged


def test_configure_survives_the_month_cascade(client):
    client.post("/trip/configure", json={"nights": 4, "travelers": 6})
    client.post("/flights/book", json={"flight_id": "AA511"})
    rebook = client.post("/trip/rebook", json={"month": "august"}).json()
    assert rebook["dates"]["nights"] == 4
    assert rebook["dates"]["start"] == "2026-08-05"
    assert rebook["dates"]["end"] == "2026-08-09"  # Aug 5 + 4 nights
    assert rebook["hotel"]["total"] == pytest.approx(620.0 * 2 * 4)
    assert rebook["flights"]["total_price"] == pytest.approx(720.0 * 6)  # AA289 pp * 6
    assert rebook["flights"]["status"] == "BOOKED"


def test_configure_bounds_are_enforced(client):
    assert client.post("/trip/configure", json={"nights": 0}).status_code == 422
    assert client.post("/trip/configure", json={"nights": 99}).status_code == 422
    assert client.post("/trip/configure", json={"travelers": 20}).status_code == 422
    assert client.post("/trip/configure", json={}).status_code == 400


def test_reset_restores_initial_november_planning_state(client):
    client.post("/trip/configure", json={"nights": 3, "travelers": 2})
    client.post("/flights/book", json={"flight_id": "AA511"})
    client.post("/trip/rebook", json={"month": "august"})
    client.post("/payment/confirm", json={})

    reset = client.post("/demo/reset").json()
    assert reset["reset"] is True

    trip = client.post("/trip/status").json()
    assert trip["status"] == "PLANNING"
    assert trip["month"] == "november"
    assert trip["dates"]["start"] == "2026-11-02"
    assert trip["dates"]["nights"] == 5
    assert trip["party"]["total"] == 5
    assert all(trip[v]["status"] == "NOT_BOOKED" for v in ("flights", "hotel", "transport"))
    assert trip["activities"]["status"] == "NOT_BOOKED"
    assert trip["payments"] == []


def test_book_unknown_flight_id_is_404(client):
    resp = client.post("/flights/book", json={"flight_id": "AA999"})
    assert resp.status_code == 404
    assert "AA511" in resp.json()["detail"]


def test_rebook_unknown_month_is_404(client):
    resp = client.post("/trip/rebook", json={"month": "december"})
    assert resp.status_code == 404
    assert "november" in resp.json()["detail"]


def test_rebook_to_the_same_month_is_400(client):
    resp = client.post("/trip/rebook", json={"month": "november"})
    assert resp.status_code == 400
