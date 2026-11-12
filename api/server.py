"""Entry point for uvicorn: uv run uvicorn api.server:app --reload

Reads DATABASE_URL, OFT_PASSWORD_HASH, OFT_SESSION_SECRET and OFT_COOKIE_SECURE (also from a
.env in the working directory). The API refuses to start without a password hash and secret,
so it can never run open by accident. uvicorn listens on 127.0.0.1 by default.
"""

from dotenv import load_dotenv

from api.auth import AuthSettings
from api.main import create_app
from core.db import get_engine

load_dotenv()
try:
    _auth = AuthSettings.from_env()
except ValueError as error:
    raise SystemExit(f"OpenFitTrack API: {error}") from error

app = create_app(get_engine(), _auth)
