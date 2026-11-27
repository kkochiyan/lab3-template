from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import async_engine

from app.routers.hotels import router as hotel_router
from app.routers.reservations import router as reservation_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await async_engine.dispose()

app = FastAPI(title="Reservation Service", lifespan=lifespan)

app.include_router(hotel_router, prefix="/internal/v1")
app.include_router(reservation_router, prefix="/internal/v1")

@app.get("/manage/health")
def health_check():
    return {"status": "ok"}