import os

os.environ["DATABASE_URL"] = "sqlite:///./resqnet-test.db"
os.environ["SEED_DEMO_DATA"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Ambulance, Emergency


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def login(client: TestClient, username: str = "demo-admin") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "DemoOnly123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_and_seeded_dashboard(client: TestClient) -> None:
    assert client.get("/api/v1/health").json()["status"] == "ok"
    response = client.get("/api/v1/analytics/dashboard", headers=login(client))
    assert response.status_code == 200
    assert response.json()["stats"]["activeEmergencies"] == 3
    assert response.json()["stats"]["availableAmbulances"] == 2


def test_auth_refresh_rotation_and_rbac(client: TestClient) -> None:
    login_response = client.post("/api/v1/auth/login", json={"username": "demo-field", "password": "DemoOnly123!"})
    assert login_response.status_code == 200
    token = login_response.json()
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": token["refresh_token"]})
    assert refreshed.status_code == 200
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": token["refresh_token"]})
    assert reused.status_code == 401
    denied = client.post("/api/v1/emergencies", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"}, json={
        "title": "Unauthorized record",
        "category": "Medical Emergency",
        "severity": "High",
        "latitude": 40.7,
        "longitude": -74,
        "description": "This role cannot create dispatch records.",
    })
    assert denied.status_code == 403


def test_register_accepts_legacy_dispatcher_role_alias(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={
        "username": "dispatcher-alias",
        "email": "dispatcher-alias@example.com",
        "password": "Password123!",
        "role": "Dispatcher",
    })
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "Emergency Dispatcher"


def test_public_registration_cannot_create_administrator(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={
        "username": "public-admin-attempt",
        "email": "public-admin-attempt@example.com",
        "password": "Password123!",
        "role": "Administrator",
    })
    assert response.status_code == 422


def test_incident_create_and_public_sos_lifecycle(client: TestClient) -> None:
    headers = login(client, "demo-dispatcher")
    incident = client.post("/api/v1/emergencies", headers=headers, json={
        "title": "Synthetic integration scenario",
        "category": "Road Accident",
        "severity": "Critical",
        "latitude": 40.72,
        "longitude": -74.01,
        "description": "Synthetic test data for the emergency workflow.",
    })
    assert incident.status_code == 201
    assert incident.json()["priority"] > 5

    sos = client.post("/api/v1/public/sos", json={
        "category": "Medical Emergency",
        "severity": "High",
        "description": "Synthetic public SOS integration test.",
        "latitude": 40.72,
        "longitude": -74.01,
        "confirmation": True,
    })
    assert sos.status_code == 201
    payload = sos.json()
    assert payload["status"] == "Pending Approval"
    assert "cancel_token" in payload
    tracked = client.get(f"/api/v1/public/sos/{payload['id']}")
    assert tracked.status_code == 200
    assert "description" not in tracked.json()
    cancelled = client.post(f"/api/v1/public/sos/{payload['id']}/cancel", json={"cancel_token": payload["cancel_token"]})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "Cancelled"
    assert client.post(f"/api/v1/public/sos/{payload['id']}/cancel", json={"cancel_token": payload["cancel_token"]}).status_code == 404


def test_dispatch_requires_approval_and_prevents_reassignment(client: TestClient) -> None:
    headers = login(client)
    incidents = client.get("/api/v1/emergencies", headers=headers).json()
    incident = next(item for item in incidents if item["status"] == "Open")
    recommendation = client.get(f"/api/v1/dispatch/recommend/{incident['id']}", headers=headers)
    assert recommendation.status_code == 200
    vehicle_id = recommendation.json()["vehicle"]["id"]
    approved = client.post(f"/api/v1/dispatch/{incident['id']}/approve", headers=headers, json={"vehicle_id": vehicle_id})
    assert approved.status_code == 201
    assert approved.json()["route_algorithm"] == "dijkstra"
    duplicate = client.post(f"/api/v1/dispatch/{incident['id']}/approve", headers=headers, json={"vehicle_id": vehicle_id})
    assert duplicate.status_code == 409
    with SessionLocal() as db:
        vehicle = db.scalar(select(Ambulance).where(Ambulance.id == vehicle_id))
        record = db.get(Emergency, incident["id"])
        assert vehicle is not None and vehicle.status == "Dispatched"
        assert record is not None and record.assigned_vehicle_id == vehicle_id


def test_road_graph_algorithms_route_and_hospital_recommendation(client: TestClient) -> None:
    headers = login(client)
    request = {
        "origin": {"latitude": 40.706, "longitude": -74.005},
        "destination": {"latitude": 40.748, "longitude": -73.99},
    }
    dijkstra = client.post("/api/v1/routing/route", headers=headers, json={**request, "algorithm": "dijkstra"})
    astar = client.post("/api/v1/routing/route", headers=headers, json={**request, "algorithm": "astar"})
    assert dijkstra.status_code == astar.status_code == 200
    assert dijkstra.json()["distance"] == astar.json()["distance"]
    assert dijkstra.json()["route_source"] == "road graph"
    assert dijkstra.json()["coordinates"]

    algorithm = client.post("/api/v1/dsa/run", headers=headers, json={"algorithm": "dijkstra", "source": "North Hub", "destination": "South Ward"})
    assert algorithm.status_code == 200
    assert algorithm.json()["path"][0] == "North Hub"
    assert algorithm.json()["trace"]
    recommendation = client.get("/api/v1/hospitals/recommend?latitude=40.72&longitude=-74.0", headers=headers)
    assert recommendation.status_code == 200
    assert recommendation.json()[0]["distance_km"] > 0


def test_operator_resource_permissions_and_live_location(client: TestClient) -> None:
    operator = login(client, "demo-field")
    vehicles = client.get("/api/v1/ambulances", headers=operator).json()
    assigned = next(item for item in vehicles if item["name"] == "A-101")
    updated = client.patch(f"/api/v1/ambulances/{assigned['id']}/location", headers=operator, json={"latitude": 40.715, "longitude": -74.011})
    assert updated.status_code == 200
    denied = client.patch(f"/api/v1/ambulances/{vehicles[-1]['id']}/location", headers=operator, json={"latitude": 40.715, "longitude": -74.011})
    assert denied.status_code == 403

    hospital_operator = login(client, "demo-hospital")
    hospitals = client.get("/api/v1/hospitals", headers=hospital_operator).json()
    mercy = next(item for item in hospitals if item["name"] == "Mercy General")
    changed = client.patch(f"/api/v1/hospitals/{mercy['id']}/resources", headers=hospital_operator, json={"available_beds": 17, "accepting_patients": True})
    assert changed.status_code == 200
    other_hospital = next(item for item in hospitals if item["name"] != "Mercy General")
    denied = client.patch(f"/api/v1/hospitals/{other_hospital['id']}/resources", headers=hospital_operator, json={"available_beds": 1, "accepting_patients": True})
    assert denied.status_code == 403


def test_authenticated_websocket_connects(client: TestClient) -> None:
    headers = login(client)
    token = headers["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/api/v1/ws/updates?token={token}") as socket:
        message = socket.receive_json()
        assert message["type"] == "connection"
        assert message["role"] == "Administrator"
