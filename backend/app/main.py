from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.db.session import engine
from app.db.base import Base

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