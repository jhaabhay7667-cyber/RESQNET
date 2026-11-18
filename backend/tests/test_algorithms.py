from concurrent.futures import ThreadPoolExecutor

import pytest

from app.algorithms.dispatch import GreedyDispatcher
from app.algorithms.graph import Graph, astar, build_demo_graph, dijkstra, run_algorithm
from app.algorithms.structures import (
    BinaryMinHeap,
    DisjointSetUnion,
    EmergencyPriorityQueue,
    FenwickTree,
    LRUCache,
    SegmentTree,
    Trie,
)


def test_dijkstra_single_vertex_and_invalid_or_disconnected_nodes() -> None:
    graph = Graph()
    graph.add_vertex("only")
    assert dijkstra(graph, "only", "only").path == ["only"]
    graph.add_vertex("isolated")
    with pytest.raises(ValueError, match="No route"):
        dijkstra(graph, "only", "isolated")
    with pytest.raises(ValueError, match="Unknown vertex"):
        dijkstra(graph, "only", "missing")


def test_equal_paths_and_blocked_road() -> None:
    graph = Graph()
    for node in ("A", "B", "C", "D"):
        graph.add_vertex(node)
    graph.add_edge("A", "B", 2)
    graph.add_edge("B", "D", 2)
    graph.add_edge("A", "C", 2)
    graph.add_edge("C", "D", 2)
    result = dijkstra(graph, "A", "D")
    assert result.distance == 4
    assert result.path in (["A", "B", "D"], ["A", "C", "D"])
    graph.block_road("A", "B")
    assert dijkstra(graph, "A", "D").path == ["A", "C", "D"]
    graph.reopen_road("A", "B")
    assert "B" in graph.reachable("A")


def test_graph_mutations_and_duplicate_vertex() -> None:
    graph = Graph()
    graph.add_vertex("A")
    graph.add_vertex("A")
    graph.add_vertex("B")
    graph.add_edge("A", "B", 1)
    graph.update_traffic("A", "B", 2)
    assert dijkstra(graph, "A", "B").distance == 2
    graph.remove_edge("A", "B")
    with pytest.raises(ValueError, match="No route"):
        dijkstra(graph, "A", "B")
    graph.remove_vertex("B")
    assert "B" not in graph.adjacency


def test_astar_matches_dijkstra_on_demo_graph() -> None:
    graph = build_demo_graph()
    assert astar(graph, "North Hub", "South Ward").distance == dijkstra(graph, "North Hub", "South Ward").distance
    assert run_algorithm(graph, "North Hub", "South Ward", "bfs").path[0] == "North Hub"
    assert run_algorithm(graph, "North Hub", "South Ward", "dfs").path[-1] == "South Ward"


def test_heap_underflow_and_order() -> None:
    heap: BinaryMinHeap[int] = BinaryMinHeap()
    with pytest.raises(IndexError):
        heap.pop()
    with pytest.raises(IndexError):
        heap.peek()
    for value in (5, 1, 3, 1):
        heap.push(value)
    assert [heap.pop() for _ in range(4)] == [1, 1, 3, 5]


def test_priority_queue_wait_boost_and_stable_order() -> None:
    queue: EmergencyPriorityQueue[str] = EmergencyPriorityQueue(starvation_interval_seconds=10, max_wait_boost=5)
    queue.push("old-low", priority=1, enqueued_at=0)
    queue.push("new-high", priority=5, enqueued_at=100)
    assert queue.pop(now=100) == "old-low"
    assert queue.pop(now=100) == "new-high"


def test_trie_prefix_collisions() -> None:
    trie = Trie()
    trie.insert("rescue")
    trie.insert("res")
    assert trie.search("res")
    assert trie.search("rescue")
    assert not trie.search("rescu")
    assert trie.starts_with("rescu")


def test_disjoint_set_union_and_connectivity() -> None:
    dsu = DisjointSetUnion(["north", "south"])
    assert dsu.union("north", "central")
    assert dsu.find("north") == dsu.find("central")
    assert dsu.find("south") != dsu.find("central")
    assert not dsu.union("north", "central")


def test_segment_and_fenwick_range_queries() -> None:
    segment = SegmentTree([1, 2, 3, 4, 5])
    assert segment.query(1, 3) == 9
    segment.update(2, 10)
    assert segment.query(1, 3) == 16
    fenwick = FenwickTree([1, 2, 3, 4, 5])
    assert fenwick.range_sum(1, 3) == 9
    fenwick.add(2, 7)
    assert fenwick.range_sum(1, 3) == 16


def test_lru_cache_evicts_least_recently_used() -> None:
    cache: LRUCache[str, int] = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1


def test_dispatch_reservation_is_atomic_for_concurrent_calls() -> None:
    dispatcher = GreedyDispatcher(build_demo_graph())

    def reserve() -> bool:
        try:
            dispatcher.reserve("amb-1")
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: reserve(), range(16)))
    assert sum(results) == 1
