"""Standalone trading daemon with an internal health endpoint for Vercel probes."""
import asyncio
import contextlib
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine
from app.services.paper_worker import PaperWorker

logger = logging.getLogger(__name__)


def healthy(worker: PaperWorker, started: float) -> bool:
    # A completed cycle increments this heartbeat. A wedged database/provider call
    # must eventually fail the probe even if the Python HTTP thread still responds.
    last = getattr(worker, 'last_progress_monotonic', None)
    allowance = max(180, settings.paper_worker_interval_seconds * 4)
    return not worker.stop_event.is_set() and time.monotonic() - (last or started) < allowance


@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as connection:
        connection.execute(text('SELECT 1'))
    worker = PaperWorker()
    app.state.worker = worker
    app.state.started = time.monotonic()
    task = asyncio.create_task(worker.run())
    logger.info('Standalone paper trading worker started')
    try:
        yield
    finally:
        worker.stop()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=25)
        except asyncio.TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        engine.dispose()
        logger.info('Standalone paper trading worker stopped')


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get('/health')
def health():
    worker = app.state.worker
    ok = healthy(worker, app.state.started)
    return JSONResponse({'status': 'ok' if ok else 'stalled', 'paper_trading': worker.status},
                        status_code=200 if ok else 503)
