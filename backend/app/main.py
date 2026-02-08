from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.api import api_router
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.core.config import settings
from app.services.price_refresh import refresh_watchlist_db

app = FastAPI(title="Trading Platform API")

# DEV CORS: allow your frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


async def _watchlist_refresh_loop():
    while True:
        if settings.watchlist_refresh_enabled:
            db = SessionLocal()
            try:
                refresh_watchlist_db(db, limit=settings.watchlist_refresh_limit)
            except Exception as e:
                print(f"[watchlist_refresh] failed: {e}")
            finally:
                db.close()
        await asyncio.sleep(settings.watchlist_refresh_interval_seconds)


@app.on_event("startup")
async def start_watchlist_job():
    app.state.watchlist_task = asyncio.create_task(_watchlist_refresh_loop())


@app.on_event("shutdown")
async def stop_watchlist_job():
    task = getattr(app.state, "watchlist_task", None)
    if task:
        task.cancel()
