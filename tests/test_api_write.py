"""The write endpoints of the API. Business rules are tested in core; here we test the wiring:
status codes, defaults, that changes show up in the reports, and that a login is required."""

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from tests.auth_helpers import PASSWORD, auth_settings
from tests.seed import TODAY

NOW = dt.datetime(2026, 1, 12, 13, 47, 31)


@pytest.fixture
def client(seeded):
    app = create_app(seeded, auth_settings(), today=lambda: TODAY, now=lambda: NOW)
    with TestClient(app, base_url="https://testserver") as test_client:
        assert test_client.post("/api/login", json={"password": PASSWORD}).status_code == 204
        yield test_client


def food_id(client, name: str) -> int:
    return client.get("/api/foods/search", params={"q": name}).json()["results"][0]["id"]


def day(client, date: str = "2026-01-12") -> dict:
    return client.get("/api/day", params={"date": date}).json()


# --- logged entries ----------------------------------------------------------------------


def test_log_food_defaults_to_now_without_seconds(client):
    response = client.post(
        "/api/entries", json={"food_id": food_id(client, "Banaan"), "amount_g": 120}
    )

    assert response.status_code == 201
    assert response.json()["logged_at"] == "2026-01-12T13:47:00"
    banaan = day(client)["entries"][-1]
    assert (banaan["food"], banaan["time"], banaan["amount_g"]) == ("Banaan", "13:47", 120.0)


def test_log_food_on_another_day(client):
    client.post(
        "/api/entries",
        json={
            "food_id": food_id(client, "Banaan"),
            "amount_g": 100,
            "logged_at": "2026-01-07T19:30",
        },
    )

    assert day(client, "2026-01-07")["totals"]["kcal"] == 90.0


def test_log_food_with_an_unknown_food_is_not_found(client):
    response = client.post("/api/entries", json={"food_id": 999, "amount_g": 100})

    assert response.status_code == 404


@pytest.mark.parametrize("grams", [0, -3])
def test_log_food_rejects_non_positive_amounts(client, grams):
    response = client.post(
        "/api/entries", json={"food_id": food_id(client, "Banaan"), "amount_g": grams}
    )

    assert response.status_code == 400
    assert len(day(client)["entries"]) == 1  # only the seeded one


def test_misspelled_fields_are_rejected(client):
    response = client.post(
        "/api/entries", json={"food_id": food_id(client, "Banaan"), "grams": 100}
    )

    assert response.status_code == 422


def test_correct_an_entry(client):
    entry = day(client)["entries"][0]

    response = client.patch(f"/api/entries/{entry['id']}", json={"amount_g": 250})

    assert response.status_code == 200
    corrected = day(client)["entries"][0]
    assert (corrected["amount_g"], corrected["time"]) == (250.0, entry["time"])


def test_correct_the_time_of_an_entry(client):
    entry = day(client)["entries"][0]

    client.patch(
        f"/api/entries/{entry['id']}", json={"amount_g": 100, "logged_at": "2026-01-12T09:15"}
    )

    assert day(client)["entries"][0]["time"] == "09:15"


def test_correct_an_unknown_entry_is_not_found(client):
    assert client.patch("/api/entries/999", json={"amount_g": 100}).status_code == 404


def test_delete_an_entry(client):
    entry = day(client)["entries"][0]

    response = client.delete(f"/api/entries/{entry['id']}")

    assert response.status_code == 204
    assert day(client)["entries"] == []
    assert client.delete(f"/api/entries/{entry['id']}").status_code == 404


# --- foods -------------------------------------------------------------------------------


def test_create_and_edit_your_own_food(client):
    created = client.post(
        "/api/foods",
        json={"name": "Havermout", "kcal": 370, "protein_g": 13, "carbs_g": 60, "fat_g": 7},
    )

    assert created.status_code == 201
    body = created.json()
    assert (body["name"], body["source"]) == ("Havermout", "manual")
    assert food_id(client, "Havermout") == body["id"]

    edited = client.patch(
        f"/api/foods/{body['id']}",
        json={"name": "Havermout", "kcal": 380, "protein_g": 13, "carbs_g": 60, "fat_g": 7},
    )

    assert edited.status_code == 200
    assert edited.json()["kcal"] == 380


def test_a_duplicate_or_impossible_food_is_a_bad_request(client):
    duplicate = {"name": "banaan", "kcal": 90, "protein_g": 1, "carbs_g": 20, "fat_g": 0}
    too_much = {"name": "Magie", "kcal": 90, "protein_g": 60, "carbs_g": 60, "fat_g": 0}

    assert client.post("/api/foods", json=duplicate).status_code == 400
    assert client.post("/api/foods", json=too_much).status_code == 400


# --- weight and goals --------------------------------------------------------------------


def test_save_weight_defaults_to_today_and_shows_in_the_trend(client):
    response = client.put("/api/weight", json={"weight_kg": 80.0})

    assert response.status_code == 200
    assert response.json() == {"date": "2026-01-12", "weight_kg": 80.0}
    data = client.get("/api/weight").json()
    assert data["latest_weight_kg"] == 80.0
    assert data["measurements_total"] == 3  # the seeded measurement of that day was replaced


def test_save_weight_for_another_day(client):
    client.put("/api/weight", json={"date": "2026-01-10", "weight_kg": 80.8})

    assert client.get("/api/weight").json()["measurements_total"] == 4


@pytest.mark.parametrize("kg", [5, 900])
def test_implausible_weight_is_a_bad_request(client, kg):
    assert client.put("/api/weight", json={"weight_kg": kg}).status_code == 400


def test_set_a_goal_valid_from_today(client):
    response = client.put(
        "/api/goals",
        json={"kcal": 1900, "protein_g": 130, "carbs_g": 180, "fat_g": 60, "target_weight_kg": 77},
    )

    assert response.status_code == 200
    goals = client.get("/api/goals").json()
    assert goals["current"]["kcal"] == 1900
    assert goals["current"]["valid_from"] == "2026-01-12"
    assert len(goals["history"]) == 2


def test_an_invalid_goal_is_a_bad_request(client):
    response = client.put(
        "/api/goals", json={"kcal": 0, "protein_g": 130, "carbs_g": 180, "fat_g": 60}
    )

    assert response.status_code == 400


# --- login -------------------------------------------------------------------------------


def test_all_write_endpoints_need_a_login(seeded):
    app = create_app(seeded, auth_settings(), today=lambda: TODAY)
    with TestClient(app, base_url="https://testserver") as anonymous:
        calls = [
            anonymous.post("/api/entries", json={"food_id": 1, "amount_g": 100}),
            anonymous.patch("/api/entries/1", json={"amount_g": 100}),
            anonymous.delete("/api/entries/1"),
            anonymous.post("/api/foods", json={}),
            anonymous.patch("/api/foods/1", json={}),
            anonymous.put("/api/weight", json={"weight_kg": 80}),
            anonymous.put("/api/goals", json={}),
        ]

    assert [call.status_code for call in calls] == [401] * len(calls)
