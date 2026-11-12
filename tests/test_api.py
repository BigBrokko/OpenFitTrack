"""The API, tested with FastAPI's TestClient against an in-memory database."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from tests.auth_helpers import PASSWORD, auth_settings
from tests.seed import TODAY


@pytest.fixture
def client(seeded):
    """A logged-in client. Login is tested in test_api_auth.py."""
    app = create_app(seeded, auth_settings(), today=lambda: TODAY)
    with TestClient(app, base_url="https://testserver") as test_client:
        assert test_client.post("/api/login", json={"password": PASSWORD}).status_code == 204
        yield test_client


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_day_summary_for_a_given_day(client):
    response = client.get("/api/day", params={"date": "2026-01-06"})

    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-01-06"
    assert data["totals"]["kcal"] == 102.0  # 200 g of 51 kcal / 100 g
    assert data["goal"]["kcal"] == 2000
    assert data["progress"]["kcal"]["remaining"] == 1898.0
    (entry,) = data["entries"]
    assert (entry["time"], entry["food"], entry["amount_g"]) == ("08:00", "Kwark magere", 200.0)


def test_day_summary_defaults_to_today(client):
    data = client.get("/api/day").json()

    assert data["date"] == "2026-01-12"
    assert data["totals"]["kcal"] == 51.0


def test_empty_day_says_unlogged_is_not_zero_intake(client):
    data = client.get("/api/day", params={"date": "2026-01-07"}).json()

    assert data["entries"] == []
    assert "does not mean nothing was eaten" in data["note"]


def test_period_summary_averages_only_logged_days(client):
    response = client.get(
        "/api/period", params={"start_date": "2026-01-06", "end_date": "2026-01-12"}
    )

    data = response.json()
    assert (data["days_in_period"], data["days_logged"]) == (7, 3)
    assert data["average_per_logged_day"]["kcal"] == 85.0
    assert "3 of 7 days" in data["note"]


def test_period_summary_defaults_to_the_last_seven_days(client):
    data = client.get("/api/period").json()

    assert (data["start_date"], data["end_date"]) == ("2026-01-06", "2026-01-12")


def test_period_with_the_end_before_the_start_is_a_bad_request(client):
    response = client.get(
        "/api/period", params={"start_date": "2026-01-12", "end_date": "2026-01-06"}
    )

    assert response.status_code == 400
    assert "before the start" in response.json()["detail"]


def test_period_longer_than_a_year_is_a_bad_request(client):
    response = client.get(
        "/api/period", params={"start_date": "2024-01-01", "end_date": "2026-01-12"}
    )

    assert response.status_code == 400
    assert "366" in response.json()["detail"]


def test_weight_trend_window_keeps_the_trend_of_the_full_history(client):
    full = client.get("/api/weight", params={"days": 90}).json()
    window = client.get("/api/weight", params={"days": 5}).json()

    assert [p["date"] for p in full["points"]] == ["2026-01-01", "2026-01-08", "2026-01-12"]
    assert [p["date"] for p in window["points"]] == ["2026-01-08", "2026-01-12"]
    assert window["points"][-1]["trend_kg"] == full["points"][-1]["trend_kg"]
    assert full["latest_weight_kg"] == 80.5
    assert full["target_weight_kg"] == 78


def test_goals(client):
    data = client.get("/api/goals").json()

    assert data["current"]["kcal"] == 2000
    assert len(data["history"]) == 1


def test_food_search(client):
    data = client.get("/api/foods/search", params={"q": "banaan", "limit": 3}).json()

    assert data["query"] == "banaan"
    assert data["results"][0]["name"] == "Banaan"
    assert data["results"][0]["kcal"] == 90.0


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/api/day", {"date": "yesterday"}),
        ("/api/weight", {"days": 0}),
        ("/api/weight", {"days": 1000}),
        ("/api/foods/search", {}),
        ("/api/foods/search", {"q": ""}),
        ("/api/foods/search", {"q": "kwark", "limit": 500}),
    ],
)
def test_invalid_parameters_are_rejected(client, path, params):
    assert client.get(path, params=params).status_code == 422


def test_an_empty_database_gets_its_tables_and_returns_empty_answers(memory_engine):
    app = create_app(memory_engine, auth_settings(), today=lambda: TODAY)

    with TestClient(app, base_url="https://testserver") as client:
        client.post("/api/login", json={"password": PASSWORD})
        assert client.get("/api/goals").json() == {"current": None, "history": []}
        assert client.get("/api/weight").json()["points"] == []


def test_openapi_describes_the_endpoints_with_readable_operation_ids(client):
    spec = client.get("/openapi.json").json()

    operations = {
        operation["operationId"]
        for methods in spec["paths"].values()
        for operation in methods.values()
    }
    assert operations == {
        "get_health",
        "login",
        "logout",
        "get_me",
        "get_day_summary",
        "get_period_summary",
        "get_weight_trend",
        "get_goals",
        "search_foods",
    }
    assert "DaySummary" in spec["components"]["schemas"]
