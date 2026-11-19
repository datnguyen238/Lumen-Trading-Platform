import asyncio
import contextlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.db.session import engine
from app.db.base import Base
from app.db.privacy import protect_private_tables
from app.core.config import settings
from app.services.paper_worker import PaperWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_auto_setup and not settings.vercel:
        Base.metadata.create_all(bind=engine)
        protect_private_tables(engine)
    worker = PaperWorker()
    app.state.paper_worker = worker if settings.embedded_worker_enabled else None
    app.state.external_paper_worker = settings.vercel and settings.paper_worker_enabled
    task = asyncio.create_task(worker.run()) if settings.embedded_worker_enabled else None
    try:
        yield
    finally:
        worker.stop()
        if task:
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=15)
            except asyncio.TimeoutError:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task


app = FastAPI(title='Lumen Paper Trading API', lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=sorted(settings.allowed_origins),
    allow_credentials=True, allow_methods=['*'], allow_headers=['*'])


@app.middleware('http')
async def protect_browser_requests(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        allowed = settings.allowed_origins
        if origin and origin not in allowed:
            return JSONResponse({'detail': 'This origin is not allowed.'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Cross-site requests are not allowed.'}, status_code=403)
        path = request.scope['path']
        root = request.scope.get('root_path', '')
        if root and path.startswith(root):
            path = path[len(root):]
        if path.startswith('/auth/') and 'application/json' not in request.headers.get('content-type', ''):
            return JSONResponse({'detail': 'Send this request as JSON.'}, status_code=415)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


app.include_router(api_router)
