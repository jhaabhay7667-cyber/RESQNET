from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..algorithms.dispatch import GreedyDispatcher
from ..algorithms.graph import dijkstra
from ..database import get_db
from ..models import Ambulance, Dispatch, Emergency, EmergencyEvent, Notification, User, utc_now
from ..realtime import manager
from ..schemas import DispatchApproveRequest
from .deps import require_roles
from .graph_service import graph_from_db, nearest_graph_node

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


@router.get("")
def list_dispatches(db: Session = Depends(get_db), _user: User = Depends(require_roles("Administrator", "Emergency Dispatcher", "Field Operator"))) -> list[dict]:
    records = db.scalars(select(Dispatch).order_by(Dispatch.created_at.desc())).all()
    return [{
        "id": item.id,
        "emergency_id": item.emergency_id,
        "vehicle_id": item.vehicle_id,
        "status": item.status,
        "route_algorithm": item.route_algorithm,
        "distance_km": item.distance_km,
        "estimated_travel_time_min": item.estimated_travel_time_min,
        "created_at": item.created_at.isoformat(),
    } for item in records]


@router.get("/recommend/{emergency_id}")
def recommend(
    emergency_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("Administrator", "Emergency Dispatcher")),
) -> dict:
    emergency = db.get(Emergency, emergency_id)
    if emergency is None:
        raise HTTPException(status_code=404, detail="Emergency not found")
    if emergency.assigned_vehicle_id:
        raise HTTPException(status_code=409, detail="Emergency already has an assigned vehicle")
    graph = graph_from_db(db)
    target = nearest_graph_node(graph, emergency.latitude, emergency.longitude)
    candidates = []
    for vehicle in db.scalars(select(Ambulance).where(Ambulance.status == "Available")).all():
        start = nearest_graph_node(graph, vehicle.latitude, vehicle.longitude)
        try:
            route = dijkstra(graph, start, target)
        except ValueError:
            continue
        candidates.append({
            "id": vehicle.id,
            "name": vehicle.name,
            "vehicle_type": vehicle.vehicle_type,
            "status": vehicle.status,
            "capacity": vehicle.capacity,
            "equipment": vehicle.equipment,
            "graph_node": start,
            "distance_km": route.distance,
            "estimated_travel_time_min": round(route.distance * 2.4, 1),
        })
    allocator = GreedyDispatcher(graph)
    suggestion = allocator.recommend(
        {"category": emergency.category, "severity": emergency.severity, "graph_node": target},
        candidates,
    )
    vehicle = suggestion["vehicle"]
    if vehicle is None:
        return {"vehicle": None, "estimated_travel_time_min": None, "reason": suggestion["reason"], "alternatives": []}
    alternatives = sorted(candidates, key=lambda item: (item["distance_km"], item["name"]))
    return {
        "vehicle": {key: value for key, value in vehicle.items() if key != "graph_node"},
        "estimated_travel_time_min": vehicle["estimated_travel_time_min"],
        "reason": suggestion["reason"],
        "alternatives": [{key: value for key, value in candidate.items() if key != "graph_node"} for candidate in alternatives[:3]],
    }


@router.post("/{emergency_id}/approve", status_code=status.HTTP_201_CREATED)
async def approve_dispatch(
    emergency_id: str,
    payload: DispatchApproveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Administrator", "Emergency Dispatcher")),
) -> dict:
    emergency = db.scalar(select(Emergency).where(Emergency.id == emergency_id).with_for_update())
    vehicle = db.scalar(select(Ambulance).where(Ambulance.id == payload.vehicle_id).with_for_update())
    if emergency is None:
        raise HTTPException(status_code=404, detail="Emergency not found")
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if emergency.assigned_vehicle_id is not None or emergency.status in {"Resolved", "Cancelled"}:
        raise HTTPException(status_code=409, detail="Emergency is already assigned or closed")
    if vehicle.status != "Available":
        raise HTTPException(status_code=409, detail="Vehicle is not available")

    graph = graph_from_db(db)
    start = nearest_graph_node(graph, vehicle.latitude, vehicle.longitude)
    end = nearest_graph_node(graph, emergency.latitude, emergency.longitude)
    try:
        route = dijkstra(graph, start, end)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="No viable road route for this assignment") from exc

    vehicle.status = "Dispatched"
    emergency.status = "Dispatched"
    emergency.assigned_vehicle_id = vehicle.id
    dispatch = Dispatch(
        emergency_id=emergency.id,
        vehicle_id=vehicle.id,
        approved_by=user.id,
        status="Dispatched",
        route_algorithm="dijkstra",
        distance_km=route.distance,
        estimated_travel_time_min=round(route.distance * 2.4, 1),
    )
    db.add(dispatch)
    db.add(EmergencyEvent(emergency_id=emergency.id, actor_id=user.id, event_type="dispatch_approved", message=f"{vehicle.name} assigned by dispatcher"))
    db.add(Notification(title="Dispatch approved", message=f"{vehicle.name} assigned to incident {emergency.id}"))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Emergency or vehicle was assigned by another dispatcher") from exc
    db.refresh(dispatch)
    await manager.broadcast({"type": "dispatch.approved", "message": f"{vehicle.name} assigned to emergency {emergency.id}.", "dispatch_id": dispatch.id})
    return {
        "id": dispatch.id,
        "emergency_id": dispatch.emergency_id,
        "vehicle_id": dispatch.vehicle_id,
        "status": dispatch.status,
        "route_algorithm": dispatch.route_algorithm,
        "distance_km": dispatch.distance_km,
        "estimated_travel_time_min": dispatch.estimated_travel_time_min,
        "path": route.path,
    }
