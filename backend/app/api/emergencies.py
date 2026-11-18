from __future__ import annotations

import threading
from collections import defaultdict, deque
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..algorithms.structures import EmergencyPriorityQueue
from ..api.deps import get_current_user, require_roles
from ..database import get_db
from ..models import Dispatch, Emergency, EmergencyEvent, Notification, User, utc_now
from ..realtime import manager
from ..schemas import (
    EmergencyCreate,
    EmergencyOut,
    EmergencyUpdate,
    PublicCancelRequest,
    PublicSosCreate,
    PublicSosOut,
    PublicStatusOut,
)
from ..security import create_cancel_token, verify_cancel_token
from .priorities import priority_score

router = APIRouter(tags=["emergencies"])
_request_times: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = threading.Lock()


def _rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    now = time()
    with _rate_lock:
        attempts = _request_times[client]
        while attempts and now - attempts[0] > 60:
            attempts.popleft()
        if len(attempts) >= 5:
            raise HTTPException(status_code=429, detail="SOS rate limit exceeded; try again later")
        attempts.append(now)


def _out(item: Emergency) -> EmergencyOut:
    return EmergencyOut(
        id=item.id,
        title=item.title,
        category=item.category,
        severity=item.severity,
        priority=item.priority,
        latitude=item.latitude,
        longitude=item.longitude,
        description=item.description,
        status=item.status,
        assigned_vehicle_id=item.assigned_vehicle_id,
        created_at=item.created_at.isoformat(),
    )


