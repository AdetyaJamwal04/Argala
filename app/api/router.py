from fastapi import APIRouter

from app.api.routes_health import router as health_router
from app.api.routes_telemetry import router as telemetry_router
from app.api.routes_mcp import router as mcp_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_vault import router as vault_router
from app.api.routes_approvals import router as approvals_router
from app.api.routes_admin import router as admin_router

api_router = APIRouter()

# Mount health checks under /v1/health as well as top-level /health
api_router.include_router(health_router, prefix="/v1")
api_router.include_router(telemetry_router, prefix="/v1")
api_router.include_router(mcp_router, prefix="/v1")
api_router.include_router(jobs_router, prefix="/v1")
api_router.include_router(vault_router, prefix="/v1")
api_router.include_router(approvals_router, prefix="/v1")
api_router.include_router(admin_router, prefix="/v1")

