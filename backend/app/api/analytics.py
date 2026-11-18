from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.deps import get_current_user, require_roles
from ..database import get_db
from ..models import Ambulance, Dispatch, Emergency, EmergencyEvent, Hospital, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _week_label(date: datetime) -> str:
    return f"{date.isocalendar().year}-W{date.isocalendar().week:02d}"


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    emergencies = db.scalars(select(Emergency)).all()
    ambulances = db.scalars(select(Ambulance)).all()
    hospitals = db.scalars(select(Hospital)).all()
    active = [item for item in emergencies if item.status not in {"Resolved", "Cancelled"}]
    dispatches = db.scalars(select(Dispatch).order_by(Dispatch.created_at.desc()).limit(10)).all()
    events = db.scalars(select(EmergencyEvent).order_by(EmergencyEvent.created_at.desc()).limit(8)).all()
    activity = [{"id": event.id, "message": event.message, "time": event.created_at.isoformat(), "type": event.event_type} for event in events]
    category_counts = Counter(item.category for item in emergencies)
    utilization_counts = Counter(item.vehicle_id for item in dispatches)
    utilization = [{"name": vehicle.name, "value": min(100, utilization_counts.get(vehicle.id, 0) * 20)} for vehicle in ambulances]
    completed = [item for item in dispatches if item.completed_at is not None]
    response_times = [
        (item.completed_at - item.created_at).total_seconds() / 60
        for item in completed
        if item.completed_at is not None
    ]
    return {
        "stats": {
            "activeEmergencies": len(active),
            "criticalIncidents": sum(item.severity == "Critical" for item in active),
            "availableAmbulances": sum(item.status == "Available" for item in ambulances),
            "dispatchedVehicles": sum(item.status in {"Dispatched", "En Route", "On Scene", "Transporting"} for item in ambulances),
            "hospitalsAvailable": sum(item.accepting_patients and item.available_beds > 0 for item in hospitals),
            "averageResponseTime": round(sum(response_times) / len(response_times), 1) if response_times else 0,
        },
        "activity": activity,
        "distribution": [{"name": key, "value": value} for key, value in category_counts.items()],
        "utilization": utilization,
    }


@router.get("")
def analytics(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    emergencies = db.scalars(select(Emergency).order_by(Emergency.created_at)).all()
    dispatches = db.scalars(select(Dispatch)).all()
    categories = Counter(item.category for item in emergencies)
    daily: dict[str, int] = defaultdict(int)
    weekly: dict[str, list[float]] = defaultdict(list)
    monthly: dict[str, int] = defaultdict(int)
    hotspots: dict[tuple[float, float], int] = defaultdict(int)
    for item in emergencies:
        created = item.created_at
        daily[created.date().isoformat()] += 1
        monthly[created.strftime("%Y-%m")] += 1
        hotspots[(round(item.latitude, 3), round(item.longitude, 3))] += 1
    for dispatch in dispatches:
        if dispatch.completed_at is not None:
            elapsed = max(0.0, (dispatch.completed_at - dispatch.created_at).total_seconds() / 60)
            weekly[_week_label(dispatch.created_at)].append(elapsed)
    response_weekly = [
        {"label": label, "responseTime": round(sum(values) / len(values), 1)}
        for label, values in sorted(weekly.items())
    ]
    average_response = (
        sum(value for values in weekly.values() for value in values)
        / sum(len(values) for values in weekly.values())
        if weekly else 0
    )
    vehicle_counts = Counter(item.vehicle_id for item in dispatches)
    hospital_workload = [
        {"name": item.name, "available_beds": item.available_beds, "icu_capacity": item.icu_capacity, "accepting_patients": item.accepting_patients}
        for item in db.scalars(select(Hospital)).all()
    ]
    return {
        "daily": [{"label": label, "incidents": value} for label, value in sorted(daily.items())],
        "weekly": response_weekly,
        "monthly": [{"label": label, "incidents": value} for label, value in sorted(monthly.items())],
        "category_distribution": [{"label": key, "value": value} for key, value in categories.items()],
        "geographic_hotspots": [{"latitude": lat, "longitude": lon, "count": count} for (lat, lon), count in hotspots.items()],
        "average_response_time_min": round(average_response, 1),
        "ambulance_utilization": [{"vehicle_id": key, "dispatch_count": value} for key, value in vehicle_counts.items()],
        "hospital_workload": hospital_workload,
    }


@router.get("/events")
def recent_events(db: Session = Depends(get_db), _user: User = Depends(require_roles("Administrator", "Emergency Dispatcher"))) -> list[dict]:
    records = db.scalars(select(EmergencyEvent).order_by(EmergencyEvent.created_at.desc()).limit(100)).all()
    return [{"id": item.id, "emergency_id": item.emergency_id, "event_type": item.event_type, "message": item.message, "created_at": item.created_at.isoformat()} for item in records]
