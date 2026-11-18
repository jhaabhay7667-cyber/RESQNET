from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_role_active", "role", "is_active"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="Emergency Dispatcher")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    emergency_events: Mapped[list[EmergencyEvent]] = relationship(back_populates="actor")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Emergency(Base):
    __tablename__ = "emergencies"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_emergency_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_emergency_longitude"),
        Index("ix_emergencies_status_severity_created", "status", "severity", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(48), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    priority: Mapped[float] = mapped_column(Float, default=1)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="Open", index=True)
    assigned_vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("ambulances.id", ondelete="SET NULL"), nullable=True)
    public_cancel_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    assigned_vehicle: Mapped[Ambulance | None] = relationship(foreign_keys=[assigned_vehicle_id])
    dispatch: Mapped[Dispatch | None] = relationship(back_populates="emergency", uselist=False)
    events: Mapped[list[EmergencyEvent]] = relationship(back_populates="emergency", cascade="all, delete-orphan")


class Ambulance(Base):
    __tablename__ = "ambulances"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_ambulance_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_ambulance_longitude"),
        CheckConstraint("capacity >= 1", name="ck_ambulance_capacity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), default="Available", index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer, default=2)
    equipment: Mapped[str] = mapped_column(String(255), default="")
    assigned_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dispatches: Mapped[list[Dispatch]] = relationship(back_populates="vehicle")


class Hospital(Base):
    __tablename__ = "hospitals"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_hospital_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_hospital_longitude"),
        CheckConstraint("available_beds >= 0 AND icu_capacity >= 0", name="ck_hospital_capacity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    available_beds: Mapped[int] = mapped_column(Integer, default=0)
    icu_capacity: Mapped[int] = mapped_column(Integer, default=0)
    emergency_facilities: Mapped[str] = mapped_column(String(255), default="")
    accepting_patients: Mapped[bool] = mapped_column(Boolean, default=True)
    operator_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    resources: Mapped[list[HospitalResource]] = relationship(back_populates="hospital", cascade="all, delete-orphan")


class HospitalResource(Base):
    __tablename__ = "hospital_resources"
    __table_args__ = (UniqueConstraint("hospital_id", "resource_type", name="uq_hospital_resource_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    available: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    hospital: Mapped[Hospital] = relationship(back_populates="resources")


class Road(Base):
    __tablename__ = "roads"
    __table_args__ = (
        UniqueConstraint("start_node", "end_node", name="uq_road_direction"),
        CheckConstraint("distance_km >= 0", name="ck_road_distance"),
        Index("ix_roads_start_end", "start_node", "end_node"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    start_node: Mapped[str] = mapped_column(String(100))
    end_node: Mapped[str] = mapped_column(String(100))
    distance_km: Mapped[float] = mapped_column(Float)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    traffic_multiplier: Mapped[float] = mapped_column(Float, default=1.0)


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_location_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_location_longitude"),
        Index("ix_locations_owner_time", "owner_type", "owner_id", "recorded_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_type: Mapped[str] = mapped_column(String(24))
    owner_id: Mapped[str] = mapped_column(String(36))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Dispatch(Base):
    __tablename__ = "dispatches"
    __table_args__ = (
        UniqueConstraint("emergency_id", name="uq_dispatch_emergency"),
        Index("ix_dispatch_vehicle_status", "vehicle_id", "status"),
        Index(
            "uq_dispatch_active_vehicle",
            "vehicle_id",
            unique=True,
            sqlite_where=text("status IN ('Dispatched', 'En Route', 'On Scene', 'Transporting')"),
            postgresql_where=text("status IN ('Dispatched', 'En Route', 'On Scene', 'Transporting')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    emergency_id: Mapped[str] = mapped_column(ForeignKey("emergencies.id", ondelete="CASCADE"))
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("ambulances.id", ondelete="RESTRICT"))
    approved_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(24), default="Dispatched")
    route_algorithm: Mapped[str] = mapped_column(String(24), default="dijkstra")
    distance_km: Mapped[float] = mapped_column(Float)
    estimated_travel_time_min: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emergency: Mapped[Emergency] = relationship(back_populates="dispatch")
    vehicle: Mapped[Ambulance] = relationship(back_populates="dispatches")


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"
    __table_args__ = (Index("ix_emergency_events_emergency_time", "emergency_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    emergency_id: Mapped[str] = mapped_column(ForeignKey("emergencies.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(48))
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    emergency: Mapped[Emergency] = relationship(back_populates="events")
    actor: Mapped[User | None] = relationship(back_populates="emergency_events")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read_time", "user_id", "is_read", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AlgorithmRun(Base):
    __tablename__ = "algorithm_runs"
    __table_args__ = (Index("ix_algorithm_runs_name_time", "algorithm", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    algorithm: Mapped[str] = mapped_column(String(24))
    source: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    distance_km: Mapped[float] = mapped_column(Float)
    execution_time_ms: Mapped[float] = mapped_column(Float)
    nodes_explored: Mapped[int] = mapped_column(Integer)
    operations: Mapped[int] = mapped_column(Integer)
    trace_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user_expiry", "user_id", "expires_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="refresh_tokens")
