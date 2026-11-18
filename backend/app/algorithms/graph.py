from __future__ import annotations

from dataclasses import asdict, dataclass, field
from collections import deque
from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt
from time import perf_counter
from typing import Any, Literal

AlgorithmName = Literal["dijkstra", "astar", "bfs", "dfs"]


@dataclass
class Edge:
    weight: float
    blocked: bool = False


@dataclass
class AlgorithmResult:
    algorithm: str
    path: list[str]
    distance: float
    travel_cost: float
    nodes_explored: int
    execution_time_ms: float
    operations: int
    trace: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class Graph:
    """Weighted adjacency-list graph.

    Dijkstra and A* run in O((V + E) log V) time and O(V) auxiliary space.
    BFS/DFS run in O(V + E) time and O(V) auxiliary space.
    Edge weights represent non-negative road distance/cost in kilometers.
    """

    def __init__(self) -> None:
        self.adjacency: dict[str, dict[str, Edge]] = {}
        self.coordinates: dict[str, tuple[float, float]] = {}

    def add_vertex(self, vertex: str, coordinates: tuple[float, float] | None = None) -> None:
        if not vertex:
            raise ValueError("Vertex name cannot be empty")
        self.adjacency.setdefault(vertex, {})
        if coordinates is not None:
            lat, lon = coordinates
            if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError("Invalid geographic coordinates")
            self.coordinates[vertex] = (float(lat), float(lon))

    def remove_vertex(self, vertex: str) -> None:
        self._require_vertex(vertex)
        del self.adjacency[vertex]
        self.coordinates.pop(vertex, None)
        for neighbors in self.adjacency.values():
            neighbors.pop(vertex, None)

    def add_edge(self, start: str, end: str, weight: float, bidirectional: bool = True) -> None:
        self._require_vertex(start)
        self._require_vertex(end)
        if start == end or weight < 0:
            raise ValueError("Road edges must connect distinct vertices and have non-negative weights")
        self.adjacency[start][end] = Edge(float(weight))
        if bidirectional:
            self.adjacency[end][start] = Edge(float(weight))

    def remove_edge(self, start: str, end: str, bidirectional: bool = True) -> None:
        self._require_vertex(start)
        self._require_vertex(end)
        self.adjacency[start].pop(end, None)
        if bidirectional:
            self.adjacency[end].pop(start, None)

    def update_traffic(self, start: str, end: str, multiplier: float, bidirectional: bool = True) -> None:
        if multiplier < 0:
            raise ValueError("Traffic multiplier cannot be negative")
        self._require_edge(start, end)
        self.adjacency[start][end].weight *= multiplier
        if bidirectional and end in self.adjacency and start in self.adjacency[end]:
            self.adjacency[end][start].weight *= multiplier

    def block_road(self, start: str, end: str, bidirectional: bool = True) -> None:
        self._require_edge(start, end)
        self.adjacency[start][end].blocked = True
        if bidirectional and end in self.adjacency and start in self.adjacency[end]:
            self.adjacency[end][start].blocked = True

    def reopen_road(self, start: str, end: str, bidirectional: bool = True) -> None:
        self._require_edge(start, end)
        self.adjacency[start][end].blocked = False
        if bidirectional and end in self.adjacency and start in self.adjacency[end]:
            self.adjacency[end][start].blocked = False

    def reachable(self, start: str) -> set[str]:
        self._require_vertex(start)
        seen = {start}
        pending = deque([start])
        while pending:
            current = pending.pop()
            for neighbor, edge in self.adjacency[current].items():
                if not edge.blocked and neighbor not in seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
        return seen

    def _require_vertex(self, vertex: str) -> None:
        if vertex not in self.adjacency:
            raise ValueError(f"Unknown vertex: {vertex}")

    def _require_edge(self, start: str, end: str) -> None:
        self._require_vertex(start)
        self._require_vertex(end)
        if end not in self.adjacency[start]:
            raise ValueError(f"Unknown edge: {start} -> {end}")


def _haversine_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1 = first
    lat2, lon2 = second
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi, delta_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    value = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(value))


def _path_to(previous: dict[str, str | None], start: str, end: str) -> list[str]:
    path: list[str] = []
    current: str | None = end
    while current is not None:
        path.append(current)
        if current == start:
            break
        current = previous.get(current)
    if not path or path[-1] != start:
        return []
    return list(reversed(path))


def _finish(
    graph: Graph,
    name: str,
    path: list[str],
    distance: float,
    explored: int,
    operations: int,
    started: float,
    trace: list[dict[str, Any]],
) -> AlgorithmResult:
    for node in path:
        trace.append({"step": len(trace) + 1, "node": node, "state": "path"})
    return AlgorithmResult(name, path, distance, distance, explored, (perf_counter() - started) * 1000, operations, trace)


def dijkstra(graph: Graph, start: str, end: str) -> AlgorithmResult:
    graph._require_vertex(start)
    graph._require_vertex(end)
    started = perf_counter()
    distances = {node: float("inf") for node in graph.adjacency}
    previous: dict[str, str | None] = {node: None for node in graph.adjacency}
    distances[start] = 0.0
    frontier: list[tuple[float, int, str]] = [(0.0, 0, start)]
    settled: set[str] = set()
    trace: list[dict[str, Any]] = []
    operations = 0

    while frontier:
        distance, _, current = heappop(frontier)
        operations += 1
        if current in settled:
            continue
        settled.add(current)
        trace.append({"step": len(trace) + 1, "node": current, "state": "current", "distance": distance})
        if current == end:
            break
        for neighbor, edge in graph.adjacency[current].items():
            operations += 1
            if edge.blocked or neighbor in settled:
                continue
            candidate = distance + edge.weight
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                previous[neighbor] = current
                heappush(frontier, (candidate, operations, neighbor))
                trace.append({"step": len(trace) + 1, "node": neighbor, "state": "visited", "distance": candidate})

    path = _path_to(previous, start, end)
    if not path:
        raise ValueError(f"No route from {start} to {end}")
    return _finish(graph, "dijkstra", path, distances[end], len(settled), operations, started, trace)


