from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..algorithms.graph import Graph, run_algorithm
from ..database import get_db
from ..models import Road, User
from ..schemas import RouteRequest
from .deps import get_current_user, require_roles
from .graph_service import graph_from_db, nearest_graph_node

router = APIRouter(prefix="/routing", tags=["routing"])


def _alternate(graph: Graph, path: list[str], start: str, end: str) -> list[str]:
    alternatives: list[tuple[float, list[str]]] = []
    for left, right in zip(path, path[1:]):
        edge = graph.adjacency[left][right]
        was_blocked = edge.blocked
        reverse = graph.adjacency.get(right, {}).get(left)
        reverse_was_blocked = reverse.blocked if reverse else False
        edge.blocked = True
        if reverse:
            reverse.blocked = True
        try:
            result = run_algorithm(graph, start, end, "dijkstra")
            if result.path != path:
                alternatives.append((result.distance, result.path))
        except ValueError:
            pass
        finally:
            edge.blocked = was_blocked
            if reverse:
                reverse.blocked = reverse_was_blocked
    return min(alternatives, default=(0.0, []), key=lambda entry: entry[0])[1]


@router.get("/roads")
def list_roads(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[dict]:
    records = db.scalars(select(Road).order_by(Road.start_node, Road.end_node)).all()
    graph = graph_from_db(db)
    return [{
        "id": item.id,
        "start": item.start_node,
        "end": item.end_node,
        "distance_km": item.distance_km * item.traffic_multiplier,
        "blocked": item.blocked,
        "coordinates": [
            coordinate
            for coordinate in (graph.coordinates.get(item.start_node), graph.coordinates.get(item.end_node))
            if coordinate is not None
        ],
    } for item in records]


@router.post("/route")
def calculate_route(payload: RouteRequest, db: Session = Depends(get_db), _user: User = Depends(require_roles("Administrator", "Emergency Dispatcher", "Field Operator", "Hospital Operator"))) -> dict:
    graph = graph_from_db(db)
    for start, end in payload.blocked_roads:
        try:
            graph.block_road(start, end)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        start = nearest_graph_node(graph, payload.origin.latitude, payload.origin.longitude)
        end = nearest_graph_node(graph, payload.destination.latitude, payload.destination.longitude)
        result = run_algorithm(graph, start, end, payload.algorithm)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    alternate = _alternate(graph, result.path, start, end)
    return {
        "algorithm": result.algorithm,
        "path": result.path,
        "coordinates": [graph.coordinates[node] for node in result.path if node in graph.coordinates],
        "distance": result.distance,
        "travel_cost": round(result.distance * 2.4, 1),
        "estimated_travel_time_min": round(result.distance * 2.4, 1),
        "nodes_explored": result.nodes_explored,
        "execution_time_ms": result.execution_time_ms,
        "operations": result.operations,
        "alternative_path": alternate,
        "blocked_roads": [{
            "start": left,
            "end": right,
            "coordinates": [coordinate for coordinate in (graph.coordinates.get(left), graph.coordinates.get(right)) if coordinate is not None],
        } for left, right in payload.blocked_roads],
        "route_source": "road graph",
    }
