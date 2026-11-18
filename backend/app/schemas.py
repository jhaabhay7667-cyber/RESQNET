from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["Administrator", "Emergency Dispatcher", "Field Operator", "Hospital Operator"]
Severity = Literal["Critical", "High", "Medium", "Low"]
EmergencyStatus = Literal["Open", "Pending Approval", "Dispatched", "En Route", "On Scene", "Transporting", "Resolved", "Cancelled"]
VehicleStatus = Literal["Available", "Dispatched", "En Route", "On Scene", "Transporting", "Out of Service"]
EmergencyCategory = Literal["Road Accident", "Medical Emergency", "Fire Emergency", "Road Blockage"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    email: str
    role: str


class AuthCredentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(AuthCredentials):
    email: EmailStr
    role: str = "Emergency Dispatcher"

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: str | None) -> str:
        if value is None:
            return "Emergency Dispatcher"
        normalized = str(value).strip()
        aliases = {
            "admin": "Administrator",
            "administrator": "Administrator",
            "dispatcher": "Emergency Dispatcher",
            "emergency dispatcher": "Emergency Dispatcher",
            "field": "Field Operator",
            "field operator": "Field Operator",
            "hospital": "Hospital Operator",
            "hospital operator": "Hospital Operator",
        }
        return aliases.get(normalized.lower(), normalized)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class EmergencyCreate(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    category: EmergencyCategory
    severity: Severity = "High"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    description: str = Field(min_length=8, max_length=4000)


class EmergencyUpdate(BaseModel):
    status: EmergencyStatus


class EmergencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    category: str
    severity: str
    priority: float
    latitude: float
    longitude: float
    description: str
    status: str
    assigned_vehicle_id: str | None
    created_at: str


class PublicSosCreate(BaseModel):
    category: EmergencyCategory
    severity: Severity = "High"
    description: str = Field(min_length=8, max_length=1000)
    contact: str | None = Field(default=None, max_length=40)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    confirmation: Literal[True]


class PublicCancelRequest(BaseModel):
    cancel_token: str = Field(min_length=20, max_length=128)


class PublicSosOut(BaseModel):
    id: str
    status: str
    created_at: str
    cancel_token: str | None = None


class PublicStatusOut(BaseModel):
    id: str
    title: str
    category: str
    severity: str
    status: str
    latitude: float
    longitude: float
    created_at: str


class AmbulanceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    vehicle_type: Literal["Ambulance", "Fire Truck", "Rescue Unit", "Support Van"]
    status: VehicleStatus = "Available"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacity: int = Field(ge=1, le=100)
    equipment: str = Field(default="", max_length=255)


class AmbulanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    vehicle_type: str
    status: str
    latitude: float
    longitude: float
    capacity: int
    equipment: str
    last_updated: str | None


class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class HospitalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    available_beds: int = Field(ge=0, le=100000)
    icu_capacity: int = Field(ge=0, le=100000)
    emergency_facilities: str = Field(default="", max_length=255)


class HospitalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    latitude: float
    longitude: float
    available_beds: int
    icu_capacity: int
    emergency_facilities: str
    accepting_patients: bool


class HospitalResourceUpdate(BaseModel):
    available_beds: int = Field(ge=0, le=100000)
    accepting_patients: bool


class LocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: LocationRequest
    destination: LocationRequest
    algorithm: Literal["dijkstra", "astar"] = "dijkstra"
    blocked_roads: list[tuple[str, str]] = Field(default_factory=list)


class DsaRunRequest(BaseModel):
    algorithm: Literal["dijkstra", "astar", "bfs", "dfs"]
    source: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=100)


class DispatchApproveRequest(BaseModel):
    vehicle_id: str = Field(min_length=1, max_length=36)


class AssistantRequest(BaseModel):
    report: str = Field(min_length=8, max_length=4000)
    language: str = Field(default="auto", max_length=32)
