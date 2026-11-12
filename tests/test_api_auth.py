"""Login, sessions and the limit on failed attempts."""

import re
from io import StringIO

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from api.auth import (
    AuthSettings,
    LoginLimiter,
    create_credentials,
    verify_password,
)
from api.main import SESSION_COOKIE, create_app
from tests.auth_helpers import PASSWORD, SECRET, auth_settings
from tests.seed import TODAY

PUBLIC_PATHS = {"/api/health", "/api/login", "/api/logout", "/api/me"}


class FakeClock:
    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


def make_app(engine, settings=None, limiter=None):
    return create_app(engine, settings or auth_settings(), today=lambda: TODAY, limiter=limiter)


def make_client(engine, settings=None, limiter=None):
    return TestClient(make_app(engine, settings, limiter), base_url="https://testserver")


def login(client, password=PASSWORD):
    return client.post("/api/login", json={"password": password})


# --- Logging in and out ----------------------------------------------------------


def test_login_with_the_right_password_sets_a_safe_cookie(seeded):
    with make_client(seeded) as client:
        response = login(client)

    assert response.status_code == 204
    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "secure" in cookie
    assert "max-age=1209600" in cookie  # 14 days


def test_a_wrong_password_is_rejected_without_a_cookie(seeded):
    with make_client(seeded) as client:
        response = login(client, "not the password")

    assert response.status_code == 401
    assert response.json() == {"detail": "Wrong password."}
    assert "set-cookie" not in response.headers


def test_me_reflects_the_login_state(seeded):
    with make_client(seeded) as client:
        assert client.get("/api/me").status_code == 401
        login(client)
        assert client.get("/api/me").json() == {"authenticated": True}


def test_logout_ends_the_session(seeded):
    with make_client(seeded) as client:
        login(client)
        assert client.get("/api/goals").status_code == 200

        assert client.post("/api/logout").status_code == 204

        assert client.get("/api/goals").status_code == 401


def test_login_needs_a_json_body_with_a_password(seeded):
    with make_client(seeded) as client:
        assert client.post("/api/login").status_code == 422
        assert client.post("/api/login", json={}).status_code == 422
        assert client.post("/api/login", data={"password": PASSWORD}).status_code == 422


def test_health_stays_open(seeded):
    with make_client(seeded) as client:
        assert client.get("/api/health").status_code == 200


# --- Protection -------------------------------------------------------------------


def test_every_route_except_the_public_ones_requires_a_login(seeded):
    """Guards future endpoints: a new unprotected route makes this test fail.

    Routes are listed from the OpenAPI description, which covers every registered route.
    """
    app = make_app(seeded)
    operations = [
        (method.upper(), re.sub(r"\{[^}]+\}", "1", path))
        for path, methods in app.openapi()["paths"].items()
        if path.startswith("/api") and path not in PUBLIC_PATHS
        for method in methods
    ]
    assert len(operations) >= 5

    with TestClient(app, base_url="https://testserver") as client:
        for method, path in operations:
            response = client.request(method, path, json={})
            assert response.status_code == 401, f"{method} {path} is not protected"


def swap_first_character(value: str) -> str:
    return ("A" if value[0] != "A" else "B") + value[1:]


def valid_cookie(engine) -> str:
    with make_client(engine) as client:
        login(client)
        return client.cookies[SESSION_COOKIE]


def get_with_cookie(engine, cookie_value: str):
    """A request from a client that has no cookie jar, carrying exactly this cookie."""
    with make_client(engine) as client:
        return client.get("/api/goals", headers={"Cookie": f"{SESSION_COOKIE}={cookie_value}"})


def test_the_untouched_cookie_works_when_sent_by_hand(seeded):
    """Control for the tamper tests: this way of sending a cookie does authenticate."""
    assert get_with_cookie(seeded, valid_cookie(seeded)).status_code == 200


@pytest.mark.parametrize("part", ["payload", "signature"])
def test_a_tampered_cookie_is_rejected(seeded, part):
    # cookie format: <payload>.<timestamp>.<signature>
    payload, timestamp, signature = valid_cookie(seeded).split(".")
    if part == "payload":
        payload = swap_first_character(payload)
    else:
        signature = swap_first_character(signature)

    response = get_with_cookie(seeded, ".".join([payload, timestamp, signature]))

    assert response.status_code == 401


