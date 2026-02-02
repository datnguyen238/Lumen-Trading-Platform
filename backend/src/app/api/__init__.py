from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.users import router as users_router
from app.api.accounts import router as accounts_router
from app.api.prices import router as prices_router
from app.api.orders import router as orders_router
from app.api.trades import router as trades_router
from app.api.account_orders import router as account_orders_router
from app.api.summary import router as summary_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
api_router.include_router(prices_router, prefix="/prices", tags=["prices"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(trades_router, tags=["accounts"])
api_router.include_router(account_orders_router, tags=["accounts"])
api_router.include_router(summary_router, tags=["accounts"])

