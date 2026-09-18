from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.router import api_router
from app.api.routes_health import router as health_router

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("argala")



from app.db.database import init_db
from app.queue.worker import queue_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Node Lifecycle Manager:
    Runs startup verification before accepting traffic,
    initializes WAL database, starts the edge queue worker,
    and handles graceful teardown on SIGTERM/SIGINT.
    """
    logger.info("Initializing %s (Node ID: %s)", settings.GATEWAY_NAME, settings.NODE_ID)
    if settings.API_KEY == "argala-dev-key-change-me":
        logger.warning("SECURITY WARNING: Gateway is using default development API key! Set GATEWAY_API_KEY environment variable for production.")
    
    # 1. Initialize SQLite Database & Tables in WAL mode
    init_db()
    
    # 2. Start Background Queue Worker
    await queue_worker.start()
    
    logger.info("Listening on %s:%s", settings.HOST, settings.PORT)
    yield
    
    # Graceful Teardown: stop worker before exiting
    logger.info("Shutting down %s gracefully...", settings.GATEWAY_NAME)
    await queue_worker.stop()


def create_app() -> FastAPI:
    """Application factory."""
    application = FastAPI(
        title=settings.GATEWAY_NAME,
        description="24/7 Sovereign Edge Gateway & Control Plane for Android Termux",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS Middleware: Enable cross-origin requests from desktop tools / dashboards
    allow_credentials = "*" not in settings.CORS_ORIGINS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(PermissionError)
    async def permission_error_handler(request, exc: PermissionError):
        from fastapi.responses import JSONResponse
        from app.core.identity import lockdown_manager
        status_code = 423 if lockdown_manager.is_locked() else 403
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc)},
        )


    # Top-level informational and backward-compatible endpoints
    @application.get("/", tags=["Root"])
    async def root():
        return {
            "gateway": settings.GATEWAY_NAME,
            "node_id": settings.NODE_ID,
            "status": "online",
            "docs": "/docs",
            "v1_prefix": "/v1",
            "approvals_ui": "/approvals",
        }

    # Mount top-level /approvals mobile dashboard
    from app.hitl.web_ui import HTML_TEMPLATE
    from fastapi.responses import HTMLResponse

    @application.get("/approvals", response_class=HTMLResponse, tags=["HITL Dashboard"])
    async def approvals_console():
        return HTMLResponse(content=HTML_TEMPLATE)

    # Top-level convenience route: /admin redirects directly to the approvals & kill-switch console
    @application.get("/admin", tags=["HITL Dashboard"])
    async def admin_console_redirect():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/approvals")


    # Mount top-level /health directly for simple ping tools
    application.include_router(health_router)

    # Mount versioned API routes
    application.include_router(api_router)

    return application


app = create_app()
