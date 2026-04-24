"""
Main FastAPI application.
Configures the application with middleware, routes, and lifecycle events.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.db.session import db_manager
from app.utils.cache import cache_manager
from app.api.v1.router import api_router
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.middleware.error_handler import (
    app_error_handler,
    validation_exception_handler,
    database_exception_handler,
    general_exception_handler,
)
from app.schemas.response import ok

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application", environment=settings.ENVIRONMENT)
    db_manager.init_engine()
    logger.info("Database engine initialized")
    await cache_manager.connect()
    logger.info("Redis cache connected")

    yield

    logger.info("Shutting down application")
    await db_manager.close_engine()
    logger.info("Database connections closed")
    await cache_manager.close()
    logger.info("Redis connection closed")


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade FastAPI backend with async operations, JWT auth, and RBAC",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


def _verify_cohort_list_route_or_raise(application: FastAPI) -> None:
    """
    Fail fast if another route (e.g. a stray ``GET /{tenant_id}``) shadows ``GET …/cohorts``.
    If this passes but clients still see ``tenant_id`` / ``cohorts`` 422s, they are almost certainly
    hitting a *different* process on the same URL (stale uvicorn on the port).
    """
    from starlette.routing import Match

    probe_path = f"{settings.API_V1_PREFIX}/cohorts"
    scope: dict = {
        "type": "http",
        "path": probe_path,
        "method": "GET",
        "headers": [],
        "query_string": b"",
    }
    for route in application.router.routes:
        m, _ = route.matches(scope)
        if m != Match.FULL:
            continue
        endpoint = getattr(route, "endpoint", None)
        name = getattr(endpoint, "__name__", None)
        rpath = getattr(route, "path", None)
        if name != "list_cohorts":
            raise RuntimeError(
                f"Route table is wrong: GET {probe_path!r} resolves to {name!r} (route.path={rpath!r}), "
                "expected list_cohorts. Stop every uvicorn/python process, delete __pycache__ under app/, "
                "then start again from squinia-backend."
            )
        logger.info("Route probe OK", probe=probe_path, handler=name)
        return
    raise RuntimeError(f"No route matched GET {probe_path!r} — cohorts router may be missing.")


_verify_cohort_list_route_or_raise(app)


@app.get("/", tags=["Health"])
async def root():
    return ok({
        "message": f"Welcome to {settings.APP_NAME}",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
    })


@app.get("/health", tags=["Health"])
async def health_check():
    return ok({
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
