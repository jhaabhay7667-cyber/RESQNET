from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import time
from typing import Any

from .graph import Graph, dijkstra

CATEGORY_VEHICLE_TYPES = {
    "Fire Emergency": {"Fire Truck", "Rescue Unit"},
    "Road Accident": {"Ambulance", "Rescue Unit"},
    "Medical Emergency": {"Ambulance"},
    "Road Blockage": {"Rescue Unit", "Support Van"},
}
EQUIPMENT_NEEDS = {
    "Critical": {"advanced", "trauma", "rescue"},
    "High": {"advanced", "first aid", "rescue"},
    "Medium": {"first aid"},
    "Low": set(),
}


@dataclass
class GreedyDispatcher:
    """Greedy resource allocator with an explicit no-double-assignment guard."""

    graph: Graph
    assigned_vehicle_ids: set[str] = field(default_factory=set)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def recommend(self, emergency: dict[str, Any], vehicles: list[dict[str, Any]]) -> dict[str, Any]:
        category = str(emergency.get("category", ""))
        severity = str(emergency.get("severity", "Medium"))
        allowed_types = CATEGORY_VEHICLE_TYPES.get(category, set())
        required_equipment = EQUIPMENT_NEEDS.get(severity, set())
        candidates: list[tuple[float, dict[str, Any], float]] = []

        for vehicle in vehicles:
            vehicle_id = str(vehicle.get("id", ""))
            if vehicle.get("status") != "Available" or vehicle_id in self.assigned_vehicle_ids:
                continue
            if allowed_types and vehicle.get("vehicle_type") not in allowed_types:
                continue
            if int(vehicle.get("capacity", 0)) < 1:
                continue
            equipment = str(vehicle.get("equipment", "")).casefold()
            matching = sum(1 for requirement in required_equipment if requirement in equipment)
            try:
                start = str(vehicle["graph_node"])
                end = str(emergency["graph_node"])
                distance = dijkstra(self.graph, start, end).distance
            except (KeyError, ValueError):
                continue
            eta = distance * 2.4
            score = matching * 10 - eta
            candidates.append((score, vehicle, eta))

        if not candidates:
            return {"vehicle": None, "estimated_travel_time_min": None, "reason": "No suitable available vehicle"}
        candidates.sort(key=lambda candidate: (-candidate[0], candidate[2], str(candidate[1].get("id"))))
        _, vehicle, eta = candidates[0]
        return {
            "vehicle": vehicle,
            "estimated_travel_time_min": round(eta, 1),
            "reason": "Eligible vehicle ranked by equipment fit and road-graph travel time; dispatcher approval required.",
        }

    def reserve(self, vehicle_id: str) -> None:
        with self._lock:
            if vehicle_id in self.assigned_vehicle_ids:
                raise ValueError(f"Vehicle already assigned: {vehicle_id}")
            self.assigned_vehicle_ids.add(vehicle_id)

    def release(self, vehicle_id: str) -> None:
        with self._lock:
            self.assigned_vehicle_ids.discard(vehicle_id)


def priority_score(severity: str, category: str, created_at: float, now: float | None = None) -> float:
    severity_score = {"Critical": 5, "High": 4, "Medium": 3, "Low": 1}.get(severity, 1)
    category_bonus = {"Medical Emergency": 0.5, "Fire Emergency": 0.4, "Road Accident": 0.3}.get(category, 0.0)
    wait_minutes = max(0.0, ((now if now is not None else time()) - created_at) / 60)
    return severity_score + category_bonus + min(wait_minutes / 10, 5)
