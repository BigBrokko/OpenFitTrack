"""The API: JSON endpoints over `core`. Free of side effects on import; see api/server.py."""

import datetime as dt
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.engine import Engine
from sqlmodel import Session
from starlette.middleware.sessions import SessionMiddleware

from api.auth import AuthSettings, LoginLimiter, build_auth_router, require_login
from api.inputs import (
    EntryChange,
    EntryOut,
    FoodOut,
    FoodValues,
    GoalIn,
    NewEntry,
    WeightIn,
    WeightOut,
)
from core import foods, goals, meal_log, reports, weight
from core.db import create_db
from core.report_models import (
    DaySummary,
    FoodSearchResult,
    GoalInfo,
    GoalsInfo,
    PeriodSummary,
    WeightTrend,
)

SESSION_COOKIE = "oft_session"


def create_app(
    engine: Engine,
    auth: AuthSettings,
    today: Callable[[], dt.date] = dt.date.today,
    now: Callable[[], dt.datetime] = dt.datetime.now,
    limiter: LoginLimiter | None = None,
    web_dir: Path | None = None,
) -> FastAPI:
    """Build the API around a database engine. Tests can replace `today`, `now`, `limiter`.

    With `web_dir` (the built React app, web/dist) the app is served as well: one process for
    the website and the API.
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        create_db(engine)  # a fresh database gets its tables instead of "no such table" errors
        yield

    app = FastAPI(
        title="OpenFitTrack API",
        version="0.2.0",
        lifespan=lifespan,
        # Operation ids like "get_day_summary" give a readable generated TypeScript client.
        generate_unique_id_function=lambda route: route.name,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=auth.session_secret,
        session_cookie=SESSION_COOKIE,
        max_age=auth.session_max_age,
        same_site="strict",
        https_only=auth.cookie_secure,
    )

    def get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    SessionDep = Annotated[Session, Depends(get_session)]

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, error: ValueError) -> JSONResponse:
        # core raises ValueError for invalid input (e.g. an end date before the start date)
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(LookupError)
    async def lookup_error_handler(_: Request, error: LookupError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    # Public: health (for the Docker healthcheck) and the login endpoints.
    @app.get("/api/health")
    def get_health() -> dict[str, str]:
        return {"status": "ok"}

    limiter = limiter or LoginLimiter(auth.max_failed_attempts, auth.lockout_seconds)
    app.include_router(build_auth_router(auth, limiter))

    # Everything else needs a login. Put new routes on this router so they are protected
    # by default.
    protected = APIRouter(dependencies=[Depends(require_login)])

    @protected.get("/api/day")
    def get_day_summary(
        session: SessionDep,
        date: Annotated[dt.date | None, Query(description="YYYY-MM-DD, default today")] = None,
    ) -> DaySummary:
        """One day: logged food, totals, and the totals against that day's goal."""
        return reports.day_summary(session, date or today())

    @protected.get("/api/period")
    def get_period_summary(
        session: SessionDep,
        start_date: Annotated[
            dt.date | None, Query(description="YYYY-MM-DD, default 6 days before the end date")
        ] = None,
        end_date: Annotated[dt.date | None, Query(description="YYYY-MM-DD, default today")] = None,
    ) -> PeriodSummary:
        """Daily totals and averages over a period (at most 366 days), against the goal."""
        end = end_date or today()
        return reports.period_summary(session, start_date or end - dt.timedelta(days=6), end)

    @protected.get("/api/weight")
    def get_weight_trend(
        session: SessionDep,
        days: Annotated[int, Query(ge=1, le=730, description="How many days back")] = 90,
    ) -> WeightTrend:
        """Weights with an exponential moving average trend and the 7-day change."""
        return reports.weight_summary(session, days, today())

    @protected.get("/api/goals")
    def get_goals(session: SessionDep) -> GoalsInfo:
        """The goal that applies today and the goal history."""
        return reports.goals_summary(session, today())

    @protected.get("/api/foods/search")
    def search_foods(
        session: SessionDep,
        q: Annotated[str, Query(min_length=1, description="Food name")],
        limit: Annotated[int, Query(ge=1, le=20)] = 5,
    ) -> FoodSearchResult:
        """Find foods in the database. Values are per 100 g."""
        return reports.food_search(session, q, limit)

    # --- write endpoints -----------------------------------------------------------------
    # The session cookie is SameSite=Strict, so other websites cannot trigger these.

    @protected.post("/api/entries", status_code=201)
    def create_entry(session: SessionDep, body: NewEntry) -> EntryOut:
        """Log an amount of a food (by food id)."""
        when = body.logged_at or now().replace(second=0, microsecond=0)
        return meal_log.log_food(session, body.food_id, body.amount_g, when)

    @protected.patch("/api/entries/{entry_id}")
    def update_entry(session: SessionDep, entry_id: int, body: EntryChange) -> EntryOut:
        """Correct the amount (and optionally the time) of a logged line."""
        return meal_log.update_entry(session, entry_id, body.amount_g, body.logged_at)

    @protected.delete("/api/entries/{entry_id}", status_code=204)
    def delete_entry(session: SessionDep, entry_id: int) -> Response:
        """Remove a logged line."""
        meal_log.delete_entry(session, entry_id)
        return Response(status_code=204)

    @protected.post("/api/foods", status_code=201)
    def create_food(session: SessionDep, body: FoodValues) -> FoodOut:
        """Create your own food from values per 100 g."""
        return foods.add_manual_food(session, **body.model_dump())

    @protected.patch("/api/foods/{food_id}")
    def update_food(session: SessionDep, food_id: int, body: FoodValues) -> FoodOut:
        """Change one of your own foods (imported foods cannot be edited)."""
        return foods.update_manual_food(session, food_id, **body.model_dump())

    @protected.put("/api/weight")
    def put_weight(session: SessionDep, body: WeightIn) -> WeightOut:
        """Save the weight of a day. A measurement already on that day is replaced."""
        return weight.log_weight(session, body.date or today(), body.weight_kg)

    @protected.put("/api/goals")
    def put_goal(session: SessionDep, body: GoalIn) -> GoalInfo:
        """Save a goal valid from a date. A goal already starting on that date is replaced."""
        values = body.model_dump()
        values["valid_from"] = body.valid_from or today()
        return goals.set_goal(session, **values)

    app.include_router(protected)
    if web_dir is not None:
        _serve_frontend(app, web_dir)
    return app


def _serve_frontend(app: FastAPI, web_dir: Path) -> None:
    """Serve the built frontend. Registered last, so /api, /docs and /openapi.json win."""
    root = web_dir.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise ValueError(f"No built web app in {root} (index.html is missing).")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404)  # an unknown API path must not answer with a web page
        candidate = (root / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)  # a page of the app (e.g. /dag): the app routes it itself
