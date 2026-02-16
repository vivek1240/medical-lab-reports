import logging
from datetime import datetime, timezone
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import engine
from backend.models import biomarker, lab_report  # noqa: F401
from backend.routers import biomarkers, reports, trends
from backend.seed.biomarker_seed import seed_biomarkers

app = FastAPI(title="Medical Lab Reports API", version="0.1.0")
logger = logging.getLogger(__name__)

allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _assert_database_at_head() -> None:
    project_root = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
    script = ScriptDirectory.from_config(alembic_cfg)
    expected_heads = set(script.get_heads())

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_heads = set(context.get_current_heads())

    if current_heads != expected_heads:
        raise RuntimeError(
            "Database schema is not at Alembic head. "
            "Run `alembic upgrade head` before starting the API. "
            f"Current revisions: {sorted(current_heads) or ['<none>']}, "
            f"expected: {sorted(expected_heads)}."
        )


@app.on_event("startup")
def startup_event():
    _assert_database_at_head()
    seed_biomarkers()


@app.get("/")
def root():
    return {"statusCode": 200, "message": "Success", "data": {"status": "ok", "service": "custom-labs"}}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "custom-labs",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _error_name(status_code: int) -> str:
    if status_code == 400:
        return "BadRequest"
    if status_code == 401:
        return "Unauthorized"
    if status_code == 403:
        return "Forbidden"
    if status_code == 404:
        return "NotFound"
    if status_code == 422:
        return "ValidationError"
    if status_code >= 500:
        return "InternalServerError"
    return "HTTPError"


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "message": str(exc.detail) if exc.detail else "Request failed",
            "error": _error_name(exc.status_code),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "statusCode": 422,
            "message": "Invalid request payload",
            "error": "ValidationError",
            "details": {"errors": exc.errors()},
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "statusCode": 500,
            "message": str(exc) or "An unexpected error occurred",
            "error": "InternalServerError",
        },
    )


app.include_router(reports.router)
app.include_router(biomarkers.router)
app.include_router(trends.router)
