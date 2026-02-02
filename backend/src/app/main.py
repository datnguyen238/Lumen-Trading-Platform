from fastapi import FastAPI

from app.api import api_router
from app.db.session import engine
from app.db.base import Base

app = FastAPI(title="Trading Platform API")

@app.on_event("startup")
def startup():
    # SQLite file DB will be created automatically on first connect
    Base.metadata.create_all(bind=engine)

app.include_router(api_router)
