from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from prometheus_client import make_asgi_app

from app.core.config import settings
from app.api.v1 import router as api_v1
from app.api.admin import router as admin_router
from app.observability.tracing import setup_tracing, instrument_fastapi
from app.core.logging import setup_logging, get_logger


setup_logging()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
log = get_logger("app.main")

# UI
app.mount("/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    log.info("ui.index")
    return templates.TemplateResponse(
        "index.html", {"request": request, "app_name": settings.APP_NAME}
    )


# API
app.include_router(api_v1, prefix="/v1")
app.include_router(admin_router)

# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.on_event("startup")
async def on_startup():
    log.bind(
        env=settings.APP_ENV, version=settings.APP_VERSION, level=settings.LOG_LEVEL
    ).info("startup")
    # Tracing instrumentation if enabled
    setup_tracing()
    instrument_fastapi(app)


# CORS (dev friendly) — register at init time
if settings.APP_ENV == "dev":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("shutdown")
async def on_shutdown():
    log.info("shutdown")
