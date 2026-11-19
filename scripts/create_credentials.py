"""Create the login settings for the API.

Asks for a password (twice, not shown) and prints two lines for your .env file: the Argon2
hash of the password and a random secret that signs the session cookies. The password itself
is never stored. Run it yourself: the password should not pass through anyone else.

Usage: uv run python scripts/create_credentials.py
"""

import getpass
import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.auth import MIN_PASSWORD_LENGTH, create_credentials  # noqa: E402


def main() -> None:
    password = getpass.getpass(f"New password (at least {MIN_PASSWORD_LENGTH} characters): ")
    if password != getpass.getpass("Repeat the password: "):
        sys.exit("The passwords do not match.")
    try:
        password_hash, secret = create_credentials(password)
    except ValueError as error:
        sys.exit(str(error))

    print("\nAdd these two lines to your .env (single quotes keep the $ signs intact):\n")
    print(f"OFT_PASSWORD_HASH='{password_hash}'")
    print(f"OFT_SESSION_SECRET='{secret}'")
    print("\nChanging OFT_SESSION_SECRET later logs every session out.")


if __name__ == "__main__":
    main()