def _admissible_scale(graph: Graph) -> float:
    ratios = []
    for start, neighbors in graph.adjacency.items():
        if start not in graph.coordinates:
            continue
        for end, edge in neighbors.items():
            if edge.blocked or end not in graph.coordinates:
                continue
            geographic = _haversine_km(graph.coordinates[start], graph.coordinates[end])
            if geographic > 0:
                ratios.append(edge.weight / geographic)
    return max(0.0, min(ratios, default=0.0))


def astar(graph: Graph, start: str, end: str) -> AlgorithmResult:
    """A* using a scaled great-circle heuristic guaranteed not to overestimate."""
    graph._require_vertex(start)
    graph._require_vertex(end)
    started = perf_counter()
    goal = graph.coordinates.get(end)
    scale = _admissible_scale(graph) if goal is not None else 0.0

    def heuristic(vertex: str) -> float:
        position = graph.coordinates.get(vertex)
        return _haversine_km(position, goal) * scale if position is not None and goal is not None else 0.0

    distances = {node: float("inf") for node in graph.adjacency}
    previous: dict[str, str | None] = {node: None for node in graph.adjacency}
    distances[start] = 0.0
    frontier: list[tuple[float, int, str]] = [(heuristic(start), 0, start)]
    settled: set[str] = set()
    trace: list[dict[str, Any]] = []
    operations = 0

    while frontier:
        _, _, current = heappop(frontier)
        operations += 1
        if current in settled:
            continue
        settled.add(current)
        trace.append({"step": len(trace) + 1, "node": current, "state": "current", "distance": distances[current]})
        if current == end:
            break
        for neighbor, edge in graph.adjacency[current].items():
            operations += 1
            if edge.blocked or neighbor in settled:
                continue
            candidate = distances[current] + edge.weight
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                previous[neighbor] = current
                heappush(frontier, (candidate + heuristic(neighbor), operations, neighbor))
                trace.append({"step": len(trace) + 1, "node": neighbor, "state": "visited", "distance": candidate})

    path = _path_to(previous, start, end)
    if not path:
        raise ValueError(f"No route from {start} to {end}")
    return _finish(graph, "astar", path, distances[end], len(settled), operations, started, trace)


def traverse(graph: Graph, start: str, end: str, algorithm: Literal["bfs", "dfs"]) -> AlgorithmResult:
    graph._require_vertex(start)
    graph._require_vertex(end)
    started = perf_counter()
    pending = deque([start])
    previous: dict[str, str | None] = {start: None}
    discovered = {start}
    trace: list[dict[str, Any]] = []
    operations = 0
    found = False
    while pending:
        current = pending.popleft() if algorithm == "bfs" else pending.pop()
        operations += 1
        trace.append({"step": len(trace) + 1, "node": current, "state": "current"})
        if current == end:
            found = True
            break
        neighbors = sorted(graph.adjacency[current])
        if algorithm == "dfs":
            neighbors.reverse()
        for neighbor in neighbors:
            operations += 1
            if graph.adjacency[current][neighbor].blocked or neighbor in discovered:
                continue
            discovered.add(neighbor)
            previous[neighbor] = current
            pending.append(neighbor)
            trace.append({"step": len(trace) + 1, "node": neighbor, "state": "visited"})
    path = _path_to(previous, start, end) if found else []
    if not path:
        raise ValueError(f"No route from {start} to {end}")
    distance = sum(graph.adjacency[left][right].weight for left, right in zip(path, path[1:]))
    return _finish(graph, algorithm, path, distance, len(discovered), operations, started, trace)


def run_algorithm(graph: Graph, start: str, end: str, algorithm: AlgorithmName = "dijkstra") -> AlgorithmResult:
    if algorithm == "dijkstra":
        return dijkstra(graph, start, end)
    if algorithm == "astar":
        return astar(graph, start, end)
    if algorithm in {"bfs", "dfs"}:
        return traverse(graph, start, end, algorithm)
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def build_demo_graph() -> Graph:
    graph = Graph()
    vertices = {
        "North Hub": (40.755, -74.008),
        "Central Ave": (40.739, -74.006),
        "Medical District": (40.728, -73.999),
        "City Center": (40.731, -74.016),
        "Old Town": (40.719, -74.014),
        "East Connector": (40.733, -73.995),
        "River East": (40.718, -73.994),
        "South Ward": (40.704, -74.001),
        "Harbor Point": (40.707, -74.018),
    }
    for node, coordinate in vertices.items():
        graph.add_vertex(node, coordinate)
    edges = [
        ("North Hub", "Central Ave", 2.3), ("North Hub", "Harbor Point", 4.1),
        ("Central Ave", "Medical District", 3.4), ("Central Ave", "City Center", 2.8),
        ("Medical District", "South Ward", 2.6), ("City Center", "East Connector", 3.1),
        ("City Center", "Old Town", 1.9), ("Old Town", "River East", 2.5),
        ("East Connector", "River East", 2.7), ("River East", "South Ward", 3.2),
        ("South Ward", "Harbor Point", 5.1),
    ]
    for start, end, weight in edges:
        graph.add_edge(start, end, weight)
    return graph