@router.get("/emergencies", response_model=list[EmergencyOut])
def list_emergencies(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[EmergencyOut]:
    records = db.scalars(select(Emergency)).all()
    now = time()
    queue: EmergencyPriorityQueue[Emergency] = EmergencyPriorityQueue()
    for item in records:
        queue.push(item, item.priority, enqueued_at=item.created_at.timestamp())
    prioritized = [queue.pop(now=now) for _ in range(len(queue))]
    return [_out(item) for item in prioritized]


@router.post("/emergencies", response_model=EmergencyOut, status_code=status.HTTP_201_CREATED)
async def create_emergency(
    payload: EmergencyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Administrator", "Emergency Dispatcher")),
) -> EmergencyOut:
    now = utc_now()
    item = Emergency(
        title=payload.title,
        category=payload.category,
        severity=payload.severity,
        priority=priority_score(payload.severity, payload.category, now.timestamp()),
        latitude=payload.latitude,
        longitude=payload.longitude,
        description=payload.description,
        status="Open",
    )
    db.add(item)
    db.flush()
    db.add(EmergencyEvent(emergency_id=item.id, actor_id=user.id, event_type="created", message="Emergency created by dispatcher"))
    db.add(Notification(title="New emergency", message=f"{item.category} incident created ({item.severity} priority)"))
    db.commit()
    db.refresh(item)
    await manager.broadcast({"type": "emergency.created", "message": f"New {item.severity.lower()} {item.category.lower()} incident recorded.", "emergency_id": item.id})
    return _out(item)


@router.patch("/emergencies/{emergency_id}", response_model=EmergencyOut)
async def update_emergency(
    emergency_id: str,
    payload: EmergencyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Administrator", "Emergency Dispatcher")),
) -> EmergencyOut:
    item = db.scalar(select(Emergency).where(Emergency.id == emergency_id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Emergency not found")
    if payload.status == "Dispatched" and item.assigned_vehicle_id is None:
        raise HTTPException(status_code=409, detail="Approve a dispatch before marking this incident dispatched")
    if payload.status in {"En Route", "On Scene", "Transporting", "Resolved"} and item.assigned_vehicle_id is None:
        raise HTTPException(status_code=409, detail="An assigned dispatch is required for this status")
    previous = item.status
    item.status = payload.status
    item.updated_at = utc_now()
    db.add(EmergencyEvent(emergency_id=item.id, actor_id=user.id, event_type="status_changed", message=f"Status changed from {previous} to {payload.status}"))
    if payload.status in {"Resolved", "Cancelled"} and item.assigned_vehicle_id:
        vehicle = item.assigned_vehicle
        if vehicle is not None:
            vehicle.status = "Available"
        dispatch = db.scalar(select(Dispatch).where(Dispatch.emergency_id == item.id).with_for_update())
        if dispatch is not None:
            dispatch.status = "Completed" if payload.status == "Resolved" else "Cancelled"
            dispatch.completed_at = utc_now()
    db.commit()
    db.refresh(item)
    await manager.broadcast({"type": "emergency.updated", "message": f"Incident {item.id} status changed to {item.status}.", "emergency_id": item.id})
    return _out(item)


@router.get("/public/sos/{emergency_id}", response_model=PublicStatusOut)
def track_sos(emergency_id: str, db: Session = Depends(get_db)) -> PublicStatusOut:
    item = db.get(Emergency, emergency_id)
    if item is None:
        raise HTTPException(status_code=404, detail="SOS request not found")
    return PublicStatusOut(
        id=item.id,
        title=item.title,
        category=item.category,
        severity=item.severity,
        status=item.status,
        latitude=item.latitude,
        longitude=item.longitude,
        created_at=item.created_at.isoformat(),
    )


@router.post("/public/sos", response_model=PublicSosOut, status_code=status.HTTP_201_CREATED)
async def create_public_sos(payload: PublicSosCreate, request: Request, db: Session = Depends(get_db)) -> PublicSosOut:
    _rate_limit(request)
    now = utc_now()
    cancel_token, cancel_hash = create_cancel_token()
    item = Emergency(
        title=f"Public {payload.category.lower()} request",
        category=payload.category,
        severity=payload.severity,
        priority=priority_score(payload.severity, payload.category, now.timestamp()),
        latitude=payload.latitude,
        longitude=payload.longitude,
        description=payload.description,
        status="Pending Approval",
        public_cancel_token_hash=cancel_hash,
    )
    db.add(item)
    db.flush()
    db.add(EmergencyEvent(emergency_id=item.id, actor_id=None, event_type="public_sos", message="Synthetic public SOS submitted; dispatcher approval required"))
    db.add(Notification(title="Public SOS submitted", message=f"Synthetic {payload.category.lower()} request awaiting dispatcher review"))
    db.commit()
    db.refresh(item)
    await manager.broadcast({"type": "emergency.sos", "message": "A simulated public SOS request is awaiting dispatcher review.", "emergency_id": item.id})
    return PublicSosOut(id=item.id, status=item.status, created_at=item.created_at.isoformat(), cancel_token=cancel_token)


@router.post("/public/sos/{emergency_id}/cancel", response_model=PublicStatusOut)
async def cancel_public_sos(
    emergency_id: str,
    payload: PublicCancelRequest,
    db: Session = Depends(get_db),
) -> PublicStatusOut:
    item = db.scalar(select(Emergency).where(Emergency.id == emergency_id).with_for_update())
    if item is None or not verify_cancel_token(payload.cancel_token, item.public_cancel_token_hash):
        raise HTTPException(status_code=404, detail="SOS request or cancellation token not found")
    if item.status in {"Resolved", "Cancelled"}:
        raise HTTPException(status_code=409, detail="SOS request is already closed")
    item.status = "Cancelled"
    item.public_cancel_token_hash = None
    item.updated_at = utc_now()
    db.add(EmergencyEvent(emergency_id=item.id, event_type="public_cancelled", message="Public SOS cancellation requested by submitter"))
    db.commit()
    await manager.broadcast({"type": "emergency.cancelled", "message": "A simulated SOS request was cancelled.", "emergency_id": item.id})
    return PublicStatusOut(id=item.id, title=item.title, category=item.category, severity=item.severity, status=item.status, latitude=item.latitude, longitude=item.longitude, created_at=item.created_at.isoformat())
