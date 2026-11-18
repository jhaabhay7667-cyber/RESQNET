from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..algorithms.graph import Graph, build_demo_graph
from ..models import Road


def graph_from_db(db: Session) -> Graph:
    graph = build_demo_graph()
    roads = db.scalars(select(Road)).all()
    for road in roads:
        if road.start_node not in graph.adjacency:
            graph.add_vertex(road.start_node)
        if road.end_node not in graph.adjacency:
            graph.add_vertex(road.end_node)
        graph.add_edge(road.start_node, road.end_node, road.distance_km)
        if road.blocked:
            graph.block_road(road.start_node, road.end_node)
        if road.traffic_multiplier != 1:
            graph.update_traffic(road.start_node, road.end_node, road.traffic_multiplier)
    return graph


def haversine_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1 = first
    lat2, lon2 = second
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi, delta_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    value = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lon / 2) ** 2
    return 6371 * 2 * asin(sqrt(value))


def nearest_graph_node(graph: Graph, latitude: float, longitude: float) -> str:
    if not graph.adjacency:
        raise ValueError("Road graph has no vertices")
    point = (latitude, longitude)
    return min(
        graph.adjacency,
        key=lambda node: haversine_km(point, graph.coordinates[node]) if node in graph.coordinates else float("inf"),
    )
