from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import models  # noqa: F401 - registers ORM metadata before schema initialization
from .api import analytics, ambulances, assistant, auth, dispatch, dsa, emergencies, hospitals, notifications, routing
from .database import Base, SessionLocal, engine
from .models import User
from .realtime import manager
from .security import decode_token
from .seed import seed_demo_data


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    if os.getenv("AUTO_CREATE_SCHEMA", "true").lower() in {"1", "true", "yes"}:
        Base.metadata.create_all(bind=engine)
    if os.getenv("SEED_DEMO_DATA", "true").lower() in {"1", "true", "yes"}:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(
    title="RESQNET API",
    description="Emergency response coordination demo. All seed records are synthetic; this service does not contact emergency services.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [origin.strip() for origin in os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(emergencies.router)
api_v1.include_router(ambulances.router)
api_v1.include_router(hospitals.router)
api_v1.include_router(dispatch.router)
api_v1.include_router(routing.router)
api_v1.include_router(analytics.router)
api_v1.include_router(notifications.router)
api_v1.include_router(dsa.router)
api_v1.include_router(assistant.router)


@api_v1.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": os.getenv("RESQNET_ENV", "development")}


@api_v1.get("/health/ready")
def readiness() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


app.include_router(api_v1)

# Kept as a lightweight compatibility health URL for earlier local setup instructions.
@app.get("/api/health", include_in_schema=False)
def legacy_health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/api/v1/ws/updates")
async def websocket_updates(socket: WebSocket, token: str = "") -> None:
    try:
        claims = decode_token(token, expected_type="access")
    except ValueError:
        await socket.close(code=1008, reason="Authentication required")
        return
    with SessionLocal() as db:
        user = db.get(User, claims.get("sub"))
        if user is None or not user.is_active:
            await socket.close(code=1008, reason="Account unavailable")
            return
    await manager.connect(socket)
    try:
        await socket.send_json({"type": "connection", "message": "Authenticated live updates connected.", "role": user.role})
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(socket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
