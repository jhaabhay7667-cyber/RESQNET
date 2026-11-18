from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.deps import get_current_user, require_roles
from ..algorithms.graph import dijkstra
from ..database import get_db
from ..models import Hospital, HospitalResource, User
from ..realtime import manager
from ..schemas import HospitalCreate, HospitalOut, HospitalResourceUpdate
from .graph_service import graph_from_db, nearest_graph_node

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("", response_model=list[HospitalOut])
def list_hospitals(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[Hospital]:
    return list(db.scalars(select(Hospital).order_by(Hospital.name)).all())


@router.post("", response_model=HospitalOut, status_code=status.HTTP_201_CREATED)
def create_hospital(payload: HospitalCreate, db: Session = Depends(get_db), _user: User = Depends(require_roles("Administrator", "Emergency Dispatcher"))) -> Hospital:
    if db.scalar(select(Hospital.id).where(Hospital.name == payload.name)):
        raise HTTPException(status_code=409, detail="Hospital name already exists")
    item = Hospital(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{hospital_id}/resources", response_model=HospitalOut)
async def update_resources(
    hospital_id: str,
    payload: HospitalResourceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Hospital:
    item = db.scalar(select(Hospital).where(Hospital.id == hospital_id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Hospital not found")
    if user.role not in {"Administrator", "Emergency Dispatcher"} and not (
        user.role == "Hospital Operator" and item.operator_user_id == user.id
    ):
        raise HTTPException(status_code=403, detail="You are not assigned to this hospital")
    item.available_beds = payload.available_beds
    item.accepting_patients = payload.accepting_patients
    resource = db.scalar(select(HospitalResource).where(
        HospitalResource.hospital_id == item.id,
        HospitalResource.resource_type == "beds",
    ))
    if resource is None:
        resource = HospitalResource(hospital_id=item.id, resource_type="beds", available=payload.available_beds)
        db.add(resource)
    else:
        resource.available = payload.available_beds
    db.commit()
    db.refresh(item)
    await manager.broadcast({"type": "hospital.resources", "message": f"Hospital capacity updated for {item.name}.", "hospital_id": item.id})
    return item


@router.get("/recommend", response_model=list[dict])
def recommend_hospitals(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[dict]:
    graph = graph_from_db(db)
    origin = nearest_graph_node(graph, latitude, longitude)
    result: list[dict] = []
    for hospital in db.scalars(select(Hospital).where(Hospital.accepting_patients.is_(True), Hospital.available_beds > 0)).all():
        destination = nearest_graph_node(graph, hospital.latitude, hospital.longitude)
        try:
            route = dijkstra(graph, origin, destination)
        except ValueError:
            continue
        score = hospital.available_beds * 0.6 + hospital.icu_capacity * 0.4 - route.distance
        result.append({
            "id": hospital.id,
            "name": hospital.name,
            "distance_km": round(route.distance, 2),
            "estimated_travel_time_min": round(route.distance * 2.4, 1),
            "available_beds": hospital.available_beds,
            "icu_capacity": hospital.icu_capacity,
            "emergency_facilities": hospital.emergency_facilities,
            "score": round(score, 2),
        })
    return sorted(result, key=lambda item: (-item["score"], item["distance_km"]))
