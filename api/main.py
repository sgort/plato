import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

from db.database import init_db
from routers import cbs, legislation, ob, searches, tk
from services.cache import cache_close

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database…")
    await init_db()
    logger.info("Ready.")
    yield
    await cache_close()


app = FastAPI(
    title="Policy Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def no_cache_api(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        FRONTEND_ORIGIN,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tk.router)
app.include_router(ob.router)
app.include_router(legislation.router)
app.include_router(cbs.router)
app.include_router(searches.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
