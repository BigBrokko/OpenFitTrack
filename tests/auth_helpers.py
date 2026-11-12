"""Login settings for the API tests, with a cheap hash so the tests stay fast."""

from argon2 import PasswordHasher

from api.auth import AuthSettings

PASSWORD = "correct horse battery"
SECRET = "test-secret-" + "x" * 40
_FAST_HASH = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)


def auth_settings(**overrides) -> AuthSettings:
    values = {"password_hash": _FAST_HASH, "session_secret": SECRET} | overrides
    return AuthSettings(**values)
