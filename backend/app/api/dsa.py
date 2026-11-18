from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..algorithms.graph import run_algorithm
from ..database import get_db
from ..models import AlgorithmRun, User
from ..schemas import DsaRunRequest
from .deps import require_roles
from .graph_service import graph_from_db

router = APIRouter(prefix="/dsa", tags=["dsa"])
COMPLEXITY = {
    "dijkstra": ("O((V + E) log V)", "O(V)"),
    "astar": ("O((V + E) log V) worst case", "O(V)"),
    "bfs": ("O(V + E)", "O(V)"),
    "dfs": ("O(V + E)", "O(V)"),
}


@router.post("/run")
def run_dsa(
    payload: DsaRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Administrator", "Emergency Dispatcher", "Field Operator", "Hospital Operator")),
) -> dict:
    graph = graph_from_db(db)
    try:
        result = run_algorithm(graph, payload.source, payload.destination, payload.algorithm)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    run = AlgorithmRun(
        user_id=user.id,
        algorithm=result.algorithm,
        source=payload.source,
        destination=payload.destination,
        distance_km=result.distance,
        execution_time_ms=result.execution_time_ms,
        nodes_explored=result.nodes_explored,
        operations=result.operations,
        trace_json=json.dumps(result.trace),
    )
    db.add(run)
    db.commit()
    return {
        **result.as_dict(),
        "time_complexity": COMPLEXITY[result.algorithm][0],
        "space_complexity": COMPLEXITY[result.algorithm][1],
        "memory_peak_bytes": None,
        "trace": result.trace,
    }


@router.post("/benchmark")
def benchmark(
    payload: DsaRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Administrator", "Emergency Dispatcher", "Field Operator", "Hospital Operator")),
) -> dict:
    graph = graph_from_db(db)
    try:
        results = [run_algorithm(graph, payload.source, payload.destination, name) for name in ("dijkstra", "astar")]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for result in results:
        db.add(AlgorithmRun(user_id=user.id, algorithm=result.algorithm, source=payload.source, destination=payload.destination, distance_km=result.distance, execution_time_ms=result.execution_time_ms, nodes_explored=result.nodes_explored, operations=result.operations, trace_json=json.dumps(result.trace)))
    db.commit()
    return {
        "runs": [{
            "algorithm": result.algorithm,
            "path": result.path,
            "distance": result.distance,
            "execution_time_ms": result.execution_time_ms,
            "nodes_explored": result.nodes_explored,
            "operations": result.operations,
        } for result in results],
        "warning": "Execution time is environment- and load-dependent; do not compare across different machines.",
    }


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), _user: User = Depends(require_roles("Administrator", "Emergency Dispatcher"))) -> list[dict]:
    records = db.query(AlgorithmRun).order_by(AlgorithmRun.created_at.desc()).limit(100).all()
    return [{"id": item.id, "algorithm": item.algorithm, "source": item.source, "destination": item.destination, "distance": item.distance_km, "execution_time_ms": item.execution_time_ms, "nodes_explored": item.nodes_explored, "operations": item.operations, "created_at": item.created_at.isoformat()} for item in records]
