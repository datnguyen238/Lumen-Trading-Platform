"""Vercel service entrypoint. The browser and API share the site's origin."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.main import app as api


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mounted ASGI applications do not run their own lifespan automatically.
    async with api.router.lifespan_context(api):
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/api', api)
