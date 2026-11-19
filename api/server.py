"""Entry point for uvicorn: uv run uvicorn api.server:app --reload

Reads DATABASE_URL, OFT_PASSWORD_HASH, OFT_SESSION_SECRET, OFT_COOKIE_SECURE and (optional)
OFT_WEB_DIR, the built web app to serve (also from a .env in the working directory).
The API refuses to start without a password hash and secret, so it can never run open by
accident. uvicorn listens on 127.0.0.1 by default.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from api.auth import AuthSettings
from api.main import create_app
from core.db import get_engine

load_dotenv()
try:
    _auth = AuthSettings.from_env()
except ValueError as error:
    raise SystemExit(f"OpenFitTrack API: {error}") from error

_web_dir = os.environ.get("OFT_WEB_DIR")
app = create_app(get_engine(), _auth, web_dir=Path(_web_dir) if _web_dir else None)
