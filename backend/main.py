import logging
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.database import engine
from backend.models import biomarker, lab_report, user  # noqa: F401
from backend.routers import auth, biomarkers, reports, trends
from backend.seed.biomarker_seed import seed_biomarkers

app = FastAPI(title="Medical Lab Reports API", version="0.1.0")
logger = logging.getLogger(__name__)


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    details = exc.detail if isinstance(exc.detail, dict) else {"reason": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": "Request failed",
                "details": details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload",
                "details": {"errors": exc.errors()},
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
            }
        },
    )


app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(biomarkers.router)
app.include_router(trends.router)
