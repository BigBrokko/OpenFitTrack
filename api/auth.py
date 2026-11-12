"""Login for the API: one password, a signed session cookie, and a limit on failed attempts.

The password is stored only as an Argon2 hash (OFT_PASSWORD_HASH). The session lives in a
signed, HttpOnly, SameSite=Strict cookie (Starlette's SessionMiddleware, signed with
OFT_SESSION_SECRET). Changing the secret logs everyone out.
"""

import logging
import math
import os
import secrets
import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from argon2 import PasswordHasher, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

logger = logging.getLogger("openfittrack.auth")

MIN_PASSWORD_LENGTH = 10
MIN_SECRET_LENGTH = 32
SESSION_FLAG = "authenticated"
FALSE_VALUES = {"false", "0", "no", "off"}


@dataclass(frozen=True)
class AuthSettings:
    password_hash: str
    session_secret: str
    cookie_secure: bool = True  # only send the cookie over HTTPS; turn off to test over http
    session_max_age: int = 14 * 24 * 3600  # seconds
    max_failed_attempts: int = 5
    lockout_seconds: int = 15 * 60

    def __post_init__(self) -> None:
        try:
            extract_parameters(self.password_hash)
        except InvalidHashError as error:
            raise ValueError("OFT_PASSWORD_HASH is not a valid Argon2 hash.") from error
        if len(self.session_secret) < MIN_SECRET_LENGTH:
            raise ValueError(f"OFT_SESSION_SECRET must be at least {MIN_SECRET_LENGTH} characters.")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AuthSettings":
        """Read the settings from environment variables. Raises ValueError with a clear message."""
        env = os.environ if env is None else env
        missing = [
            name for name in ("OFT_PASSWORD_HASH", "OFT_SESSION_SECRET") if not env.get(name)
        ]
        if missing:
            raise ValueError(
                f"{' and '.join(missing)} not set. Create both with: "
                "uv run python scripts/create_credentials.py, and put the lines in your .env."
            )
        secure = env.get("OFT_COOKIE_SECURE", "true").strip().lower() not in FALSE_VALUES
        return cls(
            password_hash=env["OFT_PASSWORD_HASH"],
            session_secret=env["OFT_SESSION_SECRET"],
            cookie_secure=secure,
        )


def create_credentials(password: str) -> tuple[str, str]:
    """Return (password hash, new session secret) for the .env file."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Use a password of at least {MIN_PASSWORD_LENGTH} characters.")
    return PasswordHasher().hash(password), secrets.token_urlsafe(48)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return PasswordHasher().verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


class LoginLimiter:
    """Blocks a client after too many failed logins within a sliding window (in memory)."""

    def __init__(
        self,
        max_failures: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, key: str) -> deque[float]:
        now = self._clock()
        failures = self._failures[key]
        while failures and now - failures[0] >= self._window:
            failures.popleft()
        if not failures:
            self._failures.pop(key, None)
        return failures

    def retry_after(self, key: str) -> int:
        """Seconds until this client may try again; 0 when it may try now."""
        failures = self._recent(key)
        if len(failures) < self._max:
            return 0
        return max(1, math.ceil(failures[0] + self._window - self._clock()))

    def record_failure(self, key: str) -> None:
        self._failures[key].append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


def require_login(request: Request) -> None:
    """Dependency for every protected route: 401 without a valid session."""
    if not request.session.get(SESSION_FLAG):
        raise HTTPException(status_code=401, detail="Not logged in.")


class LoginRequest(BaseModel):
    password: str = Field(max_length=1024)


class Me(BaseModel):
    authenticated: bool


def build_auth_router(settings: AuthSettings, limiter: LoginLimiter) -> APIRouter:
    router = APIRouter()

    @router.post("/api/login", status_code=204)
    def login(body: LoginRequest, request: Request) -> Response:
        client = request.client.host if request.client else "unknown"
        wait = limiter.retry_after(client)
        if wait:
            raise HTTPException(
                status_code=429,
                detail="Too many failed attempts. Try again later.",
                headers={"Retry-After": str(wait)},
            )
        if not verify_password(settings.password_hash, body.password):
            limiter.record_failure(client)
            logger.warning("Failed login from %s", client)
            raise HTTPException(status_code=401, detail="Wrong password.")
        limiter.reset(client)
        request.session.clear()
        request.session[SESSION_FLAG] = True
        return Response(status_code=204)

    @router.post("/api/logout", status_code=204)
    def logout(request: Request) -> Response:
        request.session.clear()
        return Response(status_code=204)

    @router.get("/api/me")
    def get_me(request: Request) -> Me:
        """Used by the frontend to decide between the login screen and the app."""
        require_login(request)
        return Me(authenticated=True)

    return router
