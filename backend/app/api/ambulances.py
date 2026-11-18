from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.deps import get_current_user, require_roles
from ..database import get_db
from ..models import Ambulance, Location, User
from ..realtime import manager
from ..schemas import AmbulanceCreate, AmbulanceOut, LocationUpdate

router = APIRouter(prefix="/ambulances", tags=["ambulances"])


def _out(item: Ambulance) -> AmbulanceOut:
    return AmbulanceOut(
        id=item.id,
        name=item.name,
        vehicle_type=item.vehicle_type,
        status=item.status,
        latitude=item.latitude,
        longitude=item.longitude,
        capacity=item.capacity,
        equipment=item.equipment,
        last_updated=item.last_updated.isoformat() if item.last_updated else None,
    )


@router.get("", response_model=list[AmbulanceOut])
def list_ambulances(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[AmbulanceOut]:
    return [_out(item) for item in db.scalars(select(Ambulance).order_by(Ambulance.name)).all()]


@router.post("", response_model=AmbulanceOut, status_code=status.HTTP_201_CREATED)
def create_ambulance(payload: AmbulanceCreate, db: Session = Depends(get_db), _user: User = Depends(require_roles("Administrator", "Emergency Dispatcher"))) -> AmbulanceOut:
    if db.scalar(select(Ambulance.id).where(Ambulance.name == payload.name)):
        raise HTTPException(status_code=409, detail="Vehicle name already exists")
    item = Ambulance(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _out(item)


@router.patch("/{ambulance_id}", response_model=AmbulanceOut)
def update_ambulance(
    ambulance_id: str,
    payload: AmbulanceCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("Administrator", "Emergency Dispatcher")),
) -> AmbulanceOut:
    item = db.scalar(select(Ambulance).where(Ambulance.id == ambulance_id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    if payload.status == "Available" and item.status in {"Dispatched", "En Route", "On Scene", "Transporting"}:
        raise HTTPException(status_code=409, detail="A dispatched vehicle cannot be marked available before dispatch closure")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _out(item)


@router.patch("/{ambulance_id}/location", response_model=AmbulanceOut)
async def update_location(
    ambulance_id: str,
    payload: LocationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AmbulanceOut:
    item = db.scalar(select(Ambulance).where(Ambulance.id == ambulance_id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    if user.role not in {"Administrator", "Emergency Dispatcher"} and not (
        user.role == "Field Operator" and item.assigned_user_id == user.id
    ):
        raise HTTPException(status_code=403, detail="You are not assigned to this vehicle")
    now = datetime.now(timezone.utc)
    item.latitude = payload.latitude
    item.longitude = payload.longitude
    item.last_updated = now
    db.add(Location(owner_type="ambulance", owner_id=item.id, latitude=payload.latitude, longitude=payload.longitude, simulated=True))
    db.commit()
    db.refresh(item)
    await manager.broadcast({"type": "ambulance.location", "message": f"Operator-reported location updated for {item.name}.", "vehicle_id": item.id, "simulated": True})
    return _out(item)
