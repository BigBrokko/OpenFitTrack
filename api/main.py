"""The API: JSON endpoints over `core`. Free of side effects on import; see api/server.py."""

import datetime as dt
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlmodel import Session
from starlette.middleware.sessions import SessionMiddleware

from api.auth import AuthSettings, LoginLimiter, build_auth_router, require_login
from core import reports
from core.db import create_db
from core.report_models import DaySummary, FoodSearchResult, GoalsInfo, PeriodSummary, WeightTrend

SESSION_COOKIE = "oft_session"


def create_app(
    engine: Engine,
    auth: AuthSettings,
    today: Callable[[], dt.date] = dt.date.today,
    limiter: LoginLimiter | None = None,
) -> FastAPI:
    """Build the API around a database engine. `today` and `limiter` can be replaced in tests."""

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

    app.include_router(protected)
    return app
