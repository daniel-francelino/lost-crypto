from fastapi import APIRouter

from modules.backtesting.presentation.router import router as backtests_router
from modules.health.router import router as health_router
from modules.market_data.presentation.router import router as market_data_router
from modules.strategies.presentation.router import router as strategies_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(strategies_router)
api_router.include_router(market_data_router)
api_router.include_router(backtests_router)
