from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import async_engine
from app.routers.loyalty import router as loyalty_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await async_engine.dispose()


app = FastAPI(title="Loyalty Service", lifespan=lifespan)
app.include_router(loyalty_router, prefix="/internal/v1")


@app.get("/manage/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
