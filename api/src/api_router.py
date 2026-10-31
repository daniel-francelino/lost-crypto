from fastapi import APIRouter, Depends

from core.security.auth import require_access, require_auth_configured
from modules.audit.router import router as audit_router
from modules.auth.router import router as auth_router
from modules.backtesting.presentation.router import router as backtests_router
from modules.bots.presentation.router import router as bots_router
from modules.exchanges.presentation.router import router as connections_router
from modules.health.router import router as health_router
from modules.market_data.presentation.router import router as market_data_router
from modules.notifications.presentation.router import router as alerts_router
from modules.risk_management.presentation.router import router as system_router
from modules.strategies.presentation.router import router as strategies_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)  # health checks stay open for probes

# Login endpoints are open (they enforce their own rules); everything else needs a signed-in
# user, or the service token. Reading is open to any role, changing state needs admin.
api_router.include_router(auth_router)
_protected = [Depends(require_access)]
for _router in (
    strategies_router,
    market_data_router,
    backtests_router,
    bots_router,
    system_router,
    audit_router,
    alerts_router,
):
    api_router.include_router(_router, dependencies=_protected)
# Accepts secrets: also refuses to work while no token is configured at all.
api_router.include_router(
    connections_router, dependencies=[*_protected, Depends(require_auth_configured)]
)