def test_a_cookie_signed_with_another_secret_is_rejected(seeded):
    with make_client(seeded) as first:
        login(first)
        cookie = first.cookies[SESSION_COOKIE]

    other = make_client(seeded, auth_settings(session_secret="another-secret-" + "y" * 40))
    with other:
        other.cookies.set(SESSION_COOKIE, cookie)
        assert other.get("/api/goals").status_code == 401


def test_a_session_expires(seeded, monkeypatch):
    clock = FakeClock(now=1_000_000.0)
    # itsdangerous reads the time through its own reference to the time module.
    monkeypatch.setattr("itsdangerous.timed.time", type("T", (), {"time": staticmethod(clock)}))
    with make_client(seeded, auth_settings(session_max_age=3600)) as client:
        login(client)
        clock.now += 3599
        assert client.get("/api/goals").status_code == 200

        clock.now += 2
        assert client.get("/api/goals").status_code == 401


# --- Failed attempts ----------------------------------------------------------------


def test_five_failures_lock_the_client_out_even_for_the_right_password(seeded):
    clock = FakeClock()
    limiter = LoginLimiter(5, 900, clock=clock)
    with make_client(seeded, limiter=limiter) as client:
        for _ in range(5):
            assert login(client, "wrong").status_code == 401

        locked = login(client)  # the correct password is refused during the lockout

        assert locked.status_code == 429
        assert int(locked.headers["retry-after"]) == 900
        assert client.get("/api/me").status_code == 401

        clock.now += 901
        assert login(client).status_code == 204


def test_a_successful_login_resets_the_failure_count(seeded):
    limiter = LoginLimiter(5, 900, clock=FakeClock())
    with make_client(seeded, limiter=limiter) as client:
        for _ in range(4):
            login(client, "wrong")
        assert login(client).status_code == 204
        client.post("/api/logout")

        for _ in range(4):
            assert login(client, "wrong").status_code == 401
        assert login(client).status_code == 204


def test_limiter_counts_per_client_and_forgets_old_failures():
    clock = FakeClock()
    limiter = LoginLimiter(2, 100, clock=clock)

    limiter.record_failure("a")
    limiter.record_failure("a")
    assert limiter.retry_after("a") == 100
    assert limiter.retry_after("b") == 0

    clock.now += 60
    assert limiter.retry_after("a") == 40  # the oldest failure leaves the window first
    clock.now += 41
    assert limiter.retry_after("a") == 0


# --- Settings and credentials -----------------------------------------------------------


def test_settings_from_env_need_both_values():
    with pytest.raises(ValueError, match="OFT_PASSWORD_HASH and OFT_SESSION_SECRET"):
        AuthSettings.from_env({})
    with pytest.raises(ValueError, match="create_credentials"):
        AuthSettings.from_env({"OFT_PASSWORD_HASH": "", "OFT_SESSION_SECRET": SECRET})


def test_settings_reject_a_bad_hash_and_a_short_secret():
    with pytest.raises(ValueError, match="Argon2"):
        auth_settings(password_hash="plaintext-password")
    with pytest.raises(ValueError, match="at least 32"):
        auth_settings(session_secret="short")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, True), ("true", True), ("1", True), ("false", False), ("False", False), ("0", False)],
)
def test_cookie_secure_defaults_to_on(value, expected):
    password_hash, secret = create_credentials(PASSWORD)
    env = {"OFT_PASSWORD_HASH": password_hash, "OFT_SESSION_SECRET": secret}
    if value is not None:
        env["OFT_COOKIE_SECURE"] = value

    assert AuthSettings.from_env(env).cookie_secure is expected


def test_created_credentials_verify_and_survive_the_env_file_format():
    password_hash, secret = create_credentials(PASSWORD)

    assert verify_password(password_hash, PASSWORD)
    assert not verify_password(password_hash, "something else")
    assert len(secret) >= 32

    # exactly how scripts/create_credentials.py prints them
    env_file = f"OFT_PASSWORD_HASH='{password_hash}'\nOFT_SESSION_SECRET='{secret}'\n"
    values = dotenv_values(stream=StringIO(env_file))
    assert values["OFT_PASSWORD_HASH"] == password_hash
    assert AuthSettings.from_env(values).session_secret == secret


def test_a_weak_password_is_refused():
    with pytest.raises(ValueError, match="at least 10"):
        create_credentials("short")


def test_verify_password_is_false_for_a_broken_hash():
    assert verify_password("not-a-hash", PASSWORD) is False
