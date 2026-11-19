"""Serving the built web app from the API (one process in Docker)."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from tests.auth_helpers import auth_settings
from tests.seed import TODAY


@pytest.fixture
def web_dir(tmp_path):
    (tmp_path / "index.html").write_text("<html>the app</html>")
    (tmp_path / "sw.js").write_text("// service worker")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app-123.js").write_text("console.log('app')")
    return tmp_path / "."  # a path that is not already resolved


@pytest.fixture
def client(seeded, web_dir):
    app = create_app(seeded, auth_settings(), today=lambda: TODAY, web_dir=web_dir)
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def test_the_root_and_app_pages_give_the_app(client):
    for path in ["/", "/dag", "/dag/toevoegen", "/login"]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert "the app" in response.text, path


def test_real_files_are_served_as_they_are(client):
    assert client.get("/sw.js").text == "// service worker"
    assert "console.log" in client.get("/assets/app-123.js").text


def test_the_api_and_docs_still_win(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "OpenFitTrack API"
    assert client.get("/api/day").status_code == 401  # still behind the login


def test_an_unknown_api_path_is_not_the_app(client):
    for path in ["/api/nothing", "/api/nothing/deeper", "/api"]:
        assert client.get(path).status_code == 404, path


def test_paths_cannot_leave_the_web_folder(client, web_dir):
    (web_dir.parent / "secret.txt").write_text("secret")

    response = client.get("/..%2fsecret.txt")

    assert "secret" not in response.text
    assert "the app" in response.text


def test_without_web_dir_nothing_is_served(seeded):
    app = create_app(seeded, auth_settings(), today=lambda: TODAY)
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/").status_code == 404


def test_a_folder_without_a_build_is_an_error(seeded, tmp_path):
    with pytest.raises(ValueError, match="index.html"):
        create_app(seeded, auth_settings(), web_dir=tmp_path)
