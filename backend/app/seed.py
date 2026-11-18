from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from .algorithms.graph import build_demo_graph
from .models import Ambulance, Emergency, EmergencyEvent, Hospital, HospitalResource, Road, User, utc_now
from .security import hash_password

DEMO_ACCOUNTS = [
    ("demo-admin", "admin@resqnet.local", "Administrator"),
    ("demo-dispatcher", "dispatcher@resqnet.local", "Emergency Dispatcher"),
    ("demo-field", "field@resqnet.local", "Field Operator"),
    ("demo-hospital", "hospital@resqnet.local", "Hospital Operator"),
]
DEMO_PASSWORD = "DemoOnly123!"


def seed_demo_data(db: Session) -> None:
    if os.getenv("SEED_DEMO_DATA", "true").lower() not in {"1", "true", "yes"}:
        return
    seeded_users: dict[str, User] = {}
    for username, email, role in DEMO_ACCOUNTS:
        if db.scalar(select(User).where(User.username == username)) is None:
            user = User(username=username, email=email, password_hash=hash_password(DEMO_PASSWORD), role=role)
            db.add(user)
            seeded_users[username] = user
        else:
            seeded_users[username] = db.scalar(select(User).where(User.username == username))
    db.flush()

    graph = build_demo_graph()
    existing_roads = db.scalar(select(Road.id).limit(1))
    if existing_roads is None:
        for start, neighbors in graph.adjacency.items():
            for end, edge in neighbors.items():
                if start < end:
                    db.add(Road(start_node=start, end_node=end, distance_km=edge.weight, blocked=edge.blocked))

    if db.scalar(select(Ambulance.id).limit(1)) is None:
        db.add_all([
            Ambulance(name="A-101", vehicle_type="Ambulance", status="Available", latitude=40.7145, longitude=-74.012, capacity=2, equipment="Advanced life support, trauma kit", assigned_user_id=seeded_users["demo-field"].id),
            Ambulance(name="R-315", vehicle_type="Rescue Unit", status="Available", latitude=40.7208, longitude=-73.9986, capacity=3, equipment="Rescue tools, first aid"),
            Ambulance(name="F-204", vehicle_type="Fire Truck", status="Out of Service", latitude=40.748, longitude=-73.9901, capacity=5, equipment="Foam, rescue tools"),
        ])

    if db.scalar(select(Hospital.id).limit(1)) is None:
        db.add_all([
            Hospital(name="Mercy General", latitude=40.7065, longitude=-74.0092, available_beds=18, icu_capacity=7, emergency_facilities="Trauma center", accepting_patients=True, operator_user_id=seeded_users["demo-hospital"].id),
            Hospital(name="Northside Care", latitude=40.7341, longitude=-73.9852, available_beds=24, icu_capacity=9, emergency_facilities="Stroke and heart response", accepting_patients=True),
            Hospital(name="Harbor Medical", latitude=40.7609, longitude=-73.976, available_beds=12, icu_capacity=5, emergency_facilities="Burn unit", accepting_patients=True),
        ])
        db.flush()
        db.add_all([
            HospitalResource(hospital_id=hospital.id, resource_type="beds", available=hospital.available_beds)
            for hospital in db.scalars(select(Hospital)).all()
        ])
    if db.scalar(select(Emergency.id).limit(1)) is None:
        now = utc_now()
        samples = [
            Emergency(title="Synthetic multi-vehicle collision", category="Road Accident", severity="Critical", priority=5.3, latitude=40.7128, longitude=-74.006, description="Synthetic training scenario near the downtown grid.", status="Open", created_at=now),
            Emergency(title="Synthetic medical response request", category="Medical Emergency", severity="High", priority=4.5, latitude=40.7351, longitude=-73.9949, description="Synthetic training scenario requesting hospital transport.", status="Pending Approval", created_at=now),
            Emergency(title="Synthetic road obstruction", category="Road Blockage", severity="Medium", priority=3.0, latitude=40.7505, longitude=-73.9934, description="Synthetic training scenario with a temporary access obstruction.", status="Open", created_at=now),
        ]
        db.add_all(samples)
        db.flush()
        db.add_all([
            EmergencyEvent(emergency_id=item.id, event_type="seeded", message="Synthetic seed scenario; no real emergency.")
            for item in samples
        ])
    db.commit()
