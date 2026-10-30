from fastapi import APIRouter

from modules.audit.router import router as audit_router
from modules.backtesting.presentation.router import router as backtests_router
from modules.bots.presentation.router import router as bots_router
from modules.health.router import router as health_router
from modules.market_data.presentation.router import router as market_data_router
from modules.risk_management.presentation.router import router as system_router
from modules.strategies.presentation.router import router as strategies_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(strategies_router)
api_router.include_router(market_data_router)
api_router.include_router(backtests_router)
api_router.include_router(bots_router)
api_router.include_router(system_router)
api_router.include_router(audit_router)
